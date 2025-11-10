"""Vector store interface for document storage and similarity search."""

from abc import ABC, abstractmethod
from typing import Optional


class VectorStore(ABC):
    """Abstract interface for vector store implementations.
    
    This interface defines the contract for storing document chunks with embeddings
    and performing similarity searches. All implementations must support the
    specified metadata fields: doc_id, page, source, mime, created_at, tenant, tags.
    """

    @abstractmethod
    def upsert(self, chunks: list[dict]) -> None:
        """Insert or update document chunks in the vector store.
        
        Args:
            chunks: List of dictionaries, each containing:
                - 'embedding': list[float] - The vector embedding
                - 'doc_id': str - Unique document identifier
                - 'page': int - Page number (optional)
                - 'source': str - Source identifier (optional)
                - 'mime': str - MIME type (optional)
                - 'created_at': str or datetime - Creation timestamp (optional)
                - 'tenant': str - Tenant identifier (optional)
                - 'tags': list[str] - List of tags (optional)
                - Any additional metadata fields
        """
        pass

    @abstractmethod
    def similarity_search(
        self, 
        embedding: list[float], 
        k: int, 
        filters: Optional[dict] = None
    ) -> list[dict]:
        """Search for similar documents using vector similarity.
        
        Args:
            embedding: Query vector embedding
            k: Number of results to return
            filters: Optional dictionary of metadata filters (e.g., {'tenant': 'abc', 'tags': ['tag1']})
        
        Returns:
            List of dictionaries containing matching chunks with their metadata
            and similarity scores. Each dict should include:
                - All metadata fields (doc_id, page, source, mime, created_at, tenant, tags)
                - 'score' or 'distance': float - Similarity score or distance
        """
        pass

    @abstractmethod
    def create_index_if_needed(self) -> None:
        """Create or update the vector index if it doesn't exist or needs updating.
        
        This method should be idempotent - safe to call multiple times.
        """
        pass

    @abstractmethod
    def delete_documents(self, doc_ids: list[str]) -> int:
        """Delete all chunks associated with the given document IDs.
        
        Args:
            doc_ids: List of document IDs to delete
        
        Returns:
            Number of chunks deleted
        """
        pass
