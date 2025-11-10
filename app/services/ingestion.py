"""
PDF Ingestion Service for extracting and cleaning text from PDF documents.

This service supports both text-based and scanned PDFs using PyPDF as primary
extraction method with PyMuPDF as fallback for better OCR and scanned document support.
"""

import io
import re
from pathlib import Path
from typing import Union, List, Dict

try:
    import pypdf
except ImportError:
    try:
        import PyPDF2 as pypdf
    except ImportError:
        pypdf = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class PDFIngestionService:
    """Service for extracting and cleaning text from PDF documents."""
    
    def __init__(self):
        """Initialize the PDF ingestion service."""
        if pypdf is None and fitz is None:
            raise ImportError(
                "At least one PDF library is required. "
                "Please install pypdf or PyMuPDF (pip install pypdf PyMuPDF)"
            )
    
    def extract_text(
        self, 
        pdf_input: Union[bytes, str, Path]
    ) -> List[Dict[str, Union[int, str]]]:
        """
        Extract text from a PDF file.
        
        Args:
            pdf_input: Either bytes of PDF content, or a file path (str or Path)
            
        Returns:
            List of dictionaries with 'page' (int) and 'text' (str) keys
            
        Raises:
            ValueError: If pdf_input is invalid
            IOError: If file cannot be read
        """
        # Convert path to bytes if needed
        if isinstance(pdf_input, (str, Path)):
            pdf_path = Path(pdf_input)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
        elif isinstance(pdf_input, bytes):
            pdf_bytes = pdf_input
        else:
            raise ValueError(f"Invalid pdf_input type: {type(pdf_input)}")
        
        # Try PyPDF first
        if pypdf is not None:
            try:
                return self._extract_with_pypdf(pdf_bytes)
            except Exception as e:
                # Fallback to PyMuPDF if PyPDF fails
                if fitz is not None:
                    try:
                        return self._extract_with_pymupdf(pdf_bytes)
                    except Exception as fallback_error:
                        raise RuntimeError(
                            f"PyPDF extraction failed: {e}. "
                            f"PyMuPDF fallback also failed: {fallback_error}"
                        )
                raise RuntimeError(f"PyPDF extraction failed: {e}")
        
        # Use PyMuPDF if PyPDF is not available
        if fitz is not None:
            return self._extract_with_pymupdf(pdf_bytes)
        
        raise RuntimeError("No PDF extraction library available")
    
    def _extract_with_pypdf(self, pdf_bytes: bytes) -> List[Dict[str, Union[int, str]]]:
        """Extract text using PyPDF library."""
        pdf_file = io.BytesIO(pdf_bytes)
        
        # Try pypdf (newer) or PyPDF2 (older)
        if hasattr(pypdf, 'PdfReader'):
            reader = pypdf.PdfReader(pdf_file)
            num_pages = len(reader.pages)
        else:
            reader = pypdf.PdfFileReader(pdf_file)
            num_pages = reader.numPages
        
        pages = []
        for page_num in range(num_pages):
            if hasattr(pypdf, 'PdfReader'):
                page = reader.pages[page_num]
                text = page.extract_text()
            else:
                page = reader.getPage(page_num)
                text = page.extractText()
            
            pages.append({
                "page": page_num + 1,  # 1-indexed
                "text": text or ""
            })
        
        return pages
    
    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> List[Dict[str, Union[int, str]]]:
        """Extract text using PyMuPDF (fitz) library."""
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        pages = []
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text = page.get_text()
            
            pages.append({
                "page": page_num + 1,  # 1-indexed
                "text": text or ""
            })
        
        pdf_document.close()
        return pages
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text by normalizing whitespace and removing headers/footers.
        
        Args:
            text: Raw text extracted from PDF
            
        Returns:
            Cleaned text string
        """
        if not text:
            return ""
        
        # Normalize whitespace: replace multiple spaces/tabs/newlines with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common header/footer patterns
        # Page numbers (e.g., "Page 1", "1", "Page 1 of 10")
        text = re.sub(r'\bPage\s+\d+\s+of\s+\d+\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bPage\s+\d+\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
        
        # Common footer patterns (copyright, dates, etc.)
        text = re.sub(r'\b©\s*\d{4}.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'\bCopyright\s+©\s*\d{4}.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # Date patterns that might appear in headers/footers
        # (but be careful not to remove dates in content)
        # Only remove if they're on their own line
        text = re.sub(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', '', text, flags=re.MULTILINE)
        
        # Remove very short lines that are likely headers/footers (1-3 words)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip lines that are very short and contain only numbers or common header words
            if len(line) < 10 and (
                line.isdigit() or
                line.lower() in ['confidential', 'draft', 'page', 'table of contents']
            ):
                continue
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Final whitespace normalization
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
