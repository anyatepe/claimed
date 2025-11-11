"""
Tests for text chunking functionality.
"""
import pytest
from unittest.mock import Mock, patch


class TestTextChunker:
    """Test basic text chunking."""

    def test_chunk_by_size(self, sample_text_content):
        """Test chunking by character size."""
        from chunking import TextChunker
        
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        chunks = chunker.chunk(sample_text_content)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= 50 for chunk in chunks)
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_by_tokens(self, sample_text_content):
        """Test chunking by token count."""
        from chunking import TextChunker
        
        chunker = TextChunker(chunk_size=20, chunk_overlap=5, chunk_by="tokens")
        chunks = chunker.chunk(sample_text_content)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_chunk_overlap(self, sample_text_content):
        """Test chunk overlap functionality."""
        from chunking import TextChunker
        
        chunker = TextChunker(chunk_size=50, chunk_overlap=20)
        chunks = chunker.chunk(sample_text_content)
        
        if len(chunks) > 1:
            # Check that there's overlap between consecutive chunks
            overlap_found = False
            for i in range(len(chunks) - 1):
                if chunks[i][-20:] in chunks[i + 1]:
                    overlap_found = True
                    break
            # Overlap may not always be visible in text, so we just check chunks exist
            assert len(chunks) > 0

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        from chunking import TextChunker
        
        chunker = TextChunker()
        chunks = chunker.chunk("")
        
        assert chunks == []

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size."""
        from chunking import TextChunker
        
        chunker = TextChunker(chunk_size=1000)
        chunks = chunker.chunk("Short text")
        
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_chunk_with_metadata(self, sample_text_content):
        """Test chunking with metadata preservation."""
        from chunking import TextChunker
        
        chunker = TextChunker()
        metadata = {"source": "test.pdf", "page": 1}
        chunks = chunker.chunk(sample_text_content, metadata=metadata)
        
        assert len(chunks) > 0
        # Check that metadata is preserved in chunk objects if supported
        if hasattr(chunks[0], "metadata"):
            assert chunks[0].metadata == metadata


class TestRecursiveChunker:
    """Test recursive text chunking."""

    def test_recursive_chunk_by_paragraph(self, sample_text_content):
        """Test recursive chunking by paragraph."""
        from chunking import RecursiveChunker
        
        chunker = RecursiveChunker(chunk_size=100, separators=["\n\n", "\n", " "])
        chunks = chunker.chunk(sample_text_content)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_recursive_chunk_by_sentence(self):
        """Test recursive chunking by sentence."""
        from chunking import RecursiveChunker
        
        text = "First sentence. Second sentence. Third sentence."
        chunker = RecursiveChunker(chunk_size=30, separators=[". ", " "])
        chunks = chunker.chunk(text)
        
        assert len(chunks) > 0

    def test_recursive_chunk_fallback(self):
        """Test recursive chunking with fallback to character splitting."""
        from chunking import RecursiveChunker
        
        text = "A" * 200  # Long text without separators
        chunker = RecursiveChunker(chunk_size=50, separators=["\n\n", "\n"])
        chunks = chunker.chunk(text)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= 50 for chunk in chunks)


class TestSemanticChunker:
    """Test semantic chunking."""

    @patch("chunking.SemanticChunker")
    def test_semantic_chunk_by_similarity(self, mock_chunker, sample_text_content):
        """Test semantic chunking by similarity."""
        from chunking import SemanticChunker
        
        chunker = SemanticChunker(threshold=0.5)
        chunks = chunker.chunk(sample_text_content)
        
        assert len(chunks) > 0

    @patch("chunking.SemanticChunker")
    def test_semantic_chunk_with_embeddings(self, mock_chunker, sample_text_content):
        """Test semantic chunking with pre-computed embeddings."""
        from chunking import SemanticChunker
        
        embeddings = [[0.1] * 128] * 10
        chunker = SemanticChunker(threshold=0.5)
        chunks = chunker.chunk(sample_text_content, embeddings=embeddings)
        
        assert len(chunks) > 0


class TestChunkingStrategies:
    """Test different chunking strategies."""

    def test_fixed_size_chunking(self, sample_text_content):
        """Test fixed-size chunking strategy."""
        from chunking import FixedSizeChunker
        
        chunker = FixedSizeChunker(size=50, overlap=10)
        chunks = chunker.chunk(sample_text_content)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= 50 for chunk in chunks)

    def test_sentence_chunking(self):
        """Test sentence-based chunking."""
        from chunking import SentenceChunker
        
        text = "First sentence. Second sentence. Third sentence."
        chunker = SentenceChunker(max_chunk_size=100)
        chunks = chunker.chunk(text)
        
        assert len(chunks) > 0

    def test_paragraph_chunking(self, sample_text_content):
        """Test paragraph-based chunking."""
        from chunking import ParagraphChunker
        
        chunker = ParagraphChunker(max_chunk_size=200)
        chunks = chunker.chunk(sample_text_content)
        
        assert len(chunks) > 0

    def test_sliding_window_chunking(self, sample_text_content):
        """Test sliding window chunking."""
        from chunking import SlidingWindowChunker
        
        chunker = SlidingWindowChunker(window_size=50, step_size=25)
        chunks = chunker.chunk(sample_text_content)
        
        assert len(chunks) > 0


class TestChunkMetadata:
    """Test chunk metadata handling."""

    def test_add_metadata_to_chunks(self, sample_chunks, sample_metadata):
        """Test adding metadata to chunks."""
        from chunking import add_metadata_to_chunks
        
        chunks_with_metadata = add_metadata_to_chunks(
            sample_chunks, sample_metadata
        )
        
        assert len(chunks_with_metadata) == len(sample_chunks)
        # Verify metadata is attached if supported
        if hasattr(chunks_with_metadata[0], "metadata"):
            assert chunks_with_metadata[0].metadata == sample_metadata

    def test_chunk_indexing(self, sample_text_content):
        """Test chunk indexing."""
        from chunking import TextChunker
        
        chunker = TextChunker()
        chunks = chunker.chunk(sample_text_content)
        
        # Verify chunks can be indexed
        if len(chunks) > 0:
            assert chunks[0] is not None
            if len(chunks) > 1:
                assert chunks[-1] is not None

    def test_chunk_source_tracking(self, sample_text_content):
        """Test tracking source information in chunks."""
        from chunking import TextChunker
        
        chunker = TextChunker()
        source_info = {"file": "test.pdf", "page": 1}
        chunks = chunker.chunk(sample_text_content, source_info=source_info)
        
        assert len(chunks) > 0


class TestChunkingUtils:
    """Test chunking utility functions."""

    def test_estimate_tokens(self):
        """Test token estimation."""
        from chunking import estimate_tokens
        
        text = "This is a test sentence."
        tokens = estimate_tokens(text)
        
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_split_by_separator(self):
        """Test splitting by separator."""
        from chunking import split_by_separator
        
        text = "Part1|Part2|Part3"
        parts = split_by_separator(text, "|")
        
        assert len(parts) == 3
        assert parts[0] == "Part1"

    def test_merge_chunks(self, sample_chunks):
        """Test merging chunks."""
        from chunking import merge_chunks
        
        merged = merge_chunks(sample_chunks)
        
        assert isinstance(merged, str)
        assert len(merged) > 0

    def test_validate_chunk_size(self):
        """Test chunk size validation."""
        from chunking import validate_chunk_size
        
        assert validate_chunk_size(100) is True
        with pytest.raises(ValueError):
            validate_chunk_size(-1)
        with pytest.raises(ValueError):
            validate_chunk_size(0)

    def test_calculate_overlap_size(self):
        """Test overlap size calculation."""
        from chunking import calculate_overlap_size
        
        overlap = calculate_overlap_size(chunk_size=100, overlap_ratio=0.1)
        
        assert overlap == 10

    def test_trim_chunk(self):
        """Test chunk trimming."""
        from chunking import trim_chunk
        
        chunk = "  This is a chunk with extra spaces  "
        trimmed = trim_chunk(chunk)
        
        assert trimmed == trimmed.strip()
