#!/usr/bin/env python3
"""
MCP Server demonstration script.

This script demonstrates the basic functionality of the MCP server
including tool registration, execution, and state management.
"""

import asyncio
import logging

from agentic_neurodata_conversion.mcp_server.server import MCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


async def demonstrate_mcp_server():
    """Demonstrate MCP server functionality."""
    logger.info("=== MCP Server Demonstration ===")

    # Create and start server
    server = MCPServer()
    server.start()
    logger.info("MCP server started")

    try:
        # Show server status
        logger.info("\n--- Server Status ---")
        status_result = await server.execute_tool("server_status")
        if status_result["status"] == "success":
            status = status_result["result"]
            logger.info(f"Server running: {status['status']}")
            logger.info(f"Registered tools: {status['registered_tools']}")
            logger.info(f"Available agents: {status['agents']}")

        # List available tools
        logger.info("\n--- Available Tools ---")
        tools_result = await server.execute_tool("list_tools")
        if tools_result["status"] == "success":
            tools_data = tools_result["result"]
            logger.info(f"Total tools: {tools_data['tool_count']}")
            for tool_name, metadata in tools_data["tools"].items():
                logger.info(f"  - {tool_name}: {metadata['description']}")

        # Demonstrate echo tool
        logger.info("\n--- Echo Tool Demo ---")
        echo_result = await server.execute_tool(
            "echo",
            message="Hello from MCP server!",
            metadata={"demo": True, "timestamp": "2025-09-10"},
        )
        if echo_result["status"] == "success":
            echo_data = echo_result["result"]
            logger.info(f"Echoed message: {echo_data['echoed_message']}")
            logger.info(f"Server available: {echo_data['server_available']}")
            logger.info(f"Metadata: {echo_data.get('metadata', {})}")

        # Demonstrate pipeline state management
        logger.info("\n--- Pipeline State Demo ---")

        # Update state
        update_result = await server.execute_tool(
            "pipeline_state",
            action="update",
            updates={
                "demo_step": "initialization",
                "processed_files": 0,
                "last_update": "2025-09-10T18:00:00Z",
            },
        )
        if update_result["status"] == "success":
            logger.info("Pipeline state updated successfully")

        # Get current state
        get_result = await server.execute_tool("pipeline_state", action="get")
        if get_result["status"] == "success":
            state = get_result["result"]["pipeline_state"]
            logger.info("Current pipeline state:")
            for key, value in state.items():
                logger.info(f"  {key}: {value}")

        # Register and execute a custom tool
        logger.info("\n--- Custom Tool Demo ---")

        @server.registry.tool(
            name="demo_analysis", description="Demonstrate custom tool registration"
        )
        async def demo_analysis_tool(
            dataset_name: str, analysis_type: str = "basic", _server=None
        ):
            """Demo analysis tool."""
            return {
                "status": "success",
                "dataset": dataset_name,
                "analysis_type": analysis_type,
                "result": f"Analyzed {dataset_name} using {analysis_type} analysis",
                "files_processed": 42,
                "state_updates": {"last_analysis": dataset_name, "analysis_count": 1},
            }

        # Execute the custom tool
        analysis_result = await server.execute_tool(
            "demo_analysis",
            dataset_name="sample_dataset.nwb",
            analysis_type="comprehensive",
        )

        if analysis_result["status"] == "success":
            logger.info(f"Analysis result: {analysis_result['result']}")
            logger.info(f"Files processed: {analysis_result['files_processed']}")

        # Show updated state
        final_state_result = await server.execute_tool("pipeline_state", action="get")
        if final_state_result["status"] == "success":
            final_state = final_state_result["result"]["pipeline_state"]
            logger.info("\nFinal pipeline state:")
            for key, value in final_state.items():
                logger.info(f"  {key}: {value}")

        # Clear state
        logger.info("\n--- Cleanup ---")
        clear_result = await server.execute_tool("pipeline_state", action="clear")
        if clear_result["status"] == "success":
            logger.info("Pipeline state cleared")

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)

    finally:
        # Stop server
        server.stop()
        logger.info("MCP server stopped")

    logger.info("=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demonstrate_mcp_server())
