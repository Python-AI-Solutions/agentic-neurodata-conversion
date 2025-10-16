"""
Unit tests for ConversationAgent OpenEphys structure validation (Task 4.2).

Tests the _validate_openephys_structure method which:
- Validates OpenEphys dataset structure
- Returns DatasetInfo with all fields populated
- Checks for required files (settings.xml, .continuous)
- Calculates total size and file counts
- Detects metadata files (.md)
"""

from pathlib import Path
import tempfile

import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.session_context import DatasetInfo


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


@pytest.mark.asyncio
async def test_validate_openephys_structure_with_valid_dataset(
    conversation_agent: ConversationAgent, test_dataset_path: Path
) -> None:
    """Test validate structure succeeds with valid OpenEphys dataset."""
    # Arrange
    dataset_path = str(test_dataset_path)

    # Act
    dataset_info = conversation_agent._validate_openephys_structure(dataset_path)

    # Assert
    assert isinstance(dataset_info, DatasetInfo)
    assert dataset_info.dataset_path == dataset_path
    assert dataset_info.format == "openephys"


@pytest.mark.asyncio
async def test_validate_returns_dataset_info_with_all_fields(
    conversation_agent: ConversationAgent, test_dataset_path: Path
) -> None:
    """Test validate structure returns DatasetInfo with all required fields populated."""
    # Arrange
    dataset_path = str(test_dataset_path)

    # Act
    dataset_info = conversation_agent._validate_openephys_structure(dataset_path)

    # Assert
    assert dataset_info.dataset_path == dataset_path
    assert dataset_info.format == "openephys"
    assert dataset_info.total_size_bytes > 0
    assert dataset_info.file_count > 0
    assert isinstance(dataset_info.has_metadata_files, bool)
    assert isinstance(dataset_info.metadata_files, list)


@pytest.mark.asyncio
async def test_validate_raises_error_for_missing_settings_xml(
    conversation_agent: ConversationAgent,
) -> None:
    """Test validate structure raises ValueError when settings.xml is missing."""
    # Arrange: Create temp directory with .continuous files but no settings.xml
    with tempfile.TemporaryDirectory() as tmpdir:
        continuous_file = Path(tmpdir) / "100_CH1.continuous"
        continuous_file.write_bytes(b"fake continuous data")

        # Act & Assert
        with pytest.raises(ValueError, match="settings.xml not found"):
            conversation_agent._validate_openephys_structure(tmpdir)


@pytest.mark.asyncio
async def test_validate_raises_error_for_missing_continuous_files(
    conversation_agent: ConversationAgent,
) -> None:
    """Test validate structure raises ValueError when no .continuous files found."""
    # Arrange: Create temp directory with settings.xml but no .continuous files
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "settings.xml"
        settings_file.write_text("<settings></settings>")

        # Act & Assert
        with pytest.raises(ValueError, match="No .continuous files found"):
            conversation_agent._validate_openephys_structure(tmpdir)


@pytest.mark.asyncio
async def test_validate_calculates_total_size_correctly(
    conversation_agent: ConversationAgent, test_dataset_path: Path
) -> None:
    """Test validate structure calculates total size correctly."""
    # Arrange
    dataset_path = str(test_dataset_path)
    # Calculate expected size manually
    expected_size = sum(
        f.stat().st_size for f in test_dataset_path.rglob("*") if f.is_file()
    )

    # Act
    dataset_info = conversation_agent._validate_openephys_structure(dataset_path)

    # Assert
    assert dataset_info.total_size_bytes == expected_size


@pytest.mark.asyncio
async def test_validate_counts_files_correctly(
    conversation_agent: ConversationAgent, test_dataset_path: Path
) -> None:
    """Test validate structure counts files correctly."""
    # Arrange
    dataset_path = str(test_dataset_path)
    # Count expected files manually
    expected_count = sum(1 for f in test_dataset_path.rglob("*") if f.is_file())

    # Act
    dataset_info = conversation_agent._validate_openephys_structure(dataset_path)

    # Assert
    assert dataset_info.file_count == expected_count


@pytest.mark.asyncio
async def test_validate_detects_md_files(
    conversation_agent: ConversationAgent, test_dataset_path: Path
) -> None:
    """Test validate structure detects .md files in dataset."""
    # Arrange
    dataset_path = str(test_dataset_path)

    # Act
    dataset_info = conversation_agent._validate_openephys_structure(dataset_path)

    # Assert
    # The synthetic dataset has README.md
    md_files = [f for f in dataset_info.metadata_files if f.endswith(".md")]
    assert len(md_files) > 0


@pytest.mark.asyncio
async def test_validate_sets_has_metadata_files_flag_correctly(
    conversation_agent: ConversationAgent, test_dataset_path: Path
) -> None:
    """Test validate structure sets has_metadata_files flag correctly."""
    # Arrange
    dataset_path = str(test_dataset_path)

    # Act
    dataset_info = conversation_agent._validate_openephys_structure(dataset_path)

    # Assert
    # The synthetic dataset has README.md, so has_metadata_files should be True
    assert dataset_info.has_metadata_files is True
    assert len(dataset_info.metadata_files) > 0

    # Test with dataset without .md files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create valid OpenEphys structure without .md files
        settings_file = Path(tmpdir) / "settings.xml"
        settings_file.write_text("<settings></settings>")
        continuous_file = Path(tmpdir) / "100_CH1.continuous"
        continuous_file.write_bytes(b"fake continuous data")

        # Act
        dataset_info_no_md = conversation_agent._validate_openephys_structure(tmpdir)

        # Assert
        assert dataset_info_no_md.has_metadata_files is False
        assert len(dataset_info_no_md.metadata_files) == 0
