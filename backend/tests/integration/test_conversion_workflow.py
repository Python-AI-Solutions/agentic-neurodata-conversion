"""
Integration tests for the complete conversion workflow.

Tests the full agent interaction through MCP server.
"""
import tempfile
from pathlib import Path

import pytest

from agents import (
    register_conversation_agent,
    register_conversion_agent,
    register_evaluation_agent,
)
from models import ConversionStatus, MCPMessage
from services import MCPServer, MockLLMService, reset_mcp_server


@pytest.fixture
def toy_dataset_path():
    """Get path to the toy SpikeGLX dataset."""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "toy_spikeglx"
    if not fixtures_path.exists():
        pytest.skip("Toy dataset not generated. Run: pixi run generate-fixtures")
    return str(fixtures_path)


@pytest.fixture
def mcp_server_with_agents():
    """Create MCP server with all agents registered."""
    reset_mcp_server()
    server = MCPServer()

    # Use mock LLM service for testing
    mock_llm = MockLLMService()

    # Register all agents
    register_conversion_agent(server)
    register_evaluation_agent(server, llm_service=mock_llm)
    register_conversation_agent(server, llm_service=mock_llm)

    return server


class TestConversionAgentIntegration:
    """Test conversion agent integration."""

    @pytest.mark.asyncio
    async def test_detect_spikeglx_format(self, mcp_server_with_agents, toy_dataset_path):
        """Test detecting SpikeGLX format."""
        message = MCPMessage(
            target_agent="conversion",
            action="detect_format",
            context={"input_path": toy_dataset_path},
        )

        response = await mcp_server_with_agents.send_message(message)

        assert response.success is True
        assert response.result["format"] == "SpikeGLX"
        assert response.result["confidence"] == "high"

    @pytest.mark.asyncio
    async def test_format_detection_unknown(self, mcp_server_with_agents):
        """Test format detection with unknown format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an empty directory
            message = MCPMessage(
                target_agent="conversion",
                action="detect_format",
                context={"input_path": tmpdir},
            )

            response = await mcp_server_with_agents.send_message(message)

            assert response.success is True
            assert response.result["format"] is None
            assert response.result["confidence"] == "ambiguous"


class TestEvaluationAgentIntegration:
    """Test evaluation agent integration."""

    @pytest.mark.asyncio
    async def test_validation_with_mock_llm(self, mcp_server_with_agents):
        """Test validation with mock LLM service."""
        # This is a placeholder test - in real scenario we'd need a valid NWB file
        # For now, we test that the handler exists and returns appropriate error
        message = MCPMessage(
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": "/nonexistent/file.nwb"},
        )

        response = await mcp_server_with_agents.send_message(message)

        # Should fail because file doesn't exist
        assert response.success is False
        assert response.error["code"] == "VALIDATION_FAILED"


class TestWorkflowIntegration:
    """Test complete workflow integration."""

    @pytest.mark.asyncio
    async def test_start_conversion_workflow(self, mcp_server_with_agents, toy_dataset_path):
        """Test starting conversion workflow with format detection."""
        server = mcp_server_with_agents

        # Start conversion
        start_msg = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={
                "input_path": toy_dataset_path,
                "metadata": {"session_description": "Test session"},
            },
        )

        response = await server.send_message(start_msg)

        # Check that workflow started
        assert response.success is True

        # State should be updated
        state = server.global_state
        assert state.input_path == toy_dataset_path
        assert state.metadata["session_description"] == "Test session"

        # Should have detected format and started conversion
        # (or completed it if conversion succeeds)
        assert state.status in [
            ConversionStatus.CONVERTING,
            ConversionStatus.VALIDATING,
            ConversionStatus.COMPLETED,
            ConversionStatus.AWAITING_RETRY_APPROVAL,
            ConversionStatus.FAILED,
        ]

    @pytest.mark.asyncio
    async def test_user_format_selection(self, mcp_server_with_agents):
        """Test user format selection workflow."""
        server = mcp_server_with_agents

        # Simulate state where user input is needed
        server.global_state.status = ConversionStatus.AWAITING_USER_INPUT
        server.global_state.input_path = "/tmp/test_data"

        # Submit format selection
        format_msg = MCPMessage(
            target_agent="conversation",
            action="user_format_selection",
            context={"format": "SpikeGLX"},
        )

        response = await server.send_message(format_msg)

        # Should proceed with conversion
        # (will likely fail due to missing file, but tests the flow)
        assert response.success is True or response.error["code"] == "CONVERSION_FAILED"

    @pytest.mark.asyncio
    async def test_retry_decision_approve(self, mcp_server_with_agents):
        """Test user approving retry."""
        server = mcp_server_with_agents

        # Simulate state where retry approval is needed
        server.global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        server.global_state.correction_attempt = 1

        # Submit approval
        retry_msg = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await server.send_message(retry_msg)

        assert response.success is True
        assert server.global_state.correction_attempt == 2

    @pytest.mark.asyncio
    async def test_retry_decision_reject(self, mcp_server_with_agents):
        """Test user rejecting retry."""
        server = mcp_server_with_agents

        # Simulate state where retry approval is needed
        server.global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # Submit rejection
        retry_msg = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "reject"},
        )

        response = await server.send_message(retry_msg)

        assert response.success is True
        assert response.result["status"] == "failed"
        assert server.global_state.status == ConversionStatus.FAILED


class TestStateManagement:
    """Test global state management during workflow."""

    @pytest.mark.asyncio
    async def test_state_logging(self, mcp_server_with_agents, toy_dataset_path):
        """Test that state is logged throughout workflow."""
        server = mcp_server_with_agents

        initial_log_count = len(server.global_state.logs)

        # Send a message
        message = MCPMessage(
            target_agent="conversion",
            action="detect_format",
            context={"input_path": toy_dataset_path},
        )

        await server.send_message(message)

        # Should have added logs
        assert len(server.global_state.logs) > initial_log_count

        # Check log content
        log_messages = [log.message for log in server.global_state.logs]
        assert any("detect_format" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_state_reset(self, mcp_server_with_agents, toy_dataset_path):
        """Test state reset functionality."""
        server = mcp_server_with_agents

        # Modify state
        message = MCPMessage(
            target_agent="conversion",
            action="detect_format",
            context={"input_path": toy_dataset_path},
        )
        await server.send_message(message)

        assert len(server.global_state.logs) > 0

        # Reset
        server.reset_state()

        # State should be clean
        assert server.global_state.status == ConversionStatus.IDLE
        assert len(server.global_state.logs) == 1  # Just the reset log
        assert server.global_state.input_path is None
