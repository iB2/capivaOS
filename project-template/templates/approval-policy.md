# Approval Policy — human-authored law (ADR-0014)

> THIS FILE MUST BE CREATED AND EDITED BY A HUMAN. The phase guard denies agent
> writes to `.board/approval-policy.md` in every phase — agents propose changes
> only as escalations in `.board/approvals.md`. Copy this template to
> `.board/approval-policy.md` yourself and edit the fields.
>
> The never-list is NOT configurable here or anywhere: merge decisions, P0/P1
> gates, approval of human-less specs, and anything this file doesn't
> explicitly cover always escalate. Safe default below = everything escalates.

## Delegation grants

- **Auto-Approve Fast-Lane Spec+Plan**: no
  <!-- yes = fast-lane-qualifying P3 tasks' combined spec+plan gate may be
       cleared by the gate-judge with zero anomalies. Set to "yes, P2 and P3"
       to include P2. Interlocutor note (ADR-0014 amendment): your board ACs
       ARE the human interlocutor for these specs — the judge verifies every
       spec AC traces to your task's ACs and escalates anything untraceable,
       so write board ACs you would stand behind. -->
- **Auto-Approve Quality Gate**: no
  <!-- yes = quality gates where ALL mechanical gates PASS, every acs.json
       status is pass with e2e evidence, and the gate-judge finds zero
       anomalies may be cleared without waiting for you. -->
- **Max Auto-Approvals Per Run**: 0
  <!-- circuit breaker: after N delegated clears in one auto run, everything
       further escalates regardless of grants. -->

## Notes

- Agent writes to this file are denied by phase_guard.py in every phase (hook-enforced). Human edits are recorded by the run-log's deny/allow events like any other board activity.
- Absent, unparseable, or partially filled = the missing parts escalate.
