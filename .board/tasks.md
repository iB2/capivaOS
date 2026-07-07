# Task Board

## In Progress

<!-- Max 1 task. Managed by /sprint. Do NOT manually edit while sprint is running. -->

## Up Next

<!-- Queued for this sprint, priority order. /sprint picks from here. -->

## Blocked

<!-- Cannot proceed. Must include Blocker: with reason and date. -->

## Done

<!-- Completed. Immutable. PR + quality metrics. -->

- [x] **HARN-001** Repair context-persistence hook + Windows compatibility (P0)
  - **Spec**: docs/audits/2026-07-07-harness-audit.md (findings F1.2, F1.3, F2.1–F2.3)
  - **AC**: 4/4 verified — hook schema fixed (previous flat format never registered), plain python3 invocation valid in bash/cmd/PowerShell (verified on Windows), Boss/cycle dead paths removed, .state/ gitignored, board + sprint-state parsers match actual bullet formats
  - **Depends**: none
  - **Assignee**: main
  - **Status**: Done
  - **Phase**: IDLE
  - **Branch**: chore/harness-audit-backlog
  - **PR**: -- (fast-tracked with COS owner approval; branch PR covers HARN batch)
  - **Quality**: precompact/restore/stop entry points manually verified on Windows
  - **Started**: 2026-07-07
  - **Completed**: 2026-07-07
  - **Notes**: Extra finding during implementation: settings.json used a flat hook format that never registered with Claude Code, and the sprint-state parser always fell back to a stub — both worse than audited. Commit 816c0e3.

## Backlog — P0 Critical

<!-- Blocking other work or requiring immediate attention -->

<!-- HARN-* tasks: harness self-improvement backlog from docs/audits/2026-07-07-harness-audit.md (findings F1-F6 detailed there) -->

- [ ] **HARN-002** Fix dead references and doc inconsistencies (P0)
  - **Spec**: Remove/resolve every dead reference and stale count. See audit findings F1.1, F3.1–F3.7.
  - **AC**:
    1. No reference to nonexistent `/discovery` skill (README, init, grill-spec) — either create the skill or remove the references
    2. Single consistent law numbering in CLAUDE.md; DESIGN.md agrees on the count
    3. ADR count references match reality (7 ADRs) in grill-spec, artifact-standards, DESIGN.md index
    4. SCOPE.md blueprint table lists all 3 blueprints
    5. One canonical ADR template shared by grill-spec and arch role
    6. README attribution links point to real project repos
  - **Depends**: none
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: These would fail the harness's own artifact-standards review.

## Backlog — P1 Sprint

<!-- Committed for delivery this sprint -->

- [ ] **HARN-003** De-.NET the universal layer + delete orphan blueprint.md duplicates (P1)
  - **Spec**: Complete the stack-agnostic migration the blueprint-migration-map promised. See audit findings F4.1–F4.7, F5.1.
  - **AC**:
    1. Zero SonarQube/StyleCop/`dotnet test` mentions in files classified Universal (sprint, handover, sprint-state.md, artifact-standards, board-protocol, context-management, state-management, qa role) — replaced with "per blueprint §static-analysis / §build-commands" phrasing
    2. Orphaned `dotnet-hexagonal/blueprint.md` (598 lines) and `python-fastapi/blueprint.md` (818 lines) deleted or reduced to nextjs-style 14-line summaries (referenced by nothing — verify with grep before delete)
    3. `.gitignore` covers all three stacks (bin/obj, node_modules/.next, __pycache__/.venv) plus harness runtime state
    4. `grep -ri "sonarqube\|stylecop\|dotnet test" .claude/rules .claude/skills .board` returns only blueprint-scoped hits
  - **Depends**: HARN-002
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: artifact-standards.md examples may stay .NET-flavored if explicitly labeled as example stack.

- [ ] **HARN-004** Mechanical phase-guard enforcement: PreToolUse hooks + sprint-state.json (P1)
  - **Spec**: Convert Laws 1–2 from prompt-enforced to hook-enforced. See audit finding F6.2, F6.6. Rationale: Anthropic steering guidance — prompted "never do X" is not a guardrail.
  - **AC**:
    1. `sprint-state.json` written alongside sprint-state.md at every transition (phase, task, approvals, gates); markdown stays human-readable view
    2. PreToolUse hook denies Edit/Write to source paths unless Phase = IMPLEMENT (tests also allowed in TEST_VERIFY), with clear denial message pointing to /sprint
    3. PreToolUse hook denies `gh pr create` unless Phase = FINISH and Quality Gate = PASS
    4. Hooks tested on Windows + POSIX; always fail-open with a logged warning if state file is missing/corrupt
  - **Depends**: HARN-001
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Highest-leverage design change in the audit.

- [ ] **HARN-010** Template cleanup: restore distribution-pristine state before merge (P1)
  - **Spec**: This repo IS the distributed template — every project that adopts the harness copies `.board/`, `docs/`, `.claude/` verbatim. Session-specific tracking artifacts (HARN board entries, phase-history rows, audit docs) must NOT ship to adopters. This task runs LAST, immediately before the HARN branch merges.
  - **AC**:
    1. `.board/tasks.md` restored to pristine template: COS example tasks only, all HARN entries removed (git history preserves them)
    2. `.board/sprint-state.md` restored to clean initial state: empty Phase History, zeroed metrics, Phase = IDLE
    3. `docs/audits/` removed from the template (audit lives in git history and the PR description; decide whether a permanent `docs/MAINTENANCE.md` distills anything worth keeping)
    4. No stray session artifacts: no `.state/`, no scratch files, no board.lock
    5. Final check: `git diff main...HEAD --stat` shows only intentional harness improvements — zero session-tracking noise
  - **Depends**: HARN-002, HARN-003, HARN-004, HARN-005, HARN-006, HARN-007, HARN-008, HARN-009 (or whichever subset ships in the branch — must be the final commit before merge)
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Owner-requested 2026-07-07. Rationale: dogfooding the board for harness meta-work is correct for tracking, but the distributed artifact must be clean — adopters should never see another project's history.

