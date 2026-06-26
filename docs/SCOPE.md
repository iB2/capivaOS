# Scope — What This Harness Is and Isn't

## What This Harness IS

A **development pipeline enforcer** for Claude Code that structures how AI agents build production-quality .NET code. It is:

- **A state machine** that prevents skills from running out of sequence
- **A quality framework** that gates progression on artifacts, tests, and human approval
- **A multi-session execution model** that handles context limits gracefully via handover
- **A board-driven task manager** that persists state to disk, not conversation memory
- **A spec-first discipline** that forces requirements clarity before implementation
- **A TDD enforcer** that makes "code without test" mechanically impossible in the pipeline

### Target Use Cases

| Use Case | Fit | Notes |
|----------|-----|-------|
| New feature development (.NET) | Excellent | The primary design target |
| Bug fixes with clear reproduction | Good | Full pipeline ensures the fix is tested and spec'd |
| API endpoint implementation | Excellent | Spec → plan → implement → verify maps naturally |
| Database schema changes | Good | Grill-spec catches migration edge cases early |
| Complex refactoring | Fair | Pipeline adds overhead but prevents regression |
| Infrastructure/DevOps changes | Poor | Pipeline assumes code + test artifacts — infra changes don't always produce these |
| Documentation-only tasks | Poor | Use P4 priority to bypass quality gates |
| Exploratory spikes | Acceptable | Use P4 — no spec or quality gates required |

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

If you use Jira, the harness can transition Jira tickets (optional integration in `/finish`), but the board is the sprint-level source of truth.

### Not Language-Agnostic (Currently)

The pipeline structure (6 phases, state machine, artifact gating) is language-agnostic. But the implementation details are .NET-specific:

- Test stack: xUnit, NSubstitute, AwesomeAssertions, Testcontainers, Stryker.NET
- Quality gates: `dotnet test`, `dotnet build`, coverage via Coverlet
- Coding standards: C# 12+, .NET 8+, nullable reference types
- Azure Functions: isolated worker model constraints
- Static analysis: SonarQube, StyleCop

**Adapting to other stacks**: Replace `.claude/rules/quality-gates.md` and `.claude/rules/coding-standards.md` with your stack's equivalents. Replace test commands in skills. The pipeline phases, state machine, board protocol, and artifact standards are reusable as-is.

### Not a Framework or Library

You don't import this or add it as a dependency. You **copy** the `.claude/`, `.board/`, and `docs/` directories into your project. It becomes part of your project's Claude Code configuration.

### Not Suitable for Fully Autonomous Operation

The harness has four blocking human checkpoints by design. It cannot run unattended through a full task lifecycle. This is intentional — see [DESIGN.md](DESIGN.md) "Human in the Loop, Machine in the Pipeline."

If you need fully autonomous AI development (no human approval gates), this harness is not the right tool. Consider removing the checkpoint enforcement, but understand you're removing the quality guarantee that comes with it.

---

## Assumptions

The harness assumes:

1. **Claude Code is the execution agent.** Skills use Claude Code slash commands and tool conventions. The harness doesn't work with other AI coding assistants without modification.

2. **Context7 MCP is available.** The `/plan` skill queries Context7 for current library documentation. If Context7 is not configured, the skill logs a warning and falls back to training data — but the quality guarantee is weakened.

3. **Docker is available.** Integration tests use Testcontainers, which requires Docker. Without Docker, integration tests cannot run, and quality gates that require them will fail.

4. **Git is initialized.** The pipeline creates feature branches, commits, and PRs. A git repository must exist.

5. **The project compiles.** `dotnet build` and `dotnet test` must succeed on the base branch before the pipeline starts. The harness doesn't fix existing build failures.

6. **Tasks are well-scoped.** The pipeline works best with tasks that can be specified, planned, and implemented in 1-3 sessions. Epics should be broken into tasks before entering the board.

---

## Adaptation Guide

### Adding a New Phase

If you need to add a phase (e.g., SECURITY_REVIEW between TEST_VERIFY and FINISH):

1. Update the state machine in `.claude/rules/state-management.md` — add the new state and its valid transitions
2. Update the phase guard matrix in `.claude/rules/workflow-pipeline.md`
3. Create the new skill in `.claude/skills/your-phase/SKILL.md` with phase guard
4. Update `.claude/CLAUDE.md` — pipeline diagram, Law 2 transitions, phase table
5. Update `docs/workflow-complete.mmd` — Mermaid diagram
6. Create an ADR in `docs/adr/` explaining why the new phase was needed

### Removing a Phase

Not recommended — each phase solves a specific problem (see [DESIGN.md](DESIGN.md) for rationale). If you must:

1. Document WHY in an ADR (what problem does removing it cause, and how will you mitigate?)
2. Update all files listed in "Adding a New Phase" above
3. Ensure artifact gating still works (the phase before and after must connect)

### Changing Quality Thresholds

Edit `.claude/rules/quality-gates.md`. The thresholds are:
- **Target**: what you aim for (soft ceiling)
- **Hard fail**: below this, the PR cannot proceed (hard floor)

Current values are calibrated for enterprise .NET development. Tighter thresholds (e.g., 90% coverage minimum) increase pipeline friction. Looser thresholds (e.g., 50% coverage minimum) weaken the quality guarantee. Document any changes in an ADR.

### Adapting for Another Language

1. Replace `.claude/rules/coding-standards.md` with your language's conventions
2. Replace `.claude/rules/quality-gates.md` with your test/coverage/analysis tooling
3. Update test commands in all skills (`dotnet test` → your equivalent)
4. Update `.claude/agents/roles/dev.md` and `qa.md` with your language's patterns
5. Keep everything else — the pipeline, state machine, board protocol, artifact standards, and context management are language-independent

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
