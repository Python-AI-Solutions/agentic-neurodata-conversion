"""
Unit tests for WorkflowStateManager.

Tests centralized workflow state logic including:
- Metadata request decisions
- Upload/conversion state checks
- Active conversation detection
- Metadata policy transitions
"""
import pytest
from models.state import (
    GlobalState,
    ConversionStatus,
    ValidationOutcome,
    ConversationPhase,
    MetadataRequestPolicy,
)
from models.workflow_state_manager import WorkflowStateManager


@pytest.mark.unit
class TestWorkflowStateManager:
    """Test suite for WorkflowStateManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create WorkflowStateManager instance."""
        return WorkflowStateManager()

    @pytest.fixture
    def fresh_state(self):
        """Create fresh GlobalState instance."""
        return GlobalState()

    # =========================================================================
    # Metadata Request Logic Tests
    # =========================================================================

    def test_should_request_metadata_fresh_state(self, manager, fresh_state):
        """Test metadata request on fresh state with missing fields."""
        # Fresh state should request metadata
        assert manager.should_request_metadata(fresh_state) is True

    def test_should_request_metadata_already_asked(self, manager, fresh_state):
        """Test that metadata is not requested twice."""
        # Simulate having already asked
        manager.update_metadata_policy_after_request(fresh_state)

        # Should not request again
        assert manager.should_request_metadata(fresh_state) is False
        assert fresh_state.metadata_policy == MetadataRequestPolicy.ASKED_ONCE

    def test_should_request_metadata_user_provided(self, manager, fresh_state):
        """Test that metadata is not requested after user provided it."""
        # Simulate user providing metadata
        manager.update_metadata_policy_after_user_provided(fresh_state)

        # Should not request
        assert manager.should_request_metadata(fresh_state) is False
        assert fresh_state.metadata_policy == MetadataRequestPolicy.USER_PROVIDED

    def test_should_request_metadata_user_declined(self, manager, fresh_state):
        """Test that metadata is not requested after user declined."""
        # Simulate user declining
        manager.update_metadata_policy_after_user_declined(fresh_state)

        # Should not request
        assert manager.should_request_metadata(fresh_state) is False
        assert fresh_state.metadata_policy == MetadataRequestPolicy.USER_DECLINED

    def test_should_request_metadata_in_active_conversation(self, manager, fresh_state):
        """Test that metadata is not requested during active conversation."""
        # Simulate active metadata conversation - first need to have requested it
        manager.update_metadata_policy_after_request(fresh_state)

        fresh_state.conversation_phase = ConversationPhase.METADATA_COLLECTION
        fresh_state.conversation_type = fresh_state.conversation_phase.value
        fresh_state.status = ConversionStatus.AWAITING_USER_INPUT
        fresh_state.add_conversation_message(role="assistant", content="Please provide metadata")
        fresh_state.add_conversation_message(role="user", content="Here it is")

        # Should not request (conversation in progress)
        assert manager.should_request_metadata(fresh_state) is False

    def test_should_request_metadata_all_fields_present(self, manager, fresh_state):
        """Test that metadata is not requested when all required fields present."""
        # Provide all required DANDI fields
        fresh_state.metadata.update({
            'experimenter': 'Dr. Smith',
            'institution': 'MIT',
            'experiment_description': 'Visual cortex recording',
            'session_start_time': '2024-01-15T10:30:00',
            'subject_id': 'mouse001',
            'species': 'Mus musculus',
            'sex': 'M',
        })

        # Should not request (all fields present)
        assert manager.should_request_metadata(fresh_state) is False

    # =========================================================================
    # Upload State Tests
    # =========================================================================

    def test_can_accept_upload_idle_state(self, manager, fresh_state):
        """Test upload allowed in IDLE state."""
        assert fresh_state.status == ConversionStatus.IDLE
        assert manager.can_accept_upload(fresh_state) is True

    def test_can_accept_upload_completed_state(self, manager, fresh_state):
        """Test upload allowed after completion (reset scenario)."""
        fresh_state.status = ConversionStatus.COMPLETED
        assert manager.can_accept_upload(fresh_state) is True

    def test_can_accept_upload_blocked_during_conversion(self, manager, fresh_state):
        """Test upload blocked during active conversion."""
        blocking_statuses = [
            ConversionStatus.UPLOADING,
            ConversionStatus.DETECTING_FORMAT,
            ConversionStatus.CONVERTING,
            ConversionStatus.VALIDATING,
        ]

        for status in blocking_statuses:
            fresh_state.status = status
            assert manager.can_accept_upload(fresh_state) is False, \
                f"Upload should be blocked during {status}"

    def test_can_accept_upload_awaiting_user_input(self, manager, fresh_state):
        """Test upload allowed when awaiting user input (user can restart)."""
        fresh_state.status = ConversionStatus.AWAITING_USER_INPUT
        assert manager.can_accept_upload(fresh_state) is True

    # =========================================================================
    # Conversion Start Tests
    # =========================================================================

    def test_can_start_conversion_with_input_path(self, manager, fresh_state):
        """Test conversion can start with valid input path."""
        fresh_state.input_path = "/path/to/data.bin"
        fresh_state.status = ConversionStatus.IDLE

        assert manager.can_start_conversion(fresh_state) is True

    def test_can_start_conversion_no_input_path(self, manager, fresh_state):
        """Test conversion cannot start without input path."""
        fresh_state.input_path = None

        assert manager.can_start_conversion(fresh_state) is False

    def test_can_start_conversion_blocked_during_conversion(self, manager, fresh_state):
        """Test conversion blocked when already in progress."""
        fresh_state.input_path = "/path/to/data.bin"

        blocking_statuses = [
            ConversionStatus.DETECTING_FORMAT,
            ConversionStatus.CONVERTING,
            ConversionStatus.VALIDATING,
        ]

        for status in blocking_statuses:
            fresh_state.status = status
            assert manager.can_start_conversion(fresh_state) is False, \
                f"Conversion should be blocked during {status}"

    def test_can_start_conversion_from_completed(self, manager, fresh_state):
        """Test conversion can restart from completed state."""
        fresh_state.input_path = "/path/to/data.bin"
        fresh_state.status = ConversionStatus.COMPLETED

        assert manager.can_start_conversion(fresh_state) is True

    # =========================================================================
    # Active Conversation Tests
    # =========================================================================

    def test_is_in_active_conversation_awaiting_input_with_history(self, manager, fresh_state):
        """Test active conversation detected with history."""
        fresh_state.status = ConversionStatus.AWAITING_USER_INPUT
        fresh_state.add_conversation_message(role="assistant", content="Please provide info")

        assert manager.is_in_active_conversation(fresh_state) is True

    def test_is_in_active_conversation_metadata_collection(self, manager, fresh_state):
        """Test active conversation during metadata collection."""
        fresh_state.status = ConversionStatus.AWAITING_USER_INPUT
        fresh_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

        assert manager.is_in_active_conversation(fresh_state) is True

    def test_is_in_active_conversation_idle_state(self, manager, fresh_state):
        """Test no active conversation in idle state."""
        assert fresh_state.status == ConversionStatus.IDLE
        assert manager.is_in_active_conversation(fresh_state) is False

    def test_is_in_active_conversation_converting_state(self, manager, fresh_state):
        """Test no active conversation during conversion."""
        fresh_state.status = ConversionStatus.CONVERTING
        assert manager.is_in_active_conversation(fresh_state) is False

    # =========================================================================
    # Metadata Policy Transition Tests
    # =========================================================================

    def test_metadata_policy_lifecycle_requested(self, manager, fresh_state):
        """Test metadata policy transitions after request."""
        # Initial state
        assert fresh_state.metadata_policy == MetadataRequestPolicy.NOT_ASKED

        # After requesting
        manager.update_metadata_policy_after_request(fresh_state)
        assert fresh_state.metadata_policy == MetadataRequestPolicy.ASKED_ONCE

        # Backward compatibility - counter should increment
        assert fresh_state.metadata_requests_count == 1

    def test_metadata_policy_lifecycle_provided(self, manager, fresh_state):
        """Test metadata policy after user provides data."""
        # Request, then user provides
        manager.update_metadata_policy_after_request(fresh_state)
        manager.update_metadata_policy_after_user_provided(fresh_state)

        assert fresh_state.metadata_policy == MetadataRequestPolicy.USER_PROVIDED

    def test_metadata_policy_lifecycle_declined(self, manager, fresh_state):
        """Test metadata policy after user declines."""
        # Request, then user declines
        manager.update_metadata_policy_after_request(fresh_state)
        manager.update_metadata_policy_after_user_declined(fresh_state)

        assert fresh_state.metadata_policy == MetadataRequestPolicy.USER_DECLINED

        # Backward compatibility - user_wants_minimal should be True
        assert fresh_state.user_wants_minimal is True

    def test_metadata_policy_proceeding_minimal(self, manager, fresh_state):
        """Test metadata policy for minimal conversion."""
        # Request, user declines, system proceeds with minimal
        manager.update_metadata_policy_after_request(fresh_state)
        manager.update_metadata_policy_after_user_declined(fresh_state)

        # This should transition to PROCEEDING_MINIMAL when conversion starts
        assert fresh_state.metadata_policy == MetadataRequestPolicy.USER_DECLINED

    # =========================================================================
    # Edge Case Tests
    # =========================================================================

    def test_multiple_metadata_requests_blocked(self, manager, fresh_state):
        """Test that metadata cannot be requested multiple times."""
        # First request
        assert manager.should_request_metadata(fresh_state) is True
        manager.update_metadata_policy_after_request(fresh_state)

        # Second attempt should be blocked
        assert manager.should_request_metadata(fresh_state) is False

        # Even after resetting some fields
        fresh_state.conversation_history = []
        assert manager.should_request_metadata(fresh_state) is False

    def test_state_reset_clears_metadata_policy(self, manager):
        """Test that state reset clears metadata policy."""
        state = GlobalState()

        # Set some policy
        manager.update_metadata_policy_after_request(state)
        assert state.metadata_policy == MetadataRequestPolicy.ASKED_ONCE

        # Reset
        state.reset()

        # Should be back to NOT_ASKED
        assert state.metadata_policy == MetadataRequestPolicy.NOT_ASKED

    def test_concurrent_upload_blocked(self, manager, fresh_state):
        """Test that concurrent uploads are blocked."""
        # Start upload
        fresh_state.status = ConversionStatus.UPLOADING
        fresh_state.input_path = "/path/to/first.bin"

        # Try second upload
        assert manager.can_accept_upload(fresh_state) is False

    def test_conversion_blocked_during_validation(self, manager, fresh_state):
        """Test conversion blocked during validation."""
        fresh_state.input_path = "/path/to/data.bin"
        fresh_state.status = ConversionStatus.VALIDATING

        assert manager.can_start_conversion(fresh_state) is False

    # =========================================================================
    # Integration Tests
    # =========================================================================

    def test_full_workflow_happy_path(self, manager):
        """Test full workflow from upload to completion."""
        state = GlobalState()

        # 1. Initial state - can accept upload
        assert manager.can_accept_upload(state) is True

        # 2. Upload file
        state.input_path = "/path/to/data.bin"
        state.status = ConversionStatus.IDLE

        # 3. Check if metadata needed
        assert manager.should_request_metadata(state) is True

        # 4. Request metadata
        manager.update_metadata_policy_after_request(state)
        state.conversation_phase = ConversationPhase.METADATA_COLLECTION
        state.status = ConversionStatus.AWAITING_USER_INPUT

        # 5. User is in active conversation
        assert manager.is_in_active_conversation(state) is True

        # 6. User provides metadata
        state.metadata['experimenter'] = 'Dr. Smith'
        manager.update_metadata_policy_after_user_provided(state)

        # 7. Can start conversion
        state.status = ConversionStatus.IDLE
        assert manager.can_start_conversion(state) is True

        # 8. Start conversion
        state.status = ConversionStatus.CONVERTING

        # 9. Cannot accept new uploads during conversion
        assert manager.can_accept_upload(state) is False

        # 10. Complete
        state.status = ConversionStatus.COMPLETED

        # 11. Can accept new uploads after completion
        assert manager.can_accept_upload(state) is True

    def test_full_workflow_user_declines_metadata(self, manager):
        """Test workflow when user declines metadata."""
        state = GlobalState()

        # 1. Upload file
        state.input_path = "/path/to/data.bin"
        state.status = ConversionStatus.IDLE

        # 2. Check if metadata needed
        assert manager.should_request_metadata(state) is True

        # 3. Request metadata
        manager.update_metadata_policy_after_request(state)

        # 4. User declines
        manager.update_metadata_policy_after_user_declined(state)

        # 5. Should not request again
        assert manager.should_request_metadata(state) is False

        # 6. Can still start conversion with minimal metadata
        assert manager.can_start_conversion(state) is True

    # =========================================================================
    # Backward Compatibility Tests
    # =========================================================================

    def test_backward_compatibility_user_wants_minimal(self, manager, fresh_state):
        """Test that user_wants_minimal syncs with metadata_policy."""
        # Initially False
        assert fresh_state.user_wants_minimal is False

        # Decline metadata
        manager.update_metadata_policy_after_user_declined(fresh_state)

        # Should be True now
        assert fresh_state.user_wants_minimal is True

    def test_backward_compatibility_metadata_requests_count(self, manager, fresh_state):
        """Test that metadata_requests_count syncs with policy."""
        # Initially 0
        assert fresh_state.metadata_requests_count == 0

        # Request metadata
        manager.update_metadata_policy_after_request(fresh_state)

        # Should be 1 now
        assert fresh_state.metadata_requests_count == 1
