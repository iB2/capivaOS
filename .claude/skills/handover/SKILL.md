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
1. **Automatically by /sprint** when context budget rules trigger (see `.claude/rules/context-management.md`)
2. **Manually by human** — "hand over", "save and continue later", "pausa", "/handover"
3. **Before expensive phases** when context is already pressured (1+ auto-compactions)
4. **On sprint interruption** — rate limit, timeout, or user stop

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
3. [Specific next action — e.g., "Run /implement to continue micro-task execution"]

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
- Last test run: `dotnet test` — [N] passed, [M] failed, [K] skipped
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
- Static analysis: [run/not run — StyleCop warnings, SonarQube status if available]
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

To resume: start a new session, run /sprint, and the pipeline will detect
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

- **Handover is not optional when triggered.** Context budget rules are hard limits. See `.claude/rules/context-management.md`.
- **Persist everything before documenting.** Save artifacts → commit code → update board → THEN write handover doc.
- **The document must be self-contained.** A fresh agent reads ONLY the handover doc + sprint-state to resume. If they'd need to ask "what happened?", the handover is incomplete.
- **Don't restart the pipeline.** The handover explicitly tells the next agent which phases are DONE. Redoing approved work wastes time and may produce different (worse) results.
- **Handover at phase boundaries when possible.** Between phases is the cleanest handover point. Mid-phase handovers work but require more detail.
- **Never lose uncommitted code.** `git add . && git commit -m "WIP: handover at [phase]"` before writing the handover doc.
