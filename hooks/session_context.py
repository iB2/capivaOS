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
COMPACTION_COUNT = PROJECT_ROOT / ".state" / "compaction-count"
GUARD_HEARTBEAT = PROJECT_ROOT / ".state" / "guard-heartbeat"
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


def _loop_resume_block(state: str) -> str:
    """[AUTO_LOOP_RESUME] injection when a loop is active (ADR-0014).

    The loop driver persists its counters as sprint-state fields; after a
    compaction this block restores the loop's position so it continues instead
    of silently dying with the context."""
    if not re.search(r"^- \*\*Loop Active\*\*:\s*yes\s*$", state, re.MULTILINE | re.IGNORECASE):
        return ""
    def field(name, default="?"):
        m = re.search(rf"^- \*\*{name}\*\*:\s*(.+)$", state, re.MULTILINE)
        return m.group(1).strip() if m else default
    done = field("Loop Tasks Done", "0")
    cap = field("Loop Task Cap")
    return (
        f"\n[AUTO_LOOP_RESUME] An auto-mode loop was active when this context "
        f"compacted. Progress: {done}/{cap} tasks; budget note: {field('Loop Phase Budget', 'see driver defaults')}. "
        f"Re-read .board/sprint-state.md and .board/approvals.md, then CONTINUE the "
        f"loop from the current phase per the auto-mode contract (never re-run "
        f"completed phases; artifacts on disk are the source of truth). "
        f"Stop reason so far: {field('Loop Stop Reason', '--')}."
    )


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
        try:
            count = int(_read(COMPACTION_COUNT).strip() or 0)
        except ValueError:
            count = 0
        parts.append(f"[capivaOS credo reminder after compaction] {CREDO}")
        parts.append(
            f"[COMPACTION COUNT] Auto-compactions this session: {count} "
            f"(hook-maintained). Per Law 6 / sprint Step 4a: 2+ means MANDATORY "
            f"handover at the next phase boundary; 1 before a heavy phase "
            f"(IMPLEMENT, TEST_VERIFY) also means handover.")
        resume = _loop_resume_block(state)
        if resume:
            parts.append(resume)
    else:
        # fresh or cleared session: the compaction counter starts over
        # (makes "/clear resets the compaction counter" mechanically true)
        try:
            if COMPACTION_COUNT.is_file():
                COMPACTION_COUNT.write_text("0", encoding="utf-8")
        except OSError:
            pass
        laws = _read(PLUGIN_ROOT / "rules" / "laws.md")
        if laws:
            parts.append("# capivaOS — Active Harness Rules (injected by plugin)\n\n" + laws.strip())
        else:
            parts.append(f"[capivaOS] {CREDO} (laws.md unavailable — read "
                         f"rules in the capiva plugin directory before pipeline work)")

    # Guard liveness surfacing (PRD-001): if a task is active but the guard
    # has left no heartbeat, the enforcement layer is probably not firing
    # (e.g. the POSIX dispatch died). Silence must never read as healthy.
    phase_line = re.search(r"^- \*\*Phase\*\*:\s*(.+)$", state, re.MULTILINE)
    active = bool(phase_line) and phase_line.group(1).strip().upper() not in ("IDLE", "--", "")
    hb = _read(GUARD_HEARTBEAT).strip()
    if active and not hb:
        parts.append(
            "\n\u26a0\ufe0f [GUARD LIVENESS] A pipeline task is active but the phase "
            "guard has left NO heartbeat (.state/guard-heartbeat missing). The "
            "enforcement layer may not be firing \u2014 on POSIX this happens when the "
            "hook dispatcher is not executable. Do NOT trust phase enforcement or "
            "start /capiva:auto until a write refreshes the heartbeat.")
    elif hb:
        parts.append(f"\n[GUARD LIVENESS] Phase guard last fired: {hb}")

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
