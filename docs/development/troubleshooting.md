# Troubleshooting Guide

This guide covers common issues and solutions when developing with the agentic neurodata conversion project.

## Environment Issues

### Pixi Installation Problems

**Problem**: `pixi: command not found`

**Solution**:
```bash
# Install pixi
curl -fsSL https://pixi.sh/install.sh | bash

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.pixi/bin:$PATH"

# Reload shell
source ~/.bashrc  # or ~/.zshrc
```

**Problem**: `pixi install` fails with dependency conflicts

**Solution**:
```bash
# Clear pixi cache
pixi clean

# Remove lock file and reinstall
rm pixi.lock
pixi install

# If still failing, check pixi.toml for conflicting versions
```

### Python Environment Issues

**Problem**: Import errors when running tests or scripts

**Solution**:
```bash
# Always use pixi run, never system Python
pixi run python script.py  # ✅ Correct
python script.py           # ❌ Wrong

# Verify environment
pixi run python -c "import sys; print(sys.executable)"
```

**Problem**: `ModuleNotFoundError` for project modules

**Solution**:
```bash
# Install project in development mode
pixi run pip install -e .

# Or run from project root with proper PYTHONPATH
pixi run python -c "import agentic_neurodata_conversion; print('OK')"
```

## MCP Server Issues

### Server Startup Problems

**Problem**: MCP server fails to start

**Solution**:
```bash
# Check configuration
pixi run python -c "from agentic_neurodata_conversion.core.config import settings; print(settings)"

# Start with debug mode
pixi run python scripts/run_mcp_server.py --debug

# Check port availability
lsof -i :8000  # Check if port 8000 is in use
```

**Problem**: Tools not registering properly

**Solution**:
```python
# Verify tool registration
from agentic_neurodata_conversion.mcp_server.server import mcp
print(mcp.list_tools())

# Check for import errors in tool modules
pixi run python -c "
from agentic_neurodata_conversion.mcp_server.tools import dataset_analysis
print('Tools imported successfully')
"
```

### API Connection Issues

**Problem**: Client cannot connect to MCP server

**Solution**:
```bash
# Check server status
curl http://127.0.0.1:8000/status

# Verify server is running
pixi run python -c "
import requests
try:
    response = requests.get('http://127.0.0.1:8000/status')
    print('Server response:', response.json())
except Exception as e:
    print('Connection error:', e)
"
```

## Testing Issues

### Test Failures

**Problem**: Tests fail with import errors

**Solution**:
```bash
# Ensure all dependencies installed
pixi install

# Run tests with verbose output
pixi run pytest tests/unit/test_file.py -v

# Check test environment
pixi run python -c "
import sys
print('Python path:', sys.path)
print('Python executable:', sys.executable)
"
```

**Problem**: Async test failures

**Solution**:
```python
# Ensure proper async test setup
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None

# Check pytest-asyncio is installed
# Should be in pixi.toml dependencies
```

**Problem**: Mock-related test failures

**Solution**:
```python
# Proper mock usage
from unittest.mock import Mock, patch, AsyncMock

# For async functions
mock_agent = AsyncMock()
mock_agent.analyze_dataset.return_value = {"status": "success"}

# Reset mocks between tests
@pytest.fixture(autouse=True)
def reset_mocks():
    # Reset any global mocks here
    pass
```

### Coverage Issues

**Problem**: Coverage reports missing files

**Solution**:
```bash
# Run coverage with proper source
pixi run pytest --cov=agentic_neurodata_conversion --cov-report=html

# Check coverage configuration in pyproject.toml
[tool.coverage.run]
source = ["agentic_neurodata_conversion"]
```

## Code Quality Issues

### Pre-commit Hook Failures

**Problem**: Pre-commit hooks fail

**Solution**:
```bash
# Install hooks
pixi run setup-hooks

# Run specific hook
pixi run pre-commit run ruff --all-files

# Auto-fix formatting issues
pixi run format

# Check specific file
pixi run ruff check src/file.py
```

