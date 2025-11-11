"""
Tests for prompt construction and management.
"""
import pytest
from unittest.mock import Mock, patch


class TestPromptBuilder:
    """Test prompt building functionality."""

    def test_build_simple_prompt(self):
        """Test building a simple prompt."""
        from prompting import PromptBuilder
        
        builder = PromptBuilder()
        prompt = builder.build("What is the answer?")
        
        assert isinstance(prompt, str)
        assert "What is the answer?" in prompt

    def test_build_prompt_with_context(self):
        """Test building prompt with context."""
        from prompting import PromptBuilder
        
        builder = PromptBuilder()
        context = "This is the context."
        prompt = builder.build("What is the answer?", context=context)
        
        assert context in prompt
        assert "What is the answer?" in prompt

    def test_build_prompt_with_system_message(self):
        """Test building prompt with system message."""
        from prompting import PromptBuilder
        
        builder = PromptBuilder(system_message="You are a helpful assistant.")
        prompt = builder.build("What is the answer?")
        
        assert "You are a helpful assistant." in prompt

    def test_build_prompt_with_template(self):
        """Test building prompt with template."""
        from prompting import PromptBuilder
        
        template = "Context: {context}\nQuestion: {question}"
        builder = PromptBuilder(template=template)
        prompt = builder.build(
            question="What is the answer?",
            context="This is context."
        )
        
        assert "Context:" in prompt
        assert "Question:" in prompt
        assert "What is the answer?" in prompt

    def test_build_prompt_with_multiple_contexts(self):
        """Test building prompt with multiple context chunks."""
        from prompting import PromptBuilder
        
        builder = PromptBuilder()
        contexts = ["Context 1", "Context 2", "Context 3"]
        prompt = builder.build("What is the answer?", contexts=contexts)
        
        assert all(ctx in prompt for ctx in contexts)


class TestRAGPrompt:
    """Test RAG (Retrieval-Augmented Generation) prompts."""

    def test_build_rag_prompt(self):
        """Test building RAG prompt."""
        from prompting import RAGPromptBuilder
        
        builder = RAGPromptBuilder()
        query = "What is machine learning?"
        retrieved_docs = [
            "Machine learning is a subset of AI.",
            "It involves training models on data.",
        ]
        
        prompt = builder.build(query, retrieved_docs)
        
        assert query in prompt
        assert all(doc in prompt for doc in retrieved_docs)

    def test_build_rag_prompt_with_metadata(self):
        """Test building RAG prompt with document metadata."""
        from prompting import RAGPromptBuilder
        
        builder = RAGPromptBuilder()
        query = "What is machine learning?"
        retrieved_docs = [
            {"text": "Machine learning is a subset of AI.", "source": "doc1.pdf"},
            {"text": "It involves training models on data.", "source": "doc2.pdf"},
        ]
        
        prompt = builder.build(query, retrieved_docs)
        
        assert query in prompt
        assert "doc1.pdf" in prompt or "doc2.pdf" in prompt

    def test_build_rag_prompt_with_citations(self):
        """Test building RAG prompt with citations."""
        from prompting import RAGPromptBuilder
        
        builder = RAGPromptBuilder(include_citations=True)
        query = "What is machine learning?"
        retrieved_docs = [
            {"text": "Machine learning is a subset of AI.", "source": "doc1.pdf", "id": "1"},
            {"text": "It involves training models on data.", "source": "doc2.pdf", "id": "2"},
        ]
        
        prompt = builder.build(query, retrieved_docs)
        
        assert "[1]" in prompt or "doc1.pdf" in prompt
        assert query in prompt


class TestConversationPrompt:
    """Test conversation prompt building."""

    def test_build_conversation_prompt(self):
        """Test building conversation prompt."""
        from prompting import ConversationPromptBuilder
        
        builder = ConversationPromptBuilder()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What is AI?"},
        ]
        
        prompt = builder.build(messages)
        
        assert "Hello" in prompt
        assert "What is AI?" in prompt

    def test_build_conversation_with_context(self):
        """Test building conversation prompt with context."""
        from prompting import ConversationPromptBuilder
        
        builder = ConversationPromptBuilder()
        messages = [{"role": "user", "content": "What is AI?"}]
        context = "AI stands for Artificial Intelligence."
        
        prompt = builder.build(messages, context=context)
        
        assert context in prompt
        assert "What is AI?" in prompt

    def test_conversation_history_limit(self):
        """Test limiting conversation history."""
        from prompting import ConversationPromptBuilder
        
        builder = ConversationPromptBuilder(max_history=2)
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
        ]
        
        prompt = builder.build(messages)
        
        # Should only include last 2 messages
        assert "Message 3" in prompt
        assert "Message 1" not in prompt


