"""Chat models."""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """Chat request model."""
    query: str = Field(..., description="User query")
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str = Field(..., description="Generated answer")
    sources: List[str] = Field(default_factory=list, description="Source documents")
