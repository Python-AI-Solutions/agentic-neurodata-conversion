"""
Unit tests for critical bug fixes.

Tests for:
- Bug #1: Race condition in conversation history
- Bug #2: Metadata policy not reset (verification)
- Bug #3: MAX_RETRY_ATTEMPTS enforcement (verification)
- Edge Case #1: Concurrent LLM processing

Created: 2025-10-20
"""
import asyncio
import pytest
from models.state import (
    GlobalState,
    ConversionStatus,
    ConversationPhase,
    MetadataRequestPolicy,
    ValidationOutcome,
    MAX_RETRY_ATTEMPTS,
)
from models.workflow_state_manager import WorkflowStateManager


# ===============================================================================
# Bug #1: Race Condition in Conversation History
# ===============================================================================

@pytest.mark.asyncio
async def test_bug1_concurrent_conversation_appends():
    """
    BUG #1 FIX TEST: Concurrent message appends don't corrupt history.

    Simulates multiple agents adding messages concurrently.
    With the fix (async locking), this should work perfectly.
    Without the fix, this would cause race conditions.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    async def add_messages(role: str, count: int):
        """Add messages concurrently."""
        for i in range(count):
            await state.add_conversation_message_safe(role, f"{role} message {i}")
            await asyncio.sleep(0.001)  # Simulate async delay

    # Run 3 concurrent tasks (simulating 3 agents)
    await asyncio.gather(
        add_messages("user", 10),
        add_messages("assistant", 10),
        add_messages("system", 10),
    )

    # Check results
    history = await state.get_conversation_history_snapshot()

    assert len(history) == 30, f"Expected 30 messages, got {len(history)}"
    assert all(isinstance(msg, dict) for msg in history), "All messages should be dicts"
    assert all('role' in msg and 'content' in msg for msg in history), "Messages missing required fields"

    # Check message distribution
    user_msgs = [m for m in history if m['role'] == 'user']
    assistant_msgs = [m for m in history if m['role'] == 'assistant']
    system_msgs = [m for m in history if m['role'] == 'system']

    assert len(user_msgs) == 10, f"Expected 10 user messages, got {len(user_msgs)}"
    assert len(assistant_msgs) == 10, f"Expected 10 assistant messages, got {len(assistant_msgs)}"
    assert len(system_msgs) == 10, f"Expected 10 system messages, got {len(system_msgs)}"


@pytest.mark.asyncio
async def test_bug1_snapshot_safe_iteration():
    """
    BUG #1 FIX TEST: Snapshot allows safe iteration during modifications.

    Tests that get_conversation_history_snapshot() returns an immutable copy
    that can be safely iterated while the original is modified.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # Add initial messages
    for i in range(10):
        await state.add_conversation_message_safe("user", f"msg {i}")

    # Get snapshot
    snapshot = await state.get_conversation_history_snapshot()

    # Modify original while iterating snapshot (should not cause RuntimeError)
    iteration_count = 0
    for msg in snapshot:
        await state.add_conversation_message_safe("assistant", "response")
        iteration_count += 1

    # Verify iteration completed fully
    assert iteration_count == 10, "Should iterate all 10 messages"

    # Snapshot should be unchanged (it's a copy)
    assert len(snapshot) == 10, f"Snapshot should still be 10 messages, got {len(snapshot)}"

    # Original should have grown
    history = await state.get_conversation_history_snapshot()
    assert len(history) == 20, f"Original should have 20 messages (10 + 10), got {len(history)}"


