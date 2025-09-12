#!/usr/bin/env python3
"""
Simple HTTP server for MCP tool execution.

This script provides a basic HTTP interface to the MCP server for testing
client examples and integration.

Usage:
    pixi run python scripts/run_http_server.py
    pixi run python scripts/run_http_server.py --port 8001
"""

import argparse
import asyncio
import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agentic_neurodata_conversion.core.config import configure_logging, get_config
from agentic_neurodata_conversion.mcp_server.server import MCPServer
from agentic_neurodata_conversion.mcp_server.tools import basic_tools  # noqa: F401

logger = logging.getLogger(__name__)


class ToolExecutionRequest(BaseModel):
    """Request model for tool execution."""

    parameters: dict[str, Any] = {}


class ToolExecutionResponse(BaseModel):
    """Response model for tool execution."""

    status: str
    result: Optional[dict[str, Any]] = None
    message: Optional[str] = None
    tool: Optional[str] = None
    error_type: Optional[str] = None


class ServerStatusResponse(BaseModel):
    """Response model for server status."""

    status: str
    registered_tools: int
    tool_names: list[str]
    agents: list[str]
    pipeline_state_keys: list[str]
    config_available: bool


class ToolsListResponse(BaseModel):
    """Response model for tools list."""

    tools: dict[str, dict[str, Any]]


class SimpleHTTPServer:
    """
    Simple HTTP server that wraps the MCP server for client testing.
    """

    def __init__(self, port: int = 8000, host: str = "127.0.0.1"):
        """
        Initialize the HTTP server.

        Args:
            port: Port to run the server on
            host: Host to bind the server to
        """
        self.port = port
        self.host = host
        self.app = FastAPI(
            title="Agentic Neurodata Conversion MCP Server",
            description="Simple HTTP interface for MCP server testing",
            version="1.0.0",
        )
        self.mcp_server = None

        # Configure CORS for client testing
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._setup_routes()

    def _setup_routes(self):
        """Set up HTTP routes."""

        @self.app.get("/status", response_model=ServerStatusResponse)
        async def get_status():
            """Get server status."""
            if not self.mcp_server:
                raise HTTPException(
                    status_code=503, detail="MCP server not initialized"
                )

            status = self.mcp_server.get_server_status()
            return ServerStatusResponse(**status)

        @self.app.get("/tools", response_model=ToolsListResponse)
        async def list_tools():
            """List all available tools."""
            if not self.mcp_server:
                raise HTTPException(
                    status_code=503, detail="MCP server not initialized"
                )

            tools = self.mcp_server.registry.list_tools()
            return ToolsListResponse(tools=tools)

        @self.app.post("/tool/{tool_name}", response_model=ToolExecutionResponse)
        async def execute_tool(tool_name: str, request: ToolExecutionRequest):
            """Execute a specific tool."""
            if not self.mcp_server:
                raise HTTPException(
                    status_code=503, detail="MCP server not initialized"
                )

            try:
                result = await self.mcp_server.execute_tool(
                    tool_name, **request.parameters
                )
                return ToolExecutionResponse(**result)
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                raise HTTPException(status_code=500, detail=str(e)) from e

        @self.app.post("/reset")
        async def reset_pipeline():
            """Reset pipeline state."""
            if not self.mcp_server:
                raise HTTPException(
                    status_code=503, detail="MCP server not initialized"
                )

            self.mcp_server.clear_pipeline_state()
            return {"status": "success", "message": "Pipeline state cleared"}

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "mcp_server_running": self.mcp_server.is_running()
                if self.mcp_server
                else False,
            }

    async def start_server(self):
        """Start the HTTP server with MCP server."""
        try:
            # Load configuration
            config = get_config()
            configure_logging(config.logging)

            logger.info("Starting MCP server...")

            # Initialize MCP server
            self.mcp_server = MCPServer(config)
            self.mcp_server.start()

            logger.info(
                f"MCP server started with {len(self.mcp_server.registry.tools)} tools"
            )
            logger.info(
                f"Available tools: {list(self.mcp_server.registry.tools.keys())}"
            )

            # Start HTTP server
            logger.info(f"Starting HTTP server on {self.host}:{self.port}")

            config = uvicorn.Config(
                app=self.app, host=self.host, port=self.port, log_level="info"
            )

            server = uvicorn.Server(config)
            await server.serve()

        except Exception as e:
            logger.error(f"Server startup failed: {e}")
            raise
        finally:
            if self.mcp_server:
                self.mcp_server.stop()
                logger.info("MCP server stopped")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Run simple HTTP server for MCP testing"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to run server on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind server to")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Set up logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create and start server
    server = SimpleHTTPServer(port=args.port, host=args.host)

    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
