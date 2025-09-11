# Development Workflow Guidelines

## Daily Development Workflow

This document outlines the complete development workflow for the Agentic Neurodata Conversion project, integrating TDD, pre-commit hooks, and quality assurance.

### 1. Setup (One-time)

```bash
# Clone and setup project
git clone <repository-url>
cd agentic-neurodata-conversion

# Install dependencies and setup environment
pixi install

# Install pre-commit hooks
pixi run setup-hooks
```

### 2. Feature Development Workflow

#### Step 1: Write Failing Tests (TDD)
```bash
# Create test file in appropriate directory
# tests/unit/ for unit tests
# tests/integration/ for integration tests
# tests/e2e/ for end-to-end tests

# Write failing tests that define expected behavior
pixi run test-unit  # Should show failing tests (expected)
```

#### Step 2: Check Code Quality Early
```bash
# Run pre-commit to catch style issues early
pixi run pre-commit

# Fix any issues and run again
pixi run pre-commit
```

#### Step 3: Implement Minimal Code
```bash
# Write just enough code to make tests pass
# Follow TDD red-green-refactor cycle

# Run tests to see progress
pixi run test-unit
```

#### Step 4: Refactor and Improve
```bash
# Improve implementation while keeping tests passing
# Run quality checks frequently
pixi run format      # Format code
pixi run lint        # Check linting
pixi run type-check  # Check types
pixi run test-unit   # Ensure tests still pass
```

#### Step 5: Final Quality Check
```bash
# Run comprehensive pre-commit check
pixi run pre-commit

# Run full test suite for affected areas
pixi run test-fast   # Quick tests
pixi run test-unit   # Unit tests
```

### 3. Code Quality Standards

#### Pre-commit Integration
All code must pass pre-commit hooks:
- **Ruff linter**: Comprehensive Python linting
- **Ruff formatter**: Code formatting (88 character line length)
- **Import sorting**: Automatic import organization
- **File quality**: Trailing whitespace, end-of-file fixes
- **Documentation**: YAML/JSON/Markdown formatting
- **Security**: Private key and credential detection

#### Common Quality Patterns

##### Function Arguments
```python
# ✅ GOOD - Prefix unused arguments with underscore
def my_function(used_param: str, _unused_param: int = 42) -> str:
    return used_param

# ✅ GOOD - Test functions with unused parameters
@pytest.mark.unit
def test_feature(_config, items):
    assert len(items) > 0

# ✅ GOOD - MCP tool functions
async def mcp_tool(param1: str, _server=None):
    return {"result": param1}
```

##### Import Handling
```python
# ✅ GOOD - Let ruff handle import sorting automatically
import json
import logging
from pathlib import Path
from typing import Any, Optional

from .types import MyType

# ✅ GOOD - Conditional imports with noqa when needed
try:
    import optional_dependency  # noqa: F401
    DEPENDENCY_AVAILABLE = True
except ImportError:
    DEPENDENCY_AVAILABLE = False
```

##### Line Length and Formatting
```python
# ✅ GOOD - Break long lines appropriately
def long_function_name_that_processes_data(
    input_parameter: str,
    output_parameter: Path,
    configuration_options: Dict[str, Any],
) -> ProcessingResult:
    """Process data with proper line breaks."""
    return ProcessingResult()

# ✅ GOOD - String formatting
message = (
    f"Processing {input_file.name} with configuration "
    f"{config.name} and output to {output_file}"
)
```

### 4. Testing Workflow

#### Test-Driven Development
```bash
# 1. Write failing test
pixi run test-unit  # Should fail (red)

# 2. Write minimal implementation
pixi run test-unit  # Should pass (green)

# 3. Refactor and improve
pixi run test-unit  # Should still pass
pixi run pre-commit # Ensure quality
```

#### Test Categories by Resource Usage
```bash
# Fast tests (run frequently)
pixi run test-unit           # Unit tests only
pixi run test-fast           # Unit + mock tests

# Medium tests (run before commits)
pixi run test-integration    # Integration tests
pixi run test-e2e           # End-to-end tests

# Expensive tests (run sparingly)
pixi run test-benchmark     # Performance tests
# API tests run in CI only
```

