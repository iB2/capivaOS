# Coding Standards

Stack-specific coding standards are defined in the active blueprint's `reference.md` file.

## Where to Find Standards

- **Naming conventions**: `reference.md` §coding-standards
- **Code style rules**: `reference.md` §coding-standards
- **Architecture patterns**: `reference.md` §architecture
- **Enterprise patterns**: `reference.md` §enterprise-patterns
- **Test conventions**: `reference.md` §test-stack

## Universal Standards (All Blueprints)

1. **TDD is mandatory.** Tests before implementation. No exceptions.
2. **Soft deletes only.** No hard deletes in any stack.
3. **Dependency direction is inviolable.** Inner layers never depend on outer layers.
4. **Interface-first design.** Services and repositories have interfaces/abstractions.
5. **Async for all I/O.** No synchronous I/O operations.
6. **Type safety.** Use the stack's type system fully (nullable types, type hints, generics).
7. **No magic values.** Named constants, enums, or configuration for all non-obvious values.
8. **Error handling with structured responses.** All API errors return ProblemDetails-style JSON.
9. **DTOs are immutable.** Use the stack's immutable data container (records, frozen dataclasses, readonly interfaces).
10. **No deep nesting.** Max 2 levels of indentation per method.
11. **Single responsibility.** One class/module per concern. No god classes (200+ lines).

## Code Review Standards (Universal)

These are enforced during /test-verify and /finish, regardless of stack:

1. **SOLID principles** — every class has a single responsibility
2. **Method parameters**: 0 ideal, 1-2 normal, 3+ needs justification
3. **`if` blocks**: one line of logic. Extract methods for complex conditions
4. **No magic numbers** — named constants only
5. **Max 2 levels of indentation** per method

## Comments

- No comments explaining WHAT — code is self-documenting
- Comments for WHY only: non-obvious decisions, workarounds, business rules
- No TODO/HACK without a board task

## Commit Convention

Commit format follows Karma convention. See `.claude/rules/board-protocol.md` for format, scopes, and examples.

## Blueprint Reference Location

```
.claude/blueprints/<blueprint-name>/reference.md
```

The active blueprint is configured in CLAUDE.md under the "Active Blueprint" section.
