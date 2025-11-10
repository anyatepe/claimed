"""
Script to generate fixture PDFs for testing.

This script creates sample PDFs that can be used for testing the PDF ingestion service.
"""

from pathlib import Path
import sys

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
except ImportError:
    print("reportlab is required. Install with: pip install reportlab")
    sys.exit(1)

try:
    from PIL import Image
    import io
except ImportError:
    print("Pillow is required. Install with: pip install Pillow")
    sys.exit(1)


def create_text_pdf(output_path: Path):
    """Create a text-based PDF with multiple pages."""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    
    # Page 1
    c.drawString(100, 750, "This is page 1 of the test PDF.")
    c.drawString(100, 730, "It contains multiple lines of text.")
    c.drawString(100, 710, "This is a test document for PDF ingestion.")
    c.drawString(100, 690, "The service should extract all pages correctly.")
    c.showPage()
    
    # Page 2
    c.drawString(100, 750, "This is page 2 of the test PDF.")
    c.drawString(100, 730, "It has different content than page 1.")
    c.drawString(100, 710, "Testing multi-page extraction.")
    c.drawString(100, 690, "Each page should be extracted separately.")
    c.showPage()
    
    # Page 3
    c.drawString(100, 750, "This is page 3 of the test PDF.")
    c.drawString(100, 730, "Final page for testing.")
    c.drawString(100, 710, "Page count should be validated.")
    c.drawString(100, 690, "The extraction should return exactly 3 pages.")
    
    c.save()
    print(f"Created text PDF: {output_path}")


def create_scanned_pdf(output_path: Path):
    """Create a scanned/image-based PDF (simulating scanned document)."""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    
    # Create a simple image
    img = Image.new('RGB', (400, 200), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Page 1 - image-based
    c.drawImage(img_bytes, 100, 700, width=400, height=200)
    c.showPage()
    
    # Page 2 - image-based
    c.drawImage(img_bytes, 100, 700, width=400, height=200)
    c.showPage()
    
    c.save()
    print(f"Created scanned PDF: {output_path}")


def create_pdf_with_headers_footers(output_path: Path):
    """Create a PDF with headers and footers to test cleaning."""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    
    # Page 1 with header/footer
    c.drawString(50, 800, "CONFIDENTIAL")  # Header
    c.drawString(100, 750, "This is the main content of page 1.")
    c.drawString(100, 730, "It should remain after cleaning.")
    c.drawString(100, 710, "The cleaning function should remove headers and footers.")
    c.drawString(50, 50, "Page 1")  # Footer
    c.drawString(500, 50, "Copyright © 2024 Test Company")  # Footer
    c.showPage()
    
    # Page 2 with header/footer
    c.drawString(50, 800, "CONFIDENTIAL")  # Header
    c.drawString(100, 750, "This is the main content of page 2.")
    c.drawString(100, 730, "Headers and footers should be removed.")
    c.drawString(100, 710, "But the main content should be preserved.")
    c.drawString(50, 50, "Page 2")  # Footer
    c.drawString(500, 50, "Copyright © 2024 Test Company")  # Footer
    
    c.save()
    print(f"Created PDF with headers/footers: {output_path}")


if __name__ == "__main__":
    fixtures_dir = Path(__file__).parent
    
    # Create fixture PDFs
    create_text_pdf(fixtures_dir / "test_text.pdf")
    create_scanned_pdf(fixtures_dir / "test_scanned.pdf")
    create_pdf_with_headers_footers(fixtures_dir / "test_headers_footers.pdf")
    
    print("\nAll fixture PDFs created successfully!")
