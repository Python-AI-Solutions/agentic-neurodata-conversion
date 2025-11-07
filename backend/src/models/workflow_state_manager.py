"""
Workflow State Manager - Centralized state transition logic.

WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Consolidate state transition logic
(Recommendation 6.1, Breaking Point #1)

This module provides a single source of truth for all state transition decisions,
eliminating the distributed logic problem identified in the analysis.
"""

from .state import ConversationPhase, ConversionStatus, GlobalState, MetadataRequestPolicy


class WorkflowStateManager:
    """
    Centralized state transition logic for the conversion workflow.

    This class consolidates all state check logic that was previously scattered
    across conversation_agent.py, conversational_handler.py, and main.py.
    """

    # Required DANDI metadata fields
    REQUIRED_DANDI_FIELDS = [
        "experimenter",
        "institution",
        "experiment_description",
        "session_start_time",
        "subject_id",
        "species",
        "sex",
    ]

    def __init__(self):
        """Initialize the workflow state manager."""
        pass

    def should_request_metadata(self, state: GlobalState) -> bool:
        """
        Single method to decide if metadata request is needed.

        Replaces complex multi-file logic with single source of truth.

        Previous locations:
        - conversation_agent.py:430 (4 conditions)
        - conversational_handler.py:106 (2 conditions)

        Args:
            state: Current global state

        Returns:
            True if metadata should be requested, False otherwise
        """
        return (
            self._has_missing_required_fields(state)
            and self._not_already_asked(state)
            and not self._user_declined_metadata(state)
            and not self._in_active_metadata_conversation(state)
        )

    def can_accept_upload(self, state: GlobalState) -> bool:
        """
        Check if file upload is allowed in current state.

        Replaces: main.py:226-237

        Args:
            state: Current global state

        Returns:
            True if upload allowed, False otherwise
        """
        blocking_statuses = {
            ConversionStatus.UPLOADING,
            ConversionStatus.DETECTING_FORMAT,
            ConversionStatus.CONVERTING,
            ConversionStatus.VALIDATING,
        }
        return state.status not in blocking_statuses

    def can_start_conversion(self, state: GlobalState) -> bool:
        """
        Check if conversion can be started.

        Replaces: main.py:541-551

        Args:
            state: Current global state

        Returns:
            True if conversion can start, False otherwise
        """
        if not state.input_path:
            return False

        blocking_statuses = {
            ConversionStatus.DETECTING_FORMAT,
            ConversionStatus.CONVERTING,
            ConversionStatus.VALIDATING,
        }
        return state.status not in blocking_statuses

    def is_in_active_conversation(self, state: GlobalState) -> bool:
        """
        Check if user is in an active conversation.

        Replaces: main.py:304-308

        Args:
            state: Current global state

        Returns:
            True if active conversation, False otherwise
        """
        return state.status == ConversionStatus.AWAITING_USER_INPUT and (
            len(state.conversation_history) > 0 or state.conversation_phase == ConversationPhase.METADATA_COLLECTION
        )

    def should_proceed_with_minimal_metadata(self, state: GlobalState) -> bool:
        """
        Check if should proceed with minimal metadata (user declined).

        Replaces logic in:
        - conversational_handler.py:106
        - conversation_agent.py:1477

        Args:
            state: Current global state

        Returns:
            True if should proceed with minimal, False otherwise
        """
        return state.metadata_policy in {
            MetadataRequestPolicy.USER_DECLINED,
            MetadataRequestPolicy.PROCEEDING_MINIMAL,
            MetadataRequestPolicy.ASKED_ONCE,  # Already asked once
        }

    def get_missing_required_fields(self, state: GlobalState) -> list[str]:
        """
        Get list of missing required DANDI fields.

        Args:
            state: Current global state

        Returns:
            List of missing field names
        """
        missing = []
        for field in self.REQUIRED_DANDI_FIELDS:
            if field not in state.metadata or not state.metadata.get(field):
                # Skip if user explicitly declined this field
                if field not in state.user_declined_fields:
                    missing.append(field)
        return missing

    # Private helper methods

    def _has_missing_required_fields(self, state: GlobalState) -> bool:
        """Check if any required DANDI fields are missing."""
        missing = self.get_missing_required_fields(state)
        return len(missing) > 0

    def _not_already_asked(self, state: GlobalState) -> bool:
        """Check if haven't asked for metadata yet."""
        return state.metadata_policy == MetadataRequestPolicy.NOT_ASKED

    def _user_declined_metadata(self, state: GlobalState) -> bool:
        """Check if user explicitly declined to provide metadata."""
        return state.metadata_policy in {
            MetadataRequestPolicy.USER_DECLINED,
            MetadataRequestPolicy.PROCEEDING_MINIMAL,
        }

    def _in_active_metadata_conversation(self, state: GlobalState) -> bool:
        """Check if currently in active metadata collection conversation."""
        return (
            state.conversation_phase == ConversationPhase.METADATA_COLLECTION
            and state.metadata_policy == MetadataRequestPolicy.ASKED_ONCE
        )

    def _recently_had_user_response(self, state: GlobalState) -> bool:
        """
        Check if user recently responded in conversation.

        Looks at last 2 messages in conversation history.
        """
        if len(state.conversation_history) < 1:
            return False

        # Check last 2 messages for user role
        recent_messages = state.conversation_history[-2:]
        return any(msg.get("role") == "user" for msg in recent_messages)

    def update_metadata_policy_after_request(self, state: GlobalState) -> None:
        """
        Update metadata policy after requesting metadata from user.

        Args:
            state: Current global state (modified in-place)
        """
        if state.metadata_policy == MetadataRequestPolicy.NOT_ASKED:
            state.metadata_policy = MetadataRequestPolicy.ASKED_ONCE
            # Update deprecated fields for backward compatibility
            state.metadata_requests_count = 1

    def update_metadata_policy_after_user_provided(self, state: GlobalState) -> None:
        """
        Update metadata policy after user provided metadata.

        Args:
            state: Current global state (modified in-place)
        """
        state.metadata_policy = MetadataRequestPolicy.USER_PROVIDED

    def update_metadata_policy_after_user_declined(self, state: GlobalState) -> None:
        """
        Update metadata policy after user declined to provide metadata.

        Args:
            state: Current global state (modified in-place)
        """
        state.metadata_policy = MetadataRequestPolicy.USER_DECLINED
        # Update deprecated fields for backward compatibility
        state.user_wants_minimal = True

    def format_missing_fields_message(self, missing_fields: list[str]) -> str:
        """
        Format a user-friendly message for missing fields.

        Args:
            missing_fields: List of missing field names

        Returns:
            Formatted message string
        """
        if not missing_fields:
            return ""

        field_descriptions = {
            "experimenter": "experimenter name(s)",
            "institution": "institution name",
            "experiment_description": "experiment description",
            "session_start_time": "session start time",
            "subject_id": "subject ID",
            "species": "species (e.g., Mus musculus for mouse)",
            "sex": "subject's sex (M/F/U)",
        }

        formatted = []
        for field in missing_fields:
            desc = field_descriptions.get(field, field)
            formatted.append(f"  - {desc}")

        return "Could you provide:\n" + "\n".join(formatted)
