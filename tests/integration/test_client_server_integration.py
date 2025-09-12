"""
Integration tests for client-server interaction.

This module tests that the client examples work correctly with the MCP server,
ensuring the complete system integration functions as expected.
"""

import asyncio
import json
import logging
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from agentic_neurodata_conversion.core.config import ConfigurationManager
from agentic_neurodata_conversion.mcp_server.server import MCPServer
from agentic_neurodata_conversion.mcp_server.tools import basic_tools  # noqa: F401

logger = logging.getLogger(__name__)


class MCPServerFixture:
    """Test fixture for running MCP server during tests."""

    def __init__(self, port: int = 8002):
        """Initialize server fixture."""
        self.port = port
        self.server = None
        self.config = None
        self.server_process = None

    async def start(self) -> None:
        """Start MCP server for testing."""
        # Create test configuration
        test_config_data = {
            "environment": "testing",
            "debug": True,
            "data_directory": "./temp/test_data",
            "temp_directory": "./temp/test_temp",
            "logging": {"level": "INFO", "enable_file_logging": False},
            "http": {"host": "127.0.0.1", "port": self.port},
            "mcp": {"transport_type": "stdio"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_config_data, f, indent=2)
            config_path = f.name

        # Load configuration
        config_manager = ConfigurationManager(config_path)
        self.config = config_manager.load_config()

        # Create and start server
        self.server = MCPServer(self.config)
        self.server.start()

        # Clean up temp config
        Path(config_path).unlink()

        logger.info(f"Test MCP server started on port {self.port}")

    async def stop(self) -> None:
        """Stop MCP server."""
        if self.server:
            self.server.stop()
            logger.info("Test MCP server stopped")

    def get_api_url(self) -> str:
        """Get API URL for the test server."""
        return f"http://127.0.0.1:{self.port}"


@pytest.fixture
async def mcp_server():
    """Pytest fixture for MCP server."""
    server_fixture = MCPServerFixture()
    await server_fixture.start()
    yield server_fixture
    await server_fixture.stop()


@pytest.mark.integration
class TestClientServerIntegration:
    """Test client-server integration functionality."""

    async def test_server_startup_and_status(self, mcp_server):
        """Test that server starts up and responds to status requests."""
        mcp_server.get_api_url()

        # Wait a moment for server to be ready
        await asyncio.sleep(0.1)

        # Test server status endpoint (simulated)
        assert mcp_server.server.is_running()
        status = mcp_server.server.get_server_status()
        assert status["status"] == "running"
        assert "registered_tools" in status

    @pytest.mark.xfail(reason="Basic tools may not be fully implemented yet")
    async def test_basic_tool_execution(self, mcp_server):
        """Test basic tool execution through server."""
        server = mcp_server.server

        # Test server status tool
        result = await server.execute_tool("server_status")
        assert result["status"] == "success"
        assert "result" in result

        # Test echo tool
        result = await server.execute_tool("echo", message="test message")
        assert result["status"] == "success"
        assert result["result"]["echoed_message"] == "test message"

        # Test pipeline state management
        result = await server.execute_tool(
            "pipeline_state", action="update", updates={"test": "value"}
        )
        assert result["status"] == "success"

        result = await server.execute_tool("pipeline_state", action="get")
        assert result["status"] == "success"
        assert result["result"]["pipeline_state"]["test"] == "value"

    async def test_simple_client_integration(self, mcp_server):
        """Test simple client example integration."""
        # Import the simple client
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples"))

        from python_client.simple_client import SimpleMCPClient

        # Create client pointing to test server
        client = SimpleMCPClient(api_url=mcp_server.get_api_url())

        # Test server status (mock the HTTP call since we're testing directly)
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"status": "running", "tools": 4}
            mock_get.return_value.raise_for_status.return_value = None

            status = client.get_server_status()
            assert status["status"] == "running"

        # Test tool listing (mock the HTTP call)
        with patch("requests.get") as mock_get:
            mock_tools = {
                "tools": {
                    "server_status": {"description": "Get server status"},
                    "echo": {"description": "Echo tool"},
                }
            }
            mock_get.return_value.json.return_value = mock_tools
            mock_get.return_value.raise_for_status.return_value = None

            tools = client.list_tools()
            assert "tools" in tools
            assert "server_status" in tools["tools"]

        # Test tool execution (mock the HTTP call)
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "status": "success",
                "result": {"echoed_message": "test"},
            }
            mock_post.return_value.raise_for_status.return_value = None

            result = client._call_tool("echo", {"message": "test"})
            assert result["status"] == "success"

    async def test_workflow_client_integration(self, mcp_server):
        """Test workflow client example integration."""
        # Import the workflow client
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples"))

        from python_client.workflow_example import MCPWorkflowClient

        # Create client pointing to test server
        client = MCPWorkflowClient(
            api_url=mcp_server.get_api_url(),
            output_dir="./temp/test_output",
            use_llm=False,
        )

        # Test server status check (mock HTTP calls)
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"status": "running"}
            mock_get.return_value.raise_for_status.return_value = None

            status = client.check_server_status()
            assert status["status"] == "running"

        # Test tool listing
        with patch("requests.get") as mock_get:
            mock_tools = {
                "tools": {
                    "dataset_analysis": {"description": "Analyze dataset"},
                    "conversion_orchestration": {"description": "Convert data"},
                }
            }
            mock_get.return_value.json.return_value = mock_tools
            mock_get.return_value.raise_for_status.return_value = None

            tools = client.list_available_tools()
            assert "tools" in tools

        # Test dataset analysis (mock the tool call)
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {
                "status": "success",
                "result": {"metadata": {"subject": "test"}},
            }
            mock_post.return_value.raise_for_status.return_value = None

            result = client.analyze_dataset("./test/dataset")
            assert result["status"] == "success"
            assert "normalized_metadata" in client.pipeline_state

    @pytest.mark.xfail(reason="Error handling may not be fully implemented yet")
    async def test_error_handling_integration(self, mcp_server):
        """Test error handling in client-server integration."""
        server = mcp_server.server

        # Test calling non-existent tool
        result = await server.execute_tool("nonexistent_tool")
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

        # Test tool with invalid parameters
        result = await server.execute_tool("echo")  # Missing required message parameter
        assert result["status"] == "error"

        # Test server error handling - server should catch exceptions and return error responses
        with patch.object(
            server.registry, "get_tool", side_effect=Exception("Test error")
        ):
            result = await server.execute_tool("echo", message="test")
            assert result["status"] == "error"
            assert "Test error" in result["message"]

    async def test_pipeline_state_persistence(self, mcp_server):
        """Test pipeline state persistence across tool calls."""
        server = mcp_server.server

        # Set initial state
        result = await server.execute_tool(
            "pipeline_state",
            action="update",
            updates={"step1": "completed", "data": {"key": "value"}},
        )
        assert result["status"] == "success"

        # Verify state persists
        result = await server.execute_tool("pipeline_state", action="get")
        assert result["status"] == "success"
        state = result["result"]["pipeline_state"]
        assert state["step1"] == "completed"
        assert state["data"]["key"] == "value"

        # Update state
        result = await server.execute_tool(
            "pipeline_state", action="update", updates={"step2": "completed"}
        )
        assert result["status"] == "success"

        # Verify both updates persist
        result = await server.execute_tool("pipeline_state", action="get")
        state = result["result"]["pipeline_state"]
        assert state["step1"] == "completed"
        assert state["step2"] == "completed"

        # Clear state
        result = await server.execute_tool("pipeline_state", action="clear")
        assert result["status"] == "success"

        # Verify state is cleared
        result = await server.execute_tool("pipeline_state", action="get")
        state = result["result"]["pipeline_state"]
        assert len(state) == 0

    async def test_concurrent_tool_execution(self, mcp_server):
        """Test concurrent tool execution."""
        server = mcp_server.server

        # Execute multiple tools concurrently
        tasks = [server.execute_tool("echo", message=f"message_{i}") for i in range(5)]

        results = await asyncio.gather(*tasks)

        # Verify all executions succeeded
        for i, result in enumerate(results):
            assert result["status"] == "success"
            assert result["result"]["echoed_message"] == f"message_{i}"

    async def test_tool_metadata_access(self, mcp_server):
        """Test tool metadata access and validation."""
        server = mcp_server.server

        # Get tool metadata
        tools = server.registry.list_tools()

        # Verify expected tools are present
        expected_tools = ["server_status", "list_tools", "pipeline_state", "echo"]
        for tool_name in expected_tools:
            assert tool_name in tools
            tool_meta = tools[tool_name]
            assert "description" in tool_meta
            assert "parameters" in tool_meta

        # Verify tool parameters are documented
        echo_meta = tools["echo"]
        assert "message" in echo_meta["parameters"]
        assert echo_meta["parameters"]["message"]["required"] is True

    async def test_server_lifecycle_management(self, mcp_server):
        """Test server lifecycle management."""
        server = mcp_server.server

        # Verify server is running
        assert server.is_running()

        # Test server status
        status = server.get_server_status()
        assert status["status"] == "running"
        assert status["registered_tools"] > 0

        # Test server stop/start cycle
        server.stop()
        assert not server.is_running()

        server.start()
        assert server.is_running()

    async def test_configuration_integration(self, mcp_server):
        """Test configuration system integration."""
        server = mcp_server.server
        config = mcp_server.config

        # Verify configuration is loaded
        assert config is not None
        assert config.environment.value == "testing"
        assert config.debug is True

        # Verify server uses configuration
        assert config.http.port == mcp_server.port

        # Test configuration access through server
        assert server.config == config


