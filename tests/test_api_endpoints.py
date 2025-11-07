"""
Tests for API endpoints functionality.
"""
import pytest
import json
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_rag_pipeline():
    """Mock RAG pipeline for testing."""
    pipeline = Mock()
    pipeline.index_documents.return_value = {
        "documents_indexed": 2,
        "chunks_created": 5,
        "vectors_stored": 5,
    }
    pipeline.query.return_value = {
        "question": "Test question",
        "response": "Test response",
        "context_chunks": 3,
        "sources": ["doc1", "doc2"],
    }
    pipeline.get_stats.return_value = {
        "vectors_in_store": 10,
        "embedding_dimension": 384,
    }
    return pipeline


@pytest.fixture
def api_app(mock_rag_pipeline):
    """Fixture for API application."""
    from fastapi import FastAPI, HTTPException
    
    app = FastAPI()
    
    @app.post("/api/v1/documents/index")
    async def index_documents(request: Dict[str, Any]):
        """Index documents endpoint."""
        documents = request.get("documents", [])
        if not documents:
            raise HTTPException(status_code=400, detail="No documents provided")
        
        result = mock_rag_pipeline.index_documents(documents)
        return {"status": "success", "data": result}
    
    @app.post("/api/v1/query")
    async def query(request: Dict[str, Any]):
        """Query endpoint."""
        question = request.get("question")
        if not question:
            raise HTTPException(status_code=400, detail="No question provided")
        
        top_k = request.get("top_k", 3)
        result = mock_rag_pipeline.query(question, top_k=top_k)
        return {"status": "success", "data": result}
    
    @app.get("/api/v1/stats")
    async def get_stats():
        """Get statistics endpoint."""
        stats = mock_rag_pipeline.get_stats()
        return {"status": "success", "data": stats}
    
    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "rag-api"}
    
    return app


@pytest.fixture
def client(api_app):
    """Test client fixture."""
    return TestClient(api_app)


class TestAPIEndpoints:
    """Test suite for API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
    
    def test_index_documents_success(self, client, mock_rag_pipeline):
        """Test successful document indexing."""
        payload = {
            "documents": ["Document 1", "Document 2"]
        }
        
        response = client.post("/api/v1/documents/index", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["documents_indexed"] == 2
        
        # Verify pipeline was called
        mock_rag_pipeline.index_documents.assert_called_once()
    
    def test_index_documents_empty(self, client):
        """Test indexing with empty documents list."""
        payload = {
            "documents": []
        }
        
        response = client.post("/api/v1/documents/index", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_index_documents_missing_field(self, client):
        """Test indexing without documents field."""
        payload = {}
        
        response = client.post("/api/v1/documents/index", json=payload)
        
        assert response.status_code == 400
    
    def test_query_success(self, client, mock_rag_pipeline):
        """Test successful query."""
        payload = {
            "question": "What is the answer?",
            "top_k": 5
        }
        
        response = client.post("/api/v1/query", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "response" in data["data"]
        assert data["data"]["question"] == payload["question"]
        
        # Verify pipeline was called
        mock_rag_pipeline.query.assert_called_once_with(payload["question"], top_k=5)
    
    def test_query_default_top_k(self, client, mock_rag_pipeline):
        """Test query with default top_k."""
        payload = {
            "question": "Test question"
        }
        
        response = client.post("/api/v1/query", json=payload)
        
        assert response.status_code == 200
        # Verify default top_k was used
        mock_rag_pipeline.query.assert_called_once_with("Test question", top_k=3)
    
    def test_query_missing_question(self, client):
        """Test query without question."""
        payload = {}
        
        response = client.post("/api/v1/query", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_query_empty_question(self, client):
        """Test query with empty question."""
        payload = {
            "question": ""
        }
        
        response = client.post("/api/v1/query", json=payload)
        
        assert response.status_code == 400
    
    def test_get_stats(self, client, mock_rag_pipeline):
        """Test getting statistics."""
        response = client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "vectors_in_store" in data["data"]
        assert "embedding_dimension" in data["data"]
        
        # Verify pipeline was called
        mock_rag_pipeline.get_stats.assert_called_once()
    
    def test_index_documents_invalid_json(self, client):
        """Test indexing with invalid JSON."""
        response = client.post(
            "/api/v1/documents/index",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_query_invalid_json(self, client):
        """Test query with invalid JSON."""
        response = client.post(
            "/api/v1/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_query_response_structure(self, client):
        """Test that query response has correct structure."""
        payload = {
            "question": "Test question"
        }
        
        response = client.post("/api/v1/query", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "data" in data
        assert "question" in data["data"]
        assert "response" in data["data"]
        assert "context_chunks" in data["data"]
        assert "sources" in data["data"]
    
    def test_index_documents_response_structure(self, client):
        """Test that index response has correct structure."""
        payload = {
            "documents": ["Doc 1", "Doc 2"]
        }
        
        response = client.post("/api/v1/documents/index", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "data" in data
        assert "documents_indexed" in data["data"]
        assert "chunks_created" in data["data"]
        assert "vectors_stored" in data["data"]
    
    def test_end_to_end_api_workflow(self, client, mock_rag_pipeline):
        """Test complete API workflow."""
        # Index documents
        index_payload = {
            "documents": ["Document 1", "Document 2"]
        }
        index_response = client.post("/api/v1/documents/index", json=index_payload)
        assert index_response.status_code == 200
        
        # Query
        query_payload = {
            "question": "What is in the documents?",
            "top_k": 3
        }
        query_response = client.post("/api/v1/query", json=query_payload)
        assert query_response.status_code == 200
        
        # Get stats
        stats_response = client.get("/api/v1/stats")
        assert stats_response.status_code == 200
    
    def test_query_with_custom_top_k(self, client, mock_rag_pipeline):
        """Test query with custom top_k value."""
        payload = {
            "question": "Test question",
            "top_k": 10
        }
        
        response = client.post("/api/v1/query", json=payload)
        
        assert response.status_code == 200
        mock_rag_pipeline.query.assert_called_once_with("Test question", top_k=10)
    
    def test_index_multiple_documents(self, client, mock_rag_pipeline):
        """Test indexing multiple documents."""
        payload = {
            "documents": [f"Document {i}" for i in range(10)]
        }
        
        response = client.post("/api/v1/documents/index", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["documents_indexed"] == 10


if __name__ == "__main__":
    pytest.main([__file__])
