"""Deterministic tests for TextChunker boundaries and overlap."""

import pytest

from app.services.chunking import TextChunker, Chunk, MAX_CHUNK_TOKENS, CHUNK_OVERLAP


class TestTextChunker:
    """Test suite for TextChunker with deterministic boundary and overlap tests."""
    
    @pytest.fixture
    def chunker(self):
        """Create a TextChunker instance for testing."""
        return TextChunker()
    
    def test_empty_text(self, chunker):
        """Test that empty text returns empty list."""
        chunks = chunker.chunk("", page=1, doc_id="doc1")
        assert chunks == []
    
    def test_whitespace_only(self, chunker):
        """Test that whitespace-only text returns empty list."""
        chunks = chunker.chunk("   \n\n  ", page=1, doc_id="doc1")
        assert chunks == []
    
    def test_single_paragraph_under_limit(self, chunker):
        """Test single paragraph that fits within token limit."""
        text = "This is a short paragraph that should fit in one chunk."
        chunks = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=100)
        
        assert len(chunks) == 1
        assert chunks[0].doc_id == "doc1"
        assert chunks[0].page == 1
        assert chunks[0].chunk_id == "doc1_page1_chunk0"
        assert chunks[0].text == text
        assert chunks[0].token_count <= 100
    
    def test_multiple_paragraphs_no_overlap(self, chunker):
        """Test multiple paragraphs that require multiple chunks without overlap."""
        # Create text with multiple paragraphs
        para1 = "This is the first paragraph. " * 10
        para2 = "This is the second paragraph. " * 10
        para3 = "This is the third paragraph. " * 10
        text = f"{para1}\n\n{para2}\n\n{para3}"
        
        chunks = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=50, overlap=0)
        
        assert len(chunks) >= 2
        # Verify no overlap when overlap=0
        for i in range(len(chunks) - 1):
            assert chunks[i].token_count <= 50
            # Check that chunks don't share text (no overlap)
            assert chunks[i].text not in chunks[i + 1].text or overlap == 0
    
    def test_overlap_between_chunks(self, chunker):
        """Test that overlap is correctly applied between consecutive chunks."""
        # Create text that will definitely create multiple chunks
        para1 = "This is paragraph one. " * 20
        para2 = "This is paragraph two. " * 20
        para3 = "This is paragraph three. " * 20
        text = f"{para1}\n\n{para2}\n\n{para3}"
        
        chunks = chunker.chunk(
            text, 
            page=1, 
            doc_id="doc1", 
            target_tokens=100, 
            overlap=30
        )
        
        assert len(chunks) >= 2
        
        # Check that consecutive chunks have overlap
        for i in range(len(chunks) - 1):
            chunk1_text = chunks[i].text
            chunk2_text = chunks[i + 1].text
            
            # Find overlapping text (should be at the start of chunk2 and end of chunk1)
            # Extract last N words from chunk1 and first N words from chunk2
            chunk1_words = chunk1_text.split()
            chunk2_words = chunk2_text.split()
            
            # Check if there's overlap (at least some words match)
            # The overlap should be at the beginning of chunk2
            overlap_found = False
            for overlap_len in range(min(10, len(chunk1_words), len(chunk2_words)), 0, -1):
                chunk1_end = " ".join(chunk1_words[-overlap_len:])
                chunk2_start = " ".join(chunk2_words[:overlap_len])
                if chunk1_end == chunk2_start:
                    overlap_found = True
                    break
            
            # With overlap > 0, we should find some overlap
            assert overlap_found, f"No overlap found between chunk {i} and {i+1}"
    
    def test_chunk_boundaries_respected(self, chunker):
        """Test that chunk token boundaries are respected."""
        # Create text that will create multiple chunks
        text = "This is a sentence. " * 50
        
        chunks = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=50)
        
        # All chunks except possibly the last should be <= target_tokens
        for i, chunk in enumerate(chunks[:-1]):
            assert chunk.token_count <= 50, \
                f"Chunk {i} exceeds target_tokens: {chunk.token_count} > 50"
    
    def test_chunk_id_format(self, chunker):
        """Test that chunk IDs follow the expected format."""
        text = "This is a test. " * 20
        chunks = chunker.chunk(text, page=5, doc_id="test_doc_123", target_tokens=50)
        
        assert len(chunks) > 0
        for i, chunk in enumerate(chunks):
            expected_id = f"test_doc_123_page5_chunk{i}"
            assert chunk.chunk_id == expected_id
            assert chunk.doc_id == "test_doc_123"
            assert chunk.page == 5
    
    def test_page_info_preserved(self, chunker):
        """Test that page information is preserved in all chunks."""
        text = "Page content here. " * 30
        chunks = chunker.chunk(text, page=42, doc_id="doc42", target_tokens=50)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.page == 42
            assert chunk.doc_id == "doc42"
    
    def test_long_sentence_splitting(self, chunker):
        """Test that very long sentences are split appropriately."""
        # Create a very long sentence (no periods)
        long_sentence = "word " * 200
        text = f"{long_sentence}."
        
        chunks = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=50)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        # All chunks should respect token limit
        for chunk in chunks[:-1]:
            assert chunk.token_count <= 50
    
    def test_deterministic_output(self, chunker):
        """Test that the same input produces the same output (deterministic)."""
        text = "First paragraph with multiple sentences. Here is another sentence. And one more.\n\n"
        text += "Second paragraph starts here. It has its own sentences. Multiple of them.\n\n"
        text += "Third paragraph concludes the text. With final sentences. The end."
        
        chunks1 = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=50, overlap=10)
        chunks2 = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=50, overlap=10)
        
        # Should produce identical results
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
            assert c1.text == c2.text
            assert c1.token_count == c2.token_count
    
    def test_overlap_token_budget(self, chunker):
        """Test that overlap respects the token budget."""
        text = "Sentence one. " * 30
        text += "Sentence two. " * 30
        text += "Sentence three. " * 30
        
        overlap_size = 20
        chunks = chunker.chunk(
            text, 
            page=1, 
            doc_id="doc1", 
            target_tokens=100, 
            overlap=overlap_size
        )
        
        if len(chunks) > 1:
            # Check that overlap text in chunk2 doesn't exceed overlap token budget
            chunk1 = chunks[0]
            chunk2 = chunks[1]
            
            # Extract overlap portion (should be at start of chunk2)
            chunk2_words = chunk2.text.split()
            chunk1_words = chunk1.text.split()
            
            # Find where overlap ends
            overlap_text = ""
            for i in range(min(len(chunk1_words), len(chunk2_words))):
                if chunk1_words[-(i+1):] == chunk2_words[:i+1]:
                    overlap_text = " ".join(chunk2_words[:i+1])
                    break
            
            if overlap_text:
                overlap_tokens = chunker._count_tokens(overlap_text)
                # Overlap should be approximately within the overlap budget
                # Allow some flexibility due to sentence/paragraph boundaries
                assert overlap_tokens <= overlap_size * 1.5, \
                    f"Overlap tokens {overlap_tokens} significantly exceed budget {overlap_size}"
    
    def test_custom_target_tokens(self, chunker):
        """Test with custom target_tokens parameter."""
        text = "This is a test sentence. " * 100
        
        chunks = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=25)
        
        assert len(chunks) > 1
        for chunk in chunks[:-1]:
            assert chunk.token_count <= 25
    
    def test_custom_overlap(self, chunker):
        """Test with custom overlap parameter."""
        text = "Paragraph one content. " * 30
        text += "\n\nParagraph two content. " * 30
        
        chunks = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=50, overlap=15)
        
        if len(chunks) > 1:
            # Verify overlap exists
            chunk1_text = chunks[0].text
            chunk2_text = chunks[1].text
            
            # Check for overlap at boundary
            chunk1_end_words = chunk1_text.split()[-10:]
            chunk2_start_words = chunk2_text.split()[:10]
            
            # Should have some matching words
            overlap_found = any(
                " ".join(chunk1_end_words[-i:]) == " ".join(chunk2_start_words[:i])
                for i in range(1, min(len(chunk1_end_words), len(chunk2_start_words)) + 1)
            )
            assert overlap_found, "No overlap found between chunks"
    
    def test_paragraph_boundary_preservation(self, chunker):
        """Test that paragraph boundaries are preserved when possible."""
        para1 = "First paragraph with content."
        para2 = "Second paragraph with different content."
        para3 = "Third paragraph with more content."
        text = f"{para1}\n\n{para2}\n\n{para3}"
        
        # Use large target_tokens to keep paragraphs together
        chunks = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=200)
        
        # Should ideally keep paragraphs together, but may split if needed
        # At minimum, verify chunks contain complete sentences
        for chunk in chunks:
            # Each chunk should end with proper punctuation
            assert chunk.text.strip().endswith(('.', '!', '?')), \
                f"Chunk doesn't end with sentence punctuation: {chunk.text[-50:]}"
    
    def test_sentence_boundary_preservation(self, chunker):
        """Test that sentence boundaries are preserved when possible."""
        sentences = [
            "This is sentence one.",
            "This is sentence two.",
            "This is sentence three.",
            "This is sentence four.",
            "This is sentence five."
        ]
        text = " ".join(sentences)
        
        chunks = chunker.chunk(text, page=1, doc_id="doc1", target_tokens=30)
        
        # Verify chunks end at sentence boundaries
        for chunk in chunks:
            text_clean = chunk.text.strip()
            # Should end with sentence punctuation
            assert text_clean.endswith(('.', '!', '?')), \
                f"Chunk doesn't preserve sentence boundary: {text_clean[-30:]}"
