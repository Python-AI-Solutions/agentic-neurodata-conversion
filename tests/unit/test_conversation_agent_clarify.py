"""
Unit tests for ConversationAgent clarification handler (Task 4.5).

Tests the _handle_clarification method which:
- Updates metadata based on user clarification
- Clears requires_user_clarification flag
- Clears clarification_prompt
- Triggers conversion agent retry
- Handles missing updated_metadata gracefully
"""

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import Response
import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.session_context import (
    MetadataExtractionResult,
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


@pytest.mark.asyncio
async def test_handle_clarification_updates_metadata(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_clarification updates metadata with user input."""
    # Arrange
    session_id = "test-session-001"
    user_input = None
    updated_metadata = {
        "subject_id": "Mouse 002",
        "species": "Mus musculus",
        "age": "P60",
    }

    mock_session = SessionContext(
        session_id=session_id,
        workflow_stage=WorkflowStage.COLLECTING_METADATA,
        requires_user_clarification=True,
        clarification_prompt="Please provide subject ID",
        metadata=MetadataExtractionResult(subject_id="Unknown"),
    )

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
                conversation_agent.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = MagicMock(spec=Response, status_code=200)

                # Act
                result = await conversation_agent._handle_clarification(
                    session_id, user_input, updated_metadata
                )

                # Assert
                assert result["status"] == "success"
                assert mock_update_context.called
                # Verify metadata was updated
                updates = mock_update_context.call_args[0][1]
                assert "metadata" in updates
                assert updates["metadata"]["subject_id"] == "Mouse 002"


@pytest.mark.asyncio
async def test_handle_clarification_clears_requires_clarification_flag(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_clarification clears requires_user_clarification flag."""
    # Arrange
    session_id = "test-session-002"
    updated_metadata = {"subject_id": "Mouse 003"}

    mock_session = SessionContext(
        session_id=session_id,
        requires_user_clarification=True,
        metadata=MetadataExtractionResult(),
    )

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
                conversation_agent.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = MagicMock(spec=Response, status_code=200)

                # Act
                await conversation_agent._handle_clarification(
                    session_id, None, updated_metadata
                )

                # Assert
                updates = mock_update_context.call_args[0][1]
                assert updates["requires_user_clarification"] is False


@pytest.mark.asyncio
async def test_handle_clarification_clears_clarification_prompt(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_clarification clears clarification_prompt."""
    # Arrange
    session_id = "test-session-003"
    updated_metadata = {"subject_id": "Mouse 004"}

    mock_session = SessionContext(
        session_id=session_id,
        requires_user_clarification=True,
        clarification_prompt="Please provide more info",
        metadata=MetadataExtractionResult(),
    )

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
                conversation_agent.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = MagicMock(spec=Response, status_code=200)

                # Act
                await conversation_agent._handle_clarification(
                    session_id, None, updated_metadata
                )

                # Assert
                updates = mock_update_context.call_args[0][1]
                assert updates["clarification_prompt"] is None


@pytest.mark.asyncio
async def test_handle_clarification_triggers_conversion_agent_retry(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_clarification triggers conversion agent to retry."""
    # Arrange
    session_id = "test-session-004"
    updated_metadata = {"subject_id": "Mouse 005"}

    mock_session = SessionContext(
        session_id=session_id,
        requires_user_clarification=True,
        metadata=MetadataExtractionResult(),
    )

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
                conversation_agent.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = MagicMock(spec=Response, status_code=200)

                # Act
                await conversation_agent._handle_clarification(
                    session_id, None, updated_metadata
                )

                # Assert
                assert mock_post.called
                # Verify it's posting to the message router
                call_url = mock_post.call_args[0][0]
                assert "message/route" in call_url
                # Verify it's targeting conversion_agent
                call_json = mock_post.call_args[1]["json"]
                assert call_json["target_agent"] == "conversion_agent"


@pytest.mark.asyncio
async def test_handle_clarification_returns_success_status(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_clarification returns success status."""
    # Arrange
    session_id = "test-session-005"
    updated_metadata = {"subject_id": "Mouse 006"}

    mock_session = SessionContext(
        session_id=session_id,
        requires_user_clarification=True,
        metadata=MetadataExtractionResult(),
    )

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
                conversation_agent.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = MagicMock(spec=Response, status_code=200)

                # Act
                result = await conversation_agent._handle_clarification(
                    session_id, None, updated_metadata
                )

                # Assert
                assert result["status"] == "success"
                assert "session_id" in result
                assert result["session_id"] == session_id


@pytest.mark.asyncio
async def test_handle_clarification_handles_missing_updated_metadata(
    conversation_agent: ConversationAgent,
) -> None:
    """Test handle_clarification handles missing updated_metadata gracefully."""
    # Arrange
    session_id = "test-session-006"
    user_input = "Subject is Mouse 007"
    updated_metadata = None

    mock_session = SessionContext(
        session_id=session_id,
        requires_user_clarification=True,
        metadata=MetadataExtractionResult(subject_id="Unknown"),
    )

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
                conversation_agent.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.return_value = MagicMock(spec=Response, status_code=200)

                # Act
                result = await conversation_agent._handle_clarification(
                    session_id, user_input, updated_metadata
                )

                # Assert
                assert result["status"] == "success"
                # Metadata should remain unchanged when updated_metadata is None
                updates = mock_update_context.call_args[0][1]
                # The metadata should still be in the update (preserving existing)
                assert "metadata" in updates
