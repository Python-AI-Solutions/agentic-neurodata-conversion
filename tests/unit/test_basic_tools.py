"""
Unit tests for basic MCP tools.

Tests the basic tools that demonstrate the MCP tool system functionality.
"""

import pytest
from unittest.mock import Mock

# Import components to test
try:
    from agentic_neurodata_conversion.mcp_server.server import MCPServer
    from agentic_neurodata_conversion.mcp_server.tools.basic_tools import (
        get_server_status, list_registered_tools, manage_pipeline_state, echo_tool
    )
    BASIC_TOOLS_AVAILABLE = True
except ImportError:
    BASIC_TOOLS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not BASIC_TOOLS_AVAILABLE, 
    reason="Basic tools not implemented yet"
)


@pytest.fixture
def mcp_server():
    """Create a fresh MCPServer for testing."""
    return MCPServer()


@pytest.mark.unit
class TestBasicTools:
    """Test basic MCP tools functionality."""
    
    @pytest.mark.asyncio
    async def test_server_status_tool(self, mcp_server):
        """Test server status tool execution."""
        result = await get_server_status(server=mcp_server)
        
        assert result["status"] == "success"
        assert "result" in result
        status_data = result["result"]
        assert "status" in status_data
        assert "registered_tools" in status_data
        assert "tool_names" in status_data
    
    @pytest.mark.asyncio
    async def test_server_status_tool_no_server(self):
        """Test server status tool without server context."""
        result = await get_server_status(server=None)
        
        assert result["status"] == "error"
        assert "Server context not available" in result["message"]
    
    @pytest.mark.asyncio
    async def test_list_tools_tool(self, mcp_server):
        """Test list tools functionality."""
        result = await list_registered_tools(server=mcp_server)
        
        assert result["status"] == "success"
        assert "result" in result
        tools_data = result["result"]
        assert "tool_count" in tools_data
        assert "tools" in tools_data
        assert isinstance(tools_data["tool_count"], int)
    
    @pytest.mark.asyncio
    async def test_pipeline_state_get(self, mcp_server):
        """Test getting pipeline state."""
        result = await manage_pipeline_state(action="get", server=mcp_server)
        
        assert result["status"] == "success"
        assert "result" in result
        state_data = result["result"]
        assert "pipeline_state" in state_data
        assert "state_keys" in state_data
    
    @pytest.mark.asyncio
    async def test_pipeline_state_update(self, mcp_server):
        """Test updating pipeline state."""
        updates = {"test_key": "test_value", "number": 42}
        result = await manage_pipeline_state(
            action="update", 
            updates=updates, 
            server=mcp_server
        )
        
        assert result["status"] == "success"
        assert "result" in result
        update_data = result["result"]
        assert "updated_keys" in update_data
        assert set(update_data["updated_keys"]) == set(updates.keys())
        
        # Verify state was actually updated
        server_state = mcp_server.get_pipeline_state()
        assert server_state["test_key"] == "test_value"
        assert server_state["number"] == 42
    
    @pytest.mark.asyncio
    async def test_pipeline_state_clear(self, mcp_server):
        """Test clearing pipeline state."""
        # First add some state
        mcp_server.update_pipeline_state({"key": "value"})
        assert len(mcp_server.get_pipeline_state()) > 0
        
        # Clear it
        result = await manage_pipeline_state(action="clear", server=mcp_server)
        
        assert result["status"] == "success"
        assert "Pipeline state cleared" in result["result"]["message"]
        
        # Verify state was cleared
        assert len(mcp_server.get_pipeline_state()) == 0
    
    @pytest.mark.asyncio
    async def test_pipeline_state_invalid_action(self, mcp_server):
        """Test pipeline state with invalid action."""
        result = await manage_pipeline_state(action="invalid", server=mcp_server)
        
        assert result["status"] == "error"
        assert "Unknown action" in result["message"]
    
    @pytest.mark.asyncio
    async def test_echo_tool_basic(self, mcp_server):
        """Test basic echo tool functionality."""
        message = "Hello, MCP!"
        result = await echo_tool(message=message, server=mcp_server)
        
        assert result["status"] == "success"
        assert "result" in result
        echo_data = result["result"]
        assert echo_data["echoed_message"] == message
        assert echo_data["server_available"] is True
        assert echo_data["server_status"] is False  # Server not started
    
    @pytest.mark.asyncio
    async def test_echo_tool_with_metadata(self, mcp_server):
        """Test echo tool with metadata."""
        message = "Test message"
        metadata = {"type": "test", "priority": "high"}
        
        result = await echo_tool(
            message=message, 
            metadata=metadata, 
            server=mcp_server
        )
        
        assert result["status"] == "success"
        echo_data = result["result"]
        assert echo_data["echoed_message"] == message
        assert echo_data["metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_echo_tool_no_server(self):
        """Test echo tool without server context."""
        result = await echo_tool(message="test", server=None)
        
        assert result["status"] == "success"
        echo_data = result["result"]
        assert echo_data["server_available"] is False
        assert "server_status" not in echo_data