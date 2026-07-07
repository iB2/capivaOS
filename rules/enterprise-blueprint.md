# Enterprise Blueprint — Hard Constraints

> These constraints come from the Capiva OS enterprise blueprint system.
> They are NOT suggestions — they are enforceable rules. The harness validates compliance at every phase.

Stack-specific enterprise patterns are defined in the active blueprint's `reference.md` file. This document defines the **universal rules** that apply regardless of technology stack.

---

## Architecture Enforcement

Every project MUST follow the architecture defined in the active blueprint's `reference.md` §architecture section. The harness validates:

1. **Layer placement**: Every class/module in the correct architectural layer
2. **Dependency direction**: Dependencies flow inward (as defined per blueprint)
3. **No circular dependencies. No shortcuts. No "just this once."**

Read the active blueprint's §architecture for the specific project structure, layer rules, and dependency direction for your stack.

---

## Enterprise Patterns (MANDATORY)

The active blueprint's `reference.md` §enterprise-patterns section defines the mandatory patterns for the stack. Universal requirements across all blueprints:

### Service/Use Case Pattern
- One class per business operation with interface/abstraction
- Dependency injection for all dependencies
- No static methods for business logic

### Repository Pattern
- Return domain objects, not DTOs
- Filter active (non-deleted) records by default
- Accept cancellation/timeout mechanisms per stack conventions

### Validation at Boundaries
- All input validated before reaching business logic
- Stack-specific validation framework (per blueprint §enterprise-patterns)

### ProblemDetails for All Errors
- All error responses MUST use RFC 7807 ProblemDetails-style JSON
- Structured error responses with type, title, status, detail

### Soft Deletes
- Entities use an active/deleted flag — NEVER hard delete
- Repository queries filter active records by default
- "Delete" operations set the flag, never remove the row

### Interface-First Design
- Every service, repository, and transport has an interface/abstraction
- No concrete class injected directly

---

## SDLC Process Compliance

### Environment Progression

```
DEV → UAT → Sandbox (optional) → Production
```

- Merge to `main` happens AFTER production validation (not before)
- Each environment has its own CI pipeline stage (per blueprint §ci-cd)
- CAB approval required before production deployment

### Quality Gates Summary (SDLC)

9 enterprise quality gates from the SDLC:

1. Executive Approval (project level)
2. Requirements Workshop Sign-off
3. Solution Design Approval
4. Infrastructure Provisioning Complete
5. Code Review by Tech Lead
6. QA Sign-off (UAT)
7. CAB Approval (before production)
8. Production Deployment Validation
9. Business Production Validation

The harness maps to gates 5-7 via its pipeline phases.

---

## Deviation Documentation (MANDATORY)

When a project needs to deviate from ANY blueprint constraint, a Deviation Record MUST be created.

### When Required

- Suppressing a linter/analyzer rule not in the blueprint's accepted suppressions list
- Using a different pattern than specified in the blueprint
- Skipping a mandatory pattern (e.g., no soft deletes, no validation)
- Adding packages not in the blueprint stack
- Changing the architecture structure
- Any SDLC process deviation

### Process

1. Create `docs/deviations/DEV-NNN-[slug].md` using the template at `${CLAUDE_PLUGIN_ROOT}/project-template/templates/deviation-record.md`
2. Reference the deviation in the PR description
3. The deviation is reviewed as part of the PR code review
4. Approved deviations are binding — future work follows the deviation, not the blueprint

### Template Location

`${CLAUDE_PLUGIN_ROOT}/project-template/templates/deviation-record.md` — use this for all deviation records.

---

## Blueprint Reference

Stack-specific patterns, commands, and configurations are in the active blueprint's `reference.md`:

```
${CLAUDE_PLUGIN_ROOT}/blueprints/<blueprint-name>/reference.md
```

The active blueprint is configured in CLAUDE.md under the "Active Blueprint" section. The blueprint reference IS the source of truth for all stack-specific rules.

---

*Enterprise blueprint constraints for the Capiva OS development harness*
*Source: Capiva OS Blueprint + SDLC Process Documentation*
