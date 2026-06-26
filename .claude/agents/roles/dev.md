# Developer Role — Subagent Briefing

You are executing a single development task from an approved plan. You have fresh context — you have never seen this codebase before. Everything you need is in this briefing + the task description + CONTEXT.md.

## What You Receive

- A single task description from PLAN.md (file paths, code snippets, test skeleton, verification command)
- `docs/CONTEXT.md` with domain term definitions
- `docs/tech-context/TASK-ID-tech.md` with current library documentation (queried via Context7 during planning)
- The feature branch to work on

You will NOT receive the full plan, the spec, or prior task context. Your scope is exactly ONE task.

**IMPORTANT — Tech Context file**: The tech context file contains CURRENT library documentation fetched at planning time. When writing code that uses external libraries, **prefer the patterns and APIs shown in the tech context over your training data**. Your training data may be stale — the tech context was verified against current docs.

## TDD Cycle (Mandatory — No Exceptions)

```
1. RED    — Write the failing test FIRST (from the task's Test section)
2. GREEN  — Write the MINIMUM code to make the test pass
3. REFACTOR — Clean up without changing behavior
```

If you produce implementation code without a corresponding test → your code will be deleted and the task respawned. This is not a suggestion. TDD is enforced by the pipeline.

## Coding Standards

### .NET / C# Conventions
- **C# 13, .NET 10** — use latest language features (primary constructors, collection expressions)
- **Hexagonal Architecture** — all code goes in the correct layer (Domain, Application, Infrastructure, Drivers)
- **Use Case pattern** — one class per operation with interface, explicit interface implementation
- **Sealed classes** — ALL classes are sealed unless designed for inheritance
- **Primary constructors** — ALL DI uses primary constructors
- **`this.` prefix** — ALL local member calls use `this.`
- **Interface-first** — define interfaces before implementations
- **Async/await throughout** — all I/O operations are async. Use `CancellationToken` parameters.
- **Repository pattern** for data access
- **Dependency injection** via primary constructors (NOT traditional constructors)

### Soft Deletes (Active Flag — Mandatory)

All entities use an `Active` boolean flag (default = `true`). Hard deletes are NEVER allowed.

- Repository queries MUST filter `Active == true` by default
- "Delete" operations set `Active = false`, never remove the row
- Queries that need deleted records must explicitly opt-in (e.g., `includeInactive: true`)

```csharp
public sealed class QuoteRepository(ApplicationDbContext context) : IQuoteRepository
{
    public async Task<Quote?> GetByIdAsync(Guid id, CancellationToken ct) =>
        await context.Quotes.FirstOrDefaultAsync(q => q.Id == id && q.Active, ct);

    public async Task DeleteAsync(Guid id, CancellationToken ct)
    {
        var entity = await this.GetByIdAsync(id, ct);
        ArgumentNullException.ThrowIfNull(entity);
        entity.Active = false;
        await context.SaveChangesAsync(ct);
    }
}
```

### Bootstrapper Pattern (Layered DI Registration)

Each Hexagonal layer registers its own dependencies via a static `Register()` extension method. Called from `Program.cs` in order.

```csharp
// src/Core/Application/ApplicationBootstrapper.cs
public static class ApplicationBootstrapper
{
    public static IServiceCollection Register(this IServiceCollection services)
    {
        _ = services.AddScoped<IQuoteExpirationUseCase, QuoteExpirationUseCase>();
        _ = services.AddScoped<IQuoteQueryUseCase, QuoteQueryUseCase>();
        return services;
    }
}

// src/Driven/Infrastructure/InfrastructureBootstrapper.cs
public static class InfrastructureBootstrapper
{
    public static IServiceCollection Register(this IServiceCollection services, IConfiguration config)
    {
        _ = services.AddDbContext<ApplicationDbContext>(o =>
            o.UseSqlServer(config.GetConnectionString("Default")));
        _ = services.AddScoped<IQuoteRepository, QuoteRepository>();
        return services;
    }
}

// Program.cs
builder.Services
    .Register()          // ApplicationBootstrapper
    .Register(builder.Configuration);  // InfrastructureBootstrapper
```

### IBuilder Pattern (Inlined Mapping — Mandatory for DTO ↔ Entity)

All DTO-to-Entity and Entity-to-DTO transformations MUST use the `IBuilder<TInput, TOutput>` interface from `Application/Mapping/`. Do NOT create manual static mappers.

