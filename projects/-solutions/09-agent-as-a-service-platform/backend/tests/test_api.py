"""Backend tests — smoke tests for the API."""
import os
import sys

import pytest
from fastapi.testclient import TestClient

# Make backend importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def client():
    """Spin up a TestClient against the FastAPI app.

    Note: this requires a running Postgres at DATABASE_URL.
    For unit tests without DB, use the in-memory fixtures below.
    """
    from main import app

    return TestClient(app)


def test_health_endpoint(client):
    """Health endpoint should return 200."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert data["version"] == "1.0.0"


def test_register_validation(client):
    """Register with short password should fail."""
    resp = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "short",  # too short
        },
    )
    assert resp.status_code == 422
