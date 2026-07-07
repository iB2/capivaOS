---
name: finish
description: Phase 5 — Create PR with CAB ticket + release checklist, update board, transition Jira, cleanup. Phase guard ensures quality gates passed.
---

# Finish — Phase 5

Wrap up a completed task: create a PR, update the board, transition Jira, and clean up artifacts.

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = FINISH
3. Verify Quality Gate = PASS (or ACCEPTED_SOFT_FAIL)
4. Verify `docs/reports/TASK-ID-quality.md` exists
5. If ANY check fails → **STOP**: "⛔ Phase guard failed. [specific failure]. Complete /capiva:test-verify first."
6. If ALL checks pass → proceed

## Process

### Step 1: Pre-Flight Checks

Before creating the PR, verify:

1. **All tests pass:** Run the test command from blueprint §build-commands.
2. **Quality gates met:** Read `docs/reports/TASK-ID-quality.md`, confirm verdict
3. **No uncommitted changes:**
   ```bash
   git status
   ```
4. **Branch pushed to remote:**
   ```bash
   git push -u origin feature/TASK-ID-slug
   ```
5. **Branch is up to date with base:**
   ```bash
   git fetch origin
   git rebase origin/main
   ```
   Re-run tests after rebase to verify nothing broke.

If ANY check fails → STOP and report. Do NOT create a PR with failing tests.

### Step 2: Create Pull Request

Create PR using `gh pr create`:

```markdown
## Summary
[1-3 bullet points: what changed and why]

## Spec Reference
- Spec: docs/specs/[TASK-ID]-spec.md
- ADRs: [list or "None"]

## Changes
[Files changed, grouped by concern]

## Test Plan
- Unit tests: [N] new, [M] total passing
- Integration tests: [N] new, [M] total passing
- BDD scenarios: [N]
- Property-based tests: [N]

## Quality Metrics
| Metric | Value | Target |
|--------|-------|--------|
| Unit coverage | X% | >= 80% |
| Linter warnings | 0 | 0 |
| Quality gate | Pass | Pass |

## Acceptance Criteria
[Generated from docs/specs/TASK-ID-acs.json — one checkbox per entry, text verbatim]
- [x] AC1: [text] — tested by [test name], exercised end-to-end
- [x] AC2: [text] — tested by [test name], exercised end-to-end

## SDLC Artifacts
- Quality report: `docs/reports/[TASK-ID]-quality.md`
- Coverage HTML: `[path per blueprint]`
- CAB ticket: `docs/cab/[TASK-ID]-cab.md` (P0/P1 only)
- Release checklist: `docs/release/[TASK-ID]-release.md`
- Solution document: `docs/solution-document.md`
- Deviation records: `docs/deviations/` (if any)
```

### Step 2.5: Generate CAB Ticket

For P0 and P1 tasks, generate a Change Advisory Board ticket:

1. Copy template from `${CLAUDE_PLUGIN_ROOT}/project-template/templates/cab-ticket.md`
2. Fill with task-specific information:
   - Change description from spec summary
   - Risk assessment based on quality report
   - Database changes from PLAN.md
   - Rollback plan from implementation details
   - Test evidence from quality report
3. Save to `docs/cab/TASK-ID-cab.md`
4. Present to human for review

**Skip for P2-P4 tasks** unless explicitly requested.

### Step 2.6: Generate Release Checklist

For ALL tasks that will deploy to production:

1. Copy template from `${CLAUDE_PLUGIN_ROOT}/project-template/templates/release-checklist.md`
2. Fill with task-specific deployment details
3. Save to `docs/release/TASK-ID-release.md`
4. Include link in PR description

### Step 2.7: Generate/Update Solution Document

If this is the FIRST task for a new service, generate the solution document:

1. Copy template from `${CLAUDE_PLUGIN_ROOT}/project-template/templates/solution-document.md`
2. Fill with service architecture, dependencies, configuration
3. Save to `docs/solution-document.md`

If the solution document already exists, UPDATE it with:
- New dependencies added by this task
- New configuration settings
- New ADRs
- New deviation records

### Step 3: Update Board

**Acquire board lock** (follow `${CLAUDE_PLUGIN_ROOT}/rules/board-protocol.md`):

1. Read `.board/tasks.md` FRESH
2. Move task from "In Progress" to "Done"
3. Update task entry:
   ```markdown
   - [x] **TASK-ID** Task title (P1)
     - **PR**: #[number]
     - **Quality**: [coverage]% / [quality gate pass/fail]
     - **Branch**: feature/TASK-ID-slug
     - **Completed**: [ISO date]
   ```
4. **Release board lock**

### Step 4: Jira Transition (if configured)

If Jira MCP tools are available AND project is configured:
1. Transition issue to "In Review" (or configured status)
2. Add comment: PR link + quality metrics summary
3. Log the transition

If Jira not configured → skip silently. Board update in Step 3 is sufficient.

### Step 5: Cleanup

1. Remove worktree if used:
   ```bash
   git worktree remove .worktrees/feature-name 2>/dev/null || true
   ```
2. Keep test results for reference until PR is merged

### Step 6: Present Merge Options

Present to human:
```
PR #[N] created: [title]
Board updated: [TASK-ID] moved to Done
Quality: coverage [X]%, Linter: 0 warnings, Quality Gate: Pass

Options:
1. Merge now — squash merge into main (commit message follows project convention)
2. Keep for review — leave PR open for team review
3. Discard — close PR and delete branch (requires confirmation)

🧑 What would you like to do?
```

