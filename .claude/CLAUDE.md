# CLAUDE.md — Spec-Driven Development Harness

## What This Is

A 6-phase development pipeline for Claude Code that enforces spec-driven, test-first development. The pipeline is state-machine driven — every phase reads and updates `.board/sprint-state.md`, every skill enforces phase guards, and no skill can run out of sequence.

**Three immutable laws:**
1. If it's not on the board, it doesn't get built.
2. If there's no approved spec, there's no code.
3. If there's no test, there's no implementation.

**Why this harness exists**: Claude Code without structure jumps to code, skips specs, forgets decisions after compaction, and self-approves mediocre quality. This pipeline makes disciplined development the path of least resistance — the agent can't skip steps because the state machine won't let it. See `docs/DESIGN.md` for the full design philosophy, source attribution, and rationale for every design decision. See `docs/SCOPE.md` for what this harness is and isn't.

---

## Active Blueprint

The harness is **stack-agnostic**. Technology-specific patterns, commands, and standards are defined in **blueprint reference files**. The active blueprint determines which stack's conventions are used.

### Configuration

Set the active blueprint by specifying its path:

```
Active Blueprint: .claude/blueprints/dotnet-hexagonal
```

### Available Blueprints

| Blueprint | Stack | Reference |
|-----------|-------|-----------|
| `dotnet-hexagonal` | .NET 10 / C# 13 / Hexagonal Architecture | `.claude/blueprints/dotnet-hexagonal/reference.md` |
| `python-fastapi` | Python 3.13 / FastAPI / Layered Architecture | `.claude/blueprints/python-fastapi/reference.md` |
| `nextjs-typescript` | Node.js 22 / Next.js 15+ / App Router / shadcn/ui | `.claude/blueprints/nextjs-typescript/reference.md` |

### How Blueprints Work

Agent roles, skills, and rules reference the active blueprint's `reference.md` for:
- **§architecture** — Project structure, layer rules, dependency direction
- **§coding-standards** — Naming conventions, code style, mandatory patterns
- **§enterprise-patterns** — Service/repository pattern, DI, validation, error handling
- **§test-stack** — Test framework, assertion library, test infrastructure
- **§static-analysis** — Linters, analyzers, quality gate tools
- **§build-commands** — Build, test, lint, deploy commands
- **§ci-cd** — Pipeline configuration, environment progression
- **§qa-checklist** — Stack-specific review items

### Blueprint Projects (Local Only)

Each blueprint has an associated **real, buildable project** on the local filesystem (path defined in §project). These serve as reference implementations. Blueprint projects are **never committed to the harness repo** — they remain local.

---

## How to Read This Harness

| Audience | Start Here |
|----------|-----------|
| **First-time setup** | Jump to "Project Configuration" → copy directories, configure blueprint, populate `.board/tasks.md`, run `/sprint` |
| **As an agent** | Start at "MANDATORY — Pipeline Enforcement" → follow phase guards → read the relevant skill for the current phase |
| **As a maintainer** | Rules in `.claude/rules/`, skills in `.claude/skills/`, roles in `.claude/agents/roles/`, blueprints in `.claude/blueprints/` |

**Key concept -- three building blocks:**
- **Skills** = phase executors (what to do). Each slash command (`/grill-spec`, `/plan`, `/implement`, etc.) maps to one skill that owns one phase.
- **Roles** = subagent briefings (who does it). Dev, QA, and Architect roles are loaded into subagents by skills -- they define expertise, not workflow.
- **Rules** = shared constraints (how to do it right). Quality gates, coding standards, board protocol -- enforced across all phases and roles.

---

## MANDATORY — Pipeline Enforcement

> These rules override ALL other behavior. They are not guidelines — they are hard constraints.
> Violating any of these is equivalent to a build failure.

### Law 1: State Machine Governs All

> **Why**: Without persistent state, the agent can't recover from crashes or session boundaries — it either restarts from scratch (wasting work) or guesses (producing errors). The state machine makes pipeline position deterministic and auditable. See [ADR-0002](docs/adr/0002-state-machine-governance.md).

- **Before executing ANY skill**: Read `.board/sprint-state.md` and verify the phase matches.
- **If phase mismatch**: REFUSE to execute. Print phase guard failure. Suggest correct action.
- **After completing ANY skill**: Update `.board/sprint-state.md` with new phase + timestamp + artifacts.
- **Sprint state is canonical.** If sprint-state says GRILL_SPEC, you are in GRILL_SPEC. Period.

