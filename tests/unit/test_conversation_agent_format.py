"""
Unit tests for ConversationAgent format detection (Task 4.1).

Tests the _detect_format method which identifies dataset formats:
- OpenEphys detection via settings.xml
- OpenEphys detection via .continuous files
- Unknown format handling
- Error handling for invalid paths
- Empty directory handling
"""

from pathlib import Path
import tempfile

import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.config import AgentConfig


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
async def test_detect_format_with_settings_xml(
    conversation_agent: ConversationAgent, test_dataset_path: Path
) -> None:
    """Test detect format returns 'openephys' when settings.xml is present."""
    # Arrange: test_dataset_path has settings.xml
    dataset_path = str(test_dataset_path)

    # Act
    detected_format = conversation_agent._detect_format(dataset_path)

    # Assert
    assert detected_format == "openephys"


@pytest.mark.asyncio
async def test_detect_format_with_continuous_files_only(
    conversation_agent: ConversationAgent,
) -> None:
    """Test detect format returns 'openephys' when .continuous files present but no settings.xml."""
    # Arrange: Create temp directory with .continuous files but no settings.xml
    with tempfile.TemporaryDirectory() as tmpdir:
        continuous_file = Path(tmpdir) / "100_CH1.continuous"
        continuous_file.write_bytes(b"fake continuous data")

        # Act
        detected_format = conversation_agent._detect_format(tmpdir)

        # Assert
        assert detected_format == "openephys"


@pytest.mark.asyncio
async def test_detect_format_with_neither_returns_unknown(
    conversation_agent: ConversationAgent,
) -> None:
    """Test detect format returns 'unknown' when neither settings.xml nor .continuous files present."""
    # Arrange: Create empty temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Act
        detected_format = conversation_agent._detect_format(tmpdir)

        # Assert
        assert detected_format == "unknown"


@pytest.mark.asyncio
async def test_detect_format_with_nonexistent_path_raises_error(
    conversation_agent: ConversationAgent,
) -> None:
    """Test detect format raises FileNotFoundError for non-existent path."""
    # Arrange
    nonexistent_path = "/this/path/does/not/exist/at/all"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        conversation_agent._detect_format(nonexistent_path)


@pytest.mark.asyncio
async def test_detect_format_with_empty_directory_returns_unknown(
    conversation_agent: ConversationAgent,
) -> None:
    """Test detect format returns 'unknown' for empty directory."""
    # Arrange: Create empty temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Ensure directory is truly empty
        assert len(list(Path(tmpdir).iterdir())) == 0

        # Act
        detected_format = conversation_agent._detect_format(tmpdir)

        # Assert
        assert detected_format == "unknown"
