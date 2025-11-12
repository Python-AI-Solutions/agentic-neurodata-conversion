"""Global state management for conversion pipeline.

This module defines the GlobalState model that tracks the entire conversion
lifecycle, from upload through validation to final output.
"""

import asyncio
import threading
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Import MCPEvent for WebSocket progress events
# Safe to import here - no circular dependency (mcp.py doesn't import state.py)
try:
    from models.mcp import MCPEvent
except ImportError:
    # If MCPEvent is not available, WebSocket events will be disabled
    MCPEvent = None


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
    """Final session outcome status tracking user decisions.

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


class ValidationOutcome(str, Enum):
    """NWB Inspector validation outcome.

    WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Replace string-based overall_status
    with type-safe enum (Recommendation 6.2)
    """

    PASSED = "PASSED"
    PASSED_WITH_ISSUES = "PASSED_WITH_ISSUES"
    FAILED = "FAILED"


class ConversationPhase(str, Enum):
    """Current phase of user conversation.

    WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Replace string-based conversation_type
    with type-safe enum (Recommendation 6.2, Breaking Point #3)
    """

    IDLE = "idle"  # No active conversation
    METADATA_COLLECTION = "required_metadata"  # Collecting required metadata
    VALIDATION_ANALYSIS = "validation_analysis"  # Analyzing validation failures
    IMPROVEMENT_DECISION = "improvement_decision"  # User deciding improve/accept


class MetadataRequestPolicy(str, Enum):
    """Policy for metadata requests.

    WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Unify metadata_requests_count and
    user_wants_minimal into single enum (Recommendation 6.4, Breaking Point #5)
    """

    NOT_ASKED = "not_asked"  # Haven't requested metadata yet
    ASKED_ONCE = "asked_once"  # Requested once, awaiting response
    USER_PROVIDED = "user_provided"  # User gave metadata
    USER_DECLINED = "user_declined"  # User explicitly declined
    PROCEEDING_MINIMAL = "proceeding_minimal"  # Proceeding with minimal metadata


class LogLevel(str, Enum):
    """Log entry severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetadataProvenance(str, Enum):
    """Tracks the source and origin of metadata fields.

    Essential for scientific transparency, DANDI compliance, and user trust.
    Allows users to understand reliability and review requirements for each field.
    """

    USER_SPECIFIED = "user-specified"  # User explicitly provided this value
    AI_PARSED = "ai-parsed"  # LLM parsed from natural language input
    AI_INFERRED = "ai-inferred"  # AI guessed/inferred from context
    AUTO_EXTRACTED = "auto-extracted"  # Extracted from file metadata (.meta, .json)
    AUTO_CORRECTED = "auto-corrected"  # Applied during validation error correction
    DEFAULT = "default"  # Fallback/placeholder value
    SYSTEM_GENERATED = "system-generated"  # Auto-generated (UUIDs, timestamps)


class LogEntry(BaseModel):
    """Individual log entry in the conversion process."""

    timestamp: datetime = Field(default_factory=datetime.now)
    level: LogLevel
    message: str
    context: dict[str, Any] = Field(default_factory=dict)

    # Pydantic V2 configuration
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class ProvenanceInfo(BaseModel):
    """Tracks the source, confidence, and origin of a metadata field.

    Provides complete audit trail for scientific reproducibility and DANDI compliance.
    """

    value: Any = Field(description="The actual metadata value")
    provenance: MetadataProvenance = Field(description="How this value was obtained")
    confidence: float = Field(
        default=100.0, ge=0.0, le=100.0, description="Confidence score (0-100) for AI-parsed/inferred values"
    )
    source: str = Field(description="Human-readable description of where this value came from")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this provenance was recorded")
    needs_review: bool = Field(default=False, description="Flag indicating low-confidence field requiring user review")
    raw_input: str | None = Field(
        default=None, description="Original user input or file content that led to this value"
    )

    # Pydantic V2 configuration
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


# Retry limit to prevent infinite loops and protect API budget
# Matches documented architecture (CLAUDE.md) and industry standards
MAX_RETRY_ATTEMPTS = 5


class GlobalState(BaseModel):
    """Central state object tracking the entire conversion pipeline.

    This state is shared across all agents and updated via MCP messages.
    """

    # Status tracking
    status: ConversionStatus = Field(default=ConversionStatus.IDLE)
    validation_status: ValidationStatus | None = Field(
        default=None, description="Final session outcome including user decisions (Story 2.1, 8.8)"
    )
    # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use ValidationOutcome enum instead of string
    overall_status: ValidationOutcome | None = Field(
        default=None, description="NWB Inspector evaluation result: PASSED, PASSED_WITH_ISSUES, or FAILED (Story 7.2)"
    )

    # Thread safety - not serialized by Pydantic (Pydantic V2: private field)
    _status_lock: asyncio.Lock | None = None
    _conversation_lock: asyncio.Lock | None = None
    _llm_lock: asyncio.Lock | None = None
    _lock_init_lock: threading.Lock | None = None  # Thread-safe lock for initializing async locks
    _mcp_server: Any | None = None  # Reference to MCP server for event broadcasting

    # LLM processing state
    llm_processing: bool = Field(
        default=False,
        description="EDGE CASE FIX #1: Flag indicating LLM call in progress (prevents concurrent LLM calls)",
    )

    # File paths
    input_path: str | None = Field(default=None)
    output_path: str | None = Field(default=None)
    pending_conversion_input_path: str | None = Field(
        default=None,
        description="Stores original input_path when metadata conversation starts, used to resume conversion after skip",
    )
    detected_format: str | None = Field(
        default=None, description="Auto-detected data format (e.g., SpikeGLX, OpenEphys)"
    )

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    inference_result: dict[str, Any] = Field(
        default_factory=dict, description="Internal metadata inference results (not included in NWB output)"
    )
    user_provided_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata explicitly provided by user (separate from auto-inferred)"
    )
    auto_extracted_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata automatically extracted from file analysis (separate from user-provided)",
    )
    metadata_provenance: dict[str, ProvenanceInfo] = Field(
        default_factory=dict,
        description="Tracks source, confidence, and origin of each metadata field for scientific transparency",
    )

    # Progress tracking
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    progress_message: str | None = Field(default=None)
    current_stage: str | None = Field(default=None)

    # Conversational state
    # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use ConversationPhase enum instead of string
    conversation_phase: ConversationPhase = Field(
        default=ConversationPhase.IDLE, description="Current phase of user conversation"
    )
    # Deprecated: kept for backward compatibility during migration, use conversation_phase instead
    conversation_type: str | None = Field(default=None, description="DEPRECATED: Use conversation_phase instead")
    llm_message: str | None = Field(default=None)
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Conversation history for LLM context (rolling window of last 50 messages)"
    )

    # Conversation memory - track user preferences
    user_declined_fields: set[str] = Field(
        default_factory=set, description="Fields/metadata that user explicitly declined to provide"
    )
    already_asked_fields: set[str] = Field(
        default_factory=set,
        description="Fields that have already been requested from user in this session (prevents re-asking)",
    )
    # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use MetadataRequestPolicy enum
    metadata_policy: MetadataRequestPolicy = Field(
        default=MetadataRequestPolicy.NOT_ASKED,
        description="Policy for metadata requests - replaces metadata_requests_count and user_wants_minimal",
    )
    # Deprecated: kept for backward compatibility during migration
    metadata_requests_count: int = Field(
        default=0,
        ge=0,
        description="DEPRECATED: Use metadata_policy instead. Number of times we've asked user for metadata",
    )
    user_wants_minimal: bool = Field(
        default=False,
        description="DEPRECATED: Use metadata_policy instead. User has indicated they want minimal metadata conversion",
    )
    user_wants_sequential: bool = Field(
        default=False, description="User has requested sequential (one-by-one) questions instead of batch"
    )
    pending_parsed_fields: dict[str, Any] = Field(
        default_factory=dict, description="Temporarily stores parsed metadata fields awaiting user confirmation"
    )

    # Logs and history
    logs: list[LogEntry] = Field(default_factory=list)
    log_file_path: str | None = Field(
        default=None, description="Path to persistent log file for this conversion session"
    )

    # Correction tracking
    # Retry limit enforced to prevent infinite loops and protect API budget
    correction_attempt: int = Field(default=0, ge=0, le=MAX_RETRY_ATTEMPTS)

    # Bug #11 fix: Track previous validation issues for "no progress" detection (Story 4.7 lines 461-466)
    previous_validation_issues: list[dict[str, Any]] | None = Field(
        default=None, description="Validation issues from previous attempt for detecting 'no progress'"
    )
    user_provided_input_this_attempt: bool = Field(
        default=False, description="Whether user provided new input in current correction attempt"
    )
    auto_corrections_applied_this_attempt: bool = Field(
        default=False, description="Whether automatic corrections were applied in current attempt"
    )

    # File integrity
    checksums: dict[str, str] = Field(
        default_factory=dict,
        description="SHA256 checksums: {file_path: checksum}",
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Pydantic V2 configuration
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        arbitrary_types_allowed=True,  # Allow asyncio.Lock type
    )

    def __init__(self, **data):
        """Initialize GlobalState with async locks."""
        super().__init__(**data)
        # Initialize locks as None - will be created lazily when needed in async context
        # This avoids "no event loop" errors when GlobalState is created outside async context
        object.__setattr__(self, "_status_lock", None)
        object.__setattr__(self, "_conversation_lock", None)
        object.__setattr__(self, "_llm_lock", None)
        object.__setattr__(self, "_lock_init_lock", threading.Lock())  # Thread-safe lock initialization

    def set_mcp_server(self, mcp_server: Any) -> None:
        """Set MCP server reference for event broadcasting.

        Args:
            mcp_server: MCP server instance
        """
        object.__setattr__(self, "_mcp_server", mcp_server)

    def add_log(self, level: LogLevel, message: str, context: dict[str, Any] | None = None) -> None:
        """Add a log entry to the state.

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

    def add_conversation_message(self, role: str, content: str, context: dict[str, Any] | None = None) -> None:
        """Add a message to conversation history with rolling window (SYNCHRONOUS VERSION - for backward compatibility).

        DEPRECATED: Use add_conversation_message_safe() for thread-safe async operations.
        This method is kept for backward compatibility but is NOT thread-safe.

        Keeps only the last 50 messages to prevent memory leaks.

        Args:
            role: Role of the speaker ("user" or "assistant")
            content: Message content
            context: Optional context data
        """
        message: dict[str, Any] = {
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

    async def add_conversation_message_safe(
        self, role: str, content: str, context: dict[str, Any] | None = None
    ) -> None:
        """Add a message to conversation history with rolling window (THREAD-SAFE ASYNC VERSION).

        BUG FIX #1: Prevents race conditions in concurrent access to conversation_history.
        Use this method instead of add_conversation_message() in async contexts.

        Keeps only the last 50 messages to prevent memory leaks.

        Args:
            role: Role of the speaker ("user" or "assistant")
            content: Message content
            context: Optional context data
        """
        # Lazy initialization of conversation lock (thread-safe)
        if self._conversation_lock is None:
            with self._lock_init_lock:
                # Double-check pattern to prevent race condition
                if self._conversation_lock is None:
                    object.__setattr__(self, "_conversation_lock", asyncio.Lock())

        message: dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if context:
            message["context"] = context

        async with self._conversation_lock:
            self.conversation_history.append(message)

            # Rolling window: keep only last 50 messages
            if len(self.conversation_history) > 50:
                self.conversation_history = self.conversation_history[-50:]

        self.updated_at = datetime.now()

    async def get_conversation_history_snapshot(self) -> list[dict[str, Any]]:
        """Get an immutable snapshot of conversation history (THREAD-SAFE).

        BUG FIX #1: Safe to iterate without race conditions even if history is being modified.

        Returns:
            Copy of conversation history list
        """
        # Lazy initialization of conversation lock (thread-safe)
        if self._conversation_lock is None:
            with self._lock_init_lock:
                # Double-check pattern to prevent race condition
                if self._conversation_lock is None:
                    object.__setattr__(self, "_conversation_lock", asyncio.Lock())

        async with self._conversation_lock:
            return list(self.conversation_history)  # Return copy

    async def clear_conversation_history_safe(self) -> None:
        """Clear conversation history (THREAD-SAFE).

        BUG FIX #1: Prevents race conditions when clearing history.
        """
        # Lazy initialization of conversation lock (thread-safe)
        if self._conversation_lock is None:
            with self._lock_init_lock:
                # Double-check pattern to prevent race condition
                if self._conversation_lock is None:
                    object.__setattr__(self, "_conversation_lock", asyncio.Lock())

        async with self._conversation_lock:
            self.conversation_history.clear()

    def reset(self) -> None:
        """Reset state to initial values for a new conversion.

        WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Complete state reset (Breaking Point #6)
        """
        self.status = ConversionStatus.IDLE
        self.validation_status = None
        self.overall_status = None
        self.llm_processing = False  # EDGE CASE FIX #1: Reset LLM processing flag
        self.input_path = None
        self.output_path = None
        self.pending_conversion_input_path = None
        self.metadata = {}
        # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Clear all metadata caches
        self.inference_result = {}
        self.auto_extracted_metadata = {}
        self.user_provided_metadata = {}
        self.metadata_provenance = {}
        self.logs = []
        self.log_file_path = None
        self.correction_attempt = 0
        self.checksums = {}
        # Reset "no progress" detection fields
        self.previous_validation_issues = None
        self.user_provided_input_this_attempt = False
        self.auto_corrections_applied_this_attempt = False
        self.user_declined_fields = set()
        # Reset new enum fields
        self.conversation_phase = ConversationPhase.IDLE
        self.metadata_policy = MetadataRequestPolicy.NOT_ASKED
        # Reset deprecated fields for backward compatibility
        self.metadata_requests_count = 0
        self.user_wants_minimal = False
        self.user_wants_sequential = False
        self.conversation_history = []
        self.progress_percent = 0.0
        self.progress_message = None
        self.current_stage = None
        self.llm_message = None
        self.conversation_type = None
        self.updated_at = datetime.now()

    def update_progress(self, percent: float, message: str | None = None, stage: str | None = None) -> None:
        """Update conversion progress and emit WebSocket event.

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

        # Emit WebSocket event for real-time progress updates
        if self._mcp_server and MCPEvent:
            try:
                event = MCPEvent(
                    event_type="progress_update",
                    data={
                        "progress": self.progress_percent,
                        "progress_message": self.progress_message,
                        "current_stage": self.current_stage,
                        "status": self.status.value if self.status else None,
                    },
                )

                # Broadcast event safely from any thread context
                try:
                    # Try to get running event loop (works from async context)
                    loop = asyncio.get_running_loop()
                    # Schedule coroutine in the event loop from another thread
                    asyncio.run_coroutine_threadsafe(self._mcp_server.broadcast_event(event), loop)
                except RuntimeError:
                    # No event loop running (e.g., called from background thread)
                    # Skip WebSocket broadcast - progress still tracked via polling
                    pass
            except Exception as e:
                # Log error but don't fail the progress update
                self.add_log(
                    LogLevel.WARNING,
                    f"Failed to broadcast progress event via WebSocket: {e}",
                )

    # Bug #14 fix: Removed can_retry() - unlimited retries with user permission
    # No programmatic limit on retry attempts (Story 8.7 line 933, Story 8.8 line 953)

    def detect_no_progress(self, current_issues: list[dict[str, Any]]) -> bool:
        """Bug #11 fix: Detect if retry attempt is making no progress (Story 4.7 lines 461-466).

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
        def normalize_issue(issue: dict[str, Any]) -> str:
            """Create normalized string representation of issue for comparison."""
            return f"{issue.get('check_name', '')}|{issue.get('location', '')}|{issue.get('message', '')}"

        previous_normalized = {normalize_issue(issue) for issue in self.previous_validation_issues}
        current_normalized = {normalize_issue(issue) for issue in current_issues}

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
        """Update the conversion status with thread safety.

        Args:
            status: New status
        """
        # Thread-safe lazy initialization of async lock
        if self._status_lock is None:
            with self._lock_init_lock:
                # Double-check pattern to prevent race condition
                if self._status_lock is None:
                    object.__setattr__(self, "_status_lock", asyncio.Lock())

        async with self._status_lock:
            self.status = status
            self.updated_at = datetime.now()
            self.add_log(
                LogLevel.INFO,
                f"Status changed to {status.value}",
                {"status": status.value},
            )

    def update_status_sync(self, status: ConversionStatus) -> None:
        """Synchronous version of update_status for backward compatibility.

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
        """Update the validation status with thread safety.

        Args:
            validation_status: New validation status
        """
        # Thread-safe lazy initialization of async lock
        if self._status_lock is None:
            with self._lock_init_lock:
                # Double-check pattern to prevent race condition
                if self._status_lock is None:
                    object.__setattr__(self, "_status_lock", asyncio.Lock())

        async with self._status_lock:
            self.validation_status = validation_status
            self.updated_at = datetime.now()
            self.add_log(
                LogLevel.INFO,
                f"Validation status changed to {validation_status.value}",
                {"validation_status": validation_status.value},
            )

    async def finalize_validation(
        self, conversion_status: ConversionStatus, validation_status: ValidationStatus
    ) -> None:
        """Atomically update both conversion and validation statuses.

        Args:
            conversion_status: New conversion status
            validation_status: New validation status
        """
        # Thread-safe lazy initialization of async lock
        if self._status_lock is None:
            with self._lock_init_lock:
                # Double-check pattern to prevent race condition
                if self._status_lock is None:
                    object.__setattr__(self, "_status_lock", asyncio.Lock())

        async with self._status_lock:
            self.status = conversion_status
            self.validation_status = validation_status
            self.updated_at = datetime.now()
            self.add_log(
                LogLevel.INFO,
                f"Status finalized: {conversion_status.value}, validation: {validation_status.value}",
                {"conversion_status": conversion_status.value, "validation_status": validation_status.value},
            )

    async def set_validation_result(
        self,
        overall_status: ValidationOutcome,
        requires_user_decision: bool = False,
        conversation_phase: ConversationPhase | None = None,
    ) -> None:
        """Atomically update validation result and related state.

        WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Atomic state updates (Recommendation 6.3, Breaking Point #2)

        Args:
            overall_status: NWB Inspector validation outcome
            requires_user_decision: Whether user needs to make a decision
            conversation_phase: Optional conversation phase to set
        """
        # Thread-safe lazy initialization of async lock
        if self._status_lock is None:
            with self._lock_init_lock:
                # Double-check pattern to prevent race condition
                if self._status_lock is None:
                    object.__setattr__(self, "_status_lock", asyncio.Lock())

        async with self._status_lock:
            self.overall_status = overall_status

            if requires_user_decision:
                self.status = ConversionStatus.AWAITING_USER_INPUT
                self.conversation_phase = conversation_phase or ConversationPhase.IMPROVEMENT_DECISION
                # Set deprecated field for backward compatibility
                self.conversation_type = self.conversation_phase.value
            else:
                self.status = ConversionStatus.COMPLETED
                self.conversation_phase = ConversationPhase.IDLE
                self.conversation_type = None

            self.updated_at = datetime.now()
            self.add_log(
                LogLevel.INFO,
                f"Validation result set atomically: {overall_status.value}, "
                f"status: {self.status.value}, phase: {self.conversation_phase.value}",
                {
                    "overall_status": overall_status.value,
                    "status": self.status.value,
                    "conversation_phase": self.conversation_phase.value,
                },
            )

    def get_llm_lock(self) -> asyncio.Lock:
        """Get the LLM lock, initializing it lazily if needed (THREAD-SAFE).

        Returns:
            The asyncio.Lock for LLM operations
        """
        if self._llm_lock is None:
            with self._lock_init_lock:
                # Double-check pattern to prevent race condition
                if self._llm_lock is None:
                    object.__setattr__(self, "_llm_lock", asyncio.Lock())
        return self._llm_lock

    @property
    def can_retry(self) -> bool:
        """Check if more retry attempts are allowed.

        Prevents infinite loops and protects API budget.

        Returns:
            True if more retries allowed, False otherwise
        """
        return self.correction_attempt < MAX_RETRY_ATTEMPTS

    @property
    def retry_attempts_remaining(self) -> int:
        """Get number of retry attempts remaining.

        Returns:
            Number of retries left
        """
        return max(0, MAX_RETRY_ATTEMPTS - self.correction_attempt)
