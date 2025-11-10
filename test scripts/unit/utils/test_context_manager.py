"""
Unit tests for ConversationContextManager.

Tests smart conversation summarization and context management.
"""
import pytest
from unittest.mock import AsyncMock, Mock

from agents.context_manager import ConversationContextManager
from models.state import GlobalState


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    service = Mock()
    service.generate_structured_output = AsyncMock()
    return service


@pytest.fixture
def context_manager(mock_llm_service):
    """Create context manager with mock LLM."""
    return ConversationContextManager(llm_service=mock_llm_service)


@pytest.fixture
def sample_conversation():
    """Create sample conversation history."""
    return [
        {"role": "user", "content": f"Message {i}"}
        for i in range(20)
    ]


@pytest.fixture
def state():
    """Create mock global state."""
    return GlobalState()


@pytest.mark.unit
class TestConversationContextManager:
    """Test suite for ConversationContextManager."""

    def test_initialization(self, mock_llm_service):
        """Test context manager initialization."""
        manager = ConversationContextManager(llm_service=mock_llm_service)
        assert manager.llm_service == mock_llm_service
        assert manager.max_messages == 50
        assert manager.keep_recent == 10
        assert manager.summarize_threshold == 15

    def test_initialization_without_llm(self):
        """Test context manager works without LLM."""
        manager = ConversationContextManager(llm_service=None)
        assert manager.llm_service is None

    @pytest.mark.asyncio
    async def test_short_conversation_no_summarization(self, context_manager, state):
        """Test that short conversations are returned as-is."""
        short_conversation = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)
        ]

        result = await context_manager.manage_context(
            conversation_history=short_conversation,
            state=state,
        )

        # Should return unchanged
        assert result == short_conversation
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_long_conversation_triggers_summarization(
        self, context_manager, mock_llm_service, sample_conversation, state
    ):
        """Test that long conversations trigger summarization."""
        # Mock LLM response - needs to be a coroutine
        async def mock_llm_response(*args, **kwargs):
            return {
                "summary": "Summary of old messages",
                "key_decisions": ["decision1", "decision2"],
                "metadata_mentioned": {"experimenter": "Dr. Smith"},
            }

        mock_llm_service.generate_structured_output = mock_llm_response

        result = await context_manager.manage_context(
            conversation_history=sample_conversation,
            state=state,
        )

        # Result should have summary message + recent messages
        assert len(result) > 0
        # First message should be the summary
        assert result[0]["role"] == "system"
        assert "Summary" in result[0]["content"] or "summary" in result[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_llm(self, state):
        """Test fallback when LLM unavailable."""
        manager = ConversationContextManager(llm_service=None)

        long_conversation = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(30)
        ]

        result = await manager.manage_context(
            conversation_history=long_conversation,
            state=state,
        )

        # Should use simple truncation
        assert len(result) <= manager.max_messages
        # Should keep recent messages
        assert result[-1]["content"] == "Message 29"

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(
        self, context_manager, mock_llm_service, sample_conversation, state
    ):
        """Test fallback when LLM call fails."""
        # Mock LLM to raise exception
        mock_llm_service.generate_structured_output.side_effect = Exception("LLM failed")

        result = await context_manager.manage_context(
            conversation_history=sample_conversation,
            state=state,
        )

        # Should fallback to simple truncation
        assert len(result) <= context_manager.max_messages
        # Should still have recent messages
        assert any("Message 19" in msg["content"] for msg in result)

    @pytest.mark.asyncio
    async def test_preserves_recent_messages(
        self, context_manager, mock_llm_service, sample_conversation, state
    ):
        """Test that recent messages are always preserved."""
        mock_llm_service.generate_structured_output.return_value = {
            "summary": "Old messages summary",
            "key_decisions": [],
            "metadata_mentioned": {},
        }

        result = await context_manager.manage_context(
            conversation_history=sample_conversation,
            state=state,
        )

        # Recent messages should be preserved
        recent_messages = [msg for msg in result if msg["role"] != "system"]
        assert len(recent_messages) == context_manager.keep_recent

        # Should have the most recent messages
        assert recent_messages[-1]["content"] == "Message 19"
        assert recent_messages[-2]["content"] == "Message 18"

    def test_simple_truncation_logic(self, context_manager, state):
        """Test the simple truncation fallback."""
        long_conversation = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(60)
        ]

        result = context_manager._simple_truncation(long_conversation, state)

        # Should return summary + recent messages (keep_recent + 1)
        assert len(result) == context_manager.keep_recent + 1
        # First message should be system summary
        assert result[0]["role"] == "system"
        # Should keep most recent
        assert result[-1]["content"] == "Message 59"

    @pytest.mark.asyncio
    async def test_custom_thresholds(self, state):
        """Test custom threshold configuration."""
        # Create a proper mock
        mock_llm = Mock()

        async def mock_llm_response(*args, **kwargs):
            return {
                "summary": "Summary",
                "key_decisions": [],
                "metadata_mentioned": {},
            }

        mock_llm.generate_structured_output = mock_llm_response

        manager = ConversationContextManager(
            llm_service=mock_llm,
            max_messages=30,
            keep_recent=5,
            summarize_threshold=10,
        )

        conversation = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(12)
        ]

        result = await manager.manage_context(
            conversation_history=conversation,
            state=state,
        )

        # Should trigger summarization (12 > 10)
        # Should keep only 5 recent messages + summary
        recent = [m for m in result if m["role"] != "system"]
        assert len(recent) == 5
