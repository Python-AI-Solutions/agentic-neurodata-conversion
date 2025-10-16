"""
Unit tests for ConversationAgent edge cases and error handling.

Tests edge cases and error handling scenarios not covered in other test files:
- Markdown code block parsing
- Error handling in initialization
- Error handling in clarification
- Unknown task handling
"""

from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType
from agentic_neurodata_conversion.models.session_context import (
    SessionContext,
)


@pytest.fixture
def conversation_agent() -> ConversationAgent:
    """Create ConversationAgent instance for testing."""
    config = AgentConfig(
        agent_name="test-conversation-agent",
        agent_type="conversation",
        agent_port=8001,
        mcp_server_url="http://localhost:3000",
        llm_provider="anthropic",
        llm_api_key="test-key",
        llm_model="claude-3-5-sonnet-20241022",
        temperature=0.7,
        max_tokens=4096,
    )
    return ConversationAgent(config)


@pytest.mark.asyncio
async def test_get_capabilities_returns_correct_list(
    conversation_agent: ConversationAgent,
) -> None:
    """Test get_capabilities returns the correct capability list."""
    # Act
    capabilities = conversation_agent.get_capabilities()

    # Assert
    assert capabilities == ["initialize_session", "handle_clarification"]
    assert "initialize_session" in capabilities
    assert "handle_clarification" in capabilities


@pytest.mark.asyncio
async def test_extract_metadata_handles_llm_response_with_code_blocks(
    conversation_agent: ConversationAgent,
) -> None:
    """Test metadata extraction handles LLM response wrapped in markdown code blocks."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        readme = Path(tmpdir) / "README.md"
        readme.write_text("Subject: Mouse 001")

        # LLM response wrapped in markdown code blocks
        llm_response_with_blocks = """```json
{
    "subject_id": "Mouse 001",
    "species": "Mus musculus",
    "extraction_confidence": {"subject_id": "high"}
}
```"""

        with patch.object(
            conversation_agent, "call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = llm_response_with_blocks

            # Act
            result = await conversation_agent._extract_metadata_from_md_files(
                tmpdir, ["README.md"]
            )

            # Assert
            assert result.subject_id == "Mouse 001"
            assert result.species == "Mus musculus"


@pytest.mark.asyncio
async def test_initialize_session_handles_file_not_found_error(
    conversation_agent: ConversationAgent,
) -> None:
    """Test initialize session handles FileNotFoundError gracefully."""
    # Arrange
    session_id = "test-session-error-001"
    nonexistent_path = "/this/path/does/not/exist"

    mock_session = SessionContext(session_id=session_id)

    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        # Act
        result = await conversation_agent._initialize_session(
            session_id, nonexistent_path
        )

        # Assert
        assert result["status"] == "error"
        assert "does not exist" in result["message"].lower()


@pytest.mark.asyncio
async def test_initialize_session_handles_generic_exception(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
) -> None:
    """Test initialize session handles generic exceptions gracefully."""
    # Arrange
    session_id = "test-session-error-002"
    dataset_path = str(test_dataset_path)

    # Mock get_session_context to raise an exception
    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.side_effect = RuntimeError("Database connection failed")

        # Act
        result = await conversation_agent._initialize_session(
            session_id, dataset_path
        )

        # Assert
        assert result["status"] == "error"
        assert "Unexpected error" in result["message"]
        assert "Database connection failed" in result["message"]


@pytest.mark.asyncio
async def test_handle_clarification_handles_exception(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_clarification handles exceptions gracefully."""
    # Arrange
    session_id = "test-session-error-003"
    updated_metadata = {"subject_id": "Mouse 001"}

    # Mock get_session_context to raise an exception
    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.side_effect = RuntimeError("Session not found")

        # Act
        result = await conversation_agent._handle_clarification(
            session_id, None, updated_metadata
        )

        # Assert
        assert result["status"] == "error"
        assert "Error processing clarification" in result["message"]
        assert "Session not found" in result["message"]


@pytest.mark.asyncio
async def test_handle_message_with_unknown_task(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_message returns error for unknown task."""
    # Arrange
    session_id = "test-session-unknown"
    message = MCPMessage(
        message_id="msg-unknown",
        source_agent="mcp_server",
        target_agent="conversation_agent",
        message_type=MessageType.AGENT_EXECUTE,
        session_id=session_id,
        payload={
            "task_name": "unknown_task",
            "session_id": session_id,
            "parameters": {},
        },
    )

    # Act
    result = await conversation_agent.handle_message(message)

    # Assert
    assert result["status"] == "error"
    assert "Unknown task" in result["message"]


@pytest.mark.asyncio
async def test_handle_message_with_none_task_name(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_message handles None task_name gracefully."""
    # Arrange
    session_id = "test-session-none-task"
    message = MCPMessage(
        message_id="msg-none-task",
        source_agent="mcp_server",
        target_agent="conversation_agent",
        message_type=MessageType.AGENT_EXECUTE,
        session_id=session_id,
        payload={
            "session_id": session_id,
            "parameters": {},
            # task_name is missing
        },
    )

    # Act
    result = await conversation_agent.handle_message(message)

    # Assert
    assert result["status"] == "error"
    assert "Unknown task" in result["message"]
