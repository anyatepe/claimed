"""
Tests for document ingestion functionality.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os


class TestPDFIngestion:
    """Test PDF document ingestion."""

    def test_ingest_pdf_success(self, sample_pdf_path):
        """Test successful PDF ingestion."""
        from ingestion import PDFIngester
        
        ingester = PDFIngester()
        result = ingester.ingest(str(sample_pdf_path))
        
        assert result is not None
        assert "content" in result
        assert "metadata" in result
        assert result["metadata"]["file_path"] == str(sample_pdf_path)
        assert result["metadata"]["file_type"] == "pdf"

    def test_ingest_pdf_multi_page(self, sample_pdf_path_multi_page):
        """Test multi-page PDF ingestion."""
        from ingestion import PDFIngester
        
        ingester = PDFIngester()
        result = ingester.ingest(str(sample_pdf_path_multi_page))
        
        assert result is not None
        assert "content" in result
        assert result["metadata"]["page_count"] == 2

    def test_ingest_pdf_nonexistent_file(self):
        """Test ingestion of non-existent file."""
        from ingestion import PDFIngester
        
        ingester = PDFIngester()
        with pytest.raises(FileNotFoundError):
            ingester.ingest("/nonexistent/file.pdf")

    def test_ingest_pdf_invalid_file(self, tmp_path):
        """Test ingestion of invalid PDF file."""
        from ingestion import PDFIngester
        
        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_text("This is not a PDF file")
        
        ingester = PDFIngester()
        with pytest.raises(ValueError, match="Invalid PDF"):
            ingester.ingest(str(invalid_pdf))

    def test_ingest_pdf_with_metadata(self, sample_pdf_path):
        """Test PDF ingestion with custom metadata."""
        from ingestion import PDFIngester
        
        ingester = PDFIngester()
        custom_metadata = {"source": "test", "category": "documentation"}
        result = ingester.ingest(str(sample_pdf_path), metadata=custom_metadata)
        
        assert result["metadata"]["source"] == "test"
        assert result["metadata"]["category"] == "documentation"

    def test_ingest_pdf_extract_text(self, sample_pdf_path):
        """Test text extraction from PDF."""
        from ingestion import PDFIngester
        
        ingester = PDFIngester()
        result = ingester.ingest(str(sample_pdf_path))
        
        assert len(result["content"]) > 0
        assert isinstance(result["content"], str)

    def test_ingest_pdf_empty_file(self, tmp_path):
        """Test ingestion of empty PDF file."""
        from ingestion import PDFIngester
        
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"%PDF-1.4\n%%EOF")
        
        ingester = PDFIngester()
        result = ingester.ingest(str(empty_pdf))
        
        assert result is not None
        assert result["content"] == ""

    @patch("ingestion.PyPDF2")
    def test_ingest_pdf_extraction_error(self, mock_pypdf2, sample_pdf_path):
        """Test handling of PDF extraction errors."""
        from ingestion import PDFIngester
        
        mock_pypdf2.PdfReader.side_effect = Exception("Extraction failed")
        
        ingester = PDFIngester()
        with pytest.raises(Exception, match="Extraction failed"):
            ingester.ingest(str(sample_pdf_path))


class TestDocumentIngester:
    """Test generic document ingestion."""

    def test_ingest_auto_detect_pdf(self, sample_pdf_path):
        """Test automatic PDF detection."""
        from ingestion import DocumentIngester
        
        ingester = DocumentIngester()
        result = ingester.ingest(str(sample_pdf_path))
        
        assert result is not None
        assert result["metadata"]["file_type"] == "pdf"

    def test_ingest_unsupported_format(self, tmp_path):
        """Test ingestion of unsupported file format."""
        from ingestion import DocumentIngester
        
        unsupported_file = tmp_path / "file.xyz"
        unsupported_file.write_text("content")
        
        ingester = DocumentIngester()
        with pytest.raises(ValueError, match="Unsupported"):
            ingester.ingest(str(unsupported_file))

    def test_ingest_batch(self, sample_pdf_path, sample_pdf_path_multi_page):
        """Test batch ingestion of multiple files."""
        from ingestion import DocumentIngester
        
        ingester = DocumentIngester()
        files = [str(sample_pdf_path), str(sample_pdf_path_multi_page)]
        results = ingester.ingest_batch(files)
        
        assert len(results) == 2
        assert all("content" in r for r in results)
        assert all("metadata" in r for r in results)

    def test_ingest_batch_with_failures(self, sample_pdf_path, tmp_path):
        """Test batch ingestion with some failures."""
        from ingestion import DocumentIngester
        
        invalid_file = tmp_path / "invalid.pdf"
        invalid_file.write_text("not a pdf")
        
        ingester = DocumentIngester()
        files = [str(sample_pdf_path), str(invalid_file)]
        
        with pytest.raises(ValueError):
            ingester.ingest_batch(files, fail_fast=True)
        
        results = ingester.ingest_batch(files, fail_fast=False)
        assert len(results) == 1  # Only successful ingestion

    def test_ingest_with_encoding(self, sample_pdf_path):
        """Test ingestion with specific encoding."""
        from ingestion import DocumentIngester
        
        ingester = DocumentIngester()
        result = ingester.ingest(str(sample_pdf_path), encoding="utf-8")
        
        assert result is not None

    def test_ingest_preserve_structure(self, sample_pdf_path_multi_page):
        """Test preservation of document structure."""
        from ingestion import DocumentIngester
        
        ingester = DocumentIngester()
        result = ingester.ingest(str(sample_pdf_path_multi_page), preserve_structure=True)
        
        assert "pages" in result or "structure" in result


class TestIngestionUtils:
    """Test ingestion utility functions."""

    def test_validate_file_exists(self, sample_pdf_path):
        """Test file existence validation."""
        from ingestion import validate_file_exists
        
        assert validate_file_exists(str(sample_pdf_path)) is True

    def test_validate_file_exists_nonexistent(self):
        """Test file existence validation for non-existent file."""
        from ingestion import validate_file_exists
        
        with pytest.raises(FileNotFoundError):
            validate_file_exists("/nonexistent/file.pdf")

    def test_get_file_type(self, sample_pdf_path):
        """Test file type detection."""
        from ingestion import get_file_type
        
        assert get_file_type(str(sample_pdf_path)) == "pdf"

    def test_get_file_type_unknown(self, tmp_path):
        """Test file type detection for unknown format."""
        from ingestion import get_file_type
        
        unknown_file = tmp_path / "file.xyz"
        unknown_file.write_text("content")
        
        assert get_file_type(str(unknown_file)) == "unknown"

    def test_normalize_file_path(self, tmp_path):
        """Test file path normalization."""
        from ingestion import normalize_file_path
        
        file_path = tmp_path / "test" / ".." / "test" / "file.pdf"
        normalized = normalize_file_path(str(file_path))
        
        assert ".." not in normalized

    def test_extract_metadata(self, sample_pdf_path):
        """Test metadata extraction."""
        from ingestion import extract_metadata
        
        metadata = extract_metadata(str(sample_pdf_path))
        
        assert "file_size" in metadata
        assert "file_path" in metadata
        assert metadata["file_type"] == "pdf"

    def test_clean_text(self):
        """Test text cleaning."""
        from ingestion import clean_text
        
        dirty_text = "  This   has   extra   spaces  \n\n\n"
        cleaned = clean_text(dirty_text)
        
        assert cleaned == "This has extra spaces"

    def test_clean_text_preserve_structure(self):
        """Test text cleaning with structure preservation."""
        from ingestion import clean_text
        
        text_with_structure = "Paragraph 1\n\nParagraph 2"
        cleaned = clean_text(text_with_structure, preserve_structure=True)
        
        assert "\n\n" in cleaned
