"""Tests for v2 books endpoints: advanced list, search, bulk ops, and security headers."""


# --- helpers ---

def _create(client, **kwargs):
    payload = {"title": "Test Book", "authors": ["Author One"], **kwargs}
    r = client.post("/v2/books", json=payload)
    assert r.status_code == 201
    return r.json()


# --- security headers ---


def test_security_headers_present(client):
    r = client.get("/v1/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("x-xss-protection") == "1; mode=block"
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


# --- v1 health richer response ---


def test_v1_health_includes_version(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["database"] == "ok"


# --- v2 CRUD ---


def test_v2_create_book(client):
    book = _create(client, title="Neuromancer", published_year=1984)
    assert book["title"] == "Neuromancer"
    assert book["published_year"] == 1984


def test_v2_get_book(client):
    book = _create(client, title="Foundation")
    r = client.get(f"/v2/books/{book['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Foundation"


def test_v2_patch_book(client):
    book = _create(client, title="Old Title")
    r = client.patch(f"/v2/books/{book['id']}", json={"title": "New Title"})
    assert r.status_code == 200
    assert r.json()["title"] == "New Title"


def test_v2_delete_book(client):
    book = _create(client, title="Delete Me")
    r = client.delete(f"/v2/books/{book['id']}")
    assert r.status_code == 204
    assert client.get(f"/v2/books/{book['id']}").status_code == 404


# --- v2 list: advanced filters ---


def test_v2_list_year_min_max(client):
    _create(client, title="Old Book", published_year=1950)
    _create(client, title="Middle Book", published_year=1975)
    _create(client, title="New Book", published_year=2000)

    r = client.get("/v2/books?year_min=1960&year_max=1990")
    assert r.status_code == 200
    titles = [b["title"] for b in r.json()["items"]]
    assert "Middle Book" in titles
    assert "Old Book" not in titles
    assert "New Book" not in titles


def test_v2_list_sort_by_title_asc(client):
    _create(client, title="Zebra")
    _create(client, title="Alpha")
    _create(client, title="Mango")

    r = client.get("/v2/books?sort=title&sort_dir=asc")
    assert r.status_code == 200
    titles = [b["title"] for b in r.json()["items"]]
    assert titles == sorted(titles)


def test_v2_list_has_more_pagination(client):
    for i in range(5):
        _create(client, title=f"Book {i}")

    r = client.get("/v2/books?limit=2&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["has_more"] is True
    assert body["next_offset"] == 2


def test_v2_list_no_more_on_last_page(client):
    for i in range(3):
        _create(client, title=f"Book {i}")

    r = client.get("/v2/books?limit=10&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["has_more"] is False
    assert body["next_offset"] is None


def test_v2_list_x_total_count_header(client):
    _create(client, title="A")
    _create(client, title="B")

    r = client.get("/v2/books")
    assert r.status_code == 200
    assert r.headers.get("x-total-count") == "2"


# --- v2 search includes description ---


def test_v2_search_matches_description(client):
    _create(client, title="Generic Title", description="A story about time-traveling wizards")
    _create(client, title="Another Book", description="Completely different content")

    r = client.get("/v2/books/search?q=time-traveling")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Generic Title"


def test_v2_search_has_more(client):
    for i in range(5):
        _create(client, title=f"Search Book {i}", description="target keyword")

    r = client.get("/v2/books/search?q=target&limit=2")
    assert r.status_code == 200
    body = r.json()
    assert body["has_more"] is True


# --- bulk create ---


def test_v2_bulk_create(client):
    payload = {
        "books": [
            {"title": "Bulk A", "authors": ["Author 1"]},
            {"title": "Bulk B", "authors": ["Author 2"]},
            {"title": "Bulk C"},
        ]
    }
    r = client.post("/v2/books/bulk", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["total_created"] == 3
    assert body["total_failed"] == 0
    assert len(body["created"]) == 3


def test_v2_bulk_create_partial_failure_isbn_conflict(client):
    _create(client, title="Existing", isbn="111-1")
    payload = {
        "books": [
            {"title": "New Book"},
            {"title": "Conflict Book", "isbn": "111-1"},
        ]
    }
    r = client.post("/v2/books/bulk", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["total_created"] == 1
    assert body["total_failed"] == 1
    assert body["failed"][0]["index"] == 1


def test_v2_bulk_create_too_many_books(client):
    payload = {"books": [{"title": f"Book {i}"} for i in range(51)]}
    r = client.post("/v2/books/bulk", json=payload)
    assert r.status_code == 422


# --- bulk delete ---


def test_v2_bulk_delete(client):
    a = _create(client, title="Del A")
    b = _create(client, title="Del B")

    r = client.request("DELETE", "/v2/books/bulk", json={"ids": [a["id"], b["id"]]})
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] == 2
    assert body["not_found"] == []


def test_v2_bulk_delete_partial_not_found(client):
    book = _create(client, title="Real Book")
    r = client.request("DELETE", "/v2/books/bulk", json={"ids": [book["id"], "00000000-0000-0000-0000-000000000000"]})
    assert r.status_code == 200
    body = r.json()
    assert body["deleted"] == 1
    assert len(body["not_found"]) == 1
