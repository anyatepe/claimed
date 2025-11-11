# Test Suite

This directory contains comprehensive pytest test files for the application.

## Test Files

- `test_ingestion.py` - Tests for document ingestion (PDF, etc.)
- `test_chunking.py` - Tests for text chunking strategies
- `test_embeddings.py` - Tests for embedding generation
- `test_vector_store_contract.py` - Tests for vector store interface/contract
- `test_retriever.py` - Tests for retrieval functionality
- `test_prompting.py` - Tests for prompt construction
- `test_chat_endpoints.py` - Tests for chat API endpoints
- `test_auth_rate_limit.py` - Tests for authentication and rate limiting

## Fixtures

Shared fixtures are defined in `conftest.py`:
- `sample_pdf_path` - Sample PDF file for testing
- `sample_pdf_path_multi_page` - Multi-page PDF file
- `sample_text_content` - Sample text content
- `sample_chunks` - Sample text chunks
- `sample_embeddings` - Sample embeddings
- `mock_vector_store` - Mock vector store
- `mock_embedding_model` - Mock embedding model
- `mock_llm` - Mock LLM
- `sample_metadata` - Sample metadata
- `temp_dir` - Temporary directory
- `mock_request` - Mock HTTP request
- `mock_user` - Mock user

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ingestion.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/test_ingestion.py::TestPDFIngestion::test_ingest_pdf_success
```

## Coverage

The test suite aims for >=80% code coverage. Run coverage reports with:

```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

## Requirements

Install test dependencies:

```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio fastapi[all]
```
