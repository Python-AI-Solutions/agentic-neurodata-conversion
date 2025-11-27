"""Focused unit tests for WorkflowOrchestrator.

Tests critical workflow paths including initialization, format detection,
error handling, and state management.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.conversation.workflow_orchestrator import (
    WorkflowOrchestrator,
)
from agentic_neurodata_conversion.models import (
    ConversionStatus,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationOutcome,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for WorkflowOrchestrator."""
    metadata_collector = Mock()
    # Add AsyncMock for async methods
    metadata_collector.generate_custom_metadata_prompt = AsyncMock(return_value=None)
    metadata_collector.validate_required_nwb_metadata = Mock(return_value=(True, []))

    return {
        "mcp_server": Mock(),
        "metadata_collector": metadata_collector,
        "metadata_parser": Mock(),
        "provenance_tracker": Mock(),
        "workflow_manager": Mock(),
        "conversational_handler": Mock(),
        "metadata_inference_engine": Mock(),
        "llm_service": Mock(),
    }


@pytest.fixture
def orchestrator(mock_dependencies):
    """Create WorkflowOrchestrator instance with mocked dependencies."""
    return WorkflowOrchestrator(**mock_dependencies)


@pytest.fixture
def start_conversion_message():
    """Create a valid start_conversion message."""
    return MCPMessage(
        target_agent="conversation",
        action="start_conversion",
        context={"input_path": "/test/input.dat", "metadata": {}},
        message_id="test-msg-id",
    )


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestWorkflowOrchestratorInitialization:
    """Test WorkflowOrchestrator initialization."""

    def test_init_with_all_dependencies(self, mock_dependencies):
        """Test initialization with all dependencies provided."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        assert orchestrator._mcp_server == mock_dependencies["mcp_server"]
        assert orchestrator._metadata_collector == mock_dependencies["metadata_collector"]
        assert orchestrator._metadata_parser == mock_dependencies["metadata_parser"]
        assert orchestrator._provenance_tracker == mock_dependencies["provenance_tracker"]
        assert orchestrator._workflow_manager == mock_dependencies["workflow_manager"]
        assert orchestrator._conversational_handler == mock_dependencies["conversational_handler"]
        assert orchestrator._metadata_inference_engine == mock_dependencies["metadata_inference_engine"]
        assert orchestrator._llm_service == mock_dependencies["llm_service"]

    def test_init_without_optional_dependencies(self):
        """Test initialization without optional LLM and inference engine."""
        orchestrator = WorkflowOrchestrator(
            mcp_server=Mock(),
            metadata_collector=Mock(),
            metadata_parser=Mock(),
            provenance_tracker=Mock(),
            workflow_manager=Mock(),
        )

        assert orchestrator._mcp_server is not None
        assert orchestrator._conversational_handler is None
        assert orchestrator._metadata_inference_engine is None
        assert orchestrator._llm_service is None


# ============================================================================
# Start Conversion Tests - Input Validation
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestStartConversionInputValidation:
    """Test handle_start_conversion input validation."""

    @pytest.mark.asyncio
    async def test_missing_input_path(self, orchestrator, global_state):
        """Test error when input_path is missing."""
        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={},  # Missing input_path
            message_id="test-msg-id",
        )

        response = await orchestrator.handle_start_conversion(message, global_state)

        assert not response.success
        assert response.error.get("code") == "MISSING_INPUT_PATH"
        assert "input_path is required" in response.error.get("message")

        # Verify error was logged
        error_logs = [log for log in global_state.logs if log.level == "error"]
        assert len(error_logs) > 0
        assert "Missing input_path" in error_logs[0].message

    @pytest.mark.asyncio
    async def test_input_path_stored_in_state(self, orchestrator, global_state, start_conversion_message):
        """Test that input_path is stored in global state."""
        # Mock format detection to succeed
        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={
                "format": "nwb",
                "confidence": "high",
            },
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        await orchestrator.handle_start_conversion(start_conversion_message, global_state)

        assert global_state.input_path == "/test/input.dat"
        # Metadata will contain the detected format
        assert "format" in global_state.metadata


# ============================================================================
# Format Detection Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestFormatDetection:
    """Test format detection workflow."""

    @pytest.mark.asyncio
    async def test_format_detection_failure(self, orchestrator, global_state, start_conversion_message):
        """Test handling of format detection failure."""
        mock_detect_response = MCPResponse(
            success=False,
            reply_to="test-msg-id",
            error={"message": "Detection failed", "error_code": "DETECTION_ERROR"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        response = await orchestrator.handle_start_conversion(start_conversion_message, global_state)

        assert not response.success
        assert response.error.get("code") == "DETECTION_FAILED"
        assert "Format detection failed" in response.error.get("message")

    @pytest.mark.asyncio
    async def test_ambiguous_format_detection(self, orchestrator, global_state, start_conversion_message):
        """Test handling of ambiguous format detection."""
        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={
                "format": None,
                "confidence": "ambiguous",
                "supported_formats": ["nwb", "mat", "tif"],
            },
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        response = await orchestrator.handle_start_conversion(start_conversion_message, global_state)

        assert response.success
        assert response.result["status"] == "awaiting_format_selection"
        assert "supported_formats" in response.result
        assert len(response.result["supported_formats"]) == 3
        assert global_state.status == ConversionStatus.AWAITING_USER_INPUT

    @pytest.mark.asyncio
    async def test_format_stored_in_metadata(self, orchestrator, global_state, start_conversion_message):
        """Test that detected format is stored in both metadata locations."""
        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={
                "format": "nwb",
                "confidence": "high",
            },
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        await orchestrator.handle_start_conversion(start_conversion_message, global_state)

        # Format should be stored in both locations (bug fix verification)
        assert global_state.metadata["format"] == "nwb"
        assert global_state.auto_extracted_metadata["format"] == "nwb"


# ============================================================================
# Metadata Inference Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataInference:
    """Test metadata inference workflow."""

    @pytest.mark.asyncio
    async def test_metadata_inference_skipped_without_engine(self, mock_dependencies, global_state):
        """Test that metadata inference is skipped when engine is None."""
        # Create orchestrator without inference engine
        mock_dependencies["metadata_inference_engine"] = None
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/test/input.dat"},
            message_id="test-msg-id",
        )

        await orchestrator.handle_start_conversion(message, global_state)

        # Should not attempt inference without engine
        # Verify no inference-related logs
        inference_logs = [log for log in global_state.logs if "inferring metadata" in log.message.lower()]
        assert len(inference_logs) == 0


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestErrorHandling:
    """Test error handling in workflow orchestrator."""

    @pytest.mark.asyncio
    async def test_handles_mcp_server_exception(self, orchestrator, global_state, start_conversion_message):
        """Test handling when MCP server raises exception."""
        orchestrator._mcp_server.send_message = AsyncMock(side_effect=Exception("Server error"))

        with pytest.raises(Exception, match="Server error"):
            await orchestrator.handle_start_conversion(start_conversion_message, global_state)

    @pytest.mark.asyncio
    async def test_logs_workflow_start(self, orchestrator, global_state, start_conversion_message):
        """Test that workflow start is logged."""
        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        await orchestrator.handle_start_conversion(start_conversion_message, global_state)

        # Verify workflow start was logged
        start_logs = [log for log in global_state.logs if "Starting conversion workflow" in log.message]
        assert len(start_logs) > 0
        assert start_logs[0].context.get("input_path") == "/test/input.dat"


# ============================================================================
# State Management Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestStateManagement:
    """Test global state management during workflow."""

    @pytest.mark.asyncio
    async def test_state_updated_on_ambiguous_format(self, orchestrator, global_state):
        """Test that state is updated to AWAITING_USER_INPUT for ambiguous format."""
        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": None, "confidence": "ambiguous", "supported_formats": []},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/test/input.dat"},
            message_id="test-msg-id",
        )

        initial_status = global_state.status
        await orchestrator.handle_start_conversion(message, global_state)

        assert initial_status != ConversionStatus.AWAITING_USER_INPUT
        assert global_state.status == ConversionStatus.AWAITING_USER_INPUT

    @pytest.mark.asyncio
    async def test_metadata_initialized_from_message(self, orchestrator, global_state):
        """Test that metadata from message is stored in state."""
        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/test/input.dat", "metadata": {"experimenter": "Test User"}},
            message_id="test-msg-id",
        )

        await orchestrator.handle_start_conversion(message, global_state)

        assert global_state.metadata["experimenter"] == "Test User"


# ============================================================================
# MCP Message Format Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMCPMessageFormat:
    """Test MCP message format construction."""

    @pytest.mark.asyncio
    async def test_detect_format_message_structure(self, orchestrator, global_state, start_conversion_message):
        """Test that detect_format message is constructed correctly."""
        sent_messages = []

        async def capture_message(msg):
            sent_messages.append(msg)
            return MCPResponse(success=True, reply_to=msg.message_id, result={"format": "nwb", "confidence": "high"})

        orchestrator._mcp_server.send_message = AsyncMock(side_effect=capture_message)

        await orchestrator.handle_start_conversion(start_conversion_message, global_state)

        # Verify detect_format message was sent
        assert len(sent_messages) > 0
        detect_msg = sent_messages[0]
        assert detect_msg.target_agent == "conversion"
        assert detect_msg.action == "detect_format"
        assert detect_msg.context["input_path"] == "/test/input.dat"
        assert detect_msg.reply_to == "test-msg-id"


# ============================================================================
# Metadata Collection Workflow Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataCollectionWorkflow:
    """Test metadata collection workflow in handle_start_conversion."""

    @pytest.mark.asyncio
    async def test_metadata_collection_triggered_when_required(
        self, mock_dependencies, global_state, start_conversion_message
    ):
        """Test that metadata collection is triggered when fields are missing."""
        # Setup: workflow_manager should indicate metadata is needed
        mock_dependencies["workflow_manager"].should_request_metadata = Mock(return_value=True)
        # Mock metadata_collector to return missing fields
        mock_dependencies["metadata_collector"].validate_required_nwb_metadata = Mock(
            return_value=(False, ["experimenter", "institution"])
        )
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        # Mock format detection success
        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        # Mock _generate_dynamic_metadata_request
        orchestrator._generate_dynamic_metadata_request = AsyncMock(
            return_value="Please provide the following metadata..."
        )

        response = await orchestrator.handle_start_conversion(start_conversion_message, global_state)

        assert response.success
        assert response.result["status"] == "awaiting_user_input"
        assert response.result["conversation_type"] == "required_metadata"
        assert "message" in response.result
        assert "required_fields" in response.result
        # The actual enum value for METADATA_COLLECTION is "required_metadata"
        assert global_state.conversation_phase.value == "required_metadata"

    @pytest.mark.asyncio
    async def test_already_asked_fields_not_requested_again(self, mock_dependencies, global_state):
        """Test that already asked fields are not requested again."""
        # Mark some fields as already asked
        global_state.already_asked_fields = {"experimenter", "institution"}
        mock_dependencies["workflow_manager"].should_request_metadata = Mock(return_value=False)
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/test/input.dat", "metadata": {}},
            message_id="test-msg-id",
        )

        await orchestrator.handle_start_conversion(message, global_state)

        # Should not re-ask for already asked fields
        assert "experimenter" in global_state.already_asked_fields
        assert "institution" in global_state.already_asked_fields

    @pytest.mark.asyncio
    async def test_user_declined_fields_skipped(self, mock_dependencies, global_state):
        """Test that user-declined fields are not requested."""
        global_state.user_declined_fields = {"subject_id", "sex"}
        mock_dependencies["workflow_manager"].should_request_metadata = Mock(return_value=False)
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/test/input.dat", "metadata": {}},
            message_id="test-msg-id",
        )

        await orchestrator.handle_start_conversion(message, global_state)

        # Declined fields should remain in declined set
        assert "subject_id" in global_state.user_declined_fields
        assert "sex" in global_state.user_declined_fields


# ============================================================================
# Metadata Inference Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataInferenceWorkflow:
    """Test metadata inference workflow in handle_start_conversion."""

    @pytest.mark.asyncio
    async def test_high_confidence_metadata_auto_extracted(self, mock_dependencies, global_state):
        """Test that high-confidence inferred metadata is auto-extracted."""
        # Setup inference engine to return high-confidence results
        mock_inference_engine = Mock()
        mock_inference_engine.infer_metadata = AsyncMock(
            return_value={
                "inferred_metadata": {
                    "species": "Mus musculus",
                    "experimenter": "Dr. Smith",
                    "institution": "Example University",
                },
                "confidence_scores": {
                    "species": 95.0,  # High confidence
                    "experimenter": 85.0,  # High confidence
                    "institution": 70.0,  # Low confidence - should not be auto-extracted
                },
                "suggestions": [],
            }
        )
        mock_dependencies["metadata_inference_engine"] = mock_inference_engine
        mock_dependencies["workflow_manager"].should_request_metadata = Mock(return_value=False)
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/test/input.dat", "metadata": {}},
            message_id="test-msg-id",
        )

        await orchestrator.handle_start_conversion(message, global_state)

        # High-confidence fields should be in auto_extracted_metadata
        assert global_state.auto_extracted_metadata.get("species") == "Mus musculus"
        assert global_state.auto_extracted_metadata.get("experimenter") == "Dr. Smith"
        # Low-confidence field should NOT be auto-extracted
        assert "institution" not in global_state.auto_extracted_metadata

    @pytest.mark.asyncio
    async def test_metadata_inference_failure_graceful(self, mock_dependencies, global_state):
        """Test that metadata inference failures are handled gracefully."""
        # Setup inference engine to fail
        mock_inference_engine = Mock()
        mock_inference_engine.infer_metadata = AsyncMock(side_effect=Exception("Inference failed"))
        mock_dependencies["metadata_inference_engine"] = mock_inference_engine
        mock_dependencies["workflow_manager"].should_request_metadata = Mock(return_value=False)
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/test/input.dat", "metadata": {}},
            message_id="test-msg-id",
        )

        # Should not raise exception
        response = await orchestrator.handle_start_conversion(message, global_state)

        # Should have logged warning
        warning_logs = [log for log in global_state.logs if log.level == "warning"]
        assert any("Metadata inference failed" in log.message for log in warning_logs)

    @pytest.mark.asyncio
    async def test_provenance_tracked_for_auto_extracted_metadata(self, mock_dependencies, global_state):
        """Test that provenance is tracked for auto-extracted metadata."""
        # Setup inference engine
        mock_inference_engine = Mock()
        mock_inference_engine.infer_metadata = AsyncMock(
            return_value={
                "inferred_metadata": {"species": "Mus musculus"},
                "confidence_scores": {"species": 90.0},
                "suggestions": [],
            }
        )
        mock_dependencies["metadata_inference_engine"] = mock_inference_engine
        mock_dependencies["workflow_manager"].should_request_metadata = Mock(return_value=False)
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        mock_detect_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"format": "nwb", "confidence": "high"},
        )
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_detect_response)

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/test/input.dat", "metadata": {}},
            message_id="test-msg-id",
        )

        await orchestrator.handle_start_conversion(message, global_state)

        # Provenance tracker should have been called
        mock_dependencies["provenance_tracker"].track_metadata_provenance.assert_called()


# ============================================================================
# Proactive Issue Detection Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestProactiveIssueDetection:
    """Test _proactive_issue_detection method."""

    @pytest.mark.asyncio
    async def test_without_llm_returns_unknown_risk(self, mock_dependencies, global_state, tmp_path):
        """Test proactive detection without LLM returns unknown risk."""
        # Create orchestrator WITHOUT LLM
        mock_dependencies["llm_service"] = None
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"test data")

        result = await orchestrator._proactive_issue_detection(
            input_path=str(test_file),
            format_name="testformat",
            state=global_state,
        )

        assert result["risk_level"] == "unknown"
        assert result["should_proceed"] is True

    @pytest.mark.asyncio
    async def test_with_llm_success_low_risk(self, mock_dependencies, global_state, tmp_path):
        """Test proactive detection with LLM predicting low risk."""
        # Setup LLM service mock
        mock_llm = AsyncMock()
        mock_llm.generate_structured_output = AsyncMock(
            return_value={
                "success_probability": 95,
                "risk_level": "low",
                "predicted_issues": [],
                "suggested_fixes": [],
                "should_proceed": True,
            }
        )
        mock_dependencies["llm_service"] = mock_llm
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"test data")

        result = await orchestrator._proactive_issue_detection(
            input_path=str(test_file),
            format_name="testformat",
            state=global_state,
        )

        assert result["risk_level"] == "low"
        assert result["success_probability"] == 95
        assert result["should_proceed"] is True
        mock_llm.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_llm_high_risk_prediction(self, mock_dependencies, global_state, tmp_path):
        """Test proactive detection with high risk prediction."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured_output = AsyncMock(
            return_value={
                "success_probability": 30,
                "risk_level": "high",
                "predicted_issues": [
                    {"issue": "Missing metadata", "severity": "error", "likelihood": "likely"},
                    {"issue": "File structure problem", "severity": "warning", "likelihood": "possible"},
                ],
                "suggested_fixes": ["Add metadata file", "Check file structure"],
                "warning_message": "High risk of conversion failure",
                "should_proceed": False,
            }
        )
        mock_dependencies["llm_service"] = mock_llm
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"test data")

        result = await orchestrator._proactive_issue_detection(
            input_path=str(test_file),
            format_name="testformat",
            state=global_state,
        )

        assert result["risk_level"] == "high"
        assert result["success_probability"] == 30
        assert result["should_proceed"] is False
        assert len(result["predicted_issues"]) == 2
        assert len(result["suggested_fixes"]) == 2

    @pytest.mark.asyncio
    async def test_file_characteristics_gathered(self, mock_dependencies, global_state, tmp_path):
        """Test that file characteristics are properly gathered."""
        mock_llm = AsyncMock()
        captured_prompt = None

        async def capture_prompt(**kwargs):
            nonlocal captured_prompt
            captured_prompt = kwargs["prompt"]
            return {
                "success_probability": 80,
                "risk_level": "low",
                "should_proceed": True,
            }

        mock_llm.generate_structured_output = capture_prompt
        mock_dependencies["llm_service"] = mock_llm
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        # Create test file with companion files
        test_file = tmp_path / "test_data.dat"
        test_file.write_bytes(b"x" * 1024 * 1024)  # 1 MB
        (tmp_path / "test_data.json").write_text("{}")
        (tmp_path / "test_data.meta").write_text("metadata")

        await orchestrator._proactive_issue_detection(
            input_path=str(test_file),
            format_name="testformat",
            state=global_state,
        )

        # Verify prompt includes file info
        assert "test_data.dat" in captured_prompt
        assert "testformat" in captured_prompt
        assert "test_data.json" in captured_prompt or "test_data.meta" in captured_prompt

    @pytest.mark.asyncio
    async def test_nonexistent_file_returns_unknown(self, mock_dependencies, global_state):
        """Test handling of nonexistent file path."""
        mock_llm = AsyncMock()
        mock_dependencies["llm_service"] = mock_llm
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        result = await orchestrator._proactive_issue_detection(
            input_path="/nonexistent/file.dat",
            format_name="testformat",
            state=global_state,
        )

        # Should handle gracefully and return unknown
        assert result["risk_level"] == "unknown"
        assert result["should_proceed"] is True
        # LLM should not be called if file info gathering fails
        mock_llm.generate_structured_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_failure_returns_unknown(self, mock_dependencies, global_state, tmp_path):
        """Test graceful handling when LLM fails."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured_output = AsyncMock(side_effect=Exception("LLM error"))
        mock_dependencies["llm_service"] = mock_llm
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"test data")

        result = await orchestrator._proactive_issue_detection(
            input_path=str(test_file),
            format_name="testformat",
            state=global_state,
        )

        # Should handle exception and return unknown
        assert result["risk_level"] == "unknown"
        assert result["should_proceed"] is True

        # Should log warning
        warning_logs = [log for log in global_state.logs if log.level == LogLevel.WARNING.value]
        assert any("Proactive analysis failed" in log.message for log in warning_logs)

    @pytest.mark.asyncio
    async def test_logs_risk_assessment(self, mock_dependencies, global_state, tmp_path):
        """Test that risk assessment is logged."""
        mock_llm = AsyncMock()
        mock_llm.generate_structured_output = AsyncMock(
            return_value={
                "success_probability": 75,
                "risk_level": "medium",
                "predicted_issues": [{"issue": "test", "severity": "warning", "likelihood": "possible"}],
                "should_proceed": True,
            }
        )
        mock_dependencies["llm_service"] = mock_llm
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        test_file = tmp_path / "test.dat"
        test_file.write_bytes(b"test data")

        await orchestrator._proactive_issue_detection(
            input_path=str(test_file),
            format_name="testformat",
            state=global_state,
        )

        # Verify logging
        info_logs = [log for log in global_state.logs if log.level == LogLevel.INFO.value]
        assert any("Proactive analysis" in log.message and "medium risk" in log.message for log in info_logs)

    @pytest.mark.asyncio
    async def test_companion_metadata_files_detected(self, mock_dependencies, global_state, tmp_path):
        """Test detection of companion metadata files."""
        mock_llm = AsyncMock()
        captured_prompt = None

        async def capture_prompt(**kwargs):
            nonlocal captured_prompt
            captured_prompt = kwargs["prompt"]
            return {
                "success_probability": 85,
                "risk_level": "low",
                "should_proceed": True,
            }

        mock_llm.generate_structured_output = capture_prompt
        mock_dependencies["llm_service"] = mock_llm
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        # Create test file with metadata companion
        test_file = tmp_path / "data.dat"
        test_file.write_bytes(b"data")
        (tmp_path / "metadata.json").write_text("{}")

        await orchestrator._proactive_issue_detection(
            input_path=str(test_file),
            format_name="testformat",
            state=global_state,
        )

        # Should detect metadata file
        assert "Has metadata: True" in captured_prompt or "metadata.json" in captured_prompt

    @pytest.mark.asyncio
    async def test_file_size_calculation(self, mock_dependencies, global_state, tmp_path):
        """Test file size is correctly calculated and included."""
        mock_llm = AsyncMock()
        captured_prompt = None

        async def capture_prompt(**kwargs):
            nonlocal captured_prompt
            captured_prompt = kwargs["prompt"]
            return {
                "success_probability": 90,
                "risk_level": "low",
                "should_proceed": True,
            }

        mock_llm.generate_structured_output = capture_prompt
        mock_dependencies["llm_service"] = mock_llm
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        # Create 2MB file
        test_file = tmp_path / "large.dat"
        test_file.write_bytes(b"x" * (2 * 1024 * 1024))

        await orchestrator._proactive_issue_detection(
            input_path=str(test_file),
            format_name="testformat",
            state=global_state,
        )

        # Should include size in prompt
        assert "2.0 MB" in captured_prompt or "Size: 2" in captured_prompt


# ============================================================================
# PASSED_WITH_ISSUES Handling Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestFinalizeWithMinimalMetadata:
    """Test _finalize_with_minimal_metadata method."""

    @pytest.mark.asyncio
    async def test_generates_report(self, mock_dependencies, global_state, tmp_path):
        """Test that report is generated when finalizing."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)  # 1 KB

        mock_report_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={"report_path": "/test/report.html"},
        )

        report_called = False

        async def mock_send_message(msg):
            nonlocal report_called
            if msg.action == "generate_report":
                report_called = True
                return mock_report_response
            return MCPResponse(success=False, reply_to=msg.message_id, error={"message": "Unknown"})

        orchestrator._mcp_server.send_message = mock_send_message

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [{"severity": "WARNING", "message": "Missing experimenter"}],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        assert report_called is True
        assert response.result["report_path"] == "/test/report.html"

    @pytest.mark.asyncio
    async def test_extracts_missing_experimenter(self, mock_dependencies, global_state, tmp_path):
        """Test extraction of missing 'experimenter' field."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [{"severity": "WARNING", "message": "Missing required field: experimenter"}],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        assert "experimenter" in response.result["missing_fields"]

    @pytest.mark.asyncio
    async def test_extracts_missing_institution(self, mock_dependencies, global_state, tmp_path):
        """Test extraction of missing 'institution' field."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [{"severity": "WARNING", "message": "institution not found in metadata"}],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        assert "institution" in response.result["missing_fields"]

    @pytest.mark.asyncio
    async def test_extracts_multiple_missing_fields(self, mock_dependencies, global_state, tmp_path):
        """Test extraction of multiple missing fields."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [
                {"severity": "WARNING", "message": "Missing experimenter"},
                {"severity": "WARNING", "message": "institution not found"},
                {"severity": "WARNING", "message": "keywords are missing"},
            ],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        missing = response.result["missing_fields"]
        assert "experimenter" in missing
        assert "institution" in missing
        assert "keywords" in missing

    @pytest.mark.asyncio
    async def test_includes_file_size_in_message(self, mock_dependencies, global_state, tmp_path):
        """Test that file size is included in completion message."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        # Create 2MB file
        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * (2 * 1024 * 1024))

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        assert "2.0 MB" in response.result["message"]

    @pytest.mark.asyncio
    async def test_includes_format_name_in_message(self, mock_dependencies, global_state, tmp_path):
        """Test that format name is included in message."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="CED Signal",
            input_path="/test/input.dat",
            state=global_state,
        )

        assert "CED Signal" in response.result["message"]

    @pytest.mark.asyncio
    async def test_completion_status_set(self, mock_dependencies, global_state, tmp_path):
        """Test that status is set to completed_with_warnings."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        assert response.result["status"] == "completed_with_warnings"

    @pytest.mark.asyncio
    async def test_user_declined_metadata_flag(self, mock_dependencies, global_state, tmp_path):
        """Test that user_declined_metadata flag is set to True."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        assert response.result["user_declined_metadata"] is True

    @pytest.mark.asyncio
    async def test_logging_finalization(self, mock_dependencies, global_state, tmp_path):
        """Test that finalization is logged."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [],
        }

        await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        # Should log finalization
        info_logs = [log for log in global_state.logs if log.level == LogLevel.INFO.value]
        assert any("Finalizing conversion with minimal metadata" in log.message for log in info_logs)

    @pytest.mark.asyncio
    async def test_deduplicates_missing_fields(self, mock_dependencies, global_state, tmp_path):
        """Test that duplicate missing fields are deduplicated."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [
                {"severity": "WARNING", "message": "Missing experimenter"},
                {"severity": "WARNING", "message": "experimenter not found"},
                {"severity": "WARNING", "message": "Experimenter is required but missing"},
            ],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        # Should only have 'experimenter' once
        missing = response.result["missing_fields"]
        assert missing.count("experimenter") == 1

    @pytest.mark.asyncio
    async def test_includes_helpful_guidance(self, mock_dependencies, global_state, tmp_path):
        """Test that message includes helpful guidance for adding metadata later."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        message = response.result["message"]
        # Should include guidance
        assert "How to add metadata later" in message
        assert "PyNWB" in message or "Re-run conversion" in message

    @pytest.mark.asyncio
    async def test_returns_success_response(self, mock_dependencies, global_state, tmp_path):
        """Test that method returns success MCPResponse."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        assert isinstance(response, MCPResponse)
        assert response.success is True
        assert response.reply_to == "msg-id"

    @pytest.mark.asyncio
    async def test_includes_subject_and_session_description(self, mock_dependencies, global_state, tmp_path):
        """Test extraction of subject and session_description fields."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"x" * 1024)

        mock_report_response = MCPResponse(success=True, reply_to="msg-id", result={})
        orchestrator._mcp_server.send_message = AsyncMock(return_value=mock_report_response)

        validation_result = {
            "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
            "issues": [
                {"severity": "WARNING", "message": "subject information missing"},
                {"severity": "WARNING", "message": "session_description not found"},
            ],
        }

        response = await orchestrator._finalize_with_minimal_metadata(
            original_message_id="msg-id",
            output_path=str(output_file),
            validation_result=validation_result,
            format_name="testformat",
            input_path="/test/input.dat",
            state=global_state,
        )

        missing = response.result["missing_fields"]
        assert "subject" in missing
        assert "session_description" in missing


