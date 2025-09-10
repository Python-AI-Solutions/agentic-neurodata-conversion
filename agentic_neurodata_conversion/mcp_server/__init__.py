"""
MCP Server module for agentic neurodata conversion.

This module provides the Model Context Protocol (MCP) server implementation
that serves as the primary orchestration layer for the conversion pipeline.
"""

from .server import MCPServer, MCPRegistry, mcp

__all__ = ["MCPServer", "MCPRegistry", "mcp"]