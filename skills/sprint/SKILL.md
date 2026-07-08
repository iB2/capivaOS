---
name: sprint
description: State-machine orchestrator — reads sprint-state, picks tasks, invokes skills in sequence, enforces phase transitions
---

# Sprint — Pipeline Orchestrator

The sprint skill is the ONLY entry point for the development pipeline. It reads the state machine, picks tasks, and invokes each skill in sequence with proper phase transitions.

## When to Use

Invoke `/capiva:sprint` to:
- Start a new development sprint (picks tasks from board)
- Resume an interrupted sprint (reads sprint-state to find where it stopped)
- Check pipeline status (reports current state without advancing)

## Process

### Step 0: Init Gate (MANDATORY)

**Before doing anything else, verify the harness has been initialized.**

Check all three conditions:

1. `docs/CONTEXT.md` exists and has **at least one glossary entry or domain rule** (not just empty template headers)
2. `docs/specs/INTAKE-summary.md` exists and has content
3. `.board/harness-config.md` has an `- **Active Blueprint**:` field whose blueprint resolves on disk — `capiva-blueprints/<name>/reference.md` in the project, or `${CLAUDE_PLUGIN_ROOT}/blueprints/<name>/reference.md` in the plugin

**If ANY condition fails → STOP:**

```
⛔ Harness not initialized. Run /capiva:init first.

Missing:
- [ ] docs/CONTEXT.md (populated)        ← domain context for spec grilling
- [ ] docs/specs/INTAKE-summary.md       ← project scope and requirements
- [ ] Active Blueprint configured         ← stack-specific patterns

/capiva:init will validate your project docs, detect your stack, and configure the harness.
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
2. Find the next ELIGIBLE task. Eligible = Status not Done/Blocked AND every ID
   in its **Depends** field is Done ("none" = no dependencies). A dependency
   that is Blocked counts as not-Done — skip and say why. Selection order is
   DETERMINISTIC (required for unattended runs): priority (P0 > P1 > P2 > P3 — P3 runs only when P0-P2 are exhausted, but it DOES run: the fast lane's headline case is a P3 task) →
   dependency order (a task never precedes anything it depends on) → board
   order as the tiebreak.
3. If the Depends graph contains a cycle: that is a BOARD DEFECT — report the
   cycle members and STOP task selection entirely (never silently skip a cycle
   member; `harness_lint` catches this in CI too).
4. If no eligible tasks: report "Sprint complete — no tasks available" (listing
   any dependency-blocked remainder) and STOP

5. **Lane selection (ADR-0010)** — evaluate the fast-lane qualifying predicate (ALL must hold):
   - Priority is P2 or P3
   - No new source files (task modifies existing files only, per its spec/AC)
   - No schema/migration changes
   - No architectural changes (blueprint §architecture) and no new dependencies

   ALL hold → Lane = fast. ANY fails (or P0/P1, or you cannot tell from the task) → Lane = full. **Full is the default; when in doubt, full.**

6. **Acquire board lock** (follow `${CLAUDE_PLUGIN_ROOT}/rules/board-protocol.md` protocol)
7. Move task to "In Progress" section
8. Set task Status = "In Progress", Phase = TRIAGE, Started = now
9. **Release board lock**

10. Update `.board/sprint-state.md`:
   - Task ID, Title, Priority from the selected task
   - Phase = TRIAGE, Lane = full | fast
   - Phase Started = now
   - Reset: Spec Approved = No, Plan Approved = No, Quality Gate = --
   - Add Phase History row: `| [now] | [task] | IDLE | TRIAGE | -- | Task selected; lane: [full|fast] ([reason]) |`

11. Present to human:
```
Sprint: picking up [TASK-ID] — [Task Title] (Priority: P1)
Lane: [full | fast — qualifies: P3, modify-only, no schema/arch changes]
Spec: [brief summary or "no spec — will create during grill"]
→ Starting Phase 1: [Grill Spec | Spec-Plan (fast lane)]
```

The human can override lane selection here ("full pipeline" always wins; "fast"
is honored ONLY if the predicate actually passes — a non-qualifying task cannot
be forced fast).

### Step 3: Load Spec

- If task has a linked spec document: read it into context
- If task has inline spec: extract it
- If task has no spec: note that /capiva:grill-spec will need to create one from the acceptance criteria

### Step 4: Execute Pipeline

Run each phase in strict sequence. Between each phase:
1. Update sprint-state
2. **Run context budget check** (see Step 4a)
3. If budget check triggers handover → invoke /capiva:handover instead of next phase

#### Step 4a — Context Budget Check (BEFORE EVERY PHASE)

At every phase boundary, BEFORE invoking the next skill:

```
CHECK context pressure:
  Read the hook-maintained count: the [COMPACTION COUNT] block injected
  after every compaction, or .state/compaction-count directly (0 if absent).
  Never estimate it yourself — the counter is hook-maintained (mechanical).

  IF count >= 2 → HANDOVER (mandatory)
  IF count == 1 AND next phase is IMPLEMENT or TEST_VERIFY → HANDOVER
  IF count == 1 AND next phase is PLAN, GRILL_SPEC, or FINISH → /compact with focus, continue
  IF count == 0 → continue

