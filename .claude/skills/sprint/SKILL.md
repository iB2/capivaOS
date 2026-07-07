---
name: sprint
description: State-machine orchestrator — reads sprint-state, picks tasks, invokes skills in sequence, enforces phase transitions
---

# Sprint — Pipeline Orchestrator

The sprint skill is the ONLY entry point for the development pipeline. It reads the state machine, picks tasks, and invokes each skill in sequence with proper phase transitions.

## When to Use

Invoke `/sprint` to:
- Start a new development sprint (picks tasks from board)
- Resume an interrupted sprint (reads sprint-state to find where it stopped)
- Check pipeline status (reports current state without advancing)

## Process

### Step 0: Init Gate (MANDATORY)

**Before doing anything else, verify the harness has been initialized.**

Check all three conditions:

1. `docs/CONTEXT.md` exists and has **at least one glossary entry or domain rule** (not just empty template headers)
2. `docs/specs/INTAKE-summary.md` exists and has content
3. The `Active Blueprint:` line in `.claude/CLAUDE.md` points to a blueprint directory that exists on disk (e.g., `.claude/blueprints/nextjs-typescript/reference.md` is a real file)

**If ANY condition fails → STOP:**

```
⛔ Harness not initialized. Run /init first.

Missing:
- [ ] docs/CONTEXT.md (populated)        ← domain context for spec grilling
- [ ] docs/specs/INTAKE-summary.md       ← project scope and requirements
- [ ] Active Blueprint configured         ← stack-specific patterns

/init will validate your project docs, detect your stack, and configure the harness.
Without it, the pipeline starts from zero context — specs will be shallow,
plans will miss constraints, and implementation will lack stack guidance.
```

**Do NOT proceed to Step 1 until all three conditions pass.**

### Step 1: Read State

Read `.board/sprint-state.md` and determine current state:

- **Phase = IDLE**: Clean state. Proceed to pick a new task (Step 2).
- **Phase = BLOCKED**: Report what's blocked and wait for human resolution.
- **Phase ≠ IDLE and ≠ BLOCKED**: Sprint was interrupted. Resume from the current phase (Step 4).

Report the state to the human:
```
Sprint state: [IDLE | Resuming TASK-ID at phase IMPLEMENT | BLOCKED on...]
```

### Step 2: Pick Task (TRIAGE)

1. Read `.board/tasks.md`
2. Find highest-priority uncompleted, unblocked task (P0 > P1 > P2)
3. If no eligible tasks: report "Sprint complete — no tasks available" and STOP

4. **Acquire board lock** (follow `.claude/rules/board-protocol.md` protocol)
5. Move task to "In Progress" section
6. Set task Status = "In Progress", Phase = TRIAGE, Started = now
7. **Release board lock**

8. Update `.board/sprint-state.md`:
   - Task ID, Title, Priority from the selected task
   - Phase = TRIAGE
   - Phase Started = now
   - Reset: Spec Approved = No, Plan Approved = No, Quality Gate = --
   - Add Phase History row: `| [now] | [task] | IDLE | TRIAGE | -- | Task selected from board |`

9. Present to human:
```
Sprint: picking up [TASK-ID] — [Task Title] (Priority: P1)
Spec: [brief summary or "no spec — will create during grill"]
→ Starting Phase 1: Grill Spec
```

### Step 3: Load Spec

- If task has a linked spec document: read it into context
- If task has inline spec: extract it
- If task has no spec: note that /grill-spec will need to create one from the acceptance criteria

### Step 4: Execute Pipeline

Run each phase in strict sequence. Between each phase:
1. Update sprint-state
2. **Run context budget check** (see Step 4a)
3. If budget check triggers handover → invoke /handover instead of next phase

#### Step 4a — Context Budget Check (BEFORE EVERY PHASE)

At every phase boundary, BEFORE invoking the next skill:

```
CHECK context pressure:
  IF 2+ auto-compactions have occurred this session → HANDOVER (mandatory)
  IF 1 auto-compaction AND next phase is IMPLEMENT or TEST_VERIFY → HANDOVER
  IF 1 auto-compaction AND next phase is PLAN, GRILL_SPEC, or FINISH → /compact with focus, continue
  IF 0 auto-compactions → continue

COMPACT FOCUS (when compacting between phases):
  /compact Focus: [TASK-ID] Phase [current→next].
  Preserve: sprint-state fields, modified files, branch name, artifact paths, decisions made.
  Discard: interview history, rejected alternatives, build logs, exploration output.
```

**If HANDOVER triggered:**
```
INVOKE /handover
STOP sprint loop (do not continue to next phase)
Report: "Context budget reached. Handover document written. Resume with /sprint in a new session."
```

#### Phase 1 — GRILL_SPEC

```
CONTEXT CHECK → (see Step 4a)
UPDATE sprint-state → Phase: GRILL_SPEC, Phase Started: [now]
LOG phase transition in Phase History
INVOKE /grill-spec
```

/grill-spec will:
- Run adversarial interview
- Produce `docs/specs/TASK-ID-spec.md`, CONTEXT.md entries, ADRs
- Present refined spec to human

**🧑 CHECKPOINT — Spec Approval**

Wait for human to say "approved" / "sim" / "go ahead" / "ok".
- If approved: SET Spec Approved = Yes in sprint-state. Continue.
- If rejected: iterate with /grill-spec. Do NOT advance.
- If "stop": end sprint gracefully (Step 6).