### Law 2: No Phase Skipping

> **Why**: The most common AI development failure is jumping straight to code — skipping spec clarification, planning, and test design. Phase skipping is the root cause of spec amnesia, untested code, and rework. Even "simple" tasks reveal hidden complexity during grill-spec and planning. See [ADR-0001](docs/adr/0001-six-phase-pipeline.md).

```
IDLE → TRIAGE → GRILL_SPEC → PLAN → IMPLEMENT → TEST_VERIFY → FINISH → IDLE
```

You CANNOT:
- Write implementation code unless sprint-state Phase = IMPLEMENT
- Write test code (beyond TDD in /implement) unless Phase = TEST_VERIFY
- Create a PR unless Phase = FINISH
- Start a new task unless Phase = IDLE
- Run /plan without an approved spec (Spec Approved = Yes in sprint-state)
- Run /implement without an approved plan (Plan Approved = Yes in sprint-state)
- Run /finish without quality gates passing (Quality Gate = PASS in sprint-state)

### Law 3: Artifacts Gate Progression

> **Why**: Conversation claims ("the spec is done") are unverifiable after compaction and unfalsifiable by audit. Files on disk either exist or they don't — binary, persistent, auditable. This prevents the "I'll do it properly later" pattern. See [ADR-0006](docs/adr/0006-artifact-gating.md).

Each phase produces artifacts. The next phase MUST verify these exist:

| Phase | Produces | Next Phase Checks |
|-------|----------|-------------------|
| GRILL_SPEC | `docs/specs/TASK-ID-spec.md`, CONTEXT.md entries | /plan verifies spec file exists |
| PLAN | `PLAN.md`, `docs/tech-context/TASK-ID-tech.md` | /implement verifies PLAN.md exists, tech context available |
| IMPLEMENT | Code + tests on feature branch | /test-verify verifies branch exists, tests pass |
| TEST_VERIFY | `docs/reports/TASK-ID-quality.md` | /finish verifies report exists, gates pass |
| FINISH | PR on remote | /sprint verifies task in Done |

If ANY artifact is missing → STOP. Report what's missing. Do NOT improvise.

### Law 4: Board Lock Protocol

> **Why**: During IMPLEMENT, the orchestrator and multiple subagents write to tasks.md concurrently (progress updates, subtask checkboxes). Without mutual exclusion, concurrent writes corrupt the file — one agent's changes silently overwrite another's. See [ADR-0003](docs/adr/0003-board-lock-file-based.md).

Before ANY write to `.board/tasks.md`:
1. Check `.board/board.lock` — if fresh lock exists, WAIT and retry (3x max)
2. Acquire lock (create file with holder + timestamp + operation)
3. Read board FRESH
4. Write changes
5. Release lock (delete file)
6. Log in sprint-state Phase History

See `.claude/rules/board-protocol.md` for full protocol.

### Law 5: Human Checkpoints Are Blocking

> **Why**: Without blocking gates, the agent approves its own work — generates a spec, approves it, plans it, implements it, passes its own quality review, ships a PR. This defeats spec-driven development entirely. The four checkpoints are the minimum set where human judgment is irreplaceable.

Four mandatory human gates. Silence is NOT approval.

| Gate | When | What Human Does |
|------|------|----------------|
| Spec approval | After /grill-spec | Approves refined spec |
| Plan approval | After /plan | Approves micro-task breakdown |
| Quality review | After /test-verify | Reviews coverage + static analysis reports |
| Merge decision | After /finish | Merges, requests review, or discards PR |

At each gate: present the deliverable clearly, then WAIT. Do not proceed until the human explicitly approves.

### Law 6: Context Budget Is a Hard Limit (200K Tokens)

> **Why**: After ~200K tokens (empirically: 2 auto-compactions), output quality degrades measurably — forgotten decisions, contradictions, vaguer code, missed edge cases. Token-bounding replaces arbitrary time limits with the actual limiting resource. Multi-session execution via handover is the expected path for complex tasks, not a failure mode. See [ADR-0004](docs/adr/0004-token-bounded-execution.md).

The pipeline is **token-bounded, not time-bounded**. It runs until the board is empty or context is exhausted.

