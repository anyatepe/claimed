"""
Tests for retrieval functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np


class TestRetriever:
    """Test basic retriever functionality."""

    def test_retrieve_single_query(self, mock_vector_store, sample_embeddings):
        """Test retrieving documents for a single query."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(query_embedding, top_k=5)
        
        assert isinstance(results, list)
        assert len(results) <= 5

    def test_retrieve_with_metadata_filter(self, mock_vector_store, sample_embeddings):
        """Test retrieving with metadata filter."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        filter_dict = {"source": "test.pdf"}
        
        results = retriever.retrieve(
            query_embedding, 
            top_k=5, 
            filter=filter_dict
        )
        
        assert isinstance(results, list)

    def test_retrieve_empty_results(self, mock_vector_store, sample_embeddings):
        """Test retrieving when no results are found."""
        from retriever import Retriever
        
        mock_vector_store.search.return_value = []
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(query_embedding, top_k=5)
        
        assert results == []

    def test_retrieve_with_score_threshold(self, mock_vector_store, sample_embeddings):
        """Test retrieving with score threshold."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(
            query_embedding, 
            top_k=5, 
            score_threshold=0.7
        )
        
        assert isinstance(results, list)
        if results:
            assert all(r.get("score", 0) >= 0.7 for r in results)


class TestHybridRetriever:
    """Test hybrid retrieval (vector + keyword)."""

    def test_hybrid_retrieve(self, mock_vector_store, sample_text_content):
        """Test hybrid retrieval combining vector and keyword search."""
        from retriever import HybridRetriever
        
        retriever = HybridRetriever(vector_store=mock_vector_store)
        query = "test query"
        query_embedding = [0.1, 0.2, 0.3]
        
        results = retriever.retrieve(query, query_embedding, top_k=5)
        
        assert isinstance(results, list)

    def test_hybrid_retrieve_weighted(self, mock_vector_store, sample_text_content):
        """Test hybrid retrieval with custom weights."""
        from retriever import HybridRetriever
        
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            vector_weight=0.7,
            keyword_weight=0.3
        )
        query = "test query"
        query_embedding = [0.1, 0.2, 0.3]
        
        results = retriever.retrieve(query, query_embedding, top_k=5)
        
        assert isinstance(results, list)


class TestReranking:
    """Test result reranking."""

    def test_rerank_results(self, mock_vector_store, sample_embeddings):
        """Test reranking retrieved results."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store, rerank=True)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(query_embedding, top_k=10)
        
        assert isinstance(results, list)

    def test_rerank_with_cross_encoder(self, mock_vector_store, sample_embeddings):
        """Test reranking with cross-encoder model."""
        from retriever import Retriever
        
        retriever = Retriever(
            vector_store=mock_vector_store,
            rerank=True,
            reranker_model="cross-encoder"
        )
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(query_embedding, top_k=10)
        
        assert isinstance(results, list)


class TestRetrievalStrategies:
    """Test different retrieval strategies."""

    def test_mmr_retrieval(self, mock_vector_store, sample_embeddings):
        """Test Maximum Marginal Relevance retrieval."""
        from retriever import MMRRetriever
        
        retriever = MMRRetriever(vector_store=mock_vector_store, lambda_param=0.5)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(query_embedding, top_k=5)
        
        assert isinstance(results, list)
        assert len(results) <= 5

    def test_diverse_retrieval(self, mock_vector_store, sample_embeddings):
        """Test diverse retrieval strategy."""
        from retriever import DiverseRetriever
        
        retriever = DiverseRetriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(query_embedding, top_k=5)
        
        assert isinstance(results, list)


class TestRetrievalFilters:
    """Test retrieval filtering."""

    def test_filter_by_source(self, mock_vector_store, sample_embeddings):
        """Test filtering by source."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(
            query_embedding,
            top_k=5,
            filter={"source": "test.pdf"}
        )
        
        assert isinstance(results, list)

    def test_filter_by_date_range(self, mock_vector_store, sample_embeddings):
        """Test filtering by date range."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(
            query_embedding,
            top_k=5,
            filter={
                "date_from": "2024-01-01",
                "date_to": "2024-12-31"
            }
        )
        
        assert isinstance(results, list)

    def test_filter_by_multiple_conditions(self, mock_vector_store, sample_embeddings):
        """Test filtering with multiple conditions."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(
            query_embedding,
            top_k=5,
            filter={
                "source": "test.pdf",
                "page": 1,
                "category": "documentation"
            }
        )
        
        assert isinstance(results, list)


