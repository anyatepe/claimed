"""
Upsert service for document processing pipeline.
Handles text extraction, chunking, embedding, and vector store upsert with idempotency.
"""

import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import io

try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class VectorStore:
    """Abstract interface for vector store operations."""
    
    def upsert(self, documents: List[Dict[str, Any]]) -> None:
        """
        Upsert documents into the vector store.
        
        Args:
            documents: List of document dicts with keys like 'id', 'text', 'embedding', 'metadata'
        """
        raise NotImplementedError
    
    def get_document_checksum(self, doc_id: str) -> Optional[str]:
        """
        Get the stored checksum for a document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Stored checksum if exists, None otherwise
        """
        raise NotImplementedError


def extract_text(bytes_or_path: Union[bytes, str, Path]) -> Dict[str, Any]:
    """
    Extract text from a document (bytes or file path).
    
    Supports:
    - PDF files (.pdf)
    - Word documents (.docx)
    - Plain text (.txt)
    - Raw bytes (assumed to be text)
    
    Args:
        bytes_or_path: Either bytes content or path to file
        
    Returns:
        Dict with keys: 'text' (str), 'pages' (int), 'format' (str)
    """
    if isinstance(bytes_or_path, (str, Path)):
        path = Path(bytes_or_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            if not HAS_PDF:
                raise ImportError("PyPDF2 is required for PDF processing. Install with: pip install PyPDF2")
            return _extract_text_from_pdf(path)
        elif suffix == '.docx':
            if not HAS_DOCX:
                raise ImportError("python-docx is required for DOCX processing. Install with: pip install python-docx")
            return _extract_text_from_docx(path)
        elif suffix == '.txt':
            return _extract_text_from_txt(path)
        else:
            # Try as text file
            return _extract_text_from_txt(path)
    else:
        # Assume bytes are text
        text = bytes_or_path.decode('utf-8', errors='ignore')
        return {
            'text': text,
            'pages': 1,
            'format': 'bytes'
        }


def _extract_text_from_pdf(path: Path) -> Dict[str, Any]:
    """Extract text from PDF file."""
    text_parts = []
    pages = 0
    
    with open(path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        pages = len(pdf_reader.pages)
        
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text())
    
    return {
        'text': '\n\n'.join(text_parts),
        'pages': pages,
        'format': 'pdf'
    }


def _extract_text_from_docx(path: Path) -> Dict[str, Any]:
    """Extract text from DOCX file."""
    doc = DocxDocument(path)
    paragraphs = [para.text for para in doc.paragraphs]
    
    # Count pages (rough estimate: ~500 words per page)
    word_count = sum(len(p.split()) for p in paragraphs)
    pages = max(1, (word_count + 499) // 500)
    
    return {
        'text': '\n\n'.join(paragraphs),
        'pages': pages,
        'format': 'docx'
    }


def _extract_text_from_txt(path: Path) -> Dict[str, Any]:
    """Extract text from plain text file."""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    
    # Rough page estimate: ~500 words per page
    word_count = len(text.split())
    pages = max(1, (word_count + 499) // 500)
    
    return {
        'text': text,
        'pages': pages,
        'format': 'txt'
    }


def chunk(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < text_length:
            # Look for sentence endings within the last 200 chars
            for i in range(end, max(start + chunk_size - 200, start), -1):
                if text[i] in '.!?\n':
                    end = i + 1
                    break
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(chunk_text)
        
        # Move start position with overlap
        start = end - chunk_overlap
        if start >= text_length:
            break
    
    return chunks


def embed_batch(texts: List[str], embedding_model=None) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.
    
    Args:
        texts: List of text strings to embed
        embedding_model: Optional embedding model (if None, uses dummy embeddings)
        
    Returns:
        List of embedding vectors (each is a list of floats)
    """
    if embedding_model is None:
        # Dummy embeddings for testing/fallback
        # In production, use actual embedding model like sentence-transformers
        return [[0.0] * 384 for _ in texts]
    
    # If embedding_model is provided, use it
    if hasattr(embedding_model, 'encode'):
        return embedding_model.encode(texts).tolist()
    elif callable(embedding_model):
        return [embedding_model(text) for text in texts]
    else:
        # Fallback to dummy embeddings
        return [[0.0] * 384 for _ in texts]


def calculate_checksum(content: Union[bytes, str]) -> str:
    """
    Calculate SHA256 checksum of content.
    
    Args:
        content: Content to checksum (bytes or str)
        
    Returns:
        Hex digest of SHA256 hash
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def count_tokens(text: str) -> int:
    """
    Estimate token count (rough approximation: 1 token ≈ 4 characters).
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Estimated token count
    """
    return (len(text) + 3) // 4


def upsert_document(
    doc_id: str,
    bytes_or_path: Union[bytes, str, Path],
    metadata: Optional[Dict[str, Any]] = None,
    vector_store: Optional[VectorStore] = None,
    embedding_model=None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict[str, Any]:
    """
    Upsert a document into the vector store with idempotency.
    
    Pipeline: extract_text -> chunk -> embed_batch -> vector_store.upsert
    
    Args:
        doc_id: Unique document identifier
        bytes_or_path: Document content as bytes or path to file
        metadata: Optional metadata dict to attach to document
        vector_store: VectorStore instance for upserting documents
        embedding_model: Optional embedding model (if None, uses dummy embeddings)
        chunk_size: Size of text chunks in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        Summary dict with keys: doc_id, chunks, tokens, pages, elapsed_ms
    """
    if vector_store is None:
        raise ValueError("vector_store is required")
    
    start_time = time.time()
    
    # Read content for checksum calculation
    if isinstance(bytes_or_path, (str, Path)):
        path = Path(bytes_or_path)
        with open(path, 'rb') as f:
            content_bytes = f.read()
    else:
        content_bytes = bytes_or_path if isinstance(bytes_or_path, bytes) else bytes_or_path
    
    # Calculate checksum for idempotency
    checksum = calculate_checksum(content_bytes)
    
    # Check if document with same doc_id and checksum already exists
    stored_checksum = vector_store.get_document_checksum(doc_id)
    if stored_checksum == checksum:
        # Document unchanged, skip processing
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            'doc_id': doc_id,
            'chunks': 0,
            'tokens': 0,
            'pages': 0,
            'elapsed_ms': elapsed_ms,
            'skipped': True,
            'reason': 'unchanged'
        }
    
    # Extract text
    extraction_result = extract_text(bytes_or_path)
    text = extraction_result['text']
    pages = extraction_result['pages']
    
    # Chunk text
    chunks = chunk(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    if not chunks:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            'doc_id': doc_id,
            'chunks': 0,
            'tokens': 0,
            'pages': pages,
            'elapsed_ms': elapsed_ms,
            'skipped': True,
            'reason': 'no_content'
        }
    
    # Generate embeddings
    embeddings = embed_batch(chunks, embedding_model=embedding_model)
    
    # Prepare documents for upsert
    documents = []
    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_metadata = {
            **(metadata or {}),
            'doc_id': doc_id,
            'chunk_index': i,
            'checksum': checksum,
            'total_chunks': len(chunks)
        }
        
        documents.append({
            'id': f"{doc_id}_chunk_{i}",
            'text': chunk_text,
            'embedding': embedding,
            'metadata': chunk_metadata
        })
    
    # Upsert to vector store
    vector_store.upsert(documents)
    
    # Calculate total tokens
    total_tokens = sum(count_tokens(chunk_text) for chunk_text in chunks)
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    return {
        'doc_id': doc_id,
        'chunks': len(chunks),
        'tokens': total_tokens,
        'pages': pages,
        'elapsed_ms': elapsed_ms,
        'skipped': False
    }
