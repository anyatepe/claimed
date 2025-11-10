"""Tests for VectorStore interface using in-memory implementation."""

import pytest
from datetime import datetime
from typing import Optional
from app.services.vector_store import VectorStore


class InMemoryVectorStore(VectorStore):
    """In-memory implementation of VectorStore for testing."""
    
    def __init__(self):
        """Initialize empty in-memory store."""
        self._chunks: dict[str, dict] = {}  # doc_id -> chunk data
        self._index_created = False
    
    def upsert(self, chunks: list[dict]) -> None:
        """Insert or update chunks."""
        for chunk in chunks:
            if 'doc_id' not in chunk:
                raise ValueError("chunk must contain 'doc_id'")
            if 'embedding' not in chunk:
                raise ValueError("chunk must contain 'embedding'")
            
            doc_id = chunk['doc_id']
            # Store chunk with all metadata
            self._chunks[doc_id] = chunk.copy()
    
    def similarity_search(
        self, 
        embedding: list[float], 
        k: int, 
        filters: Optional[dict] = None
    ) -> list[dict]:
        """Search using cosine similarity (simplified)."""
        if not self._index_created:
            raise RuntimeError("Index not created. Call create_index_if_needed() first.")
        
        results = []
        
        # Filter chunks by metadata if filters provided
        filtered_chunks = list(self._chunks.values())
        if filters:
            for chunk in list(filtered_chunks):
                # Check each filter condition
                for key, value in filters.items():
                    if key not in chunk:
                        filtered_chunks.remove(chunk)
                        break
                    elif isinstance(value, list):
                        # For tags and other list fields
                        if not any(tag in chunk.get(key, []) for tag in value):
                            if chunk in filtered_chunks:
                                filtered_chunks.remove(chunk)
                            break
                    elif chunk.get(key) != value:
                        if chunk in filtered_chunks:
                            filtered_chunks.remove(chunk)
                        break
        
        # Simple cosine similarity calculation
        for chunk in filtered_chunks:
            chunk_embedding = chunk['embedding']
            if len(chunk_embedding) != len(embedding):
                continue
            
            # Cosine similarity: dot product / (norm1 * norm2)
            dot_product = sum(a * b for a, b in zip(embedding, chunk_embedding))
            norm1 = sum(a * a for a in embedding) ** 0.5
            norm2 = sum(a * a for a in chunk_embedding) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                score = 0.0
            else:
                score = dot_product / (norm1 * norm2)
            
            result = chunk.copy()
            result['score'] = score
            results.append(result)
        
        # Sort by score descending and return top k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:k]
    
    def create_index_if_needed(self) -> None:
        """Mark index as created."""
        self._index_created = True
    
    def delete_documents(self, doc_ids: list[str]) -> int:
        """Delete chunks by doc_id."""
        count = 0
        for doc_id in doc_ids:
            if doc_id in self._chunks:
                del self._chunks[doc_id]
                count += 1
        return count


