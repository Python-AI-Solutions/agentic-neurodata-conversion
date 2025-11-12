"""
Unit tests for ConversationalHandler.

Tests intelligent LLM-driven conversational interactions for NWB conversion.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from agents.conversational_handler import ConversationalHandler
from models import MetadataRequestPolicy
from services.llm_service import MockLLMService


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
        from agents.conversational_handler import ConversationalHandler

        handler = ConversationalHandler(llm_service=mock_llm_api_only)

        # Verify real initialization
        assert handler.llm_service is not None
        assert handler.llm_service == mock_llm_api_only

    @pytest.mark.asyncio
    async def test_real_message_processing(self, mock_llm_api_only, global_state):
        """Test real message processing logic."""
        from agents.conversational_handler import ConversationalHandler

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
        from agents.conversational_handler import ConversationalHandler

        handler = ConversationalHandler(llm_service=mock_llm_api_only)

        # Verify handler has context manager component
        assert handler.context_manager is not None

        # Verify context manager can manage context
        conversation_history = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]
        managed = await handler.context_manager.manage_context(
            conversation_history=conversation_history, state=global_state
        )
        assert isinstance(managed, list)
