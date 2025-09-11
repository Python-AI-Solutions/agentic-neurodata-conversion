---
inclusion: always
---

# Testing Commands Reference

## Quick Test Execution Commands

### By Resource Requirements (Recommended Order)

```bash
# 1. Unit tests only (fastest, no external dependencies)
pixi run pytest -m "unit" --no-cov

# 2. Unit + Mocked LLM tests (fast, deterministic)
pixi run pytest -m "unit or mock_llm" --no-cov

# 3. Integration tests (moderate speed)
pixi run pytest -m "integration" --no-cov

# 4. Performance tests (resource intensive)
pixi run pytest -m "performance" --no-cov

# 5. Small model tests (requires Ollama with <3B models)
pixi run pytest -m "small_model" --no-cov

# 6. Large model tests (requires significant RAM)
pixi run pytest -m "large_model_minimal" --no-cov
pixi run pytest -m "large_model_extended" --no-cov

# 7. API tests (external dependencies, costs money)
pixi run pytest -m "cheap_api" --no-cov
pixi run pytest -m "frontier_api" --no-cov
```

### Development Workflow

```bash
# During development - run fast tests frequently
pixi run pytest -m "unit" --no-cov -x

# Before committing - run quality checks and tests
pixi run pre-commit                                    # Quality checks first
pixi run pytest -m "unit or integration" --no-cov     # Then tests

# CI/CD pipeline - exclude expensive tests
pixi run pytest -m "not (cheap_api or frontier_api or large_model_extended)" --no-cov

# Full test suite (expensive, use sparingly)
pixi run pytest --no-cov
```

### Pre-commit Integration

```bash
# Essential workflow - run before every commit
pixi run pre-commit

# If pre-commit fails, fix issues and run again
pixi run format      # Fix formatting issues
pixi run lint        # Check remaining linting issues
pixi run pre-commit  # Verify all issues resolved

# Combined quality and testing workflow
pixi run pre-commit && pixi run pytest -m "unit" --no-cov
```

### Specific Test Categories

```bash
# MCP Server tests only
pixi run pytest tests/unit/test_mcp_server.py --no-cov

# Agent tests only
pixi run pytest -m "agents" --no-cov

# Error handling tests
pixi run pytest -k "error" --no-cov

# Async tests only
pixi run pytest -k "async" --no-cov
```

### Test Collection and Debugging

```bash
# See what tests would run without executing
pixi run pytest -m "unit" --collect-only -q

# Run with verbose output
pixi run pytest -m "unit" -v --no-cov

# Run single test method
pixi run pytest tests/unit/test_mcp_server.py::TestToolRegistry::test_tool_registration --no-cov

# Run with debugging on first failure
pixi run pytest -m "unit" --no-cov -x --pdb
```

### Coverage and Reporting

```bash
# Run with coverage (slower)
pixi run pytest -m "unit" --cov=agentic_neurodata_conversion

# Generate HTML coverage report
pixi run pytest -m "unit" --cov=agentic_neurodata_conversion --cov-report=html

# Coverage for specific module
pixi run pytest tests/unit/test_mcp_server.py --cov=agentic_neurodata_conversion.mcp_server
```

## Test Markers Explained

- `@pytest.mark.unit` - Pure functionality tests, no external dependencies
- `@pytest.mark.integration` - Tests that coordinate multiple components
- `@pytest.mark.performance` - Resource-intensive performance tests
- `@pytest.mark.mock_llm` - Tests with mocked LLM responses
- `@pytest.mark.small_model` - Tests with <3B parameter models
- `@pytest.mark.large_model_minimal` - Tests with 7B models, minimal context
- `@pytest.mark.large_model_extended` - Tests with 7B models, full context
- `@pytest.mark.cheap_api` - Tests with inexpensive cloud APIs
- `@pytest.mark.frontier_api` - Tests with expensive frontier models

## TDD Workflow

```bash
# 1. Write failing tests
pixi run pytest tests/unit/test_new_feature.py --no-cov
# Tests should be SKIPPED (not implemented) or FAIL (wrong implementation)

# 2. Implement minimal functionality
# Write just enough code to make tests pass

# 3. Run tests again
pixi run pytest tests/unit/test_new_feature.py --no-cov
# Tests should now PASS

# 4. Refactor and repeat
# Improve implementation while keeping tests passing
```

## Common Patterns

### Skip Tests Until Implementation

```python
pytestmark = pytest.mark.skipif(
    not COMPONENT_AVAILABLE,
    reason="Component not implemented yet"
)
```

### Test Real Components

```python
def test_real_functionality(component_fixture):
    """Test actual component, not mocks."""
    result = component_fixture.real_method()
    assert result.status == "success"
```

### Resource-Appropriate Testing

```python
@pytest.mark.unit
def test_fast_logic():
    """Fast test with no external dependencies."""
    pass

@pytest.mark.integration
def test_component_coordination():
    """Test multiple components working together."""
    pass

@pytest.mark.performance
def test_under_load():
    """Test performance characteristics."""
    pass
```