COMPACT FOCUS (when compacting between phases):
  /compact Focus: [TASK-ID] Phase [current→next].
  Preserve: sprint-state fields, modified files, branch name, artifact paths, decisions made.
  Discard: interview history, rejected alternatives, build logs, exploration output.
```

**If HANDOVER triggered:**
```
INVOKE /capiva:handover
STOP sprint loop (do not continue to next phase)
Report: "Context budget reached. Handover document written. Resume with /capiva:sprint in a new session."
```

#### Fast Lane (Lane = fast) — SPEC_PLAN → IMPLEMENT → VERIFY_FINISH

When Lane = fast, the loop runs the alternate path (ADR-0010) instead of Phases 1-5:

```
SPEC_PLAN:     CONTEXT CHECK → UPDATE state → Phase: SPEC_PLAN → INVOKE /capiva:spec-plan
               🧑 ONE gate: approve spec+plan → Spec Approved = Yes, Plan Approved = Yes
               → UPDATE state → IMPLEMENT
IMPLEMENT:     CONTEXT CHECK → INVOKE /capiva:implement   (unchanged — TDD enforced)
               → UPDATE state → VERIFY_FINISH
VERIFY_FINISH: CONTEXT CHECK → INVOKE /capiva:verify-finish
               🧑 ONE gate: quality review + merge decision → PR created
               → UPDATE state → IDLE, Lane reset to full
```

Transitions are logged in Phase History like any other. If /capiva:spec-plan or
/capiva:verify-finish aborts to the full lane (scope growth), the loop continues from
the phase they set (GRILL_SPEC or TEST_VERIFY) — do not restart.

#### Phase 1 — GRILL_SPEC

```
CONTEXT CHECK → (see Step 4a)
UPDATE sprint-state → Phase: GRILL_SPEC, Phase Started: [now]
LOG phase transition in Phase History
INVOKE /capiva:grill-spec
```

/capiva:grill-spec will:
- Run adversarial interview
- Produce `docs/specs/TASK-ID-spec.md`, `docs/specs/TASK-ID-acs.json`, CONTEXT.md entries, ADRs
- Present refined spec to human

**🧑 CHECKPOINT — Spec Approval**

Wait for human to say "approved" / "sim" / "go ahead" / "ok".
- If approved: SET Spec Approved = Yes in sprint-state. Continue.
- If rejected: iterate with /capiva:grill-spec. Do NOT advance.
- If "stop": end sprint gracefully (Step 6).

```
UPDATE sprint-state → Phase: PLAN, Spec Approved: Yes
LOG: | [now] | [task] | GRILL_SPEC | PLAN | spec-approved | [summary] |
```

#### Phase 2 — PLAN

```
CONTEXT CHECK → (see Step 4a)
INVOKE /capiva:plan
```

/capiva:plan will:
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
INVOKE /capiva:implement
```

/capiva:implement will:
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

**Note**: /capiva:implement delegates to subagents, which have their own context windows.
The main context consumes tokens for orchestration, not implementation.
However, collecting subagent results and running reviews is still ~30-60K.

#### Phase 4 — TEST_VERIFY

```
CONTEXT CHECK → (see Step 4a — TEST_VERIFY is the second most expensive phase)
INVOKE /capiva:test-verify
```

/capiva:test-verify will:
- Generate integration tests (two-agent pattern)
- Run static analysis (per blueprint §static-analysis)
- Produce `docs/reports/TASK-ID-quality.md`
- Present quality report

**🧑 CHECKPOINT — Quality Review**

Human reviews the quality report.
- If gates pass and human approves: continue.
- If human requests additional tests: iterate.
- If hard fail: block and escalate.

```
UPDATE sprint-state → Phase: FINISH, Quality Gate: PASS
LOG: | [now] | [task] | TEST_VERIFY | FINISH | quality-approved | coverage X%, quality gate pass |
```

#### Phase 5 — FINISH

