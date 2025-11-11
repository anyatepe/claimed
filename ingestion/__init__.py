"""Ingestion package for document processing pipelines."""

from .langflow_ingestion import (
    LangflowIngestionPipeline,
    ingest_with_langflow,
)

__all__ = [
    "LangflowIngestionPipeline",
    "ingest_with_langflow",
]
