"""Unit tests for VectorStore."""

import pytest
import asyncio
import numpy as np
from app.services.vector_store import VectorStore


# Test database configuration
TEST_DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "test_vector_db",
    "user": "postgres",
    "password": "postgres",
    "table_name": "test_document_vectors"
}


@pytest.fixture(scope="function")
async def vector_store():
    """Create a VectorStore instance for testing."""
    store = VectorStore(**TEST_DB_CONFIG)
    await store.connect()
    yield store
    await store.close()


@pytest.fixture(scope="function")
async def clean_table(vector_store):
    """Clean the test table before each test."""
    async with vector_store._pool.acquire() as conn:
        await conn.execute(f"TRUNCATE TABLE {vector_store.table_name}")
    yield
    async with vector_store._pool.acquire() as conn:
        await conn.execute(f"TRUNCATE TABLE {vector_store.table_name}")


def generate_test_embeddings(dimension: int = 1536, num_vectors: int = 5) -> list:
    """Generate random normalized embeddings for testing."""
    embeddings = []
    for _ in range(num_vectors):
        # Generate random vector and normalize it
        vec = np.random.randn(dimension).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        embeddings.append(vec.tolist())
    return embeddings


@pytest.mark.asyncio
async def test_add_document(vector_store, clean_table):
    """Test adding a document with chunks and embeddings."""
    doc_id = "test_doc_1"
    chunks = [
        "This is the first chunk of text.",
        "This is the second chunk of text.",
        "This is the third chunk of text."
    ]
    embeddings = generate_test_embeddings(dimension=1536, num_vectors=3)
    metadata = {"source": "test", "author": "test_author"}
    
    await vector_store.add_document(doc_id, chunks, embeddings, metadata)
    
    # Verify data was inserted
    async with vector_store._pool.acquire() as conn:
        result = await conn.fetch(
            f"SELECT COUNT(*) as count FROM {vector_store.table_name} WHERE doc_id = $1",
            doc_id
        )
        assert result[0]["count"] == 3


@pytest.mark.asyncio
async def test_add_document_mismatched_lengths(vector_store, clean_table):
    """Test that mismatched chunks and embeddings raise ValueError."""
    doc_id = "test_doc_2"
    chunks = ["chunk1", "chunk2"]
    embeddings = generate_test_embeddings(dimension=1536, num_vectors=3)  # 3 embeddings, 2 chunks
    
    with pytest.raises(ValueError, match="Number of chunks"):
        await vector_store.add_document(doc_id, chunks, embeddings)


@pytest.mark.asyncio
async def test_search_cosine_similarity(vector_store, clean_table):
    """Test cosine similarity search with sample embeddings."""
    # Create a reference embedding
    reference_embedding = np.random.randn(1536).astype(np.float32)
    reference_embedding = reference_embedding / np.linalg.norm(reference_embedding)
    
    # Create embeddings: one very similar, one moderately similar, one dissimilar
    similar_embedding = reference_embedding + 0.1 * np.random.randn(1536).astype(np.float32)
    similar_embedding = similar_embedding / np.linalg.norm(similar_embedding)
    
    moderate_embedding = reference_embedding + 0.5 * np.random.randn(1536).astype(np.float32)
    moderate_embedding = moderate_embedding / np.linalg.norm(moderate_embedding)
    
    dissimilar_embedding = np.random.randn(1536).astype(np.float32)
    dissimilar_embedding = dissimilar_embedding / np.linalg.norm(dissimilar_embedding)
    
    # Add documents
    await vector_store.add_document(
        "doc_similar",
        ["Similar chunk"],
        [similar_embedding.tolist()],
        {"type": "similar"}
    )
    
    await vector_store.add_document(
        "doc_moderate",
        ["Moderate chunk"],
        [moderate_embedding.tolist()],
        {"type": "moderate"}
    )
    
    await vector_store.add_document(
        "doc_dissimilar",
        ["Dissimilar chunk"],
        [dissimilar_embedding.tolist()],
        {"type": "dissimilar"}
    )
    
    # Search with reference embedding
    results = await vector_store.search(reference_embedding.tolist(), top_k=3)
    
    # Verify results
    assert len(results) == 3
    
    # Verify similarity scores are in descending order
    similarities = [r["similarity"] for r in results]
    assert similarities == sorted(similarities, reverse=True)
    
    # Verify the most similar document is returned first
    assert results[0]["doc_id"] == "doc_similar"
    assert results[0]["similarity"] > results[1]["similarity"]
    assert results[1]["similarity"] > results[2]["similarity"]
    
    # Verify similarity scores are between 0 and 1 (cosine similarity range)
    for result in results:
        assert 0 <= result["similarity"] <= 1


