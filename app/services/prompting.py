"""Prompt building service for PDF RAG assistant."""


def build_chat_prompt(query, contexts, system_style="You are a PDF RAG assistant that cites sources as [doc_id:page]."):
    """
    Build a chat prompt with query and contexts.
    
    Args:
        query: The user's query string
        contexts: List of context dictionaries, each containing:
            - doc_id: Document identifier
            - page: Page number
            - content: Text content from the document
        system_style: System message style/instruction
    
    Returns:
        List of message dictionaries with 'role' and 'content' keys
    """
    messages = []
    
    # Add system message
    messages.append({
        "role": "system",
        "content": system_style
    })
    
    # Build context content with citations
    context_parts = []
    for ctx in contexts:
        doc_id = ctx.get("doc_id", "")
        page = ctx.get("page", "")
        content = ctx.get("content", "")
        
        # Add citation marker
        citation = f"[{doc_id}:{page}]" if doc_id and page else ""
        context_parts.append(f"{content} {citation}".strip())
    
    # Combine contexts
    context_text = "\n\n".join(context_parts)
    
    # Build user message with context and query
    user_content = f"Context:\n{context_text}\n\nQuestion: {query}"
    
    messages.append({
        "role": "user",
        "content": user_content
    })
    
    return messages


def build_citation_footer(contexts):
    """
    Build a citation footer string with references.
    
    Args:
        contexts: List of context dictionaries, each containing:
            - doc_id: Document identifier
            - page: Page number
            - content: Optional text content
    
    Returns:
        String with formatted references
    """
    if not contexts:
        return ""
    
    # Collect unique citations
    citations = {}
    for ctx in contexts:
        doc_id = ctx.get("doc_id", "")
        page = ctx.get("page", "")
        
        if doc_id and page:
            citation_key = f"{doc_id}:{page}"
            if citation_key not in citations:
                citations[citation_key] = {
                    "doc_id": doc_id,
                    "page": page
                }
    
    if not citations:
        return ""
    
    # Build footer
    footer_parts = ["\n\nReferences:"]
    for citation_key in sorted(citations.keys()):
        citation = citations[citation_key]
        footer_parts.append(f"[{citation['doc_id']}:{citation['page']}] - Document: {citation['doc_id']}, Page: {citation['page']}")
    
    return "\n".join(footer_parts)
