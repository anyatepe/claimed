"""
Tests for RAG pipeline caching functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.rag_pipeline import RAGPipeline
from app.services.cache import CacheService


class MockVectorStore:
    """Mock vector store for testing."""
    
    def __init__(self):
        self.search_calls = []
    
    def search(self, query: str, k: int = 5):
        """Mock search that records calls."""
        self.search_calls.append((query, k))
        return [
            {"id": f"chunk{i}", "text": f"Chunk {i} for query: {query}"}
            for i in range(k)
        ]


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    cache = AsyncMock(spec=CacheService)
    cache.get_retrieval_cache = AsyncMock(return_value=None)
    cache.set_retrieval_cache = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def rag_pipeline_with_cache(mock_cache_service):
    """Create RAG pipeline with cache service."""
    vector_store = MockVectorStore()
    return RAGPipeline(vector_store=vector_store, cache_service=mock_cache_service)


@pytest.fixture
def rag_pipeline_without_cache():
    """Create RAG pipeline without cache service."""
    vector_store = MockVectorStore()
    return RAGPipeline(vector_store=vector_store, cache_service=None)


@pytest.mark.asyncio
async def test_retrieve_with_cache_hit(rag_pipeline_with_cache, mock_cache_service):
    """Test retrieval with cache hit."""
    query = "test query"
    cached_chunks = [
        {"id": "cached1", "text": "Cached chunk 1"},
        {"id": "cached2", "text": "Cached chunk 2"},
    ]
    
    # Mock cache hit
    mock_cache_service.get_retrieval_cache = AsyncMock(return_value=cached_chunks)
    
    result = await rag_pipeline_with_cache.retrieve(query, k=5)
    
    # Should return cached chunks
    assert result == cached_chunks
    # Should not call vector store search
    assert len(rag_pipeline_with_cache.vector_store.search_calls) == 0
    # Should not set cache (already cached)
    mock_cache_service.set_retrieval_cache.assert_not_called()


@pytest.mark.asyncio
async def test_retrieve_with_cache_miss(rag_pipeline_with_cache, mock_cache_service):
    """Test retrieval with cache miss."""
    query = "test query"
    
    # Mock cache miss
    mock_cache_service.get_retrieval_cache = AsyncMock(return_value=None)
    
    result = await rag_pipeline_with_cache.retrieve(query, k=5)
    
    # Should call vector store search
    assert len(rag_pipeline_with_cache.vector_store.search_calls) == 1
    assert rag_pipeline_with_cache.vector_store.search_calls[0] == (query, 5)
    # Should cache the results
    mock_cache_service.set_retrieval_cache.assert_called_once()
    # Verify cached chunks match returned chunks
    cached_chunks = mock_cache_service.set_retrieval_cache.call_args[0][1]
    assert cached_chunks == result


@pytest.mark.asyncio
async def test_retrieve_without_cache(rag_pipeline_without_cache):
    """Test retrieval without cache service."""
    query = "test query"
    
    result = await rag_pipeline_without_cache.retrieve(query, k=5)
    
    # Should call vector store search
    assert len(rag_pipeline_without_cache.vector_store.search_calls) == 1
    assert len(result) == 5


@pytest.mark.asyncio
async def test_retrieve_with_filters(rag_pipeline_with_cache, mock_cache_service):
    """Test retrieval with filters."""
    query = "test query"
    filters = {"category": "test"}
    
    # Mock cache miss
    mock_cache_service.get_retrieval_cache = AsyncMock(return_value=None)
    
    result = await rag_pipeline_with_cache.retrieve(query, k=5, filters=filters)
    
    # Should call cache with filters
    mock_cache_service.get_retrieval_cache.assert_called_once()
    call_args = mock_cache_service.get_retrieval_cache.call_args
    assert call_args[0][1] == filters
    # Should cache with filters
    mock_cache_service.set_retrieval_cache.assert_called_once()
    cache_call_args = mock_cache_service.set_retrieval_cache.call_args
    assert cache_call_args[0][2] == filters
