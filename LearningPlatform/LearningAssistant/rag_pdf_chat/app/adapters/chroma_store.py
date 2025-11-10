"""ChromaDB vector store adapter."""
from typing import List, Optional
import chromadb
from chromadb.config import Settings


class ChromaStore:
    """Adapter for ChromaDB vector store."""
    
    def __init__(self):
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./chroma_db",
        ))
        self.collection = self.client.get_or_create_collection(
            name="rag_chat",
            metadata={"hnsw:space": "cosine"},
        )
    
    async def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ):
        """Add documents to ChromaDB."""
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(texts))]
        
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> List:
        """Search for similar documents in ChromaDB."""
        from app.services.embeddings import EmbeddingsService
        embeddings_service = EmbeddingsService()
        query_embedding = embeddings_service.embed_query(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter,
        )
        
        # Convert to document-like objects
        class Document:
            def __init__(self, page_content, metadata):
                self.page_content = page_content
                self.metadata = metadata
        
        documents = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                documents.append(Document(
                    page_content=doc,
                    metadata=metadata,
                ))
        
        return documents
    
    async def delete(self, ids: List[str]):
        """Delete documents by IDs."""
        self.collection.delete(ids=ids)
