# Core Project Organization Design

## Overview

This design document outlines the foundational project structure, packaging, development tooling, and collaborative workflows for the agentic neurodata conversion project. It establishes the base infrastructure that supports all other system components detailed in specialized specs. The system is built around a central MCP (Model Context Protocol) server that serves as the primary orchestration layer, exposing dataset analysis capabilities, conversion orchestration tools, and workflow handoff mechanisms, which delegate tasks to internal agent modules (conversation and conversion agents). This core organization provides the foundation for MCP server architecture, agent implementations, validation systems, knowledge graphs, evaluation frameworks, data management, and testing infrastructure.

## Coordination with Other Specs

This core project organization provides the foundation for specialized components:

- **MCP Server Architecture** (`mcp-server-architecture` spec): Implemented in `agentic_neurodata_conversion/mcp_server/` with dataset analysis, conversion orchestration, and workflow handoff capabilities
- **Agent Implementations** (`agent-implementations` spec): Implemented in `agentic_neurodata_conversion/agents/` including conversation and conversion agent modules
- **Validation Systems** (`validation-quality-assurance` spec): Implemented in `agentic_neurodata_conversion/validation/`
- **Knowledge Graph Systems** (`knowledge-graph-systems` spec): Implemented in `agentic_neurodata_conversion/knowledge_graph/`
- **Evaluation and Reporting** (`evaluation-reporting` spec): Implemented in `agentic_neurodata_conversion/evaluation/`
- **Data Management** (`data-management-provenance` spec): Implemented in `agentic_neurodata_conversion/data_management/`
- **Client Examples** (`client-libraries-integrations` spec): Provided in `examples/`
- **Testing Framework** (`testing-quality-assurance` spec): Implemented in `tests/`

## Architecture

### High-Level Architecture

```
Core Project Organization (Foundation Layer)
├── Package Structure
│   ├── Main Package (agentic_neurodata_conversion/)
│   ├── Specialized Component Directories
│   ├── Examples Directory
│   └── Testing Infrastructure
├── Development Infrastructure
│   ├── Configuration Management (Pydantic-based)
│   ├── Dependency Management (Pixi)
│   ├── Code Quality Tools (Ruff, Pre-commit)
│   └── Basic CI/CD Pipeline
├── Documentation Foundation
│   ├── API Documentation Structure
│   ├── Architecture Documentation
│   ├── Development Guides
│   └── Third-party Integration Docs
└── Collaborative Workflows
    ├── Git Workflow Patterns
    ├── Code Review Processes
    ├── Release Management
    └── Team Onboarding
```

### Project Structure

