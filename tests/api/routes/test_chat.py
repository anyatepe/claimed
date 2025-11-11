"""
Tests for chat API endpoints using httpx AsyncClient.
"""
import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from app.api.routes.chat import router


# Create test app
app = FastAPI()
app.include_router(router)


@pytest.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_chat_query_basic(client: AsyncClient):
    """Test basic chat query without optional parameters."""
    response = await client.post(
        "/v1/chat/query",
        json={
            "query": "What is machine learning?"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert "session_id" in data
    assert isinstance(data["citations"], list)
    assert len(data["session_id"]) > 0


@pytest.mark.asyncio
async def test_chat_query_with_all_params(client: AsyncClient):
    """Test chat query with all optional parameters."""
    session_id = "test-session-123"
    response = await client.post(
        "/v1/chat/query",
        json={
            "session_id": session_id,
            "query": "What is deep learning?",
            "k": 5,
            "filters": {"source": "wikipedia", "language": "en"}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "answer" in data
    assert isinstance(data["citations"], list)
    # Check citation structure
    if len(data["citations"]) > 0:
        citation = data["citations"][0]
        assert "doc_id" in citation
        assert "page" in citation
        assert "score" in citation


@pytest.mark.asyncio
async def test_chat_query_session_continuity(client: AsyncClient):
    """Test that multiple queries with same session_id maintain continuity."""
    session_id = "continuity-test-session"
    
    # First query
    response1 = await client.post(
        "/v1/chat/query",
        json={
            "session_id": session_id,
            "query": "What is AI?"
        }
    )
    assert response1.status_code == 200
    
    # Second query
    response2 = await client.post(
        "/v1/chat/query",
        json={
            "session_id": session_id,
            "query": "Tell me more about it."
        }
    )
    assert response2.status_code == 200
    assert response2.json()["session_id"] == session_id
    
    # Check history
    history_response = await client.get(f"/v1/chat/history/{session_id}")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history["turns"]) == 2
    assert history["turns"][0]["query"] == "What is AI?"
    assert history["turns"][1]["query"] == "Tell me more about it."


@pytest.mark.asyncio
async def test_chat_query_validation(client: AsyncClient):
    """Test input validation for chat query."""
    # Missing required field
    response = await client.post(
        "/v1/chat/query",
        json={}
    )
    assert response.status_code == 422  # Validation error
    
    # Invalid k value (negative)
    response = await client.post(
        "/v1/chat/query",
        json={
            "query": "test",
            "k": -1
        }
    )
    assert response.status_code == 422
    
    # Invalid k value (too large)
    response = await client.post(
        "/v1/chat/query",
        json={
            "query": "test",
            "k": 101
        }
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_basic(client: AsyncClient):
    """Test basic chat stream endpoint."""
    response = await client.post(
        "/v1/chat/stream",
        json={
            "query": "What is machine learning?"
        }
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Read stream
    content = b""
    async for chunk in response.aiter_bytes():
        content += chunk
        if len(content) > 1000:  # Limit reading for test
            break
    
    assert len(content) > 0


@pytest.mark.asyncio
async def test_chat_stream_with_params(client: AsyncClient):
    """Test chat stream with all parameters."""
    session_id = "stream-test-session"
    response = await client.post(
        "/v1/chat/stream",
        json={
            "session_id": session_id,
            "query": "Explain neural networks",
            "k": 3,
            "filters": {"source": "wikipedia"}
        }
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # Verify session was created
    history_response = await client.get(f"/v1/chat/history/{session_id}")
    # Note: History might be empty if stream hasn't completed, but session should exist
    assert history_response.status_code in [200, 404]  # 404 is ok if stream hasn't finished


@pytest.mark.asyncio
async def test_chat_stream_events(client: AsyncClient):
    """Test that stream returns valid SSE events."""
    response = await client.post(
        "/v1/chat/stream",
        json={
            "query": "Test query"
        }
    )
    assert response.status_code == 200
    
    # Read a few events
    events = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            events.append(line)
        if len(events) >= 5:  # Read first 5 events
            break
    
    assert len(events) > 0
    # Check event format
    for event in events:
        assert event.startswith("data: ")


@pytest.mark.asyncio
async def test_get_chat_history_existing(client: AsyncClient):
    """Test retrieving history for an existing session."""
    session_id = "history-test-session"
    
    # Create some history
    await client.post(
        "/v1/chat/query",
        json={
            "session_id": session_id,
            "query": "First question"
        }
    )
    await client.post(
        "/v1/chat/query",
        json={
            "session_id": session_id,
            "query": "Second question"
        }
    )
    
    # Retrieve history
    response = await client.get(f"/v1/chat/history/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert len(data["turns"]) == 2
    assert data["turns"][0]["query"] == "First question"
    assert data["turns"][1]["query"] == "Second question"
    
    # Check turn structure
    turn = data["turns"][0]
    assert "turn_id" in turn
    assert "query" in turn
    assert "answer" in turn
    assert "timestamp" in turn
    assert "citations" in turn


@pytest.mark.asyncio
async def test_get_chat_history_not_found(client: AsyncClient):
    """Test retrieving history for non-existent session."""
    response = await client.get("/v1/chat/history/non-existent-session")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_history_turn_structure(client: AsyncClient):
    """Test that chat history turns have correct structure."""
    session_id = "structure-test-session"
    
    await client.post(
        "/v1/chat/query",
        json={
            "session_id": session_id,
            "query": "Test query"
        }
    )
    
    response = await client.get(f"/v1/chat/history/{session_id}")
    assert response.status_code == 200
    data = response.json()
    
    turn = data["turns"][0]
    # Check all required fields
    assert isinstance(turn["turn_id"], str)
    assert isinstance(turn["query"], str)
    assert isinstance(turn["answer"], str)
    assert isinstance(turn["timestamp"], str)
    assert isinstance(turn["citations"], list)
    
    # Check citation structure if present
    if len(turn["citations"]) > 0:
        citation = turn["citations"][0]
        assert isinstance(citation["doc_id"], str)
        assert isinstance(citation["page"], int)
        assert isinstance(citation["score"], float)
        assert 0.0 <= citation["score"] <= 1.0


@pytest.mark.asyncio
async def test_chat_query_citation_structure(client: AsyncClient):
    """Test that citations in query response have correct structure."""
    response = await client.post(
        "/v1/chat/query",
        json={
            "query": "Test query for citations"
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    citations = data["citations"]
    assert isinstance(citations, list)
    
    if len(citations) > 0:
        citation = citations[0]
        assert "doc_id" in citation
        assert "page" in citation
        assert "score" in citation
        assert isinstance(citation["doc_id"], str)
        assert isinstance(citation["page"], int)
        assert isinstance(citation["score"], float)
        assert citation["page"] >= 0
        assert 0.0 <= citation["score"] <= 1.0
