"""
Unit tests for pytest fixtures defined in conftest.py.

Tests verify that all shared fixtures are working correctly:
- Event loop
- Redis client (fakeredis)
- Context manager
- Agent registry
- Test session
- Test dataset path
- MCP server URL
"""

from pathlib import Path

import fakeredis.aioredis
import pytest

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.models.session_context import (
    SessionContext,
    WorkflowStage,
)

pytestmark = pytest.mark.unit


class TestEventLoopFixture:
    """Test event loop fixture."""

    def test_event_loop_available(self, event_loop):
        """Test that event loop is available."""
        assert event_loop is not None
        assert not event_loop.is_closed()


class TestRedisClientFixture:
    """Test Redis client fixture."""

    @pytest.mark.asyncio
    async def test_redis_client_available(self, redis_client):
        """Test that Redis client is available and working."""
        assert redis_client is not None
        assert isinstance(redis_client, fakeredis.aioredis.FakeRedis)

        # Test basic Redis operation
        await redis_client.set(b"test_key", b"test_value")
        value = await redis_client.get(b"test_key")
        assert value == b"test_value"

    @pytest.mark.asyncio
    async def test_redis_client_isolated(self, redis_client):
        """Test that Redis client is isolated between tests."""
        # Set a value
        await redis_client.set(b"isolation_test", b"value1")

        # This should be isolated from other tests
        value = await redis_client.get(b"isolation_test")
        assert value == b"value1"


class TestContextManagerFixture:
    """Test context manager fixture."""

    @pytest.mark.asyncio
    async def test_context_manager_available(self, context_manager):
        """Test that context manager is available and configured."""
        assert context_manager is not None
        assert isinstance(context_manager, ContextManager)
        assert context_manager._redis is not None

    @pytest.mark.asyncio
    async def test_context_manager_can_create_session(
        self, context_manager, test_session
    ):
        """Test that context manager can create sessions."""
        await context_manager.create_session(test_session)

        # Retrieve session
        retrieved = await context_manager.get_session(test_session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == test_session.session_id

    @pytest.mark.asyncio
    async def test_context_manager_uses_temp_path(self, context_manager, tmp_path):
        """Test that context manager uses temporary path."""
        # The filesystem base path should be the temp path
        assert str(tmp_path) in context_manager._filesystem_base_path


class TestAgentRegistryFixture:
    """Test agent registry fixture."""

    def test_agent_registry_available(self, agent_registry):
        """Test that agent registry is available."""
        assert agent_registry is not None
        assert isinstance(agent_registry, AgentRegistry)

    def test_agent_registry_empty_initially(self, agent_registry):
        """Test that agent registry starts empty."""
        agents = agent_registry.list_agents()
        assert len(agents) == 0

    def test_agent_registry_can_register_agents(self, agent_registry):
        """Test that agents can be registered."""
        agent_registry.register_agent(
            agent_name="test_agent",
            agent_type="test",
            base_url="http://localhost:3001",
            capabilities=["test_capability"],
        )

        agent = agent_registry.get_agent("test_agent")
        assert agent is not None
        assert agent["agent_name"] == "test_agent"


class TestTestSessionFixture:
    """Test test_session fixture."""

    def test_test_session_available(self, test_session):
        """Test that test session is available."""
        assert test_session is not None
        assert isinstance(test_session, SessionContext)

    def test_test_session_has_correct_values(self, test_session):
        """Test that test session has expected values."""
        assert test_session.session_id == "test-session-001"
        assert test_session.workflow_stage == WorkflowStage.INITIALIZED
        assert test_session.created_at is not None
        assert test_session.last_updated is not None


class TestTestDatasetPathFixture:
    """Test test_dataset_path fixture."""

    def test_test_dataset_path_available(self, test_dataset_path):
        """Test that test dataset path is available."""
        assert test_dataset_path is not None
        assert isinstance(test_dataset_path, Path)

    def test_test_dataset_path_exists(self, test_dataset_path):
        """Test that test dataset path exists."""
        assert test_dataset_path.exists()
        assert test_dataset_path.is_dir()

    def test_test_dataset_has_required_files(self, test_dataset_path):
        """Test that test dataset has all required files."""
        # Check for required files
        assert (test_dataset_path / "settings.xml").exists()
        assert (test_dataset_path / "100_CH1.continuous").exists()
        assert (test_dataset_path / "100_CH2.continuous").exists()
        assert (test_dataset_path / "README.md").exists()

    def test_test_dataset_readme_has_metadata(self, test_dataset_path):
        """Test that README.md contains expected metadata."""
        readme_path = test_dataset_path / "README.md"
        content = readme_path.read_text()

        # Check for key metadata fields
        assert "Test Mouse 001" in content
        assert "Mus musculus" in content
        assert "P56" in content
        assert "Male" in content
        assert "Open Ephys" in content
        assert "30000 Hz" in content


class TestMCPServerURLFixture:
    """Test mcp_server_url fixture."""

    def test_mcp_server_url_available(self, mcp_server_url):
        """Test that MCP server URL is available."""
        assert mcp_server_url is not None
        assert isinstance(mcp_server_url, str)

    def test_mcp_server_url_format(self, mcp_server_url):
        """Test that MCP server URL has correct format."""
        assert mcp_server_url.startswith("http://")
        assert "localhost" in mcp_server_url or "127.0.0.1" in mcp_server_url


class TestMessageRouterFixture:
    """Test message_router fixture (placeholder for Phase 2)."""

    def test_message_router_fixture_exists(self, message_router):
        """Test that message_router fixture exists (returns None for now)."""
        # For now, this should return None as MessageRouter is not yet implemented
        assert message_router is None
