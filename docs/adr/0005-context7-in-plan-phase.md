# ADR-0005: Context7 Documentation Lookup in /plan, Not /grill-spec

## Status

Accepted

## Context

Claude Code's training data has a knowledge cutoff. When writing code that uses external libraries (Testcontainers, Entity Framework, xUnit, etc.), the agent may use outdated API patterns — deprecated methods, removed parameters, changed signatures. This produces code that doesn't compile or behaves incorrectly.

Context7 MCP provides current library documentation lookup: `resolve-library-id` finds the library, `query-docs` retrieves current docs for specific topics. The question is WHERE in the pipeline to query it.

### Options Considered

**Option A: Query in /grill-spec (Phase 1)**
- During the adversarial interview, validate technical assumptions against current docs
- Pro: Catches "this API doesn't exist anymore" before any planning happens
- Con: During grill-spec, we don't yet know HOW we'll implement — we're still defining WHAT to build. Library API details are premature
- Con: The spec should be about business requirements and behavior, not library syntax
- Con: Wastes context on library docs that might not be needed if the approach changes during planning

**Option B: Query in /plan (Phase 2)**
- After the spec is approved and the approach is being designed, query Context7 for the specific APIs the plan will reference
- Pro: By this point we know WHAT libraries we need (from the spec's Technical Context + .csproj scan)
- Pro: We know WHAT APIs within those libraries we need (from the approach brainstorm)
- Pro: The code snippets in PLAN.md use CURRENT syntax — subagents receive correct patterns
- Pro: The tech context file persists on disk for subagent consumption
- Con: If an API turns out not to exist, we've already approved a spec that assumed it does (mitigated: the approach brainstorm happens AFTER Context7 lookup, so API discoveries inform the approach)

**Option C: Query in /implement (Phase 3)**
- Each subagent queries Context7 for its specific task's libraries
- Pro: Most targeted — each subagent only looks up what it needs
- Con: N subagents × M library queries = significant token overhead across subagents
- Con: Subagents have fresh context — spending it on documentation lookup reduces implementation capacity
- Con: No centralized tech context — if two subagents use the same library, they query independently
- Con: Inconsistency risk — subagent A might get different docs than subagent B for the same library

**Option D: Query as a standalone discovery phase (new Phase 1.5)**
- A separate phase between GRILL_SPEC and PLAN
- Pro: Clean separation of concerns
- Con: Adds a 7th phase to the pipeline — violates the "minimum phases" principle (ADR-0001)
- Con: Would require its own phase guard, state transition, artifact, and human checkpoint
- Con: The documentation lookup is a natural SUB-STEP of planning, not a separate phase

## Decision

**Query in /plan (Phase 2) as Step 1.5 (Option B).**

The documentation discovery is embedded within /plan as a sub-step between "Load Inputs" (Step 1) and "Brainstorm Approach" (Step 2). This positioning means:

1. Step 1 loads the spec → we know WHAT the task needs
2. **Step 1.5 queries Context7** → we know the CURRENT state of the APIs we'll use
3. Step 2 brainstorms the approach → informed by both the spec AND current library state
4. Step 3 decomposes into tasks → code snippets use verified, current syntax

### Output artifact

The tech context is written to `docs/tech-context/TASK-ID-tech.md` — a file that persists on disk and is passed to every subagent during /implement. This is:
- Centralized — one lookup, used by all subagents
- Persistent — survives handover and session transitions
- Auditable — you can see exactly what library docs informed the plan

### Fallback

If Context7 is unavailable or has no docs for a library:
- The skill logs: "Context7 had no docs for [library]. Using training data — verify manually."
- The gap is flagged in the plan's Risk Assessment section
- The pipeline continues — stale training data is better than no data, but the risk is made visible

## Consequences

- /plan takes ~5-15K additional tokens for Context7 queries (depending on library count)
- Code snippets in PLAN.md use current API patterns — subagents write correct code on first attempt
- `docs/tech-context/TASK-ID-tech.md` becomes a gated artifact — /implement verifies it exists
- The approach brainstorm is informed by real API state, not assumptions
- If Context7 is down, the pipeline degrades gracefully (logs warning, flags risk) rather than blocking
