"""
Global state management for conversion pipeline.

This module defines the GlobalState model that tracks the entire conversion
lifecycle, from upload through validation to final output.
"""
import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, ConfigDict


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
    """
    Final session outcome status tracking user decisions.

    This is distinct from overall_status (PASSED/PASSED_WITH_ISSUES/FAILED)
    which comes from NWB Inspector. ValidationStatus tracks the final outcome
    including user decisions.

    Story 2.1 (requirements.md line 220), Story 8.8 (lines 954-960)
    """

    PASSED = "passed"  # No issues at all
    PASSED_ACCEPTED = "passed_accepted"  # User accepted file with warnings
    PASSED_IMPROVED = "passed_improved"  # Warnings resolved through improvement
    FAILED_USER_DECLINED = "failed_user_declined"  # User declined retry
    FAILED_USER_ABANDONED = "failed_user_abandoned"  # User cancelled during input


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

    # Pydantic V2 configuration
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class GlobalState(BaseModel):
    """
    Central state object tracking the entire conversion pipeline.

    This state is shared across all agents and updated via MCP messages.
    """

    # Status tracking
    status: ConversionStatus = Field(default=ConversionStatus.IDLE)
    validation_status: Optional[ValidationStatus] = Field(
        default=None,
        description="Final session outcome including user decisions (Story 2.1, 8.8)"
    )
    overall_status: Optional[str] = Field(
        default=None,
        description="NWB Inspector evaluation result: PASSED, PASSED_WITH_ISSUES, or FAILED (Story 7.2)"
    )

    # Thread safety - not serialized by Pydantic (Pydantic V2: private field)
    _status_lock: Optional[asyncio.Lock] = None

    # File paths
    input_path: Optional[str] = Field(default=None)
    output_path: Optional[str] = Field(default=None)
    pending_conversion_input_path: Optional[str] = Field(
        default=None,
        description="Stores original input_path when metadata conversation starts, used to resume conversion after skip"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Progress tracking
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    progress_message: Optional[str] = Field(default=None)
    current_stage: Optional[str] = Field(default=None)

    # Conversational state
    conversation_type: Optional[str] = Field(default=None)
    llm_message: Optional[str] = Field(default=None)
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conversation history for LLM context (rolling window of last 50 messages)"
    )

    # Conversation memory - track user preferences
    user_declined_fields: Set[str] = Field(
        default_factory=set,
        description="Fields/metadata that user explicitly declined to provide"
    )
    metadata_requests_count: int = Field(
        default=0,
        ge=0,
        description="Number of times we've asked user for metadata"
    )
    user_wants_minimal: bool = Field(
        default=False,
        description="User has indicated they want minimal metadata conversion"
    )
    user_wants_sequential: bool = Field(
        default=False,
        description="User has requested sequential (one-by-one) questions instead of batch"
    )

    # Logs and history
    logs: List[LogEntry] = Field(default_factory=list)

    # Correction tracking
    # Bug #14 fix: No max limit - unlimited retries with user permission (Story 8.7 line 933, Story 8.8 line 953)
    correction_attempt: int = Field(default=0, ge=0)

    # Bug #11 fix: Track previous validation issues for "no progress" detection (Story 4.7 lines 461-466)
    previous_validation_issues: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Validation issues from previous attempt for detecting 'no progress'"
    )
    user_provided_input_this_attempt: bool = Field(
        default=False,
        description="Whether user provided new input in current correction attempt"
    )
    auto_corrections_applied_this_attempt: bool = Field(
        default=False,
        description="Whether automatic corrections were applied in current attempt"
    )

    # File integrity
    checksums: Dict[str, str] = Field(
        default_factory=dict,
        description="SHA256 checksums: {file_path: checksum}",
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Pydantic V2 configuration
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        arbitrary_types_allowed=True  # Allow asyncio.Lock type
    )

    def __init__(self, **data):
        """Initialize GlobalState with async lock."""
        super().__init__(**data)
        self._status_lock = asyncio.Lock()

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

    def add_conversation_message(self, role: str, content: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to conversation history with rolling window.

        Keeps only the last 50 messages to prevent memory leaks.

        Args:
            role: Role of the speaker ("user" or "assistant")
            content: Message content
            context: Optional context data
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if context:
            message["context"] = context

        self.conversation_history.append(message)

        # Rolling window: keep only last 50 messages
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

        self.updated_at = datetime.now()

    def reset(self) -> None:
        """Reset state to initial values for a new conversion."""
        self.status = ConversionStatus.IDLE
        self.validation_status = None
        self.overall_status = None  # Bug #15: Reset overall_status
        self.input_path = None
        self.output_path = None
        self.pending_conversion_input_path = None
        self.metadata = {}
        self.logs = []
        self.correction_attempt = 0
        self.checksums = {}
        # Bug #11 fix: Reset "no progress" detection fields
        self.previous_validation_issues = None
        self.user_provided_input_this_attempt = False
        self.auto_corrections_applied_this_attempt = False
        self.user_declined_fields = set()
        self.metadata_requests_count = 0
        self.user_wants_minimal = False
        self.user_wants_sequential = False
        self.conversation_history = []
        self.progress_percent = 0.0
        self.progress_message = None
        self.current_stage = None
        self.updated_at = datetime.now()

    def update_progress(
        self,
        percent: float,
        message: Optional[str] = None,
        stage: Optional[str] = None
    ) -> None:
        """
        Update conversion progress.

        Args:
            percent: Progress percentage (0-100)
            message: Optional progress message
            stage: Optional current stage name
        """
        self.progress_percent = max(0.0, min(100.0, percent))
        if message:
            self.progress_message = message
        if stage:
            self.current_stage = stage
        self.updated_at = datetime.now()

        self.add_log(
            LogLevel.INFO,
            f"Progress: {self.progress_percent:.1f}% - {message or stage or 'Processing...'}",
            {
                "progress_percent": self.progress_percent,
                "stage": stage,
            },
        )

    # Bug #14 fix: Removed can_retry() - unlimited retries with user permission
    # No programmatic limit on retry attempts (Story 8.7 line 933, Story 8.8 line 953)

    def detect_no_progress(self, current_issues: List[Dict[str, Any]]) -> bool:
        """
        Bug #11 fix: Detect if retry attempt is making no progress (Story 4.7 lines 461-466).

        No progress is detected when ALL of the following are true:
        - Same exact validation errors between attempts (error codes + locations match)
        - No user input provided since last attempt
        - No auto-corrections applied since last attempt

        Args:
            current_issues: Current validation issues from latest evaluation

        Returns:
            True if no progress detected, False otherwise
        """
        # First attempt always has "progress" (nothing to compare against)
        if self.previous_validation_issues is None or self.correction_attempt == 0:
            return False

        # If user provided input or auto-corrections applied, we have progress
        if self.user_provided_input_this_attempt or self.auto_corrections_applied_this_attempt:
            return False

        # Compare current issues with previous issues
        # Create normalized representations for comparison
        def normalize_issue(issue: Dict[str, Any]) -> str:
            """Create normalized string representation of issue for comparison."""
            return f"{issue.get('check_name', '')}|{issue.get('location', '')}|{issue.get('message', '')}"

        previous_normalized = set(normalize_issue(issue) for issue in self.previous_validation_issues)
        current_normalized = set(normalize_issue(issue) for issue in current_issues)

        # If issues are identical, no progress was made
        return previous_normalized == current_normalized

    def increment_retry(self) -> None:
        """Increment the retry counter."""
        self.correction_attempt += 1
        self.updated_at = datetime.now()

    def increment_correction_attempt(self) -> None:
        """Alias for increment_retry for clarity."""
        self.increment_retry()

    async def update_status(self, status: ConversionStatus) -> None:
        """
        Update the conversion status with thread safety.

        Args:
            status: New status
        """
        if self._status_lock is None:
            self._status_lock = asyncio.Lock()

        async with self._status_lock:
            self.status = status
            self.updated_at = datetime.now()
            self.add_log(
                LogLevel.INFO,
                f"Status changed to {status.value}",
                {"status": status.value},
            )

    def update_status_sync(self, status: ConversionStatus) -> None:
        """
        Synchronous version of update_status for backward compatibility.
        Use update_status() (async) when possible.

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

    async def update_validation_status(self, validation_status: ValidationStatus) -> None:
        """
        Update the validation status with thread safety.

        Args:
            validation_status: New validation status
        """
        if self._status_lock is None:
            self._status_lock = asyncio.Lock()

        async with self._status_lock:
            self.validation_status = validation_status
            self.updated_at = datetime.now()
            self.add_log(
                LogLevel.INFO,
                f"Validation status changed to {validation_status.value}",
                {"validation_status": validation_status.value},
            )

    async def finalize_validation(
        self,
        conversion_status: ConversionStatus,
        validation_status: ValidationStatus
    ) -> None:
        """
        Atomically update both conversion and validation statuses.

        Args:
            conversion_status: New conversion status
            validation_status: New validation status
        """
        if self._status_lock is None:
            self._status_lock = asyncio.Lock()

        async with self._status_lock:
            self.status = conversion_status
            self.validation_status = validation_status
            self.updated_at = datetime.now()
            self.add_log(
                LogLevel.INFO,
                f"Status finalized: {conversion_status.value}, validation: {validation_status.value}",
                {
                    "conversion_status": conversion_status.value,
                    "validation_status": validation_status.value
                },
            )
