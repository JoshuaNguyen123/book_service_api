# Book API

`Book API` is a backend portfolio project built to demonstrate clean REST API design in Python. It provides CRUD operations for books, supports filtering and search, uses a lightweight SQLite database for zero-cost local development, and includes Docker support for portable demos and deployment.

The project is intentionally simple in product scope and strong in backend fundamentals: request validation, structured error responses, environment-based configuration, database persistence, automated tests, and clear developer documentation.

## What This Project Demonstrates

- REST API design with versioned endpoints under `/v1`
- FastAPI application structure with routers, schemas, and dependency injection
- SQLAlchemy ORM integration with SQLite for a lightweight persistence layer
- Pydantic validation for request bodies and query parameters
- Standardized JSON error responses for validation, conflict, and not-found cases
- Search, pagination, and filter patterns commonly used in production APIs
- Dockerized local execution for consistent environments
- Automated tests using `pytest` and FastAPI's test client

## Technical Features

- **Books CRUD**
  Create, read, update, and delete book records.
- **Search**
  Search across `title`, `authors`, and `tags`.
- **Pagination**
  `limit` and `offset` are supported on list and search endpoints.
- **Filtering**
  Filter by `author`, `tag`, and `year`.
- **Validation**
  Required titles, bounded `published_year`, and typed request/response models.
- **Unique constraints**
  `isbn` must be unique when provided.
- **Consistent error contract**
  Errors return:
  `{"error":{"code":"...","message":"...","details":{...}}}`
- **Configurable CORS**
  Disabled by default, enabled with `CORS_ORIGINS`.
- **Portable storage**
  Defaults to `sqlite:///./data/app.db` and auto-creates the data directory on startup.
- **Docker support**
  The API can be launched with `docker compose up --build`.

## Architecture Overview

The codebase follows a small but clean separation of concerns:

- `app/main.py`
  Creates the FastAPI app, registers routers, initializes the database on startup, and centralizes exception handling.
- `app/api/v1/`
  Contains versioned HTTP routes.
- `app/models/`
  Contains SQLAlchemy models.
- `app/db/`
  Contains the declarative base, engine creation, sessions, and database initialization.
- `app/core/`
  Contains application settings loaded from environment variables or `.env`.
- `tests/`
  Contains endpoint-level tests that validate API behavior and error handling.
- `scripts/`
  Contains utility scripts such as database seeding.

## API Design

### Resource Model

Each book includes:

- `id`
- `title`
- `authors`
- `isbn`
- `published_year`
- `tags`
- `description`
- `created_at`
- `updated_at`

The API stores `authors` and `tags` as JSON-encoded lists in SQLite while exposing them as `list[str]` in the external API. This keeps the public contract clean while keeping the local storage model lightweight.

### Endpoints

Base path: `/v1`

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/books` | Create a book |
| `GET` | `/books` | List books with pagination and filters |
| `GET` | `/books/{book_id}` | Retrieve one book |
| `PATCH` | `/books/{book_id}` | Partially update a book |
| `DELETE` | `/books/{book_id}` | Delete a book |
| `GET` | `/books/search?q=...` | Search books |

### Query Parameters

- `limit`
  Default `25`, max `100`
- `offset`
  Default `0`
- `author`
  Optional author filter
- `tag`
  Optional tag filter
- `year`
  Optional published year filter

## Error Handling

The API uses a consistent JSON error shape to make client integration easier:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": {
      "errors": []
    }
  }
}
```

Current handled cases include:

- `404 not_found`
- `409 conflict`
- `422 validation_error`
- `500 internal_error`

## Quality and Production-Readiness

This project is designed to be small in scope but disciplined in implementation.

- Input validation is enforced through Pydantic models.
- The application returns standardized error payloads instead of raw framework exceptions.
- The database schema is created automatically on startup for easier demos and onboarding.
- Configuration is environment-driven through `pydantic-settings`.
- Docker support allows a reproducible local runtime.
- Tests run against an in-memory SQLite database, so they are isolated from the local data file.

### Current Production Considerations

This project is deployable, but it is intentionally lightweight.

