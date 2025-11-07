"""
Tests for RAG (Retrieval Augmented Generation) pipeline functionality.
"""
import pytest
import numpy as np
from typing import List, Dict, Optional
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_chunker():
    """Mock chunker for testing."""
    chunker = Mock()
    chunker.chunk_text.return_value = ["chunk1", "chunk2", "chunk3"]
    chunker.chunk_documents.return_value = [
        {"document_id": 0, "chunk_id": 0, "text": "chunk1", "metadata": {}},
        {"document_id": 0, "chunk_id": 1, "text": "chunk2", "metadata": {}},
    ]
    return chunker


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for testing."""
    model = Mock()
    model.embed.return_value = np.random.randn(384).astype(np.float32)
    model.embed_batch.return_value = [
        np.random.randn(384).astype(np.float32),
        np.random.randn(384).astype(np.float32),
    ]
    model.dimension = 384
    return model


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    store = Mock()
    store.add.return_value = "doc_id_1"
    store.add_batch.return_value = ["doc_id_1", "doc_id_2"]
    store.search.return_value = [
        ("doc_id_1", 0.95, {"text": "chunk1"}),
        ("doc_id_2", 0.85, {"text": "chunk2"}),
    ]
    store.count.return_value = 2
    return store


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = Mock()
    llm.generate.return_value = "Generated response based on context."
    return llm


@pytest.fixture
def rag_pipeline(mock_chunker, mock_embedding_model, mock_vector_store, mock_llm):
    """Fixture for RAG pipeline instance."""
    class RAGPipeline:
        def __init__(self, chunker, embedding_model, vector_store, llm):
            self.chunker = chunker
            self.embedding_model = embedding_model
            self.vector_store = vector_store
            self.llm = llm
        
        def index_documents(self, documents: List[str]) -> Dict[str, int]:
            """Index documents into the vector store."""
            # Chunk documents
            chunks = self.chunker.chunk_documents(documents)
            
            # Generate embeddings
            texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedding_model.embed_batch(texts)
            
            # Add to vector store
            doc_ids = [f"chunk_{i}" for i in range(len(chunks))]
            metadata_list = [chunk["metadata"] for chunk in chunks]
            
            self.vector_store.add_batch(embeddings, doc_ids, metadata_list)
            
            return {
                "documents_indexed": len(documents),
                "chunks_created": len(chunks),
                "vectors_stored": len(embeddings),
            }
        
        def query(self, question: str, top_k: int = 3) -> Dict[str, any]:
            """Query the RAG pipeline."""
            # Generate query embedding
            query_embedding = self.embedding_model.embed(question)
            
            # Search vector store
            results = self.vector_store.search(query_embedding, top_k=top_k)
            
            # Extract context from results
            context_chunks = [result[2].get("text", "") for result in results]
            context = "\n\n".join(context_chunks)
            
            # Generate response using LLM
            prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
            response = self.llm.generate(prompt)
            
            return {
                "question": question,
                "response": response,
                "context_chunks": len(context_chunks),
                "sources": [result[0] for result in results],
            }
        
        def get_stats(self) -> Dict[str, any]:
            """Get pipeline statistics."""
            return {
                "vectors_in_store": self.vector_store.count(),
                "embedding_dimension": self.embedding_model.dimension,
            }
    
    return RAGPipeline(mock_chunker, mock_embedding_model, mock_vector_store, mock_llm)


class TestRAGPipeline:
    """Test suite for RAG pipeline functionality."""
    
    def test_index_documents(self, rag_pipeline):
        """Test indexing documents into the pipeline."""
        documents = ["Document 1", "Document 2"]
        
        result = rag_pipeline.index_documents(documents)
        
        assert isinstance(result, dict)
        assert "documents_indexed" in result
        assert "chunks_created" in result
        assert "vectors_stored" in result
        assert result["documents_indexed"] == len(documents)
        
        # Verify chunker was called
        rag_pipeline.chunker.chunk_documents.assert_called_once_with(documents)
        
        # Verify embeddings were generated
        assert rag_pipeline.embedding_model.embed_batch.called
        
        # Verify vectors were stored
        assert rag_pipeline.vector_store.add_batch.called
    
    def test_index_empty_documents(self, rag_pipeline):
        """Test indexing empty document list."""
        result = rag_pipeline.index_documents([])
        
        assert result["documents_indexed"] == 0
    
    def test_query_basic(self, rag_pipeline):
        """Test basic query functionality."""
        question = "What is the answer?"
        
        result = rag_pipeline.query(question)
        
        assert isinstance(result, dict)
        assert "question" in result
        assert "response" in result
        assert "context_chunks" in result
        assert "sources" in result
        
        assert result["question"] == question
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
        
        # Verify query embedding was generated
        rag_pipeline.embedding_model.embed.assert_called_once_with(question)
        
        # Verify vector store search was called
        assert rag_pipeline.vector_store.search.called
        
        # Verify LLM was called
        assert rag_pipeline.llm.generate.called
    
    def test_query_with_top_k(self, rag_pipeline):
        """Test query with custom top_k."""
        question = "Test question"
        
        result = rag_pipeline.query(question, top_k=5)
        
        assert result["context_chunks"] <= 5
        
        # Verify search was called with correct top_k
        call_args = rag_pipeline.vector_store.search.call_args
        assert call_args[1]["top_k"] == 5
    
    def test_query_context_included(self, rag_pipeline):
        """Test that context is included in LLM prompt."""
        question = "Test question"
        
        rag_pipeline.query(question)
        
        # Verify LLM was called with a prompt containing context
        llm_call_args = rag_pipeline.llm.generate.call_args
        prompt = llm_call_args[0][0]
        
        assert "Context:" in prompt
        assert question in prompt
    
    def test_query_sources_returned(self, rag_pipeline):
        """Test that source document IDs are returned."""
        question = "Test question"
        
        result = rag_pipeline.query(question)
        
        assert "sources" in result
        assert isinstance(result["sources"], list)
        assert len(result["sources"]) > 0
    
    def test_get_stats(self, rag_pipeline):
        """Test getting pipeline statistics."""
        stats = rag_pipeline.get_stats()
        
        assert isinstance(stats, dict)
        assert "vectors_in_store" in stats
        assert "embedding_dimension" in stats
        
        assert isinstance(stats["vectors_in_store"], int)
        assert isinstance(stats["embedding_dimension"], int)
    
    def test_end_to_end_workflow(self, rag_pipeline):
        """Test complete end-to-end workflow."""
        # Index documents
        documents = ["Document 1", "Document 2"]
        index_result = rag_pipeline.index_documents(documents)
        assert index_result["documents_indexed"] == len(documents)
        
        # Query
        question = "What is in the documents?"
        query_result = rag_pipeline.query(question)
        assert "response" in query_result
        assert len(query_result["response"]) > 0
        
        # Get stats
        stats = rag_pipeline.get_stats()
        assert stats["vectors_in_store"] >= 0
    
    def test_query_empty_store(self, rag_pipeline):
        """Test querying when vector store is empty."""
        # Mock empty store
        rag_pipeline.vector_store.search.return_value = []
        
        question = "Test question"
        result = rag_pipeline.query(question)
        
        assert result["context_chunks"] == 0
        assert result["sources"] == []
        
        # LLM should still be called (with empty context)
        assert rag_pipeline.llm.generate.called
    
    def test_index_single_document(self, rag_pipeline):
        """Test indexing a single document."""
        documents = ["Single document"]
        
        result = rag_pipeline.index_documents(documents)
        
        assert result["documents_indexed"] == 1
        assert result["chunks_created"] > 0
        assert result["vectors_stored"] > 0
    
    def test_query_multiple_times(self, rag_pipeline):
        """Test querying multiple times."""
        questions = ["Question 1", "Question 2", "Question 3"]
        
        for question in questions:
            result = rag_pipeline.query(question)
            assert "response" in result
            assert result["question"] == question
        
        # Verify embedding model was called for each question
        assert rag_pipeline.embedding_model.embed.call_count == len(questions)


if __name__ == "__main__":
    pytest.main([__file__])
