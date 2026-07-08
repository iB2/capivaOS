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
4. Verify `docs/specs/TASK-ID-acs.json` exists and parses (the verification contract — see ADR-0009)
5. Run the test command from blueprint §build-commands — all tests must pass (implementation is green)
6. If ANY check fails → **STOP**: "⛔ Phase guard failed. [specific failure]. Complete /capiva:implement first."
7. If ALL checks pass → proceed

## Process

### Step 1: Analyze Implementation

1. Read the feature branch changes (`git diff main..HEAD`)
2. Read `docs/specs/TASK-ID-spec.md` for coverage mapping
3. Read `docs/specs/TASK-ID-acs.json` — this is THE list of criteria to verify. Do not re-derive ACs from the spec prose or from memory; the JSON is the contract.
4. Read PLAN.md for the list of implemented tasks
5. Read the active blueprint's `reference.md` for test conventions (§test-stack) and static analysis tools (§static-analysis)
6. Identify untested paths:
   - Focus on **service classes** and **domain logic**
   - Skip framework wrappers and auto-generated code
   - Map each acceptance criterion to at least one test

### Step 2: Two-Agent Test Generation

Spawn two subagents:

#### Agent 1: Test Writer
- Agent: **dev** (native definition `${CLAUDE_PLUGIN_ROOT}/agents/dev.md`, spawned by type — platform-enforced tool allowlist), with test-writing focus
- Input: Spec + implementation diff + existing tests + blueprint reference.md
- Produces: New test files following existing patterns and blueprint §test-stack conventions

Test categories to cover:
1. **Integration tests**: Using the test infrastructure specified in blueprint §test-stack
2. **BDD scenarios**: If spec includes Gherkin features (per blueprint §test-stack)
3. **Property-based tests**: For data transformation logic (if supported by the stack)
4. **Edge case tests**: Null inputs, boundary values, concurrent access, timeouts

#### Agent 2: Adversarial Reviewer
- Agent: **qa** (native definition `${CLAUDE_PLUGIN_ROOT}/agents/qa.md`, spawned by type — READ-ONLY tool allowlist: the reviewer mechanically cannot modify what it reviews)
- Input: The implementation report's CLAIMS + all tests (existing + new from Agent 1) + the diff + `docs/specs/TASK-ID-acs.json` + blueprint reference.md
- Produces: Review with CLAIMS VERIFIED or REFUTED verdict

**Framing is adversarial, not confirmatory.** The reviewer's prompt must state:
"The implementation report below is a set of CLAIMS made by the agent that wrote
the code. Your job is to REFUTE them. For each claim (task complete, AC covered,
tests meaningful), actively look for the counterexample: the AC with no real
assertion behind it, the test that passes vacuously, the error path the report
says is handled but isn't. A review that finds nothing must show what it tried
and failed to refute — not just agree."

Refutation targets (minimum set):
- For each AC in `TASK-ID-acs.json`: is there a test that would FAIL if the behavior were broken? (Delete-the-code thought experiment)
- Are assertions meaningful (not just "didn't throw" / "is not null")?
- Are integration tests using real dependencies (not mocks where the blueprint requires real containers)?
- Do any implementation-report claims (files changed, tests added, ACs covered) contradict the actual diff?

If any claim is REFUTED: iterate once (fix code/tests, re-review). If claims remain refuted after iteration, flag for human.

#### Agent 3: Second Independent Reviewer (optional — Dual Review)

Only when `- **Dual Review**: on` in `.board/harness-config.md` (absent/off =
skip this agent entirely; attended behavior unchanged). A second qa-role agent
reviews the same claims INDEPENDENTLY (no sight of Agent 2's findings). Then:
- **Deduplicate** findings by file + issue key (same issue within ±5 lines = one
  finding), preserving both reviewers' attribution
- **Normalize severity** to P0/P1/P2/Nit before the quality report
- **Disagreement is a signal**: if the reviewers disagree on a finding's
  validity, or on any severity ≥ P1 — in auto mode this forces ESCALATE at the
  quality gate regardless of policy grants; in attended mode, present the
  disagreement explicitly to the human.

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
2. **Quality Gate Tool** (per blueprint §static-analysis): If available locally, run analysis per §build-commands. If not available locally, note deferral to CI pipeline.

Analysis exclusions:
- Auto-generated files (migrations, generated code)
- Entry points / bootstrap configuration
- Framework boilerplate

### Step 5b: End-to-End Feature Exercise (MANDATORY)

Tests verify components. This step verifies the FEATURE — by driving the built
system the way its caller will, using the blueprint's tooling (§build-commands /
§test-stack). The quality report CANNOT say PASS without evidence from this step.

