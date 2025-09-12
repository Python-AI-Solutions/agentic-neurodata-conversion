# Testing Infrastructure

This directory contains the comprehensive testing infrastructure for the agentic
neurodata conversion project.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
├── integration/             # Integration tests for component interactions
├── e2e/                     # End-to-end tests for complete workflows
├── fixtures/                # Test fixtures, mock services, and data generators
├── datasets/                # Test dataset management and generation
├── conftest.py              # Global pytest configuration and fixtures
└── README.md                # This file
```

## Test Categories

### Unit Tests (`tests/unit/`)

- **Purpose**: Test individual components in isolation
- **Markers**: `@pytest.mark.unit`
- **Command**: `pixi run pytest tests/unit/ -m unit --no-cov`
- **Coverage**: Core functionality, data validation, pure functions

### Integration Tests (`tests/integration/`)

- **Purpose**: Test component interactions and workflows
- **Markers**: `@pytest.mark.integration`
- **Command**: `pixi run pytest tests/integration/ -m integration --no-cov`
- **Coverage**: MCP server + agents, adapter parity, multi-component workflows

### End-to-End Tests (`tests/e2e/`)

- **Purpose**: Test complete user workflows
- **Markers**: `@pytest.mark.e2e`
- **Command**: `pixi run pytest tests/e2e/ -m e2e --no-cov`
- **Coverage**: Full pipeline execution, client examples

## Test Fixtures (`tests/fixtures/`)

### Data Generators

- **`test_data_generators.py`** - Synthetic neuroscience data generation
- Supports: Open Ephys, SpikeGLX, generic formats
- Creates: Clean, corrupted, minimal, and large datasets

### Mock Services

- **`test_mock_services.py`** - Mock external service implementations
- Includes: LLM clients, NeuroConv, NWB Inspector, DataLad, MCP server
- Purpose: Isolated testing without external dependencies

## Configuration

### Pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Direct functionality tests with no external dependencies",
    "mock_llm: Tests with mocked LLM responses",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "performance: Performance and load tests",
    # ... additional markers
]
```

### Test Markers by Resource Cost

1. **`unit`** - Fastest, no external dependencies
2. **`mock_llm`** - Fast, mocked LLM responses
3. **`integration`** - Medium, real component coordination
4. **`performance`** - Slow, resource intensive
5. **`small_model`** - Local models <3B parameters
6. **`large_model_*`** - Local models 7B+ parameters
7. **`cheap_api`** - Inexpensive cloud APIs
8. **`frontier_api`** - Expensive frontier models

## Available Test Commands

### Basic Commands

- `pixi run test` - Run all tests with coverage (default)
- `pixi run test-quick` - Run all tests without coverage (fast)
- `pixi run test-unit` - Run unit tests only (no coverage)
- `pixi run test-integration` - Run integration tests only (no coverage)
- `pixi run test-e2e` - Run end-to-end tests only (no coverage)

### Specialized Commands

- `pixi run test-fast` - Run fast tests (excludes slow/LLM/dataset tests)
- `pixi run test-slow` - Run slow tests only
- `pixi run test-cov` - Run all tests with detailed coverage reports
- `pixi run test-cov-unit` - Run unit tests with coverage
- `pixi run test-parallel` - Run tests in parallel (faster on multi-core)
- `pixi run test-debug` - Run tests with debugging enabled (--pdb)
- `pixi run test-failed` - Re-run only failed tests from last run
- `pixi run test-benchmark` - Run benchmark tests only

## Quick Commands

### Development Workflow

```bash
# Fast development cycle
pixi run test-quick -x                              # All tests, stop on first failure, no coverage
pixi run test-unit                                  # Unit tests only, no coverage
pixi run test-fast                                  # Fast tests (excludes slow/LLM/dataset tests)

# Before committing
pixi run pre-commit run --all-files                # Quality checks first
pixi run test-unit && pixi run test-integration    # Then relevant tests

# Full test suite with coverage
pixi run test                                       # All tests with coverage
pixi run test-cov                                   # All tests with detailed coverage reports
```

### Debugging & Specific Tests

```bash
# Verbose output
pixi run test-unit -v

# Single test method
pixi run test-quick tests/unit/test_file.py::TestClass::test_method

# Debug on first failure
pixi run test-debug                                 # Includes --pdb and detailed tracebacks

# See what tests would run
pixi run test-quick --collect-only -q
```

### Coverage & Reporting

```bash
# Full coverage report
pixi run test-cov                                   # HTML + terminal + XML coverage reports

# Unit tests with coverage
pixi run test-cov-unit                              # Coverage for unit tests only

# Quick coverage check
pixi run test                                       # Default test command includes coverage
```

## Test Development Guidelines

### TDD Methodology

1. **Write failing tests first** - Define expected behavior before
   implementation
2. **Test real interfaces** - Avoid mocking actual components you're building
3. **Skip until implemented** - Use `pytest.mark.skipif` when components don't
   exist
4. **Drive design through tests** - Let test requirements inform component
   design

### Implementation Pattern

```python
# Import real components
try:
    from agentic_neurodata_conversion.module import ComponentClass
    COMPONENT_AVAILABLE = True
except ImportError:
    ComponentClass = None
    COMPONENT_AVAILABLE = False

# Skip tests until implementation exists
pytestmark = pytest.mark.skipif(
    not COMPONENT_AVAILABLE,
    reason="Component not implemented yet"
)

class TestComponentClass:
    def test_expected_behavior(self, component_fixture):
        # Test will be skipped until ComponentClass is implemented
        result = component_fixture.some_method()
        assert result.status == "success"
```

### Test Quality Standards

- **Pre-commit compliance** - All tests must pass
  `pixi run pre-commit run --all-files`
- **Unused parameters** - Prefix with underscore (`_config`, `_server`)
- **Import handling** - Use try/except with availability flags
- **Error testing** - Test both success and failure scenarios

## Environment Variables

Tests automatically set these environment variables:

- `AGENTIC_CONVERTER_ENV=test`
- `AGENTIC_CONVERTER_LOG_LEVEL=DEBUG`
- `AGENTIC_CONVERTER_DATABASE_URL=sqlite:///:memory:`
- `AGENTIC_CONVERTER_DISABLE_TELEMETRY=true`
- `AGENTIC_CONVERTER_CACHE_DISABLED=true`

## CI/CD Integration

### Test Execution Tiers

1. **PR Tests**: `unit` and `mock_llm` tests
2. **Nightly Tests**: `small_model` and `large_model_minimal` tests
3. **Weekly Tests**: `large_model_extended` tests
4. **Release Tests**: `cheap_api` tests (limited)
5. **Final Validation**: `frontier_api` tests (minimal)

## Dependencies

All test dependencies are managed in `pixi.toml`:

- pytest and plugins (asyncio, cov, mock, etc.)
- Test data generators (factory-boy, faker)
- Mock utilities (responses, aioresponses)
- Performance testing (pytest-benchmark)

## Best Practices

1. **Start with unit tests** - Build confidence in individual components
2. **Test real interfaces** - Don't mock what you're building
3. **Use appropriate markers** - Help with test selection and CI optimization
4. **Follow TDD** - Write tests first, implement second
5. **Maintain pre-commit compliance** - Ensure code quality standards
6. **Use fixtures effectively** - Leverage shared test data and mocks
7. **Test error conditions** - Don't just test the happy path

## Getting Help

- Check existing test files for patterns and examples
- Use `pixi run pytest --collect-only` to see available tests
- Run `pixi run pytest --markers` to see all available markers
- Refer to the steering documentation in `.kiro/steering/` for detailed
  guidelines
