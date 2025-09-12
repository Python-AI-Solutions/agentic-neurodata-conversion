# MCP Tools Development Guide

This guide explains how to develop MCP tools and agents for the agentic neurodata conversion system.

## MCP Server Architecture

The MCP server serves as the central orchestration layer that:
- Exposes dataset analysis capabilities
- Provides conversion orchestration tools
- Manages workflow handoff mechanisms
- Delegates tasks to internal agent modules

## Creating MCP Tools

### Tool Registration

Use the `@mcp.tool` decorator to register new tools:

```python
from agentic_neurodata_conversion.mcp_server.server import mcp

@mcp.tool(
    name="my_tool",
    description="Description of what the tool does"
)
async def my_tool(param1: str, param2: int = 10, server=None) -> dict:
    """
    Tool implementation.

    Args:
        param1: Required string parameter
        param2: Optional integer parameter with default
        server: MCP server instance (injected automatically)

    Returns:
        Dictionary with status and results
    """
    try:
        # Tool logic here
        result = process_data(param1, param2)

        return {
            'status': 'success',
            'result': result,
            'state_updates': {
                'last_processed': param1
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
```

### Tool Guidelines

1. **Always return structured responses** with `status` field
2. **Handle errors gracefully** and return error information
3. **Use type hints** for parameters
4. **Include docstrings** with parameter descriptions
5. **Update pipeline state** when appropriate using `state_updates`

### Agent Integration

Tools can interact with internal agents through the server instance:

```python
@mcp.tool(name="analyze_with_agent")
async def analyze_with_agent(dataset_path: str, server=None):
    conversation_agent = server.agents['conversation']
    result = await conversation_agent.analyze_dataset(dataset_path)
    return {'status': 'success', 'result': result}
```

## Agent Development

### Base Agent Interface

All agents should inherit from the base agent class:

```python
from agentic_neurodata_conversion.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, config):
        super().__init__(config)
        # Agent-specific initialization

    async def process(self, data):
        # Agent logic
        pass
```

### Agent Registration

Agents are automatically registered in the MCP server during initialization. Add new agents to the server's `_initialize_agents` method.

## Testing MCP Tools

### Unit Testing

```python
import pytest
from agentic_neurodata_conversion.mcp_server.server import MCPServer

@pytest.fixture
def mcp_server():
    from agentic_neurodata_conversion.core.config import Settings
    config = Settings()
    return MCPServer(config)

async def test_my_tool(mcp_server):
    result = await mcp_server.execute_tool("my_tool", param1="test")
    assert result['status'] == 'success'
```

### Integration Testing

Test tools through the FastAPI interface:

```python
from fastapi.testclient import TestClient
from agentic_neurodata_conversion.mcp_server.interfaces.fastapi_interface import create_fastapi_app

def test_tool_via_api():
    app = create_fastapi_app(mcp_server)
    client = TestClient(app)

    response = client.post("/tool/my_tool", json={"param1": "test"})
    assert response.status_code == 200
    assert response.json()['status'] == 'success'
```

## Best Practices

1. **Keep tools focused** - Each tool should have a single responsibility
2. **Use async/await** - All tools should be async for better performance
3. **Validate inputs** - Check parameters before processing
4. **Log operations** - Use structured logging for debugging
5. **Handle timeouts** - Set appropriate timeouts for long-running operations
6. **Document thoroughly** - Include examples in docstrings

## Common Patterns

### Dataset Analysis Tool
```python
@mcp.tool(name="dataset_analysis")
async def dataset_analysis(dataset_dir: str, use_llm: bool = False, server=None):
    # Implementation pattern for dataset analysis
    pass
```

### Conversion Orchestration Tool
```python
@mcp.tool(name="conversion_orchestration")
async def conversion_orchestration(metadata: dict, files_map: dict, server=None):
    # Implementation pattern for conversion orchestration
    pass
```

### Evaluation Tool
```python
@mcp.tool(name="evaluate_nwb_file")
async def evaluate_nwb_file(nwb_path: str, generate_report: bool = True, server=None):
    # Implementation pattern for NWB file evaluation
    pass
```
