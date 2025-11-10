"""Chroma vector store adapter."""

import uuid
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb import ClientAPI, Collection
    from chromadb.config import Settings
except ImportError:
    raise ImportError(
        "chromadb is required for ChromaStore. Install it with: pip install chromadb"
    )

from adapters.base import VectorStore


class ChromaStore(VectorStore):
    """Chroma vector store implementation."""

    def __init__(
        self,
        collection_name: str,
        client: Optional[ClientAPI] = None,
        persist_directory: Optional[str] = None,
        collection_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize ChromaStore.

        Args:
            collection_name: Name of the Chroma collection
            client: Optional Chroma client instance. If not provided, creates a new client.
            persist_directory: Optional directory to persist data. If None, uses in-memory mode.
            collection_metadata: Optional metadata for the collection
        """
        self.collection_name = collection_name
        self.collection_metadata = collection_metadata or {}

        if client is None:
            if persist_directory is not None:
                self.client = chromadb.PersistentClient(path=persist_directory)
            else:
                self.client = chromadb.Client(Settings(anonymized_telemetry=False))
        else:
            self.client = client

        self._collection: Optional[Collection] = None

    @property
    def collection(self) -> Collection:
        """Get or create the Chroma collection."""
        if self._collection is None:
            try:
                self._collection = self.client.get_collection(
                    name=self.collection_name,
                    metadata=self.collection_metadata,
                )
            except Exception:
                # Collection doesn't exist, create it
                self._collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata=self.collection_metadata,
                )
        return self._collection

    def add_embeddings(
        self,
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add embeddings to the Chroma collection.

        Args:
            embeddings: List of embedding vectors
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of IDs for the embeddings. If not provided, generates UUIDs.

        Returns:
            List of IDs that were added
        """
        if not embeddings:
            return []

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(embeddings))]

        # Ensure metadatas list matches embeddings length
        if metadatas is None:
            metadatas = [{}] * len(embeddings)
        elif len(metadatas) != len(embeddings):
            raise ValueError(
                f"Length of metadatas ({len(metadatas)}) must match "
                f"length of embeddings ({len(embeddings)})"
            )

        if len(ids) != len(embeddings):
            raise ValueError(
                f"Length of ids ({len(ids)}) must match "
                f"length of embeddings ({len(embeddings)})"
            )

        # Add to collection
        self.collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        return ids

    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 4,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings using k-nearest neighbors.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            where: Optional metadata filter dictionary. Supports Chroma's where syntax.

        Returns:
            List of dictionaries containing 'id', 'embedding', 'metadata', and 'distance'
        """
        # Build query parameters
        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": k,
        }

        if where is not None:
            query_kwargs["where"] = where

        # Perform query
        results = self.collection.query(**query_kwargs)

        # Format results
        formatted_results = []
        if results["ids"] and len(results["ids"]) > 0:
            ids = results["ids"][0]
            embeddings = results["embeddings"][0] if results.get("embeddings") else [None] * len(ids)
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            distances = results["distances"][0] if results.get("distances") else [None] * len(ids)

            for i in range(len(ids)):
                formatted_results.append({
                    "id": ids[i],
                    "embedding": embeddings[i] if i < len(embeddings) else None,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else None,
                })

        return formatted_results

    def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Delete embeddings from the Chroma collection.

        Args:
            ids: Optional list of IDs to delete
            where: Optional metadata filter dictionary
        """
        if ids is not None:
            self.collection.delete(ids=ids)
        elif where is not None:
            self.collection.delete(where=where)
        else:
            raise ValueError("Either 'ids' or 'where' must be provided")

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection information
        """
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
            "metadata": self.collection.metadata,
        }