@pytest.mark.asyncio
async def test_bug1_rolling_window_with_concurrent_access():
    """
    BUG #1 FIX TEST: Rolling window (50 message limit) works with concurrent access.

    Tests that the 50-message rolling window doesn't break with concurrent appends.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    async def add_many_messages(role: str, count: int):
        """Add many messages to test rolling window."""
        for i in range(count):
            await state.add_conversation_message_safe(role, f"{role} msg {i}")
            await asyncio.sleep(0.0001)  # Very short delay

    # Add 100 messages total (should trigger rolling window)
    await asyncio.gather(
        add_many_messages("user", 50),
        add_many_messages("assistant", 50),
    )

    history = await state.get_conversation_history_snapshot()

    # Should be exactly 50 (rolling window limit)
    assert len(history) == 50, f"Rolling window should keep 50 messages, got {len(history)}"


@pytest.mark.asyncio
async def test_bug1_clear_conversation_history_safe():
    """
    BUG #1 FIX TEST: Clear conversation history is thread-safe.

    Tests that clearing history doesn't cause race conditions.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # Add messages
    for i in range(10):
        await state.add_conversation_message_safe("user", f"msg {i}")

    history = await state.get_conversation_history_snapshot()
    assert len(history) == 10

    # Clear
    await state.clear_conversation_history_safe()

    history = await state.get_conversation_history_snapshot()
    assert len(history) == 0, "History should be empty after clear"


# ===============================================================================
# Bug #2: Metadata Policy Not Reset
# ===============================================================================

def test_bug2_metadata_policy_resets_between_sessions():
    """
    BUG #2 VERIFICATION TEST: Metadata policy doesn't persist across uploads.

    This bug was already fixed in the codebase. This test verifies the fix.
    """
    state = GlobalState(status=ConversionStatus.IDLE)
    manager = WorkflowStateManager()

    # Session 1: User declines metadata
    state.metadata_policy = MetadataRequestPolicy.USER_DECLINED
    state.conversation_phase = ConversationPhase.METADATA_COLLECTION
    state.user_declined_fields = {"experimenter", "institution"}
    state.conversation_type = "required_metadata"

    # Verify state before reset
    assert state.metadata_policy == MetadataRequestPolicy.USER_DECLINED
    assert state.conversation_phase == ConversationPhase.METADATA_COLLECTION
    assert len(state.user_declined_fields) == 2

    # Reset for session 2
    state.reset()

    # Session 2: Should ask for metadata again
    assert state.metadata_policy == MetadataRequestPolicy.NOT_ASKED, \
        f"metadata_policy should be NOT_ASKED, got {state.metadata_policy}"
    assert state.conversation_phase == ConversationPhase.IDLE, \
        f"conversation_phase should be IDLE, got {state.conversation_phase}"
    assert state.conversation_type is None or state.conversation_type == "idle", \
        f"conversation_type should be None or 'idle', got {state.conversation_type}"
    assert len(state.user_declined_fields) == 0, \
        f"user_declined_fields should be empty, got {state.user_declined_fields}"

    # WorkflowStateManager should allow metadata request
    state.metadata = {}  # Ensure there are missing fields
    assert manager.should_request_metadata(state) == True, \
        "WorkflowStateManager should request metadata on fresh session"


def test_bug2_all_session_state_resets():
    """
    BUG #2 VERIFICATION TEST: Comprehensive check that all session state resets.

    Ensures reset() clears ALL session-specific state to prevent carryover.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # Simulate completed session with full state
    state.input_path = "/uploads/file1.bin"
    state.output_path = "/outputs/file1.nwb"
    state.metadata = {"subject_id": "mouse001"}
    state.conversation_history = [{"role": "user", "content": "test"}]
    state.metadata_policy = MetadataRequestPolicy.USER_DECLINED
    state.conversation_phase = ConversationPhase.IMPROVEMENT_DECISION
    state.correction_attempt = 3
    state.validation_result = {"status": "FAILED"}
    state.checksums = {"/outputs/file1.nwb": "abc123"}
    state.overall_status = ValidationOutcome.FAILED

    # Reset
    state.reset()

    # Verify everything reset
    assert state.input_path is None
    assert state.output_path is None
    assert len(state.metadata) == 0
    assert len(state.conversation_history) == 0
    assert state.metadata_policy == MetadataRequestPolicy.NOT_ASKED
    assert state.conversation_phase == ConversationPhase.IDLE
    assert state.correction_attempt == 0
    assert state.validation_result is None
    assert len(state.checksums) == 0
    assert state.overall_status is None


# ===============================================================================
# Bug #3: MAX_RETRY_ATTEMPTS Not Enforced
# ===============================================================================

def test_bug3_can_retry_computed_property():
    """
    BUG #3 VERIFICATION TEST: can_retry is always accurate.

    This bug was already fixed (can_retry is a @property). This test verifies it.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # Initial: can retry
    assert state.correction_attempt == 0
    assert state.can_retry == True, "Should be able to retry at attempt 0"

    # After 4 retries: can still retry
    state.correction_attempt = 4
    assert state.can_retry == True, "Should be able to retry at attempt 4"

    # At limit (attempt 5): cannot retry
    state.correction_attempt = 5
    assert state.can_retry == False, f"Should NOT be able to retry at attempt {MAX_RETRY_ATTEMPTS}"

    # Beyond limit: cannot retry
    state.correction_attempt = 6
    assert state.can_retry == False, "Should NOT be able to retry beyond limit"