class TestRetrievalScoring:
    """Test retrieval scoring."""

    def test_score_normalization(self, mock_vector_store, sample_embeddings):
        """Test score normalization."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(query_embedding, top_k=5, normalize_scores=True)
        
        assert isinstance(results, list)
        if results:
            scores = [r.get("score", 0) for r in results]
            assert all(0 <= score <= 1 for score in scores)

    def test_boost_by_recency(self, mock_vector_store, sample_embeddings):
        """Test boosting results by recency."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embedding = sample_embeddings[0]
        
        results = retriever.retrieve(
            query_embedding,
            top_k=5,
            boost_recency=True
        )
        
        assert isinstance(results, list)


class TestRetrievalUtils:
    """Test retrieval utility functions."""

    def test_format_results(self, mock_vector_store, sample_embeddings):
        """Test formatting retrieval results."""
        from retriever import format_retrieval_results
        
        raw_results = [
            {"id": "1", "text": "chunk1", "score": 0.9},
            {"id": "2", "text": "chunk2", "score": 0.8},
        ]
        
        formatted = format_retrieval_results(raw_results)
        
        assert isinstance(formatted, list)
        assert len(formatted) == len(raw_results)

    def test_merge_results(self):
        """Test merging multiple result sets."""
        from retriever import merge_retrieval_results
        
        results1 = [{"id": "1", "score": 0.9}]
        results2 = [{"id": "2", "score": 0.8}]
        
        merged = merge_retrieval_results([results1, results2])
        
        assert len(merged) == 2

    def test_deduplicate_results(self):
        """Test deduplicating retrieval results."""
        from retriever import deduplicate_results
        
        results = [
            {"id": "1", "text": "chunk1", "score": 0.9},
            {"id": "1", "text": "chunk1", "score": 0.85},
            {"id": "2", "text": "chunk2", "score": 0.8},
        ]
        
        deduplicated = deduplicate_results(results)
        
        assert len(deduplicated) == 2
        assert deduplicated[0]["id"] == "1"
        assert deduplicated[0]["score"] == 0.9  # Higher score kept

    def test_combine_metadata(self):
        """Test combining metadata from results."""
        from retriever import combine_metadata
        
        results = [
            {"id": "1", "metadata": {"source": "doc1.pdf", "page": 1}},
            {"id": "2", "metadata": {"source": "doc2.pdf", "page": 2}},
        ]
        
        combined = combine_metadata(results)
        
        assert "sources" in combined or "metadata" in combined


class TestRetrievalPerformance:
    """Test retrieval performance."""

    def test_batch_retrieval(self, mock_vector_store, sample_embeddings):
        """Test batch retrieval of multiple queries."""
        from retriever import Retriever
        
        retriever = Retriever(vector_store=mock_vector_store)
        query_embeddings = sample_embeddings
        
        results = retriever.retrieve_batch(query_embeddings, top_k=5)
        
        assert isinstance(results, list)
        assert len(results) == len(query_embeddings)

    def test_async_retrieval(self, mock_vector_store, sample_embeddings):
        """Test asynchronous retrieval."""
        import asyncio
        from retriever import AsyncRetriever
        
        async def test_async():
            retriever = AsyncRetriever(vector_store=mock_vector_store)
            query_embedding = sample_embeddings[0]
            
            results = await retriever.retrieve(query_embedding, top_k=5)
            return results
        
        results = asyncio.run(test_async())
        assert isinstance(results, list)
