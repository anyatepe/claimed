"""
FastAPI application with Redis caching and idempotency support.
"""
import hashlib
import os
from typing import Optional
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uuid

from app.services.cache import CacheService
from app.services.rag_pipeline import RAGPipeline, VectorStore
from app.services.llm_service import LLMService

app = FastAPI(
    title="RAG API with Redis Caching",
    description="API endpoints with retrieval and response caching, plus idempotency support",
    version="1.0.0",
)

# Initialize services
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
cache_service = CacheService(redis_url=redis_url)

# These would be initialized properly in production
# For now, we'll use stubs
vector_store: Optional[VectorStore] = None
rag_pipeline: Optional[RAGPipeline] = None
llm_service: Optional[LLMService] = None


def get_session_id(request: Request) -> str:
    """Get or create session ID from request headers."""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        # Generate a new session ID
        session_id = str(uuid.uuid4())
    return session_id


def get_idempotency_key(request: Request) -> Optional[str]:
    """Get idempotency key from request headers."""
    return request.headers.get("Idempotency-Key")


def hash_query(query: str) -> str:
    """Generate hash for a query."""
    return hashlib.sha256(query.encode()).hexdigest()


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., description="Query text", min_length=1)
    model_version: Optional[str] = Field(None, description="Model version for caching")
    deterministic: bool = Field(True, description="Whether the prompt is deterministic")


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str = Field(..., description="Generated answer")
    cached: bool = Field(False, description="Whether the response was from cache")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key for this response")


@app.post("/v1/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    http_request: Request,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Process a query with caching and idempotency support.
    
    Headers:
    - X-Session-ID: Session identifier (optional, will be generated if not provided)
    - Idempotency-Key: Idempotency key for deterministic requests (optional)
    
    For deterministic prompts, responses are cached and idempotency headers are returned.
    """
    session_id = x_session_id or get_session_id(http_request)
    query_hash = hash_query(request.query)
    model_version = request.model_version or "default"
    
    # Generate idempotency key if not provided and request is deterministic
    if request.deterministic and not idempotency_key:
        idempotency_key = f"{session_id}:{query_hash}:{model_version}"
    
    # Check response cache for deterministic prompts
    if request.deterministic:
        cached_response = await cache_service.get_response_cache(
            session_id, query_hash, model_version
        )
        if cached_response is not None:
            response = QueryResponse(
                answer=cached_response.get("answer", ""),
                cached=True,
                idempotency_key=idempotency_key,
            )
            # Add idempotency headers
            headers = {
                "X-Cache-Hit": "true",
                "Idempotency-Key": idempotency_key or "",
            }
            return JSONResponse(
                content=response.model_dump(),
                headers=headers,
            )
    
    # Process query (stub implementation)
    # In production, this would use RAG pipeline and LLM service
    answer = f"[STUBBED] Answer for query: {request.query}"
    
    # Cache response for deterministic prompts
    if request.deterministic:
        await cache_service.set_response_cache(
            session_id,
            query_hash,
            model_version,
            {"answer": answer},
            ttl=None,  # No expiration for response cache
        )
    
    response = QueryResponse(
        answer=answer,
        cached=False,
        idempotency_key=idempotency_key,
    )
    
    # Add idempotency headers
    headers = {
        "X-Cache-Hit": "false",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    
    return JSONResponse(
        content=response.model_dump(),
        headers=headers,
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    await cache_service.close()
