# Python Client Examples

This directory contains Python client examples for interacting with the Agentic Neurodata Conversion MCP Server.

## Examples

### workflow_example.py
A comprehensive example based on the original workflow.py pattern. Demonstrates the complete pipeline from dataset analysis through NWB conversion and evaluation.

**Usage:**
```bash
# Start MCP server first
pixi run server

# Run the workflow example
pixi run python workflow_example.py
```

### simple_client.py
A minimal example showing basic MCP server interaction patterns. Good starting point for new integrations.

**Usage:**
```bash
# Start MCP server first
pixi run server

# Run the simple client
pixi run python simple_client.py
```

## Client Development Guide

### Basic Pattern

All Python clients follow this basic pattern:

```python
import requests
from typing import Dict, Any, Optional

class MCPClient:
    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_url.rstrip("/")
    
    def _call_tool(self, tool_name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call MCP server tool with error handling."""
        url = f"{self.api_url}/tool/{tool_name}"
        try:
            response = requests.post(url, json=payload or {})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}
```

### Error Handling

Always include proper error handling:

```python
def safe_tool_call(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call tool with comprehensive error handling."""
    try:
        result = self._call_tool(tool_name, payload)
        if result.get("status") == "error":
            print(f"Tool {tool_name} returned error: {result.get('message')}")
        return result
    except Exception as e:
        print(f"Failed to call {tool_name}: {e}")
        return {"status": "error", "message": str(e)}
```

### Pipeline State Management

For multi-step workflows, maintain pipeline state:

```python
class StatefulMCPClient(MCPClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pipeline_state = {}
    
    def analyze_dataset(self, dataset_dir: str) -> Dict[str, Any]:
        result = self._call_tool("dataset_analysis", {"dataset_dir": dataset_dir})
        if result.get("status") == "success":
            self.pipeline_state["normalized_metadata"] = result.get("result", {})
        return result
```

### Available MCP Tools

The MCP server provides these tools (check `/tools` endpoint for current list):

- `dataset_analysis` - Analyze dataset structure and extract metadata
- `conversion_orchestration` - Generate and execute NeuroConv conversion script
- `evaluate_nwb_file` - Evaluate generated NWB file quality
- `generate_knowledge_graph` - Create knowledge graph from NWB data

### Server Status and Debugging

Always check server status and use debugging endpoints:

```python
def check_server_status(self) -> Dict[str, Any]:
    """Check if MCP server is running and get status."""
    try:
        response = requests.get(f"{self.api_url}/status")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Server not reachable: {e}"}

def list_available_tools(self) -> Dict[str, Any]:
    """Get list of available MCP tools."""
    try:
        response = requests.get(f"{self.api_url}/tools")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"tools": {}, "error": str(e)}
```

## Best Practices

1. **Always check server status** before running workflows
2. **Handle errors gracefully** - the server may be down or tools may fail
3. **Use pipeline state** for multi-step workflows
4. **Validate inputs** before sending to server
5. **Log operations** for debugging and monitoring
6. **Test with real data** to ensure robustness

## Troubleshooting

### Server Connection Issues
- Ensure MCP server is running: `pixi run server`
- Check server status: `curl http://127.0.0.1:8000/status`
- Verify port configuration matches client settings

### Tool Execution Failures
- Check tool availability: `curl http://127.0.0.1:8000/tools`
- Validate input parameters match tool requirements
- Check server logs for detailed error messages

### Pipeline State Issues
- Reset pipeline state if needed: `POST /reset`
- Verify each step completes successfully before proceeding
- Save intermediate results for debugging