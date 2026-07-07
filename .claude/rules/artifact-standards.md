# Artifact Standards — Gold Standard Output for Every Phase

> Every phase produces artifacts that gate the next phase. Poor output at Phase 1
> cascades into poor code at Phase 3 and meaningless tests at Phase 4.
> This file defines the MINIMUM quality bar for every artifact.
> The examples here are the FLOOR, not the ceiling. Produce richer output when the task warrants it.

## Anti-Slop Rules (Apply to ALL Artifacts)

1. **No placeholder content.** Every section must contain real, specific information. "[TBD]", "[TODO]", "as discussed", "various", "etc." are NEVER acceptable.
2. **No single-sentence sections.** If a section exists, it has substance. A section with one vague sentence is worse than no section — it creates false confidence that the topic was addressed.
3. **No copying the template verbatim.** Templates show structure. Your output fills that structure with project-specific analysis. If your output looks like the template with blanks filled in, you're not thinking — you're form-filling.
4. **Specificity over generality.** "Handles errors correctly" → reject. "Returns HTTP 409 Conflict when quote is already expired, with body `{ error: 'QUOTE_EXPIRED', quoteId, expiredAt }`" → accept.
5. **Quantify when possible.** "Fast response time" → reject. "P95 latency under 200ms for cached quotes, under 800ms for cache-miss with SQL fallback" → accept.
6. **Name things.** Don't say "the service" — say `QuoteOrchestrationService`. Don't say "the table" — say `QUOTE_EVENT`. Don't say "the endpoint" — say `POST /api/v1/orders`.
7. **Justify decisions.** Don't say "We chose approach A." Say "We chose approach A because [tradeoff]. Approach B was rejected because [reason]."
8. **Examples prove understanding.** When explaining behavior, include a concrete scenario: "When a NatWest quote expires after 30 seconds, the system writes a QUOTE_EVENT(EXPIRED) and the orchestrator initiates fallback to Barclays."

---

## Artifact 1: Spec Document

**Produced by**: /grill-spec (Phase 1)
**Consumed by**: /plan (Phase 2)
**File**: `docs/specs/TASK-ID-spec.md`

### What /plan Needs From This

The plan skill must decompose the spec into implementable micro-tasks. It needs:
- Unambiguous acceptance criteria that map to testable assertions
- Domain terms with precise definitions (not "see CONTEXT.md" — inline the relevant terms)
- Clear scope boundaries so it doesn't plan work that's out of scope
- Integration points so it can plan interface definitions and mocks
- Error scenarios so it can plan error handling paths and their tests

### Required Sections

```markdown
# Spec: [Task Title]

## Task Reference
- ID: [TASK-ID from board]
- Priority: [P0-P4]
- Source: [Jira link or board reference]
- Related: [other task IDs this depends on or is blocked by]

## Summary
[3-5 sentences. What this task delivers, why it matters, and how it fits into the
broader system. NOT a rewording of the title — explain the business value and
technical significance.]

## Acceptance Criteria

[Numbered. Each criterion is a testable assertion with specific values, inputs,
and expected outputs. If you can't write a test from it, it's too vague.]

1. GIVEN [precondition with specific data]
   WHEN [action with specific input]
   THEN [observable outcome with specific values]
   AND [side effect if any — database writes, events published, logs emitted]

## Domain Terms

[Terms relevant to THIS task, extracted from CONTEXT.md with any refinements
from the grill session. Include the "Avoid" column so implementers don't use
wrong synonyms in code.]

| Term | Definition | Used In Code As | Avoid |
|------|-----------|-----------------|-------|
| [term] | [precise definition] | [C# class/property name] | [ambiguous alternatives] |

## Scope

### In Scope
[Explicit list of what this task DOES deliver. Bullet points, specific.]

### Out of Scope
[Explicit list of what this task does NOT deliver. This is as important as in-scope.
Without it, /plan will over-plan.]

### Deferred
[Items that are in scope for the project but NOT this task. Reference future task IDs
if they exist.]

## Technical Context

### Integration Points
[Systems this task touches. For each: protocol, data format, auth, error contract.]

### Data Model
[Tables, columns, types, constraints affected. Reference the DER if it exists.
If creating new entities: full column definitions, not just "add a table".]

### Error Scenarios
[What can go wrong and what should happen. Each error gets:
 - Trigger condition (specific, not "something fails")
 - Expected behavior (retry? fallback? propagate? log?)
 - User/caller impact (HTTP status, error payload, timeout behavior)]

### Performance Constraints
[If applicable: latency targets, throughput requirements, data volume expectations.
Quantified, not "should be fast".]

## Clarifications from Grill Session

[Numbered Q&A from the adversarial interview. These are decisions that were made
during the grill — they're binding unless revisited.]

1. **Q**: [The ambiguity that was identified]
   **A**: [The decision that was made, with rationale]
   **Impact**: [How this affects implementation]

## ADRs Created
[List with file paths and one-line summaries, or "None — no hard-to-reverse decisions in this task"]

## Open Questions
[ONLY if there are genuinely unresolved items. These BLOCK /plan.
If this section has entries, the spec is NOT approved.]
```

