---
name: handover
description: Document pipeline state and produce a self-contained handover for a fresh agent to resume with zero context loss. Triggered by context budget limits or manually.
---

# Handover — Context-Safe Pipeline Continuation

Produce a handover document that enables a fresh agent (new session, different machine,
different person) to resume the pipeline from the exact point where this session stops.

The handover document is the ONLY thing the next agent reads to get started.
If it's incomplete, the next agent wastes time reconstructing context.

## When This Skill Runs

This skill is invoked:
1. **Automatically by /capiva:sprint** when context budget rules trigger (see `${CLAUDE_PLUGIN_ROOT}/rules/context-management.md`)
2. **Manually by human** — "hand over", "save and continue later", "pausa", "/capiva:handover"
3. **Before expensive phases** when context is already pressured (1+ auto-compactions)
4. **On sprint interruption** — rate limit, timeout, or user stop

## Two Modes

This skill has two modes. Pick by WHAT is being handed over.

**Mode A — Task/Sprint handover** (default — everything under "Process" below): one task inside
the `/capiva:sprint` pipeline. Triggered as listed above.

**Mode B — Orchestrator-Seat handover** (see the section at the end of this file): the BOSS SEAT
of a whole multi-track project, handed to a fresh agent that must "become you." Use Mode B when
the request signals the SEAT, not a task:
"handover do assento/seat de orquestrador", "passe/atualize o plano pro próximo agente",
"orchestrator seat", "ele precisa 'ser você'", "prepara a mensagem pro novo agente pra eu colar",
"hand over the project". If unsure which mode → ask.

## Process

### Step 1: Snapshot Current State

