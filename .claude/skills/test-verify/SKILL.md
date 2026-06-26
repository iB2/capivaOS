---
name: test-verify
description: Phase 4 — Integration tests, static analysis, and quality reports with phase guard. Two-agent pattern enforced.
---

# Test & Verify — Phase 4

Generate integration tests beyond what TDD produced, run static analysis, and produce quality reports. Focus on business logic quality, not test volume.

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = TEST_VERIFY
3. Verify a feature branch exists (Branch field in sprint-state is not "--")
4. Run the test command from blueprint §build-commands — all tests must pass (implementation is green)
5. If ANY check fails → **STOP**: "⛔ Phase guard failed. [specific failure]. Complete /implement first."
6. If ALL checks pass → proceed

## Process

### Step 1: Analyze Implementation

1. Read the feature branch changes (`git diff main..HEAD`)
2. Read `docs/specs/TASK-ID-spec.md` for coverage mapping
3. Read PLAN.md for the list of implemented tasks
4. Read the active blueprint's `reference.md` for test conventions (§test-stack) and static analysis tools (§static-analysis)
5. Identify untested paths:
   - Focus on **service classes** and **domain logic**
   - Skip framework wrappers and auto-generated code
   - Map each acceptance criterion to at least one test

### Step 2: Two-Agent Test Generation

Spawn two subagents:

#### Agent 1: Test Writer
- Role: `.claude/agents/roles/dev.md` (with test-writing focus)
- Input: Spec + implementation diff + existing tests + blueprint reference.md
- Produces: New test files following existing patterns and blueprint §test-stack conventions

Test categories to cover:
1. **Integration tests**: Using the test infrastructure specified in blueprint §test-stack
2. **BDD scenarios**: If spec includes Gherkin features (per blueprint §test-stack)
3. **Property-based tests**: For data transformation logic (if supported by the stack)
4. **Edge case tests**: Null inputs, boundary values, concurrent access, timeouts

#### Agent 2: Test Reviewer
- Role: `.claude/agents/roles/qa.md`
- Input: All tests (existing + new from Agent 1) + blueprint reference.md
- Produces: Review with APPROVE or NEEDS IMPROVEMENT verdict

Review criteria:
- Does each AC have at least one test?
- Are assertions meaningful (not just "didn't throw")?
- Are integration tests using real dependencies (not mocks where the blueprint requires real containers)?
- Are there redundant tests that add volume but not quality?

If NEEDS IMPROVEMENT: iterate once. If still not approved after iteration, flag for human.

### Step 3: Test Infrastructure

Follow the test infrastructure setup defined in the blueprint's reference.md §test-stack section. Use the correct:
- Test framework and assertion library
- Container/fixture setup patterns
- Test naming conventions
- Snapshot testing tools (if applicable)

### Step 4: Run Tests

Run the full test suite using the command from blueprint §build-commands.

ALL tests (unit + integration) must pass. If any fail → fix and re-run.

### Step 5: Static Analysis Verification

Run the static analysis tools defined in the blueprint's reference.md §static-analysis section:

1. **Linter/Analyzer**: Run the linting command from §build-commands. Confirm zero new warnings in new/changed files.
2. **Quality Gate Tool** (e.g., SonarQube): If available locally, run analysis per §build-commands. If not available locally, note deferral to CI pipeline.

Analysis exclusions:
- Auto-generated files (migrations, generated code)
- Entry points / bootstrap configuration
- Framework boilerplate

### Step 6: Generate Reports

1. **Coverage report**: Run coverage command from blueprint §build-commands.

2. **Quality report** — write to `docs/reports/TASK-ID-quality.md`:

```markdown
# Quality Report: [Task Title]

## Task Reference
- ID: [TASK-ID]
- Branch: feature/[slug]
- Spec: docs/specs/[TASK-ID]-spec.md
- Blueprint: [active blueprint name]

## Coverage
| Scope | Coverage | Target | Status |
|-------|----------|--------|--------|
| Unit tests | X% | >= 80% | ✅/❌ |
| Integration tests | Y% | -- | -- |
| Combined | Z% | >= 80% | ✅/❌ |

## Static Analysis
| Tool | Status | Details |
|------|--------|---------|
| [Linter per blueprint] | ✅/❌ | [N] warnings in new code |
| [Quality gate per blueprint] | ✅/❌/Deferred to CI | [quality gate status or "CI pipeline"] |
| Code Smells | [N] new | [details] |
| Vulnerabilities | [N] new | [details] |

## Test Inventory
| Category | Count | New |
|----------|-------|-----|
| Unit tests | N | M |
| Integration tests | N | M |
| BDD scenarios | N | M |
| Property-based | N | M |

## Acceptance Criteria Coverage
| AC# | Criterion | Test(s) | Covered? |
|-----|-----------|---------|----------|
| 1 | [criterion] | [test names] | ✅/❌ |

## Static Analysis Issues (attention required)
| File | Issue | Category | Severity | Resolution |
|------|-------|----------|----------|------------|

## Quality Gate Verdict
- **Overall**: PASS / SOFT FAIL / HARD FAIL
- [Details for any failures]

## Report Files
- Coverage HTML: [path per blueprint §build-commands]
- Quality gate: [server URL or "deferred to CI pipeline"]
```

