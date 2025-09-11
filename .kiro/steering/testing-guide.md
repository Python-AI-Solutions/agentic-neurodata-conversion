---
inclusion: always
---

# Testing Guide

## TDD Methodology

### Core Principles

1. **Write failing tests first** - Define expected behavior before
   implementation
2. **Test real interfaces** - Avoid mocking actual components you're building
3. **Fail fast when missing** - Let tests fail clearly when components don't
   exist to provide immediate feedback
4. **Drive design through tests** - Let test requirements inform component
   design

### Implementation Pattern

```python
# Import real components - fail fast if not implemented
from agentic_neurodata_conversion.module import ComponentClass

class TestComponentClass:
    def test_expected_behavior(self, component_fixture):
        # Test will fail clearly if ComponentClass is not implemented
        # This provides immediate feedback about missing dependencies
        result = component_fixture.some_method()
        assert result.status == "success"
```

### Defensive Testing Approach

**✅ CORRECT - Fail Fast Testing**
```python
# Direct imports that fail immediately with clear error messages
from agentic_neurodata_conversion.core.service import ConversionService
from agentic_neurodata_conversion.evaluation.quality import QualityAssessment

class TestConversionService:
    def test_conversion_workflow(self):
        # Test fails immediately if dependencies are missing
        service = ConversionService()
        result = service.convert_data("test.nwb")
        assert result.success
```

**❌ WRONG - Graceful Degradation in Tests**
```python
# Don't do this - hides real dependency issues
try:
    from agentic_neurodata_conversion.module import ComponentClass
    AVAILABLE = True
except ImportError:
    ComponentClass = None
    AVAILABLE = False

@pytest.mark.skipif(not AVAILABLE, reason="Component not available")
def test_component():
    # This silently skips tests and hides missing dependencies
    pass
```

## Test Categories by Resource Cost

### 1. Unit Tests (`@pytest.mark.unit`)

- **No external dependencies** - Pure function testing, data validation
- **Priority**: Highest (run always, run first)
- **Default Command**: `pixi run test-unit` (quiet output)
- **Debug Command**: `pixi run test-verbose -m "unit"`

### 2. Mock LLM Tests (`@pytest.mark.mock_llm`)

- **Mocked LLM responses** - Deterministic agent workflow testing
- **Priority**: High (fast, reliable)
- **Default Command**: `pixi run pytest -m "mock_llm" -q --no-cov`
- **Debug Command**: `pixi run test-verbose -m "mock_llm"`

### 3. Integration Tests (`@pytest.mark.integration`)

- **Multiple components** - Real component coordination
- **Priority**: Medium-High
- **Default Command**: `pixi run test-integration` (quiet output)
- **Debug Command**: `pixi run test-verbose -m "integration"`

### 4. Performance Tests (`@pytest.mark.performance`)

- **Resource intensive** - Benchmarks, memory usage
- **Priority**: Medium-Low
- **Default Command**: `pixi run pytest -m "performance" -q --no-cov`
- **Debug Command**: `pixi run test-detailed -m "performance"`

### 5. Model Tests (Local)

- **Small models** (`@pytest.mark.small_model`) - <3B parameters
- **Large models** (`@pytest.mark.large_model_minimal`) - 7B parameters, minimal
  context
- **Extended tests** (`@pytest.mark.large_model_extended`) - Full context
- **Priority**: Low (resource intensive)

### 6. API Tests (External)

- **Cheap APIs** (`@pytest.mark.cheap_api`) - Inexpensive cloud models
- **Frontier APIs** (`@pytest.mark.frontier_api`) - Latest/expensive models
- **Priority**: Lowest (external dependency, cost)

## Quick Commands

### Development Workflow (Minimal Output by Default)

```bash
# Fast development cycle - quiet by default
pixi run test-unit                                  # Unit tests, minimal output
pixi run test-fast                                  # Fast tests, minimal output

# Before committing
pixi run pre-commit                                 # Quality checks first
pixi run test -m "unit or integration"              # Relevant tests, minimal output

# CI/CD pipeline - optimized for automated processing
pixi run test-ci                                    # CI-friendly minimal output
```

### Verbose Commands for Debugging

```bash
# When you need detailed output for debugging
pixi run test-verbose                               # Standard verbose output
pixi run test-debug                                 # Full verbosity with pdb integration
pixi run test-detailed                              # Maximum verbosity (-vv)

# Single test debugging
pixi run pytest tests/unit/test_file.py::TestClass::test_method -v --no-cov

# Interactive debugging on first failure
pixi run test-debug -x                              # Stop on first failure with pdb

# See what tests would run (minimal output)
pixi run pytest -m "unit" --collect-only -q
```

