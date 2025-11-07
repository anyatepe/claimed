"""Vector store implementation using pgvector for PostgreSQL."""

import asyncpg
import json
from typing import List, Dict, Any, Optional
from pgvector.asyncpg import register_vector


class VectorStore:
    """Vector store for storing and searching document embeddings using pgvector."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        user: str = "postgres",
        password: str = "postgres",
        table_name: str = "document_vectors"
    ):
        """
        Initialize VectorStore.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            table_name: Name of the table to store vectors
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.table_name = table_name
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create connection pool and initialize database schema."""
        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            min_size=1,
            max_size=10
        )
        
        async with self._pool.acquire() as conn:
            # Register pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Register vector type for asyncpg
            await register_vector(conn)
            
            # Create table if it doesn't exist
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    doc_id VARCHAR(255) NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding vector(1536) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(doc_id, chunk_index)
                )
            """)
            
            # Create index for vector similarity search
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx 
                ON {self.table_name} 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            # Create index on doc_id for faster lookups
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_doc_id_idx 
                ON {self.table_name} (doc_id)
            """)
    
    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def add_document(
        self,
        doc_id: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a document with its chunks and embeddings.
        
        Args:
            doc_id: Unique document identifier
            chunks: List of text chunks
            embeddings: List of embedding vectors (each should be a list of floats)
            metadata: Optional metadata dictionary to store with the document
            
        Raises:
            ValueError: If chunks and embeddings lengths don't match
            RuntimeError: If not connected to database
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        if len(chunks) != len(embeddings):
            raise ValueError(f"Number of chunks ({len(chunks)}) must match number of embeddings ({len(embeddings)})")
        
        if metadata is None:
            metadata = {}
        
        async with self._pool.acquire() as conn:
            await register_vector(conn)
            
            # Delete existing chunks for this doc_id
            await conn.execute(
                f"DELETE FROM {self.table_name} WHERE doc_id = $1",
                doc_id
            )
            
            # Insert chunks and embeddings
            for chunk_index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                await conn.execute(
                    f"""
                    INSERT INTO {self.table_name} 
                    (doc_id, chunk_index, chunk_text, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    doc_id,
                    chunk_index,
                    chunk,
                    embedding,
                    json.dumps(metadata)
                )
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            
        Returns:
            List of dictionaries containing:
                - doc_id: Document identifier
                - chunk_index: Index of the chunk
                - chunk_text: Text content of the chunk
                - similarity: Cosine similarity score (1 - distance)
                - metadata: Document metadata
                
        Raises:
            RuntimeError: If not connected to database
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            await register_vector(conn)
            
            # Use cosine distance (1 - cosine similarity)
            # pgvector's <=> operator returns cosine distance
            # We convert it to similarity by doing 1 - distance
            results = await conn.fetch(
                f"""
                SELECT 
                    doc_id,
                    chunk_index,
                    chunk_text,
                    1 - (embedding <=> $1::vector) as similarity,
                    metadata
                FROM {self.table_name}
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                query_embedding,
                top_k
            )
            
            return [
                {
                    "doc_id": row["doc_id"],
                    "chunk_index": row["chunk_index"],
                    "chunk_text": row["chunk_text"],
                    "similarity": float(row["similarity"]),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                }
                for row in results
            ]
    
    async def delete_document(self, doc_id: str):
        """
        Delete all chunks for a document.
        
        Args:
            doc_id: Document identifier to delete
        """
        if not self._pool:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {self.table_name} WHERE doc_id = $1",
                doc_id
            )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
