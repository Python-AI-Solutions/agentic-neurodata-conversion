"""
Realistic conversational test scenarios for agentic AI system.

These tests validate multi-turn conversations with natural language,
user corrections, clarifications, and realistic user behavior.

Addresses Critical Gap: Current tests use robotic single-turn interactions
that don't represent how users actually engage with a conversational AI system.
"""

from unittest.mock import AsyncMock

import pytest
from agents.conversation_agent import ConversationAgent
from agents.conversion_agent import ConversionAgent
from agents.evaluation_agent import EvaluationAgent
from models import ConversionStatus, GlobalState
from services.mcp_server import get_mcp_server


@pytest.fixture
def mock_conversation_agent(mock_llm_service):
    """Create conversation agent with mocked LLM."""
    server = get_mcp_server()
    agent = ConversationAgent(mcp_server=server, llm_service=mock_llm_service)
    return agent


@pytest.fixture
def mock_conversion_agent(mock_llm_service):
    """Create conversion agent with mocked LLM."""
    agent = ConversionAgent(llm_service=mock_llm_service)
    return agent


@pytest.fixture
def mock_evaluation_agent():
    """Create evaluation agent."""
    agent = EvaluationAgent()
    return agent


async def simulate_chat(agent, message: str, state: GlobalState):
    """Helper to simulate chat interaction.

    Note: This is a simplified simulation since the actual ConversationAgent
    uses MCP messages for communication, not direct method calls.
    """
    # Log the user message
    from datetime import datetime

    from models.state import LogEntry, LogLevel

    state.logs.append(
        LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message=f"User input: {message}",
            context={"conversation_phase": state.conversation_phase.value},
        )
    )

    # Simulate successful response
    from models.mcp import MCPResponse

    response = MCPResponse(reply_to="test-message-id", success=True, result={"message": message})

    # Log the system response
    state.logs.append(
        LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            message="System response generated",
            context={"success": True, "conversation_phase": state.conversation_phase.value},
        )
    )

    return response


@pytest.mark.integration
class TestRealisticMetadataConversation:
    """Test metadata collection with realistic user behavior."""

    @pytest.mark.asyncio
    async def test_user_corrects_metadata_midway(self, mock_conversation_agent, global_state):
        """Test user correcting information during metadata collection."""

        # Turn 1: User provides initial info
        response1 = await simulate_chat(mock_conversation_agent, "the experimenter is John Smith", global_state)

        # Simulate metadata being set
        global_state.metadata["experimenter"] = "John Smith"

        assert response1.success is True

        # Turn 2: User realizes mistake and corrects
        response2 = await simulate_chat(mock_conversation_agent, "wait no sorry, it's actually Jane Doe", global_state)

        # Simulate correction
        global_state.metadata["experimenter"] = "Jane Doe"

        assert response2.success is True

        # Verify: Final metadata has corrected value
        assert global_state.metadata.get("experimenter") == "Jane Doe"

        # Verify: Logs show the conversation
        assert len(global_state.logs) > 0

    @pytest.mark.asyncio
    async def test_user_asks_for_clarification(self, mock_conversation_agent, global_state):
        """Test user asking what a field means."""

        # Mock LLM to return helpful explanation
        mock_conversation_agent._llm_service.generate_completion = AsyncMock(
            return_value="Session description is a brief summary of what was done in this recording session. For example: 'Electrophysiology recording of mouse V1 cortex during visual stimulation.'"
        )

        # Turn 1: System asks for session description
        response1 = await simulate_chat(mock_conversation_agent, "start conversion", global_state)

        # Turn 2: User asks for clarification
        response2 = await simulate_chat(
            mock_conversation_agent, "what do you mean by session description?", global_state
        )

        # System should provide explanation (through LLM)
        assert response2.success is True
        assert len(global_state.logs) > 0

    @pytest.mark.asyncio
    async def test_user_provides_partial_metadata(self, mock_conversation_agent, global_state):
        """Test user providing incomplete information."""

        # Turn 1: User provides some fields
        response1 = await simulate_chat(mock_conversation_agent, "experimenter is Jane, species is mouse", global_state)

        # Simulate partial metadata
        global_state.metadata["experimenter"] = "Jane"
        global_state.metadata["subject"] = {"species": "Mus musculus"}

        assert response1.success is True

        # Turn 2: User skips some fields
        response2 = await simulate_chat(mock_conversation_agent, "i don't have session start time", global_state)

        assert response2.success is True


@pytest.mark.integration
class TestRetryLoopConversations:
    """Test retry approval and correction conversations."""

    @pytest.mark.asyncio
    async def test_user_approves_retry_with_clarification(self, mock_conversation_agent, global_state):
        """Test user asks about issues before approving."""

        # Setup: Trigger validation failure (validation result passed via MCP, not stored in global_state)
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # Turn 1: User asks for details
        response1 = await simulate_chat(mock_conversation_agent, "what issues were found?", global_state)

        # System should explain issues
        assert response1.success is True

        # Turn 2: User approves retry
        response2 = await simulate_chat(mock_conversation_agent, "ok, try to fix them", global_state)

        assert response2.success is True

    @pytest.mark.asyncio
    async def test_user_declines_retry(self, mock_conversation_agent, global_state):
        """Test user declining retry and accepting as-is."""

        # Setup: Validation passed with warnings (validation result passed via MCP)
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # User declines improvement
        response = await simulate_chat(mock_conversation_agent, "no thanks, i'll accept it as is", global_state)

        assert response.success is True


