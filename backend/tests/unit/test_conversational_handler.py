"""
Unit tests for conversational handler.

Tests the conversational AI handler for intelligent validation analysis and metadata requests.
"""
import pytest
import json
from unittest.mock import AsyncMock, Mock
from pathlib import Path
import tempfile

from agents.conversational_handler import ConversationalHandler
from models import GlobalState, ConversionStatus, ValidationStatus, LogLevel
from services.llm_service import MockLLMService


class TestConversationalHandler:
    """Tests for the ConversationalHandler class."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        return MockLLMService()

    @pytest.fixture
    def handler(self, mock_llm_service):
        """Create a conversational handler with mock LLM."""
        return ConversationalHandler(llm_service=mock_llm_service)

    @pytest.fixture
    def state(self):
        """Create a global state for testing."""
        return GlobalState()

    @pytest.fixture
    def validation_result(self):
        """Create a sample validation result."""
        return {
            "overall_status": "FAILED",
            "summary": {
                "total_issues": 5,
                "critical": 0,
                "errors": 2,
                "warnings": 3,
            },
            "issues": [
                {
                    "severity": "ERROR",
                    "message": "Missing experimenter information",
                    "location": "/general",
                    "check_function_name": "check_experimenter_exists",
                },
                {
                    "severity": "ERROR",
                    "message": "Missing experiment_description",
                    "location": "/general",
                    "check_function_name": "check_experiment_description_exists",
                },
                {
                    "severity": "WARNING",
                    "message": "Missing keywords",
                    "location": "/general",
                    "check_function_name": "check_keywords_exist",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_initialization(self, mock_llm_service):
        """Test handler initializes with LLM service."""
        handler = ConversationalHandler(llm_service=mock_llm_service)
        assert handler.llm_service is mock_llm_service

    @pytest.mark.asyncio
    async def test_analyze_validation_basic(self, handler, state, validation_result):
        """Test basic validation analysis."""
        # Mock LLM to return structured response
        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            return {
                "message": "I found some issues with your NWB file that need attention.",
                "needs_user_input": True,
                "suggested_fixes": [
                    {
                        "field": "experimenter",
                        "description": "Name of person who performed experiment",
                        "example": "Jane Doe",
                    }
                ],
                "severity": "medium",
            }

        handler.llm_service.generate_structured_output = mock_generate_structured

        result = await handler.analyze_validation_and_respond(
            validation_result=validation_result,
            nwb_file_path="/tmp/test.nwb",
            state=state,
        )

        assert result["type"] == "conversational"
        assert "message" in result
        assert result["needs_user_input"] is True
        assert isinstance(result["suggested_fixes"], list)

    @pytest.mark.asyncio
    async def test_analyze_validation_with_smart_metadata(self, handler, state, validation_result):
        """Test validation analysis generates smart metadata requests."""
        # Mock both LLM calls
        call_count = 0

        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call: analyze_validation_and_respond
                return {
                    "message": "Need metadata",
                    "needs_user_input": True,
                    "suggested_fixes": [],
                    "severity": "medium",
                }
            else:
                # Second call: generate_smart_metadata_requests
                return {
                    "message": "I noticed you're working with electrophysiology data. Could you provide some metadata?",
                    "required_fields": [
                        {
                            "field_name": "experimenter",
                            "display_name": "Experimenter",
                            "description": "Person who performed the experiment",
                            "why_needed": "Required for DANDI submission",
                            "example": "Jane Doe",
                            "field_type": "text",
                        }
                    ],
                    "suggestions": ["Great data structure!", "Add keywords for searchability"],
                    "detected_data_type": "electrophysiology",
                }

        handler.llm_service.generate_structured_output = mock_generate_structured

        # Create a temporary NWB file for context extraction
        with tempfile.NamedTemporaryFile(suffix=".nwb", delete=False) as f:
            nwb_path = f.name

        try:
            result = await handler.analyze_validation_and_respond(
                validation_result=validation_result,
                nwb_file_path=nwb_path,
                state=state,
            )

            # Should have smart metadata fields
            assert "required_fields" in result
            assert "suggestions" in result
            assert result["detected_data_type"] == "electrophysiology"
            assert len(result["required_fields"]) > 0

        finally:
            Path(nwb_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_analyze_validation_no_user_input_needed(self, handler, state):
        """Test validation analysis when no user input is needed."""
        validation_result = {
            "overall_status": "PASSED_WITH_WARNINGS",
            "summary": {"total_issues": 1},
            "issues": [
                {
                    "severity": "WARNING",
                    "message": "Consider adding more keywords",
                    "location": "/general",
                }
            ],
        }

        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            return {
                "message": "Your file looks good! Just one minor suggestion.",
                "needs_user_input": False,
                "suggested_fixes": [],
                "severity": "low",
            }

        handler.llm_service.generate_structured_output = mock_generate_structured

        result = await handler.analyze_validation_and_respond(
            validation_result=validation_result,
            nwb_file_path="/tmp/test.nwb",
            state=state,
        )

        assert result["needs_user_input"] is False
        assert result["severity"] == "low"

    @pytest.mark.asyncio
    async def test_process_user_response_extracts_metadata(self, handler, state):
        """Test processing user response extracts metadata correctly."""
        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            return {
                "extracted_metadata": {
                    "experimenter": ["Jane Doe", "John Smith"],
                    "institution": "MIT",
                    "keywords": ["electrophysiology", "mouse"],
                },
                "needs_more_info": False,
                "follow_up_message": "Great! I have all the information I need.",
                "ready_to_proceed": True,
            }

        handler.llm_service.generate_structured_output = mock_generate_structured

        user_message = "The experimenters were Jane Doe and John Smith from MIT. This is electrophysiology data from mice."
        context = {
            "validation_result": {},
            "issues": [],
            "conversation_history": [],
        }

        result = await handler.process_user_response(user_message, context, state)

        assert result["type"] == "user_response_processed"
        assert result["ready_to_proceed"] is True
        assert "experimenter" in result["extracted_metadata"]
        assert result["extracted_metadata"]["experimenter"] == ["Jane Doe", "John Smith"]

    @pytest.mark.asyncio
    async def test_process_user_response_needs_more_info(self, handler, state):
        """Test processing user response when more info is needed."""
        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            return {
                "extracted_metadata": {
                    "experimenter": ["Jane Doe"],
                },
                "needs_more_info": True,
                "follow_up_message": "Thanks! Could you also provide the institution name?",
                "ready_to_proceed": False,
            }

        handler.llm_service.generate_structured_output = mock_generate_structured

        result = await handler.process_user_response(
            "Jane Doe did the experiment", {}, state
        )

        assert result["needs_more_info"] is True
        assert result["ready_to_proceed"] is False
        assert "follow_up_message" in result

    @pytest.mark.asyncio
    async def test_process_user_response_with_conversation_history(self, handler, state):
        """Test processing user response with conversation history."""
        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            return {
                "extracted_metadata": {"institution": "Stanford"},
                "needs_more_info": False,
                "ready_to_proceed": True,
            }

        handler.llm_service.generate_structured_output = mock_generate_structured

        context = {
            "conversation_history": [
                {"role": "assistant", "content": "Who performed the experiment?"},
                {"role": "user", "content": "Jane Doe"},
                {"role": "assistant", "content": "What institution?"},
            ],
            "issues": [],
        }

        result = await handler.process_user_response("Stanford", context, state)

        assert result["type"] == "user_response_processed"
        assert "institution" in result["extracted_metadata"]

    @pytest.mark.asyncio
    async def test_process_user_response_error_handling(self, handler, state):
        """Test error handling when processing user response fails."""
        async def mock_failing_generate(*args, **kwargs):
            raise Exception("LLM API Error")

        handler.llm_service.generate_structured_output = mock_failing_generate

        result = await handler.process_user_response("test message", {}, state)

        # Should return fallback response
        assert result["type"] == "user_response_processed"
        assert result["needs_more_info"] is True
        assert result["ready_to_proceed"] is False
        assert "follow_up_message" in result

    @pytest.mark.asyncio
    async def test_format_validation_issues(self, handler):
        """Test validation issue formatting."""
        validation_result = {
            "issues": [
                {
                    "severity": "ERROR",
                    "message": "Missing experimenter",
                    "location": "/general",
                    "check_function_name": "check_experimenter",
                },
                {
                    "severity": "WARNING",
                    "message": "Missing keywords",
                    "location": "/general/keywords",
                    "check_function_name": "check_keywords",
                },
            ]
        }

        formatted = handler._format_validation_issues(validation_result)

        assert isinstance(formatted, str)
        assert "ERROR" in formatted
        assert "Missing experimenter" in formatted
        assert "WARNING" in formatted
        assert "Missing keywords" in formatted

    @pytest.mark.asyncio
    async def test_format_validation_issues_empty(self, handler):
        """Test formatting when no issues exist."""
        validation_result = {"issues": []}

        formatted = handler._format_validation_issues(validation_result)

        assert formatted == "No issues found"

    @pytest.mark.asyncio
    async def test_format_validation_issues_many(self, handler):
        """Test formatting limits to first 20 issues."""
        issues = [
            {
                "severity": f"ERROR_{i}",
                "message": f"Issue {i}",
                "location": f"/path/{i}",
                "check_function_name": f"check_{i}",
            }
            for i in range(30)
        ]
        validation_result = {"issues": issues}

        formatted = handler._format_validation_issues(validation_result)

        # Should include first 20 and mention there are more
        assert "Issue 0" in formatted
        assert "Issue 19" in formatted
        assert "10 more issues" in formatted

    @pytest.mark.asyncio
    async def test_extract_basic_required_fields(self, handler):
        """Test extracting basic required fields from validation issues."""
        validation_result = {
            "issues": [
                {"message": "Missing experimenter information"},
                {"message": "No experiment description provided"},
                {"message": "Institution not specified"},
                {"message": "Keywords are missing"},
            ]
        }

        fields = handler._extract_basic_required_fields(validation_result)

        assert len(fields) == 4
        field_names = [f["field_name"] for f in fields]
        assert "experimenter" in field_names
        assert "experiment_description" in field_names
        assert "institution" in field_names
        assert "keywords" in field_names

        # Check field structure
        for field in fields:
            assert "field_name" in field
            assert "display_name" in field
            assert "description" in field
            assert "field_type" in field
            assert "example" in field

    @pytest.mark.asyncio
    async def test_extract_basic_required_fields_no_duplicates(self, handler):
        """Test that duplicate fields are not added."""
        validation_result = {
            "issues": [
                {"message": "Missing experimenter information"},
                {"message": "Experimenter field is empty"},
                {"message": "No experimenter found"},
            ]
        }

        fields = handler._extract_basic_required_fields(validation_result)

        # Should only have one experimenter field despite 3 mentions
        assert len(fields) == 1
        assert fields[0]["field_name"] == "experimenter"

    @pytest.mark.asyncio
    async def test_generate_smart_metadata_requests_success(self, handler, state, validation_result):
        """Test generating smart metadata requests with LLM."""
        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            return {
                "message": "I see you're working with electrophysiology data. Could you provide experimenter info?",
                "required_fields": [
                    {
                        "field_name": "experimenter",
                        "display_name": "Experimenter",
                        "description": "Person who performed experiment",
                        "why_needed": "Required for DANDI",
                        "inferred_value": "",
                        "example": "Jane Doe",
                        "field_type": "text",
                    }
                ],
                "suggestions": ["Add more keywords", "Include detailed description"],
                "detected_data_type": "electrophysiology",
            }

        handler.llm_service.generate_structured_output = mock_generate_structured

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".nwb", delete=False) as f:
            nwb_path = f.name

        try:
            result = await handler.generate_smart_metadata_requests(
                validation_result=validation_result,
                nwb_file_path=nwb_path,
                state=state,
            )

            assert "message" in result
            assert "required_fields" in result
            assert len(result["required_fields"]) > 0
            assert result["detected_data_type"] == "electrophysiology"

        finally:
            Path(nwb_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_generate_smart_metadata_requests_fallback(self, handler, state, validation_result):
        """Test fallback when LLM fails to generate smart metadata."""
        async def mock_failing_generate(*args, **kwargs):
            raise Exception("LLM error")

        handler.llm_service.generate_structured_output = mock_failing_generate

        result = await handler.generate_smart_metadata_requests(
            validation_result=validation_result,
            nwb_file_path="/nonexistent/file.nwb",
            state=state,
        )

        # Should return fallback response
        assert "message" in result
        assert "required_fields" in result
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_extract_file_context_nonexistent_file(self, handler, state):
        """Test extracting context from non-existent file returns defaults."""
        context = await handler._extract_file_context("/nonexistent/file.nwb", state)

        assert context["file_size_mb"] == 0
        assert context["has_subject_info"] is False
        assert context["has_devices"] is False
        assert context["has_electrodes"] is False

    @pytest.mark.asyncio
    async def test_logs_added_to_state(self, handler, state, validation_result):
        """Test that operations add logs to state."""
        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            return {
                "message": "Test",
                "needs_user_input": False,
                "severity": "low",
            }

        handler.llm_service.generate_structured_output = mock_generate_structured

        initial_log_count = len(state.logs)

        await handler.analyze_validation_and_respond(
            validation_result=validation_result,
            nwb_file_path="/tmp/test.nwb",
            state=state,
        )

        # Should have added logs
        assert len(state.logs) > initial_log_count
        log_messages = [log.message for log in state.logs]
        assert any("Analyzing validation results" in msg for msg in log_messages)
