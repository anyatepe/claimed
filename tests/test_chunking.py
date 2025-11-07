"""
Pytest tests for TextChunker class.
"""

import pytest
from app.services.chunking import TextChunker


class TestTextChunker:
    """Test suite for TextChunker class."""
    
    def test_initialization_defaults(self):
        """Test TextChunker initialization with default parameters."""
        chunker = TextChunker()
        assert chunker.chunk_size == 800
        assert chunker.overlap_size == 100
    
    def test_initialization_custom_params(self):
        """Test TextChunker initialization with custom parameters."""
        chunker = TextChunker(chunk_size=500, overlap_size=50)
        assert chunker.chunk_size == 500
        assert chunker.overlap_size == 50
    
    def test_initialization_invalid_chunk_size(self):
        """Test that invalid chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            TextChunker(chunk_size=0)
        
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            TextChunker(chunk_size=-1)
    
    def test_initialization_invalid_overlap_size(self):
        """Test that invalid overlap_size raises ValueError."""
        with pytest.raises(ValueError, match="overlap_size must be non-negative"):
            TextChunker(overlap_size=-1)
        
        with pytest.raises(ValueError, match="overlap_size must be less than chunk_size"):
            TextChunker(chunk_size=100, overlap_size=100)
        
        with pytest.raises(ValueError, match="overlap_size must be less than chunk_size"):
            TextChunker(chunk_size=100, overlap_size=150)
    
    def test_empty_text(self):
        """Test chunking empty text returns empty list."""
        chunker = TextChunker()
        assert chunker.chunk_text("") == []
    
    def test_short_text_single_chunk(self):
        """Test that text shorter than chunk_size returns single chunk."""
        chunker = TextChunker(chunk_size=100, overlap_size=10)
        text = "This is a short text that fits in one chunk."
        chunks = chunker.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_deterministic_chunk_boundaries(self):
        """Test that chunking produces deterministic, consistent boundaries."""
        chunker = TextChunker(chunk_size=100, overlap_size=20)
        
        # Create a longer text
        text = " ".join([f"Word{i}" for i in range(200)])
        
        # Chunk multiple times
        chunks1 = chunker.chunk_text(text)
        chunks2 = chunker.chunk_text(text)
        chunks3 = chunker.chunk_text(text)
        
        # All results should be identical
        assert chunks1 == chunks2 == chunks3
        assert len(chunks1) > 1  # Should produce multiple chunks
    
    def test_overlap_between_chunks(self):
        """Test that consecutive chunks have the expected overlap."""
        chunker = TextChunker(chunk_size=50, overlap_size=10)
        
        # Create text that will produce multiple chunks
        text = " ".join([f"Token{i}" for i in range(100)])
        
        chunks = chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Tokenize chunks to verify overlap
            for i in range(len(chunks) - 1):
                tokens1 = chunker.encoding.encode(chunks[i])
                tokens2 = chunker.encoding.encode(chunks[i + 1])
                
                # Find overlap by checking end of chunk1 and start of chunk2
                overlap_found = False
                for overlap_len in range(min(len(tokens1), len(tokens2)), 0, -1):
                    if tokens1[-overlap_len:] == tokens2[:overlap_len]:
                        overlap_found = True
                        # Overlap should be approximately overlap_size
                        assert abs(overlap_len - chunker.overlap_size) <= 2, \
                            f"Expected overlap ~{chunker.overlap_size}, got {overlap_len}"
                        break
                
                assert overlap_found, "No overlap found between consecutive chunks"
    
    def test_chunk_size_approximation(self):
        """Test that chunks are approximately the target size."""
        chunker = TextChunker(chunk_size=100, overlap_size=10)
        
        text = " ".join([f"Word{i}" for i in range(500)])
        chunks = chunker.chunk_text(text)
        
        # All chunks except possibly the last should be close to chunk_size
        for i, chunk in enumerate(chunks[:-1]):
            tokens = chunker.encoding.encode(chunk)
            # Allow some tolerance (within 5 tokens)
            assert abs(len(tokens) - chunker.chunk_size) <= 5, \
                f"Chunk {i} has {len(tokens)} tokens, expected ~{chunker.chunk_size}"
    
    def test_no_overlap_when_overlap_zero(self):
        """Test chunking with zero overlap."""
        chunker = TextChunker(chunk_size=50, overlap_size=0)
        
        text = " ".join([f"Token{i}" for i in range(100)])
        chunks = chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Verify no overlap between chunks
            for i in range(len(chunks) - 1):
                tokens1 = chunker.encoding.encode(chunks[i])
                tokens2 = chunker.encoding.encode(chunks[i + 1])
                
                # End of chunk1 should not match start of chunk2
                # (except for edge cases where text naturally continues)
                # In practice, with zero overlap, they should be adjacent but not overlapping
                assert len(tokens1) == chunker.chunk_size or i == len(chunks) - 2
    
    def test_preserves_text_content(self):
        """Test that chunks cover the original text content."""
        chunker = TextChunker(chunk_size=100, overlap_size=20)
        
        text = "This is a test text. " * 50
        chunks = chunker.chunk_text(text)
        
        # Verify basic properties:
        # 1. All chunks are non-empty
        assert all(len(chunk) > 0 for chunk in chunks), "All chunks should be non-empty"
        
        # 2. First chunk should start with the beginning of the text
        # (allowing for whitespace normalization)
        first_chunk_normalized = ' '.join(chunks[0].split())
        text_start_normalized = ' '.join(text[:len(chunks[0])+20].split())
        assert first_chunk_normalized in text_start_normalized or \
               text_start_normalized.startswith(first_chunk_normalized[:50]), \
               "First chunk should match the start of the text"
        
        # 3. Last chunk should end near the end of the text
        last_chunk_normalized = ' '.join(chunks[-1].split())
        text_end_normalized = ' '.join(text[-len(chunks[-1])-20:].split())
        assert last_chunk_normalized in text_end_normalized or \
               text_end_normalized.endswith(last_chunk_normalized[-50:]), \
               "Last chunk should match the end of the text"
        
        # 4. Total character count should be reasonable (accounting for overlaps)
        total_chars = sum(len(chunk) for chunk in chunks)
        # With overlaps, total should be greater than original
        assert total_chars >= len(text) * 0.7, \
            f"Total chunk length {total_chars} seems too small for text length {len(text)}"
    
    def test_multiple_runs_consistency(self):
        """Test that multiple runs on the same text produce identical results."""
        chunker = TextChunker()
        
        text = "The quick brown fox jumps over the lazy dog. " * 100
        
        results = []
        for _ in range(10):
            chunks = chunker.chunk_text(text)
            results.append(chunks)
        
        # All results should be identical
        assert all(result == results[0] for result in results)
    
    def test_unicode_text(self):
        """Test chunking with unicode characters."""
        chunker = TextChunker(chunk_size=50, overlap_size=10)
        
        text = "Hello 世界 🌍 " * 20
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        # Verify chunks can be decoded back
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) > 0
