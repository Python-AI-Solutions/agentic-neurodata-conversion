---
inclusion: fileMatch
fileMatchPattern: 'test_*.py|*_test.py|conftest.py|tests/*'
---

# Testing Guidelines for Pixi Environment

## Test Execution Rules

### Always Use Pixi for Testing
- **Run all tests**: `pixi run test`
- **Run with coverage**: `pixi run test-cov`
- **Run specific test types**: `pixi run test-unit`, `pixi run test-integration`, `pixi run test-e2e`
- **Run fast tests only**: `pixi run test-fast`
- **Run in parallel**: `pixi run test-parallel`

### Test Development
- **Install test dependencies**: Already included in pixi.toml dev feature
- **Add new test dependencies**: `pixi add --feature test <package>`
- **Run single test file**: `pixi run python -m pytest tests/unit/test_example.py`
- **Run with debugging**: `pixi run python -m pytest tests/ -v -s --tb=long`

### Environment Setup for Tests
```python
# In test files, never assume system Python or manipulate PYTHONPATH
# The pixi environment will be active when tests run via pixi commands

# For subprocess calls in tests, use pixi:
import subprocess

# Wrong - uses system Python
result = subprocess.run(["python", "script.py"])

# Wrong - manipulates PYTHONPATH
import os
os.environ["PYTHONPATH"] = "/some/path"  # ❌ Never do this

# Correct - uses pixi environment
result = subprocess.run(["pixi", "run", "python", "script.py"])

# Correct - trust pixi's dependency management
import agentic_neurodata_conversion  # Works automatically
```

### Test Configuration
- All pytest configuration is in `pyproject.toml`
- Test markers are defined for different test types
- Coverage settings are configured for the pixi environment
- Async test support is enabled

### Test Data and Fixtures
- Use the fixtures in `tests/fixtures/` for consistent test data
- Temporary files and directories are automatically cleaned up
- Mock services are available for external dependencies

### Performance Testing
- Use `pixi run test-benchmark` for performance tests
- Resource monitoring is available through test utilities
- Memory and file handle leak detection is built-in

## Common Test Patterns

### Unit Tests
```python
# tests/unit/test_example.py
import pytest
from unittest.mock import Mock, patch

# Use pixi-installed packages
from agentic_neurodata_conversion.core import SomeClass

@pytest.mark.unit
def test_some_functionality():
    # Test implementation
    pass
```

### Integration Tests
```python
# tests/integration/test_example.py
import pytest

@pytest.mark.integration
async def test_component_integration():
    # Integration test implementation
    pass
```

### End-to-End Tests
```python
# tests/e2e/test_example.py
import pytest

@pytest.mark.e2e
@pytest.mark.requires_datasets
async def test_full_pipeline():
    # E2E test implementation
    pass
```

## Test Markers Usage

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Component integration tests  
- `@pytest.mark.e2e` - End-to-end workflow tests
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.requires_llm` - Tests needing LLM services
- `@pytest.mark.requires_datasets` - Tests needing test datasets
- `@pytest.mark.performance` - Performance/benchmark tests

## Running Specific Test Types

```bash
# Fast tests only (excludes slow, requires_llm, requires_datasets)
pixi run test-fast

# Unit tests only
pixi run test-unit

# Integration tests only  
pixi run test-integration

# E2E tests only
pixi run test-e2e

# All tests with coverage
pixi run test-cov

# Parallel execution
pixi run test-parallel
```

## Debugging Tests

```bash
# Verbose output with full tracebacks
pixi run python -m pytest tests/ -v -s --tb=long

# Stop on first failure
pixi run python -m pytest tests/ -x

# Run specific test
pixi run python -m pytest tests/unit/test_example.py::test_function

# Interactive debugging with pdb
pixi run python -m pytest tests/ --pdb
```

## Test Environment Variables

The test environment automatically sets:
- `AGENTIC_CONVERTER_ENV=test`
- `AGENTIC_CONVERTER_LOG_LEVEL=DEBUG`
- `AGENTIC_CONVERTER_DATABASE_URL=sqlite:///:memory:`
- `AGENTIC_CONVERTER_DISABLE_TELEMETRY=true`
- `AGENTIC_CONVERTER_CACHE_DISABLED=true`

## Dependencies for Testing

All test dependencies are managed in pixi.toml:
- pytest and plugins (asyncio, cov, mock, etc.)
- Test data generators (factory-boy, faker)
- Mock utilities (responses, aioresponses)
- Performance testing (pytest-benchmark)
- Test reporting (pytest-html, pytest-json-report)

Never install test dependencies with pip - they're already included in the pixi environment.