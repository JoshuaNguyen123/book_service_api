"""Web search service: Open Library (free) and Google Books (optional API key).

Both backends return a list of WebBookResult-compatible dicts with a common schema.
"""
import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "BookServiceAPI/1.0 (https://github.com/joshuanguyen123/book_service_api)"}
_TIMEOUT = 10.0


def _normalize_open_library(doc: dict) -> dict:
    authors = doc.get("author_name") or []
    isbn_list = doc.get("isbn") or []
    return {
        "title": doc.get("title", ""),
        "authors": authors[:5],
        "isbn": isbn_list[0] if isbn_list else None,
        "published_year": doc.get("first_publish_year"),
        "description": None,
        "tags": (doc.get("subject") or [])[:10],
        "source": "open_library",
        "source_url": f"https://openlibrary.org{doc['key']}" if doc.get("key") else None,
        "cover_url": (
            f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-M.jpg"
            if doc.get("cover_i")
            else None
        ),
    }


def _normalize_google_books(item: dict) -> dict:
    info = item.get("volumeInfo", {})
    identifiers = {i["type"]: i["identifier"] for i in info.get("industryIdentifiers", [])}
    isbn = identifiers.get("ISBN_13") or identifiers.get("ISBN_10")
    published = info.get("publishedDate", "")
    year = int(published[:4]) if published and len(published) >= 4 and published[:4].isdigit() else None
    image_links = info.get("imageLinks", {})
    return {
        "title": info.get("title", ""),
        "authors": info.get("authors") or [],
        "isbn": isbn,
        "published_year": year,
        "description": info.get("description"),
        "tags": info.get("categories") or [],
        "source": "google_books",
        "source_url": info.get("infoLink"),
        "cover_url": image_links.get("thumbnail"),
    }


def search_open_library(q: str, limit: int = 10) -> list[dict]:
    """Search Open Library for books matching q. No API key required."""
    url = "https://openlibrary.org/search.json"
    try:
        with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            _fields = "key,title,author_name,first_publish_year,isbn,subject,cover_i"
            resp = client.get(url, params={"q": q, "limit": limit, "fields": _fields})
            resp.raise_for_status()
            docs = resp.json().get("docs", [])
            return [_normalize_open_library(d) for d in docs[:limit]]
    except httpx.HTTPError as exc:
        logger.warning("Open Library search failed: %s", exc)
        return []


def search_google_books(q: str, limit: int = 10) -> list[dict]:
    """Search Google Books API. Requires GOOGLE_BOOKS_API_KEY env var for higher quotas."""
    api_key = Settings().google_books_api_key
    url = "https://www.googleapis.com/books/v1/volumes"
    params: dict = {"q": q, "maxResults": min(limit, 40)}
    if api_key:
        params["key"] = api_key
    try:
        with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            items = resp.json().get("items") or []
            return [_normalize_google_books(i) for i in items[:limit]]
    except httpx.HTTPError as exc:
        logger.warning("Google Books search failed: %s", exc)
        return []


def search_books_web(q: str, limit: int = 10, sources: list[str] | None = None) -> list[dict]:
    """Search across enabled sources and merge results (deduped by ISBN)."""
    enabled = set(sources or ["open_library", "google_books"])
    results: list[dict] = []

    if "open_library" in enabled:
        results.extend(search_open_library(q, limit))
    if "google_books" in enabled:
        results.extend(search_google_books(q, limit))

    # Deduplicate by ISBN, preserving order
    seen_isbns: set[str] = set()
    deduped: list[dict] = []
    for r in results:
        isbn = r.get("isbn")
        if isbn and isbn in seen_isbns:
            continue
        if isbn:
            seen_isbns.add(isbn)
        deduped.append(r)

    return deduped[:limit]
