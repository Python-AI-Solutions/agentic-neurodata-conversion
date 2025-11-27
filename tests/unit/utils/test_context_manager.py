"""
Unit tests for ConversationContextManager.

Tests smart conversation summarization and context management.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.utils.context_manager import ConversationContextManager
from agentic_neurodata_conversion.models.state import GlobalState


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
    return [{"role": "user", "content": f"Message {i}"} for i in range(20)]


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
        short_conversation = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

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

        long_conversation = [{"role": "user", "content": f"Message {i}"} for i in range(30)]

        result = await manager.manage_context(
            conversation_history=long_conversation,
            state=state,
        )

        # Should use simple truncation
        assert len(result) <= manager.max_messages
        # Should keep recent messages
        assert result[-1]["content"] == "Message 29"

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self, context_manager, mock_llm_service, sample_conversation, state):
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
    async def test_preserves_recent_messages(self, context_manager, mock_llm_service, sample_conversation, state):
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
        long_conversation = [{"role": "user", "content": f"Message {i}"} for i in range(60)]

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

        conversation = [{"role": "user", "content": f"Message {i}"} for i in range(12)]

        result = await manager.manage_context(
            conversation_history=conversation,
            state=state,
        )

        # Should trigger summarization (12 > 10)
        # Should keep only 5 recent messages + summary
        recent = [m for m in result if m["role"] != "system"]
        assert len(recent) == 5

    @pytest.mark.asyncio
    async def test_smart_summarization_success_path(
        self, context_manager, mock_llm_service, sample_conversation, state
    ):
        """Test successful LLM summarization with proper message creation (lines 186-203)."""
        # Mock LLM generate_completion (not generate_structured_output) to return string summary
        mock_llm_service.generate_completion = AsyncMock(
            return_value="Summary: User provided experimenter name Dr. Smith and discussed file formats."
        )

        result = await context_manager.manage_context(
            conversation_history=sample_conversation,
            state=state,
        )

        # Verify summary message structure (lines 186-191)
        assert result[0]["role"] == "system"
        assert "[Previous conversation summary]:" in result[0]["content"]
        assert result[0]["timestamp"] == "llm_generated"
        assert "metadata" in result[0]
        assert "summarized_messages" in result[0]["metadata"]
        assert "summary_tokens_approx" in result[0]["metadata"]

        # Verify logging occurred (lines 193-201)
        log_messages = [log.message for log in state.logs]
        assert any("Conversation context summarized successfully" in msg for msg in log_messages)

        # Verify compression ratio logged
        compression_log = next((log for log in state.logs if "summarized successfully" in log.message), None)
        assert compression_log is not None
        assert "original_messages" in compression_log.context
        assert "new_messages" in compression_log.context
        assert "compression_ratio" in compression_log.context

        # Verify return value (line 203)
        assert len(result) == context_manager.keep_recent + 1  # summary + recent messages

    @pytest.mark.asyncio
    async def test_format_messages_with_context_field(self, context_manager, state):
        """Test formatting messages with context metadata (lines 223-225)."""
        # Create messages with context field containing field name
        messages_with_context = [
            {"role": "user", "content": "What is your name?"},
            {
                "role": "assistant",
                "content": "I need your experimenter name",
                "context": {"field": "experimenter"},
            },
            {
                "role": "user",
                "content": "Dr. Smith",
                "context": {"field": "experimenter"},
            },
        ]

        # Call _format_messages_for_summary which should handle context field
        formatted = context_manager._format_messages_for_summary(messages_with_context)

        # Verify context field was formatted (lines 223-225)
        assert "Context: Asking for field 'experimenter'" in formatted
        assert formatted.count("Context:") == 2  # Two messages have context

    def test_estimate_tokens(self, context_manager):
        """Test token estimation method (lines 238-241)."""
        # Create conversation with known character counts
        conversation = [
            {"role": "user", "content": "Hello"},  # 5 chars
            {"role": "assistant", "content": "Hi there"},  # 8 chars
            {"role": "user", "content": "How are you?"},  # 12 chars
        ]
        # Total: 25 chars
        # Expected: 25 / 5 = 5 words, 5 * 1.3 = 6.5 -> 6 tokens

        tokens = context_manager.estimate_tokens(conversation)

        # Verify calculation (lines 238-241)
        assert isinstance(tokens, int)
        assert tokens == 6  # int(25 / 5 * 1.3) = int(6.5) = 6

    def test_estimate_tokens_empty_conversation(self, context_manager):
        """Test token estimation with empty conversation."""
        tokens = context_manager.estimate_tokens([])
        assert tokens == 0

    def test_estimate_tokens_large_conversation(self, context_manager):
        """Test token estimation with larger conversation."""
        # Create conversation with substantial content
        large_conversation = [
            {"role": "user", "content": "A" * 500},  # 500 chars
            {"role": "assistant", "content": "B" * 500},  # 500 chars
            {"role": "user", "content": "C" * 500},  # 500 chars
        ]
        # Total: 1500 chars -> 300 words -> 390 tokens

        tokens = context_manager.estimate_tokens(large_conversation)

        assert isinstance(tokens, int)
        assert tokens == 390  # int(1500 / 5 * 1.3)

    def test_should_summarize_below_threshold(self, context_manager):
        """Test should_summarize returns False when below threshold."""
        short_conversation = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

        should_summarize = context_manager.should_summarize(short_conversation)

        assert should_summarize is False

    def test_should_summarize_above_threshold(self, context_manager):
        """Test should_summarize returns True when above threshold."""
        long_conversation = [{"role": "user", "content": f"Message {i}"} for i in range(20)]

        should_summarize = context_manager.should_summarize(long_conversation)

        assert should_summarize is True

    def test_should_summarize_at_threshold(self, context_manager):
        """Test should_summarize at exact threshold."""
        # Default threshold is 15
        at_threshold_conversation = [{"role": "user", "content": f"Message {i}"} for i in range(15)]

        should_summarize = context_manager.should_summarize(at_threshold_conversation)

        # At threshold (15), should NOT summarize (only > threshold)
        assert should_summarize is False
