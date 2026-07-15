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
For each task in dependency order, run the **grill-spec process** (Steps 1–5 of `/capiva:grill-spec`)
with the **context-answerer** enabled (it is the whole point of clustered mode — set
`Context Answerer: on` for the run, or honor the config):

1. **Generate** the full adversarial question set (unchanged, context-blind — never let
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

### Step 4 — Converge (fixed-point, bounded)
Grilling a task may **spawn** new tasks (write them to the backlog, locked). After a pass, re-scan:
if new eligible tasks appeared, refine them too. Repeat until no new tasks — bounded by a **spawn cap
(default 2 rounds)** so it cannot run away. If the cap is hit with tasks still un-refined, report them
as "awaiting a further refine pass" and stop.

### Step 5 — Exit
When the refine set is exhausted (or the cap is hit), transition **REFINING → IDLE**. Report: tasks
refined + approved, tasks spawned, anything left awaiting. Execution is a separate step — the human
runs `/capiva:sprint` (attended) or `/capiva:auto` (unattended) to clear the pre-approved backlog.

## What this skill does NOT do
- It does not implement, test, or merge — it produces approved specs and stops.
- It does not persist decisions to a reusable decision-log (that is RFN-005's two-tier write-back).
- It does not change question generation or the attended per-task lane.

## Boundary with /capiva:sprint and /capiva:auto
`/capiva:refine` produces the approved specs; `/capiva:sprint` / `/capiva:auto` consume them. Keeping
them separate is deliberate (the plan/execute split): refine is attended and judgment-heavy; execution
is mechanical and can be unattended.
