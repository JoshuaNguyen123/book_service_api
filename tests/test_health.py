"""Health endpoint tests."""
import pytest
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}
