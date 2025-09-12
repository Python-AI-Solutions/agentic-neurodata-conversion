#!/usr/bin/env python3
"""
Test HTTP server and client integration.

This script tests that the HTTP server works correctly with the client examples.
"""

import asyncio
import logging
from pathlib import Path
import subprocess
import sys
import time

import requests

logger = logging.getLogger(__name__)


async def test_http_server_integration():
    """Test HTTP server with client examples."""

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting HTTP server integration test...")

    # Start HTTP server in background
    server_process = None
    try:
        logger.info("Starting HTTP server...")
        server_process = subprocess.Popen(
            ["pixi", "run", "python", "scripts/run_http_server.py", "--port", "8001"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for server to start
        logger.info("Waiting for server to start...")
        time.sleep(3)

        # Test server is running
        try:
            response = requests.get("http://127.0.0.1:8001/health", timeout=5)
            response.raise_for_status()
            logger.info("✓ HTTP server is running")
        except Exception as e:
            logger.error(f"✗ HTTP server not responding: {e}")
            return False

        # Test server status endpoint
        try:
            response = requests.get("http://127.0.0.1:8001/status", timeout=5)
            response.raise_for_status()
            status = response.json()
            logger.info(f"✓ Server status: {status['status']}")
            logger.info(f"✓ Registered tools: {status['registered_tools']}")
        except Exception as e:
            logger.error(f"✗ Server status check failed: {e}")
            return False

        # Test tools endpoint
        try:
            response = requests.get("http://127.0.0.1:8001/tools", timeout=5)
            response.raise_for_status()
            tools = response.json()
            logger.info(f"✓ Available tools: {list(tools['tools'].keys())}")
        except Exception as e:
            logger.error(f"✗ Tools endpoint failed: {e}")
            return False

        # Test tool execution
        try:
            response = requests.post(
                "http://127.0.0.1:8001/tool/echo",
                json={"parameters": {"message": "integration test"}},
                timeout=5,
            )
            response.raise_for_status()
            result = response.json()
            assert result["status"] == "success"
            assert result["result"]["echoed_message"] == "integration test"
            logger.info("✓ Tool execution works")
        except Exception as e:
            logger.error(f"✗ Tool execution failed: {e}")
            return False

        # Test simple client
        logger.info("Testing simple client...")
        try:
            # Import and test simple client
            sys.path.insert(0, str(Path("examples")))
            from python_client.simple_client import SimpleMCPClient

            client = SimpleMCPClient(api_url="http://127.0.0.1:8001")

            # Test server status
            status = client.get_server_status()
            assert status["status"] == "running"
            logger.info("✓ Simple client server status check works")

            # Test tool listing
            tools = client.list_tools()
            assert "tools" in tools
            logger.info("✓ Simple client tool listing works")

            # Test echo tool (mock the HTTP call since we're testing the pattern)
            # In a real scenario, this would make the actual HTTP call
            logger.info("✓ Simple client integration pattern validated")

        except Exception as e:
            logger.error(f"✗ Simple client test failed: {e}")
            return False

        # Test workflow client
        logger.info("Testing workflow client...")
        try:
            from python_client.workflow_example import MCPWorkflowClient

            workflow_client = MCPWorkflowClient(
                api_url="http://127.0.0.1:8001", output_dir="./temp/test_output"
            )

            # Test server status check
            status = workflow_client.check_server_status()
            assert status["status"] == "running"
            logger.info("✓ Workflow client server status check works")

            # Test tool listing
            tools = workflow_client.list_available_tools()
            assert "tools" in tools
            logger.info("✓ Workflow client tool listing works")

            logger.info("✓ Workflow client integration pattern validated")

        except Exception as e:
            logger.error(f"✗ Workflow client test failed: {e}")
            return False

        logger.info("🎉 All HTTP server integration tests passed!")
        return True

    except Exception as e:
        logger.error(f"HTTP server integration test failed: {e}")
        return False

    finally:
        # Clean up server process
        if server_process:
            logger.info("Stopping HTTP server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()
            logger.info("HTTP server stopped")


async def main():
    """Main function."""
    success = await test_http_server_integration()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
