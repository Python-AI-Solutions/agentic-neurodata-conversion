"""
Unit tests for GlobalState and related models.

Tests central state management, thread safety, and state transitions.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock

import pytest
from models.state import (
    MAX_RETRY_ATTEMPTS,
    ConversationPhase,
    ConversionStatus,
    GlobalState,
    LogEntry,
    LogLevel,
    MetadataProvenance,
    MetadataRequestPolicy,
    ProvenanceInfo,
    ValidationOutcome,
    ValidationStatus,
)


@pytest.mark.unit
@pytest.mark.model
class TestEnums:
    """Tests for state enums."""

    @pytest.mark.smoke
    def test_conversion_status_values(self):
        """Test ConversionStatus enum values."""
        assert ConversionStatus.IDLE == "idle"
        assert ConversionStatus.UPLOADING == "uploading"
        assert ConversionStatus.DETECTING_FORMAT == "detecting_format"
        assert ConversionStatus.CONVERTING == "converting"
        assert ConversionStatus.VALIDATING == "validating"
        assert ConversionStatus.COMPLETED == "completed"
        assert ConversionStatus.FAILED == "failed"

    def test_validation_status_values(self):
        """Test ValidationStatus enum values."""
        assert ValidationStatus.PASSED == "passed"
        assert ValidationStatus.PASSED_ACCEPTED == "passed_accepted"
        assert ValidationStatus.PASSED_IMPROVED == "passed_improved"
        assert ValidationStatus.FAILED_USER_DECLINED == "failed_user_declined"

    def test_validation_outcome_values(self):
        """Test ValidationOutcome enum values."""
        assert ValidationOutcome.PASSED == "PASSED"
        assert ValidationOutcome.PASSED_WITH_ISSUES == "PASSED_WITH_ISSUES"
        assert ValidationOutcome.FAILED == "FAILED"

    def test_conversation_phase_values(self):
        """Test ConversationPhase enum values."""
        assert ConversationPhase.IDLE == "idle"
        assert ConversationPhase.METADATA_COLLECTION == "required_metadata"
        assert ConversationPhase.VALIDATION_ANALYSIS == "validation_analysis"
        assert ConversationPhase.IMPROVEMENT_DECISION == "improvement_decision"

    def test_metadata_request_policy_values(self):
        """Test MetadataRequestPolicy enum values."""
        assert MetadataRequestPolicy.NOT_ASKED == "not_asked"
        assert MetadataRequestPolicy.ASKED_ONCE == "asked_once"
        assert MetadataRequestPolicy.USER_PROVIDED == "user_provided"
        assert MetadataRequestPolicy.USER_DECLINED == "user_declined"
        assert MetadataRequestPolicy.PROCEEDING_MINIMAL == "proceeding_minimal"

    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.WARNING == "warning"
        assert LogLevel.ERROR == "error"
        assert LogLevel.CRITICAL == "critical"

    def test_metadata_provenance_values(self):
        """Test MetadataProvenance enum values."""
        assert MetadataProvenance.USER_SPECIFIED == "user-specified"
        assert MetadataProvenance.AI_PARSED == "ai-parsed"
        assert MetadataProvenance.AI_INFERRED == "ai-inferred"
        assert MetadataProvenance.AUTO_EXTRACTED == "auto-extracted"
        assert MetadataProvenance.AUTO_CORRECTED == "auto-corrected"
        assert MetadataProvenance.DEFAULT == "default"
        assert MetadataProvenance.SYSTEM_GENERATED == "system-generated"


@pytest.mark.unit
@pytest.mark.model
class TestLogEntry:
    """Tests for LogEntry model."""

    @pytest.mark.smoke
    def test_create_log_entry(self):
        """Test creating a log entry."""
        entry = LogEntry(level=LogLevel.INFO, message="Test message")

        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert isinstance(entry.timestamp, datetime)
        assert entry.context == {}

    def test_log_entry_with_context(self):
        """Test log entry with context data."""
        context = {"file": "test.nwb", "size": 1024}
        entry = LogEntry(level=LogLevel.WARNING, message="File warning", context=context)

        assert entry.context == context


@pytest.mark.unit
@pytest.mark.model
class TestProvenanceInfo:
    """Tests for ProvenanceInfo model."""

    @pytest.mark.smoke
    def test_create_provenance_info(self):
        """Test creating provenance info."""
        provenance = ProvenanceInfo(
            value="Mus musculus",
            provenance=MetadataProvenance.USER_SPECIFIED,
            confidence=100.0,
            source="User input",
        )

        assert provenance.value == "Mus musculus"
        assert provenance.provenance == MetadataProvenance.USER_SPECIFIED
        assert provenance.confidence == 100.0
        assert provenance.source == "User input"
        assert isinstance(provenance.timestamp, datetime)
        assert provenance.needs_review is False

    def test_provenance_info_with_low_confidence(self):
        """Test provenance info with low confidence needing review."""
        provenance = ProvenanceInfo(
            value="Rattus norvegicus",
            provenance=MetadataProvenance.AI_INFERRED,
            confidence=45.0,
            source="LLM inference",
            needs_review=True,
            raw_input="rat experiment",
        )

        assert provenance.confidence == 45.0
        assert provenance.needs_review is True
        assert provenance.raw_input == "rat experiment"


@pytest.mark.unit
@pytest.mark.model
class TestGlobalStateInitialization:
    """Tests for GlobalState initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        state = GlobalState()

        assert state.status == ConversionStatus.IDLE
        assert state.validation_status is None
        assert state.overall_status is None
        assert state.input_path is None
        assert state.output_path is None
        assert state.metadata == {}
        assert state.conversation_phase == ConversationPhase.IDLE
        assert state.metadata_policy == MetadataRequestPolicy.NOT_ASKED
        assert state.correction_attempt == 0
        assert state.progress_percent == 0.0
        assert state.llm_processing is False
        assert isinstance(state.logs, list)
        assert isinstance(state.conversation_history, list)

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        state = GlobalState(
            status=ConversionStatus.CONVERTING,
            input_path="/test/input.bin",
            detected_format="SpikeGLX",
        )

        assert state.status == ConversionStatus.CONVERTING
        assert state.input_path == "/test/input.bin"
        assert state.detected_format == "SpikeGLX"


