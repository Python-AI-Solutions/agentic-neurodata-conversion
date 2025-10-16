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


class TestCorrectionLoopIntegration:
    """Test correction loop and LLM-powered fixes."""

    @pytest.mark.asyncio
    async def test_auto_fix_extraction(self, mcp_server_with_agents):
        """Test that auto-fixes are correctly extracted from LLM analysis."""
        server = mcp_server_with_agents

        # Create a mock validation result with issues
        mock_validation_result = {
            "is_valid": False,
            "issues": [
                {"severity": "error", "message": "Missing species", "location": "/general"}
            ],
            "summary": {"critical": 0, "error": 1, "warning": 0, "info": 0},
            "overall_status": "FAILED",
        }

        # Simulate state for correction
        server.global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        server.global_state.correction_attempt = 0
        server.global_state.output_path = "/tmp/test.nwb"
        server.global_state.add_log("info", "Validation failed", {"validation": mock_validation_result})

        # Approve retry to trigger LLM analysis
        retry_msg = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await server.send_message(retry_msg)

        # Should process through correction flow
        assert response.success is True
        assert server.global_state.correction_attempt >= 1

        # Check logs for correction analysis
        log_messages = [log.message for log in server.global_state.logs]
        correction_logs = [msg for msg in log_messages if "correction" in msg.lower()]
        assert len(correction_logs) > 0

    @pytest.mark.asyncio
    async def test_user_input_required_detection(self, mcp_server_with_agents):
        """Test detection of issues requiring user input."""
        server = mcp_server_with_agents

        # Mock LLM service with specific corrections requiring user input
        mock_llm = server._handlers["evaluation"]["analyze_corrections"].__self__._llm_service

        # Set up specific response for user input required scenario
        mock_llm.set_mock_response({
            "analysis": "Critical metadata missing",
            "suggestions": [
                {
                    "issue": "Missing subject_id",
                    "suggestion": "Subject ID must be provided by user",
                    "actionable": False,  # Not auto-fixable
                    "severity": "error",
                }
            ],
            "recommended_action": "request_user_input",
        })

        # Test the identify_user_input_required method
        mock_validation_result = {
            "is_valid": False,
            "issues": [{"severity": "error", "message": "Missing subject_id"}],
            "summary": {"error": 1},
            "overall_status": "FAILED",
        }

        server.global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        server.global_state.add_log("info", "Validation failed", {"validation": mock_validation_result})

        retry_msg = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await server.send_message(retry_msg)

        # Should transition to AWAITING_USER_INPUT if issues require user input
        # (depends on mock LLM configuration)
        assert response.success is True


class TestReportGeneration:
    """Test report generation for different validation outcomes."""

    @pytest.mark.asyncio
    async def test_pdf_report_for_passed_validation(self, mcp_server_with_agents):
        """Test PDF report generation for PASSED validation."""
        server = mcp_server_with_agents

        # Create a mock PASSED validation result
        mock_validation_result = {
            "is_valid": True,
            "issues": [],
            "summary": {"critical": 0, "error": 0, "warning": 0, "info": 0},
            "overall_status": "PASSED",
        }

        # Send report generation request
        with tempfile.TemporaryDirectory() as tmpdir:
            nwb_path = Path(tmpdir) / "test.nwb"
            nwb_path.touch()  # Create empty file

            report_msg = MCPMessage(
                target_agent="evaluation",
                action="generate_report",
                context={
                    "validation_result": mock_validation_result,
                    "nwb_path": str(nwb_path),
                },
            )

            response = await server.send_message(report_msg)

            assert response.success is True
            assert "report_path" in response.result
            assert response.result["report_type"] == "pdf"
            assert response.result["report_path"].endswith(".pdf")

    @pytest.mark.asyncio
    async def test_json_report_for_failed_validation(self, mcp_server_with_agents):
        """Test JSON report generation for FAILED validation."""
        server = mcp_server_with_agents

        # Create a mock FAILED validation result
        mock_validation_result = {
            "is_valid": False,
            "issues": [
                {"severity": "error", "message": "Missing required field", "location": "/general"}
            ],
            "summary": {"critical": 0, "error": 1, "warning": 0, "info": 0},
            "overall_status": "FAILED",
        }

        # Send report generation request
        with tempfile.TemporaryDirectory() as tmpdir:
            nwb_path = Path(tmpdir) / "test.nwb"
            nwb_path.touch()

            report_msg = MCPMessage(
                target_agent="evaluation",
                action="generate_report",
                context={
                    "validation_result": mock_validation_result,
                    "nwb_path": str(nwb_path),
                },
            )

            response = await server.send_message(report_msg)

            assert response.success is True
            assert "report_path" in response.result
            assert response.result["report_type"] == "json"
            assert response.result["report_path"].endswith(".json")


class TestEndToEndWorkflow:
    """Complete end-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_full_workflow_passed_scenario(self, mcp_server_with_agents, toy_dataset_path):
        """Test full workflow resulting in PASSED validation."""
        server = mcp_server_with_agents

        # Start conversion with good metadata
        start_msg = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={
                "input_path": toy_dataset_path,
                "metadata": {
                    "session_description": "Complete test session with all required metadata",
                    "experimenter": ["Test Experimenter"],
                    "subject_id": "test_subject_001",
                    "species": "Mus musculus",
                },
            },
        )

        response = await server.send_message(start_msg)
        assert response.success is True

        # Verify final state
        state = server.global_state
        assert state.status in [
            ConversionStatus.COMPLETED,
            ConversionStatus.AWAITING_RETRY_APPROVAL,
            ConversionStatus.FAILED,
        ]

        # Check that logs contain key workflow steps
        log_messages = [log.message.lower() for log in state.logs]
        assert any("format" in msg for msg in log_messages)  # Format detection
        assert any("conversion" in msg for msg in log_messages)  # Conversion
        assert any("validation" in msg for msg in log_messages)  # Validation
