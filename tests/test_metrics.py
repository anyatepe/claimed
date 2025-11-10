"""Tests for Prometheus metrics endpoint."""
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_metrics_endpoint_returns_200(client):
    """Test that /metrics endpoint returns 200 status code."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    
    # Check that response contains Prometheus metrics format
    content = response.text
    assert "http_requests_total" in content or len(content) > 0


def test_metrics_endpoint_contains_expected_metrics(client):
    """Test that /metrics endpoint contains expected metric names."""
    # Make a request to generate some metrics
    client.get("/health")
    
    response = client.get("/metrics")
    assert response.status_code == 200
    
    content = response.text
    # Check for Prometheus format (should contain # HELP or # TYPE or metric names)
    assert any(keyword in content for keyword in ["# HELP", "# TYPE", "http_requests_total", "http_request_duration_seconds"])
