"""
Pytest tests for FastAPI application with OpenTelemetry and Prometheus.
"""
import pytest
from fastapi.testclient import TestClient
from app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_metrics_endpoint_exists(client):
    """Test that /metrics endpoint returns 200."""
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_content_type(client):
    """Test that /metrics returns Prometheus format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")


def test_metrics_contains_request_rate(client):
    """Test that metrics include request rate metric."""
    # Make a request to generate some metrics
    client.get("/")
    
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text
    
    # Check for request count metric (http_requests_total)
    assert "http_requests_total" in metrics_text


def test_metrics_contains_latency(client):
    """Test that metrics include latency metric."""
    # Make a request to generate some metrics
    client.get("/")
    
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text
    
    # Check for latency metric (http_request_duration_seconds)
    assert "http_request_duration_seconds" in metrics_text


def test_metrics_contains_error_count(client):
    """Test that metrics include error count metric."""
    # Make a request that might generate an error
    client.get("/nonexistent")
    
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text
    
    # Check for error count metric (http_errors_total)
    assert "http_errors_total" in metrics_text


def test_metrics_key_metrics_exist(client):
    """Test that all key metrics exist in the /metrics endpoint."""
    # Generate some traffic
    client.get("/")
    client.get("/health")
    client.get("/nonexistent")  # This will generate a 404 error
    
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text
    
    # Verify all three key metrics are present
    assert "http_requests_total" in metrics_text, "Request rate metric missing"
    assert "http_request_duration_seconds" in metrics_text, "Latency metric missing"
    assert "http_errors_total" in metrics_text, "Error count metric missing"
    
    # Verify metrics have labels
    assert "method=" in metrics_text
    assert "endpoint=" in metrics_text
    assert "status=" in metrics_text


def test_root_endpoint(client):
    """Test root endpoint works."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_endpoint(client):
    """Test health endpoint works."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
