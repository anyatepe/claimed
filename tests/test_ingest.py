"""
Tests for document ingestion and deletion API endpoints.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.ingest import router

# Create test app
app = FastAPI()
app.include_router(router)

client = TestClient(app)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF"""
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(pdf_content)
        tmp_file_path = tmp_file.name
    
    yield tmp_file_path
    
    # Cleanup
    if os.path.exists(tmp_file_path):
        os.unlink(tmp_file_path)


@pytest.fixture
def api_key():
    """Set up API key for testing."""
    os.environ["API_KEY"] = "test-api-key-123"
    yield "test-api-key-123"
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]


@pytest.fixture
def jwt_token():
    """Set up JWT token for testing."""
    os.environ["JWT_SECRET"] = "test-jwt-secret"
    yield "test-jwt-token"
    if "JWT_SECRET" in os.environ:
        del os.environ["JWT_SECRET"]


class TestIngestDocument:
    """Tests for POST /v1/documents endpoint."""
    
    def test_ingest_document_happy_path_with_api_key(self, sample_pdf, api_key):
        """Test successful document ingestion with API key authentication."""
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers={"X-API-Key": api_key},
            )
        
        assert response.status_code == 201
        data = response.json()
        assert "doc_id" in data
        assert "summary" in data
        assert "filename" in data
        assert data["filename"] == "test.pdf"
        assert len(data["doc_id"]) > 0
    
    def test_ingest_document_happy_path_with_jwt(self, sample_pdf, jwt_token):
        """Test successful document ingestion with JWT authentication."""
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )
        
        assert response.status_code == 201
        data = response.json()
        assert "doc_id" in data
        assert "summary" in data
    
    def test_ingest_document_with_custom_doc_id(self, sample_pdf, api_key):
        """Test document ingestion with custom doc_id."""
        custom_doc_id = "custom-doc-123"
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"doc_id": custom_doc_id},
                headers={"X-API-Key": api_key},
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["doc_id"] == custom_doc_id
    
    def test_ingest_document_with_metadata(self, sample_pdf, api_key):
        """Test document ingestion with metadata."""
        metadata = {"author": "Test Author", "category": "test"}
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"metadata": json.dumps(metadata)},
                headers={"X-API-Key": api_key},
            )
        
        assert response.status_code == 201
        data = response.json()
        assert "summary" in data
        assert "author" in data["summary"] or "metadata" in data["summary"].lower()
    
    def test_ingest_document_with_tenant(self, sample_pdf, api_key):
        """Test document ingestion with tenant."""
        tenant = "test-tenant-123"
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"tenant": tenant},
                headers={"X-API-Key": api_key},
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["tenant"] == tenant
    
    def test_ingest_document_with_all_fields(self, sample_pdf, api_key):
        """Test document ingestion with all optional fields."""
        doc_id = "test-doc-456"
        metadata = {"key": "value", "number": 42}
        tenant = "test-tenant"
        
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={
                    "doc_id": doc_id,
                    "metadata": json.dumps(metadata),
                    "tenant": tenant,
                },
                headers={"X-API-Key": api_key},
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["doc_id"] == doc_id
        assert data["tenant"] == tenant
    
    def test_ingest_document_no_auth(self, sample_pdf):
        """Test document ingestion without authentication."""
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        
        assert response.status_code == 401
    
    def test_ingest_document_invalid_api_key(self, sample_pdf):
        """Test document ingestion with invalid API key."""
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers={"X-API-Key": "invalid-key"},
            )
        
        assert response.status_code == 401
    
    def test_ingest_document_no_file(self, api_key):
        """Test document ingestion without file."""
        response = client.post(
            "/v1/documents",
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_ingest_document_invalid_metadata_json(self, sample_pdf, api_key):
        """Test document ingestion with invalid JSON metadata."""
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={"metadata": "invalid json {["},
                headers={"X-API-Key": api_key},
            )
        
        assert response.status_code == 400
        assert "Invalid JSON format" in response.json()["detail"]
    
    def test_ingest_document_empty_filename(self, api_key):
        """Test document ingestion with empty filename."""
        response = client.post(
            "/v1/documents",
            files={"file": ("", b"content", "application/pdf")},
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 400
        assert "File is required" in response.json()["detail"]


class TestDeleteDocument:
    """Tests for DELETE /v1/documents/{doc_id} endpoint."""
    
    def test_delete_document_happy_path_with_api_key(self, api_key):
        """Test successful document deletion with API key."""
        doc_id = "test-doc-123"
        response = client.delete(
            f"/v1/documents/{doc_id}",
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["doc_id"] == doc_id
        assert "deleted successfully" in data["message"]
    
    def test_delete_document_happy_path_with_jwt(self, jwt_token):
        """Test successful document deletion with JWT."""
        doc_id = "test-doc-456"
        response = client.delete(
            f"/v1/documents/{doc_id}",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["doc_id"] == doc_id
    
    def test_delete_document_with_tenant(self, api_key):
        """Test document deletion with tenant."""
        doc_id = "test-doc-789"
        tenant = "test-tenant"
        response = client.delete(
            f"/v1/documents/{doc_id}?tenant={tenant}",
            headers={"X-API-Key": api_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["doc_id"] == doc_id
    
    def test_delete_document_no_auth(self):
        """Test document deletion without authentication."""
        doc_id = "test-doc-123"
        response = client.delete(f"/v1/documents/{doc_id}")
        
        assert response.status_code == 401
    
    def test_delete_document_invalid_api_key(self):
        """Test document deletion with invalid API key."""
        doc_id = "test-doc-123"
        response = client.delete(
            f"/v1/documents/{doc_id}",
            headers={"X-API-Key": "invalid-key"},
        )
        
        assert response.status_code == 401
    
    def test_delete_document_empty_doc_id(self, api_key):
        """Test document deletion with empty doc_id."""
        response = client.delete(
            "/v1/documents/",
            headers={"X-API-Key": api_key},
        )
        
        # FastAPI will return 404 for empty path
        assert response.status_code in [404, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