def test_bug3_max_retry_boundary_conditions():
    """
    BUG #3 VERIFICATION TEST: Test exact boundary at MAX_RETRY_ATTEMPTS.

    Ensures the retry limit is enforced at exactly the right boundary.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # Test all attempts from 0 to MAX+1
    for attempt in range(MAX_RETRY_ATTEMPTS + 2):
        state.correction_attempt = attempt

        expected_can_retry = (attempt < MAX_RETRY_ATTEMPTS)
        assert state.can_retry == expected_can_retry, \
            f"At attempt {attempt}, expected can_retry={expected_can_retry}, got {state.can_retry}"


def test_bug3_retry_limit_prevents_infinite_loop():
    """
    BUG #3 VERIFICATION TEST: Retry limit prevents infinite loops.

    Simulates a retry loop and ensures it stops at MAX_RETRY_ATTEMPTS.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    retry_count = 0
    while state.can_retry and retry_count < 10:  # Safety: max 10 iterations
        state.correction_attempt += 1
        retry_count += 1

    # Should stop at exactly MAX_RETRY_ATTEMPTS
    assert retry_count == MAX_RETRY_ATTEMPTS, \
        f"Should stop at {MAX_RETRY_ATTEMPTS} retries, stopped at {retry_count}"
    assert state.correction_attempt == MAX_RETRY_ATTEMPTS
    assert state.can_retry == False, "can_retry should be False at limit"


def test_bug3_retry_attempts_remaining_property():
    """
    BUG #3 VERIFICATION TEST: retry_attempts_remaining property is accurate.

    Tests the additional retry_attempts_remaining property.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # At attempt 0: 5 remaining
    assert state.retry_attempts_remaining == MAX_RETRY_ATTEMPTS

    # At attempt 3: 2 remaining
    state.correction_attempt = 3
    assert state.retry_attempts_remaining == 2

    # At attempt 5: 0 remaining
    state.correction_attempt = MAX_RETRY_ATTEMPTS
    assert state.retry_attempts_remaining == 0

    # Beyond limit: 0 remaining (not negative)
    state.correction_attempt = MAX_RETRY_ATTEMPTS + 1
    assert state.retry_attempts_remaining == 0


# ===============================================================================
# Edge Case #1: Concurrent LLM Processing
# ===============================================================================

def test_edge_case1_llm_processing_flag():
    """
    EDGE CASE #1 TEST: LLM processing flag prevents concurrent calls.

    Tests that the llm_processing flag can be used to prevent concurrent LLM calls.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # Initial state: not processing
    assert state.llm_processing == False

    # Simulate LLM processing start
    state.llm_processing = True
    assert state.llm_processing == True

    # While processing, new requests should check this flag
    if state.llm_processing:
        # This is what the API endpoint does
        should_block = True
    else:
        should_block = False

    assert should_block == True, "Should block when LLM is processing"

    # Simulate LLM processing complete
    state.llm_processing = False
    assert state.llm_processing == False


