"""Data models for the retriever service."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ContextChunk:
    """Represents a chunk of context retrieved from the vector store."""
    text: str
    doc_id: str
    page: Optional[int] = None
    score: float = 0.0
    citation_id: Optional[str] = None