```
UPDATE sprint-state → Phase: PLAN, Spec Approved: Yes
LOG: | [now] | [task] | GRILL_SPEC | PLAN | spec-approved | [summary] |
```

#### Phase 2 — PLAN

```
CONTEXT CHECK → (see Step 4a)
INVOKE /plan
```

/plan will:
- Read approved spec
- Decompose into micro-tasks
- Write PLAN.md
- Present for approval

**🧑 CHECKPOINT — Plan Approval**

Wait for explicit approval.
- If approved: SET Plan Approved = Yes. Continue.
- If changes requested: revise plan, re-present. Do NOT advance.

```
UPDATE sprint-state → Phase: IMPLEMENT, Plan Approved: Yes
LOG: | [now] | [task] | PLAN | IMPLEMENT | plan-approved | [N] micro-tasks |
```

#### Phase 3 — IMPLEMENT

```
CONTEXT CHECK → (see Step 4a — IMPLEMENT is the most expensive phase)
INVOKE /implement
```

/implement will:
- Create feature branch
- Execute micro-tasks via subagents (TDD enforced)
- Run final test verification
- Report completion

No human checkpoint here — implementation is autonomous.
If all tests green:

```
UPDATE sprint-state → Phase: TEST_VERIFY
LOG: | [now] | [task] | IMPLEMENT | TEST_VERIFY | tests-green | [N] tasks, [M] tests |
REGISTER artifact: Branch = [branch-name]
```

**Note**: /implement delegates to subagents, which have their own context windows.
The main context consumes tokens for orchestration, not implementation.
However, collecting subagent results and running reviews is still ~30-60K.

#### Phase 4 — TEST_VERIFY

```
CONTEXT CHECK → (see Step 4a — TEST_VERIFY is the second most expensive phase)
INVOKE /test-verify
```

/test-verify will:
- Generate integration tests (two-agent pattern)
- Run static analysis (SonarQube + StyleCop)
- Produce `docs/reports/TASK-ID-quality.md`
- Present quality report

**🧑 CHECKPOINT — Quality Review**

Human reviews the quality report.
- If gates pass and human approves: continue.
- If human requests additional tests: iterate.
- If hard fail: block and escalate.

```
UPDATE sprint-state → Phase: FINISH, Quality Gate: PASS
LOG: | [now] | [task] | TEST_VERIFY | FINISH | quality-approved | coverage X%, SonarQube pass |
```

#### Phase 5 — FINISH

```
CONTEXT CHECK → (see Step 4a — FINISH is lightweight, usually safe to continue)
INVOKE /finish
```

/finish will:
- Create PR with structured description
- Update board (move to Done)
- Transition Jira if configured
- Clean up worktree

**🧑 CHECKPOINT — Merge Decision**

Human decides: merge now, keep for review, or discard.

```
UPDATE sprint-state → Phase: IDLE
LOG: | [now] | [task] | FINISH | IDLE | [merge/review/discard] | PR #[N] |
INCREMENT sprint metrics (tasks completed, PRs created)
RESET Current Task fields to (none)
```

### Step 5: Between Tasks

After completing a task:

1. **`/clear`** — mandatory context reset (this resets compaction counter)
2. Re-read `.board/sprint-state.md` (should be IDLE)
3. Re-read `.board/tasks.md` for updated state
4. Return to Step 2 (pick next task)

### Step 6: Sprint End

Sprint ends when:
- **Board empty**: No more P0-P2 tasks
- **Human stop**: "stop", "pause", "enough", "para"
- **Context handover**: /handover was triggered (sprint continues in next session)

On sprint end, produce summary:

```markdown
## Sprint Summary

### Completed
- [TASK-ID] Title — PR #N (coverage: X%, SonarQube: pass)

### In Progress (if handover or interrupted)
- [TASK-ID] Title — Phase [N], handover at docs/handover/TASK-ID-handover.md

### Remaining
- [TASK-ID] Title (P2) — unstarted

### Metrics
- Tasks completed: N
- PRs created: N
- Average coverage: X%
- SonarQube quality gate: pass/fail

### Context
- Auto-compactions this session: N
- Handover triggered: Yes/No
- Resume: /sprint in new session (reads sprint-state to continue)
```

## Rules

- **Sprint-state is the source of truth.** If it says IMPLEMENT, you're in IMPLEMENT. No overrides.
- **One task at a time.** Sequential by design. Parallelism happens WITHIN /implement, not across tasks.
- **`/clear` between tasks.** Non-negotiable. Context hygiene prevents quality degradation.
- **Never skip phases.** Even for "trivial" tasks. The pipeline IS the quality guarantee.
- **Checkpoints are blocking.** Silence ≠ approval. Wait for explicit human confirmation.
- **Resume on restart.** If sprint-state shows a task in progress, resume from that phase.
- **Log everything.** Every phase transition goes in the Phase History table.
- **Board lock for writes.** Every board write follows the lock protocol.
- **Context budget is a hard limit.** 2+ auto-compactions = mandatory handover. No exceptions. No "just one more phase."
- **Handover at phase boundaries.** Always complete the current phase step before handing over. Never hand over mid-skill.
- **No timebox.** The sprint is token-bounded, not time-bounded. It runs until the board is empty or context is exhausted.
