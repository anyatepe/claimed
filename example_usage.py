"""Example usage of VectorStore."""

import asyncio
from app.services.vector_store import VectorStore


async def main():
    """Example usage of VectorStore."""
    # Initialize VectorStore
    vector_store = VectorStore(
        host="localhost",
        port=5432,
        database="vector_db",
        user="postgres",
        password="postgres"
    )
    
    # Connect to database
    await vector_store.connect()
    
    try:
        # Example: Add a document with chunks and embeddings
        doc_id = "example_doc_1"
        chunks = [
            "Machine learning is a subset of artificial intelligence.",
            "It enables computers to learn from data without explicit programming.",
            "Deep learning uses neural networks with multiple layers."
        ]
        
        # In practice, you would generate embeddings using a model like OpenAI, Sentence-BERT, etc.
        # For this example, we'll use dummy embeddings
        import numpy as np
        embeddings = []
        for _ in chunks:
            vec = np.random.randn(1536).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            embeddings.append(vec.tolist())
        
        metadata = {
            "source": "example",
            "category": "AI/ML",
            "author": "Example Author"
        }
        
        await vector_store.add_document(doc_id, chunks, embeddings, metadata)
        print(f"Added document: {doc_id}")
        
        # Example: Search for similar documents
        query_embedding = embeddings[0]  # Use first chunk's embedding as query
        results = await vector_store.search(query_embedding, top_k=3)
        
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Document: {result['doc_id']}")
            print(f"   Chunk Index: {result['chunk_index']}")
            print(f"   Similarity: {result['similarity']:.4f}")
            print(f"   Text: {result['chunk_text'][:50]}...")
            print(f"   Metadata: {result['metadata']}")
        
        # Example: Delete a document
        await vector_store.delete_document(doc_id)
        print(f"\nDeleted document: {doc_id}")
        
    finally:
        # Close connection
        await vector_store.close()


# Alternative: Using context manager
async def example_with_context_manager():
    """Example using VectorStore as async context manager."""
    async with VectorStore(
        host="localhost",
        port=5432,
        database="vector_db",
        user="postgres",
        password="postgres"
    ) as vector_store:
        # Add document
        import numpy as np
        chunks = ["Example text"]
        vec = np.random.randn(1536).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        embeddings = [vec.tolist()]
        
        await vector_store.add_document("doc_1", chunks, embeddings)
        
        # Search
        results = await vector_store.search(embeddings[0], top_k=5)
        print(f"Found {len(results)} results")


if __name__ == "__main__":
    asyncio.run(main())