**Enforced**: `context-persistence.py` hooks auto-save session state to `.state/boss-session.md` on every compaction (PreCompact) and session end (Stop). SessionStart:compact restores context automatically after compaction. The `/handover` skill remains available for deliberate, detailed checkpoints — manual handovers take priority over auto-saved state.

- **Before EVERY phase transition**: run context budget check (see `.claude/rules/context-management.md`)
- **When output quality degrades** (forgotten decisions, vague output, repeated questions) = mandatory handover via `/handover` at next phase boundary
- **Before token-heavy phases** (IMPLEMENT, TEST_VERIFY) in a long session = mandatory handover
- **Before lighter phases** = `/compact` with focus, continue

When handover triggers:
1. Complete the current phase step (never hand over mid-skill)
2. Invoke `/handover` — produces `docs/handover/TASK-ID-handover.md`
3. Stop the sprint loop
4. Next session: `/sprint` reads sprint-state and resumes from the exact phase

Complex tasks spanning multiple sessions is EXPECTED behavior, not a failure.
The artifact chain (spec → plan → code → report → PR) persists on disk across sessions.

---

## The Pipeline

```
Phase 0        Phase 1         Phase 2          Phase 3           Phase 4          Phase 5
BOARD TRIAGE → GRILL SPEC   → PLANNING      → IMPLEMENTATION  → TEST & VERIFY → FINISH
/sprint        /grill-spec    /plan            /implement         /test-verify     /finish
pick task      adversarial    Context7 docs    SDD + TDD          analysis +       PR + CAB +
               interview      + micro-tasks    subagent/task      integration      board update
               → spec.md      → tech.md        RED→GREEN→REFAC    → report.md      → PR
               → CONTEXT.md   → PLAN.md        feature branch     quality gates    → Done
               → ADRs         verification
```

### Phase 0 — Board Triage (/sprint)

Pick highest-priority uncompleted task. Load spec. If no spec exists, create one.

- **Entry**: /sprint invoked or sprint loop continues
- **State**: IDLE → TRIAGE
- **Exit**: Task selected, spec loaded → transition to GRILL_SPEC
- **Invoke next**: /grill-spec

### Phase 1 — Spec Grill (/grill-spec)

Adversarial interview. One question at a time. Concurrent domain modeling — while interviewing the human, also explore existing codebase patterns and the domain glossary to ground decisions in what already exists.

- **Entry**: Sprint-state Phase = GRILL_SPEC
- **Produces**: `docs/specs/TASK-ID-spec.md`, CONTEXT.md entries, ADRs

#### Domain Glossary (CONTEXT.md)

`docs/CONTEXT.md` is a cumulative domain glossary maintained during `/grill-spec`. It captures terms that were ambiguous or contested during adversarial review.

Table format (see `artifact-standards.md` for the full spec-level format):

```
| Term | Definition | Used In Code As | Avoid |
```

- **Term**: The canonical domain concept (e.g., "TradeOrder")
- **Used In Code As**: The class/property name that dev subagents MUST use for naming
- **Avoid**: Ambiguous synonyms that MUST NOT appear in code (e.g., "Order", "Trade")
- Entries are never removed — only added or amended
- Dev and QA subagents receive CONTEXT.md in their prompt and must respect it
- **Gate**: 🧑 Human approves refined spec
- **State**: GRILL_SPEC → PLAN (on approval)
- **Exit**: Spec approved, artifacts registered in sprint-state
- **Invoke next**: /plan

### Phase 2 — Planning (/plan)

Documentation discovery via Context7 MCP, then decompose spec into micro-tasks (2-5 min each). File paths, code snippets verified against current docs, verification steps.

- **Entry**: Sprint-state Phase = PLAN, Spec Approved = Yes
- **Step 1.5**: Query Context7 MCP for current library docs relevant to this task → `docs/tech-context/TASK-ID-tech.md`
- **Produces**: `PLAN.md`, `docs/tech-context/TASK-ID-tech.md`
- **Gate**: 🧑 Human approves plan
- **State**: PLAN → IMPLEMENT (on approval)
- **Exit**: Plan approved, artifacts registered
- **Invoke next**: /implement

### Phase 3 — Implementation (/implement)

Subagent-Driven Development. One subagent per micro-task. TDD enforced.

