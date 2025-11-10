"""Chat API endpoints."""
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.rag import RAGService
from app.services.chat_memory import ChatMemoryService

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with RAG."""
    try:
        rag_service = RAGService()
        memory_service = ChatMemoryService()
        
        # Get chat history
        history = await memory_service.get_history(request.session_id)
        
        # Generate response using RAG
        response = await rag_service.generate_response(
            query=request.query,
            history=history,
            session_id=request.session_id,
        )
        
        # Save to memory
        await memory_service.save_interaction(
            session_id=request.session_id,
            query=request.query,
            response=response.answer,
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