class TestVectorStoreInterface:
    """Test suite validating VectorStore interface contract."""
    
    @pytest.fixture
    def vector_store(self):
        """Create a fresh in-memory vector store for each test."""
        store = InMemoryVectorStore()
        store.create_index_if_needed()
        return store
    
    def test_upsert_stores_chunks(self, vector_store):
        """Test that upsert stores chunks with all metadata."""
        chunks = [
            {
                'doc_id': 'doc1',
                'embedding': [0.1, 0.2, 0.3],
                'page': 1,
                'source': 'test.pdf',
                'mime': 'application/pdf',
                'created_at': '2024-01-01T00:00:00Z',
                'tenant': 'tenant1',
                'tags': ['tag1', 'tag2']
            },
            {
                'doc_id': 'doc2',
                'embedding': [0.4, 0.5, 0.6],
                'page': 2,
                'source': 'test.pdf',
                'mime': 'application/pdf',
                'created_at': datetime.now(),
                'tenant': 'tenant1',
                'tags': ['tag2', 'tag3']
            }
        ]
        
        vector_store.upsert(chunks)
        
        # Verify chunks were stored
        results = vector_store.similarity_search([0.1, 0.2, 0.3], k=10)
        assert len(results) == 2
        assert any(r['doc_id'] == 'doc1' for r in results)
        assert any(r['doc_id'] == 'doc2' for r in results)
    
    def test_upsert_requires_doc_id(self, vector_store):
        """Test that upsert requires doc_id."""
        chunks = [{'embedding': [0.1, 0.2, 0.3]}]
        
        with pytest.raises(ValueError, match="doc_id"):
            vector_store.upsert(chunks)
    
    def test_upsert_requires_embedding(self, vector_store):
        """Test that upsert requires embedding."""
        chunks = [{'doc_id': 'doc1'}]
        
        with pytest.raises(ValueError, match="embedding"):
            vector_store.upsert(chunks)
    
    def test_similarity_search_returns_top_k(self, vector_store):
        """Test that similarity_search returns top k results."""
        chunks = [
            {'doc_id': 'doc1', 'embedding': [1.0, 0.0, 0.0]},
            {'doc_id': 'doc2', 'embedding': [0.0, 1.0, 0.0]},
            {'doc_id': 'doc3', 'embedding': [0.0, 0.0, 1.0]},
            {'doc_id': 'doc4', 'embedding': [0.5, 0.5, 0.0]},
        ]
        
        vector_store.upsert(chunks)
        
        # Query similar to doc1
        results = vector_store.similarity_search([1.0, 0.0, 0.0], k=2)
        
        assert len(results) == 2
        assert results[0]['doc_id'] == 'doc1'  # Should be most similar
        assert 'score' in results[0]
        assert results[0]['score'] > 0
    
    def test_similarity_search_with_filters(self, vector_store):
        """Test that similarity_search respects metadata filters."""
        chunks = [
            {
                'doc_id': 'doc1',
                'embedding': [1.0, 0.0, 0.0],
                'tenant': 'tenant1',
                'tags': ['tag1']
            },
            {
                'doc_id': 'doc2',
                'embedding': [1.0, 0.0, 0.0],
                'tenant': 'tenant2',
                'tags': ['tag1']
            },
            {
                'doc_id': 'doc3',
                'embedding': [1.0, 0.0, 0.0],
                'tenant': 'tenant1',
                'tags': ['tag2']
            }
        ]
        
        vector_store.upsert(chunks)
        
        # Filter by tenant
        results = vector_store.similarity_search([1.0, 0.0, 0.0], k=10, filters={'tenant': 'tenant1'})
        assert len(results) == 2
        assert all(r['tenant'] == 'tenant1' for r in results)
        
        # Filter by tags
        results = vector_store.similarity_search([1.0, 0.0, 0.0], k=10, filters={'tags': ['tag1']})
        assert len(results) == 2
        assert all('tag1' in r.get('tags', []) for r in results)
        
        # Combined filters
        results = vector_store.similarity_search(
            [1.0, 0.0, 0.0], 
            k=10, 
            filters={'tenant': 'tenant1', 'tags': ['tag1']}
        )
        assert len(results) == 1
        assert results[0]['doc_id'] == 'doc1'
    
    def test_similarity_search_without_index_raises(self):
        """Test that similarity_search requires index to be created."""
        store = InMemoryVectorStore()
        store.upsert([{'doc_id': 'doc1', 'embedding': [0.1, 0.2, 0.3]}])
        
        with pytest.raises(RuntimeError, match="Index not created"):
            store.similarity_search([0.1, 0.2, 0.3], k=1)
    
    def test_create_index_if_needed_is_idempotent(self, vector_store):
        """Test that create_index_if_needed can be called multiple times."""
        vector_store.create_index_if_needed()
        vector_store.create_index_if_needed()  # Should not raise
        
        # Should still work
        vector_store.upsert([{'doc_id': 'doc1', 'embedding': [0.1, 0.2, 0.3]}])
        results = vector_store.similarity_search([0.1, 0.2, 0.3], k=1)
        assert len(results) == 1
    
    def test_delete_documents_removes_chunks(self, vector_store):
        """Test that delete_documents removes chunks by doc_id."""
        chunks = [
            {'doc_id': 'doc1', 'embedding': [0.1, 0.2, 0.3]},
            {'doc_id': 'doc2', 'embedding': [0.4, 0.5, 0.6]},
            {'doc_id': 'doc3', 'embedding': [0.7, 0.8, 0.9]},
        ]
        
        vector_store.upsert(chunks)
        
        # Delete one document
        deleted_count = vector_store.delete_documents(['doc2'])
        assert deleted_count == 1
        
        # Verify it's gone
        results = vector_store.similarity_search([0.1, 0.2, 0.3], k=10)
        assert len(results) == 2
        assert not any(r['doc_id'] == 'doc2' for r in results)
    
    def test_delete_documents_returns_count(self, vector_store):
        """Test that delete_documents returns correct count."""
        chunks = [
            {'doc_id': 'doc1', 'embedding': [0.1, 0.2, 0.3]},
            {'doc_id': 'doc2', 'embedding': [0.4, 0.5, 0.6]},
        ]
        
        vector_store.upsert(chunks)
        
        # Delete existing and non-existing
        deleted_count = vector_store.delete_documents(['doc1', 'doc3'])
        assert deleted_count == 1
        
        # Delete non-existing
        deleted_count = vector_store.delete_documents(['doc99'])
        assert deleted_count == 0
    
    def test_metadata_fields_preserved(self, vector_store):
        """Test that all metadata fields are preserved through operations."""
        chunk = {
            'doc_id': 'doc1',
            'embedding': [0.1, 0.2, 0.3],
            'page': 42,
            'source': 'document.pdf',
            'mime': 'application/pdf',
            'created_at': '2024-01-15T10:30:00Z',
            'tenant': 'acme-corp',
            'tags': ['important', 'reviewed', 'final']
        }
        
        vector_store.upsert([chunk])
        
        results = vector_store.similarity_search([0.1, 0.2, 0.3], k=1)
        assert len(results) == 1
        
        result = results[0]
        assert result['doc_id'] == 'doc1'
        assert result['page'] == 42
        assert result['source'] == 'document.pdf'
        assert result['mime'] == 'application/pdf'
        assert result['created_at'] == '2024-01-15T10:30:00Z'
        assert result['tenant'] == 'acme-corp'
        assert result['tags'] == ['important', 'reviewed', 'final']
        assert 'score' in result
    
    def test_upsert_updates_existing_chunks(self, vector_store):
        """Test that upsert updates existing chunks with same doc_id."""
        chunk1 = {
            'doc_id': 'doc1',
            'embedding': [0.1, 0.2, 0.3],
            'page': 1,
            'tags': ['old']
        }
        
        chunk2 = {
            'doc_id': 'doc1',
            'embedding': [0.9, 0.8, 0.7],
            'page': 2,
            'tags': ['new']
        }
        
        vector_store.upsert([chunk1])
        vector_store.upsert([chunk2])
        
        results = vector_store.similarity_search([0.9, 0.8, 0.7], k=1)
        assert len(results) == 1
        assert results[0]['page'] == 2
        assert results[0]['tags'] == ['new']
