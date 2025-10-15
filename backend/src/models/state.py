"""
Global state management for conversion pipeline.

This module defines the GlobalState model that tracks the entire conversion
lifecycle, from upload through validation to final output.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversionStatus(str, Enum):
    """Status of the conversion process."""

    IDLE = "idle"
    UPLOADING = "uploading"
    DETECTING_FORMAT = "detecting_format"
    AWAITING_USER_INPUT = "awaiting_user_input"
    CONVERTING = "converting"
    VALIDATING = "validating"
    AWAITING_RETRY_APPROVAL = "awaiting_retry_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationStatus(str, Enum):
    """Status of NWB validation."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED_WITH_ERRORS = "failed_with_errors"
    FAILED_WITH_WARNINGS = "failed_with_warnings"


class LogLevel(str, Enum):
    """Log entry severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEntry(BaseModel):
    """Individual log entry in the conversion process."""

    timestamp: datetime = Field(default_factory=datetime.now)
    level: LogLevel
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class GlobalState(BaseModel):
    """
    Central state object tracking the entire conversion pipeline.

    This state is shared across all agents and updated via MCP messages.
    """

    # Status tracking
    status: ConversionStatus = Field(default=ConversionStatus.IDLE)
    validation_status: Optional[ValidationStatus] = Field(default=None)

    # File paths
    input_path: Optional[str] = Field(default=None)
    output_path: Optional[str] = Field(default=None)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Logs and history
    logs: List[LogEntry] = Field(default_factory=list)

    # Correction tracking
    correction_attempt: int = Field(default=0, ge=0)
    max_correction_attempts: int = Field(default=3, ge=1)

    # File integrity
    checksums: Dict[str, str] = Field(
        default_factory=dict,
        description="SHA256 checksums: {file_path: checksum}",
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def add_log(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a log entry to the state.

        Args:
            level: Log severity level
            message: Log message
            context: Optional contextual data
        """
        log_entry = LogEntry(
            level=level,
            message=message,
            context=context or {},
        )
        self.logs.append(log_entry)
        self.updated_at = datetime.now()

    def reset(self) -> None:
        """Reset state to initial values for a new conversion."""
        self.status = ConversionStatus.IDLE
        self.validation_status = None
        self.input_path = None
        self.output_path = None
        self.metadata = {}
        self.logs = []
        self.correction_attempt = 0
        self.checksums = {}
        self.updated_at = datetime.now()

    def can_retry(self) -> bool:
        """Check if another correction attempt is allowed."""
        return self.correction_attempt < self.max_correction_attempts

    def increment_retry(self) -> None:
        """Increment the retry counter."""
        self.correction_attempt += 1
        self.updated_at = datetime.now()

    def update_status(self, status: ConversionStatus) -> None:
        """
        Update the conversion status.

        Args:
            status: New status
        """
        self.status = status
        self.updated_at = datetime.now()
        self.add_log(
            LogLevel.INFO,
            f"Status changed to {status.value}",
            {"status": status.value},
        )

    def update_validation_status(self, validation_status: ValidationStatus) -> None:
        """
        Update the validation status.

        Args:
            validation_status: New validation status
        """
        self.validation_status = validation_status
        self.updated_at = datetime.now()
        self.add_log(
            LogLevel.INFO,
            f"Validation status changed to {validation_status.value}",
            {"validation_status": validation_status.value},
        )
