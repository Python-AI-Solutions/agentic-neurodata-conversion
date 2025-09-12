# Development Environment Setup

This guide covers setting up the development environment for the agentic neurodata conversion project.

## Prerequisites

- Python 3.9 or higher
- Git
- [Pixi](https://pixi.sh/) package manager

## Quick Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agentic-neurodata-converter
   ```

2. **Install dependencies**
   ```bash
   pixi install
   ```

3. **Set up development hooks**
   ```bash
   pixi run setup-hooks
   ```

4. **Verify installation**
   ```bash
   pixi run pytest -m "unit" --no-cov
   ```

## MCP Server Development

### Starting the MCP Server

```bash
# Development mode
pixi run python scripts/run_mcp_server.py --debug

# Production mode
pixi run python scripts/run_mcp_server.py --host 0.0.0.0 --port 8000
```

### Configuration

The system uses pydantic-settings based configuration with environment variable support:

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration as needed
# Key variables:
# - MCP_SERVER_HOST=127.0.0.1
# - MCP_SERVER_PORT=8000
# - MCP_SERVER_DEBUG=true
```

## Development Workflow

1. **Code Quality Checks**
   ```bash
   pixi run pre-commit run --all-files
   ```

2. **Testing**
   ```bash
   # Fast unit tests
   pixi run pytest -m "unit" --no-cov

   # Integration tests
   pixi run pytest -m "integration"

   # All tests with coverage
   pixi run pytest --cov=agentic_neurodata_conversion
   ```

3. **Formatting and Linting**
   ```bash
   pixi run format
   pixi run lint
   ```

## Project Structure

```
agentic_neurodata_conversion/
├── core/                    # Core functionality and configuration
├── mcp_server/             # MCP server implementation
├── agents/                 # Internal agent implementations
├── interfaces/             # External service interfaces
└── utils/                  # Utility functions
```

## Common Issues

See `troubleshooting.md` for solutions to common development issues.