Read and capture ALL of the following (don't skip any — missing data = lost context):

1. **Sprint state**: Read `.board/sprint-state.md` completely
2. **Board state**: Read `.board/tasks.md` — active task, progress notes, phase
3. **Current phase progress**:
   - If GRILL_SPEC: how many questions asked, what's been clarified, what remains
   - If PLAN: approach approved? how many tasks decomposed? PLAN.md written?
   - If IMPLEMENT: which micro-tasks complete, which in progress, branch name, test status
   - If TEST_VERIFY: tests written? Static analysis run? report drafted?
   - If FINISH: PR created? board updated?
4. **Artifact inventory**: which artifacts exist on disk (spec, plan, report, branch)
5. **Decisions made**: any choices during this session that aren't captured in artifacts yet
6. **Open questions**: anything unresolved that the next agent needs to address
7. **Modified files list**: everything changed in this session

### Step 2: Ensure Artifacts Are on Disk

Everything must be persisted — not just in conversation memory:

- [ ] Sprint-state.md is current (phase, approvals, artifacts registered)
- [ ] If spec was being written → save to `docs/specs/TASK-ID-spec.md` (even if incomplete, mark as DRAFT)
- [ ] If plan was being written → save to `PLAN.md` (even if incomplete, mark remaining tasks as TODO)
- [ ] If implementation is in progress → commit all changes on the feature branch, push to remote
- [ ] If quality report was being drafted → save to `docs/reports/TASK-ID-quality.md` (even partial)
- [ ] If CONTEXT.md was updated → ensure saved
- [ ] If ADRs were created → ensure saved

**Critical**: `git add` and `git commit` any uncommitted work on the feature branch.
A handover with uncommitted code is a handover with lost work.

### Step 3: Update Board

**Acquire board lock**, then update the active task:

```markdown
- [ ] **TASK-ID** Task title (P1)
  - **Status**: In Progress
  - **Phase**: [current phase]
  - **Progress**: [specific — "3/7 micro-tasks complete", "spec draft at 80%", etc.]
  - **Branch**: feature/TASK-ID-slug (if exists)
  - **Handover**: docs/handover/TASK-ID-handover.md
  - **Notes**: Handover at [timestamp] — context budget reached after [N] compactions
```

**Release board lock.**

### Step 4: Write Handover Document

Write to `docs/handover/TASK-ID-handover.md`:

```markdown
# Handover: [Task Title]

> Written: [ISO timestamp]
> By: [session/agent identifier if available]
> Reason: [context budget | manual | interruption]

## Resume Instructions

**You are resuming [TASK-ID] at Phase [PHASE_NAME].**

1. Read `.board/sprint-state.md` — it has your current state
2. Read this document — it has the context you need
3. [Specific next action — e.g., "Run /capiva:implement to continue micro-task execution"]

DO NOT restart the pipeline from scratch. The work below has been completed and approved.

## Completed Work

### Phases Done
| Phase | Status | Key Output |
|-------|--------|-----------|
| TRIAGE | ✅ Done | Task selected from board |
| GRILL_SPEC | ✅ Done | Spec approved: docs/specs/TASK-ID-spec.md |
| PLAN | ✅ Done | Plan approved: PLAN.md (N tasks) |
| IMPLEMENT | 🔶 Partial | 4/7 tasks done, 3 remaining |
| TEST_VERIFY | ⬜ Not started | — |
| FINISH | ⬜ Not started | — |

### Artifacts on Disk
| Artifact | Path | Status |
|----------|------|--------|
| Spec | docs/specs/TASK-ID-spec.md | ✅ Approved |
| CONTEXT.md | docs/CONTEXT.md | ✅ Updated (N new terms) |
| ADRs | docs/adr/000N-slug.md | ✅ Written |
| PLAN.md | PLAN.md | ✅ Approved |
| Feature branch | feature/TASK-ID-slug | 🔶 4/7 tasks committed |
| Quality report | — | ⬜ Not started |
| Handover | docs/handover/TASK-ID-handover.md | 📄 This document |

### Branch State (if IMPLEMENT in progress)
- Branch: `feature/TASK-ID-slug`
- Based on: `main` at commit [hash]
- Commits: [N] (list one-line summaries)
- Last test run: [test command per blueprint §build-commands] — [N] passed, [M] failed, [K] skipped
- Uncommitted changes: [none / description]

## Current Phase Detail

### [Phase Name] — Progress

[Detailed description of where within the current phase things stopped.
This is the most critical section — be specific enough that the next agent
knows EXACTLY what to do next.]

**If GRILL_SPEC:**
- Questions asked: [list with answers]
- Questions remaining: [list]
- Spec draft status: [complete/partial — which sections done]

**If PLAN:**
- Approach: [approved/pending]
- Tasks decomposed: [N of M]
- PLAN.md status: [written/partial]

**If IMPLEMENT:**
- Tasks completed: [list with commit hashes]
- Task in progress: [task N — what's done, what remains]
- Tasks remaining: [list with dependencies]
- Parallel group status: [which groups done, which pending]
- Known issues: [any failing tests, blocked tasks]

**If TEST_VERIFY:**
- Tests written: [which categories done]
- Static analysis: [run/not run — linter warnings, quality gate status per blueprint §static-analysis]
- Report: [drafted/not started]
- Quality gates: [known status]

## Decisions Made This Session

[Numbered list of decisions that are NOT captured in artifacts.
These are conversation decisions that would be lost without this section.]

1. [Decision]: [what was decided and why]
2. [Decision]: [what was decided and why]

## Open Questions / Known Issues

[Anything the next agent needs to be aware of.
Not "general concerns" — specific, actionable items.]

1. [Issue]: [description + suggested resolution]
2. [Question]: [what needs answering before the next step]

## Context the Next Agent Will Need

[Pointers to files the next agent should read to build context.
Ordered by priority — most important first.]

1. `.board/sprint-state.md` — current pipeline state
2. `docs/specs/TASK-ID-spec.md` — what we're building
3. `PLAN.md` — how we're building it
4. `docs/CONTEXT.md` — domain terms (read the terms relevant to this task)
5. [Any other relevant files]
```

### Step 5: Update Sprint State

Update `.board/sprint-state.md`:
- Add Phase History row: `| [now] | [task] | [current phase] | HANDOVER | context-budget | [compaction count] compactions, [reason] |`
- Note: Phase field stays at the current phase (NOT changed to IDLE — the task is still in progress)

### Step 6: Confirm to Human

Present:
```
Handover complete.

📄 Handover document: docs/handover/TASK-ID-handover.md
📋 Sprint state: updated at Phase [X]
📦 Board: task updated with progress notes
🔀 Branch: [committed and pushed / no branch yet]

To resume: start a new session, run /capiva:sprint, and the pipeline will detect
the in-progress task and resume from Phase [X].

Or a fresh agent can read the handover document directly for full context.
```

## Quality Standard for Handover Documents

The handover document follows the same anti-slop rules as all artifacts:

- **No vague progress.** Not "some tasks done" — "tasks 1-4 complete (commits abc, def, ghi, jkl), task 5 in progress (test written, implementation 60% done), tasks 6-7 not started."
- **No missing artifacts.** Every artifact's disk path and status must be listed.
- **No assumptions.** The next agent has NEVER seen this codebase. Don't say "continue as before" — say exactly what to do.
- **Branch state must be current.** If there's uncommitted work, commit it before handover. Mention the commit hash.
- **Decisions must be explicit.** "We decided to use cache-aside pattern" is useless without "because [reason], and this means [implication for remaining work]."

## Rules

- **Handover is not optional when triggered.** Context budget rules are hard limits. See `${CLAUDE_PLUGIN_ROOT}/rules/context-management.md`.
- **Persist everything before documenting.** Save artifacts → commit code → update board → THEN write handover doc.
- **The document must be self-contained.** A fresh agent reads ONLY the handover doc + sprint-state to resume. If they'd need to ask "what happened?", the handover is incomplete.
- **Don't restart the pipeline.** The handover explicitly tells the next agent which phases are DONE. Redoing approved work wastes time and may produce different (worse) results.
- **Handover at phase boundaries when possible.** Between phases is the cleanest handover point. Mid-phase handovers work but require more detail.
- **Never lose uncommitted code.** `git add . && git commit -m "WIP: handover at [phase]"` before writing the handover doc.

---

## Mode B — Orchestrator-Seat Handover

You are handing over the SEAT of a whole project (many tracks, subagents, decisions) — not one
task. The next agent must be able to "be you": own the sequencing, delegation, validation, and
the "is this actually done?" check with zero context loss. Produce or UPDATE one living seat
document, then deliver it to the next agent.

### Reference the durable — don't re-embed it
Identity, standing guardrails, and global rules already live in durable files (the project's
`CLAUDE.md`, memory, board). POINT to them ("operate under the guardrails in `<file>`"); do NOT
paste their full text into every handover — a re-embedded copy just goes stale and burns tokens.
The seat doc carries only what is NOT already durable: the live plan, this session's decisions,
work in flight, dead ends, and the resume point.

### Where it lives
`docs/handover/PROJECT-ORCHESTRATOR-handover.md` in the project's primary repo (fall back to the
project folder if there is no repo). It is a LIVING doc: UPDATE in place, newest block on top;
never fork a new file per handover.