### Step 7: Evaluate Quality Gates

| Metric | Target | Hard Fail |
|--------|--------|-----------|
| Unit coverage | >= 80% | < 60% |
| Linter warnings (new code) | 0 | Any warning |
| Quality gate (if available) | Pass | Fail |
| All integration tests | Pass | Any failure |
| All AC covered | Yes | Any uncovered |

- **PASS**: All targets met → proceed to /finish
- **SOFT FAIL**: Between target and hard fail → flag issues, recommend fixes, present to human
- **HARD FAIL**: Below hard fail → BLOCK /finish, require additional tests, iterate

### Step 8: Present to Human

Present the quality report with:
- Pass/fail verdict per gate (color-coded)
- Static analysis issues sorted by severity
- AC coverage matrix
- Links to HTML reports

```
Quality report written to docs/reports/[TASK-ID]-quality.md

Gate Results:
  Coverage: X% (target: 80%) — ✅ PASS
  Linter: 0 warnings — ✅ PASS
  Quality Gate: Pass (or deferred to CI) — ✅ PASS
  AC coverage: 5/5 — ✅ PASS

Overall: PASS — all gates met.

🧑 Awaiting quality review to proceed to /finish phase.
```

## Phase Transition (MANDATORY)

**After human approves quality report (or accepts soft fail):**

1. Update `.board/sprint-state.md`:
   - Quality Gate: PASS (or ACCEPTED_SOFT_FAIL)
   - Register artifact: `docs/reports/TASK-ID-quality.md`
2. Add Phase History: `| [now] | [task] | TEST_VERIFY | FINISH | quality-[verdict] | coverage X%, [quality gate status] |`
3. Update `.board/tasks.md` (with lock):
   - Set Quality field: `X% / [quality gate pass/fail]`
4. **→ Return control to /sprint** which will invoke /finish next.

If invoked standalone:
- Update sprint-state as above
- State: "Quality gates [PASS/SOFT FAIL]. Next: invoke /finish to create PR and update board."

## Input Quality Validation

Before starting test generation, validate /implement output against `.claude/rules/artifact-standards.md` "Artifact 3":

- [ ] Feature branch exists and is checked out
- [ ] Test suite passes (all green — implementation is complete)
- [ ] Files changed are documented (know what was built to know what to test)
- [ ] AC coverage status shows what TDD covered and what still needs coverage

If tests fail → STOP. Report: "Implementation has failing tests. Return to /implement."

## Output Quality Gate

Before presenting the quality report, validate against `.claude/rules/artifact-standards.md` "Artifact 4: Quality Report":

- [ ] Executive summary is 2-3 sentences with verdict, key findings, and concerns
- [ ] Coverage table has Lines, Branches, Coverage, Target, and Verdict per scope
- [ ] Uncovered lines table explains WHY they're uncovered and their risk level
- [ ] Static analysis table has linter warnings, quality gate status, code smells, vulnerabilities
- [ ] EVERY new static analysis issue is analyzed: category, severity, and resolution (not just counted)
- [ ] Test inventory shows Existing, New, Total, and Notes per category
- [ ] New tests detail table maps EACH test to what behavior it validates and which AC
- [ ] AC coverage matrix has a row for EVERY AC in the spec with test names and verdict
- [ ] Quality gate verdict table has Value, Target, Hard Fail, and Status per gate
- [ ] No "pending" or "--" verdicts — every gate must have a concrete result

If ANY check fails → iterate on the report and/or add more tests before presenting.

## Rules

- **Quality over quantity.** Meaningful assertions, not line coverage padding.
- **Real dependencies where required.** Follow blueprint §test-stack for when to use real containers vs mocks.
- **Two-agent pattern.** Writer and reviewer are separate roles.
- **Every AC needs a test.** Acceptance criteria coverage is a quality gate.
- **Static analysis per blueprint.** Run the tools specified in blueprint §static-analysis.
- **Zero new linter warnings.** No new warnings in changed files.
- **Report is mandatory artifact.** `docs/reports/TASK-ID-quality.md` must exist before /finish.
- **Hard fail blocks progression.** Cannot proceed to /finish with hard fail.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.
- **Static analysis issue analysis is MANDATORY.** Each code smell or issue in new code must be analyzed and addressed or justified.
