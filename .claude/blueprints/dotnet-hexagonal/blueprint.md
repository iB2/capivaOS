# Blueprint: .NET Hexagonal (.NET 10 + C# 13)

> Stack reference for Capiva OS harness. Agent roles and skills inject this file for stack-specific guidance.
> These are enforceable rules — the harness validates compliance at every phase.

---

## 1. Stack & Version

- **Runtime**: .NET 10 (`net10.0`)
- **Language**: C# 13+ (latest)
- **SDK**: 10.0.x
- **Nullable reference types**: `enable` (project-wide)
- **Implicit usings**: `enable`

---

## 2. Architecture: Hexagonal (Ports & Adapters)

```
src/
  Core/
    [Project].Domain/            # Entities, value objects, domain interfaces, enums
    [Project].Application/       # Use cases, DTOs, validators, builders, mapping
  Driven/
    [Project].Infrastructure/    # Repositories, EF DbContext, external integrations
  Drivers/
    [Project].Api/               # ASP.NET Core Web API controllers
    [Project].FunctionDriver/    # Azure Functions triggers (optional)

tests/
  [Project].Domain.Tests/
  [Project].Application.Tests/
  [Project].Infrastructure.Tests/
  [Project].Integration.Tests/
```

### Dependency Direction (INVIOLABLE)

```
Drivers → Application → Domain ← Infrastructure
```

- **Domain**: Zero dependencies on other layers. Pure business logic.
- **Application**: Depends ONLY on Domain. Use cases, DTOs, validators.
- **Infrastructure**: Depends on Domain (implements interfaces). NEVER on Application.
- **Drivers**: Depends on Application. Entry points are THIN — delegate to use cases.
- **NO circular dependencies. NO shortcuts.**

### Namespace Convention

```
[Company].[Project].[Layer].[Feature]
```

Example: `Capiva.OS.Application.UseCases.Quotes`

---

## 3. Patterns (MANDATORY)

### Use Case Pattern

One class per business operation. Every use case has an interface. Explicit interface implementation.

```csharp
public interface ICreateCustomerUseCase
{
    Task<CustomerResponse> ExecuteAsync(CreateCustomerRequest request, CancellationToken ct);
}

public sealed class CreateCustomerUseCase(
    ICustomerRepository customerRepository,
    IBuilder<CreateCustomerRequest, Customer> customerBuilder) : ICreateCustomerUseCase
{
    Task<CustomerResponse> ICreateCustomerUseCase.ExecuteAsync(
        CreateCustomerRequest request, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        var quote = customerBuilder.Build(request);
        return customerRepository.SaveAsync(quote, ct);
    }
}
```

**Dependency Records** group related use cases for DI:

```csharp
public sealed record CustomerUseCaseDependencies(
    ICreateCustomerUseCase CreateCustomer,
    IGetCustomerByIdUseCase GetCustomerById,
    IUpdateCustomerUseCase UpdateCustomer);
```

### Builder Pattern (Inlined Mapping)

`IBuilder<TInput, TOutput>` from `Application/Mapping/` for all DTO-Entity transformations. No external package — interfaces and implementation live inside the Application project.

```csharp
public sealed class CustomerToResponseBuilder : IBuilder<Customer, CustomerResponse>
{
    public CustomerResponse Build(Customer source) => new()
    {
        Id = source.Id,
        Name = source.Name,
        Email = source.Email
    };
}
```

Auto-registration: `services.AddMapping(assembly)` in the bootstrapper scans and registers all builders.

**Deviation allowed**: Manual static mappers acceptable for simple transforms — document via Deviation Record.

### Bootstrapper Pattern

Each layer registers its own DI via `Register()` extension method:

```csharp
public static class ApplicationBootstrapper
{
    public static IServiceCollection Register(this IServiceCollection services)
    {
        _ = services.AddTransient<ICreateCustomerUseCase, CreateCustomerUseCase>();
        _ = services.AddMapping(typeof(ApplicationBootstrapper).Assembly);
        return services;
    }
}

public static class InfrastructureBootstrapper
{
    public static IServiceCollection Register(this IServiceCollection services, IConfiguration configuration)
    {
        _ = services.AddDbContext<AppDbContext>(options =>
            options.UseSqlServer(configuration.GetConnectionString("Default")));
        _ = services.AddTransient<ICustomerRepository, CustomerRepository>();
        return services;
    }
}
```