```
CONTEXT CHECK → (see Step 4a — FINISH is lightweight, usually safe to continue)
INVOKE /capiva:finish
```

/capiva:finish will:
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

1. **`/clear`** — mandatory context reset (the SessionStart hook resets `.state/compaction-count` to 0)
2. Re-read `.board/sprint-state.md` (should be IDLE)
3. Re-read `.board/tasks.md` for updated state
4. Return to Step 2 (pick next task)

### Step 6: Sprint End

Sprint ends when:
- **Board empty**: No more P0-P3 tasks
- **Human stop**: "stop", "pause", "enough", "para"
- **Context handover**: /capiva:handover was triggered (sprint continues in next session)

On sprint end, produce summary:

```markdown
## Sprint Summary

### Completed
- [TASK-ID] Title — PR #N (coverage: X%, quality gate: pass)

### In Progress (if handover or interrupted)
- [TASK-ID] Title — Phase [N], handover at docs/handover/TASK-ID-handover.md

### Remaining
- [TASK-ID] Title (P2) — unstarted

### Metrics
- Tasks completed: N
- PRs created: N
- Average coverage: X%
- Static analysis quality gate: pass/fail

### Context
- Auto-compactions this session: N
- Handover triggered: Yes/No
- Resume: /capiva:sprint in new session (reads sprint-state to continue)
```

## Orchestrator Mode — Phase Isolation (ADR-0014)

When `- **Phase Isolation**: on` in `.board/harness-config.md` (attended opt-in)
or when running under auto mode (always), the sprint loop stops executing phases
inline and becomes a thin dispatcher. The orchestrating context holds only
state-shuttling — it never does phase work, so it never grows.

**Per phase**: spawn a `phase-runner` agent with the briefing package →
await its completion report → validate the phase's required artifacts exist on
disk (Law 3 is the ORCHESTRATOR'S check, not the runner's claim) → perform the
sprint-state transition + Phase History row yourself → proceed.

**Briefing package** (assembled per phase):
1. The phase's full SKILL body from `${CLAUDE_PLUGIN_ROOT}/skills/<phase>/SKILL.md`
2. `${CLAUDE_PLUGIN_ROOT}/rules/laws.md` content
3. Current Task block of `.board/sprint-state.md` + `.board/harness-config.md`
4. Explicit input artifact paths and the phase's required outputs

**Phase applicability**:
| Phase | Isolated? |
|-------|-----------|
| GRILL_SPEC | NO in attended mode — it is an interview; the interlocutor lives here. (Auto mode never grills — ADR-0014) |
| PLAN / TEST_VERIFY / FINISH / SPEC_PLAN / VERIFY_FINISH | Yes — via phase-runner |
| IMPLEMENT | Already isolated by construction: the ORCHESTRATOR dispatches one dev agent per PLAN.md micro-task directly (subagents cannot spawn subagents), collecting validated JSON reports — same TDD/verification protocol as the inline skill |

**Single-writer rule**: only the orchestrator writes `.board/sprint-state.md`.
A runner that transitions state has violated its briefing; the orchestrator's
view wins. Runner failure without required artifacts = one strike; three
strikes = BLOCKED (unchanged).

**Human gates are unchanged by isolation**: in attended mode, gate presentations
still block here in the main context, exactly as below.

## Rules

- **Sprint-state is the source of truth.** If it says IMPLEMENT, you're in IMPLEMENT. No overrides.
- **One task at a time.** Sequential by design. Parallelism happens WITHIN /capiva:implement, not across tasks.
- **`/clear` between tasks.** Non-negotiable. Context hygiene prevents quality degradation.
- **Never skip phases.** Even for "trivial" tasks. The pipeline IS the quality guarantee. (The fast lane is not a skip — it is an alternate state-machine path with its own guarded phases; see ADR-0010.)
- **Lane selection is mechanical.** The predicate decides; the human can force full but cannot force fast for a non-qualifying task.
- **Checkpoints are blocking.** Silence ≠ approval. Wait for explicit human confirmation.
- **Resume on restart.** If sprint-state shows a task in progress, resume from that phase.
- **Log everything.** Every phase transition goes in the Phase History table.
- **Board lock for writes.** Every board write follows the lock protocol.
- **Context budget is a hard limit.** 2+ auto-compactions = mandatory handover. No exceptions. No "just one more phase."
- **Handover at phase boundaries.** Always complete the current phase step before handing over. Never hand over mid-skill.
- **No timebox.** The sprint is token-bounded, not time-bounded. It runs until the board is empty or context is exhausted.
