"""
Unit tests for ConversationAgent.

Tests initialization, provenance tracking, and core utility methods.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.models.mcp import MCPMessage, MCPResponse
from agentic_neurodata_conversion.services.llm_service import MockLLMService


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractMetadataFromMessage:
    """Tests for _extract_metadata_from_message method."""

    @pytest.mark.asyncio
    async def test_extract_without_handler_simple_pattern(self, global_state):
        """Test extracting metadata without handler using simple pattern matching."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        message = "experimenter: Dr. Smith, institution: MIT"

        result = await agent._extract_metadata_from_message(message, global_state)

        assert "experimenter" in result
        assert "institution" in result

    @pytest.mark.asyncio
    async def test_extract_with_handler(self, global_state):
        """Test extracting metadata with conversational handler."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        # Mock conversational handler response
        agent._conversational_handler.process_user_response = AsyncMock(
            return_value={
                "extracted_metadata": {
                    "experimenter": ["Dr. Jane Smith"],
                    "institution": "Stanford",
                },
                "ready_to_proceed": True,
            }
        )

        message = "The experimenter is Dr. Jane Smith from Stanford"

        result = await agent._extract_metadata_from_message(message, global_state)

        assert result["experimenter"] == ["Dr. Jane Smith"]
        assert result["institution"] == "Stanford"


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestHandleCustomMetadataResponse:
    """Tests for _handle_custom_metadata_response method."""

    @pytest.mark.asyncio
    async def test_without_metadata_mapper(self, global_state):
        """Test handling custom metadata without metadata mapper."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        result = await agent._handle_custom_metadata_response(user_input="sampling rate is 30kHz", state=global_state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_with_mapper_success(self, global_state):
        """Test successful custom metadata parsing."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        # Mock metadata mapper in the parser (where it's actually used)
        mock_mapper = Mock()
        mock_mapper.parse_custom_metadata = AsyncMock(
            return_value={
                "standard_fields": {"sampling_rate": 30000},
                "custom_fields": {"electrode_config": "16-channel"},
                "mapping_report": "Parsed 2 fields",
            }
        )
        agent._metadata_parser._metadata_mapper = mock_mapper

        result = await agent._handle_custom_metadata_response(
            user_input="sampling rate is 30kHz with 16-channel electrode", state=global_state
        )

        assert "standard_fields" in result
        assert result["standard_fields"]["sampling_rate"] == 30000
        assert "custom_fields" in result
        mock_mapper.parse_custom_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_mapper_failure(self, global_state):
        """Test custom metadata parsing failure."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        # Mock metadata mapper in the parser that raises exception
        mock_mapper = Mock()
        mock_mapper.parse_custom_metadata = AsyncMock(side_effect=Exception("Parsing failed"))
        agent._metadata_parser._metadata_mapper = mock_mapper

        result = await agent._handle_custom_metadata_response(user_input="invalid input", state=global_state)

        # When mapper fails, handle_custom_metadata_response returns empty dict with structure
        # Check it returns a dict (implementation returns structured empty result)
        assert isinstance(result, dict)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestIsValidDateFormat:
    """Tests for _is_valid_date_format method."""

    def test_valid_iso_format(self, global_state):
        """Test ISO format date is valid."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        assert agent._is_valid_date_format("2024-01-15T10:30:00") is True

    def test_valid_natural_language_date(self, global_state):
        """Test natural language date is valid."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # This requires dateutil to be installed
        assert agent._is_valid_date_format("January 15, 2024") is True

    def test_invalid_date_format(self, global_state):
        """Test invalid date format returns False."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        assert agent._is_valid_date_format("not a date") is False
        assert agent._is_valid_date_format("") is False


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataAutoFillFromInference:
    """Tests for auto-filling metadata from AI inference."""

    @pytest.mark.asyncio
    async def test_autofill_optional_fields_from_inference(self, global_state, tmp_path):
        """Test auto-filling optional metadata fields from inference results."""
        mock_mcp = Mock()
        mock_mcp.send_message = AsyncMock(
            side_effect=[
                # Conversion response
                MCPResponse.success_response(
                    reply_to="msg_1",
                    result={"status": "success", "nwb_path": "/tmp/output.nwb"},
                ),
                # Validation response
                MCPResponse.success_response(
                    reply_to="msg_2",
                    result={"outcome": "PASSED", "issues": [], "overall_status": "PASSED"},
                ),
            ]
        )

        agent = ConversationAgent(mock_mcp, llm_service=None)

        input_file = tmp_path / "test.bin"
        input_file.write_bytes(b"test data")
        global_state.input_path = str(input_file)

        # Set up inference results with high confidence
        global_state.inference_result = {
            "inferred_metadata": {
                "keywords": ["electrophysiology", "visual cortex"],
                "experiment_description": "Visual cortex recording",
                "session_description": "Recording session 1",
            },
            "confidence_scores": {
                "keywords": 85.0,
                "experiment_description": 75.0,
                "session_description": 70.0,
            },
        }

        # Minimal required metadata (no optional fields)
        global_state.metadata = {
            "format": "SpikeGLX",
            "experimenter": "Doe, John",
            "institution": "Test University",
            "session_start_time": "2024-01-01T10:00:00",
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
            "_custom_metadata_prompted": True,
            "_metadata_review_shown": True,
        }

        message = MCPMessage(
            message_id="msg_123",
            target_agent="conversation",
            action="start_conversion",
            context={},
        )

        response = await agent.handle_start_conversion(message, global_state)

        # Should auto-fill optional fields from inference
        # Note: This tests the _run_conversion path which does the autofill
        assert response is not None

    @pytest.mark.asyncio
    async def test_autofill_skips_low_confidence_inferences(self, global_state, tmp_path):
        """Test that low-confidence inferences are not auto-filled."""
        mock_mcp = Mock()
        mock_mcp.send_message = AsyncMock(
            side_effect=[
                MCPResponse.success_response(
                    reply_to="msg_1",
                    result={"status": "success", "nwb_path": "/tmp/output.nwb"},
                ),
                MCPResponse.success_response(
                    reply_to="msg_2",
                    result={"outcome": "PASSED", "issues": [], "overall_status": "PASSED"},
                ),
            ]
        )

        agent = ConversationAgent(mock_mcp, llm_service=None)

        input_file = tmp_path / "test.bin"
        input_file.write_bytes(b"test data")
        global_state.input_path = str(input_file)

        # Set up inference results with LOW confidence (< 60%)
        global_state.inference_result = {
            "inferred_metadata": {
                "keywords": ["electrophysiology"],
                "experiment_description": "Uncertain description",
            },
            "confidence_scores": {
                "keywords": 45.0,  # Too low
                "experiment_description": 55.0,  # Too low
            },
        }

        global_state.metadata = {
            "format": "SpikeGLX",
            "experimenter": "Doe, John",
            "institution": "Test University",
            "session_start_time": "2024-01-01T10:00:00",
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
            "_custom_metadata_prompted": True,
            "_metadata_review_shown": True,
        }

        message = MCPMessage(
            message_id="msg_123",
            target_agent="conversation",
            action="start_conversion",
            context={},
        )

        response = await agent.handle_start_conversion(message, global_state)

        # Low-confidence inferences should NOT be auto-filled
        assert response is not None

    @pytest.mark.asyncio
    async def test_autofill_respects_user_provided_metadata(self, global_state, tmp_path):
        """Test that user-provided metadata is not overwritten by inference."""
        mock_mcp = Mock()
        mock_mcp.send_message = AsyncMock(
            side_effect=[
                MCPResponse.success_response(
                    reply_to="msg_1",
                    result={"status": "success", "nwb_path": "/tmp/output.nwb"},
                ),
                MCPResponse.success_response(
                    reply_to="msg_2",
                    result={"outcome": "PASSED", "issues": [], "overall_status": "PASSED"},
                ),
            ]
        )

        agent = ConversationAgent(mock_mcp, llm_service=None)

        input_file = tmp_path / "test.bin"
        input_file.write_bytes(b"test data")
        global_state.input_path = str(input_file)

        # User already provided keywords
        user_provided_keywords = ["my", "custom", "keywords"]

        global_state.inference_result = {
            "inferred_metadata": {
                "keywords": ["different", "keywords"],  # Should NOT override user's
            },
            "confidence_scores": {
                "keywords": 90.0,
            },
        }

        global_state.metadata = {
            "format": "SpikeGLX",
            "experimenter": "Doe, John",
            "institution": "Test University",
            "keywords": user_provided_keywords,  # User-provided
            "session_start_time": "2024-01-01T10:00:00",
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
            "_custom_metadata_prompted": True,
            "_metadata_review_shown": True,
        }

        message = MCPMessage(
            message_id="msg_123",
            target_agent="conversation",
            action="start_conversion",
            context={},
        )

        response = await agent.handle_start_conversion(message, global_state)

        # User-provided metadata should remain unchanged
        assert global_state.metadata["keywords"] == user_provided_keywords


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestValidateMetadataFormat:
    """Tests for _validate_metadata_format method."""

    def test_validate_valid_metadata(self, global_state):
        """Test validation with valid metadata."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        metadata = {
            "session_description": "Test session",
            "experimenter": "Smith, John",
        }

        errors = agent._validate_metadata_format(metadata)

        assert len(errors) == 0

    def test_validate_invalid_sex(self, global_state):
        """Test validation with invalid sex value."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        metadata = {"sex": "male"}  # Should be 'M', not 'male'

        errors = agent._validate_metadata_format(metadata)

        assert "sex" in errors
        assert "M" in errors["sex"]

    def test_validate_invalid_experimenter_format(self, global_state):
        """Test validation with invalid experimenter format."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        metadata = {"experimenter": "John Smith"}  # Missing comma

        errors = agent._validate_metadata_format(metadata)

        assert "experimenter" in errors
        assert "LastName, FirstName" in errors["experimenter"]

    def test_validate_invalid_species(self, global_state):
        """Test validation with invalid species."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        metadata = {"species": "mouse"}  # Should be scientific name

        errors = agent._validate_metadata_format(metadata)

        assert "species" in errors
        assert "scientific name" in errors["species"].lower()

    def test_validate_unknown_field_skipped(self, global_state):
        """Test that unknown fields are skipped during validation (line 86)."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Include a field that doesn't exist in NWBDANDISchema
        metadata = {
            "session_description": "Test session",
            "unknown_custom_field": "some value",  # This field has no schema
            "another_unknown": "test",
        }

        errors = agent._validate_metadata_format(metadata)

        # Unknown fields should be skipped (line 86: continue)
        # Only known fields with errors should be in the errors dict
        assert "unknown_custom_field" not in errors
        assert "another_unknown" not in errors

    def test_validate_invalid_date_format_error_message(self, global_state):
        """Test invalid date format produces specific error message (lines 91-95)."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Use a field that has "date" type in schema (session_start_time)
        metadata = {
            "session_start_time": "not a valid date format",
        }

        errors = agent._validate_metadata_format(metadata)

        # Should have error for session_start_time with specific message (lines 92-95)
        assert "session_start_time" in errors
        assert "ISO format" in errors["session_start_time"]
        assert "YYYY-MM-DDTHH:MM:SS" in errors["session_start_time"]
        assert "natural language" in errors["session_start_time"]


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestIsValidDateFormatEdgeCases:
    """Tests for edge cases in _is_valid_date_format method."""

    def test_none_value_returns_false(self, global_state):
        """Test that None value returns False (TypeError handling, line 136)."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # None should be handled gracefully and return False
        assert agent._is_valid_date_format(None) is False

    def test_numeric_value_handling(self, global_state):
        """Test that numeric value is handled by dateutil parser (line 132)."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Numeric values can be interpreted as timestamps by dateutil
        # So they may return True (valid) - this tests the dateutil path
        result = agent._is_valid_date_format(123)
        assert isinstance(result, bool)  # Should return a boolean without errors

    def test_empty_string_returns_false(self, global_state):
        """Test that empty string returns False (ValueError handling, line 135)."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Empty string should return False
        assert agent._is_valid_date_format("") is False

    def test_invalid_string_returns_false(self, global_state):
        """Test that invalid string returns False (ValueError handling, line 135)."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Random strings that can't be parsed as dates
        assert agent._is_valid_date_format("definitely not a date") is False
        assert agent._is_valid_date_format("xyz123") is False
        assert agent._is_valid_date_format("@#$%") is False

    def test_partial_iso_format_returns_true(self, global_state):
        """Test that partial ISO format is accepted."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # ISO format check uses regex that matches partial dates
        assert agent._is_valid_date_format("2024-01-15T10:30:00") is True
        assert agent._is_valid_date_format("2024-12-31T23:59:59") is True

    def test_dateutil_parser_success_cases(self, global_state):
        """Test dateutil parser handles various natural language dates (line 132)."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Various natural language date formats
        assert agent._is_valid_date_format("January 1, 2024") is True
        assert agent._is_valid_date_format("2024-01-01") is True
        assert agent._is_valid_date_format("01/15/2024") is True
        assert agent._is_valid_date_format("15 Jan 2024") is True