- **Entry**: Sprint-state Phase = IMPLEMENT, Plan Approved = Yes
- **Produces**: Code + tests on feature branch
- **State**: IMPLEMENT → TEST_VERIFY (when all tasks complete + tests green)
- **Exit**: All micro-tasks done, test suite passes (per blueprint §build-commands)
- **Invoke next**: /test-verify

### Phase 4 — Test & Verify (/test-verify)

Two-agent pattern. Integration tests, static analysis (per blueprint §static-analysis), quality reports.

- **Entry**: Sprint-state Phase = TEST_VERIFY
- **Produces**: `docs/reports/TASK-ID-quality.md`
- **Gate**: 🧑 Human reviews quality report
- **State**: TEST_VERIFY → FINISH (on review + gates pass)
- **Exit**: Quality gates pass, report registered
- **Invoke next**: /finish

### Phase 5 — Finish (/finish)

Create PR with CAB ticket + release checklist, update board, transition Jira, cleanup.

- **Entry**: Sprint-state Phase = FINISH, Quality Gate = PASS
- **Produces**: PR on remote, board task in Done
- **Gate**: 🧑 Human decides merge/review/discard
- **State**: FINISH → IDLE
- **Exit**: PR created, board updated, sprint-state reset
- **Invoke next**: /sprint (for next task) or stop

---

## Sprint Loop (/sprint)

Orchestrates the full pipeline. Token-bounded, not time-bounded.
Reads sprint-state to resume from interrupted or handed-over sprints.

```
ON START:
  READ .board/sprint-state.md
  CHECK docs/handover/ for handover document (if resuming)
  IF Phase ≠ IDLE → RESUME from current phase (do not restart)
  IF Phase = IDLE → pick next task from board

LOOP:
  TRIAGE:      pick task, load spec
                 → UPDATE state → GRILL_SPEC
  GRILL_SPEC:  CONTEXT CHECK → INVOKE /grill-spec → WAIT approval
                 → UPDATE state → PLAN
  PLAN:        CONTEXT CHECK → INVOKE /plan → WAIT approval
                 → UPDATE state → IMPLEMENT
  IMPLEMENT:   CONTEXT CHECK → INVOKE /implement → WAIT completion
                 → UPDATE state → TEST_VERIFY
  TEST_VERIFY: CONTEXT CHECK → INVOKE /test-verify → WAIT review
                 → UPDATE state → FINISH
  FINISH:      CONTEXT CHECK → INVOKE /finish → WAIT merge decision
                 → UPDATE state → IDLE
  /clear context
  CONTINUE LOOP

CONTEXT CHECK (before each phase):
  IF quality degraded (vague output, repeated questions) → INVOKE /handover → STOP
  IF long session + next phase is IMPLEMENT or TEST_VERIFY → INVOKE /handover → STOP
  IF long session + next phase is lighter → /compact with focus → CONTINUE
  IF session is fresh → CONTINUE
  NOTE: PreCompact hook auto-saves state on every compaction. Manual check is a safety net.

STOP WHEN: board empty | human says stop | context budget triggers handover
```

Between tasks: `/clear` is MANDATORY. Each task starts with clean context.
Between sessions: `/handover` produces a document. Next `/sprint` reads it to resume.

### Phase History Format

Each phase transition appends a row to the sprint-state Phase History table:

```
| Timestamp | Task | From Phase | To Phase | Gate | Notes |
| 2026-06-22T14:30Z | COS-042 | GRILL_SPEC | PLAN | spec-approved | 3 ACs, 2 CONTEXT.md terms added |
```

---

## Quality Gates

All thresholds and measurement procedures are defined in `.claude/rules/quality-gates.md` (single source of truth).

Key gates (summary — refer to quality-gates.md for detailed scoping):
- **Unit coverage**: Business logic >= 80%, Infrastructure >= 60%, Overall >= 75%
- **Static analysis**: Zero linter warnings in new code, quality gate pass (per blueprint §static-analysis)
- **Integration tests**: All pass (using test infrastructure per blueprint §test-stack)
- **AC coverage**: Every acceptance criterion mapped to at least one passing test
- **Hard fail**: Any gate below minimum blocks progression to /finish

---

## Law 6: Artifact Quality Standards

Every artifact MUST meet the gold standard defined in `.claude/rules/artifact-standards.md`.

