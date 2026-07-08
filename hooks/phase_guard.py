#!/usr/bin/env python3
"""
phase_guard.py — Mechanical phase-guard enforcement (PreToolUse hook).

Enforces Laws 1-2 of the harness at the tool layer instead of trusting prompts
(see ADR-0008):

  - Edit/MultiEdit/Write/NotebookEdit to source paths -> only when Phase =
    IMPLEMENT (test paths also allowed when Phase = TEST_VERIFY/VERIFY_FINISH)
  - shell writes (redirects, tee, sed -i, touch) -> TOOL PARITY (AUD-005): a
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

Pipeline artifacts (.board/, docs/, .claude/, templates/, PLAN.md, root *.md)
are writable in every phase — the pipeline itself produces them.

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

Keep the field parser in sync with context-persistence.py (same format).
"""

import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
SPRINT_STATE = PROJECT_ROOT / ".board" / "sprint-state.md"

WRITE_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}

# Paths writable in ANY phase — pipeline artifacts plus harness/CI tooling.
ALWAYS_ALLOWED_DIRS = (".board", ".claude", ".state", ".github", "docs", "scripts", "templates", "reports", "capiva-blueprints")
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
# source of truth for every "mechanically enforced" claim (AUD-011).
# harness_lint check 13 asserts each surface carries its documentation marker
# (<!-- enforced: X -->) in README.md AND SECURITY.md, and that no unknown
# marker exists — claims and code cannot drift apart without failing CI.
# Add a surface ONLY together with its deny logic, its scenarios, and both
# doc rows; the lint fails on any partial landing.
ENFORCED_SURFACES = (
    "source-writes-outside-implement",  # write tools + shell parity, AUD-005
    "pr-create-gate",                   # FINISH/VERIFY_FINISH + passing gate
    "human-only-files",                 # approval-policy.md + kill-switch marker
    "merge-verbs",                      # gh pr merge; git push -> default branch
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

# Shell write parity (AUD-005). Strip heredoc BODIES and quoted strings first
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
    text = QUOTED_RE.sub("", text)
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
            if t and not any(c in t for c in ("$", "`", "%"))]


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
        # side sorts first (AUD-005; enforcement-code audit §6). Never trust
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
    """The single write decision, shared by every route (AUD-005 tool parity):
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


def _check_file_write(tool_input: dict, phase: str):
    raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw:
        _allow()
    path = Path(raw) if os.path.isabs(raw) else PROJECT_ROOT / raw
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


def main():
    if os.environ.get("CAPIVA_PHASE_GUARD", "").lower() in ("off", "0", "false"):
        print("phase_guard: disabled via CAPIVA_PHASE_GUARD", file=sys.stderr)
        _allow()
    if (PROJECT_ROOT / ".state" / "phase-guard-off").is_file():
        print("phase_guard: disabled via .state/phase-guard-off marker", file=sys.stderr)
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

    if tool_name in WRITE_TOOLS:
        _check_file_write(tool_input, phase)
    elif tool_name in SHELL_TOOLS:
        _check_shell(tool_input, phase, gate)
    _allow()


if __name__ == "__main__":
    main()
