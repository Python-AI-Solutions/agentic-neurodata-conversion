# Documentation Index

Generated on: 2025-09-12T10:29:52.373212

This is a comprehensive index of all documentation for the agentic neurodata conversion project.

## Quick Start

1. **Setup**: [Development Setup](development/setup.md)
2. **Architecture**: [System Overview](architecture/README.md)
3. **API**: [MCP Tools](api/README.md)
4. **Examples**: [Client Integration](examples/README.md)

## Documentation Structure

- **api/**
  - [API Documentation](api/README.md)
  - [Agents API Reference](api/agents.md)
  - [Configuration Reference](api/configuration.md)
  - [HTTP API Reference](api/http_api.md)
  - [MCP Server API Reference](api/mcp_server.md)
  - [MCP Tools API Reference](api/mcp_tools.md)
- **architecture/**
  - [Architecture Documentation](architecture/README.md)
  - [MCP Server Architecture](architecture/mcp_server.md)
  - [System Architecture Overview](architecture/overview.md)
- **development/**
  - [Development Documentation](development/README.md)
  - [Contributing Guidelines](development/contributing.md)
  - [MCP Tools Development Guide](development/mcp-tools.md)
  - [Development Environment Setup](development/setup.md)
  - [Testing Guidelines](development/testing.md)
  - [Troubleshooting Guide](development/troubleshooting.md)
- **examples/**
  - [Documentation Examples](examples/README.md)
  - [API Usage Examples](examples/api-usage.md)
  - [Client Integration Examples](examples/client-integration.md)
  - [MCP Tool Implementation Examples](examples/mcp-tool-examples.md)
  - [Workflow Examples](examples/workflow-examples.md)
- [Documentation](README.md)
- [CI/CD Setup Complete](ci-cd-setup.md)
- [Defensive Programming and TDD Review](defensive_programming_review.md)
- [Deployment Guide](deployment.md)
- [Fail Fast Imports](fail_fast_imports.md)
- [Secrets Management](secrets-management.md)

## By Category

### Development
- [Setup Guide](development/setup.md) - Environment setup and installation
- [MCP Tools Development](development/mcp-tools.md) - Creating MCP tools and agents
- [Testing Guidelines](development/testing.md) - Testing practices and commands
- [Contributing](development/contributing.md) - Contribution workflow and standards
- [Troubleshooting](development/troubleshooting.md) - Common issues and solutions

### API Reference
- [MCP Tools](api/mcp_tools.md) - All available MCP tools and parameters
- [Agents](api/agents.md) - Internal agent interfaces
- [HTTP API](api/http_api.md) - REST API endpoints
- [Configuration](api/configuration.md) - Configuration options

### Architecture
- [System Overview](architecture/overview.md) - High-level system design
- [MCP Server](architecture/mcp_server.md) - MCP server architecture

### Examples
- [Client Integration](examples/client-integration.md) - Integration patterns
- [MCP Tool Examples](examples/mcp-tool-examples.md) - Tool implementation examples

## External Resources

- [NeuroConv Documentation](https://neuroconv.readthedocs.io/)
- [NWB Format Specification](https://nwb-schema.readthedocs.io/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Pixi Package Manager](https://pixi.sh/)

## Maintenance

### Regenerating Documentation

```bash
# Generate API documentation
pixi run python scripts/generate_api_docs.py

# Build and validate all documentation
pixi run python scripts/build_docs.py
```

### Documentation Standards

- Use clear, descriptive titles
- Include code examples where appropriate
- Keep examples up-to-date with API changes
- Use consistent formatting and structure
- Include cross-references to related documentation