### Quality Bar Examples

**REJECT** — vague AC:
```
1. The service should handle quote expiration correctly
2. Errors should be logged
3. Tests should be written
```

**ACCEPT** — testable AC:
```
1. GIVEN a QUOTE row with status = ACTIVE and created_at older than config.quoteExpirationMinutes (default: 30)
   WHEN the QuoteExpirationJob runs its scheduled sweep
   THEN the QUOTE.status is updated to EXPIRED
   AND a QUOTE_EVENT row is inserted with event_type = EXPIRED, timestamp = UTC now
   AND a metric quote_expired_total is incremented with labels {bank, symbol}

2. GIVEN a QUOTE row with status = EXPIRED
   WHEN any service attempts to read it via IQuoteRepository.GetActiveQuote(quoteId)
   THEN the method returns null (not the expired quote)
   AND no exception is thrown (expired = normal lifecycle, not error)

3. GIVEN the QuoteExpirationJob encounters a SQL timeout during the sweep
   WHEN the timeout exceeds 5 seconds
   THEN the job logs a warning with the batch size and timeout duration
   AND retries once after 10 seconds
   AND if the retry also times out, logs an error and skips to the next batch
   AND does NOT mark any quotes as expired from the failed batch (no partial updates)
```

### ADR Quality Bar

ADRs are optional artifacts — most specs produce zero. But when created, they must meet the same quality standard as any other artifact. The harness ships with exemplar ADRs in `docs/adr/` that define the floor.

**REJECT** — missing options:
```
# ADR-0042: Use Redis for caching

## Status
Accepted

## Context
We need a caching layer.

## Decision
We will use Redis.

## Consequences
Caching will be faster.
```

**Why rejected**: No options considered (why Redis over Memcached, in-memory, or no cache?). Context is one sentence — doesn't explain the problem. Consequences are vague ("faster" — how much? at what cost?).

