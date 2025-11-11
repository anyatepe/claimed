"""
Script to create a small test PDF file for load testing.
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os


def create_test_pdf(output_path="test_document.pdf"):
    """Create a small test PDF file."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Add some content
    c.setFont("Helvetica", 16)
    c.drawString(100, height - 100, "Test Document for Load Testing")
    
    c.setFont("Helvetica", 12)
    y = height - 150
    text_lines = [
        "This is a test document used for load testing the document upload and query API.",
        "",
        "Key Points:",
        "1. This document contains sample text for testing purposes.",
        "2. The document is designed to be small in size for efficient testing.",
        "3. It includes various topics that can be queried.",
        "",
        "Main Topic:",
        "This document discusses load testing methodologies and best practices.",
        "",
        "Methodology:",
        "The testing approach involves uploading documents and querying them with",
        "various questions to measure API performance under load.",
        "",
        "Conclusions:",
        "Load testing is essential for ensuring API reliability and performance.",
        "Proper test design helps identify bottlenecks and scalability issues.",
        "",
        "Recommendations:",
        "- Monitor response times and error rates",
        "- Test under realistic load conditions",
        "- Use appropriate tools for load testing",
    ]
    
    for line in text_lines:
        c.drawString(100, y, line)
        y -= 20
        if y < 100:
            c.showPage()
            y = height - 100
    
    c.save()
    file_size = os.path.getsize(output_path)
    print(f"Created test PDF: {output_path} ({file_size} bytes)")


if __name__ == "__main__":
    create_test_pdf()
