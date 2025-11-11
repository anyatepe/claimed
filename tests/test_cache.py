"""
Tests for Redis caching functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.cache import CacheService


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    return client


@pytest.fixture
def cache_service(mock_redis_client):
    """Create a CacheService with mocked Redis client."""
    service = CacheService(redis_client=mock_redis_client)
    return service


@pytest.mark.asyncio
async def test_get_retrieval_cache_hit(cache_service, mock_redis_client):
    """Test retrieval cache hit."""
    query_hash = "abc123"
    filters = {"category": "test"}
    
    cached_chunks = [
        {"id": "chunk1", "text": "Test chunk 1"},
        {"id": "chunk2", "text": "Test chunk 2"},
    ]
    
    # Mock Redis get to return cached data
    mock_redis_client.get = AsyncMock(return_value=json.dumps(cached_chunks).encode())
    
    result = await cache_service.get_retrieval_cache(query_hash, filters)
    
    assert result == cached_chunks
    mock_redis_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_retrieval_cache_miss(cache_service, mock_redis_client):
    """Test retrieval cache miss."""
    query_hash = "abc123"
    filters = {"category": "test"}
    
    # Mock Redis get to return None (cache miss)
    mock_redis_client.get = AsyncMock(return_value=None)
    
    result = await cache_service.get_retrieval_cache(query_hash, filters)
    
    assert result is None
    mock_redis_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_set_retrieval_cache(cache_service, mock_redis_client):
    """Test setting retrieval cache."""
    query_hash = "abc123"
    filters = {"category": "test"}
    chunks = [
        {"id": "chunk1", "text": "Test chunk 1"},
        {"id": "chunk2", "text": "Test chunk 2"},
    ]
    ttl = 300
    
    # Mock Redis setex
    mock_redis_client.setex = AsyncMock(return_value=True)
    
    result = await cache_service.set_retrieval_cache(query_hash, chunks, filters, ttl=ttl)
    
    assert result is True
    mock_redis_client.setex.assert_called_once()
    # Verify the key and value
    call_args = mock_redis_client.setex.call_args
    assert call_args[0][1] == ttl
    assert json.loads(call_args[0][2]) == chunks


@pytest.mark.asyncio
async def test_get_response_cache_hit(cache_service, mock_redis_client):
    """Test response cache hit."""
    session_id = "session123"
    query_hash = "abc123"
    model_version = "v1.0"
    
    cached_response = {"answer": "Cached answer"}
    
    # Mock Redis get to return cached data
    mock_redis_client.get = AsyncMock(return_value=json.dumps(cached_response).encode())
    
    result = await cache_service.get_response_cache(session_id, query_hash, model_version)
    
    assert result == cached_response
    mock_redis_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_set_response_cache(cache_service, mock_redis_client):
    """Test setting response cache."""
    session_id = "session123"
    query_hash = "abc123"
    model_version = "v1.0"
    response = {"answer": "Test answer"}
    ttl = 3600
    
    # Mock Redis setex
    mock_redis_client.setex = AsyncMock(return_value=True)
    
    result = await cache_service.set_response_cache(
        session_id, query_hash, model_version, response, ttl=ttl
    )
    
    assert result is True
    mock_redis_client.setex.assert_called_once()
    # Verify the value
    call_args = mock_redis_client.setex.call_args
    assert json.loads(call_args[0][2]) == response


@pytest.mark.asyncio
async def test_retrieval_cache_with_different_filters(cache_service, mock_redis_client):
    """Test that different filters produce different cache keys."""
    query_hash = "abc123"
    filters1 = {"category": "test"}
    filters2 = {"category": "other"}
    
    chunks1 = [{"id": "chunk1"}]
    chunks2 = [{"id": "chunk2"}]
    
    mock_redis_client.setex = AsyncMock(return_value=True)
    
    # Set cache with different filters
    await cache_service.set_retrieval_cache(query_hash, chunks1, filters1, ttl=300)
    await cache_service.set_retrieval_cache(query_hash, chunks2, filters2, ttl=300)
    
    # Verify different keys were used
    assert mock_redis_client.setex.call_count == 2
    key1 = mock_redis_client.setex.call_args_list[0][0][0]
    key2 = mock_redis_client.setex.call_args_list[1][0][0]
    assert key1 != key2