Called from Program.cs: `builder.Services.Register().Register(builder.Configuration);`

### FluentValidation

Auto-validation via `AsyncAutoValidation` filter + `AsyncModelStateFilter`:

```csharp
public sealed class CreateCustomerRequestValidator : AbstractValidator<CreateCustomerRequest>
{
    public CreateCustomerRequestValidator()
    {
        this.RuleFor(x => x.Name).NotEmpty().MaximumLength(200);
        this.RuleFor(x => x.Email).NotEmpty().EmailAddress();
    }
}
```

Registration: `services.AddValidatorsFromAssembly(assembly)` + endpoint filter pipeline.

### ProblemDetails for All Errors

All error responses MUST use RFC 7807 ProblemDetails:

```csharp
public sealed class ExceptionHandlingMiddleware(RequestDelegate next, ILogger<ExceptionHandlingMiddleware> logger)
{
    public async Task InvokeAsync(HttpContext context)
    {
        try { await next(context); }
        catch (Exception ex)
        {
            logger.LogError(ex, "Unhandled exception");
            context.Response.StatusCode = StatusCodes.Status500InternalServerError;
            await context.Response.WriteAsJsonAsync(new ProblemDetails
            {
                Status = StatusCodes.Status500InternalServerError,
                Title = "Internal Server Error",
                Detail = $"Trace ID: {context.TraceIdentifier}"
            });
        }
    }
}
```

### Soft Deletes

Entities use `Active` boolean flag — NEVER hard delete:

```csharp
public bool Active { get; set; } = true;
```

Repositories filter `Active == true` by default. "Delete" = set `Active = false`.

**Deviation allowed**: Status-based lifecycle may replace soft deletes — document via Deviation Record.

### Interface-First Design

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
- Filter `Active == true` by default

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

## 4. Code Style (MANDATORY)

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Namespace | PascalCase, match layer | `Capiva.OS.Application.UseCases` |
| Class / Record | PascalCase, **sealed** | `sealed class QuoteService` |
| Interface | `I` + PascalCase | `IQuoteRepository` |
| Method | PascalCase | `GetActiveQuotesAsync` |
| Property | PascalCase | `ExpirationDate` |
| Private field | `_camelCase` | `_quoteRepository` |
| Parameter | camelCase | `quoteId` |
| Constant | PascalCase | `MaxRetryCount` |
| Async method | Suffix `Async` | `SaveQuoteAsync` |
| DTOs | Immutable records | `record CreateQuoteRequest(...)` |

### Primary Constructors (C# 12+)

ALL classes with DI use primary constructors:

```csharp
// CORRECT
public sealed class QuoteService(IQuoteRepository repository, ILogger<QuoteService> logger)

// WRONG
public class QuoteService
{
    private readonly IQuoteRepository _repository;
    public QuoteService(IQuoteRepository repository) => _repository = repository;
}
```

### Sealed Classes

ALL classes are `sealed` unless explicitly designed for inheritance (rare).

### Explicit Interface Implementation

Services use explicit interface implementation:

```csharp
public sealed class CreateCustomerUseCase : ICreateCustomerUseCase
{
    Task<CustomerResponse> ICreateCustomerUseCase.ExecuteAsync(
        CreateCustomerRequest request, CancellationToken ct) { }
}
```

### `this.` Prefix

Use `this.` for all local member calls:

```csharp
this.Ok(response);
this.HttpContext.RequestAborted;
this.RuleFor(x => x.Name);
```

### Alphabetical Sorting

Sort members A-Z within visibility groups (StyleCop ordering: constants, static fields, instance fields, constructors, properties, methods).

### Discard Pattern

`_ =` for fluent API return values: `_ = services.AddTransient<IQuoteService, QuoteService>();`

### Guard Validation

```csharp
ArgumentNullException.ThrowIfNull(customer);
ArgumentException.ThrowIfNullOrWhiteSpace(customer.Name);
```

### DTOs as Records

All DTOs MUST be immutable records:

