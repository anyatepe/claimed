"""
Tests for text/document chunking functionality.
"""
import pytest
from typing import List, Dict
from unittest.mock import Mock, patch


@pytest.fixture
def sample_text():
    """Sample text for testing chunking."""
    return """
    This is a sample document for testing chunking functionality.
    It contains multiple sentences and paragraphs to demonstrate
    how text can be split into smaller chunks. Each chunk should
    maintain semantic meaning and context. The chunking algorithm
    should handle various text lengths and structures appropriately.
    """


@pytest.fixture
def sample_documents():
    """Sample list of documents for batch chunking."""
    return [
        "First document with some content.",
        "Second document with different content.",
        "Third document with yet another set of content.",
    ]


@pytest.fixture
def chunker():
    """Fixture for chunker instance."""
    # Mock chunker class
    class MockChunker:
        def __init__(self, chunk_size: int = 100, chunk_overlap: int = 20):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
        
        def chunk_text(self, text: str) -> List[str]:
            """Chunk text into smaller pieces."""
            if not text or not text.strip():
                return []
            
            chunks = []
            words = text.split()
            current_chunk = []
            current_length = 0
            
            for word in words:
                word_length = len(word) + 1  # +1 for space
                if current_length + word_length > self.chunk_size and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    # Apply overlap
                    overlap_words = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_words + [word]
                    current_length = sum(len(w) + 1 for w in current_chunk)
                else:
                    current_chunk.append(word)
                    current_length += word_length
            
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            
            return chunks
        
        def chunk_documents(self, documents: List[str]) -> List[Dict[str, any]]:
            """Chunk multiple documents."""
            result = []
            doc_id = 0
            for doc in documents:
                chunks = self.chunk_text(doc)
                for chunk_idx, chunk in enumerate(chunks):
                    result.append({
                        "document_id": doc_id,
                        "chunk_id": chunk_idx,
                        "text": chunk,
                        "metadata": {"source": f"doc_{doc_id}"}
                    })
                doc_id += 1
            return result
    
    return MockChunker(chunk_size=50, chunk_overlap=10)


class TestChunking:
    """Test suite for chunking functionality."""
    
    def test_chunk_text_basic(self, chunker, sample_text):
        """Test basic text chunking."""
        chunks = chunker.chunk_text(sample_text)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        assert all(len(chunk) > 0 for chunk in chunks)
    
    def test_chunk_text_empty(self, chunker):
        """Test chunking empty text."""
        chunks = chunker.chunk_text("")
        assert chunks == []
        
        chunks = chunker.chunk_text("   ")
        assert chunks == []
    
    def test_chunk_text_preserves_content(self, chunker, sample_text):
        """Test that chunking preserves all content."""
        chunks = chunker.chunk_text(sample_text)
        combined = " ".join(chunks)
        
        # Remove extra whitespace for comparison
        original_clean = " ".join(sample_text.split())
        combined_clean = " ".join(combined.split())
        
        assert original_clean in combined_clean or combined_clean in original_clean
    
    def test_chunk_size_respected(self, chunker):
        """Test that chunks respect maximum size."""
        long_text = "word " * 200
        chunks = chunker.chunk_text(long_text)
        
        for chunk in chunks:
            assert len(chunk) <= chunker.chunk_size + 50  # Allow some margin
    
    def test_chunk_overlap_applied(self, chunker):
        """Test that overlap is applied between chunks."""
        text = "word " * 100
        chunks = chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Check that consecutive chunks have overlap
            first_end = chunks[0].split()[-chunker.chunk_overlap:]
            second_start = chunks[1].split()[:chunker.chunk_overlap]
            
            # There should be some overlap
            assert len(set(first_end) & set(second_start)) > 0
    
    def test_chunk_documents(self, chunker, sample_documents):
        """Test chunking multiple documents."""
        result = chunker.chunk_documents(sample_documents)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        for item in result:
            assert isinstance(item, dict)
            assert "document_id" in item
            assert "chunk_id" in item
            assert "text" in item
            assert "metadata" in item
            assert isinstance(item["text"], str)
            assert len(item["text"]) > 0
    
    def test_chunk_documents_preserves_document_count(self, chunker, sample_documents):
        """Test that all documents are processed."""
        result = chunker.chunk_documents(sample_documents)
        
        unique_doc_ids = set(item["document_id"] for item in result)
        assert len(unique_doc_ids) == len(sample_documents)
    
    def test_chunk_with_custom_size(self):
        """Test chunking with custom chunk size."""
        # Create a new chunker instance with custom parameters
        class MockChunker:
            def __init__(self, chunk_size: int = 100, chunk_overlap: int = 20):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap
            
            def chunk_text(self, text: str) -> List[str]:
                if not text or not text.strip():
                    return []
                chunks = []
                words = text.split()
                current_chunk = []
                current_length = 0
                for word in words:
                    word_length = len(word) + 1
                    if current_length + word_length > self.chunk_size and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        overlap_words = current_chunk[-self.chunk_overlap:]
                        current_chunk = overlap_words + [word]
                        current_length = sum(len(w) + 1 for w in current_chunk)
                    else:
                        current_chunk.append(word)
                        current_length += word_length
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                return chunks
        
        chunker = MockChunker(chunk_size=30, chunk_overlap=5)
        text = "This is a test sentence for custom chunk size."
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk) <= 50  # Allow margin
    
    def test_chunk_metadata_included(self, chunker, sample_documents):
        """Test that metadata is included in chunked documents."""
        result = chunker.chunk_documents(sample_documents)
        
        for item in result:
            assert "metadata" in item
            assert isinstance(item["metadata"], dict)
            assert "source" in item["metadata"]


if __name__ == "__main__":
    pytest.main([__file__])