### Step 1 — Refresh before writing
Reconcile the CURRENT prioritized plan (board/tasks, blocked vs unblocked, the priority/spec
agreed with the human). Hand over the plan as it is NOW, not a stale snapshot. Persist any
session-only state (worktree/scratchpad paths, verbal agreements) — if it lives only in this
window, it is about to be lost.

### Step 2 — Update the seat document (newest block on top)

    # Project Handover — [Project] — the ORCHESTRATOR SEAT
    > Updated [ISO] by [session id]. Living doc: newest block first, UPDATE in place.
    > This is the WHOLE-PROJECT seat, not a task. Read once, top to bottom — it is your full orientation.

    ## ★★★ [DATE] — READ THIS FIRST (latest)
    [What changed since the last handover: advanced / completed / merged (commits, PRs). Newest
     first; older dated blocks stay below for continuity.]

    ## HOW TO OPERATE THIS SEAT
    - You are the SOLE orchestrator: you coordinate and VALIDATE; you do not build directly.
      Subagents build — you write precise briefs, then re-validate every result yourself
      (adversarial: gates AND your own eyes; a green gate is not proof).
    - Keep the record current each session: board, this doc, memory.
    - Operate under the standing guardrails in [pointer to CLAUDE.md / rules] — do not restate them here.

    ## PRIORITIZED PLAN (current — agreed with the human)
    | Prio | Item | Status | Done = (acceptance bar) | Spec / where | Notes |
    (P0→P3. "Done =" is the agreed acceptance criterion for THIS item — the yardstick the next
     agent uses for its "is this actually done?" check. Priority + spec are as agreed, not re-derived.)

    ## BLOCKED — dependency, unblock trigger, owner
    | Item | Blocked on | Unblocks when | Owner |

    ## DELEGATED CONVERSATIONS / AGENTS — and what each owes
    | Agent / session | Track | Owes | State |

    ## WORK IN FLIGHT (running now — do NOT re-spawn)
    | Agent / job | Task id / how to check | What it owes | Expected signal |
    (Background agents/jobs still running: their id, where output lands, and the fact that a fresh
     agent must WAIT for their result instead of starting the same work again.)

    ## REJECTED / DEAD ENDS (do not re-explore)
    [Approaches already tried and discarded, each with WHY. This is the anti-rework carry — the
     single most expensive thing to lose is a path the next agent re-explores because nobody
     wrote down that it was already killed.]

    ## DECISIONS THIS SESSION (not yet in artifacts)
    1. [decision + why + implication for remaining work]

    ## RESUME POINT
    [Exact next action. "Continue X" is banned — say precisely what to do next.]

### Step 3 — Deliver to the next agent
Default: the next agent is ALREADY started (the human set its model). On finishing the doc,
contact it over the mesh (SendMessage) with a short pointer: "You hold the ORCHESTRATOR SEAT for
[project]. Read `docs/handover/PROJECT-ORCHESTRATOR-handover.md` — top block + HOW TO OPERATE THIS
SEAT first; it is your full context. Resume at [resume point]." If the human asked for a
paste-ready message instead, output the full message as text — don't just point at the file.

### Mode B quality standard
- The plan handed over is the CURRENT prioritized one; blocked/unblocked reflects reality now.
- Every item carries its "Done =" acceptance bar, so the next agent can actually run the done-check.
- Every delegated agent, and every job still IN FLIGHT, is listed — no duplicate work, nothing orphaned.
- Rejected paths are recorded with WHY — the next agent never re-explores a dead end.
- Guardrails/identity are REFERENCED from the durable source, not re-embedded.
- Nothing session-only is lost (paths, worktrees, verbal decisions).
