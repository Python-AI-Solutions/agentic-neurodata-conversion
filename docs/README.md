# Documentation

This directory contains comprehensive documentation for the Agentic Neurodata
Conversion project.

## Structure

- **`architecture/`** - System architecture and design documentation
- **`api/`** - API reference documentation for MCP server tools and agents
- **`development/`** - Development guides and contributor documentation
- **`examples/`** - Usage examples and tutorials

## Quick Links

- [Architecture Overview](architecture/overview.md)
- [MCP Server API](api/mcp_server.md)
- [Development Setup](development/setup.md)
- [Getting Started Examples](examples/getting_started.md)

## Building Documentation

```bash
# Generate API documentation
pixi run python scripts/generate_docs.py

# Build documentation site (if using mkdocs/sphinx)
pixi run build-docs

# Serve documentation locally
pixi run serve-docs
```

## Contributing to Documentation

1. Follow the existing structure and templates
2. Update relevant sections when adding new features
3. Include code examples and clear explanations
4. Run documentation builds to verify formatting
5. Keep examples up-to-date with API changes
