"""
Chat API routes for querying, streaming, and retrieving chat history.
"""
from typing import Optional, Dict, List, AsyncGenerator
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

router = APIRouter()


# Request/Response Schemas
class ChatQueryRequest(BaseModel):
    """Request schema for chat query endpoint."""
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation continuity. If not provided, a new session will be created.",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    query: str = Field(
        ...,
        description="The user's query/question",
        example="What is machine learning?"
    )
    k: Optional[int] = Field(
        None,
        description="Number of top documents to retrieve for context",
        ge=1,
        le=100,
        example=5
    )
    filters: Optional[Dict] = Field(
        None,
        description="Optional filters to apply to document retrieval",
        example={"source": "wikipedia", "language": "en"}
    )

    class Config:
        schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "query": "What is machine learning?",
                "k": 5,
                "filters": {"source": "wikipedia", "language": "en"}
            }
        }


class Citation(BaseModel):
    """Citation schema for document references."""
    doc_id: str = Field(..., description="Document identifier", example="doc_12345")
    page: int = Field(..., description="Page number in the document", example=1, ge=0)
    score: float = Field(..., description="Relevance score", example=0.95, ge=0.0, le=1.0)

    class Config:
        schema_extra = {
            "example": {
                "doc_id": "doc_12345",
                "page": 1,
                "score": 0.95
            }
        }


class ChatQueryResponse(BaseModel):
    """Response schema for chat query endpoint."""
    answer: str = Field(..., description="The generated answer to the query", example="Machine learning is a subset of artificial intelligence...")
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of citations/references used in the answer"
    )
    session_id: str = Field(..., description="Session ID for this conversation", example="550e8400-e29b-41d4-a716-446655440000")

    class Config:
        schema_extra = {
            "example": {
                "answer": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
                "citations": [
                    {
                        "doc_id": "doc_12345",
                        "page": 1,
                        "score": 0.95
                    },
                    {
                        "doc_id": "doc_67890",
                        "page": 3,
                        "score": 0.87
                    }
                ],
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ChatStreamRequest(BaseModel):
    """Request schema for chat stream endpoint."""
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for conversation continuity",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    query: str = Field(..., description="The user's query/question", example="What is machine learning?")
    k: Optional[int] = Field(None, description="Number of top documents to retrieve", ge=1, le=100, example=5)
    filters: Optional[Dict] = Field(None, description="Optional filters to apply", example={"source": "wikipedia"})

    class Config:
        schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "query": "What is machine learning?",
                "k": 5,
                "filters": {"source": "wikipedia"}
            }
        }


