"""Integration tests for job lifecycle."""
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.models.job import JobType, JobStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_create_upsert_job(client):
    """Test creating an upsert job."""
    response = client.post(
        "/v1/jobs",
        json={
            "type": "upsert",
            "payload": {
                "document_id": "test_doc_1",
                "content": "Test document content",
                "metadata": {"source": "test"},
            },
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["type"] == "upsert"
    assert data["status"] == "pending"
    assert "created_at" in data
    
    return data["id"]


def test_create_chat_job(client):
    """Test creating a chat job."""
    response = client.post(
        "/v1/jobs",
        json={
            "type": "chat",
            "payload": {
                "query": "What is machine learning?",
                "max_hops": 2,
                "temperature": 0.7,
            },
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["type"] == "chat"
    assert data["status"] == "pending"
    
    return data["id"]


def test_get_job_status(client):
    """Test getting job status."""
    # Create a job
    create_response = client.post(
        "/v1/jobs",
        json={
            "type": "upsert",
            "payload": {
                "document_id": "test_doc_2",
                "content": "Test content",
            },
        },
    )
    job_id = create_response.json()["id"]
    
    # Get job status
    response = client.get(f"/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["type"] == "upsert"
    assert data["status"] in ["pending", "started", "success", "failure"]


def test_get_nonexistent_job(client):
    """Test getting a non-existent job."""
    response = client.get("/v1/jobs/nonexistent-id")
    assert response.status_code == 404


def test_job_lifecycle_upsert(client):
    """Test complete job lifecycle for upsert job."""
    # Create job
    create_response = client.post(
        "/v1/jobs",
        json={
            "type": "upsert",
            "payload": {
                "document_id": "lifecycle_test",
                "content": "Lifecycle test content",
                "metadata": {"test": True},
            },
        },
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]
    
    # Wait a bit for task to process (in real scenario, use proper async waiting)
    time.sleep(3)
    
    # Check status
    status_response = client.get(f"/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    # Job should be in progress or completed
    assert status_data["status"] in ["pending", "started", "success", "failure"]
    
    # If successful, check result
    if status_data["status"] == "success":
        assert status_data["result_url"] is not None
        
        result_response = client.get(status_data["result_url"])
        assert result_response.status_code == 200
        result_data = result_response.json()
        assert "document_id" in result_data
        assert result_data["document_id"] == "lifecycle_test"


def test_job_lifecycle_chat(client):
    """Test complete job lifecycle for chat job."""
    # Create job
    create_response = client.post(
        "/v1/jobs",
        json={
            "type": "chat",
            "payload": {
                "query": "Explain quantum computing",
                "max_hops": 2,
            },
        },
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]
    
    # Wait for processing
    time.sleep(3)
    
    # Check status
    status_response = client.get(f"/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    assert status_data["status"] in ["pending", "started", "success", "failure"]
    
    # If successful, check result
    if status_data["status"] == "success":
        assert status_data["result_url"] is not None
        
        result_response = client.get(status_data["result_url"])
        assert result_response.status_code == 200
        result_data = result_response.json()
        assert "query" in result_data
        assert "response" in result_data
        assert "retrieval_hops" in result_data


def test_job_with_webhook(client):
    """Test job creation with webhook URL."""
    # Note: In a real test, you'd set up a mock webhook server
    response = client.post(
        "/v1/jobs",
        json={
            "type": "upsert",
            "payload": {
                "document_id": "webhook_test",
                "content": "Test",
            },
            "webhook_url": "https://example.com/webhook",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None


def test_invalid_job_type(client):
    """Test creating job with invalid type."""
    response = client.post(
        "/v1/jobs",
        json={
            "type": "invalid_type",
            "payload": {},
        },
    )
    
    assert response.status_code == 422  # Validation error


def test_missing_payload(client):
    """Test creating job without payload."""
    response = client.post(
        "/v1/jobs",
        json={
            "type": "upsert",
        },
    )
    
    assert response.status_code == 422  # Validation error
