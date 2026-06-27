# Blueprint Reference: Python FastAPI (Python 3.13 / FastAPI)

> This file is the bridge between the stack-agnostic harness and the Python FastAPI blueprint project.
> Agent roles and skills read this file to get stack-specific patterns, commands, and standards.

## §project — Blueprint Project

- **Path**: `C:\Users\bruno\Documents\DevProjects\blueprint-python-fastapi\`
- **Type**: Python FastAPI project with layered architecture
- **Contents**: ~30 files — app (routes, services, repositories, schemas), tests, Dockerfile, CI pipeline
- **Status**: Functional, scaffoldable

---

## §stack — Technology Identity

| Property | Value |
|----------|-------|
| Language | Python 3.13 |
| Runtime | CPython |
| Framework | FastAPI |
| Database | PostgreSQL (psycopg v3 async — raw SQL, no ORM) |
| Cache | Redis (redis-py async) |
| DI | FastAPI `Depends()` |
| Validation | Pydantic v2 (built into FastAPI) |
| Type checking | mypy (strict mode) |
| Logging | structlog (structured JSON logging) |
| Rate limiting | slowapi (based on limits) |
| Observability | OpenTelemetry (traces + metrics) |

### Dependency Pinning

All dependencies MUST use exact pinned versions (`==`), not ranges (`>=`). This ensures reproducible builds and prevents supply chain drift.

```
# requirements.txt — CORRECT
fastapi==0.115.6
uvicorn[standard]==0.34.0

# WRONG — never use ranges
fastapi>=0.115.0,<1.0.0
```

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
    logging.py          # structlog configuration
    telemetry.py        # OpenTelemetry setup
  schemas/              # Pydantic models (request/response DTOs)
    customer.py
  services/             # Business logic (equivalent to Use Cases)
    customer_service.py
  db/                   # Database layer
    pool.py             # psycopg AsyncConnectionPool factory
  repositories/         # Data access (raw SQL, parameterized queries)
    customer_repository.py
  graph/                # Optional: LangGraph agentic module
    state.py            # TypedDict state
    agent.py            # Graph definition
  utils/                # Shared utilities
  main.py               # FastAPI app factory
  config.py             # pydantic-settings configuration

tests/
  conftest.py           # Fixtures (test database, client)
  test_health.py
  test_customers.py
  services/
    test_customer_service.py
```

### Dependency Direction

```
api/ → services/ → repositories/ → db/pool
         ↓
      schemas/ (DTOs used across layers)
```