```
agentic-neurodata-converter/
├── pyproject.toml                 # Pixi-managed dependencies and project config
├── pixi.toml                      # Pixi environment configuration
├── .env.example                   # Environment configuration template
├── README.md                      # Project overview and setup
├── 
├── agentic_neurodata_conversion/         # Main package
│   ├── __init__.py
│   ├── core/                      # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic-based configuration
│   │   ├── logging.py             # Centralized logging setup
│   │   └── exceptions.py          # Custom exception classes
│   ├── mcp_server/                # MCP Server implementation
│   │   ├── __init__.py
│   │   ├── server.py              # Main MCP server with tool registry
│   │   ├── tools/                 # MCP tool implementations
│   │   │   ├── __init__.py
│   │   │   ├── dataset_analysis.py
│   │   │   ├── conversion.py
│   │   │   ├── evaluation.py
│   │   │   └── knowledge_graph.py
│   │   └── interfaces/            # Different interface implementations
│   │       ├── __init__.py
│   │       ├── fastapi_interface.py
│   │       └── stdio_interface.py
│   ├── agents/                    # Agent implementations (internal)
│   │   ├── __init__.py
│   │   ├── base.py                # Base agent interface
│   │   ├── conversation.py        # Conversation agent
│   │   ├── conversion.py          # Conversion agent
│   │   ├── evaluation.py          # Evaluation agent
│   │   └── knowledge_graph.py     # Knowledge graph agent
│   ├── interfaces/                # External interfaces and utilities
│   │   ├── __init__.py
│   │   ├── neuroconv_wrapper.py   # NeuroConv integration
│   │   ├── nwb_inspector.py       # NWB Inspector integration
│   │   └── linkml_validator.py    # LinkML validation
│   └── utils/                     # Utility functions
│       ├── __init__.py
│       ├── file_utils.py
│       ├── format_detection.py
│       └── metadata_utils.py
├── 
├── examples/                      # Client examples for third-party developers
│   ├── python_client/
│   │   ├── workflow_example.py    # Based on current workflow.py
│   │   ├── simple_client.py       # Minimal example
│   │   └── README.md              # Client development guide
│   ├── integration_patterns/
│   │   ├── jupyter_notebook.ipynb
│   │   └── cli_wrapper.py
│   └── README.md                  # Examples overview
├── 
├── etl/                           # Data processing and workflows
│   ├── input-data/                # Raw datasets for processing
│   ├── workflows/                 # ETL workflow definitions
│   └── evaluation-data/           # Test and evaluation datasets
├── 
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   │   ├── test_mcp_server.py
│   │   ├── test_agents.py
│   │   └── test_tools.py
│   ├── integration/               # Integration tests
│   │   ├── test_pipeline.py
│   │   └── test_client_examples.py
│   └── fixtures/                  # Test data and fixtures
├── 
├── docs/                          # Documentation
│   ├── architecture/              # Architecture documentation
│   ├── api/                       # API documentation
│   ├── development/               # Development guides
│   └── examples/                  # Usage examples
├── 
├── scripts/                       # Development and deployment scripts
│   ├── setup_dev.py               # Development environment setup
│   ├── run_server.py              # MCP server startup script
│   └── deploy.py                  # Deployment utilities
└── 
└── .github/                       # GitHub workflows and templates
    ├── workflows/
    │   ├── ci.yml                 # Continuous integration
    │   ├── tests.yml              # Test automation
    │   └── docs.yml               # Documentation building
    └── ISSUE_TEMPLATE/            # Issue templates
```

## Core Components

### 1. MCP Server (Primary Orchestration Layer)

#### Server Implementation
```python
# agentic_neurodata_conversion/mcp_server/server.py
from typing import Dict, Any, Optional, Callable
from fastapi import FastAPI, HTTPException
import logging

logger = logging.getLogger(__name__)

class MCPRegistry:
    """Central registry for MCP tools with decorator-based registration."""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
    
    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """Decorator for registering MCP tools."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            self.tools[tool_name] = func
            self.tool_metadata[tool_name] = {
                'description': description or func.__doc__,
                'function': func.__name__,
                'module': func.__module__
            }
            logger.info(f"Registered MCP tool: {tool_name}")
            return func
        return decorator
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get registered tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all registered tools with metadata."""
        return self.tool_metadata.copy()

# Global registry instance
mcp = MCPRegistry()

class MCPServer:
    """Central MCP server that orchestrates all agent interactions."""
    
    def __init__(self, config: 'ServerConfig'):
        self.config = config
        self.registry = mcp
        self.pipeline_state: Dict[str, Any] = {}
        self.agents = self._initialize_agents()
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize internal agents."""
        from ..agents import (
            ConversationAgent, ConversionAgent, 
            EvaluationAgent, KnowledgeGraphAgent
        )
        
        return {
            'conversation': ConversationAgent(self.config.agent_config),
            'conversion': ConversionAgent(self.config.agent_config),
            'evaluation': EvaluationAgent(self.config.agent_config),
            'knowledge_graph': KnowledgeGraphAgent(self.config.agent_config)
        }
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a registered tool with error handling."""
        tool = self.registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        try:
            # Inject server context into tool execution
            kwargs['server'] = self
            result = await tool(**kwargs)
            
            # Update pipeline state if needed
            if isinstance(result, dict) and 'state_updates' in result:
                self.pipeline_state.update(result['state_updates'])
            
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return {
                'status': 'error',
                'message': str(e),
                'tool': tool_name
            }
```

