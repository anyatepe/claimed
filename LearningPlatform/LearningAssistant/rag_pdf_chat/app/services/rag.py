"""RAG (Retrieval-Augmented Generation) service."""
from app.services.llm import LLMService
from app.services.vector_store import VectorStoreService
from app.models.chat import ChatResponse


class RAGService:
    """Service for RAG-based chat responses."""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.vector_store = VectorStoreService()
    
    async def generate_response(
        self,
        query: str,
        history: list[dict] | None = None,
        session_id: str | None = None,
    ) -> ChatResponse:
        """Generate a response using RAG."""
        # Retrieve relevant documents
        relevant_docs = await self.vector_store.similarity_search(
            query=query,
            k=5,
        )
        
        # Generate response using LLM with context
        answer = await self.llm_service.generate(
            query=query,
            context=relevant_docs,
            history=history,
        )
        
        return ChatResponse(
            answer=answer,
            sources=[doc.metadata.get("source", "") for doc in relevant_docs],
        )
