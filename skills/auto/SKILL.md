---
name: auto
description: Auto mode — work a pre-approved backlog unattended under the ADR-0014 contract. Opt-in per run; fresh-context phases; gates routed via policy + gate-judge with escalation; hard budgets; parks cleanly at phase boundaries; morning report. Use when the user says "run the backlog", "work overnight", or invokes auto mode.
---

# Auto — The Loop Driver (ADR-0014)

One invocation works the backlog until: board empty, budget cap, or an
escalation pile-up. Attended `/capiva:sprint` is unchanged and remains the
default; this mode is opt-in **per run** — never a standing repo state.

## Entry Gate (MANDATORY — refuse politely, never improvise past it)

1. **Init check**: same as /capiva:sprint Step 0 (docs, blueprint, config).
1b. **Guard liveness** (MANDATORY, PRD-001): the phase guard must be proven
   alive before accepting autonomy. Check `.state/guard-heartbeat` is fresh
   (updated this session). If absent, run a probe: attempt an out-of-phase
   source write that MUST be denied, then confirm the heartbeat updated. If
   the guard cannot be shown alive (no heartbeat, probe not denied — e.g. a
   dead POSIX dispatcher), REFUSE to start. A guard that might be dead is a
   guard that is not there; autonomy on top of it is unacceptable.
2. **Branch protection re-check** (ADR-0014 prerequisite): verify the default
   branch requires PRs. Unprotected → REFUSE with the init Step 5b explanation;
   the human may override with an explicit "run unprotected" — record the
   override in Phase History.
3. **Task eligibility**: auto only picks tasks that are (a) full-lane with an
   ALREADY-APPROVED spec (`Spec Approved` recorded from an attended session, or
   spec + acs.json exist with the board noting human approval), or (b)
   fast-lane qualifiers (ADR-0010 predicate). Everything else is SKIPPED and
   listed in the report as "awaiting attended grill". Never grill in auto mode.
4. **Budgets** (no uncapped runs — the option does not exist):
   - `Loop Task Cap`: from invocation or `- **Auto Task Cap**:` in
     harness-config; default **3**
   - `Loop Phase Budget`: hard cap on total phase executions this run; default
     **15** (the countable proxy for the token budget — isolation bounds each
     phase, so phases×bound ≈ tokens; additionally, ANY provider limit signal
     = immediate park)
5. **Re-entry safety**: if sprint-state already has `Loop Active: yes`, RESUME
   that run's counters (never reset, never double-start).

Write the loop fields to sprint-state: `Loop Active: yes`, caps, `Loop Tasks
Done: 0`, `Loop Stop Reason: --`. (These power the AUTO_LOOP_RESUME injection
after any compaction.)

## The Loop

```
WHILE tasks-done < cap AND phases-used < budget:
  task = next eligible per dependency-aware triage (sprint Step 2 order; cycles = board defect, stop + report)
  none eligible -> stop (reason: board empty / all awaiting grill or approvals)
  run phases via Phase Isolation (ADR-0014 isolation-first): phase-runner per phase,
    orchestrator validates artifacts + transitions state (single writer)
  AT EACH GATE (never the merge gate):
    policy explicitly covers it?         -> CLEAR, log `gate-delegated` + basis
    else gate-judge (ADR-0014) verdict (briefing MUST include the original
      board task text — the judge checks spec-AC-to-board-AC traceability):
      CLEAR (zero anomalies, in bounds)  -> log `gate-delegated` + basis
      ESCALATE -> append ESC entry to .board/approvals.md,
                  log `gate-escalated`, PARK THIS TASK, continue loop
  three-strike on any phase -> BLOCKED per protocol, park task, continue loop
  task reaches FINISH -> create PR (guard allows: Phase=FINISH+PASS),
    board -> Done with PR number; MERGE IS NEVER TOUCHED
  tasks-done += 1
PARK at the phase boundary when any cap/limit hits (standard /capiva:handover doc)
```

Parking is always clean: mid-phase budget death abandons that phase's runner
(branch stays at its last green commit) and the task re-enters at that phase.

## Circuit breakers
- `Max Auto-Approvals Per Run` from the policy file: after N delegated CLEARs,
  everything further escalates
- 3 escalations on a single task = that task parks to attended (stop retrying)
- Judge recognizes its own output = escalate (producer/judge separation)

## Morning Report (always written: `docs/reports/auto-run-[date].md`)

On board-clear, ALSO emit a **review packet** (`docs/reports/review-packet-[date].md`, from
`${CLAUDE_PLUGIN_ROOT}/project-template/templates/review-packet.md`, RFN-007) — the per-task
backstop the human reviews once: PR / spec / ACs+evidence / quality / gate-judge verdict /
deviations / parks. `${CLAUDE_PLUGIN_ROOT}/scripts/validate_review_packet.py <path>` checks it is
complete (required sections; every Done row carries a PR). It is a review AID, not a gate — the merge
decision stays the human's. `/capiva:refine` references the same packet on its exit.


**Reconcile against the mechanical run-log.** Read `.state/run-log.jsonl`
(hook-written: deny / transition / gate / lock / guard-status /
heartbeat-missing events) and cross-check your
narrative against it. Any transition or gate you report MUST have a matching
run-log line; any deny in the log MUST be explained. The log is the ground
truth the model narrative is checked against — not the other way around.

Line 1 is ALWAYS why the loop stopped: board-empty | task-cap | phase-budget |
provider-limit | escalation-pile-up | cycle-defect. Then:
- PRs created (links) — awaiting YOUR merge decision
- Gates delegated, each with its basis (policy line or judge zero-anomaly)
- Escalations queued (count + one-line exceptions) → `.board/approvals.md`
- Tasks parked/blocked with three-strike details
- Skipped: awaiting attended grill
- Budget spend: tasks X/cap, phases Y/budget

Then reset loop fields (`Loop Active: no`, stop reason recorded) and log the
run summary in Phase History.

## Scheduling

Works under a scheduled routine or cron invocation. Safe because of the entry
gate + re-entry rule; recommended together with the notification recipe
(point a watcher at `.board/approvals.md` — see SECURITY.md posture: the
plugin itself never notifies over the network).

## Rules
- **Never grill. Never merge. Never touch the policy file.** (The guard mechanically denies the last two in every phase: merge verbs — `gh pr merge`, `git push` to the default branch — and policy-file writes. Grilling is contract-level: auto mode skips un-specced full-lane tasks.)
- **One stuck task never stalls the run** — park and continue.
- **Every delegated decision is auditable** in Phase History with its basis.
- **Attended mode is not affected by this skill's existence in any way.**
