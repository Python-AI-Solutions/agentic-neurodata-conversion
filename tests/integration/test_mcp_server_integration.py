"""
Integration tests for MCP server functionality.

Tests the complete MCP server workflow including tool registration,
execution, and state management.
"""

import pytest

# Import components to test
try:
    from agentic_neurodata_conversion.mcp_server.server import MCPServer

    MCP_INTEGRATION_AVAILABLE = True
except ImportError:
    MCP_INTEGRATION_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not MCP_INTEGRATION_AVAILABLE,
    reason="MCP server integration components not implemented yet",
)


@pytest.fixture
def mcp_server():
    """Create a fresh MCPServer for integration testing."""
    return MCPServer()


@pytest.mark.integration
class TestMCPServerIntegration:
    """Test complete MCP server integration."""

    @pytest.mark.asyncio
    async def test_basic_tool_workflow(self, mcp_server):
        """Test complete workflow using basic tools."""
        # Start server
        mcp_server.start()
        assert mcp_server.is_running()

        # Test server status tool
        status_result = await mcp_server.execute_tool("server_status")
        assert status_result["status"] == "success"

        # Test list tools
        tools_result = await mcp_server.execute_tool("list_tools")
        assert tools_result["status"] == "success"
        assert tools_result["result"]["tool_count"] > 0

        # Test echo tool
        echo_result = await mcp_server.execute_tool(
            "echo", message="Integration test message", metadata={"test": "integration"}
        )
        assert echo_result["status"] == "success"
        assert echo_result["result"]["echoed_message"] == "Integration test message"

        # Test pipeline state management
        state_update_result = await mcp_server.execute_tool(
            "pipeline_state",
            action="update",
            updates={"integration_test": True, "step": 1},
        )
        assert state_update_result["status"] == "success"

        # Verify state was updated
        state_get_result = await mcp_server.execute_tool("pipeline_state", action="get")
        assert state_get_result["status"] == "success"
        pipeline_state = state_get_result["result"]["pipeline_state"]
        assert pipeline_state["integration_test"] is True
        assert pipeline_state["step"] == 1

        # Clear state
        state_clear_result = await mcp_server.execute_tool(
            "pipeline_state", action="clear"
        )
        assert state_clear_result["status"] == "success"

        # Stop server
        mcp_server.stop()
        assert not mcp_server.is_running()

    @pytest.mark.asyncio
    async def test_tool_registration_and_execution(self, mcp_server):
        """Test dynamic tool registration and execution."""

        # Register a custom tool
        @mcp_server.registry.tool(
            name="integration_test_tool", description="Tool for integration testing"
        )
        async def integration_test_function(
            test_param: str, optional_param: int = 100, server=None
        ):
            return {
                "status": "success",
                "test_param": test_param,
                "optional_param": optional_param,
                "server_available": server is not None,
            }

        # Verify tool was registered
        tools = mcp_server.registry.list_tools()
        assert "integration_test_tool" in tools

        # Execute the custom tool
        result = await mcp_server.execute_tool(
            "integration_test_tool", test_param="integration_value", optional_param=200
        )

        assert result["status"] == "success"
        assert result["test_param"] == "integration_value"
        assert result["optional_param"] == 200
        assert result["server_available"] is True

    def test_server_status_reporting(self, mcp_server):
        """Test comprehensive server status reporting."""
        status = mcp_server.get_server_status()

        # Verify all expected status fields
        expected_fields = [
            "status",
            "registered_tools",
            "tool_names",
            "agents",
            "pipeline_state_keys",
            "config_available",
        ]

        for field in expected_fields:
            assert field in status, f"Missing status field: {field}"

        # Verify tool registration is reflected in status
        assert status["registered_tools"] > 0
        assert len(status["tool_names"]) > 0
        assert "server_status" in status["tool_names"]
        assert "echo" in status["tool_names"]