- **api/**: Thin route handlers. Delegate ALL logic to services.
- **services/**: Business logic. Depend on repositories and schemas.
- **repositories/**: Data access. Raw SQL with psycopg, parameterized queries. Returns dicts (via `dict_row`).
- **db/pool.py**: psycopg `AsyncConnectionPool`. No ORM, no models directory.
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
| Type alias | PascalCase | `CustomerList = list[dict]` |
| Async function | No special suffix | `async def get_by_id(...)` |

### Mandatory Code Style

- **Type hints on all function signatures** (parameters and return types)
- **Pydantic models for all DTOs** — never pass raw dicts across API boundaries (repositories return dicts, services convert to Pydantic)
- **Async everywhere** — all I/O operations use `async`/`await`
- **Dependency injection via `Depends()`** — no global state, no module-level singletons
- **`from __future__ import annotations`** at top of every module
- **Dataclasses or Pydantic for data containers** — no plain dicts for structured data (except raw DB results)
- **No mutable default arguments** — use `None` + assignment in body
- **One class per file** for services and repositories (small helpers can share)
- **structlog for all logging** — never use `print()` or stdlib `logging` directly
- **No ORM** — all database access via raw SQL with parameterized queries

### Code Style Examples

```python
from __future__ import annotations

import structlog
from fastapi import Depends
from psycopg import AsyncConnection

from app.db.pool import get_connection
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerResponse

logger = structlog.get_logger()


class CustomerService:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def create(self, data: CustomerCreate) -> CustomerResponse:
        row = await self._repository.create(data.model_dump())
        logger.info("customer_created", customer_id=row["id"])
        return CustomerResponse.model_validate(row)
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
        row = await self._repository.create(data.model_dump())
        return CustomerResponse.model_validate(row)

    async def get_by_id(self, customer_id: str) -> CustomerResponse:
        row = await self._repository.get_by_id(customer_id)
        if not row:
            raise NotFoundError("Customer", customer_id)
        return CustomerResponse.model_validate(row)
```

### Repository Pattern (Raw SQL)

No ORM. Parameterized queries only. `dict_row` factory for dict results (equivalent to psycopg2's `RealDictCursor`).

```python
from psycopg import AsyncConnection
from psycopg.rows import dict_row


class CustomerRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def get_by_id(self, customer_id: str) -> dict | None:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT * FROM customers WHERE id = %s AND active = true",
                (customer_id,),
            )
            return await cur.fetchone()

    async def get_all(self, page: int, page_size: int) -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT count(*) AS total FROM customers WHERE active = true",
            )
            count_row = await cur.fetchone()
            total = count_row["total"]

            await cur.execute(
                "SELECT * FROM customers WHERE active = true "
                "ORDER BY created_at DESC OFFSET %s LIMIT %s",
                (offset, page_size),
            )
            rows = await cur.fetchall()
        return rows, total

    async def create(self, data: dict) -> dict:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """INSERT INTO customers
                   (id, name, email, phone_number, active, created_at, created_by)
                   VALUES (gen_random_uuid()::text, %(name)s, %(email)s,
                           %(phone_number)s, true, now(), 'system')
                   RETURNING *""",
                data,
            )
            return await cur.fetchone()

    async def soft_delete(self, customer_id: str) -> bool:
        async with self._conn.cursor() as cur:
            await cur.execute(
                "UPDATE customers SET active = false, updated_at = now() "
                "WHERE id = %s AND active = true",
                (customer_id,),
            )
            return cur.rowcount > 0
```

### Soft Deletes

All tables include `active boolean NOT NULL DEFAULT true` column.

- Repository queries MUST filter `WHERE active = true` by default
- "Delete" operations execute `UPDATE ... SET active = false`, never `DELETE FROM`
- Queries that need deleted records must explicitly opt-in

### Database Schema Convention

Tables are created and managed via SQL migration files (not ORM auto-generation). Example:

```sql
CREATE TABLE IF NOT EXISTS customers (
    id           TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name         VARCHAR(200) NOT NULL,
    email        VARCHAR(254) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    active       BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by   VARCHAR(200) NOT NULL DEFAULT 'system',
    updated_at   TIMESTAMPTZ,
    updated_by   VARCHAR(200)
);
```

### Dependency Injection (FastAPI)

```python
from psycopg import AsyncConnection

async def get_customer_service(
    conn: AsyncConnection = Depends(get_connection),
) -> CustomerService:
    repository = CustomerRepository(conn)
    return CustomerService(repository)

@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.get_by_id(customer_id)
```

### Pydantic Schemas (DTOs)

```python
class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone_number: str = Field(..., min_length=1, max_length=20)

class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    phone_number: str
    active: bool
    created_at: datetime
```

### Configuration (pydantic-settings)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    database_url: str = "postgresql://postgres:postgres@localhost:5432/app"
    debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    otel_service_name: str = "blueprint-api"
    otel_exporter_endpoint: str = ""
```

### Structured Logging (structlog)

```python
import structlog

def configure_logging(debug: bool = False) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if debug
            else structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

### Rate Limiting (slowapi)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/customers")
@limiter.limit("60/minute")
async def list_customers(request: Request, ...):
    ...
```

### Observability (OpenTelemetry)

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_telemetry(app: FastAPI, settings: Settings) -> None:
    if settings.otel_exporter_endpoint:
        # Configure OTLP exporter for production
        ...
    FastAPIInstrumentor.instrument_app(app)
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
| testcontainers | PostgreSQL container for integration tests (optional) |

### Test Naming

`test_<what>_<scenario>_<expected>` or `test_<behavior_description>`

### Test Organization

- `conftest.py` with shared fixtures (test client, test database connection)
- API tests use `httpx.AsyncClient` against the FastAPI test app
- Integration tests use PostgreSQL (real or via testcontainers) — no SQLite substitution
- Service tests can mock repositories for unit isolation
- Unit tests for pure logic use standard pytest

### Test Example

```python
@pytest.mark.asyncio
async def test_create_customer_returns_201(client: AsyncClient) -> None:
    response = await client.post("/api/v1/customers", json={
        "name": "Test Customer",
        "email": "test@example.com",
        "phone_number": "+5511999990000",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Customer"
    assert data["active"] is True
```

### Fixtures

```python
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

---

## §static-analysis — Linters & Analyzers

### ruff (linter + formatter)

```toml
# ruff.toml
target-version = "py313"
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
python_version = "3.13"
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

### Dockerfile (Multi-stage, non-root)

```dockerfile
FROM python:3.13-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-slim
RUN adduser --disabled-password --no-create-home appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ app/
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
```

---

## §qa-checklist — Stack-Specific QA Items

| Check | What to Look For |
|-------|-----------------|
| Type hints | All function signatures have type hints (params + return) |
| Pydantic models | All DTOs are Pydantic BaseModel subclasses |
| No ORM | No SQLAlchemy imports. Raw SQL with psycopg only |
| Parameterized queries | All SQL uses `%s` or `%(name)s` placeholders — never f-strings or string concatenation |
| Soft deletes | Repository queries filter `WHERE active = true`. No `DELETE FROM` |
| Async | All I/O operations use async/await |
| Dependency injection | All services use `Depends()`, no global state |
| Error handling | Custom exceptions, ProblemDetails-style JSON, no bare `except` |
| Structured logging | All logging via structlog, no `print()` or stdlib logging |
| Rate limiting | slowapi applied to public endpoints |
| ruff clean | `ruff check .` returns zero issues |
| mypy clean | `mypy app/` returns zero errors |
| Test coverage | pytest with `--cov` shows adequate coverage |
| Pinned deps | All versions in requirements.txt use `==`, not `>=` |
| Non-root Docker | Dockerfile uses `adduser` + `USER appuser` |
| Naming | snake_case functions/vars, PascalCase classes, UPPER_SNAKE constants |

---

## §build-commands — Build, Test & Verify

```bash
# Install dependencies (pinned versions)
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

### Dependency Files

`requirements.txt` (production) + `requirements-dev.txt` (dev/test tools). All versions pinned with `==`.

### Dependency Pinning Rules

- **Pin exact versions** with `==` (e.g., `fastapi==0.115.6`)
- **Never use ranges** (`>=`, `~=`, `<`)
- **Update pins deliberately** — run `pip-compile` or manually update when upgrading
- **Lock file**: `requirements.txt` IS the lock file. No separate `poetry.lock` or `Pipfile.lock`

---

## §deviation-rules — Accepted Deviations

None currently defined. All deviations from this reference require a formal Deviation Record.

---

*Blueprint reference for Python FastAPI stack*
*Source: Capiva OS Blueprint (aligned with SSB/Serta Python stack agreement)*
