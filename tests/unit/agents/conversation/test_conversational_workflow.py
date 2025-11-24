"""Unit tests for ConversationalWorkflow.

Tests conversational interaction handling, metadata extraction,
multi-turn conversations, and workflow continuation.

Phase 1 Target: Lines 338-380 (ready to proceed path)
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.conversation.conversational_workflow import (
    ConversationalWorkflow,
)
from agentic_neurodata_conversion.models import (
    ConversationPhase,
    ConversionStatus,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationStatus,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for ConversationalWorkflow."""
    metadata_collector = Mock()
    metadata_parser = Mock()
    provenance_tracker = Mock()
    provenance_tracker.track_user_provided_metadata = Mock()

    workflow_manager = Mock()

    conversational_handler = Mock()
    conversational_handler.detect_skip_type_with_llm = AsyncMock(return_value="none")
    conversational_handler.process_user_response = AsyncMock(
        return_value={
            "type": "conversation_continues",
            "follow_up_message": "Got it! Any other metadata?",
            "extracted_metadata": {},
            "ready_to_proceed": False,
            "needs_more_info": True,
        }
    )

    llm_service = Mock()
    llm_service.generate_response = AsyncMock(return_value="Mock response")

    return {
        "metadata_collector": metadata_collector,
        "metadata_parser": metadata_parser,
        "provenance_tracker": provenance_tracker,
        "workflow_manager": workflow_manager,
        "conversational_handler": conversational_handler,
        "llm_service": llm_service,
    }


@pytest.fixture
def workflow(mock_dependencies):
    """Create ConversationalWorkflow instance with mocked dependencies."""
    return ConversationalWorkflow(**mock_dependencies)


@pytest.fixture
def conversational_message():
    """Create a conversational response message."""
    return MCPMessage(
        target_agent="conversation",
        action="conversational_response",
        context={"message": "The experiment was conducted on 2024-01-15"},
        message_id="test-msg-id",
    )


@pytest.fixture
def mock_callbacks():
    """Create mock workflow callbacks."""
    return {
        "handle_start_conversion_callback": AsyncMock(
            return_value=MCPResponse.success_response(
                reply_to="test",
                result={"status": "started"},
            )
        ),
        "continue_conversion_workflow_callback": AsyncMock(
            return_value=MCPResponse.success_response(
                reply_to="test",
                result={"status": "continued"},
            )
        ),
        "run_conversion_callback": AsyncMock(
            return_value=MCPResponse.success_response(
                reply_to="test",
                result={"status": "converting"},
            )
        ),
    }


