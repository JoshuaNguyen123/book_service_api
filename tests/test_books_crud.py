"""Books CRUD and error contract tests."""
from fastapi.testclient import TestClient


def test_create_book(client: TestClient):
    payload = {
        "title": "The Great Book",
        "authors": ["Author One"],
        "tags": ["fiction"],
    }
    response = client.post("/v1/books", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "The Great Book"
    assert data["authors"] == ["Author One"]
    assert data["tags"] == ["fiction"]
    assert "id" in data
    assert data["created_at"]
    assert data["updated_at"]


def test_create_book_with_isbn(client: TestClient):
    payload = {"title": "Book With ISBN", "authors": [], "isbn": "978-0-123456-78-9"}
    response = client.post("/v1/books", json=payload)
    assert response.status_code == 201
    assert response.json()["isbn"] == "978-0-123456-78-9"


def test_get_book(client: TestClient):
    create = client.post("/v1/books", json={"title": "Fetch Me", "authors": []})
    assert create.status_code == 201
    book_id = create.json()["id"]
    response = client.get(f"/v1/books/{book_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Fetch Me"


def test_get_book_404(client: TestClient):
    response = client.get("/v1/books/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"


def test_patch_book(client: TestClient):
    create = client.post("/v1/books", json={"title": "Original", "authors": []})
    book_id = create.json()["id"]
    response = client.patch(f"/v1/books/{book_id}", json={"title": "Updated"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"


def test_patch_book_404(client: TestClient):
    response = client.patch("/v1/books/00000000-0000-0000-0000-000000000000", json={"title": "No"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_delete_book(client: TestClient):
    create = client.post("/v1/books", json={"title": "To Delete", "authors": []})
    book_id = create.json()["id"]
    response = client.delete(f"/v1/books/{book_id}")
    assert response.status_code == 204
    get_resp = client.get(f"/v1/books/{book_id}")
    assert get_resp.status_code == 404


def test_delete_book_404(client: TestClient):
    response = client.delete("/v1/books/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_unique_isbn_conflict(client: TestClient):
    client.post("/v1/books", json={"title": "First", "authors": [], "isbn": "111"})
    response = client.post("/v1/books", json={"title": "Second", "authors": [], "isbn": "111"})
    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "conflict"


def test_validation_error_format(client: TestClient):
    response = client.post("/v1/books", json={"title": ""})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_title_cannot_be_whitespace_only(client: TestClient):
    response = client.post("/v1/books", json={"title": "   ", "authors": []})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_book_strips_blank_list_values(client: TestClient):
    response = client.post(
        "/v1/books",
        json={
            "title": "Normalized",
            "authors": [" Author One ", "   "],
            "tags": [" fiction ", ""],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["authors"] == ["Author One"]
    assert data["tags"] == ["fiction"]
