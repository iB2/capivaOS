# Solution Document — [Service Name]

## Overview
- **Service Name**: [name]
- **Repository**: [GitHub URL]
- **Pipeline**: [CI/CD pipeline URL — per blueprint §ci-cd]
- **Quality Gate Project**: [project key, if a quality gate tool is used — per blueprint §static-analysis]
- **Owner Team**: [team name]

## Architecture

### Layer Map

[Map the service's directories to the architectural layers defined in the active
blueprint's reference.md §architecture. Example shape:]

```
[layer 1 path]/    → [what lives here — entities, business logic]
[layer 2 path]/    → [what lives here — services, use cases]
[layer 3 path]/    → [what lives here — persistence, external clients]
[layer 4 path]/    → [what lives here — API surface, entry points]
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

- **Template**: [CI/CD platform per blueprint §ci-cd]
- **Triggers**: main, release/*, develop
- **Environments**: DEV → UAT → Production

### Infrastructure Provisioning

[What cloud/infrastructure resources are needed and how they're provisioned]

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