# ============================================================================
# Phase 1: Core Interaction Tests (Lines 338-380)
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestReadyToProceedPath:
    """Test lines 335-386: User ready to proceed workflow continuation."""

    @pytest.mark.asyncio
    async def test_ready_to_proceed_with_valid_path(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 335-386: Normal ready to proceed path with valid conversion path."""
        # Setup: User is ready to proceed with metadata
        mock_dependencies["conversational_handler"].process_user_response = AsyncMock(
            return_value={
                "type": "ready_to_convert",
                "follow_up_message": "Great! Starting conversion now.",
                "extracted_metadata": {"experimenter": "Dr. Smith", "session_start_time": "2024-01-15T10:00:00"},
                "ready_to_proceed": True,
                "needs_more_info": False,
            }
        )

        # Set state for metadata collection phase
        global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION
        global_state.conversation_type = "metadata_collection"
        global_state.pending_conversion_input_path = "/test/data/input.dat"
        global_state.input_path = "/test/data/input.dat"
        # Format must be in auto_extracted_metadata to survive merge on lines 308-309
        global_state.auto_extracted_metadata = {"format": "Calcium Imaging"}
        global_state.metadata = {"format": "Calcium Imaging"}

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: user_provided_input_this_attempt flag set (line 338)
        assert global_state.user_provided_input_this_attempt is True

        # Verify: conversation phase reset to IDLE (lines 341-343)
        assert global_state.conversation_phase == ConversationPhase.IDLE
        assert global_state.conversation_type is None

        # Verify: metadata was persisted (lines 304-309)
        assert "experimenter" in global_state.user_provided_metadata
        assert "session_start_time" in global_state.user_provided_metadata
        assert "experimenter" in global_state.metadata

        # Verify: provenance tracked (lines 316-323)
        assert mock_dependencies["provenance_tracker"].track_user_provided_metadata.call_count == 2

        # Verify: continue_conversion_workflow_callback called (lines 380-386)
        mock_callbacks["continue_conversion_workflow_callback"].assert_called_once()
        call_kwargs = mock_callbacks["continue_conversion_workflow_callback"].call_args.kwargs
        assert call_kwargs["input_path"] == "/test/data/input.dat"
        assert call_kwargs["detected_format"] == "Calcium Imaging"

        # Verify: success response
        assert response.success is True

    @pytest.mark.asyncio
    async def test_ready_to_proceed_missing_conversion_path(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 354-371: Error when conversion path is missing/invalid."""
        # Setup: User ready but no valid path
        mock_dependencies["conversational_handler"].process_user_response = AsyncMock(
            return_value={
                "type": "ready_to_convert",
                "follow_up_message": "Ready to start!",
                "extracted_metadata": {},
                "ready_to_proceed": True,
                "needs_more_info": False,
            }
        )

        # Set state WITHOUT valid conversion path
        global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION
        global_state.pending_conversion_input_path = None
        global_state.input_path = None

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: error response (lines 367-371)
        assert response.success is False
        assert response.error["code"] == "INVALID_STATE"
        assert "file path is not available" in response.error["message"]

        # Verify: error logged (lines 355-365)
        error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR]
        assert len(error_logs) > 0
        assert any("Cannot restart conversion" in log.message for log in error_logs)

        # Verify: callback NOT called
        mock_callbacks["continue_conversion_workflow_callback"].assert_not_called()

    @pytest.mark.asyncio
    async def test_ready_to_proceed_with_fallback_to_input_path(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 351-353: Fallback to input_path when pending_conversion_input_path is None."""
        # Setup: User ready with fallback path
        mock_dependencies["conversational_handler"].process_user_response = AsyncMock(
            return_value={
                "type": "ready_to_convert",
                "follow_up_message": "Starting conversion.",
                "extracted_metadata": {},
                "ready_to_proceed": True,
                "needs_more_info": False,
            }
        )

        # Set state: pending_conversion_input_path is None, but input_path is valid
        global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION
        global_state.pending_conversion_input_path = None
        global_state.input_path = "/fallback/path/data.dat"
        global_state.auto_extracted_metadata = {"format": "Electrophysiology"}
        global_state.metadata = {"format": "Electrophysiology"}

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: fallback path used (line 353)
        mock_callbacks["continue_conversion_workflow_callback"].assert_called_once()
        call_kwargs = mock_callbacks["continue_conversion_workflow_callback"].call_args.kwargs
        assert call_kwargs["input_path"] == "/fallback/path/data.dat"

        # Verify: success response
        assert response.success is True

    @pytest.mark.asyncio
    async def test_ready_to_proceed_without_format_detection(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 373-386: Continue workflow without re-running format detection."""
        # Setup: Format already detected
        mock_dependencies["conversational_handler"].process_user_response = AsyncMock(
            return_value={
                "type": "ready_to_convert",
                "follow_up_message": "Continuing...",
                "extracted_metadata": {},
                "ready_to_proceed": True,
                "needs_more_info": False,
            }
        )

        global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION
        global_state.pending_conversion_input_path = "/test/input.dat"
        global_state.auto_extracted_metadata = {"format": "Behavioral", "experimenter": "Dr. Jones"}
        global_state.metadata = {"format": "Behavioral", "experimenter": "Dr. Jones"}

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: detected_format passed from metadata (line 377)
        call_kwargs = mock_callbacks["continue_conversion_workflow_callback"].call_args.kwargs
        assert call_kwargs["detected_format"] == "Behavioral"
        assert call_kwargs["metadata"]["experimenter"] == "Dr. Jones"

        # Verify: workflow continues (not starts from scratch)
        assert response.success is True


# ============================================================================
# Phase 1: Metadata Extraction and Persistence (Lines 300-332)
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataExtractionAndPersistence:
    """Test lines 300-332: Incremental metadata extraction and provenance tracking."""

    @pytest.mark.asyncio
    async def test_metadata_persisted_incrementally(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 303-309: Extracted metadata persisted incrementally during conversation."""
        # Setup: Multi-turn conversation with incremental metadata
        mock_dependencies["conversational_handler"].process_user_response = AsyncMock(
            return_value={
                "type": "conversation_continues",
                "follow_up_message": "Great! What about the institution?",
                "extracted_metadata": {"experimenter": "Dr. Smith", "lab": "Neural Lab"},
                "ready_to_proceed": False,
                "needs_more_info": True,
            }
        )

        # Pre-existing auto-extracted metadata
        global_state.auto_extracted_metadata = {"format": "Calcium Imaging", "session_id": "S001"}
        global_state.metadata = {"format": "Calcium Imaging", "session_id": "S001"}

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: user_provided_metadata updated (line 305)
        assert "experimenter" in global_state.user_provided_metadata
        assert global_state.user_provided_metadata["experimenter"] == "Dr. Smith"
        assert "lab" in global_state.user_provided_metadata

        # Verify: combined metadata includes both auto and user (lines 308-309)
        assert "format" in global_state.metadata  # Auto-extracted
        assert "session_id" in global_state.metadata  # Auto-extracted
        assert "experimenter" in global_state.metadata  # User-provided
        assert "lab" in global_state.metadata  # User-provided

        # Verify: metadata logged (lines 325-332)
        info_logs = [log for log in global_state.logs if log.level == LogLevel.INFO]
        metadata_logs = [log for log in info_logs if "User-provided metadata extracted and persisted" in log.message]
        assert len(metadata_logs) > 0

    @pytest.mark.asyncio
    async def test_provenance_tracking_for_user_metadata(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 314-323: Provenance tracked for user-provided metadata."""
        # Setup: User provides new metadata
        user_msg = "The experimenter was Dr. Alice Johnson and the session was on 2024-02-20"
        conversational_message.context["message"] = user_msg

        mock_dependencies["conversational_handler"].process_user_response = AsyncMock(
            return_value={
                "type": "conversation_continues",
                "follow_up_message": "Thanks! Anything else?",
                "extracted_metadata": {"experimenter": "Dr. Alice Johnson", "session_date": "2024-02-20"},
                "ready_to_proceed": False,
                "needs_more_info": True,
            }
        )

        # No existing provenance for these fields
        global_state.metadata_provenance = {}

        # Call handle_conversational_response
        await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: provenance tracked for both fields (lines 316-323)
        assert mock_dependencies["provenance_tracker"].track_user_provided_metadata.call_count == 2

        # Check calls for both fields
        calls = mock_dependencies["provenance_tracker"].track_user_provided_metadata.call_args_list
        field_names = [call.kwargs["field_name"] for call in calls]
        assert "experimenter" in field_names
        assert "session_date" in field_names

        # Verify source includes user message (line 321)
        experimenter_call = [call for call in calls if call.kwargs["field_name"] == "experimenter"][0]
        assert "User provided:" in experimenter_call.kwargs["source"]
        assert user_msg[:100] in experimenter_call.kwargs["source"]

    @pytest.mark.asyncio
    async def test_provenance_not_overwritten_if_already_set(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 315-316: Don't overwrite provenance if already set by parser."""
        # Setup: User provides metadata that was already parsed
        mock_dependencies["conversational_handler"].process_user_response = AsyncMock(
            return_value={
                "type": "conversation_continues",
                "follow_up_message": "Got it!",
                "extracted_metadata": {"experimenter": "Dr. Smith"},
                "ready_to_proceed": False,
                "needs_more_info": True,
            }
        )

        # Provenance already set by IntelligentMetadataParser
        global_state.metadata_provenance = {"experimenter": Mock(method="AI_PARSED")}

        # Call handle_conversational_response
        await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: provenance NOT tracked (condition on line 315 prevents it)
        mock_dependencies["provenance_tracker"].track_user_provided_metadata.assert_not_called()


# ============================================================================
# Phase 1: Input Validation (Lines 132-146)
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestInputValidation:
    """Test lines 132-146: Message input validation."""

    @pytest.mark.asyncio
    async def test_message_too_long_rejected(self, workflow, conversational_message, mock_callbacks, global_state):
        """Test line 132-137: Message over 10,000 characters is rejected."""
        # Setup: Message with 10,001 characters
        long_message = "x" * 10001
        conversational_message.context["message"] = long_message

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: error response (lines 133-137)
        assert response.success is False
        assert response.error["code"] == "MESSAGE_TOO_LONG"
        assert "under 10,000 characters" in response.error["message"]

    @pytest.mark.asyncio
    async def test_empty_message_after_strip_rejected(
        self, workflow, conversational_message, mock_callbacks, global_state
    ):
        """Test lines 140-146: Message that is empty after stripping is rejected."""
        # Setup: Message with only whitespace
        conversational_message.context["message"] = "   \n\t   "

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: error response (lines 142-146)
        assert response.success is False
        assert response.error["code"] == "EMPTY_MESSAGE"
        assert "cannot be empty" in response.error["message"]

    @pytest.mark.asyncio
    async def test_missing_message_field_rejected(self, workflow, mock_callbacks, global_state):
        """Test lines 124-129: Message without 'message' field is rejected."""
        # Setup: Message without 'message' in context
        message_without_content = MCPMessage(
            target_agent="conversation",
            action="conversational_response",
            context={},  # No "message" field
            message_id="test-msg-id",
        )

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=message_without_content,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: error response (lines 125-129)
        assert response.success is False
        assert response.error["code"] == "MISSING_MESSAGE"
        assert "required" in response.error["message"]


# ============================================================================
# Phase 1: Cancellation Keywords (Lines 162-180)
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestCancellationKeywords:
    """Test lines 162-180: Explicit cancellation keywords."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "keyword",
        ["cancel", "quit", "stop", "abort", "exit"],
    )
    async def test_cancellation_keywords_stop_workflow(
        self, workflow, conversational_message, mock_callbacks, global_state, keyword
    ):
        """Test line 162: Cancellation keywords stop the workflow."""
        # Setup: User sends cancellation keyword
        conversational_message.context["message"] = keyword

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: validation_status set to FAILED_USER_ABANDONED (line 165)
        assert global_state.validation_status == ValidationStatus.FAILED_USER_ABANDONED

        # Verify: status updated to FAILED (line 166)
        assert global_state.status == ConversionStatus.FAILED

        # Verify: success response with failed status (lines 173-180)
        assert response.success is True
        assert response.result["status"] == "failed"
        assert response.result["validation_status"] == "failed_user_abandoned"
        assert "cancelled by user" in response.result["message"].lower()

        # Verify: logged (lines 167-171)
        logs = [log for log in global_state.logs if "User abandoned" in log.message]
        assert len(logs) > 0

    @pytest.mark.asyncio
    async def test_cancellation_case_insensitive(self, workflow, conversational_message, mock_callbacks, global_state):
        """Test line 162: Cancellation detection is case-insensitive."""
        # Setup: Mixed case cancellation
        conversational_message.context["message"] = "CANCEL"

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: cancellation detected (line 162 uses .lower())
        assert response.success is True
        assert response.result["status"] == "failed"
        assert global_state.validation_status == ValidationStatus.FAILED_USER_ABANDONED


# ============================================================================
# Phase 2: Skip Handlers (Lines 846-856, 894-931)
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGlobalSkipHandler:
    """Test lines 846-856: Global skip error handling when path is missing."""

    @pytest.mark.asyncio
    async def test_global_skip_missing_path_error(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 846-856: Error when global skip requested but no valid path."""
        # Setup: User wants to skip all questions, but no path available
        mock_dependencies["conversational_handler"].detect_skip_type_with_llm = AsyncMock(return_value="global")

        # No valid path
        global_state.pending_conversion_input_path = None
        global_state.input_path = None

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: error response (lines 856-860)
        assert response.success is False
        assert response.error["code"] == "INVALID_STATE"
        assert "file path is not available" in response.error["message"]

        # Verify: error logged (lines 846-855)
        error_logs = [log for log in global_state.logs if log.level == LogLevel.ERROR]
        assert any("Cannot restart conversion" in log.message for log in error_logs)

        # Verify: callback NOT called
        mock_callbacks["handle_start_conversion_callback"].assert_not_called()


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestFieldSkipHandler:
    """Test lines 894-931: Field skip handling."""

    @pytest.mark.asyncio
    async def test_field_skip_with_current_field(self, workflow, mock_callbacks, global_state, mock_dependencies):
        """Test lines 894-929: Field skip when current field is in context.

        NOTE: This tests the implementation's actual behavior where it looks for field
        context in conversation_history[-1]. Due to how user messages are added (line 149),
        the field context must be directly accessible in the last message.
        """
        # Setup: User wants to skip a specific field
        mock_dependencies["conversational_handler"].detect_skip_type_with_llm = AsyncMock(return_value="field")

        # Create message with field in context (simulating a properly structured request)
        message_with_field = MCPMessage(
            target_agent="conversation",
            action="conversational_response",
            context={"message": "skip this field"},
            message_id="test-msg-id",
        )

        # Pre-populate conversation history so after user message is added,
        # we manually set field context on the last message
        global_state.conversation_history = []
        global_state.pending_conversion_input_path = "/test/data.dat"
        global_state.metadata = {"session_description": "Test"}

        # Manually add user message with field context (simulating the expected state)
        global_state.conversation_history.append(
            {
                "role": "user",
                "content": "skip this field",
                "context": {"field": "experimenter"},
            }
        )

        # Now call _handle_field_skip directly to test lines 894-929
        response = await workflow._handle_field_skip(
            user_message="skip this field",
            message_id="test-msg-id",
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
        )

        # Verify: field added to declined_fields (line 898)
        assert "experimenter" in global_state.user_declined_fields

        # Verify: skip logged (lines 899-903)
        info_logs = [log for log in global_state.logs if log.level == LogLevel.INFO]
        assert any("User skipped field: experimenter" in log.message for log in info_logs)

        # Verify: acknowledgment added to conversation (lines 906-907)
        last_message = global_state.conversation_history[-1]
        assert last_message["role"] == "assistant"
        assert "Skipping experimenter" in last_message["content"]

        # Verify: callback called to restart conversion (lines 919-929)
        mock_callbacks["handle_start_conversion_callback"].assert_called_once()
        call_args = mock_callbacks["handle_start_conversion_callback"].call_args
        message_arg = call_args[0][0]
        assert message_arg.action == "start_conversion"
        assert message_arg.context["input_path"] == "/test/data.dat"

        # Verify: success response
        assert response.success is True

    @pytest.mark.asyncio
    async def test_field_skip_missing_path(self, workflow, mock_callbacks, global_state, mock_dependencies):
        """Test lines 910-916: Error when field skip requested but no valid path."""
        # Setup: Manually add user message with field context
        global_state.conversation_history = [
            {
                "role": "user",
                "content": "skip institution",
                "context": {"field": "institution"},
            }
        ]

        # No valid path
        global_state.pending_conversion_input_path = None
        global_state.input_path = None

        # Call _handle_field_skip directly
        response = await workflow._handle_field_skip(
            user_message="skip institution",
            message_id="test-msg-id",
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
        )

        # Verify: field still added to declined_fields (line 898)
        assert "institution" in global_state.user_declined_fields

        # Verify: error response (lines 912-916)
        assert response.success is False
        assert response.error["code"] == "INVALID_STATE"
        assert "upload a file first" in response.error["message"]

        # Verify: callback NOT called
        mock_callbacks["handle_start_conversion_callback"].assert_not_called()

    @pytest.mark.asyncio
    async def test_field_skip_no_current_field(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test lines 931-935: Error when no current field in context."""
        # Setup: User wants to skip field, but no field in context
        mock_dependencies["conversational_handler"].detect_skip_type_with_llm = AsyncMock(return_value="field")

        # Conversation history WITHOUT field context
        global_state.conversation_history = [
            {
                "role": "assistant",
                "content": "How can I help you?",
                "context": {},  # No field key
            }
        ]

        global_state.pending_conversion_input_path = "/test/data.dat"

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: error response (lines 931-935)
        assert response.success is False
        assert response.error["code"] == "NO_CURRENT_FIELD"
        assert "Could not determine which field to skip" in response.error["message"]

        # Verify: callback NOT called
        mock_callbacks["handle_start_conversion_callback"].assert_not_called()

    @pytest.mark.asyncio
    async def test_field_skip_empty_conversation_history(
        self, workflow, conversational_message, mock_callbacks, global_state, mock_dependencies
    ):
        """Test line 894: Handle empty conversation history gracefully."""
        # Setup: User wants to skip field, but conversation history is empty
        mock_dependencies["conversational_handler"].detect_skip_type_with_llm = AsyncMock(return_value="field")

        # Empty conversation history
        global_state.conversation_history = []

        global_state.pending_conversion_input_path = "/test/data.dat"

        # Call handle_conversational_response
        response = await workflow.handle_conversational_response(
            message=conversational_message,
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
            continue_conversion_workflow_callback=mock_callbacks["continue_conversion_workflow_callback"],
            run_conversion_callback=mock_callbacks["run_conversion_callback"],
        )

        # Verify: error response because no current field (line 894 returns empty dict)
        assert response.success is False
        assert response.error["code"] == "NO_CURRENT_FIELD"


# ============================================================================
# Phase 3: Sequential Request Handler (Lines 955-976)
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestSequentialRequestHandler:
    """Test lines 955-976: Sequential questioning workflow."""

    @pytest.mark.asyncio
    async def test_sequential_request_success(self, workflow, mock_callbacks, global_state):
        """Test lines 955-984: Successful sequential request workflow."""
        # Setup
        global_state.pending_conversion_input_path = "/test/data.dat"
        global_state.metadata = {"format": "Test"}

        # Call _handle_sequential_request directly
        response = await workflow._handle_sequential_request(
            user_message="one at a time please",
            message_id="test-msg-id",
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
        )

        # Verify: sequential preference saved (line 961)
        assert global_state.user_wants_sequential is True

        # Verify: logged (lines 955-958)
        info_logs = [log for log in global_state.logs if log.level == LogLevel.INFO]
        assert any("sequential questioning" in log.message for log in info_logs)

        # Verify: acknowledgment added to conversation (lines 964-965)
        last_message = global_state.conversation_history[-1]
        assert last_message["role"] == "assistant"
        assert "one question at a time" in last_message["content"].lower()

        # Verify: callback called to restart conversion (lines 976-984)
        mock_callbacks["handle_start_conversion_callback"].assert_called_once()
        call_args = mock_callbacks["handle_start_conversion_callback"].call_args
        message_arg = call_args[0][0]
        assert message_arg.action == "start_conversion"
        assert message_arg.context["input_path"] == "/test/data.dat"

        # Verify: success response
        assert response.success is True

    @pytest.mark.asyncio
    async def test_sequential_request_missing_path(self, workflow, mock_callbacks, global_state):
        """Test lines 969-974: Error when sequential request but no valid path."""
        # Setup: No valid path
        global_state.pending_conversion_input_path = None
        global_state.input_path = None

        # Call _handle_sequential_request directly
        response = await workflow._handle_sequential_request(
            user_message="one at a time please",
            message_id="test-msg-id",
            state=global_state,
            handle_start_conversion_callback=mock_callbacks["handle_start_conversion_callback"],
        )

        # Verify: sequential preference still saved (line 961)
        assert global_state.user_wants_sequential is True

        # Verify: error response (lines 970-974)
        assert response.success is False
        assert response.error["code"] == "INVALID_STATE"
        assert "upload a file first" in response.error["message"]

        # Verify: callback NOT called
        mock_callbacks["handle_start_conversion_callback"].assert_not_called()
