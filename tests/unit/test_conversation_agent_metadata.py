"""
Unit tests for ConversationAgent metadata extraction (Task 4.3).

Tests the _extract_metadata_from_md_files method which:
- Extracts metadata from README.md files using LLM
- Returns MetadataExtractionResult with all fields
- Handles empty metadata file lists
- Combines content from multiple .md files
- Parses LLM JSON responses
- Handles LLM JSON parsing errors
"""

import json
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.session_context import (
    MetadataExtractionResult,
)


@pytest.fixture
def conversation_agent() -> ConversationAgent:
    """Create ConversationAgent instance for testing."""
    config = AgentConfig(
        agent_name="test-conversation-agent",
        agent_type="conversation",
        agent_port=8001,
        mcp_server_url="http://localhost:3000",
        llm_provider="anthropic",
        llm_api_key="test-key",
        llm_model="claude-3-5-sonnet-20241022",
        temperature=0.7,
        max_tokens=4096,
    )
    return ConversationAgent(config)


@pytest.fixture
def sample_llm_response() -> str:
    """Sample LLM response with extracted metadata."""
    return json.dumps(
        {
            "subject_id": "Test Mouse 001",
            "species": "Mus musculus",
            "age": "P56",
            "sex": "Male",
            "session_start_time": "2024-01-15T12:00:00",
            "experimenter": "Test User",
            "device_name": "Open Ephys Acquisition Board",
            "manufacturer": "Open Ephys",
            "recording_location": "CA1",
            "description": "Test session for validating the multi-agent NWB conversion pipeline.",
            "extraction_confidence": {
                "subject_id": "high",
                "species": "high",
                "age": "high",
                "sex": "high",
                "session_start_time": "high",
                "experimenter": "medium",
                "device_name": "high",
                "manufacturer": "high",
                "recording_location": "high",
                "description": "high",
            },
        }
    )


