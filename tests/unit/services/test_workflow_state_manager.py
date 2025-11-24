"""
Unit tests for WorkflowStateManager.

Tests centralized workflow state logic including:
- Metadata request decisions
- Upload/conversion state checks
- Active conversation detection
- Metadata policy transitions
"""

import pytest

from agentic_neurodata_conversion.models.state import (
    ConversationPhase,
    ConversionStatus,
    GlobalState,
    MetadataRequestPolicy,
)
from agentic_neurodata_conversion.models.workflow_state_manager import WorkflowStateManager


@pytest.mark.unit
@pytest.mark.service
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
        fresh_state.metadata.update(
            {
                "experimenter": "Dr. Smith",
                "institution": "MIT",
                "experiment_description": "Visual cortex recording",
                "session_start_time": "2024-01-15T10:30:00",
                "subject_id": "mouse001",
                "species": "Mus musculus",
                "sex": "M",
            }
        )

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
            assert manager.can_accept_upload(fresh_state) is False, f"Upload should be blocked during {status}"

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
            assert manager.can_start_conversion(fresh_state) is False, f"Conversion should be blocked during {status}"

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
        state.metadata["experimenter"] = "Dr. Smith"
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

    # =========================================================================
    # should_proceed_with_minimal_metadata Tests (lines 112-129)
    # =========================================================================

    def test_should_proceed_with_minimal_user_declined(self, manager, fresh_state):
        """Test proceed with minimal when user declined (line 126)."""
        manager.update_metadata_policy_after_user_declined(fresh_state)

        assert manager.should_proceed_with_minimal_metadata(fresh_state) is True
        assert fresh_state.metadata_policy == MetadataRequestPolicy.USER_DECLINED

    def test_should_proceed_with_minimal_proceeding_minimal(self, manager, fresh_state):
        """Test proceed with minimal when policy is PROCEEDING_MINIMAL (line 127)."""
        fresh_state.metadata_policy = MetadataRequestPolicy.PROCEEDING_MINIMAL

        assert manager.should_proceed_with_minimal_metadata(fresh_state) is True

    def test_should_proceed_with_minimal_asked_once(self, manager, fresh_state):
        """Test proceed with minimal when asked once (line 128)."""
        manager.update_metadata_policy_after_request(fresh_state)

        assert manager.should_proceed_with_minimal_metadata(fresh_state) is True
        assert fresh_state.metadata_policy == MetadataRequestPolicy.ASKED_ONCE

    def test_should_proceed_with_minimal_not_asked(self, manager, fresh_state):
        """Test do not proceed with minimal when not asked yet."""
        assert fresh_state.metadata_policy == MetadataRequestPolicy.NOT_ASKED

        assert manager.should_proceed_with_minimal_metadata(fresh_state) is False

    def test_should_proceed_with_minimal_user_provided(self, manager, fresh_state):
        """Test do not proceed with minimal when user provided metadata."""
        manager.update_metadata_policy_after_user_provided(fresh_state)

        assert manager.should_proceed_with_minimal_metadata(fresh_state) is False
        assert fresh_state.metadata_policy == MetadataRequestPolicy.USER_PROVIDED

    # =========================================================================
    # get_missing_required_fields Tests (lines 131-146)
    # =========================================================================

    def test_get_missing_required_fields_all_missing(self, manager, fresh_state):
        """Test getting all missing fields when none provided."""
        missing = manager.get_missing_required_fields(fresh_state)

        # All 7 DANDI fields should be missing
        assert len(missing) == 7
        assert "experimenter" in missing
        assert "institution" in missing
        assert "experiment_description" in missing
        assert "session_start_time" in missing
        assert "subject_id" in missing
        assert "species" in missing
        assert "sex" in missing

    def test_get_missing_required_fields_some_provided(self, manager, fresh_state):
        """Test getting missing fields when some provided."""
        fresh_state.metadata["experimenter"] = "Dr. Smith"
        fresh_state.metadata["institution"] = "MIT"

        missing = manager.get_missing_required_fields(fresh_state)

        assert len(missing) == 5
        assert "experimenter" not in missing
        assert "institution" not in missing
        assert "experiment_description" in missing

    def test_get_missing_required_fields_all_provided(self, manager, fresh_state):
        """Test no missing fields when all provided."""
        fresh_state.metadata.update(
            {
                "experimenter": "Dr. Smith",
                "institution": "MIT",
                "experiment_description": "Test",
                "session_start_time": "2024-01-01T00:00:00",
                "subject_id": "subj001",
                "species": "Mus musculus",
                "sex": "M",
            }
        )

        missing = manager.get_missing_required_fields(fresh_state)

        assert len(missing) == 0

    def test_get_missing_required_fields_with_declined_fields(self, manager, fresh_state):
        """Test missing fields excludes user-declined fields (lines 144-145)."""
        # User declined some fields
        fresh_state.user_declined_fields.add("experimenter")
        fresh_state.user_declined_fields.add("institution")

        missing = manager.get_missing_required_fields(fresh_state)

        # Should not include declined fields
        assert "experimenter" not in missing
        assert "institution" not in missing
        # Should still include others
        assert "experiment_description" in missing
        assert len(missing) == 5

    def test_get_missing_required_fields_empty_string_not_valid(self, manager, fresh_state):
        """Test that empty string values are treated as missing (line 142)."""
        fresh_state.metadata["experimenter"] = ""
        fresh_state.metadata["institution"] = "   "  # Whitespace is treated as valid by implementation

        missing = manager.get_missing_required_fields(fresh_state)

        # Empty string is treated as missing, whitespace is not (truthy check)
        assert "experimenter" in missing
        assert "institution" not in missing  # Whitespace string is truthy, so not missing

    def test_get_missing_required_fields_none_value(self, manager, fresh_state):
        """Test that None values are treated as missing (line 142)."""
        fresh_state.metadata["experimenter"] = None

        missing = manager.get_missing_required_fields(fresh_state)

        assert "experimenter" in missing

    # =========================================================================
    # _recently_had_user_response Tests (lines 173-183)
    # =========================================================================

    def test_recently_had_user_response_empty_history(self, manager, fresh_state):
        """Test no recent response when history is empty (line 178)."""
        assert len(fresh_state.conversation_history) == 0

        assert manager._recently_had_user_response(fresh_state) is False

    def test_recently_had_user_response_last_message_user(self, manager, fresh_state):
        """Test recent response when last message is from user (lines 181-183)."""
        fresh_state.add_conversation_message(role="assistant", content="Question?")
        fresh_state.add_conversation_message(role="user", content="Answer")

        assert manager._recently_had_user_response(fresh_state) is True

    def test_recently_had_user_response_second_to_last_user(self, manager, fresh_state):
        """Test recent response checks last 2 messages (lines 182-183)."""
        fresh_state.add_conversation_message(role="user", content="First message")
        fresh_state.add_conversation_message(role="assistant", content="Response")

        assert manager._recently_had_user_response(fresh_state) is True

    def test_recently_had_user_response_no_user_messages(self, manager, fresh_state):
        """Test no recent response when no user messages (line 183)."""
        fresh_state.add_conversation_message(role="assistant", content="Message 1")
        fresh_state.add_conversation_message(role="assistant", content="Message 2")

        assert manager._recently_had_user_response(fresh_state) is False

    def test_recently_had_user_response_only_checks_last_two(self, manager, fresh_state):
        """Test only checks last 2 messages, not entire history (line 182)."""
        # User message far back in history
        fresh_state.add_conversation_message(role="user", content="Old message")
        fresh_state.add_conversation_message(role="assistant", content="Response 1")
        fresh_state.add_conversation_message(role="assistant", content="Response 2")
        fresh_state.add_conversation_message(role="assistant", content="Response 3")

        # Last 2 are both assistant, so should be False
        assert manager._recently_had_user_response(fresh_state) is False

    def test_recently_had_user_response_single_user_message(self, manager, fresh_state):
        """Test recent response with only one message in history (line 178-183)."""
        fresh_state.add_conversation_message(role="user", content="Hello")

        assert manager._recently_had_user_response(fresh_state) is True

    # =========================================================================
    # format_missing_fields_message Tests (lines 214-241)
    # =========================================================================

    def test_format_missing_fields_message_empty_list(self, manager):
        """Test formatting with no missing fields (lines 223-224)."""
        result = manager.format_missing_fields_message([])

        assert result == ""

    def test_format_missing_fields_message_single_field(self, manager):
        """Test formatting with single missing field (lines 226-241)."""
        result = manager.format_missing_fields_message(["experimenter"])

        assert "Could you provide:" in result
        assert "experimenter name(s)" in result

    def test_format_missing_fields_message_all_fields(self, manager):
        """Test formatting with all DANDI fields missing (lines 226-241)."""
        all_fields = [
            "experimenter",
            "institution",
            "experiment_description",
            "session_start_time",
            "subject_id",
            "species",
            "sex",
        ]

        result = manager.format_missing_fields_message(all_fields)

        assert "Could you provide:" in result
        assert "experimenter name(s)" in result
        assert "institution name" in result
        assert "experiment description" in result
        assert "session start time" in result
        assert "subject ID" in result
        assert "species (e.g., Mus musculus for mouse)" in result
        assert "subject's sex (M/F/U)" in result

    def test_format_missing_fields_message_uses_descriptions(self, manager):
        """Test that formatted message uses friendly descriptions (lines 226-234)."""
        result = manager.format_missing_fields_message(["species", "sex"])

        # Should use descriptions, not raw field names
        assert "species (e.g., Mus musculus for mouse)" in result
        assert "subject's sex (M/F/U)" in result
        # Should not contain raw field names without description
        assert result.count("species") == 1  # Only in the description
        assert result.count("sex") == 1  # Only in the description

    def test_format_missing_fields_message_unknown_field(self, manager):
        """Test formatting with unknown field falls back to field name (lines 238-239)."""
        result = manager.format_missing_fields_message(["unknown_field"])

        assert "Could you provide:" in result
        assert "unknown_field" in result

    def test_format_missing_fields_message_mixed_known_unknown(self, manager):
        """Test formatting with mix of known and unknown fields."""
        result = manager.format_missing_fields_message(["experimenter", "custom_field", "species"])

        assert "experimenter name(s)" in result
        assert "custom_field" in result
        assert "species (e.g., Mus musculus for mouse)" in result

    def test_format_missing_fields_message_formatting(self, manager):
        """Test message formatting structure (lines 236-241)."""
        result = manager.format_missing_fields_message(["experimenter", "institution"])

        # Should have header
        assert result.startswith("Could you provide:")
        # Should have bullet points
        assert "  - " in result
        # Should be on separate lines
        lines = result.split("\n")
        assert len(lines) >= 3  # Header + 2 fields
