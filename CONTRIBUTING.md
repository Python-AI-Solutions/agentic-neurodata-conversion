# Contributing to Agentic Neurodata Converter

Thank you for your interest in contributing to the Agentic Neurodata Converter!
This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Component Guidelines](#component-guidelines)

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to
uphold this code. Please report unacceptable behavior to the project
maintainers.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- [Pixi](https://pixi.sh/) for dependency management
- Git

### Setup Development Environment

1. **Fork and clone the repository:**

   ```bash
   git clone https://github.com/your-username/agentic-neurodata-converter.git
   cd agentic-neurodata-converter
   ```

2. **Install dependencies:**

   ```bash
   pixi install
   ```

3. **Set up pre-commit hooks:**

   ```bash
   pixi run setup-hooks
   ```

4. **Verify installation:**
   ```bash
   pixi run pytest tests/unit/ --no-cov -x
   pixi run pre-commit
   ```

## Development Workflow

### Daily Development

1. **Start with quality checks:**

   ```bash
   pixi run pre-commit
   ```

2. **Run fast tests:**

   ```bash
   pixi run pytest tests/unit/ --no-cov -x
   ```

3. **Make your changes following TDD:**
   - Write failing tests first
   - Implement minimal code to pass tests
   - Refactor while keeping tests green

4. **Before committing:**
   ```bash
   pixi run pre-commit
   pixi run pytest tests/unit/ tests/integration/ -v
   ```

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/your-feature-name` - Feature development
- `bugfix/issue-description` - Bug fixes
- `hotfix/critical-fix` - Critical production fixes

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:

- `feat(mcp-server): add dataset analysis tool`
- `fix(conversion): handle missing metadata gracefully`
- `docs(api): update MCP tool documentation`

## Code Standards

### Code Quality

All code must pass pre-commit checks:

```bash
pixi run pre-commit
```

This includes:

- **Ruff formatting** (88 character line limit)
- **Ruff linting** (import sorting, unused variables, etc.)
- **MyPy type checking**
- **Security checks** (Bandit)
- **Documentation checks**

### Common Patterns

#### Unused Parameters

```python
# ✅ Prefix with underscore
def test_func(_config, items):
    assert len(items) > 0

async def mcp_tool(param: str, _server=None):
    return {"result": param}
```

#### Import Handling

```python
# ✅ Defensive imports
try:
    import optional_dependency
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

# ✅ Critical dependency checks
try:
    import pynwb
except ImportError:
    raise ImportError(
        "pynwb is required for NWB operations. "
        "Install with: pixi add pynwb"
    )
```

#### Error Handling

```python
# ✅ Fail fast with clear messages
if not critical_dependency_available:
    raise MissingDependencyError(
        "Cannot perform operation without critical dependency. "
        "Install with: pixi add dependency-name"
    )
```

### File Organization

- **Never create files in project root**
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- **Scripts**: `scripts/`, `scripts/temp/`, `scripts/debug/`
- **Documentation**: `docs/`

## Testing

### Test Categories

Tests are organized by resource requirements:

```bash
# Fast tests (no external dependencies)
pixi run pytest -m "unit" --no-cov

# Mock LLM tests (deterministic)
pixi run pytest -m "mock_llm" --no-cov

# Integration tests (multiple components)
pixi run pytest -m "integration"

# Performance tests (resource intensive)
pixi run pytest -m "performance"
```

### TDD Methodology

1. **Write failing tests first** - Define expected behavior
2. **Test real interfaces** - Avoid mocking components you're building
3. **Skip until implemented** - Use `pytest.mark.skipif` for missing components
4. **Drive design through tests** - Let test requirements inform design

### Test Structure

```python
# Import real components
try:
    from agentic_neurodata_conversion.module import Component
    COMPONENT_AVAILABLE = True
except ImportError:
    Component = None
    COMPONENT_AVAILABLE = False

# Skip tests until implementation exists
pytestmark = pytest.mark.skipif(
    not COMPONENT_AVAILABLE,
    reason="Component not implemented yet"
)

class TestComponent:
    @pytest.mark.unit
    def test_initialization(self):
        """Test component initialization."""
        component = Component()
        assert component is not None
```

### Test Commands

```bash
# Development workflow
pixi run pytest tests/unit/ --no-cov -x        # Fast feedback
pixi run pytest tests/integration/ -v          # Integration testing
pixi run pytest --cov=agentic_neurodata_conversion  # With coverage

# Debugging
pixi run pytest tests/unit/test_file.py::TestClass::test_method -v -s
pixi run pytest --pdb -x                       # Debug on failure
```

## Documentation

### Code Documentation

- **Docstrings**: All public functions, classes, and modules
- **Type hints**: Required for all function signatures
- **Comments**: Explain complex logic and business rules

### API Documentation

- **MCP Tools**: Document parameters, return values, and examples
- **Agent Interfaces**: Document expected behavior and usage patterns
- **Configuration**: Document all settings and their effects

### Examples

- **Client examples**: Keep `examples/` directory current
- **Integration patterns**: Show real-world usage
- **Configuration examples**: Demonstrate different setups

## Submitting Changes

### Pull Request Process

1. **Create feature branch:**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes following TDD:**
   - Write tests first
   - Implement minimal code
   - Ensure all tests pass

3. **Run quality checks:**

   ```bash
   pixi run pre-commit
   pixi run pytest tests/unit/ tests/integration/
   ```

4. **Update documentation:**
   - Add/update docstrings
   - Update README if needed
   - Add examples if applicable

5. **Create pull request:**
   - Use the PR template
   - Link related issues
   - Provide clear description

### PR Requirements

- [ ] All tests pass
- [ ] Pre-commit checks pass
- [ ] Documentation updated
- [ ] Examples added/updated if needed
- [ ] Breaking changes documented

### Review Process

1. **Automated checks** run on all PRs
2. **Code review** by maintainers
3. **Testing** in CI environment
4. **Approval** required before merge

## Component Guidelines

### MCP Server Development

- **Tool registration**: Use `@mcp.tool` decorator
- **Error handling**: Return structured error responses
- **State management**: Update pipeline state appropriately
- **Documentation**: Include parameter descriptions and examples

### Agent Development

- **Base class**: Inherit from `BaseAgent`
- **Async methods**: Use async/await for I/O operations
- **Error propagation**: Let errors bubble up with context
- **Configuration**: Accept config in constructor

### Interface Development

- **Defensive programming**: Check dependencies at initialization
- **Clear errors**: Provide installation instructions
- **Graceful degradation**: Only for truly optional features
- **Type safety**: Use proper type hints

### Testing Components

- **Real interfaces**: Test actual implementations
- **Mock external services**: Use mocks for external APIs
- **Deterministic tests**: Ensure tests are repeatable
- **Resource management**: Clean up after tests

## Getting Help

- **Documentation**: Check `docs/` directory
- **Examples**: Look at `examples/` directory
- **Issues**: Search existing issues first
- **Discussions**: Use GitHub Discussions for questions
- **Community**: Join CatalystNeuro community

## Recognition

Contributors are recognized in:

- `CONTRIBUTORS.md` file
- Release notes
- Project documentation

Thank you for contributing to the Agentic Neurodata Converter!
