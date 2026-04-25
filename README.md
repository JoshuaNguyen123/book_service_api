# Book API

A production-ready REST API for managing books, built with FastAPI and SQLAlchemy.

**v1** provides a stable CRUD contract with search, filtering, and pagination.  
**v2** adds frontier capabilities: Ollama AI enrichment, web crawling, ISBN lookup, web search (Open Library + Google Books), and bulk operations.

---

## API Versions at a Glance

| Capability | v1 | v2 |
|------------|----|----|
| Full CRUD (create / read / update / delete) | ✓ | ✓ |
| Pagination (`limit` / `offset`) | ✓ | ✓ + `has_more` / `next_offset` |
| Filter by author, tag, year | ✓ | ✓ + `year_min` / `year_max` range |
| Sort control | — | `sort` + `sort_dir` |
| Full-text search (title, authors, tags) | ✓ | ✓ + description |
| AI book enrichment (Ollama) | — | ✓ |
| Web search (Open Library + Google Books) | — | ✓ |
| ISBN lookup (Open Library) | — | ✓ |
| Import from ISBN or URL | — | ✓ |
| Bulk create / delete | — | ✓ |
| `X-Total-Count` header on lists | — | ✓ |
| Richer health (Ollama status, uptime) | — | ✓ |

---

## v2 Highlights

### AI Enrichment via Ollama
`POST /v2/books/{id}/enrich` calls the configured Ollama model and returns a structured JSON response with an AI-written summary, suggested tags, and themes. Works with any model available on your Ollama instance (default: `llama3`). Degrades gracefully to a 503 if Ollama is unreachable.

### Web Search
`GET /v2/books/search-web?q=dune` queries Open Library (free, no key required) and optionally Google Books (set `GOOGLE_BOOKS_API_KEY`). Results are normalized to a common schema and deduplicated by ISBN.

### ISBN Lookup
`GET /v2/books/lookup/{isbn}` resolves an ISBN-10 or ISBN-13 to structured metadata via Open Library — without touching your database.

### Import from Web
`POST /v2/books/import` fetches metadata by ISBN or by scraping a URL (using Open Graph, schema.org, and meta tags), then optionally saves it to the database. Set `save: false` for a dry-run preview.

### Bulk Operations
`POST /v2/books/bulk` creates up to 50 books in a single request. Each item is processed independently; failures are reported per-item without blocking successes. `DELETE /v2/books/bulk` deletes by a list of IDs.

---

## Technical Features

- **Production middleware** — request logging (`method path status duration_ms`) and security headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`) on every response
- **Structured configuration** — all settings via env vars / `.env` with Pydantic Settings
- **Consistent error contract** — `{"error":{"code":"...","message":"...","details":{...}}}`
- **Input validation** — Pydantic models with whitespace normalization, year bounds, ISBN uniqueness
- **Alembic migrations** — schema evolution without data loss (`alembic upgrade head`)
- **GitHub Actions CI** — lint + test on every push
- **Makefile** — common dev tasks at your fingertips
- **Docker support** — single `docker compose up --build` to run

---

## Architecture

```
app/
  main.py              # App factory, middleware, exception handlers
  core/config.py       # Pydantic Settings (env vars + .env file)
  api/
    v1/                # Stable CRUD API
      books.py         # CRUD, search, filtering, pagination
      health.py        # Basic health check
    v2/                # Frontier API
      books.py         # All v1 + AI enrich, web search, import, bulk
      health.py        # Extended health (Ollama status, uptime)
  models/book.py       # SQLAlchemy ORM model
  db/session.py        # Engine, session factory, init_db()
  services/
    ollama_client.py   # Ollama AI enrichment wrapper
    web_search.py      # Open Library + Google Books search
    web_crawler.py     # ISBN lookup + URL scraping
