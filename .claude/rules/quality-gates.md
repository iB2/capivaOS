# Quality Gates

## Gate Enforcement

Quality gates are checked in Phase 4 (Test & Verify). No task moves to Phase 5 without passing all applicable gates. There are no exceptions for deadlines or convenience.

**Enterprise alignment**: SonarQube is the primary code quality tool (NOT Stryker/mutation testing). StyleCop analyzers enforce code style. Both are mandatory per the enterprise blueprint and SDLC process.

---

## Test Stack (.NET 10)

Single source of truth for all test and analysis packages.

### Test Packages

| Package | Version | Purpose |
|---------|---------|---------|
| xUnit | 2.9+ | Test framework |
| NSubstitute | 5.3+ | Mocking/substitution |
| AwesomeAssertions | latest | Fluent assertions (Apache 2.0, NOT FluentAssertions v8 — commercial license) |
| Bogus | 35.6+ | Test data generation |
| Verify | 31.x | Snapshot testing (response shape validation, complex object comparisons) |
| Testcontainers | 4.12+ | Redis + MsSql integration tests |
| Reqnroll | latest | BDD/Gherkin specs (NOT SpecFlow — EOL Dec 2024) |
| ReportGenerator | latest | TRX to HTML reports |

### Static Analysis (Enterprise Mandatory)

| Tool | Purpose |
|------|---------|
| SonarAnalyzer.CSharp | Code quality + vulnerability detection |
| StyleCop.Analyzers | Code style enforcement |
| SonarQube | CI quality gate (Azure Pipelines) |

---

## Unit Test Coverage

| Scope | Minimum | Target |
|-------|---------|--------|
| Business logic (services, domain) | 80% | 90% |
| Infrastructure (repositories, transports) | 60% | 75% |
| Overall solution | 75% | 85% |

**Measurement**: `dotnet test --collect:"XPlat Code Coverage"` with Coverlet, processed by ReportGenerator.

**Exclusions** (do not count toward coverage):
- Program.cs / Startup.cs / host configuration
- Auto-generated code (EF migrations, gRPC stubs)
- DTOs and record types with no logic
- Azure Functions entry points (test the injected services instead)

---

## Static Analysis (SonarQube + StyleCop)

SonarQube replaces mutation testing as the primary quality analysis tool, aligned with the enterprise CI/CD pipeline.

### SonarQube Requirements

- **All builds** run SonarQube analysis via Azure Pipelines
- **Quality Gate**: SonarQube quality gate must pass (configured server-side)
- **No new code smells** in changed files
- **No new bugs** or vulnerabilities
- **Coverage data** published to SonarQube via cobertura format

### StyleCop Compliance

- `StyleCop.Analyzers` enabled via `Directory.Build.props`
- Zero StyleCop warnings in new code
- Accepted suppressions documented in `enterprise-blueprint.md`
- Any new suppression requires a Deviation Record (`templates/deviation-record.md`)

### SonarQube Coverage Exclusions

Configure per project in `.csproj`:

```xml
<PropertyGroup>
  <SonarQubeExcludeFromCoverage>
    **/Migrations/**,
    **/Program.cs,
    **/*Bootstrapper.cs,
    **/*Extensions.cs
  </SonarQubeExcludeFromCoverage>
</PropertyGroup>
```

---

## Code Review

| Priority | Review Required | Reviewer |
|----------|----------------|----------|
| P0 | Mandatory human review between every micro-task | Human |
| P1 | Mandatory human review after all micro-tasks complete | Human |
| P2 | Automated review (Claude subagent) acceptable | Subagent |
| P3-P4 | Self-review sufficient | Self |

**Review checklist**:
- [ ] Tests cover the acceptance criteria
- [ ] No business logic without corresponding test
- [ ] Error handling is explicit (no swallowed exceptions)
- [ ] Naming follows coding standards
- [ ] No TODO/HACK comments without a linked board task
- [ ] Async/await used correctly (no sync-over-async, no fire-and-forget)
- [ ] Nullable reference types respected (no `!` operator without justification)

---

## Integration Tests

**Required when code touches**:
- SQL (any IRepository implementation) -- use Testcontainers.MsSql
- Redis (any ICacheTransport / IStreamTransport) -- use Testcontainers.Redis
- External HTTP APIs -- use WireMock.Net or similar
- File system -- use System.IO.Abstractions

**Integration test rules**:
- Each test class manages its own container lifecycle
- Tests must be parallelizable (no shared mutable state)
- Cleanup happens in `Dispose`, not in test teardown
- Connection strings come from the container, never from config files
- Timeout: 60 seconds max per integration test

---

## TDD Enforcement

**No code without tests. This is non-negotiable.**

The implementation phase (Phase 3) enforces the TDD cycle:

1. **RED**: Write a test that describes the expected behavior. Run it. It must fail.
2. **GREEN**: Write the minimum code to make the test pass. No more.
3. **REFACTOR**: Clean up the code and the test. Extract, rename, simplify. All tests still green.

**Violations**:
- Writing implementation before the test: revert and start over
- Writing a test that passes immediately: the test is not testing anything useful -- rewrite it
- Skipping refactor: acceptable for trivial changes, but not for anything touching business logic

### TDD Verification Method

TDD compliance is verified through commit structure and QA review:

1. **Commit order**: Each micro-task should produce at least two commits — test commit before implementation commit. The /implement orchestrator verifies this by checking `git log` on the feature branch after each subtask completes.
2. **QA review**: The QA role (Stage 3) checks for TDD evidence — tests that are clearly written to describe behavior, not retrofitted to match existing code (indicators: meaningful test names describing expected behavior, assertions on specific outcomes, not just "doesn't throw").
3. **Orchestrator spot-check**: /implement samples the last 3 commits from each subagent and verifies at least one test file was committed before or alongside each implementation file.

If TDD violation is detected:
- The subagent's code is reverted (`git checkout -- [files]`)
- The task is respawned with an explicit warning
- The violation is logged in sprint-state Notes

---

## Azure Functions Specifics

The .NET isolated worker model for Azure Functions does NOT support in-process test hosts. Do not attempt to spin up a Functions host in tests.

**Instead**:
- Extract all logic into service classes with interfaces
- Test service classes directly via unit tests
- Test the Function class only for correct DI wiring (constructor injection)
- Integration tests target services, not Functions endpoints

---

## Report Artifacts

After Phase 4 completes, the following artifacts must exist:

| Artifact | Location | Format |
|----------|----------|--------|
| Test results | `reports/test-results/` | TRX + HTML (ReportGenerator) |
| Coverage report | `reports/coverage/` | HTML (ReportGenerator) |
| SonarQube report | SonarQube server | Online dashboard |

**CI Integration**:
- TRX files consumed by Azure Pipelines test result publisher
- Coverage published to SonarQube via cobertura format
- SonarQube quality gate status reported on PR
- Coverage HTML reports generated via ReportGenerator

---

## Gate Override

Quality gates can only be overridden by explicit human decision. To override:

1. Document WHY the gate cannot be met (not "it's too hard" -- a real technical reason)
2. Create a follow-up task on the board to close the gap
3. Mark the override in the PR description: `Quality gate override: [gate] -- [reason] -- [follow-up task]`
4. Human must approve the PR knowing about the override

No silent overrides. No "we'll fix it later" without a board task.
