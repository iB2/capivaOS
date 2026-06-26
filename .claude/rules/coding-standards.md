# Coding Standards (.NET — Enterprise Blueprint)

## Language and Runtime

- C# 13 or later (latest)
- .NET 10 (`net10.0`)
- Nullable reference types: **enabled** project-wide (`<Nullable>enable</Nullable>`)
- Implicit usings: enabled
- Static analysis: SonarAnalyzer.CSharp + StyleCop.Analyzers (see `enterprise-blueprint.md`)

---

## Architecture: Hexagonal (Ports & Adapters)

All code follows Hexagonal Architecture. See `enterprise-blueprint.md` for full rules.

```
src/Core/[Project].Domain/           # Entities, value objects, domain interfaces
src/Core/[Project].Application/      # Use cases, DTOs, validators, builders
src/Driven/[Project].Infrastructure/ # Repositories, DbContext, external clients
src/Drivers/[Project].Api/           # Controllers, middleware (thin layer)
src/Drivers/[Project].FunctionDriver/# Azure Functions triggers (thin layer)
```

**Dependencies flow inward**: Drivers → Application → Domain ← Infrastructure.

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Namespace | PascalCase, match Hexagonal layer | `Capiva.OS.Application.UseCases.Quotes` |
| Class / Record / Struct | PascalCase, **sealed** | `sealed class QuoteService` |
| Interface | `I` + PascalCase | `IQuoteRepository` |
| Method | PascalCase | `GetActiveQuotesAsync` |
| Property | PascalCase | `ExpirationDate` |
| Private field | `_camelCase` (SA1309 suppressed) | `_quoteRepository` |
| Private static field | `s_camelCase` | `s_instance` |
| Parameter | camelCase | `quoteId` |
| Local variable | camelCase | `activeQuotes` |
| Constant | PascalCase | `MaxRetryCount` |
| Async method | Suffix with `Async` | `SaveQuoteAsync` |
| DTOs | Immutable records | `record CreateQuoteRequest(...)` |

---

## Enterprise Design Patterns

### Use Case Pattern

One class per business operation with interface. Explicit interface implementation.

```csharp
public interface ICreateQuoteUseCase
{
    Task<QuoteResponse> ExecuteAsync(CreateQuoteRequest request, CancellationToken ct);
}

public sealed class CreateQuoteUseCase(
    IQuoteRepository quoteRepository,
    IBuilder<CreateQuoteRequest, Quote> quoteBuilder) : ICreateQuoteUseCase
{
    Task<QuoteResponse> ICreateQuoteUseCase.ExecuteAsync(
        CreateQuoteRequest request, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        var quote = quoteBuilder.Build(request);
        return quoteRepository.SaveAsync(quote, ct);
    }
}
```

### Dependency Records

Group related use cases for cleaner DI:

```csharp
public sealed record QuoteUseCaseDependencies(
    ICreateQuoteUseCase CreateQuote,
    IGetQuoteByIdUseCase GetQuoteById,
    IExpireQuoteUseCase ExpireQuote);
```

### Builder Pattern (Inlined Mapping)

`IBuilder<TInput, TOutput>` from `Application/Mapping/` for all DTO ↔ Entity transformations. Auto-registered via `services.AddMapping(assembly)`.

### Bootstrapper Pattern

Each layer registers its own DI via static `Register()` extension method on `IServiceCollection`.

### FluentValidation

`AbstractValidator<T>` for request validation. Auto-validated via endpoint filters. Returns `ProblemDetails` on failure.

### ProblemDetails

ALL error responses use RFC 7807 ProblemDetails. `ExceptionHandlingMiddleware` catches unhandled exceptions.

### Soft Deletes

`Active` boolean flag. Repositories filter `Active == true` by default. "Delete" = set `Active = false`.

---

## Code Style

### Primary Constructors (MANDATORY)

