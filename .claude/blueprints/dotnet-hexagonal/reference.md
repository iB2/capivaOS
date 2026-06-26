# Blueprint Reference: .NET Hexagonal (.NET 10 / C# 13)

> This file is the bridge between the stack-agnostic harness and the .NET blueprint project.
> Agent roles and skills read this file to get stack-specific patterns, commands, and standards.

## §project — Blueprint Project

- **Path**: `C:\Users\bruno\Documents\DevProjects\blueprint-backend\`
- **Type**: .NET 10 solution with Hexagonal Architecture
- **Contents**: ~80 files — solution, csproj, controllers, use cases, builders, validators, repositories, migrations, tests, CI pipeline
- **Origin**: Enterprise blueprint (Lumon project, descharacterized)
- **Status**: Functional, buildable

---

## §stack — Technology Identity

| Property | Value |
|----------|-------|
| Language | C# 13 |
| Runtime | .NET 10 (`net10.0`) |
| Framework | ASP.NET Core (Web API) + Azure Functions (optional) |
| Database | SQL Server (EF Core 10) |
| Cache | Redis (StackExchange.Redis) |
| DI | Built-in Microsoft.Extensions.DependencyInjection |
| Validation | FluentValidation 12.x |
| Nullable | Enabled project-wide |
| Implicit usings | Enabled |

---

## §architecture — Hexagonal (Ports & Adapters)

### Project Structure

```
src/
  Core/                          # Inner hexagon — business logic
    [Project].Domain/            # Entities, value objects, domain interfaces, enums
    [Project].Application/       # Use cases, DTOs, validators, application interfaces
  Driven/                        # Secondary adapters — infrastructure
    [Project].Infrastructure/    # Repositories, EF DbContext, external integrations
  Drivers/                       # Primary adapters — entry points
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

- **Domain**: Zero dependencies on other project layers. Pure business logic.
- **Application**: Depends ONLY on Domain. Defines use cases, DTOs, validators.
- **Infrastructure**: Depends on Domain (implements domain interfaces). NEVER on Application.
- **Drivers (Api/Functions)**: Depends on Application. Entry points are THIN — delegate to use cases.
- **NO circular dependencies. NO shortcuts. NO "just this once."**

### Namespace Convention

```
[Company].[Project].[Layer].[Feature]
```

Example: `Capiva.OS.Application.UseCases.Quotes`

### Layer Placement Rules

| Element | Layer | Project |
|---------|-------|---------|
| Entities, Value Objects, Domain Events | Domain | `Core/[Project].Domain` |
| Domain Interfaces (IRepository, ITransport) | Domain | `Core/[Project].Domain` |
| Use Cases (ICreateXUseCase, IGetXUseCase) | Application | `Core/[Project].Application` |
| DTOs (Request/Response records) | Application | `Core/[Project].Application` |
| Validators (FluentValidation) | Application | `Core/[Project].Application` |
| Builders (IBuilder implementations) | Application | `Core/[Project].Application` |
| Bootstrappers | Each layer | Own project |
| EF DbContext, Repositories | Infrastructure | `Driven/[Project].Infrastructure` |
| External service clients | Infrastructure | `Driven/[Project].Infrastructure` |
| API Controllers | Drivers | `Drivers/[Project].Api` |
| Azure Function Triggers | Drivers | `Drivers/[Project].FunctionDriver` |
| Middleware | Drivers | `Drivers/[Project].Api` |

---

## §coding-standards — C# Conventions

### Naming Conventions

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

### Mandatory Code Style