- **Anti-slop rules apply to ALL output**: no placeholders, no single-sentence sections, no vague AC, no unnamed entities
- **Each skill validates its inputs** against the standards before proceeding
- **Each skill produces outputs** matching or exceeding the standards' examples
- **The examples in artifact-standards.md are the FLOOR, not the ceiling** — richer output is always preferred
- **Cross-artifact traceability**: every AC in the spec must appear in plan → tests → quality report → PR

If an artifact's quality is below the standard → the skill that produced it MUST iterate before the pipeline advances.

---

## Strategic Documentation

| File | Content |
|------|---------|
| `docs/DESIGN.md` | **Design philosophy, source attribution, core principles, rationale for every law** |
| `docs/SCOPE.md` | **What the harness is/isn't, adaptation guide, assumptions** |
| `docs/adr/0001-*.md` through `0007-*.md` | **Architecture Decision Records for the harness's own design choices** |

## Rules (detailed)

| File | Content |
|------|---------|
| `artifact-standards.md` | **Gold standard templates and anti-slop rules for every phase output** |
| `context-management.md` | **Token budget model, compaction triggers, handover protocol, multi-session execution** |
| `state-management.md` | Sprint state machine, board lock protocol, artifact chain, session recovery |
| `workflow-pipeline.md` | Phase guards, transitions, failure handling, parallelism |
| `board-protocol.md` | Task format, board sections, write protocol, subagent access |
| `quality-gates.md` | Coverage thresholds, static analysis, review policy |
| `coding-standards.md` | Universal coding conventions + pointer to active blueprint |
| `enterprise-blueprint.md` | Universal enterprise constraints + pointer to active blueprint |

---

## Agent Roles

The pipeline uses three specialist roles, spawned as subagents by skills:

| Role | File | Spawned By | Purpose |
|------|------|-----------|---------|
| Developer | `.claude/agents/roles/dev.md` | /implement, /test-verify | Executes micro-tasks with TDD enforced |
| QA Reviewer | `.claude/agents/roles/qa.md` | /test-verify | Reviews spec compliance, code quality, blueprint patterns |
| Architect | `.claude/agents/roles/arch.md` | /plan | Validates layer placement, enterprise patterns, creates ADRs |

Each role receives a focused briefing with the spec, CONTEXT.md, the active blueprint's reference.md, and relevant artifacts. Roles are not interchangeable — dev writes code, QA reviews it, arch validates structure.

The arch role is invoked during /plan to validate that every new file maps to the correct architectural layer (per blueprint §architecture) and that dependency direction is correct. If blueprint deviations are identified, arch creates Deviation Record tasks.

### Subagent Execution

Skills spawn subagents using Claude Code's `Agent()` tool. Each subagent receives:

1. **Role briefing**: The full content of the role file (e.g., `.claude/agents/roles/dev.md`)
2. **Task-specific context**: Spec, PLAN.md task, CONTEXT.md, tech-context, blueprint reference.md — loaded into the agent's prompt
3. **Branch**: The feature branch to work on

```
Agent(
  prompt: "[role file content]\n\n## Your Task\n[task from PLAN.md]\n\n## Context\n[CONTEXT.md + tech-context + blueprint reference]",
  description: "Dev: [task title]",
  run_in_background: true  // for parallel micro-tasks
)
```

**Orchestration rules**:
- Max 4 concurrent subagents (diminishing returns beyond that)
- Each subagent works on ONE micro-task — never multiple
- Orchestrator waits for completion, reads result, verifies tests pass
- If subagent fails 3 times → BLOCKED (three-strike rule)
- Subagent results are summarized by orchestrator — full output stays in subagent context

---

## Anti-Patterns

### Sprint Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Skip phases | Artifacts won't exist for downstream phases | Follow the sequence -- IDLE through FINISH |
| Run skills out of sequence | Phase guards will reject, but don't rely on them as your workflow | Check sprint-state before invoking any skill |
| Ignore phase guards | They exist to prevent cascade failures | Fix the root cause (complete current phase first) |
| Continue after handover trigger | Context degradation produces buggy output | Run `/handover`, stop, resume next session |

### Artifact Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Placeholder content ("TBD", "TODO") | Blocks downstream phases, violates artifact standards | Write the real content or mark the task BLOCKED |
| Vague AC ("system should work") | Untestable, unverifiable, will fail quality gates | Specific, measurable criteria with concrete values |
| Missing traceability | AC appears in spec but not in plan/tests/report | Every AC threads through the full artifact chain |
| Single-sentence spec sections | Fails anti-slop rules in `artifact-standards.md` | Expand with context, constraints, and examples |