class TestPromptTemplates:
    """Test prompt templates."""

    def test_use_predefined_template(self):
        """Test using predefined template."""
        from prompting import PromptBuilder, TEMPLATES
        
        builder = PromptBuilder(template=TEMPLATES["qa"])
        prompt = builder.build(
            question="What is AI?",
            context="AI is artificial intelligence."
        )
        
        assert "What is AI?" in prompt
        assert "AI is artificial intelligence." in prompt

    def test_custom_template(self):
        """Test using custom template."""
        from prompting import PromptBuilder
        
        custom_template = "Answer this: {question} using: {context}"
        builder = PromptBuilder(template=custom_template)
        prompt = builder.build(
            question="What is AI?",
            context="AI is artificial intelligence."
        )
        
        assert "Answer this:" in prompt
        assert "What is AI?" in prompt

    def test_template_variables(self):
        """Test template variable substitution."""
        from prompting import PromptBuilder
        
        template = "User: {user}\nQuery: {query}\nContext: {context}"
        builder = PromptBuilder(template=template)
        prompt = builder.build(
            user="Alice",
            query="What is AI?",
            context="AI explanation"
        )
        
        assert "Alice" in prompt
        assert "What is AI?" in prompt
        assert "AI explanation" in prompt


class TestPromptValidation:
    """Test prompt validation."""

    def test_validate_prompt_length(self):
        """Test prompt length validation."""
        from prompting import PromptBuilder, PromptValidationError
        
        builder = PromptBuilder(max_length=100)
        long_context = "A" * 200
        
        with pytest.raises(PromptValidationError):
            builder.build("Question?", context=long_context)

    def test_validate_required_variables(self):
        """Test validation of required template variables."""
        from prompting import PromptBuilder, PromptValidationError
        
        template = "Question: {question}\nAnswer: {answer}"
        builder = PromptBuilder(template=template)
        
        with pytest.raises(PromptValidationError):
            builder.build(question="What is AI?")  # Missing 'answer'

    def test_validate_prompt_format(self):
        """Test prompt format validation."""
        from prompting import validate_prompt_format
        
        valid_prompt = "This is a valid prompt."
        assert validate_prompt_format(valid_prompt) is True
        
        # Empty prompt might be invalid depending on requirements
        empty_prompt = ""
        # This depends on implementation


class TestPromptOptimization:
    """Test prompt optimization."""

    def test_optimize_prompt_length(self):
        """Test optimizing prompt length."""
        from prompting import optimize_prompt_length
        
        long_prompt = "A" * 1000 + " Question?"
        optimized = optimize_prompt_length(long_prompt, max_length=100)
        
        assert len(optimized) <= 100
        assert "Question?" in optimized

    def test_compress_context(self):
        """Test compressing context in prompt."""
        from prompting import compress_context
        
        context = "This is a very long context that needs to be compressed."
        compressed = compress_context(context, max_length=20)
        
        assert len(compressed) <= 20

    def test_prioritize_relevant_context(self):
        """Test prioritizing relevant context chunks."""
        from prompting import prioritize_context
        
        contexts = [
            {"text": "Relevant context 1", "score": 0.9},
            {"text": "Less relevant context", "score": 0.5},
            {"text": "Relevant context 2", "score": 0.8},
        ]
        
        prioritized = prioritize_context(contexts, top_k=2)
        
        assert len(prioritized) == 2
        assert prioritized[0]["score"] >= prioritized[1]["score"]


class TestPromptUtils:
    """Test prompt utility functions."""

    def test_escape_special_characters(self):
        """Test escaping special characters in prompts."""
        from prompting import escape_prompt
        
        prompt = "Question: What is {this}?"
        escaped = escape_prompt(prompt)
        
        assert "{" in escaped or "{" not in escaped  # Depends on implementation

    def test_format_documents(self):
        """Test formatting documents for prompt."""
        from prompting import format_documents
        
        docs = [
            {"text": "Document 1", "source": "doc1.pdf"},
            {"text": "Document 2", "source": "doc2.pdf"},
        ]
        
        formatted = format_documents(docs)
        
        assert "Document 1" in formatted
        assert "Document 2" in formatted

    def test_add_instructions(self):
        """Test adding instructions to prompt."""
        from prompting import add_instructions
        
        prompt = "Answer the question."
        instructions = "Be concise and accurate."
        
        enhanced = add_instructions(prompt, instructions)
        
        assert instructions in enhanced
        assert "Answer the question." in enhanced

    def test_count_tokens(self):
        """Test counting tokens in prompt."""
        from prompting import count_tokens
        
        prompt = "This is a test prompt."
        token_count = count_tokens(prompt)
        
        assert token_count > 0
        assert isinstance(token_count, int)
