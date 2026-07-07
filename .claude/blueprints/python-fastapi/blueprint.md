# Blueprint: Python FastAPI (Python 3.13 + FastAPI)

> Stack reference for Capiva OS harness. Agent roles and skills inject this file for stack-specific guidance.
> These are enforceable rules — the harness validates compliance at every phase.
> Based on SSB production backends (SSB-Quiz, ssb-mattress-backend) with quality improvements.

---

## 1. Stack & Version

- **Runtime**: Python 3.13 (latest stable)
- **Framework**: FastAPI 0.117+
- **ASGI Server**: uvicorn 0.36+
- **Type system**: Type hints mandatory on all function signatures and class attributes
- **Package manager**: pip with `requirements.txt` (or `pyproject.toml` for libraries)

---

## 2. Architecture: Layered Modules

```
app/
  __init__.py
  main.py                          # FastAPI app factory + lifespan (migrations, pool init)
  api/
    __init__.py
    v1/
      __init__.py
      <feature>.py                 # Route handlers — one file per domain
  core/
    __init__.py
    config.py                      # Pydantic BaseSettings + secrets loader
    logging_setup.py               # structlog + stdlib logging configuration
    tracing.py                     # OpenTelemetry + Application Insights
  services/
    __init__.py
    <domain>.py                    # Business logic — functions, not classes
  schemas/
    __init__.py
    errors.py                      # ErrorResponse model + error_code_for_status()
    <domain>.py                    # Request/Response Pydantic models per domain
  db/
    __init__.py
    pool.py                        # Connection pooling (psycopg2 ThreadedConnectionPool)
    migrations/                    # Numbered idempotent .sql files (001-*.sql)
  utils/
    __init__.py
    rate_limit.py                  # SlowAPI limiter setup

tests/
  __init__.py
  conftest.py                      # Shared fixtures, env vars, mock factories
  test_api.py                      # Integration tests (HTTP endpoints)
  test_<domain>.py                 # Unit tests per domain
  services/
    test_<service>.py              # Service-layer unit tests
```

### Dependency Direction

```
api/ → services/ → db/
         ↓
      schemas/
         ↓
       core/
```