# ============================================================================
# Integration Tests for _run_conversion with Validation Outcomes
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestRunConversionValidationOutcomes:
    """Integration tests for _run_conversion method focusing on validation outcome handling.

    Tests lines 970-1158 which handle the three validation outcomes:
    - PASSED: Clean success (lines 932-968)
    - PASSED_WITH_ISSUES: Warnings present (lines 970-1061)
    - FAILED: Critical/error issues (lines 1063-1158)
    """

    @pytest.mark.asyncio
    async def test_passed_with_issues_outcome(self, mock_dependencies, global_state, tmp_path):
        """Test PASSED_WITH_ISSUES validation outcome (lines 970-1061)."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        # Create test input file
        input_file = tmp_path / "test_input.dat"
        input_file.write_bytes(b"test data")

        # Mock conversion success
        conversion_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={
                "output_path": str(tmp_path / "output.nwb"),
                "status": "success",
            },
        )

        # Mock validation with PASSED_WITH_ISSUES outcome (lines 970-1061)
        validation_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={
                "validation_result": {
                    "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
                    "summary": {
                        "warning": 2,
                        "best_practice": 1,
                        "info": 1,
                    },
                    "issues": [
                        {"severity": "WARNING", "message": "Missing experimenter"},
                        {"severity": "WARNING", "message": "Missing institution"},
                        {"severity": "BEST_PRACTICE_SUGGESTION", "message": "Add keywords"},
                        {"severity": "INFO", "message": "Session description could be more detailed"},
                    ],
                }
            },
        )

        # Mock report generation
        report_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={"report_path": "/test/report.html"},
        )

        # Setup MCP server to return different responses based on action
        async def mock_send_message(msg):
            if msg.action == "run_conversion":
                # Create output file for validation
                output_file = tmp_path / "output.nwb"
                output_file.write_bytes(b"x" * 1024)
                return conversion_response
            elif msg.action == "run_validation":
                return validation_response
            elif msg.action == "generate_report":
                return report_response
            return MCPResponse(success=False, reply_to=msg.message_id, error={"message": "Unknown action"})

        orchestrator._mcp_server.send_message = mock_send_message

        # Call _run_conversion
        response = await orchestrator._run_conversion(
            original_message_id="msg-id",
            input_path=str(input_file),
            format_name="testformat",
            metadata={"session_description": "Test session"},
            state=global_state,
        )

        # Verify PASSED_WITH_ISSUES response (lines 1050-1061)
        assert response.success
        assert response.result["status"] == "awaiting_user_input"
        assert response.result["conversation_type"] == "improvement_decision"
        assert response.result["overall_status"] == ValidationOutcome.PASSED_WITH_ISSUES

        # Verify message includes issue counts (lines 998-1009)
        message = response.result["message"]
        assert "2 warnings" in message
        assert "1 best practice suggestion" in message
        assert "1 informational issue" in message

        # Verify state updates (lines 1033-1037)
        assert global_state.status == ConversionStatus.AWAITING_USER_INPUT
        from agentic_neurodata_conversion.models.state import ConversationPhase

        assert global_state.conversation_phase == ConversationPhase.IMPROVEMENT_DECISION

    @pytest.mark.asyncio
    async def test_passed_with_issues_shows_top_5_issues(self, mock_dependencies, global_state, tmp_path):
        """Test that PASSED_WITH_ISSUES shows top 5 issues (lines 1014-1022)."""
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        input_file = tmp_path / "test_input.dat"
        input_file.write_bytes(b"test data")

        # Create 10 issues to test the "top 5" logic
        issues = [{"severity": "WARNING", "message": f"Issue {i}"} for i in range(1, 11)]

        validation_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={
                "validation_result": {
                    "overall_status": ValidationOutcome.PASSED_WITH_ISSUES,
                    "summary": {"warning": 10},
                    "issues": issues,
                }
            },
        )

        async def mock_send_message(msg):
            if msg.action == "run_conversion":
                output_file = tmp_path / "output.nwb"
                output_file.write_bytes(b"x" * 1024)
                return MCPResponse(
                    success=True, reply_to=msg.message_id, result={"output_path": str(output_file), "status": "success"}
                )
            elif msg.action == "run_validation":
                return validation_response
            elif msg.action == "generate_report":
                return MCPResponse(success=True, reply_to=msg.message_id, result={"report_path": "/test/report.html"})
            return MCPResponse(success=False, reply_to=msg.message_id, error={"message": "Unknown"})

        orchestrator._mcp_server.send_message = mock_send_message

        response = await orchestrator._run_conversion(
            original_message_id="msg-id",
            input_path=str(input_file),
            format_name="testformat",
            metadata={"session_description": "Test"},
            state=global_state,
        )

        # Verify only top 5 issues shown (lines 1014-1020)
        message = response.result["message"]
        assert "1. [WARNING] Issue 1" in message
        assert "5. [WARNING] Issue 5" in message
        assert "and 5 more issues" in message  # Line 1020

    @pytest.mark.asyncio
    async def test_failed_with_llm_analysis(self, mock_dependencies, global_state, tmp_path):
        """Test FAILED validation with LLM analysis (lines 1067-1125)."""
        # Setup conversational handler with LLM analysis
        mock_conversational_handler = Mock()
        mock_conversational_handler.analyze_validation_and_respond = AsyncMock(
            return_value={
                "message": "I analyzed the validation issues. Here's what needs to be fixed...",
                "needs_user_input": True,
                "suggested_fixes": ["Add experimenter field", "Add institution field"],
                "required_fields": ["experimenter", "institution"],
                "proceed_with_minimal": False,  # Don't finalize
            }
        )
        mock_dependencies["conversational_handler"] = mock_conversational_handler
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        input_file = tmp_path / "test_input.dat"
        input_file.write_bytes(b"test data")

        # Mock FAILED validation
        validation_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={
                "validation_result": {
                    "overall_status": ValidationOutcome.FAILED,
                    "summary": {"error": 2, "critical": 1},
                    "issues": [
                        {"severity": "ERROR", "message": "Missing required field: experimenter"},
                        {"severity": "ERROR", "message": "Missing required field: institution"},
                        {"severity": "CRITICAL", "message": "Invalid file structure"},
                    ],
                }
            },
        )

        async def mock_send_message(msg):
            if msg.action == "run_conversion":
                output_file = tmp_path / "output.nwb"
                output_file.write_bytes(b"x" * 1024)
                return MCPResponse(
                    success=True, reply_to=msg.message_id, result={"output_path": str(output_file), "status": "success"}
                )
            elif msg.action == "run_validation":
                return validation_response
            return MCPResponse(success=False, reply_to=msg.message_id, error={"message": "Unknown"})

        orchestrator._mcp_server.send_message = mock_send_message

        response = await orchestrator._run_conversion(
            original_message_id="msg-id",
            input_path=str(input_file),
            format_name="testformat",
            metadata={},
            state=global_state,
        )

        # Verify LLM analysis was used (lines 1075-1080)
        mock_conversational_handler.analyze_validation_and_respond.assert_called_once()

        # Verify response structure (lines 1110-1125)
        assert response.success
        assert response.result["status"] == "awaiting_user_input"
        assert response.result["conversation_type"] == "validation_analysis"
        assert "suggested_fixes" in response.result
        assert "required_fields" in response.result
        assert response.result["can_retry"] is True

        # Verify state updates (lines 1068, 1106-1108)
        assert global_state.status == ConversionStatus.AWAITING_USER_INPUT
        from agentic_neurodata_conversion.models.state import ConversationPhase

        assert global_state.conversation_phase == ConversationPhase.VALIDATION_ANALYSIS

    @pytest.mark.asyncio
    async def test_failed_with_proceed_minimal_flag(self, mock_dependencies, global_state, tmp_path):
        """Test FAILED validation with proceed_with_minimal=True (lines 1083-1098)."""
        # Setup conversational handler to return proceed_with_minimal=True
        mock_conversational_handler = Mock()
        mock_conversational_handler.analyze_validation_and_respond = AsyncMock(
            return_value={
                "message": "Proceeding with minimal metadata as requested",
                "proceed_with_minimal": True,  # Trigger finalization path
            }
        )
        mock_dependencies["conversational_handler"] = mock_conversational_handler
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        input_file = tmp_path / "test_input.dat"
        input_file.write_bytes(b"test data")

        validation_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={
                "validation_result": {
                    "overall_status": ValidationOutcome.FAILED,
                    "summary": {"error": 1},
                    "issues": [{"severity": "ERROR", "message": "Missing experimenter"}],
                }
            },
        )

        # Mock report generation for finalization
        report_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={"report_path": "/test/report.html"},
        )

        async def mock_send_message(msg):
            if msg.action == "run_conversion":
                # Create the output file at the path specified in the message
                output_path = msg.context["output_path"]
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(b"x" * 1024)
                return MCPResponse(
                    success=True, reply_to=msg.message_id, result={"output_path": output_path, "status": "success"}
                )
            elif msg.action == "run_validation":
                return validation_response
            elif msg.action == "generate_report":
                return report_response
            return MCPResponse(success=False, reply_to=msg.message_id, error={"message": "Unknown"})

        orchestrator._mcp_server.send_message = mock_send_message

        response = await orchestrator._run_conversion(
            original_message_id="msg-id",
            input_path=str(input_file),
            format_name="testformat",
            metadata={},
            state=global_state,
        )

        # Check if analyze_validation_and_respond was called
        mock_conversational_handler.analyze_validation_and_respond.assert_called_once()

        # Check logs to see what happened
        info_logs = [log for log in global_state.logs if log.level == LogLevel.INFO.value]
        log_messages = [log.message for log in info_logs]

        # Verify finalization path was taken (lines 1083-1098)
        assert response.success, (
            f"Response failed: {response.error if hasattr(response, 'error') else 'No error'}, logs: {log_messages}"
        )
        assert response.result["status"] == "completed_with_warnings", (
            f"Got status: {response.result.get('status')}, logs: {log_messages}"
        )
        assert response.result["user_declined_metadata"] is True

        # Verify state was updated to COMPLETED (line 1084)
        assert global_state.status == ConversionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_failed_without_llm_falls_back_to_retry(self, mock_dependencies, global_state, tmp_path):
        """Test FAILED validation without LLM falls back to retry flow (lines 1126-1158)."""
        # No conversational handler - should fall back to retry approval
        mock_dependencies["conversational_handler"] = None
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        input_file = tmp_path / "test_input.dat"
        input_file.write_bytes(b"test data")

        validation_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={
                "validation_result": {
                    "overall_status": ValidationOutcome.FAILED,
                    "summary": {"error": 2},
                    "issues": [
                        {"severity": "ERROR", "message": "Error 1"},
                        {"severity": "ERROR", "message": "Error 2"},
                    ],
                }
            },
        )

        async def mock_send_message(msg):
            if msg.action == "run_conversion":
                output_file = tmp_path / "output.nwb"
                output_file.write_bytes(b"x" * 1024)
                return MCPResponse(
                    success=True, reply_to=msg.message_id, result={"output_path": str(output_file), "status": "success"}
                )
            elif msg.action == "run_validation":
                return validation_response
            return MCPResponse(success=False, reply_to=msg.message_id, error={"message": "Unknown"})

        orchestrator._mcp_server.send_message = mock_send_message

        response = await orchestrator._run_conversion(
            original_message_id="msg-id",
            input_path=str(input_file),
            format_name="testformat",
            metadata={},
            state=global_state,
        )

        # Verify fallback to retry approval (lines 1134-1158)
        assert response.success
        # State should be AWAITING_RETRY_APPROVAL (line 1136)
        assert global_state.status == ConversionStatus.AWAITING_RETRY_APPROVAL

    @pytest.mark.asyncio
    async def test_failed_llm_exception_fallback(self, mock_dependencies, global_state, tmp_path):
        """Test FAILED validation when LLM analysis raises exception (lines 1126-1132)."""
        # Setup conversational handler to raise exception
        mock_conversational_handler = Mock()
        mock_conversational_handler.analyze_validation_and_respond = AsyncMock(
            side_effect=Exception("LLM analysis failed")
        )
        mock_dependencies["conversational_handler"] = mock_conversational_handler
        orchestrator = WorkflowOrchestrator(**mock_dependencies)

        input_file = tmp_path / "test_input.dat"
        input_file.write_bytes(b"test data")

        validation_response = MCPResponse(
            success=True,
            reply_to="msg-id",
            result={
                "validation_result": {
                    "overall_status": ValidationOutcome.FAILED,
                    "summary": {"error": 1},
                    "issues": [{"severity": "ERROR", "message": "Test error"}],
                }
            },
        )

        async def mock_send_message(msg):
            if msg.action == "run_conversion":
                output_file = tmp_path / "output.nwb"
                output_file.write_bytes(b"x" * 1024)
                return MCPResponse(
                    success=True, reply_to=msg.message_id, result={"output_path": str(output_file), "status": "success"}
                )
            elif msg.action == "run_validation":
                return validation_response
            return MCPResponse(success=False, reply_to=msg.message_id, error={"message": "Unknown"})

        orchestrator._mcp_server.send_message = mock_send_message

        response = await orchestrator._run_conversion(
            original_message_id="msg-id",
            input_path=str(input_file),
            format_name="testformat",
            metadata={},
            state=global_state,
        )

        # Verify exception was logged (line 1127-1132)
        error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR.value]
        assert any("LLM analysis failed" in log.message for log in error_logs)

        # Verify fallback to retry approval (lines 1136-1158)
        assert global_state.status == ConversionStatus.AWAITING_RETRY_APPROVAL
