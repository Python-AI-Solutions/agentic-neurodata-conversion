# MCP Server Architecture Design

## Overview

This design document outlines the MCP (Model Context Protocol) server that serves as the central orchestration hub for the agentic neurodata conversion pipeline. The MCP server coordinates specialized agents through HTTP endpoints and manages the complete conversion workflow from dataset analysis to NWB file generation and evaluation.

## Architecture

### High-Level MCP Server Architecture

```
MCP Server (Central Orchestration Hub)
├── HTTP API Layer (FastAPI)
│   ├── Conversion Endpoints
│   ├── Agent Coordination Endpoints
│   ├── Status and Monitoring Endpoints
│   └── Configuration Management
├── Agent Management System
│   ├── Agent Registry and Discovery
│   ├── Agent Lifecycle Management
│   ├── Inter-Agent Communication
│   └── Error Handling and Recovery
├── Workflow Orchestration Engine
│   ├── Pipeline State Management
│   ├── Step Dependencies and Sequencing
│   ├── Progress Tracking
│   └── Result Aggregation
├── Tool Registry and Execution
│   ├── Tool Registration (@mcp.tool decorators)
│   ├── Dynamic Tool Discovery
│   ├── Tool Execution Engine
│   └── Result Processing
└── Infrastructure Services
    ├── Configuration Management
    ├── Logging and Monitoring
    ├── Error Tracking
    └── Performance Metrics
```

### Request Flow Architecture

```
HTTP Request → API Validation → Tool Resolution → Agent Coordination → Workflow Execution → Response Assembly
                     ↓
State Management → Progress Tracking → Error Handling → Result Aggregation → Structured Response
```## 
Core Components

### 1. HTTP API Layer (FastAPI)

#### Main Server Application
```python
# src/agentic_converter/mcp_server/app.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any, Optional, List
import logging
import time
from contextlib import asynccontextmanager

from .server import MCPServer
from .middleware import LoggingMiddleware, MetricsMiddleware, ErrorHandlingMiddleware
from ..core.config import settings

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting MCP Server...")
    app.state.mcp_server = MCPServer(settings)
    await app.state.mcp_server.initialize()
    logger.info("MCP Server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP Server...")
    await app.state.mcp_server.shutdown()
    logger.info("MCP Server shutdown complete")

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Agentic Neurodata Converter MCP Server",
        description="MCP server for orchestrating neurodata conversion pipeline",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Include routers
    from .routers import conversion, agents, monitoring, tools
    app.include_router(conversion.router, prefix="/api/v1/conversion", tags=["conversion"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
    app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
    
    # Legacy endpoints for backward compatibility
    from .legacy_endpoints import setup_legacy_endpoints
    setup_legacy_endpoints(app)
    
    return app

# Create application instance
app = create_app()

def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Agentic Neurodata Converter MCP Server",
        version="1.0.0",
        description="Central orchestration hub for agentic neurodata conversion",
        routes=app.routes,
    )
    
    # Add custom schema extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

#### Conversion Router
```python
# src/agentic_converter/mcp_server/routers/conversion.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import asyncio
import uuid
from datetime import datetime

from ..dependencies import get_mcp_server
from ..models import ConversionRequest, ConversionResponse, ConversionStatus

router = APIRouter()

class DatasetAnalysisRequest(BaseModel):
    dataset_dir: str = Field(..., description="Path to dataset directory")
    use_llm: bool = Field(False, description="Whether to use LLM for metadata extraction")
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")

class ConversionScriptRequest(BaseModel):
    normalized_metadata: Dict[str, Any] = Field(..., description="Normalized metadata from analysis")
    files_map: Dict[str, str] = Field(..., description="Mapping of file types to paths")
    output_nwb_path: Optional[str] = Field(None, description="Output NWB file path")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

class EvaluationRequest(BaseModel):
    nwb_path: str = Field(..., description="Path to NWB file to evaluate")
    generate_report: bool = Field(True, description="Whether to generate evaluation report")
    include_visualizations: bool = Field(True, description="Whether to include visualizations")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

