"""
Tests for upsert_service module.
"""

import unittest
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch

from app.services.upsert_service import (
    upsert_document,
    extract_text,
    chunk,
    embed_batch,
    calculate_checksum,
    count_tokens,
    VectorStore
)


class FakeVectorStore(VectorStore):
    """Fake vector store for testing."""
    
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.checksums: Dict[str, str] = {}
        self.upsert_calls = []
    
    def upsert(self, documents: List[Dict[str, Any]]) -> None:
        """Store documents and track upsert calls."""
        self.upsert_calls.append(documents)
        for doc in documents:
            self.documents[doc['id']] = doc
            # Store checksum from metadata
            if 'metadata' in doc and 'doc_id' in doc['metadata']:
                doc_id = doc['metadata']['doc_id']
                checksum = doc['metadata'].get('checksum')
                if checksum:
                    self.checksums[doc_id] = checksum
    
    def get_document_checksum(self, doc_id: str) -> Optional[str]:
        """Get stored checksum for document."""
        return self.checksums.get(doc_id)
    
    def get_document_count(self) -> int:
        """Get total number of documents stored."""
        return len(self.documents)
    
    def get_chunk_count_for_doc(self, doc_id: str) -> int:
        """Get number of chunks for a document."""
        return sum(1 for doc_id_key in self.documents.keys() if doc_id_key.startswith(f"{doc_id}_chunk_"))


