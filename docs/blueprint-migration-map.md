# Blueprint Migration Map — File Classification & Destination

> **HISTORICAL RECORD — pre-plugin layout.** The paths below reflect the
> pre-ADR-0013 copy-mode layout (`.claude/skills/...`, `.claude/rules/...`)
> and do not resolve in the current repo (top-level `skills/`, `rules/`,
> `agents/`). Deliberately excluded from `harness_lint` scans; kept as the
> audit trail of the ADR-0007 blueprint separation.

This document maps every file in the harness to its classification (universal, stack-specific, or mixed) and its destination after the blueprint separation.

## Classification Legend

| Classification | Meaning | Action |
|---------------|---------|--------|
| **Universal** | No stack-specific content. Pipeline, state machine, board, context management. | Keep in harness as-is |
| **Stack-specific** | 100% tied to a specific technology stack (.NET, Python, etc.) | Move to blueprint reference.md or blueprint project |
| **Mixed** | Universal structure with stack-specific content embedded | Split: universal stays in harness, stack-specific migrates to reference.md |

---

## File-by-File Classification

### Agent Roles (`.claude/agents/roles/`)

| File | Classification | Stack-Specific Sections | Migration |
|------|---------------|------------------------|-----------|
| `dev.md` | **Mixed** | C# coding standards (lines 29-125), .NET test conventions (lines 127-144), code quality patterns (lines 146-152), TDD examples use C# syntax, `dotnet test` commands | **Split**: Keep universal structure (what you receive, TDD cycle, task execution, completion report, must-not-do list). Move all C# patterns, .NET conventions, test stack details, and code examples to reference.md §coding-standards and §test-stack |
| `qa.md` | **Mixed** | Blueprint compliance checks reference .NET patterns (sealed, primary constructors, `this.` prefix, ProblemDetails), StyleCop/SonarQube references, AwesomeAssertions/Testcontainers/IAsyncLifetime specifics | **Split**: Keep universal structure (two-stage evaluation, verdict format, what you must not do). Move .NET-specific checks (blueprint compliance items, static analysis tools, test framework references) to reference.md §qa-checklist |
| `arch.md` | **Mixed** | Hexagonal Architecture .NET structure (src/Core, src/Driven, src/Drivers), C# layer placement table, EF Core/SQL Server references, technology stack assumptions | **Split**: Keep universal structure (responsibilities, ADR format, quality gate checklist, must-not-do). Move .NET architecture structure, layer placement table, and technology-specific references to reference.md §architecture |

### Skills (`.claude/skills/`)

| File | Classification | Stack-Specific Sections | Migration |
|------|---------------|------------------------|-----------|
| `sprint/SKILL.md` | **Universal** | None — orchestrates phases, reads state, no stack references | Keep as-is |
| `grill-spec/SKILL.md` | **Universal** | None — adversarial interview, spec production, domain modeling | Keep as-is |
| `plan/SKILL.md` | **Mixed** | Step 1.5 references `.csproj` files, `PackageReference` XML, Context7 examples use .NET libraries. Architecture enforcement section references Hexagonal .NET structure, enterprise patterns (Use Case, Bootstrapper, FluentValidation, ProblemDetails), deviation records for .NET blueprint. Layer assignments table uses .NET project paths. | **Split**: Keep universal structure (phase guard, process steps, output quality gate). Replace .NET-specific references with "Read active blueprint reference.md for: dependency file format, architecture patterns, layer placement rules, enterprise patterns, static analysis tools." |
| `implement/SKILL.md` | **Mixed** | `dotnet test` commands (lines 39, 117-118), feature branch conventions use .NET patterns | **Split**: Keep universal structure (phase guard, TDD enforcement, subagent spawning, parallel execution, board updates). Replace `dotnet test` with "Run the build/test command from the active blueprint reference.md". Replace .NET-specific code examples with generic references to blueprint patterns. |
| `test-verify/SKILL.md` | **Mixed** | `dotnet test` commands, Testcontainers C# setup code, StyleCop/SonarQube commands, AwesomeAssertions reference, .NET coverage tooling (Coverlet, ReportGenerator), TRX format, `.csproj` exclusion config | **Split**: Keep universal structure (phase guard, two-agent pattern, quality report format, gate evaluation). Move all test infrastructure code, static analysis commands, coverage tooling, and report formats to reference.md §test-stack and §static-analysis. |
| `finish/SKILL.md` | **Mixed** | `dotnet test` pre-flight check, Karma commit convention (partially universal), CAB ticket and release checklist are universal but examples reference .NET | **Split**: Keep universal structure (phase guard, PR creation, board update, Jira transition, cleanup, merge options). Replace `dotnet test` with generic build/test command from blueprint. Keep CAB/release/solution document templates as universal. |
| `handover/SKILL.md` | **Universal** | None — context serialization, no stack references | Keep as-is |

### Rules (`.claude/rules/`)

