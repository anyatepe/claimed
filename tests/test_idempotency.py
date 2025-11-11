"""
Tests for idempotency functionality.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    cache = AsyncMock()
    cache.get_response_cache = AsyncMock(return_value=None)
    cache.set_response_cache = AsyncMock(return_value=True)
    cache.close = AsyncMock()
    return cache


@pytest.mark.asyncio
async def test_idempotency_key_in_response(client, mock_cache_service):
    """Test that idempotency key is included in response headers."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        mock_cache_service.get_response_cache = AsyncMock(return_value=None)
        
        response = client.post(
            "/v1/query",
            json={
                "query": "test query",
                "model_version": "v1.0",
                "deterministic": True,
            },
            headers={"X-Session-ID": "session123"},
        )
        
        assert response.status_code == 200
        # Should have Idempotency-Key header
        assert "Idempotency-Key" in response.headers
        # Should also be in response body
        data = response.json()
        assert "idempotency_key" in data
        assert data["idempotency_key"] is not None


@pytest.mark.asyncio
async def test_idempotency_key_consistency(client, mock_cache_service):
    """Test that same request produces same idempotency key."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        mock_cache_service.get_response_cache = AsyncMock(return_value=None)
        
        session_id = "session123"
        query = "test query"
        model_version = "v1.0"
        
        # First request
        response1 = client.post(
            "/v1/query",
            json={
                "query": query,
                "model_version": model_version,
                "deterministic": True,
            },
            headers={"X-Session-ID": session_id},
        )
        idempotency_key1 = response1.headers.get("Idempotency-Key")
        
        # Second request with same parameters
        response2 = client.post(
            "/v1/query",
            json={
                "query": query,
                "model_version": model_version,
                "deterministic": True,
            },
            headers={"X-Session-ID": session_id},
        )
        idempotency_key2 = response2.headers.get("Idempotency-Key")
        
        # Should produce same idempotency key
        assert idempotency_key1 == idempotency_key2


@pytest.mark.asyncio
async def test_idempotency_key_different_for_different_queries(client, mock_cache_service):
    """Test that different queries produce different idempotency keys."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        mock_cache_service.get_response_cache = AsyncMock(return_value=None)
        
        session_id = "session123"
        model_version = "v1.0"
        
        # First request
        response1 = client.post(
            "/v1/query",
            json={
                "query": "query 1",
                "model_version": model_version,
                "deterministic": True,
            },
            headers={"X-Session-ID": session_id},
        )
        idempotency_key1 = response1.headers.get("Idempotency-Key")
        
        # Second request with different query
        response2 = client.post(
            "/v1/query",
            json={
                "query": "query 2",
                "model_version": model_version,
                "deterministic": True,
            },
            headers={"X-Session-ID": session_id},
        )
        idempotency_key2 = response2.headers.get("Idempotency-Key")
        
        # Should produce different idempotency keys
        assert idempotency_key1 != idempotency_key2


@pytest.mark.asyncio
async def test_idempotency_key_with_provided_key(client, mock_cache_service):
    """Test that provided idempotency key is used."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        mock_cache_service.get_response_cache = AsyncMock(return_value=None)
        
        provided_key = "custom-idempotency-key-12345"
        
        response = client.post(
            "/v1/query",
            json={
                "query": "test query",
                "model_version": "v1.0",
                "deterministic": True,
            },
            headers={
                "X-Session-ID": "session123",
                "Idempotency-Key": provided_key,
            },
        )
        
        assert response.status_code == 200
        # Should use provided key
        assert response.headers.get("Idempotency-Key") == provided_key
        data = response.json()
        assert data["idempotency_key"] == provided_key


@pytest.mark.asyncio
async def test_idempotency_headers_present(client, mock_cache_service):
    """Test that idempotency-related headers are present in responses."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        mock_cache_service.get_response_cache = AsyncMock(return_value=None)
        
        response = client.post(
            "/v1/query",
            json={
                "query": "test query",
                "model_version": "v1.0",
                "deterministic": True,
            },
            headers={"X-Session-ID": "session123"},
        )
        
        assert response.status_code == 200
        # Check for idempotency headers
        assert "Idempotency-Key" in response.headers
        assert "X-Cache-Hit" in response.headers
        # Idempotency key should not be empty
        assert response.headers["Idempotency-Key"] != ""