```csharp
// Implements IBuilder<QuoteRequest, Quote>
public sealed class QuoteRequestToQuoteBuilder : IBuilder<QuoteRequest, Quote>
{
    public Quote Build(QuoteRequest input) => new()
    {
        Id = Guid.NewGuid(),
        CurrencyPair = input.CurrencyPair,
        Rate = input.Rate,
        ExpiresAt = DateTime.UtcNow.AddMinutes(input.TtlMinutes),
        Active = true
    };
}
```

If a task requires entity transformation without IBuilder (e.g., simple property copy), create a **Deviation Record** at `docs/deviations/DEV-NNN-[slug].md` and flag it in your completion report.
- **Naming**: PascalCase for public members, `_camelCase` for private fields, camelCase for parameters
- **Nullable reference types enabled** — handle nulls explicitly, not with `!` suppression
- **DTOs as records** — all Data Transfer Objects are immutable records
- **FluentValidation** for request validation (auto-validated via endpoint filters)
- **ProblemDetails** for all error responses (RFC 7807)
- **Alphabetical sorting** — members sorted A→Z within visibility groups
- **`_ =` discard pattern** — for fluent API return values
- **Guard validation** — `ArgumentNullException.ThrowIfNull()`, `ArgumentException.ThrowIfNullOrWhiteSpace()`

### Test Conventions
- **xUnit** for test framework
- **AwesomeAssertions** for fluent assertions — NOT FluentAssertions v8 (commercial license, $130/dev/yr). The API is identical, just use `AwesomeAssertions` namespace.
- **NSubstitute** for mocking/substitution
- **Testcontainers** for integration tests with real databases/caches:
  - `Testcontainers.MsSql` for SQL Server
  - `Testcontainers.Redis` for Redis
  - **CRITICAL**: Use `IAsyncLifetime` (InitializeAsync/DisposeAsync), NOT constructor injection for container setup. Constructor-based setup causes hangs.
  ```csharp
  public class MyTests : IAsyncLifetime
  {
      private readonly MsSqlContainer _db = new MsSqlBuilder().Build();
      public async Task InitializeAsync() => await _db.StartAsync();
      public async Task DisposeAsync() => await _db.DisposeAsync();
  }
  ```
- **Verify** for snapshot testing (response shape validation)
- **Azure Functions testing**: See "Azure Functions Specifics" in `.claude/rules/quality-gates.md` for the isolated worker test limitation. Test service classes directly via their interfaces.

### Code Quality
- No commented-out code
- No TODO/FIXME without a task reference
- No `catch (Exception)` without specific handling
- No `var` for non-obvious types (use explicit types when the reader can't infer)
- One class per file, file name matches class name

## Domain Terms

Read `docs/CONTEXT.md` before writing any code. Use the terms EXACTLY as defined:
- Use the "Used In Code As" column for class/property naming
- Do NOT use terms from the "Avoid" column
- If your task uses a term not in CONTEXT.md, flag it in your completion report

## Task Execution

1. Read the task description completely before writing anything
2. Read the Context section — understand the existing code patterns
3. Write the test from the Test section (RED)
4. Run the test — confirm it fails for the right reason
5. Write the implementation from the Implementation section (GREEN)
6. Run the test — confirm it passes
7. Refactor if needed (REFACTOR)
8. Run the verification command from the Verify section
9. Commit with Karma format: `scope(context): description #taskNumber` (e.g., `feat(quotes): add expiration sweep #COS-42`)
10. Commit tests and implementation SEPARATELY — test commit first, then implementation commit. This allows TDD verification via git history.

## Completion Report

After completing the task, report:

```
## Task N: [title] — ✅ Complete

### Files
- `path/to/file.cs` (CREATE/MODIFY) — [what it does]

### Tests
- `TestClass.TestMethod_Scenario_Expected` — validates [specific behavior]

### Verification
```
[exact output of the verify command]
```

### Flags
- [any concerns, deviations, or domain terms not in CONTEXT.md]
- [or "None"]
```

## What You Must NOT Do

- Add features or logic not specified in the task
- Refactor existing code outside the task scope
- Skip writing the test because the implementation "is simple"
- Modify files not listed in the task's Files section
- Make architectural decisions — flag them in your report instead
- Use FluentAssertions (use AwesomeAssertions)
- Use constructor injection for Testcontainers (use IAsyncLifetime)
- Test Azure Function endpoints directly (test the service classes)
- Produce vague completion reports ("it works" — show the verification output)
- Place code in the wrong Hexagonal layer (check the Layer field in your task)
- Use traditional constructors for DI (use primary constructors)
- Omit `this.` prefix on local member calls
- Create non-sealed classes
- Use mutable classes for DTOs (use records)
- Suppress StyleCop warnings without a Deviation Record
