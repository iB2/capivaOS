#!/usr/bin/env python3
"""
phase_guard.py — Mechanical phase-guard enforcement (PreToolUse hook).

Enforces Laws 1-2 of the harness at the tool layer instead of trusting prompts
(see ADR-0008):

  - Edit/Write/NotebookEdit to source paths  -> only when Phase = IMPLEMENT
    (test paths also allowed when Phase = TEST_VERIFY or VERIFY_FINISH)
  - `gh pr create`                           -> only when Phase = FINISH or
    VERIFY_FINISH (fast lane, ADR-0010) and Quality Gate is PASS /
    ACCEPTED_SOFT_FAIL

Pipeline artifacts (.board/, docs/, .claude/, templates/, PLAN.md, root *.md)
are writable in every phase — the pipeline itself produces them.

State source: parses `.board/sprint-state.md` directly (the `- **Field**:`
format defined in state-management.md). There is deliberately NO separate
sprint-state.json — a dual file would drift from the markdown (ADR-0008).

Fail-open: if sprint-state.md is missing or unparseable, the guard allows the
call and prints a warning to stderr. It must never brick a project.

Escape hatch (both logged to stderr):
  - env  CAPIVA_PHASE_GUARD=off  — must be set in Claude Code's own environment
    at launch (the hook is spawned by Claude Code, so per-command env vars in a
    shell tool call cannot reach it)
  - file .state/phase-guard-off  — create to disable mid-session, delete to
    re-enable; gitignored, explicit, auditable

Keep the field parser in sync with context-persistence.py (same format).
"""

import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
SPRINT_STATE = PROJECT_ROOT / ".board" / "sprint-state.md"

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}

# Paths writable in ANY phase — pipeline artifacts plus harness/CI tooling.
ALWAYS_ALLOWED_DIRS = (".board", ".claude", ".state", ".github", "docs", "scripts", "templates", "reports")
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
# Fast lane (ADR-0010): VERIFY_FINISH combines TEST_VERIFY + FINISH.
TEST_WRITE_PHASES = {"TEST_VERIFY", "VERIFY_FINISH"}
PR_PHASES = {"FINISH", "VERIFY_FINISH"}


def _parse_field(content: str, field: str) -> str:
    m = re.search(rf"^- \*\*{re.escape(field)}\*\*:\s*(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _read_state():
    """Returns (phase, quality_gate, task_id) or None if unavailable (fail-open)."""
    try:
        content = SPRINT_STATE.read_text(encoding="utf-8")
    except OSError:
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


def _check_file_write(tool_input: dict, phase: str):
    raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw:
        _allow()
    path = Path(raw) if os.path.isabs(raw) else PROJECT_ROOT / raw
    if _is_always_allowed(path):
        _allow()
    if phase == "IMPLEMENT":
        _allow()
    if phase in TEST_WRITE_PHASES and TEST_PATH_RE.search(str(path)):
        _allow()
    _deny(
        f"Phase guard: source file writes require Phase = IMPLEMENT "
        f"(tests also allowed in TEST_VERIFY / VERIFY_FINISH). Current phase: {phase or 'UNKNOWN'}. "
        f"Run /sprint to advance the pipeline, or edit pipeline artifacts "
        f"(docs/, .board/, PLAN.md) instead. File: {path}"
    )


def _check_shell(tool_input: dict, phase: str, gate: str):
    command = tool_input.get("command", "")
    if re.search(r"\bgh\s+pr\s+create\b", command):
        if phase not in PR_PHASES:
            _deny(
                f"Phase guard: `gh pr create` requires Phase = FINISH "
                f"(or VERIFY_FINISH in the fast lane). "
                f"Current phase: {phase or 'UNKNOWN'}. Complete /test-verify and "
                f"quality review first, then /finish creates the PR."
            )
        if gate not in PASSING_GATES:
            _deny(
                f"Phase guard: `gh pr create` requires Quality Gate = PASS or "
                f"ACCEPTED_SOFT_FAIL. Current: {gate or '--'}. Run /test-verify "
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
