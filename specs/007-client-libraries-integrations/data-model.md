# Data Model: Client Libraries and Integrations

**Feature**: 007-client-libraries-integrations
**Date**: 2025-10-06
**Status**: Complete

## Overview

This document defines the core data models for the MCP client library and CLI tool. All models use Pydantic v2 for validation, serialization, and type safety.

---

## Core Models

### 1. MCPConfig

Configuration for MCP client connection and behavior.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from pathlib import Path

class ServerConfig(BaseModel):
    """MCP server configuration."""

    command: str = Field(
        default="python -m agentic_neurodata_conversion.mcp_server",
        description="Command to start MCP server"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Server startup timeout in seconds"
    )
    working_dir: Optional[Path] = Field(
        default=None,
        description="Working directory for server process"
    )

class RetryConfig(BaseModel):
    """Retry policy configuration."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_factor: float = Field(default=2.0, ge=1.0, le=10.0)
    initial_delay: float = Field(default=1.0, ge=0.1, le=10.0)
    max_delay: float = Field(default=60.0, ge=1.0, le=300.0)

class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["text", "json"] = "text"
    file: Optional[Path] = None

class MCPConfig(BaseModel):
    """Complete MCP client configuration."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    request_timeout: int = Field(default=60, ge=1, le=3600)

    @field_validator("request_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1:
            raise ValueError("request_timeout must be >= 1 second")
        return v

    class Config:
        frozen = False
        validate_assignment = True
```

**Relationships**: Used by MCPClient for initialization

**Validation Rules**:
- Server timeout: 1-300 seconds
- Retry attempts: 1-10
- Backoff factor: 1.0-10.0
- Request timeout: 1-3600 seconds

---

### 2. MCPClient

Main client interface for MCP server interaction.

```python
from typing import Optional, AsyncGenerator
import asyncio
from contextlib import asynccontextmanager

class MCPClient:
    """MCP client for neurodata conversion.

    Supports both synchronous and asynchronous APIs.
    Manages connection lifecycle, retries, and streaming.
    """

    def __init__(self, config: Optional[MCPConfig] = None):
        """Initialize MCP client.

        Args:
            config: Client configuration. If None, uses defaults.
        """
        self.config = config or MCPConfig()
        self._session: Optional[ClientSession] = None
        self._process: Optional[subprocess.Popen] = None
        self._connected: bool = False
        self._lock = asyncio.Lock()

    # Async context manager
    async def __aenter__(self) -> "MCPClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    # Connection management
    async def connect(self) -> None:
        """Establish connection to MCP server."""
        ...

    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        ...

    async def health_check(self) -> bool:
        """Check if server is responsive."""
        ...

    # Conversion operations (async)
    async def convert_async(
        self,
        request: ConversionRequest
    ) -> AsyncGenerator[ConversionProgress, None]:
        """Convert data with streaming progress updates.

        Yields:
            ConversionProgress: Progress updates during conversion
        """
        ...

    async def get_conversion_result(
        self,
        conversion_id: str
    ) -> ConversionResponse:
        """Get final conversion result."""
        ...

    # Conversion operations (sync - convenience wrappers)
    def convert(
        self,
        request: ConversionRequest,
        progress_callback: Optional[Callable[[ConversionProgress], None]] = None
    ) -> ConversionResponse:
        """Synchronous conversion (blocks until complete).

        Args:
            request: Conversion request
            progress_callback: Optional callback for progress updates

        Returns:
            ConversionResponse: Final conversion result
        """
        return asyncio.run(self._convert_sync(request, progress_callback))

    # Agent interaction
    async def query_agent(
        self,
        agent: AgentType,
        query: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Query a specific agent."""
        ...

    # Session management
    async def create_session(self) -> Session:
        """Create new conversation session."""
        ...

    async def get_session_history(
        self,
        session_id: str
    ) -> list[Message]:
        """Get message history for session."""
        ...
```

**State Machine**:
```
[Disconnected] --connect()--> [Connected]
[Connected] --disconnect()--> [Disconnected]
[Connected] --convert_async()--> [Converting]
[Converting] --complete/error--> [Connected]
```

**Key Behaviors**:
- Lazy connection (connects on first operation if not explicit)
- Auto-reconnect on connection failures (respects retry policy)
- Thread-safe (uses asyncio.Lock)
- Resource cleanup via context manager

---

### 3. ConversionRequest

Request model for data conversion operations.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from pathlib import Path
from enum import Enum

class DataFormat(str, Enum):
    """Supported input data formats."""
    SPIKE2 = "spike2"
    NEURODATA_WITHOUT_BORDERS = "nwb"
    MEA_RECORDING = "mea"
    CALCIUM_IMAGING = "calcium"
    ELECTROPHYSIOLOGY = "ephys"

class ConversionMode(str, Enum):
    """Conversion execution mode."""
    AUTOMATIC = "automatic"  # Orchestrator decides workflow
    MANUAL = "manual"  # User specifies agents

class ConversionRequest(BaseModel):
    """Request for data conversion."""

    # Required fields
    input_path: Path = Field(
        description="Path to input data file or directory"
    )
    output_path: Path = Field(
        description="Path for output NWB file"
    )

    # Optional fields
    data_format: Optional[DataFormat] = Field(
        default=None,
        description="Input data format (auto-detected if not specified)"
    )
    mode: ConversionMode = Field(
        default=ConversionMode.AUTOMATIC,
        description="Conversion mode"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for conversation context"
    )
    metadata: Optional[dict] = Field(
        default_factory=dict,
        description="Additional metadata for conversion"
    )

    # Conversion options
    validate_output: bool = Field(
        default=True,
        description="Validate NWB file after conversion"
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite existing output file"
    )

    @field_validator("input_path")
    @classmethod
    def validate_input_path(cls, v: Path) -> Path:
        """Validate input path exists."""
        if not v.exists():
            raise ValueError(f"Input path does not exist: {v}")
        return v.resolve()

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, v: Path) -> Path:
        """Validate output path."""
        if v.exists() and not cls.overwrite:
            raise ValueError(f"Output path already exists: {v}")
        if not v.suffix == ".nwb":
            raise ValueError("Output path must have .nwb extension")
        return v.resolve()

    class Config:
        use_enum_values = True
```

**Validation Rules**:
- input_path must exist
- output_path must have .nwb extension
- output_path must not exist unless overwrite=True
- metadata must be JSON-serializable

---

### 4. ConversionResponse

Response model for conversion results.

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ConversionStatus(str, Enum):
    """Conversion status."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some data converted, some failed

class ValidationResult(BaseModel):
    """NWB validation result."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ConversionMetrics(BaseModel):
    """Conversion performance metrics."""

    duration_seconds: float
    input_size_bytes: int
    output_size_bytes: int
    records_processed: int

class ConversionResponse(BaseModel):
    """Response from conversion operation."""

    # Result status
    status: ConversionStatus
    conversion_id: str = Field(description="Unique conversion ID")

    # File paths
    input_path: Path
    output_path: Optional[Path] = Field(
        default=None,
        description="Path to output NWB file (None if failed)"
    )

    # Timestamps
    started_at: datetime
    completed_at: datetime

    # Validation
    validation: Optional[ValidationResult] = None

    # Metrics
    metrics: Optional[ConversionMetrics] = None

    # Errors and warnings
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Suggestions for errors
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested fixes for errors"
    )

    # Session context
    session_id: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if conversion was successful."""
        return self.status == ConversionStatus.SUCCESS
```

**Business Logic**:
- success property for quick status check
- validation runs automatically if validate_output=True in request
- errors list includes agent errors and validation errors
- suggestions provide actionable fixes

---

### 5. ConversionProgress

Streaming progress update model.

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

class ConversionStage(str, Enum):
    """Stages of conversion process."""
    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    CONVERTING = "converting"
    VALIDATING = "validating"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"

class ProgressUpdate(BaseModel):
    """Progress update during conversion."""

    # Stage info
    stage: ConversionStage
    stage_description: str = Field(
        description="Human-readable stage description"
    )

    # Progress
    percent_complete: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall progress percentage"
    )
    current_step: int = Field(ge=1)
    total_steps: int = Field(ge=1)

    # Status
    message: str = Field(description="Progress message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Optional details
    details: Optional[dict] = Field(
        default=None,
        description="Stage-specific details"
    )

    # Agent info
    current_agent: Optional[str] = Field(
        default=None,
        description="Currently active agent"
    )

class ConversionProgress(BaseModel):
    """Streaming progress container."""

    conversion_id: str
    update: ProgressUpdate

    # Retry info (if applicable)
    retry_count: int = Field(default=0, ge=0)
    is_retry: bool = False

    @property
    def is_complete(self) -> bool:
        """Check if conversion is complete."""
        return self.update.stage in [
            ConversionStage.COMPLETED,
            ConversionStage.FAILED
        ]
```

**Streaming Behavior**:
- Emitted during async conversion via AsyncGenerator
- Sent at each stage transition
- Can be sent multiple times per stage for long operations
- Final update has stage=COMPLETED or FAILED

---

### 6. AgentType and AgentResponse

Models for individual agent interaction.

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum

class AgentType(str, Enum):
    """Available agent types."""
    ORCHESTRATOR = "orchestrator"
    ANALYSIS = "analysis"
    CONVERSION = "conversion"
    EVALUATION = "evaluation"

class AgentResponse(BaseModel):
    """Response from agent query."""

    agent: AgentType
    response: str = Field(description="Agent's text response")
    context: dict = Field(
        default_factory=dict,
        description="Context data from agent"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Agent suggestions"
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score (if applicable)"
    )
    session_id: Optional[str] = None
```

---

### 7. Session and Message

Models for conversation management.

```python
from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime
from uuid import uuid4

class MessageRole(str, Enum):
    """Message role in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    """Single message in conversation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Optional metadata
    agent: Optional[AgentType] = None
    metadata: dict = Field(default_factory=dict)

class Session(BaseModel):
    """Conversation session."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Conversation history
    messages: List[Message] = Field(default_factory=list)

    # Session metadata
    metadata: dict = Field(default_factory=dict)

    def add_message(self, message: Message) -> None:
        """Add message to session."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    @property
    def message_count(self) -> int:
        """Get message count."""
        return len(self.messages)
```

---

### 8. Error Models

Structured error responses.

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum

class ErrorCode(str, Enum):
    """Error codes matching JSON-RPC."""
    PARSE_ERROR = "parse_error"  # -32700
    INVALID_REQUEST = "invalid_request"  # -32600
    METHOD_NOT_FOUND = "method_not_found"  # -32601
    INVALID_PARAMS = "invalid_params"  # -32602
    INTERNAL_ERROR = "internal_error"  # -32603
    SERVER_ERROR = "server_error"  # -32000
    CONNECTION_ERROR = "connection_error"  # Custom
    VALIDATION_ERROR = "validation_error"  # Custom

class ErrorResponse(BaseModel):
    """Structured error response."""

    code: ErrorCode
    message: str = Field(description="Error message")

    # Additional context
    details: Optional[dict] = Field(
        default=None,
        description="Error details"
    )

    # Actionable suggestions
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested fixes"
    )

    # Retry info
    retry_after: Optional[int] = Field(
        default=None,
        description="Seconds to wait before retry"
    )
    is_retryable: bool = Field(default=False)

class MCPException(Exception):
    """Base exception for MCP client."""

    def __init__(self, error: ErrorResponse):
        self.error = error
        super().__init__(error.message)

class ConnectionError(MCPException):
    """Connection error."""
    pass

class ValidationError(MCPException):
    """Validation error."""
    pass

class ServerError(MCPException):
    """Server error."""
    pass
```

---

## CLI-Specific Models

### 9. CLIConfig

Configuration specific to CLI tool.

```python
from pydantic import BaseModel, Field
from typing import Literal

class OutputFormat(str, Enum):
    """CLI output formats."""
    JSON = "json"
    YAML = "yaml"
    TABLE = "table"
    TEXT = "text"

class CLIConfig(BaseModel):
    """CLI-specific configuration."""

    output_format: OutputFormat = OutputFormat.TEXT
    color: bool = Field(
        default=True,
        description="Enable colored output"
    )
    verbose: bool = Field(default=False)

    # Progress display
    show_progress: bool = Field(default=True)
    progress_style: Literal["bar", "spinner", "dots"] = "bar"

    # Interactive mode
    interactive: bool = Field(default=False)
    confirm_operations: bool = Field(default=True)
```

---

### 10. BatchConfig

Configuration for batch processing.

```python
from pydantic import BaseModel, Field
from typing import List
from pathlib import Path

class BatchItem(BaseModel):
    """Single item in batch conversion."""

    input_path: Path
    output_path: Path
    data_format: Optional[DataFormat] = None
    metadata: dict = Field(default_factory=dict)

class BatchConfig(BaseModel):
    """Configuration for batch conversion."""

    items: List[BatchItem] = Field(description="Items to convert")

    # Execution options
    parallel: bool = Field(
        default=False,
        description="Run conversions in parallel"
    )
    max_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Max parallel workers"
    )

    # Error handling
    stop_on_error: bool = Field(
        default=False,
        description="Stop batch if any conversion fails"
    )

    # Resume support
    checkpoint_file: Optional[Path] = Field(
        default=None,
        description="File to save progress for resume"
    )
    resume: bool = Field(
        default=False,
        description="Resume from checkpoint"
    )

class BatchResult(BaseModel):
    """Result of batch conversion."""

    total: int
    successful: int
    failed: int
    skipped: int

    results: List[ConversionResponse]

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total == 0:
            return 0.0
        return self.successful / self.total
```

---

## Model Relationships Diagram

```
MCPConfig
    └─> MCPClient
            ├─> ConversionRequest → ConversionResponse
            ├─> ConversionRequest → ConversionProgress (stream)
            ├─> AgentType → AgentResponse
            └─> Session
                    └─> Message[]

CLIConfig
    ├─> BatchConfig
    │       └─> BatchItem[]
    └─> OutputFormat

ErrorResponse
    └─> MCPException
            ├─> ConnectionError
            ├─> ValidationError
            └─> ServerError
```

---

## Validation Rules Summary

| Model | Key Validations |
|-------|-----------------|
| MCPConfig | Timeout ranges, retry attempts, backoff factors |
| ConversionRequest | Path existence, .nwb extension, overwrite check |
| ConversionResponse | Status consistency, path validation |
| ConversionProgress | Progress 0-100%, current_step <= total_steps |
| Session | UUID generation, timestamp management |
| BatchConfig | Worker limits 1-16, checkpoint file path |

---

## Serialization Examples

### ConversionRequest JSON

```json
{
  "input_path": "/data/experiment_001.spike2",
  "output_path": "/data/output/experiment_001.nwb",
  "data_format": "spike2",
  "mode": "automatic",
  "metadata": {
    "experimenter": "Jane Doe",
    "lab": "Neuroscience Lab",
    "experiment_date": "2025-10-01"
  },
  "validate_output": true,
  "overwrite": false
}
```

### ConversionProgress JSON

```json
{
  "conversion_id": "conv-123e4567-e89b-12d3-a456-426614174000",
  "update": {
    "stage": "converting",
    "stage_description": "Converting spike2 data to NWB format",
    "percent_complete": 45.5,
    "current_step": 3,
    "total_steps": 5,
    "message": "Processing channel 2/4",
    "timestamp": "2025-10-06T12:34:56Z",
    "current_agent": "conversion"
  },
  "retry_count": 0,
  "is_retry": false
}
```

### ErrorResponse JSON

```json
{
  "code": "validation_error",
  "message": "Input file format not recognized",
  "details": {
    "file_path": "/data/unknown.dat",
    "detected_format": null
  },
  "suggestions": [
    "Specify data_format explicitly in request",
    "Ensure file has correct extension",
    "Check if file is corrupted"
  ],
  "retry_after": null,
  "is_retryable": false
}
```

---

## Type Hints and IDE Support

All models include comprehensive type hints for IDE autocomplete:

```python
# Type checking example
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neuroconv_client.models import (
        MCPClient,
        ConversionRequest,
        ConversionResponse,
    )

# Usage with full type support
client: MCPClient = MCPClient()
request: ConversionRequest = ConversionRequest(
    input_path=Path("/data/input.spike2"),
    output_path=Path("/data/output.nwb"),
)
response: ConversionResponse = client.convert(request)
```

---

## Completion Checklist

- [x] Core models defined (MCPConfig, MCPClient, ConversionRequest, ConversionResponse)
- [x] Progress models defined (ConversionProgress, ConversionStage)
- [x] Agent models defined (AgentType, AgentResponse)
- [x] Session models defined (Session, Message)
- [x] Error models defined (ErrorResponse, MCPException)
- [x] CLI models defined (CLIConfig, BatchConfig)
- [x] Validation rules documented
- [x] Relationships documented
- [x] Serialization examples provided
- [x] Type hints comprehensive

**Status**: Data model design complete - ready for contract definition
