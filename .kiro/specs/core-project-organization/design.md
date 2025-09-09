# Core Project Organization Design

## Overview

This design document outlines the foundational project structure for the agentic neurodata conversion project, organized around a central MCP (Model Context Protocol) server architecture. The MCP server acts as the orchestration hub, coordinating specialized agents for neuroscience data conversion to NWB format.

The design follows modern Python project patterns while embracing the MCP-centric architecture revealed by the actual implementation in `workflow.py`.

## Architecture

### High-Level Architecture

```
agentic-neurodata-conversion/
├── agentic_neurodata_conversion/    # Main package
│   ├── mcp_server/                  # MCP server implementation (central hub)
│   ├── agents/                      # Agent implementations called by MCP server
│   ├── clients/                     # Client libraries (like workflow.py)
│   ├── core/                        # Shared core functionality
│   └── config/                      # Configuration management
├── tests/                           # Test suite
├── docs/                            # Documentation
├── scripts/                         # Development and deployment scripts
├── examples/                        # Usage examples (including workflow.py)
├── data/                            # Sample data and fixtures
└── deployment/                      # Containerization and deployment
```

### MCP-Centric Architecture Flow

```
Client Libraries (workflow.py) 
    ↓ HTTP/API calls
MCP Server (FastAPI)
    ↓ Direct Python calls
Individual Agents (ConversationAgent, ConversionAgent, EvaluationAgent)
    ↓ Tool usage
External Tools (NeuroConv, NWB Inspector, Knowledge Graphs)
```

### Package Structure

#### 1. MCP Server (`agentic_neurodata_conversion/mcp_server/`)
- **Purpose**: Central orchestration hub that exposes conversion pipeline as MCP tools
- **Current Implementation**: `mcp_server.py` (FastAPI-based)
- **Key Responsibilities**:
  - Expose pipeline steps as HTTP endpoints
  - Coordinate agent interactions
  - Manage conversion state and configuration
  - Handle error propagation and recovery

#### 2. Agents (`agentic_neurodata_conversion/agents/`)
- **Purpose**: Specialized agents called by MCP server
- **Current Implementations**: 
  - `conversationAgent.py` - Dataset analysis and metadata extraction
  - `conversionagent.py` - Conversion script generation and execution
  - `evaluation_agent_final.py` - NWB validation and quality assessment
  - `metadata_questioner.py` - Dynamic metadata questioning
- **Key Responsibilities**:
  - Implement specific conversion tasks
  - Provide clean interfaces for MCP server integration
  - Handle agent-specific error conditions

#### 3. Client Libraries (`agentic_neurodata_conversion/clients/`)
- **Purpose**: Python libraries for interacting with MCP server
- **Current Implementation**: `workflow.py` (to be moved here)
- **Key Responsibilities**:
  - Provide convenient Python API for pipeline usage
  - Handle HTTP communication with MCP server
  - Manage client-side state and error handling

#### 4. Core (`agentic_neurodata_conversion/core/`)
- **Purpose**: Shared functionality used by MCP server and agents
- **Current Implementations**:
  - `format_detector.py` - Data format detection
  - `knowledge_graph.py` - RDF/knowledge graph utilities
- **Key Responsibilities**:
  - Provide common utilities and data structures
  - Define shared interfaces and protocols
  - Handle configuration and logging

## Components and Interfaces

### MCP Server Interface

Based on `workflow.py` usage, the MCP server exposes these key tools:

```python
# MCP Server Tools (HTTP endpoints)
class MCPServer:
    async def initialize_pipeline(self, config: Dict) -> Dict[str, Any]
    async def analyze_dataset(self, dataset_dir: str, use_llm: bool = False) -> Dict[str, Any]
    async def generate_conversion_script(self, normalized_metadata: Dict, files_map: Dict) -> Dict[str, Any]
    async def evaluate_nwb_file(self, nwb_path: str, generate_report: bool = True) -> Dict[str, Any]
    async def generate_knowledge_graph(self, nwb_path: str) -> Dict[str, Any]
    async def get_status(self) -> Dict[str, Any]
```

### Agent Interfaces

Agents are called directly by the MCP server:

```python
# Agent interfaces (called by MCP server)
class ConversationAgent:
    def analyze_dataset(self, dataset_dir: str, out_report_json: Optional[str] = None) -> Dict[str, Any]

class ConversionAgent:
    def synthesize_conversion_script(self, normalized_metadata: Dict, files_map: Dict, output_nwb_path: str) -> str
    def write_generated_script(self, code: str, out_path: str) -> str
    def run_generated_script(self, script_path: str) -> int

class EvaluationAgent:
    def validate_nwb(self, nwb_path: str) -> Dict[str, Any]
    def generate_ttl_and_outputs(self, nwb_path: str, **kwargs) -> Dict[str, Any]
    def write_context_and_report(self, nwb_path: str, eval_results: Dict) -> Dict[str, Any]
```

### Client Library Interface

Based on `workflow.py` implementation:

```python
class MCPPipeline:
    def __init__(self, api_url: str = "http://127.0.0.1:8000", output_dir: str = "test_outputs", use_llm: bool = False)
    def initialize_pipeline(self) -> Dict[str, Any]
    def analyze_dataset(self, dataset_dir: str) -> Dict[str, Any]
    def generate_conversion_script(self, files_map: Dict) -> Dict[str, Any]
    def evaluate_nwb_file(self) -> Dict[str, Any]
    def generate_knowledge_graph(self) -> Dict[str, Any]
    def get_status(self) -> Dict[str, Any]
    def run(self, dataset_dir: str, files_map: Dict) -> Dict[str, Any]  # Full pipeline
```

## Design Patterns

### 1. MCP Server as Facade
- **Pattern**: The MCP server acts as a Facade that simplifies access to complex agent interactions
- **Implementation**: Single HTTP API that coordinates multiple agents internally

### 2. Agent as Strategy
- **Pattern**: Different agents implement different strategies for their domain (conversation, conversion, evaluation)
- **Implementation**: Agents are swappable implementations called by MCP server

### 3. Client as Proxy
- **Pattern**: Client libraries act as proxies for remote MCP server operations
- **Implementation**: `MCPPipeline` class manages HTTP communication and state

### 4. Pipeline as Template Method
- **Pattern**: The conversion pipeline follows a template method pattern with defined steps
- **Implementation**: `run()` method in client defines the standard workflow sequence

## Configuration Management

### Environment-Based Configuration
```python
# Configuration hierarchy
class MCPServerConfig:
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    output_dir: str = "outputs"
    use_llm: bool = False
    log_level: str = "INFO"

class AgentConfig:
    openrouter_api_key: Optional[str] = None
    model_name: str = "default"
    max_retries: int = 3
    timeout: int = 300
```

### Development vs Production
- **Development**: Local MCP server, file-based outputs, debug logging
- **Production**: Containerized MCP server, persistent storage, structured logging

## Error Handling Strategy

### MCP Server Error Handling
- **HTTP Status Codes**: Standard HTTP status codes for different error types
- **Structured Error Responses**: Consistent error response format
- **Agent Error Propagation**: Wrap agent errors in HTTP responses

### Client Error Handling
- **Connection Errors**: Retry logic for network issues
- **API Errors**: Parse and display structured error messages
- **State Recovery**: Handle partial pipeline failures gracefully

## Testing Strategy

### MCP Server Testing
- **Unit Tests**: Test individual MCP tools
- **Integration Tests**: Test agent coordination
- **API Tests**: Test HTTP endpoints with various inputs

### Agent Testing
- **Unit Tests**: Test agent logic in isolation
- **Mock Testing**: Test agent interfaces without external dependencies
- **End-to-End Tests**: Test agents with real data

### Client Testing
- **Unit Tests**: Test client logic
- **Mock Server Tests**: Test against mock MCP server
- **Integration Tests**: Test against real MCP server

## Development Workflow

### Local Development Setup
1. **Start MCP Server**: `python -m agentic_neurodata_conversion.mcp_server`
2. **Run Client**: `python examples/workflow.py`
3. **Test Pipeline**: Use test datasets and verify outputs

### CI/CD Pipeline
1. **Code Quality**: Ruff linting and formatting
2. **Unit Tests**: Test all components in isolation
3. **Integration Tests**: Test MCP server with agents
4. **End-to-End Tests**: Test full pipeline with sample data

This design embraces the MCP-centric architecture while providing a solid foundation for project organization, development workflows, and team collaboration.