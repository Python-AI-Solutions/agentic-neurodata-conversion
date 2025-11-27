"""
Unit tests for ConversationAgent.

Tests initialization, provenance tracking, and core utility methods.
"""

from unittest.mock import Mock

import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.models import (
    MetadataProvenance,
)
from agentic_neurodata_conversion.services.llm_service import MockLLMService


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestMetadataProvenanceTracking:
    """Tests for metadata provenance tracking."""

    def test_track_metadata_provenance(self, global_state):
        """Test tracking metadata provenance."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        agent._track_metadata_provenance(
            global_state,
            field_name="species",
            value="Mus musculus",
            provenance_type=MetadataProvenance.USER_SPECIFIED,
            confidence=100.0,
            source="User form input",
        )

        assert "species" in global_state.metadata_provenance
        assert global_state.metadata_provenance["species"].value == "Mus musculus"
        assert global_state.metadata_provenance["species"].confidence == 100.0
        assert global_state.metadata_provenance["species"].provenance == MetadataProvenance.USER_SPECIFIED

    def test_track_user_provided_metadata(self, global_state):
        """Test tracking user-provided metadata."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        agent._track_user_provided_metadata(
            global_state,
            field_name="experimenter",
            value=["Jane Doe"],
            raw_input="experimenter: Jane Doe",
        )

        assert "experimenter" in global_state.metadata_provenance
        assert global_state.metadata_provenance["experimenter"].provenance == MetadataProvenance.USER_SPECIFIED
        assert global_state.metadata_provenance["experimenter"].value == ["Jane Doe"]
        assert global_state.metadata_provenance["experimenter"].raw_input == "experimenter: Jane Doe"

    def test_track_ai_parsed_metadata(self, global_state):
        """Test tracking AI-parsed metadata."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        agent._track_ai_parsed_metadata(
            global_state,
            field_name="institution",
            value="MIT",
            confidence=85.0,
            raw_input="We did the experiment at MIT",
        )

        assert "institution" in global_state.metadata_provenance
        assert global_state.metadata_provenance["institution"].provenance == MetadataProvenance.AI_PARSED
        assert global_state.metadata_provenance["institution"].confidence == 85.0
        assert global_state.metadata_provenance["institution"].value == "MIT"

    def test_track_ai_parsed_metadata_low_confidence(self, global_state):
        """Test tracking low-confidence AI-parsed metadata."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        agent._track_ai_parsed_metadata(
            global_state,
            field_name="keywords",
            value=["neuroscience", "mouse"],
            confidence=60.0,
            raw_input="neuroscience study with mouse",
        )

        assert "keywords" in global_state.metadata_provenance
        assert global_state.metadata_provenance["keywords"].confidence == 60.0
        assert global_state.metadata_provenance["keywords"].needs_review is True

    def test_track_auto_corrected_metadata(self, global_state):
        """Test tracking auto-corrected metadata."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        agent._track_auto_corrected_metadata(
            global_state,
            field_name="session_start_time",
            value="2024-01-01T10:00:00",
            source="ISO 8601 format correction",
        )

        assert "session_start_time" in global_state.metadata_provenance
        assert global_state.metadata_provenance["session_start_time"].provenance == MetadataProvenance.AUTO_CORRECTED
        assert global_state.metadata_provenance["session_start_time"].value == "2024-01-01T10:00:00"