**ACCEPT** — full analysis:
```
# ADR-0042: Redis Over In-Memory Cache for Quote Price Data

## Status
Accepted

## Context
The Quote Orchestrator fetches prices from multiple banks (NatWest, Barclays, HSBC)
via FIX protocol. Each quote has a 30-second TTL. During peak trading, the same
symbol is requested 50-100 times per second across multiple Azure Function instances.

Without a shared cache, each instance makes redundant FIX requests — increasing
latency (P99 jumps from 200ms to 1.2s) and risking rate limits from banks.
The cache must be shared across instances (ruling out in-process) and support
TTL-based expiration (ruling out simple key-value stores without TTL).

### Options Considered

**Option A: In-process MemoryCache**
- Built into .NET, zero infrastructure
- Pro: Lowest latency (~0.1ms), no network hop
- Con: Not shared across Function instances — each instance caches independently
- Con: Cold starts on scale-out mean cache misses during traffic spikes

**Option B: Redis (StackExchange.Redis)**
- Shared cache via Azure Cache for Redis
- Pro: Shared across all instances — one cache hit serves everyone
- Pro: Native TTL support per key (maps directly to quote expiration)
- Pro: Already in the infrastructure (used by the streaming transport layer)
- Con: Network hop adds ~1-3ms latency
- Con: Requires Redis availability — outage means fallback to direct FIX calls

**Option C: NCache / Hazelcast distributed cache**
- Enterprise distributed cache
- Pro: More features (near-cache, replication topologies)
- Con: Additional license cost and operational complexity
- Con: Team has no experience — learning curve during active sprint

## Decision
**Redis (Option B)** — it's already in our infrastructure, supports TTL natively,
and is shared across instances. The 1-3ms network hop is acceptable given we're
avoiding 50-100 redundant FIX calls per second. Option A was rejected because
Function instance isolation means no cache sharing. Option C was rejected because
the additional complexity isn't justified when Redis already meets our requirements.

## Consequences
- Redis becomes a runtime dependency for the Quote Orchestrator (already a dependency for streaming)
- Quote price lookups add ~1-3ms for cache hit vs. ~200ms for FIX call (99% improvement on cache hit)
- Redis outage degrades to direct FIX calls (higher latency, not data loss) — acceptable
- Cache key format: `quote:{symbol}:{bank}` with TTL = config.quoteExpirationSeconds
- Integration tests require Testcontainers.Redis (already configured)
```

---

## Artifact 2: PLAN.md

**Produced by**: /plan (Phase 2)
**Consumed by**: /implement (Phase 3) — specifically, subagents with ZERO prior context
**File**: `PLAN.md` (working directory root)

### What /implement Needs From This

Each micro-task is executed by a fresh subagent that has never seen the codebase. The plan must contain:
- The exact file path to create or modify (not "somewhere in services")
- Enough code context that the agent knows the patterns, naming, namespace, existing signatures
- A test skeleton that the agent writes FIRST (TDD red phase)
- A verification command that proves the task is done
- Explicit dependencies so the agent doesn't build on code that doesn't exist yet
- Reference to `docs/tech-context/TASK-ID-tech.md` with current library docs (verified via Context7 at planning time)

### Required Sections

```markdown
# Plan: [Task Title]

## Spec Reference
docs/specs/[TASK-ID]-spec.md — [one-line summary of what the spec decided]

## Tech Context
docs/tech-context/[TASK-ID]-tech.md — [libraries queried via Context7, key findings]

## Approach

### Chosen Strategy
[2-3 paragraphs explaining the implementation approach. Reference ADRs.
Reference verified API patterns from the tech context.
Explain WHY this approach, not just WHAT.]

### Rejected Alternatives
[What you considered and why you rejected it. This prevents subagents from
"improving" the approach by accidentally choosing a rejected path.]

### Risk Assessment
- **Highest risk**: [task N] — [why it's risky and what to watch for]
- **Integration risk**: [where things might not fit together]
- **Testing risk**: [what's hard to test and how we'll handle it]

## Task Summary
- Total tasks: [N]
- Sequential tasks: [list]
- Parallel group A: [tasks that can run simultaneously]
- Parallel group B: [if applicable]
- Estimated total: [M] minutes
- Estimated wall clock (with parallelism): [K] minutes

## Dependency Graph

```
Task 1: IQuoteRepository interface
├── Task 2: QuoteRepository (SQL impl) ── depends on 1
├── Task 3: QuoteOrchestrationService  ── depends on 1
│   └── Task 5: Orchestration tests    ── depends on 3
└── Task 4: QuoteExpirationJob         ── depends on 1, 2
    └── Task 6: Expiration tests       ── depends on 4
