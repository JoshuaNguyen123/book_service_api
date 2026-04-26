"""v2 Books API — full CRUD plus AI enrichment, web search, ISBN lookup, and bulk ops."""
import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx
import ollama
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.books import (
    YEAR_MAX,
    YEAR_MIN,
    BookCreate,
    BookResponse,
    BookUpdate,
    _apply_filters,
    _book_to_response,
    _commit_or_raise_conflict,
    _json_dump,
    _raise_isbn_conflict,
)
from app.db.session import get_db
from app.models.book import Book
from app.services import ollama_client, web_crawler, web_search

logger = logging.getLogger(__name__)

router = APIRouter(tags=["books-v2"])

# --- v2-only schemas ---


class WebBookResult(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    isbn: str | None = None
    published_year: int | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str
    source_url: str | None = None
    cover_url: str | None = None


class EnrichResponse(BaseModel):
    book_id: str
    ai_summary: str | None
    suggested_tags: list[str]
    themes: list[str]
    model: str
    generated_at: datetime


class ImportRequest(BaseModel):
    isbn: str | None = None
    url: str | None = None
    save: bool = Field(True, description="False = dry-run; preview metadata without saving")

    @model_validator(mode="after")
    def require_isbn_or_url(self) -> "ImportRequest":
        if not self.isbn and not self.url:
            raise ValueError("Provide at least one of: isbn, url")
        return self


class BulkCreateRequest(BaseModel):
    books: list[BookCreate] = Field(..., min_length=1, max_length=50)


class BulkCreateResponse(BaseModel):
    created: list[BookResponse]
    failed: list[dict]
    total_created: int
    total_failed: int


class BulkDeleteRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=100)


class BulkDeleteResponse(BaseModel):
    deleted: int
    not_found: list[str]


class BookListResponseV2(BaseModel):
    items: list[BookResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None


# --- helpers ---

_SORT_FIELDS = {"title": Book.title, "year": Book.published_year, "created_at": Book.created_at}

_NOT_FOUND_RESPONSES = {
    404: {
        "description": "Book not found",
        "content": {
            "application/json": {
                "example": {"error": {"code": "not_found", "message": "Book not found", "details": {"id": "<uuid>"}}}
            }
        },
    }
}


def _not_found(book_id) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "not_found", "message": "Book not found", "details": {"id": str(book_id)}},
    )


def _apply_sort(query, sort: str, sort_dir: str):
    col = _SORT_FIELDS.get(sort, Book.created_at)
    return query.order_by(col.asc() if sort_dir == "asc" else col.desc())


def _apply_v2_filters(
    query, author: str | None, tag: str | None, year: int | None, year_min: int | None, year_max: int | None
):
    query = _apply_filters(query, author, tag, year)
    if year_min is not None:
        query = query.filter(Book.published_year >= year_min)
    if year_max is not None:
        query = query.filter(Book.published_year <= year_max)
    return query


# --- Routes ---
# IMPORTANT: Literal paths must be registered BEFORE dynamic /{book_id} paths
# so FastAPI doesn't try to cast "bulk", "search", etc. as UUIDs.


@router.post(
    "",
    response_model=BookResponse,
    status_code=201,
    summary="Create a book (v2)",
    description="Create a new book. Identical to v1 POST /books.",
)
def create_book_v2(body: BookCreate, db: Session = Depends(get_db)):
    if body.isbn:
        if db.query(Book).filter(Book.isbn == body.isbn).first():
            _raise_isbn_conflict()
    book = Book(
        title=body.title,
        authors=_json_dump(body.authors),
        isbn=body.isbn,
        published_year=body.published_year,
        tags=_json_dump(body.tags),
        description=body.description,
    )
    db.add(book)
    _commit_or_raise_conflict(db)
    db.refresh(book)
    return _book_to_response(book)


