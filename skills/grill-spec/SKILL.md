---
name: grill-spec
description: Phase 1 — Adversarial spec validation with phase guard. Produces formal spec document, CONTEXT.md entries, and ADRs.
---

# Grill Spec — Phase 1

Stress-test a task specification through adversarial questioning. Produces a formal spec document, domain glossary entries, and ADRs.

## Init Gate (MANDATORY — before phase guard)

**Check that the harness has been initialized:**

1. `docs/CONTEXT.md` must have at least one glossary entry or domain rule (not just empty headers)
2. `docs/specs/INTAKE-summary.md` must exist with content

**If EITHER is missing or empty → STOP:**

```
⛔ Project docs not found. Run /capiva:init before starting the pipeline.

Grill-spec needs domain context and project scope to produce useful specs.
Without CONTEXT.md and INTAKE-summary.md, the adversarial interview
starts from zero — questions will be generic, specs will miss constraints.

Run /capiva:init to set up the harness. If the project docs are missing, draft
them from your raw materials first (${CLAUDE_PLUGIN_ROOT}/project-template/templates/intake-summary.md defines
the INTAKE format).
```

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = GRILL_SPEC
3. If Phase ≠ GRILL_SPEC → **STOP**: "⛔ Phase guard failed. Current: [actual]. Required: GRILL_SPEC. Run /capiva:sprint to advance to this phase."
4. If Phase = GRILL_SPEC → proceed

## Process

### Step 1: Load Context

- Read the task spec from sprint-state (Task ID → find in board or linked doc)
- **Read `docs/specs/INTAKE-summary.md`** — load project scope, stakeholders, requirements, constraints as starting context
- Read `docs/CONTEXT.md` for existing domain terms
- Read `${CLAUDE_PLUGIN_ROOT}/docs/adr/` for existing architectural decisions
- Scan relevant source files referenced in the spec

### Step 2: Adversarial Interview

Walk each branch of the decision tree. **One question at a time.**

For each question:
1. State the ambiguity or risk identified
2. Provide a **recommended answer** based on codebase exploration
3. Wait for human confirmation or correction before moving on

Priority order:
1. Scope boundaries — what is explicitly OUT of scope?
2. Domain term ambiguity — does "X" mean the same thing everywhere?
3. Edge cases the spec doesn't address
4. Integration points with existing systems
5. Performance and scaling implications
6. Error handling and failure modes
7. Security considerations

### Step 3: Explore Before Asking

Before asking a question, check if the answer exists:
- Search codebase for related patterns
- Check ADRs for prior rulings
- If the codebase answers definitively → state the finding, don't ask

### Step 4: Update CONTEXT.md

As domain terms crystallize, add to `docs/CONTEXT.md`:

```markdown
| Term | Definition | Used In Code As | Avoid |
|------|-----------|-----------------|-------|
| TradeOrder | A request to execute a buy/sell transaction | TradeOrder | Order (too generic), Trade (ambiguous) |
```

- Only add terms that were ambiguous or contested during the interview
- Cross-reference against existing entries — flag contradictions explicitly

### Step 5: Create ADRs

Create `${CLAUDE_PLUGIN_ROOT}/docs/adr/NNNN-slug.md` ONLY when ALL THREE criteria are met:
1. Hard to reverse (changing requires significant rework)
2. Non-obvious (reasonable engineers would disagree)
3. Real trade-offs (not just "best practice")

**Numbering**: Continue from the highest existing ADR number in `${CLAUDE_PLUGIN_ROOT}/docs/adr/` (list the directory — the harness ships with its own exemplar ADRs).

**Exemplars**: Read any of the shipped ADRs in `${CLAUDE_PLUGIN_ROOT}/docs/adr/` as gold-standard examples. Your ADRs must match this depth.