Task 7: Integration tests              ── depends on 2, 3, 4
```

## Tasks

### Task 1: [Descriptive title — not "Create interface"]

**Purpose**: [One sentence: WHY this task exists in the plan, what it enables]

**Files**:
- `src/Domain/Interfaces/IQuoteRepository.cs` (CREATE)
- `src/Domain/Models/Quote.cs` (MODIFY — add Status enum value)

**Context** (existing code the agent needs to see):
```csharp
// Current state of Quote.cs that the agent needs to understand
namespace COS.Domain.Models;

public class Quote
{
    public Guid Id { get; set; }
    public string Symbol { get; set; }
    public string Bank { get; set; }
    public QuoteStatus Status { get; set; }
    // ... other properties
}

public enum QuoteStatus
{
    Active,
    Filled,
    Rejected
    // Task: add Expired here
}
```

**Implementation**:
```csharp
// What the agent should produce
namespace COS.Domain.Interfaces;

public interface IQuoteRepository
{
    Task<Quote?> GetActiveQuote(Guid quoteId);
    Task<IReadOnlyList<Quote>> GetExpiredQuotes(TimeSpan olderThan, int batchSize);
    Task MarkAsExpired(Guid quoteId, CancellationToken ct);
}
```

**Test (write FIRST)**:
```csharp
namespace COS.Tests.Domain;

public class QuoteStatusTests
{
    [Fact]
    public void QuoteStatus_Should_Include_Expired_Value()
    {
        var expired = QuoteStatus.Expired;
        expired.Should().BeDefined();
        ((int)expired).Should().BeGreaterThan((int)QuoteStatus.Rejected);
    }
}
```

**Verify**:
```bash
dotnet test --filter "QuoteStatusTests"
```

**Depends on**: None (first task)
**Parallelizable**: No — other tasks depend on this interface
**Estimate**: 3 min
**Risk**: Low

### Task 2: [next task...]
[Same depth and detail as Task 1]

## Quality Checklist
- [ ] All existing tests still pass after each task
- [ ] Every new public method has a corresponding test
- [ ] CONTEXT.md terms used consistently (no synonyms in code)
- [ ] No ADR violations
- [ ] No new compiler warnings
- [ ] Each task's test is written BEFORE its implementation
```

### Quality Bar Examples

**REJECT** — vague task:
```
### Task 3: Implement the service

**Files**: src/Services/QuoteService.cs (create)

**Code**: Implement the service that handles quote operations.

**Verify**: dotnet test
```

**ACCEPT** — complete task (see template above for the full pattern)

A task is acceptable when a developer who has NEVER seen the codebase can implement it by reading ONLY the task description + CONTEXT.md. If they'd need to "figure out" anything — the task is incomplete.

---

## Artifact 3: Implementation Report

**Produced by**: /implement (Phase 3)
**Consumed by**: /test-verify (Phase 4)
**Format**: Terminal output + sprint-state update (not a separate file)

### What /test-verify Needs From This

Test-verify must know what was built to know what to test. It needs:
- Complete list of files changed with their purpose
- All tests already written (TDD) so it doesn't duplicate
- Which AC items are already covered vs need additional coverage
- Branch name to checkout and analyze
- Any known gaps or flags from implementation

### Required Content

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
- AC 3 (timeout handling) partially deferred to /test-verify — requires Testcontainers with fault injection

### Test Results
```
dotnet test — 11 passed, 0 failed, 0 skipped
Build: 0 warnings
```
```

---

## Artifact 4: Quality Report

**Produced by**: /test-verify (Phase 4)
**Consumed by**: /finish (Phase 5) — included in PR description
**File**: `docs/reports/TASK-ID-quality.md`

### What /finish Needs From This

The PR description must include quality metrics and test evidence. It needs:
- Gate verdicts (pass/soft fail/hard fail) for each metric
- Specific numbers (not "above threshold")
- AC traceability matrix (each AC → test names)
- SonarQube issue analysis (each code smell/vulnerability addressed or justified)

### Required Sections

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

### SonarQube Issue Analysis

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

[THE most important table in this report. Every AC maps to specific tests.
If an AC has no test → quality gate FAILS.]

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

## Artifact 5: PR Description

**Produced by**: /finish (Phase 5)
**Consumed by**: Human reviewers, CI pipeline, future archaeology
**Format**: GitHub PR body via `gh pr create`

### Required Content

```markdown
## Summary
[2-3 bullet points. What changed and WHY — not a list of files.]

