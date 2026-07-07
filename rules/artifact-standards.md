# Artifact Standards — Gold Standard Output for Every Phase

> Every phase produces artifacts that gate the next phase. Poor output at Phase 1
> cascades into poor code at Phase 3 and meaningless tests at Phase 4.
> This file is the normative INDEX: anti-slop rules, schemas, and validation
> checklists for every artifact. The gold-standard worked examples live in the
> skill that produces each artifact ("Gold Standard" sections — see ADR-0011),
> so they load only when that phase runs. The examples are the FLOOR, not the
> ceiling. Produce richer output when the task warrants it.
>
> **Example stack note**: The worked examples use the `dotnet-hexagonal`
> blueprint stack (C#, xUnit, Testcontainers, StyleCop, SonarQube) for concreteness.
> The STRUCTURE and DEPTH are what's normative — substitute your active blueprint's
> equivalents (test framework, linter, quality gate tool, build commands) throughout.

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


**Gold-standard template and worked examples**: moved to `.claude/skills/grill-spec/SKILL.md` ("Gold Standard" section — spec template, AC quality bar, ADR quality bar) per ADR-0011, so they load only when that phase runs. The structure and depth shown there are normative.

### Machine-Readable AC Companion (`TASK-ID-acs.json`)

Every spec ships with `docs/specs/TASK-ID-acs.json` — the acceptance criteria as
data (see ADR-0009). Schema:

- Top level: `task` (board ID), `spec` (repo-relative spec path), `acs` (non-empty list)
- Each entry: `id` (matches the spec's AC numbering: "AC1", "AC2", ...), `text`
  (the full criterion, one line, complete — no "see spec"), `status`
  (`pending` | `pass` | `fail`; always `pending` at creation)
- Validated by `scripts/harness_lint.py` (schema check runs in CI)

**Immutability rule**: after spec approval, `id` and `text` are frozen and entries
may not be added or removed. Only /test-verify flips `status` — and only to `pass`
when the AC has BOTH a meaningful test AND end-to-end exercise evidence. Scope
changes route back through /grill-spec, which regenerates the file with all
statuses reset to `pending`.

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


**Gold-standard template and worked examples**: moved to `.claude/skills/plan/SKILL.md` ("Gold Standard" section — plan template, task quality bar) per ADR-0011, so they load only when that phase runs. The structure and depth shown there are normative.

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


**Gold-standard template and worked examples**: moved to `.claude/skills/implement/SKILL.md` ("Gold Standard" section — implementation report exemplar) per ADR-0011, so they load only when that phase runs. The structure and depth shown there are normative.

## Artifact 4: Quality Report

**Produced by**: /test-verify (Phase 4)
**Consumed by**: /finish (Phase 5) — included in PR description
**File**: `docs/reports/TASK-ID-quality.md`

### What /finish Needs From This

The PR description must include quality metrics and test evidence. It needs:
- Gate verdicts (pass/soft fail/hard fail) for each metric
- Specific numbers (not "above threshold")
- AC traceability matrix generated from `TASK-ID-acs.json` (each AC → test names + e2e evidence)
- End-to-end exercise evidence (the built feature was DRIVEN, not just unit-tested)
- Static analysis issue analysis (each code smell/vulnerability addressed or justified)


**Gold-standard template and worked examples**: moved to `.claude/skills/test-verify/SKILL.md` ("Gold Standard" section — quality report exemplar) per ADR-0011, so they load only when that phase runs. The structure and depth shown there are normative.

## Artifact 5: PR Description

**Produced by**: /finish (Phase 5)
**Consumed by**: Human reviewers, CI pipeline, future archaeology
**Format**: GitHub PR body via `gh pr create`


**Gold-standard template and worked examples**: moved to `.claude/skills/finish/SKILL.md` ("Gold Standard" section — PR description exemplar) per ADR-0011, so they load only when that phase runs. The structure and depth shown there are normative.

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
AC in spec.md  →  entry in TASK-ID-acs.json  →  task in PLAN.md  →  test in implementation  →  generated row in quality report (status: pass)  →  checkbox in PR
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
- [ ] `TASK-ID-acs.json` exists, matches the spec's ACs one-to-one, all statuses `pending`
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
- [ ] Test suite passes — all green (per blueprint §build-commands)
- [ ] Implementation report lists all files changed
- [ ] AC coverage status shows what's covered and what's not

**/finish checks /test-verify output:**
- [ ] Quality report file exists at expected path
- [ ] All quality gates show verdict (not "--" or "pending")
- [ ] Every `TASK-ID-acs.json` entry has status `pass`
- [ ] AC coverage matrix row count equals the acs.json entry count
- [ ] End-to-End Exercise section has evidence per AC (or an explicitly flagged gap)
- [ ] Overall verdict is PASS or ACCEPTED_SOFT_FAIL