### Specialized Minimal Commands for Agents

```bash
# Ultra-minimal output for automated agents
pixi run test-summary                               # Absolute minimal output
pixi run test-agent                                 # Agent-optimized output format
```

### Coverage & Reporting

```bash
# With coverage (slower) - quiet by default
pixi run test-cov                                   # Coverage with minimal output
pixi run test-cov-unit                              # Unit test coverage only

# HTML coverage report with verbose output for debugging
pixi run pytest -m "unit" --cov=agentic_neurodata_conversion --cov-report=html -v
```

## Verbosity Control Guide

### When to Use Quiet Mode (Default)

- **Daily development** - Quick feedback on test status
- **CI/CD pipelines** - Minimal log output, faster processing
- **Automated agents** - Token-efficient test result consumption
- **Batch testing** - Running large test suites

### When to Use Verbose Mode

- **Debugging test failures** - Need detailed error information
- **Understanding test behavior** - See what tests are actually doing
- **Investigating performance** - Detailed timing and resource usage
- **Learning the codebase** - Understand test structure and flow

### Verbosity Levels Explained

```bash
# Level 0: Quiet (default) - Summary only
pixi run test                                       # Minimal output, essential info only

# Level 1: Standard verbose - Test names and basic info
pixi run test-verbose                               # -v flag, shows test names

# Level 2: Extra verbose - Detailed test information
pixi run test-detailed                              # -vv flag, maximum detail

# Debug mode: Full diagnostics with interactive debugging
pixi run test-debug                                 # -v -s --tb=long --pdb

# Ultra-minimal: For automated processing
pixi run test-summary                               # --tb=no, absolute minimum
pixi run test-agent                                 # Optimized for agent consumption
```

### Escalating Verbosity During Development

```bash
# Start minimal, escalate as needed
pixi run test-unit                                  # Quick check
pixi run test-verbose -m "unit"                     # If failures need investigation
pixi run test-debug -k "specific_test"              # For deep debugging
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

### Test Execution Tiers (All with Minimal Output)

1. **PR Tests**: `pixi run test-ci -m "unit or mock_llm"` - Fast, minimal output
2. **Nightly Tests**:
   `pixi run test-ci -m "small_model or large_model_minimal"` - Automated
   processing
3. **Weekly Tests**: `pixi run test-ci -m "large_model_extended"` -
   Comprehensive but quiet
4. **Release Tests**: `pixi run test-ci -m "cheap_api"` - Limited external calls
5. **Final Validation**: `pixi run test-ci -m "frontier_api"` - Minimal
   expensive tests

### CI/CD Command Patterns

```bash
# Standard CI pipeline - optimized for log parsing
pixi run test-ci                                    # Line-level tracebacks, no header

# Agent-driven testing - ultra-minimal output
pixi run test-agent                                 # No summaries, essential info only

# Coverage in CI - quiet with reports
pixi run test-cov                                   # Coverage with minimal console output
```

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

## Execution Context Guidelines

### For Developers

```bash
# Daily workflow - start quiet, escalate as needed
pixi run test-fast                                  # Quick sanity check
pixi run test-verbose -k "failing_test"             # Debug specific failures
pixi run test-debug --pdb                           # Interactive debugging session
```

### For Automated Agents

```bash
# Token-efficient commands for AI agents
pixi run test-agent                                 # Ultra-minimal, parseable output
pixi run test-summary                               # Summary only, no noise
pixi run test-ci                                    # CI-friendly format
```

### For CI/CD Systems

```bash
# Optimized for automated processing and log parsing
pixi run test-ci                                    # Consistent, minimal format
pixi run test-cov                                   # Coverage with quiet console output
pixi run test-parallel                              # Fast parallel execution
```

### For Interactive Development

```bash
# When you need to see what's happening
pixi run test-verbose                               # Standard detailed output
pixi run test-detailed                              # Maximum verbosity
pixi run test-debug                                 # Full diagnostics with pdb
```

### Command Selection Decision Tree

1. **Quick check?** → `pixi run test-fast`
2. **Need details?** → `pixi run test-verbose`
3. **Debugging?** → `pixi run test-debug`
4. **CI/CD?** → `pixi run test-ci`
5. **Agent processing?** → `pixi run test-agent`

Remember: **Start with minimal output, escalate verbosity only when needed. Test
real interfaces, skip until implemented, maintain pre-commit compliance.**