@pytest.mark.asyncio
async def test_extract_metadata_from_readme_md(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test extract metadata successfully extracts from README.md."""
    # Arrange
    dataset_path = str(test_dataset_path)
    md_files = ["README.md"]

    # Mock LLM call
    with patch.object(
        conversation_agent, "call_llm", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = sample_llm_response

        # Act
        result = await conversation_agent._extract_metadata_from_md_files(
            dataset_path, md_files
        )

        # Assert
        assert isinstance(result, MetadataExtractionResult)
        assert mock_llm.called


@pytest.mark.asyncio
async def test_extract_returns_metadata_extraction_result_with_all_fields(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test extract metadata returns MetadataExtractionResult with all fields populated."""
    # Arrange
    dataset_path = str(test_dataset_path)
    md_files = ["README.md"]

    # Mock LLM call
    with patch.object(
        conversation_agent, "call_llm", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = sample_llm_response

        # Act
        result = await conversation_agent._extract_metadata_from_md_files(
            dataset_path, md_files
        )

        # Assert
        assert result.subject_id == "Test Mouse 001"
        assert result.species == "Mus musculus"
        assert result.age == "P56"
        assert result.sex == "Male"
        assert result.session_start_time == "2024-01-15T12:00:00"
        assert result.experimenter == "Test User"
        assert result.device_name == "Open Ephys Acquisition Board"
        assert result.manufacturer == "Open Ephys"
        assert result.recording_location == "CA1"
        assert result.description is not None
        assert result.extraction_confidence is not None
        assert isinstance(result.extraction_confidence, dict)


@pytest.mark.asyncio
async def test_extract_returns_empty_metadata_when_no_md_files(
    conversation_agent: ConversationAgent,
) -> None:
    """Test extract metadata returns empty result when no .md files provided."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        md_files: list[str] = []

        # Act
        result = await conversation_agent._extract_metadata_from_md_files(
            tmpdir, md_files
        )

        # Assert
        assert isinstance(result, MetadataExtractionResult)
        assert result.subject_id is None
        assert result.species is None
        assert result.llm_extraction_log is None


@pytest.mark.asyncio
async def test_extract_combines_content_from_multiple_md_files(
    conversation_agent: ConversationAgent, sample_llm_response: str
) -> None:
    """Test extract metadata combines content from multiple .md files."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create multiple .md files
        file1 = Path(tmpdir) / "README.md"
        file1.write_text("Subject: Mouse 001\nSpecies: Mus musculus")

        file2 = Path(tmpdir) / "DETAILS.md"
        file2.write_text("Experimenter: Test User\nSession: 2024-01-15")

        md_files = ["README.md", "DETAILS.md"]

        # Mock LLM call to verify combined content is passed
        with patch.object(
            conversation_agent, "call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = sample_llm_response

            # Act
            await conversation_agent._extract_metadata_from_md_files(tmpdir, md_files)

            # Assert
            assert mock_llm.called
            # Verify that the prompt contains content from both files
            call_args = mock_llm.call_args
            prompt = call_args[0][0]
            assert "Mouse 001" in prompt or "Mus musculus" in prompt


@pytest.mark.asyncio
async def test_llm_extracts_subject_id_correctly(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test LLM correctly extracts subject_id from metadata."""
    # Arrange
    dataset_path = str(test_dataset_path)
    md_files = ["README.md"]

    # Mock LLM call
    with patch.object(
        conversation_agent, "call_llm", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = sample_llm_response

        # Act
        result = await conversation_agent._extract_metadata_from_md_files(
            dataset_path, md_files
        )

        # Assert
        assert result.subject_id == "Test Mouse 001"


@pytest.mark.asyncio
async def test_llm_applies_reasonable_defaults(
    conversation_agent: ConversationAgent,
) -> None:
    """Test LLM applies reasonable defaults (e.g., 'mouse' -> 'Mus musculus')."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple .md file with minimal info
        readme = Path(tmpdir) / "README.md"
        readme.write_text("Subject: mouse\nExperiment on a mouse")

        md_files = ["README.md"]

        # Mock LLM to return standardized species name
        llm_response = json.dumps(
            {
                "species": "Mus musculus",  # LLM should standardize "mouse" to "Mus musculus"
                "extraction_confidence": {"species": "medium"},
            }
        )

        with patch.object(
            conversation_agent, "call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = llm_response

            # Act
            result = await conversation_agent._extract_metadata_from_md_files(
                tmpdir, md_files
            )

            # Assert
            assert result.species == "Mus musculus"


@pytest.mark.asyncio
async def test_extraction_confidence_tracked_per_field(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test extraction_confidence is tracked for each field."""
    # Arrange
    dataset_path = str(test_dataset_path)
    md_files = ["README.md"]

    # Mock LLM call
    with patch.object(
        conversation_agent, "call_llm", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = sample_llm_response

        # Act
        result = await conversation_agent._extract_metadata_from_md_files(
            dataset_path, md_files
        )

        # Assert
        assert isinstance(result.extraction_confidence, dict)
        assert "subject_id" in result.extraction_confidence
        assert "species" in result.extraction_confidence
        assert result.extraction_confidence["subject_id"] == "high"


@pytest.mark.asyncio
async def test_llm_extraction_log_stored(
    conversation_agent: ConversationAgent,
    test_dataset_path: Path,
    sample_llm_response: str,
) -> None:
    """Test llm_extraction_log is stored with the full LLM response."""
    # Arrange
    dataset_path = str(test_dataset_path)
    md_files = ["README.md"]

    # Mock LLM call
    with patch.object(
        conversation_agent, "call_llm", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = sample_llm_response

        # Act
        result = await conversation_agent._extract_metadata_from_md_files(
            dataset_path, md_files
        )

        # Assert
        assert result.llm_extraction_log is not None
        assert isinstance(result.llm_extraction_log, str)


@pytest.mark.asyncio
async def test_handles_llm_json_parsing_errors(
    conversation_agent: ConversationAgent, test_dataset_path: Path
) -> None:
    """Test gracefully handles LLM JSON parsing errors."""
    # Arrange
    dataset_path = str(test_dataset_path)
    md_files = ["README.md"]

    # Mock LLM to return invalid JSON
    invalid_json = "This is not valid JSON at all!"

    with patch.object(
        conversation_agent, "call_llm", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.return_value = invalid_json

        # Act
        result = await conversation_agent._extract_metadata_from_md_files(
            dataset_path, md_files
        )

        # Assert - should return empty metadata but not crash
        assert isinstance(result, MetadataExtractionResult)
        assert result.llm_extraction_log == invalid_json
        # All fields should be None or default
        assert result.subject_id is None
        assert result.species is None
