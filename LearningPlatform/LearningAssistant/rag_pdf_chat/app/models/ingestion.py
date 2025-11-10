"""Ingestion models."""
from pydantic import BaseModel, Field


class IngestionResponse(BaseModel):
    """Ingestion response model."""
    document_id: str = Field(..., description="Document identifier")
    pages_ingested: int = Field(..., description="Number of pages ingested")
    status: str = Field(..., description="Ingestion status")
