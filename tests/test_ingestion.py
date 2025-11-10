"""
Tests for PDF Ingestion Service.

Tests cover:
- Text extraction from text-based PDFs
- Text extraction from scanned PDFs (using PyMuPDF fallback)
- Page count validation
- Text cleaning functionality
"""

import os
import pytest
from pathlib import Path
from app.services.ingestion import PDFIngestionService


# Fixture to create a simple text-based PDF
@pytest.fixture
def text_pdf_path(tmp_path):
    """Create a simple text-based PDF fixture."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_path = tmp_path / "test_text.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Page 1
        c.drawString(100, 750, "This is page 1 of the test PDF.")
        c.drawString(100, 730, "It contains multiple lines of text.")
        c.drawString(100, 710, "This is a test document for PDF ingestion.")
        c.showPage()
        
        # Page 2
        c.drawString(100, 750, "This is page 2 of the test PDF.")
        c.drawString(100, 730, "It has different content than page 1.")
        c.drawString(100, 710, "Testing multi-page extraction.")
        c.showPage()
        
        # Page 3
        c.drawString(100, 750, "This is page 3 of the test PDF.")
        c.drawString(100, 730, "Final page for testing.")
        c.drawString(100, 710, "Page count should be validated.")
        
        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not available, skipping PDF fixture creation")


@pytest.fixture
def scanned_pdf_path(tmp_path):
    """Create a scanned PDF fixture (image-based)."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from PIL import Image
        import io
        
        pdf_path = tmp_path / "test_scanned.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Create a simple image-based page (simulating scanned document)
        # Create a simple image
        img = Image.new('RGB', (200, 100), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Page 1 - image-based
        c.drawImage(img_bytes, 100, 700, width=200, height=100)
        c.showPage()
        
        # Page 2 - image-based
        c.drawImage(img_bytes, 100, 700, width=200, height=100)
        c.showPage()
        
        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab or PIL not available, skipping scanned PDF fixture creation")


@pytest.fixture
def pdf_with_headers_footers(tmp_path):
    """Create a PDF with headers and footers."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_path = tmp_path / "test_headers_footers.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Page 1 with header/footer
        c.drawString(50, 800, "CONFIDENTIAL")  # Header
        c.drawString(100, 750, "This is the main content of page 1.")
        c.drawString(100, 730, "It should remain after cleaning.")
        c.drawString(50, 50, "Page 1")  # Footer
        c.drawString(500, 50, "Copyright © 2024")  # Footer
        c.showPage()
        
        # Page 2 with header/footer
        c.drawString(50, 800, "CONFIDENTIAL")  # Header
        c.drawString(100, 750, "This is the main content of page 2.")
        c.drawString(100, 730, "Headers and footers should be removed.")
        c.drawString(50, 50, "Page 2")  # Footer
        c.drawString(500, 50, "Copyright © 2024")  # Footer
        
        c.save()
        return pdf_path
    except ImportError:
        pytest.skip("reportlab not available, skipping PDF fixture creation")


class TestPDFIngestionService:
    """Test suite for PDFIngestionService."""
    
    def test_extract_text_from_path(self, text_pdf_path):
        """Test extracting text from PDF file path."""
        service = PDFIngestionService()
        result = service.extract_text(text_pdf_path)
        
        assert isinstance(result, list)
        assert len(result) == 3, f"Expected 3 pages, got {len(result)}"
        
        for page_data in result:
            assert "page" in page_data
            assert "text" in page_data
            assert isinstance(page_data["page"], int)
            assert isinstance(page_data["text"], str)
            assert page_data["page"] > 0
        
        # Verify page numbers are sequential
        page_numbers = [p["page"] for p in result]
        assert page_numbers == [1, 2, 3]
    
    def test_extract_text_from_bytes(self, text_pdf_path):
        """Test extracting text from PDF bytes."""
        service = PDFIngestionService()
        
        with open(text_pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        result = service.extract_text(pdf_bytes)
        
        assert isinstance(result, list)
        assert len(result) == 3, f"Expected 3 pages, got {len(result)}"
    
    def test_extract_text_page_count_validation(self, text_pdf_path):
        """Test that extracted page count matches expected."""
        service = PDFIngestionService()
        result = service.extract_text(text_pdf_path)
        
        # Should extract exactly 3 pages
        assert len(result) == 3
        
        # Each page should have content
        for page_data in result:
            assert len(page_data["text"]) > 0
    
    def test_extract_text_scanned_pdf(self, scanned_pdf_path):
        """Test extracting text from scanned/image-based PDF."""
        service = PDFIngestionService()
        result = service.extract_text(scanned_pdf_path)
        
        assert isinstance(result, list)
        # Should still extract pages even if no text content
        assert len(result) == 2, f"Expected 2 pages, got {len(result)}"
        
        # Page numbers should be correct
        page_numbers = [p["page"] for p in result]
        assert page_numbers == [1, 2]
    
    def test_clean_text_normalize_whitespace(self):
        """Test that clean_text normalizes whitespace."""
        service = PDFIngestionService()
        
        text_with_extra_spaces = "This   has    multiple    spaces"
        cleaned = service.clean_text(text_with_extra_spaces)
        assert cleaned == "This has multiple spaces"
        
        text_with_newlines = "This\nhas\nmultiple\nnewlines"
        cleaned = service.clean_text(text_with_newlines)
        assert "  " not in cleaned  # No double spaces
    
    def test_clean_text_remove_headers_footers(self):
        """Test that clean_text removes headers and footers."""
        service = PDFIngestionService()
        
        # Test page number removal
        text_with_page = "Main content here. Page 1 More content."
        cleaned = service.clean_text(text_with_page)
        assert "Page 1" not in cleaned or cleaned.count("Page 1") < text_with_page.count("Page 1")
        
        # Test copyright removal
        text_with_copyright = "Main content. Copyright © 2024 Company Name"
        cleaned = service.clean_text(text_with_copyright)
        # Copyright should be removed or reduced
        assert "Copyright © 2024" not in cleaned or cleaned.count("Copyright © 2024") < text_with_copyright.count("Copyright © 2024")
    
    def test_clean_text_preserves_content(self, text_pdf_path):
        """Test that clean_text preserves actual content."""
        service = PDFIngestionService()
        result = service.extract_text(text_pdf_path)
        
        # Get text from first page
        original_text = result[0]["text"]
        cleaned_text = service.clean_text(original_text)
        
        # Main content keywords should still be present
        assert "page 1" in cleaned_text.lower() or "test PDF" in cleaned_text.lower()
        assert len(cleaned_text) > 0
    
    def test_clean_text_with_headers_footers(self, pdf_with_headers_footers):
        """Test cleaning PDF with headers and footers."""
        service = PDFIngestionService()
        result = service.extract_text(pdf_with_headers_footers)
        
        # Clean the text from first page
        original_text = result[0]["text"]
        cleaned_text = service.clean_text(original_text)
        
        # Main content should be preserved
        assert "main content" in cleaned_text.lower()
        # Headers/footers should be reduced or removed
        assert cleaned_text.count("CONFIDENTIAL") < original_text.count("CONFIDENTIAL") or "CONFIDENTIAL" not in cleaned_text
    
    def test_extract_text_invalid_path(self):
        """Test that invalid file path raises appropriate error."""
        service = PDFIngestionService()
        
        with pytest.raises(FileNotFoundError):
            service.extract_text("/nonexistent/path/to/file.pdf")
    
    def test_extract_text_invalid_input_type(self):
        """Test that invalid input type raises appropriate error."""
        service = PDFIngestionService()
        
        with pytest.raises(ValueError):
            service.extract_text(12345)  # Invalid type
    
    def test_clean_text_empty_string(self):
        """Test that clean_text handles empty strings."""
        service = PDFIngestionService()
        
        assert service.clean_text("") == ""
        assert service.clean_text("   ") == ""
        assert service.clean_text("\n\n\n") == ""
