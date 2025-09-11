#!/usr/bin/env python3
"""
Integration test script for the Agentic Neurodata Conversion system.

This script wires together all components and tests the basic functionality
of the MCP server, agents, configuration, and logging systems.

Usage:
    pixi run python scripts/integration_test.py
"""

import asyncio
import json
import logging
from pathlib import Path
import sys
import tempfile
from typing import Any

# Import core components
from agentic_neurodata_conversion.core.config import (
    ConfigurationManager,
    configure_logging,
)
from agentic_neurodata_conversion.mcp_server.server import MCPServer, mcp
from agentic_neurodata_conversion.mcp_server.tools import basic_tools  # noqa: F401


class IntegrationTester:
    """
    Integration tester that validates all system components work together.
    """

    def __init__(self):
        """Initialize the integration tester."""
        self.config_manager = None
        self.config = None
        self.mcp_server = None
        self.test_results = {}
        self.logger = None

    def setup_logging(self) -> None:
        """Set up logging for integration testing."""
        # Configure basic logging first
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Integration testing started")

    def setup_configuration(self) -> bool:
        """
        Set up and validate configuration system.

        Returns:
            True if configuration setup succeeded, False otherwise.
        """
        try:
            self.logger.info("Setting up configuration system...")

            # Create temporary config for testing
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                test_config = {
                    "environment": "testing",
                    "debug": True,
                    "data_directory": "./temp/test_data",
                    "temp_directory": "./temp/test_temp",
                    "logging": {"level": "DEBUG", "enable_file_logging": False},
                    "http": {"host": "127.0.0.1", "port": 8001},
                    "mcp": {"transport_type": "stdio"},
                    "agents": {"timeout_seconds": 60, "max_retries": 2},
                }
                json.dump(test_config, f, indent=2)
                config_path = f.name

            # Initialize configuration manager
            self.config_manager = ConfigurationManager(config_path)
            self.config = self.config_manager.load_config()

            # Configure logging with the loaded config
            configure_logging(self.config.logging)

            self.logger.info("Configuration system setup completed")
            self.logger.info(f"Environment: {self.config.environment}")
            self.logger.info(f"Debug mode: {self.config.debug}")

            # Clean up temp config file
            Path(config_path).unlink()

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Configuration setup failed: {e}")
            else:
                print(f"Configuration setup failed: {e}")
            return False

    def setup_mcp_server(self) -> bool:
        """
        Set up and initialize MCP server.

        Returns:
            True if MCP server setup succeeded, False otherwise.
        """
        try:
            self.logger.info("Setting up MCP server...")

            # Create MCP server with configuration
            self.mcp_server = MCPServer(self.config)

            # Start the server
            self.mcp_server.start()

            self.logger.info("MCP server setup completed")
            self.logger.info(f"Server running: {self.mcp_server.is_running()}")

            return True

        except Exception as e:
            self.logger.error(f"MCP server setup failed: {e}")
            return False

    def test_tool_registration(self) -> bool:
        """
        Test MCP tool registration system.

        Returns:
            True if tool registration tests passed, False otherwise.
        """
        try:
            self.logger.info("Testing tool registration...")

            # Check that basic tools are registered
            registered_tools = self.mcp_server.registry.list_tools()
            expected_tools = ["server_status", "list_tools", "pipeline_state", "echo"]

            missing_tools = []
            for tool_name in expected_tools:
                if tool_name not in registered_tools:
                    missing_tools.append(tool_name)

            if missing_tools:
                self.logger.error(f"Missing expected tools: {missing_tools}")
                return False

            self.logger.info(f"Found {len(registered_tools)} registered tools")
            self.logger.info(f"Tool names: {list(registered_tools.keys())}")

            # Test dynamic tool registration
            @mcp.tool(
                name="test_integration_tool", description="Test tool for integration"
            )
            async def test_tool(message: str, server=None) -> dict[str, Any]:
                return {"status": "success", "message": f"Test: {message}"}

            # Verify the test tool was registered
            updated_tools = self.mcp_server.registry.list_tools()
            if "test_integration_tool" not in updated_tools:
                self.logger.error("Dynamic tool registration failed")
                return False

            self.logger.info("Tool registration tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Tool registration test failed: {e}")
            return False

    async def test_tool_execution(self) -> bool:
        """
        Test MCP tool execution flow.

        Returns:
            True if tool execution tests passed, False otherwise.
        """
        try:
            self.logger.info("Testing tool execution...")

            # Test 1: Server status tool
            result = await self.mcp_server.execute_tool("server_status")
            if result.get("status") != "success":
                self.logger.error(f"Server status tool failed: {result}")
                return False

            self.logger.info("✓ Server status tool executed successfully")

            # Test 2: Echo tool
            test_message = "Integration test message"
            result = await self.mcp_server.execute_tool(
                "echo", message=test_message, metadata={"test": True}
            )

            if result.get("status") != "success":
                self.logger.error(f"Echo tool failed: {result}")
                return False

            echo_result = result.get("result", {})
            if echo_result.get("echoed_message") != test_message:
                self.logger.error("Echo tool returned incorrect message")
                return False

            self.logger.info("✓ Echo tool executed successfully")

            # Test 3: Pipeline state management
            test_state = {"test_key": "test_value", "integration": True}
            result = await self.mcp_server.execute_tool(
                "pipeline_state", action="update", updates=test_state
            )

            if result.get("status") != "success":
                self.logger.error(f"Pipeline state update failed: {result}")
                return False

            # Verify state was updated
            result = await self.mcp_server.execute_tool("pipeline_state", action="get")
            if result.get("status") != "success":
                self.logger.error(f"Pipeline state get failed: {result}")
                return False

            state = result.get("result", {}).get("pipeline_state", {})
            if state.get("test_key") != "test_value":
                self.logger.error("Pipeline state was not updated correctly")
                return False

            self.logger.info("✓ Pipeline state management executed successfully")

            # Test 4: Error handling
            result = await self.mcp_server.execute_tool("nonexistent_tool")
            if result.get("status") != "error":
                self.logger.error(
                    "Error handling test failed - should have returned error"
                )
                return False

            self.logger.info("✓ Error handling works correctly")

            # Test 5: Dynamic tool execution
            result = await self.mcp_server.execute_tool(
                "test_integration_tool", message="integration test"
            )
            if result.get("status") != "success":
                self.logger.error(f"Dynamic tool execution failed: {result}")
                return False

            self.logger.info("✓ Dynamic tool executed successfully")

            self.logger.info("Tool execution tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Tool execution test failed: {e}")
            return False

    def test_agent_integration(self) -> bool:
        """
        Test agent integration (when agents are available).

        Returns:
            True if agent integration tests passed, False otherwise.
        """
        try:
            self.logger.info("Testing agent integration...")

            # Check if agents are initialized
            agents = self.mcp_server.agents
            if not agents:
                self.logger.warning(
                    "No agents initialized - this is expected during development"
                )
                return True

            self.logger.info(f"Found {len(agents)} agents: {list(agents.keys())}")

            # Test agent status (when available)
            for agent_name, agent in agents.items():
                if hasattr(agent, "get_status"):
                    status = agent.get_status()
                    self.logger.info(
                        f"Agent {agent_name} status: {status.get('status')}"
                    )

            self.logger.info("Agent integration tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Agent integration test failed: {e}")
            return False

    def test_configuration_integration(self) -> bool:
        """
        Test configuration system integration.

        Returns:
            True if configuration integration tests passed, False otherwise.
        """
        try:
            self.logger.info("Testing configuration integration...")

            # Test configuration access
            if not self.config:
                self.logger.error("Configuration not available")
                return False

            # Test nested configuration access
            http_config = self.config.http
            if http_config.host != "127.0.0.1":
                self.logger.error("HTTP configuration not loaded correctly")
                return False

            # Test environment variable override (simulate)
            import os

            original_port = os.environ.get("ANC_HTTP_PORT")
            os.environ["ANC_HTTP_PORT"] = "9999"

            # Reload configuration
            new_config = self.config_manager.reload_config()
            if new_config.http.port != 9999:
                self.logger.error("Environment variable override failed")
                return False

            # Restore original environment
            if original_port:
                os.environ["ANC_HTTP_PORT"] = original_port
            else:
                os.environ.pop("ANC_HTTP_PORT", None)

            self.logger.info("Configuration integration tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Configuration integration test failed: {e}")
            return False

    def test_logging_integration(self) -> bool:
        """
        Test logging system integration.

        Returns:
            True if logging integration tests passed, False otherwise.
        """
        try:
            self.logger.info("Testing logging integration...")

            # Test different log levels
            self.logger.debug("Debug message test")
            self.logger.info("Info message test")
            self.logger.warning("Warning message test")

            # Test logger hierarchy
            component_logger = logging.getLogger("agentic_neurodata_conversion.test")
            component_logger.info("Component logger test")

            # Test that MCP server logging works
            server_logger = logging.getLogger("agentic_neurodata_conversion.mcp_server")
            server_logger.info("MCP server logger test")

            self.logger.info("Logging integration tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Logging integration test failed: {e}")
            return False

    async def run_all_tests(self) -> dict[str, bool]:
        """
        Run all integration tests.

        Returns:
            Dictionary mapping test names to their results.
        """
        self.logger.info("Starting comprehensive integration tests...")

        tests = [
            ("configuration", self.test_configuration_integration),
            ("logging", self.test_logging_integration),
            ("tool_registration", self.test_tool_registration),
            ("tool_execution", self.test_tool_execution),
            ("agent_integration", self.test_agent_integration),
        ]

        results = {}

        for test_name, test_func in tests:
            self.logger.info(f"\n--- Running {test_name} test ---")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                results[test_name] = result
                status = "PASSED" if result else "FAILED"
                self.logger.info(f"{test_name} test: {status}")
            except Exception as e:
                self.logger.error(f"{test_name} test failed with exception: {e}")
                results[test_name] = False

        return results

    def cleanup(self) -> None:
        """Clean up resources after testing."""
        try:
            if self.mcp_server:
                self.mcp_server.stop()
                self.logger.info("MCP server stopped")

            # Clean up test directories
            import shutil

            for dir_path in ["./temp/test_data", "./temp/test_temp"]:
                if Path(dir_path).exists():
                    shutil.rmtree(dir_path)

            self.logger.info("Cleanup completed")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Cleanup failed: {e}")

    async def run_integration_test(self) -> bool:
        """
        Run the complete integration test suite.

        Returns:
            True if all tests passed, False otherwise.
        """
        try:
            # Setup phase
            self.setup_logging()
            self.logger.info("=" * 60)
            self.logger.info("AGENTIC NEURODATA CONVERSION - INTEGRATION TEST")
            self.logger.info("=" * 60)

            if not self.setup_configuration():
                return False

            if not self.setup_mcp_server():
                return False

            # Test phase
            results = await self.run_all_tests()

            # Results phase
            self.logger.info("\n" + "=" * 60)
            self.logger.info("INTEGRATION TEST RESULTS")
            self.logger.info("=" * 60)

            passed_tests = sum(1 for result in results.values() if result)
            total_tests = len(results)

            for test_name, result in results.items():
                status = "✓ PASSED" if result else "✗ FAILED"
                self.logger.info(f"{test_name:20} : {status}")

            self.logger.info("-" * 60)
            self.logger.info(f"TOTAL: {passed_tests}/{total_tests} tests passed")

            success = passed_tests == total_tests
            if success:
                self.logger.info("🎉 ALL INTEGRATION TESTS PASSED!")
            else:
                self.logger.error("❌ SOME INTEGRATION TESTS FAILED")

            return success

        except Exception as e:
            if self.logger:
                self.logger.error(f"Integration test suite failed: {e}")
            else:
                print(f"Integration test suite failed: {e}")
            return False

        finally:
            self.cleanup()


async def main():
    """Main function to run integration tests."""
    tester = IntegrationTester()
    success = await tester.run_integration_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
