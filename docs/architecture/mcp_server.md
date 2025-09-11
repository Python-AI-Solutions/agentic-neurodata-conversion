# MCP Server Architecture

## Overview

The MCP (Model Context Protocol) server serves as the central orchestration
layer for the Agentic Neurodata Conversion system. It exposes standardized tool
interfaces and manages internal agent coordination.

## Core Components

### MCPRegistry

Decorator-based tool registration system that enables dynamic tool discovery and
execution.

```python
@mcp.tool(name="dataset_analysis", description="Analyze dataset structure")
async def dataset_analysis(dataset_dir: str, server=None) -> Dict[str, Any]:
    # Tool implementation
    pass
```

### MCPServer

Central server class that coordinates agent interactions and manages pipeline
state.

Key responsibilities:

- Agent lifecycle management
- Tool execution coordination
- Pipeline state persistence
- Error handling and recovery

### Interface Adapters

Multiple interface implementations for different client needs:

- **FastAPI Interface**: RESTful HTTP API for web clients
- **Stdio Interface**: Standard input/output for CLI integration
- **WebSocket Interface**: Real-time communication for interactive clients

## Tool Categories

### Dataset Analysis Tools

- `dataset_analysis`: Extract metadata and analyze dataset structure
- `format_detection`: Identify data formats and file types
- `metadata_normalization`: Standardize metadata across formats

### Conversion Orchestration Tools

- `conversion_orchestration`: Generate and execute conversion scripts
- `script_validation`: Validate generated NeuroConv scripts
- `conversion_monitoring`: Track conversion progress and status

### Workflow Handoff Tools

- `workflow_handoff`: Transfer control between pipeline stages
- `state_management`: Manage pipeline state and context
- `error_recovery`: Handle and recover from pipeline errors

## Agent Integration

The MCP server manages four internal agents:

```python
self.agents = {
    'conversation': ConversationAgent(config),
    'conversion': ConversionAgent(config),
    'evaluation': EvaluationAgent(config),
    'knowledge_graph': KnowledgeGraphAgent(config)
}
```

Each agent is initialized with shared configuration and accessed through the
server context during tool execution.

## State Management

Pipeline state is maintained in-memory with optional persistence:

```python
self.pipeline_state = {
    'last_analyzed_dataset': '/path/to/dataset',
    'normalized_metadata': {...},
    'current_nwb_path': '/path/to/output.nwb',
    'conversion_status': 'completed'
}
```

State updates are triggered by tool execution results and can be queried by
clients.

## Error Handling

Comprehensive error handling at multiple levels:

- Tool-level exception catching and error response formatting
- Agent-level error recovery and fallback mechanisms
- Server-level logging and monitoring integration

## Configuration

Server configuration through pydantic-settings:

```python
class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: List[str] = ["*"]
```

## Deployment Patterns

### Development

- Single-process server with all agents in-memory
- Hot-reload for development iteration
- Debug logging and detailed error reporting

### Production

- Multi-process deployment with agent isolation
- Load balancing across server instances
- Centralized logging and monitoring
- State persistence through external storage