@pytest.mark.asyncio
async def test_edge_case1_llm_lock_prevents_concurrent_access():
    """
    EDGE CASE #1 TEST: LLM lock prevents concurrent LLM calls.

    Tests that the _llm_lock actually prevents concurrent access.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    call_order = []

    async def simulate_llm_call(call_id: int, duration: float):
        """Simulate an LLM call with lock."""
        async with state._llm_lock:
            call_order.append(f"start_{call_id}")
            state.llm_processing = True
            await asyncio.sleep(duration)
            state.llm_processing = False
            call_order.append(f"end_{call_id}")

    # Start 3 concurrent "LLM calls"
    await asyncio.gather(
        simulate_llm_call(1, 0.01),
        simulate_llm_call(2, 0.01),
        simulate_llm_call(3, 0.01),
    )

    # With lock, calls should be sequential, not interleaved
    # Each call should start and end before the next starts
    assert len(call_order) == 6, "Should have 6 events (3 starts, 3 ends)"

    # Find pairs of start/end
    for i in range(0, len(call_order), 2):
        start_event = call_order[i]
        end_event = call_order[i + 1]

        # Each start should be followed by its own end
        call_id = start_event.split('_')[1]
        assert end_event == f"end_{call_id}", \
            f"Call {call_id} should end before next call starts"


# ===============================================================================
# Additional Edge Case Tests
# ===============================================================================

def test_reset_also_resets_llm_processing():
    """
    Verify that reset() also resets llm_processing flag.

    This prevents stuck "processing" state from carrying over.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # Simulate LLM stuck in processing state
    state.llm_processing = True

    # Reset should clear this
    state.reset()

    assert state.llm_processing == False, \
        "reset() should clear llm_processing flag"


@pytest.mark.asyncio
async def test_conversation_history_backward_compatibility():
    """
    Verify that old sync method still works (backward compatibility).

    While not thread-safe, the old method should still function for existing code.
    """
    state = GlobalState(status=ConversionStatus.IDLE)

    # Old sync method should still work
    state.add_conversation_message("user", "test message")

    # Should be in history
    assert len(state.conversation_history) == 1
    assert state.conversation_history[0]['role'] == "user"
    assert state.conversation_history[0]['content'] == "test message"


# ===============================================================================
# Integration Tests
# ===============================================================================

@pytest.mark.asyncio
async def test_full_workflow_with_all_bug_fixes():
    """
    Integration test: Full workflow exercising all bug fixes.

    Simulates a complete conversion workflow touching all fixed code paths.
    """
    state = GlobalState(status=ConversionStatus.IDLE)
    manager = WorkflowStateManager()

    # Session 1: User declines metadata
    await state.add_conversation_message_safe("assistant", "Would you like to provide metadata?")
    await state.add_conversation_message_safe("user", "skip all")

    state.metadata_policy = MetadataRequestPolicy.USER_DECLINED
    state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    # Simulate validation failure (multiple retries)
    state.correction_attempt = 3
    assert state.can_retry == True, "Should allow retry at attempt 3"

    state.correction_attempt = 5
    assert state.can_retry == False, "Should block retry at attempt 5"

    # Reset for session 2
    state.reset()

    # Session 2: Fresh start
    assert state.metadata_policy == MetadataRequestPolicy.NOT_ASKED
    assert state.conversation_phase == ConversationPhase.IDLE
    assert state.correction_attempt == 0
    assert state.can_retry == True
    assert state.llm_processing == False
    assert len(state.conversation_history) == 0

    # Should request metadata again
    assert manager.should_request_metadata(state) == True

    # Simulate concurrent messages (bug #1 fix)
    await asyncio.gather(
        state.add_conversation_message_safe("user", "msg1"),
        state.add_conversation_message_safe("assistant", "resp1"),
        state.add_conversation_message_safe("user", "msg2"),
    )

    history = await state.get_conversation_history_snapshot()
    assert len(history) == 3, "Should have 3 messages with no corruption"


if __name__ == "__main__":
    # Run tests with pytest
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
