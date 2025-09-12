# API Documentation

Generated on: 2025-09-12T10:29:52.264830

This directory contains comprehensive API documentation for the agentic neurodata conversion system.

## Documentation Files

- **[mcp_tools.md](mcp_tools.md)** - MCP tools and their parameters
- **[agents.md](agents.md)** - Internal agent interfaces and methods
- **[http_api.md](http_api.md)** - HTTP API endpoints and responses
- **[configuration.md](configuration.md)** - Configuration options and environment variables

## Quick Reference

### MCP Server
- Default URL: `http://127.0.0.1:8000`
- Status endpoint: `GET /status`
- Tools list: `GET /tools`
- Execute tool: `POST /tool/{tool_name}`

### Key Tools
- `dataset_analysis` - Analyze dataset structure and metadata
- `conversion_orchestration` - Generate and execute NeuroConv scripts
- `evaluate_nwb_file` - Validate and evaluate NWB files

### Configuration
- Environment variables: `AGENTIC_CONVERTER_<SECTION>__<FIELD>`
- Configuration file: `.env` in project root
- Nested structure: server, agents, data, database

## Regenerating Documentation

To regenerate this documentation:

```bash
pixi run python scripts/generate_api_docs.py
```

This will update all API documentation files with the latest information from the codebase.
