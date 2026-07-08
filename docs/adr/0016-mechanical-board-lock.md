# ADR-0016: Mechanical Board Lock — Code, Not a Prompt Ritual

**Status**: Accepted (2026-07-09). **Supersedes** the "no lock code by design"
decision of [ADR-0003](0003-board-lock-file-based.md).
**Context**: a 2026-07 external code review (resilience/containment lens) and
the shipped-code reality of `/capiva:auto`.

## Context

ADR-0003 chose a file-based board lock and deliberately left it as a *prompt
ritual*: the model reads `board.lock`, decides staleness from a
model-generated timestamp string, and creates/deletes the file over separate
tool calls. ADR-0003 named the race ("two agents could check simultaneously
and both proceed") and judged it acceptable given Claude Code's serialized
single-agent execution.

Two things changed that judgment:

1. **Auto mode ships.** `/capiva:auto` runs the backlog with phase-isolated
   subagents. Even with the single-writer-orchestrator rule, coordination that
   depends on the model faithfully running a multi-step ritual is the class of
   guarantee this harness otherwise refuses to make. The review's Principle 5:
   *state coordination is infrastructure, not model behavior.*
2. **The ritual contradicted itself.** The rules docs carried TWO staleness
   numbers (60s in one place, 30s in another) — a ritual so under-specified it
   couldn't be followed deterministically even by a compliant model.

The deeper point matches the whole harness thesis: a lock whose only
enforcement is the model it constrains is not a lock. ADR-0003's own framing
("prompted-rule-is-not-a-guardrail") is exactly what ADR-0008 rejected for
phase state — and left un-migrated for the board.

## Options Considered

- **A — Keep the prose ritual (ADR-0003 status quo).** Rejected: the
  contradiction above, and it fails the harness's own bar under auto mode.
- **B — External lock service (Redis/DB).** Rejected for the same reason
  ADR-0003 rejected it: absurd infrastructure for a single markdown board;
  adds a network dependency the zero-network posture forbids.
- **C — File lock in hook code, guard-enforced (CHOSEN).** Atomic `O_EXCL`
  create in `scripts/board_lock.py`; `time.time()` staleness with ONE window;
  the PreToolUse guard denies board writes held by another live holder.

## Decision

Option C. `scripts/board_lock.py` provides `acquire` (atomic `O_EXCL` — two
racers cannot both win; a stale lock is stolen), `release`, and `check`, with a
single `STALE_SECONDS` window (the only staleness number; docs quote it, never
restate). On `acquire` it records the holder token in `.state/lock-holder`;
`phase_guard.py` reads it and denies writes to `.board/tasks.md` /
`sprint-state.md` held by a *different* live holder (a new `board-lock`
ENFORCED_SURFACE). The rules docs stop describing the ritual and call the code.

## Consequences

- The race ADR-0003 conceded is closed by `O_EXCL` atomicity.
- The lock is now a real guarantee under auto mode, not trust.
- **Backward-compatible by construction**: the guard enforces only when BOTH
  `board.lock` and `.state/lock-holder` exist (i.e. `board_lock.py` is in use).
  Absent either, it defers — an adopter mid-migration on the old prose ritual
  is never bricked.
- Honest residual: the staleness window lives in two files (`board_lock.py`
  source of truth + a `phase_guard.py` copy for the enforcement side). Lint
  check 18 asserts they match, so the drift class that produced the original
  60-vs-30 contradiction cannot recur.
- Read is still lock-free; only writes coordinate.
- Revisit when: Claude Code exposes a native cross-subagent coordination
  primitive — this collapses onto it, as ADR-0012/0013 did for agents/plugins.