class TestUpsertService(unittest.TestCase):
    """Test cases for upsert_service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.vector_store = FakeVectorStore()
        self.test_text = "This is a test document. " * 50  # ~1000 chars
        self.doc_id = "test_doc_001"
    
    def test_extract_text_from_bytes(self):
        """Test text extraction from bytes."""
        content = b"This is test content from bytes."
        result = extract_text(content)
        
        self.assertEqual(result['format'], 'bytes')
        self.assertIn('text', result)
        self.assertIn('pages', result)
        self.assertEqual(result['text'], "This is test content from bytes.")
    
    def test_extract_text_from_txt_file(self):
        """Test text extraction from text file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.test_text)
            temp_path = f.name
        
        try:
            result = extract_text(temp_path)
            self.assertEqual(result['format'], 'txt')
            self.assertIn('text', result)
            self.assertIn('pages', result)
            self.assertEqual(result['text'], self.test_text)
        finally:
            os.unlink(temp_path)
    
    def test_chunk_text(self):
        """Test text chunking."""
        text = "Sentence one. Sentence two. Sentence three. " * 100
        chunks = chunk(text, chunk_size=100, chunk_overlap=20)
        
        self.assertGreater(len(chunks), 0)
        # Check that chunks don't exceed size significantly
        for chunk_text in chunks:
            self.assertLessEqual(len(chunk_text), 150)  # Allow some flexibility
    
    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunks = chunk("")
        self.assertEqual(chunks, [])
    
    def test_embed_batch(self):
        """Test batch embedding generation."""
        texts = ["Text one", "Text two", "Text three"]
        embeddings = embed_batch(texts)
        
        self.assertEqual(len(embeddings), len(texts))
        self.assertIsInstance(embeddings[0], list)
        self.assertGreater(len(embeddings[0]), 0)
    
    def test_calculate_checksum(self):
        """Test checksum calculation."""
        content1 = "test content"
        content2 = "test content"
        content3 = "different content"
        
        checksum1 = calculate_checksum(content1)
        checksum2 = calculate_checksum(content2)
        checksum3 = calculate_checksum(content3)
        
        self.assertEqual(checksum1, checksum2)
        self.assertNotEqual(checksum1, checksum3)
        self.assertEqual(len(checksum1), 64)  # SHA256 hex digest length
    
    def test_count_tokens(self):
        """Test token counting."""
        text = "This is a test sentence."
        tokens = count_tokens(text)
        
        self.assertGreater(tokens, 0)
        # Rough check: ~25 chars should be ~6-7 tokens
        self.assertGreaterEqual(tokens, 5)
        self.assertLessEqual(tokens, 10)
    
    def test_upsert_document_basic(self):
        """Test basic document upsert."""
        result = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=self.test_text.encode('utf-8'),
            vector_store=self.vector_store
        )
        
        # Check return summary
        self.assertEqual(result['doc_id'], self.doc_id)
        self.assertGreater(result['chunks'], 0)
        self.assertGreater(result['tokens'], 0)
        self.assertGreaterEqual(result['pages'], 0)
        self.assertGreaterEqual(result['elapsed_ms'], 0)
        self.assertFalse(result.get('skipped', False))
        
        # Check vector store was called
        self.assertEqual(len(self.vector_store.upsert_calls), 1)
        self.assertGreater(self.vector_store.get_document_count(), 0)
        self.assertEqual(
            self.vector_store.get_chunk_count_for_doc(self.doc_id),
            result['chunks']
        )
    
    def test_upsert_document_with_metadata(self):
        """Test document upsert with metadata."""
        metadata = {'author': 'Test Author', 'category': 'test'}
        
        result = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=self.test_text.encode('utf-8'),
            metadata=metadata,
            vector_store=self.vector_store
        )
        
        # Check metadata was stored
        stored_docs = self.vector_store.upsert_calls[0]
        for doc in stored_docs:
            self.assertEqual(doc['metadata']['author'], 'Test Author')
            self.assertEqual(doc['metadata']['category'], 'test')
            self.assertEqual(doc['metadata']['doc_id'], self.doc_id)
    
    def test_upsert_document_idempotency_same_content(self):
        """Test idempotency: same doc_id and content should skip."""
        content = self.test_text.encode('utf-8')
        
        # First upsert
        result1 = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=content,
            vector_store=self.vector_store
        )
        
        chunks_first = result1['chunks']
        self.assertGreater(chunks_first, 0)
        self.assertEqual(len(self.vector_store.upsert_calls), 1)
        
        # Second upsert with same content
        result2 = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=content,
            vector_store=self.vector_store
        )
        
        # Should be skipped
        self.assertTrue(result2.get('skipped', False))
        self.assertEqual(result2['chunks'], 0)
        self.assertEqual(result2['reason'], 'unchanged')
        # Vector store should not be called again
        self.assertEqual(len(self.vector_store.upsert_calls), 1)
    
    def test_upsert_document_idempotency_different_content(self):
        """Test that different content with same doc_id processes again."""
        content1 = "First content"
        content2 = "Second different content"
        
        # First upsert
        result1 = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=content1.encode('utf-8'),
            vector_store=self.vector_store
        )
        
        self.assertFalse(result1.get('skipped', False))
        self.assertEqual(len(self.vector_store.upsert_calls), 1)
        
        # Second upsert with different content
        result2 = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=content2.encode('utf-8'),
            vector_store=self.vector_store
        )
        
        # Should process again (different checksum)
        self.assertFalse(result2.get('skipped', False))
        self.assertGreater(result2['chunks'], 0)
        # Vector store should be called again
        self.assertEqual(len(self.vector_store.upsert_calls), 2)
    
    def test_upsert_document_empty_content(self):
        """Test upsert with empty content."""
        result = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=b"",
            vector_store=self.vector_store
        )
        
        self.assertEqual(result['chunks'], 0)
        self.assertEqual(result['tokens'], 0)
        self.assertTrue(result.get('skipped', False))
        self.assertEqual(result['reason'], 'no_content')
        # Vector store should not be called
        self.assertEqual(len(self.vector_store.upsert_calls), 0)
    
    def test_upsert_document_chunk_counts(self):
        """Test that chunk counts are accurate."""
        # Create text that will produce multiple chunks
        long_text = "Sentence. " * 500  # ~5000 chars
        result = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=long_text.encode('utf-8'),
            vector_store=self.vector_store,
            chunk_size=500,
            chunk_overlap=50
        )
        
        self.assertGreater(result['chunks'], 1)
        # Verify chunk count matches stored chunks
        stored_chunks = self.vector_store.get_chunk_count_for_doc(self.doc_id)
        self.assertEqual(stored_chunks, result['chunks'])
    
    def test_upsert_document_token_counts(self):
        """Test that token counts are calculated correctly."""
        text = "This is a test sentence with multiple words. " * 20
        result = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=text.encode('utf-8'),
            vector_store=self.vector_store
        )
        
        self.assertGreater(result['tokens'], 0)
        # Tokens should roughly match sum of chunk tokens
        stored_docs = self.vector_store.upsert_calls[0] if self.vector_store.upsert_calls else []
        total_chunk_tokens = sum(
            count_tokens(doc['text']) for doc in stored_docs
        )
        self.assertEqual(result['tokens'], total_chunk_tokens)
    
    def test_upsert_document_pages_count(self):
        """Test that page counts are included in summary."""
        result = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=self.test_text.encode('utf-8'),
            vector_store=self.vector_store
        )
        
        self.assertIn('pages', result)
        self.assertGreaterEqual(result['pages'], 0)
    
    def test_upsert_document_elapsed_time(self):
        """Test that elapsed time is measured."""
        result = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=self.test_text.encode('utf-8'),
            vector_store=self.vector_store
        )
        
        self.assertIn('elapsed_ms', result)
        self.assertGreaterEqual(result['elapsed_ms'], 0)
    
    def test_upsert_document_missing_vector_store(self):
        """Test that missing vector_store raises error."""
        with self.assertRaises(ValueError):
            upsert_document(
                doc_id=self.doc_id,
                bytes_or_path=self.test_text.encode('utf-8'),
                vector_store=None
            )
    
    def test_upsert_document_file_path(self):
        """Test upsert with file path instead of bytes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.test_text)
            temp_path = f.name
        
        try:
            result = upsert_document(
                doc_id=self.doc_id,
                bytes_or_path=temp_path,
                vector_store=self.vector_store
            )
            
            self.assertGreater(result['chunks'], 0)
            self.assertEqual(len(self.vector_store.upsert_calls), 1)
        finally:
            os.unlink(temp_path)
    
    def test_upsert_document_chunk_metadata(self):
        """Test that chunk metadata includes correct information."""
        result = upsert_document(
            doc_id=self.doc_id,
            bytes_or_path=self.test_text.encode('utf-8'),
            vector_store=self.vector_store
        )
        
        stored_docs = self.vector_store.upsert_calls[0]
        for i, doc in enumerate(stored_docs):
            self.assertEqual(doc['metadata']['doc_id'], self.doc_id)
            self.assertEqual(doc['metadata']['chunk_index'], i)
            self.assertEqual(doc['metadata']['total_chunks'], len(stored_docs))
            self.assertIn('checksum', doc['metadata'])


if __name__ == '__main__':
    unittest.main()
