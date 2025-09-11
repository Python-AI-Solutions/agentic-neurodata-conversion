"""
Unit tests for MCP server functionality.

Tests the MCPRegistry, MCPServer, and tool registration system.
Following TDD methodology - tests define expected behavior.
"""

from unittest.mock import Mock

import pytest

# Import components to test
from agentic_neurodata_conversion.mcp_server.server import (
    MCPRegistry,
    MCPServer,
    create_mcp_server,
)

# Import basic tools for testing (currently unused but may be needed for future tests)
from agentic_neurodata_conversion.mcp_server.tools.basic_tools import (  # noqa: F401
    echo_tool,
    get_server_status,
    list_registered_tools,
    manage_pipeline_state,
)


@pytest.fixture
def registry():
    """Create a fresh MCPRegistry for testing."""
    return MCPRegistry()


@pytest.fixture
def mcp_server():
    """Create a fresh MCPServer for testing."""
    return MCPServer()


@pytest.mark.unit
class TestMCPRegistry:
    """Test MCP tool registry functionality."""

    def test_registry_initialization(self, registry):
        """Test registry initializes with empty state."""
        assert len(registry.tools) == 0
        assert len(registry.tool_metadata) == 0
        assert registry.get_tool_names() == []

    def test_tool_registration_with_decorator(self, registry):
        """Test tool registration using decorator."""

        @registry.tool(name="test_tool", description="Test tool")
        async def test_function():
            return {"status": "success"}

        assert "test_tool" in registry.tools
        assert registry.get_tool("test_tool") == test_function
        assert registry.tool_metadata["test_tool"]["description"] == "Test tool"

    def test_tool_registration_without_name(self, registry):
        """Test tool registration uses function name when name not provided."""

        @registry.tool(description="Test function")
        async def my_test_function():
            return {"status": "success"}

        assert "my_test_function" in registry.tools
        assert registry.get_tool("my_test_function") == my_test_function

    def test_tool_metadata_extraction(self, registry):
        """Test tool metadata is properly extracted."""

        @registry.tool(name="metadata_test", description="Metadata test")
        async def test_func(_param1: str, _param2: int = 42, _server=None):
            """Test function docstring."""
            return {"status": "success"}

        metadata = registry.tool_metadata["metadata_test"]
        assert metadata["name"] == "metadata_test"
        assert metadata["description"] == "Metadata test"
        # Parameters include the underscore prefix as they appear in the function signature
        assert "_param1" in metadata["parameters"]
        assert "_param2" in metadata["parameters"]
        assert "server" not in metadata["parameters"]  # Should be excluded
        assert metadata["parameters"]["_param1"]["required"] is True
        assert metadata["parameters"]["_param2"]["required"] is False

    def test_list_tools(self, registry):
        """Test listing all registered tools."""

        @registry.tool(name="tool1")
        async def func1():
            pass

        @registry.tool(name="tool2")
        async def func2():
            pass

        tools = registry.list_tools()
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools

    def test_unregister_tool(self, registry):
        """Test tool unregistration."""

        @registry.tool(name="temp_tool")
        async def temp_function():
            pass

        assert "temp_tool" in registry.tools
        result = registry.unregister_tool("temp_tool")
        assert result is True
        assert "temp_tool" not in registry.tools

        # Test unregistering non-existent tool
        result = registry.unregister_tool("non_existent")
        assert result is False


@pytest.mark.unit
class TestMCPServer:
    """Test MCP server functionality."""

    def test_server_initialization(self, mcp_server):
        """Test server initializes with proper state."""
        assert mcp_server.registry is not None
        assert isinstance(mcp_server.pipeline_state, dict)
        assert len(mcp_server.pipeline_state) == 0
        assert mcp_server.is_running() is False

    def test_server_start_stop(self, mcp_server):
        """Test server start and stop functionality."""
        assert mcp_server.is_running() is False

        mcp_server.start()
        assert mcp_server.is_running() is True

        mcp_server.stop()
        assert mcp_server.is_running() is False

    @pytest.mark.asyncio
    async def test_tool_execution_success(self, mcp_server):
        """Test successful tool execution."""

        @mcp_server.registry.tool(name="test_execution")
        async def test_execution_function(param1: str, _server=None):
            return {"status": "success", "param1": param1}

        result = await mcp_server.execute_tool("test_execution", param1="test_value")
        # The result should contain the returned data from the function
        assert result["status"] == "success"
        assert result["param1"] == "test_value"

    @pytest.mark.asyncio
    async def test_tool_execution_not_found(self, mcp_server):
        """Test tool execution with non-existent tool."""
        result = await mcp_server.execute_tool("non_existent_tool")
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()
        assert "available_tools" in result

    @pytest.mark.asyncio
    async def test_tool_execution_with_state_updates(self, mcp_server):
        """Test tool execution updates pipeline state."""

        @mcp_server.registry.tool(name="state_updater")
        async def state_updater_function(_server=None):
            return {
                "status": "success",
                "state_updates": {"test_key": "test_value", "counter": 1},
            }

        initial_state = mcp_server.get_pipeline_state()
        assert len(initial_state) == 0

        result = await mcp_server.execute_tool("state_updater")
        assert result["status"] == "success"

        updated_state = mcp_server.get_pipeline_state()
        assert updated_state["test_key"] == "test_value"
        assert updated_state["counter"] == 1

    def test_pipeline_state_management(self, mcp_server):
        """Test pipeline state get/update/clear operations."""
        # Test initial empty state
        state = mcp_server.get_pipeline_state()
        assert len(state) == 0

        # Test update
        updates = {"key1": "value1", "key2": 42}
        mcp_server.update_pipeline_state(updates)

        state = mcp_server.get_pipeline_state()
        assert state["key1"] == "value1"
        assert state["key2"] == 42

        # Test clear
        mcp_server.clear_pipeline_state()
        state = mcp_server.get_pipeline_state()
        assert len(state) == 0

    def test_server_status(self, mcp_server):
        """Test server status reporting."""
        status = mcp_server.get_server_status()

        assert "status" in status
        assert "registered_tools" in status
        assert "tool_names" in status
        assert "agents" in status
        assert "pipeline_state_keys" in status
        assert "config_available" in status

        assert isinstance(status["registered_tools"], int)
        assert isinstance(status["tool_names"], list)


def test_create_mcp_server():
    """Test MCP server factory function."""
    server = create_mcp_server()
    assert isinstance(server, MCPServer)
    assert server.config is None

    mock_config = Mock()
    server_with_config = create_mcp_server(mock_config)
    assert server_with_config.config == mock_config