- Implemented quote expiration lifecycle: scheduled sweep marks stale quotes as EXPIRED,
  writes QUOTE_EVENT audit trail, and emits Prometheus metrics
- Added SQL timeout resilience: single retry with exponential backoff, batch skipping
  on persistent failure, zero partial updates
- QuoteOrchestrationService coordinates the full cycle; QuoteRepository handles SQL persistence

## Spec & Decisions
- Spec: `docs/specs/STH-1192-spec.md`
- ADRs: `docs/adr/0003-quote-expiration-batch-strategy.md` — batch sweep chosen over
  per-quote timer (lower SQL load, simpler recovery)

## Changes

### Domain (`src/Domain/`)
- `Models/Quote.cs` — Added `QuoteStatus.Expired` enum value
- `Interfaces/IQuoteRepository.cs` — New: `GetExpiredQuotes`, `MarkAsExpired`

### Application (`src/Application/`)
- `Services/QuoteOrchestrationService.cs` — New: expiration sweep logic, metric emission,
  timeout retry strategy

### Infrastructure (`src/Infrastructure/`)
- `Repositories/QuoteRepository.cs` — New: SQL implementations of IQuoteRepository methods

### Tests
- `tests/Domain/QuoteStatusTests.cs` — Enum validation (1 test)
- `tests/Application/QuoteOrchestrationTests.cs` — Service logic (8 tests)
- `tests/Infrastructure/QuoteRepositoryTests.cs` — SQL integration via Testcontainers (6 tests)

## Quality Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Unit coverage | 86.6% | >= 80% |
| Mutation score (business) | 74.5% | >= 70% |
| Mutation score (infra) | 60.9% | >= 50% |
| Tests | 15 new, 15 total | All passing |
| AC coverage | 3/3 | All covered |

Full quality report: `docs/reports/STH-1192-quality.md`

## Acceptance Criteria

- [x] AC1: Expiration sweep updates QUOTE.status and writes QUOTE_EVENT — 5 tests
- [x] AC2: Expired quotes excluded from GetActiveQuote — 3 tests
- [x] AC3: SQL timeout retry, skip, no partial updates — 3 tests

## Test Plan

