"""
Tests for embedding generation functionality.
"""
import pytest
import numpy as np
from typing import List, Union
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def sample_texts():
    """Sample texts for embedding generation."""
    return [
        "This is the first sample text.",
        "This is the second sample text.",
        "This is a longer sample text with more words and content.",
    ]


@pytest.fixture
def embedding_model():
    """Fixture for embedding model."""
    class MockEmbeddingModel:
        def __init__(self, model_name: str = "test-model", dimension: int = 384):
            self.model_name = model_name
            self.dimension = dimension
        
        def embed(self, text: str) -> np.ndarray:
            """Generate embedding for a single text."""
            # Generate deterministic embedding based on text hash
            np.random.seed(hash(text) % 2**32)
            return np.random.randn(self.dimension).astype(np.float32)
        
        def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
            """Generate embeddings for multiple texts."""
            return [self.embed(text) for text in texts]
        
        def get_dimension(self) -> int:
            """Get embedding dimension."""
            return self.dimension
    
    return MockEmbeddingModel(dimension=384)


@pytest.fixture
def sample_embedding():
    """Sample embedding vector."""
    return np.random.randn(384).astype(np.float32)


class TestEmbeddings:
    """Test suite for embedding functionality."""
    
    def test_embed_single_text(self, embedding_model):
        """Test embedding generation for a single text."""
        text = "Test text for embedding"
        embedding = embedding_model.embed(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (embedding_model.dimension,)
        assert embedding.dtype == np.float32
    
    def test_embed_batch(self, embedding_model, sample_texts):
        """Test batch embedding generation."""
        embeddings = embedding_model.embed_batch(sample_texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(sample_texts)
        
        for emb in embeddings:
            assert isinstance(emb, np.ndarray)
            assert emb.shape == (embedding_model.dimension,)
    
    def test_embedding_dimension(self, embedding_model):
        """Test that embeddings have correct dimension."""
        text = "Test text"
        embedding = embedding_model.embed(text)
        
        assert embedding.shape[0] == embedding_model.dimension
        assert embedding_model.get_dimension() == embedding_model.dimension
    
    def test_embedding_deterministic(self, embedding_model):
        """Test that same text produces same embedding."""
        text = "Deterministic test text"
        embedding1 = embedding_model.embed(text)
        embedding2 = embedding_model.embed(text)
        
        np.testing.assert_array_equal(embedding1, embedding2)
    
    def test_embedding_different_texts(self, embedding_model):
        """Test that different texts produce different embeddings."""
        text1 = "First text"
        text2 = "Second text"
        
        embedding1 = embedding_model.embed(text1)
        embedding2 = embedding_model.embed(text2)
        
        # Embeddings should be different
        assert not np.array_equal(embedding1, embedding2)
    
    def test_embedding_normalized(self, embedding_model):
        """Test that embeddings can be normalized."""
        text = "Test text for normalization"
        embedding = embedding_model.embed(text)
        
        # Normalize embedding
        norm = np.linalg.norm(embedding)
        normalized = embedding / norm if norm > 0 else embedding
        
        assert np.isclose(np.linalg.norm(normalized), 1.0) or norm == 0
    
    def test_embedding_similarity(self, embedding_model):
        """Test cosine similarity between embeddings."""
        text1 = "Similar text one"
        text2 = "Similar text two"
        text3 = "Completely different content"
        
        emb1 = embedding_model.embed(text1)
        emb2 = embedding_model.embed(text2)
        emb3 = embedding_model.embed(text3)
        
        # Normalize for cosine similarity
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        sim_12 = cosine_similarity(emb1, emb2)
        sim_13 = cosine_similarity(emb1, emb3)
        
        assert -1.0 <= sim_12 <= 1.0
        assert -1.0 <= sim_13 <= 1.0
    
    def test_embed_empty_text(self, embedding_model):
        """Test embedding generation for empty text."""
        embedding = embedding_model.embed("")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (embedding_model.dimension,)
    
    def test_embed_special_characters(self, embedding_model):
        """Test embedding generation with special characters."""
        texts = [
            "Text with @#$% special chars!",
            "Text with\nnewlines\tand\ttabs",
            "Text with unicode: 你好世界 🌍",
        ]
        
        for text in texts:
            embedding = embedding_model.embed(text)
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (embedding_model.dimension,)
    
    def test_embed_batch_empty(self, embedding_model):
        """Test batch embedding with empty list."""
        embeddings = embedding_model.embed_batch([])
        assert embeddings == []
    
    def test_embed_batch_large(self, embedding_model):
        """Test batch embedding with large number of texts."""
        texts = [f"Text number {i}" for i in range(100)]
        embeddings = embedding_model.embed_batch(texts)
        
        assert len(embeddings) == 100
        assert all(isinstance(emb, np.ndarray) for emb in embeddings)
    
    def test_embedding_finite_values(self, embedding_model):
        """Test that embeddings contain only finite values."""
        text = "Test text"
        embedding = embedding_model.embed(text)
        
        assert np.all(np.isfinite(embedding))
        assert not np.any(np.isnan(embedding))
        assert not np.any(np.isinf(embedding))
    
    def test_embedding_model_name(self, embedding_model):
        """Test that model name is accessible."""
        assert hasattr(embedding_model, 'model_name')
        assert isinstance(embedding_model.model_name, str)
        assert len(embedding_model.model_name) > 0


if __name__ == "__main__":
    pytest.main([__file__])