@router.get(
    "",
    response_model=BookListResponseV2,
    summary="List books (v2)",
    description=(
        "Paginated book list with advanced filtering and sorting. "
        "Adds `year_min`/`year_max` range filters and `sort`/`sort_dir` controls. "
        "Response includes `has_more` and `next_offset` for easy cursor-style pagination."
    ),
)
def list_books_v2(
    response: Response,
    db: Session = Depends(get_db),
    limit: int = Query(25, ge=1, le=100, description="Max items (1–100)"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    author: str | None = Query(None, description="Filter by exact author name"),
    tag: str | None = Query(None, description="Filter by exact tag"),
    year: int | None = Query(None, ge=YEAR_MIN, le=YEAR_MAX, description="Filter by exact year"),
    year_min: int | None = Query(None, ge=YEAR_MIN, le=YEAR_MAX, description="Year ≥"),
    year_max: int | None = Query(None, ge=YEAR_MIN, le=YEAR_MAX, description="Year ≤"),
    sort: str = Query("created_at", pattern="^(title|year|created_at)$", description="Sort field"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
):
    query = db.query(Book)
    query = _apply_v2_filters(query, author, tag, year, year_min, year_max)
    total = query.count()
    query = _apply_sort(query, sort, sort_dir)
    items = query.offset(offset).limit(limit).all()
    has_more = (offset + limit) < total
    response.headers["X-Total-Count"] = str(total)
    return BookListResponseV2(
        items=[_book_to_response(b) for b in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
    )


@router.get(
    "/search",
    response_model=BookListResponseV2,
    summary="Search books (v2)",
    description=(
        "Full-text search across **title**, **authors**, **tags**, and **description** "
        "(v1 omits description). Supports all v2 filters and sorting."
    ),
)
def search_books_v2(
    response: Response,
    q: str = Query(..., min_length=1, description="Search query"),
    db: Session = Depends(get_db),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    author: str | None = None,
    tag: str | None = None,
    year: int | None = Query(None, ge=YEAR_MIN, le=YEAR_MAX),
    year_min: int | None = Query(None, ge=YEAR_MIN, le=YEAR_MAX),
    year_max: int | None = Query(None, ge=YEAR_MIN, le=YEAR_MAX),
    sort: str = Query("created_at", pattern="^(title|year|created_at)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
):
    q = q.strip()
    if not q:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "message": "Request validation failed",
                "details": {"field": "q", "message": "Search query must not be blank"},
            },
        )
    pattern = f"%{q}%"
    query = db.query(Book).filter(
        or_(
            Book.title.ilike(pattern),
            Book.authors.ilike(pattern),
            Book.tags.ilike(pattern),
            Book.description.ilike(pattern),
        )
    )
    query = _apply_v2_filters(query, author, tag, year, year_min, year_max)
    total = query.count()
    query = _apply_sort(query, sort, sort_dir)
    items = query.offset(offset).limit(limit).all()
    has_more = (offset + limit) < total
    response.headers["X-Total-Count"] = str(total)
    return BookListResponseV2(
        items=[_book_to_response(b) for b in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
    )


@router.get(
    "/search-web",
    response_model=list[WebBookResult],
    summary="Search books on the web",
    description=(
        "Search for books across **Open Library** (always active, no key) and optionally "
        "**Google Books** (set `GOOGLE_BOOKS_API_KEY` for higher quota). "
        "Results are deduplicated by ISBN."
    ),
)
def search_web(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=40, description="Max results per source"),
    sources: str = Query("open_library,google_books", description="Comma-separated source list"),
):
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    results = web_search.search_books_web(q, limit=limit, sources=source_list)
    return [WebBookResult(**r) for r in results]


@router.get(
    "/lookup/{isbn}",
    response_model=WebBookResult,
    summary="Lookup a book by ISBN",
    description=(
        "Fetch structured book metadata from Open Library by ISBN-10 or ISBN-13. "
        "Does **not** save to the database — use `/v2/books/import` to persist."
    ),
    responses={404: {"description": "ISBN not found on Open Library"}},
)
def lookup_isbn(isbn: str):
    result = web_crawler.fetch_by_isbn(isbn)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "ISBN not found on Open Library", "details": {"isbn": isbn}},
        )
    return WebBookResult(**result)


