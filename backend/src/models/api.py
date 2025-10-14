"""
API request/response models.

Models for FastAPI endpoints following OpenAPI specification.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .state import ConversionStatus, ValidationStatus
from .validation import ValidationIssue


class UploadResponse(BaseModel):
    """Response for file upload endpoint."""

    session_id: str = Field(description="Unique session identifier")
    message: str = Field(description="Status message")
    input_path: str = Field(description="Path to uploaded file")
    checksum: str = Field(description="SHA256 checksum of uploaded file")


class StatusResponse(BaseModel):
    """Response for status endpoint."""

    status: ConversionStatus
    validation_status: Optional[ValidationStatus] = None
    progress: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)",
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


class UserDecision(str, Enum):
    """User decision for retry approval."""

    APPROVE = "approve"
    REJECT = "reject"


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

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


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

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    event_type: str = Field(description="Event type")
    data: Dict[str, Any] = Field(description="Event payload")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Event timestamp",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
