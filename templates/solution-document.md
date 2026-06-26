# Solution Document — [Service Name]

## Overview
- **Service Name**: [name]
- **Repository**: [GitHub URL]
- **Pipeline**: [Azure Pipelines URL]
- **SonarQube Project**: [project key]
- **Owner Team**: [team name]

## Architecture

### Hexagonal Layer Map

```
src/Core/
  [Project].Domain/           → [entities, interfaces]
  [Project].Application/      → [use cases, DTOs, validators]
src/Driven/
  [Project].Infrastructure/   → [repositories, external clients]
src/Drivers/
  [Project].Api/              → [controllers, middleware]
  [Project].FunctionDriver/   → [triggers] (if applicable)
```

### Component Diagram

```
[ASCII diagram of key components and their interactions]
```

### Data Model

[Key entities and their relationships — reference DER if exists]

## Dependencies

### Inlined Libraries

| Library | Location | Purpose |
|---------|----------|---------|
| Mapping (`IBuilder<TInput, TOutput>`) | `Application/Mapping/` | DTO ↔ Entity transformations |
| Logging | Native `ILogger<T>` | Structured logging |

### External Packages

| Package | Version | Purpose |
|---------|---------|---------|
| [package] | [version] | [purpose] |

### Infrastructure Dependencies

| Resource | Type | Environment |
|----------|------|-------------|
| [resource] | SQL Server / Redis / Service Bus / etc. | DEV / UAT / PROD |

## Configuration

### App Settings

| Setting | Description | Default | Sensitive? |
|---------|-------------|---------|------------|
| [key] | [description] | [default] | Yes/No |

### Connection Strings

| Name | Target | Notes |
|------|--------|-------|
| [name] | [what it connects to] | [any notes] |

## Deployment

### Pipeline

- **Template**: Standalone Azure Pipelines
- **Triggers**: main, release/*, develop
- **Environments**: DEV → UAT → Production

### Infrastructure Provisioning

[What Azure resources are needed and how they're provisioned]

## Monitoring

### Health Checks

| Endpoint | What It Checks |
|----------|---------------|
| `/health` | [components checked] |

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| [metric] | [what it measures] | [when to alert] |

## ADRs

| ID | Title | Status |
|----|-------|--------|
| [NNNN] | [title] | Accepted |

## Deviations from Blueprint

| ID | What | Why | Status |
|----|------|-----|--------|
| DEV-001 | [deviation] | [reason] | Approved |
