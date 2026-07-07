#!/usr/bin/env python3
"""
context-persistence.py — Automated session state persistence for the harness.

Entry points:
  precompact  — save current state before compaction fires
  restore     — return saved state as additionalContext after compaction
  stop        — save final state on session end (skip if /handover exists)

Always exits 0, never blocks the session.

Invoked via hooks/run-hook.cmd (plugin mode) or directly (dev mode). The
dispatcher resolves the Python interpreter per platform and exits 0 when
none is found — this script must also never block (always exits 0).
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
STATE_DIR = PROJECT_ROOT / ".state"
BOARD_DIR = PROJECT_ROOT / ".board"
HANDOVER_DIR = PROJECT_ROOT / "docs" / "handover"
SESSION_STATE_FILE = STATE_DIR / "session-state.md"

# Fields parsed from the "Current Task" section of sprint-state.md
SPRINT_FIELDS = ("Task ID", "Phase", "Spec Approved", "Plan Approved", "Quality Gate", "Branch")


def _run(cmd: list[str], fallback: str = "") -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5, cwd=str(PROJECT_ROOT))
        return r.stdout.strip() if r.returncode == 0 else fallback
    except Exception:
        return fallback


def _board_snapshot() -> str:
    tasks = BOARD_DIR / "tasks.md"
    if not tasks.is_file():
        return "Board: not found"
    try:
        lines = tasks.read_text(encoding="utf-8").splitlines()
        in_progress = sum(1 for l in lines if l.strip().startswith("- **Status**: In Progress"))
        open_tasks = sum(1 for l in lines if l.lstrip().startswith("- [ ]"))
        done_tasks = sum(1 for l in lines if l.lstrip().startswith("- [x]"))
        return f"Board: {open_tasks} open, {in_progress} in progress, {done_tasks} done"
    except Exception:
        return "Board: read error"


def _sprint_state_summary() -> str:
    """Parse `- **Field**: value` bullets from sprint-state.md (state-management.md field format)."""
    state_file = BOARD_DIR / "sprint-state.md"
    if not state_file.is_file():
        return "Sprint state: IDLE (no sprint-state.md)"
    try:
        content = state_file.read_text(encoding="utf-8")
        summary_parts = []
        for field in SPRINT_FIELDS:
            m = re.search(rf"^- \*\*{re.escape(field)}\*\*:\s*(.+)$", content, re.MULTILINE)
            if m:
                summary_parts.append(f"{field}: {m.group(1).strip()}")
        return "Sprint state: " + (" | ".join(summary_parts) if summary_parts else "see sprint-state.md")
    except Exception:
        return "Sprint state: read error"


def _gather_state() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sections = [f"# Session State\n\n> Auto-saved: {now}\n> Source: context-persistence.py\n"]

    sections.append("## Sprint State\n")
    sections.append(_sprint_state_summary())

    sections.append("\n## Board Snapshot\n")
    sections.append(_board_snapshot())

    sections.append("\n## Git State\n")
    sections.append("```")
    sections.append(_run(["git", "branch", "--show-current"], "unknown branch"))
    sections.append(_run(["git", "status", "--short"], "no changes"))
    sections.append("```")

    diff_stat = _run(["git", "diff", "--stat"], "")
    if diff_stat:
        sections.append("\n### Diff\n```")
        sections.append(diff_stat[:1000])
        sections.append("```")

    sections.append("\n## Recent Commits\n```")
    sections.append(_run(["git", "log", "--oneline", "-5"], "no commits"))
    sections.append("```")

    return "\n".join(sections)


def _has_manual_handover() -> bool:
    if not HANDOVER_DIR.is_dir():
        return False
    return any(f.suffix == ".md" for f in HANDOVER_DIR.iterdir())


def precompact():
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        content = _gather_state()
        SESSION_STATE_FILE.write_text(content, encoding="utf-8")
    except Exception:
        pass


def restore():
    try:
        if SESSION_STATE_FILE.is_file():
            content = SESSION_STATE_FILE.read_text(encoding="utf-8")
            SESSION_STATE_FILE.unlink()
            print(json.dumps({"additionalContext": content}))
            return
        for hf in sorted(HANDOVER_DIR.glob("*-handover.md"), reverse=True) if HANDOVER_DIR.is_dir() else []:
            content = hf.read_text(encoding="utf-8")
            print(json.dumps({"additionalContext": f"# Resuming from handover\n\n{content}"}))
            return
    except Exception:
        pass


def stop():
    try:
        if _has_manual_handover():
            return
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        content = _gather_state()
        SESSION_STATE_FILE.write_text(content, encoding="utf-8")
    except Exception:
        pass


def main():
    # Inert outside harness projects (ADR-0013): a user-scope plugin install
    # must never write .state/ into repos that never ran /capiva:init.
    if not BOARD_DIR.is_dir():
        sys.exit(0)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "precompact":
        precompact()
    elif cmd == "restore":
        restore()
    elif cmd == "stop":
        stop()
    sys.exit(0)


if __name__ == "__main__":
    main()