1. **Start the system** the way the blueprint runs it (dev server, function host, CLI binary).
2. **Exercise each AC end-to-end** from `docs/specs/TASK-ID-acs.json`:
   - API feature → call the real endpoint (curl/httpie/REST client) with the spec's inputs; capture status code + response body
   - UI feature → drive the running UI (per blueprint tooling); capture the observed behavior
   - Job/CLI feature → trigger the job or run the command; capture output and side effects (DB rows, events, logs)
3. **Record evidence per AC**: the exact command/action, the observed output, and whether it matches the AC's THEN clause.
4. **Update `docs/specs/TASK-ID-acs.json`**: set each AC's `status` to `pass` or
   `fail` based on BOTH its test coverage AND its end-to-end result. This is the
   ONLY edit allowed to that file — never touch `id` or `text`.
5. Any `fail` → fix and re-exercise before proceeding. If the failure reveals a
   spec ambiguity → STOP, follow the spec-ambiguity protocol (return to GRILL_SPEC).

If the feature genuinely cannot be exercised end-to-end in the dev environment
(e.g., requires a third-party system with no sandbox), document WHY in the quality
report's End-to-End Exercise section, exercise the closest reachable boundary
(e.g., the outermost mockable seam), and flag the gap explicitly for the human
quality review. Silence is not an option.

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

## End-to-End Exercise
[Evidence from Step 5b — one entry per AC. Command/action, observed output, verdict.
If any AC could not be exercised end-to-end: WHY, what boundary was exercised instead,
and an explicit flag for the human review.]

| AC | How Exercised | Observed | Verdict |
|----|--------------|----------|---------|
| AC1 | `curl -X POST /api/v1/quotes -d @quote.json` | 201, body matches QuoteResponse schema | ✅ pass |

## Acceptance Criteria Coverage

[GENERATED from `docs/specs/TASK-ID-acs.json` — do not hand-write this table.
For each entry in the JSON: emit id, text, mapped tests, e2e evidence, and the
status now recorded in the file. Row count MUST equal the JSON entry count.]

| AC | Criterion (from acs.json) | Test(s) | E2E | Status |
|----|---------------------------|---------|-----|--------|
| AC1 | [text field, verbatim] | [test names] | ✅ | pass |

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
| All ACs `pass` in acs.json | Yes | Any `pending` or `fail` |
| End-to-end exercise evidence | Every AC | Missing section or unflagged gap |

- **PASS**: All targets met → proceed to /capiva:finish
- **SOFT FAIL**: Between target and hard fail → flag issues, recommend fixes, present to human
- **HARD FAIL**: Below hard fail → BLOCK /capiva:finish, require additional tests, iterate

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
  AC statuses (acs.json): 5/5 pass — ✅ PASS
  End-to-end exercise: 5/5 ACs exercised — ✅ PASS

Overall: PASS — all gates met.

