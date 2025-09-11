---
inclusion: always
---

# Testing Methodology and Standards

## Test-Driven Development (TDD) Approach

### Core TDD Principles

**Always follow proper TDD methodology when adding tests:**

1. **Write failing tests first** - Tests should define expected behavior before
   implementation exists
2. **Test real interfaces** - Avoid testing mocks; test the actual components
   you're building
3. **Skip tests until implementation** - Use `pytest.mark.skipif` to skip tests
   when components don't exist yet
4. **Drive design through tests** - Let test requirements inform the design of
   your components

### TDD Implementation Pattern

```python
# Import the actual components that should be implemented
try:
    from agentic_neurodata_conversion.module import (
        ComponentClass,
        AnotherClass
    )
    COMPONENTS_AVAILABLE = True
except ImportError:
    # These should fail until implemented
    ComponentClass = None
    AnotherClass = None
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE,
    reason="Components not implemented yet"
)

class TestComponentClass:
    """Test the actual component functionality."""

    def test_expected_behavior(self, component_fixture):
        """Test that defines expected behavior before implementation."""
        # This test will be skipped until ComponentClass is implemented
        result = component_fixture.some_method()
        assert result.status == "success"
```

### What NOT to Do

❌ **Don't create mock implementations that make tests pass** ❌ **Don't test
mock objects instead of real functionality** ❌ **Don't write tests that pass
without real implementation** ❌ **Don't use extensive mocking to avoid testing
real interfaces**

### What TO Do

✅ **Write tests that expect real component interfaces** ✅ **Use pytest.skipif
to skip tests until implementation exists** ✅ **Define clear expected behavior
through test assertions** ✅ **Let tests drive the design of your components**

## Resource-Based Test Clustering

### Testing Approaches by Resource Requirements

Tests are organized into clusters based on resource requirements and external
dependencies, from lowest to highest cost:

#### 1. Direct Functionality Tests (`@pytest.mark.unit`)

- **No external dependencies**
- Pure function testing
- Data model validation
- Configuration loading
- **Priority**: Highest (run first, run always)

```python
@pytest.mark.unit
def test_data_model_validation():
    """Test data model without external dependencies."""
    pass
```

#### 2. Mocked LLM Tests (`@pytest.mark.mock_llm`)

- Mock LLM responses for deterministic testing
- Agent workflow testing with predictable outputs
- Low maintenance burden
- Based on existing `testing_pipeline_pytest.py` pattern
- **Priority**: High (fast, reliable)

```python
@pytest.mark.mock_llm
def test_agent_workflow_with_mocked_llm(mock_llm_client):
    """Test agent workflow with mocked LLM responses."""
    pass
```

#### 3. Small Local Model Tests (`@pytest.mark.small_model`)

- <3B parameter models (e.g., Ministral 3B, llama3.2:3b, OLMo-2-1B, Gemma 270M)
- Basic agent functionality validation
- Requires local Ollama installation
- **Priority**: Medium-High (reasonable resource usage)

```python
@pytest.mark.small_model
def test_basic_agent_functionality():
    """Test with small local models for basic validation."""
    pass
```

#### 4. Large Local Model Tests (`@pytest.mark.large_model_minimal`)

- 7B parameter models with minimal context
- More complex reasoning tests
- Requires significant RAM
- **Priority**: Medium (higher resource usage)

```python
@pytest.mark.large_model_minimal
def test_complex_reasoning():
    """Test complex reasoning with 7B models."""
    pass
```

#### 5. Large Local Model Extended Tests (`@pytest.mark.large_model_extended`)

- ~7B parameter models with full context (e.g. gpt-oss-20B, NVIDIA Nemotron Nano
  9B V2, Mistral 7B, Gemma 7B)
- End-to-end workflow testing
- Requires high RAM availability
- **Priority**: Medium-Low (resource intensive)

```python
@pytest.mark.large_model_extended
def test_end_to_end_workflow():
    """Test full workflow with large models and full context."""
    pass
```

#### 6. Cheap API Tests (`@pytest.mark.cheap_api`)

- Inexpensive cloud models (gpt-oss-120B (high), GPT-5 mini (medium), Grok 3
  mini Reasoning (high), Gemini 2.5 Flash)
- Integration testing with real APIs
- Rate-limited execution
- **Priority**: Low (external dependency, cost)

```python
@pytest.mark.cheap_api
def test_api_integration():
    """Test integration with inexpensive cloud APIs."""
    pass
```

#### 7. Frontier API Tests (`@pytest.mark.frontier_api`)

- Latest/most expensive models (Claude 4.1 Opus, Claude 4 Sonnet, GPT-5 (high),
  Gemini 2.5 Pro)
- Final validation and benchmarking
- Minimal usage, high confidence tests
- **Priority**: Lowest (expensive, limited usage)

```python
@pytest.mark.frontier_api
def test_frontier_model_validation():
    """Test with frontier models for final validation."""
    pass
```

## Test Organization Structure

### Directory Structure

```
tests/
├── unit/                    # @pytest.mark.unit tests
├── integration/            # Integration tests with mocked dependencies
├── e2e/                    # End-to-end tests with real services
├── performance/            # Performance and load tests
├── fixtures/               # Shared test fixtures
└── conftest.py            # Global pytest configuration
```

### Test File Naming

