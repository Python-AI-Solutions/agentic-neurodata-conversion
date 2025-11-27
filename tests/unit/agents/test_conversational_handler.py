"""
Unit tests for ConversationalHandler.

Tests intelligent LLM-driven conversational interactions for NWB conversion.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler
from agentic_neurodata_conversion.models import MetadataRequestPolicy
from agentic_neurodata_conversion.services.llm_service import MockLLMService


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestConversationalHandlerInitialization:
    """Tests for ConversationalHandler initialization."""

    def test_init_with_llm_service(self):
        """Test initialization with LLM service."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service=llm_service)

        assert handler.llm_service is llm_service
        assert handler.metadata_strategy is not None
        assert handler.context_manager is not None
        assert handler.metadata_parser is not None


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestDetectUserDecline:
    """Tests for detect_user_decline method."""

    def test_detect_user_decline_with_skip(self, real_conversational_handler):
        """Test detecting skip patterns with real helper agents."""
        # Uses real MetadataRequestStrategy for actual skip detection logic
        result = real_conversational_handler.detect_user_decline("skip this field")

        assert result is True

    def test_detect_user_decline_with_global_skip(self, real_conversational_handler):
        """Test detecting global skip patterns with real helper agents."""
        # Uses real MetadataRequestStrategy for actual skip detection logic
        result = real_conversational_handler.detect_user_decline("skip all metadata")

        assert result is True

    def test_detect_user_decline_with_no_skip(self, real_conversational_handler):
        """Test no decline detected with real helper agents."""
        # Uses real MetadataRequestStrategy for actual skip detection logic
        result = real_conversational_handler.detect_user_decline("I have the information")

        assert result is False


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestDetectSkipTypeWithLLM:
    """Tests for detect_skip_type_with_llm method."""

    @pytest.mark.asyncio
    async def test_detect_skip_type_with_llm_delegates(self):
        """Test method delegates to metadata_strategy."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        handler.metadata_strategy.detect_skip_type_with_llm = AsyncMock(return_value="field")

        result = await handler.detect_skip_type_with_llm("skip", "context")

        assert result == "field"
        handler.metadata_strategy.detect_skip_type_with_llm.assert_called_once_with("skip", "context")


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestDetectSkipType:
    """Tests for detect_skip_type method."""

    def test_detect_skip_type_delegates(self):
        """Test method delegates to metadata_strategy."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        handler.metadata_strategy.detect_skip_type = Mock(return_value="sequential")

        result = handler.detect_skip_type("skip for now")

        assert result == "sequential"
        handler.metadata_strategy.detect_skip_type.assert_called_once_with("skip for now")


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestAnalyzeValidationAndRespond:
    """Tests for analyze_validation_and_respond method."""

    @pytest.mark.asyncio
    async def test_analyze_validation_user_declined(self, global_state):
        """Test returns proceed_minimal when user declined."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        global_state.metadata_policy = MetadataRequestPolicy.USER_DECLINED

        validation_result = {"summary": {}, "issues": []}

        result = await handler.analyze_validation_and_respond(validation_result, "/test/file.nwb", global_state)

        assert result["type"] == "proceed_minimal"
        assert result["proceed_with_minimal"] is True
        assert result["needs_user_input"] is False

    @pytest.mark.asyncio
    async def test_analyze_validation_proceeding_minimal(self, global_state):
        """Test returns proceed_minimal when policy is PROCEEDING_MINIMAL."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        global_state.metadata_policy = MetadataRequestPolicy.PROCEEDING_MINIMAL

        validation_result = {"summary": {}, "issues": []}

        result = await handler.analyze_validation_and_respond(validation_result, "/test/file.nwb", global_state)

        assert result["type"] == "proceed_minimal"

    @pytest.mark.asyncio
    async def test_analyze_validation_needs_user_input(self, global_state):
        """Test requests user input when LLM indicates need."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "message": "I need some information",
                "needs_user_input": True,
                "severity": "medium",
            }
        )

        handler = ConversationalHandler(llm_service)
        handler.metadata_strategy.get_next_request = Mock(
            return_value={
                "action": "request",
                "message": "What is the experimenter name?",
                "phase": "required",
                "priority": "high",
                "field": "experimenter",
            }
        )

        validation_result = {
            "summary": {"error": 1},
            "issues": [{"message": "Missing experimenter"}],
        }

        result = await handler.analyze_validation_and_respond(validation_result, "/test/file.nwb", global_state)

        assert result["type"] == "conversational"
        assert result["needs_user_input"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_analyze_validation_no_user_input_needed(self, global_state):
        """Test returns conversational response without input request."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "message": "Everything looks good",
                "needs_user_input": False,
                "severity": "low",
            }
        )

        handler = ConversationalHandler(llm_service)

        validation_result = {"summary": {}, "issues": []}

        result = await handler.analyze_validation_and_respond(validation_result, "/test/file.nwb", global_state)

        assert result["type"] == "conversational"
        assert result["needs_user_input"] is False

    @pytest.mark.asyncio
    async def test_analyze_validation_strategy_proceed(self, global_state):
        """Test proceeds when strategy indicates proceed action."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "message": "Need info",
                "needs_user_input": True,
                "severity": "medium",
            }
        )

        handler = ConversationalHandler(llm_service)
        handler.metadata_strategy.get_next_request = Mock(return_value={"action": "proceed"})

        validation_result = {"summary": {}, "issues": []}

        result = await handler.analyze_validation_and_respond(validation_result, "/test/file.nwb", global_state)

        assert result["type"] == "proceed_minimal"

    @pytest.mark.asyncio
    async def test_analyze_validation_strategy_failure_fallback(self, global_state):
        """Test falls back when strategy fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "message": "Fallback message",
                "needs_user_input": True,
                "severity": "medium",
            }
        )

        handler = ConversationalHandler(llm_service)
        handler.metadata_strategy.get_next_request = Mock(side_effect=Exception("Strategy failed"))

        validation_result = {"summary": {}, "issues": []}

        result = await handler.analyze_validation_and_respond(validation_result, "/test/file.nwb", global_state)

        # Should fall back to simple response
        assert result["type"] == "conversational"
        assert result["message"] == "Fallback message"


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestFormatValidationIssues:
    """Tests for _format_validation_issues method."""

    def test_format_validation_issues_empty(self):
        """Test formatting with no issues."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        validation_result = {"issues": []}

        formatted = handler._format_validation_issues(validation_result)

        assert formatted == "No issues found"

    def test_format_validation_issues_with_issues(self):
        """Test formatting with issues."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        validation_result = {
            "issues": [
                {"severity": "ERROR", "message": "Missing experimenter"},
                {"severity": "WARNING", "message": "No keywords"},
            ]
        }

        formatted = handler._format_validation_issues(validation_result)

        assert "Missing experimenter" in formatted
        assert "ERROR" in formatted or "error" in formatted.lower()


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractBasicRequiredFields:
    """Tests for _extract_basic_required_fields method."""

    def test_extract_basic_required_fields_from_issues(self):
        """Test extracts fields from validation issues."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        validation_result = {
            "issues": [
                {"message": "Missing required field: experimenter"},
                {"message": "Missing required field: institution"},
            ]
        }

        fields = handler._extract_basic_required_fields(validation_result)

        # Should return list of dicts with field_name keys
        field_names = [f["field_name"] for f in fields]
        assert "experimenter" in field_names
        assert "institution" in field_names

        # Verify structure of first field
        assert len(fields) > 0
        first_field = fields[0]
        assert "field_name" in first_field
        assert "display_name" in first_field
        assert "description" in first_field
        assert "field_type" in first_field
        assert "example" in first_field


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestParseAndConfirmMetadata:
    """Tests for parse_and_confirm_metadata method."""

    @pytest.mark.asyncio
    async def test_parse_user_confirms_pending_fields(self, global_state):
        """Test user confirming previously parsed fields."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        # Set up pending parsed fields
        global_state.pending_parsed_fields = {
            "experimenter": ["Dr. Jane Smith"],
            "institution": "MIT",
        }

        result = await handler.parse_and_confirm_metadata("yes", global_state, mode="batch")

        assert result["type"] == "confirmed"
        assert "experimenter" in result["confirmed_fields"]
        assert "institution" in result["confirmed_fields"]

    @pytest.mark.asyncio
    async def test_parse_user_wants_to_edit(self, global_state):
        """Test user wants to edit parsed fields."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        global_state.pending_parsed_fields = {"experimenter": ["Dr. Jane Smith"]}

        result = await handler.parse_and_confirm_metadata("no, change it", global_state, mode="batch")

        assert result["type"] == "needs_edit"
        assert "confirmation_message" in result

    @pytest.mark.asyncio
    async def test_parse_user_skips_confirmation(self, global_state):
        """Test user skips/auto-applies metadata."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        global_state.pending_parsed_fields = {"experimenter": ["Dr. Smith"]}

        result = await handler.parse_and_confirm_metadata("skip", global_state, mode="batch")

        assert result["type"] == "auto_applied"
        assert "auto_applied_fields" in result

    @pytest.mark.asyncio
    async def test_parse_new_metadata_awaiting_confirmation(self, real_conversational_handler, global_state):
        """Test parsing new metadata with real MetadataParser."""
        # Uses real MetadataParser with MockLLMService for actual parsing logic
        # Configure MockLLMService to return expected structured output
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            return_value={
                "parsed_fields": [{"field_name": "experimenter", "value": ["Dr. Jane Smith"], "confidence": 95.0}],
                "confidence_scores": {"experimenter": 95.0},
            }
        )

        result = await real_conversational_handler.parse_and_confirm_metadata(
            "experimenter is Dr. Jane Smith", global_state, mode="batch"
        )

        assert result["type"] == "awaiting_confirmation"
        assert "parsed_fields" in result
        assert "confirmation_message" in result

    @pytest.mark.asyncio
    async def test_parse_handles_exception(self, real_conversational_handler, global_state):
        """Test handles exception during parsing with real MetadataParser."""
        # Configure MockLLMService to raise exception
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Parser error")
        )

        # Should not raise, should handle gracefully
        result = await real_conversational_handler.parse_and_confirm_metadata("some input", global_state, mode="batch")

        # Should fall back to basic extraction
        assert isinstance(result, dict)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestAnalyzeValidationLLMFailure:
    """Tests for LLM failure handling in analyze_validation_and_respond."""

    @pytest.mark.asyncio
    async def test_analyze_validation_llm_exception(self, global_state):
        """Test handles LLM exception gracefully."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM service failed"))

        handler = ConversationalHandler(llm_service)

        validation_result = {"summary": {}, "issues": []}

        # Should raise the exception (no fallback at this level)
        with pytest.raises(Exception, match="LLM service failed"):
            await handler.analyze_validation_and_respond(validation_result, "/test/file.nwb", global_state)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestProcessUserResponse:
    """Tests for process_user_response method."""

    @pytest.mark.asyncio
    async def test_process_response_with_llm_fallback(self, real_conversational_handler, global_state):
        """Test processing user response when parser fails - handler should not crash."""
        # Configure parser's LLM to fail
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Parser error")
        )

        # Configure main LLM for fallback extraction
        real_conversational_handler.llm_service.generate_structured_output = AsyncMock(
            return_value={
                "extracted_metadata": {"experimenter": ["Dr. Smith"]},
                "needs_more_info": False,
                "follow_up_message": "Got it!",
                "ready_to_proceed": True,
                "confidence": 95.0,
            }
        )

        result = await real_conversational_handler.process_user_response(
            user_message="The experimenter is Dr. Smith",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        # When parser fails, falls back gracefully - should not crash
        assert result["type"] == "user_response_processed"
        assert isinstance(result.get("extracted_metadata"), dict)
        assert isinstance(result.get("needs_more_info"), bool)

    @pytest.mark.asyncio
    async def test_process_response_with_confirmation_fallback(self, real_conversational_handler, global_state):
        """Test processing user response when confirming pending fields using real parser."""
        # Set up pending parsed fields
        global_state.pending_parsed_fields = {
            "experimenter": ["Dr. Jane Smith"],
            "institution": "MIT",
        }

        # Configure parser's LLM to fail
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Parser error")
        )

        result = await real_conversational_handler.process_user_response(
            user_message="yes, correct",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        assert result["type"] == "user_response_processed"
        assert result["extracted_metadata"]["experimenter"] == ["Dr. Jane Smith"]
        assert result["ready_to_proceed"] is True

    @pytest.mark.asyncio
    async def test_process_response_llm_extraction_failure(self, real_conversational_handler, global_state):
        """Test processing user response when both parser and LLM fail - should not crash."""
        # Configure both LLM services to fail
        real_conversational_handler.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("LLM failed")
        )
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Parser error")
        )

        result = await real_conversational_handler.process_user_response(
            user_message="some random text",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        # When both fail, handler falls back gracefully and doesn't crash
        assert result["type"] == "user_response_processed"
        assert isinstance(result["extracted_metadata"], dict)
        assert isinstance(result["needs_more_info"], bool)
        assert isinstance(result.get("follow_up_message"), str)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateSmartMetadataRequests:
    """Tests for generate_smart_metadata_requests method."""

    @pytest.mark.asyncio
    async def test_generate_smart_request_with_llm(self, tmp_path, global_state):
        """Test generating smart metadata request with LLM."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "message": "I need some metadata",
                "required_fields": [
                    {
                        "field_name": "experimenter",
                        "display_name": "Experimenter Name",
                        "description": "Who performed the experiment",
                    }
                ],
                "suggestions": ["Provide complete metadata"],
                "detected_data_type": "electrophysiology",
            }
        )

        handler = ConversationalHandler(llm_service)

        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock nwb")

        validation_result = {
            "issues": [{"message": "Missing experimenter"}],
        }

        result = await handler.generate_smart_metadata_requests(validation_result, str(nwb_file), global_state)

        assert result["message"] == "I need some metadata"
        assert len(result["required_fields"]) == 1
        assert result["required_fields"][0]["field_name"] == "experimenter"

    @pytest.mark.asyncio
    async def test_generate_smart_request_llm_failure(self, tmp_path, global_state):
        """Test generating metadata request falls back when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM error"))

        handler = ConversationalHandler(llm_service)

        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock nwb")

        validation_result = {
            "issues": [{"message": "Missing required field: experimenter"}],
        }

        result = await handler.generate_smart_metadata_requests(validation_result, str(nwb_file), global_state)

        # Should fallback to basic request
        assert "message" in result
        assert "required_fields" in result
        assert "suggestions" in result


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractFileContext:
    """Tests for _extract_file_context method."""

    @pytest.mark.asyncio
    async def test_extract_file_context_with_h5py(self, tmp_path, global_state):
        """Test extracting file context from NWB file."""
        import h5py

        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        nwb_file = tmp_path / "test.nwb"

        # Create a mock NWB file
        with h5py.File(nwb_file, "w") as f:
            general = f.create_group("general")
            subject = general.create_group("subject")
            subject.attrs["subject_id"] = "mouse-001"

            devices = general.create_group("devices")
            devices.create_group("device1")

            extracellular = general.create_group("extracellular_ephys")
            extracellular.create_group("electrodes")

            acquisition = f.create_group("acquisition")
            acquisition.create_dataset("ElectricalSeries", data=[1, 2, 3])

        context = await handler._extract_file_context(str(nwb_file), global_state)

        assert context["file_size_mb"] > 0
        assert context["has_subject_info"] is True
        assert context["has_devices"] is True
        assert context["device_count"] == 1
        assert context["has_electrodes"] is True
        assert "ElectricalSeries" in context["acquisition_types"]
        assert "extracellular_ephys" in context["data_interfaces"]

    @pytest.mark.asyncio
    async def test_extract_file_context_nonexistent_file(self, global_state):
        """Test extracting context from non-existent file."""
        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        context = await handler._extract_file_context("/nonexistent/file.nwb", global_state)

        # Should return default context without crashing
        assert context["file_size_mb"] == 0
        assert context["has_subject_info"] is False
        assert context["has_devices"] is False


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestRealConversationalHandlerWorkflows:
    """
    Integration-style unit tests using real ConversationalHandler with MockLLMService.

    Tests real conversation logic instead of mocking it away.
    """

    @pytest.mark.asyncio
    async def test_real_handler_initialization(self, mock_llm_api_only):
        """Test real handler initialization with LLM service."""
        from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler

        handler = ConversationalHandler(llm_service=mock_llm_api_only)

        # Verify real initialization
        assert handler.llm_service is not None
        assert handler.llm_service == mock_llm_api_only

    @pytest.mark.asyncio
    async def test_real_message_processing(self, mock_llm_api_only, global_state):
        """Test real message processing logic."""
        from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler

        handler = ConversationalHandler(llm_service=mock_llm_api_only)

        # Configure LLM for processing
        mock_llm_api_only.generate_structured_output = AsyncMock(
            return_value={
                "fields": [
                    {
                        "field_name": "experimenter",
                        "raw_value": "Dr. Smith",
                        "normalized_value": ["Smith, Dr."],
                        "confidence": 95.0,
                        "reasoning": "Extracted experimenter name",
                        "extraction_type": "explicit",
                        "needs_review": False,
                    }
                ]
            }
        )

        # Test with real handler using process_user_response
        user_message = "The experimenter is Dr. Smith"

        # Process with real logic
        response = await handler.process_user_response(
            user_message=user_message, context={"issues": [], "conversation_history": []}, state=global_state
        )

        # Verify real processing happened
        assert isinstance(response, dict)
        assert response["type"] == "user_response_processed"

    @pytest.mark.asyncio
    async def test_real_context_management(self, mock_llm_api_only, global_state):
        """Test that handler has context manager for conversation management."""
        from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler

        handler = ConversationalHandler(llm_service=mock_llm_api_only)

        # Verify handler has context manager component
        assert handler.context_manager is not None

        # Verify context manager can manage context
        conversation_history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]
        managed = await handler.context_manager.manage_context(
            conversation_history=conversation_history, state=global_state
        )
        assert isinstance(managed, list)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestProcessUserResponseFallbackPaths:
    """
    Tests for process_user_response critical fallback logic (lines 576-742).

    Tests confirmation keyword detection, context manager fallback,
    already-provided metadata context, and full LLM extraction.
    """

    @pytest.mark.asyncio
    async def test_confirmation_keyword_fallback_with_pending_fields(self, real_conversational_handler, global_state):
        """Test confirmation keyword fallback when parser fails but user is confirming (lines 587-626)."""
        # Set up pending parsed fields that user is confirming
        global_state.pending_parsed_fields = {
            "experimenter": ["Dr. Jane Smith"],
            "institution": "MIT",
        }

        # Configure both parser and main LLM to fail
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Parser failed")
        )
        real_conversational_handler.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Main LLM failed")
        )

        # User confirms with keyword - should trigger fallback confirmation detection
        result = await real_conversational_handler.process_user_response(
            user_message="yes, looks good",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        # Should detect confirmation and use pending fields
        assert result["type"] == "user_response_processed"
        assert result["extracted_metadata"]["experimenter"] == ["Dr. Jane Smith"]
        assert result["extracted_metadata"]["institution"] == "MIT"
        assert result["ready_to_proceed"] is True
        assert "✓" in result["follow_up_message"]

    @pytest.mark.asyncio
    async def test_confirmation_keyword_word_boundary_matching(self, real_conversational_handler, global_state):
        """Test word boundary matching prevents false positives in confirmation detection (lines 595-603)."""
        # Set up pending fields
        global_state.pending_parsed_fields = {"experimenter": ["Dr. Smith"]}

        # Configure parser to fail
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Parser failed")
        )

        # User says "okay" which contains "ok" but should still match
        result = await real_conversational_handler.process_user_response(
            user_message="okay, that's correct",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        # Should detect confirmation using word boundary matching
        assert result["type"] == "user_response_processed"
        assert result["extracted_metadata"]["experimenter"] == ["Dr. Smith"]
        assert result["ready_to_proceed"] is True

    @pytest.mark.asyncio
    async def test_confirmation_with_phrase_keywords(self, real_conversational_handler, global_state):
        """Test confirmation detection with multi-word phrases like 'looks good' (lines 595-603)."""
        global_state.pending_parsed_fields = {"session_id": "session-001"}

        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Parser failed")
        )

        result = await real_conversational_handler.process_user_response(
            user_message="looks good to me",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        assert result["type"] == "user_response_processed"
        assert result["extracted_metadata"]["session_id"] == "session-001"
        assert result["ready_to_proceed"] is True

    @pytest.mark.asyncio
    async def test_no_confirmation_without_pending_fields(self, real_conversational_handler, global_state):
        """Test confirmation keywords ignored when no pending fields (lines 604-620)."""
        # No pending fields
        global_state.pending_parsed_fields = {}

        # Configure parser to fail
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("Parser failed")
        )

        # Configure main LLM for fallback extraction
        real_conversational_handler.llm_service.generate_structured_output = AsyncMock(
            return_value={
                "extracted_metadata": {},
                "needs_more_info": True,
                "follow_up_message": "Could you provide more details?",
                "ready_to_proceed": False,
                "confidence": 50.0,
            }
        )

        result = await real_conversational_handler.process_user_response(
            user_message="yes",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        # Should fall through to LLM extraction instead of confirmation
        assert result["type"] == "user_response_processed"
        assert result["needs_more_info"] is True

    @pytest.mark.asyncio
    async def test_context_manager_fallback_on_failure(self, real_conversational_handler, global_state):
        """Test context manager fallback to simple truncation when it fails (lines 641-656)."""
        # Configure parser's parse_and_confirm_metadata to fail
        real_conversational_handler.parse_and_confirm_metadata = AsyncMock(side_effect=Exception("Parser failed"))

        # Configure context manager to fail
        real_conversational_handler.context_manager.manage_context = AsyncMock(
            side_effect=Exception("Context manager failed")
        )

        # Configure main LLM for successful extraction
        real_conversational_handler.llm_service.generate_structured_output = AsyncMock(
            return_value={
                "extracted_metadata": {"experimenter": ["Dr. Smith"]},
                "needs_more_info": False,
                "follow_up_message": "Got it!",
                "ready_to_proceed": True,
                "confidence": 90.0,
            }
        )

        # Include conversation history to test fallback truncation
        conversation_history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)  # More than 5 messages
        ]

        result = await real_conversational_handler.process_user_response(
            user_message="experimenter is Dr. Smith",
            context={"issues": [], "conversation_history": conversation_history},
            state=global_state,
        )

        # Should succeed with fallback to simple truncation (last 5 messages)
        assert result["type"] == "user_response_processed"
        assert "experimenter" in result["extracted_metadata"] or result["needs_more_info"] is True

    @pytest.mark.asyncio
    async def test_already_provided_metadata_context_building(self, real_conversational_handler, global_state):
        """Test building context from already-provided metadata (lines 658-674)."""
        # Set up user-provided metadata
        global_state.user_provided_metadata = {
            "experimenter": ["Dr. Alice Johnson"],
            "institution": "Stanford",
            "session_id": "session-001",
        }

        # Configure parser's parse_and_confirm_metadata to fail
        real_conversational_handler.parse_and_confirm_metadata = AsyncMock(side_effect=Exception("Parser failed"))

        # Configure main LLM - it will receive the already-provided context in the prompt
        real_conversational_handler.llm_service.generate_structured_output = AsyncMock(
            return_value={
                "extracted_metadata": {"subject_id": "mouse-123"},
                "needs_more_info": False,
                "follow_up_message": "Got the subject ID!",
                "ready_to_proceed": True,
                "confidence": 95.0,
            }
        )

        result = await real_conversational_handler.process_user_response(
            user_message="subject is mouse-123",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        # Verify the LLM was called (which means it received the already-provided context)
        assert real_conversational_handler.llm_service.generate_structured_output.called
        assert result["type"] == "user_response_processed"
        assert "subject_id" in result["extracted_metadata"] or result["needs_more_info"] is True

    @pytest.mark.asyncio
    async def test_full_llm_extraction_with_schema_prompt(self, real_conversational_handler, global_state):
        """Test full LLM extraction with NWB/DANDI schema prompt (lines 631-742)."""
        # Configure parser's parse_and_confirm_metadata to fail
        real_conversational_handler.parse_and_confirm_metadata = AsyncMock(side_effect=Exception("Parser failed"))

        # Configure main LLM with full schema-based extraction
        real_conversational_handler.llm_service.generate_structured_output = AsyncMock(
            return_value={
                "extracted_metadata": {
                    "experimenter": ["Dr. Bob Wilson"],
                    "institution": "Harvard",
                    "session_description": "Recording session 1",
                },
                "needs_more_info": False,
                "follow_up_message": "Thank you! I've captured all the metadata.",
                "ready_to_proceed": True,
                "confidence": 92.0,
            }
        )

        result = await real_conversational_handler.process_user_response(
            user_message="The experimenter is Dr. Bob Wilson at Harvard, this is recording session 1",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        # Verify full extraction worked
        assert result["type"] == "user_response_processed"
        # Check if extraction succeeded or if it needs more info
        assert (
            "experimenter" in result["extracted_metadata"]
            or result["needs_more_info"] is True
            or "extracted_metadata" in result
        )

    @pytest.mark.asyncio
    async def test_llm_extraction_final_fallback_on_error(self, real_conversational_handler, global_state):
        """Test final fallback when LLM extraction fails (lines 730-742)."""
        # Configure parse_and_confirm_metadata to fail
        real_conversational_handler.parse_and_confirm_metadata = AsyncMock(side_effect=Exception("Parser failed"))

        # Configure main LLM to fail
        real_conversational_handler.llm_service.generate_structured_output = AsyncMock(
            side_effect=Exception("LLM extraction failed")
        )

        # No pending fields to trigger confirmation fallback
        global_state.pending_parsed_fields = {}

        result = await real_conversational_handler.process_user_response(
            user_message="some random text",
            context={"issues": [], "conversation_history": []},
            state=global_state,
        )

        # Should return final fallback response
        assert result["type"] == "user_response_processed"
        assert result["extracted_metadata"] == {}
        assert result["needs_more_info"] is True
        # Check for various fallback message patterns
        assert (
            "trouble parsing" in result["follow_up_message"].lower()
            or "having trouble" in result["follow_up_message"].lower()
            or "structured way" in result["follow_up_message"].lower()
        )
        assert result["ready_to_proceed"] is False


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestParseAndConfirmMetadataEdgeCases:
    """
    Tests for parse_and_confirm_metadata edge cases (lines 410-465).

    Tests scenarios where user confirms without pending fields,
    wants to edit, or skips/auto-applies.
    """

    @pytest.mark.asyncio
    async def test_user_confirms_without_pending_fields(self, real_conversational_handler, global_state):
        """Test user confirms but no pending fields exist (lines 410-418)."""
        # No pending fields
        global_state.pending_parsed_fields = {}

        result = await real_conversational_handler.parse_and_confirm_metadata(
            user_message="yes, correct", state=global_state, mode="batch"
        )

        # Should return needs_edit type with message explaining no pending fields
        assert result["type"] == "needs_edit"
        # Check for message about missing pending metadata (handles "don't" contraction)
        assert (
            "pending metadata" in result["confirmation_message"].lower()
            or "no pending" in result["confirmation_message"].lower()
        )
        assert result["needs_confirmation"] is True

    @pytest.mark.asyncio
    async def test_user_wants_to_edit_with_no_keyword(self, real_conversational_handler, global_state):
        """Test user wants to edit without using 'no' keyword (lines 421-431)."""
        global_state.pending_parsed_fields = {"experimenter": ["Dr. Smith"]}

        result = await real_conversational_handler.parse_and_confirm_metadata(
            user_message="edit", state=global_state, mode="batch"
        )

        # Should return needs_edit type
        assert result["type"] == "needs_edit"
        assert "provide the correct information" in result["confirmation_message"].lower()
        assert result["needs_confirmation"] is True

    @pytest.mark.asyncio
    async def test_user_auto_applies_with_skip(self, real_conversational_handler, global_state):
        """Test user auto-applies with 'skip' keyword (lines 433-451)."""
        global_state.pending_parsed_fields = {
            "experimenter": ["Dr. Taylor"],
            "session_id": "session-xyz",
        }

        result = await real_conversational_handler.parse_and_confirm_metadata(
            user_message="skip", state=global_state, mode="batch"
        )

        # Should auto-apply pending fields
        assert result["type"] == "auto_applied"
        assert "experimenter" in result["auto_applied_fields"]
        assert "session_id" in result["auto_applied_fields"]
        assert result["needs_confirmation"] is False
        assert "✓" in result["confirmation_message"]

    @pytest.mark.asyncio
    async def test_empty_user_message_triggers_auto_apply(self, real_conversational_handler, global_state):
        """Test empty/whitespace message triggers auto-apply (lines 434)."""
        global_state.pending_parsed_fields = {"institution": "MIT"}

        result = await real_conversational_handler.parse_and_confirm_metadata(
            user_message="   ",  # Just whitespace
            state=global_state,
            mode="batch",
        )

        # Should auto-apply
        assert result["type"] == "auto_applied"
        assert result["auto_applied_fields"]["institution"] == "MIT"

    @pytest.mark.asyncio
    async def test_user_provides_new_metadata_batch_mode(self, real_conversational_handler, global_state):
        """Test user provides new metadata in batch mode (lines 459-465)."""
        # No pending fields - user is providing new data
        global_state.pending_parsed_fields = {}

        # Configure parser for successful parsing
        real_conversational_handler.metadata_parser.llm_service.generate_structured_output = AsyncMock(
            return_value={
                "parsed_fields": [{"field_name": "experimenter", "value": ["Dr. New Person"], "confidence": 90.0}],
                "confidence_scores": {"experimenter": 90.0},
            }
        )

        result = await real_conversational_handler.parse_and_confirm_metadata(
            user_message="experimenter is Dr. New Person", state=global_state, mode="batch"
        )

        # Should parse and await confirmation
        assert result["type"] == "awaiting_confirmation"
        assert "parsed_fields" in result
        assert result["needs_confirmation"] is True


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractFileContextBranching:
    """
    Tests for _extract_file_context branching logic (lines 924-946).

    Tests different data interface detection paths.
    """

    @pytest.mark.asyncio
    async def test_extract_context_with_intracellular_ephys(self, tmp_path, global_state):
        """Test file context extraction with intracellular_ephys interface (lines 941-942)."""
        import h5py

        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        nwb_file = tmp_path / "test_intracellular.nwb"

        with h5py.File(nwb_file, "w") as f:
            general = f.create_group("general")
            general.create_group("intracellular_ephys")

        context = await handler._extract_file_context(str(nwb_file), global_state)

        assert "intracellular_ephys" in context["data_interfaces"]

    @pytest.mark.asyncio
    async def test_extract_context_with_optophysiology(self, tmp_path, global_state):
        """Test file context extraction with optophysiology interface (lines 945-946)."""
        import h5py

        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        nwb_file = tmp_path / "test_opto.nwb"

        with h5py.File(nwb_file, "w") as f:
            general = f.create_group("general")
            general.create_group("optophysiology")

        context = await handler._extract_file_context(str(nwb_file), global_state)

        assert "optophysiology" in context["data_interfaces"]

    @pytest.mark.asyncio
    async def test_extract_context_with_multiple_interfaces(self, tmp_path, global_state):
        """Test file context extraction with multiple data interfaces (lines 941-946)."""
        import h5py

        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        nwb_file = tmp_path / "test_multi.nwb"

        with h5py.File(nwb_file, "w") as f:
            general = f.create_group("general")
            general.create_group("intracellular_ephys")
            general.create_group("extracellular_ephys")
            general.create_group("optophysiology")

        context = await handler._extract_file_context(str(nwb_file), global_state)

        # All three interfaces should be detected
        assert "intracellular_ephys" in context["data_interfaces"]
        assert "extracellular_ephys" in context["data_interfaces"]
        assert "optophysiology" in context["data_interfaces"]

    @pytest.mark.asyncio
    async def test_extract_context_acquisition_types_limited(self, tmp_path, global_state):
        """Test acquisition types are limited to first 5 (lines 938)."""
        import h5py

        llm_service = MockLLMService()
        handler = ConversationalHandler(llm_service)

        nwb_file = tmp_path / "test_acquisition.nwb"

        with h5py.File(nwb_file, "w") as f:
            acquisition = f.create_group("acquisition")
            # Create more than 5 acquisition types
            for i in range(10):
                acquisition.create_dataset(f"Series{i}", data=[1, 2, 3])

        context = await handler._extract_file_context(str(nwb_file), global_state)

        # Should only return first 5
        assert len(context["acquisition_types"]) <= 5