ADR format:
```markdown
# ADR-NNNN: Title

## Status
Proposed | Accepted | Superseded by ADR-XXXX | Deprecated

## Context

[The problem or decision point. 2-3 paragraphs minimum. Explain:
- What triggered this decision (a requirement, a risk, a conflict)
- What constraints exist (performance, compatibility, team skill, enterprise policy)
- Why the status quo is insufficient]

### Options Considered

**Option A: [Name]**
- [How it works — 1-2 sentences]
- Pro: [specific benefit]
- Pro: [specific benefit]
- Con: [specific drawback]
- Con: [specific drawback]

**Option B: [Name]**
- [How it works]
- Pro: [...]
- Con: [...]

**Option C: [Name]**
- [How it works]
- Pro: [...]
- Con: [...]

[Minimum 2 options. If there's only one viable option, explain why the alternatives
were eliminated before this decision point. "We had no choice" is not a decision —
it's a constraint that should be in Context.]

## Decision

**[Option X] — [one-sentence summary].**

[1-2 paragraphs explaining WHY this option. Not just "we chose X" but "we chose X
because [tradeoff]. Option Y was rejected because [reason]. Option Z would have
required [cost we weren't willing to pay]."

If the decision was close between two options, say so — it helps future reviewers
understand when this ADR might need revisiting.]

## Consequences

[What becomes easier, harder, or different as a result of this decision.
Be specific — not "this makes things simpler" but "repository implementations
now follow the IAsyncLifetime pattern, which adds 10 lines of boilerplate per
test class but eliminates container lifecycle bugs."]

- [Positive consequence]
- [Positive consequence]
- [Negative consequence or trade-off accepted]
- [Future consideration — when might this decision need revisiting?]
```

### ADR Anti-Patterns (do NOT produce these)

- **Missing options**: "We decided to use X" without explaining what else was considered. If there were no alternatives, it's not a decision — it's a constraint (put it in Context instead).
- **Vague consequences**: "This is better." Better HOW? For whom? At what cost?
- **Premature ADR**: Using dependency injection is not ADR-worthy (it's standard practice). Choosing BETWEEN two DI containers IS.
- **One-paragraph ADR**: If the entire ADR fits in 5 lines, either the decision wasn't significant enough (don't write it) or you're not thinking deeply enough (expand it).

### Step 6: Write Formal Spec Document

Create `docs/specs/TASK-ID-spec.md` with this structure:

```markdown
# Spec: [Task Title]

## Task Reference
- ID: [TASK-ID]
- Priority: [P0-P4]
- Source: [Jira link or board reference]

## Summary
[2-3 sentences describing what this task delivers]

## Acceptance Criteria
1. [Measurable criterion]
2. [Measurable criterion]
...

## Clarifications
[Numbered Q&A from the adversarial interview]

## Domain Terms
[Terms added to CONTEXT.md during this spec]

## ADRs Created
[List of ADR files created, or "None"]

## Out of Scope
[Explicitly listed items that are NOT part of this task]

## Open Questions
[Any remaining ambiguities — these BLOCK progression to /capiva:plan]
```

### Step 6b: Emit Machine-Readable AC List

Alongside the spec, write `docs/specs/TASK-ID-acs.json` — the acceptance criteria
as data. This file is the verification contract: /capiva:test-verify generates the
quality-report AC matrix from it and /capiva:finish refuses a PR while any entry is not
`pass` (see ADR-0009).

```json
{
  "task": "COS-042",
  "spec": "docs/specs/COS-042-spec.md",
  "acs": [
    {
      "id": "AC1",
      "text": "GIVEN a QUOTE row with status ACTIVE older than quoteExpirationMinutes WHEN the expiration sweep runs THEN status becomes EXPIRED and a QUOTE_EVENT(EXPIRED) row is written",
      "status": "pending"
    },
    {
      "id": "AC2",
      "text": "GIVEN a QUOTE row with status EXPIRED WHEN GetActiveQuote(quoteId) is called THEN it returns null without throwing",
      "status": "pending"
    }
  ]
}
```

Rules:
- One entry per AC in the spec, same order, `id` matching the spec's numbering (`AC1`, `AC2`, ...)
- `text` is the full GIVEN/WHEN/THEN criterion — condensed to one line, but complete (no "see spec")
- `status` is always `"pending"` at creation. Valid values: `pending` | `pass` | `fail`
- **Immutable except status.** Once the spec is approved, no skill may edit `id` or `text`, add entries, or remove entries. Only /capiva:test-verify (and the fast-lane equivalent, if configured) flips `status`. Scope changes go back through /capiva:grill-spec, which regenerates the file and resets all statuses to `pending`.

### Step 7: Present for Approval