#### Tool Registration Examples
```python
# agentic_neurodata_conversion/mcp_server/tools/dataset_analysis.py
from ..server import mcp
from typing import Dict, Any

@mcp.tool(
    name="dataset_analysis",
    description="Analyze dataset structure and extract metadata"
)
async def dataset_analysis(
    dataset_dir: str, 
    use_llm: bool = False,
    server=None
) -> Dict[str, Any]:
    """Analyze dataset using conversation agent."""
    conversation_agent = server.agents['conversation']
    
    try:
        result = await conversation_agent.analyze_dataset(
            dataset_dir=dataset_dir,
            use_llm=use_llm
        )
        
        return {
            'status': 'success',
            'result': result,
            'state_updates': {
                'last_analyzed_dataset': dataset_dir,
                'normalized_metadata': result.get('metadata', {})
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

@mcp.tool(
    name="conversion_orchestration",
    description="Generate and execute NeuroConv conversion script"
)
async def conversion_orchestration(
    normalized_metadata: Dict[str, Any],
    files_map: Dict[str, str],
    output_nwb_path: str = None,
    server=None
) -> Dict[str, Any]:
    """Generate conversion script using conversion agent."""
    conversion_agent = server.agents['conversion']
    
    try:
        result = await conversion_agent.generate_script(
            metadata=normalized_metadata,
            files_map=files_map,
            output_path=output_nwb_path
        )
        
        return {
            'status': 'success',
            'result': result,
            'output_nwb_path': result.get('nwb_path'),
            'state_updates': {
                'last_conversion_result': result,
                'current_nwb_path': result.get('nwb_path')
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
```

### 2. Configuration Management

#### Pydantic-based Configuration System
```python
# agentic_neurodata_conversion/core/config.py
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, Any, Optional, List
from pathlib import Path
import os

class ServerConfig(BaseModel):
    """MCP Server configuration."""
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: List[str] = ["*"]

class AgentConfig(BaseModel):
    """Configuration for internal agents."""
    conversation_model: str = "gpt-4"
    conversion_timeout: int = 300
    evaluation_strict: bool = True
    knowledge_graph_format: str = "ttl"

class DataConfig(BaseModel):
    """Data processing configuration."""
    output_dir: str = "outputs"
    temp_dir: str = "temp"
    max_file_size: int = 1024 * 1024 * 1024  # 1GB
    supported_formats: List[str] = [
        "open_ephys", "spikeglx", "neuralynx", "blackrock"
    ]

class DatabaseConfig(BaseModel):
    """Database configuration for state persistence."""
    url: Optional[str] = None
    echo: bool = False
    pool_size: int = 5

class Settings(BaseSettings):
    """Main application settings."""
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Nested configurations
    server: ServerConfig = ServerConfig()
    agents: AgentConfig = AgentConfig()
    data: DataConfig = DataConfig()
    database: DatabaseConfig = DatabaseConfig()
    
    # Environment-specific overrides
    environment: str = "development"
    debug: bool = True
    
    @validator("data")
    def validate_directories(cls, v):
        """Ensure required directories exist."""
        Path(v.output_dir).mkdir(parents=True, exist_ok=True)
        Path(v.temp_dir).mkdir(parents=True, exist_ok=True)
        return v

# Global settings instance
settings = Settings()
```

### 3. Interface Layer

#### FastAPI Interface Implementation
```python
# agentic_neurodata_conversion/mcp_server/interfaces/fastapi_interface.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
from ...core.config import settings
from ..server import MCPServer
import logging

logger = logging.getLogger(__name__)

def create_fastapi_app(mcp_server: MCPServer) -> FastAPI:
    """Create FastAPI application with MCP server integration."""
    
    app = FastAPI(
        title="Agentic Neurodata Converter MCP Server",
        description="MCP server for orchestrating neurodata conversion pipeline",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.post("/tool/{tool_name}")
    async def execute_tool(
        tool_name: str, 
        payload: Optional[Dict[str, Any]] = None
    ):
        """Execute a registered MCP tool."""
        payload = payload or {}
        
        try:
            result = await mcp_server.execute_tool(tool_name, **payload)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/tools")
    async def list_tools():
        """List all registered tools."""
        return {"tools": mcp_server.registry.list_tools()}
    
    @app.get("/status")
    async def get_status():
        """Get server status and pipeline state."""
        return {
            "status": "running",
            "pipeline_state": mcp_server.pipeline_state,
            "registered_tools": len(mcp_server.registry.tools),
            "agents": list(mcp_server.agents.keys())
        }
    
    @app.post("/reset")
    async def reset_pipeline():
        """Reset pipeline state."""
        mcp_server.pipeline_state.clear()
        return {"status": "reset", "message": "Pipeline state cleared"}
    
    return app
```

