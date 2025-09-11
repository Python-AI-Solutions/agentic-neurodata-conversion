# MCP Server API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication required for development. Production deployments
should implement appropriate authentication mechanisms.

## Endpoints

### Tool Execution

#### Execute Tool

Execute a registered MCP tool with parameters.

```http
POST /tool/{tool_name}
Content-Type: application/json

{
  "param1": "value1",
  "param2": "value2"
}
```

**Response:**

```json
{
  "status": "success",
  "result": {...},
  "execution_time": 1.23,
  "tool": "tool_name"
}
```

**Error Response:**

```json
{
  "status": "error",
  "message": "Error description",
  "tool": "tool_name",
  "error_code": "TOOL_EXECUTION_FAILED"
}
```

### Server Management

#### List Available Tools

Get list of all registered tools with metadata.

```http
GET /tools
```

**Response:**

```json
{
  "tools": {
    "dataset_analysis": {
      "description": "Analyze dataset structure and extract metadata",
      "function": "dataset_analysis",
      "module": "agentic_neurodata_conversion.mcp_server.tools.dataset_analysis"
    }
  }
}
```

#### Server Status

Get server status and pipeline state.

```http
GET /status
```

**Response:**

```json
{
  "status": "running",
  "pipeline_state": {
    "last_analyzed_dataset": "/path/to/dataset",
    "normalized_metadata": {...}
  },
  "registered_tools": 12,
  "agents": ["conversation", "conversion", "evaluation", "knowledge_graph"]
}
```

#### Reset Pipeline

Clear pipeline state and reset server.

```http
POST /reset
```

**Response:**

```json
{
  "status": "reset",
  "message": "Pipeline state cleared"
}
```

## Tool-Specific APIs

### Dataset Analysis

#### Analyze Dataset

```http
POST /tool/dataset_analysis
Content-Type: application/json

{
  "dataset_dir": "/path/to/dataset",
  "use_llm": true
}
```

### Conversion Orchestration

#### Generate Conversion Script

```http
POST /tool/conversion_orchestration
Content-Type: application/json

{
  "normalized_metadata": {...},
  "files_map": {
    "recording": "/path/to/recording.dat"
  },
  "output_nwb_path": "/path/to/output.nwb"
}
```

### Evaluation

#### Evaluate NWB File

```http
POST /tool/evaluate_nwb_file
Content-Type: application/json

{
  "nwb_path": "/path/to/file.nwb",
  "generate_report": true
}
```

## Error Codes

| Code                    | Description                            |
| ----------------------- | -------------------------------------- |
| `TOOL_NOT_FOUND`        | Requested tool is not registered       |
| `TOOL_EXECUTION_FAILED` | Tool execution encountered an error    |
| `INVALID_PARAMETERS`    | Tool parameters are invalid or missing |
| `AGENT_UNAVAILABLE`     | Required agent is not available        |
| `PIPELINE_STATE_ERROR`  | Pipeline state is inconsistent         |

## Rate Limiting

Development server has no rate limiting. Production deployments should implement
appropriate rate limiting based on usage patterns.

## WebSocket API

For real-time communication:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.send(
  JSON.stringify({
    tool: "dataset_analysis",
    params: {
      dataset_dir: "/path/to/dataset",
    },
  }),
);
```
