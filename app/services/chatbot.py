"""Chatbot service for answering user queries with retrieval-augmented generation."""

from app.services import memory, retriever, prompting, llm


def answer_query(session_id, user_query, retrieval_k=6, filters=None):
    """
    Answer a user query using retrieval-augmented generation.
    
    Args:
        session_id: Unique identifier for the conversation session
        user_query: The user's query/question
        retrieval_k: Number of retrieval contexts to fetch (default: 6)
        filters: Optional filters to apply to retrieval (default: None)
    
    Returns:
        Dictionary containing:
            - answer: The LLM-generated answer
            - citations: List of retrieved contexts used
            - session_id: The session identifier
    """
    history = memory.load_history(session_id)
    contexts = retriever.retrieve(user_query, k=retrieval_k, filters=filters)
    prompt = prompting.build_chat_prompt(user_query, contexts)
    llm_out = llm.chat(prompt)
    memory.save_turn(session_id, user_query, llm_out)
    return {
        "answer": llm_out,
        "citations": contexts,
        "session_id": session_id
    }