- **Primary Constructors (C# 12+)**: ALL classes with DI use primary constructors
- **Sealed Classes**: ALL classes are `sealed` unless designed for inheritance
- **`this.` Prefix**: ALL local member calls use `this.`
- **Alphabetical Sorting**: Members sorted A→Z within visibility groups
- **Discard Pattern**: `_ =` for fluent API return values
- **Guard Clauses**: `ArgumentNullException.ThrowIfNull()`, `ArgumentException.ThrowIfNullOrWhiteSpace()`
- **Explicit Interface Implementation**: Services use explicit interface implementation
- **Interface-First Design**: Every service, repository, and transport has an interface
- **Nullable reference types enabled** — handle nulls explicitly, not with `!` suppression
- **No var for non-obvious types**

### Code Style Examples

```csharp
// Primary Constructor + Sealed + Explicit Interface
public sealed class CreateCustomerUseCase(
    ICustomerRepository customerRepository,
    IBuilder<CreateCustomerRequest, Customer> customerBuilder) : ICreateCustomerUseCase
{
    Task<CustomerResponse> ICreateCustomerUseCase.ExecuteAsync(
        CreateCustomerRequest request, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(request);
        var customer = customerBuilder.Build(request);
        return customerRepository.SaveAsync(customer, ct);
    }
}

// Discard pattern + DI registration
_ = services.AddTransient<ICreateCustomerUseCase, CreateCustomerUseCase>();
_ = services.AddMapping(typeof(ApplicationBootstrapper).Assembly);

// this. prefix
this.Ok(response);
this.HttpContext.RequestAborted;
this.RuleFor(x => x.Name);
```

### SDLC Code Review Standards

1. **SOLID principles** enforced — single responsibility per class
2. **Method parameters**: 0 ideal, 1-2 normal, 3+ needs justification
3. **`if` blocks**: one line of logic. Extract methods for complex conditions
4. **No magic numbers** — named constants only
5. **Max 2 levels of indentation** per method

---

## §enterprise-patterns — Mandatory Patterns

### Use Case Pattern

One class per business operation with interface. Explicit interface implementation.

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
        // implementation
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

`IBuilder<TInput, TOutput>` from `Application/Mapping/` for all DTO ↔ Entity transformations.

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

Auto-registration: `services.AddMapping(assembly)`.

### Bootstrapper Pattern

Each layer registers its own DI via static `Register()` extension method:

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

// Program.cs
builder.Services.Register().Register(builder.Configuration);
```

### FluentValidation

Auto-validation via `AsyncAutoValidation` filter:

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

### ProblemDetails for All Errors

All error responses MUST use RFC 7807 ProblemDetails.

### Soft Deletes

Entities use `Active` boolean flag (default = true). Repositories filter `Active == true` by default. "Delete" = set `Active = false`. Hard deletes NEVER allowed.

```csharp
public async Task DeleteAsync(Guid id, CancellationToken ct)
{
    var entity = await this.GetByIdAsync(id, ct);
    ArgumentNullException.ThrowIfNull(entity);
    entity.Active = false;
    await context.SaveChangesAsync(ct);
}
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

### Transport Interfaces

```csharp
public interface IStreamTransport
{
    Task PublishAsync<T>(string stream, T message, CancellationToken ct = default);
}

public interface ICacheTransport
{
    Task<T?> GetAsync<T>(string key, CancellationToken ct = default);
    Task SetAsync<T>(string key, T value, TimeSpan? ttl = null, CancellationToken ct = default);
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

### Async/Await Rules

- All I/O is async. No sync-over-async (`.Result`, `.Wait()`, `.GetAwaiter().GetResult()`)
- `CancellationToken` on every async method
- `ConfigureAwait`: omit in application code, use `ConfigureAwait(false)` only in library code

### DTOs as Records

All Data Transfer Objects MUST be immutable records:

```csharp
public sealed record CreateCustomerRequest(string Name, string Email);
public sealed record CustomerResponse(Guid Id, string Name, string Email);
```

---

## §test-stack — Test Frameworks & Conventions

### Packages

| Package | Version | Purpose |
|---------|---------|---------|
| xUnit | 2.9+ | Test framework |
| NSubstitute | 5.3+ | Mocking/substitution |
| AwesomeAssertions | latest | Fluent assertions (Apache 2.0, NOT FluentAssertions v8 — commercial license) |
| Bogus | 35.6+ | Test data generation |
| Verify | 31.x | Snapshot testing |
| Testcontainers | 4.12+ | Redis + MsSql integration tests |
| Reqnroll | latest | BDD/Gherkin specs (NOT SpecFlow — EOL Dec 2024) |
| ReportGenerator | latest | TRX to HTML reports |

### Test Naming

`MethodName_Scenario_ExpectedResult`

### Test Organization

- One test class per production class
- Test project mirrors source structure
- Shared fixtures in `Fixtures/`, test data builders in `Builders/`
- AAA pattern (Arrange-Act-Assert) with blank line separation

### Testcontainers (CRITICAL)

Use `IAsyncLifetime`, NOT constructor injection (causes hangs):

```csharp
public class IntegrationTests : IAsyncLifetime
{
    private readonly MsSqlContainer _db = new MsSqlBuilder().Build();
    public async Task InitializeAsync() => await _db.StartAsync();
    public async Task DisposeAsync() => await _db.DisposeAsync();
}
```

### Azure Functions Testing

The .NET isolated worker model does NOT support in-process test hosts. Test service classes directly via their interfaces — do not attempt to spin up a Functions host.

### Assertion Library

AwesomeAssertions (Apache 2.0) — NOT FluentAssertions v8 ($130/dev/yr commercial license). The API is identical — just use `AwesomeAssertions` namespace.

---

## §static-analysis — Linters & Analyzers

### Required Analyzers (via `Directory.Build.props`)

```xml
<ItemGroup>
  <PackageReference Include="SonarAnalyzer.CSharp" PrivateAssets="all" />
  <PackageReference Include="StyleCop.Analyzers" PrivateAssets="all">
    <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
  </PackageReference>
</ItemGroup>
```

Analysis mode: `<AnalysisMode>AllEnabledByDefault</AnalysisMode>`

### Accepted StyleCop Suppressions

| Rule | Description | When Acceptable |
|------|-------------|-----------------|
| SA0001 | XML comment analysis disabled | When not producing a public library |
| SA1101 | `this.` prefix | ONLY suppress if entire team agrees |
| SA1309 | Field names begin with underscore | Suppressed for `_camelCase` convention |
| SA1600-SA1602 | XML documentation | When not producing a public library |
| SA1633 | File header | When file headers not required |

Any OTHER suppression requires a Deviation Record.

### Central Package Management

All projects use `Directory.Packages.props` at solution root. Individual `.csproj` files reference packages WITHOUT version numbers.

---

## §ci-cd — Pipeline Configuration

### Azure Pipelines (NOT GitHub Actions)

See blueprint project `azure-pipelines/` for the base configuration.

- **Triggers**: `main`, `release/*`, `develop`
- **PR triggers**: `main`, `release/*`, `feature/*`, `hotfix/*`, `develop`
- **SDK**: .NET 10.0.x
- **SonarQube**: Mandatory for all builds
- **Coverage**: cobertura + opencover formats
- **Deploy**: 3 environments (dev, uat, prod) on Linux stack

### Environment Progression

```
DEV → UAT → Sandbox (optional) → Production
```

Merge to `main` happens AFTER production validation.

### SDLC Compliance Mapping

- Phase 1 (GRILL_SPEC) → SDLC Phase 3 (Requirement Analysis)
- Phase 2 (PLAN) → SDLC Phase 4 (Solution Design)
- Phase 3 (IMPLEMENT) → SDLC Phase 6 (Refinement & Development)
- Phase 4 (TEST_VERIFY) → SDLC Phase 7 (Testing & QA)
- Phase 5 (FINISH) → SDLC Phases 6-8 (Code Review → CAB → Deploy)

---

## §qa-checklist — Stack-Specific QA Items

### Blueprint Compliance Checks

| Check | What to Look For |
|-------|-----------------|
| Layer placement | Every new class in correct Hexagonal layer (Domain/Application/Infrastructure/Drivers) |
| Blueprint compliance | Use Case, sealed, primary constructors, `this.` prefix, ProblemDetails |
| Soft deletes | Repository queries filter `Active == true` by default. No hard deletes |
| Bootstrappers | DI via `Register()` extension methods in each layer |
| Inlined Mapping | All DTO ↔ Entity transformations use `IBuilder<TInput, TOutput>` |
| Assertions | AwesomeAssertions — NOT FluentAssertions v8 |
| Containers | Testcontainers with `IAsyncLifetime` — NOT constructor injection |
| Azure Functions | Service classes tested directly — NOT Function endpoints |
| Commit format | Karma convention: `scope(context): description #taskNumber` |
| Discard pattern | `_ =` used for fluent API return values |
| Alphabetical | Members sorted A→Z within visibility groups |

---

## §build-commands — Build, Test & Verify

```bash
# Build
dotnet build --no-incremental

# Run all tests
dotnet test

# Run specific test
dotnet test --filter "ClassName.MethodName_Scenario_ExpectedResult"

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Generate coverage report
reportgenerator -reports:TestResults/**/coverage.cobertura.xml -targetdir:TestResults/CoverageReport -reporttypes:Html

# Run with TRX output
dotnet test --logger trx --results-directory TestResults/

# Check StyleCop warnings
dotnet build --no-incremental 2>&1 | grep -i "warning SA\|warning S\|warning CA"

# SonarQube analysis (if available locally)
dotnet sonarscanner begin /k:"[project-key]" /d:sonar.cs.opencover.reportsPaths="**/coverage.opencover.xml"
dotnet build --no-incremental
dotnet test --collect:"XPlat Code Coverage" -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=opencover
dotnet sonarscanner end
```

### Dependency File

`.csproj` files with `<PackageReference>` entries (versions centralized in `Directory.Packages.props`).

---

## §deviation-rules — When Deviations Are Required

A Deviation Record (`docs/deviations/DEV-NNN-[slug].md`) MUST be created when:

- Suppressing a StyleCop/SonarQube rule not in the "Accepted Suppressions" list
- Using manual static mappers instead of `IBuilder<TInput, TOutput>`
- Skipping soft deletes, FluentValidation, or any mandatory pattern
- Adding packages not in the blueprint stack
- Changing the architecture structure
- Any SDLC process deviation

---

*Blueprint reference for .NET Hexagonal stack*
*Source: Extracted from harness v1.0 (pre-separation)*
