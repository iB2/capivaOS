#!/usr/bin/env python3
"""
context-persistence.py — Automated session state persistence for Boss sessions.

Entry points:
  precompact  — save current state before compaction fires
  restore     — return saved state as additionalContext after compaction
  stop        — save final state on session end (skip if /handover exists)

Always exits 0, never blocks. Follows session-start.py conventions.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path.cwd()
STATE_DIR = PROJECT_ROOT / ".state"
BOARD_DIR = PROJECT_ROOT / ".board"
HANDOVER_DIR = PROJECT_ROOT / "docs" / "handover"
SESSION_STATE_FILE = STATE_DIR / "boss-session.md"


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
        content = tasks.read_text(encoding="utf-8")
        in_progress = content.count("**Status**: In Progress")
        open_tasks = content.count("- [ ]")
        done_tasks = content.count("- [x]")
        return f"Board: {open_tasks} open, {in_progress} in progress, {done_tasks} done"
    except Exception:
        return "Board: read error"


def _sprint_state_summary() -> str:
    state_file = BOARD_DIR / "sprint-state.md"
    if not state_file.is_file():
        return "Sprint state: IDLE (no sprint-state.md)"
    try:
        content = state_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        summary_parts = []
        for line in lines:
            low = line.lower().strip()
            if low.startswith("| phase") or low.startswith("| task") or low.startswith("| sprint"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    summary_parts.append(f"{parts[0]}: {parts[1]}")
        return "Sprint state: " + (" | ".join(summary_parts[:5]) if summary_parts else "see sprint-state.md")
    except Exception:
        return "Sprint state: read error"


def _gather_state() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sections = [f"# Boss Session State\n\n> Auto-saved: {now}\n> Source: context-persistence.py precompact\n"]

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

    cycle_state = STATE_DIR / "cycle-state.json"
    if cycle_state.is_file():
        try:
            cs = json.loads(cycle_state.read_text(encoding="utf-8"))
            sections.append(f"\n## Cycle State\n")
            sections.append(f"- Cycle: {cs.get('cycle_number', '?')}")
            sections.append(f"- Health: {cs.get('health', '?')}")
            sections.append(f"- Last result: {cs.get('last_result', '?')}")
        except Exception:
            pass

    state_md = STATE_DIR / "state.md"
    if state_md.is_file():
        try:
            content = state_md.read_text(encoding="utf-8")[:500]
            sections.append(f"\n## Last Cycle Narrative\n{content}")
        except Exception:
            pass

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