**NEVER merge without explicit human approval.** "Merge it", "merge", "1" = proceed. Anything else = wait.

## Phase Transition (MANDATORY)

**After human decides (merge/review/discard):**

1. If merge: `gh pr merge [N] --squash`
2. If review: no action needed (PR stays open)
3. If discard: `gh pr close [N]` + `git push origin --delete feature/TASK-ID-slug` (ONLY with explicit confirmation)

4. Update `.board/sprint-state.md`:
   - Phase: IDLE
   - Reset Current Task to (none)
   - Register artifact: PR #[N]
   - Increment sprint metrics (tasks completed, PRs created)
5. Add Phase History: `| [now] | [task] | FINISH | IDLE | [merge/review/discard] | PR #[N] |`

6. **→ Return control to /capiva:sprint** which will `/clear` and pick the next task.

If invoked standalone:
- Update sprint-state as above
- State: "Task [TASK-ID] complete. PR #[N] [merged/open for review/discarded]. Sprint state reset to IDLE."

## Input Quality Validation

Before creating the PR, validate /capiva:test-verify output against `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md` "Artifact 4":

- [ ] Quality report exists at `docs/reports/TASK-ID-quality.md`
- [ ] All quality gates have concrete verdicts (not "--" or "pending")
- [ ] `docs/specs/TASK-ID-acs.json`: every entry has `status: "pass"` — any `pending` or `fail` blocks the PR
- [ ] AC coverage matrix row count equals the acs.json entry count (the matrix is generated from it)
- [ ] Quality report has an End-to-End Exercise section with evidence per AC (see ADR-0009)
- [ ] Overall verdict is PASS or ACCEPTED_SOFT_FAIL (not HARD_FAIL)
- [ ] All static analysis issues in new code are analyzed and addressed or justified

If ANY check fails → STOP. Report: "Quality report incomplete. Return to /capiva:test-verify."

## Output Quality Gate

Before presenting the PR for merge decision, validate the PR description against `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md` "Artifact 5: PR Description":

- [ ] Summary has 2-3 bullets explaining WHAT and WHY (not just file lists)
- [ ] Spec & Decisions section references spec file path and any ADRs
- [ ] Changes section groups files by concern with one-line purpose each
- [ ] Quality Metrics table has Value and Target for every gate
- [ ] AC section has checkboxes mapping each criterion to test count
- [ ] Test Plan has checkboxes for unit, integration, static analysis, and manual verification
- [ ] No vague descriptions ("updated service", "added tests") — everything is specific

### SDLC Artifact Validation (before presenting PR)

For **P0/P1 tasks** — validate CAB ticket (`docs/cab/TASK-ID-cab.md`):
- [ ] Change Details section describes what changed and why (not just file list)
- [ ] Risk Assessment filled: impact level, affected systems, data changes
- [ ] Technical Details lists database changes, infrastructure changes, configuration changes
- [ ] Rollback Plan has concrete steps (not "revert the PR")
- [ ] Test Evidence references quality report path and key metrics
- [ ] Approvals table is prepared with required approver roles

For **ALL tasks** — validate Release Checklist (`docs/release/TASK-ID-release.md`):
- [ ] Pre-Deployment section lists all prerequisites
- [ ] Day-of-Deployment steps are specific and ordered
- [ ] Rollback Trigger Criteria defined (what conditions trigger a rollback)
- [ ] Environment table filled (per blueprint §ci-cd environments)

For **ALL tasks** — enterprise compliance:
- [ ] All branch commits follow the commit convention (see `${CLAUDE_PLUGIN_ROOT}/rules/board-protocol.md`)
- [ ] Solution document (`docs/solution-document.md`) created (first task per service) or updated
- [ ] All deviation record files in `docs/deviations/` are referenced in the PR description and follow `${CLAUDE_PLUGIN_ROOT}/project-template/templates/deviation-record.md` format

If any SDLC artifact fails validation → iterate before creating PR.

## Quality Gate Override

If the human requests an override for a SOFT_FAIL gate:

1. Follow the protocol in `${CLAUDE_PLUGIN_ROOT}/rules/quality-gates.md` "Gate Override" section
2. Document the reason in the PR description: `Quality gate override: [gate] -- [reason] -- [follow-up task]`
3. Create a follow-up task on `.board/tasks.md` for the deferred fix
4. Update `.board/sprint-state.md` Quality Gate to `ACCEPTED_SOFT_FAIL`

No silent overrides. HARD_FAIL gates cannot be overridden — they block /capiva:finish entirely.

## Rules

- **Never merge without human approval.** PR is created, not merged. Merging requires explicit "merge it".
- **PR must include quality metrics.** Coverage and quality gate status in every PR.
- **Board update is mandatory.** Even without Jira, `.board/tasks.md` must be updated.
- **Board lock for writes.** Every board write follows lock protocol.
- **Clean up artifacts.** Worktrees, temp files — remove them.
- **No force pushes.** If branch has issues, fix forward.
- **Jira failures are non-blocking.** Log and continue. PR + board = what matters.
- **Sprint-state reset to IDLE.** Task is done, state machine returns to start.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.

---

## Gold Standard (moved from artifact-standards.md, ADR-0011)

The normative template and quality bar for this skill's artifact — the FLOOR, not the ceiling. `artifact-standards.md` keeps the anti-slop rules and validation checklists; the worked examples live here so they load only when this phase runs.

### Artifact 5: PR Description — Required Content
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
- ADRs: `docs/adr/0003-quote-expiration-batch-strategy.md` (project ADR from the example task) — batch sweep chosen over
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

