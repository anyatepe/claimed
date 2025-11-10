"""Pinecone vector store adapter."""
from typing import List, Optional
from pinecone import Pinecone, ServerlessSpec
import os


class PineconeStore:
    """Adapter for Pinecone vector store."""
    
    def __init__(self):
        api_key = os.getenv("PINECONE_API_KEY", "")
        index_name = os.getenv("PINECONE_INDEX_NAME", "rag-chat")
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)
    
    async def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ):
        """Add documents to Pinecone."""
        vectors = []
        for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
            vector_id = ids[i] if ids else f"doc_{i}"
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {**metadata, "text": text},
            })
        
        self.index.upsert(vectors=vectors)
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> List:
        """Search for similar documents in Pinecone."""
        from app.services.embeddings import EmbeddingsService
        embeddings_service = EmbeddingsService()
        query_embedding = embeddings_service.embed_query(query)
        
        results = self.index.query(
            vector=query_embedding,
            top_k=k,
            filter=filter,
            include_metadata=True,
        )
        
        # Convert to document-like objects
        class Document:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata
        
        documents = []
        for match in results.matches:
            documents.append(Document(
                page_content=match.metadata.get("text", ""),
                metadata=match.metadata,
            ))
        
        return documents
    
    async def delete(self, ids: List[str]):
        """Delete documents by IDs."""
        self.index.delete(ids=ids)
