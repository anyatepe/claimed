"""Tests for PineconeStore adapter."""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from typing import List, Dict, Any

from adapters.pinecone_store import PineconeStore
from adapters.base import VectorStore


class MockEmbeddingModel:
    """Mock embedding model for testing."""
    def __init__(self, dimension: int = 384):
        self.dimension = dimension


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone client."""
    with patch('adapters.pinecone_store.Pinecone') as mock_pc_class:
        mock_pc_instance = MagicMock()
        mock_pc_class.return_value = mock_pc_instance
        
        # Mock list_indexes
        mock_index_list = MagicMock()
        mock_index_list.list_indexes.return_value = []
        mock_pc_instance.list_indexes.return_value = []
        
        # Mock create_index
        mock_pc_instance.create_index = MagicMock()
        
        # Mock Index
        mock_index = MagicMock()
        mock_pc_instance.Index.return_value = mock_index
        
        yield {
            'client': mock_pc_instance,
            'index': mock_index,
            'class': mock_pc_class,
        }


@pytest.fixture
def embedding_model():
    """Create a mock embedding model."""
    return MockEmbeddingModel(dimension=384)


class TestPineconeStore:
    """Test suite for PineconeStore."""
    
    def test_inherits_from_vector_store(self, mock_pinecone, embedding_model):
        """Test that PineconeStore inherits from VectorStore."""
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        assert isinstance(store, VectorStore)
    
    def test_initialization_creates_index_if_missing(
        self, mock_pinecone, embedding_model
    ):
        """Test that index is created if it doesn't exist."""
        mock_pc = mock_pinecone['client']
        mock_pc.list_indexes.return_value = []
        
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        
        # Verify Pinecone client was initialized
        mock_pinecone['class'].assert_called_once_with(api_key="test-key")
        
        # Verify create_index was called with correct parameters
        mock_pc.create_index.assert_called_once()
        call_args = mock_pc.create_index.call_args
        
        assert call_args.kwargs['name'] == "test-index"
        assert call_args.kwargs['dimension'] == 384
        assert call_args.kwargs['metric'] == "cosine"
        
        # Verify Index was retrieved
        mock_pc.Index.assert_called_once_with("test-index")
    
    def test_initialization_skips_creation_if_index_exists(
        self, mock_pinecone, embedding_model
    ):
        """Test that index creation is skipped if index already exists."""
        mock_pc = mock_pinecone['client']
        
        # Mock existing index
        mock_existing_index = MagicMock()
        mock_existing_index.name = "test-index"
        mock_pc.list_indexes.return_value = [mock_existing_index]
        
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        
        # Verify create_index was NOT called
        mock_pc.create_index.assert_not_called()
        
        # Verify Index was still retrieved
        mock_pc.Index.assert_called_once_with("test-index")
    
    def test_uses_tenant_id_as_namespace(
        self, mock_pinecone, embedding_model
    ):
        """Test that tenant_id is used as namespace."""
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
            tenant_id="tenant-123",
        )
        
        assert store.namespace == "tenant-123"
        assert store.tenant_id == "tenant-123"
    
    def test_uses_default_namespace_when_no_tenant_id(
        self, mock_pinecone, embedding_model
    ):
        """Test that default namespace is used when no tenant_id provided."""
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        
        assert store.namespace == "default"
        assert store.tenant_id is None
    
    def test_upsert_without_metadata(
        self, mock_pinecone, embedding_model
    ):
        """Test upsert without metadata."""
        mock_index = mock_pinecone['index']
        
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        
        vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        ids = ["id1", "id2"]
        
        store.upsert(vectors=vectors, ids=ids)
        
        # Verify upsert was called with correct payload shape
        mock_index.upsert.assert_called_once()
        call_args = mock_index.upsert.call_args
        
        assert 'vectors' in call_args.kwargs
        assert 'namespace' in call_args.kwargs
        assert call_args.kwargs['namespace'] == "default"
        
        vectors_payload = call_args.kwargs['vectors']
        assert len(vectors_payload) == 2
        assert vectors_payload[0]['id'] == "id1"
        assert vectors_payload[0]['values'] == [0.1, 0.2, 0.3]
        assert 'metadata' not in vectors_payload[0]
        
        assert vectors_payload[1]['id'] == "id2"
        assert vectors_payload[1]['values'] == [0.4, 0.5, 0.6]
    
    def test_upsert_with_metadata(
        self, mock_pinecone, embedding_model
    ):
        """Test upsert with metadata."""
        mock_index = mock_pinecone['index']
        
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
            tenant_id="tenant-123",
        )
        
        vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        ids = ["id1", "id2"]
        metadata = [
            {"category": "A", "score": 0.9},
            {"category": "B", "score": 0.8},
        ]
        
        store.upsert(vectors=vectors, ids=ids, metadata=metadata)
        
        # Verify upsert was called with correct payload shape including metadata
        mock_index.upsert.assert_called_once()
        call_args = mock_index.upsert.call_args
        
        vectors_payload = call_args.kwargs['vectors']
        assert len(vectors_payload) == 2
        assert vectors_payload[0]['id'] == "id1"
        assert vectors_payload[0]['values'] == [0.1, 0.2, 0.3]
        assert vectors_payload[0]['metadata'] == {"category": "A", "score": 0.9}
        
        assert vectors_payload[1]['id'] == "id2"
        assert vectors_payload[1]['values'] == [0.4, 0.5, 0.6]
        assert vectors_payload[1]['metadata'] == {"category": "B", "score": 0.8}
        
        # Verify namespace is tenant-specific
        assert call_args.kwargs['namespace'] == "tenant-123"
    
    def test_upsert_batch_processing(
        self, mock_pinecone, embedding_model
    ):
        """Test that upsert processes vectors in batches."""
        mock_index = mock_pinecone['index']
        
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        
        # Create 250 vectors to test batching (batch size is 100)
        vectors = [[0.1] * 384 for _ in range(250)]
        ids = [f"id{i}" for i in range(250)]
        
        store.upsert(vectors=vectors, ids=ids)
        
        # Verify upsert was called 3 times (100 + 100 + 50)
        assert mock_index.upsert.call_count == 3
        
        # Verify batch sizes
        calls = mock_index.upsert.call_args_list
        assert len(calls[0].kwargs['vectors']) == 100
        assert len(calls[1].kwargs['vectors']) == 100
        assert len(calls[2].kwargs['vectors']) == 50
    
    def test_upsert_validation_errors(
        self, mock_pinecone, embedding_model
    ):
        """Test upsert validation for mismatched lengths."""
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        
        # Test mismatched vectors and ids
        with pytest.raises(ValueError, match="Number of vectors must match"):
            store.upsert(vectors=[[0.1, 0.2]], ids=["id1", "id2"])
        
        # Test mismatched vectors and metadata
        with pytest.raises(ValueError, match="Number of metadata entries"):
            store.upsert(
                vectors=[[0.1, 0.2], [0.3, 0.4]],
                ids=["id1", "id2"],
                metadata=[{"key": "value"}],
            )
    
    def test_similarity_search_without_filter(
        self, mock_pinecone, embedding_model
    ):
        """Test similarity_search without metadata filter."""
        mock_index = mock_pinecone['index']
        
        # Mock query results
        mock_results = MagicMock()
        mock_match1 = MagicMock()
        mock_match1.id = "id1"
        mock_match1.score = 0.95
        mock_match1.metadata = {"category": "A"}
        
        mock_match2 = MagicMock()
        mock_match2.id = "id2"
        mock_match2.score = 0.85
        mock_match2.metadata = {"category": "B"}
        
        mock_results.matches = [mock_match1, mock_match2]
        mock_index.query.return_value = mock_results
        
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        
        query_vector = [0.1, 0.2, 0.3]
        results = store.similarity_search(query_vector, top_k=10)
        
        # Verify query was called correctly
        mock_index.query.assert_called_once_with(
            vector=query_vector,
            top_k=10,
            namespace="default",
            include_metadata=True,
        )
        
        # Verify results format
        assert len(results) == 2
        assert results[0]['id'] == "id1"
        assert results[0]['score'] == 0.95
        assert results[0]['metadata'] == {"category": "A"}
        
        assert results[1]['id'] == "id2"
        assert results[1]['score'] == 0.85
        assert results[1]['metadata'] == {"category": "B"}
    
    def test_similarity_search_with_filter(
        self, mock_pinecone, embedding_model
    ):
        """Test similarity_search with metadata filter."""
        mock_index = mock_pinecone['index']
        
        # Mock query results
        mock_results = MagicMock()
        mock_match = MagicMock()
        mock_match.id = "id1"
        mock_match.score = 0.95
        mock_match.metadata = {"category": "A", "status": "active"}
        
        mock_results.matches = [mock_match]
        mock_index.query.return_value = mock_results
        
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
            tenant_id="tenant-123",
        )
        
        query_vector = [0.1, 0.2, 0.3]
        filter_dict = {"category": {"$eq": "A"}}
        results = store.similarity_search(
            query_vector, top_k=5, filter=filter_dict
        )
        
        # Verify query was called with filter
        mock_index.query.assert_called_once_with(
            vector=query_vector,
            top_k=5,
            namespace="tenant-123",
            include_metadata=True,
            filter=filter_dict,
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]['id'] == "id1"
        assert results[0]['score'] == 0.95
    
    def test_similarity_search_with_empty_metadata(
        self, mock_pinecone, embedding_model
    ):
        """Test similarity_search handles empty metadata gracefully."""
        mock_index = mock_pinecone['index']
        
        # Mock query results with None metadata
        mock_results = MagicMock()
        mock_match = MagicMock()
        mock_match.id = "id1"
        mock_match.score = 0.95
        mock_match.metadata = None
        
        mock_results.matches = [mock_match]
        mock_index.query.return_value = mock_results
        
        store = PineconeStore(
            api_key="test-key",
            index_name="test-index",
            embedding_model=embedding_model,
        )
        
        query_vector = [0.1, 0.2, 0.3]
        results = store.similarity_search(query_vector, top_k=10)
        
        assert len(results) == 1
        assert results[0]['id'] == "id1"
        assert results[0]['metadata'] == {}
    
    def test_index_name_persistence(
        self, mock_pinecone, embedding_model
    ):
        """Test that index name is correctly stored and used."""
        store = PineconeStore(
            api_key="test-key",
            index_name="my-custom-index",
            embedding_model=embedding_model,
        )
        
        assert store.index_name == "my-custom-index"
        
        # Verify Index was called with correct name
        mock_pinecone['client'].Index.assert_called_once_with("my-custom-index")
