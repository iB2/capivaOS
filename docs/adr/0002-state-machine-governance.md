# ADR-0002: State Machine Governance Over Trust-Based Enforcement

## Status

Accepted

## Context

The pipeline has 6 phases that must execute in order. We need a mechanism to ensure this ordering is followed — even when the agent is under context pressure, the human asks to "just skip ahead," or a session crashes mid-pipeline.

### Options Considered

**Option A: Convention-based (trust the agent)**
- Each skill's prompt says "check that the previous phase is done before proceeding"
- Pro: Zero infrastructure — just prompt engineering
- Con: Language models optimize for helpfulness. When the human says "just implement it," the agent will comply — skipping the spec and plan phases
- Con: No recovery mechanism after a crash — the agent has to infer where it was from conversation context, which may have compacted

**Option B: Checklist-based (human verifies)**
- A checklist in CLAUDE.md that the human and agent work through together
- Pro: Human stays in control
- Con: Relies on human discipline — which is the same problem we're solving for the agent
- Con: No persistence across sessions

**Option C: State machine with persistent state file**
- `.board/sprint-state.md` holds the current phase. Every skill reads it before executing and updates it after completing. Phase guards mechanically refuse to execute if the phase doesn't match.
- Pro: Binary enforcement — skill either runs or doesn't, no judgment required
- Pro: Survives crashes — read the file, know exactly where you are
- Pro: Auditable — Phase History table shows every transition with timestamps
- Pro: Recoverable — fresh agent reads sprint-state and resumes from the current phase
- Con: Additional file I/O on every skill invocation (~2K tokens overhead)

## Decision

**State machine with persistent state file (Option C).**

The state machine is defined as:
```
IDLE → TRIAGE → GRILL_SPEC → PLAN → IMPLEMENT → TEST_VERIFY → FINISH → IDLE
```

With special transitions:
- ANY → BLOCKED (escalation)
- BLOCKED → (return to blocking phase after human resolution)
- ANY → IDLE (human abort)

Every skill implements a phase guard: read sprint-state, verify phase matches, refuse if mismatch. This is template code — identical structure in every skill, varying only in the required phase name.

## Consequences

- Agents cannot skip phases, even if explicitly asked to by a human — the skill will refuse and explain why
- Session recovery is deterministic: read sprint-state, resume from current phase
- Every phase transition is logged in the Phase History table — full audit trail
- The overhead is ~2K tokens per skill invocation (sprint-state read + update) — acceptable given the 200K budget
- Adding a new phase requires updating the state transition diagram, guard matrix, and every skill that references adjacent phases — this friction is intentional (see ADR-0001)
