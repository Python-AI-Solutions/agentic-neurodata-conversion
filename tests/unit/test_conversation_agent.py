"""
Unit tests for the conversation agent.

Tests the ConversationAgent functionality including dataset analysis,
metadata extraction, and question generation.
"""

from pathlib import Path
import shutil
import tempfile

import pytest

# Import the actual components that should be implemented
from agentic_neurodata_conversion.agents.base import (
    AgentCapability,
    AgentStatus,
)
from agentic_neurodata_conversion.agents.conversation import ConversationAgent


class TestConversationAgent:
    """Test the ConversationAgent functionality."""

    @pytest.fixture
    def conversation_agent(self):
        """Create a conversation agent instance."""
        config = {"use_llm": False, "llm_config": {"model": "test-model"}}
        return ConversationAgent(config=config, agent_id="test_conversation_agent")

    @pytest.fixture
    def test_dataset_dir(self):
        """Create a temporary test dataset directory."""
        temp_dir = tempfile.mkdtemp()
        dataset_path = Path(temp_dir)

        # Create some test files
        (dataset_path / "data.continuous").write_text("test data")
        (dataset_path / "events.events").write_text("test events")
        (dataset_path / "metadata.json").write_text('{"test": "metadata"}')

        yield str(dataset_path)

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.mark.unit
    def test_agent_initialization(self, conversation_agent):
        """Test conversation agent initialization."""
        assert conversation_agent.agent_id == "test_conversation_agent"
        assert conversation_agent.status == AgentStatus.READY
        assert conversation_agent.has_capability(AgentCapability.CONVERSATION)
        assert conversation_agent.has_capability(AgentCapability.DATASET_ANALYSIS)
        assert conversation_agent.has_capability(AgentCapability.METADATA_EXTRACTION)

    @pytest.mark.unit
    async def test_dataset_analysis_task(self, conversation_agent, test_dataset_dir):
        """Test dataset analysis task execution."""
        task = {
            "type": "dataset_analysis",
            "dataset_dir": test_dataset_dir,
            "use_llm": False,
            "session_id": "test_session",
        }

        result = await conversation_agent.execute_task(task)

        assert result["status"] == "completed"
        assert result["agent_id"] == conversation_agent.agent_id

        # Check result data structure
        data = result.get("data", {})
        assert "format_analysis" in data
        assert "basic_metadata" in data
        assert "enriched_metadata" in data
        assert "missing_metadata" in data
        assert "questions" in data
        assert "session_id" in data

        assert data["session_id"] == "test_session"

    @pytest.mark.unit
    async def test_conversation_task(self, conversation_agent):
        """Test conversation task execution."""
        task = {
            "type": "conversation",
            "message": "What metadata is missing?",
            "session_id": "test_session",
        }

        result = await conversation_agent.execute_task(task)

        assert result["status"] == "completed"
        assert result["agent_id"] == conversation_agent.agent_id
        assert "response" in result
        assert "session_id" in result

    @pytest.mark.unit
    async def test_unsupported_task_type(self, conversation_agent):
        """Test handling of unsupported task type."""
        task = {"type": "unsupported_task", "params": {}}

        with pytest.raises(ValueError, match="cannot handle task type"):
            await conversation_agent.execute_task(task)

    @pytest.mark.unit
    async def test_format_detection_task(self, conversation_agent, test_dataset_dir):
        """Test format detection functionality."""
        task = {
            "type": "dataset_analysis",
            "dataset_dir": test_dataset_dir,
            "use_llm": False,
        }

        result = await conversation_agent.execute_task(task)

        format_analysis = result["data"]["format_analysis"]
        assert "formats" in format_analysis
        assert "file_count" in format_analysis
        assert "total_size" in format_analysis

        # Should detect Open Ephys format from .continuous and .events files
        formats = format_analysis["formats"]
        if formats:
            assert any(f["format"] == "open_ephys" for f in formats)

    @pytest.mark.unit
    def test_capability_registration(self, conversation_agent):
        """Test that conversation agent has correct capabilities."""
        capabilities = conversation_agent.get_capabilities()

        assert AgentCapability.CONVERSATION in capabilities
        assert AgentCapability.DATASET_ANALYSIS in capabilities
        assert AgentCapability.METADATA_EXTRACTION in capabilities

    @pytest.mark.unit
    def test_task_handling_capability(self, conversation_agent):
        """Test task handling capabilities."""
        # Should handle conversation tasks
        conv_task = {"type": "conversation", "message": "test"}
        assert conversation_agent.can_handle_task(conv_task)

        # Should handle dataset analysis tasks
        analysis_task = {"type": "dataset_analysis", "dataset_dir": "/test"}
        assert conversation_agent.can_handle_task(analysis_task)

        # Should handle metadata extraction tasks
        metadata_task = {"type": "metadata_extraction", "data": {}}
        assert conversation_agent.can_handle_task(metadata_task)

        # Should not handle unsupported tasks
        unsupported_task = {"type": "format_detection", "data": {}}
        assert not conversation_agent.can_handle_task(unsupported_task)

    @pytest.mark.unit
    async def test_metadata_extraction_task(self, conversation_agent):
        """Test metadata extraction task."""
        task = {
            "type": "metadata_extraction",
            "data": {
                "session_description": "Test recording session",
                "experimenter": "John Doe",
                "sampling_rate": "30000",
            },
            "session_id": "test_session",
        }

        result = await conversation_agent.execute_task(task)

        assert result["status"] == "completed"
        assert result["agent_id"] == conversation_agent.agent_id
        assert "extracted_metadata" in result
        assert result["session_id"] == "test_session"

    @pytest.mark.unit
    async def test_error_handling(self, conversation_agent):
        """Test error handling in task processing."""
        # Test with invalid task data
        task = {
            "type": "dataset_analysis",
            "dataset_dir": "/nonexistent/path",
            "session_id": "test_session",
        }

        with pytest.raises((ValueError, FileNotFoundError, RuntimeError)):
            await conversation_agent.execute_task(task)

        # Agent should be in error state
        assert conversation_agent.status == AgentStatus.ERROR
        assert conversation_agent.error_count > 0

    @pytest.mark.unit
    def test_agent_status_reporting(self, conversation_agent):
        """Test agent status reporting."""
        status = conversation_agent.get_status()

        assert status["agent_id"] == "test_conversation_agent"
        assert status["agent_type"] == "ConversationAgent"
        assert status["status"] == "ready"
        assert "conversation" in status["capabilities"]
        assert "dataset_analysis" in status["capabilities"]
        assert "metadata_extraction" in status["capabilities"]

    @pytest.mark.unit
    async def test_agent_shutdown(self, conversation_agent):
        """Test agent shutdown."""
        await conversation_agent.shutdown()
        assert conversation_agent.status == AgentStatus.STOPPED