@pytest.mark.unit
@pytest.mark.model
class TestGlobalStateLogs:
    """Tests for log management."""

    def test_add_log(self):
        """Test adding a log entry."""
        state = GlobalState()

        state.add_log(LogLevel.INFO, "Test log message")

        assert len(state.logs) == 1
        assert state.logs[0].level == LogLevel.INFO
        assert state.logs[0].message == "Test log message"

    def test_add_log_with_context(self):
        """Test adding log with context."""
        state = GlobalState()
        context = {"operation": "validation", "file": "test.nwb"}

        state.add_log(LogLevel.WARNING, "Validation warning", context)

        assert len(state.logs) == 1
        assert state.logs[0].context == context

    def test_add_multiple_logs(self):
        """Test adding multiple logs."""
        state = GlobalState()

        state.add_log(LogLevel.INFO, "First log")
        state.add_log(LogLevel.WARNING, "Second log")
        state.add_log(LogLevel.ERROR, "Third log")

        assert len(state.logs) == 3
        assert state.logs[0].message == "First log"
        assert state.logs[2].level == LogLevel.ERROR


@pytest.mark.unit
@pytest.mark.model
class TestConversationHistory:
    """Tests for conversation history management."""

    def test_add_conversation_message(self):
        """Test adding conversation message (sync version)."""
        state = GlobalState()

        state.add_conversation_message("user", "Hello")

        assert len(state.conversation_history) == 1
        assert state.conversation_history[0]["role"] == "user"
        assert state.conversation_history[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_add_conversation_message_safe(self):
        """Test adding conversation message (async thread-safe version)."""
        state = GlobalState()

        await state.add_conversation_message_safe("user", "Hello", context={"test": True})

        assert len(state.conversation_history) == 1
        assert state.conversation_history[0]["role"] == "user"
        assert state.conversation_history[0]["content"] == "Hello"
        assert state.conversation_history[0]["context"]["test"] is True

    def test_conversation_rolling_window(self):
        """Test conversation history rolling window (50 messages max)."""
        state = GlobalState()

        # Add 60 messages
        for i in range(60):
            state.add_conversation_message("user", f"Message {i}")

        # Should only keep last 50
        assert len(state.conversation_history) == 50
        assert state.conversation_history[0]["content"] == "Message 10"
        assert state.conversation_history[-1]["content"] == "Message 59"

    @pytest.mark.asyncio
    async def test_get_conversation_history_snapshot(self):
        """Test getting immutable snapshot of conversation history."""
        state = GlobalState()

        await state.add_conversation_message_safe("user", "Hello")
        await state.add_conversation_message_safe("assistant", "Hi there")

        snapshot = await state.get_conversation_history_snapshot()

        assert len(snapshot) == 2
        assert snapshot[0]["role"] == "user"
        # Verify it's a copy (modifying snapshot doesn't affect original)
        snapshot.append({"role": "test", "content": "test"})
        assert len(state.conversation_history) == 2

    @pytest.mark.asyncio
    async def test_clear_conversation_history_safe(self):
        """Test clearing conversation history."""
        state = GlobalState()

        await state.add_conversation_message_safe("user", "Hello")
        await state.add_conversation_message_safe("assistant", "Hi")

        await state.clear_conversation_history_safe()

        assert len(state.conversation_history) == 0


@pytest.mark.unit
@pytest.mark.model
class TestStateReset:
    """Tests for state reset functionality."""

    def test_reset_clears_state(self):
        """Test reset clears all state."""
        state = GlobalState(
            status=ConversionStatus.COMPLETED,
            input_path="/test/file.bin",
            output_path="/test/output.nwb",
            detected_format="SpikeGLX",
            correction_attempt=3,
        )
        state.add_log(LogLevel.INFO, "Test log")
        state.add_conversation_message("user", "Test message")

        state.reset()

        assert state.status == ConversionStatus.IDLE
        assert state.input_path is None
        assert state.output_path is None
        # Note: detected_format is intentionally NOT reset to preserve format detection results
        assert state.correction_attempt == 0
        assert len(state.logs) == 0
        assert len(state.conversation_history) == 0


@pytest.mark.unit
@pytest.mark.model
class TestProgressTracking:
    """Tests for progress tracking."""

    def test_update_progress(self):
        """Test updating progress."""
        state = GlobalState()

        state.update_progress(25.0, "Converting data")

        assert state.progress_percent == 25.0
        assert state.progress_message == "Converting data"

    def test_update_progress_with_stage(self):
        """Test updating progress with stage."""
        state = GlobalState()

        state.update_progress(50.0, "Validating", stage="validation")

        assert state.progress_percent == 50.0
        assert state.current_stage == "validation"


@pytest.mark.unit
@pytest.mark.model
class TestRetryManagement:
    """Tests for retry and correction management."""

    def test_increment_correction_attempt(self):
        """Test incrementing correction attempt."""
        state = GlobalState()

        state.increment_correction_attempt()

        assert state.correction_attempt == 1

    def test_increment_correction_attempt_multiple(self):
        """Test multiple increments."""
        state = GlobalState()

        state.increment_correction_attempt()
        state.increment_correction_attempt()
        state.increment_correction_attempt()

        assert state.correction_attempt == 3

    def test_can_retry_when_under_limit(self):
        """Test can_retry property returns True when under limit."""
        state = GlobalState(correction_attempt=2)

        assert state.can_retry is True

    def test_can_retry_when_at_limit(self):
        """Test can_retry property returns False at limit."""
        state = GlobalState(correction_attempt=MAX_RETRY_ATTEMPTS)

        assert state.can_retry is False

    def test_retry_attempts_remaining(self):
        """Test calculating remaining retry attempts via property."""
        state = GlobalState(correction_attempt=2)

        remaining = state.retry_attempts_remaining

        assert remaining == MAX_RETRY_ATTEMPTS - 2

    def test_retry_attempts_remaining_at_zero(self):
        """Test remaining attempts property when at limit."""
        state = GlobalState(correction_attempt=MAX_RETRY_ATTEMPTS)

        remaining = state.retry_attempts_remaining

        assert remaining == 0


@pytest.mark.unit
@pytest.mark.model
class TestDetectNoProgress:
    """Tests for no-progress detection."""

    def test_detect_no_progress_first_attempt(self):
        """Test no-progress detection on first attempt (no previous issues)."""
        state = GlobalState()
        current_issues = [{"message": "Missing experimenter"}]

        has_no_progress = state.detect_no_progress(current_issues)

        assert has_no_progress is False

    def test_detect_no_progress_when_same_issues(self):
        """Test detecting no progress when issues are identical."""
        state = GlobalState(correction_attempt=1)  # Must be > 0 for comparison
        issues = [{"message": "Missing experimenter"}, {"message": "Missing institution"}]

        state.previous_validation_issues = issues
        state.user_provided_input_this_attempt = False
        state.auto_corrections_applied_this_attempt = False

        has_no_progress = state.detect_no_progress(issues)

        assert has_no_progress is True

    def test_detect_no_progress_when_user_provided_input(self):
        """Test no detection when user provided new input."""
        state = GlobalState()
        issues = [{"message": "Missing experimenter"}]

        state.previous_validation_issues = issues
        state.user_provided_input_this_attempt = True

        has_no_progress = state.detect_no_progress(issues)

        assert has_no_progress is False

    def test_detect_no_progress_when_corrections_applied(self):
        """Test no detection when auto corrections were applied."""
        state = GlobalState()
        issues = [{"message": "Missing experimenter"}]

        state.previous_validation_issues = issues
        state.auto_corrections_applied_this_attempt = True

        has_no_progress = state.detect_no_progress(issues)

        assert has_no_progress is False

    def test_detect_no_progress_when_issues_changed(self):
        """Test no detection when issues have changed."""
        state = GlobalState()

        state.previous_validation_issues = [{"message": "Missing experimenter"}]
        current_issues = [{"message": "Missing institution"}]

        has_no_progress = state.detect_no_progress(current_issues)

        assert has_no_progress is False


@pytest.mark.unit
@pytest.mark.model
class TestStatusUpdates:
    """Tests for status update methods."""

    @pytest.mark.asyncio
    async def test_update_status(self):
        """Test async status update."""
        state = GlobalState()

        await state.update_status(ConversionStatus.CONVERTING)

        assert state.status == ConversionStatus.CONVERTING

    def test_update_status_sync(self):
        """Test sync status update (deprecated)."""
        state = GlobalState()

        state.update_status_sync(ConversionStatus.VALIDATING)

        assert state.status == ConversionStatus.VALIDATING

    @pytest.mark.asyncio
    async def test_update_validation_status(self):
        """Test updating validation status."""
        state = GlobalState()

        await state.update_validation_status(ValidationStatus.PASSED_ACCEPTED)

        assert state.validation_status == ValidationStatus.PASSED_ACCEPTED


@pytest.mark.unit
@pytest.mark.model
class TestValidationResults:
    """Tests for validation result management."""

    @pytest.mark.asyncio
    async def test_finalize_validation_passed(self):
        """Test finalizing validation with PASSED outcome."""
        state = GlobalState()

        await state.finalize_validation(
            conversion_status=ConversionStatus.COMPLETED,
            validation_status=ValidationStatus.PASSED,
        )

        assert state.status == ConversionStatus.COMPLETED
        assert state.validation_status == ValidationStatus.PASSED

    @pytest.mark.asyncio
    async def test_finalize_validation_with_issues(self):
        """Test finalizing validation with issues."""
        state = GlobalState()

        await state.finalize_validation(
            conversion_status=ConversionStatus.COMPLETED,
            validation_status=ValidationStatus.PASSED_ACCEPTED,
        )

        assert state.status == ConversionStatus.COMPLETED
        assert state.validation_status == ValidationStatus.PASSED_ACCEPTED

    @pytest.mark.asyncio
    async def test_set_validation_result(self):
        """Test setting validation result with user decision."""
        state = GlobalState()

        await state.set_validation_result(
            overall_status=ValidationOutcome.PASSED_WITH_ISSUES,
            requires_user_decision=True,
            conversation_phase=ConversationPhase.IMPROVEMENT_DECISION,
        )

        assert state.overall_status == ValidationOutcome.PASSED_WITH_ISSUES
        assert state.status == ConversionStatus.AWAITING_USER_INPUT
        assert state.conversation_phase == ConversationPhase.IMPROVEMENT_DECISION

    @pytest.mark.asyncio
    async def test_set_validation_result_no_decision(self):
        """Test setting validation result without user decision needed."""
        state = GlobalState()

        await state.set_validation_result(
            overall_status=ValidationOutcome.PASSED,
            requires_user_decision=False,
        )

        assert state.overall_status == ValidationOutcome.PASSED
        assert state.status == ConversionStatus.COMPLETED
        assert state.conversation_phase == ConversationPhase.IDLE


@pytest.mark.unit
@pytest.mark.model
class TestMetadataProvenance:
    """Tests for metadata provenance tracking."""

    def test_add_metadata_provenance(self):
        """Test adding metadata with provenance."""
        state = GlobalState()

        provenance = ProvenanceInfo(
            value="Mus musculus",
            provenance=MetadataProvenance.USER_SPECIFIED,
            confidence=100.0,
            source="User form input",
        )

        state.metadata_provenance["species"] = provenance

        assert "species" in state.metadata_provenance
        assert state.metadata_provenance["species"].value == "Mus musculus"
        assert state.metadata_provenance["species"].provenance == MetadataProvenance.USER_SPECIFIED

    def test_add_inferred_metadata_with_low_confidence(self):
        """Test tracking AI-inferred metadata with low confidence."""
        state = GlobalState()

        provenance = ProvenanceInfo(
            value="MIT",
            provenance=MetadataProvenance.AI_INFERRED,
            confidence=55.0,
            source="LLM inference from filename",
            needs_review=True,
            raw_input="mit_mouse_001.bin",
        )

        state.metadata_provenance["institution"] = provenance

        assert state.metadata_provenance["institution"].needs_review is True
        assert state.metadata_provenance["institution"].confidence == 55.0


@pytest.mark.unit
@pytest.mark.model
class TestThreadSafety:
    """Tests for thread-safe operations."""

    @pytest.mark.asyncio
    async def test_get_llm_lock_creates_lock(self):
        """Test get_llm_lock creates lock on first call."""
        state = GlobalState()

        lock = state.get_llm_lock()

        assert lock is not None
        assert isinstance(lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_get_llm_lock_reuses_lock(self):
        """Test get_llm_lock reuses same lock."""
        state = GlobalState()

        lock1 = state.get_llm_lock()
        lock2 = state.get_llm_lock()

        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_concurrent_conversation_updates(self):
        """Test concurrent conversation message additions are safe."""
        state = GlobalState()

        async def add_messages(start_idx):
            for i in range(10):
                await state.add_conversation_message_safe("user", f"Message {start_idx + i}")

        # Run multiple concurrent tasks
        await asyncio.gather(add_messages(0), add_messages(100), add_messages(200))

        # Should have all 30 messages
        assert len(state.conversation_history) == 30


@pytest.mark.unit
@pytest.mark.model
class TestMCPIntegration:
    """Tests for MCP server integration."""

    def test_set_mcp_server(self):
        """Test setting MCP server reference."""
        state = GlobalState()
        mock_mcp = Mock()

        state.set_mcp_server(mock_mcp)

        # MCP server is stored internally
        assert state._mcp_server is mock_mcp


@pytest.mark.unit
@pytest.mark.model
class TestChecksums:
    """Tests for file checksum tracking."""

    def test_add_checksum(self):
        """Test adding file checksum."""
        state = GlobalState()

        state.checksums["/test/file.nwb"] = "abc123def456"

        assert "/test/file.nwb" in state.checksums
        assert state.checksums["/test/file.nwb"] == "abc123def456"

    def test_multiple_checksums(self):
        """Test tracking multiple file checksums."""
        state = GlobalState()

        state.checksums["/test/input.bin"] = "checksum1"
        state.checksums["/test/output.nwb"] = "checksum2"

        assert len(state.checksums) == 2


@pytest.mark.unit
@pytest.mark.model
class TestDeprecatedFields:
    """Tests for backward compatibility with deprecated fields."""

    def test_deprecated_conversation_type(self):
        """Test deprecated conversation_type field."""
        state = GlobalState(conversation_type="metadata_collection")

        assert state.conversation_type == "metadata_collection"
        # New field should be used instead
        assert state.conversation_phase == ConversationPhase.IDLE

    def test_deprecated_metadata_requests_count(self):
        """Test deprecated metadata_requests_count field."""
        state = GlobalState(metadata_requests_count=2)

        assert state.metadata_requests_count == 2
        # New field should be used instead
        assert state.metadata_policy == MetadataRequestPolicy.NOT_ASKED

    def test_deprecated_user_wants_minimal(self):
        """Test deprecated user_wants_minimal field."""
        state = GlobalState(user_wants_minimal=True)

        assert state.user_wants_minimal is True
        # New field should be used instead
        assert state.metadata_policy == MetadataRequestPolicy.NOT_ASKED
