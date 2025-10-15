# Data Model: Agentic Neurodata Conversion System

**Phase**: 1 - Design & Contracts
**Date**: 2025-10-15
**Status**: Complete
**Related**: [plan.md](plan.md), [research.md](research.md)

## Purpose

This document defines all Pydantic data models used throughout the system. These schemas ensure type safety, runtime validation, and consistent data structures across agents, API, and storage.

**Source**: Extracted from [requirements.md Appendix B](../../requirements.md#appendix-b-data-schemas)

---

## Core Schemas

### 1. MCP Message Schema

**Purpose**: Standardized message format for all inter-agent communication via MCP server.

**File**: `backend/src/mcp/message.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

class MCPMessage(BaseModel):
    """
    Standard message format for Model Context Protocol communication.
    Used by all agents to communicate via the MCP server.

    Related Stories: 1.2 (Message Routing), 1.3 (Context Management)
    """
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    target_agent: str = Field(
        ...,
        description="Target agent name from registry (e.g., 'conversation_agent', 'conversion_agent', 'evaluation_agent')"
    )
    action: str = Field(
        ...,
        description="MCP tool/method name to invoke (e.g., 'validate_metadata', 'convert_file', 'generate_report')"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Request-specific parameters and data"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    source_agent: Optional[str] = Field(
        None,
        description="Optional: which agent sent this message"
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Optional: for tracing related messages"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "abc-123-def-456",
                "target_agent": "conversion_agent",
                "action": "convert_file",
                "context": {
                    "input_path": "/uploads/spikeglx_data.bin",
                    "metadata": {"subject_id": "mouse_001"}
                },
                "timestamp": "2025-10-15T10:30:00Z",
                "source_agent": "conversation_agent"
            }
        }
```

**Usage**:
- All agent-to-agent calls use this schema
- MCP server validates and routes based on `target_agent` and `action`
- Context injection (Story 1.3) adds global state to `context` field

---

### 2. Global State Schema

**Purpose**: Single in-memory object tracking current conversion session.

**File**: `backend/src/models/global_state.py`

```python
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional

class ConversionStatus(str, Enum):
    """Overall conversion status"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ValidationStatus(str, Enum):
    """Granular validation outcome status (Story 2.1, 7.2)"""
    PASSED = "passed"                          # No issues at all
    PASSED_ACCEPTED = "passed_accepted"        # User accepted file with warnings
    PASSED_IMPROVED = "passed_improved"        # Warnings resolved through improvement
    FAILED_USER_DECLINED = "failed_user_declined"  # User declined retry
    FAILED_USER_ABANDONED = "failed_user_abandoned"  # User cancelled during input

class StageStatus(str, Enum):
    """Status of individual pipeline stages"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class LogLevel(str, Enum):
    """Log severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogEntry(BaseModel):
    """Individual log entry (Story 2.1)"""
    timestamp: datetime
    level: LogLevel
    component: str = Field(..., description="Component name (e.g., 'mcp_server', 'conversation_agent')")
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Stage(BaseModel):
    """Pipeline stage tracking (Story 2.2)"""
    name: str = Field(..., description="Stage name: 'conversion', 'evaluation', 'report_generation'")
    status: StageStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GlobalState(BaseModel):
    """
    Single global state object for the current conversion session.
    Tracks all aspects of the conversion pipeline.

    Related Stories: 2.1 (Global State Object), 2.2 (Stage Tracking)
    """
    status: ConversionStatus
    validation_status: Optional[ValidationStatus] = None
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="NWB metadata fields (subject_id, species, session_description, etc.)"
    )
    logs: List[LogEntry] = Field(default_factory=list)
    stages: List[Stage] = Field(default_factory=list)
    timestamps: Dict[str, datetime] = Field(
        default_factory=dict,
        description="Key: event name, Value: timestamp (e.g., 'upload', 'conversion_start')"
    )
    correction_attempt: int = Field(
        default=0,
        description="Number of correction attempts (0 = first attempt)"
    )
    checksums: Dict[str, str] = Field(
        default_factory=dict,
        description="Key: attempt number, Value: SHA256 checksum (Research Decision 5)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "processing",
                "validation_status": None,
                "input_path": "/uploads/spikeglx_data.bin",
                "output_path": "/outputs/mouse_001.nwb",
                "metadata": {
                    "subject_id": "mouse_001",
                    "species": "Mus musculus",
                    "session_description": "Neuropixels recording",
                    "session_start_time": "2025-10-15T09:00:00Z"
                },
                "logs": [],
                "stages": [
                    {
                        "name": "conversion",
                        "status": "completed",
                        "start_time": "2025-10-15T10:00:00Z",
                        "end_time": "2025-10-15T10:05:00Z"
                    }
                ],
                "timestamps": {
                    "upload": "2025-10-15T09:55:00Z",
                    "conversion_start": "2025-10-15T10:00:00Z"
                },
                "correction_attempt": 0,
                "checksums": {
                    "1": "a3f9d1c8b7e2f4d9...",
                    "2": "b7e2f4d9a3f9d1c8..."
                }
            }
        }
```

**Usage**:
- Singleton instance in `backend/src/api/main.py`
- Injected into all MCP messages via context (Story 1.3)
- Reset after each conversion completes (Story 2.1)

---

### 3. Validation Result Schema

**Purpose**: Structure for NWB Inspector validation results.

**File**: `backend/src/models/validation.py`

```python
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional

class IssueSeverity(str, Enum):
    """NWB Inspector issue severity levels (Story 7.2)"""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    BEST_PRACTICE = "BEST_PRACTICE"

class OverallStatus(str, Enum):
    """Three-tier validation status (Story 7.2)"""
    PASSED = "PASSED"                      # No issues at all
    PASSED_WITH_ISSUES = "PASSED_WITH_ISSUES"  # Only WARNING or BEST_PRACTICE issues
    FAILED = "FAILED"                      # Has CRITICAL or ERROR issues

class ValidationIssue(BaseModel):
    """Individual validation issue from NWB Inspector (Story 7.2)"""
    check_name: str = Field(..., description="Name of the NWB Inspector check")
    severity: IssueSeverity
    message: str = Field(..., description="Human-readable description of the issue")
    location: str = Field(..., description="Path in NWB file where issue occurs (e.g., '/general/subject')")
    file_path: str = Field(..., description="Path to the NWB file")
    importance: Optional[str] = Field(None, description="NWB Inspector importance level")

class FileInfo(BaseModel):
    """Comprehensive NWB file information (Story 7.1)"""
    nwb_version: str
    creation_date: datetime
    identifier: str
    session_description: str
    subject_id: Optional[str] = None
    species: Optional[str] = None
    age: Optional[str] = None
    sex: Optional[str] = None
    experimenter: Optional[List[str]] = None
    institution: Optional[str] = None
    lab: Optional[str] = None
    devices: List[str] = Field(default_factory=list)
    electrode_groups: List[str] = Field(default_factory=list)
    acquisition_data: List[Dict[str, Any]] = Field(default_factory=list)
    processing_modules: List[str] = Field(default_factory=list)
    file_size_bytes: int
    temporal_coverage_seconds: Optional[float] = None

class ValidationResult(BaseModel):
    """
    Complete validation result from Evaluation Agent.
    Passed between Evaluation Agent and Conversation Agent.

    Related Stories: 7.2 (Schema Validation), 7.3 (Result Processing)
    """
    overall_status: OverallStatus
    issues: List[ValidationIssue] = Field(default_factory=list)
    issue_counts: Dict[IssueSeverity, int] = Field(
        default_factory=lambda: {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.ERROR: 0,
            IssueSeverity.WARNING: 0,
            IssueSeverity.BEST_PRACTICE: 0
        }
    )
    file_info: FileInfo
    timestamp: datetime = Field(default_factory=datetime.now)
    nwb_file_path: str
    checksum_sha256: Optional[str] = Field(
        None,
        description="SHA256 checksum of NWB file (Story 8.7, Research Decision 5)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "overall_status": "PASSED_WITH_ISSUES",
                "issues": [
                    {
                        "check_name": "subject_age_check",
                        "severity": "WARNING",
                        "message": "Subject age is missing. Recommended for DANDI archive.",
                        "location": "/general/subject",
                        "file_path": "/outputs/mouse_001.nwb"
                    }
                ],
                "issue_counts": {
                    "CRITICAL": 0,
                    "ERROR": 0,
                    "WARNING": 1,
                    "BEST_PRACTICE": 0
                },
                "file_info": {
                    "nwb_version": "2.6.0",
                    "subject_id": "mouse_001",
                    "species": "Mus musculus"
                },
                "timestamp": "2025-10-15T10:10:00Z",
                "nwb_file_path": "/outputs/mouse_001.nwb",
                "checksum_sha256": "a3f9d1c8b7e2f4d9..."
            }
        }
```

**Usage**:
- Evaluation Agent generates after running NWB Inspector (Story 7.2)
- Sent to Conversation Agent via MCP for user notification (Story 8.2)
- Used by Report Service to generate PDF/JSON reports (Stories 9.5, 9.6)

---

### 4. Correction Context Schema

**Purpose**: Context passed from Evaluation Agent to Conversation Agent for corrections.

**File**: `backend/src/models/correction.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from .validation import ValidationResult, ValidationIssue

class FixStrategy(BaseModel):
    """Suggested fix for an issue (Story 8.1)"""
    issue_id: str = Field(..., description="Reference to ValidationIssue")
    strategy: str = Field(..., description="Human-readable fix strategy")
    auto_fixable: bool = Field(..., description="Can system fix automatically?")
    user_input_required: bool = Field(..., description="Does this require user input?")
    user_prompt: Optional[str] = Field(None, description="If user input required, what to ask")
    estimated_effort: Optional[str] = Field(None, description="'easy', 'medium', 'hard'")

class CorrectionContext(BaseModel):
    """
    Context passed from Evaluation Agent to Conversation Agent
    when validation fails or passes with issues.

    Related Stories: 8.1 (Context Generation), 8.2 (User Notification), 8.3 (Approval Handler)
    """
    validation_result: ValidationResult
    auto_fixable_issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="Issues the system can fix automatically (Story 8.5)"
    )
    user_input_required_issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="Issues requiring user to provide data (Story 8.6)"
    )
    suggested_fixes: List[FixStrategy] = Field(default_factory=list)
    attempt_number: int = Field(default=1, description="Which correction attempt (1, 2, 3, ...)")
    previous_issues: Optional[List[ValidationIssue]] = Field(
        None,
        description="Issues from previous attempt (for detecting 'no progress', Story 4.7)"
    )
    llm_analysis: Optional[str] = Field(
        None,
        description="LLM's analysis of the issues (Story 4.4, 9.4)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "validation_result": {"overall_status": "FAILED", "issues": [...]},
                "auto_fixable_issues": [],
                "user_input_required_issues": [
                    {
                        "check_name": "subject_id_missing",
                        "severity": "ERROR",
                        "message": "Subject ID is required"
                    }
                ],
                "suggested_fixes": [
                    {
                        "issue_id": "subject_id_missing",
                        "strategy": "Prompt user to provide subject_id",
                        "auto_fixable": False,
                        "user_input_required": True,
                        "user_prompt": "What is the subject ID? (e.g., 'mouse_001')"
                    }
                ],
                "attempt_number": 1
            }
        }
```

**Usage**:
- Evaluation Agent creates after validation (Story 8.1)
- Conversation Agent uses to determine user prompts (Story 8.2)
- Drives correction loop orchestration (Story 4.7, 8.7)

---

### 5. API Request/Response Schemas

**Purpose**: Type-safe API endpoint contracts.

**File**: `backend/src/models/api_schemas.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from .global_state import ConversionStatus, ValidationStatus, Stage, LogEntry
from .validation import IssueSeverity

class UploadRequest(BaseModel):
    """Request body for file upload (Story 10.2)"""
    subject_id: str
    species: str
    session_description: str
    session_start_time: str = Field(..., description="ISO 8601 format")
    experimenter: Optional[str] = None
    institution: Optional[str] = None
    lab: Optional[str] = None
    age: Optional[str] = None
    sex: Optional[str] = None
    weight: Optional[str] = None

class StatusResponse(BaseModel):
    """Response from GET /api/status (Story 10.4)"""
    status: ConversionStatus
    validation_status: Optional[ValidationStatus]
    current_stage: Optional[Stage]
    stages: List[Stage]
    metadata: Dict[str, Any]
    logs: List[LogEntry]
    validation_details: Optional[Dict[IssueSeverity, int]] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None

class RetryApprovalRequest(BaseModel):
    """Request body for POST /api/retry-approval (Story 8.3)"""
    approved: bool = Field(..., description="True = user approves retry, False = user declines")
    accept_as_is: Optional[bool] = Field(
        False,
        description="For PASSED_WITH_ISSUES: accept file without improvement (Story 8.3a)"
    )

class UserInputRequest(BaseModel):
    """Request body for POST /api/user-input (Story 8.6)"""
    field_name: str
    value: Any

class WebSocketMessage(BaseModel):
    """WebSocket progress update message (Story 10.5, Research Decision 3)"""
    type: str = Field(
        ...,
        description="Message type: 'progress', 'stage_update', 'notification', 'error'"
    )
    message: str
    stage: Optional[str] = None
    status: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**Usage**:
- FastAPI endpoint type hints (Epic 10)
- Frontend TypeScript interface generation (Epic 11)
- API documentation (FastAPI auto-generates from these schemas)

---

## Schema Relationships

```
┌─────────────────┐
│  MCPMessage     │ ──┐
└─────────────────┘   │
                      │  All agents communicate via MCP
                      ▼
              ┌────────────────┐
              │  MCP Server    │
              │  (routes msgs) │
              └────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │Conversa- │ │Conversion│ │Evaluation│
    │tion Agent│ │  Agent   │ │  Agent   │
    └──────────┘ └──────────┘ └──────────┘
          │           │           │
          │           │           └──> ValidationResult ──┐
          │           │                                    │
          │           └──> (converts files)               │
          │                                                 │
          └──> receives CorrectionContext <────────────────┘
                      │
                      └──> sends to User (WebSocketMessage, API responses)

Global State: Accessible by all agents via MCP context injection
```

---

## State Machines

### Conversion Status State Machine

```
IDLE ──(upload)──> PROCESSING ──(success)──> COMPLETED
                        │
                        └──(error)──> FAILED
```

### Validation Status State Machine

```
null (not yet validated)
  │
  ├──> PASSED (no issues)
  │
  ├──> PASSED_WITH_ISSUES
  │      ├──(user: Accept As-Is)──> passed_accepted
  │      └──(user: Improve + success)──> passed_improved
  │
  └──> FAILED
         ├──(user: Decline Retry)──> failed_user_declined
         └──(user: Cancel Input)──> failed_user_abandoned
```

### Stage Status State Machine

```
PENDING ──> IN_PROGRESS ──(success)──> COMPLETED
                  │
                  └──(error)──> FAILED
```

---

## Validation Rules

### MCPMessage
- `target_agent` must be in MCP server registry
- `action` must be a valid handler method for target agent
- `message_id` automatically generated (UUID4)

### GlobalState
- `status` resets to IDLE after conversion completes
- `validation_status` null until evaluation runs
- `correction_attempt` increments with each retry
- `checksums` keys match attempt numbers

### ValidationResult
- `overall_status` derived from issue severity counts:
  - FAILED: ≥1 CRITICAL or ERROR
  - PASSED_WITH_ISSUES: 0 CRITICAL/ERROR, ≥1 WARNING/BEST_PRACTICE
  - PASSED: 0 issues
- `issue_counts` must sum to `len(issues)`

### CorrectionContext
- `attempt_number` matches GlobalState.correction_attempt
- `previous_issues` used to detect "no progress" (Story 4.7)

---

**Data Model Complete**: All Pydantic schemas defined and documented.

**Next**: Create API contracts (OpenAPI, MCP messages, WebSocket events)