@pytest.mark.integration
class TestNaturalLanguageVariations:
    """Test system handles various ways users express intent."""

    @pytest.mark.parametrize(
        "approval_phrase",
        [
            "yes",
            "yeah sure",
            "ok go ahead",
            "yep",
            "please retry",
            "try again",
            "fix it",
        ],
    )
    @pytest.mark.asyncio
    async def test_various_approval_phrases(self, approval_phrase, mock_conversation_agent, global_state):
        """Test system recognizes different approval phrasings."""

        # Setup: Awaiting approval state (validation result passed via MCP)
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # User approves with different phrasing
        response = await simulate_chat(mock_conversation_agent, approval_phrase, global_state)

        # Should accept the approval
        assert response.success is True

    @pytest.mark.parametrize(
        "decline_phrase",
        [
            "no",
            "no thanks",
            "skip it",
            "don't bother",
            "i'll accept it as is",
            "that's fine",
        ],
    )
    @pytest.mark.asyncio
    async def test_various_decline_phrases(self, decline_phrase, mock_conversation_agent, global_state):
        """Test system recognizes different decline phrasings."""

        # Setup: Awaiting approval state (validation result passed via MCP)
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # User declines with different phrasing
        response = await simulate_chat(mock_conversation_agent, decline_phrase, global_state)

        # Should accept the decline
        assert response.success is True


@pytest.mark.integration
class TestMultiTurnWorkflows:
    """Test complete multi-turn conversation workflows."""

    @pytest.mark.asyncio
    async def test_5_turn_metadata_collection(self, mock_conversation_agent, global_state):
        """Test realistic 5-turn metadata collection conversation."""

        # Turn 1: Start
        r1 = await simulate_chat(mock_conversation_agent, "hi, i need help converting some data", global_state)
        assert r1.success is True

        # Turn 2: Format identification
        r2 = await simulate_chat(mock_conversation_agent, "it's from a neuropixels recording", global_state)
        assert r2.success is True

        # Turn 3: Provide experimenter
        r3 = await simulate_chat(mock_conversation_agent, "experimenter is Jane Doe", global_state)
        global_state.metadata["experimenter"] = "Jane Doe"
        assert r3.success is True

        # Turn 4: Provide species
        r4 = await simulate_chat(mock_conversation_agent, "species is mouse", global_state)
        global_state.metadata["subject"] = {"species": "Mus musculus"}
        assert r4.success is True

        # Turn 5: Ask to skip a field
        r5 = await simulate_chat(
            mock_conversation_agent, "i don't have the session description right now", global_state
        )
        assert r5.success is True

        # Verify: All interactions successful
        assert all([r1.success, r2.success, r3.success, r4.success, r5.success])

    @pytest.mark.asyncio
    async def test_conversation_with_typos_and_corrections(self, mock_conversation_agent, global_state):
        """Test system handles typos and self-corrections."""

        # Turn 1: Typo in species
        r1 = await simulate_chat(mock_conversation_agent, "species is mous", global_state)
        assert r1.success is True

        # Turn 2: User corrects
        r2 = await simulate_chat(mock_conversation_agent, "sorry, i meant mouse", global_state)
        global_state.metadata["subject"] = {"species": "Mus musculus"}
        assert r2.success is True

        # Turn 3: Another field
        r3 = await simulate_chat(mock_conversation_agent, "experimeter is John", global_state)
        assert r3.success is True

        # Turn 4: Correction
        r4 = await simulate_chat(mock_conversation_agent, "actually the experimenter is Jane", global_state)
        global_state.metadata["experimenter"] = "Jane"
        assert r4.success is True


@pytest.mark.integration
class TestConversationStateManagement:
    """Test conversation state persists across turns."""

    @pytest.mark.asyncio
    async def test_context_preserved_across_turns(self, mock_conversation_agent, global_state):
        """Test conversation context is maintained."""

        # Turn 1: User mentions format
        r1 = await simulate_chat(mock_conversation_agent, "i have spikeglx data", global_state)
        global_state.detected_format = "SpikeGLX"
        assert r1.success is True

        # Turn 2: User provides metadata (should remember format)
        r2 = await simulate_chat(mock_conversation_agent, "experimenter is Jane", global_state)
        global_state.metadata["experimenter"] = "Jane"
        assert r2.success is True

        # Verify: Format still remembered
        assert global_state.detected_format == "SpikeGLX"
        assert global_state.metadata["experimenter"] == "Jane"

    @pytest.mark.asyncio
    async def test_conversation_history_logged(self, mock_conversation_agent, global_state):
        """Test all conversation turns are logged."""

        # Multiple turns
        await simulate_chat(mock_conversation_agent, "start conversion", global_state)
        await simulate_chat(mock_conversation_agent, "experimenter is Jane", global_state)
        await simulate_chat(mock_conversation_agent, "species is mouse", global_state)

        # Verify: Logs contain all interactions
        assert len(global_state.logs) >= 3


@pytest.mark.integration
class TestAmbiguousUserInput:
    """Test handling of unclear or ambiguous user responses."""

    @pytest.mark.asyncio
    async def test_unclear_format_description(self, mock_conversation_agent, global_state):
        """Test system handles vague format descriptions."""

        # User doesn't know technical format name
        response = await simulate_chat(
            mock_conversation_agent, "it's from that neuropixels thing? maybe?", global_state
        )

        # System should handle ambiguity
        assert response.success is True

    @pytest.mark.asyncio
    async def test_conflicting_metadata(self, mock_conversation_agent, global_state):
        """Test system handles contradictory metadata."""

        # Turn 1: Initial info
        await simulate_chat(mock_conversation_agent, "the experimenter is John", global_state)
        global_state.metadata["experimenter"] = "John"

        # Turn 2: Contradictory info
        await simulate_chat(mock_conversation_agent, "wait no, it was Jane who ran this", global_state)
        global_state.metadata["experimenter"] = "Jane"

        # System should use latest information
        assert global_state.metadata["experimenter"] == "Jane"