All DI uses primary constructors (C# 12+):

```csharp
public sealed class QuoteService(IQuoteRepository repository, ILogger<QuoteService> logger) : IQuoteService
```

### Sealed Classes (MANDATORY)

All classes are `sealed` unless designed for inheritance.

### `this.` Prefix (MANDATORY)

All local member calls use `this.`:

```csharp
this.Ok(response);
this.HttpContext.RequestAborted;
this.RuleFor(x => x.Name);
```

### Alphabetical Sorting

Sort members A→Z within visibility groups (StyleCop ordering: constants → static fields → instance fields → constructors → properties → methods).

### Discard Pattern

`_ =` for fluent API return values:

```csharp
_ = services.AddTransient<IQuoteService, QuoteService>();
```

### Guard Clauses

```csharp
ArgumentNullException.ThrowIfNull(entity);
ArgumentException.ThrowIfNullOrWhiteSpace(entity.Name);
```

---

## Interface-First Design

Every service, repository, and transport has an interface. No concrete class injected directly.

```csharp
// CORRECT
public sealed class QuoteService(IQuoteRepository repository, ICacheTransport cache)

// WRONG
public sealed class QuoteService(QuoteRepository repository, RedisCache cache)
```

### Repository Pattern

```csharp
public interface IQuoteRepository
{
    Task<Quote?> GetByIdAsync(Guid id, CancellationToken ct = default);
    Task<IReadOnlyList<Quote>> GetActiveAsync(CancellationToken ct = default);
    Task SaveAsync(Quote quote, CancellationToken ct = default);
}
```

- Return domain objects, not DTOs
- Accept `CancellationToken` on every async method
- Return `T?` for "not found" (never throw)
- Filter `Active == true` by default (soft deletes)

### Transport Interfaces

```csharp
public interface IStreamTransport
{
    Task PublishAsync<T>(string stream, T message, CancellationToken ct = default);
    Task<IReadOnlyList<T>> ReadAsync<T>(string stream, string group, int count, CancellationToken ct = default);
}

public interface ICacheTransport
{
    Task<T?> GetAsync<T>(string key, CancellationToken ct = default);
    Task SetAsync<T>(string key, T value, TimeSpan? ttl = null, CancellationToken ct = default);
    Task RemoveAsync(string key, CancellationToken ct = default);
}
```

### Result Pattern

```csharp
public sealed record Result<T>
{
    public T? Value { get; init; }
    public string? Error { get; init; }
    public bool IsSuccess => Error is null;
    public static Result<T> Ok(T value) => new() { Value = value };
    public static Result<T> Fail(string error) => new() { Error = error };
}
```

Prefer `Result<T>` for expected failures. Reserve exceptions for unexpected failures.

---

## Async/Await

- All I/O is async. No synchronous database, HTTP, or file I/O.
- No sync-over-async: never `.Result`, `.Wait()`, `.GetAwaiter().GetResult()`
- No fire-and-forget: every `Task` must be awaited
- `CancellationToken` on every async method
- `ConfigureAwait`: omit in application code, use `ConfigureAwait(false)` only in library code

---

## Error Handling

- No swallowed exceptions: every `catch` logs, rethrows, or returns meaningful result
- No `catch (Exception)` at service level: catch specific exceptions
- Validation at API/Function boundaries via FluentValidation
- Guard clauses for preconditions
- `ProblemDetails` for all HTTP error responses

---

## Commit Convention — Karma Format

Commit format follows Karma convention. See `.claude/rules/board-protocol.md` for format, scopes, and examples.

---

## SDLC Code Review Standards

These apply to all code and are checked during review:

1. **SOLID principles** enforced — single responsibility per class
2. **Method parameters**: 0 ideal, 1-2 normal, 3+ needs justification
3. **`if` blocks**: one line of logic. Extract methods for complex conditions
4. **No magic numbers** — named constants only
5. **Max 2 levels of indentation** per method

---

## Test Conventions

### AAA Pattern

Every test: Arrange-Act-Assert with blank line separation.

### Test Naming

`MethodName_Scenario_ExpectedResult`

### Test Organization

- One test class per production class
- Test project mirrors source structure
- Shared fixtures in `Fixtures/`
- Test data builders in `Builders/`

### Mocking

NSubstitute. Never mock what you don't own (wrap behind interfaces).

### Snapshot Testing

Verify for serialization contracts and complex object comparisons.

### Test Stack

Test stack packages and versions are defined in `.claude/rules/quality-gates.md` (single source of truth).

---

## Comments

- No comments explaining WHAT — code is self-documenting
- Comments for WHY only: non-obvious decisions, workarounds, business rules
- XML docs on public API interfaces
- No TODO/HACK without a board task

---

## Code Smells to Avoid

- God class: no class over 200 lines
- Primitive obsession: use value objects for domain concepts
- Static abuse: no static methods for business logic
- String typing: use enums or strongly-typed alternatives
- Deep nesting: max 2 levels of indentation
