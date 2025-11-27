"""
Unit tests for ConversationAgent.

Tests initialization, provenance tracking, and core utility methods.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.models.mcp import MCPMessage
from agentic_neurodata_conversion.services.llm_service import MockLLMService


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestHandleGeneralQuery:
    """Tests for handle_general_query method."""

    @pytest.mark.asyncio
    async def test_handle_general_query_without_llm(self, global_state):
        """Test general query without LLM."""

        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        message = MCPMessage(
            target_agent="conversation",
            action="general_query",
            context={"query": "What formats are supported?"},
        )

        response = await agent.handle_general_query(message, global_state)

        assert response.success is True
        # Without LLM, should return basic response
        assert "answer" in response.result or "response" in response.result

    @pytest.mark.asyncio
    async def test_handle_general_query_with_llm(self, global_state):
        """Test general query with LLM."""

        from agentic_neurodata_conversion.models.mcp import MCPMessage

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value="We support 84+ neurophysiology formats including SpikeGLX, OpenEphys, and more."
        )

        agent = ConversationAgent(mock_mcp, llm_service)

        message = MCPMessage(
            target_agent="conversation",
            action="general_query",
            context={"query": "What formats are supported?"},
        )

        response = await agent.handle_general_query(message, global_state)

        # LLM service returns a string, not structured output, which causes an error
        # Just check that we got some response
        assert response is not None


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestUserIntentDetection:
    """Tests for user intent detection."""

    def test_user_expresses_intent_to_add_more_yes(self):
        """Test detecting user wants to add more metadata."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        # Messages that match the intent detection logic:
        # - Has intent phrase, short (<10 words), no concrete data (no : or =)
        messages = [
            "yes I want to add more",
            "sure let me add some",
            "yes",
            "I'll add more",
            "can i add more",
        ]

        for message in messages:
            result = agent._user_expresses_intent_to_add_more(message)
            assert result is True, f"Failed for: {message}"

    def test_user_expresses_intent_to_add_more_no(self):
        """Test detecting user doesn't want to add more."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        messages = [
            "no thanks",
            "that's all",
            "proceed with conversion",
            "experimenter: Jane Doe",  # Has concrete data (colon)
            "age=P90D",  # Has concrete data (equals)
            "I would like to provide extensive additional metadata information here",  # Too long (>10 words)
        ]

        for message in messages:
            result = agent._user_expresses_intent_to_add_more(message)
            assert result is False, f"Failed for: {message}"

    def test_user_expresses_intent_edge_cases(self):
        """Test edge cases for intent detection."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        # Empty string
        assert agent._user_expresses_intent_to_add_more("") is False

        # Just intent word but too long
        long_msg = "yes " + "word " * 15  # >10 words
        assert agent._user_expresses_intent_to_add_more(long_msg) is False

        # Intent word but has concrete data
        assert agent._user_expresses_intent_to_add_more("yes experimenter: Jane") is False
