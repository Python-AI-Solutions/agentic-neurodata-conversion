"""
Unit tests for EvaluationAgent - Message Handler (Task 6.4).

Tests the complete message handling workflow including validation,
report generation, and session context updates.

Test coverage:
- Handle message routes to _validate_nwb
- Validation updates workflow_stage to EVALUATING
- Validation updates session context with results
- Validation generates report file
- Validation generates LLM summary
- Validation sets workflow_stage to COMPLETED
- Validation clears current_agent
- Handles missing NWB file gracefully
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import h5py
import pytest

from agentic_neurodata_conversion.agents.evaluation_agent import EvaluationAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import (
    ConversionResults,
    MetadataExtractionResult,
    SessionContext,
    WorkflowStage,
)


@pytest.fixture
def evaluation_agent(tmp_path: Path) -> EvaluationAgent:
    """Create EvaluationAgent instance for testing."""
    config = AgentConfig(
        agent_name="test-evaluation-agent",
        agent_type="evaluation",
        agent_port=8003,
        mcp_server_url="http://localhost:3000",
        llm_provider="anthropic",
        llm_api_key="test-key",
        llm_model="claude-3-5-sonnet-20241022",
        temperature=0.4,
        max_tokens=8192,
    )
    return EvaluationAgent(config)


@pytest.fixture
def valid_nwb_file(tmp_path: Path) -> Path:
    """Create a minimal valid NWB file for testing."""
    nwb_path = tmp_path / "test_session.nwb"
    with h5py.File(nwb_path, "w") as f:
        # Create minimal NWB structure
        f.attrs["nwb_version"] = "2.5.0"
        f.create_group("acquisition")
        f.create_group("general")
        f.create_group("specifications")
        # Add some test data
        f.create_dataset("acquisition/test_data", data=[1, 2, 3], compression="gzip")
    return nwb_path


@pytest.fixture
def session_with_conversion(valid_nwb_file: Path) -> SessionContext:
    """Create session context with conversion results."""
    return SessionContext(
        session_id="test-session-001",
        workflow_stage=WorkflowStage.CONVERTING,
        current_agent="conversion_agent",
        conversion_results=ConversionResults(
            nwb_file_path=str(valid_nwb_file),
            conversion_duration_seconds=10.5,
        ),
        metadata=MetadataExtractionResult(
            subject_id="Mouse001",
            species="Mus musculus",
            session_start_time="2024-01-15T12:00:00Z",
        ),
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_message_routes_to_validate_nwb(
    evaluation_agent: EvaluationAgent,
) -> None:
    """Test handle message routes to _validate_nwb."""
    # Create MCP message for validation using new MCPMessage format
    message = MCPMessage(
        message_id="msg-001",
        source_agent="mcp_server",
        target_agent="evaluation_agent",
        message_type="agent_execute",
        session_id="test-session-001",
        payload={"action": "validate_nwb"},
    )

    # Mock the _validate_nwb_full method
    with patch.object(evaluation_agent, "_validate_nwb_full", new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = {
            "status": "success",
            "session_id": "test-session-001",
        }

        # Handle message
        result = await evaluation_agent.handle_message(message)

        # Verify _validate_nwb_full was called
        mock_validate.assert_called_once_with("test-session-001")


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validation_updates_workflow_stage_to_evaluating(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    session_with_conversion: SessionContext,
) -> None:
    """Test validation updates workflow_stage to EVALUATING."""
    # Mock NWB Inspector
    mock_inspect.return_value = []

    # Mock get_session_context and update_session_context
    with patch.object(evaluation_agent, "get_session_context", new_callable=AsyncMock) as mock_get:
        with patch.object(evaluation_agent, "update_session_context", new_callable=AsyncMock) as mock_update:
            with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
                mock_get.return_value = session_with_conversion
                mock_update.return_value = {"status": "success"}
                mock_llm.return_value = "Validation summary"

                # Call validation
                result = await evaluation_agent._validate_nwb_full("test-session-001")

                # Verify workflow_stage was updated to EVALUATING
                calls = mock_update.call_args_list
                # First update should set workflow_stage to EVALUATING
                first_call = calls[0]
                assert first_call[0][0] == "test-session-001"
                assert first_call[0][1]["workflow_stage"] == WorkflowStage.EVALUATING


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validation_updates_session_context_with_results(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    session_with_conversion: SessionContext,
) -> None:
    """Test validation updates session context with results."""
    # Mock NWB Inspector
    mock_inspect.return_value = []

    # Mock get_session_context and update_session_context
    with patch.object(evaluation_agent, "get_session_context", new_callable=AsyncMock) as mock_get:
        with patch.object(evaluation_agent, "update_session_context", new_callable=AsyncMock) as mock_update:
            with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
                mock_get.return_value = session_with_conversion
                mock_update.return_value = {"status": "success"}
                mock_llm.return_value = "Validation summary"

                # Call validation
                result = await evaluation_agent._validate_nwb_full("test-session-001")

                # Verify session context was updated with validation results
                calls = mock_update.call_args_list
                # Last call should include validation_results
                last_call = calls[-1]
                assert "validation_results" in last_call[0][1]
                validation_results = last_call[0][1]["validation_results"]
                assert validation_results["overall_status"] == "passed"


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validation_generates_report_file(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    session_with_conversion: SessionContext,
    tmp_path: Path,
) -> None:
    """Test validation generates report file."""
    # Mock NWB Inspector
    mock_inspect.return_value = []

    # Mock get_session_context and update_session_context
    with patch.object(evaluation_agent, "get_session_context", new_callable=AsyncMock) as mock_get:
        with patch.object(evaluation_agent, "update_session_context", new_callable=AsyncMock) as mock_update:
            with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
                mock_get.return_value = session_with_conversion
                mock_update.return_value = {"status": "success"}
                mock_llm.return_value = "Validation summary"

                # Call validation
                result = await evaluation_agent._validate_nwb_full("test-session-001")

                # Verify report file was generated
                report_path = Path("./reports/test-session-001_validation.json")
                assert report_path.exists()

                # Verify validation results include report path
                calls = mock_update.call_args_list
                last_call = calls[-1]
                validation_results = last_call[0][1]["validation_results"]
                assert validation_results["validation_report_path"] is not None


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validation_generates_llm_summary(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    session_with_conversion: SessionContext,
) -> None:
    """Test validation generates LLM summary."""
    # Mock NWB Inspector
    mock_inspect.return_value = []

    # Mock get_session_context and update_session_context
    with patch.object(evaluation_agent, "get_session_context", new_callable=AsyncMock) as mock_get:
        with patch.object(evaluation_agent, "update_session_context", new_callable=AsyncMock) as mock_update:
            with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
                mock_get.return_value = session_with_conversion
                mock_update.return_value = {"status": "success"}
                mock_llm.return_value = "Validation passed successfully."

                # Call validation
                result = await evaluation_agent._validate_nwb_full("test-session-001")

                # Verify LLM was called for summary
                mock_llm.assert_called_once()

                # Verify validation results include LLM summary
                calls = mock_update.call_args_list
                last_call = calls[-1]
                validation_results = last_call[0][1]["validation_results"]
                assert validation_results["llm_validation_summary"] == "Validation passed successfully."


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validation_sets_workflow_stage_to_completed(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    session_with_conversion: SessionContext,
) -> None:
    """Test validation sets workflow_stage to COMPLETED."""
    # Mock NWB Inspector
    mock_inspect.return_value = []

    # Mock get_session_context and update_session_context
    with patch.object(evaluation_agent, "get_session_context", new_callable=AsyncMock) as mock_get:
        with patch.object(evaluation_agent, "update_session_context", new_callable=AsyncMock) as mock_update:
            with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
                mock_get.return_value = session_with_conversion
                mock_update.return_value = {"status": "success"}
                mock_llm.return_value = "Validation summary"

                # Call validation
                result = await evaluation_agent._validate_nwb_full("test-session-001")

                # Verify workflow_stage was updated to COMPLETED
                calls = mock_update.call_args_list
                last_call = calls[-1]
                assert last_call[0][1]["workflow_stage"] == WorkflowStage.COMPLETED


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validation_clears_current_agent(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    session_with_conversion: SessionContext,
) -> None:
    """Test validation clears current_agent field."""
    # Mock NWB Inspector
    mock_inspect.return_value = []

    # Mock get_session_context and update_session_context
    with patch.object(evaluation_agent, "get_session_context", new_callable=AsyncMock) as mock_get:
        with patch.object(evaluation_agent, "update_session_context", new_callable=AsyncMock) as mock_update:
            with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
                mock_get.return_value = session_with_conversion
                mock_update.return_value = {"status": "success"}
                mock_llm.return_value = "Validation summary"

                # Call validation
                result = await evaluation_agent._validate_nwb_full("test-session-001")

                # Verify current_agent was cleared
                calls = mock_update.call_args_list
                last_call = calls[-1]
                assert last_call[0][1]["current_agent"] is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handles_missing_nwb_file_gracefully(
    evaluation_agent: EvaluationAgent,
) -> None:
    """Test handles missing NWB file gracefully."""
    # Create session with missing NWB file
    session_with_missing_file = SessionContext(
        session_id="test-session-002",
        workflow_stage=WorkflowStage.CONVERTING,
        current_agent="conversion_agent",
        conversion_results=ConversionResults(
            nwb_file_path="/nonexistent/missing.nwb",
            conversion_duration_seconds=10.5,
        ),
    )

    # Mock get_session_context and update_session_context
    with patch.object(evaluation_agent, "get_session_context", new_callable=AsyncMock) as mock_get:
        with patch.object(evaluation_agent, "update_session_context", new_callable=AsyncMock) as mock_update:
            mock_get.return_value = session_with_missing_file
            mock_update.return_value = {"status": "success"}

            # Call validation
            result = await evaluation_agent._validate_nwb_full("test-session-002")

            # Verify error was handled gracefully
            assert result["status"] == "error"
            assert "error" in result
            assert "not found" in result["error"].lower() or "file" in result["error"].lower()
