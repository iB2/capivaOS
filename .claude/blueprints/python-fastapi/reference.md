# Blueprint Reference: Python FastAPI (Python 3.11+ / FastAPI)

> This file is the bridge between the stack-agnostic harness and the Python FastAPI blueprint project.
> Agent roles and skills read this file to get stack-specific patterns, commands, and standards.

## §project — Blueprint Project

- **Path**: `C:\Users\bruno\Documents\DevProjects\blueprint-python-fastapi\`
- **Type**: Python FastAPI project with layered architecture
- **Contents**: ~30 files — app (routes, services, repositories, schemas, models), tests, Dockerfile, CI pipeline
- **Status**: Functional, scaffoldable

---

## §stack — Technology Identity

| Property | Value |
|----------|-------|
| Language | Python 3.11+ |
| Runtime | CPython |
| Framework | FastAPI (latest) |
| Database | PostgreSQL (SQLAlchemy async) / SQLite for dev |
| Cache | Redis (redis-py async) |
| DI | FastAPI `Depends()` |
| Validation | Pydantic v2 (built into FastAPI) |
| Type checking | mypy (strict mode) |

---

## §architecture — Layered Architecture

### Project Structure

```
app/
  api/v1/              # Route handlers (thin — delegate to services)
    router.py           # Include all feature routers
    health.py           # GET /health
    customers.py        # Customer CRUD endpoints
  core/                 # Cross-cutting concerns
    exceptions.py       # Custom exception classes
    middleware.py        # Error handling middleware
  schemas/              # Pydantic models (request/response DTOs)
    customer.py
  services/             # Business logic (equivalent to Use Cases)
    customer_service.py
  db/                   # Database layer
    session.py          # SQLAlchemy async session factory
    base.py             # Base model with soft delete
    models/             # SQLAlchemy models
      customer.py
  repositories/         # Data access (async, soft deletes)
    customer_repository.py
  graph/                # Optional: LangGraph agentic module
    state.py            # TypedDict state
    agent.py            # Graph definition
  utils/                # Shared utilities
    rate_limit.py
  main.py               # FastAPI app factory
  config.py             # pydantic-settings configuration

tests/
  conftest.py           # Fixtures
  test_health.py
  test_customers.py
  services/
    test_customer_service.py
```

### Dependency Direction

```
api/ → services/ → repositories/ → db/models/
         ↓
      schemas/ (DTOs used across layers)
```

- **api/**: Thin route handlers. Delegate ALL logic to services.
- **services/**: Business logic. Depend on repositories and schemas.
- **repositories/**: Data access. Async SQLAlchemy queries.
- **db/models/**: SQLAlchemy ORM models. No business logic.
- **schemas/**: Pydantic models. Shared between layers for request/response.

---

## §coding-standards — Python Conventions

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Module | snake_case | `customer_service.py` |
| Class | PascalCase | `CustomerService` |
| Function / Method | snake_case | `get_active_customers` |
| Variable | snake_case | `active_count` |
| Constant | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Private | `_` prefix | `_validate_email` |
| Type alias | PascalCase | `CustomerList = list[Customer]` |
| Async function | No special suffix | `async def get_by_id(...)` |

### Mandatory Code Style

- **Type hints on all function signatures** (parameters and return types)
- **Pydantic models for all DTOs** — never pass raw dicts across layers
- **Async everywhere** — all I/O operations use `async`/`await`
- **Dependency injection via `Depends()`** — no global state, no module-level singletons
- **`from __future__ import annotations`** at top of every module
- **Dataclasses or Pydantic for data containers** — no plain dicts for structured data
- **No mutable default arguments** — use `None` + assignment in body
- **One class per file** for models, services, and repositories (small helpers can share)

### Code Style Examples

```python
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerResponse


class CustomerService:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def create(self, data: CustomerCreate) -> CustomerResponse:
        customer = await self._repository.create(data)
        return CustomerResponse.model_validate(customer)
```

### Error Handling

- Custom exception hierarchy inheriting from a base `AppError`
- Middleware catches exceptions and returns structured JSON (ProblemDetails-style):

```json
{
  "type": "https://errors.capiva.tech/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Customer with id 'abc' not found"
}
```

- No bare `except Exception` — catch specific exceptions
- FastAPI's `HTTPException` only used in route handlers, never in services

---

## §enterprise-patterns — Mandatory Patterns

### Service Pattern (equivalent to Use Case)

One service class per domain entity. Methods map to operations. Dependency injected via constructor.

```python
class CustomerService:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def create(self, data: CustomerCreate) -> CustomerResponse:
        customer = await self._repository.create(data)
        return CustomerResponse.model_validate(customer)

    async def get_by_id(self, customer_id: uuid.UUID) -> CustomerResponse:
        customer = await self._repository.get_by_id(customer_id)
        if not customer:
            raise NotFoundError(f"Customer {customer_id} not found")
        return CustomerResponse.model_validate(customer)
