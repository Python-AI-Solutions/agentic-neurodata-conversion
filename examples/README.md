# Examples Directory

This directory contains client examples and integration patterns for the Agentic Neurodata Conversion MCP Server. These examples demonstrate how to interact with the MCP server from various client environments.

## Directory Structure

- `python_client/` - Python client examples and templates
- `integration_patterns/` - Advanced integration patterns and examples
- `conversion-examples/` - Specific conversion workflow examples
- `sample-datasets/` - Sample datasets for testing and examples

## Quick Start

### Python Client

The simplest way to get started is with the Python client:

```bash
# Start the MCP server (in one terminal)
pixi run server

# Run the basic client example (in another terminal)
cd examples/python_client
pixi run python workflow_example.py
```

### Integration Patterns

For more advanced use cases, see the integration patterns:

- `integration_patterns/jupyter_notebook.ipynb` - Jupyter notebook integration
- `integration_patterns/cli_wrapper.py` - Command-line interface wrapper

## Requirements

All examples require:
- The MCP server to be running (`pixi run server`)
- Python environment set up with pixi (`pixi install`)

## Development

When developing new examples:
1. Follow the patterns established in existing examples
2. Include comprehensive error handling
3. Add documentation and usage instructions
4. Test with the actual MCP server
5. Keep examples current with MCP server API changes

## Support

For questions about these examples or integration patterns, please refer to:
- Project documentation in `docs/`
- MCP server API documentation
- GitHub issues for bug reports and feature requests