@router.post("/analyze", response_model=ConversionResponse)
async def analyze_dataset(
    request: DatasetAnalysisRequest,
    background_tasks: BackgroundTasks,
    mcp_server = Depends(get_mcp_server)
):
    """Analyze dataset structure and extract metadata."""
    
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Execute analysis through MCP server
        result = await mcp_server.execute_tool(
            "analyze_dataset",
            dataset_dir=request.dataset_dir,
            use_llm=request.use_llm,
            session_id=session_id
        )
        
        # Track conversion session
        background_tasks.add_task(
            mcp_server.track_conversion_step,
            session_id,
            "analysis",
            result
        )
        
        return ConversionResponse(
            status="success" if result.get("status") == "success" else "error",
            data=result,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-script", response_model=ConversionResponse)
async def generate_conversion_script(
    request: ConversionScriptRequest,
    background_tasks: BackgroundTasks,
    mcp_server = Depends(get_mcp_server)
):
    """Generate and execute NeuroConv conversion script."""
    
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        result = await mcp_server.execute_tool(
            "generate_conversion_script",
            normalized_metadata=request.normalized_metadata,
            files_map=request.files_map,
            output_nwb_path=request.output_nwb_path,
            session_id=session_id
        )
        
        background_tasks.add_task(
            mcp_server.track_conversion_step,
            session_id,
            "conversion",
            result
        )
        
        return ConversionResponse(
            status="success" if result.get("status") == "success" else "error",
            data=result,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate", response_model=ConversionResponse)
async def evaluate_nwb_file(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    mcp_server = Depends(get_mcp_server)
):
    """Evaluate NWB file quality and generate reports."""
    
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        result = await mcp_server.execute_tool(
            "evaluate_nwb_file",
            nwb_path=request.nwb_path,
            generate_report=request.generate_report,
            include_visualizations=request.include_visualizations,
            session_id=session_id
        )
        
        background_tasks.add_task(
            mcp_server.track_conversion_step,
            session_id,
            "evaluation",
            result
        )
        
        return ConversionResponse(
            status="success" if result.get("status") == "success" else "error",
            data=result,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/full-pipeline", response_model=ConversionResponse)
async def run_full_pipeline(
    request: ConversionRequest,
    background_tasks: BackgroundTasks,
    mcp_server = Depends(get_mcp_server)
):
    """Run complete conversion pipeline."""
    
    try:
        session_id = str(uuid.uuid4())
        
        # Start pipeline execution in background
        task_id = await mcp_server.start_pipeline_execution(
            session_id=session_id,
            dataset_dir=request.dataset_dir,
            files_map=request.files_map,
            use_llm=request.use_llm,
            output_nwb_path=request.output_nwb_path
        )
        
        return ConversionResponse(
            status="started",
            data={
                "task_id": task_id,
                "message": "Pipeline execution started",
                "status_endpoint": f"/api/v1/monitoring/status/{session_id}"
            },
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}/status")
async def get_conversion_status(
    session_id: str,
    mcp_server = Depends(get_mcp_server)
):
    """Get status of conversion session."""
    
    try:
        status = await mcp_server.get_session_status(session_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def cancel_conversion(
    session_id: str,
    mcp_server = Depends(get_mcp_server)
):
    """Cancel ongoing conversion session."""
    
    try:
        result = await mcp_server.cancel_session(session_id)
        
        return {
            "status": "cancelled" if result else "not_found",
            "session_id": session_id,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```### 2. A
gent Management System

#### Agent Registry and Lifecycle Management
```python
# src/agentic_converter/mcp_server/agent_manager.py
from typing import Dict, Any, Optional, List, Type
from abc import ABC, abstractmethod
import asyncio
import logging
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from ..agents.base import BaseAgent
from ..agents.conversation import ConversationAgent
from ..agents.conversion import ConversionAgent
from ..agents.evaluation import EvaluationAgent

class AgentStatus(Enum):
    """Agent status enumeration."""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"

@dataclass
class AgentInfo:
    """Agent information and metadata."""
    name: str
    agent_type: str
    status: AgentStatus
    instance: BaseAgent
    created_at: datetime
    last_used: Optional[datetime] = None
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0

class AgentManager:
    """Manages agent lifecycle and coordination."""
    
    def __init__(self, config):
        self.config = config
        self.agents: Dict[str, AgentInfo] = {}
        self.agent_classes: Dict[str, Type[BaseAgent]] = {
            "conversation": ConversationAgent,
            "conversion": ConversionAgent,
            "evaluation": EvaluationAgent
        }
        self.logger = logging.getLogger(__name__)
        self._initialization_lock = asyncio.Lock()
    
    async def initialize_agents(self):
        """Initialize all configured agents."""
        async with self._initialization_lock:
            for agent_type, agent_class in self.agent_classes.items():
                try:
                    self.logger.info(f"Initializing {agent_type} agent...")
                    
                    # Create agent instance
                    agent_instance = agent_class(self.config.agents)
                    
                    # Create agent info
                    agent_info = AgentInfo(
                        name=agent_type,
                        agent_type=agent_type,
                        status=AgentStatus.READY,
                        instance=agent_instance,
                        created_at=datetime.utcnow()
                    )
                    
                    self.agents[agent_type] = agent_info
                    self.logger.info(f"Successfully initialized {agent_type} agent")
                    
                except Exception as e:
                    self.logger.error(f"Failed to initialize {agent_type} agent: {e}")
                    # Create error state agent info
                    self.agents[agent_type] = AgentInfo(
                        name=agent_type,
                        agent_type=agent_type,
                        status=AgentStatus.ERROR,
                        instance=None,
                        created_at=datetime.utcnow()
                    )
    
    async def get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """Get agent instance by type."""
        agent_info = self.agents.get(agent_type)
        
        if not agent_info:
            self.logger.error(f"Agent type not found: {agent_type}")
            return None
        
        if agent_info.status != AgentStatus.READY:
            self.logger.warning(f"Agent {agent_type} is not ready (status: {agent_info.status})")
            return None
        
        return agent_info.instance
    
    async def execute_agent_task(self, agent_type: str, **kwargs) -> Dict[str, Any]:
        """Execute task using specified agent."""
        agent_info = self.agents.get(agent_type)
        
        if not agent_info or not agent_info.instance:
            return {
                "status": "error",
                "message": f"Agent {agent_type} not available"
            }
        
        # Update agent status
        agent_info.status = AgentStatus.BUSY
        agent_info.last_used = datetime.utcnow()
        
        try:
            # Execute agent task
            result = await agent_info.instance.execute(**kwargs)
            
            # Update statistics
            agent_info.total_executions += 1
            if result.status.value == "completed":
                agent_info.successful_executions += 1
            else:
                agent_info.failed_executions += 1
            
            # Convert agent result to dict
            return {
                "status": "success" if result.status.value == "completed" else "error",
                "data": result.data,
                "metadata": result.metadata,
                "provenance": result.provenance,
                "execution_time": result.execution_time,
                "agent_id": result.agent_id,
                "error": result.error,
                "warnings": result.warnings
            }
            
        except Exception as e:
            self.logger.error(f"Agent {agent_type} execution failed: {e}")
            agent_info.failed_executions += 1
            
            return {
                "status": "error",
                "message": str(e),
                "agent_type": agent_type
            }
        
        finally:
            # Reset agent status
            agent_info.status = AgentStatus.READY
    
    def get_agent_status(self, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Get status of agents."""
        if agent_type:
            agent_info = self.agents.get(agent_type)
            if not agent_info:
                return {"error": f"Agent {agent_type} not found"}
            
            return {
                "name": agent_info.name,
                "type": agent_info.agent_type,
                "status": agent_info.status.value,
                "created_at": agent_info.created_at.isoformat(),
                "last_used": agent_info.last_used.isoformat() if agent_info.last_used else None,
                "statistics": {
                    "total_executions": agent_info.total_executions,
                    "successful_executions": agent_info.successful_executions,
                    "failed_executions": agent_info.failed_executions,
                    "success_rate": (
                        agent_info.successful_executions / agent_info.total_executions
                        if agent_info.total_executions > 0 else 0.0
                    )
                }
            }
        else:
            # Return status for all agents
            return {
                agent_type: {
                    "name": info.name,
                    "status": info.status.value,
                    "total_executions": info.total_executions,
                    "success_rate": (
                        info.successful_executions / info.total_executions
                        if info.total_executions > 0 else 0.0
                    )
                }
                for agent_type, info in self.agents.items()
            }
    
    async def shutdown_agents(self):
        """Shutdown all agents gracefully."""
        for agent_type, agent_info in self.agents.items():
            try:
                self.logger.info(f"Shutting down {agent_type} agent...")
                agent_info.status = AgentStatus.SHUTDOWN
                
                # If agent has cleanup method, call it
                if agent_info.instance and hasattr(agent_info.instance, 'cleanup'):
                    await agent_info.instance.cleanup()
                
                self.logger.info(f"Successfully shut down {agent_type} agent")
                
            except Exception as e:
                self.logger.error(f"Error shutting down {agent_type} agent: {e}")

### 3. Workflow Orchestration Engine

class WorkflowOrchestrator:
    """Orchestrates multi-step conversion workflows."""
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def start_pipeline_execution(self, session_id: str, dataset_dir: str,
                                     files_map: Dict[str, str], use_llm: bool = False,
                                     output_nwb_path: Optional[str] = None) -> str:
        """Start full pipeline execution."""
        
        # Initialize session state
        self.active_sessions[session_id] = {
            "status": "running",
            "current_step": "initialization",
            "steps_completed": [],
            "steps_failed": [],
            "start_time": datetime.utcnow(),
            "dataset_dir": dataset_dir,
            "files_map": files_map,
            "use_llm": use_llm,
            "output_nwb_path": output_nwb_path,
            "results": {}
        }
        
        # Start pipeline execution as background task
        task_id = f"pipeline_{session_id}"
        asyncio.create_task(self._execute_pipeline(session_id))
        
        return task_id
    
    async def _execute_pipeline(self, session_id: str):
        """Execute complete pipeline workflow."""
        session = self.active_sessions[session_id]
        
        try:
            # Step 1: Dataset Analysis
            session["current_step"] = "analysis"
            self.logger.info(f"Session {session_id}: Starting dataset analysis")
            
            analysis_result = await self.agent_manager.execute_agent_task(
                "conversation",
                dataset_dir=session["dataset_dir"],
                use_llm=session["use_llm"]
            )
            
            if analysis_result["status"] != "success":
                raise Exception(f"Dataset analysis failed: {analysis_result.get('message', 'Unknown error')}")
            
            session["results"]["analysis"] = analysis_result
            session["steps_completed"].append("analysis")
            
            # Step 2: Conversion Script Generation
            session["current_step"] = "conversion"
            self.logger.info(f"Session {session_id}: Starting conversion")
            
            conversion_result = await self.agent_manager.execute_agent_task(
                "conversion",
                normalized_metadata=analysis_result["data"].get("enriched_metadata", {}),
                files_map=session["files_map"],
                output_nwb_path=session["output_nwb_path"]
            )
            
            if conversion_result["status"] != "success":
                raise Exception(f"Conversion failed: {conversion_result.get('message', 'Unknown error')}")
            
            session["results"]["conversion"] = conversion_result
            session["steps_completed"].append("conversion")
            
            # Step 3: Evaluation
            session["current_step"] = "evaluation"
            self.logger.info(f"Session {session_id}: Starting evaluation")
            
            nwb_path = conversion_result["data"].get("nwb_path")
            if nwb_path:
                evaluation_result = await self.agent_manager.execute_agent_task(
                    "evaluation",
                    nwb_path=nwb_path,
                    generate_report=True
                )
                
                session["results"]["evaluation"] = evaluation_result
                if evaluation_result["status"] == "success":
                    session["steps_completed"].append("evaluation")
                else:
                    session["steps_failed"].append("evaluation")
            
            # Pipeline completed successfully
            session["status"] = "completed"
            session["current_step"] = "completed"
            session["end_time"] = datetime.utcnow()
            
            self.logger.info(f"Session {session_id}: Pipeline completed successfully")
            
        except Exception as e:
            # Pipeline failed
            session["status"] = "failed"
            session["error"] = str(e)
            session["end_time"] = datetime.utcnow()
            session["steps_failed"].append(session["current_step"])
            
            self.logger.error(f"Session {session_id}: Pipeline failed at {session['current_step']}: {e}")
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of pipeline session."""
        session = self.active_sessions.get(session_id)
        
        if not session:
            return None
        
        # Calculate progress
        total_steps = 3  # analysis, conversion, evaluation
        completed_steps = len(session["steps_completed"])
        progress = completed_steps / total_steps
        
        return {
            "session_id": session_id,
            "status": session["status"],
            "current_step": session["current_step"],
            "progress": progress,
            "steps_completed": session["steps_completed"],
            "steps_failed": session.get("steps_failed", []),
            "start_time": session["start_time"].isoformat(),
            "end_time": session.get("end_time").isoformat() if session.get("end_time") else None,
            "error": session.get("error"),
            "results_available": list(session["results"].keys())
        }
    
    async def cancel_session(self, session_id: str) -> bool:
        """Cancel active pipeline session."""
        session = self.active_sessions.get(session_id)
        
        if not session:
            return False
        
        if session["status"] == "running":
            session["status"] = "cancelled"
            session["end_time"] = datetime.utcnow()
            self.logger.info(f"Session {session_id}: Cancelled by user request")
            return True
        
        return False
    
    def cleanup_completed_sessions(self, max_age_hours: int = 24):
        """Clean up old completed sessions."""
        current_time = datetime.utcnow()
        sessions_to_remove = []
        
        for session_id, session in self.active_sessions.items():
            if session.get("end_time"):
                age = current_time - session["end_time"]
                if age.total_seconds() > max_age_hours * 3600:
                    sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
            self.logger.info(f"Cleaned up old session: {session_id}")
```##
# 4. Tool Registry and Execution

#### Enhanced Tool Registry System
```python
# src/agentic_converter/mcp_server/tool_registry.py
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import inspect
import asyncio
import logging
from datetime import datetime

class ToolCategory(Enum):
    """Tool categories for organization."""
    ANALYSIS = "analysis"
    CONVERSION = "conversion"
    EVALUATION = "evaluation"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    UTILITY = "utility"

@dataclass
class ToolMetadata:
    """Enhanced tool metadata."""
    name: str
    description: str
    category: ToolCategory
    function: Callable
    parameters: Dict[str, Any]
    return_type: Optional[type] = None
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    deprecated: bool = False
    requires_auth: bool = False
    execution_timeout: int = 300  # seconds
    
    # Statistics
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    average_execution_time: float = 0.0
    last_called: Optional[datetime] = None

class EnhancedToolRegistry:
    """Enhanced tool registry with metadata and statistics."""
    
    def __init__(self):
        self.tools: Dict[str, ToolMetadata] = {}
        self.categories: Dict[ToolCategory, List[str]] = {
            category: [] for category in ToolCategory
        }
        self.logger = logging.getLogger(__name__)
    
    def register_tool(self, name: Optional[str] = None, description: Optional[str] = None,
                     category: ToolCategory = ToolCategory.UTILITY, version: str = "1.0.0",
                     author: Optional[str] = None, tags: Optional[List[str]] = None,
                     timeout: int = 300, requires_auth: bool = False):
        """Enhanced tool registration decorator."""
        
        def decorator(func: Callable):
            tool_name = name or func.__name__
            
            # Extract parameter information
            sig = inspect.signature(func)
            parameters = {}
            
            for param_name, param in sig.parameters.items():
                if param_name != 'server':  # Skip server parameter
                    param_info = {
                        'type': param.annotation.__name__ if param.annotation != inspect.Parameter.empty else 'Any',
                        'default': param.default if param.default != inspect.Parameter.empty else None,
                        'required': param.default == inspect.Parameter.empty
                    }
                    parameters[param_name] = param_info
            
            # Create tool metadata
            metadata = ToolMetadata(
                name=tool_name,
                description=description or func.__doc__ or "No description available",
                category=category,
                function=func,
                parameters=parameters,
                return_type=sig.return_annotation if sig.return_annotation != inspect.Parameter.empty else None,
                version=version,
                author=author,
                tags=tags or [],
                requires_auth=requires_auth,
                execution_timeout=timeout
            )
            
            # Register tool
            self.tools[tool_name] = metadata
            self.categories[category].append(tool_name)
            
            self.logger.info(f"Registered tool: {tool_name} (category: {category.value})")
            return func
        
        return decorator
    
    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        """Get tool metadata by name."""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None, 
                  include_deprecated: bool = False) -> Dict[str, Dict[str, Any]]:
        """List tools with optional filtering."""
        
        tools_list = {}
        
        for tool_name, metadata in self.tools.items():
            # Filter by category
            if category and metadata.category != category:
                continue
            
            # Filter deprecated
            if not include_deprecated and metadata.deprecated:
                continue
            
            tools_list[tool_name] = {
                'description': metadata.description,
                'category': metadata.category.value,
                'parameters': metadata.parameters,
                'version': metadata.version,
                'author': metadata.author,
                'tags': metadata.tags,
                'deprecated': metadata.deprecated,
                'statistics': {
                    'total_calls': metadata.total_calls,
                    'success_rate': (
                        metadata.successful_calls / metadata.total_calls
                        if metadata.total_calls > 0 else 0.0
                    ),
                    'average_execution_time': metadata.average_execution_time,
                    'last_called': metadata.last_called.isoformat() if metadata.last_called else None
                }
            }
        
        return tools_list
    
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """Get tools organized by category."""
        return {
            category.value: tool_names 
            for category, tool_names in self.categories.items()
            if tool_names
        }
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute tool with enhanced error handling and statistics."""
        
        metadata = self.tools.get(tool_name)
        if not metadata:
            return {
                "status": "error",
                "message": f"Tool not found: {tool_name}"
            }
        
        if metadata.deprecated:
            self.logger.warning(f"Using deprecated tool: {tool_name}")
        
        start_time = datetime.utcnow()
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                metadata.function(**kwargs),
                timeout=metadata.execution_timeout
            )
            
            # Update statistics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_tool_statistics(metadata, execution_time, success=True)
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_tool_statistics(metadata, execution_time, success=False)
            
            return {
                "status": "error",
                "message": f"Tool {tool_name} timed out after {metadata.execution_timeout} seconds"
            }
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_tool_statistics(metadata, execution_time, success=False)
            
            self.logger.error(f"Tool {tool_name} execution failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "tool": tool_name
            }
    
    def _update_tool_statistics(self, metadata: ToolMetadata, execution_time: float, success: bool):
        """Update tool execution statistics."""
        metadata.total_calls += 1
        metadata.last_called = datetime.utcnow()
        
        if success:
            metadata.successful_calls += 1
        else:
            metadata.failed_calls += 1
        
        # Update average execution time
        if metadata.total_calls == 1:
            metadata.average_execution_time = execution_time
        else:
            # Running average
            metadata.average_execution_time = (
                (metadata.average_execution_time * (metadata.total_calls - 1) + execution_time) 
                / metadata.total_calls
            )
    
    def deprecate_tool(self, tool_name: str, reason: Optional[str] = None):
        """Mark tool as deprecated."""
        metadata = self.tools.get(tool_name)
        if metadata:
            metadata.deprecated = True
            self.logger.warning(f"Tool {tool_name} marked as deprecated: {reason}")
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get overall tool registry statistics."""
        total_tools = len(self.tools)
        deprecated_tools = sum(1 for m in self.tools.values() if m.deprecated)
        total_calls = sum(m.total_calls for m in self.tools.values())
        successful_calls = sum(m.successful_calls for m in self.tools.values())
        
        category_stats = {}
        for category in ToolCategory:
            category_tools = self.categories[category]
            category_stats[category.value] = {
                'tool_count': len(category_tools),
                'total_calls': sum(self.tools[name].total_calls for name in category_tools),
                'success_rate': (
                    sum(self.tools[name].successful_calls for name in category_tools) /
                    sum(self.tools[name].total_calls for name in category_tools)
                    if sum(self.tools[name].total_calls for name in category_tools) > 0 else 0.0
                )
            }
        
        return {
            'total_tools': total_tools,
            'deprecated_tools': deprecated_tools,
            'active_tools': total_tools - deprecated_tools,
            'total_calls': total_calls,
            'overall_success_rate': successful_calls / total_calls if total_calls > 0 else 0.0,
            'category_statistics': category_stats
        }

# Global enhanced registry instance
enhanced_mcp = EnhancedToolRegistry()

### 5. Infrastructure Services

class MCPServerCore:
    """Core MCP server implementation with all components."""
    
    def __init__(self, config):
        self.config = config
        self.agent_manager = AgentManager(config)
        self.workflow_orchestrator = WorkflowOrchestrator(self.agent_manager)
        self.tool_registry = enhanced_mcp
        self.logger = logging.getLogger(__name__)
        
        # Performance metrics
        self.metrics = {
            'server_start_time': None,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'active_sessions': 0
        }
    
    async def initialize(self):
        """Initialize MCP server components."""
        self.logger.info("Initializing MCP Server components...")
        
        # Initialize agents
        await self.agent_manager.initialize_agents()
        
        # Register built-in tools
        self._register_builtin_tools()
        
        # Start background tasks
        asyncio.create_task(self._background_maintenance())
        
        self.metrics['server_start_time'] = datetime.utcnow()
        self.logger.info("MCP Server initialization complete")
    
    def _register_builtin_tools(self):
        """Register built-in MCP tools."""
        
        @self.tool_registry.register_tool(
            name="analyze_dataset",
            description="Analyze dataset structure and extract metadata",
            category=ToolCategory.ANALYSIS,
            timeout=600
        )
        async def analyze_dataset(dataset_dir: str, use_llm: bool = False, server=None):
            return await self.agent_manager.execute_agent_task(
                "conversation", dataset_dir=dataset_dir, use_llm=use_llm
            )
        
        @self.tool_registry.register_tool(
            name="generate_conversion_script",
            description="Generate and execute NeuroConv conversion script",
            category=ToolCategory.CONVERSION,
            timeout=1800
        )
        async def generate_conversion_script(
            normalized_metadata: Dict[str, Any],
            files_map: Dict[str, str],
            output_nwb_path: Optional[str] = None,
            server=None
        ):
            return await self.agent_manager.execute_agent_task(
                "conversion",
                normalized_metadata=normalized_metadata,
                files_map=files_map,
                output_nwb_path=output_nwb_path
            )
        
        @self.tool_registry.register_tool(
            name="evaluate_nwb_file",
            description="Evaluate NWB file quality and generate reports",
            category=ToolCategory.EVALUATION,
            timeout=900
        )
        async def evaluate_nwb_file(
            nwb_path: str,
            generate_report: bool = True,
            include_visualizations: bool = True,
            server=None
        ):
            return await self.agent_manager.execute_agent_task(
                "evaluation",
                nwb_path=nwb_path,
                generate_report=generate_report,
                include_visualizations=include_visualizations
            )
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute tool through registry."""
        self.metrics['total_requests'] += 1
        
        try:
            result = await self.tool_registry.execute_tool(tool_name, server=self, **kwargs)
            
            if result.get("status") == "success":
                self.metrics['successful_requests'] += 1
            else:
                self.metrics['failed_requests'] += 1
            
            return result
            
        except Exception as e:
            self.metrics['failed_requests'] += 1
            self.logger.error(f"Tool execution failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def start_pipeline_execution(self, **kwargs) -> str:
        """Start pipeline execution."""
        self.metrics['active_sessions'] += 1
        return await self.workflow_orchestrator.start_pipeline_execution(**kwargs)
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session status."""
        return self.workflow_orchestrator.get_session_status(session_id)
    
    async def cancel_session(self, session_id: str) -> bool:
        """Cancel session."""
        result = await self.workflow_orchestrator.cancel_session(session_id)
        if result:
            self.metrics['active_sessions'] = max(0, self.metrics['active_sessions'] - 1)
        return result
    
    def get_server_metrics(self) -> Dict[str, Any]:
        """Get comprehensive server metrics."""
        uptime = (
            (datetime.utcnow() - self.metrics['server_start_time']).total_seconds()
            if self.metrics['server_start_time'] else 0
        )
        
        return {
            'server_info': {
                'start_time': self.metrics['server_start_time'].isoformat() if self.metrics['server_start_time'] else None,
                'uptime_seconds': uptime,
                'version': '1.0.0'
            },
            'request_metrics': {
                'total_requests': self.metrics['total_requests'],
                'successful_requests': self.metrics['successful_requests'],
                'failed_requests': self.metrics['failed_requests'],
                'success_rate': (
                    self.metrics['successful_requests'] / self.metrics['total_requests']
                    if self.metrics['total_requests'] > 0 else 0.0
                )
            },
            'session_metrics': {
                'active_sessions': self.metrics['active_sessions']
            },
            'agent_metrics': self.agent_manager.get_agent_status(),
            'tool_metrics': self.tool_registry.get_tool_statistics()
        }
    
    async def _background_maintenance(self):
        """Background maintenance tasks."""
        while True:
            try:
                # Clean up old sessions every hour
                self.workflow_orchestrator.cleanup_completed_sessions()
                
                # Log metrics every 5 minutes
                if self.metrics['total_requests'] % 100 == 0:
                    metrics = self.get_server_metrics()
                    self.logger.info(f"Server metrics: {metrics['request_metrics']}")
                
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                self.logger.error(f"Background maintenance error: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
    
    async def shutdown(self):
        """Shutdown MCP server gracefully."""
        self.logger.info("Shutting down MCP Server...")
        
        # Shutdown agents
        await self.agent_manager.shutdown_agents()
        
        self.logger.info("MCP Server shutdown complete")
```

This comprehensive MCP server architecture design provides a robust, scalable, and well-organized central orchestration hub that coordinates all aspects of the agentic neurodata conversion pipeline while maintaining high availability, observability, and extensibility.