- `test_*.py` - Standard test files
- `*_test.py` - Alternative test files
- Use descriptive names: `test_mcp_server.py`, `test_conversation_agent.py`

### Test Class Organization

```python
class TestComponentName:
    """Test the ComponentName functionality."""

    def test_initialization(self):
        """Test component initialization."""
        pass

    def test_core_functionality(self):
        """Test core component functionality."""
        pass

    def test_error_handling(self):
        """Test error handling scenarios."""
        pass
```

## Pytest Configuration

### Required Markers in pyproject.toml

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Direct functionality tests with no external dependencies",
    "mock_llm: Tests with mocked LLM responses",
    "small_model: Tests with <3B parameter local models",
    "large_model_minimal: Tests with 7B models, minimal context",
    "large_model_extended: Tests with 7B models, full context",
    "cheap_api: Tests with inexpensive cloud APIs",
    "frontier_api: Tests with expensive frontier models",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "performance: Performance and load tests",
    "requires_llm: Tests that require LLM services",
    "requires_datasets: Tests that require test datasets",
    "slow: Slow-running tests"
]
```

### Test Execution Commands

```bash
# Run only unit tests (fastest)
pixi run pytest -m "unit"

# Run unit and mocked LLM tests
pixi run pytest -m "unit or mock_llm"

# Run all tests except expensive ones
pixi run pytest -m "not (cheap_api or frontier_api)"

# Run small model tests only
pixi run pytest -m "small_model"

# Run performance tests
pixi run pytest -m "performance"

# Run all tests in order of resource requirements
pixi run pytest -m "unit" && \
pixi run pytest -m "mock_llm" && \
pixi run pytest -m "small_model"
```

## Test Implementation Guidelines

### 1. Always Start with Unit Tests

```python
@pytest.mark.unit
class TestDataModel:
    """Test data models without external dependencies."""

    def test_model_validation(self):
        """Test model validation logic."""
        # Test the actual model class, not a mock
        pass
```

### 2. Use Proper Fixtures

```python
@pytest.fixture
def component_instance():
    """Create real component instance for testing."""
    if not COMPONENT_AVAILABLE:
        pytest.skip("Component not implemented")
    return ComponentClass()
```

### 3. Test Real Interfaces

```python
def test_component_method(component_instance):
    """Test actual component method."""
    # Test the real method, not a mock
    result = component_instance.process_data(test_data)
    assert result.status == "success"
    assert len(result.items) > 0
```

### 4. Handle Missing Implementation Gracefully

```python
# At module level
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE,
    reason="Components not implemented yet"
)
```

### 5. Use Appropriate Test Markers

```python
@pytest.mark.unit
def test_pure_function():
    """Test without external dependencies."""
    pass

@pytest.mark.mock_llm
def test_with_mocked_llm():
    """Test with mocked LLM responses."""
    pass

@pytest.mark.small_model
def test_with_local_model():
    """Test with small local model."""
    pass
```

## Error Handling in Tests

### Expected Exceptions

```python
def test_error_handling(component_instance):
    """Test proper error handling."""
    with pytest.raises(ValueError, match="Invalid input"):
        component_instance.process_invalid_data(bad_data)
```

### Graceful Degradation

```python
def test_graceful_degradation(component_instance):
    """Test graceful handling of edge cases."""
    result = component_instance.process_edge_case(edge_data)
    assert result.status == "partial_success"
    assert result.warnings is not None
```

## Performance Testing

### Benchmark Tests

```python
@pytest.mark.performance
def test_processing_performance(benchmark, component_instance):
    """Test processing performance."""
    result = benchmark(component_instance.process_large_dataset, large_data)
    assert result.processing_time < 5.0  # seconds
```

### Memory Usage Tests

```python
@pytest.mark.performance
def test_memory_usage(component_instance):
    """Test memory usage stays within bounds."""
    import psutil
    process = psutil.Process()

    initial_memory = process.memory_info().rss
    component_instance.process_large_dataset(large_data)
    final_memory = process.memory_info().rss

    memory_increase = final_memory - initial_memory
    assert memory_increase < 100 * 1024 * 1024  # 100MB limit
```

## Continuous Integration

### Test Execution Strategy

1. **PR Tests**: Run `unit` and `mock_llm` tests
2. **Nightly Tests**: Run `small_model` and `large_model_minimal` tests
3. **Weekly Tests**: Run `large_model_extended` tests
4. **Release Tests**: Run `cheap_api` tests (limited)
5. **Final Validation**: Run `frontier_api` tests (minimal)

### Resource Management

- Use test timeouts to prevent hanging
- Implement proper cleanup in fixtures
- Monitor resource usage in CI
- Cache model downloads when possible

## Documentation Requirements

### Test Documentation

- Each test class should have a clear docstring
- Each test method should describe what it's testing
- Complex test logic should include inline comments
- Mark resource requirements clearly

### Example Test Documentation

```python
class TestConversationAgent:
    """
    Test the ConversationAgent functionality.

    Tests cover dataset analysis, metadata extraction, and question generation.
    Uses TDD approach - tests define expected behavior before implementation.
    """

    @pytest.mark.unit
    def test_metadata_extraction(self, conversation_agent):
        """
        Test metadata extraction from dataset files.

        Should identify file formats, extract basic metadata, and detect
        missing required fields for NWB conversion.
        """
        pass
```

This methodology ensures consistent, reliable testing across the entire project
while managing resource costs and maintaining TDD principles.
