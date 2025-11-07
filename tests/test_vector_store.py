"""
Tests for vector store functionality.
"""
import pytest
import numpy as np
from typing import List, Dict, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def sample_vectors():
    """Sample vectors for testing."""
    return [
        np.random.randn(384).astype(np.float32),
        np.random.randn(384).astype(np.float32),
        np.random.randn(384).astype(np.float32),
    ]


@pytest.fixture
def sample_documents():
    """Sample documents with metadata."""
    return [
        {"id": "doc1", "text": "First document", "metadata": {"source": "source1"}},
        {"id": "doc2", "text": "Second document", "metadata": {"source": "source2"}},
        {"id": "doc3", "text": "Third document", "metadata": {"source": "source1"}},
    ]


@pytest.fixture
def vector_store():
    """Fixture for vector store instance."""
    class MockVectorStore:
        def __init__(self, dimension: int = 384):
            self.dimension = dimension
            self.vectors = {}
            self.metadata = {}
            self.next_id = 0
        
        def add(self, vector: np.ndarray, document_id: str, metadata: Optional[Dict] = None) -> str:
            """Add a vector to the store."""
            if vector.shape[0] != self.dimension:
                raise ValueError(f"Vector dimension {vector.shape[0]} does not match store dimension {self.dimension}")
            
            if document_id in self.vectors:
                raise ValueError(f"Document ID {document_id} already exists")
            
            self.vectors[document_id] = vector
            self.metadata[document_id] = metadata or {}
            return document_id
        
        def add_batch(self, vectors: List[np.ndarray], document_ids: List[str], 
                     metadata_list: Optional[List[Dict]] = None) -> List[str]:
            """Add multiple vectors to the store."""
            if len(vectors) != len(document_ids):
                raise ValueError("Vectors and document_ids must have same length")
            
            if metadata_list and len(metadata_list) != len(vectors):
                raise ValueError("metadata_list must have same length as vectors")
            
            added_ids = []
            for i, (vector, doc_id) in enumerate(zip(vectors, document_ids)):
                meta = metadata_list[i] if metadata_list else None
                added_ids.append(self.add(vector, doc_id, meta))
            
            return added_ids
        
        def search(self, query_vector: np.ndarray, top_k: int = 5, 
                  filter_dict: Optional[Dict] = None) -> List[Tuple[str, float, Dict]]:
            """Search for similar vectors."""
            if query_vector.shape[0] != self.dimension:
                raise ValueError(f"Query vector dimension {query_vector.shape[0]} does not match store dimension {self.dimension}")
            
            results = []
            for doc_id, vector in self.vectors.items():
                # Apply filter if provided
                if filter_dict:
                    doc_meta = self.metadata.get(doc_id, {})
                    if not all(doc_meta.get(k) == v for k, v in filter_dict.items()):
                        continue
                
                # Calculate cosine similarity
                similarity = np.dot(query_vector, vector) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(vector)
                )
                results.append((doc_id, float(similarity), self.metadata.get(doc_id, {})))
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
        
        def get(self, document_id: str) -> Optional[Tuple[np.ndarray, Dict]]:
            """Get a vector by document ID."""
            if document_id not in self.vectors:
                return None
            return (self.vectors[document_id], self.metadata.get(document_id, {}))
        
        def delete(self, document_id: str) -> bool:
            """Delete a vector by document ID."""
            if document_id in self.vectors:
                del self.vectors[document_id]
                del self.metadata[document_id]
                return True
            return False
        
        def count(self) -> int:
            """Get total number of vectors in store."""
            return len(self.vectors)
        
        def clear(self):
            """Clear all vectors from store."""
            self.vectors.clear()
            self.metadata.clear()
    
    return MockVectorStore(dimension=384)