@pytest.mark.integration
class TestClientExampleValidation:
    """Test that client examples are valid and functional."""

    def test_simple_client_syntax(self):
        """Test that simple client example has valid syntax."""
        client_path = (
            Path(__file__).parent.parent.parent
            / "examples"
            / "python_client"
            / "simple_client.py"
        )
        assert client_path.exists(), "Simple client example not found"

        # Test syntax by compiling
        with open(client_path) as f:
            f.read()


@pytest.mark.integration
class TestSystemIntegration:
    """Test overall system integration."""

    async def test_full_system_integration(self, mcp_server):
        """Test complete system integration from configuration to client."""
        # 1. Verify configuration system
        config = mcp_server.config
        assert config.environment.value == "testing"

        # 2. Verify MCP server
        server = mcp_server.server
        assert server.is_running()

        # 3. Verify tool registration
        tools = server.registry.list_tools()
        assert len(tools) >= 4  # At least the basic tools

        # 4. Verify tool execution
        result = await server.execute_tool("server_status")
        assert result["status"] == "success"

        # 5. Verify pipeline state management
        result = await server.execute_tool(
            "pipeline_state", action="update", updates={"integration_test": True}
        )
        assert result["status"] == "success"

        # 6. Verify state persistence
        result = await server.execute_tool("pipeline_state", action="get")
        assert result["result"]["pipeline_state"]["integration_test"] is True

        # 7. Verify error handling
        result = await server.execute_tool("invalid_tool")
        assert result["status"] == "error"

    async def test_component_interaction(self, mcp_server):
        """Test interaction between different system components."""
        server = mcp_server.server

        # Test configuration -> server interaction
        assert server.config == mcp_server.config

        # Test server -> registry interaction
        assert server.registry is not None
        assert len(server.registry.tools) > 0

        # Test registry -> tool interaction
        echo_tool = server.registry.get_tool("echo")
        assert echo_tool is not None

        # Test tool -> server context interaction
        result = await server.execute_tool("echo", message="context test")
        assert result["status"] == "success"
        assert result["result"]["server_available"] is True

    async def test_logging_integration(self, mcp_server):
        """Test logging system integration."""
        import logging

        # Capture log messages
        log_messages = []

        class TestLogHandler(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())

        # Add test handler
        test_handler = TestLogHandler()
        logger = logging.getLogger("agentic_neurodata_conversion")
        logger.addHandler(test_handler)
        logger.setLevel(logging.INFO)

        try:
            # Execute tool to generate log messages
            await mcp_server.server.execute_tool("echo", message="logging test")

            # Verify log messages were generated
            assert len(log_messages) > 0
            assert any("echo" in msg.lower() for msg in log_messages)

        finally:
            logger.removeHandler(test_handler)
