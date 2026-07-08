# Quality Gates

## Gate Enforcement

Quality gates are checked in Phase 4 (Test & Verify). No task moves to Phase 5 without passing all applicable gates. There are no exceptions for deadlines or convenience.

**Stack-specific tools**: The active blueprint's `reference.md` defines which static analysis tools, linters, and quality gate tools are used (§static-analysis, §test-stack, §build-commands). Read it before running any checks.

---

## Test Stack

The test framework, assertion library, and integration test infrastructure are defined in the active blueprint's `reference.md` §test-stack section. Always use the packages and patterns specified there.

---

## Unit Test Coverage

| Scope | Minimum | Target |
|-------|---------|--------|
| Business logic (services, domain) | 80% | 90% |
| Infrastructure (repositories, transports) | 60% | 75% |
| Overall solution | 75% | 85% |

**Measurement**: Use the coverage command from blueprint §build-commands.

**Exclusions** (do not count toward coverage):
- Entry points / host configuration / bootstrap
- Auto-generated code (migrations, generated stubs)
- DTOs and data containers with no logic
- Framework wrappers (test the injected services instead)

---

## Static Analysis

Static analysis tools are defined in the active blueprint's `reference.md` §static-analysis section. The universal requirements are:

- **All builds** should run static analysis (linting + type checking)
- **Quality gate** must pass (configured per blueprint)
- **No new warnings** in changed files
- **No new bugs** or vulnerabilities
- **Coverage data** published to quality gate tool (if applicable)

### Linter Compliance

- Zero linter warnings in new code
- Accepted suppressions documented in the blueprint reference
- Any new suppression requires a Deviation Record (`${CLAUDE_PLUGIN_ROOT}/project-template/templates/deviation-record.md`)

---

## Acceptance Criteria Gate (acs.json)

The AC gate is measured from `docs/specs/TASK-ID-acs.json`, not from prose:

- `/capiva:grill-spec` emits the file (all statuses `pending`); after spec approval, `id` and `text` are immutable
- `/capiva:test-verify` flips each `status` to `pass` only when the AC has BOTH a meaningful test AND end-to-end exercise evidence (driving the running feature — endpoint call, UI drive, CLI run)
- The quality report's AC matrix is GENERATED from this file — a hand-maintained matrix is a standards violation
- `/capiva:finish` blocks while any status is `pending` or `fail`

**End-to-end exercise is a hard gate**: a quality report with no End-to-End Exercise
section (or with unexplained gaps) cannot be verdict PASS. See ADR-0009.

## Code Review

| Priority | Review Required | Reviewer |
|----------|----------------|----------|
| P0 | Mandatory human review between every micro-task | Human |
| P1 | Mandatory human review after all micro-tasks complete | Human |
| P2 | Automated review (Claude subagent) acceptable | Subagent |
| P3-P4 | Self-review sufficient | Self |

> Scope note: this table governs review BETWEEN micro-tasks during
> IMPLEMENT. The end-of-task quality gate (after /capiva:test-verify) is a
> human checkpoint in attended mode for EVERY priority; in auto mode it
> routes per the approval policy (ADR-0014).

**Review checklist**:
- [ ] Tests cover the acceptance criteria
- [ ] No business logic without corresponding test
- [ ] Error handling is explicit (no swallowed exceptions)
- [ ] Naming follows blueprint §coding-standards
- [ ] No TODO/HACK comments without a linked board task
- [ ] Async patterns used correctly (no sync-over-async, no fire-and-forget)
- [ ] Type safety respected (no escape hatches without justification)

---

## Integration Tests

**Required when code touches**:
- Database (any repository implementation) — use real test database or containers per blueprint §test-stack
- Cache — use real cache or containers per blueprint §test-stack
- External HTTP APIs — use appropriate mock server for the stack
- File system — use appropriate abstractions for the stack

**Integration test rules**:
- Each test class manages its own resource lifecycle
- Tests must be parallelizable (no shared mutable state)
- Cleanup happens in teardown, not scattered through tests
- Connection strings come from the test fixture, never from config files
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
- Writing a test that passes immediately: the test is not testing anything useful — rewrite it
- Skipping refactor: acceptable for trivial changes, but not for anything touching business logic

### TDD Verification Method

TDD compliance is verified through commit structure and QA review:

1. **Commit order**: Each micro-task should produce at least two commits — test commit before implementation commit.
2. **QA review**: The QA role (Stage 3) checks for TDD evidence — tests that are clearly written to describe behavior, not retrofitted to match existing code.
3. **Orchestrator spot-check**: /capiva:implement samples the last 3 commits from each subagent and verifies at least one test file was committed before or alongside each implementation file.

If TDD violation is detected:
- The subagent's code is reverted
- The task is respawned with an explicit warning
- The violation is logged in sprint-state Notes

---

## Report Artifacts

After Phase 4 completes, the following artifacts must exist:

| Artifact | Location | Format |
|----------|----------|--------|
| Test results | `reports/test-results/` | Per blueprint format |
| Coverage report | `reports/coverage/` | HTML (per blueprint §build-commands) |
| Quality gate report | Per blueprint §static-analysis | Per tool |

**CI Integration**:
- Test results consumed by CI pipeline per blueprint §ci-cd
- Coverage published to quality gate tool (if applicable)
- Quality gate status reported on PR

---

## Gate Override

Quality gates can only be overridden by explicit human decision. To override:

1. Document WHY the gate cannot be met (not "it's too hard" — a real technical reason)
2. Create a follow-up task on the board to close the gap
3. Mark the override in the PR description: `Quality gate override: [gate] -- [reason] -- [follow-up task]`
4. Human must approve the PR knowing about the override

No silent overrides. No "we'll fix it later" without a board task.