🧑 Awaiting quality review to proceed to /capiva:finish phase.
```

## Phase Transition (MANDATORY)

**After human approves quality report (or accepts soft fail):**

1. Update `.board/sprint-state.md`:
   - Quality Gate: PASS (or ACCEPTED_SOFT_FAIL)
   - Register artifact: `docs/reports/TASK-ID-quality.md`
2. Add Phase History: `| [now] | [task] | TEST_VERIFY | FINISH | quality-[verdict] | coverage X%, [quality gate status] |`
3. Update `.board/tasks.md` (with lock):
   - Set Quality field: `X% / [quality gate pass/fail]`
4. **→ Return control to /capiva:sprint** which will invoke /capiva:finish next.

If invoked standalone:
- Update sprint-state as above
- State: "Quality gates [PASS/SOFT FAIL]. Next: invoke /capiva:finish to create PR and update board."

## Input Quality Validation

Before starting test generation, validate /capiva:implement output against `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md` "Artifact 3":

- [ ] Feature branch exists and is checked out
- [ ] Test suite passes (all green — implementation is complete)
- [ ] Files changed are documented (know what was built to know what to test)
- [ ] AC coverage status shows what TDD covered and what still needs coverage

If tests fail → STOP. Report: "Implementation has failing tests. Return to /capiva:implement."

## Output Quality Gate

Before presenting the quality report, validate against `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md` "Artifact 4: Quality Report":

- [ ] Executive summary is 2-3 sentences with verdict, key findings, and concerns
- [ ] Coverage table has Lines, Branches, Coverage, Target, and Verdict per scope
- [ ] Uncovered lines table explains WHY they're uncovered and their risk level
- [ ] Static analysis table has linter warnings, quality gate status, code smells, vulnerabilities
- [ ] EVERY new static analysis issue is analyzed: category, severity, and resolution (not just counted)
- [ ] Test inventory shows Existing, New, Total, and Notes per category
- [ ] New tests detail table maps EACH test to what behavior it validates and which AC
- [ ] AC coverage matrix is GENERATED from `docs/specs/TASK-ID-acs.json` — row count equals JSON entry count, criterion text is verbatim from the `text` field
- [ ] `docs/specs/TASK-ID-acs.json` statuses updated (`pass`/`fail`) — no entry left `pending`; `id`/`text` untouched
- [ ] End-to-End Exercise section has evidence (command + observed output) for every AC, or an explicit flagged justification for any gap
- [ ] Quality gate verdict table has Value, Target, Hard Fail, and Status per gate
- [ ] No "pending" or "--" verdicts — every gate must have a concrete result

If ANY check fails → iterate on the report and/or add more tests before presenting.

## Rules

- **Quality over quantity.** Meaningful assertions, not line coverage padding.
- **Real dependencies where required.** Follow blueprint §test-stack for when to use real containers vs mocks.
- **Two-agent pattern.** Writer and reviewer are separate roles — and the reviewer's job is to REFUTE, not confirm.
- **Every AC needs a test AND an end-to-end exercise.** `acs.json` status flips to `pass` only when both hold.
- **acs.json is immutable except status.** Never edit `id` or `text`, never add or remove entries. Scope changes go back through /capiva:grill-spec.
- **Verify by driving the system.** "Tests pass" is not "the feature works" — Step 5b is not optional.
- **Static analysis per blueprint.** Run the tools specified in blueprint §static-analysis.
- **Zero new linter warnings.** No new warnings in changed files.
- **Report is mandatory artifact.** `docs/reports/TASK-ID-quality.md` must exist before /capiva:finish.
- **Hard fail blocks progression.** Cannot proceed to /capiva:finish with hard fail.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.
- **Static analysis issue analysis is MANDATORY.** Each code smell or issue in new code must be analyzed and addressed or justified.

---

## Gold Standard (moved from artifact-standards.md, ADR-0011)

The normative template and quality bar for this skill's artifact — the FLOOR, not the ceiling. `artifact-standards.md` keeps the anti-slop rules and validation checklists; the worked examples live here so they load only when this phase runs.

### Artifact 4: Quality Report — Required Sections
```markdown
# Quality Report: [Task Title]

## Task Reference
- ID: [TASK-ID]
- Branch: `feature/TASK-ID-slug`
- Spec: `docs/specs/TASK-ID-spec.md`
- Plan: `PLAN.md` ([N] tasks, [M] commits)

## Executive Summary

[2-3 sentences: overall quality verdict, key findings, any concerns.
This is what the human reads first to decide if they need to dig deeper.]

Example: "All quality gates pass. Coverage at 87% across business logic.
SonarQube clean — zero new code smells, zero vulnerabilities. StyleCop zero warnings.
One uncovered catch block in QuoteRepository (connection disposed during shutdown) —
low risk, defensive code."

## Coverage

| Scope | Lines | Branches | Coverage | Target | Verdict |
|-------|-------|----------|----------|--------|---------|
| Business logic (`Application/`) | 142/158 | 38/44 | 89.9% | >= 80% | ✅ PASS |
| Infrastructure (`Infrastructure/`) | 67/87 | 18/24 | 77.0% | >= 60% | ✅ PASS |
| Domain (`Domain/`) | 23/23 | 6/6 | 100% | >= 80% | ✅ PASS |
| **Combined** | **232/268** | **62/74** | **86.6%** | **>= 80%** | **✅ PASS** |

### Uncovered Lines (notable)

[Don't list every uncovered line — list the ones that MATTER.
Why are they uncovered? Should they be covered? Or are they legitimately excluded?]

| File | Lines | Reason | Risk |
|------|-------|--------|------|
| `QuoteRepository.cs` | 78-82 | Catch block for connection disposed during shutdown | Low — defensive code, not business logic |
| `QuoteOrchestrationService.cs` | 134-138 | Circuit breaker tripped path | Medium — consider adding targeted test |

## Static Analysis

| Tool | Status | New Issues | Details |
|------|--------|-----------|---------|
| StyleCop | ✅ 0 warnings | 0 | All new code compliant |
| SonarQube | ✅ Quality Gate Pass | 0 code smells, 0 vulnerabilities | [server URL or "deferred to CI pipeline"] |

### Quality Gate Issue Analysis

[If any issues found, each must be analyzed — not just counted.
Explain the issue, its impact, and the resolution or justification.]

| # | File | Issue | Category | Severity | Resolution |
|---|------|-------|----------|----------|------------|
| — | — | No new issues | — | — | — |

## Test Inventory

| Category | Existing | New | Total | Notes |
|----------|----------|-----|-------|-------|
| Unit tests | 0 | 8 | 8 | QuoteStatus, QuoteOrchestration |
| Integration tests | 0 | 6 | 6 | QuoteRepository (Testcontainers.MsSql) |
| BDD scenarios | 0 | 0 | 0 | Not applicable — no Gherkin in spec |
| Property-based | 0 | 1 | 1 | Quote ID generation uniqueness (FsCheck) |
| **Total** | **0** | **15** | **15** | |

