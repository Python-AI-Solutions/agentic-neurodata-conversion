"""
API request/response models.

Models for FastAPI endpoints following OpenAPI specification.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from .state import (
    ConversionStatus,
    ValidationStatus,
    ValidationOutcome,
    ConversationPhase,
    MetadataRequestPolicy,
)
from .validation import ValidationIssue


class UploadResponse(BaseModel):
    """Response for file upload endpoint."""

    session_id: str = Field(description="Unique session identifier")
    message: str = Field(description="Status message")
    input_path: str = Field(description="Path to uploaded file")
    checksum: str = Field(default="", description="SHA256 checksum of uploaded file")
    status: Optional[str] = Field(default=None, description="Upload status")
    uploaded_files: Optional[List[str]] = Field(default=None, description="List of uploaded files")
    conversation_active: Optional[bool] = Field(default=None, description="Whether conversation is active")


class StatusResponse(BaseModel):
    """Response for status endpoint."""

    status: ConversionStatus
    validation_status: Optional[ValidationStatus] = None
    overall_status: Optional[str] = Field(
        default=None,
        description="NWB Inspector evaluation result: PASSED, PASSED_WITH_ISSUES, or FAILED (Bug #12)",
    )
    progress: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)",
    )
    progress_message: Optional[str] = Field(
        default=None,
        description="Detailed progress message (e.g., 'Writing data chunks...')",
    )
    current_stage: Optional[str] = Field(
        default=None,
        description="Current conversion stage name",
    )
    message: Optional[str] = Field(
        default=None,
        description="Current status message",
    )
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    correction_attempt: int = Field(
        default=0,
        description="Current correction attempt number",
    )
    can_retry: bool = Field(
        default=False,
        description="Whether retry is possible",
    )
    conversation_type: Optional[str] = Field(
        default=None,
        description="Type of conversation (e.g., 'validation_analysis')",
    )


class UserDecision(str, Enum):
    """
    User decision for retry/improvement approval.

    Story 8.3 (requirements.md lines 813-824)
    """

    APPROVE = "approve"  # Start improvement/retry
    REJECT = "reject"    # Decline retry
    ACCEPT = "accept"    # Accept as-is (PASSED_WITH_ISSUES only)


class RetryApprovalRequest(BaseModel):
    """Request for retry approval endpoint."""

    decision: UserDecision = Field(description="User's decision")
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes from user",
    )


class RetryApprovalResponse(BaseModel):
    """Response for retry approval endpoint."""

    accepted: bool = Field(description="Whether decision was accepted")
    message: str = Field(description="Status message")
    new_status: ConversionStatus = Field(
        description="New conversion status after decision",
    )


class UserInputRequest(BaseModel):
    """Request for user input submission endpoint."""

    input_data: Dict[str, Any] = Field(
        description="User-provided correction data",
    )


class UserInputResponse(BaseModel):
    """Response for user input submission endpoint."""

    accepted: bool = Field(description="Whether input was accepted")
    message: str = Field(description="Status message")
    new_status: ConversionStatus = Field(
        description="New conversion status after input",
    )


class ValidationResponse(BaseModel):
    """Response for validation results endpoint."""

    is_valid: bool = Field(description="Overall validation status")
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="Validation issues found",
    )
    summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Issue counts by severity",
    )


class LogsResponse(BaseModel):
    """Response for logs endpoint."""

    logs: List[Dict[str, Any]] = Field(
        description="List of log entries",
    )
    total_count: int = Field(
        description="Total number of log entries",
    )


class DownloadInfo(BaseModel):
    """Information about downloadable file."""

    filename: str = Field(description="Name of the file")
    size_bytes: int = Field(description="File size in bytes")
    checksum: str = Field(description="SHA256 checksum")
    created_at: datetime = Field(description="File creation timestamp")

    # Pydantic V2 configuration
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    error_code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Error timestamp",
    )

    # Pydantic V2 configuration
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    event_type: str = Field(description="Event type")
    data: Dict[str, Any] = Field(description="Event payload")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Event timestamp",
    )

    # Pydantic V2 configuration
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class StartConversionResponse(BaseModel):
    """Response for start conversion endpoint."""

    status: str = Field(description="Conversion initiation status")
    message: str = Field(description="Status message")
    session_id: Optional[str] = Field(default=None, description="Session identifier")


class ImprovementDecisionResponse(BaseModel):
    """Response for improvement decision endpoint."""

    status: str = Field(description="Decision processing status")
    message: str = Field(description="Response message")
    next_step: Optional[str] = Field(default=None, description="Next workflow step")


class ChatResponse(BaseModel):
    """Response for chat endpoints."""

    response: str = Field(description="Chat response message")
    status: Optional[str] = Field(default=None, description="Conversation status")
    conversation_type: Optional[str] = Field(default=None, description="Type of conversation")


class ResetResponse(BaseModel):
    """Response for reset endpoint."""

    status: str = Field(description="Reset status")
    message: str = Field(description="Confirmation message")


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: str = Field(description="Service health status", default="healthy")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check timestamp")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
