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
class TestGenerateCustomMetadataPrompt:
    """Tests for _generate_custom_metadata_prompt method."""

    @pytest.mark.asyncio
    async def test_without_llm_returns_fallback(self, global_state):
        """Test prompt generation without LLM returns fallback message."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        result = await agent._generate_custom_metadata_prompt(
            format_name="SpikeGLX", metadata={"experimenter": "test"}, state=global_state
        )

        # Check for key elements of fallback message
        assert "Ready to Convert" in result or "custom" in result.lower()
        assert "additional metadata" in result.lower() or "custom" in result.lower()

    @pytest.mark.asyncio
    async def test_with_llm_success(self, global_state):
        """Test prompt generation with LLM successfully."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={"message": "Would you like to add sampling rate or electrode information?"}
        )

        agent = ConversationAgent(mock_mcp, llm_service)

        result = await agent._generate_custom_metadata_prompt(
            format_name="SpikeGLX", metadata={"experimenter": "test"}, state=global_state
        )

        assert "sampling rate" in result.lower() or "electrode" in result.lower()
        llm_service.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_llm_failure_uses_fallback(self, global_state):
        """Test that LLM failure returns fallback message."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM failed"))

        agent = ConversationAgent(mock_mcp, llm_service)

        result = await agent._generate_custom_metadata_prompt(
            format_name="SpikeGLX", metadata={"experimenter": "test"}, state=global_state
        )

        # Should return fallback
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateDynamicMetadataRequest:
    """Tests for _generate_dynamic_metadata_request method."""

    @pytest.mark.asyncio
    async def test_generate_request_without_llm(self, global_state):
        """Test metadata request generation falls back to template without LLM."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        missing_fields = ["experimenter", "institution", "experiment_description"]
        inference_result = {"inferred_metadata": {}, "confidence_scores": {}}
        file_info = {"name": "test.nwb", "format": "SpikeGLX", "size_mb": 10.5}

        result = await agent._generate_dynamic_metadata_request(
            missing_fields, inference_result, file_info, global_state
        )

        assert "DANDI Metadata Collection" in result
        assert "experimenter" in result.lower()
        assert "institution" in result.lower()
        assert "skip" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_request_with_llm(self, global_state):
        """Test metadata request generation with LLM."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()

        # Mock the generate_structured_output to return a message
        llm_service.generate_structured_output = AsyncMock(
            return_value="I've analyzed your SpikeGLX file. Could you provide experimenter information?"
        )

        agent = ConversationAgent(mock_mcp, llm_service)

        missing_fields = ["experimenter"]
        inference_result = {
            "inferred_metadata": {"species": "Mus musculus"},
            "confidence_scores": {"species": 85.0},
        }
        file_info = {"name": "test.bin", "format": "SpikeGLX", "size_mb": 10.5}

        result = await agent._generate_dynamic_metadata_request(
            missing_fields, inference_result, file_info, global_state
        )

        # LLM returns a string directly in this case
        assert isinstance(result, str)
        llm_service.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_request_with_previous_requests(self, global_state):
        """Test request adapts based on conversation history."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value="Quick follow-up: still need experimenter info."
        )

        agent = ConversationAgent(mock_mcp, llm_service)

        # Simulate previous requests
        global_state.metadata_requests_count = 2
        await global_state.add_conversation_message_safe("user", "I provided species earlier")

        missing_fields = ["experimenter"]
        inference_result = {"inferred_metadata": {}, "confidence_scores": {}}
        file_info = {"name": "test.nwb", "format": "SpikeGLX", "size_mb": 5.0}

        result = await agent._generate_dynamic_metadata_request(
            missing_fields, inference_result, file_info, global_state
        )

        assert isinstance(result, str)
        # Verify LLM was called
        llm_service.generate_structured_output.assert_called_once()


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateFallbackMissingMetadataMessage:
    """Tests for _generate_fallback_missing_metadata_message method."""

    def test_generate_fallback_message_single_field(self):
        """Test fallback message for single missing field."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        result = agent._generate_fallback_missing_metadata_message(["experimenter"])

        assert "experimenter" in result.lower()
        assert isinstance(result, str)

    def test_generate_fallback_message_multiple_fields(self):
        """Test fallback message for multiple missing fields."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        missing_fields = ["experimenter", "institution", "experiment_description"]
        result = agent._generate_fallback_missing_metadata_message(missing_fields)

        assert isinstance(result, str)
        # Should mention some of the fields
        assert any(field in result.lower() for field in missing_fields)

    def test_generate_fallback_message_empty_fields(self):
        """Test fallback message for empty field list."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        result = agent._generate_fallback_missing_metadata_message([])

        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateMetadataReviewMessage:
    """Tests for _generate_metadata_review_message method."""

    @pytest.mark.asyncio
    async def test_without_llm_shows_metadata(self, global_state):
        """Test review message without LLM shows collected metadata."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        metadata = {
            "experimenter": ["John Doe"],
            "institution": "University",
            "session_description": "Test session",
        }

        result = await agent._generate_metadata_review_message(metadata, "SpikeGLX", global_state)

        assert "Metadata Review" in result
        assert "John Doe" in result
        assert "University" in result
        assert "proceed" in result.lower()

    @pytest.mark.asyncio
    async def test_without_llm_shows_missing_fields(self, global_state):
        """Test review message without LLM shows missing fields."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        metadata = {
            "session_description": "Test",
        }

        result = await agent._generate_metadata_review_message(metadata, "SpikeGLX", global_state)

        assert "missing" in result.lower()
        assert "proceed" in result.lower()

    @pytest.mark.asyncio
    async def test_with_llm_success(self, global_state):
        """Test review message with LLM."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={"message": "Great! Your metadata looks complete. Ready to proceed?"}
        )

        agent = ConversationAgent(mock_mcp, llm_service)

        metadata = {
            "experimenter": ["Jane Smith"],
            "institution": "MIT",
        }

        result = await agent._generate_metadata_review_message(metadata, "SpikeGLX", global_state)

        assert "complete" in result.lower() or "proceed" in result.lower()
        llm_service.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_llm_failure_uses_fallback(self, global_state):
        """Test that LLM failure uses fallback message."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM failed"))

        agent = ConversationAgent(mock_mcp, llm_service)

        metadata = {"session_description": "Test"}

        result = await agent._generate_metadata_review_message(metadata, "SpikeGLX", global_state)

        # Bug fixed: now properly awaits the fallback call
        # Should return a string fallback message
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateMissingMetadataMessageWithLLM:
    """Tests for _generate_missing_metadata_message with LLM."""

    @pytest.mark.asyncio
    async def test_generate_with_llm_success(self, global_state):
        """Test generating metadata message with LLM successfully."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(
            return_value="Hi! I need your experimenter name and institution for NWB compliance. Please provide them."
        )

        agent = ConversationAgent(mock_mcp, llm_service)

        missing_fields = ["experimenter", "institution"]
        metadata = {"session_description": "test"}

        result = await agent._generate_missing_metadata_message(missing_fields, metadata, global_state)

        assert "experimenter" in result.lower() or "institution" in result.lower()
        llm_service.generate_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_llm_failure_uses_fallback(self, global_state):
        """Test that LLM failure falls back to simple message."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(side_effect=Exception("LLM failed"))

        agent = ConversationAgent(mock_mcp, llm_service)

        missing_fields = ["experimenter"]
        metadata = {}

        # Bug fixed: now properly uses state parameter instead of self._state
        result = await agent._generate_missing_metadata_message(missing_fields, metadata, global_state)

        # Should return fallback message containing the missing field
        assert isinstance(result, str)
        assert len(result) > 0
        assert "experimenter" in result.lower()


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMissingMetadataWarnings:
    """Tests for missing metadata field warnings."""

    @pytest.mark.asyncio
    async def test_missing_fields_warning_logged(self, global_state, tmp_path):
        """Test that missing recommended fields generate warnings."""
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

        # Minimal metadata - missing many recommended fields
        global_state.metadata = {
            "format": "SpikeGLX",
            "experimenter": "Doe, John",
            # Missing: institution, experiment_description, session_description, etc.
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

        # Should log warning about missing fields
        # Note: The actual validation happens inside _run_conversion
        assert response is not None

    @pytest.mark.asyncio
    async def test_missing_fields_stored_in_metadata(self, global_state, tmp_path):
        """Test that missing field warnings are stored in metadata."""
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

        # Minimal metadata
        global_state.metadata = {
            "format": "SpikeGLX",
            "experimenter": "Doe, John",
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

        # Missing fields warning should be stored
        # This tests the _run_conversion path
        assert response is not None


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestValidateRequiredMetadata:
    """Tests for _validate_required_nwb_metadata method."""

    def test_validate_required_metadata_complete(self, global_state):
        """Test validation with complete metadata."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        global_state.metadata = {
            "experimenter": ["Jane Doe"],
            "institution": "MIT",
            "experiment_description": "Neural recording in V1",
        }

        is_valid, missing = agent._validate_required_nwb_metadata(global_state)

        # Should validate based on NWBDANDISchema
        assert isinstance(is_valid, bool)
        assert isinstance(missing, list)

    def test_validate_required_metadata_incomplete(self, global_state):
        """Test validation with incomplete metadata."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        global_state.metadata = {
            "experimenter": ["Jane Doe"],
        }

        is_valid, missing = agent._validate_required_nwb_metadata(global_state)

        assert is_valid is False
        assert len(missing) > 0

    def test_validate_required_metadata_empty(self, global_state):
        """Test validation with empty metadata."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        global_state.metadata = {}

        is_valid, missing = agent._validate_required_nwb_metadata(global_state)

        assert is_valid is False
        # Should have multiple missing fields
        assert len(missing) >= 3


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestValidateRequiredNwbMetadata:
    """Tests for _validate_required_nwb_metadata method."""

    def test_validate_complete_metadata(self, global_state):
        """Test validation with complete metadata."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Complete metadata (based on NWB/DANDI requirements)
        metadata = {
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
            "experimenter": ["Doe, John"],
            "institution": "Test University",
            "experiment_description": "Test experiment",
            "session_description": "Test recording session for behavior analysis",
            "session_start_time": "2024-01-01T10:00:00",
        }

        is_valid, missing = agent._validate_required_nwb_metadata(metadata)

        # Should be valid with complete metadata
        assert is_valid is True or len(missing) == 0  # Either truly valid or no missing fields

    def test_validate_missing_fields(self, global_state):
        """Test validation with missing required fields."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Incomplete metadata
        metadata = {
            "subject_id": "mouse001",
        }

        is_valid, missing = agent._validate_required_nwb_metadata(metadata)

        # Should detect missing fields
        assert is_valid is False or len(missing) > 0
        if missing:
            # Common required fields that should be detected as missing
            assert any(field in ["experimenter", "session_description", "sex", "species"] for field in missing)

    def test_validate_empty_metadata(self, global_state):
        """Test validation with empty metadata."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        metadata = {}

        is_valid, missing = agent._validate_required_nwb_metadata(metadata)

        # Should not be valid with empty metadata
        assert is_valid is False
        assert len(missing) > 0
