#!/usr/bin/env python3
"""
phase_guard.py — Mechanical phase-guard enforcement (PreToolUse hook).

Enforces Laws 1-2 of the harness at the tool layer instead of trusting prompts
(see ADR-0008):

  - Edit/MultiEdit/Write/NotebookEdit to source paths -> only when Phase =
    IMPLEMENT (test paths also allowed when Phase = TEST_VERIFY/VERIFY_FINISH)
  - shell writes (redirects, tee, sed -i, touch) -> TOOL PARITY: a
    Bash/PowerShell write to path X is denied exactly when Write to X would
    be. Best-effort by construction: quoted strings and heredoc bodies are
    stripped before scanning (prose containing '>' can't false-deny), so a
    quoted target is invisible — fail-open prefers false negatives. cp/mv/dd
    and encoded writes (python -c, base64) are out of scope; see SECURITY.md
  - `gh pr create`                           -> only when Phase = FINISH or
    VERIFY_FINISH (fast lane, ADR-0010) and Quality Gate is PASS /
    ACCEPTED_SOFT_FAIL
  - human-only files (.board/approval-policy.md, .state/phase-guard-off)
    -> agent writes DENIED in every phase (ADR-0014 self-licensing
    prevention; humans edit/create them directly)
  - merge verbs (`gh pr merge`; `git push` targeting the default branch)
    -> DENIED in every phase and mode (ADR-0014 never-list item 1 — the
    merge decision is never delegated to any agent)
  - sprint-state.md Phase transitions -> validated against the legal
    full/fast-lane chain (ADR-0015); illegal jumps, forged Quality Gate =
    PASS without a report, and phase blanking are DENIED. The state file
    the guard trusts is no longer freely rewritable by the constrained party.
    Write-tool routes only: shell writes to sprint-state can't be
    content-reconstructed and get best-effort parity, not transition
    validation (documented in SECURITY.md scope notes)
  - board writes under a live foreign board.lock -> DENIED (PRD-003
    mechanical lock; enforced only when board_lock.py is in use)

Pipeline artifacts (.board/, docs/, templates/, reports/, capiva-blueprints/,
PLAN.md) are writable in every phase — the pipeline produces them. NOT
.github/scripts/.claude (source, IMPLEMENT-only) nor the human-only files
(.claude/settings.json, root CLAUDE.md) — see PRD-002.

State source: parses `.board/sprint-state.md` directly (the `- **Field**:`
format defined in state-management.md). There is deliberately NO separate
sprint-state.json — a dual file would drift from the markdown (ADR-0008).

Fail-open: if sprint-state.md is missing, unparseable, or contains merge
conflict markers (a conflicted Phase field must never be trusted to whichever
side sorts first), the guard allows the call and prints a LOUD warning to
stderr. It must never brick a project.

Escape hatch (both logged to stderr, both HUMAN-only by construction):
  - env  CAPIVA_PHASE_GUARD=off  — must be set in Claude Code's own environment
    at launch (the hook is spawned by Claude Code, so per-command env vars in a
    shell tool call cannot reach it)
  - file .state/phase-guard-off  — a HUMAN creates it from their own terminal
    to disable mid-session, deletes it to re-enable; gitignored, explicit,
    auditable. Agent writes to this marker are DENIED in every phase (it is a
    HUMAN_ONLY_FILE — a guard whose off-switch is agent-writable enforces
    nothing; the exact self-licensing class ADR-0014 exists to prevent)

Enforcement heartbeat: every enforced invocation refreshes
.state/guard-heartbeat (PRD-001). A missing/stale heartbeat means the
guard is not firing (e.g. the POSIX dispatch died) — session_context warns
and /capiva:auto refuses to run. Silence must never read as healthy.

Keep the field parser in sync with context-persistence.py (same format).
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
SPRINT_STATE = PROJECT_ROOT / ".board" / "sprint-state.md"
# Enforcement heartbeat (PRD-001): proof-of-life the guard actually fired.
# session_context surfaces it; /capiva:auto refuses autonomy without it.
# On POSIX a non-executable/misdispatched hook fails before the .py runs,
# so a fresh heartbeat is the mechanical signal that enforcement is alive.
HEARTBEAT = PROJECT_ROOT / ".state" / "guard-heartbeat"
# Guard on/off status (PRD-008): a kill-switch flip is an auditable event.
# The run-log records the CHANGE (enforcing <-> off-env/off-marker), not
# every disabled invocation — this file holds the last known status.
GUARD_STATUS = PROJECT_ROOT / ".state" / "guard-status"
RUN_LOG = PROJECT_ROOT / ".state" / "run-log.jsonl"
BOARD_LOCK = PROJECT_ROOT / ".board" / "board.lock"
LOCK_HOLDER = PROJECT_ROOT / ".state" / "lock-holder"
SPRINT_STATE_REL = ".board/sprint-state.md"
BOARD_FILES = (".board/sprint-state.md", ".board/tasks.md")
# Board-lock staleness — keep in sync with scripts/board_lock.py (lint 18).
LOCK_STALE_SECONDS = 120

WRITE_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}

# Dirs writable in ANY phase = genuine pipeline-artifact surfaces only.
# NOT .github / scripts / .claude (PRD-002): CI config is arbitrary code
# execution, scripts are the validators the pipeline trusts, and
# .claude/settings.json IS the hook registration in dev mode — all three
# are self-licensing routes if always-writable. They are source now:
# writable only in IMPLEMENT (a task whose plan legitimately covers them),
# never in IDLE/GRILL/PLAN/TEST_VERIFY.
ALWAYS_ALLOWED_DIRS = (".board", ".state", "docs", "templates", "reports", "capiva-blueprints")
ALWAYS_ALLOWED_FILES = ("PLAN.md", ".gitignore", ".mcp.json")

# Heuristics for "this is a test file" (blueprint test layouts: tests/,
# __tests__/, *.test.*, *.spec.*, *Tests.*, test_*.py)
TEST_PATH_RE = re.compile(
    r"(^|[/\\])(tests?|__tests__)([/\\]|$)"
    r"|\.(test|spec)\.[^/\\]+$"
    r"|Tests?\.[^/\\.]+$"
    r"|(^|[/\\])test_[^/\\]+$",
    re.IGNORECASE,
)

PASSING_GATES = {"PASS", "ACCEPTED_SOFT_FAIL"}

# The complete inventory of what this hook mechanically DENIES — the single
# source of truth for every "mechanically enforced" claim.
# harness_lint check 13 asserts each surface carries its documentation marker
# (<!-- enforced: X -->) in README.md AND SECURITY.md, and that no unknown
# marker exists — claims and code cannot drift apart without failing CI.
# Add a surface ONLY together with its deny logic, its scenarios, and both
# doc rows; the lint fails on any partial landing.
ENFORCED_SURFACES = (
    "source-writes-outside-implement",  # write tools + shell parity
    "pr-create-gate",                   # FINISH/VERIFY_FINISH + passing gate
    "human-only-files",                 # approval-policy.md + kill-switch marker
    "merge-verbs",                      # gh pr merge; git push -> default branch
    "sprint-state-transitions",         # illegal Phase jumps / forged gate / blanking
    "board-lock",                       # board writes under a live foreign lock
)  # NOTE: no parentheses inside this tuple — lint check 13 parses it with a
   # first-closing-paren regex; keep comments paren-free.

# Human-only files: agent writes denied in EVERY phase (ADR-0014 self-licensing
# prevention), each with its own deny message. The approval policy is the
# delegated portion of Law 5 — an agent that can edit it can grant itself
# permissions. The kill-switch marker is the guard's own off-switch — an agent
# that can write it can disable ALL enforcement for the session. Checked BEFORE
# the always-allowed dirs so .board/.state general writability doesn't bypass.
HUMAN_ONLY_FILES = {
    ".board/approval-policy.md": (
        "Phase guard: .board/approval-policy.md is human-authored law "
        "(ADR-0014). Agents may not edit it in any phase — propose the "
        "change as an escalation in .board/approvals.md instead."
    ),
    ".state/phase-guard-off": (
        "Phase guard: .state/phase-guard-off is the guard's own kill switch. "
        "Agents may not create or edit it in any phase (ADR-0014 "
        "self-licensing prevention). If you believe enforcement must be "
        "disabled, stop and ask the human — they create the marker from "
        "their own terminal."
    ),
    ".claude/settings.json": (
        "Phase guard: .claude/settings.json registers the hooks themselves "
        "(dev/copy mode) — an agent that rewrites it can DEREGISTER its own "
        "guard (PRD-002, same self-licensing class as the kill switch). "
        "Humans edit hook registration directly."
    ),
    "CLAUDE.md": (
        "Phase guard: a root CLAUDE.md is auto-loaded by Claude Code as project "
        "instructions — rewriting it is a prompt-level self-licensing channel "
        "(PRD-002). Agents may not edit it in any phase; humans author project "
        "instructions directly."
    ),
}
# Fast lane (ADR-0010): VERIFY_FINISH combines TEST_VERIFY + FINISH.
TEST_WRITE_PHASES = {"TEST_VERIFY", "VERIFY_FINISH"}
PR_PHASES = {"FINISH", "VERIFY_FINISH"}

# Merge verbs (ADR-0014 never-list item 1): denied in EVERY phase and mode.
# `gh pr merge` in any form; `git push` whose target resolves to the default
# branch. Bare `git merge` is deliberately NOT matched — merging the default
# branch INTO a feature branch is legitimate mid-IMPLEMENT work, and knowing
# the direction would require running git inside the hook. Known limits
# (documented in SECURITY.md): a bare `git push` on a checked-out default
# branch, the GitHub web UI, and GitHub MCP tools are not interceptable here —
# branch protection is the backstop for those routes.
GH_PR_MERGE_RE = re.compile(r"\bgh\s+pr\s+merge\b")
GIT_PUSH_RE = re.compile(r"\bgit\s+push\b")
DEFAULT_BRANCHES = {"main", "master"}

# Shell write parity. Strip heredoc BODIES and quoted strings first
# so prose containing '>' (commit messages, echo'd text) can never false-deny;
# the cost is that quoted targets are invisible — fail-open prefers false
# negatives over blocking legitimate work. Then extract targets of: > and >>
# redirects (also catches heredoc-fed `cat > file <<EOF`), tee, sed -i, touch.
HEREDOC_BODY_RE = re.compile(r"<<-?\s*'?(\w+)'?[^\n]*\n.*?\n\s*\1\s*(?=\n|$|\))", re.DOTALL)
QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")
REDIRECT_RE = re.compile(r"(?<![<>=\-\w])>{1,2}\s*([^\s;&|<>()]+)")


def _shell_write_targets(command: str):
    """Best-effort extraction of paths a shell command writes to.

    Conservative by design (grill decision 2026-07-08): redirects, tee,
    sed -i, touch. Tokens containing shell expansions ($, `, %) are skipped —
    unresolvable means fail-open. cp/mv/dd and interpreter one-liners are
    documented limits (SECURITY.md), not silently claimed coverage.
    """
    text = HEREDOC_BODY_RE.sub("\n", command)
    # Replace quoted strings with a placeholder instead of DELETING them:
    # deletion made `> "quoted" 2>/dev/null` collapse to `>  2>/dev/null`,
    # and REDIRECT_RE captured the neighboring `2` as a write target — a
    # live false deny (PRD-009). The placeholder keeps quoted targets
    # invisible-by-design (fail-open, documented) without shifting tokens.
    text = QUOTED_RE.sub("\x00", text)
    targets = [m.group(1) for m in REDIRECT_RE.finditer(text)]
    for seg in re.split(r"[;&|]", text):
        toks = seg.split()
        for cmd_name in ("tee", "touch"):
            if cmd_name in toks:
                targets.extend(
                    t for t in toks[toks.index(cmd_name) + 1:]
                    if not t.startswith("-"))
        if "sed" in toks and any(t.startswith("-i") for t in toks):
            files = [t for t in toks[toks.index("sed") + 1:]
                     if not t.startswith("-")]
            if files:
                targets.append(files[-1])  # sed expr is quoted (stripped); file is last
    return [t for t in targets
            if t and not any(c in t for c in ("$", "`", "%", "\x00"))]


def _push_targets_default_branch(command: str) -> bool:
    """True if any `git push` segment of the command targets main/master.

    Tokenizes each push segment (up to the next shell separator). A token
    denies when it is the default branch itself, a refspec whose DESTINATION
    is the default branch (HEAD:main, refs/heads/main), or --all/--mirror
    (which push the default branch among everything else). A refspec whose
    destination is elsewhere (main:backup) and branch names that merely
    contain 'main' (feature/main-menu) do not match.
    """
    for m in GIT_PUSH_RE.finditer(command):
        segment = re.split(r"[;&|]", command[m.end():])[0]
        for tok in segment.split():
            tok = tok.strip("'\"")
            if tok.startswith("-"):
                if tok in ("--all", "--mirror"):
                    return True
                continue
            dst = tok.split(":", 1)[1] if ":" in tok else tok
            if dst.startswith("refs/heads/"):
                dst = dst[len("refs/heads/"):]
            if dst in DEFAULT_BRANCHES:
                return True
    return False


def _parse_field(content: str, field: str) -> str:
    m = re.search(rf"^- \*\*{re.escape(field)}\*\*:\s*(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _read_state():
    """Returns (phase, quality_gate, task_id) or None if unavailable (fail-open)."""
    try:
        content = SPRINT_STATE.read_text(encoding="utf-8")
    except OSError:
        return None
    if "<<<<<<<" in content:
        # A conflicted state file is neither missing nor unparseable — the
        # first `Phase:` regex match would silently win, enforcing whichever
        # side sorts first (enforcement-code audit §6). Never trust
        # it: fail open LOUDLY instead.
        print(
            "phase_guard: .board/sprint-state.md contains merge-conflict "
            "markers — no parsed field can be trusted; failing open (no "
            "enforcement). RESOLVE THE CONFLICT before any pipeline work.",
            file=sys.stderr,
        )
        return None
    phase = _parse_field(content, "Phase").upper()
    if not phase:
        return None
    return phase, _parse_field(content, "Quality Gate").upper(), _parse_field(content, "Task ID")


def _deny(reason: str):
    _run_log("deny", reason=reason[:200])
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def _allow():
    sys.exit(0)


def _is_always_allowed(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        return True  # outside the project (scratchpad, temp) — not ours to guard
    parts = rel.parts
    if not parts:
        return True
    if parts[0] in ALWAYS_ALLOWED_DIRS:
        return True
    if len(parts) == 1 and (parts[0] in ALWAYS_ALLOWED_FILES or parts[0].endswith(".md")):
        return True
    return False


def _write_denial(path: Path, phase: str):
    """The single write decision, shared by every route (tool parity):
    Edit/MultiEdit/Write/NotebookEdit and shell-extracted write targets all
    resolve here. Returns a deny reason, or None to allow."""
    try:
        rel = str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
        if rel in HUMAN_ONLY_FILES:
            return HUMAN_ONLY_FILES[rel]
    except ValueError:
        pass
    if _is_always_allowed(path):
        return None
    if phase == "IMPLEMENT":
        return None
    if phase in TEST_WRITE_PHASES and TEST_PATH_RE.search(str(path)):
        return None
    return (
        f"Phase guard: source file writes require Phase = IMPLEMENT "
        f"(tests also allowed in TEST_VERIFY / VERIFY_FINISH). Current phase: {phase or 'UNKNOWN'}. "
        f"Run /capiva:sprint to advance the pipeline, or edit pipeline artifacts "
        f"(docs/, .board/, PLAN.md) instead. File: {path}"
    )



# Legal sprint-state Phase transitions (PRD-003 / ADR-0015). The guard now
# validates the Phase field on writes to sprint-state.md instead of trusting a
# file the constrained party can freely rewrite. Same-phase (field updates),
# ANY->BLOCKED, ANY->IDLE (abort), and BLOCKED->* (resume) are always legal;
# the rest must follow the full- or fast-lane chain.
_LEGAL_EDGES = {
    ("IDLE", "TRIAGE"), ("TRIAGE", "GRILL_SPEC"), ("GRILL_SPEC", "PLAN"),
    ("PLAN", "IMPLEMENT"), ("IMPLEMENT", "TEST_VERIFY"), ("TEST_VERIFY", "FINISH"),
    ("FINISH", "IDLE"),
    ("TRIAGE", "SPEC_PLAN"), ("SPEC_PLAN", "IMPLEMENT"),
    ("IMPLEMENT", "VERIFY_FINISH"), ("VERIFY_FINISH", "IDLE"),
    ("SPEC_PLAN", "GRILL_SPEC"), ("VERIFY_FINISH", "TEST_VERIFY"),
    ("IDLE", "REFINING"),  # RFN-004: clustered/batch-refine entry (ADR-0014
    # clustered-mode amendment). REFINING->IDLE (batch done) and ->BLOCKED are
    # already auto-legal; only the entry edge is added. Minimal, additive.
}


def _transition_legal(old_phase: str, new_phase: str) -> bool:
    if not old_phase or old_phase == new_phase:
        return True            # first write / field update within a phase
    if new_phase in ("BLOCKED", "IDLE"):
        return True            # escalation / abort always legal
    if old_phase == "BLOCKED":
        return True            # resume from BLOCKED (prior phase unknown here)
    return (old_phase, new_phase) in _LEGAL_EDGES


def _projected_content(tool_name: str, tool_input: dict, disk: str):
    """Reconstruct the sprint-state content this write would produce, or None
    if it can't be determined (then transition validation is skipped)."""
    if tool_name == "Write":
        return tool_input.get("content")
    if tool_name == "Edit":
        old_s = tool_input.get("old_string")
        new_s = tool_input.get("new_string")
        if old_s is None or new_s is None or old_s not in disk:
            return None
        count = -1 if tool_input.get("replace_all") else 1
        return disk.replace(old_s, new_s) if count == -1 else disk.replace(old_s, new_s, 1)
    if tool_name == "MultiEdit":
        content = disk
        for e in tool_input.get("edits", []):
            o, n = e.get("old_string"), e.get("new_string")
            if o is None or n is None or o not in content:
                return None
            content = content.replace(o, n) if e.get("replace_all") else content.replace(o, n, 1)
        return content
    return None


def _transition_denial(tool_name: str, tool_input: dict):
    """Validate a write to sprint-state.md: legal Phase transition, artifact
    preconditions on entering IMPLEMENT/FINISH, no forged PASS, no phase blanking.
    Returns a deny reason or None. Fails OPEN only when the new content can't be
    reconstructed (reads fail open; writes fail closed on a corrupt transition)."""
    try:
        disk = SPRINT_STATE.read_text(encoding="utf-8")
    except OSError:
        disk = ""
    new = _projected_content(tool_name, tool_input, disk)
    if new is None:
        return None  # can't reconstruct (e.g. shell redirect) — don't block
    old_phase = _parse_field(disk, "Phase").upper()
    new_phase = _parse_field(new, "Phase").upper()

    # phase blanking: a valid active phase must not vanish (fail-open exploit)
    if old_phase and old_phase not in ("IDLE", "") and not new_phase:
        return ("Phase guard: this write blanks the Phase field while a pipeline "
                "task is active (was %s). A blank phase silently disables "
                "enforcement (fail-open) — refused. Set an explicit legal phase."
                % old_phase)

    if not _transition_legal(old_phase, new_phase):
        return ("Phase guard: illegal phase transition %s -> %s in sprint-state.md "
                "(ADR-0015). Legal steps follow the full/fast lane; use "
                "/capiva:sprint to advance, or -> BLOCKED / IDLE to escalate/abort."
                % (old_phase or "(none)", new_phase or "(none)"))

    task_id = _parse_field(new, "Task ID")
    # artifact preconditions on ENTERING a phase (Law 3 rising to the hook)
    if new_phase == "IMPLEMENT" and old_phase != "IMPLEMENT":
        missing = []
        if not (PROJECT_ROOT / "PLAN.md").is_file():
            missing.append("PLAN.md")
        if task_id and not (PROJECT_ROOT / "docs" / "specs" / f"{task_id}-acs.json").is_file():
            missing.append(f"docs/specs/{task_id}-acs.json")
        if missing:
            return ("Phase guard: cannot enter IMPLEMENT without %s on disk "
                    "(ADR-0015 artifact precondition). Produce the plan and the "
                    "acs.json first." % " + ".join(missing))
    if new_phase == "FINISH" and old_phase != "FINISH":
        if task_id and not (PROJECT_ROOT / "docs" / "reports" / f"{task_id}-quality.md").is_file():
            return ("Phase guard: cannot enter FINISH without the quality report "
                    "docs/reports/%s-quality.md on disk (ADR-0015). Run "
                    "/capiva:test-verify first." % task_id)

    # forged pass: PASS/ACCEPTED_SOFT_FAIL can only be SET when a report exists
    old_gate = _parse_field(disk, "Quality Gate").upper()
    new_gate = _parse_field(new, "Quality Gate").upper()
    if new_gate in PASSING_GATES and old_gate not in PASSING_GATES:
        if task_id and not (PROJECT_ROOT / "docs" / "reports" / f"{task_id}-quality.md").is_file():
            return ("Phase guard: cannot set Quality Gate = %s without a quality "
                    "report (docs/reports/%s-quality.md) on disk — a gate is not "
                    "PASS just because the field says so (ADR-0015)." % (new_gate, task_id))
    if new_phase and new_phase != old_phase:
        _run_log("transition", task=task_id, frm=old_phase or "(none)", to=new_phase)
    if new_gate in PASSING_GATES and old_gate not in PASSING_GATES:
        _run_log("gate", task=task_id, gate=new_gate)
    return None


def _board_lock_denial(rel: str):
    """Deny a board write held by another live holder (PRD-003 mechanical lock).
    Enforced only when the lock mechanism is in use (both board.lock and
    .state/lock-holder exist) — absent either, defer to the prose ritual so an
    adopter mid-migration is never bricked."""
    if rel not in BOARD_FILES or not BOARD_LOCK.is_file() or not LOCK_HOLDER.is_file():
        return None
    try:
        holder = epoch = None
        for line in BOARD_LOCK.read_text(encoding="utf-8").splitlines():
            if line.startswith("holder="):
                holder = line[7:].strip()
            elif line.startswith("epoch="):
                epoch = float(line[6:].strip())
        mine = LOCK_HOLDER.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return None
    if holder is None or epoch is None:
        return None
    from time import time as _now
    if (_now() - epoch) > LOCK_STALE_SECONDS:
        return None  # stale — ignore
    if holder == mine:
        return None  # this session holds it
    return ("Phase guard: %s is board-locked by another holder (%s). Wait for "
            "release or, if the lock is stale, let board_lock.py steal it — do "
            "not write the board under a live foreign lock (PRD-003)." % (rel, holder))


def _check_file_write(tool_name: str, tool_input: dict, phase: str):
    raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw:
        _allow()
    path = Path(raw) if os.path.isabs(raw) else PROJECT_ROOT / raw
    try:
        rel = str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        rel = ""
    # board-lock + transition validation run BEFORE the always-allowed
    # short-circuit (sprint-state/.board are always-allowed for writes, but
    # WHICH writes is exactly what PRD-003 governs).
    lock_reason = _board_lock_denial(rel)
    if lock_reason:
        _deny(lock_reason)
    if rel == SPRINT_STATE_REL:
        tr = _transition_denial(tool_name, tool_input)
        if tr:
            _deny(tr)
    reason = _write_denial(path, phase)
    if reason:
        _deny(reason)
    _allow()


def _check_shell(tool_input: dict, phase: str, gate: str):
    command = tool_input.get("command", "")
    if GH_PR_MERGE_RE.search(command):
        _deny(
            "Phase guard: `gh pr merge` is the merge decision — item 1 of the "
            "ADR-0014 never-list. No agent may merge in any phase or mode. "
            "The human merges from their own terminal or the GitHub UI."
        )
    if _push_targets_default_branch(command):
        _deny(
            "Phase guard: `git push` targeting the default branch "
            "(main/master) is denied in every phase — changes land only via "
            "reviewed pull requests (ADR-0014 never-list). Push a feature "
            "branch and open the PR at FINISH instead."
        )
    for raw in _shell_write_targets(command):
        p = Path(raw) if os.path.isabs(raw) else PROJECT_ROOT / raw
        reason = _write_denial(p, phase)
        if reason:
            _deny(reason + f" (detected as a shell write target: {raw})")
    if re.search(r"\bgh\s+pr\s+create\b", command):
        if phase not in PR_PHASES:
            _deny(
                f"Phase guard: `gh pr create` requires Phase = FINISH "
                f"(or VERIFY_FINISH in the fast lane). "
                f"Current phase: {phase or 'UNKNOWN'}. Complete /capiva:test-verify and "
                f"quality review first, then /capiva:finish creates the PR."
            )
        if gate not in PASSING_GATES:
            _deny(
                f"Phase guard: `gh pr create` requires Quality Gate = PASS or "
                f"ACCEPTED_SOFT_FAIL. Current: {gate or '--'}. Run /capiva:test-verify "
                f"and pass the quality gates first."
            )
    _allow()


def _run_log(event: str, **fields):
    """Append one JSONL line to the mechanical run-log (PRD-004). Hook-written,
    append-only — the audit trail is NOT the same agent's markdown narrative.
    Best-effort: a logging failure must never block a tool call."""
    try:
        RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rec = {"ts": stamp, "event": event}
        rec.update(fields)
        with RUN_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _touch_heartbeat(phase: str):
    """Drop a proof-of-life marker on every enforced invocation. Best-effort:
    a heartbeat failure must never block a tool call."""
    try:
        HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        HEARTBEAT.write_text(f"{stamp} phase={phase or '--'}\n", encoding="utf-8")
    except Exception:
        pass


def _guard_status(status: str):
    """Record the guard's on/off status; run-log the CHANGE only (PRD-008).
    A kill-switch flip must leave a mechanical trace — but logging every
    disabled invocation would flood an append-only log. Best-effort."""
    try:
        prev = GUARD_STATUS.read_text(encoding="utf-8").strip() if GUARD_STATUS.is_file() else ""
        if prev != status:
            GUARD_STATUS.parent.mkdir(parents=True, exist_ok=True)
            GUARD_STATUS.write_text(status + "\n", encoding="utf-8")
            _run_log("guard-status", status=status, previous=prev or "(none)")
    except Exception:
        pass


def main():
    if os.environ.get("CAPIVA_PHASE_GUARD", "").lower() in ("off", "0", "false"):
        print("phase_guard: disabled via CAPIVA_PHASE_GUARD", file=sys.stderr)
        _guard_status("off-env")
        _allow()
    if (PROJECT_ROOT / ".state" / "phase-guard-off").is_file():
        print("phase_guard: disabled via .state/phase-guard-off marker", file=sys.stderr)
        _guard_status("off-marker")
        _allow()

    try:
        payload = json.load(sys.stdin)
    except Exception:
        _allow()  # unparseable input — never block on our own failure

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    state = _read_state()
    if state is None:
        print(
            "phase_guard: .board/sprint-state.md missing or unparseable — "
            "failing open (no enforcement).",
            file=sys.stderr,
        )
        _allow()
    phase, gate, _task = state
    _touch_heartbeat(phase)
    _guard_status("enforcing")

    if tool_name in WRITE_TOOLS:
        _check_file_write(tool_name, tool_input, phase)
    elif tool_name in SHELL_TOOLS:
        _check_shell(tool_input, phase, gate)
    _allow()


if __name__ == "__main__":
    main()
