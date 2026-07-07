# Scope — What This Harness Is and Isn't

## What This Harness IS

A **development pipeline enforcer** for Claude Code that structures how AI agents build production-quality code. It is:

- **A state machine** that prevents skills from running out of sequence
- **A quality framework** that gates progression on artifacts, tests, and human approval
- **A multi-session execution model** that handles context limits gracefully via handover
- **A board-driven task manager** that persists state to disk, not conversation memory
- **A spec-first discipline** that forces requirements clarity before implementation
- **A TDD enforcer** that makes "code without test" mechanically impossible in the pipeline
- **Stack-agnostic** via pluggable blueprints — the pipeline is universal, stack-specific patterns are injected

### Target Use Cases

| Use Case | Fit | Notes |
|----------|-----|-------|
| New feature development | Excellent | The primary design target — works with any stack via blueprints |
| Bug fixes with clear reproduction | Good | Full pipeline ensures the fix is tested and spec'd |
| API endpoint implementation | Excellent | Spec → plan → implement → verify maps naturally |
| Database schema changes | Good | Grill-spec catches migration edge cases early |
| Complex refactoring | Fair | Pipeline adds overhead but prevents regression |
| Infrastructure/DevOps changes | Poor | Pipeline assumes code + test artifacts — infra changes don't always produce these |
| Documentation-only tasks | Poor | Use P4 priority to bypass quality gates |
| Exploratory spikes | Acceptable | Use P4 — no spec or quality gates required |

### Pipeline Lanes — When Each Applies

The harness has two state-machine paths (see [ADR-0010](adr/0010-fast-lane-pipeline.md)). **Full is the default**; the fast lane must be earned by a mechanical predicate evaluated at TRIAGE.

| | Full lane | Fast lane |
|---|-----------|-----------|
| Path | TRIAGE → GRILL_SPEC → PLAN → IMPLEMENT → TEST_VERIFY → FINISH | TRIAGE → SPEC_PLAN → IMPLEMENT → VERIFY_FINISH |
| Human gates | 4 (spec, plan, quality, merge) | 2 (spec+plan combined; quality+merge combined) |
| Applies to | P0/P1 always; any task creating files, touching schema/migrations, changing architecture, or adding dependencies; anything failing the predicate; anything ambiguous | P2/P3 tasks that modify existing files only, with no schema/migration changes, no architectural changes, and no new dependencies |
| Typical examples | New endpoint, new service, schema change, new integration | One-file bug fix with clear repro, copy/config change with a testable AC, small behavior tweak in an existing service |
| Unchanged in both | Board entry, sprint-state, TDD, `TASK-ID-acs.json` contract + end-to-end exercise (ADR-0009), quality thresholds, lint/static analysis | |

Lane rules:
- The human can always force the full lane; nothing can force a non-qualifying task fast.
- Scope growth mid-lane (a new file, schema change, architectural decision, or >4 micro-tasks discovered during /capiva:spec-plan or later) is a **mandatory abort to the full lane** — logged in Phase History, never silent.
- P4 (spike/exploratory) remains outside both lanes: no spec, no quality gates, explicitly experimental.

### Target Team Size

Designed for **solo developer or small team (1-3)** working with Claude Code as the primary implementation agent. The human provides direction, reviews, and approval; Claude Code executes the pipeline.

Not designed for large teams with their own CI/CD, code review, and project management — those teams already have the discipline this harness provides.

---

## What This Harness ISN'T

### Not a CI/CD Pipeline

The harness runs inside Claude Code sessions. It does NOT:
- Replace GitHub Actions, Azure Pipelines, or any CI system
- Run in a CI environment
- Deploy code
- Manage environments

It produces artifacts (PRs, quality reports) that feed INTO your CI pipeline. The harness ends at "PR created" — what happens after merge is your CI's job.

### Not a Project Management Tool

`.board/tasks.md` is a lightweight task board for the sprint loop. It does NOT:
- Replace Jira, Linear, or any project management tool
- Track cross-team dependencies
- Manage sprints across multiple projects
- Provide reporting or analytics

If you use Jira, the harness can transition Jira tickets (optional integration in `/capiva:finish`), but the board is the sprint-level source of truth.

### Not a Framework or Library

You don't import this or add it as a dependency. It installs as a **Claude Code plugin** (`/plugin marketplace add iB2/capivaOS` → `/plugin install capiva@capiva`); the engine lives in the plugin cache and updates centrally, while `/capiva:init` scaffolds your project's mutable state (`.board/`, docs skeleton). Air-gapped: add a local clone as the marketplace — no other network access exists (see SECURITY.md).

### Not Suitable for Fully Autonomous Operation

The harness has four blocking human checkpoints by design. It cannot run unattended through a full task lifecycle. This is intentional — see [DESIGN.md](DESIGN.md) "Human in the Loop, Machine in the Pipeline."

If you need fully autonomous AI development (no human approval gates), this harness is not the right tool. Consider removing the checkpoint enforcement, but understand you're removing the quality guarantee that comes with it.

---

## Blueprint System

The harness is stack-agnostic. Technology-specific patterns, commands, and standards are defined in **blueprint reference files** at `blueprints/<stack-name>/reference.md`.

### What's in the Harness (Universal)