```

### Repository Pattern

Async SQLAlchemy, returns ORM models. Services convert to Pydantic schemas.

```python
class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.active == True,  # noqa: E712 — SQLAlchemy requires == for column comparison
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
```

### Soft Deletes

All models inherit from `SoftDeleteBase` with `active: bool = True`.

```python
class SoftDeleteBase(Base):
    __abstract__ = True
    active: Mapped[bool] = mapped_column(default=True)
```

- Repository queries MUST filter `active == True` by default
- "Delete" operations set `active = False`, never remove the row
- Queries that need deleted records must explicitly opt-in

### Dependency Injection (FastAPI)

```python
async def get_customer_service(
    session: AsyncSession = Depends(get_session),
) -> CustomerService:
    repository = CustomerRepository(session)
    return CustomerService(repository)

@router.get("/{customer_id}")
async def get_customer(
    customer_id: uuid.UUID,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.get_by_id(customer_id)
```

### Pydantic Schemas (DTOs)

```python
class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr

class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: str
    active: bool
    created_at: datetime
```

### Configuration (pydantic-settings)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    database_url: str = "sqlite+aiosqlite:///./app.db"
    debug: bool = False
    api_prefix: str = "/api/v1"
```

---

## §test-stack — Test Frameworks & Conventions

### Packages

| Package | Purpose |
|---------|---------|
| pytest | Test framework |
| pytest-asyncio | Async test support |
| httpx | AsyncClient for API tests |
| coverage | Code coverage |
| ruff | Linting (replaces flake8/black/isort) |
| mypy | Static type checking |
| factory-boy | Test data generation (optional) |

### Test Naming

`test_<what>_<scenario>_<expected>` or `test_<behavior_description>`

### Test Organization

- `conftest.py` with shared fixtures (test client, test database session)
- API tests use `httpx.AsyncClient` against the FastAPI test app
- Service tests use real database (in-memory SQLite) — no mocks for data access
- Unit tests for pure logic use standard pytest

### Test Example

```python
@pytest.mark.asyncio
async def test_create_customer_returns_201(client: AsyncClient) -> None:
    response = await client.post("/api/v1/customers", json={
        "name": "Test Customer",
        "email": "test@example.com",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Customer"
    assert data["active"] is True
```

### Fixtures

```python
@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

---

## §static-analysis — Linters & Analyzers

### ruff (linter + formatter)

```toml
# ruff.toml
target-version = "py311"
line-length = 120

[lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM", "TCH", "RUF"]

[lint.isort]
known-first-party = ["app"]
```

### mypy (type checker)

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

---

## §ci-cd — Pipeline Configuration

### Azure Pipelines

See blueprint project `azure-pipelines.yml`.

Stages:
1. **Lint**: `ruff check .` + `mypy app/`
2. **Test**: `pytest --cov=app --cov-report=xml`
3. **Build**: `docker build -t app .`
4. **Deploy**: Push to container registry, deploy to Azure App Service

### Dockerfile (Multi-stage)

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY app/ app/
CMD ["uvicorn", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
```

---

## §qa-checklist — Stack-Specific QA Items

| Check | What to Look For |
|-------|-----------------|
| Type hints | All function signatures have type hints (params + return) |
| Pydantic models | All DTOs are Pydantic BaseModel subclasses |
| Soft deletes | Repository queries filter `active == True`. No hard deletes |
| Async | All I/O operations use async/await |
| Dependency injection | All services use `Depends()`, no global state |
| Error handling | Custom exceptions, ProblemDetails-style JSON, no bare `except` |
| ruff clean | `ruff check .` returns zero issues |
| mypy clean | `mypy app/` returns zero errors |
| Test coverage | pytest with `--cov` shows adequate coverage |
| Naming | snake_case functions/vars, PascalCase classes, UPPER_SNAKE constants |

---

## §build-commands — Build, Test & Verify

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run specific test
pytest tests/test_customers.py::test_create_customer_returns_201

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Lint
ruff check .
ruff format --check .

# Type check
mypy app/

# Run the app
uvicorn app.main:create_app --reload --factory

# Build Docker image
docker build -t blueprint-fastapi .
```

### Dependency File

`requirements.txt` (production) + `requirements-dev.txt` (dev/test tools).

---

*Blueprint reference for Python FastAPI stack*
*Source: Created for harness v2.0 (blueprint separation)*