### 4. Client Examples

#### Python Client Example (Based on workflow.py)
```python
# examples/python_client/workflow_example.py
import requests
import json
from pathlib import Path
from typing import Dict, Any, Optional

class MCPClient:
    """Example Python client for MCP server interaction."""
    
    def __init__(self, api_url: str = "http://127.0.0.1:8000", output_dir: str = "outputs"):
        self.api_url = api_url.rstrip("/")
        self.output_dir = output_dir
        self.pipeline_state = {}
    
    def _call_tool(self, tool_name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call MCP server tool with error handling."""
        url = f"{self.api_url}/tool/{tool_name}"
        
        try:
            response = requests.post(url, json=payload or {})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {tool_name} failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return {"status": "error", "message": str(e)}
    
    def get_available_tools(self) -> Dict[str, Any]:
        """Get list of available tools from server."""
        try:
            response = requests.get(f"{self.api_url}/tools")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to get tools: {e}")
            return {"tools": {}}
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get server status and pipeline state."""
        try:
            response = requests.get(f"{self.api_url}/status")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to get status: {e}")
            return {"status": "unknown"}
    
    def analyze_dataset(self, dataset_dir: str, use_llm: bool = False) -> Dict[str, Any]:
        """Analyze dataset structure and metadata."""
        result = self._call_tool("dataset_analysis", {
            "dataset_dir": dataset_dir,
            "use_llm": use_llm
        })
        
        if result.get("status") == "success":
            self.pipeline_state["normalized_metadata"] = result.get("result", {})
        
        return result
    
    def generate_conversion_script(self, files_map: Dict[str, str]) -> Dict[str, Any]:
        """Generate and execute conversion script."""
        if "normalized_metadata" not in self.pipeline_state:
            return {"status": "error", "message": "No metadata available. Run analyze_dataset first."}
        
        result = self._call_tool("conversion_orchestration", {
            "normalized_metadata": self.pipeline_state["normalized_metadata"],
            "files_map": files_map
        })
        
        if result.get("status") == "success":
            self.pipeline_state["nwb_path"] = result.get("output_nwb_path")
        
        return result
    
    def evaluate_nwb_file(self, nwb_path: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate generated NWB file."""
        nwb_path = nwb_path or self.pipeline_state.get("nwb_path")
        
        if not nwb_path:
            return {"status": "error", "message": "No NWB file available for evaluation"}
        
        return self._call_tool("evaluate_nwb_file", {
            "nwb_path": nwb_path,
            "generate_report": True
        })
    
    def run_full_pipeline(self, dataset_dir: str, files_map: Dict[str, str]) -> Dict[str, Any]:
        """Run complete conversion pipeline."""
        print("=== Starting Full Pipeline ===")
        
        # Step 1: Analyze dataset
        print("Step 1: Analyzing dataset...")
        analysis_result = self.analyze_dataset(dataset_dir)
        if analysis_result.get("status") != "success":
            return analysis_result
        
        # Step 2: Generate conversion
        print("Step 2: Generating conversion...")
        conversion_result = self.generate_conversion_script(files_map)
        if conversion_result.get("status") != "success":
            return conversion_result
        
        # Step 3: Evaluate result
        print("Step 3: Evaluating NWB file...")
        evaluation_result = self.evaluate_nwb_file()
        
        print("=== Pipeline Complete ===")
        return {
            "status": "success",
            "analysis": analysis_result,
            "conversion": conversion_result,
            "evaluation": evaluation_result,
            "pipeline_state": self.pipeline_state
        }

# Example usage
if __name__ == "__main__":
    client = MCPClient()
    
    # Check server status
    status = client.get_server_status()
    print("Server Status:", json.dumps(status, indent=2))
    
    # List available tools
    tools = client.get_available_tools()
    print("Available Tools:", json.dumps(tools, indent=2))
    
    # Run pipeline (example)
    # result = client.run_full_pipeline(
    #     dataset_dir="/path/to/dataset",
    #     files_map={"recording": "/path/to/recording.dat"}
    # )
```