- [x] All existing tests pass (0 regressions)
- [x] New unit tests pass (8/8)
- [x] New integration tests pass (6/6, Testcontainers.MsSql)
- [x] Property-based test passes (FsCheck, 1000 iterations)
- [x] SonarQube quality gate: Pass, StyleCop: 0 warnings
- [ ] Manual verification: trigger expiration sweep with test data (reviewer)
```

---

## Artifact 6: CAB Ticket

**Produced by**: /finish (Phase 5) — P0/P1 tasks only
**Consumed by**: Tech Lead, Engineering Manager, CAB reviewers
**File**: `docs/cab/TASK-ID-cab.md`
**Template**: `templates/cab-ticket.md`

The CAB (Change Advisory Board) ticket documents the change for production deployment approval. It must include:
- Change description with business impact
- Risk assessment (complexity, impact, urgency)
- Technical details (database, infrastructure, code changes)
- Rollback plan with estimated time
- Test evidence referencing the quality report
- Deployment plan with maintenance window

**Quality bar**: A CAB reviewer unfamiliar with the codebase must understand what's changing, why, and how to roll back.

---

## Artifact 7: Release Checklist

**Produced by**: /finish (Phase 5)
**Consumed by**: DevOps, on-call team, deployment engineer
**File**: `docs/release/TASK-ID-release.md`
**Template**: `templates/release-checklist.md`

The release checklist tracks every step before, during, and after deployment. It includes:
- Pre-deployment verification (CAB, quality gates, UAT sign-off)
- Day-of execution steps (maintenance page, scripts, deployment, smoke tests)
- Post-deployment monitoring (24h error rate, performance baseline)
- Rollback trigger criteria (specific thresholds, not vague "if something goes wrong")

---

## Artifact 8: Solution Document

**Produced by**: /finish (Phase 5) — first task per service creates it, subsequent tasks update it
**Consumed by**: New team members, Tech Lead, DevOps
**File**: `docs/solution-document.md`
**Template**: `templates/solution-document.md`

The solution document is the living reference for a service. It includes:
- Architecture (Hexagonal layer map, component diagram, data model)
- Dependencies (internal Capiva packages, external packages, infrastructure)
- Configuration (app settings, connection strings, environment variables)
- Deployment (pipeline, environments, provisioning)
- Monitoring (health checks, key metrics, alert thresholds)
- ADRs and Deviation Records

**Quality bar**: A developer joining the team can understand the service architecture, find the pipeline, and know what to monitor — from this single document.

---

## Artifact 9: Deviation Record

**Produced by**: /plan or /implement (when blueprint deviation is needed)
**Consumed by**: Tech Lead, PR reviewers
**File**: `docs/deviations/DEV-NNN-[slug].md`
**Template**: `templates/deviation-record.md`

Required whenever code deviates from the enterprise blueprint constraints defined in `enterprise-blueprint.md`. Must justify WHY the deviation is necessary, WHAT alternative approach is used, and what the IMPACT is.

**Quality bar**: A Tech Lead can approve or reject the deviation based on this document alone, without reading the code.

---

## Cross-Artifact Traceability

The full chain from spec to PR must be traceable:

```
AC in spec.md  →  task in PLAN.md  →  test in implementation  →  row in quality report  →  checkbox in PR
```

Every acceptance criterion must appear in ALL five artifacts:
1. Spec: defined with GIVEN/WHEN/THEN
2. Plan: decomposed into tasks that deliver it
3. Implementation: test written that validates it
4. Quality report: mapped in AC coverage matrix
5. PR: checked off with test count

If an AC appears in the spec but NOT in the quality report's coverage matrix → quality gate FAILS.

---

## Enforcement in Skills

Each skill MUST:
1. Validate its INPUT artifacts against these standards before proceeding
2. Produce its OUTPUT artifacts matching or exceeding these standards
3. Refuse to advance if output quality is below the floor demonstrated here

### Input Validation Checklist

**/plan checks /grill-spec output:**
- [ ] Spec file exists at expected path
- [ ] AC section has numbered items with GIVEN/WHEN/THEN structure
- [ ] Domain Terms table has entries (at least the task's core terms)
- [ ] Scope section has both In Scope and Out of Scope
- [ ] No "Open Questions" section (or section is empty)

**/implement checks /plan output:**
- [ ] PLAN.md exists
- [ ] `docs/tech-context/TASK-ID-tech.md` exists (Context7 library docs)
- [ ] Every task has Files, Implementation, Test, and Verify sections
- [ ] File paths are absolute from project root (not relative or vague)
- [ ] Code snippets include namespace and class context
- [ ] Code snippets use API patterns consistent with tech context (not stale training data)
- [ ] Dependency graph is present and consistent with task ordering

**/test-verify checks /implement output:**
- [ ] Feature branch exists and is checked out
- [ ] `dotnet test` passes (all green)
- [ ] Implementation report lists all files changed
- [ ] AC coverage status shows what's covered and what's not

**/finish checks /test-verify output:**
- [ ] Quality report file exists at expected path
- [ ] All quality gates show verdict (not "--" or "pending")
- [ ] AC coverage matrix has a row for every AC in the spec
- [ ] Overall verdict is PASS or ACCEPTED_SOFT_FAIL
