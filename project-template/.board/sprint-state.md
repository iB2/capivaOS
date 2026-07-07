# Sprint State

> **Source of truth for pipeline execution.** Every skill reads this FIRST.
> Updated by skills at every phase transition. On session restart, read this to resume.

## Current Task

- **Task ID**: (none)
- **Task Title**: (none)
- **Priority**: --
- **Lane**: full
- **Phase**: IDLE
- **Phase Started**: --
- **Spec Approved**: No
- **Plan Approved**: No
- **Quality Gate**: --
- **Branch**: --

## Valid Transitions

```
Full lane: IDLE → TRIAGE → GRILL_SPEC → PLAN → IMPLEMENT → TEST_VERIFY → FINISH → IDLE
Fast lane: IDLE → TRIAGE → SPEC_PLAN → IMPLEMENT → VERIFY_FINISH → IDLE   (ADR-0010)
ANY  → BLOCKED (escalation) → resume previous phase
ANY  → IDLE (abort)
SPEC_PLAN → GRILL_SPEC / VERIFY_FINISH → TEST_VERIFY (fast-lane abort/escalation, Lane resets to full)
```

## Phase History

| Timestamp | Task | From | To | Gate | Notes |
|-----------|------|------|----|------|-------|

## Board Lock

- **Status**: UNLOCKED
- **Holder**: (none)
- **Since**: --

## Sprint Metrics

- Tasks completed this sprint: 0
- PRs created: 0
- Average coverage: --
- Average quality gate status: --
- Total time: --

## Artifacts Registry

| Phase | Artifact | Path | Status |
|-------|----------|------|--------|
| GRILL_SPEC | Spec document | -- | -- |
| GRILL_SPEC | CONTEXT.md updates | -- | -- |
| PLAN | PLAN.md | -- | -- |
| IMPLEMENT | Feature branch | -- | -- |
| TEST_VERIFY | Quality report | -- | -- |
| FINISH | Pull request | -- | -- |
