"""
Shared pytest fixtures for all tests.
"""
import pytest
import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, MagicMock
import io


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Path:
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "sample.pdf"
    # Create a minimal valid PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def sample_pdf_path_multi_page(tmp_path: Path) -> Path:
    """Create a multi-page sample PDF file for testing."""
    pdf_path = tmp_path / "sample_multi.pdf"
    # Create a minimal multi-page PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R 4 0 R]
/Count 2
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 5 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 6 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
5 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Page One) Tj
ET
endstream
endobj
6 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Page Two) Tj
ET
endstream
endobj
xref
0 7
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000200 00000 n 
0000000285 00000 n 
0000000370 00000 n 
trailer
<<
/Size 7
/Root 1 0 R
>>
startxref
451
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def sample_text_content() -> str:
    """Sample text content for testing."""
    return """This is a sample document for testing purposes.
It contains multiple sentences and paragraphs.

This is the second paragraph with more content.
It includes various words and concepts that can be used for testing
chunking, embedding, and retrieval functionality.

The document continues with additional information.
This helps test how the system handles longer documents."""


@pytest.fixture
def sample_chunks() -> list[str]:
    """Sample text chunks for testing."""
    return [
        "This is the first chunk of text.",
        "This is the second chunk of text.",
        "This is the third chunk of text with more content.",
    ]


@pytest.fixture
def sample_embeddings() -> list[list[float]]:
    """Sample embeddings for testing."""
    return [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.6, 0.7, 0.8, 0.9, 1.0],
        [0.2, 0.3, 0.4, 0.5, 0.6],
    ]


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    store = Mock()
    store.add.return_value = None
    store.search.return_value = [
        {"id": "1", "text": "Sample text 1", "score": 0.95},
        {"id": "2", "text": "Sample text 2", "score": 0.85},
    ]
    store.delete.return_value = True
    store.get.return_value = {"id": "1", "text": "Sample text", "metadata": {}}
    return store


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for testing."""
    model = Mock()
    model.embed.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    model.embed_batch.return_value = [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.6, 0.7, 0.8, 0.9, 1.0],
    ]
    return model


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = Mock()
    llm.generate.return_value = "This is a generated response."
    llm.chat.return_value = "This is a chat response."
    return llm


@pytest.fixture
def sample_metadata() -> dict:
    """Sample metadata for testing."""
    return {
        "source": "test_document.pdf",
        "page": 1,
        "chunk_index": 0,
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Temporary directory for testing."""
    return tmp_path


@pytest.fixture
def mock_request():
    """Mock HTTP request for testing."""
    request = Mock()
    request.headers = {"Authorization": "Bearer test_token"}
    request.remote_addr = "127.0.0.1"
    request.method = "GET"
    request.path = "/api/chat"
    return request


@pytest.fixture
def mock_user():
    """Mock user for authentication testing."""
    user = Mock()
    user.id = "user123"
    user.email = "test@example.com"
    user.is_authenticated = True
    return user
