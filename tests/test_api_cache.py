"""
Tests for API caching and idempotency headers.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

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
async def test_query_with_cache_hit(client, mock_cache_service):
    """Test query endpoint with cache hit."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        # Mock cache hit
        cached_response = {"answer": "Cached answer"}
        mock_cache_service.get_response_cache = AsyncMock(return_value=cached_response)
        
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
        data = response.json()
        assert data["answer"] == "Cached answer"
        assert data["cached"] is True
        assert "Idempotency-Key" in response.headers
        assert response.headers["X-Cache-Hit"] == "true"


@pytest.mark.asyncio
async def test_query_with_cache_miss(client, mock_cache_service):
    """Test query endpoint with cache miss."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        # Mock cache miss
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
        data = response.json()
        assert "[STUBBED] Answer for query: test query" in data["answer"]
        assert data["cached"] is False
        assert "Idempotency-Key" in response.headers
        assert response.headers["X-Cache-Hit"] == "false"
        # Should cache the response
        mock_cache_service.set_response_cache.assert_called_once()


@pytest.mark.asyncio
async def test_query_with_idempotency_key(client, mock_cache_service):
    """Test query endpoint with provided idempotency key."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        mock_cache_service.get_response_cache = AsyncMock(return_value=None)
        
        idempotency_key = "test-idempotency-key-123"
        
        response = client.post(
            "/v1/query",
            json={
                "query": "test query",
                "model_version": "v1.0",
                "deterministic": True,
            },
            headers={
                "X-Session-ID": "session123",
                "Idempotency-Key": idempotency_key,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["idempotency_key"] == idempotency_key
        assert response.headers["Idempotency-Key"] == idempotency_key


@pytest.mark.asyncio
async def test_query_non_deterministic_no_cache(client, mock_cache_service):
    """Test query endpoint with non-deterministic prompt (no caching)."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        response = client.post(
            "/v1/query",
            json={
                "query": "test query",
                "model_version": "v1.0",
                "deterministic": False,
            },
            headers={"X-Session-ID": "session123"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["cached"] is False
        # Should not check or set cache
        mock_cache_service.get_response_cache.assert_not_called()
        mock_cache_service.set_response_cache.assert_not_called()


@pytest.mark.asyncio
async def test_query_generates_session_id(client, mock_cache_service):
    """Test that session ID is generated if not provided."""
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
            # No X-Session-ID header
        )
        
        assert response.status_code == 200
        # Should still work and generate idempotency key
        assert "Idempotency-Key" in response.headers


@pytest.mark.asyncio
async def test_query_same_session_same_query_cache_hit(client, mock_cache_service):
    """Test that same session and query returns cached response."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        session_id = "session123"
        query = "test query"
        model_version = "v1.0"
        
        # First request - cache miss
        mock_cache_service.get_response_cache = AsyncMock(return_value=None)
        response1 = client.post(
            "/v1/query",
            json={
                "query": query,
                "model_version": model_version,
                "deterministic": True,
            },
            headers={"X-Session-ID": session_id},
        )
        assert response1.status_code == 200
        assert response1.json()["cached"] is False
        
        # Second request - cache hit
        cached_response = {"answer": "Cached answer from first request"}
        mock_cache_service.get_response_cache = AsyncMock(return_value=cached_response)
        response2 = client.post(
            "/v1/query",
            json={
                "query": query,
                "model_version": model_version,
                "deterministic": True,
            },
            headers={"X-Session-ID": session_id},
        )
        assert response2.status_code == 200
        assert response2.json()["cached"] is True
        assert response2.json()["answer"] == "Cached answer from first request"
        assert response2.headers["X-Cache-Hit"] == "true"


@pytest.mark.asyncio
async def test_query_different_model_version_different_cache(client, mock_cache_service):
    """Test that different model versions use different cache keys."""
    # Patch cache service
    with patch("app.api.main.cache_service", mock_cache_service):
        session_id = "session123"
        query = "test query"
        
        # Request with model version v1.0
        mock_cache_service.get_response_cache = AsyncMock(return_value=None)
        response1 = client.post(
            "/v1/query",
            json={
                "query": query,
                "model_version": "v1.0",
                "deterministic": True,
            },
            headers={"X-Session-ID": session_id},
        )
        assert response1.status_code == 200
        
        # Request with model version v2.0 - should be cache miss
        response2 = client.post(
            "/v1/query",
            json={
                "query": query,
                "model_version": "v2.0",
                "deterministic": True,
            },
            headers={"X-Session-ID": session_id},
        )
        assert response2.status_code == 200
        
        # Verify different cache keys were used
        assert mock_cache_service.get_response_cache.call_count == 2
        call1_args = mock_cache_service.get_response_cache.call_args_list[0][0]
        call2_args = mock_cache_service.get_response_cache.call_args_list[1][0]
        # Same session_id and query_hash, but different model_version
        assert call1_args[0] == call2_args[0]  # session_id
        assert call1_args[1] == call2_args[1]  # query_hash
        assert call1_args[2] != call2_args[2]  # model_version
