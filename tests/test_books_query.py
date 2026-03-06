"""Books list pagination, filters, and search tests."""
import pytest
from fastapi.testclient import TestClient


def _create_books(client: TestClient, count: int, **kwargs):
    for i in range(count):
        client.post(
            "/v1/books",
            json={
                "title": kwargs.get("title", f"Book {i}"),
                "authors": kwargs.get("authors", ["Author A"] if i % 2 == 0 else ["Author B"]),
                "tags": kwargs.get("tags", ["tag1"] if i % 2 == 0 else ["tag2"]),
                "published_year": kwargs.get("published_year", 2000 + (i % 5)),
            },
        )


def test_list_books_pagination(client: TestClient):
    _create_books(client, 5)
    r = client.get("/v1/books?limit=2&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 0

    r2 = client.get("/v1/books?limit=2&offset=2")
    assert len(r2.json()["items"]) == 2


def test_list_books_default_pagination(client: TestClient):
    r = client.get("/v1/books")
    assert r.status_code == 200
    assert r.json()["limit"] == 25
    assert r.json()["offset"] == 0


def test_filter_by_author(client: TestClient):
    client.post("/v1/books", json={"title": "By Alice", "authors": ["Alice"], "tags": []})
    client.post("/v1/books", json={"title": "By Bob", "authors": ["Bob"], "tags": []})
    r = client.get("/v1/books?author=Alice")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["authors"] == ["Alice"]


def test_filter_by_tag(client: TestClient):
    client.post("/v1/books", json={"title": "T1", "authors": [], "tags": ["sci-fi"]})
    client.post("/v1/books", json={"title": "T2", "authors": [], "tags": ["romance"]})
    r = client.get("/v1/books?tag=sci-fi")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert "sci-fi" in r.json()["items"][0]["tags"]


def test_filter_by_year(client: TestClient):
    client.post("/v1/books", json={"title": "Y1", "authors": [], "published_year": 1999})
    client.post("/v1/books", json={"title": "Y2", "authors": [], "published_year": 2001})
    r = client.get("/v1/books?year=1999")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["published_year"] == 1999


def test_search_by_title(client: TestClient):
    client.post("/v1/books", json={"title": "UniqueTitleXYZ", "authors": [], "tags": []})
    r = client.get("/v1/books/search?q=UniqueTitleXYZ")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert any("UniqueTitleXYZ" in item["title"] for item in r.json()["items"])


def test_search_by_author(client: TestClient):
    client.post("/v1/books", json={"title": "T", "authors": ["RareAuthorName"], "tags": []})
    r = client.get("/v1/books/search?q=RareAuthorName")
    assert r.status_code == 200
    assert any("RareAuthorName" in item["authors"] for item in r.json()["items"])


def test_search_with_pagination(client: TestClient):
    client.post("/v1/books", json={"title": "Searchable", "authors": [], "tags": []})
    r = client.get("/v1/books/search?q=Searchable&limit=5&offset=0")
    assert r.status_code == 200
    assert "items" in r.json()
    assert r.json()["limit"] == 5
    assert r.json()["offset"] == 0


def test_search_rejects_blank_query(client: TestClient):
    r = client.get("/v1/books/search?q=   ")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