**Problem**: Ruff formatting conflicts

**Solution**:
```bash
# Let ruff handle formatting
pixi run ruff format .

# Check for remaining issues
pixi run ruff check .

# Fix specific issues manually based on error messages
```

### Type Checking Issues

**Problem**: MyPy type checking failures

**Solution**:
```bash
# Run type checking
pixi run mypy agentic_neurodata_conversion/

# Common fixes:
# 1. Add type hints
def function(param: str) -> Dict[str, Any]:
    pass

# 2. Use proper imports
from typing import Dict, Any, Optional

# 3. Handle optional types
value: Optional[str] = None
if value is not None:
    # Use value safely
    pass
```

## Performance Issues

### Slow Test Execution

**Problem**: Tests run slowly

**Solution**:
```bash
# Run only fast tests
pixi run pytest -m "unit" --no-cov

# Skip slow tests during development
pixi run pytest -m "not performance"

# Use parallel execution
pixi run pytest -n auto  # If pytest-xdist is available
```

**Problem**: Memory usage issues

**Solution**:
```python
# Use fixtures with appropriate scope
@pytest.fixture(scope="session")  # Expensive setup
def expensive_fixture():
    pass

@pytest.fixture(scope="function")  # Default, cleaned up after each test
def simple_fixture():
    pass

# Clean up resources in tests
def test_with_cleanup():
    resource = create_resource()
    try:
        # Test logic
        pass
    finally:
        resource.cleanup()
```

## Dependency Issues

### Missing Dependencies

**Problem**: Import errors for optional dependencies

**Solution**:
```python
# Proper optional import pattern
try:
    import optional_dependency
    HAS_OPTIONAL = True
except ImportError:
    HAS_OPTIONAL = False

def function_using_optional():
    if not HAS_OPTIONAL:
        raise ImportError(
            "optional_dependency required. Install: pixi add optional_dependency"
        )
    # Use dependency
```

**Problem**: Version conflicts

**Solution**:
```bash
# Check dependency tree
pixi info

# Update specific package
pixi add "package>=1.0.0"

# Check for conflicts in pixi.toml
```

## Docker Issues

### Container Build Problems

**Problem**: Docker build fails

**Solution**:
```bash
# Build with verbose output
docker build --no-cache -t agentic-converter .

# Check Dockerfile syntax
docker build --dry-run .

# Test specific layers
docker build --target <stage-name> .
```

**Problem**: Container runtime issues

**Solution**:
```bash
# Check container logs
docker logs <container-id>

# Run interactively for debugging
docker run -it agentic-converter /bin/bash

# Check environment variables
docker run agentic-converter env
```

## Getting Help

### Debug Information to Collect

When reporting issues, include:

```bash
# System information
pixi info
python --version
uname -a  # On Unix systems

# Project information
pixi run python -c "
import agentic_neurodata_conversion
print('Package location:', agentic_neurodata_conversion.__file__)
"

# Error reproduction
pixi run python -c "
# Minimal code that reproduces the error
"
```

### Log Collection

```bash
# Enable debug logging
export AGENTIC_CONVERTER_LOG_LEVEL=DEBUG

# Run with verbose output
pixi run python script.py --verbose

# Capture logs to file
pixi run python script.py 2>&1 | tee debug.log
```

### Common Commands for Debugging

```bash
# Reset environment
pixi clean && pixi install

# Verify installation
pixi run python -c "import agentic_neurodata_conversion; print('OK')"

# Check configuration
pixi run python -c "
from agentic_neurodata_conversion.core.config import settings
print(settings.model_dump())
"

# Test MCP server
pixi run python -c "
from agentic_neurodata_conversion.mcp_server.server import MCPServer
from agentic_neurodata_conversion.core.config import Settings
server = MCPServer(Settings())
print('Server created successfully')
"
```
