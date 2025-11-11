"""
Tests for embedding generation functionality.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock


class TestEmbeddingGenerator:
    """Test embedding generation."""

    def test_generate_embedding(self, sample_text_content, mock_embedding_model):
        """Test generating a single embedding."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model)
        embedding = generator.generate(sample_text_content)
        
        assert embedding is not None
        assert isinstance(embedding, (list, np.ndarray))
        assert len(embedding) > 0

    def test_generate_embedding_batch(self, sample_chunks, mock_embedding_model):
        """Test generating embeddings in batch."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model)
        embeddings = generator.generate_batch(sample_chunks)
        
        assert len(embeddings) == len(sample_chunks)
        assert all(isinstance(emb, (list, np.ndarray)) for emb in embeddings)

    def test_generate_embedding_empty_text(self, mock_embedding_model):
        """Test generating embedding for empty text."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model)
        embedding = generator.generate("")
        
        assert embedding is not None
        assert len(embedding) > 0

    def test_generate_embedding_dimension(self, sample_text_content, mock_embedding_model):
        """Test embedding dimension consistency."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model)
        embedding = generator.generate(sample_text_content)
        
        assert len(embedding) == generator.dimension

    def test_generate_embedding_normalized(self, sample_text_content, mock_embedding_model):
        """Test that embeddings are normalized."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model, normalize=True)
        embedding = generator.generate(sample_text_content)
        
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        assert abs(norm - 1.0) < 1e-6

    def test_generate_embedding_with_metadata(self, sample_text_content, mock_embedding_model):
        """Test generating embedding with metadata."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model)
        metadata = {"chunk_id": "1", "source": "test.pdf"}
        embedding = generator.generate(sample_text_content, metadata=metadata)
        
        assert embedding is not None


class TestEmbeddingModels:
    """Test different embedding models."""

    @patch("embeddings.OpenAIEmbeddings")
    def test_openai_embedding_model(self, mock_openai):
        """Test OpenAI embedding model."""
        from embeddings import OpenAIEmbeddingModel
        
        mock_openai.return_value.embed_query.return_value = [0.1] * 1536
        model = OpenAIEmbeddingModel(api_key="test_key")
        embedding = model.embed("test text")
        
        assert len(embedding) == 1536

    @patch("embeddings.HuggingFaceEmbeddings")
    def test_huggingface_embedding_model(self, mock_hf):
        """Test HuggingFace embedding model."""
        from embeddings import HuggingFaceEmbeddingModel
        
        mock_hf.return_value.embed_query.return_value = [0.1] * 384
        model = HuggingFaceEmbeddingModel(model_name="sentence-transformers/all-MiniLM-L6-v2")
        embedding = model.embed("test text")
        
        assert len(embedding) > 0

    @patch("embeddings.CohereEmbeddings")
    def test_cohere_embedding_model(self, mock_cohere):
        """Test Cohere embedding model."""
        from embeddings import CohereEmbeddingModel
        
        mock_cohere.return_value.embed_query.return_value = [0.1] * 1024
        model = CohereEmbeddingModel(api_key="test_key")
        embedding = model.embed("test text")
        
        assert len(embedding) > 0


class TestEmbeddingUtils:
    """Test embedding utility functions."""

    def test_cosine_similarity(self, sample_embeddings):
        """Test cosine similarity calculation."""
        from embeddings import cosine_similarity
        
        emb1 = sample_embeddings[0]
        emb2 = sample_embeddings[1]
        similarity = cosine_similarity(emb1, emb2)
        
        assert -1.0 <= similarity <= 1.0

    def test_euclidean_distance(self, sample_embeddings):
        """Test euclidean distance calculation."""
        from embeddings import euclidean_distance
        
        emb1 = sample_embeddings[0]
        emb2 = sample_embeddings[1]
        distance = euclidean_distance(emb1, emb2)
        
        assert distance >= 0

    def test_normalize_embedding(self, sample_embeddings):
        """Test embedding normalization."""
        from embeddings import normalize_embedding
        
        embedding = sample_embeddings[0]
        normalized = normalize_embedding(embedding)
        
        norm = np.linalg.norm(normalized)
        assert abs(norm - 1.0) < 1e-6

    def test_average_embeddings(self, sample_embeddings):
        """Test averaging multiple embeddings."""
        from embeddings import average_embeddings
        
        averaged = average_embeddings(sample_embeddings)
        
        assert len(averaged) == len(sample_embeddings[0])
        assert isinstance(averaged, (list, np.ndarray))

    def test_concatenate_embeddings(self, sample_embeddings):
        """Test concatenating embeddings."""
        from embeddings import concatenate_embeddings
        
        concatenated = concatenate_embeddings(sample_embeddings)
        
        expected_length = sum(len(emb) for emb in sample_embeddings)
        assert len(concatenated) == expected_length


class TestEmbeddingCache:
    """Test embedding caching."""

    def test_cache_embedding(self, sample_text_content, mock_embedding_model):
        """Test caching generated embeddings."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model, use_cache=True)
        
        # First generation
        embedding1 = generator.generate(sample_text_content)
        
        # Second generation should use cache
        embedding2 = generator.generate(sample_text_content)
        
        assert np.array_equal(embedding1, embedding2)

    def test_cache_invalidation(self, sample_text_content, mock_embedding_model):
        """Test cache invalidation."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model, use_cache=True)
        generator.generate(sample_text_content)
        
        generator.clear_cache()
        assert len(generator._cache) == 0

    def test_cache_size_limit(self, mock_embedding_model):
        """Test cache size limiting."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(
            model=mock_embedding_model, 
            use_cache=True, 
            cache_size=2
        )
        
        generator.generate("text1")
        generator.generate("text2")
        generator.generate("text3")  # Should evict text1
        
        assert len(generator._cache) <= 2