- SQLite is excellent for local demos, small deployments, and single-node use cases.
- For heavier production workloads, a server database such as PostgreSQL would be a better next step.
- No authentication or authorization is included in this version.
- Table creation is automatic on startup rather than managed by migrations.

Those trade-offs keep the project focused, practical, and easy to evaluate.

## Project Structure

```text
book-api/
  app/
    api/
      v1/
        __init__.py
        books.py
        health.py
    core/
      config.py
    db/
      base.py
      session.py
    models/
      book.py
    main.py
  scripts/
    seed_books.py
  tests/
    conftest.py
    test_books_crud.py
    test_books_query.py
    test_health.py
  Dockerfile
  docker-compose.yml
  pyproject.toml
  README.md
```

## Prerequisites

- `Python 3.11+`
- `pip`
- `Docker` and `Docker Compose` for the containerized workflow

Install Python:

- **Windows:** use [python.org](https://www.python.org/downloads/) or `winget install Python.Python.3.11`
- **macOS:** use `brew install python@3.11` or the official installer
- **Linux:** install from your package manager, for example `sudo apt install python3.11 python3.11-venv`

Verify your installation:

```powershell
python --version
pip --version
```

```bash
python3 --version
pip3 --version
```

## Quick Start

### Windows (PowerShell)

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# If PowerShell blocks activation, run this once:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### macOS / Linux

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Local URLs:

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

The SQLite database is created at `data/app.db`.

## Seed Sample Data

The project includes a seed script for populating the database with sample books.

**Windows**

```powershell
python scripts\seed_books.py
```

**macOS / Linux**

```bash
python scripts/seed_books.py
```

If the database already contains records, the script skips reseeding.

## Run With Docker

This project can also be run in a containerized environment:

```bash
docker compose up --build
```

The API will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000), and the SQLite data file is persisted through the `./data` volume mount.

To seed sample data inside the container:

```bash
docker compose exec api python scripts/seed_books.py
```

## Configuration

Configuration is loaded from environment variables or a local `.env` file.

Copy the example file:

**Windows**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Supported settings:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Database connection string | `sqlite:///./data/app.db` |
| `CORS_ORIGINS` | Comma-separated allowed origins | disabled |

Example:

```env
DATABASE_URL=sqlite:///./data/app.db
# CORS_ORIGINS=http://localhost:3000,https://example.com
```

## API Usage Examples

### Health Check

```bash
curl http://127.0.0.1:8000/v1/health
```

PowerShell:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/health
```

### Create a Book

```bash
curl -X POST http://127.0.0.1:8000/v1/books \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Clean Architecture\",\"authors\":[\"Robert C. Martin\"],\"tags\":[\"software\",\"architecture\"],\"published_year\":2017}"
```

### List Books

```bash
curl "http://127.0.0.1:8000/v1/books?limit=10&offset=0"
```

### Filter Books

```bash
curl "http://127.0.0.1:8000/v1/books?author=Robert%20C.%20Martin&tag=software&year=2017"
```

### Search Books

```bash
curl "http://127.0.0.1:8000/v1/books/search?q=architecture"
```

### Update a Book

```bash
curl -X PATCH http://127.0.0.1:8000/v1/books/{book_id} \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Clean Architecture, Updated Edition\"}"
```

### Delete a Book

```bash
curl -X DELETE http://127.0.0.1:8000/v1/books/{book_id}
```

## Testing

Run the test suite from the project root:

**Windows**

```powershell
pytest tests\ -v
```

**macOS / Linux**

```bash
pytest tests/ -v
```

Optional coverage tooling:

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=app --cov-report=term-missing
```

The tests cover:

- health endpoint behavior
- CRUD operations
- pagination
- filtering
- search
- unique ISBN conflict handling
- validation error formatting

## Deployment Notes

For production-style deployment:

- run without `--reload`
- bind to `0.0.0.0` when exposing the service externally
- place the app behind a reverse proxy such as Nginx or Caddy
- set configuration with environment variables
- use `/v1/health` as a health check endpoint

Example:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If the project evolves beyond SQLite's comfort zone, replacing SQLite with PostgreSQL and adding migrations with Alembic would be the natural next production upgrade.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Uvicorn
- Pytest
- HTTPX
- Docker
