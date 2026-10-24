# Sales Data Exchange

A production-style FastAPI learning project for sharing authorized FMCG retail sell-out data with manufacturers.

The functional and delivery requirements are in [docs/requirements.md](docs/requirements.md).

## Day 1 features

- FastAPI application factory and versioned API router.
- Environment-based typed settings.
- Async SQLAlchemy session management.
- PostgreSQL through Docker Compose.
- Alembic migrations with the initial `organizations` table.
- Liveness and database-readiness endpoints.
- Automated health endpoint tests.

## Prerequisites

- Python 3.14
- `uv`
- Docker Desktop with Linux containers enabled

## Start the database

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
```

## Install dependencies and migrate

```powershell
uv sync
uv run alembic upgrade head
```

## Run the API

```powershell
uv run uvicorn app.main:app --reload
```

Alternatively, start the complete local stack with:

```powershell
.\startApp.bat
```

Run linting and tests before starting the server with:

```powershell
.\startApp.bat --check
```

Open:

- Swagger UI: <http://localhost:8000/docs>
- Liveness: <http://localhost:8000/health/live>
- Readiness: <http://localhost:8000/health/ready>

## Quality checks

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

