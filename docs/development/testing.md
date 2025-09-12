# Testing Guidelines

This document outlines testing practices and guidelines for the agentic neurodata conversion project.

## Testing Philosophy

We follow Test-Driven Development (TDD) principles:
1. **Write failing tests first** - Define behavior before implementation
2. **Test real interfaces** - Import actual components, fail fast if missing
3. **Drive design through tests** - Let test requirements inform design

## Test Categories

Tests are organized by cost and complexity:

- `@pytest.mark.unit` - No dependencies, highest priority
- `@pytest.mark.mock_llm` - Mocked LLMs, fast
- `@pytest.mark.integration` - Multiple components
- `@pytest.mark.performance` - Resource intensive

## Running Tests

### Quick Commands

```bash
# Fast unit tests (recommended for development)
pixi run pytest -m "unit" --no-cov -x

# All tests with coverage
pixi run pytest --cov=agentic_neurodata_conversion

# Specific test file
pixi run pytest tests/unit/test_mcp_server.py -v

# Tests by name pattern
pixi run pytest -k "test_tool_registration" -v
```

### Test Organization

```
tests/
├── unit/                   # Unit tests (fast, isolated)
├── integration/            # Integration tests (multiple components)
├── e2e/                   # End-to-end tests (full workflows)
└── fixtures/              # Test data and utilities
```

## Writing Tests

### MCP Server Tests

```python
import pytest
from agentic_neurodata_conversion.mcp_server.server import MCPServer, mcp

class TestMCPServer:
    @pytest.mark.unit
    def test_tool_registration(self):
        @mcp.tool(name="test_tool")
        async def test_function():
            return {"status": "success"}

        assert "test_tool" in mcp.tools

    @pytest.mark.integration
    async def test_tool_execution(self, mcp_server):
        result = await mcp_server.execute_tool("test_tool")
        assert result["status"] == "success"
```

### Agent Tests

```python
from agentic_neurodata_conversion.agents.conversation import ConversationAgent

class TestConversationAgent:
    @pytest.mark.unit
    def test_agent_initialization(self, mock_config):
        agent = ConversationAgent(mock_config)
        assert agent.config == mock_config

    @pytest.mark.mock_llm
    async def test_dataset_analysis(self, conversation_agent, mock_llm):
        result = await conversation_agent.analyze_dataset("/test/path")
        assert result is not None
```

### API Tests

```python
from fastapi.testclient import TestClient

def test_tool_endpoint(client: TestClient):
    response = client.post("/tool/dataset_analysis", json={
        "dataset_dir": "/test/path"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

## Test Fixtures

### Common Fixtures

```python
# conftest.py
import pytest
from agentic_neurodata_conversion.core.config import Settings
from agentic_neurodata_conversion.mcp_server.server import MCPServer

@pytest.fixture
def mock_config():
    return Settings(environment="test")

@pytest.fixture
def mcp_server(mock_config):
    return MCPServer(mock_config)

@pytest.fixture
def client(mcp_server):
    from agentic_neurodata_conversion.mcp_server.interfaces.fastapi_interface import create_fastapi_app
    from fastapi.testclient import TestClient

    app = create_fastapi_app(mcp_server)
    return TestClient(app)
```

## Best Practices

### Code Patterns

```python
# ✅ Unused parameters - prefix with underscore
def test_feature(_config, items):
    pass

# ✅ Expected exceptions
with pytest.raises(ValueError, match="Invalid input"):
    component.process_invalid_data(bad_data)

# ✅ Optional imports
try:
    import optional_dependency  # noqa: F401
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

@pytest.mark.skipif(not AVAILABLE, reason="Optional dependency not available")
def test_with_optional_dependency():
    pass
```

### Performance Testing

```python
@pytest.mark.performance
def test_conversion_performance(benchmark):
    result = benchmark(conversion_function, large_dataset)
    assert result.time < 30.0  # seconds
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main/develop branches
- Scheduled runs (nightly)

### CI Configuration

The CI pipeline runs:
1. Code quality checks (ruff, mypy)
2. Unit tests (fast feedback)
3. Integration tests
4. Coverage reporting

## Debugging Tests

### Verbose Output

```bash
# Standard verbose output
pixi run pytest tests/unit/test_file.py -v

# Debug mode with pdb
pixi run pytest tests/unit/test_file.py -v --pdb

# Stop on first failure
pixi run pytest -x
```

### Test Environment

Tests run with these environment variables:
- `AGENTIC_CONVERTER_ENV=test`
- `AGENTIC_CONVERTER_LOG_LEVEL=DEBUG`
- `AGENTIC_CONVERTER_DISABLE_TELEMETRY=true`

## Common Issues

1. **Import errors** - Ensure `pixi install` has been run
2. **Async test failures** - Use `pytest-asyncio` and `async def` for async tests
3. **Fixture scope issues** - Check fixture scopes (function, class, module, session)
4. **Mock configuration** - Ensure mocks are properly configured and reset between tests