### Context Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Read entire files when you need 10 lines | Burns context budget, triggers early compaction | Use `offset`/`limit` on Read, delegate exploration to subagents |
| Skip `/handover` when quality degrades | Quality degrades silently in long sessions | Follow context budget rules in Law 6; hooks auto-save state but `/handover` is the deliberate checkpoint |
| Ignore quality degradation signals | Vague output, repeated questions, forgotten decisions | `/handover` at next phase boundary, resume fresh |
| Load all rules/roles into main context | Wastes tokens on reference material | Load into subagent prompts where they're needed |

### Code Anti-Patterns

| Don't | Why | Instead |
|-------|-----|---------|
| Implement before writing tests | Violates TDD (RED-GREEN-REFACTOR) | Write failing test first, then implement to green |
| Swallow errors silently | Hides bugs, fails static analysis | Catch specific errors, log or rethrow |
| Ignore blueprint conventions | Breaks consistency, fails QA review | Follow the active blueprint's reference.md patterns |
| Use wrong architectural layer | Violates dependency direction | Check blueprint §architecture for correct placement |

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Phase guard failure | Wrong phase in `sprint-state.md` | Read sprint-state, complete the current phase before invoking the next skill |
| Board locked | Stale `.board/board.lock` file | Check lock timestamp -- if older than 60 seconds, delete the lock file |
| Quality gate HARD FAIL | Coverage below minimum threshold | Add missing tests to reach the gate; do not override thresholds |
| Context budget exceeded | Too many file reads or 2+ auto-compactions | Run `/compact` with focus or `/handover` at next phase boundary |
| Subagent fails 3x | Three-strike rule triggered | Mark the micro-task BLOCKED, report to human with failure details |
| Spec not found after TRIAGE | Task on board has no spec file yet | `/grill-spec` will create one -- this is normal for new tasks |
| Tests fail in IMPLEMENT | RED-GREEN cycle incomplete | Fix failing tests before transitioning to TEST_VERIFY |
| Handover doc missing on resume | Previous session crashed before `/handover` | Read sprint-state for current phase, reconstruct context from artifacts on disk |

---

## Session Recovery

When starting a new session or resuming after a crash:

1. Read `.board/sprint-state.md`
2. If Phase ≠ IDLE → resume from that phase, announce what you're resuming
3. If `.board/board.lock` exists and is stale (> 60s) → delete it
4. If Phase = IDLE → clean state, ready for /sprint

---

## Project Configuration

### Required
1. `.board/tasks.md` — populated with prioritized tasks
2. `.board/sprint-state.md` — initialized (copy from this harness)
3. Active blueprint configured (see "Active Blueprint" section above)
4. Project's source code in the working directory

### Optional
- **Jira**: Add project key, board ID, transition IDs to this file
- **Quality overrides**: Edit `.claude/rules/quality-gates.md`
- **Custom blueprint**: Create a new `.claude/blueprints/<name>/reference.md` (see existing blueprints for the format)

### Adapting for Your Project
1. Copy `.claude/`, `.board/`, `docs/`, `templates/` directories into your project
2. Set the Active Blueprint in this file to match your stack
3. If your stack isn't covered by existing blueprints, create a new `reference.md` following the section format (§project, §stack, §architecture, §coding-standards, §enterprise-patterns, §test-stack, §static-analysis, §ci-cd, §qa-checklist, §build-commands)
4. Edit this CLAUDE.md for project-specific config (Jira, paths, domain)
5. Populate `.board/tasks.md` with your backlog
6. Run `/sprint` to begin

### Creating a New Blueprint

To add support for a new technology stack:

1. Create directory: `.claude/blueprints/<stack-name>/`
2. Create `reference.md` with all required sections (use existing blueprints as templates)
3. Create the blueprint project locally (a real, buildable reference implementation)
4. Update the "Available Blueprints" table in this file
5. Set it as the Active Blueprint to activate

### Deviation Records

When code deviates from the active blueprint, a Deviation Record MUST be created at `docs/deviations/DEV-NNN-[slug].md`. See `templates/deviation-record.md` for the template. See `enterprise-blueprint.md` for when deviations require documentation.

---

*Spec-driven development harness for Claude Code*
*State-machine enforced, board-locked, artifact-gated*
*Stack-agnostic via pluggable blueprint system*
