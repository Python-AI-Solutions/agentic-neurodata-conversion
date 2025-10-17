# Implementation Plan: Multi-Agent NWB Conversion Pipeline

**Feature ID**: multi-agent-nwb-conversion
**Plan Version**: 1.0.0
**Specification Version**: 1.1.0
**Status**: Ready for Task Generation
**Created**: 2025-01-14

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Technology Stack](#2-technology-stack)
3. [Data Models and Schemas](#3-data-models-and-schemas)
4. [Component Implementation Details](#4-component-implementation-details)
5. [Configuration Management](#5-configuration-management)
6. [Testing Strategy](#6-testing-strategy)
7. [Deployment](#7-deployment)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [API Contract Examples](#9-api-contract-examples)
10. [Risks and Mitigations](#10-risks-and-mitigations)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    User (REST Client)                           │
│               (curl, httpx, requests, etc.)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/REST (port 3000)
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     MCP Server (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ REST API Layer                                           │  │
│  │ - POST /api/v1/sessions/initialize                       │  │
│  │ - GET /api/v1/sessions/{id}/status                       │  │
│  │ - POST /api/v1/sessions/{id}/clarify                     │  │
│  │ - GET /api/v1/sessions/{id}/result                       │  │
│  │ - GET /health                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Message Router                                           │  │
│  │ - Routes MCP messages to agents                          │  │
│  │ - Message queue (in-memory for MVP)                      │  │
│  │ - At-least-once delivery                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Agent Registry                                           │  │
│  │ - Agent discovery and registration                       │  │
│  │ - Agent health tracking                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Context Manager                                          │  │
│  │ - Redis client (primary cache)                           │  │
│  │ - Filesystem writer (persistence)                        │  │
│  │ - Write-through strategy                                 │  │
│  │ - 24-hour TTL management                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└────┬────────────────────┬────────────────────┬─────────────────┘
     │ MCP Protocol       │ MCP Protocol       │ MCP Protocol
     │ (HTTP requests)    │ (HTTP requests)    │ (HTTP requests)
     │                    │                    │
┌────▼──────────┐   ┌─────▼───────────┐   ┌───▼─────────────────┐
│ Conversation  │   │   Conversion    │   │   Evaluation        │
│    Agent      │   │     Agent       │   │     Agent           │
│ (Process 1)   │   │  (Process 2)    │   │  (Process 3)        │
│               │   │                 │   │                     │
│ - Session init│   │ - NeuroConv     │   │ - NWB Inspector     │
│ - Format det. │   │ - OpenEphys     │   │ - Report gen        │
│ - Metadata    │   │ - Error fmt     │   │ - Validation sum    │
│ - Validation  │   │                 │   │                     │
│               │   │                 │   │                     │
│ LLM: Config   │   │ LLM: Config     │   │ LLM: Config         │
│ Provider: Any │   │ Provider: Any   │   │ Provider: Any       │
└───────────────┘   └─────────────────┘   └─────────────────────┘
     │                    │                    │
     └────────────────────┴────────────────────┘
                          │
                          │ Read/Write
                          │
        ┌─────────────────▼─────────────────┐
        │     Context Storage Layer         │
        │  ┌──────────────────────────────┐ │
        │  │ Redis (Primary Cache)        │ │
        │  │ - Session contexts           │ │
        │  │ - 24h TTL per session        │ │
        │  │ - Database: 0                │ │
        │  └──────────────────────────────┘ │
        │  ┌──────────────────────────────┐ │
        │  │ Filesystem (Backup)          │ │
        │  │ - JSON files                 │ │
        │  │ - Path: ./data/sessions/     │ │
        │  │ - Survives restarts          │ │
        │  └──────────────────────────────┘ │
        └───────────────────────────────────┘
```

### 1.2 Component Responsibilities

#### MCP Server (Process 0)
**Port**: 3000 (configurable via `MCP_SERVER_PORT`)
**Technology**: FastAPI + MCP Python package

**Responsibilities**:
- Expose REST API for user interaction
- Route MCP messages between agents
- Manage agent registry (discovery, health)
- Orchestrate session workflow
- Manage context storage (Redis + filesystem)
- Handle session lifecycle (create, update, expire)

**Boundaries**:
- Does NOT implement business logic
- Does NOT call LLM APIs directly
- Does NOT perform data conversions
- Delegates all domain work to agents

#### Conversation Agent (Process 1)
**Technology**: Python process + MCP client + LLM SDK

**Responsibilities**:
- Initialize conversion sessions
- Detect data format (OpenEphys)
- Validate dataset structure (settings.xml, .continuous files)
- Extract metadata from all .md files using LLM
- Apply reasonable defaults for missing metadata
- Prompt users only on conversion/validation errors
- Coordinate agent handoffs (to conversion, evaluation)

**Boundaries**:
- Does NOT perform actual conversion (delegates to Conversion Agent)
- Does NOT run NWB validation (delegates to Evaluation Agent)
- Does NOT directly communicate with other agents (via MCP server only)

#### Conversion Agent (Process 2)
**Technology**: Python process + MCP client + NeuroConv + LLM SDK

**Responsibilities**:
- Execute OpenEphys to NWB conversion via NeuroConv
- Inject user metadata into NWB files
- Monitor conversion progress
- Capture errors with full details (message, stack trace, context)
- Generate user-friendly error messages via LLM
- Return conversion results to MCP server

**Boundaries**:
- Does NOT validate NWB files (delegates to Evaluation Agent)
- Does NOT prompt users directly (delegates to Conversation Agent)
- Does NOT manage session state (stateless, reads from context)

#### Evaluation Agent (Process 3)
**Technology**: Python process + MCP client + NWB Inspector + LLM SDK

**Responsibilities**:
- Validate NWB files using NWB Inspector
- Check schema compliance, best practices, integrity
- Categorize issues by severity (critical/warning/info)
- Generate JSON validation reports
- Create LLM-powered validation summaries
- Return evaluation results to MCP server

**Boundaries**:
- Does NOT fix validation issues automatically
- Does NOT rerun conversions
- Does NOT interact with users directly

---

## 2. Technology Stack

### 2.1 Core Dependencies

```toml
# From pixi.toml and pyproject.toml
python = "3.13"  # Exact version per constitution

# MCP and Server
mcp = ">=1.0.0"              # Model Context Protocol (model-agnostic)
fastapi = ">=0.100.0"        # REST API framework
uvicorn = ">=0.20.0"         # ASGI server

# Context Storage
redis = ">=5.0.0"            # Primary cache
aiofiles = ">=23.0.0"        # Async file I/O for filesystem persistence

# Data Validation
pydantic = ">=2.0.0"         # Data models and validation
pydantic-settings = ">=2.0.0" # Environment configuration

# LLM Providers
anthropic = ">=0.18.0"       # Claude API
openai = ">=1.0.0"           # OpenAI API

# Neuroscience Tools
neuroconv = ">=0.4.0"        # NWB conversion
pynwb = ">=3.1.2,<4"         # NWB file I/O
nwbinspector = ">=0.4.0"     # NWB validation

# HTTP Client
httpx = ">=0.24.0"           # Async HTTP client for agent-to-server communication

# Utilities
click = ">=8.0.0"            # CLI (for agent process management)
rich = ">=13.0.0"            # Terminal formatting
python-dotenv = ">=1.0.0"    # Environment loading
```

### 2.2 Development Dependencies

```toml
# Testing
pytest = ">=7.0.0"
pytest-asyncio = ">=0.21.0"
pytest-cov = ">=4.0.0"
pytest-mock = ">=3.10.0"
pytest-xdist = ">=3.0.0"
pytest-timeout = ">=2.4.0"

# Code Quality
ruff = ">=0.1.0"             # Linting and formatting
mypy = ">=1.5.0"             # Type checking
pre-commit = ">=3.0.0"       # Git hooks

# Development Tools
ipython = ">=8.0.0"
jupyter = ">=1.0.0"
```

### 2.3 Explicitly Excluded Technologies

These are **OUT OF SCOPE** for MVP:

- ❌ **Claude Agent SDK**: Model-specific (Claude-only), not model-agnostic
- ❌ **LiteLLM, LangChain, LlamaIndex**: Abstraction layers deferred to post-MVP
- ❌ **DataLad**: Provenance tracking deferred to post-MVP
- ❌ **LinkML, RDF libraries**: Knowledge graph features deferred
- ❌ **PostgreSQL**: Using Redis + filesystem for MVP
- ❌ **WebSocket libraries**: HTTP polling only for MVP
- ❌ **structlog**: Using Python standard logging

---

## 3. Data Models and Schemas

### 3.1 Session Context Model

**File**: `agentic_neurodata_conversion/models/session_context.py`

```python
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkflowStage(str, Enum):
    """Workflow stages for conversion pipeline."""
    INITIALIZED = "initialized"
    COLLECTING_METADATA = "collecting_metadata"
    CONVERTING = "converting"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentHistoryEntry(BaseModel):
    """Record of agent execution."""
    agent_name: str = Field(..., description="Name of agent that executed")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution end time")
    status: str = Field(..., description="success, failed, or in_progress")
    error_message: Optional[str] = Field(None, description="Error if failed")
    stack_trace: Optional[str] = Field(None, description="Stack trace if failed")


class DatasetInfo(BaseModel):
    """Basic dataset information."""
    dataset_path: str = Field(..., description="Absolute path to dataset")
    format: str = Field(..., description="Detected format (openephys)")
    total_size_bytes: int = Field(..., description="Total dataset size")
    file_count: int = Field(..., description="Number of files")
    channel_count: Optional[int] = Field(None, description="Number of channels")
    sampling_rate_hz: Optional[float] = Field(None, description="Sampling rate")
    duration_seconds: Optional[float] = Field(None, description="Recording duration")
    has_metadata_files: bool = Field(False, description="Whether .md files found")
    metadata_files: list[str] = Field(default_factory=list, description="List of .md file paths")


class MetadataExtractionResult(BaseModel):
    """Metadata extracted from .md files."""
    subject_id: Optional[str] = None
    species: Optional[str] = None
    age: Optional[str] = None
    sex: Optional[str] = None
    session_start_time: Optional[str] = None
    experimenter: Optional[str] = None
    device_name: Optional[str] = None
    manufacturer: Optional[str] = None
    recording_location: Optional[str] = None
    description: Optional[str] = None
    extraction_confidence: dict[str, str] = Field(
        default_factory=dict,
        description="Confidence per field: high, medium, low, default, empty"
    )
    llm_extraction_log: Optional[str] = Field(None, description="LLM extraction reasoning")


class ConversionResults(BaseModel):
    """Results from conversion agent."""
    nwb_file_path: Optional[str] = Field(None, description="Path to generated NWB file")
    conversion_duration_seconds: Optional[float] = None
    conversion_warnings: list[str] = Field(default_factory=list)
    conversion_errors: list[str] = Field(default_factory=list)
    conversion_log: Optional[str] = Field(None, description="Full conversion log")


class ValidationIssue(BaseModel):
    """Single validation issue from NWB Inspector."""
    severity: str = Field(..., description="critical, warning, or info")
    message: str = Field(..., description="Issue description")
    location: Optional[str] = Field(None, description="Location in file")
    check_name: str = Field(..., description="Name of validation check")


class ValidationResults(BaseModel):
    """Results from evaluation agent."""
    overall_status: str = Field(..., description="passed, passed_with_warnings, or failed")
    issue_count: dict[str, int] = Field(
        default_factory=dict,
        description="Counts by severity: critical, warning, info"
    )
    issues: list[ValidationIssue] = Field(default_factory=list)
    metadata_completeness_score: Optional[float] = Field(None, description="0.0-1.0")
    best_practices_score: Optional[float] = Field(None, description="0.0-1.0")
    validation_report_path: Optional[str] = Field(None, description="Path to JSON report")
    llm_validation_summary: Optional[str] = Field(None, description="LLM-generated summary")


class SessionContext(BaseModel):
    """Complete session context stored in Redis and filesystem."""
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    current_agent: Optional[str] = Field(None, description="Agent currently executing")
    workflow_stage: WorkflowStage = Field(default=WorkflowStage.INITIALIZED)
    agent_history: list[AgentHistoryEntry] = Field(default_factory=list)

    # Data collected during workflow
    dataset_info: Optional[DatasetInfo] = None
    metadata: Optional[MetadataExtractionResult] = None
    conversion_results: Optional[ConversionResults] = None
    validation_results: Optional[ValidationResults] = None

    # Output paths
    output_nwb_path: Optional[str] = None
    output_report_path: Optional[str] = None

    # Error tracking
    requires_user_clarification: bool = Field(default=False)
    clarification_prompt: Optional[str] = Field(None, description="Prompt for user")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### 3.2 MCP Message Model

**File**: `agentic_neurodata_conversion/models/mcp_message.py`

```python
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """MCP message types."""
    AGENT_REGISTER = "agent_register"        # Agent registration with server
    AGENT_EXECUTE = "agent_execute"          # Server requesting agent to execute
    AGENT_RESPONSE = "agent_response"        # Agent response with results
    CONTEXT_UPDATE = "context_update"        # Request to update session context
    ERROR = "error"                          # Error notification
    HEALTH_CHECK = "health_check"            # Agent health check
    HEALTH_RESPONSE = "health_response"      # Agent health status


class MCPMessage(BaseModel):
    """MCP protocol message for agent communication."""
    message_id: str = Field(..., description="Unique message identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent: str = Field(..., description="Sending agent name or 'mcp_server'")
    target_agent: str = Field(..., description="Receiving agent name or 'mcp_server'")
    session_id: Optional[str] = Field(None, description="Session context identifier")
    message_type: MessageType = Field(..., description="Message type")
    payload: dict[str, Any] = Field(default_factory=dict, description="Message payload")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Example payload structures by message type:

# AGENT_REGISTER payload:
# {
#     "agent_name": "conversation_agent",
#     "agent_type": "conversation",
#     "capabilities": ["format_detection", "metadata_extraction"],
#     "health_check_url": "http://localhost:3001/health"
# }

# AGENT_EXECUTE payload:
# {
#     "task": "initialize_session",
#     "session_id": "550e8400-e29b-41d4-a716-446655440000",
#     "parameters": {
#         "dataset_path": "/data/openephys_dataset"
#     }
# }

# AGENT_RESPONSE payload:
# {
#     "task": "initialize_session",
#     "status": "success",  # or "failed"
#     "result": {
#         "dataset_info": {...},
#         "next_agent": "conversion_agent"
#     },
#     "error": None  # or error details if failed
# }

# CONTEXT_UPDATE payload:
# {
#     "updates": {
#         "workflow_stage": "converting",
#         "current_agent": "conversion_agent"
#     }
# }
```

### 3.3 API Request/Response Models

**File**: `agentic_neurodata_conversion/models/api_models.py`

```python
from typing import Optional

from pydantic import BaseModel, Field


class SessionInitializeRequest(BaseModel):
    """Request to initialize conversion session."""
    dataset_path: str = Field(..., description="Absolute path to dataset")


class SessionInitializeResponse(BaseModel):
    """Response from session initialization."""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., description="User-facing message")
    workflow_stage: str = Field(..., description="Current stage")


class SessionStatusResponse(BaseModel):
    """Response from status check."""
    session_id: str = Field(..., description="Session identifier")
    workflow_stage: str = Field(..., description="Current stage")
    progress_percentage: int = Field(..., description="0-100")
    status_message: str = Field(..., description="Human-readable status")
    current_agent: Optional[str] = Field(None, description="Agent currently executing")
    requires_clarification: bool = Field(default=False)
    clarification_prompt: Optional[str] = Field(None)


class SessionClarifyRequest(BaseModel):
    """Request to provide clarification when errors occur."""
    user_input: str = Field(..., description="User's clarification/correction")
    updated_metadata: Optional[dict[str, str]] = Field(None, description="Updated metadata fields")


class SessionClarifyResponse(BaseModel):
    """Response after clarification provided."""
    message: str = Field(..., description="Acknowledgment message")
    workflow_stage: str = Field(..., description="Updated workflow stage")


class SessionResultResponse(BaseModel):
    """Response with final conversion results."""
    session_id: str = Field(..., description="Session identifier")
    nwb_file_path: Optional[str] = Field(None, description="Path to NWB file")
    validation_report_path: Optional[str] = Field(None, description="Path to validation report")
    overall_status: str = Field(..., description="passed, passed_with_warnings, or failed")
    summary: str = Field(..., description="LLM-generated summary")
    validation_issues: list[dict] = Field(default_factory=list, description="List of issues")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="healthy or unhealthy")
    version: str = Field(..., description="Server version")
    agents_registered: list[str] = Field(default_factory=list)
    redis_connected: bool = Field(..., description="Redis connection status")
```

---

## 4. Component Implementation Details

### 4.1 MCP Server

**File Structure**:
```
agentic_neurodata_conversion/mcp_server/
├── __init__.py
├── main.py                    # FastAPI application
├── message_router.py          # Message routing logic
├── agent_registry.py          # Agent discovery and health
├── context_manager.py         # Redis + filesystem
└── api/
    ├── __init__.py
    ├── sessions.py            # Session endpoints
    └── health.py              # Health check endpoint
```

#### main.py (FastAPI Application)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_neurodata_conversion.config import settings
from agentic_neurodata_conversion.mcp_server.api import health, sessions
from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter


app = FastAPI(
    title="Agentic Neurodata Conversion - MCP Server",
    version="0.1.0",
    description="MCP server for multi-agent NWB conversion pipeline"
)

# CORS middleware (development only, restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core components (singleton pattern)
context_manager = ContextManager(
    redis_url=settings.REDIS_URL,
    session_ttl=settings.REDIS_SESSION_TTL_SECONDS,
    filesystem_base_path=settings.SESSION_CONTEXT_PATH
)

agent_registry = AgentRegistry()

message_router = MessageRouter(
    agent_registry=agent_registry,
    context_manager=context_manager
)

# Store in app state for access in endpoints
app.state.context_manager = context_manager
app.state.agent_registry = agent_registry
app.state.message_router = message_router

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])


@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup."""
    await context_manager.connect()
    print(f"MCP Server started on port {settings.MCP_SERVER_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection on shutdown."""
    await context_manager.disconnect()
```

#### context_manager.py (Redis + Filesystem)

```python
import json
from pathlib import Path
from typing import Optional

import redis.asyncio as redis
from pydantic import BaseModel

from agentic_neurodata_conversion.models.session_context import SessionContext


class ContextManager:
    """Manages session context with Redis (primary) + filesystem (backup)."""

    def __init__(
        self,
        redis_url: str,
        session_ttl: int,
        filesystem_base_path: str
    ):
        self.redis_url = redis_url
        self.session_ttl = session_ttl
        self.filesystem_base_path = Path(filesystem_base_path)
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self.redis_client = await redis.from_url(
            self.redis_url,
            decode_responses=True
        )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()

    def _get_redis_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:{session_id}"

    def _get_filesystem_path(self, session_id: str) -> Path:
        """Generate filesystem path for session."""
        return self.filesystem_base_path / f"{session_id}.json"

    async def create_session(self, session: SessionContext) -> None:
        """Create new session context (write-through to Redis + filesystem)."""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        session_json = session.model_dump_json()

        # Write to Redis with TTL
        await self.redis_client.set(
            self._get_redis_key(session.session_id),
            session_json,
            ex=self.session_ttl
        )

        # Write to filesystem
        fs_path = self._get_filesystem_path(session.session_id)
        fs_path.parent.mkdir(parents=True, exist_ok=True)
        fs_path.write_text(session_json)

    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get session context (try Redis first, fallback to filesystem)."""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        # Try Redis first
        session_json = await self.redis_client.get(self._get_redis_key(session_id))

        if session_json:
            return SessionContext.model_validate_json(session_json)

        # Fallback to filesystem
        fs_path = self._get_filesystem_path(session_id)
        if fs_path.exists():
            session_json = fs_path.read_text()
            # Restore to Redis
            await self.redis_client.set(
                self._get_redis_key(session_id),
                session_json,
                ex=self.session_ttl
            )
            return SessionContext.model_validate_json(session_json)

        return None

    async def update_session(self, session: SessionContext) -> None:
        """Update session context (write-through to Redis + filesystem)."""
        from datetime import datetime
        session.last_updated = datetime.utcnow()
        await self.create_session(session)  # Same logic as create

    async def delete_session(self, session_id: str) -> None:
        """Delete session from Redis and filesystem."""
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")

        # Delete from Redis
        await self.redis_client.delete(self._get_redis_key(session_id))

        # Delete from filesystem
        fs_path = self._get_filesystem_path(session_id)
        if fs_path.exists():
            fs_path.unlink()
```

#### message_router.py (Message Routing)

```python
import uuid
from datetime import datetime
from typing import Optional

import httpx

from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType
from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager


class MessageRouter:
    """Routes MCP messages between agents."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        context_manager: ContextManager
    ):
        self.agent_registry = agent_registry
        self.context_manager = context_manager
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def send_message(
        self,
        target_agent: str,
        message_type: MessageType,
        session_id: Optional[str] = None,
        payload: dict = None
    ) -> dict:
        """Send message to agent via HTTP."""
        agent_info = self.agent_registry.get_agent(target_agent)
        if not agent_info:
            raise ValueError(f"Agent '{target_agent}' not registered")

        message = MCPMessage(
            message_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            source_agent="mcp_server",
            target_agent=target_agent,
            session_id=session_id,
            message_type=message_type,
            payload=payload or {}
        )

        # Send HTTP POST to agent
        response = await self.http_client.post(
            f"{agent_info['base_url']}/mcp/message",
            json=message.model_dump(mode='json')
        )
        response.raise_for_status()

        return response.json()

    async def execute_agent_task(
        self,
        agent_name: str,
        task: str,
        session_id: str,
        parameters: dict = None
    ) -> dict:
        """Execute task on agent and wait for response."""
        payload = {
            "task": task,
            "session_id": session_id,
            "parameters": parameters or {}
        }

        response = await self.send_message(
            target_agent=agent_name,
            message_type=MessageType.AGENT_EXECUTE,
            session_id=session_id,
            payload=payload
        )

        return response
```

#### agent_registry.py (Agent Discovery)

```python
from typing import Optional


class AgentRegistry:
    """Registry for agent discovery and health tracking."""

    def __init__(self):
        self.agents: dict[str, dict] = {}

    def register_agent(
        self,
        agent_name: str,
        agent_type: str,
        base_url: str,
        capabilities: list[str]
    ) -> None:
        """Register agent with server."""
        self.agents[agent_name] = {
            "agent_name": agent_name,
            "agent_type": agent_type,
            "base_url": base_url,
            "capabilities": capabilities,
            "status": "healthy"
        }

    def get_agent(self, agent_name: str) -> Optional[dict]:
        """Get agent info by name."""
        return self.agents.get(agent_name)

    def list_agents(self) -> list[dict]:
        """List all registered agents."""
        return list(self.agents.values())

    def unregister_agent(self, agent_name: str) -> None:
        """Remove agent from registry."""
        if agent_name in self.agents:
            del self.agents[agent_name]
```

#### api/sessions.py (REST API Endpoints)

```python
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from agentic_neurodata_conversion.models.api_models import (
    SessionInitializeRequest,
    SessionInitializeResponse,
    SessionStatusResponse,
    SessionClarifyRequest,
    SessionClarifyResponse,
    SessionResultResponse
)
from agentic_neurodata_conversion.models.session_context import (
    SessionContext,
    WorkflowStage,
    AgentHistoryEntry
)

router = APIRouter()


@router.post("/sessions/initialize", response_model=SessionInitializeResponse)
async def initialize_session(
    request: SessionInitializeRequest,
    req: Request
) -> SessionInitializeResponse:
    """Initialize new conversion session."""
    context_manager = req.app.state.context_manager
    message_router = req.app.state.message_router

    # Create session context
    session_id = str(uuid.uuid4())
    session = SessionContext(
        session_id=session_id,
        workflow_stage=WorkflowStage.INITIALIZED
    )

    # Persist session
    await context_manager.create_session(session)

    # Send message to conversation agent to start initialization
    try:
        await message_router.execute_agent_task(
            agent_name="conversation_agent",
            task="initialize_session",
            session_id=session_id,
            parameters={"dataset_path": request.dataset_path}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")

    return SessionInitializeResponse(
        session_id=session_id,
        message="Session initialized successfully. Analyzing dataset...",
        workflow_stage=session.workflow_stage.value
    )


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    req: Request
) -> SessionStatusResponse:
    """Get current session status."""
    context_manager = req.app.state.context_manager

    session = await context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Calculate progress percentage
    stage_progress = {
        WorkflowStage.INITIALIZED: 10,
        WorkflowStage.COLLECTING_METADATA: 30,
        WorkflowStage.CONVERTING: 60,
        WorkflowStage.EVALUATING: 80,
        WorkflowStage.COMPLETED: 100,
        WorkflowStage.FAILED: 0
    }

    return SessionStatusResponse(
        session_id=session_id,
        workflow_stage=session.workflow_stage.value,
        progress_percentage=stage_progress.get(session.workflow_stage, 0),
        status_message=f"Current stage: {session.workflow_stage.value}",
        current_agent=session.current_agent,
        requires_clarification=session.requires_user_clarification,
        clarification_prompt=session.clarification_prompt
    )


@router.post("/sessions/{session_id}/clarify", response_model=SessionClarifyResponse)
async def clarify_session(
    session_id: str,
    request: SessionClarifyRequest,
    req: Request
) -> SessionClarifyResponse:
    """Provide clarification for errors."""
    context_manager = req.app.state.context_manager
    message_router = req.app.state.message_router

    session = await context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Send clarification to conversation agent
    try:
        await message_router.execute_agent_task(
            agent_name="conversation_agent",
            task="handle_clarification",
            session_id=session_id,
            parameters={
                "user_input": request.user_input,
                "updated_metadata": request.updated_metadata
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process clarification: {str(e)}")

    # Get updated session
    session = await context_manager.get_session(session_id)

    return SessionClarifyResponse(
        message="Clarification received. Retrying conversion...",
        workflow_stage=session.workflow_stage.value
    )


@router.get("/sessions/{session_id}/result", response_model=SessionResultResponse)
async def get_session_result(
    session_id: str,
    req: Request
) -> SessionResultResponse:
    """Get final conversion results."""
    context_manager = req.app.state.context_manager

    session = await context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.workflow_stage != WorkflowStage.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Session not completed yet. Current stage: {session.workflow_stage.value}"
        )

    validation_results = session.validation_results
    overall_status = validation_results.overall_status if validation_results else "unknown"
    summary = validation_results.llm_validation_summary if validation_results else "No validation performed"
    issues = [issue.model_dump() for issue in validation_results.issues] if validation_results else []

    return SessionResultResponse(
        session_id=session_id,
        nwb_file_path=session.output_nwb_path,
        validation_report_path=session.output_report_path,
        overall_status=overall_status,
        summary=summary,
        validation_issues=issues
    )
```

#### api/internal.py (Internal Agent Communication Endpoints)

```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class AgentRegistrationRequest(BaseModel):
    """Request to register agent with server."""
    agent_name: str
    agent_type: str
    capabilities: list[str]
    base_url: str


@router.post("/internal/register_agent")
async def register_agent(
    request: AgentRegistrationRequest,
    req: Request
) -> dict:
    """Internal endpoint for agent registration."""
    agent_registry = req.app.state.agent_registry

    agent_registry.register_agent(
        agent_name=request.agent_name,
        agent_type=request.agent_type,
        base_url=request.base_url,
        capabilities=request.capabilities
    )

    return {
        "status": "registered",
        "agent_name": request.agent_name
    }


@router.get("/internal/sessions/{session_id}/context")
async def get_session_context(
    session_id: str,
    req: Request
) -> dict:
    """Internal endpoint for agents to get session context."""
    context_manager = req.app.state.context_manager

    session = await context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session.model_dump(mode='json')


@router.patch("/internal/sessions/{session_id}/context")
async def update_session_context(
    session_id: str,
    updates: dict,
    req: Request
) -> dict:
    """Internal endpoint for agents to update session context."""
    context_manager = req.app.state.context_manager

    session = await context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Apply updates
    for key, value in updates.items():
        if hasattr(session, key):
            setattr(session, key, value)

    # Persist updated session
    await context_manager.update_session(session)

    return {"status": "updated"}


class RouteMessageRequest(BaseModel):
    """Request to route message to agent."""
    target_agent: str
    message_type: str
    session_id: str
    payload: dict


@router.post("/internal/route_message")
async def route_message(
    request: RouteMessageRequest,
    req: Request
) -> dict:
    """Internal endpoint to route messages between agents."""
    message_router = req.app.state.message_router

    from agentic_neurodata_conversion.models.mcp_message import MessageType

    response = await message_router.send_message(
        target_agent=request.target_agent,
        message_type=MessageType(request.message_type),
        session_id=request.session_id,
        payload=request.payload
    )

    return response
```

**Update main.py to include internal router**:

```python
# In main.py, add:
from agentic_neurodata_conversion.mcp_server.api import health, sessions, internal

# Include internal router
app.include_router(internal.router, tags=["internal"])
```

---

### 4.2 Base Agent Class

**File**: `agentic_neurodata_conversion/agents/base_agent.py`

```python
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx
from anthropic import Anthropic
from openai import OpenAI

from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType
from agentic_neurodata_conversion.models.session_context import SessionContext


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_name = config.agent_name
        self.agent_type = config.agent_type
        self.logger = logging.getLogger(f"agent.{self.agent_name}")

        # Initialize LLM client based on provider
        self.llm_client = self._initialize_llm_client()

        # HTTP client for MCP server communication
        self.http_client = httpx.AsyncClient(timeout=60.0)

    def _initialize_llm_client(self) -> Any:
        """Initialize LLM client based on configured provider."""
        if self.config.llm_provider == "anthropic":
            return Anthropic(api_key=self.config.llm_api_key)
        elif self.config.llm_provider == "openai":
            return OpenAI(api_key=self.config.llm_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")

    async def register_with_server(self) -> None:
        """Register agent with MCP server."""
        registration_payload = {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "capabilities": self.get_capabilities(),
            "base_url": f"http://localhost:{self.config.port}"
        }

        try:
            response = await self.http_client.post(
                f"{self.config.mcp_server_url}/internal/register_agent",
                json=registration_payload
            )
            response.raise_for_status()
            self.logger.info(f"Agent '{self.agent_name}' registered successfully")
        except Exception as e:
            self.logger.error(f"Failed to register with server: {e}")
            raise

    async def get_session_context(self, session_id: str) -> SessionContext:
        """Get session context from MCP server."""
        response = await self.http_client.get(
            f"{self.config.mcp_server_url}/internal/sessions/{session_id}/context"
        )
        response.raise_for_status()
        return SessionContext.model_validate(response.json())

    async def update_session_context(
        self,
        session_id: str,
        updates: dict[str, Any]
    ) -> None:
        """Update session context via MCP server."""
        response = await self.http_client.patch(
            f"{self.config.mcp_server_url}/internal/sessions/{session_id}/context",
            json=updates
        )
        response.raise_for_status()

    async def call_llm(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        max_retries: int = 5
    ) -> str:
        """Call LLM based on configured provider with exponential backoff retry logic."""
        import asyncio
        from anthropic import RateLimitError as AnthropicRateLimitError, APIError as AnthropicAPIError
        from openai import RateLimitError as OpenAIRateLimitError, APIError as OpenAIAPIError

        for attempt in range(max_retries):
            try:
                if self.config.llm_provider == "anthropic":
                    messages = [{"role": "user", "content": prompt}]

                    response = self.llm_client.messages.create(
                        model=self.config.llm_model,
                        max_tokens=self.config.llm_max_tokens,
                        temperature=self.config.llm_temperature,
                        top_p=self.config.llm_top_p,
                        messages=messages,
                        system=system_message or ""
                    )
                    return response.content[0].text

                elif self.config.llm_provider == "openai":
                    messages = []
                    if system_message:
                        messages.append({"role": "system", "content": system_message})
                    messages.append({"role": "user", "content": prompt})

                    response = self.llm_client.chat.completions.create(
                        model=self.config.llm_model,
                        max_tokens=self.config.llm_max_tokens,
                        temperature=self.config.llm_temperature,
                        top_p=self.config.llm_top_p,
                        messages=messages
                    )
                    return response.choices[0].message.content

                else:
                    raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")

            except (AnthropicRateLimitError, OpenAIRateLimitError) as e:
                # Rate limit error - retry with exponential backoff
                if attempt == max_retries - 1:
                    self.logger.error(f"LLM rate limit exceeded after {max_retries} attempts")
                    raise

                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                self.logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)

            except (AnthropicAPIError, OpenAIAPIError) as e:
                # API error - retry with shorter backoff for transient issues
                if attempt == max_retries - 1:
                    self.logger.error(f"LLM API error after {max_retries} attempts: {str(e)}")
                    raise

                wait_time = 1 + attempt  # Linear backoff: 1s, 2s, 3s, 4s, 5s
                self.logger.warning(f"API error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {str(e)}")
                await asyncio.sleep(wait_time)

            except Exception as e:
                # Unexpected error - don't retry
                self.logger.error(f"Unexpected LLM error: {str(e)}")
                raise

        raise RuntimeError("LLM call failed after all retries")

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        pass

    @abstractmethod
    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """Handle incoming MCP message."""
        pass

    def create_agent_server(self) -> "FastAPI":
        """Create FastAPI server for agent to receive MCP messages."""
        from fastapi import FastAPI, HTTPException

        app = FastAPI(
            title=f"{self.agent_name} HTTP Server",
            version="0.1.0",
            description=f"HTTP server for {self.agent_name} to receive MCP messages"
        )

        @app.post("/mcp/message")
        async def receive_mcp_message(message: MCPMessage) -> dict:
            """Endpoint to receive MCP messages from MCP server."""
            try:
                self.logger.info(f"Received MCP message: {message.message_type}")
                result = await self.handle_message(message)
                return result
            except Exception as e:
                self.logger.error(f"Error handling message: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/health")
        async def health_check() -> dict:
            """Health check endpoint."""
            return {
                "status": "healthy",
                "agent_name": self.agent_name,
                "agent_type": self.agent_type
            }

        return app

    async def start_server(self) -> None:
        """Start the agent's HTTP server and register with MCP server."""
        import uvicorn

        # Register with MCP server
        await self.register_with_server()

        # Start HTTP server
        app = self.create_agent_server()
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=self.config.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
```

### 4.2.1 Agent HTTP Server Implementation

Each agent runs as a separate FastAPI application on its own port:

**Agent Ports**:
- Conversation Agent: Port 3001
- Conversion Agent: Port 3002
- Evaluation Agent: Port 3003

**Agent Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mcp/message` | Receive MCP messages from server |
| GET | `/health` | Health check endpoint |

**Example Agent Startup**:

```python
# File: agentic_neurodata_conversion/agents/__main__.py

import asyncio
import sys

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.agents.conversion_agent import ConversionAgent
from agentic_neurodata_conversion.agents.evaluation_agent import EvaluationAgent
from agentic_neurodata_conversion.config import (
    get_conversation_agent_config,
    get_conversion_agent_config,
    get_evaluation_agent_config
)


async def start_agent(agent_type: str):
    """Start specific agent based on type."""
    if agent_type == "conversation":
        config = get_conversation_agent_config()
        agent = ConversationAgent(config)
    elif agent_type == "conversion":
        config = get_conversion_agent_config()
        agent = ConversionAgent(config)
    elif agent_type == "evaluation":
        config = get_evaluation_agent_config()
        agent = EvaluationAgent(config)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

    print(f"Starting {agent_type} agent on port {config.port}...")
    await agent.start_server()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m agentic_neurodata_conversion.agents <agent_type>")
        print("Agent types: conversation, conversion, evaluation")
        sys.exit(1)

    agent_type = sys.argv[1]
    asyncio.run(start_agent(agent_type))
```

---

### 4.3 Conversation Agent

**File**: `agentic_neurodata_conversion/agents/conversation_agent.py`

```python
import logging
from pathlib import Path
from typing import Any

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType
from agentic_neurodata_conversion.models.session_context import (
    DatasetInfo,
    MetadataExtractionResult,
    WorkflowStage,
    AgentHistoryEntry
)


class ConversationAgent(BaseAgent):
    """Conversation agent for session initialization and metadata extraction."""

    def get_capabilities(self) -> list[str]:
        return [
            "session_initialization",
            "format_detection",
            "metadata_extraction",
            "dataset_validation"
        ]

    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """Handle incoming MCP message."""
        if message.message_type == MessageType.AGENT_EXECUTE:
            task = message.payload.get("task")

            if task == "initialize_session":
                return await self._initialize_session(message)
            elif task == "handle_clarification":
                return await self._handle_clarification(message)
            else:
                raise ValueError(f"Unknown task: {task}")

        raise ValueError(f"Unsupported message type: {message.message_type}")

    async def _initialize_session(self, message: MCPMessage) -> dict[str, Any]:
        """Initialize conversion session."""
        session_id = message.session_id
        dataset_path = message.payload["parameters"]["dataset_path"]

        self.logger.info(f"Initializing session {session_id} for dataset {dataset_path}")

        # Get session context
        session = await self.get_session_context(session_id)

        # Detect format
        dataset_format = self._detect_format(dataset_path)
        if dataset_format != "openephys":
            return {
                "status": "failed",
                "error": f"Unsupported format: {dataset_format}. Only OpenEphys is supported."
            }

        # Validate dataset structure
        dataset_info = self._validate_openephys_structure(dataset_path)

        # Extract metadata from .md files
        metadata = await self._extract_metadata_from_md_files(dataset_path)

        # Update session context
        await self.update_session_context(
            session_id,
            {
                "workflow_stage": WorkflowStage.COLLECTING_METADATA.value,
                "dataset_info": dataset_info.model_dump(),
                "metadata": metadata.model_dump(),
                "current_agent": "conversation_agent"
            }
        )

        # Trigger conversion agent
        await self._trigger_conversion(session_id)

        return {
            "status": "success",
            "result": {
                "dataset_info": dataset_info.model_dump(),
                "metadata": metadata.model_dump()
            }
        }

    def _detect_format(self, dataset_path: str) -> str:
        """Detect dataset format (OpenEphys only for MVP)."""
        path = Path(dataset_path)

        # Check for settings.xml (OpenEphys marker)
        if (path / "settings.xml").exists():
            return "openephys"

        # Check for .continuous files
        continuous_files = list(path.glob("*.continuous"))
        if continuous_files:
            return "openephys"

        return "unknown"

    def _validate_openephys_structure(self, dataset_path: str) -> DatasetInfo:
        """Validate OpenEphys dataset structure."""
        path = Path(dataset_path)

        # Check settings.xml
        settings_xml = path / "settings.xml"
        if not settings_xml.exists():
            raise ValueError("Missing settings.xml file")

        # Check .continuous files
        continuous_files = list(path.glob("*.continuous"))
        if not continuous_files:
            raise ValueError("No .continuous files found")

        # Calculate dataset size
        total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

        # Find .md files
        md_files = list(path.glob("*.md"))

        # Extract basic info (sampling rate, channels from settings.xml)
        # TODO: Parse settings.xml for detailed info

        return DatasetInfo(
            dataset_path=str(path.absolute()),
            format="openephys",
            total_size_bytes=total_size,
            file_count=len(continuous_files),
            channel_count=len(continuous_files),  # Simplified
            sampling_rate_hz=30000.0,  # Default, should parse from settings.xml
            duration_seconds=None,  # Calculate from file sizes
            has_metadata_files=len(md_files) > 0,
            metadata_files=[str(f.absolute()) for f in md_files]
        )

    async def _extract_metadata_from_md_files(
        self,
        dataset_path: str
    ) -> MetadataExtractionResult:
        """Extract metadata from all .md files using LLM."""
        path = Path(dataset_path)
        md_files = list(path.glob("*.md"))

        if not md_files:
            self.logger.info("No .md files found, returning empty metadata")
            return MetadataExtractionResult()

        # Read all .md files
        combined_content = []
        for md_file in md_files:
            combined_content.append(f"## File: {md_file.name}\n\n{md_file.read_text()}\n\n")

        md_content = "\n".join(combined_content)

        # Use LLM to extract metadata
        prompt = f"""You are extracting metadata from neuroscience dataset documentation.

Read the following markdown files and extract these fields:
- subject_id: Identifier for the experimental subject
- species: Species name (use scientific name like "Mus musculus" for mouse)
- age: Subject age
- sex: Subject sex (M/F/Unknown)
- session_start_time: Recording start time (ISO 8601 format)
- experimenter: Name(s) of experimenter(s)
- device_name: Recording device name
- manufacturer: Device manufacturer
- recording_location: Brain region or recording location
- description: Brief experiment description

Apply reasonable defaults when ambiguous (e.g., "mouse" → "Mus musculus").
Leave fields empty if not mentioned.

Markdown content:
{md_content}

Return ONLY a JSON object with extracted fields and extraction_confidence for each field (high/medium/low/default/empty).
"""

        system_message = "You extract metadata from neuroscience documentation with high accuracy."

        llm_response = await self.call_llm(prompt, system_message)

        # Parse LLM response (expecting JSON)
        import json
        try:
            extracted = json.loads(llm_response)
            return MetadataExtractionResult(
                subject_id=extracted.get("subject_id"),
                species=extracted.get("species"),
                age=extracted.get("age"),
                sex=extracted.get("sex"),
                session_start_time=extracted.get("session_start_time"),
                experimenter=extracted.get("experimenter"),
                device_name=extracted.get("device_name"),
                manufacturer=extracted.get("manufacturer"),
                recording_location=extracted.get("recording_location"),
                description=extracted.get("description"),
                extraction_confidence=extracted.get("extraction_confidence", {}),
                llm_extraction_log=llm_response
            )
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            return MetadataExtractionResult(llm_extraction_log=llm_response)

    async def _trigger_conversion(self, session_id: str) -> None:
        """Trigger conversion agent via MCP server."""
        # Send message to MCP server to route to conversion agent
        response = await self.http_client.post(
            f"{self.config.mcp_server_url}/internal/route_message",
            json={
                "target_agent": "conversion_agent",
                "message_type": MessageType.AGENT_EXECUTE.value,
                "session_id": session_id,
                "payload": {
                    "task": "convert_to_nwb"
                }
            }
        )
        response.raise_for_status()

    async def _handle_clarification(self, message: MCPMessage) -> dict[str, Any]:
        """Handle user clarification after errors."""
        session_id = message.session_id
        user_input = message.payload["parameters"]["user_input"]
        updated_metadata = message.payload["parameters"].get("updated_metadata")

        self.logger.info(f"Handling clarification for session {session_id}")

        # Get session context
        session = await self.get_session_context(session_id)

        # Update metadata if provided
        if updated_metadata:
            for key, value in updated_metadata.items():
                setattr(session.metadata, key, value)

        # Update session context
        await self.update_session_context(
            session_id,
            {
                "metadata": session.metadata.model_dump(),
                "requires_user_clarification": False,
                "clarification_prompt": None
            }
        )

        # Retry conversion
        await self._trigger_conversion(session_id)

        return {
            "status": "success",
            "result": {"message": "Clarification processed, retrying conversion"}
        }
```

### 4.4 Conversion Agent

**File**: `agentic_neurodata_conversion/agents/conversion_agent.py`

```python
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from neuroconv.datainterfaces import OpenEphysRecordingInterface

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType
from agentic_neurodata_conversion.models.session_context import (
    ConversionResults,
    WorkflowStage
)


class ConversionAgent(BaseAgent):
    """Conversion agent for OpenEphys to NWB conversion."""

    def get_capabilities(self) -> list[str]:
        return [
            "openephys_conversion",
            "nwb_generation",
            "error_formatting"
        ]

    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """Handle incoming MCP message."""
        if message.message_type == MessageType.AGENT_EXECUTE:
            task = message.payload.get("task")

            if task == "convert_to_nwb":
                return await self._convert_to_nwb(message)
            else:
                raise ValueError(f"Unknown task: {task}")

        raise ValueError(f"Unsupported message type: {message.message_type}")

    async def _convert_to_nwb(self, message: MCPMessage) -> dict[str, Any]:
        """Convert OpenEphys data to NWB format."""
        session_id = message.session_id

        self.logger.info(f"Starting NWB conversion for session {session_id}")

        # Get session context
        session = await self.get_session_context(session_id)

        # Update workflow stage
        await self.update_session_context(
            session_id,
            {
                "workflow_stage": WorkflowStage.CONVERTING.value,
                "current_agent": "conversion_agent"
            }
        )

        start_time = datetime.utcnow()

        try:
            # Initialize NeuroConv interface
            interface = OpenEphysRecordingInterface(
                folder_path=session.dataset_info.dataset_path
            )

            # Prepare metadata
            metadata = self._prepare_metadata(session)

            # Set output path
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_nwb_path = output_dir / f"{session_id}.nwb"

            # Run conversion
            interface.run_conversion(
                nwbfile_path=str(output_nwb_path),
                metadata=metadata,
                overwrite=True,
                compression="gzip"
            )

            duration = (datetime.utcnow() - start_time).total_seconds()

            # Store results
            conversion_results = ConversionResults(
                nwb_file_path=str(output_nwb_path),
                conversion_duration_seconds=duration,
                conversion_warnings=[],
                conversion_errors=[],
                conversion_log="Conversion completed successfully"
            )

            # Update session context
            await self.update_session_context(
                session_id,
                {
                    "conversion_results": conversion_results.model_dump(),
                    "output_nwb_path": str(output_nwb_path)
                }
            )

            # Trigger evaluation agent
            await self._trigger_evaluation(session_id)

            return {
                "status": "success",
                "result": conversion_results.model_dump()
            }

        except Exception as e:
            # Capture full error details
            error_message = str(e)
            stack_trace = traceback.format_exc()

            self.logger.error(f"Conversion failed: {error_message}")

            # Generate user-friendly error message via LLM
            user_friendly_error = await self._generate_error_message(
                error_message,
                stack_trace,
                session
            )

            # Update session context with error
            conversion_results = ConversionResults(
                nwb_file_path=None,
                conversion_duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                conversion_warnings=[],
                conversion_errors=[user_friendly_error],
                conversion_log=stack_trace
            )

            await self.update_session_context(
                session_id,
                {
                    "conversion_results": conversion_results.model_dump(),
                    "workflow_stage": WorkflowStage.FAILED.value,
                    "requires_user_clarification": True,
                    "clarification_prompt": user_friendly_error
                }
            )

            return {
                "status": "failed",
                "error": user_friendly_error,
                "stack_trace": stack_trace
            }

    def _prepare_metadata(self, session) -> dict:
        """Prepare metadata for NWB file."""
        metadata = {}

        if session.metadata:
            # Subject metadata
            if session.metadata.subject_id:
                metadata["Subject"] = {
                    "subject_id": session.metadata.subject_id,
                    "species": session.metadata.species or "",
                    "age": session.metadata.age or "",
                    "sex": session.metadata.sex or ""
                }

            # Session metadata
            metadata["NWBFile"] = {
                "session_start_time": session.metadata.session_start_time or datetime.utcnow().isoformat(),
                "experimenter": [session.metadata.experimenter] if session.metadata.experimenter else [],
                "session_description": session.metadata.description or "OpenEphys recording session"
            }

            # Device metadata
            if session.metadata.device_name:
                metadata["Device"] = [{
                    "name": session.metadata.device_name,
                    "description": f"Manufactured by {session.metadata.manufacturer or 'Unknown'}"
                }]

        return metadata

    async def _generate_error_message(
        self,
        error_message: str,
        stack_trace: str,
        session
    ) -> str:
        """Generate user-friendly error message via LLM."""
        prompt = f"""You are a neuroscience data conversion expert helping users fix errors.

An error occurred during OpenEphys to NWB conversion:

Error: {error_message}

Stack trace:
{stack_trace}

Dataset info:
- Path: {session.dataset_info.dataset_path}
- Format: {session.dataset_info.format}
- Size: {session.dataset_info.total_size_bytes / 1e9:.2f} GB
- Channels: {session.dataset_info.channel_count}

Generate a user-friendly error message that:
1. Explains what went wrong in plain language
2. Suggests 2-3 specific remediation steps
3. Indicates if user clarification is needed

Keep response under 200 words and be actionable.
"""

        system_message = "You explain technical errors clearly and provide actionable solutions."

        return await self.call_llm(prompt, system_message)

    async def _trigger_evaluation(self, session_id: str) -> None:
        """Trigger evaluation agent via MCP server."""
        response = await self.http_client.post(
            f"{self.config.mcp_server_url}/internal/route_message",
            json={
                "target_agent": "evaluation_agent",
                "message_type": MessageType.AGENT_EXECUTE.value,
                "session_id": session_id,
                "payload": {
                    "task": "validate_nwb"
                }
            }
        )
        response.raise_for_status()
```

### 4.5 Evaluation Agent

**File**: `agentic_neurodata_conversion/agents/evaluation_agent.py`

```python
import json
import logging
from pathlib import Path
from typing import Any

from nwbinspector import inspect_nwb

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType
from agentic_neurodata_conversion.models.session_context import (
    ValidationIssue,
    ValidationResults,
    WorkflowStage
)


class EvaluationAgent(BaseAgent):
    """Evaluation agent for NWB validation."""

    def get_capabilities(self) -> list[str]:
        return [
            "nwb_validation",
            "report_generation",
            "validation_summary"
        ]

    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """Handle incoming MCP message."""
        if message.message_type == MessageType.AGENT_EXECUTE:
            task = message.payload.get("task")

            if task == "validate_nwb":
                return await self._validate_nwb(message)
            else:
                raise ValueError(f"Unknown task: {task}")

        raise ValueError(f"Unsupported message type: {message.message_type}")

    async def _validate_nwb(self, message: MCPMessage) -> dict[str, Any]:
        """Validate NWB file using NWB Inspector."""
        session_id = message.session_id

        self.logger.info(f"Starting NWB validation for session {session_id}")

        # Get session context
        session = await self.get_session_context(session_id)

        # Update workflow stage
        await self.update_session_context(
            session_id,
            {
                "workflow_stage": WorkflowStage.EVALUATING.value,
                "current_agent": "evaluation_agent"
            }
        )

        nwb_file_path = session.output_nwb_path

        if not nwb_file_path or not Path(nwb_file_path).exists():
            return {
                "status": "failed",
                "error": "NWB file not found"
            }

        # Run NWB Inspector
        validation_issues = []
        issue_count = {"critical": 0, "warning": 0, "info": 0}

        for issue in inspect_nwb(nwbfile_path=nwb_file_path):
            severity = issue.severity.name.lower()
            issue_count[severity] = issue_count.get(severity, 0) + 1

            validation_issues.append(
                ValidationIssue(
                    severity=severity,
                    message=issue.message,
                    location=issue.location if hasattr(issue, 'location') else None,
                    check_name=issue.check_function_name
                )
            )

        # Determine overall status
        if issue_count.get("critical", 0) > 0:
            overall_status = "failed"
        elif issue_count.get("warning", 0) > 0:
            overall_status = "passed_with_warnings"
        else:
            overall_status = "passed"

        # Generate validation report
        report_path = self._generate_report(session_id, validation_issues, overall_status)

        # Generate LLM summary
        llm_summary = await self._generate_validation_summary(
            validation_issues,
            overall_status,
            session
        )

        # Store results
        validation_results = ValidationResults(
            overall_status=overall_status,
            issue_count=issue_count,
            issues=validation_issues,
            metadata_completeness_score=self._calculate_metadata_score(session),
            best_practices_score=self._calculate_best_practices_score(validation_issues),
            validation_report_path=str(report_path),
            llm_validation_summary=llm_summary
        )

        # Update session context
        await self.update_session_context(
            session_id,
            {
                "validation_results": validation_results.model_dump(),
                "output_report_path": str(report_path),
                "workflow_stage": WorkflowStage.COMPLETED.value,
                "current_agent": None
            }
        )

        return {
            "status": "success",
            "result": validation_results.model_dump()
        }

    def _generate_report(
        self,
        session_id: str,
        validation_issues: list[ValidationIssue],
        overall_status: str
    ) -> Path:
        """Generate JSON validation report."""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"{session_id}_validation_report.json"

        report = {
            "session_id": session_id,
            "overall_status": overall_status,
            "issues": [issue.model_dump() for issue in validation_issues]
        }

        report_path.write_text(json.dumps(report, indent=2))

        return report_path

    async def _generate_validation_summary(
        self,
        validation_issues: list[ValidationIssue],
        overall_status: str,
        session
    ) -> str:
        """Generate LLM-powered validation summary."""
        issues_text = "\n".join([
            f"- [{issue.severity.upper()}] {issue.message} (at {issue.location or 'unknown'})"
            for issue in validation_issues[:20]  # Limit to first 20
        ])

        prompt = f"""You are a neuroscience data quality expert reviewing NWB file validation.

Validation Status: {overall_status}
Total Issues: {len(validation_issues)}

Issues (showing first 20):
{issues_text}

Generate a concise summary (under 150 words) that:
1. States overall validation result
2. Highlights most critical issues (if any)
3. Provides actionable recommendations
4. Indicates if file is ready for use/sharing

Be clear and direct.
"""

        system_message = "You explain validation results clearly and provide actionable guidance."

        return await self.call_llm(prompt, system_message)

    def _calculate_metadata_score(self, session) -> float:
        """Calculate metadata completeness score (0.0-1.0)."""
        if not session.metadata:
            return 0.0

        fields = [
            session.metadata.subject_id,
            session.metadata.species,
            session.metadata.age,
            session.metadata.sex,
            session.metadata.session_start_time,
            session.metadata.experimenter,
            session.metadata.device_name,
            session.metadata.manufacturer,
            session.metadata.recording_location,
            session.metadata.description
        ]

        filled_fields = sum(1 for f in fields if f)
        return filled_fields / len(fields)

    def _calculate_best_practices_score(
        self,
        validation_issues: list[ValidationIssue]
    ) -> float:
        """Calculate best practices score (0.0-1.0)."""
        # Simplified: penalize based on issue severity
        penalty = 0.0
        for issue in validation_issues:
            if issue.severity == "critical":
                penalty += 0.1
            elif issue.severity == "warning":
                penalty += 0.05
            elif issue.severity == "info":
                penalty += 0.01

        return max(0.0, 1.0 - penalty)
```

---

## 5. Configuration Management

### 5.1 Configuration Module

**File**: `agentic_neurodata_conversion/config.py`

```python
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global settings for MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # MCP Server
    MCP_SERVER_HOST: str = Field(default="0.0.0.0")
    MCP_SERVER_PORT: int = Field(default=3000)
    MCP_SERVER_URL: str = Field(default="http://localhost:3000")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_SESSION_TTL_SECONDS: int = Field(default=86400)  # 24 hours

    # Filesystem
    SESSION_CONTEXT_PATH: str = Field(default="./data/sessions")
    OUTPUT_DIR: str = Field(default="./data/output")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")


class AgentConfig(BaseSettings):
    """Configuration for individual agents."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Agent Identity
    agent_name: str
    agent_type: Literal["conversation", "conversion", "evaluation"]
    port: int

    # MCP Server
    mcp_server_url: str = Field(default="http://localhost:3000")

    # LLM Configuration
    llm_provider: Literal["anthropic", "openai"]
    llm_model: str
    llm_api_key: str
    llm_temperature: float
    llm_max_tokens: int
    llm_top_p: float = Field(default=1.0)

    # Output
    output_dir: str = Field(default="./data/output")


# Global settings instance
settings = Settings()


# Agent config factories
def get_conversation_agent_config() -> AgentConfig:
    """Get conversation agent configuration from environment."""
    return AgentConfig(
        agent_name="conversation_agent",
        agent_type="conversation",
        port=3001,
        llm_provider=os.getenv("CONVERSATION_AGENT_LLM_PROVIDER", "anthropic"),
        llm_model=os.getenv("CONVERSATION_AGENT_MODEL", "claude-3-5-sonnet-20250929"),
        llm_api_key=os.getenv("CONVERSATION_AGENT_API_KEY", ""),
        llm_temperature=float(os.getenv("CONVERSATION_AGENT_TEMPERATURE", "0.7")),
        llm_max_tokens=int(os.getenv("CONVERSATION_AGENT_MAX_TOKENS", "2048")),
        llm_top_p=float(os.getenv("CONVERSATION_AGENT_TOP_P", "0.95"))
    )


def get_conversion_agent_config() -> AgentConfig:
    """Get conversion agent configuration from environment."""
    return AgentConfig(
        agent_name="conversion_agent",
        agent_type="conversion",
        port=3002,
        llm_provider=os.getenv("CONVERSION_AGENT_LLM_PROVIDER", "anthropic"),
        llm_model=os.getenv("CONVERSION_AGENT_MODEL", "claude-3-5-sonnet-20250929"),
        llm_api_key=os.getenv("CONVERSION_AGENT_API_KEY", ""),
        llm_temperature=float(os.getenv("CONVERSION_AGENT_TEMPERATURE", "0.3")),
        llm_max_tokens=int(os.getenv("CONVERSION_AGENT_MAX_TOKENS", "1024")),
        llm_top_p=float(os.getenv("CONVERSION_AGENT_TOP_P", "0.9"))
    )


def get_evaluation_agent_config() -> AgentConfig:
    """Get evaluation agent configuration from environment."""
    return AgentConfig(
        agent_name="evaluation_agent",
        agent_type="evaluation",
        port=3003,
        llm_provider=os.getenv("EVALUATION_AGENT_LLM_PROVIDER", "anthropic"),
        llm_model=os.getenv("EVALUATION_AGENT_MODEL", "claude-3-5-sonnet-20250929"),
        llm_api_key=os.getenv("EVALUATION_AGENT_API_KEY", ""),
        llm_temperature=float(os.getenv("EVALUATION_AGENT_TEMPERATURE", "0.4")),
        llm_max_tokens=int(os.getenv("EVALUATION_AGENT_MAX_TOKENS", "1536")),
        llm_top_p=float(os.getenv("EVALUATION_AGENT_TOP_P", "0.9"))
    )
```

### 5.2 Environment Template

**File**: `.env.example`

```env
# MCP Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=3000
MCP_SERVER_URL=http://localhost:3000

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_TTL_SECONDS=86400

# Filesystem Configuration
SESSION_CONTEXT_PATH=./data/sessions
OUTPUT_DIR=./data/output

# Logging
LOG_LEVEL=INFO

# Conversation Agent (friendly, natural interaction)
CONVERSATION_AGENT_LLM_PROVIDER=anthropic
CONVERSATION_AGENT_MODEL=claude-3-5-sonnet-20250929
CONVERSATION_AGENT_API_KEY=sk-ant-your-key-here
CONVERSATION_AGENT_TEMPERATURE=0.7
CONVERSATION_AGENT_MAX_TOKENS=2048
CONVERSATION_AGENT_TOP_P=0.95

# Conversion Agent (deterministic, consistent error messages)
CONVERSION_AGENT_LLM_PROVIDER=anthropic
CONVERSION_AGENT_MODEL=claude-3-5-sonnet-20250929
CONVERSION_AGENT_API_KEY=sk-ant-your-key-here
CONVERSION_AGENT_TEMPERATURE=0.3
CONVERSION_AGENT_MAX_TOKENS=1024
CONVERSION_AGENT_TOP_P=0.9

# Evaluation Agent (clear, readable summaries)
EVALUATION_AGENT_LLM_PROVIDER=anthropic
EVALUATION_AGENT_MODEL=claude-3-5-sonnet-20250929
EVALUATION_AGENT_API_KEY=sk-ant-your-key-here
EVALUATION_AGENT_TEMPERATURE=0.4
EVALUATION_AGENT_MAX_TOKENS=1536
EVALUATION_AGENT_TOP_P=0.9
```

---

## 6. Testing Strategy

### 6.1 Testing Principles

**No Mocks Approach**:
- Build components in dependency order
- Test each component with **real** services built earlier
- Use **real** NeuroConv and NWB Inspector libraries
- Only external LLM calls may be mocked (optional)

**Coverage Requirements**:
- **Critical paths** (message handlers, context CRUD, routing): ≥90%
- **All other components**: ≥85%

### 6.2 Test Structure

```
tests/
├── unit/
│   ├── test_context_manager.py      # Redis + filesystem operations
│   ├── test_message_router.py       # Message routing logic
│   ├── test_agent_registry.py       # Agent discovery
│   ├── test_conversation_agent.py   # Format detection, metadata extraction
│   ├── test_conversion_agent.py     # NeuroConv integration
│   └── test_evaluation_agent.py     # NWB Inspector integration
├── integration/
│   ├── test_session_workflow.py     # Complete session lifecycle
│   ├── test_agent_handoffs.py       # Agent-to-agent communication
│   └── test_error_recovery.py       # Failure scenarios
├── e2e/
│   └── test_full_pipeline.py        # End-to-end with real dataset
├── conftest.py                       # Shared fixtures
└── data/
    └── synthetic_openephys/          # Test dataset (~1MB)
        ├── settings.xml
        ├── CH1.continuous
        └── README.md
```

### 6.3 Build Order for Testing (No Mocks)

**Phase 1: Foundation** (can test independently)
1. Data models (Pydantic validation)
2. Context Manager (Redis + filesystem)
3. Agent Registry (in-memory)

**Phase 2: Server Core** (tests use Phase 1)
4. Message Router (uses Agent Registry, Context Manager)
5. MCP Server startup (uses all Phase 1 + Message Router)
6. REST API endpoints (uses MCP Server)

**Phase 3: Agent Base** (tests use Phase 2)
7. Base Agent class (LLM provider abstraction)
8. Agent registration (uses Agent Registry)

**Phase 4: Specialized Agents** (tests use Phase 3)
9. Conversation Agent (format detection, metadata extraction)
10. Conversion Agent (NeuroConv, real dataset)
11. Evaluation Agent (NWB Inspector, real NWB file)

**Phase 5: Integration** (tests use all above)
12. Complete workflow tests
13. Error recovery tests
14. Performance tests

### 6.4 Test Data Creation

**Synthetic OpenEphys Dataset**:

```python
# Script: tests/data/generate_synthetic_openephys.py

import numpy as np
from pathlib import Path

def generate_synthetic_openephys(output_dir: Path, duration_seconds: int = 10):
    """Generate minimal OpenEphys dataset for testing."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create settings.xml
    settings_xml = """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <INFO>
    <VERSION>0.4.4.1</VERSION>
    <DATE>2024-01-14 12:00:00</DATE>
  </INFO>
  <SIGNALCHAIN>
    <PROCESSOR name="Sources/Rhythm FPGA" NodeId="100">
      <CHANNEL_INFO>
        <CHANNEL name="CH1" number="0" gain="0.195"/>
        <CHANNEL name="CH2" number="1" gain="0.195"/>
      </CHANNEL_INFO>
      <EDITOR isCollapsed="0" DisplayName="Rhythm FPGA">
        <SampleRate>30000</SampleRate>
      </EDITOR>
    </PROCESSOR>
  </SIGNALCHAIN>
</SETTINGS>
"""
    (output_dir / "settings.xml").write_text(settings_xml)

    # Create .continuous files (2 channels)
    sampling_rate = 30000
    n_samples = sampling_rate * duration_seconds

    for ch_id in [1, 2]:
        # Generate random data (int16)
        data = np.random.randint(-32768, 32767, size=n_samples, dtype=np.int16)

        # OpenEphys .continuous format header
        header = np.array([
            1024,  # header size
            2,     # format version
            sampling_rate,
            1,     # number of channels
            0,     # blockLength (not used)
            0,     # bufferSize (not used)
            0,     # bitVolts
        ], dtype=np.int32)

        # Write file
        filepath = output_dir / f"CH{ch_id}.continuous"
        with open(filepath, 'wb') as f:
            header.tofile(f)
            data.tofile(f)

    # Create README.md
    readme = """# Synthetic OpenEphys Dataset

This is a test dataset for the multi-agent NWB conversion pipeline.

## Experiment Information
- Subject ID: test_subject_001
- Species: mouse
- Age: P60
- Sex: M
- Experimenter: Test User
- Device: Intan RHD2000
- Recording Location: hippocampus CA1
- Session Start: 2024-01-14 12:00:00

## Recording Parameters
- Sampling Rate: 30000 Hz
- Channels: 2
- Duration: 10 seconds
"""
    (output_dir / "README.md").write_text(readme)

if __name__ == "__main__":
    generate_synthetic_openephys(Path("tests/data/synthetic_openephys"))
```

### 6.5 Key Test Examples

**Test 1: Context Manager** (Phase 1)

```python
# tests/unit/test_context_manager.py

import pytest
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.models.session_context import SessionContext, WorkflowStage


@pytest.mark.asyncio
async def test_create_and_get_session(context_manager: ContextManager):
    """Test write-through session creation."""
    session = SessionContext(
        session_id="test-session-1",
        workflow_stage=WorkflowStage.INITIALIZED
    )

    # Create session
    await context_manager.create_session(session)

    # Verify in Redis
    retrieved = await context_manager.get_session("test-session-1")
    assert retrieved is not None
    assert retrieved.session_id == "test-session-1"
    assert retrieved.workflow_stage == WorkflowStage.INITIALIZED

    # Verify on filesystem
    fs_path = context_manager._get_filesystem_path("test-session-1")
    assert fs_path.exists()


@pytest.mark.asyncio
async def test_session_persistence_after_redis_restart(context_manager: ContextManager):
    """Test filesystem fallback when Redis unavailable."""
    session = SessionContext(
        session_id="test-session-2",
        workflow_stage=WorkflowStage.CONVERTING
    )

    # Create session
    await context_manager.create_session(session)

    # Simulate Redis failure by deleting from Redis only
    await context_manager.redis_client.delete(context_manager._get_redis_key("test-session-2"))

    # Should restore from filesystem
    retrieved = await context_manager.get_session("test-session-2")
    assert retrieved is not None
    assert retrieved.session_id == "test-session-2"
    assert retrieved.workflow_stage == WorkflowStage.CONVERTING
```

### 6.6 Test Fixtures (conftest.py)

**File**: `tests/conftest.py`

```python
import asyncio
import pytest
import redis.asyncio as redis
from pathlib import Path

from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter
from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.agents.conversion_agent import ConversionAgent
from agentic_neurodata_conversion.agents.evaluation_agent import EvaluationAgent
from agentic_neurodata_conversion.config import (
    get_conversation_agent_config,
    get_conversion_agent_config,
    get_evaluation_agent_config
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def redis_client():
    """Redis client for tests (uses database 15 for isolation)."""
    client = await redis.from_url("redis://localhost:6379/15", decode_responses=True)
    yield client
    # Cleanup: flush test database
    await client.flushdb()
    await client.close()


@pytest.fixture
async def context_manager(redis_client, tmp_path):
    """Context manager fixture with test Redis and temp filesystem."""
    manager = ContextManager(
        redis_url="redis://localhost:6379/15",
        session_ttl=3600,  # 1 hour for tests
        filesystem_base_path=str(tmp_path / "sessions")
    )
    await manager.connect()
    yield manager
    await manager.disconnect()


@pytest.fixture
def agent_registry():
    """Agent registry fixture."""
    return AgentRegistry()


@pytest.fixture
async def message_router(agent_registry, context_manager):
    """Message router fixture."""
    return MessageRouter(
        agent_registry=agent_registry,
        context_manager=context_manager
    )


@pytest.fixture
def conversation_agent():
    """Conversation agent fixture."""
    config = get_conversation_agent_config()
    return ConversationAgent(config)


@pytest.fixture
def conversion_agent():
    """Conversion agent fixture."""
    config = get_conversion_agent_config()
    return ConversionAgent(config)


@pytest.fixture
def evaluation_agent():
    """Evaluation agent fixture."""
    config = get_evaluation_agent_config()
    return EvaluationAgent(config)


@pytest.fixture(scope="session")
def test_dataset_path():
    """Path to synthetic OpenEphys test dataset."""
    return Path("tests/data/synthetic_openephys")


@pytest.fixture(scope="session")
def mcp_server_url():
    """MCP server URL for integration tests."""
    return "http://localhost:3000"


@pytest.fixture
async def test_session(context_manager):
    """Create a test session and clean up after."""
    from agentic_neurodata_conversion.models.session_context import SessionContext, WorkflowStage
    import uuid

    session_id = str(uuid.uuid4())
    session = SessionContext(
        session_id=session_id,
        workflow_stage=WorkflowStage.INITIALIZED
    )
    await context_manager.create_session(session)

    yield session

    # Cleanup
    await context_manager.delete_session(session_id)
```

---

**Test 2: Conversation Agent** (Phase 4)

```python
# tests/unit/test_conversation_agent.py

import pytest
from pathlib import Path
from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType


@pytest.mark.asyncio
async def test_format_detection_openephys(conversation_agent: ConversationAgent):
    """Test OpenEphys format detection."""
    dataset_path = "tests/data/synthetic_openephys"

    detected_format = conversation_agent._detect_format(dataset_path)
    assert detected_format == "openephys"


@pytest.mark.asyncio
async def test_metadata_extraction_from_md(conversation_agent: ConversationAgent):
    """Test metadata extraction from README.md."""
    dataset_path = "tests/data/synthetic_openephys"

    metadata = await conversation_agent._extract_metadata_from_md_files(dataset_path)

    # Should extract from README.md
    assert metadata.subject_id == "test_subject_001"
    assert metadata.species in ["mouse", "Mus musculus"]
    assert metadata.age == "P60"
    assert metadata.sex == "M"
    assert metadata.experimenter == "Test User"
    assert metadata.recording_location == "hippocampus CA1"
```

**Test 3: End-to-End Pipeline** (Phase 5)

```python
# tests/e2e/test_full_pipeline.py

import pytest
import httpx
from pathlib import Path


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_conversion_workflow(mcp_server_url: str):
    """Test complete conversion workflow from initialization to result."""
    async with httpx.AsyncClient() as client:
        # 1. Initialize session
        response = await client.post(
            f"{mcp_server_url}/api/v1/sessions/initialize",
            json={"dataset_path": "tests/data/synthetic_openephys"}
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # 2. Poll status until completed
        max_attempts = 60
        for _ in range(max_attempts):
            response = await client.get(f"{mcp_server_url}/api/v1/sessions/{session_id}/status")
            assert response.status_code == 200
            status = response.json()

            if status["workflow_stage"] == "completed":
                break

            await asyncio.sleep(2)

        assert status["workflow_stage"] == "completed"

        # 3. Get results
        response = await client.get(f"{mcp_server_url}/api/v1/sessions/{session_id}/result")
        assert response.status_code == 200
        result = response.json()

        # 4. Verify NWB file exists
        assert result["nwb_file_path"] is not None
        assert Path(result["nwb_file_path"]).exists()

        # 5. Verify validation passed
        assert result["overall_status"] in ["passed", "passed_with_warnings"]
```

---

## 7. Deployment

### 7.1 Development Setup

**Prerequisites**:
- Python 3.13 (exact version)
- Redis server (local or Docker)
- Pixi package manager

**Setup Steps**:

```bash
# 1. Clone repository
git clone <repo-url>
cd agentic-neurodata-conversion

# 2. Install dependencies via Pixi
pixi install

# 3. Copy environment template
cp .env.example .env

# 4. Edit .env with your API keys
nano .env

# 5. Start Redis (Docker)
docker run -d -p 6379:6379 redis:7-alpine

# 6. Create data directories
mkdir -p data/sessions data/output

# 7. Generate test dataset
pixi run python tests/data/generate_synthetic_openephys.py

# 8. Run tests
pixi run test

# 9. Start MCP server (terminal 1)
pixi run server-dev

# 10. Start agents (terminals 2-4)
# Terminal 2:
pixi run python -m agentic_neurodata_conversion.agents.conversation_agent

# Terminal 3:
pixi run python -m agentic_neurodata_conversion.agents.conversion_agent

# Terminal 4:
pixi run python -m agentic_neurodata_conversion.agents.evaluation_agent
```

### 7.2 Process Management

**Simple Script** (`scripts/start_all.sh`):

```bash
#!/bin/bash

# Start Redis (if not running)
docker ps | grep redis || docker run -d -p 6379:6379 --name redis redis:7-alpine

# Start MCP server
pixi run server-dev &
SERVER_PID=$!

# Wait for server to be ready
sleep 3

# Start agents
pixi run python -m agentic_neurodata_conversion.agents.conversation_agent &
CONV_AGENT_PID=$!

pixi run python -m agentic_neurodata_conversion.agents.conversion_agent &
CONVERSION_AGENT_PID=$!

pixi run python -m agentic_neurodata_conversion.agents.evaluation_agent &
EVAL_AGENT_PID=$!

echo "All processes started:"
echo "  MCP Server: $SERVER_PID"
echo "  Conversation Agent: $CONV_AGENT_PID"
echo "  Conversion Agent: $CONVERSION_AGENT_PID"
echo "  Evaluation Agent: $EVAL_AGENT_PID"

# Trap SIGINT to stop all processes
trap "kill $SERVER_PID $CONV_AGENT_PID $CONVERSION_AGENT_PID $EVAL_AGENT_PID" SIGINT

wait
```

### 7.3 Health Checks

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "agents_registered": [
    "conversation_agent",
    "conversion_agent",
    "evaluation_agent"
  ],
  "redis_connected": true
}
```

---

## 8. Implementation Roadmap

### Week 1: Foundation
**Goal**: Core data models and context storage working

**Tasks**:
- [ ] Define Pydantic models (SessionContext, MCPMessage, API models)
- [ ] Implement Context Manager (Redis + filesystem)
- [ ] Write tests for Context Manager (≥90% coverage)
- [ ] Implement Agent Registry
- [ ] Write tests for Agent Registry (≥85% coverage)

**Milestone**: Can create, read, update, delete session contexts with persistence

---

### Week 2: MCP Server
**Goal**: Server handles message routing and REST API

**Tasks**:
- [ ] Implement Message Router
- [ ] Write tests for Message Router (≥90% coverage)
- [ ] Create FastAPI application (main.py)
- [ ] Implement REST API endpoints (sessions.py, health.py)
- [ ] Write API integration tests
- [ ] Add internal endpoints for agent communication

**Milestone**: Server routes messages between registered agents via HTTP

---

### Week 3: Agent Base + Conversation Agent
**Goal**: Conversation agent initializes sessions and extracts metadata

**Tasks**:
- [ ] Implement Base Agent class (LLM abstraction, MCP client)
- [ ] Write tests for Base Agent (≥85% coverage)
- [ ] Implement Conversation Agent (format detection, validation)
- [ ] Implement metadata extraction from .md files with LLM
- [ ] Write tests for Conversation Agent (≥85% coverage)
- [ ] Generate synthetic OpenEphys test dataset

**Milestone**: Conversation agent detects OpenEphys format and extracts metadata

---

### Week 4: Conversion Agent
**Goal**: Conversion agent generates NWB files

**Tasks**:
- [ ] Implement Conversion Agent (NeuroConv integration)
- [ ] Implement metadata preparation for NWB
- [ ] Implement LLM error message generation
- [ ] Write tests for Conversion Agent (≥85% coverage)
- [ ] Test with real OpenEphys dataset

**Milestone**: Conversion agent produces valid NWB files from OpenEphys data

---

### Week 5: Evaluation Agent + Integration
**Goal**: Evaluation agent validates NWB files, full pipeline works

**Tasks**:
- [ ] Implement Evaluation Agent (NWB Inspector integration)
- [ ] Implement validation report generation
- [ ] Implement LLM validation summaries
- [ ] Write tests for Evaluation Agent (≥85% coverage)
- [ ] Write integration tests (complete workflow)
- [ ] Write error recovery tests

**Milestone**: Complete pipeline produces validated NWB files with reports

---

### Week 6: Polish + Documentation
**Goal**: Production-ready system with documentation

**Tasks**:
- [ ] Review and meet coverage requirements (≥90% critical, ≥85% overall)
- [ ] Performance testing (10GB dataset)
- [ ] Setup deployment scripts (start_all.sh, Docker Compose)
- [ ] Write API documentation (OpenAPI/Swagger)
- [ ] Write user guide (setup, usage, troubleshooting)
- [ ] Write developer guide (architecture, testing, contributing)
- [ ] Final pre-commit hook setup and verification

**Milestone**: System deployed, documented, and ready for use

---

## 9. API Contract Examples

### 9.1 Initialize Session

**Request**:
```http
POST /api/v1/sessions/initialize
Content-Type: application/json

{
  "dataset_path": "/data/openephys_dataset"
}
```

**Response** (200 OK):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Session initialized successfully. Analyzing dataset...",
  "workflow_stage": "initialized"
}
```

---

### 9.2 Check Status

**Request**:
```http
GET /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/status
```

**Response** (200 OK):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_stage": "converting",
  "progress_percentage": 60,
  "status_message": "Current stage: converting",
  "current_agent": "conversion_agent",
  "requires_clarification": false,
  "clarification_prompt": null
}
```

---

### 9.3 Provide Clarification

**Request**:
```http
POST /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/clarify
Content-Type: application/json

{
  "user_input": "The session start time should be 2024-01-14T10:30:00",
  "updated_metadata": {
    "session_start_time": "2024-01-14T10:30:00"
  }
}
```

**Response** (200 OK):
```json
{
  "message": "Clarification received. Retrying conversion...",
  "workflow_stage": "converting"
}
```

---

### 9.4 Get Results

**Request**:
```http
GET /api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/result
```

**Response** (200 OK):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "nwb_file_path": "/data/output/550e8400-e29b-41d4-a716-446655440000.nwb",
  "validation_report_path": "/data/output/550e8400-e29b-41d4-a716-446655440000_validation_report.json",
  "overall_status": "passed_with_warnings",
  "summary": "Validation completed successfully with 3 warnings. The NWB file contains all required metadata and recording data. Warnings relate to optional best practices: (1) Missing institution field, (2) Device description could be more detailed, (3) Consider adding more detailed session description. The file is ready for use and sharing.",
  "validation_issues": [
    {
      "severity": "warning",
      "message": "Missing institution field in NWBFile metadata",
      "location": "/general/institution",
      "check_name": "check_institution_exists"
    },
    {
      "severity": "warning",
      "message": "Device description is minimal",
      "location": "/general/devices/device_0",
      "check_name": "check_device_description"
    },
    {
      "severity": "warning",
      "message": "Session description could be more detailed",
      "location": "/general/session_description",
      "check_name": "check_session_description_detail"
    }
  ]
}
```

---

## 10. Risks and Mitigations

### 10.1 Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **LLM API rate limits** | High - blocks workflow | Medium | Implement exponential backoff with retries (max 5 attempts); use lower temperature for conversion/evaluation agents to reduce token usage; cache common LLM responses |
| **Large dataset memory issues** | High - OOM crashes | High | Stream NeuroConv processing; monitor memory usage with psutil; warn users for datasets >10GB; implement chunked conversion if possible |
| **Redis connection failures** | Medium - context loss | Medium | Automatic reconnection with retry logic; filesystem fallback ensures no data loss; health checks detect Redis issues early |
| **NeuroConv compatibility** | High - conversion failures | Low | Pin NeuroConv version; test with multiple OpenEphys dataset versions; comprehensive error handling with user-friendly messages |
| **MCP protocol changes** | Medium - communication breaks | Low | Pin `mcp` package version; version API endpoints; monitor MCP Python package releases |
| **Agent process crashes** | High - workflow stops | Medium | Session-level recovery from context; implement agent health checks; restart crashed agents automatically |

### 10.2 Process Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Scope creep** | High - delays MVP | High | **Strict MVP enforcement**: reject DataLad, knowledge graphs, multiple formats until post-MVP; constitution compliance checks in PRs |
| **Testing delays** | Medium - quality issues | Medium | **No mocks approach** reduces test complexity; parallel development of tests and implementation; enforce TDD workflow in code reviews |
| **Integration complexity** | Medium - agent handoffs fail | Medium | Start integration tests early (Week 3); test each agent handoff immediately after implementing agent; use real MCP server in tests |
| **LLM non-determinism** | Medium - flaky tests | Medium | Use low temperature for conversion/evaluation agents; use deterministic test cases where possible; allow LLM tests to have retry logic |
| **Developer onboarding** | Low - productivity loss | Low | Clear documentation (this plan); architecture diagrams; code examples in every component; pair programming for complex areas |

---

## 11. Constitution Compliance Checklist

This plan ensures compliance with all constitutional principles:

- ✅ **MCP-Centric Architecture**: All communication through MCP server, no direct agent calls
- ✅ **Test-Driven Development**: Tests defined for each component before implementation, ≥90%/≥85% coverage
- ✅ **Schema-First Development**: Pydantic models defined before implementation
- ✅ **Feature-Driven Architecture**: Clear boundaries, agents are stateless, isolated testing
- ✅ **Data Integrity & Provenance**: Context persistence (Redis + filesystem), session-level recovery
- ✅ **Quality-First Development**: Pre-commit hooks, linting (ruff), type checking (mypy), comprehensive tests
- ✅ **Spec-Kit Workflow**: Following `/specify` → `/plan` → `/tasks` → `/analyze` → `/checklist` → `/implement`

---

## 12. Next Steps

**Immediate Actions**:
1. Review this plan with stakeholders
2. Run `/tasks` command to generate dependency-ordered task breakdown
3. Run `/analyze` to verify cross-artifact consistency
4. Run `/checklist` to validate all quality criteria
5. Upon passing gates, begin Week 1 implementation

**Success Criteria for Plan Approval**:
- [ ] All specification requirements addressed
- [ ] Technology choices aligned with constitution
- [ ] Testing strategy enables no-mock approach
- [ ] Implementation roadmap is realistic (6 weeks)
- [ ] API contracts are clear and complete
- [ ] Risks identified with mitigation strategies

---

**Plan Complete - Ready for Task Generation**
