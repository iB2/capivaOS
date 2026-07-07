---
name: implement
description: Phase 3 — Subagent-driven development with phase guard. Executes PLAN.md via isolated subagents with TDD enforcement.
---

# Implement — Phase 3

Execute an approved plan by spawning subagents for each micro-task. TDD is enforced — tests before code. All work happens on an isolated feature branch.

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = IMPLEMENT
3. Verify Plan Approved = Yes
4. Verify `PLAN.md` exists in working directory
5. Check if `docs/tech-context/TASK-ID-tech.md` exists:
   - If YES → include in each subagent's context alongside spec and PLAN.md
   - If NO and Lane = fast with PLAN.md noting "fast lane: tech context inline" → proceed (fast lane embeds tech findings in PLAN.md; see /spec-plan)
   - If NO otherwise → check sprint-state Notes for "domain-only" flag. If flagged, proceed. If NOT flagged → **WARN**: "Tech context missing. Consider running /plan Step 1.5 (Context7 discovery) to avoid using stale API docs."
6. If ANY check fails → **STOP**: "⛔ Phase guard failed. [specific failure]. Complete /plan first."
7. If ALL checks pass → proceed

## Process

### Step 1: Setup

1. Read `PLAN.md` for the complete task list
2. Read `docs/CONTEXT.md` for domain terms
3. Read `docs/specs/TASK-ID-spec.md` for acceptance criteria reference
4. Read `docs/tech-context/TASK-ID-tech.md` for current library documentation (produced by /plan)
5. Read the active blueprint's `reference.md` for stack-specific commands and patterns
6. Create feature branch:
   ```bash
   git checkout -b feature/TASK-ID-slug
   ```
7. Verify clean baseline using the test command from blueprint §build-commands.
   All existing tests MUST pass. If they don't → STOP and report.

8. Update `.board/sprint-state.md`:
   - Register artifact: Branch = `feature/TASK-ID-slug`

### Step 2: Execute Tasks

For each task in PLAN.md, in dependency order:

#### a. Spawn Subagent

