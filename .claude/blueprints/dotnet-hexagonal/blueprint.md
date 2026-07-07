# Blueprint: .NET Hexagonal (.NET 10 + C# 13 + ASP.NET Core)

> Stack reference for Capiva OS harness. See `reference.md` for the full blueprint.

## Stack Summary

- **Runtime**: .NET 10 (`net10.0`)
- **Language**: C# 13 (nullable enabled, implicit usings)
- **Framework**: ASP.NET Core Web API + Azure Functions (optional)
- **Architecture**: Hexagonal (Ports & Adapters)
- **Database**: SQL Server (EF Core 10) + Redis (StackExchange.Redis)
- **Testing**: xUnit + AwesomeAssertions + NSubstitute + Testcontainers
- **Linting**: StyleCop analyzers + SonarQube quality gate
- **Validation**: FluentValidation 12.x
- **CI/CD**: Azure Pipelines (DEV → UAT → Production)