- Pipeline phases, state machine, phase guards
- Artifact gating and quality gate thresholds
- Board protocol and lock mechanism
- Agent roles (dev, qa, arch) — reference the active blueprint for stack-specific patterns
- Skills (/capiva:grill-spec, /capiva:plan, /capiva:implement, /capiva:test-verify, /capiva:finish) — use blueprint commands
- Templates (CAB tickets, deviation records, release checklists)
- Context management and handover protocol

### What's in the Blueprint (Stack-Specific)

- Project structure and architecture rules
- Coding standards and naming conventions
- Enterprise patterns (service/use case, repository, DI, validation)
- Test framework, assertion library, integration test infrastructure
- Static analysis tools and quality gate tools
- Build, test, lint, and deploy commands
- CI/CD pipeline configuration

### Included Blueprints

| Blueprint | Stack | Architecture |
|-----------|-------|-------------|
| `dotnet-hexagonal` | .NET 10 / C# 13 | Hexagonal (Ports & Adapters) |
| `python-fastapi` | Python 3.13 / FastAPI | Layered Architecture |
| `nextjs-typescript` | Node.js 22 / Next.js 15+ / App Router | Feature-based colocation (Server/Client split) |

### Adding a New Blueprint

1. Create `blueprints/<stack-name>/reference.md` following the section format (§project, §stack, §architecture, §coding-standards, §enterprise-patterns, §test-stack, §static-analysis, §ci-cd, §qa-checklist, §build-commands)
2. Create a real, buildable reference project locally (blueprint projects stay local, never committed)
3. Set as active in CLAUDE.md
4. The harness will automatically use the new blueprint's patterns

---

## Assumptions

The harness assumes:

1. **Claude Code is the execution agent.** Skills use Claude Code slash commands and tool conventions. The harness doesn't work with other AI coding assistants without modification.

2. **Context7 MCP is available.** The `/capiva:plan` skill queries Context7 for current library documentation. If Context7 is not configured, the skill logs a warning and falls back to training data — but the quality guarantee is weakened.

3. **Stack toolchain is installed.** The active blueprint's §build-commands must be executable. The harness doesn't install toolchains.

4. **Git is initialized.** The pipeline creates feature branches, commits, and PRs. A git repository must exist.

5. **The project builds.** Build and test commands (per blueprint §build-commands) must succeed on the base branch before the pipeline starts. The harness doesn't fix existing build failures.

6. **Tasks are well-scoped.** The pipeline works best with tasks that can be specified, planned, and implemented in 1-3 sessions. Epics should be broken into tasks before entering the board.

---

## Project Setup (ADR-0013)

1. Install the plugin: `/plugin marketplace add iB2/capivaOS` then `/plugin install capiva@capiva` (or `claude plugin install capiva@capiva --scope project` for CI/teams)
2. Populate project docs: `docs/CONTEXT.md` (domain glossary) and `docs/specs/INTAKE-summary.md` (project scope — template at `${CLAUDE_PLUGIN_ROOT}/project-template/templates/intake-summary.md`)
3. Run `/capiva:init` — scaffolds `.board/` + docs skeleton, validates docs, detects your stack, writes `.board/harness-config.md`, stamps the schema version
4. Populate `.board/tasks.md` with your backlog
5. Run `/capiva:sprint` to begin; update the harness later with `/capiva:update`

Optional: Jira integration (project key/board ID in your project docs), quality-threshold overrides (documented deviation + ADR), custom blueprints in `capiva-blueprints/` (project overrides shipped).

## Adaptation Guide

### Adding a New Phase

If you need to add a phase (e.g., SECURITY_REVIEW between TEST_VERIFY and FINISH):

1. Update the state machine in `rules/state-management.md` — add the new state and its valid transitions
2. Update the phase guard matrix in `rules/workflow-pipeline.md`
3. Create the new skill in `skills/your-phase/SKILL.md` with phase guard
4. Update `rules/laws.md` — pipeline diagram, Law 2 transitions, phase table
5. Update `docs/workflow-complete.mmd` — Mermaid diagram
6. Create an ADR in `docs/adr/` explaining why the new phase was needed

### Removing a Phase

Not recommended — each phase solves a specific problem (see [DESIGN.md](DESIGN.md) for rationale). If you must:

1. Document WHY in an ADR (what problem does removing it cause, and how will you mitigate?)
2. Update all files listed in "Adding a New Phase" above
3. Ensure artifact gating still works (the phase before and after must connect)

### Changing Quality Thresholds

Edit `rules/quality-gates.md`. The thresholds are:
- **Target**: what you aim for (soft ceiling)
- **Hard fail**: below this, the PR cannot proceed (hard floor)

Current values are calibrated for production development. Tighter thresholds increase pipeline friction. Looser thresholds weaken the quality guarantee. Document any changes in an ADR.

### Adapting for a Different AI Agent

The harness is designed for Claude Code but the concepts transfer:
- **Phase guards** → any condition check before executing a workflow step
- **Artifact gating** → verify files exist before proceeding
- **Board lock** → any mutual exclusion mechanism for shared state
- **Handover** → any serialization of current state for resumption

The Claude Code-specific parts are: slash command invocation, subagent spawning, auto-compaction detection, and Context7 MCP integration.

---

*Scope document for the Spec-Driven Development Harness*
*Last updated: June 2026*