- **api/v1/**: Route handlers. THIN — validate input, call service, return response. No business logic.
- **services/**: Business logic. Functions (not classes). May call db/ and other services.
- **schemas/**: Pydantic models for request/response validation. No logic beyond validation.
- **db/**: Database access. Raw SQL with parameterized queries. Connection pooling.
- **core/**: Cross-cutting concerns — config, logging, tracing. No business logic.
- **NO circular imports. NO route handlers calling db/ directly.**

### Module Convention

```
app.<layer>.<domain>
```

Example: `app.services.catalog`, `app.api.v1.quiz`, `app.schemas.chat`

---

## 3. Patterns (MANDATORY)

### Service Functions (Not Classes)

Business logic lives in service modules as standalone async functions. No service classes with state — functions are easier to test and compose.

```python
# app/services/customers.py

async def create_customer(request: CreateCustomerRequest, conn) -> CustomerResponse:
    """Create a new customer and return the response."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO customers (name, email, active) VALUES (%s, %s, true) RETURNING id",
        (request.name, request.email),
    )
    row = cur.fetchone()
    conn.commit()
    return CustomerResponse(id=row["id"], name=request.name, email=request.email)
```

**Deviation allowed**: Classes acceptable for stateful services (e.g., LLM client with connection pool) — document via Deviation Record.

### Pydantic Models for All I/O

All request/response schemas are Pydantic BaseModel subclasses. Every route MUST declare `response_model`:

```python
# app/schemas/customers.py

class CreateCustomerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr

class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str

# app/api/v1/customers.py

@router.post("/customers", response_model=CustomerResponse, status_code=201)
async def create_customer(request: CreateCustomerRequest):
    ...
```

### Config via Pydantic BaseSettings

All configuration in one place. Env vars → Key Vault → defaults:

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "app_db"
    pg_user: str = "postgres"
    pg_password: str = ""
    azure_openai_key: str = ""
    azure_openai_endpoint: str = ""
    allowed_origins: str = "http://localhost:3000"
    rate_limit_default: str = "60/minute"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

For Azure deployments, load secrets from Key Vault at startup:

```python
async def _load_keyvault_secrets(settings: Settings) -> None:
    if not settings.azure_keyvault_url:
        return
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    client = SecretClient(vault_url=settings.azure_keyvault_url, credential=DefaultAzureCredential())
    settings.pg_password = client.get_secret("pg-password").value
    # ... other secrets
```

### Consistent Error Responses

All errors return a structured ErrorResponse:

```python
# app/schemas/errors.py

class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    trace_id: str | None = None

def error_code_for_status(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_error",
    }.get(status_code, "unknown_error")
```

Register exception handlers in `main.py`:

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_error",
            detail=f"Trace ID: {request.state.trace_id}" if hasattr(request.state, "trace_id") else None,
        ).model_dump(),
    )
```

### Database: Raw SQL with psycopg2

No ORM. Parameterized queries only. RealDictCursor for dict results:

```python
# app/db/pool.py
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

_pool: ThreadedConnectionPool | None = None

def init_pool(settings) -> None:
    global _pool
    _pool = ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=settings.pg_host,
        port=settings.pg_port,
        dbname=settings.pg_database,
        user=settings.pg_user,
        password=settings.pg_password,
        cursor_factory=RealDictCursor,
    )

def get_conn():
    return _pool.getconn()

def put_conn(conn):
    _pool.putconn(conn)
```

**Rules**:
- NEVER use f-strings for SQL. Always `%s` parameters.
- Use `RealDictCursor` — rows come as dicts, not tuples.
- Connection pooling via `ThreadedConnectionPool`.
- Return connections to pool in `finally` blocks.

### Idempotent SQL Migrations

Numbered `.sql` files in `app/db/migrations/`. Applied on startup:

```sql
-- app/db/migrations/001_create_customers.sql
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    email VARCHAR(200) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email);
```

Pattern: `IF NOT EXISTS` / `DO $$ BEGIN ... END $$` for safe re-runs.

### Soft Deletes

Entities use `active` boolean column — NEVER hard delete:

```sql
-- "Delete" = set active to false
UPDATE customers SET active = false WHERE id = %s;

-- All queries filter by active
SELECT * FROM customers WHERE active = true AND id = %s;
```

**Deviation allowed**: Status-based lifecycle may replace soft deletes — document via Deviation Record.

### App Factory + Lifespan

FastAPI app created in `main.py` with async lifespan for startup/shutdown:

```python
# app/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    init_pool(settings)
    await _run_migrations(settings)
    yield
    # Shutdown
    close_pool()

app = FastAPI(title="Service Name", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins.split(","), ...)
app.include_router(customers_router, prefix="/api/v1")
```

### Rate Limiting

SlowAPI middleware with configurable limits per route:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/chat")
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest):
    ...
```

### Security Headers

Custom middleware for CSP, HSTS, X-Frame-Options:

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### Health Check

Every service exposes `GET /healthz`:

```python
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
```

---

## 4. Code Style (MANDATORY)

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Module | snake_case | `llm_client.py` |
| Function | snake_case | `get_active_customers` |
| Async function | snake_case (no suffix) | `create_customer` |
| Class | PascalCase | `CreateCustomerRequest` |
| Constant | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Variable | snake_case | `active_customers` |
| Private | `_` prefix | `_pool`, `_settings` |
| Type alias | PascalCase | `CustomerRow = dict[str, Any]` |

### Type Hints (MANDATORY)

Type hints on ALL function signatures and return types:

```python
# CORRECT
async def get_customer(customer_id: uuid.UUID, conn) -> CustomerResponse | None:
    ...

# WRONG — no type hints
async def get_customer(customer_id, conn):
    ...
```

Use `|` union syntax (Python 3.10+), not `Optional` or `Union`.

### Async/Await

- All I/O operations are async. No synchronous database calls from async routes.
- No fire-and-forget: every coroutine must be awaited.
- Use `background_tasks.add_task()` for non-critical I/O.
- No `asyncio.run()` inside async functions.

### Imports

Standard library → Third-party → Local, separated by blank lines:

```python
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.services import customers as customer_service
```

### Error Handling

- No bare `except:` — always catch specific exceptions.
- No swallowed exceptions: every `except` logs or re-raises.
- Use `HTTPException` for expected errors in route handlers.
- Use custom exception handler for unexpected errors.
- Validation at API boundary via Pydantic models.

### Comments

- No comments explaining WHAT — code is self-documenting.
- Comments for WHY only: non-obvious decisions, workarounds, business rules.
- Docstrings on public service functions (one line only).
- No TODO/HACK without a board task.

### Code Smells to Avoid

- God module: no module over 300 lines
- Global mutable state: only for connection pools and settings (singleton)
- Circular imports: restructure modules if they occur
- String typing: use enums or Literal types
- Deep nesting: max 3 levels of indentation

---

## 5. Static Analysis (MANDATORY)

### Required Tools

| Tool | Purpose | Config |
|------|---------|--------|
| ruff | Linting + formatting (replaces black, isort, flake8) | `ruff.toml` or `pyproject.toml` |
| mypy (basic) | Type checking | `mypy.ini` or `pyproject.toml` |

### Ruff Configuration

```toml
# ruff.toml
target-version = "py313"
line-length = 120

[lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM", "TCH"]
ignore = ["E501"]  # line length handled by formatter

[lint.isort]
known-first-party = ["app"]

[format]
quote-style = "double"
indent-style = "space"
```

### Mypy Configuration

```toml
# mypy section in pyproject.toml
[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # gradual adoption — tighten over time
check_untyped_defs = true
ignore_missing_imports = true
```

### Quality Commands

```bash
ruff check .                    # Lint
ruff format .                   # Format
mypy app/ --ignore-missing-imports  # Type check
```

### Accepted Suppressions

| Rule | Description | When Acceptable |
|------|-------------|-----------------|
| `# noqa: E501` | Line too long | Config lines, SQL strings, URLs |
| `# type: ignore` | Mypy suppression | Third-party libs without stubs |

Any OTHER suppression requires a Deviation Record.

---

## 6. Testing

### Test Stack

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 8.4+ | Test framework |
| pytest-asyncio | 1.2+ | Async test support |
| httpx | latest | Async HTTP test client |
| pytest-cov | latest | Coverage measurement |
| respx | latest | HTTP mock for httpx (external APIs) |
| testcontainers | latest | Real PostgreSQL/Redis in Docker |
| factory-boy | latest | Test data factories (optional) |

### Test Command

```bash
pytest --tb=short -q --cov=app --cov-report=html --cov-report=term-missing
```

### Coverage Targets

| Scope | Minimum | Target |
|-------|---------|--------|
| Services (business logic) | 80% | 90% |
| API routes | 70% | 80% |
| Overall | 75% | 85% |

### Coverage Exclusions

- `app/main.py` (startup/lifespan)
- `app/core/config.py` (settings loading)
- `app/core/tracing.py` (telemetry setup)
- `app/db/migrations/` (SQL files)

### Test Conventions

**conftest.py** — Set env vars BEFORE importing app modules:

```python
import os
_TEST_ENV = {
    "PG_HOST": "localhost",
    "PG_PORT": "5432",
    "PG_USER": "testuser",
    "PG_PASSWORD": "testpassword",
    "PG_DATABASE": "testdb",
}
for key, val in _TEST_ENV.items():
    os.environ.setdefault(key, val)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
```

- **Naming**: `test_<function_name>_<scenario>` (e.g., `test_create_customer_success`, `test_create_customer_duplicate_email`)
- **Organization**: Mirror source structure. `tests/services/test_catalog.py` tests `app/services/catalog.py`
- **Mocking**: `unittest.mock` (AsyncMock for async). `patch()` as context manager. Mock at service boundary, not deep internals.
- **Fixtures**: `scope="module"` for expensive setup (DB containers). `scope="function"` for test isolation.

### Integration Tests

Required when code touches:
- PostgreSQL — use `testcontainers.PostgreSqlContainer`
- Redis — use `testcontainers.RedisContainer`
- External HTTP APIs — use `respx` or `responses`

```python
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="module")
def pg_container():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture
def pg_conn(pg_container):
    import psycopg2
    conn = psycopg2.connect(pg_container.get_connection_url())
    yield conn
    conn.close()
```

### TDD Enforcement

1. **RED**: Write a failing test first
2. **GREEN**: Minimum code to pass
3. **REFACTOR**: Clean up, all tests still green

Verified via commit order (test commit before implementation) and QA review.

---

## 7. CI/CD: Azure DevOps

### Pipeline Template

```yaml
trigger:
  branches:
    include:
      - main
      - develop

stages:
  - stage: Build
    jobs:
      - job: BuildAndTest
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.13'

          - script: pip install -r requirements.txt
            displayName: 'Install dependencies'

          - script: ruff check . && ruff format --check .
            displayName: 'Lint & format check'

          - script: pytest --tb=short -q --junit-xml=test-results.xml --cov=app --cov-report=xml
            displayName: 'Run tests'

          - task: PublishTestResults@2
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: 'test-results.xml'

          - task: PublishCodeCoverageResults@2
            inputs:
              summaryFileLocation: 'coverage.xml'

  - stage: DockerBuild
    dependsOn: Build
    jobs:
      - job: BuildImage
        steps:
          - task: Docker@2
            inputs:
              containerRegistry: '$(acrConnection)'
              repository: '$(imageName)'
              command: 'buildAndPush'
              Dockerfile: 'Dockerfile'
              tags: '$(Build.BuildId)'

  - stage: Deploy_dev
    dependsOn: DockerBuild
    jobs:
      - deployment: Deploy
        environment: 'dev'
        strategy:
          runOnce:
            deploy:
              steps:
                - script: |
                    az containerapp update \
                      --name $(appName) \
                      --resource-group $(rgName) \
                      --image $(acrName).azurecr.io/$(imageName):$(Build.BuildId)
```

### Docker Template

```dockerfile
FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim
WORKDIR /app
RUN adduser --disabled-password --no-create-home appuser
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ app/
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Deployment Target

- **Runtime**: Azure Container Apps
- **Registry**: Azure Container Registry (ACR)
- **Database**: Azure Database for PostgreSQL Flexible Server
- **Secrets**: Azure Key Vault
- **Monitoring**: Application Insights (via OpenTelemetry)

### Environment Progression

```
DEV → TEST → Production
```

- Merge to `main` triggers DEV deploy automatically
- TEST and Production require manual approval via Azure DevOps Environments

---

## 8. Package Management

`requirements.txt` at project root. Pin exact versions for reproducibility:

```
fastapi==0.117.1
uvicorn==0.36.0
pydantic==2.11.9
pydantic-settings==2.9.1
psycopg2-binary==2.9.10
structlog==25.1.0
slowapi==0.1.9
ruff==0.9.10
pytest==8.4.2
pytest-asyncio==1.2.0
pytest-cov==6.1.0
```

**Rules**:
- Pin exact versions (`==`), not ranges (`>=`).
- Separate `requirements.txt` (production) and `requirements-dev.txt` (test/lint tools).
- No unused packages. Audit periodically.

---

## 9. Standard Libraries

| Library | Purpose |
|---------|---------|
| FastAPI | Web framework + OpenAPI docs |
| Pydantic | Request/response validation |
| psycopg2 | PostgreSQL access (raw SQL) |
| structlog | Structured logging |
| OpenTelemetry | Distributed tracing |
| SlowAPI | Rate limiting |
| uvicorn | ASGI production server |

### AI/Agentic Extension (Optional)

For projects with LLM orchestration (e.g., SSB chatbots):

| Library | Purpose |
|---------|---------|
| LangChain | LLM abstraction + chains |
| LangGraph | State machine conversation orchestration |
| Azure OpenAI SDK | LLM API access |
| LangSmith | LLM tracing/observability |
| ChromaDB | Vector search (RAG) |

**Agentic patterns**:
- State as `TypedDict` subclass with `Annotated` message accumulators
- Subgraphs per intent (recommendation, RAG, conversation, quiz)
- Checkpoints: PostgreSQL for production, SQLite for local dev
- Thread ID = conversation_id for multi-turn persistence

---

## 10. SDLC Compliance

### Commit Convention

Karma format. See `.claude/rules/board-protocol.md` for format, scopes, and examples.

### Code Review Standards

1. **Single responsibility** — one function does one thing
2. **Type hints** on all function signatures
3. **Method parameters**: 0-3 normal, 4+ refactor into a Pydantic model
4. **No bare except** — catch specific exceptions
5. **No magic strings/numbers** — use constants or enums
6. **Max 3 levels of indentation** per function

### Quality Gates

| Gate | Tool | Threshold |
|------|------|-----------|
| Lint | ruff check | 0 errors |
| Format | ruff format --check | 0 diffs |
| Type check | mypy | 0 errors (on checked files) |
| Tests | pytest | All pass |
| Coverage | pytest-cov | >= 75% overall |

---

## 11. Deviation Documentation

When a project deviates from ANY constraint in this blueprint, a Deviation Record MUST be created.

### When Required

- Disabling a ruff rule not in "Accepted Suppressions"
- Using an ORM instead of raw SQL
- Skipping a mandatory pattern (e.g., no Pydantic models, no rate limiting)
- Adding heavy dependencies not in the blueprint stack
- Changing the architecture structure

### Process

1. Create `docs/deviations/DEV-NNN-[slug].md` using `templates/deviation-record.md`
2. Reference the deviation in the PR description
3. The deviation is reviewed as part of PR code review
4. Approved deviations are binding

---

## 12. Report Artifacts

After test/verify phase, these artifacts must exist:

| Artifact | Location | Format |
|----------|----------|--------|
| Test results | `test-results.xml` | JUnit XML |
| Coverage report | `htmlcov/` | HTML (pytest-cov) |
| Coverage summary | `coverage.xml` | Cobertura XML |

---

*Blueprint: Python FastAPI — Capiva OS Development Harness*
*Stack: Python 3.13 + FastAPI + PostgreSQL + Azure DevOps*
*Based on: SSB production backends with quality improvements (ruff, mypy, pytest-cov)*