class ChatTurn(BaseModel):
    """Schema for a single chat turn in history."""
    turn_id: str = Field(..., description="Unique identifier for this turn", example="turn_001")
    query: str = Field(..., description="The user's query", example="What is machine learning?")
    answer: str = Field(..., description="The generated answer", example="Machine learning is...")
    timestamp: str = Field(..., description="ISO timestamp of the turn", example="2024-01-15T10:30:00Z")
    citations: List[Citation] = Field(default_factory=list, description="Citations used in the answer")

    class Config:
        schema_extra = {
            "example": {
                "turn_id": "turn_001",
                "query": "What is machine learning?",
                "answer": "Machine learning is a subset of artificial intelligence...",
                "timestamp": "2024-01-15T10:30:00Z",
                "citations": [
                    {
                        "doc_id": "doc_12345",
                        "page": 1,
                        "score": 0.95
                    }
                ]
            }
        }


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history endpoint."""
    session_id: str = Field(..., description="Session ID", example="550e8400-e29b-41d4-a716-446655440000")
    turns: List[ChatTurn] = Field(default_factory=list, description="List of conversation turns")

    class Config:
        schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "turns": [
                    {
                        "turn_id": "turn_001",
                        "query": "What is machine learning?",
                        "answer": "Machine learning is a subset of artificial intelligence...",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "citations": [
                            {
                                "doc_id": "doc_12345",
                                "page": 1,
                                "score": 0.95
                            }
                        ]
                    }
                ]
            }
        }


# In-memory storage for demo purposes (replace with actual database in production)
_chat_sessions: Dict[str, List[ChatTurn]] = {}


async def _generate_answer(query: str, k: Optional[int] = None, filters: Optional[Dict] = None) -> tuple[str, List[Citation]]:
    """
    Mock function to generate an answer and citations.
    In production, this would call your actual LLM/RAG service.
    """
    # Mock implementation - replace with actual service call
    answer = f"Mock answer for query: {query}"
    citations = [
        Citation(doc_id="doc_12345", page=1, score=0.95),
        Citation(doc_id="doc_67890", page=2, score=0.87)
    ]
    return answer, citations


async def _stream_answer(query: str, k: Optional[int] = None, filters: Optional[Dict] = None) -> AsyncGenerator[str, None]:
    """
    Mock function to stream answer tokens.
    In production, this would stream from your actual LLM provider.
    
    Yields SSE-formatted events containing tokens and citations.
    """
    answer, citations = await _generate_answer(query, k, filters)
    # Simulate token streaming
    tokens = answer.split()
    for token in tokens:
        yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
    # Send citations at the end
    yield f"data: {json.dumps({'citations': [c.dict() for c in citations], 'done': True})}\n\n"


@router.post("/v1/chat/query", response_model=ChatQueryResponse, tags=["chat"])
async def chat_query(request: ChatQueryRequest):
    """
    Process a chat query and return an answer with citations.
    
    - **session_id**: Optional session ID for conversation continuity
    - **query**: The user's question or query
    - **k**: Number of top documents to retrieve (optional)
    - **filters**: Optional filters for document retrieval (optional)
    
    Returns an answer with citations and a session ID.
    """
    # Generate or use existing session ID
    session_id = request.session_id or str(uuid4())
    
    # Generate answer and citations
    answer, citations = await _generate_answer(request.query, request.k, request.filters)
    
    # Store turn in history
    if session_id not in _chat_sessions:
        _chat_sessions[session_id] = []
    
    turn = ChatTurn(
        turn_id=f"turn_{len(_chat_sessions[session_id]) + 1:03d}",
        query=request.query,
        answer=answer,
        timestamp=datetime.utcnow().isoformat() + "Z",
        citations=citations
    )
    _chat_sessions[session_id].append(turn)
    
    return ChatQueryResponse(
        answer=answer,
        citations=citations,
        session_id=session_id
    )


@router.post("/v1/chat/stream", tags=["chat"])
async def chat_stream(request: ChatStreamRequest):
    """
    Stream chat response tokens using Server-Sent Events (SSE).
    
    This endpoint streams tokens as they are generated by the LLM provider.
    Each event contains a token or metadata. The final event includes citations.
    
    - **session_id**: Optional session ID for conversation continuity
    - **query**: The user's question or query
    - **k**: Number of top documents to retrieve (optional)
    - **filters**: Optional filters for document retrieval (optional)
    
    Returns a stream of Server-Sent Events.
    """
    # Generate or use existing session ID
    session_id = request.session_id or str(uuid4())
    
    async def generate():
        # Stream tokens
        async for chunk in _stream_answer(request.query, request.k, request.filters):
            yield chunk
        
        # Store turn in history after streaming completes
        # Note: In production, you might want to reconstruct the answer from streamed tokens
        # or have the streaming function provide it. For now, we regenerate it for history.
        answer, citations = await _generate_answer(request.query, request.k, request.filters)
        if session_id not in _chat_sessions:
            _chat_sessions[session_id] = []
        
        turn = ChatTurn(
            turn_id=f"turn_{len(_chat_sessions[session_id]) + 1:03d}",
            query=request.query,
            answer=answer,
            timestamp=datetime.utcnow().isoformat() + "Z",
            citations=citations
        )
        _chat_sessions[session_id].append(turn)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/v1/chat/history/{session_id}", response_model=ChatHistoryResponse, tags=["chat"])
async def get_chat_history(session_id: str):
    """
    Retrieve chat history for a given session ID.
    
    - **session_id**: The session ID to retrieve history for
    
    Returns all conversation turns for the session.
    """
    if session_id not in _chat_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return ChatHistoryResponse(
        session_id=session_id,
        turns=_chat_sessions[session_id]
    )
