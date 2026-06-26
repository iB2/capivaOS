# Enterprise Blueprint — Hard Constraints

> These constraints come from the Capiva OS enterprise blueprint template and SDLC Process Documentation.
> They are NOT suggestions — they are enforceable rules. The harness validates compliance at every phase.

---

## Architecture: Hexagonal (Ports & Adapters)

Every project MUST follow the Hexagonal Architecture pattern from the blueprint:

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

---

## .NET Version & Language

- **Target**: .NET 10 (`net10.0`) — NOT .NET 8
- **C# version**: Latest (C# 13+)
- **SDK**: 10.0.x
- **Nullable reference types**: `enable` (project-wide)
- **Implicit usings**: `enable`

---

## Enterprise Patterns (MANDATORY)

### Use Case Pattern

One class per business operation. Every use case has an interface.

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

Use `IBuilder<TInput, TOutput>` from `Application/Mapping/` for all DTO ↔ Entity transformations. The mapping interfaces and implementation (`IBuilder`, `Builder`, `MappingExtensions`) live inside the Application project — no external package required.

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

**Deviation allowed**: If the inlined mapping pattern doesn't fit (e.g., Azure Functions project with simple transforms), manual static mappers are acceptable — but MUST be documented via a Deviation Record (see below).

### Bootstrapper Pattern

Layered DI registration. Each layer owns its registrations:

```csharp
// In Application project
public static class ApplicationBootstrapper
{
    public static IServiceCollection Register(this IServiceCollection services)
    {
        _ = services.AddTransient<ICreateCustomerUseCase, CreateCustomerUseCase>();
        _ = services.AddMapping(typeof(ApplicationBootstrapper).Assembly);
        return services;
    }
}

// In Infrastructure project
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
                Detail = ex.Message
            });
        }
    }
}
```

### Soft Deletes

Entities use an `Active` boolean flag — NEVER hard delete:

```csharp
public bool Active { get; set; } = true;
```

Repository queries filter by `Active == true` by default. "Delete" operations set `Active = false`.

**Deviation allowed**: Status-based lifecycle (e.g., `Resolved`, `Cancelled`) may replace soft deletes when the business domain requires it — document via Deviation Record.

---

## Code Style (MANDATORY)

### Primary Constructors (C# 12+)

ALL classes with DI use primary constructors:

```csharp
// CORRECT
public sealed class QuoteService(IQuoteRepository repository, ILogger<QuoteService> logger)

// WRONG — do not use traditional constructors for DI
public class QuoteService
{
    private readonly IQuoteRepository _repository;
    public QuoteService(IQuoteRepository repository) => _repository = repository;
}
```

### Sealed Classes

ALL classes are `sealed` unless explicitly designed for inheritance (rare):

```csharp
public sealed class QuoteService(IQuoteRepository repository) : IQuoteService { }
```

### Explicit Interface Implementation

Services use explicit interface implementation — consumers access via interface, not concrete type:

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

Sort members alphabetically within their visibility group, respecting StyleCop ordering:
1. Constants
2. Static fields
3. Instance fields
4. Constructors
5. Properties
6. Methods

Within each group, sort A→Z.

### Discard Pattern

Use `_ =` for fluent API return values that aren't consumed:

```csharp
_ = services.AddTransient<IQuoteService, QuoteService>();
_ = app.UseMiddleware<ExceptionHandlingMiddleware>();
```

### Guard Validation

Use built-in guard methods:

```csharp
ArgumentNullException.ThrowIfNull(customer);
ArgumentException.ThrowIfNullOrWhiteSpace(customer.Name);
```

### Private Field Naming

Use `_camelCase` for private fields (SA1309 suppressed in .editorconfig):

```csharp
private readonly IQuoteRepository _repository;
```

### DTOs as Records

All Data Transfer Objects MUST be immutable records:

```csharp
public sealed record CreateCustomerRequest(string Name, string Email);
public sealed record CustomerResponse(Guid Id, string Name, string Email);
```

---

## Static Analysis (MANDATORY)

### Required Analyzers

Every project MUST include (via `Directory.Build.props`):

