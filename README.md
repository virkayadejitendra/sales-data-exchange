# Sales Data Exchange

A production-style FastAPI learning project for sharing authorized FMCG retail sell-out data with manufacturers.

The functional and delivery requirements are in [docs/requirements.md](docs/requirements.md).

## Implemented features

- FastAPI application factory and versioned API router.
- Environment-based typed settings.
- Async SQLAlchemy session management.
- PostgreSQL through Docker Compose.
- Alembic migrations for organizations and the Day 2 catalog.
- Liveness and database-readiness endpoints.
- Product, outlet, and retailer SKU mapping CRUD APIs.
- Decimal, organization ownership, GTIN, SKU, and outlet-code validation.
- Filtered catalog lists, partial updates, and soft deletes.
- Automated health and catalog endpoint tests.

The guided catalog walkthrough and example payloads are in
[docs/day-2-catalog.md](docs/day-2-catalog.md).

Import [postman/Sales-Data-Exchange.postman_collection.json](postman/Sales-Data-Exchange.postman_collection.json)
into Postman to run the complete Day 2 API flow with automatic ID capture and assertions.

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