### New Tests Detail

[Each test with what it validates — not just names, but WHAT BEHAVIOR they prove.]

| Test | Type | Validates | AC# |
|------|------|-----------|-----|
| `QuoteStatusTests.QuoteStatus_Should_Include_Expired_Value` | Unit | Enum has Expired value | — |
| `QuoteOrchestrationTests.RunSweep_ExpiresQuotesOlderThanThreshold` | Unit | AC 1: expiration logic |  1 |
| `QuoteOrchestrationTests.RunSweep_WritesQuoteEventOnExpiration` | Unit | AC 1: event logging | 1 |
| `QuoteOrchestrationTests.RunSweep_IncrementsMetricOnExpiration` | Unit | AC 1: metric emission | 1 |
| `QuoteOrchestrationTests.GetActiveQuote_ReturnsNull_WhenExpired` | Unit | AC 2: expired not returned | 2 |
| `QuoteOrchestrationTests.RunSweep_RetriesOnce_OnSqlTimeout` | Unit | AC 3: timeout retry | 3 |
| `QuoteOrchestrationTests.RunSweep_SkipsBatch_OnDoubleTimeout` | Unit | AC 3: skip after retry fail | 3 |
| `QuoteOrchestrationTests.RunSweep_DoesNotExpire_OnFailedBatch` | Unit | AC 3: no partial update | 3 |
| `QuoteRepositoryTests.GetExpiredQuotes_ReturnsOnlyActive_OlderThan` | Integration | SQL query correctness | 1 |
| `QuoteRepositoryTests.MarkAsExpired_UpdatesStatus_AndTimestamp` | Integration | SQL update correctness | 1 |
| `QuoteRepositoryTests.GetActiveQuote_ExcludesExpired` | Integration | SQL filter correctness | 2 |
| `QuoteRepositoryTests.GetExpiredQuotes_RespectssBatchSize` | Integration | Batch limiting works | 1 |
| `QuoteRepositoryTests.MarkAsExpired_IsIdempotent` | Integration | Double-expire doesn't error | — |
| `QuoteRepositoryTests.GetActiveQuote_ReturnsNull_WhenNotFound` | Integration | Null handling | 2 |
| `QuoteIdGenerationTests.Generated_Ids_Are_Unique_Across_1000` | Property | ID uniqueness guarantee | — |

## Acceptance Criteria Coverage Matrix

[THE most important table in this report. GENERATED from `docs/specs/TASK-ID-acs.json`
— never hand-maintained. One row per JSON entry, criterion text verbatim from the
`text` field, status from the `status` field. Row count MUST equal the JSON entry
count. If an AC has no test or no end-to-end evidence → its status stays `fail`
and the quality gate FAILS.]

| AC# | Criterion | Tests | Verdict |
|-----|-----------|-------|---------|
| 1 | Quote expiration sweep updates status + writes QUOTE_EVENT + increments metric | `RunSweep_ExpiresQuotesOlderThanThreshold`, `RunSweep_WritesQuoteEventOnExpiration`, `RunSweep_IncrementsMetricOnExpiration`, `GetExpiredQuotes_ReturnsOnlyActive_OlderThan`, `MarkAsExpired_UpdatesStatus_AndTimestamp` | ✅ 5 tests |
| 2 | Expired quotes not returned by GetActiveQuote | `GetActiveQuote_ReturnsNull_WhenExpired`, `GetActiveQuote_ExcludesExpired`, `GetActiveQuote_ReturnsNull_WhenNotFound` | ✅ 3 tests |
| 3 | SQL timeout retry + skip + no partial update | `RunSweep_RetriesOnce_OnSqlTimeout`, `RunSweep_SkipsBatch_OnDoubleTimeout`, `RunSweep_DoesNotExpire_OnFailedBatch` | ✅ 3 tests |

## Quality Gate Verdict

| Gate | Value | Target | Hard Fail | Status |
|------|-------|--------|-----------|--------|
| Unit coverage | 86.6% | >= 80% | < 60% | ✅ PASS |
| StyleCop warnings | 0 | 0 | Any warning | ✅ PASS |
| SonarQube quality gate | Pass | Pass | Fail | ✅ PASS |
| Integration tests | 6/6 pass | All pass | Any failure | ✅ PASS |
| AC coverage | 3/3 covered | All covered | Any uncovered | ✅ PASS |
| **Overall** | | | | **✅ PASS** |

## Report Files
- Coverage HTML: `TestResults/CoverageReport/index.html`
- SonarQube: [server URL or "deferred to CI pipeline"]
- TRX results: `TestResults/*.trx`
```

---