Launch a dev-role subagent (`.claude/agents/roles/dev.md`) with:
- The task description from PLAN.md (verbatim)
- `docs/CONTEXT.md` domain terms
- `docs/tech-context/TASK-ID-tech.md` current library docs (relevant sections for this task's libraries)
- The active blueprint's `reference.md`
- Feature branch name
- Instruction: **write the failing test FIRST**
- Instruction: **use API patterns from the tech context file, not training data**
- Instruction: **do NOT modify any other files besides those listed in the task**

Each subagent gets fresh context — no bleed from previous tasks.

#### b. TDD Enforcement

The subagent MUST follow this cycle:
1. **RED**: Write a failing test that captures the requirement
2. **GREEN**: Write the minimum code to make the test pass
3. **REFACTOR**: Clean up without changing behavior

**Enforcement**: If a subagent produces implementation code without a corresponding test → DELETE the code, log the violation, respawn the task with stricter instructions.

#### c. Verification

After each subagent completes:
1. Run the verification command from PLAN.md
2. Run the full test suite (per blueprint §build-commands)
3. Task is complete ONLY when:
   - The new test passes
   - All previously passing tests still pass
   - The verification command succeeds

#### d. Code Review

After each task, two-stage review:

**Stage 1 — Spec Compliance:**
- Does the code match what the spec asked for?
- Are CONTEXT.md terms used correctly?
- Does it violate any ADR decisions?

**Stage 2 — Code Quality:**
- Does it follow existing patterns and blueprint conventions?
- Obvious edge cases not handled?
- Unnecessary complexity?

If review fails: fix in place (minor) or flag for human review (design disagreement).

#### e. Board Update (optional)

If the task has subtask checkboxes on the board:
1. **Acquire board lock**
2. Tick the subtask checkbox
3. **Release board lock**

### Step 3: Parallel Execution

Tasks marked parallelizable in PLAN.md can be spawned simultaneously:
- Launch 2-4 subagents in a single message
- Each works on non-overlapping files
- After all complete: run full test suite to catch integration issues
- If integration test fails: fix sequentially, don't re-parallelize

### Step 4: Final Verification

After ALL tasks complete, run build and test commands from the blueprint §build-commands.

Both must succeed. If any fail → diagnose and fix before proceeding.

**Deviation Record Verification:** If PLAN.md includes any "Create Deviation Record" tasks, verify that the corresponding files exist in `docs/deviations/` and follow the `templates/deviation-record.md` format. Missing deviation record files → STOP and report. These are mandatory artifacts.

### Step 5: Commit & Report

1. Ensure all changes are committed on the feature branch
2. Each task should have its own commit with descriptive message
3. Push branch to remote:
   ```bash
   git push -u origin feature/TASK-ID-slug
   ```

4. Produce implementation report:
```markdown
## Implementation Report

### Tasks Completed
| # | Task | Tests Added | Commits | Status |
|---|------|-------------|---------|--------|
| 1 | [title] | 3 | abc1234 | ✅ |
| 2 | [title] | 2 | def5678 | ✅ |

### Test Results
- Total tests: [N] ([M] new)
- All passing: Yes/No
- Build warnings: [count]

### Branch
- Name: feature/TASK-ID-slug
- Commits: [N]
- Files changed: [list]

### Flags
- [Any deviations from plan]
- [Any tasks that required multiple attempts]
- [Any spec ambiguities discovered — these need /grill-spec revisit]
```

## Phase Transition (MANDATORY)

**After all tasks complete and tests are green:**

The next phase depends on the lane: TEST_VERIFY (Lane = full) or VERIFY_FINISH (Lane = fast, ADR-0010).

1. Update `.board/sprint-state.md`:
   - Phase History: `| [now] | [task] | IMPLEMENT | TEST_VERIFY or VERIFY_FINISH | tests-green | [N] tasks, [M] tests |`
2. Update `.board/tasks.md` (with lock):
   - Set Branch field on the task
   - Update Phase field
3. **→ Return control to /sprint** which will invoke /test-verify (full lane) or /verify-finish (fast lane) next.

If invoked standalone:
- Update sprint-state as above
- State: "Implementation complete. [N] tasks done, [M] tests added, all green. Next: invoke /test-verify (or /verify-finish in the fast lane)."

## Input Quality Validation

Before beginning implementation, validate PLAN.md against `.claude/rules/artifact-standards.md` "Artifact 2":

- [ ] PLAN.md exists in working directory
- [ ] Every task has Files, Context, Implementation, Test, and Verify sections
- [ ] File paths are absolute from project root
- [ ] Code snippets include full structural context (not just method bodies)
- [ ] Each task's Test section has a complete failing test skeleton
- [ ] Dependency graph is present and task ordering matches it

If ANY check fails → STOP. Report: "Plan quality below standard: [specific issue]. Return to /plan."

## Output Quality Gate

Before advancing to /test-verify, validate the implementation report against `.claude/rules/artifact-standards.md` "Artifact 3":

- [ ] Branch name and base commit documented
- [ ] Tasks completed table has all columns: Task, Files Changed, Tests Added, Commits, Attempts, Status
- [ ] Files changed table lists EVERY file with Action, Lines, and Purpose
- [ ] Test inventory maps tests to AC numbers
- [ ] AC coverage status shows explicit gaps (not just "covered")
- [ ] Flags section documents any retries, deviations, or deferred items
- [ ] Test results quoted with exact pass/fail/skip counts

## Rules

- **TDD is mandatory.** Code before test = code deleted. No exceptions.
- **One subagent per task.** Fresh context per task prevents accumulated confusion.
- **Two-stage review between tasks.** Spec compliance first, code quality second.
- **Feature branch isolation.** Main branch untouched until /finish.
- **Three-strike escalation.** Task fails 3 times → STOP, set Phase = BLOCKED, escalate to human.
- **No plan deviation.** Changes not in PLAN.md → stop and flag. The plan was approved.
- **Clean commits.** Each task gets its own commit referencing the task number.
- **Board lock for writes.** Any board update follows the lock protocol.
- **Spec ambiguity = STOP.** If implementation reveals ambiguity → halt, document, return to GRILL_SPEC.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.
