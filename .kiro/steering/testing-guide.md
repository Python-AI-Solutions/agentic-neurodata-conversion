---
inclusion: always
---

# Testing Guide

## TDD Methodology

### Core Principles
1. **Write failing tests first** - Define expected behavior before implementation
2. **Test real interfaces** - Avoid mocking actual components you're building  
3. **Skip until implemented** - Use `pytest.mark.skipif` when components don't exist
4. **Drive design through tests** - Let test requirements inform component design

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

## Test Categories by Resource Cost

### 1. Unit Tests (`@pytest.mark.unit`)
- **No external dependencies** - Pure function testing, data validation
- **Priority**: Highest (run always, run first)
- **Command**: `pixi run pytest -m "unit" --no-cov`

### 2. Mock LLM Tests (`@pytest.mark.mock_llm`) 
- **Mocked LLM responses** - Deterministic agent workflow testing
- **Priority**: High (fast, reliable)
- **Command**: `pixi run pytest -m "mock_llm" --no-cov`

### 3. Integration Tests (`@pytest.mark.integration`)
- **Multiple components** - Real component coordination
- **Priority**: Medium-High
- **Command**: `pixi run pytest -m "integration" --no-cov`

### 4. Performance Tests (`@pytest.mark.performance`)
- **Resource intensive** - Benchmarks, memory usage
- **Priority**: Medium-Low
- **Command**: `pixi run pytest -m "performance" --no-cov`

### 5. Model Tests (Local)
- **Small models** (`@pytest.mark.small_model`) - <3B parameters
- **Large models** (`@pytest.mark.large_model_minimal`) - 7B parameters, minimal context
- **Extended tests** (`@pytest.mark.large_model_extended`) - Full context
- **Priority**: Low (resource intensive)

### 6. API Tests (External)
- **Cheap APIs** (`@pytest.mark.cheap_api`) - Inexpensive cloud models
- **Frontier APIs** (`@pytest.mark.frontier_api`) - Latest/expensive models  
- **Priority**: Lowest (external dependency, cost)

## Quick Commands

### Development Workflow
```bash
# Fast development cycle
pixi run pytest -m "unit" --no-cov -x              # Unit tests, stop on first failure
pixi run pytest -m "unit or mock_llm" --no-cov     # Fast tests combined

# Before committing
pixi run pre-commit                                 # Quality checks first
pixi run pytest -m "unit or integration" --no-cov  # Then relevant tests

# CI/CD pipeline  
pixi run pytest -m "not (cheap_api or frontier_api or large_model_extended)" --no-cov
```

### Debugging & Specific Tests
```bash
# Verbose output
pixi run pytest -m "unit" -v --no-cov

# Single test method
pixi run pytest tests/unit/test_file.py::TestClass::test_method --no-cov

# Debug on first failure
pixi run pytest -m "unit" --no-cov -x --pdb

# See what tests would run
pixi run pytest -m "unit" --collect-only -q
```

### Coverage & Reporting
```bash
# With coverage (slower)
pixi run pytest -m "unit" --cov=agentic_neurodata_conversion

# HTML coverage report
pixi run pytest -m "unit" --cov=agentic_neurodata_conversion --cov-report=html
```

## Test Quality Standards

### Pre-commit Compliance
```python
# ✅ Prefix unused parameters with underscore
@pytest.mark.unit
def test_feature(_config, items):
    assert len(items) > 0

# ✅ MCP tool functions
async def test_mcp_tool(param1: str, _server=None):
    return {"result": param1}

# ✅ Handle imports with noqa when needed
try:
    import datalad  # noqa: F401
    DATALAD_AVAILABLE = True
except ImportError:
    DATALAD_AVAILABLE = False
```

### Test Organization
```python
class TestComponentName:
    """Test ComponentName functionality with TDD approach."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test component initialization."""
        pass

    @pytest.mark.integration
    def test_component_interaction(self):
        """Test multiple components working together."""
        pass
```

## Pytest Configuration

### Required Markers (pyproject.toml)
```toml
[tool.pytest.ini_options]
markers = [
    "unit: Direct functionality tests with no external dependencies",
    "mock_llm: Tests with mocked LLM responses", 
    "integration: Integration tests",
    "performance: Performance and load tests",
    "small_model: Tests with <3B parameter local models",
    "large_model_minimal: Tests with 7B models, minimal context",
    "large_model_extended: Tests with 7B models, full context", 
    "cheap_api: Tests with inexpensive cloud APIs",
    "frontier_api: Tests with expensive frontier models"
]
```

## CI/CD Strategy

### Test Execution Tiers
1. **PR Tests**: `unit` and `mock_llm` tests
2. **Nightly Tests**: `small_model` and `large_model_minimal` tests  
3. **Weekly Tests**: `large_model_extended` tests
4. **Release Tests**: `cheap_api` tests (limited)
5. **Final Validation**: `frontier_api` tests (minimal)

## Error Handling Patterns

### Expected Exceptions
```python
def test_error_handling(component_instance):
    with pytest.raises(ValueError, match="Invalid input"):
        component_instance.process_invalid_data(bad_data)
```

### Performance Testing
```python
@pytest.mark.performance
def test_processing_performance(benchmark, component_instance):
    result = benchmark(component_instance.process_large_dataset, large_data)
    assert result.processing_time < 5.0
```

## Test Environment

### Automatic Environment Variables
- `AGENTIC_CONVERTER_ENV=test`
- `AGENTIC_CONVERTER_LOG_LEVEL=DEBUG`  
- `AGENTIC_CONVERTER_DATABASE_URL=sqlite:///:memory:`
- `AGENTIC_CONVERTER_DISABLE_TELEMETRY=true`
- `AGENTIC_CONVERTER_CACHE_DISABLED=true`

### Subprocess Calls in Tests
```python
# ❌ Wrong - uses system Python
result = subprocess.run(["python", "script.py"])

# ✅ Correct - uses pixi environment  
result = subprocess.run(["pixi", "run", "python", "script.py"])
```

### Dependencies
All test dependencies managed in pixi.toml - never use pip directly:
- pytest and plugins (asyncio, cov, mock, etc.)
- Test data generators (factory-boy, faker)
- Mock utilities (responses, aioresponses)
- Performance testing (pytest-benchmark)

Remember: **Start with unit tests, test real interfaces, skip until implemented, maintain pre-commit compliance.**