"""Unit tests for chatbot service."""

import unittest
from unittest.mock import Mock, patch

from app.services.chatbot import answer_query


class TestChatbot(unittest.TestCase):
    """Test cases for chatbot answer_query function."""

    @patch('app.services.chatbot.memory')
    @patch('app.services.chatbot.retriever')
    @patch('app.services.chatbot.prompting')
    @patch('app.services.chatbot.llm')
    def test_answer_query_plumbing(self, mock_llm, mock_prompting, mock_retriever, mock_memory):
        """Test that answer_query calls all dependencies correctly."""
        # Setup mocks
        mock_session_id = "test_session_123"
        mock_user_query = "What is machine learning?"
        mock_retrieval_k = 6
        mock_filters = {"category": "ai"}
        
        mock_history = [{"role": "user", "content": "Hello"}]
        mock_contexts = [
            {"id": "1", "content": "Context 1"},
            {"id": "2", "content": "Context 2"}
        ]
        mock_prompt = "Answer the question: What is machine learning?"
        mock_llm_output = "Machine learning is a subset of AI..."
        
        mock_memory.load_history.return_value = mock_history
        mock_retriever.retrieve.return_value = mock_contexts
        mock_prompting.build_chat_prompt.return_value = mock_prompt
        mock_llm.chat.return_value = mock_llm_output
        
        # Execute
        result = answer_query(mock_session_id, mock_user_query, retrieval_k=mock_retrieval_k, filters=mock_filters)
        
        # Assert plumbing - verify all dependencies were called correctly
        mock_memory.load_history.assert_called_once_with(mock_session_id)
        mock_retriever.retrieve.assert_called_once_with(mock_user_query, k=mock_retrieval_k, filters=mock_filters)
        mock_prompting.build_chat_prompt.assert_called_once_with(mock_user_query, mock_contexts)
        mock_llm.chat.assert_called_once_with(mock_prompt)
        mock_memory.save_turn.assert_called_once_with(mock_session_id, mock_user_query, mock_llm_output)
        
        # Assert return value structure
        self.assertEqual(result["answer"], mock_llm_output)
        self.assertEqual(result["citations"], mock_contexts)
        self.assertEqual(result["session_id"], mock_session_id)

    @patch('app.services.chatbot.memory')
    @patch('app.services.chatbot.retriever')
    @patch('app.services.chatbot.prompting')
    @patch('app.services.chatbot.llm')
    def test_answer_query_citations_presence(self, mock_llm, mock_prompting, mock_retriever, mock_memory):
        """Test that citations are present in the response."""
        # Setup mocks
        mock_session_id = "test_session_456"
        mock_user_query = "Explain neural networks"
        mock_contexts = [
            {"id": "doc1", "content": "Neural networks are...", "source": "book1"},
            {"id": "doc2", "content": "They consist of layers...", "source": "book2"},
            {"id": "doc3", "content": "Training involves...", "source": "book3"}
        ]
        
        mock_memory.load_history.return_value = []
        mock_retriever.retrieve.return_value = mock_contexts
        mock_prompting.build_chat_prompt.return_value = "Prompt with contexts"
        mock_llm.chat.return_value = "Neural networks are computational models..."
        
        # Execute
        result = answer_query(mock_session_id, mock_user_query, retrieval_k=3)
        
        # Assert citations are present
        self.assertIn("citations", result)
        self.assertEqual(result["citations"], mock_contexts)
        self.assertEqual(len(result["citations"]), 3)
        self.assertEqual(result["citations"][0]["id"], "doc1")
        self.assertEqual(result["citations"][1]["id"], "doc2")
        self.assertEqual(result["citations"][2]["id"], "doc3")

    @patch('app.services.chatbot.memory')
    @patch('app.services.chatbot.retriever')
    @patch('app.services.chatbot.prompting')
    @patch('app.services.chatbot.llm')
    def test_answer_query_default_parameters(self, mock_llm, mock_prompting, mock_retriever, mock_memory):
        """Test that default parameters work correctly."""
        # Setup mocks
        mock_session_id = "test_session_789"
        mock_user_query = "What is Python?"
        
        mock_memory.load_history.return_value = []
        mock_retriever.retrieve.return_value = []
        mock_prompting.build_chat_prompt.return_value = "Prompt"
        mock_llm.chat.return_value = "Python is a programming language."
        
        # Execute with default parameters
        result = answer_query(mock_session_id, mock_user_query)
        
        # Assert default retrieval_k=6 is used
        mock_retriever.retrieve.assert_called_once_with(mock_user_query, k=6, filters=None)
        
        # Assert result structure
        self.assertIn("answer", result)
        self.assertIn("citations", result)
        self.assertIn("session_id", result)
        self.assertEqual(result["session_id"], mock_session_id)


if __name__ == '__main__':
    unittest.main()