alembic/               # Database migrations
scripts/seed_books.py  # Sample data seeding
tests/                 # pytest suite (v1 + v2)
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- (Optional) [Ollama](https://ollama.com) for AI features

### 1. Install dependencies

```bash
# macOS / Linux
python -m venv .venv && source .venv/bin/activate
make install

# Windows PowerShell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Configure (optional)

```bash
cp .env.example .env
# Edit .env — all settings have sensible defaults
```

### 3. Run

```bash
make run
# Server starts at http://localhost:8000
# Docs at    http://localhost:8000/docs
```

### 4. Seed sample data (optional)

```bash
make seed
```

---

## Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. SQLite data is persisted in `./data/`.

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies (core + dev) |
| `make test` | Run pytest with coverage |
| `make lint` | Run ruff linter |
| `make format` | Auto-format code with ruff |
| `make run` | Start dev server with hot reload |
| `make docker-build` | Build Docker image |
| `make docker-run` | Start via docker compose |
| `make seed` | Seed 40+ sample books |
| `make migrate` | Run `alembic upgrade head` |

---

## Configuration

All settings are read from environment variables or a `.env` file (see `.env.example`).

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy database URL |
| `CORS_ORIGINS` | *(disabled)* | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama instance URL (local or cloud) |
| `OLLAMA_MODEL` | `llama3` | Model for AI enrichment |
| `GOOGLE_BOOKS_API_KEY` | *(none)* | Optional — higher quota for Google Books |

---

## Ollama Setup

1. Install Ollama: https://ollama.com/download  
   Or point `OLLAMA_BASE_URL` at an Ollama Cloud instance.

2. Pull a model:
   ```bash
   ollama pull llama3
   ```

3. Set env vars (or add to `.env`):
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3
   ```

The `/v2/books/{id}/enrich` endpoint will return a 503 (with a clear message) if Ollama is unreachable — all other endpoints continue to work normally.

---

## Logging & Observability

Every request is logged to stdout in this format:

```
2024-01-15T12:34:56 INFO app.main GET /v1/books 200 14ms
```

Control verbosity with `LOG_LEVEL=DEBUG` (logs SQL queries via SQLAlchemy echo) or `LOG_LEVEL=WARNING` to reduce noise in production.

---

## Database Migrations

The app uses [Alembic](https://alembic.sqlalchemy.org/) for schema evolution.

```bash
# Apply all pending migrations
make migrate                          # or: alembic upgrade head

# Create a new migration after changing a model
alembic revision --autogenerate -m "add cover_url to books"

# Roll back one step
alembic downgrade -1
```

On first run the app also calls `create_all()` for compatibility, so Alembic is strictly additive.

---

## CI

GitHub Actions runs on every push and pull request:

1. **Lint** — `ruff check .`
2. **Test** — `pytest --cov=app --cov-report=term-missing`

See `.github/workflows/ci.yml`.

---

## API Reference

### v1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/health` | Health check |
| `POST` | `/v1/books` | Create a book |
| `GET` | `/v1/books` | List books (paginated + filtered) |
| `GET` | `/v1/books/search` | Full-text search |
| `GET` | `/v1/books/{id}` | Get book by ID |
| `PATCH` | `/v1/books/{id}` | Partial update |
| `DELETE` | `/v1/books/{id}` | Delete book |

### v2 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v2/health` | Extended health (Ollama + uptime) |
| `POST` | `/v2/books` | Create a book |
| `GET` | `/v2/books` | List books (advanced filters + sort) |
| `GET` | `/v2/books/search` | Search (includes description field) |
| `GET` | `/v2/books/search-web` | Search Open Library + Google Books |
| `GET` | `/v2/books/lookup/{isbn}` | ISBN metadata lookup |
| `POST` | `/v2/books/import` | Import from ISBN or URL |
| `POST` | `/v2/books/bulk` | Bulk create (up to 50) |
| `DELETE` | `/v2/books/bulk` | Bulk delete by IDs |
| `POST` | `/v2/books/{id}/enrich` | AI enrich via Ollama |
| `GET` | `/v2/books/{id}` | Get book by ID |
| `PATCH` | `/v2/books/{id}` | Partial update |
| `DELETE` | `/v2/books/{id}` | Delete book |

### Error Contract

All errors use a consistent shape:

```json
{
  "error": {
    "code": "not_found | conflict | validation_error | service_unavailable | internal_error",
    "message": "Human-readable description",
    "details": {}
  }
}
```

### Example: Create a book

```bash
curl -X POST http://localhost:8000/v1/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Dune",
    "authors": ["Frank Herbert"],
    "isbn": "978-0-441-17271-9",
    "published_year": 1965,
    "tags": ["sci-fi", "classic"]
  }'
```

### Example: AI enrich a book (v2)

```bash
curl -X POST http://localhost:8000/v2/books/{book_id}/enrich
```

### Example: Search books on the web (v2)

```bash
curl "http://localhost:8000/v2/books/search-web?q=foundation+asimov"
```

### Example: Import by ISBN (v2)

```bash
curl -X POST http://localhost:8000/v2/books/import \
  -H "Content-Type: application/json" \
  -d '{"isbn": "9780441172719"}'
```

---

## Testing

```bash
make test
```

The test suite uses an in-memory SQLite database — no side effects on `./data/app.db`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (default) / any SQLAlchemy-compatible DB |
| Migrations | Alembic |
| AI | Ollama (local or cloud) |
| Web crawling | httpx + BeautifulSoup4 |
| Web search | Open Library API, Google Books API |
| Server | Uvicorn |
| Tests | pytest + httpx |
| Linting | ruff |
| CI | GitHub Actions |
| Container | Docker + docker compose |
