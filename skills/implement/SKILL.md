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
   - If NO and Lane = fast with PLAN.md noting "fast lane: tech context inline" → proceed (fast lane embeds tech findings in PLAN.md; see /capiva:spec-plan)
   - If NO otherwise → check sprint-state Notes for "domain-only" flag. If flagged, proceed. If NOT flagged → **WARN**: "Tech context missing. Consider running /capiva:plan Step 1.5 (Context7 discovery) to avoid using stale API docs."
6. If ANY check fails → **STOP**: "⛔ Phase guard failed. [specific failure]. Complete /capiva:plan first."
7. If ALL checks pass → proceed

## Process

### Step 1: Setup

1. Read `PLAN.md` for the complete task list
2. Read `docs/CONTEXT.md` for domain terms
3. Read `docs/specs/TASK-ID-spec.md` for acceptance criteria reference
4. Read `docs/tech-context/TASK-ID-tech.md` for current library documentation (produced by /capiva:plan)
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

Launch a **dev** subagent (native agent definition `${CLAUDE_PLUGIN_ROOT}/agents/dev.md` — spawn by
agent type so the platform enforces its tool allowlist; do NOT paste the role file
into the prompt) with:
- The task description from PLAN.md (verbatim)
- `docs/CONTEXT.md` domain terms
- `docs/tech-context/TASK-ID-tech.md` current library docs (relevant sections for this task's libraries)
- The active blueprint's `reference.md`
- Feature branch name
- Instruction: **write the failing test FIRST**
- Instruction: **use API patterns from the tech context file, not training data**
- Instruction: **do NOT modify any other files besides those listed in the task**

Each subagent gets fresh context — no bleed from previous tasks.

#### a2. Collect & Validate the Structured Report (ADR-0012)

Every dev subagent ends with one fenced JSON completion report (schema in
`${CLAUDE_PLUGIN_ROOT}/agents/dev.md`). On completion:

1. Extract the JSON block; validate it: `python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_impl_report.py report.json`
2. Missing or invalid → respawn ONCE asking for the report only (no code changes). Still invalid → the attempt counts as a failure (three-strike rule).
3. Cross-check claims mechanically:
   - `files_changed` vs `git diff --name-status` for the task's commits — any mismatch is a REFUTED claim: fix the report or the code
   - `test_results` vs your own run of the suite (Step c) — counts must match
   - `tests_added[].acs` ids must exist in `docs/specs/TASK-ID-acs.json`
4. Aggregate the validated JSONs — the Implementation Report (Step 5) is GENERATED from them, not re-written from memory.

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

**Deviation Record Verification:** If PLAN.md includes any "Create Deviation Record" tasks, verify that the corresponding files exist in `docs/deviations/` and follow the `${CLAUDE_PLUGIN_ROOT}/project-template/templates/deviation-record.md` format. Missing deviation record files → STOP and report. These are mandatory artifacts.

### Step 5: Commit & Report

1. Ensure all changes are committed on the feature branch
2. Each task should have its own commit with descriptive message
3. Push branch to remote:
   ```bash
   git push -u origin feature/TASK-ID-slug
   ```

4. Produce implementation report — GENERATED from the validated per-task JSON reports (Step a2), not hand-written:
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
- [Any spec ambiguities discovered — these need /capiva:grill-spec revisit]
```

## Phase Transition (MANDATORY)

**After all tasks complete and tests are green:**

The next phase depends on the lane: TEST_VERIFY (Lane = full) or VERIFY_FINISH (Lane = fast, ADR-0010).

1. Update `.board/sprint-state.md`:
   - Phase History: `| [now] | [task] | IMPLEMENT | TEST_VERIFY or VERIFY_FINISH | tests-green | [N] tasks, [M] tests |`
2. Update `.board/tasks.md` (with lock):
   - Set Branch field on the task
   - Update Phase field
3. **→ Return control to /capiva:sprint** which will invoke /capiva:test-verify (full lane) or /capiva:verify-finish (fast lane) next.

If invoked standalone:
- Update sprint-state as above
- State: "Implementation complete. [N] tasks done, [M] tests added, all green. Next: invoke /capiva:test-verify (or /capiva:verify-finish in the fast lane)."

## Input Quality Validation

Before beginning implementation, validate PLAN.md against `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md` "Artifact 2":

- [ ] PLAN.md exists in working directory
- [ ] Every task has Files, Context, Implementation, Test, and Verify sections
- [ ] File paths are absolute from project root
- [ ] Code snippets include full structural context (not just method bodies)
- [ ] Each task's Test section has a complete failing test skeleton
- [ ] Dependency graph is present and task ordering matches it

If ANY check fails → STOP. Report: "Plan quality below standard: [specific issue]. Return to /capiva:plan."

## Output Quality Gate

Before advancing to /capiva:test-verify, validate the implementation report against `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md` "Artifact 3":

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
- **Feature branch isolation.** Main branch untouched until /capiva:finish.
- **Three-strike escalation.** Task fails 3 times → STOP, set Phase = BLOCKED, escalate to human.
- **No plan deviation.** Changes not in PLAN.md → stop and flag. The plan was approved.
- **Clean commits.** Each task gets its own commit referencing the task number.
- **Board lock for writes.** Any board update follows the lock protocol.
- **Spec ambiguity = STOP.** If implementation reveals ambiguity → halt, document, return to GRILL_SPEC.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.

---

## Gold Standard (moved from artifact-standards.md, ADR-0011)

The normative template and quality bar for this skill's artifact — the FLOOR, not the ceiling. `artifact-standards.md` keeps the anti-slop rules and validation checklists; the worked examples live here so they load only when this phase runs.

### Artifact 3: Implementation Report — Required Content
```markdown
## Implementation Report: [Task Title]

### Branch
- Name: `feature/TASK-ID-slug`
- Base: `main` at commit [hash]
- Commits: [N]

### Tasks Completed

| # | Task Title | Files Changed | Tests Added | Commits | Attempts | Status |
|---|-----------|---------------|-------------|---------|----------|--------|
| 1 | IQuoteRepository interface | IQuoteRepository.cs, Quote.cs | QuoteStatusTests (1) | abc1234 | 1 | ✅ |
| 2 | QuoteRepository SQL impl | QuoteRepository.cs | QuoteRepositoryTests (4) | def5678 | 1 | ✅ |
| 3 | QuoteOrchestrationService | QuoteOrchestrationService.cs | QuoteOrchestrationTests (6) | ghi9012 | 2 | ✅ (retry: NSubstitute setup issue) |

### Files Changed (complete list)

| File | Action | Lines | Purpose |
|------|--------|-------|---------|
| `src/Domain/Interfaces/IQuoteRepository.cs` | CREATE | 15 | Repository interface for quote operations |
| `src/Domain/Models/Quote.cs` | MODIFY | +3 | Added QuoteStatus.Expired enum value |
| `src/Infrastructure/Repositories/QuoteRepository.cs` | CREATE | 87 | SQL Server implementation of IQuoteRepository |
| `src/Application/Services/QuoteOrchestrationService.cs` | CREATE | 142 | Quote lifecycle orchestration |
| `tests/Domain/QuoteStatusTests.cs` | CREATE | 12 | Enum validation |
| `tests/Infrastructure/QuoteRepositoryTests.cs` | CREATE | 98 | Repository integration tests (Testcontainers.MsSql) |
| `tests/Application/QuoteOrchestrationTests.cs` | CREATE | 156 | Service unit tests with NSubstitute mocks |

### Test Inventory (from TDD)

| Test Class | Tests | Type | AC Coverage |
|-----------|-------|------|-------------|
| QuoteStatusTests | 1 | Unit | AC none (infrastructure) |
| QuoteRepositoryTests | 4 | Integration | AC 1 (get active), AC 2 (expiration sweep) |
| QuoteOrchestrationTests | 6 | Unit | AC 1, AC 2, AC 3 (partial — no SQL timeout test) |

### AC Coverage Status (pre-verification)

| AC# | Description | Covered By TDD? | Gaps |
|-----|-------------|-----------------|------|
| 1 | Quote expiration sweep updates status + event | ✅ Partial | Missing: metric increment assertion |
| 2 | Expired quotes not returned by GetActiveQuote | ✅ Full | — |
| 3 | SQL timeout retry + skip behavior | ❌ Not covered | Needs integration test with simulated timeout |

### Flags & Deviations
- Task 3 required 2 attempts (first subagent misconfigured NSubstitute returns)
- No deviations from PLAN.md
- AC 3 (timeout handling) partially deferred to /capiva:test-verify — requires Testcontainers with fault injection

### Test Results
```
dotnet test — 11 passed, 0 failed, 0 skipped
Build: 0 warnings
```
```

---