class TestVectorStore:
    """Test suite for vector store functionality."""
    
    def test_add_vector(self, vector_store, sample_vectors):
        """Test adding a single vector."""
        vector = sample_vectors[0]
        doc_id = vector_store.add(vector, "test_doc_1")
        
        assert doc_id == "test_doc_1"
        assert vector_store.count() == 1
    
    def test_add_vector_with_metadata(self, vector_store, sample_vectors):
        """Test adding a vector with metadata."""
        vector = sample_vectors[0]
        metadata = {"source": "test", "type": "document"}
        doc_id = vector_store.add(vector, "test_doc_1", metadata)
        
        assert doc_id == "test_doc_1"
        stored_vector, stored_metadata = vector_store.get("test_doc_1")
        assert stored_metadata == metadata
    
    def test_add_vector_wrong_dimension(self, vector_store):
        """Test adding vector with wrong dimension."""
        wrong_vector = np.random.randn(100).astype(np.float32)
        
        with pytest.raises(ValueError):
            vector_store.add(wrong_vector, "test_doc")
    
    def test_add_duplicate_id(self, vector_store, sample_vectors):
        """Test adding vector with duplicate ID."""
        vector = sample_vectors[0]
        vector_store.add(vector, "test_doc_1")
        
        with pytest.raises(ValueError):
            vector_store.add(vector, "test_doc_1")
    
    def test_add_batch(self, vector_store, sample_vectors):
        """Test adding multiple vectors."""
        doc_ids = ["doc1", "doc2", "doc3"]
        added_ids = vector_store.add_batch(sample_vectors, doc_ids)
        
        assert len(added_ids) == 3
        assert vector_store.count() == 3
        assert all(doc_id in added_ids for doc_id in doc_ids)
    
    def test_add_batch_with_metadata(self, vector_store, sample_vectors):
        """Test adding batch with metadata."""
        doc_ids = ["doc1", "doc2", "doc3"]
        metadata_list = [
            {"source": "source1"},
            {"source": "source2"},
            {"source": "source1"},
        ]
        
        added_ids = vector_store.add_batch(sample_vectors, doc_ids, metadata_list)
        assert len(added_ids) == 3
        
        for doc_id, expected_meta in zip(doc_ids, metadata_list):
            _, stored_meta = vector_store.get(doc_id)
            assert stored_meta == expected_meta
    
    def test_add_batch_mismatched_lengths(self, vector_store, sample_vectors):
        """Test batch add with mismatched lengths."""
        doc_ids = ["doc1", "doc2"]  # Only 2 IDs for 3 vectors
        
        with pytest.raises(ValueError):
            vector_store.add_batch(sample_vectors, doc_ids)
    
    def test_search_basic(self, vector_store, sample_vectors):
        """Test basic vector search."""
        # Add vectors
        doc_ids = ["doc1", "doc2", "doc3"]
        vector_store.add_batch(sample_vectors, doc_ids)
        
        # Search with first vector as query
        query = sample_vectors[0]
        results = vector_store.search(query, top_k=2)
        
        assert len(results) == 2
        assert all(isinstance(r, tuple) and len(r) == 3 for r in results)
        assert all(isinstance(r[0], str) for r in results)  # doc_id
        assert all(isinstance(r[1], float) for r in results)  # similarity
        assert all(isinstance(r[2], dict) for r in results)  # metadata
    
    def test_search_top_k(self, vector_store, sample_vectors):
        """Test search with different top_k values."""
        doc_ids = ["doc1", "doc2", "doc3"]
        vector_store.add_batch(sample_vectors, doc_ids)
        
        query = sample_vectors[0]
        
        results_1 = vector_store.search(query, top_k=1)
        assert len(results_1) == 1
        
        results_2 = vector_store.search(query, top_k=2)
        assert len(results_2) == 2
        
        results_10 = vector_store.search(query, top_k=10)
        assert len(results_10) == 3  # Only 3 vectors in store
    
    def test_search_similarity_ordering(self, vector_store, sample_vectors):
        """Test that search results are ordered by similarity."""
        doc_ids = ["doc1", "doc2", "doc3"]
        vector_store.add_batch(sample_vectors, doc_ids)
        
        query = sample_vectors[0]
        results = vector_store.search(query, top_k=3)
        
        # Check that similarities are in descending order
        similarities = [r[1] for r in results]
        assert similarities == sorted(similarities, reverse=True)
    
    def test_search_with_filter(self, vector_store, sample_vectors):
        """Test search with metadata filter."""
        doc_ids = ["doc1", "doc2", "doc3"]
        metadata_list = [
            {"source": "source1", "type": "A"},
            {"source": "source2", "type": "B"},
            {"source": "source1", "type": "A"},
        ]
        vector_store.add_batch(sample_vectors, doc_ids, metadata_list)
        
        query = sample_vectors[0]
        results = vector_store.search(query, top_k=10, filter_dict={"source": "source1"})
        
        assert len(results) == 2
        assert all(r[2]["source"] == "source1" for r in results)
    
    def test_get_existing(self, vector_store, sample_vectors):
        """Test getting an existing vector."""
        vector = sample_vectors[0]
        metadata = {"source": "test"}
        vector_store.add(vector, "test_doc", metadata)
        
        retrieved_vector, retrieved_metadata = vector_store.get("test_doc")
        
        assert retrieved_vector is not None
        np.testing.assert_array_equal(retrieved_vector, vector)
        assert retrieved_metadata == metadata
    
    def test_get_nonexistent(self, vector_store):
        """Test getting a non-existent vector."""
        result = vector_store.get("nonexistent_doc")
        assert result is None
    
    def test_delete_existing(self, vector_store, sample_vectors):
        """Test deleting an existing vector."""
        vector = sample_vectors[0]
        vector_store.add(vector, "test_doc")
        
        assert vector_store.count() == 1
        deleted = vector_store.delete("test_doc")
        
        assert deleted is True
        assert vector_store.count() == 0
        assert vector_store.get("test_doc") is None
    
    def test_delete_nonexistent(self, vector_store):
        """Test deleting a non-existent vector."""
        deleted = vector_store.delete("nonexistent_doc")
        assert deleted is False
    
    def test_count(self, vector_store, sample_vectors):
        """Test counting vectors."""
        assert vector_store.count() == 0
        
        vector_store.add(sample_vectors[0], "doc1")
        assert vector_store.count() == 1
        
        vector_store.add(sample_vectors[1], "doc2")
        assert vector_store.count() == 2
    
    def test_clear(self, vector_store, sample_vectors):
        """Test clearing all vectors."""
        doc_ids = ["doc1", "doc2", "doc3"]
        vector_store.add_batch(sample_vectors, doc_ids)
        
        assert vector_store.count() == 3
        vector_store.clear()
        
        assert vector_store.count() == 0
        assert vector_store.get("doc1") is None
    
    def test_search_empty_store(self, vector_store):
        """Test searching empty store."""
        query = np.random.randn(384).astype(np.float32)
        results = vector_store.search(query, top_k=5)
        
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__])
