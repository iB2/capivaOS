---
name: test-verify
description: Phase 4 — Integration tests, static analysis (SonarQube + StyleCop), and quality reports with phase guard. Two-agent pattern enforced.
---

# Test & Verify — Phase 4

Generate integration tests beyond what TDD produced, run static analysis (SonarQube + StyleCop), and produce quality reports. Focus on business logic quality, not test volume.

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = TEST_VERIFY
3. Verify a feature branch exists (Branch field in sprint-state is not "--")
4. Run `dotnet test` — all tests must pass (implementation is green)
5. If ANY check fails → **STOP**: "⛔ Phase guard failed. [specific failure]. Complete /implement first."
6. If ALL checks pass → proceed

## Process

### Step 1: Analyze Implementation

1. Read the feature branch changes (`git diff main..HEAD`)
2. Read `docs/specs/TASK-ID-spec.md` for coverage mapping
3. Read PLAN.md for the list of implemented tasks
4. Identify untested paths:
   - Focus on **service classes** and **domain logic**
   - Skip Azure Function wrappers (no test host — Issue #968)
   - Skip auto-generated code (migrations, Program.cs)
   - Map each acceptance criterion to at least one test

### Step 2: Two-Agent Test Generation

Spawn two subagents:

#### Agent 1: Test Writer
- Role: `.claude/agents/roles/dev.md` (with test-writing focus)
- Input: Spec + implementation diff + existing tests
- Produces: New test files following existing patterns

Test categories to cover:
1. **Integration tests**: Testcontainers for real Redis/SQL Server
2. **BDD scenarios**: Reqnroll when spec includes Gherkin features
3. **Property-based tests**: FsCheck for data transformation logic
4. **Edge case tests**: Null inputs, boundary values, concurrent access, timeouts

#### Agent 2: Test Reviewer
- Role: `.claude/agents/roles/qa.md`
- Input: All tests (existing + new from Agent 1)
- Produces: Review with APPROVE or NEEDS IMPROVEMENT verdict

Review criteria:
- Does each AC have at least one test?
- Are assertions meaningful (not just "didn't throw")?
- Are integration tests using real containers (not mocks)?
- Are there redundant tests that add volume but not quality?

If NEEDS IMPROVEMENT: iterate once. If still not approved after iteration, flag for human.

### Step 3: Test Infrastructure

**Testcontainers setup** (required for integration tests):
```csharp
public class IntegrationTests : IAsyncLifetime
{
    private readonly MsSqlContainer _db = new MsSqlBuilder().Build();
    private readonly RedisContainer _redis = new RedisBuilder().Build();

    public async Task InitializeAsync()
    {
        await _db.StartAsync();
        await _redis.StartAsync();
    }

    public async Task DisposeAsync()
    {
        await _db.DisposeAsync();
        await _redis.DisposeAsync();
    }
}
```

**CRITICAL**: Use `IAsyncLifetime`, NOT constructor injection (causes hangs).

**Assertions**: AwesomeAssertions (NOT FluentAssertions v8 — commercial $130/dev/yr)
**Snapshots**: Verify for response shape validation

### Step 4: Run Tests

```bash
dotnet test --logger trx --results-directory TestResults/
```

ALL tests (unit + integration) must pass. If any fail → fix and re-run.

### Step 5: Static Analysis Verification

Verify SonarQube and StyleCop compliance:

1. **StyleCop**: Confirm zero warnings in new/changed files:
   ```bash
   dotnet build --no-incremental 2>&1 | grep -i "warning SA\|warning S\|warning CA"
   ```

2. **SonarQube**: If SonarQube CLI is available locally, run analysis:
   ```bash
   dotnet sonarscanner begin /k:"[project-key]" /d:sonar.cs.opencover.reportsPaths="**/coverage.opencover.xml"
   dotnet build --no-incremental
   dotnet test --collect:"XPlat Code Coverage" -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=opencover
   dotnet sonarscanner end
   ```

3. If SonarQube is NOT available locally, note in the quality report that SonarQube analysis will run in the CI pipeline (Azure Pipelines).

Analysis exclusions:
- `Migrations/*`
- `Program.cs`
- `*Bootstrapper.cs`
- Auto-generated files
- Azure Function entry points

### Step 6: Generate Reports

1. **Coverage report**:
   ```bash
   dotnet test --collect:"XPlat Code Coverage"
   reportgenerator -reports:TestResults/**/coverage.cobertura.xml -targetdir:TestResults/CoverageReport -reporttypes:Html
   ```

2. **Quality report** — write to `docs/reports/TASK-ID-quality.md`:

```markdown
# Quality Report: [Task Title]

## Task Reference
- ID: [TASK-ID]
- Branch: feature/[slug]
- Spec: docs/specs/[TASK-ID]-spec.md

## Coverage
| Scope | Coverage | Target | Status |
|-------|----------|--------|--------|
| Unit tests | X% | >= 80% | ✅/❌ |
| Integration tests | Y% | -- | -- |
| Combined | Z% | >= 80% | ✅/❌ |

## Static Analysis
| Tool | Status | Details |
|------|--------|---------|
| StyleCop | ✅/❌ | [N] warnings in new code |
| SonarQube | ✅/❌/Deferred to CI | [quality gate status or "CI pipeline"] |
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

## SonarQube Issues (attention required)
| File | Issue | Category | Severity | Resolution |
|------|-------|----------|----------|------------|

## Quality Gate Verdict
- **Overall**: PASS / SOFT FAIL / HARD FAIL
- [Details for any failures]

## Report Files
- Coverage HTML: TestResults/CoverageReport/index.html
- SonarQube: [server URL or "deferred to CI pipeline"]
```

### Step 7: Evaluate Quality Gates

| Metric | Target | Hard Fail |
|--------|--------|-----------|
| Unit coverage | >= 80% | < 60% |
| StyleCop warnings (new code) | 0 | Any warning |
| SonarQube quality gate | Pass | Fail (if available) |
| All integration tests | Pass | Any failure |
| All AC covered | Yes | Any uncovered |

- **PASS**: All targets met → proceed to /finish
- **SOFT FAIL**: Between target and hard fail → flag SonarQube issues, recommend fixes, present to human
- **HARD FAIL**: Below hard fail → BLOCK /finish, require additional tests, iterate

### Step 8: Present to Human

Present the quality report with:
- Pass/fail verdict per gate (color-coded)
- SonarQube issues sorted by severity
- AC coverage matrix
- Links to HTML reports

```
Quality report written to docs/reports/[TASK-ID]-quality.md

Gate Results:
  Coverage: X% (target: 80%) — ✅ PASS
  StyleCop: 0 warnings — ✅ PASS
  SonarQube: Pass (or deferred to CI) — ✅ PASS
  AC coverage: 5/5 — ✅ PASS

Overall: PASS — all gates met, SonarQube clean.

🧑 Awaiting quality review to proceed to /finish phase.
```

## Phase Transition (MANDATORY)

**After human approves quality report (or accepts soft fail):**

1. Update `.board/sprint-state.md`:
   - Quality Gate: PASS (or ACCEPTED_SOFT_FAIL)
   - Register artifact: `docs/reports/TASK-ID-quality.md`
2. Add Phase History: `| [now] | [task] | TEST_VERIFY | FINISH | quality-[verdict] | coverage X%, SonarQube [status] |`
3. Update `.board/tasks.md` (with lock):
   - Set Quality field: `X% / SonarQube [pass/fail]`
4. **→ Return control to /sprint** which will invoke /finish next.

If invoked standalone:
- Update sprint-state as above
- State: "Quality gates [PASS/SOFT FAIL]. Next: invoke /finish to create PR and update board."

## Input Quality Validation

Before starting test generation, validate /implement output against `.claude/rules/artifact-standards.md` "Artifact 3":

- [ ] Feature branch exists and is checked out
- [ ] `dotnet test` passes (all green — implementation is complete)
- [ ] Files changed are documented (know what was built to know what to test)
- [ ] AC coverage status shows what TDD covered and what still needs coverage

If `dotnet test` fails → STOP. Report: "Implementation has failing tests. Return to /implement."

## Output Quality Gate

Before presenting the quality report, validate against `.claude/rules/artifact-standards.md` "Artifact 4: Quality Report":

- [ ] Executive summary is 2-3 sentences with verdict, key findings, and concerns
- [ ] Coverage table has Lines, Branches, Coverage, Target, and Verdict per scope
- [ ] Uncovered lines table explains WHY they're uncovered and their risk level
- [ ] Static analysis table has StyleCop warnings, SonarQube status, code smells, vulnerabilities
- [ ] EVERY new SonarQube issue is analyzed: category, severity, and resolution (not just counted)
- [ ] Test inventory shows Existing, New, Total, and Notes per category
- [ ] New tests detail table maps EACH test to what behavior it validates and which AC
- [ ] AC coverage matrix has a row for EVERY AC in the spec with test names and verdict
- [ ] Quality gate verdict table has Value, Target, Hard Fail, and Status per gate
- [ ] No "pending" or "--" verdicts — every gate must have a concrete result

If ANY check fails → iterate on the report and/or add more tests before presenting.

## Rules

- **Quality over quantity.** Meaningful assertions, not line coverage padding.
- **Real containers only.** No mocks for databases or caches. Testcontainers.
- **IAsyncLifetime for containers.** Constructor setup causes hangs.
- **AwesomeAssertions, not FluentAssertions v8.** License issue.
- **Service classes, not function wrappers.** Isolated worker has no test host.
- **Two-agent pattern.** Writer and reviewer are separate roles.
- **Every AC needs a test.** Acceptance criteria coverage is a quality gate.
- **SonarQube analysis.** Run locally if available, otherwise note deferral to CI pipeline.
- **StyleCop zero warnings.** No new StyleCop warnings in changed files.
- **Report is mandatory artifact.** `docs/reports/TASK-ID-quality.md` must exist before /finish.
- **Hard fail blocks progression.** Cannot proceed to /finish with hard fail.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.
- **SonarQube issue analysis is MANDATORY.** Each code smell or issue in new code must be analyzed and addressed or justified.