| File | Classification | Migration |
|------|---------------|-----------|
| `artifact-standards.md` | **Universal** | Keep as-is — defines artifact quality, not stack patterns |
| `board-protocol.md` | **Universal** | Keep as-is — task format, lock protocol, no stack refs |
| `coding-standards.md` | **Stack-specific** | **Move entirely** to reference.md §coding-standards. This file IS the .NET coding standard. In the harness, replace with a stub that says "Coding standards are defined in the active blueprint's reference.md." |
| `context-management.md` | **Universal** | Keep as-is — token budget, compaction, handover |
| `enterprise-blueprint.md` | **Stack-specific** | **Move entirely** to reference.md §architecture and §enterprise-patterns. This file IS the .NET enterprise blueprint. Replace with stub pointing to active blueprint. |
| `quality-gates.md` | **Mixed** | **Split**: Keep universal gate structure (thresholds table, gate enforcement rules, review policy, TDD enforcement, report artifacts). Move .NET test stack table, SonarQube/StyleCop specifics, Testcontainers setup, coverage commands to reference.md §test-stack. |
| `state-management.md` | **Universal** | Keep as-is — state machine, board lock, artifact chain |
| `workflow-pipeline.md` | **Mixed** | **Split**: Keep phase guards, transitions, failure handling, parallel rules. Remove `dotnet test`/`dotnet build` references (line 108-113), replace with "run build/test command from active blueprint." |

### Root Documents

| File | Classification | Migration |
|------|---------------|-----------|
| `.claude/CLAUDE.md` | **Mixed** | **Split**: Keep pipeline description, laws, anti-patterns, troubleshooting, session recovery. Remove: "spec-driven .NET development" → "spec-driven development". Remove .NET test stack section. Remove "Enterprise Architecture" hex diagram. Remove CI/CD Azure Pipelines section. Remove SDLC .NET mapping. Add "Active Blueprint" config section. Replace .NET-specific references with "See active blueprint reference.md." |
| `README.md` | **Mixed** | **Rewrite**: Stack-agnostic description. Explain blueprint concept. Keep pipeline/state machine/quick start. Remove .NET test stack table, .NET quality gates, .NET requirements. Add blueprint selection to quick start. |
| `docs/SCOPE.md` | **Mixed** | **Edit**: Change "Not Language-Agnostic (Currently)" section to explain blueprint system. Update target use cases. Keep adaptation guide but update for blueprint model. |
| `docs/DESIGN.md` | **Universal** | Minor edits only — design philosophy is stack-agnostic. Remove one mention of ".NET development" in the Problem section. |
| `docs/CONTEXT.md` | **Universal** | Keep as-is — domain glossary is project-specific, not stack-specific |

### Templates (`templates/`)

| File | Classification | Migration |
|------|---------------|-----------|
| `.editorconfig` | **Stack-specific** | Move to .NET blueprint project. Each blueprint project has its own .editorconfig. |
| `Directory.Build.props` | **Stack-specific** | Move to .NET blueprint project. |
| `Directory.Packages.props` | **Stack-specific** | Move to .NET blueprint project. |
| `azure-pipelines.yml` | **Stack-specific** | Move to .NET blueprint project. |
| `cab-ticket.md` | **Universal** | Keep in harness |
| `deviation-record.md` | **Universal** | Keep in harness |
| `release-checklist.md` | **Universal** | Keep in harness |
| `solution-document.md` | **Universal** | Keep in harness |

### Other Files

| File | Classification | Migration |
|------|---------------|-----------|
| `.board/sprint-state.md` | **Universal** | Keep as-is |
| `.board/tasks.md` | **Universal** | Keep as-is |
| `docs/adr/0001-0006` | **Universal** | Keep as-is — harness design decisions |
| `docs/adr/0007` | **Universal** | New — this blueprint architecture decision |
| `docs/workflow-complete.mmd` | **Universal** | Keep as-is |
| `.gitignore` | **Mixed** | Remove .NET-specific entries (bin/, obj/, *.dll). Keep generic entries. Each blueprint project has its own .gitignore. |

---

## Migration Summary

| Category | Universal | Stack-specific | Mixed → Split |
|----------|-----------|---------------|---------------|
| Agent roles | 0 | 0 | 3 (dev, qa, arch) |
| Skills | 3 (sprint, grill-spec, handover) | 0 | 4 (plan, implement, test-verify, finish) |
| Rules | 4 (artifact-standards, board-protocol, context-management, state-management) | 2 (coding-standards, enterprise-blueprint) | 2 (quality-gates, workflow-pipeline) |
| Root docs | 1 (DESIGN.md) | 0 | 3 (CLAUDE.md, README.md, SCOPE.md) |
| Templates | 4 (cab, deviation, release, solution) | 4 (.editorconfig, Build.props, Packages.props, pipelines) | 0 |
| Other | 7 (board files, ADRs, mermaid, CONTEXT.md) | 0 | 1 (.gitignore) |
| **Total** | **19** | **6** | **13** |

> **Note on counts**: ADR-0007's Context section cites an initial audit of "41 files: 13 universal / 7 .NET-specific / 21 mixed." That was the rough pre-analysis census that motivated the decision. This map is the file-by-file classification produced afterwards (38 classified entries: 19/6/13) — several files moved buckets on closer reading, and runtime/lock files were excluded. Where the two disagree, **this map is authoritative**.

---

## Reference File Structure

Each blueprint's `reference.md` receives the extracted stack-specific content organized into sections:

```
reference.md
├── §project — Pointer to blueprint project (local path, future: repo URL)
├── §stack — Language, runtime, framework, versions
├── §architecture — Layer structure, dependency rules, project organization
├── §coding-standards — Naming, patterns, code style, conventions
├── §enterprise-patterns — Use Case/Service, Repository, DI, validation, error handling
├── §test-stack — Frameworks, assertions, containers, commands
├── §static-analysis — Linters, analyzers, configuration
├── §ci-cd — Pipeline configuration, environments, deployment
├── §qa-checklist — Stack-specific items for QA review
└── §build-commands — Build, test, lint, coverage commands
```
