"""Tests for EmbeddingService."""

import asyncio
import hashlib
import os
import pickle
from unittest.mock import MagicMock, Mock, patch

import pytest
import redis

from app.services.embeddings import EmbeddingService


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    mock_client = MagicMock(spec=redis.Redis)
    mock_client.get = Mock(return_value=None)
    mock_client.set = Mock(return_value=True)
    mock_client.mget = Mock(return_value=[None])
    mock_client.pipeline = Mock(return_value=Mock())
    return mock_client


@pytest.fixture
def mock_sentence_transformer():
    """Create a mock SentenceTransformer."""
    mock_model = MagicMock()
    mock_model.encode = Mock(return_value=[0.1, 0.2, 0.3])
    return mock_model


@pytest.fixture
def embedding_service(mock_redis_client):
    """Create an EmbeddingService instance with mocked dependencies."""
    with patch("app.services.embeddings.SentenceTransformer") as mock_transformer_class:
        mock_model = MagicMock()
        mock_model.encode = Mock(return_value=[0.1, 0.2, 0.3])
        mock_transformer_class.return_value = mock_model

        service = EmbeddingService(
            model_name="test-model",
            redis_client=mock_redis_client,
        )
        service.model = mock_model
        yield service


class TestEmbeddingService:
    """Test suite for EmbeddingService."""

    def test_init_default_model(self, mock_redis_client):
        """Test initialization with default model."""
        with patch("app.services.embeddings.SentenceTransformer") as mock_transformer_class:
            mock_model = MagicMock()
            mock_transformer_class.return_value = mock_model

            service = EmbeddingService(redis_client=mock_redis_client)
            assert service.model_name == "BAAI/bge-large-en-v1.5"
            assert service.redis_client == mock_redis_client

    def test_init_custom_model(self, mock_redis_client):
        """Test initialization with custom model."""
        with patch("app.services.embeddings.SentenceTransformer") as mock_transformer_class:
            mock_model = MagicMock()
            mock_transformer_class.return_value = mock_model

            service = EmbeddingService(
                model_name="custom-model",
                redis_client=mock_redis_client,
            )
            assert service.model_name == "custom-model"

    def test_init_env_var_model(self, mock_redis_client):
        """Test initialization with model from environment variable."""
        with patch("app.services.embeddings.SentenceTransformer") as mock_transformer_class:
            mock_model = MagicMock()
            mock_transformer_class.return_value = mock_model

            with patch.dict(os.environ, {"EMBED_MODEL_NAME": "env-model"}):
                service = EmbeddingService(redis_client=mock_redis_client)
                assert service.model_name == "env-model"

    def test_get_cache_key(self, embedding_service):
        """Test cache key generation."""
        text = "test text"
        cache_key = embedding_service._get_cache_key(text)
        expected_key = hashlib.sha256(
            f"{embedding_service.model_name}{text}".encode("utf-8")
        ).hexdigest()
        assert cache_key == expected_key

    def test_embed_text_cache_miss(self, embedding_service, mock_redis_client):
        """Test embed_text when cache misses."""
        text = "test text"
        expected_embedding = [0.1, 0.2, 0.3]

        mock_redis_client.get.return_value = None
        embedding_service.model.encode.return_value = expected_embedding

        result = embedding_service.embed_text(text)

        assert result == expected_embedding
        mock_redis_client.get.assert_called_once()
        mock_redis_client.set.assert_called_once()
        embedding_service.model.encode.assert_called_once_with(text, convert_to_numpy=False)

    def test_embed_text_cache_hit(self, embedding_service, mock_redis_client):
        """Test embed_text when cache hits."""
        text = "test text"
        cached_embedding = [0.4, 0.5, 0.6]
        cached_bytes = pickle.dumps(cached_embedding)

        mock_redis_client.get.return_value = cached_bytes

        result = embedding_service.embed_text(text)

        assert result == cached_embedding
        mock_redis_client.get.assert_called_once()
        mock_redis_client.set.assert_not_called()
        embedding_service.model.encode.assert_not_called()

    def test_embed_batch_empty(self, embedding_service):
        """Test embed_batch with empty list."""
        result = embedding_service.embed_batch([])
        assert result == []

    def test_embed_batch_cache_miss(self, embedding_service, mock_redis_client):
        """Test embed_batch when all texts cache miss."""
        texts = ["text1", "text2"]
        expected_embeddings = [[0.1, 0.2], [0.3, 0.4]]

        mock_redis_client.mget.return_value = [None, None]
        embedding_service.model.encode.return_value = expected_embeddings

        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline

        result = embedding_service.embed_batch(texts)

        assert result == expected_embeddings
        mock_redis_client.mget.assert_called_once()
        embedding_service.model.encode.assert_called_once_with(texts, convert_to_numpy=False)
        assert mock_pipeline.set.call_count == 2

    def test_embed_batch_cache_hit(self, embedding_service, mock_redis_client):
        """Test embed_batch when all texts cache hit."""
        texts = ["text1", "text2"]
        cached_embeddings = [
            pickle.dumps([0.1, 0.2]),
            pickle.dumps([0.3, 0.4]),
        ]

        mock_redis_client.mget.return_value = cached_embeddings

        result = embedding_service.embed_batch(texts)

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_redis_client.mget.assert_called_once()
        embedding_service.model.encode.assert_not_called()

    def test_embed_batch_partial_cache(self, embedding_service, mock_redis_client):
        """Test embed_batch with partial cache hits."""
        texts = ["text1", "text2", "text3"]
        cached_embeddings = [
            pickle.dumps([0.1, 0.2]),  # cached
            None,  # not cached
            pickle.dumps([0.5, 0.6]),  # cached
        ]
        new_embedding = [0.3, 0.4]

        mock_redis_client.mget.return_value = cached_embeddings
        embedding_service.model.encode.return_value = [new_embedding]

        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline

        result = embedding_service.embed_batch(texts)

        assert result == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_redis_client.mget.assert_called_once()
        embedding_service.model.encode.assert_called_once_with(["text2"], convert_to_numpy=False)
        assert mock_pipeline.set.call_count == 1  # Only one new embedding stored

    @pytest.mark.asyncio
    async def test_embed_batch_async_cache_miss(self, embedding_service, mock_redis_client):
        """Test embed_batch_async when cache misses."""
        texts = ["text1", "text2"]
        expected_embeddings = [[0.1, 0.2], [0.3, 0.4]]

        mock_redis_client.mget.return_value = [None, None]
        embedding_service.model.encode.return_value = expected_embeddings

        mock_pipeline = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline

        result = await embedding_service.embed_batch_async(texts)

        assert result == expected_embeddings
        mock_redis_client.mget.assert_called_once()
        embedding_service.model.encode.assert_called_once_with(texts, convert_to_numpy=False)

    @pytest.mark.asyncio
    async def test_embed_batch_async_cache_hit(self, embedding_service, mock_redis_client):
        """Test embed_batch_async when cache hits."""
        texts = ["text1", "text2"]
        cached_embeddings = [
            pickle.dumps([0.1, 0.2]),
            pickle.dumps([0.3, 0.4]),
        ]

        mock_redis_client.mget.return_value = cached_embeddings

        result = await embedding_service.embed_batch_async(texts)

        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_redis_client.mget.assert_called_once()
        embedding_service.model.encode.assert_not_called()

    @pytest.mark.asyncio
    async def test_embed_batch_async_parallel(self, embedding_service, mock_redis_client):
        """Test embed_batch_async_parallel with asyncio.gather."""
        texts = ["text1", "text2"]
        expected_embeddings = [[0.1, 0.2], [0.3, 0.4]]

        # Mock individual embed_text calls
        mock_redis_client.get.side_effect = [None, None]
        embedding_service.model.encode.side_effect = [
            expected_embeddings[0],
            expected_embeddings[1],
        ]

        result = await embedding_service.embed_batch_async_parallel(texts)

        assert len(result) == 2
        assert result == expected_embeddings
        assert mock_redis_client.get.call_count == 2

    def test_serialize_deserialize_embedding(self, embedding_service):
        """Test embedding serialization and deserialization."""
        embedding = [0.1, 0.2, 0.3, 0.4]
        serialized = embedding_service._serialize_embedding(embedding)
        deserialized = embedding_service._deserialize_embedding(serialized)
        assert deserialized == embedding

    def test_close(self, embedding_service):
        """Test resource cleanup."""
        embedding_service.close()
        # Verify executor is shut down (no exception should be raised)
        assert embedding_service.executor is not None
