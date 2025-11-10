"""
Example usage of PDFIngestionService.

This demonstrates how to use the PDF ingestion service to extract and clean text from PDFs.
"""

from pathlib import Path
from ingestion import PDFIngestionService


def main():
    """Example usage of PDFIngestionService."""
    # Initialize the service
    service = PDFIngestionService()
    
    # Example 1: Extract text from a PDF file path
    pdf_path = Path("path/to/your/document.pdf")
    if pdf_path.exists():
        pages = service.extract_text(pdf_path)
        print(f"Extracted {len(pages)} pages")
        
        for page_data in pages:
            page_num = page_data["page"]
            text = page_data["text"]
            print(f"\nPage {page_num}:")
            print(f"Text length: {len(text)} characters")
            print(f"Preview: {text[:100]}...")
    
    # Example 2: Extract text from PDF bytes
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    pages = service.extract_text(pdf_bytes)
    print(f"\nExtracted {len(pages)} pages from bytes")
    
    # Example 3: Clean extracted text
    for page_data in pages:
        original_text = page_data["text"]
        cleaned_text = service.clean_text(original_text)
        
        print(f"\nPage {page_data['page']}:")
        print(f"Original length: {len(original_text)}")
        print(f"Cleaned length: {len(cleaned_text)}")
        print(f"Cleaned text: {cleaned_text[:200]}...")


if __name__ == "__main__":
    main()
