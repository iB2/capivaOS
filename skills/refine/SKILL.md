---
name: refine
description: Clustered / batch-refine mode (ADR-0014 clustered-mode amendment + ADR-0017). Front-loads grilling for the WHOLE backlog in one attended session — iterate tasks in dependency order, run the grill-spec process + the context-answerer, produce approved spec+acs per task, then exit so /capiva:sprint or /capiva:auto executes the pre-approved backlog. Use when the user says "refine the backlog", "grill everything first", or "cluster the grilling".
---

# Refine — Clustered Batch-Grill (REFINING)

Cluster the human's grilling into one session, then let execution run unattended. This is the
oversight mode of the RFN epic: **front-load judgment, batch execution, review once.** It does not
implement or merge anything — it produces *approved specs* for the backlog and stops.

## When to use

Opt-in, invoked explicitly. Alternative to grilling one task at a time inside `/capiva:sprint`. The
attended per-task lane and the fast lane are unchanged; this is a third, additional lane
([ADR-0014](../../docs/adr/0014-autonomy-contract.md) clustered-mode amendment).

## Phase Guard (MANDATORY)

1. Read `.board/sprint-state.md`.
2. This skill runs in **Phase = REFINING**. If Phase = IDLE, transition IDLE→REFINING (a legal edge)
   via the orchestrator's single-writer rule, then proceed. If Phase is anything else → **STOP**:
   "⛔ Refine runs from IDLE (→REFINING). Current: [actual]. Finish or abort the active task first."
3. Board lock before any board write (ADR-0016), as always.

## Process

### Step 1 — Build the refine set
Read the backlog. Select every task eligible for refinement (has board ACs; not already
spec-approved). **Order by dependency** (a task whose `Depends` are all refined/done comes first) so
earlier decisions inform later specs.

### Step 2 — Refine each task (grill-spec, wrapped — never forked)
For each task in dependency order, run the base **grill-spec** adversarial interview
(`/capiva:grill-spec`) — but **this workflow interposes the `context-answerer` between grill-spec's
question-generation and human-answering.** The answerer is intrinsic to the grill-sprint (it is the
whole point of clustered mode); grill-spec itself stays workflow-agnostic and knows nothing about it
(ADR-0018 — the base skill is composed, not modified).

**Cadence — refine drives grill-spec in BATCH.** This composition overrides grill-spec's
one-question-at-a-time cadence (grill-spec Step 2): refine generates the *full* adversarial question
set first, then batch-triages it through the answerer, and only *then* presents the surviving
questions to the human — so "generate all, then triage, then ask" is the refine cadence, not a
contradiction of grill-spec's per-question flow. **The answerer subsumes grill-spec's "Explore Before
Asking" (Step 3):** the `context-answerer` IS refine's explore-before-asking mechanism (rigorously,
via cited FINDINGs), so skip grill-spec Step 3 when refine drives the interview — do not run both;
Step 3 stays in force for the attended per-task lane where no answerer runs.

The composed flow per task:

1. **Generate** grill-spec's full adversarial question set (unchanged, context-blind — never let
   answer-availability shrink the questions; [ADR-0017](../../docs/adr/0017-context-answerer-contract.md)
   invariant 3).
2. **Triage** via the `context-answerer` subagent (read-only): each question → `FINDING <cite>`
   (docs already decided) / `ROUTE` (ask the human) / `RED-FLAG` (contradiction — surface first).
3. **Ask the human only the ROUTEs and RED-FLAGs.** Findings are recorded cited, for spot-check.
4. **Synthesize** spec + `acs.json` per the grill-spec output contract.

### Step 3 — Itemized approval (per task; preserves the interlocutor)
Present each task's sheet with findings (auto, cited) and decisions (human) **itemized separately**,
so `Spec Approved` stays auditable (ADR-0014 clustered-mode: the human deciding every ROUTE *is* the
interlocutor moment). On approval, flip the board task's **Spec Approved: Yes** (board write, locked).
Never batch-approve across tasks — approval is per task.

Never-list holds unchanged: no P0/P1 auto-clear, no spec approval without the human deciding its
routed forks, no merge. A spec with an unresolved RED-FLAG or an untraceable AC does not get approved.

**Write-back (RFN-005 / ADR-0017 inv. 2).** When the human decides a routed question, append a
`DEC-[N]` entry to `.board/decisions.md` (status `open`, with rationale+constraints — never a bare
verdict; see board-protocol Decision Log). It is *non-dispositive prior art*: next time the answerer
may surface it but must still ROUTE — only a human promotes it to an ADR/CONTEXT term. When the
answerer cites a prior DEC entry, emit a `answerer-consulted` run-log event so `validate_decisions.py`
can compute the read-back rate. Read-back is surfaced, not acted on automatically — if it stays ~0 the
write-back is dead text and *you* remove it.

### Step 4 — Converge (fixed-point, bounded)
Grilling a task may **spawn** new tasks (write them to the backlog, locked). After a pass, re-scan:
if new eligible tasks appeared, refine them too. Repeat until no new tasks — bounded by a **spawn cap
(default 2 rounds)** so it cannot run away. If the cap is hit with tasks still un-refined, report them
as "awaiting a further refine pass" and stop.

### Step 5 — Exit (the grill→execute handoff)
When the refine set is exhausted (or the cap is hit), transition **REFINING → IDLE**. The exit report
is the handoff to the execution-sprint (ADR-0014 grill→execute-cycle amendment), so make it explicit:

- **Approved (the pre-approved backlog)**: list the task IDs now carrying `Spec Approved: Yes` — this
  is exactly what the execution-sprint will pick up.
- **Spawned** this run, and **anything left awaiting** a further refine pass.
- **Next step**: run **`/capiva:auto`** to execute the pre-approved backlog unattended — it will show a
  one-time pre-flight confirm, then create PRs for your review and **never merge**. (Attended
  `/capiva:sprint` remains the alternative if you'd rather drive each task yourself.)

The handoff is board state, not a separate artifact: `/capiva:auto` consumes every eligible
`Spec Approved: Yes` task in dependency order.

## What this skill does NOT do
- It does not implement, test, or merge — it produces approved specs and stops.
- It does not persist decisions to a reusable decision-log (that is RFN-005's two-tier write-back).
- It does not change question generation or the attended per-task lane.

## Boundary with /capiva:sprint and /capiva:auto
`/capiva:refine` produces the approved specs; `/capiva:sprint` / `/capiva:auto` consume them. Keeping
them separate is deliberate (the plan/execute split): refine is attended and judgment-heavy; execution
is mechanical and can be unattended.
