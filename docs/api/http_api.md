# HTTP API Reference

Generated on: 2025-09-12T10:29:52.263554

This document describes the HTTP API endpoints provided by the MCP server.

## Base URL

Default: `http://127.0.0.1:8000`

## Authentication

Currently, no authentication is required for local development.

## Endpoints

### GET /status

Get server status and pipeline state.

**Response:**
```json
{
  "status": "running",
  "pipeline_state": {},
  "registered_tools": 5,
  "agents": ["conversation", "conversion", "evaluation", "knowledge_graph"]
}
```

### GET /tools

List all registered MCP tools.

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

### POST /tool/{tool_name}

Execute a specific MCP tool.

**Parameters:**
- `tool_name` (path): Name of the tool to execute

**Request Body:**
```json
{
  "param1": "value1",
  "param2": "value2"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "result": {
    "data": "...",
    "metadata": "..."
  },
  "state_updates": {
    "key": "value"
  }
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Error description",
  "error_type": "ValueError"
}
```

### POST /reset

Reset pipeline state.

**Response:**
```json
{
  "status": "reset",
  "message": "Pipeline state cleared"
}
```

## Error Codes

- `200`: Success
- `404`: Tool not found
- `422`: Invalid parameters
- `500`: Internal server error

## Rate Limiting

Currently no rate limiting is implemented.

## CORS

CORS is enabled for all origins in development mode.
