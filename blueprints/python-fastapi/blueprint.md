# Blueprint: Python FastAPI (Python 3.13 + FastAPI + Layered Architecture)

> Stack reference for Capiva OS harness. See `reference.md` for the full blueprint.

## Stack Summary

- **Runtime**: CPython 3.13
- **Language**: Python 3.13 (full type hints, mypy strict)
- **Framework**: FastAPI (async)
- **Architecture**: Layered (api → services → repositories → db)
- **Database**: PostgreSQL (psycopg v3 async, raw SQL — no ORM) + Redis (redis-py async)
- **Testing**: pytest + pytest-asyncio + httpx + Testcontainers
- **Linting**: ruff + mypy (strict mode)
- **Validation**: Pydantic v2
- **CI/CD**: GitHub Actions (default) or Azure Pipelines (enterprise)