## Development Infrastructure

### 1. Testing Framework

#### MCP Server Testing
```python
# tests/unit/test_mcp_server.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.agentic_converter.mcp_server.server import MCPServer, mcp
from src.agentic_converter.core.config import Settings

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return Settings()

@pytest.fixture
def mcp_server(mock_config):
    """MCP server instance for testing."""
    return MCPServer(mock_config)

class TestMCPRegistry:
    """Test MCP tool registry functionality."""
    
    def test_tool_registration(self):
        """Test tool registration with decorator."""
        @mcp.tool(name="test_tool", description="Test tool")
        async def test_function():
            return {"status": "success"}
        
        assert "test_tool" in mcp.tools
        assert mcp.tool_metadata["test_tool"]["description"] == "Test tool"
    
    def test_tool_execution(self, mcp_server):
        """Test tool execution through server."""
        @mcp.tool(name="test_execution")
        async def test_execution_function(param1: str, server=None):
            return {"status": "success", "param1": param1}
        
        result = await mcp_server.execute_tool("test_execution", param1="test_value")
        assert result["status"] == "success"
        assert result["param1"] == "test_value"

class TestMCPServer:
    """Test MCP server functionality."""
    
    def test_server_initialization(self, mcp_server):
        """Test server initializes with agents."""
        assert "conversation" in mcp_server.agents
        assert "conversion" in mcp_server.agents
        assert "evaluation" in mcp_server.agents
        assert "knowledge_graph" in mcp_server.agents
    
    def test_pipeline_state_management(self, mcp_server):
        """Test pipeline state updates."""
        initial_state = mcp_server.pipeline_state.copy()
        
        # Simulate state update
        mcp_server.pipeline_state.update({"test_key": "test_value"})
        
        assert mcp_server.pipeline_state["test_key"] == "test_value"
        assert len(mcp_server.pipeline_state) == len(initial_state) + 1
```

#### Integration Testing
```python
# tests/integration/test_client_examples.py
import pytest
import requests
from unittest.mock import patch
from examples.python_client.workflow_example import MCPClient

@pytest.fixture
def mock_server_response():
    """Mock server responses for testing."""
    return {
        "dataset_analysis": {"status": "success", "result": {"metadata": "test"}},
        "conversion_orchestration": {"status": "success", "output_nwb_path": "/test/path.nwb"},
        "evaluate_nwb_file": {"status": "success", "evaluation": "passed"}
    }

class TestMCPClient:
    """Test client example functionality."""
    
    @patch('requests.post')
    def test_analyze_dataset(self, mock_post, mock_server_response):
        """Test dataset analysis through client."""
        mock_post.return_value.json.return_value = mock_server_response["dataset_analysis"]
        mock_post.return_value.raise_for_status.return_value = None
        
        client = MCPClient()
        result = client.analyze_dataset("/test/dataset")
        
        assert result["status"] == "success"
        assert "normalized_metadata" in client.pipeline_state
    
    @patch('requests.post')
    def test_full_pipeline(self, mock_post, mock_server_response):
        """Test complete pipeline execution."""
        # Mock sequential responses
        mock_post.return_value.json.side_effect = [
            mock_server_response["dataset_analysis"],
            mock_server_response["conversion_orchestration"],
            mock_server_response["evaluate_nwb_file"]
        ]
        mock_post.return_value.raise_for_status.return_value = None
        
        client = MCPClient()
        result = client.run_full_pipeline("/test/dataset", {"recording": "/test/file.dat"})
        
        assert result["status"] == "success"
        assert "analysis" in result
        assert "conversion" in result
        assert "evaluation" in result
```

