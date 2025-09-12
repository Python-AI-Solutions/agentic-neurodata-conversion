---
inclusion: always
---

# Testing Guide

## TDD Principles

1. **Write failing tests first** - Define behavior before implementation
2. **Test real interfaces** - Import actual components, fail fast if missing
3. **Drive design through tests** - Let test requirements inform design

```python
# ✅ Direct imports - fail fast if not implemented
from agentic_neurodata_conversion.module import ComponentClass

class TestComponentClass:
    def test_behavior(self):
        result = ComponentClass().method()
        assert result.status == "success"
```

```python
# ❌ Don't hide missing dependencies
@pytest.mark.skipif(not AVAILABLE, reason="Component not available")
def test_component(): pass  # Silently skips real issues
```

## Test Categories (by cost)

- `@pytest.mark.unit` - No dependencies, highest priority
- `@pytest.mark.mock_llm` - Mocked LLMs, fast
- `@pytest.mark.integration` - Multiple components
- `@pytest.mark.performance` - Resource intensive
- `@pytest.mark.small_model` - <3B parameters
- `@pytest.mark.large_model_minimal` - 7B, minimal context
- `@pytest.mark.large_model_extended` - Full context
- `@pytest.mark.cheap_api` - Inexpensive cloud models
- `@pytest.mark.frontier_api` - Expensive models

## Commands

### Agent-Optimized (Minimal Output)
```bash
pixi run test-agent                    # Ultra-minimal for agents
pixi run test-unit                     # Unit tests only
pixi run test-fast                     # Fast tests
pixi run test-ci                       # CI-friendly
```

### Development
```bash
pixi run test-verbose                  # Standard verbose
pixi run test-debug                    # With pdb
pixi run test-cov                      # With coverage
```

### Specific Tests
```bash
pixi run pytest -m "unit" --no-cov -x              # Fast, stop on failure
pixi run pytest tests/unit/test_file.py -v         # Single file
pixi run pytest -k "test_name" -v                  # By name
```

## Verbosity Levels

- **Quiet (default)**: `pixi run test-agent` - For agents/CI
- **Standard**: `pixi run test-verbose` - Shows test names  
- **Debug**: `pixi run test-debug` - Full diagnostics with pdb
- **Escalate as needed**: Start quiet → verbose → debug

## Code Patterns

```python
# ✅ Unused parameters - prefix with underscore
def test_feature(_config, items): pass
async def tool(param, _server=None): pass

# ✅ Optional imports
try:
    import datalad  # noqa: F401
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

# ✅ Test organization
class TestComponent:
    @pytest.mark.unit
    def test_init(self): pass
    
    @pytest.mark.integration  
    def test_interaction(self): pass
```

## Environment & Patterns

### Test Environment Variables (Auto-set)
- `AGENTIC_CONVERTER_ENV=test`
- `AGENTIC_CONVERTER_LOG_LEVEL=DEBUG`
- `AGENTIC_CONVERTER_DISABLE_TELEMETRY=true`

### Error Handling
```python
# Expected exceptions
with pytest.raises(ValueError, match="Invalid input"):
    component.process_invalid_data(bad_data)

# Performance testing
@pytest.mark.performance
def test_performance(benchmark):
    result = benchmark(component.process, data)
    assert result.time < 5.0
```

### Subprocess in Tests
```python
# ✅ Use pixi environment
subprocess.run(["pixi", "run", "python", "script.py"])

# ❌ Don't use system Python
subprocess.run(["python", "script.py"])
```

## Command Selection
1. **Quick check** → `pixi run test-agent`
2. **Need details** → `pixi run test-verbose` 
3. **Debugging** → `pixi run test-debug`
4. **CI/CD** → `pixi run test-ci`

**Key**: Start minimal, escalate as needed. Test real interfaces, fail fast.