- [ ] **HARN-005** Harness self-CI: cross-reference linter + hook tests + blueprint parity (P1)
  - **Spec**: A harness whose thesis is "no test, no implementation" has no tests. See audit finding F6.1.
  - **AC**:
    1. GitHub Actions workflow runs on PR: (a) cross-reference lint — every skill/rule/file/§anchor mentioned in docs resolves, (b) hook scripts execute on windows-latest and ubuntu-latest, (c) the three blueprint reference.md files share the identical §-section set
    2. Linter catches the F3.x class of drift (stale counts, dead skill references) — verified by seeding a known-bad fixture
    3. CI green on main after HARN-001..003 land
  - **Depends**: HARN-001, HARN-002, HARN-003
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Prevents recurrence of the entire drift class found in the audit.

- [ ] **COS-001** Implement quote creation endpoint (P1)
  - **Spec**: REST endpoint to create FX quotes with currency pair, rate, and TTL. Returns quote ID for downstream consumption.
  - **AC**:
    1. POST /api/v1/quotes accepts QuoteRequest and returns 201 with QuoteResponse
    2. Validation rejects invalid currency pairs and non-positive rates
    3. Quote stored with Active=true and ExpiresAt calculated from TTL
    4. Unit + integration tests cover happy path and validation errors
  - **Depends**: none
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Example task — replace with your actual backlog items.

- [ ] **COS-002** Add quote expiration sweep function (P1)
  - **Spec**: Azure Function on timer trigger that marks expired quotes as inactive. Runs every 5 minutes.
  - **AC**:
    1. Timer function triggers every 5 minutes
    2. Queries quotes where ExpiresAt < now AND Active == true
    3. Sets Active = false on all expired quotes (soft delete pattern)
    4. Logs count of expired quotes per run
  - **Depends**: COS-001
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Example task — replace with your actual backlog items.

## Backlog — P2 Planned

<!-- Planned, specs may be in progress -->

- [ ] **HARN-006** Verification upgrade: machine-readable AC list + end-to-end exercise + adversarial QA (P2)
  - **Spec**: Shift weight from process-before-code to verification-after-code. See audit finding F6.3. Pattern from Anthropic long-running-harness guidance: feature list JSON, immutable except status; verify by driving the system, not just tests.
  - **AC**:
    1. /grill-spec emits `docs/specs/TASK-ID-acs.json` (AC id, text, status: pending|pass|fail); skills forbidden to edit anything but status
    2. /test-verify requires an end-to-end exercise of the built feature (endpoint call / UI drive per blueprint tooling) before quality report can say PASS
    3. QA verify step reframed adversarially: reviewer prompted to REFUTE implementation-report claims, not confirm them
    4. Quality report AC matrix generated from the JSON, not hand-maintained
  - **Depends**: HARN-004
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: "Verification is the new bottleneck" — see audit Part 2 rationale.

- [ ] **HARN-007** Fast-lane pipeline for small/low-risk tasks (P2)
  - **Spec**: Scale ceremony to task size. See audit finding F6.5. Alternate state-machine path, not a bypass — task stays on board, state stays canonical.
  - **AC**:
    1. Fast lane defined for qualifying tasks (e.g., P3 + no new files + no schema/arch changes): combined spec-lite+plan phase with ONE human gate, then IMPLEMENT (TDD unchanged), then single quality gate
    2. Lane recorded in sprint-state; transitions logged in Phase History like any other
    3. Full pipeline remains default for P0/P1 and anything failing the qualifying predicate
    4. SCOPE.md documents when each lane applies
  - **Depends**: HARN-004
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Addresses the "SDD overhead exceeds return on small tasks" consensus.

- [ ] **HARN-008** Context-cost reduction: slim always-loaded layer (P2)
  - **Spec**: CLAUDE.md + 8 rules inject ~25-30K tokens per session. See audit finding F6.4. Move procedural bulk into on-demand skills.
  - **AC**:
    1. Gold-standard artifact examples moved from artifact-standards.md into the skills that consume them (/grill-spec, /plan, /test-verify)
    2. CLAUDE.md reduced toward ~200 lines (laws + pointers), measured before/after token estimate documented
    3. No loss of enforcement: everything removed from always-loaded context is either hook-enforced (HARN-004) or loaded by the owning skill
  - **Depends**: HARN-004
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Token-budget-first harness should not spend 15% of budget before work starts.

## Backlog — P3 Nice to Have

<!-- Scheduled but not committed -->

- [ ] **HARN-009** Modernize onto native Claude Code primitives (P3)
  - **Spec**: Replace hand-rolled patterns with platform-native ones where they add enforcement or reliability.
  - **AC**:
    1. Dev/QA/Arch roles become native agent definitions (`.claude/agents/*.md`) with tool restrictions (QA read-only; dev Edit+Bash) instead of role text pasted into prompts
    2. /implement subagent completion reports use structured output (validated JSON) instead of prose parsing
    3. Compaction heuristics ("2 auto-compactions = degraded") re-benchmarked against current Claude Code context management and updated or confirmed
  - **Depends**: HARN-006
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Tool restrictions on roles are themselves an enforcement mechanism.

## Backlog — P4 Ideas

<!-- Exploration, spikes, research. No spec required. -->