Present the spec document summary to the human:
- Acceptance criteria (numbered)
- Key clarifications made
- Any new ADRs
- Open questions (if any — these block planning)

Then state:
```
Spec document written to docs/specs/[TASK-ID]-spec.md
AC list written to docs/specs/[TASK-ID]-acs.json ([N] criteria, all pending)
CONTEXT.md updated with [N] new terms.
[M] ADRs created.

🧑 Awaiting spec approval to proceed to /capiva:plan phase.
```

## Phase Transition (MANDATORY)

**After human approves the spec:**

1. Update `.board/sprint-state.md`:
   - Spec Approved: Yes
   - Register artifacts: `docs/specs/TASK-ID-spec.md`, `docs/specs/TASK-ID-acs.json`
2. Add Phase History row: `| [now] | [task] | GRILL_SPEC | PLAN | spec-approved | [summary] |`
3. **→ Return control to /capiva:sprint** which will invoke /capiva:plan next.

If invoked standalone (not from /capiva:sprint):
- Update sprint-state as above
- State: "Spec approved. Next step: invoke /capiva:plan to decompose into micro-tasks."

## Output Quality Gate

Before presenting the spec for approval, validate against `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md` "Artifact 1: Spec Document":

- [ ] Summary is 3-5 sentences explaining business value (not a rewording of the title)
- [ ] Every AC uses GIVEN/WHEN/THEN with specific values, inputs, and expected outputs
- [ ] Domain Terms table has entries with Definition, Used In Code As, and Avoid columns
- [ ] Scope has BOTH In Scope and Out of Scope sections with specific bullet points
- [ ] Technical Context includes Integration Points, Data Model, and Error Scenarios
- [ ] Error Scenarios have trigger condition, expected behavior, and user/caller impact
- [ ] Clarifications are numbered Q&A with rationale and implementation impact
- [ ] `docs/specs/TASK-ID-acs.json` exists, parses as JSON, has one entry per spec AC (matching ids and order), and every status is `pending`
- [ ] No placeholders ("[TBD]", "as discussed", "various", "etc.") anywhere
- [ ] Every entity is named specifically (class names, table names, endpoint paths — not "the service")
- [ ] If ADRs were created: each has Context, Options Considered (2+ options with pros/cons), Decision (with rationale), and Consequences
- [ ] If ADRs were created: they match the depth of the harness exemplar ADRs in `${CLAUDE_PLUGIN_ROOT}/docs/adr/`

If ANY check fails → iterate on the spec before presenting. Do NOT present a below-standard spec.

## Rules

- **One question at a time.** Never dump a list.
- **Always provide a recommended answer.** Human confirms, corrects, or expands.
- **Explore before asking.** Don't waste human time on questions the codebase answers.
- **ADRs are rare.** Most specs produce zero.
- **CONTEXT.md is cumulative.** Never remove entries. Only add or amend.
- **Flag contradictions.** New answers vs existing glossary/ADR = explicit callout.
- **No code.** This skill produces specs and documentation only.
- **Formal spec document is mandatory.** The output is `docs/specs/TASK-ID-spec.md`, not just conversation.
- **The AC list is data.** `docs/specs/TASK-ID-acs.json` ships with every spec. After approval it is immutable except `status` — scope changes regenerate it through this skill.
- **Open questions block progression.** If there are unresolved ambiguities, /capiva:plan CANNOT start.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.

---

## Gold Standard (moved from artifact-standards.md, ADR-0011)

The normative template and quality bar for this skill's artifact — the FLOOR, not the ceiling. `artifact-standards.md` keeps the anti-slop rules and validation checklists; the worked examples live here so they load only when this phase runs.

### Artifact 1: Spec Document — Required Sections
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
Without it, /capiva:plan will over-plan.]

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
[ONLY if there are genuinely unresolved items. These BLOCK /capiva:plan.
If this section has entries, the spec is NOT approved.]
```

### Artifact 1: Spec Document — Quality Bar Examples
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

### Artifact 1: Spec Document — ADR Quality Bar
ADRs are optional artifacts — most specs produce zero. But when created, they must meet the same quality standard as any other artifact. The harness ships with exemplar ADRs in `${CLAUDE_PLUGIN_ROOT}/docs/adr/` that define the floor.

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

