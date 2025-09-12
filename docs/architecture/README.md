# Architecture Documentation

This directory contains system architecture and design documentation for the
Agentic Neurodata Conversion project.

## Documents

- **`overview.md`** - High-level system architecture and component overview
- **`mcp_server.md`** - MCP server architecture and orchestration patterns
- **`agents.md`** - Internal agent architecture and communication patterns
- **`data_flow.md`** - Data flow and processing pipeline architecture
- **`integration.md`** - External system integration patterns

## Architecture Principles

The system is built around a central MCP (Model Context Protocol) server that
serves as the primary orchestration layer, exposing dataset analysis
capabilities, conversion orchestration tools, and workflow handoff mechanisms.
