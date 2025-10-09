# MCP Protocol Contracts

This directory contains JSON-RPC 2.0 protocol contracts for the MCP client library.

## Overview

The MCP (Model Context Protocol) client communicates with the server using JSON-RPC 2.0 over stdio. All contracts follow the JSON-RPC 2.0 specification.

## JSON-RPC 2.0 Format

### Request Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "method_name",
  "params": {
    // Method-specific parameters
  }
}
```

### Response Format (Success)

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    // Method-specific result
  }
}
```

### Response Format (Error)

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32600,
    "message": "Error message",
    "data": {
      // Optional additional error data
    }
  }
}
```

## Error Codes

JSON-RPC 2.0 standard error codes:

| Code | Message | Meaning |
|------|---------|---------|
| -32700 | Parse error | Invalid JSON was received |
| -32600 | Invalid Request | The JSON sent is not a valid Request object |
| -32601 | Method not found | The method does not exist or is not available |
| -32602 | Invalid params | Invalid method parameter(s) |
| -32603 | Internal error | Internal JSON-RPC error |
| -32000 to -32099 | Server error | Reserved for implementation-defined server-errors |

## Available Methods

### Core Methods

1. **convert** - Convert neuroscience data to NWB format
2. **query_agent** - Query a specific agent
3. **create_session** - Create new conversation session
4. **get_session_history** - Get session message history
5. **health_check** - Check server health
6. **cancel_conversion** - Cancel running conversion

### Streaming Methods

Methods that support streaming responses:

- **convert** (with stream parameter)

Streaming responses use Server-Sent Events format over stdout.

## Contract Files

- `convert.json` - Data conversion contract
- `query_agent.json` - Agent query contract
- `session.json` - Session management contracts
- `health.json` - Health check contract
- `errors.json` - Error response examples

## Contract Testing

Each contract has corresponding test files in `/tests/contract/`:

```
tests/
└── contract/
    ├── test_convert_contract.py
    ├── test_agent_contract.py
    ├── test_session_contract.py
    └── test_health_contract.py
```

Tests verify:
- Request schema compliance
- Response schema compliance
- Error handling
- Edge cases

## Version Negotiation

The client negotiates protocol version during handshake:

```json
{
  "jsonrpc": "2.0",
  "id": "handshake-1",
  "method": "initialize",
  "params": {
    "protocol_version": "1.0",
    "client_info": {
      "name": "neuroconv-client",
      "version": "0.1.0"
    }
  }
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": "handshake-1",
  "result": {
    "protocol_version": "1.0",
    "server_info": {
      "name": "neuroconv-mcp-server",
      "version": "0.1.0"
    },
    "capabilities": {
      "streaming": true,
      "agents": ["orchestrator", "analysis", "conversion", "evaluation"]
    }
  }
}
```
