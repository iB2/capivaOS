# Troubleshooting & Anti-Patterns

Operational reference moved out of the always-loaded CLAUDE.md (ADR-0011).
Read on demand — when something fails, or before starting a phase you haven't
run recently.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Phase guard failure | Wrong phase in `sprint-state.md` | Read sprint-state, complete the current phase before invoking the next skill |
| Board locked | Stale `.board/board.lock` file | Check lock timestamp — if older than 60 seconds, delete the lock file |
| Quality gate HARD FAIL | Coverage below minimum threshold | Add missing tests to reach the gate; do not override thresholds |
| Context budget exceeded | Too many file reads or 2+ auto-compactions | Run `/compact` with focus or `/capiva:handover` at next phase boundary |
| Subagent fails 3x | Three-strike rule triggered | Mark the micro-task BLOCKED, report to human with failure details |
| Spec not found after TRIAGE | Task on board has no spec file yet | `/capiva:grill-spec` will create one — this is normal for new tasks |
| Tests fail in IMPLEMENT | RED-GREEN cycle incomplete | Fix failing tests before transitioning to TEST_VERIFY |
| Handover doc missing on resume | Previous session crashed before `/capiva:handover` | Read sprint-state for current phase, reconstruct context from artifacts on disk |
| acs.json fails lint | Hand-edited `id`/`text`, bad status value, or duplicate ids | Regenerate through /capiva:grill-spec (scope change) or fix status to `pending`/`pass`/`fail` |
| Fast-lane task grows scope | New file/schema/arch need discovered mid-lane | Mandatory abort to full lane (SPEC_PLAN → GRILL_SPEC or VERIFY_FINISH → TEST_VERIFY), logged in Phase History |
| `/capiva:sprint` → "no matching command" (esp. in the VS Code extension) | Claude Code surfaces plugin skills under their **unqualified** name; the `capiva:` prefix only appears when a name collides with a built-in | Type **`/sprint`** (unqualified). Only `init` needs the prefix — `/capiva:init` — because it collides with the built-in `/init`. If NO capiva commands appear at all, the plugin isn't loaded: check `claude plugin list` (enabled + right scope) and reload the window |

## Sprint Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Skip phases | Artifacts won't exist for downstream phases | Follow the sequence — IDLE through FINISH (or the fast lane's guarded path) |
| Run skills out of sequence | Phase guards will reject, but don't rely on them as your workflow | Check sprint-state before invoking any skill |
| Ignore phase guards | They exist to prevent cascade failures | Fix the root cause (complete current phase first) |
| Continue after handover trigger | Context degradation produces buggy output | Run `/capiva:handover`, stop, resume next session |

## Artifact Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Placeholder content ("TBD", "TODO") | Blocks downstream phases, violates artifact standards | Write the real content or mark the task BLOCKED |
| Vague AC ("system should work") | Untestable, unverifiable, will fail quality gates | Specific, measurable criteria with concrete values |
| Missing traceability | AC appears in spec but not in acs.json/plan/tests/report | Every AC threads through the full artifact chain |
| Single-sentence spec sections | Fails anti-slop rules in `artifact-standards.md` | Expand with context, constraints, and examples |

## Context Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Read entire files when you need 10 lines | Burns context budget, triggers early compaction | Use `offset`/`limit` on Read, delegate exploration to subagents |
| Skip `/capiva:handover` when quality degrades | Quality degrades silently in long sessions | Follow context budget rules in Law 6; hooks auto-save state but `/capiva:handover` is the deliberate checkpoint |
| Ignore quality degradation signals | Vague output, repeated questions, forgotten decisions | `/capiva:handover` at next phase boundary, resume fresh |
| Load all rules/roles into main context | Wastes tokens on reference material | Load into subagent prompts where they're needed |

## Code Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Implement before writing tests | Violates TDD (RED-GREEN-REFACTOR) | Write failing test first, then implement to green |
| Swallow errors silently | Hides bugs, fails static analysis | Catch specific errors, log or rethrow |
| Ignore blueprint conventions | Breaks consistency, fails QA review | Follow the active blueprint's reference.md patterns |
| Use wrong architectural layer | Violates dependency direction | Check blueprint §architecture for correct placement |
