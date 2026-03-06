"""Books CRUD, list with pagination/filters."""
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.book import Book

router = APIRouter()

# --- Pydantic schemas ---

YEAR_MIN = 1000
YEAR_MAX = 2100


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    authors: list[str] = Field(default_factory=list)
    isbn: str | None = None
    published_year: int | None = Field(None, ge=YEAR_MIN, le=YEAR_MAX)
    tags: list[str] = Field(default_factory=list)
    description: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title must not be blank")
        return title

    @field_validator("isbn", "description", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("authors", "tags", mode="before")
    @classmethod
    def normalize_string_lists(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    normalized.append(stripped)
            else:
                normalized.append(item)
        return normalized


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)
    authors: list[str] | None = None
    isbn: str | None = None
    published_year: int | None = Field(None, ge=YEAR_MIN, le=YEAR_MAX)
    tags: list[str] | None = None
    description: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def validate_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        title = value.strip()
        if not title:
            raise ValueError("Title must not be blank")
        return title

    @field_validator("isbn", "description", mode="before")
    @classmethod
    def normalize_optional_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("authors", "tags", mode="before")
    @classmethod
    def normalize_optional_string_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    normalized.append(stripped)
            else:
                normalized.append(item)
        return normalized


class BookResponse(BaseModel):
    id: str
    title: str
    authors: list[str]
    isbn: str | None
    published_year: int | None
    tags: list[str]
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_book(cls, book: Book) -> "BookResponse":
        return cls(
            id=book.id,
            title=book.title,
            authors=book.get_authors_list(),
            isbn=book.isbn,
            published_year=book.published_year,
            tags=book.get_tags_list(),
            description=book.description,
            created_at=book.created_at,
            updated_at=book.updated_at,
        )


class BookListResponse(BaseModel):
    items: list[BookResponse]
    total: int
    limit: int
    offset: int


def _book_to_response(book: Book) -> BookResponse:
    return BookResponse.from_orm_book(book)


def _apply_filters(query, author: str | None, tag: str | None, year: int | None):
    """Apply optional filters; ignore empty strings."""
    if author and author.strip():
        query = query.filter(Book.authors.contains(f'"{author.strip()}"'))
    if tag and tag.strip():
        query = query.filter(Book.tags.contains(f'"{tag.strip()}"'))
    if year is not None:
        query = query.filter(Book.published_year == year)
    return query


def _json_dump(obj: list) -> str:
    return json.dumps(obj) if obj is not None else "[]"


def _raise_isbn_conflict() -> None:
    raise HTTPException(
        status_code=409,
        detail={"code": "conflict", "message": "ISBN already exists", "details": {"field": "isbn"}},
    )


def _commit_or_raise_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "isbn" in str(exc).lower():
            _raise_isbn_conflict()
        raise


@router.post("", response_model=BookResponse, status_code=201)
def create_book(body: BookCreate, db: Session = Depends(get_db)):
    if body.isbn:
        existing = db.query(Book).filter(Book.isbn == body.isbn).first()
        if existing:
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


@router.get("", response_model=BookListResponse)
def list_books(
    db: Session = Depends(get_db),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    author: str | None = None,
    tag: str | None = None,
    year: int | None = Query(None, ge=YEAR_MIN, le=YEAR_MAX),
):
    query = db.query(Book)
    query = _apply_filters(query, author, tag, year)
    total = query.count()
    items = query.order_by(Book.created_at.desc()).offset(offset).limit(limit).all()
    return BookListResponse(
        items=[_book_to_response(b) for b in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=BookListResponse)
def search_books(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    author: str | None = None,
    tag: str | None = None,
    year: int | None = Query(None, ge=YEAR_MIN, le=YEAR_MAX),
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
        )
    )
    query = _apply_filters(query, author, tag, year)
    total = query.count()
    items = query.order_by(Book.created_at.desc()).offset(offset).limit(limit).all()
    return BookListResponse(
        items=[_book_to_response(b) for b in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: UUID, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == str(book_id)).first()
    if not book:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Book not found", "details": {"id": str(book_id)}})
    return _book_to_response(book)


@router.patch("/{book_id}", response_model=BookResponse)
def update_book(book_id: UUID, body: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == str(book_id)).first()
    if not book:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Book not found", "details": {"id": str(book_id)}})
    if body.isbn is not None and body.isbn != book.isbn:
        existing = db.query(Book).filter(Book.isbn == body.isbn).first()
        if existing:
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


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: UUID, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == str(book_id)).first()
    if not book:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Book not found", "details": {"id": str(book_id)}})
    db.delete(book)
    db.commit()
    return None