```csharp
public sealed record CreateCustomerRequest(string Name, string Email);
public sealed record CustomerResponse(Guid Id, string Name, string Email);
```

### Async/Await Rules

- All I/O is async. No synchronous database, HTTP, or file I/O.
- No sync-over-async: never `.Result`, `.Wait()`, `.GetAwaiter().GetResult()`
- No fire-and-forget: every `Task` must be awaited
- `CancellationToken` on every async method

### Error Handling

- No swallowed exceptions: every `catch` logs, rethrows, or returns meaningful result
- No `catch (Exception)` at service level: catch specific exceptions
- Validation at boundaries via FluentValidation
- Guard clauses for preconditions

### Comments

- No comments explaining WHAT — code is self-documenting
- Comments for WHY only: non-obvious decisions, workarounds, business rules
- No TODO/HACK without a board task

### Code Smells to Avoid

- God class: no class over 200 lines
- Primitive obsession: use value objects for domain concepts
- Static abuse: no static methods for business logic
- String typing: use enums or strongly-typed alternatives
- Deep nesting: max 2 levels of indentation

---

## 5. Static Analysis (MANDATORY)

### Required Analyzers

Every project MUST include (via `Directory.Build.props`):

```xml
<ItemGroup>
  <PackageReference Include="SonarAnalyzer.CSharp" PrivateAssets="all" />
  <PackageReference Include="StyleCop.Analyzers" PrivateAssets="all">
    <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
  </PackageReference>
</ItemGroup>

<PropertyGroup>
  <AnalysisMode>AllEnabledByDefault</AnalysisMode>
</PropertyGroup>
```

### SonarQube Requirements

- All builds run SonarQube analysis via Azure Pipelines
- Quality Gate must pass (server-side config)
- No new code smells, bugs, or vulnerabilities in changed files
- Coverage data published via cobertura format

### StyleCop Compliance

- Zero StyleCop warnings in new code
- Any new suppression requires a Deviation Record

### Accepted Suppressions

| Rule | Description | When Acceptable |
|------|-------------|-----------------|
| SA0001 | XML comment analysis disabled | When not producing a public library |
| SA1101 | `this.` prefix | ONLY suppress if entire team agrees |
| SA1309 | Field names begin with underscore | Suppressed for `_camelCase` convention |
| SA1600-SA1602 | XML documentation | When not producing a public library |
| SA1633 | File header | When file headers not required |

---

## 6. Testing

### Test Stack

| Package | Version | Purpose |
|---------|---------|---------|
| xUnit | 2.9+ | Test framework |
| NSubstitute | 5.3+ | Mocking/substitution |
| AwesomeAssertions | latest | Fluent assertions (Apache 2.0 — NOT FluentAssertions v8) |
| Bogus | 35.6+ | Test data generation |
| Verify | 31.x | Snapshot testing |
| Testcontainers | 4.12+ | Redis + MsSql integration tests |
| Reqnroll | latest | BDD/Gherkin (NOT SpecFlow — EOL Dec 2024) |
| ReportGenerator | latest | TRX to HTML reports |

### Test Command

```bash
dotnet test --collect:"XPlat Code Coverage" -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=cobertura,opencover
```

### Coverage Targets

| Scope | Minimum | Target |
|-------|---------|--------|
| Business logic (services, domain) | 80% | 90% |
| Infrastructure (repositories) | 60% | 75% |
| Overall solution | 75% | 85% |

### Coverage Exclusions

- Program.cs / Startup.cs / host configuration
- Auto-generated code (EF migrations, gRPC stubs)
- DTOs and record types with no logic
- Azure Functions entry points

### Test Conventions

- **AAA pattern**: Arrange-Act-Assert with blank line separation
- **Naming**: `MethodName_Scenario_ExpectedResult`
- **Organization**: One test class per production class, test project mirrors source structure
- **Mocking**: NSubstitute. Never mock what you don't own.
- **Snapshot testing**: Verify for serialization contracts and complex object comparisons

### Integration Tests

Required when code touches:
- SQL (any IRepository) — use Testcontainers.MsSql
- Redis (any ICacheTransport / IStreamTransport) — use Testcontainers.Redis
- External HTTP APIs — use WireMock.Net
- File system — use System.IO.Abstractions

