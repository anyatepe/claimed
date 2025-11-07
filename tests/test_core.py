import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    """Test the /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_endpoint():
    """Test the /version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "1.0.0"}
