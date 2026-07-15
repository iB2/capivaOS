# Review Packet — [DATE] (RFN-007)

> Emitted by `/capiva:auto` (and `/capiva:refine` exit) when the board clears. The **batched-HITL
> backstop**: review everything once, here. This is a **review aid, not a gate** — it approves
> nothing; you still read the PRs and the merge decision is yours (never-list). Reconciled against
> `.state/run-log.jsonl` — the log is ground truth; this narrative is checked against it, never the
> reverse. `validate_review_packet.py` asserts the sections below and that every Done row has a PR.

## Run summary
- **Stop reason**: [board-empty | task-cap | phase-budget | provider-limit | escalation-pile-up]
- **Tasks completed**: [N] | **Parked/escalated**: [M] | **Run-log**: `.state/run-log.jsonl`

## Per-task
| Task | PR | Spec | AC | Quality | Verdict | Deviations | Parks | Status |
|------|----|------|----|---------|---------|------------|-------|--------|
| TASK-ID | #NN | docs/specs/TASK-ID-spec.md | k/k | docs/reports/TASK-ID-quality.md | CLEAR/ESCALATE | [notes or none] | [none/parked] | Done |

## Escalations awaiting you (`.board/approvals.md`)
- [ESC-N — TASK-ID — one-line exception] (or "none")

## Decisions logged this run (`.board/decisions.md`) + read-back
- [DEC-N entries written; read-back rate from validate_decisions.py] (or "none")

## What to worry about
- [Anything the machine flagged, any deviation, any judge ESCALATE the human must resolve]