@router.post(
    "/import",
    response_model=BookResponse | WebBookResult,
    status_code=201,
    summary="Import a book from the web",
    description=(
        "Fetch book metadata from **Open Library** (by ISBN) or by **scraping a URL**, "
        "then optionally save it to the database.\n\n"
        "Set `save: false` for a dry-run preview without persisting."
    ),
    responses={
        400: {"description": "Could not resolve metadata from the provided source"},
        409: {"description": "ISBN already exists in the database"},
    },
)
def import_book(body: ImportRequest, db: Session = Depends(get_db)):
    metadata: dict | None = None

    if body.isbn:
        metadata = web_crawler.fetch_by_isbn(body.isbn)
        if not metadata:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "bad_request",
                    "message": "ISBN not found on Open Library",
                    "details": {"isbn": body.isbn},
                },
            )
    elif body.url:
        try:
            metadata = web_crawler.scrape_book_url(body.url)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "bad_request",
                    "message": "Failed to fetch URL",
                    "details": {"url": body.url, "error": str(exc)},
                },
            )

    if not metadata or not metadata.get("title"):
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "Could not extract title from source", "details": {}},
        )

    if not body.save:
        return WebBookResult(
            **{**metadata, "source": metadata.get("source", "web_scrape"), "source_url": metadata.get("source_url")}
        )

    isbn = metadata.get("isbn")
    if isbn and db.query(Book).filter(Book.isbn == isbn).first():
        _raise_isbn_conflict()

    year = metadata.get("published_year")
    if year and not (YEAR_MIN <= year <= YEAR_MAX):
        year = None

    book = Book(
        title=metadata["title"],
        authors=_json_dump(metadata.get("authors") or []),
        isbn=isbn,
        published_year=year,
        tags=_json_dump(metadata.get("tags") or []),
        description=metadata.get("description"),
    )
    db.add(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _raise_isbn_conflict()
    db.refresh(book)
    return _book_to_response(book)


@router.post(
    "/bulk",
    response_model=BulkCreateResponse,
    status_code=201,
    summary="Bulk create books",
    description=(
        "Create up to 50 books in a single request. "
        "Each book is processed independently — failures do not block other items."
    ),
)
def bulk_create(body: BulkCreateRequest, db: Session = Depends(get_db)):
    created: list[BookResponse] = []
    failed: list[dict] = []

    for i, book_data in enumerate(body.books):
        try:
            if book_data.isbn and db.query(Book).filter(Book.isbn == book_data.isbn).first():
                failed.append({"index": i, "title": book_data.title, "error": "ISBN already exists"})
                continue
            book = Book(
                title=book_data.title,
                authors=_json_dump(book_data.authors),
                isbn=book_data.isbn,
                published_year=book_data.published_year,
                tags=_json_dump(book_data.tags),
                description=book_data.description,
            )
            db.add(book)
            db.flush()
            db.refresh(book)
            created.append(_book_to_response(book))
        except IntegrityError:
            db.rollback()
            failed.append({"index": i, "title": book_data.title, "error": "ISBN conflict (race)"})
        except Exception as exc:
            db.rollback()
            failed.append({"index": i, "title": book_data.title, "error": str(exc)})

    db.commit()
    return BulkCreateResponse(
        created=created,
        failed=failed,
        total_created=len(created),
        total_failed=len(failed),
    )


@router.delete(
    "/bulk",
    response_model=BulkDeleteResponse,
    summary="Bulk delete books",
    description="Delete multiple books by UUID. Returns counts of deleted and not-found IDs.",
)
def bulk_delete(body: BulkDeleteRequest, db: Session = Depends(get_db)):
    deleted = 0
    not_found: list[str] = []
    for raw_id in body.ids:
        book = db.query(Book).filter(Book.id == raw_id).first()
        if book:
            db.delete(book)
            deleted += 1
        else:
            not_found.append(raw_id)
    db.commit()
    return BulkDeleteResponse(deleted=deleted, not_found=not_found)


# --- Dynamic /{book_id} routes (must come after all literal paths above) ---


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    summary="Get a book (v2)",
    responses={**_NOT_FOUND_RESPONSES},
)
def get_book_v2(book_id: UUID, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == str(book_id)).first()
    if not book:
        raise _not_found(book_id)
    return _book_to_response(book)


@router.patch(
    "/{book_id}",
    response_model=BookResponse,
    summary="Update a book (v2)",
    responses={**_NOT_FOUND_RESPONSES},
)
def update_book_v2(book_id: UUID, body: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == str(book_id)).first()
    if not book:
        raise _not_found(book_id)
    if body.isbn is not None and body.isbn != book.isbn:
        if db.query(Book).filter(Book.isbn == body.isbn).first():
            _raise_isbn_conflict()
    data = body.model_dump(exclude_unset=True)
    if "authors" in data and data["authors"] is not None:
        book.authors = _json_dump(data["authors"])
        del data["authors"]
    if "tags" in data and data["tags"] is not None:
        book.tags = _json_dump(data["tags"])
        del data["tags"]
    for k, v in data.items():
        setattr(book, k, v)
    _commit_or_raise_conflict(db)
    db.refresh(book)
    return _book_to_response(book)


@router.delete(
    "/{book_id}", status_code=204, summary="Delete a book (v2)", responses={**_NOT_FOUND_RESPONSES}
)
def delete_book_v2(book_id: UUID, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == str(book_id)).first()
    if not book:
        raise _not_found(book_id)
    db.delete(book)
    db.commit()
    return None


@router.post(
    "/{book_id}/enrich",
    response_model=EnrichResponse,
    summary="AI enrich a book",
    description=(
        "Use the configured Ollama model to generate an AI summary, suggested tags, and themes "
        "for an existing book. Requires a running Ollama instance (local or cloud) configured "
        "via `OLLAMA_BASE_URL` and `OLLAMA_MODEL`."
    ),
    responses={
        503: {"description": "Ollama is unavailable"},
        **_NOT_FOUND_RESPONSES,
    },
)
def enrich_book(book_id: UUID, db: Session = Depends(get_db)):
    from app.core.config import Settings

    book = db.query(Book).filter(Book.id == str(book_id)).first()
    if not book:
        raise _not_found(book_id)
    try:
        result = ollama_client.enrich_book(
            title=book.title,
            authors=book.get_authors_list(),
            description=book.description,
        )
    except (ollama.ResponseError, ConnectionError, Exception) as exc:
        logger.warning("Ollama enrichment failed for book %s: %s", book_id, exc)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "service_unavailable",
                "message": "Ollama is unavailable",
                "details": {"hint": "Check OLLAMA_BASE_URL and that the model is pulled"},
            },
        )
    settings = Settings()
    return EnrichResponse(
        book_id=str(book_id),
        ai_summary=result.get("ai_summary"),
        suggested_tags=result.get("suggested_tags") or [],
        themes=result.get("themes") or [],
        model=settings.ollama_model,
        generated_at=datetime.now(UTC),
    )
