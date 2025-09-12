"""MCP adapter layer for agentic neurodata conversion.

This module provides a thin MCP adapter that maps MCP protocol methods to the core
service layer, maintaining clean separation between transport and business logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import EmbeddedResource, ImageContent, Resource, TextContent, Tool

from ..core.config import CoreConfig, get_config
from ..core.service import ConversionService
from ..core.tools import ConversionToolSystem, ToolStatus

# ============================================================================
# MCP Adapter Implementation
# ============================================================================


class MCPAdapter:
    """MCP adapter that bridges MCP protocol to core service layer."""

    def __init__(
        self,
        conversion_service: ConversionService | None = None,
        config: CoreConfig | None = None,
    ):
        """Initialize MCP adapter.

        Args:
            conversion_service: Optional conversion service instance
            config: Optional configuration (uses global config if None)
        """
        self.config = config or get_config()
        self.conversion_service = conversion_service or ConversionService(self.config)
        self.tool_system: ConversionToolSystem | None = None
        self.server = Server("agentic-neurodata-conversion")
        self.logger = logging.getLogger(__name__)

        # Register MCP handlers
        self._register_handlers()

    async def initialize(self) -> None:
        """Initialize the adapter and core services."""
        await self.conversion_service.initialize()
        self.tool_system = ConversionToolSystem(self.conversion_service)
        self.logger.info("MCP adapter initialized successfully")

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available MCP tools."""
            if not self.tool_system:
                return []

            mcp_tools = []
            tools = self.tool_system.registry.list_tools()

            for tool_def in tools:
                # Convert tool parameters to MCP format
                properties = {}
                required = []

                for param in tool_def.parameters:
                    param_schema = {
                        "type": param.type.value,
                        "description": param.description,
                    }

                    if param.enum:
                        param_schema["enum"] = param.enum
                    if param.minimum is not None:
                        param_schema["minimum"] = param.minimum
                    if param.maximum is not None:
                        param_schema["maximum"] = param.maximum
                    if param.pattern:
                        param_schema["pattern"] = param.pattern
                    if param.default is not None:
                        param_schema["default"] = param.default

                    properties[param.name] = param_schema

                    if param.required:
                        required.append(param.name)

                # Create MCP tool definition
                mcp_tool = Tool(
                    name=tool_def.name,
                    description=tool_def.description,
                    inputSchema={
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                )

                mcp_tools.append(mcp_tool)

            self.logger.info(f"Listed {len(mcp_tools)} MCP tools")
            return mcp_tools

        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: dict[str, Any]
        ) -> list[TextContent | ImageContent | EmbeddedResource]:
            """Execute an MCP tool."""
            if not self.tool_system:
                raise RuntimeError("Tool system not initialized")

            try:
                # Execute tool through tool system
                execution = await self.tool_system.executor.execute_tool(
                    name, arguments
                )

                # Format result for MCP
                if execution.status == ToolStatus.COMPLETED:
                    result_text = json.dumps(execution.result, indent=2, default=str)
                    return [TextContent(type="text", text=result_text)]
                else:
                    error_info = {
                        "status": execution.status.value,
                        "error": execution.error,
                        "execution_time": execution.execution_time,
                        "warnings": execution.warnings,
                    }
                    error_text = json.dumps(error_info, indent=2, default=str)
                    return [TextContent(type="text", text=error_text)]

            except Exception as e:
                self.logger.error(f"Tool execution failed: {e}")
                error_result = {
                    "status": "failed",
                    "error": str(e),
                    "tool_name": name,
                    "arguments": arguments,
                }
                error_text = json.dumps(error_result, indent=2, default=str)
                return [TextContent(type="text", text=error_text)]

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available MCP resources."""
            resources = []

            # Add conversion session resources
            if self.conversion_service:
                # Get active sessions from workflow orchestrator
                active_sessions = list(
                    self.conversion_service.workflow_orchestrator.active_sessions.keys()
                )

                for session_id in active_sessions:
                    resources.append(
                        Resource(
                            uri=f"session://{session_id}",
                            name=f"Conversion Session {session_id}",
                            description=f"Status and results for conversion session {session_id}",
                            mimeType="application/json",
                        )
                    )

            # Add agent status resources
            resources.append(
                Resource(
                    uri="agents://status",
                    name="Agent Status",
                    description="Current status of all conversion agents",
                    mimeType="application/json",
                )
            )

            # Add tool metrics resources
            resources.append(
                Resource(
                    uri="tools://metrics",
                    name="Tool Metrics",
                    description="Performance metrics for all registered tools",
                    mimeType="application/json",
                )
            )

            self.logger.info(f"Listed {len(resources)} MCP resources")
            return resources

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read an MCP resource."""
            if not self.conversion_service:
                raise RuntimeError("Conversion service not initialized")

            try:
                if uri.startswith("session://"):
                    # Read session status
                    session_id = uri.replace("session://", "")
                    session_status = await self.conversion_service.get_session_status(
                        session_id
                    )

                    if session_status is None:
                        raise ValueError(f"Session not found: {session_id}")

                    return json.dumps(session_status, indent=2, default=str)

                elif uri == "agents://status":
                    # Read agent status
                    agent_status = await self.conversion_service.get_agent_status()
                    return json.dumps(agent_status, indent=2, default=str)

                elif uri == "tools://metrics":
                    # Read tool metrics
                    if self.tool_system:
                        metrics = self.tool_system.registry.get_all_metrics()
                        metrics_data = {
                            name: {
                                "total_executions": m.total_executions,
                                "success_rate": m.success_rate,
                                "failure_rate": m.failure_rate,
                                "average_execution_time": m.average_execution_time,
                                "min_execution_time": m.min_execution_time,
                                "max_execution_time": m.max_execution_time,
                                "last_execution": (
                                    m.last_execution.isoformat()
                                    if m.last_execution
                                    else None
                                ),
                            }
                            for name, m in metrics.items()
                        }
                        return json.dumps(metrics_data, indent=2, default=str)
                    else:
                        return json.dumps({"error": "Tool system not initialized"})

                else:
                    raise ValueError(f"Unknown resource URI: {uri}")

            except Exception as e:
                self.logger.error(f"Resource read failed: {e}")
                error_result = {"error": str(e), "uri": uri}
                return json.dumps(error_result, indent=2, default=str)

    async def run_stdio(self) -> None:
        """Run MCP server with stdio transport."""
        await self.initialize()

        self.logger.info("Starting MCP server with stdio transport")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )

    async def shutdown(self) -> None:
        """Shutdown the adapter and core services."""
        if self.conversion_service:
            await self.conversion_service.shutdown()
        self.logger.info("MCP adapter shutdown complete")


# ============================================================================
# MCP Server Entry Point
# ============================================================================


async def main():
    """Main entry point for MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],  # MCP uses stderr for logging
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Agentic Neurodata Conversion MCP Server")

    adapter = MCPAdapter()

    try:
        await adapter.run_stdio()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await adapter.shutdown()
        logger.info("MCP server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
