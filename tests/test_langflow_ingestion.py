"""Tests for Langflow ingestion pipeline."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from ingestion.langflow_ingestion import (
    LangflowIngestionPipeline,
    ingest_with_langflow,
)
from adapters.langflow_client import LangflowClient


class TestLangflowIngestionPipeline:
    """Test cases for LangflowIngestionPipeline."""

    def test_init_with_flow_id(self):
        """Test pipeline initialization with flow_id."""
        client = LangflowClient()
        pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=client)
        assert pipeline.flow_id == "test-flow"
        assert pipeline.client == client

    def test_init_with_env_var(self):
        """Test pipeline initialization with environment variable."""
        with patch.dict(
            os.environ, {"LANGFLOW_INGESTION_FLOW_ID": "env-flow-id"}, clear=False
        ):
            pipeline = LangflowIngestionPipeline()
            assert pipeline.flow_id == "env-flow-id"

    def test_init_without_flow_id(self):
        """Test pipeline initialization fails without flow_id."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="flow_id must be provided"):
                LangflowIngestionPipeline()

    @patch("ingestion.langflow_ingestion.LangflowClient")
    def test_ingest_document_success(self, mock_client_class):
        """Test successful document ingestion."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test document content")
            temp_path = f.name

        try:
            # Setup mock client
            mock_client = Mock()
            mock_client.run_flow.return_value = {
                "outputs": {
                    "chunks": [
                        {
                            "text": "Test document content",
                            "embedding": [0.1, 0.2, 0.3],
                            "metadata": {"chunk_index": 0},
                        }
                    ]
                }
            }
            mock_client_class.return_value = mock_client

            # Execute
            pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=mock_client)
            records = pipeline.ingest_document(temp_path, metadata={"source": "test"})

            # Verify
            assert len(records) == 1
            assert records[0]["text"] == "Test document content"
            assert records[0]["embedding"] == [0.1, 0.2, 0.3]
            assert records[0]["metadata"]["source"] == str(temp_path)
            assert records[0]["metadata"]["chunk_index"] == 0

            # Verify client was called correctly
            mock_client.run_flow.assert_called_once()
            call_args = mock_client.run_flow.call_args
            assert call_args[0][0] == "test-flow"
            assert "document" in call_args[0][1]
            assert call_args[0][1]["file_path"] == temp_path

        finally:
            os.unlink(temp_path)

    def test_ingest_document_not_found(self):
        """Test document ingestion with non-existent file."""
        pipeline = LangflowIngestionPipeline(flow_id="test-flow")
        with pytest.raises(FileNotFoundError):
            pipeline.ingest_document("/nonexistent/file.txt")

    @patch("ingestion.langflow_ingestion.LangflowClient")
    def test_ingest_documents_multiple(self, mock_client_class):
        """Test ingesting multiple documents."""
        # Create temporary files
        temp_files = []
        try:
            for i in range(2):
                f = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
                f.write(f"Document {i} content")
                temp_files.append(f.name)
                f.close()

            # Setup mock client
            mock_client = Mock()
            mock_client.run_flow.return_value = {
                "outputs": {
                    "chunks": [
                        {
                            "text": "chunk",
                            "embedding": [0.1],
                        }
                    ]
                }
            }
            mock_client_class.return_value = mock_client

            # Execute
            pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=mock_client)
            records = pipeline.ingest_documents(temp_files)

            # Verify
            assert len(records) == 2  # One chunk per document
            assert mock_client.run_flow.call_count == 2

        finally:
            for f in temp_files:
                os.unlink(f)

    @patch("ingestion.langflow_ingestion.LangflowClient")
    def test_ingest_documents_with_error(self, mock_client_class):
        """Test ingesting documents when one fails."""
        # Create temporary files
        temp_files = []
        try:
            for i in range(2):
                f = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
                f.write(f"Document {i}")
                temp_files.append(f.name)
                f.close()

            # Setup mock client to fail on second call
            mock_client = Mock()
            mock_client.run_flow.side_effect = [
                {"outputs": {"chunks": [{"text": "chunk1"}]}},
                Exception("Processing error"),
            ]
            mock_client_class.return_value = mock_client

            # Execute
            pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=mock_client)
            records = pipeline.ingest_documents(temp_files)

            # Verify - should have records from first document only
            assert len(records) == 1

        finally:
            for f in temp_files:
                os.unlink(f)

    @patch("ingestion.langflow_ingestion.LangflowClient")
    def test_ingest_text(self, mock_client_class):
        """Test text ingestion."""
        mock_client = Mock()
        mock_client.run_flow.return_value = {
            "outputs": {
                "chunks": [
                    {
                        "text": "chunk 1",
                        "embedding": [0.1, 0.2],
                    },
                    {
                        "text": "chunk 2",
                        "embedding": [0.3, 0.4],
                    },
                ]
            }
        }
        mock_client_class.return_value = mock_client

        pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=mock_client)
        records = pipeline.ingest_text("Test text content", source_id="test-source")

        assert len(records) == 2
        assert records[0]["text"] == "chunk 1"
        assert records[1]["text"] == "chunk 2"

        # Verify client was called with text input
        call_args = mock_client.run_flow.call_args
        assert call_args[0][1]["text"] == "Test text content"
        assert call_args[0][1]["source_id"] == "test-source"

    @patch("ingestion.langflow_ingestion.LangflowClient")
    def test_transform_to_upsert_records_standard_format(self, mock_client_class):
        """Test transformation with standard Langflow output format."""
        mock_client = Mock()
        mock_client.run_flow.return_value = {
            "outputs": {
                "chunks": [
                    {
                        "id": "chunk-1",
                        "text": "First chunk",
                        "embedding": [0.1, 0.2, 0.3],
                        "metadata": {"page": 1},
                    },
                    {
                        "id": "chunk-2",
                        "text": "Second chunk",
                        "embedding": [0.4, 0.5, 0.6],
                        "metadata": {"page": 2},
                    },
                ]
            }
        }
        mock_client_class.return_value = mock_client

        pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=mock_client)
        records = pipeline.ingest_text("test", metadata={"doc_id": "doc1"})

        assert len(records) == 2
        assert records[0]["id"] == "chunk-1"
        assert records[0]["text"] == "First chunk"
        assert records[0]["embedding"] == [0.1, 0.2, 0.3]
        assert records[0]["metadata"]["page"] == 1
        assert records[0]["metadata"]["doc_id"] == "doc1"

    @patch("ingestion.langflow_ingestion.LangflowClient")
    def test_transform_to_upsert_records_alternative_formats(self, mock_client_class):
        """Test transformation with alternative response formats."""
        mock_client = Mock()

        # Test with "chunks" at top level
        mock_client.run_flow.return_value = {
            "chunks": [
                {"text": "chunk1", "vector": [1, 2, 3]},
                {"text": "chunk2", "vector": [4, 5, 6]},
            ]
        }
        mock_client_class.return_value = mock_client

        pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=mock_client)
        records = pipeline.ingest_text("test")

        assert len(records) == 2
        assert records[0]["embedding"] == [1, 2, 3]  # Should use "vector" as embedding

        # Test with "data" key
        mock_client.run_flow.return_value = {
            "data": [{"text": "chunk", "embedding": [1]}]
        }
        records = pipeline.ingest_text("test")
        assert len(records) == 1

        # Test with list response
        mock_client.run_flow.return_value = [
            {"text": "chunk1"},
            {"text": "chunk2"},
        ]
        records = pipeline.ingest_text("test")
        assert len(records) == 2

        # Test with single chunk object
        mock_client.run_flow.return_value = {"text": "single chunk", "embedding": [1]}
        records = pipeline.ingest_text("test")
        assert len(records) == 1

    @patch("ingestion.langflow_ingestion.LangflowClient")
    def test_transform_to_upsert_records_no_chunks(self, mock_client_class):
        """Test transformation with empty or invalid response."""
        mock_client = Mock()
        mock_client.run_flow.return_value = {}
        mock_client_class.return_value = mock_client

        pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=mock_client)
        records = pipeline.ingest_text("test")

        assert len(records) == 0

    @patch("ingestion.langflow_ingestion.LangflowClient")
    def test_transform_to_upsert_records_generates_ids(self, mock_client_class):
        """Test that IDs are generated when not provided."""
        mock_client = Mock()
        mock_client.run_flow.return_value = {
            "outputs": {
                "chunks": [
                    {"text": "chunk1"},
                    {"text": "chunk2"},
                ]
            }
        }
        mock_client_class.return_value = mock_client

        pipeline = LangflowIngestionPipeline(flow_id="test-flow", client=mock_client)
        records = pipeline.ingest_text("test", source_id="source-123")

        assert records[0]["id"] == "source-123_0"
        assert records[1]["id"] == "source-123_1"


class TestIngestWithLangflowFunction:
    """Test cases for the convenience ingest_with_langflow function."""

    @patch("ingestion.langflow_ingestion.LangflowIngestionPipeline")
    def test_ingest_with_langflow_documents(self, mock_pipeline_class):
        """Test convenience function with documents."""
        mock_pipeline = Mock()
        mock_pipeline.ingest_documents.return_value = [
            {"id": "1", "text": "chunk1"},
            {"id": "2", "text": "chunk2"},
        ]
        mock_pipeline_class.return_value = mock_pipeline

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test")
            temp_path = f.name

        try:
            records = ingest_with_langflow(
                "flow-id", document_paths=[temp_path], metadata={"test": "meta"}
            )

            assert len(records) == 2
            mock_pipeline.ingest_documents.assert_called_once_with(
                [temp_path], {"test": "meta"}
            )
        finally:
            os.unlink(temp_path)

    @patch("ingestion.langflow_ingestion.LangflowIngestionPipeline")
    def test_ingest_with_langflow_texts(self, mock_pipeline_class):
        """Test convenience function with texts."""
        mock_pipeline = Mock()
        mock_pipeline.ingest_text.side_effect = [
            [{"id": "1", "text": "chunk1"}],
            [{"id": "2", "text": "chunk2"}],
        ]
        mock_pipeline_class.return_value = mock_pipeline

        records = ingest_with_langflow(
            "flow-id", texts=["text1", "text2"], metadata={"test": "meta"}
        )

        assert len(records) == 2
        assert mock_pipeline.ingest_text.call_count == 2

    @patch("ingestion.langflow_ingestion.LangflowIngestionPipeline")
    def test_ingest_with_langflow_both(self, mock_pipeline_class):
        """Test convenience function with both documents and texts."""
        mock_pipeline = Mock()
        mock_pipeline.ingest_documents.return_value = [{"id": "doc1"}]
        mock_pipeline.ingest_text.return_value = [{"id": "text1"}]
        mock_pipeline_class.return_value = mock_pipeline

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test")
            temp_path = f.name

        try:
            records = ingest_with_langflow(
                "flow-id",
                document_paths=[temp_path],
                texts=["text"],
                metadata={"meta": "data"},
            )

            assert len(records) == 2
            mock_pipeline.ingest_documents.assert_called_once()
            mock_pipeline.ingest_text.assert_called_once()
        finally:
            os.unlink(temp_path)