```xml
<ItemGroup>
  <PackageReference Include="SonarAnalyzer.CSharp" PrivateAssets="all" />
  <PackageReference Include="StyleCop.Analyzers" PrivateAssets="all">
    <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
  </PackageReference>
</ItemGroup>
```

### Analysis Mode

```xml
<AnalysisMode>AllEnabledByDefault</AnalysisMode>
```

### Accepted Suppressions

These StyleCop rules may be suppressed when justified:

| Rule | Description | When Acceptable |
|------|-------------|-----------------|
| SA0001 | XML comment analysis disabled | When not producing a public library |
| SA1101 | `this.` prefix | ONLY suppress if the entire team agrees (blueprint enables it) |
| SA1309 | Field names must not begin with underscore | Suppressed for `_camelCase` convention |
| SA1600-SA1602 | XML documentation | When not producing a public library |
| SA1633 | File header | When file headers are not required |

Any OTHER suppression requires a Deviation Record.

---

## CI/CD: Azure Pipelines

**NOT GitHub Actions.** All CI/CD uses Azure Pipelines with a standalone pipeline (build, test, publish, deploy).

### Pipeline Template

See `templates/azure-pipelines.yml` for the base configuration.

### Key Configuration

- **Triggers**: `main`, `release/*`, `develop`
- **PR triggers**: `main`, `release/*`, `feature/*`, `hotfix/*`, `develop`
- **SDK**: .NET 10.0.x
- **SonarQube**: Mandatory for all builds
- **Coverage**: cobertura + opencover formats
- **Deploy**: 3 environments (dev, uat, prod) on Linux stack

---

## Central Package Management

All projects use `Directory.Packages.props` at solution root. Individual `.csproj` files reference packages WITHOUT version numbers:

```xml
<!-- In .csproj -->
<PackageReference Include="FluentValidation" />

<!-- Version defined ONLY in Directory.Packages.props -->
<PackageVersion Include="FluentValidation" Version="12.1.1" />
```

See `templates/Directory.Packages.props` for the current version pins.

---

## Standard Libraries

| Library | Location | Purpose |
|---------|----------|---------|
| Mapping (`IBuilder<TInput, TOutput>`) | `Application/Mapping/` (inlined) | DTO ↔ Entity transformations |
| Logging | Native `ILogger<T>` | Structured logging via ASP.NET Core |

Additional packages (e.g., Azure Service Bus, audit clients) are added per project as needed from nuget.org.

---

## SDLC Process Compliance

### Commit Convention — Karma Format

Commit format follows Karma convention. See `.claude/rules/board-protocol.md` for format, scopes, and examples.

### Code Review Standards (from SDLC)

These are enforced during /test-verify and /finish:

1. **SOLID principles** — every class has a single responsibility
2. **DTOs as immutable records** — never mutable classes for data transfer
3. **Method parameters**: 0 ideal, 1-2 normal, 3+ needs justification via comment
4. **`if` blocks**: should contain ONE line of logic. Extract methods for complex conditionals
5. **No magic numbers** — use named constants
6. **No deep nesting** — max 2 levels of indentation

### Environment Progression

```
DEV → UAT → Sandbox (optional) → Production
```

- Merge to `main` happens AFTER production validation (not before)
- Each environment has its own Azure Pipelines stage
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

- Suppressing a StyleCop/SonarQube rule not in the "Accepted Suppressions" list
- Using a different pattern than specified (e.g., manual mappers instead of `IBuilder<TInput, TOutput>`)
- Skipping a mandatory pattern (e.g., no soft deletes, no FluentValidation)
- Adding packages not in the blueprint stack
- Changing the architecture structure
- Any SDLC process deviation

### Process

1. Create `docs/deviations/DEV-NNN-[slug].md` using the template at `templates/deviation-record.md`
2. Reference the deviation in the PR description
3. The deviation is reviewed as part of the PR code review
4. Approved deviations are binding — future work follows the deviation, not the blueprint

### Template Location

`templates/deviation-record.md` — use this for all deviation records.

---

## Blueprint Reference

The enterprise blueprint is codified in this harness. The harness rules ARE the blueprint — do NOT modify them without an ADR justifying the change.

---

*Enterprise blueprint constraints for the Capiva OS development harness*
*Source: Capiva OS Blueprint + SDLC Process Documentation*
