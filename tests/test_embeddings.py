"""
Unit tests for EmbeddingService.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import numpy as np

from app.services.embeddings import EmbeddingService


class TestEmbeddingService:
    """Test cases for EmbeddingService."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock()
        mock_client.mget = AsyncMock(return_value=[None])
        mock_client.mset = AsyncMock()
        mock_client.close = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def embedding_service(self, mock_redis_client):
        """Create EmbeddingService instance with mocked Redis."""
        with patch('app.services.embeddings.SentenceTransformer') as mock_transformer:
            mock_model = MagicMock()
            mock_model.encode = MagicMock(return_value=np.array([0.1, 0.2, 0.3], dtype=np.float32))
            mock_transformer.return_value = mock_model
            
            service = EmbeddingService(
                model_name="BAAI/bge-large-en-v1.5",
                redis_client=mock_redis_client
            )
            service.model = mock_model
            yield service
    
    @pytest.mark.asyncio
    async def test_get_embedding_cache_miss(self, embedding_service, mock_redis_client):
        """Test get_embedding when cache miss occurs."""
        text = "Hello world"
        expected_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        
        mock_redis_client.get.return_value = None
        embedding_service.model.encode.return_value = expected_embedding
        
        result = await embedding_service.get_embedding(text)
        
        # Verify cache was checked
        assert mock_redis_client.get.called
        
        # Verify embedding was generated
        embedding_service.model.encode.assert_called_once_with(text, convert_to_numpy=True)
        
        # Verify result
        np.testing.assert_array_equal(result, expected_embedding)
        
        # Verify cache was updated
        assert mock_redis_client.set.called
        call_args = mock_redis_client.set.call_args
        assert call_args[0][0] == embedding_service._get_cache_key(text)
        cached_data = json.loads(call_args[0][1])
        np.testing.assert_array_almost_equal(np.array(cached_data), expected_embedding)
    
    @pytest.mark.asyncio
    async def test_get_embedding_cache_hit(self, embedding_service, mock_redis_client):
        """Test get_embedding when cache hit occurs."""
        text = "Hello world"
        cached_embedding = [0.4, 0.5, 0.6]
        cache_key = embedding_service._get_cache_key(text)
        
        # Redis returns bytes, but our code handles both
        mock_redis_client.get.return_value = json.dumps(cached_embedding).encode('utf-8')
        
        result = await embedding_service.get_embedding(text)
        
        # Verify cache was checked
        assert mock_redis_client.get.called
        
        # Verify embedding was NOT generated (cache hit)
        embedding_service.model.encode.assert_not_called()
        
        # Verify cache was NOT updated
        mock_redis_client.set.assert_not_called()
        
        # Verify result matches cached value
        np.testing.assert_array_almost_equal(result, np.array(cached_embedding, dtype=np.float32))
    
    @pytest.mark.asyncio
    async def test_batch_embed_all_cache_miss(self, embedding_service, mock_redis_client):
        """Test batch_embed when all texts are cache misses."""
        texts = ["Hello", "World", "Test"]
        expected_embeddings = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ], dtype=np.float32)
        
        mock_redis_client.mget.return_value = [None, None, None]
        embedding_service.model.encode.return_value = expected_embeddings
        
        result = await embedding_service.batch_embed(texts)
        
        # Verify batch cache check
        assert mock_redis_client.mget.called
        
        # Verify batch embedding was generated
        embedding_service.model.encode.assert_called_once()
        call_args = embedding_service.model.encode.call_args
        assert call_args[0][0] == texts
        
        # Verify results
        assert result.shape == expected_embeddings.shape
        np.testing.assert_array_equal(result, expected_embeddings)
        
        # Verify batch cache update
        assert mock_redis_client.mset.called
    
    @pytest.mark.asyncio
    async def test_batch_embed_all_cache_hit(self, embedding_service, mock_redis_client):
        """Test batch_embed when all texts are cache hits."""
        texts = ["Hello", "World"]
        cached_embeddings = [
            json.dumps([0.1, 0.2, 0.3]).encode('utf-8'),
            json.dumps([0.4, 0.5, 0.6]).encode('utf-8')
        ]
        
        mock_redis_client.mget.return_value = cached_embeddings
        
        result = await embedding_service.batch_embed(texts)
        
        # Verify batch cache check
        assert mock_redis_client.mget.called
        
        # Verify embedding was NOT generated (all cache hits)
        embedding_service.model.encode.assert_not_called()
        
        # Verify cache was NOT updated
        mock_redis_client.mset.assert_not_called()
        
        # Verify results
        assert result.shape == (2, 3)
        np.testing.assert_array_almost_equal(
            result[0],
            np.array([0.1, 0.2, 0.3], dtype=np.float32)
        )
        np.testing.assert_array_almost_equal(
            result[1],
            np.array([0.4, 0.5, 0.6], dtype=np.float32)
        )
    
    @pytest.mark.asyncio
    async def test_batch_embed_partial_cache_hit(self, embedding_service, mock_redis_client):
        """Test batch_embed when some texts are cache hits."""
        texts = ["Hello", "World", "Test"]
        cached_embeddings = [
            json.dumps([0.1, 0.2, 0.3]).encode('utf-8'),  # Cache hit
            None,  # Cache miss
            json.dumps([0.7, 0.8, 0.9]).encode('utf-8')   # Cache hit
        ]
        new_embedding = np.array([[0.4, 0.5, 0.6]], dtype=np.float32)
        
        mock_redis_client.mget.return_value = cached_embeddings
        embedding_service.model.encode.return_value = new_embedding
        
        result = await embedding_service.batch_embed(texts)
        
        # Verify batch cache check
        assert mock_redis_client.mget.called
        
        # Verify embedding was generated only for cache miss
        embedding_service.model.encode.assert_called_once()
        call_args = embedding_service.model.encode.call_args
        assert call_args[0][0] == ["World"]  # Only the cache miss
        
        # Verify results
        assert result.shape == (3, 3)
        np.testing.assert_array_almost_equal(
            result[0],
            np.array([0.1, 0.2, 0.3], dtype=np.float32)
        )
        np.testing.assert_array_almost_equal(
            result[1],
            np.array([0.4, 0.5, 0.6], dtype=np.float32)
        )
        np.testing.assert_array_almost_equal(
            result[2],
            np.array([0.7, 0.8, 0.9], dtype=np.float32)
        )
        
        # Verify cache was updated for the new embedding
        assert mock_redis_client.mset.called
    
    @pytest.mark.asyncio
    async def test_batch_embed_empty_list(self, embedding_service):
        """Test batch_embed with empty list."""
        result = await embedding_service.batch_embed([])
        assert result.shape == (0,)
    
    @pytest.mark.asyncio
    async def test_get_embedding_no_redis(self):
        """Test get_embedding without Redis client."""
        with patch('app.services.embeddings.SentenceTransformer') as mock_transformer:
            mock_model = MagicMock()
            expected_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
            mock_model.encode.return_value = expected_embedding
            mock_transformer.return_value = mock_model
            
            service = EmbeddingService(model_name="BAAI/bge-large-en-v1.5", redis_url=None)
            service.model = mock_model
            
            result = await service.get_embedding("Hello")
            
            # Verify embedding was generated
            mock_model.encode.assert_called_once()
            
            # Verify result
            np.testing.assert_array_equal(result, expected_embedding)
    
    @pytest.mark.asyncio
    async def test_batch_embed_no_redis(self):
        """Test batch_embed without Redis client."""
        with patch('app.services.embeddings.SentenceTransformer') as mock_transformer:
            mock_model = MagicMock()
            expected_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], dtype=np.float32)
            mock_model.encode.return_value = expected_embeddings
            mock_transformer.return_value = mock_model
            
            service = EmbeddingService(model_name="BAAI/bge-large-en-v1.5", redis_url=None)
            service.model = mock_model
            
            result = await service.batch_embed(["Hello", "World"])
            
            # Verify embedding was generated
            mock_model.encode.assert_called_once()
            
            # Verify result
            np.testing.assert_array_equal(result, expected_embeddings)
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, embedding_service):
        """Test cache key generation is consistent."""
        text = "Hello world"
        key1 = embedding_service._get_cache_key(text)
        key2 = embedding_service._get_cache_key(text)
        
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA256 hex digest length
    
    @pytest.mark.asyncio
    async def test_close_redis_connection(self, embedding_service, mock_redis_client):
        """Test closing Redis connection."""
        await embedding_service.close()
        
        # Verify close was called if Redis was initialized
        if embedding_service._redis_initialized:
            mock_redis_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, embedding_service, mock_redis_client):
        """Test that Redis errors don't break the service."""
        text = "Hello world"
        expected_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        
        # Simulate Redis error
        mock_redis_client.get.side_effect = Exception("Redis error")
        embedding_service.model.encode.return_value = expected_embedding
        
        # Should still work without cache
        result = await embedding_service.get_embedding(text)
        
        # Verify embedding was generated
        embedding_service.model.encode.assert_called_once()
        
        # Verify result
        np.testing.assert_array_equal(result, expected_embedding)