#### Test Quality Standards
```python
# ✅ GOOD - Test real components, not mocks
def test_component_functionality(component_instance):
    result = component_instance.process_data(test_data)
    assert result.status == "success"

# ✅ GOOD - Skip tests until implementation exists
pytestmark = pytest.mark.skipif(
    not COMPONENT_AVAILABLE,
    reason="Component not implemented yet"
)

# ✅ GOOD - Proper test markers
@pytest.mark.unit
def test_pure_logic():
    pass

@pytest.mark.integration  
def test_component_interaction():
    pass
```

### 5. Git Workflow Integration

#### Before Committing
```bash
# 1. Run comprehensive checks
pixi run pre-commit

# 2. Run relevant tests
pixi run test-unit
pixi run test-integration  # if applicable

# 3. Commit only if everything passes
git add .
git commit -m "feat: implement feature with tests"
```

#### Commit Message Standards
```bash
# Use conventional commits
git commit -m "feat: add new MCP tool for data processing"
git commit -m "fix: resolve import sorting issue in tests"
git commit -m "test: add unit tests for conversion module"
git commit -m "docs: update development workflow guidelines"
```

### 6. IDE Configuration

#### VS Code Settings
```json
{
  "python.formatting.provider": "ruff",
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [88],
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "python.defaultInterpreterPath": "./.pixi/envs/default/bin/python"
}
```

#### PyCharm Configuration
- Set Python interpreter to `.pixi/envs/default/bin/python`
- Enable "Reformat code" on save
- Set right margin to 88 characters
- Configure pytest as test runner

### 7. Troubleshooting Common Issues

#### Pre-commit Failures
```bash
# If pre-commit fails:
# 1. Read error messages carefully
# 2. Fix issues manually (unused arguments, imports, etc.)
# 3. Run individual tools to debug
pixi run format      # Fix formatting
pixi run lint        # Check specific linting issues
# 4. Run pre-commit again
pixi run pre-commit
```

#### Test Failures
```bash
# If tests fail:
# 1. Run specific test categories
pixi run test-unit -v           # Verbose unit tests
pixi run test-integration -v    # Verbose integration tests

# 2. Run specific test files
pixi run pytest tests/unit/test_specific.py -v

# 3. Debug with pytest options
pixi run pytest tests/unit/test_specific.py::test_function -v -s
```

#### Import Issues
```bash
# If imports fail:
# 1. Ensure pixi environment is active
pixi run python -c "import agentic_neurodata_conversion"

# 2. Check if packages are installed
pixi list | grep package_name

# 3. Reinstall if needed
rm -rf .pixi
pixi install
```

### 8. Performance and Efficiency

#### Fast Development Cycle
```bash
# Quick quality check during development
pixi run format && pixi run lint && pixi run test-unit

# Full quality check before commit
pixi run pre-commit && pixi run test-fast
```

#### Parallel Testing
```bash
# Run tests in parallel for speed
pixi run test-parallel

# Run specific test markers in parallel
pixi run pytest -m "unit" -n auto
```

### 9. Documentation Integration

#### Code Documentation
- Use NumPy style docstrings
- Document all public functions and classes
- Include type hints for all parameters and returns

#### Workflow Documentation
- Update this workflow as processes evolve
- Document new testing patterns
- Share knowledge through steering files

### 10. Continuous Improvement

#### Regular Maintenance
```bash
# Update pre-commit hooks
pixi run pre-commit-update

# Update dependencies
pixi update

# Clean build artifacts
pixi run clean
```

#### Quality Metrics
- Monitor test coverage with `pixi run test-cov`
- Review pre-commit hook effectiveness
- Gather team feedback on workflow efficiency

## Summary

This workflow ensures:
1. **Quality**: Pre-commit hooks catch issues early
2. **Reliability**: TDD ensures robust implementations
3. **Consistency**: Automated formatting and linting
4. **Efficiency**: Fast feedback loops and parallel testing
5. **Maintainability**: Clear patterns and documentation

Remember: The goal is sustainable, high-quality development with minimal friction and maximum confidence in the codebase.