### 2. CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Pixi
      uses: prefix-dev/setup-pixi@v0.4.1
      with:
        pixi-version: v0.13.0
    
    - name: Install dependencies
      run: pixi install
    
    - name: Run linting
      run: |
        pixi run ruff check src/ tests/
        pixi run ruff format --check src/ tests/
    
    - name: Run type checking
      run: pixi run mypy src/
    
    - name: Run unit tests
      run: pixi run pytest tests/unit/ -v --cov=src/agentic_converter
    
    - name: Run integration tests
      run: pixi run pytest tests/integration/ -v
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Pixi
      uses: prefix-dev/setup-pixi@v0.4.1
    
    - name: Build package
      run: pixi run python -m build
    
    - name: Test installation
      run: |
        pixi run pip install dist/*.whl
        pixi run python -c "import agentic_converter; print('Package installed successfully')"
```

### 3. Documentation System

#### API Documentation Generation
```python
# scripts/generate_docs.py
"""Generate API documentation from MCP server tools and agents."""

import inspect
from pathlib import Path
from src.agentic_converter.mcp_server.server import mcp
from src.agentic_converter.agents import *

def generate_tool_docs():
    """Generate documentation for registered MCP tools."""
    docs = []
    
    for tool_name, metadata in mcp.tool_metadata.items():
        tool_func = mcp.tools[tool_name]
        signature = inspect.signature(tool_func)
        
        doc = f"""
## {tool_name}

**Description:** {metadata.get('description', 'No description available')}

**Function:** `{metadata['function']}`

**Parameters:**
"""
        
        for param_name, param in signature.parameters.items():
            if param_name != 'server':  # Skip internal server parameter
                param_type = param.annotation.__name__ if param.annotation != inspect.Parameter.empty else 'Any'
                default = f" = {param.default}" if param.default != inspect.Parameter.empty else ""
                doc += f"- `{param_name}`: {param_type}{default}\n"
        
        docs.append(doc)
    
    return "\n".join(docs)

def generate_agent_docs():
    """Generate documentation for internal agents."""
    # Implementation for agent documentation
    pass

if __name__ == "__main__":
    # Generate and save documentation
    tool_docs = generate_tool_docs()
    
    docs_dir = Path("docs/api")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    with open(docs_dir / "mcp_tools.md", "w") as f:
        f.write("# MCP Tools API Reference\n\n")
        f.write(tool_docs)
    
    print("Documentation generated successfully!")
```

## Deployment and Operations

### 1. Container Configuration

#### Dockerfile
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Pixi
RUN curl -fsSL https://pixi.sh/install.sh | bash
ENV PATH="/root/.pixi/bin:$PATH"

# Copy project files
COPY pyproject.toml pixi.toml ./
COPY src/ ./src/
COPY examples/ ./examples/

# Install dependencies
RUN pixi install --frozen

# Expose MCP server port
EXPOSE 8000

# Set environment variables
ENV MCP_SERVER_HOST=0.0.0.0
ENV MCP_SERVER_PORT=8000

# Run MCP server
CMD ["pixi", "run", "python", "-m", "src.agentic_converter.mcp_server"]
```

### 2. Development Scripts

#### Server Startup Script
```python
# scripts/run_server.py
"""Start MCP server with configuration options."""

import argparse
import asyncio
import uvicorn
from src.agentic_converter.core.config import settings
from src.agentic_converter.mcp_server.server import MCPServer
from src.agentic_converter.mcp_server.interfaces.fastapi_interface import create_fastapi_app

def main():
    parser = argparse.ArgumentParser(description="Start MCP Server")
    parser.add_argument("--host", default=settings.server.host, help="Server host")
    parser.add_argument("--port", type=int, default=settings.server.port, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--interface", choices=["fastapi", "stdio"], default="fastapi", help="Interface type")
    
    args = parser.parse_args()
    
    # Create MCP server
    mcp_server = MCPServer(settings)
    
    if args.interface == "fastapi":
        # Create FastAPI app
        app = create_fastapi_app(mcp_server)
        
        # Run with uvicorn
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            debug=args.debug,
            log_level="debug" if args.debug else "info"
        )
    else:
        # Run stdio interface
        from src.agentic_converter.mcp_server.interfaces.stdio_interface import run_stdio_server
        asyncio.run(run_stdio_server(mcp_server))

if __name__ == "__main__":
    main()
```

This design provides a comprehensive foundation for the core project organization, emphasizing the MCP server as the primary orchestration layer while providing clear examples and patterns for third-party developers to integrate with the system.