@pytest.mark.asyncio
async def test_search_top_k(vector_store, clean_table):
    """Test that search returns correct number of results."""
    # Add multiple documents
    num_docs = 10
    for i in range(num_docs):
        embeddings = generate_test_embeddings(dimension=1536, num_vectors=1)
        await vector_store.add_document(
            f"doc_{i}",
            [f"Chunk {i}"],
            embeddings,
            {"index": i}
        )
    
    # Search with top_k=5
    query_embedding = generate_test_embeddings(dimension=1536, num_vectors=1)[0]
    results = await vector_store.search(query_embedding, top_k=5)
    
    assert len(results) == 5
    
    # Search with top_k=20 (more than available)
    results = await vector_store.search(query_embedding, top_k=20)
    assert len(results) == num_docs


@pytest.mark.asyncio
async def test_add_document_overwrites_existing(vector_store, clean_table):
    """Test that adding a document with same doc_id overwrites existing chunks."""
    doc_id = "test_doc_overwrite"
    
    # Add initial document
    await vector_store.add_document(
        doc_id,
        ["Original chunk 1", "Original chunk 2"],
        generate_test_embeddings(dimension=1536, num_vectors=2)
    )
    
    # Overwrite with new chunks
    await vector_store.add_document(
        doc_id,
        ["New chunk 1"],
        generate_test_embeddings(dimension=1536, num_vectors=1)
    )
    
    # Verify only new chunks exist
    async with vector_store._pool.acquire() as conn:
        result = await conn.fetch(
            f"SELECT COUNT(*) as count FROM {vector_store.table_name} WHERE doc_id = $1",
            doc_id
        )
        assert result[0]["count"] == 1
        
        chunk_text = await conn.fetchval(
            f"SELECT chunk_text FROM {vector_store.table_name} WHERE doc_id = $1",
            doc_id
        )
        assert chunk_text == "New chunk 1"


@pytest.mark.asyncio
async def test_delete_document(vector_store, clean_table):
    """Test deleting a document."""
    doc_id = "test_doc_delete"
    
    # Add document
    await vector_store.add_document(
        doc_id,
        ["Chunk 1", "Chunk 2"],
        generate_test_embeddings(dimension=1536, num_vectors=2)
    )
    
    # Delete document
    await vector_store.delete_document(doc_id)
    
    # Verify deletion
    async with vector_store._pool.acquire() as conn:
        result = await conn.fetch(
            f"SELECT COUNT(*) as count FROM {vector_store.table_name} WHERE doc_id = $1",
            doc_id
        )
        assert result[0]["count"] == 0


@pytest.mark.asyncio
async def test_search_with_metadata(vector_store, clean_table):
    """Test that search returns metadata correctly."""
    doc_id = "test_doc_metadata"
    metadata = {"category": "science", "year": 2024, "tags": ["ai", "ml"]}
    
    await vector_store.add_document(
        doc_id,
        ["Test chunk"],
        generate_test_embeddings(dimension=1536, num_vectors=1),
        metadata
    )
    
    query_embedding = generate_test_embeddings(dimension=1536, num_vectors=1)[0]
    results = await vector_store.search(query_embedding, top_k=1)
    
    assert len(results) == 1
    assert results[0]["metadata"] == metadata
    assert results[0]["doc_id"] == doc_id
    assert results[0]["chunk_text"] == "Test chunk"


@pytest.mark.asyncio
async def test_context_manager(vector_store, clean_table):
    """Test VectorStore as async context manager."""
    async with VectorStore(**TEST_DB_CONFIG) as store:
        assert store._pool is not None
        
        # Add a document
        await store.add_document(
            "context_test",
            ["Test"],
            generate_test_embeddings(dimension=1536, num_vectors=1)
        )
        
        # Search
        results = await store.search(
            generate_test_embeddings(dimension=1536, num_vectors=1)[0],
            top_k=1
        )
        assert len(results) == 1
    
    # Verify connection is closed
    assert store._pool is None


@pytest.mark.asyncio
async def test_cosine_similarity_calculation(vector_store, clean_table):
    """Test that cosine similarity is calculated correctly."""
    # Create two identical embeddings
    embedding = generate_test_embeddings(dimension=1536, num_vectors=1)[0]
    
    await vector_store.add_document(
        "identical_doc",
        ["Identical chunk"],
        [embedding]
    )
    
    # Search with the same embedding
    results = await vector_store.search(embedding, top_k=1)
    
    # Should have very high similarity (close to 1.0)
    assert len(results) == 1
    assert results[0]["similarity"] > 0.99  # Should be very close to 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
