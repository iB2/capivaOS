#!/usr/bin/env python3
"""
session_context.py — SessionStart injection of the harness methodology (ADR-0013).

Plugins cannot ship CLAUDE.md or always-loaded rules; this hook is the
replacement. On startup/clear it injects the laws (rules/laws.md) plus the
live sprint state; on compact it injects only the credo reminder (full state
is restored separately by context-persistence.py).

Inert outside harness projects: if the project has no .board/sprint-state.md,
it prints nothing and exits 0 — a user-scope install must add zero noise to
unrelated repos.

Always exits 0. Fail-open everywhere (missing laws, bad JSON, no plugin.json).
"""

import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
# In plugin installs CLAUDE_PLUGIN_ROOT points at the cached plugin; in
# dev/copy mode fall back to this script's parent's parent (the repo root).
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)

SPRINT_STATE = PROJECT_ROOT / ".board" / "sprint-state.md"
SCHEMA_STAMP = PROJECT_ROOT / ".board" / "harness-schema-version"

CREDO = (
    "capivaOS credo: 1) If it's not on the board, it doesn't get built. "
    "2) If there's no approved spec, there's no code. "
    "3) If there's no test, there's no implementation."
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _current_task_block(state: str) -> str:
    m = re.search(r"## Current Task\n(.*?)(?=\n## )", state, re.DOTALL)
    return m.group(1).strip() if m else state[:800]


def _plugin_version() -> str:
    try:
        manifest = json.loads(_read(PLUGIN_ROOT / ".claude-plugin" / "plugin.json"))
        return str(manifest.get("version", ""))
    except (json.JSONDecodeError, TypeError):
        return ""


def _skew_nudge() -> str:
    stamp = _read(SCHEMA_STAMP).strip()
    version = _plugin_version()
    if stamp and version and stamp != version:
        return (
            f"\n⚠️ Harness schema skew: this project was scaffolded by capivaOS {stamp}, "
            f"but the installed plugin is {version}. Run /capiva:update-project to migrate "
            f"the scaffolded files before starting pipeline work."
        )
    return ""


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    source = str(payload.get("source", "startup"))

    state = _read(SPRINT_STATE)
    if not state:
        sys.exit(0)  # not a harness project — stay silent

    parts = []
    if source == "compact":
        parts.append(f"[capivaOS credo reminder after compaction] {CREDO}")
    else:
        laws = _read(PLUGIN_ROOT / "rules" / "laws.md")
        if laws:
            parts.append("# capivaOS — Active Harness Rules (injected by plugin)\n\n" + laws.strip())
        else:
            parts.append(f"[capivaOS] {CREDO} (laws.md unavailable — read "
                         f"rules in the capiva plugin directory before pipeline work)")

    parts.append("\n## Current Sprint State (live from .board/sprint-state.md)\n\n"
                 + _current_task_block(state)
                 + "\n\nRun /capiva:sprint to resume or start pipeline work. "
                   "To update the harness itself, use /capiva:update.")

    nudge = _skew_nudge()
    if nudge:
        parts.append(nudge)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(parts),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