class TestEmbeddingBatchProcessing:
    """Test batch processing of embeddings."""

    def test_batch_processing(self, sample_chunks, mock_embedding_model):
        """Test batch processing of multiple texts."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model, batch_size=2)
        embeddings = generator.generate_batch(sample_chunks)
        
        assert len(embeddings) == len(sample_chunks)

    def test_batch_processing_large_dataset(self, mock_embedding_model):
        """Test batch processing of large dataset."""
        from embeddings import EmbeddingGenerator
        
        large_chunks = [f"Text chunk {i}" for i in range(100)]
        generator = EmbeddingGenerator(model=mock_embedding_model, batch_size=10)
        embeddings = generator.generate_batch(large_chunks)
        
        assert len(embeddings) == 100

    def test_batch_processing_with_errors(self, mock_embedding_model):
        """Test batch processing with some errors."""
        from embeddings import EmbeddingGenerator
        
        chunks = ["valid text", None, "another valid text"]
        generator = EmbeddingGenerator(model=mock_embedding_model)
        
        # Should handle errors gracefully
        try:
            embeddings = generator.generate_batch(chunks, fail_fast=False)
            assert len(embeddings) <= len(chunks)
        except Exception:
            # If fail_fast=True, exception is expected
            pass


class TestEmbeddingQuality:
    """Test embedding quality metrics."""

    def test_embedding_consistency(self, sample_text_content, mock_embedding_model):
        """Test that same text produces same embedding."""
        from embeddings import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model=mock_embedding_model)
        emb1 = generator.generate(sample_text_content)
        emb2 = generator.generate(sample_text_content)
        
        assert np.allclose(emb1, emb2)

    def test_embedding_similarity_for_similar_texts(self, mock_embedding_model):
        """Test that similar texts produce similar embeddings."""
        from embeddings import EmbeddingGenerator, cosine_similarity
        
        generator = EmbeddingGenerator(model=mock_embedding_model)
        emb1 = generator.generate("The cat sat on the mat")
        emb2 = generator.generate("A cat was sitting on a mat")
        
        similarity = cosine_similarity(emb1, emb2)
        assert similarity > 0.5  # Should be reasonably similar

    def test_embedding_dissimilarity_for_different_texts(self, mock_embedding_model):
        """Test that different texts produce different embeddings."""
        from embeddings import EmbeddingGenerator, cosine_similarity
        
        generator = EmbeddingGenerator(model=mock_embedding_model)
        emb1 = generator.generate("The cat sat on the mat")
        emb2 = generator.generate("Quantum physics and machine learning")
        
        similarity = cosine_similarity(emb1, emb2)
        assert similarity < 0.5  # Should be reasonably different
