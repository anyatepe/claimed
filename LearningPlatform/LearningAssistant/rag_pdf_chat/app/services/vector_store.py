"""Vector store service."""
from typing import List, Optional
from app.adapters.pinecone_store import PineconeStore
from app.adapters.chroma_store import ChromaStore


class VectorStoreService:
    """Service for vector store operations."""
    
    def __init__(self, store_type: str = "chroma"):
        if store_type == "pinecone":
            self.store = PineconeStore()
        else:
            self.store = ChromaStore()
    
    async def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ):
        """Add documents to the vector store."""
        return await self.store.add_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> List:
        """Search for similar documents."""
        return await self.store.similarity_search(
            query=query,
            k=k,
            filter=filter,
        )
    
    async def delete(self, ids: List[str]):
        """Delete documents by IDs."""
        return await self.store.delete(ids)
