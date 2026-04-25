"""Web crawling service: ISBN lookup and URL scraping for book metadata.

Uses Open Library's REST API for ISBN lookups.
Uses httpx + BeautifulSoup for arbitrary URL scraping (Open Graph, schema.org, meta tags).
"""
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "BookServiceAPI/1.0 (https://github.com/joshuanguyen123/book_service_api)"}
_TIMEOUT = 10.0


def fetch_by_isbn(isbn: str) -> dict | None:
    """Look up book metadata from Open Library by ISBN. Returns None if not found."""
    clean_isbn = isbn.replace("-", "").replace(" ", "")
    url = f"https://openlibrary.org/isbn/{clean_isbn}.json"
    try:
        with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

        title = data.get("title", "")
        published_year = _extract_year(data.get("publish_date", ""))
        description = _extract_description(data.get("description"))

        # Resolve authors from /authors/{key}.json
        author_keys = [a.get("key") for a in (data.get("authors") or []) if a.get("key")]
        authors = _resolve_author_names(author_keys)

        # Resolve subjects / tags from works
        works = data.get("works") or []
        tags: list[str] = []
        if works:
            work_key = works[0].get("key")
            if work_key:
                tags = _fetch_work_subjects(work_key)

        return {
            "title": title,
            "authors": authors,
            "isbn": clean_isbn,
            "published_year": published_year,
            "description": description,
            "tags": tags[:10],
            "source": "open_library",
            "source_url": f"https://openlibrary.org/isbn/{clean_isbn}",
        }
    except httpx.HTTPError as exc:
        logger.warning("ISBN lookup failed for %s: %s", isbn, exc)
        return None


def scrape_book_url(url: str) -> dict:
    """Scrape a web page for book metadata using Open Graph, schema.org, and meta tags.

    Returns a partial dict — callers should treat all fields as optional.
    """
    try:
        with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
    except httpx.HTTPError as exc:
        logger.warning("URL scrape failed for %s: %s", url, exc)
        raise

    result: dict = {"source": "web_scrape", "source_url": url}

    # Open Graph
    og = {
        tag.get("property", ""): tag.get("content", "")
        for tag in soup.find_all("meta", property=True)
    }
    if og.get("og:title"):
        result["title"] = og["og:title"]
    if og.get("og:description"):
        result["description"] = og["og:description"]

    # schema.org Book JSON-LD
    import json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = next((d for d in data if d.get("@type") == "Book"), {})
            if data.get("@type") == "Book":
                result.setdefault("title", data.get("name", ""))
                if data.get("author"):
                    raw = data["author"]
                    if isinstance(raw, list):
                        result["authors"] = [a.get("name", a) if isinstance(a, dict) else a for a in raw]
                    elif isinstance(raw, dict):
                        result["authors"] = [raw.get("name", "")]
                if data.get("isbn"):
                    result["isbn"] = data["isbn"]
                if data.get("datePublished"):
                    result["published_year"] = _extract_year(data["datePublished"])
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    # Fallback: <title> tag
    if not result.get("title") and soup.title:
        result["title"] = soup.title.string or ""

    # Fallback: meta description
    if not result.get("description"):
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["description"] = meta_desc["content"]

    return result


# --- helpers ---

def _extract_year(date_str: str) -> int | None:
    if not date_str:
        return None
    for part in str(date_str).split():
        if len(part) == 4 and part.isdigit():
            return int(part)
    if len(str(date_str)) >= 4 and str(date_str)[:4].isdigit():
        return int(str(date_str)[:4])
    return None


def _extract_description(raw) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("value")
    return None


def _resolve_author_names(keys: list[str]) -> list[str]:
    names: list[str] = []
    for key in keys[:5]:
        try:
            with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = client.get(f"https://openlibrary.org{key}.json")
                if resp.status_code == 200:
                    names.append(resp.json().get("name", ""))
        except httpx.HTTPError:
            pass
    return [n for n in names if n]


def _fetch_work_subjects(work_key: str) -> list[str]:
    try:
        with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(f"https://openlibrary.org{work_key}.json")
            if resp.status_code == 200:
                subjects = resp.json().get("subjects") or []
                return [s for s in subjects if isinstance(s, str)][:10]
    except httpx.HTTPError:
        pass
    return []