Rules:
- Each test class manages its own container lifecycle
- Tests must be parallelizable (no shared mutable state)
- Connection strings from container, never from config files
- Timeout: 60 seconds max per integration test

### Azure Functions Testing

The .NET isolated worker model does NOT support in-process test hosts.
- Extract all logic into service classes with interfaces
- Test service classes directly via unit tests
- Test the Function class only for correct DI wiring
- Integration tests target services, not Functions endpoints

### TDD Enforcement

1. **RED**: Write a failing test first
2. **GREEN**: Minimum code to pass
3. **REFACTOR**: Clean up, all tests still green

Verified via commit order (test commit before implementation) and QA review.

---

## 7. CI/CD: Azure Pipelines

**NOT GitHub Actions.** All CI/CD uses Azure Pipelines with a standalone pipeline.

### Pipeline Configuration

- **Triggers**: `main`, `release/*`, `develop`
- **PR triggers**: `main`, `release/*`, `feature/*`, `hotfix/*`, `develop`
- **SDK**: .NET 10.0.x
- **SonarQube**: Mandatory for all builds
- **Coverage**: cobertura + opencover formats
- **Deploy**: 3 environments (dev, uat, prod) on Linux stack

See `templates/azure-pipelines.yml` for the base template.

### Environment Progression

```
DEV → UAT → Sandbox (optional) → Production
```

- Merge to `main` happens AFTER production validation
- Each environment has its own pipeline stage
- CAB approval required before production deployment

---

## 8. Package Management

Central Package Management via `Directory.Packages.props` at solution root:

```xml
<!-- In .csproj — no version -->
<PackageReference Include="FluentValidation" />

<!-- In Directory.Packages.props — single version source -->
<PackageVersion Include="FluentValidation" Version="12.1.1" />
```

See `templates/Directory.Packages.props` for current version pins.

---

## 9. Standard Libraries

| Library | Location | Purpose |
|---------|----------|---------|
| Mapping (`IBuilder<TInput, TOutput>`) | `Application/Mapping/` (inlined) | DTO-Entity transformations |
| Logging | Native `ILogger<T>` | Structured logging via ASP.NET Core |
| Validation | FluentValidation 12.x | Request validation |
| ORM | Entity Framework Core 10.x | Data access |
| Telemetry | OpenTelemetry + Azure Monitor | Observability |

Additional packages added per project as needed from nuget.org.

---

## 10. SDLC Compliance

### Commit Convention

Karma format. See `.claude/rules/board-protocol.md` for format, scopes, and examples.

### Code Review Standards

1. **SOLID principles** — single responsibility per class
2. **DTOs as immutable records** — never mutable classes
3. **Method parameters**: 0 ideal, 1-2 normal, 3+ needs justification
4. **`if` blocks**: one line of logic. Extract methods for complex conditions
5. **No magic numbers** — named constants only
6. **Max 2 levels of indentation** per method

### Quality Gates (SDLC)

9 enterprise quality gates:
1. Executive Approval
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

## 11. Deviation Documentation

When a project deviates from ANY constraint in this blueprint, a Deviation Record MUST be created.

### When Required

- Suppressing a StyleCop/SonarQube rule not in "Accepted Suppressions"
- Using a different pattern than specified
- Skipping a mandatory pattern
- Adding packages not in the blueprint stack
- Changing the architecture structure

### Process

1. Create `docs/deviations/DEV-NNN-[slug].md` using `templates/deviation-record.md`
2. Reference the deviation in the PR description
3. The deviation is reviewed as part of PR code review
4. Approved deviations are binding — future work follows the deviation

---

## 12. Report Artifacts

After test/verify phase, these artifacts must exist:

| Artifact | Location | Format |
|----------|----------|--------|
| Test results | `reports/test-results/` | TRX + HTML (ReportGenerator) |
| Coverage report | `reports/coverage/` | HTML (ReportGenerator) |
| SonarQube report | SonarQube server | Online dashboard |

---

*Blueprint: .NET Hexagonal — Capiva OS Development Harness*
*Stack: .NET 10 + C# 13 + Hexagonal Architecture + Azure Pipelines*
