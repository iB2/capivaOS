# ADR-0007: Blueprint Plugin Architecture — Reference Injection

## Status

Accepted

## Context

The Capiva OS harness currently hardcodes .NET/C# patterns throughout agent roles, skills, and rules. This coupling prevents reuse with other technology stacks (Python/FastAPI, Node/TypeScript, Go, etc.) even though the pipeline structure (6 phases, state machine, artifact gating, board protocol, context management) is inherently stack-agnostic.

An audit of the harness's 41 files revealed:
- **13 files** are fully universal (pipeline, state machine, board protocol, artifact standards, context management)
- **7 files** are 100% .NET-specific (coding-standards.md, enterprise-blueprint.md, quality-gates.md, templates/*.props, templates/azure-pipelines.yml)
- **21 files** are mixed — universal structure with .NET content embedded inline (agent roles, skills, CLAUDE.md, README.md, SCOPE.md, DESIGN.md)

The mixed files are the hardest problem. Simply extracting .NET content into separate files would break the performance model — agents need stack-specific instructions in their context window to produce correct code. The challenge is: how to make the harness stack-agnostic while ensuring agents always have concrete, stack-specific instructions available.

### Constraints

1. **Performance**: Agent subagents (dev, qa, arch) must receive stack-specific instructions in their prompt context. Lazy loading or "go read file X" degrades output quality.
2. **Simplicity**: Switching stacks should be a single configuration change, not a 20-file edit.
3. **Real projects**: Blueprints are real, buildable projects (not markdown descriptions). A .NET blueprint is a .NET solution with controllers, use cases, tests, and pipelines. A Python blueprint is a FastAPI app with routes, services, tests, and Dockerfiles.
4. **Extensibility**: Adding a new stack (e.g., Go/Gin) should require creating one blueprint project and one reference file — no harness core changes.

### Options Considered

**Option A: Template Inheritance (file-level override)**
- Blueprint directories contain override files (e.g., `blueprints/dotnet/dev.md` replaces `agents/roles/dev.md`)
- Pro: Simple mental model — files override files
- Pro: Easy to see what's different per stack
- Con: Massive duplication — the universal parts of dev.md are copied into every blueprint's dev.md
- Con: Updates to universal pipeline logic require editing every blueprint's copy
- Con: Drift risk — blueprint copies diverge from harness originals over time

**Option B: Reference Injection (chosen)**
- Universal files stay in the harness with stack-specific content removed
- Each blueprint has a `reference.md` file that contains: (1) pointer to the real project, (2) all stack-specific instructions extracted from agent roles, skills, and rules
- Agent roles and skills contain a loading directive: "Read the active blueprint's reference.md for stack-specific patterns"
- The active blueprint is configured in CLAUDE.md via a single path
- Pro: Zero duplication of universal logic — one source of truth for pipeline behavior
- Pro: Switching stacks = changing one path in CLAUDE.md
- Pro: reference.md is a self-contained document — agents get all stack-specific context in one read
- Con: reference.md files can grow large (but this is bounded — it's the sum of extracted sections)
- Con: Agents must perform one extra file read (reference.md) at the start of each phase

**Option C: Parameterized Templates (variable substitution)**
- Agent roles and skills use `{{STACK_TEST_COMMAND}}`, `{{STACK_BUILD_COMMAND}}` variables
- A config file maps variables to values per stack
- Pro: No extra file reads — variables resolve inline
- Con: Extremely brittle — every new stack-specific concept requires a new variable
- Con: Complex patterns (code examples, architecture diagrams) don't fit in variables
- Con: Config file becomes a massive, unreadable key-value dump

## Decision

**Option B — Reference Injection.**

The harness discovers the active blueprint through a configuration section in `.claude/CLAUDE.md`:

```markdown
## Active Blueprint

Blueprint: `.claude/blueprints/dotnet-hexagonal/reference.md`
```

Each reference.md file contains:

1. **Project pointer**: Local path (and future: remote repo URL) to the real blueprint project
2. **Stack identity**: Language, runtime, framework, versions
3. **Coding standards**: The full coding standards extracted from the harness (currently in `coding-standards.md`)
4. **Architecture patterns**: Hexagonal/Clean/etc. patterns with code examples (currently in `enterprise-blueprint.md`)
5. **Test stack**: Frameworks, assertion libraries, container tools, commands (currently in `quality-gates.md`)
6. **Build & verify commands**: `dotnet test`, `pytest`, `go test`, etc. (currently hardcoded in skills)
7. **CI/CD patterns**: Pipeline configuration guidance (currently in `enterprise-blueprint.md`)
8. **Static analysis**: Linter/analyzer configuration (currently in `quality-gates.md`)

Agent roles (dev.md, qa.md, arch.md) and skills (/implement, /plan, /test-verify, /finish) reference the active blueprint's reference.md instead of containing stack-specific content inline. The loading pattern is:

```
BEFORE executing any stack-specific work:
1. Read the active blueprint path from .claude/CLAUDE.md "Active Blueprint" section
2. Read the referenced reference.md file
3. Use the stack-specific patterns, commands, and standards from that file
```

Option A was rejected because duplication creates drift — when we improve the pipeline, we'd need to update every blueprint's copy of every file. Option C was rejected because parameterization works for simple values but breaks down for the rich, contextual instructions that agents need (code examples, architectural patterns, decision frameworks).

## Consequences

- **Positive**: The harness core becomes truly stack-agnostic. Adding a new stack requires: (1) create a real project in DevProjects, (2) write one reference.md file, (3) update the path in CLAUDE.md. No harness files change.
- **Positive**: Universal pipeline improvements (new phase, better artifact standards, context management tweaks) automatically apply to all stacks — they live in the harness, not in blueprints.
- **Positive**: reference.md is auditable — you can diff two stacks' reference files to see exactly what differs.
- **Negative**: Agents perform one extra file read per phase (reference.md). This costs ~2-5K tokens per read. Acceptable given the typical 200K context budget.
- **Negative**: reference.md files must be kept in sync with their blueprint projects. If the blueprint project evolves (new patterns, updated versions), the reference.md must be updated too. This is manual — no automated sync.
- **Future consideration**: When blueprint projects move to remote repositories (Azure DevOps), the reference.md pointer format will need to support repo URLs alongside local paths. The current design accommodates this — the pointer section is free-form text, not a parsed path.
