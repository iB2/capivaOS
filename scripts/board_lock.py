#!/usr/bin/env python3
"""
board_lock.py — mechanical board lock (PRD-003 / supersedes ADR-0003's prose).

The board lock stops two writers from corrupting `.board/tasks.md` /
`sprint-state.md`. ADR-0003 left it as a prompt ritual the model was trusted
to follow (check-then-create over separate tool calls, no atomicity, and two
contradictory staleness numbers). This makes it code:

  - acquire : atomic O_EXCL create — two racers cannot both win. Writes the
              holder token to BOTH .board/board.lock and .state/lock-holder so
              phase_guard can tell "this session holds it" from "someone else
              does". A fresh foreign lock => exit 1 (held). A stale one is
              stolen. Prints the holder token on success.
  - release : delete the lock iff we hold it (token matches .state/lock-holder).
  - check   : exit 0 if free/stale, 1 if held by another; prints status.

ONE staleness number, here, quoted by the rules docs — never restated.
Zero dependencies; never raises in a way that bricks a caller.
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
BOARD_LOCK = PROJECT_ROOT / ".board" / "board.lock"
LOCK_HOLDER = PROJECT_ROOT / ".state" / "lock-holder"

# The single source of truth for lock staleness. phase_guard.py keeps a copy
# with a "keep in sync" note; lint check 18 asserts they match.
STALE_SECONDS = 120


def _token() -> str:
    return f"{os.getpid()}-{time.time():.3f}"


def _read_lock():
    """Return (holder, epoch) or None if absent/unparseable."""
    try:
        holder, epoch = None, None
        for line in BOARD_LOCK.read_text(encoding="utf-8").splitlines():
            if line.startswith("holder="):
                holder = line[len("holder="):].strip()
            elif line.startswith("epoch="):
                epoch = float(line[len("epoch="):].strip())
        if holder is None or epoch is None:
            return None
        return holder, epoch
    except (OSError, ValueError):
        return None


def _is_stale(epoch: float) -> bool:
    return (time.time() - epoch) > STALE_SECONDS


def acquire() -> int:
    BOARD_LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK_HOLDER.parent.mkdir(parents=True, exist_ok=True)
    token = _token()
    payload = f"holder={token}\nepoch={time.time():.3f}\n"
    try:
        fd = os.open(str(BOARD_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
    except FileExistsError:
        cur = _read_lock()
        if cur and not _is_stale(cur[1]):
            print(f"board_lock: held by {cur[0]} (fresh) — not acquiring", file=sys.stderr)
            return 1
        # stale (or unparseable) — steal it
        BOARD_LOCK.write_text(payload, encoding="utf-8")
    LOCK_HOLDER.write_text(token, encoding="utf-8")
    print(token)
    return 0


def release() -> int:
    cur = _read_lock()
    mine = LOCK_HOLDER.read_text(encoding="utf-8").strip() if LOCK_HOLDER.is_file() else ""
    if cur and mine and cur[0] == mine:
        try:
            BOARD_LOCK.unlink()
        except OSError:
            pass
    try:
        if LOCK_HOLDER.is_file():
            LOCK_HOLDER.unlink()
    except OSError:
        pass
    return 0


def check() -> int:
    cur = _read_lock()
    if cur is None:
        print("free")
        return 0
    if _is_stale(cur[1]):
        print(f"stale (holder {cur[0]})")
        return 0
    print(f"held by {cur[0]}")
    return 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    return {"acquire": acquire, "release": release, "check": check}.get(cmd, check)()


if __name__ == "__main__":
    sys.exit(main())
