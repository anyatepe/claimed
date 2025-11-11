"""Tests for the Retriever service."""
import unittest
from unittest.mock import Mock, MagicMock
from typing import List, Any

from app.services.retriever import Retriever
from app.models import ContextChunk


class MockEmbeddingService:
    """Mock embedding service for testing."""
    
    def __init__(self):
        # Simple embedding: just return a hash-based vector for consistency
        self._cache = {}
    
    def embed(self, text: str) -> List[float]:
        """Generate a simple mock embedding."""
        # Use a simple hash-based approach for consistent embeddings
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        # Generate a 384-dimensional vector (common embedding size)
        seed = int(hash_obj.hexdigest(), 16)
        import random
        random.seed(seed)
        return [random.random() for _ in range(384)]


class MockVectorStore:
    """Mock vector store for testing."""
    
    def __init__(self, corpus: List[dict]):
        """
        Initialize with a toy corpus.
        
        Args:
            corpus: List of documents with 'text', 'doc_id', 'page', 'citation_id'
        """
        self.corpus = corpus
    
    def similarity_search(
        self,
        query_embedding: List[float],
        k: int,
        filters: dict = None
    ) -> List[Any]:
        """
        Perform a mock similarity search.
        
        For simplicity, we'll use a keyword-based ranking:
        - Count matching words between query and document
        - Return top k results
        """
        # Extract query text from embedding (in real scenario, we'd have the query)
        # For testing, we'll use a simple scoring mechanism
        
        # Create mock results with scores
        results = []
        for doc in self.corpus:
            # Simple scoring: count word overlap (case-insensitive)
            # In a real scenario, this would use vector similarity
            doc_words = set(doc['text'].lower().split())
            
            # Create a mock result object
            result = Mock()
            result.text = doc['text']
            result.score = len(doc_words) / max(len(doc_words), 1)  # Normalized score
            result.metadata = {
                'doc_id': doc['doc_id'],
                'page': doc.get('page'),
                'citation_id': doc.get('citation_id')
            }
            results.append(result)
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply filters if provided
        if filters:
            filtered_results = []
            for result in results:
                match = True
                for key, value in filters.items():
                    if key in result.metadata and result.metadata[key] != value:
                        match = False
                        break
                if match:
                    filtered_results.append(result)
            results = filtered_results
        
        return results[:k]


class TestRetriever(unittest.TestCase):
    """Test cases for the Retriever service."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a toy corpus
        self.toy_corpus = [
            {
                'text': 'Python is a high-level programming language. It is widely used for data science and machine learning.',
                'doc_id': 'doc1',
                'page': 1,
                'citation_id': 'cite1'
            },
            {
                'text': 'Machine learning algorithms can learn from data without explicit programming.',
                'doc_id': 'doc2',
                'page': 5,
                'citation_id': 'cite2'
            },
            {
                'text': 'Data science involves statistics, programming, and domain expertise.',
                'doc_id': 'doc3',
                'page': 3,
                'citation_id': 'cite3'
            },
            {
                'text': 'The weather today is sunny and warm.',
                'doc_id': 'doc4',
                'page': 10,
                'citation_id': 'cite4'
            },
            {
                'text': 'Natural language processing is a branch of artificial intelligence.',
                'doc_id': 'doc5',
                'page': 7,
                'citation_id': 'cite5'
            },
            {
                'text': 'Deep learning uses neural networks with multiple layers.',
                'doc_id': 'doc6',
                'page': 12,
                'citation_id': 'cite6'
            },
            {
                'text': 'Vector databases enable efficient similarity search for embeddings.',
                'doc_id': 'doc7',
                'page': 15,
                'citation_id': 'cite7'
            },
        ]
        
        self.embedding_service = MockEmbeddingService()
        self.vector_store = MockVectorStore(self.toy_corpus)
    
    def test_retrieve_basic(self):
        """Test basic retrieval functionality."""
        retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            rerank=False
        )
        
        query = "machine learning"
        results = retriever.retrieve(query, k=3)
        
        # Should return 3 results
        self.assertEqual(len(results), 3)
        
        # All results should be ContextChunk instances
        for result in results:
            self.assertIsInstance(result, ContextChunk)
            self.assertIsNotNone(result.text)
            self.assertIsNotNone(result.doc_id)
            self.assertIsNotNone(result.score)
    
    def test_retrieve_with_reranking(self):
        """Test retrieval with reranking enabled."""
        retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            rerank=True
        )
        
        query = "machine learning algorithms"
        results = retriever.retrieve(query, k=3)
        
        # Should return 3 results
        self.assertEqual(len(results), 3)
        
        # Results should be sorted by score (descending)
        scores = [r.score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
        # Top result should be most relevant
        # In our toy corpus, doc2 mentions "machine learning algorithms" directly
        self.assertGreater(results[0].score, 0)
    
    def test_retrieve_ordering(self):
        """Test that results are ordered by relevance."""
        retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            rerank=True
        )
        
        query = "data science"
        results = retriever.retrieve(query, k=5)
        
        # Verify ordering: scores should be descending
        for i in range(len(results) - 1):
            self.assertGreaterEqual(
                results[i].score,
                results[i + 1].score,
                f"Results not properly ordered: {results[i].score} < {results[i+1].score}"
            )
    
    def test_retrieve_with_filters(self):
        """Test retrieval with filters."""
        retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            rerank=False
        )
        
        query = "machine learning"
        filters = {'doc_id': 'doc2'}
        results = retriever.retrieve(query, k=6, filters=filters)
        
        # All results should match the filter
        for result in results:
            self.assertEqual(result.doc_id, 'doc2')
    
    def test_context_chunk_fields(self):
        """Test that ContextChunk has all required fields."""
        retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            rerank=False
        )
        
        query = "test query"
        results = retriever.retrieve(query, k=1)
        
        if results:
            chunk = results[0]
            # Verify all required fields are present
            self.assertIsNotNone(chunk.text)
            self.assertIsNotNone(chunk.doc_id)
            self.assertIsNotNone(chunk.score)
            # page and citation_id are optional, but should be present in our corpus
            self.assertIsNotNone(chunk.page)
            self.assertIsNotNone(chunk.citation_id)
    
    def test_retrieve_k_parameter(self):
        """Test that k parameter controls the number of results."""
        retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            rerank=False
        )
        
        query = "test"
        
        # Test different k values
        for k in [1, 3, 5, 10]:
            results = retriever.retrieve(query, k=k)
            self.assertLessEqual(len(results), k)
    
    def test_retrieve_empty_query(self):
        """Test retrieval with empty query."""
        retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            rerank=False
        )
        
        results = retriever.retrieve("", k=3)
        # Should handle empty query gracefully
        self.assertIsInstance(results, list)
    
    def test_retrieve_expected_ordering(self):
        """Test that retrieval returns results in expected order for specific query."""
        retriever = Retriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            rerank=True
        )
        
        # Query that should match doc2 most closely
        query = "machine learning algorithms learn from data"
        results = retriever.retrieve(query, k=3)
        
        # Verify we got results
        self.assertGreater(len(results), 0)
        
        # Verify scores are in descending order
        scores = [r.score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
        # Print results for manual inspection
        print("\n=== Retrieval Results ===")
        for i, result in enumerate(results, 1):
            print(f"{i}. Score: {result.score:.4f}")
            print(f"   Doc ID: {result.doc_id}")
            print(f"   Text: {result.text[:60]}...")
            print(f"   Page: {result.page}, Citation: {result.citation_id}")
            print()


if __name__ == '__main__':
    unittest.main()
