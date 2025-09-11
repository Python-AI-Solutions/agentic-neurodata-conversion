# Integration Patterns

This directory contains advanced integration patterns and examples for the
Agentic Neurodata Conversion MCP Server.

## Available Patterns

### jupyter_notebook.ipynb

Interactive Jupyter notebook demonstrating MCP server integration in a research
environment. Shows how to:

- Set up the client in a notebook environment
- Run interactive analysis workflows
- Visualize results and intermediate steps
- Handle long-running operations with progress indicators

### cli_wrapper.py

Command-line interface wrapper that provides a CLI frontend to the MCP server.
Features:

- Argument parsing for all major operations
- Progress reporting for long operations
- Configuration file support
- Batch processing capabilities

## Usage

### Jupyter Notebook

```bash
# Start MCP server
pixi run server

# Start Jupyter
pixi run jupyter notebook examples/integration_patterns/jupyter_notebook.ipynb
```

### CLI Wrapper

```bash
# Start MCP server
pixi run server

# Use CLI wrapper
pixi run python examples/integration_patterns/cli_wrapper.py --help
pixi run python examples/integration_patterns/cli_wrapper.py analyze /path/to/dataset
pixi run python examples/integration_patterns/cli_wrapper.py convert /path/to/dataset --files-map '{"recording": "data.dat"}'
```

## Integration Guidelines

### For Interactive Environments (Jupyter, IPython)

- Use async/await patterns for non-blocking operations
- Implement progress bars for long-running tasks
- Provide rich output formatting (HTML, plots)
- Handle kernel interrupts gracefully

### For CLI Applications

- Provide comprehensive help and documentation
- Support configuration files for complex setups
- Implement proper exit codes and error messages
- Support batch operations and scripting

### For Web Applications

- Use async HTTP clients for better performance
- Implement proper error handling and user feedback
- Consider WebSocket connections for real-time updates
- Handle authentication and authorization if needed

### For Desktop Applications

- Use threading to avoid blocking the UI
- Provide progress indicators and cancellation
- Handle network connectivity issues gracefully
- Consider offline modes and caching

## Best Practices

1. **Error Handling**: Always handle network errors, timeouts, and server errors
2. **Progress Reporting**: Provide feedback for long-running operations
3. **Configuration**: Support configuration files and environment variables
4. **Logging**: Implement appropriate logging for debugging and monitoring
5. **Testing**: Include tests for integration patterns
6. **Documentation**: Provide clear usage examples and API documentation

## Contributing New Patterns

When adding new integration patterns:

1. Create a new file or directory for the pattern
2. Include comprehensive documentation and examples
3. Add error handling and edge case coverage
4. Test with the actual MCP server
5. Update this README with the new pattern
6. Consider adding tests in the appropriate test directory
