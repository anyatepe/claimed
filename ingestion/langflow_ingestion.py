"""
Langflow-based ingestion pipeline.

This module provides an alternate ingestion path that uses Langflow
for parsing, chunking, and embedding documents, returning upsert-ready records.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from adapters.langflow_client import LangflowClient, run_flow

logger = logging.getLogger(__name__)


class LangflowIngestionPipeline:
    """
    Ingestion pipeline using Langflow for document processing.

    This pipeline expects a Langflow flow that accepts document inputs
    and returns structured records with text chunks and embeddings.
    """

    def __init__(
        self,
        flow_id: Optional[str] = None,
        client: Optional[LangflowClient] = None,
    ):
        """
        Initialize the Langflow ingestion pipeline.

        Args:
            flow_id: ID of the Langflow flow to use (defaults to LANGFLOW_INGESTION_FLOW_ID env var)
            client: Optional LangflowClient instance (creates new one if not provided)
        """
        self.flow_id = flow_id or os.getenv("LANGFLOW_INGESTION_FLOW_ID")
        if not self.flow_id:
            raise ValueError(
                "flow_id must be provided or LANGFLOW_INGESTION_FLOW_ID must be set"
            )
        self.client = client or LangflowClient()

    def ingest_document(
        self,
        document_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ingest a single document using Langflow pipeline.

        Args:
            document_path: Path to the document file
            metadata: Optional metadata to include with the document

        Returns:
            List of upsert-ready records, each containing:
            - text: The chunked text content
            - embedding: The embedding vector (if available)
            - metadata: Document metadata including source path
        """
        document_path = Path(document_path)
        if not document_path.exists():
            raise FileNotFoundError(f"Document not found: {document_path}")

        # Read document content
        with open(document_path, "rb") as f:
            document_content = f.read()

        # Prepare inputs for Langflow flow
        inputs = {
            "document": document_content,
            "file_path": str(document_path),
            "file_name": document_path.name,
        }

        if metadata:
            inputs["metadata"] = metadata

        logger.info(f"Ingesting document: {document_path}")

        # Run Langflow pipeline
        result = self.client.run_flow(self.flow_id, inputs)

        # Transform Langflow output to upsert-ready records
        records = self._transform_to_upsert_records(result, document_path, metadata)

        logger.info(f"Generated {len(records)} records from {document_path}")
        return records

    def ingest_documents(
        self,
        document_paths: List[Union[str, Path]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ingest multiple documents using Langflow pipeline.

        Args:
            document_paths: List of paths to document files
            metadata: Optional metadata to include with all documents

        Returns:
            List of upsert-ready records from all documents
        """
        all_records = []
        for doc_path in document_paths:
            try:
                records = self.ingest_document(doc_path, metadata)
                all_records.extend(records)
            except Exception as e:
                logger.error(f"Failed to ingest {doc_path}: {e}")
                # Continue with other documents
                continue

        return all_records

    def ingest_text(
        self,
        text: str,
        source_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ingest raw text using Langflow pipeline.

        Args:
            text: The text content to ingest
            source_id: Optional identifier for the text source
            metadata: Optional metadata to include

        Returns:
            List of upsert-ready records
        """
        inputs = {
            "text": text,
        }

        if source_id:
            inputs["source_id"] = source_id

        if metadata:
            inputs["metadata"] = metadata

        logger.info(f"Ingesting text (length: {len(text)} chars)")

        # Run Langflow pipeline
        result = self.client.run_flow(self.flow_id, inputs)

        # Transform Langflow output to upsert-ready records
        records = self._transform_to_upsert_records(result, source_id, metadata)

        logger.info(f"Generated {len(records)} records from text")
        return records

    def _transform_to_upsert_records(
        self,
        langflow_result: Dict[str, Any],
        source: Union[str, Path, None],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Transform Langflow pipeline output to upsert-ready records.

        Expected Langflow output format:
        {
            "outputs": {
                "chunks": [
                    {
                        "text": "...",
                        "embedding": [...],
                        "metadata": {...}
                    }
                ]
            }
        }

        Returns:
            List of records ready for upsert, each containing:
            - id: Unique identifier for the chunk
            - text: The chunk text
            - embedding: The embedding vector (if available)
            - metadata: Combined metadata including source information
        """
        records = []

        # Extract chunks from Langflow result
        # Handle different possible response structures
        chunks = None
        if isinstance(langflow_result, dict):
            # Try different possible output structures
            if "outputs" in langflow_result:
                outputs = langflow_result["outputs"]
                if isinstance(outputs, dict) and "chunks" in outputs:
                    chunks = outputs["chunks"]
                elif isinstance(outputs, list):
                    chunks = outputs
            elif "chunks" in langflow_result:
                chunks = langflow_result["chunks"]
            elif "data" in langflow_result:
                chunks = langflow_result["data"]
            else:
                # Assume the entire result is a list of chunks
                if isinstance(langflow_result, list):
                    chunks = langflow_result
                else:
                    # Single chunk result
                    chunks = [langflow_result]

        if not chunks:
            logger.warning("No chunks found in Langflow result, returning empty list")
            return []

        # Build base metadata
        base_metadata = {}
        if source:
            base_metadata["source"] = str(source)
        if metadata:
            base_metadata.update(metadata)

        # Transform each chunk to an upsert-ready record
        for idx, chunk in enumerate(chunks):
            record = {
                "id": chunk.get("id") or f"{source}_{idx}" if source else f"chunk_{idx}",
                "text": chunk.get("text") or chunk.get("content") or "",
            }

            # Add embedding if available
            if "embedding" in chunk:
                record["embedding"] = chunk["embedding"]
            elif "vector" in chunk:
                record["embedding"] = chunk["vector"]

            # Merge metadata
            chunk_metadata = chunk.get("metadata", {})
            record["metadata"] = {**base_metadata, **chunk_metadata}

            # Add any additional fields from chunk
            for key in ["start_index", "end_index", "chunk_index"]:
                if key in chunk:
                    record["metadata"][key] = chunk[key]

            records.append(record)

        return records


def ingest_with_langflow(
    flow_id: str,
    document_paths: Optional[List[Union[str, Path]]] = None,
    texts: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function for ingesting documents/texts with Langflow.

    Args:
        flow_id: ID of the Langflow flow to use
        document_paths: Optional list of document file paths
        texts: Optional list of text strings to ingest
        metadata: Optional metadata to include

    Returns:
        List of upsert-ready records
    """
    pipeline = LangflowIngestionPipeline(flow_id=flow_id)
    all_records = []

    if document_paths:
        all_records.extend(pipeline.ingest_documents(document_paths, metadata))

    if texts:
        for text in texts:
            records = pipeline.ingest_text(text, metadata=metadata)
            all_records.extend(records)

    return all_records
