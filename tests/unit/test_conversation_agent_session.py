"""
Unit tests for ConversationAgent session initialization (Task 4.4).

Tests the session initialization workflow which:
- Routes handle_message to _initialize_session
- Detects dataset format
- Validates dataset structure
- Extracts metadata from .md files
- Updates session context
- Triggers conversion agent
- Handles errors appropriately
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import Response
import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType
from agentic_neurodata_conversion.models.session_context import (
    SessionContext,
    WorkflowStage,
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


@pytest.fixture
def sample_llm_response() -> str:
    """Sample LLM response with extracted metadata."""
    return json.dumps(
        {
            "subject_id": "Test Mouse 001",
            "species": "Mus musculus",
            "age": "P56",
            "sex": "Male",
            "session_start_time": "2024-01-15T12:00:00",
            "experimenter": "Test User",
            "device_name": "Open Ephys Acquisition Board",
            "manufacturer": "Open Ephys",
            "recording_location": "CA1",
            "description": "Test session for validation.",
            "extraction_confidence": {
                "subject_id": "high",
                "species": "high",
                "age": "high",
            },
        }
    )


@pytest.mark.asyncio
async def test_handle_message_routes_to_initialize_session(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test handle_message routes initialize_session task to _initialize_session."""
    # Arrange
    session_id = "test-session-001"
    message = MCPMessage(
        message_id="msg-001",
        source_agent="mcp_server",
        target_agent="conversation_agent",
        message_type=MessageType.AGENT_EXECUTE,
        session_id=session_id,
        payload={
            "task_name": "initialize_session",
            "session_id": session_id,
            "parameters": {"dataset_path": str(test_dataset_path)},
        },
    )

    # Mock dependencies
    mock_session = SessionContext(session_id=session_id)

    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        with patch.object(
            conversation_agent, "update_session_context", new_callable=AsyncMock
        ) as mock_update_context:
            mock_update_context.return_value = {"status": "success"}

            with patch.object(
                conversation_agent, "call_llm", new_callable=AsyncMock
            ) as mock_llm:
                mock_llm.return_value = sample_llm_response

                with patch.object(
                    conversation_agent.http_client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.return_value = MagicMock(
                        spec=Response, status_code=200
                    )

                    # Act
                    result = await conversation_agent.handle_message(message)

                    # Assert
                    assert result["status"] == "success"
                    assert mock_get_context.called
                    assert mock_update_context.called


@pytest.mark.asyncio
async def test_initialize_session_with_valid_openephys_dataset(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test initialize session successfully processes valid OpenEphys dataset."""
    # Arrange
    session_id = "test-session-002"
    dataset_path = str(test_dataset_path)
    mock_session = SessionContext(session_id=session_id)

    # Mock dependencies
    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        with patch.object(
            conversation_agent, "update_session_context", new_callable=AsyncMock
        ) as mock_update_context:
            mock_update_context.return_value = {"status": "success"}

            with patch.object(
                conversation_agent, "call_llm", new_callable=AsyncMock
            ) as mock_llm:
                mock_llm.return_value = sample_llm_response

                with patch.object(
                    conversation_agent.http_client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.return_value = MagicMock(
                        spec=Response, status_code=200
                    )

                    # Act
                    result = await conversation_agent._initialize_session(
                        session_id, dataset_path
                    )

                    # Assert
                    assert result["status"] == "success"
                    assert "dataset_info" in result
                    assert "metadata" in result


@pytest.mark.asyncio
async def test_initialize_updates_session_context_with_dataset_info(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test initialize session updates context with dataset_info."""
    # Arrange
    session_id = "test-session-003"
    dataset_path = str(test_dataset_path)
    mock_session = SessionContext(session_id=session_id)

    # Mock dependencies
    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        with patch.object(
            conversation_agent, "update_session_context", new_callable=AsyncMock
        ) as mock_update_context:
            mock_update_context.return_value = {"status": "success"}

            with patch.object(
                conversation_agent, "call_llm", new_callable=AsyncMock
            ) as mock_llm:
                mock_llm.return_value = sample_llm_response

                with patch.object(
                    conversation_agent.http_client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.return_value = MagicMock(
                        spec=Response, status_code=200
                    )

                    # Act
                    await conversation_agent._initialize_session(
                        session_id, dataset_path
                    )

                    # Assert
                    assert mock_update_context.called
                    # Get the updates argument from the first call
                    updates = mock_update_context.call_args_list[0][0][1]
                    assert "dataset_info" in updates
                    assert updates["dataset_info"]["format"] == "openephys"


@pytest.mark.asyncio
async def test_initialize_updates_session_context_with_metadata(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test initialize session updates context with extracted metadata."""
    # Arrange
    session_id = "test-session-004"
    dataset_path = str(test_dataset_path)
    mock_session = SessionContext(session_id=session_id)

    # Mock dependencies
    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        with patch.object(
            conversation_agent, "update_session_context", new_callable=AsyncMock
        ) as mock_update_context:
            mock_update_context.return_value = {"status": "success"}

            with patch.object(
                conversation_agent, "call_llm", new_callable=AsyncMock
            ) as mock_llm:
                mock_llm.return_value = sample_llm_response

                with patch.object(
                    conversation_agent.http_client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.return_value = MagicMock(
                        spec=Response, status_code=200
                    )

                    # Act
                    await conversation_agent._initialize_session(
                        session_id, dataset_path
                    )

                    # Assert
                    assert mock_update_context.called
                    updates = mock_update_context.call_args_list[0][0][1]
                    assert "metadata" in updates
                    assert updates["metadata"]["subject_id"] == "Test Mouse 001"


@pytest.mark.asyncio
async def test_initialize_sets_workflow_stage_to_collecting_metadata(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test initialize session sets workflow_stage to COLLECTING_METADATA."""
    # Arrange
    session_id = "test-session-005"
    dataset_path = str(test_dataset_path)
    mock_session = SessionContext(session_id=session_id)

    # Mock dependencies
    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        with patch.object(
            conversation_agent, "update_session_context", new_callable=AsyncMock
        ) as mock_update_context:
            mock_update_context.return_value = {"status": "success"}

            with patch.object(
                conversation_agent, "call_llm", new_callable=AsyncMock
            ) as mock_llm:
                mock_llm.return_value = sample_llm_response

                with patch.object(
                    conversation_agent.http_client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.return_value = MagicMock(
                        spec=Response, status_code=200
                    )

                    # Act
                    await conversation_agent._initialize_session(
                        session_id, dataset_path
                    )

                    # Assert
                    assert mock_update_context.called
                    updates = mock_update_context.call_args_list[0][0][1]
                    assert updates["workflow_stage"] == WorkflowStage.COLLECTING_METADATA


@pytest.mark.asyncio
async def test_initialize_triggers_conversion_agent_after_initialization(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test initialize session triggers conversion agent after successful initialization."""
    # Arrange
    session_id = "test-session-006"
    dataset_path = str(test_dataset_path)
    mock_session = SessionContext(session_id=session_id)

    # Mock dependencies
    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        with patch.object(
            conversation_agent, "update_session_context", new_callable=AsyncMock
        ) as mock_update_context:
            mock_update_context.return_value = {"status": "success"}

            with patch.object(
                conversation_agent, "call_llm", new_callable=AsyncMock
            ) as mock_llm:
                mock_llm.return_value = sample_llm_response

                with patch.object(
                    conversation_agent.http_client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.return_value = MagicMock(
                        spec=Response, status_code=200
                    )

                    # Act
                    await conversation_agent._initialize_session(
                        session_id, dataset_path
                    )

                    # Assert
                    assert mock_post.called
                    # Verify it's posting to the message router
                    call_url = mock_post.call_args[0][0]
                    assert "message/route" in call_url


@pytest.mark.asyncio
async def test_initialize_returns_success_status_with_results(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test initialize session returns success status with results."""
    # Arrange
    session_id = "test-session-007"
    dataset_path = str(test_dataset_path)
    mock_session = SessionContext(session_id=session_id)

    # Mock dependencies
    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        with patch.object(
            conversation_agent, "update_session_context", new_callable=AsyncMock
        ) as mock_update_context:
            mock_update_context.return_value = {"status": "success"}

            with patch.object(
                conversation_agent, "call_llm", new_callable=AsyncMock
            ) as mock_llm:
                mock_llm.return_value = sample_llm_response

                with patch.object(
                    conversation_agent.http_client, "post", new_callable=AsyncMock
                ) as mock_post:
                    mock_post.return_value = MagicMock(
                        spec=Response, status_code=200
                    )

                    # Act
                    result = await conversation_agent._initialize_session(
                        session_id, dataset_path
                    )

                    # Assert
                    assert result["status"] == "success"
                    assert "session_id" in result
                    assert result["session_id"] == session_id
                    assert "dataset_info" in result
                    assert "metadata" in result


@pytest.mark.asyncio
async def test_initialize_fails_for_unsupported_format(
    conversation_agent: ConversationAgent,
) -> None:
    """Test initialize session fails for unsupported format (not OpenEphys)."""
    # Arrange
    import tempfile

    session_id = "test-session-008"
    mock_session = SessionContext(session_id=session_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory with no OpenEphys files
        dataset_path = tmpdir

        # Mock dependencies
        with patch.object(
            conversation_agent, "get_session_context", new_callable=AsyncMock
        ) as mock_get_context:
            mock_get_context.return_value = mock_session

            # Act
            result = await conversation_agent._initialize_session(
                session_id, dataset_path
            )

            # Assert
            assert result["status"] == "error"
            assert "unsupported" in result["message"].lower()


@pytest.mark.asyncio
async def test_initialize_fails_for_invalid_dataset_structure(
    conversation_agent: ConversationAgent,
) -> None:
    """Test initialize session fails for invalid dataset structure."""
    # Arrange
    import tempfile

    session_id = "test-session-009"
    mock_session = SessionContext(session_id=session_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory with .continuous but no settings.xml
        continuous_file = Path(tmpdir) / "100_CH1.continuous"
        continuous_file.write_bytes(b"fake data")
        dataset_path = tmpdir

        # Mock dependencies
        with patch.object(
            conversation_agent, "get_session_context", new_callable=AsyncMock
        ) as mock_get_context:
            mock_get_context.return_value = mock_session

            # Act
            result = await conversation_agent._initialize_session(
                session_id, dataset_path
            )

            # Assert
            assert result["status"] == "error"
            assert "settings.xml" in result["message"]


@pytest.mark.asyncio
async def test_initialize_error_handling_for_missing_dataset_path(
    conversation_agent: ConversationAgent,
) -> None:
    """Test initialize session handles missing dataset_path parameter."""
    # Arrange
    session_id = "test-session-010"
    message = MCPMessage(
        message_id="msg-010",
        source_agent="mcp_server",
        target_agent="conversation_agent",
        message_type=MessageType.AGENT_EXECUTE,
        session_id=session_id,
        payload={
            "task_name": "initialize_session",
            "session_id": session_id,
            "parameters": {},  # Missing dataset_path
        },
    )

    # Mock dependencies
    mock_session = SessionContext(session_id=session_id)

    with patch.object(
        conversation_agent, "get_session_context", new_callable=AsyncMock
    ) as mock_get_context:
        mock_get_context.return_value = mock_session

        # Act
        result = await conversation_agent.handle_message(message)

        # Assert
        assert result["status"] == "error"
        assert "dataset_path" in result["message"].lower()
