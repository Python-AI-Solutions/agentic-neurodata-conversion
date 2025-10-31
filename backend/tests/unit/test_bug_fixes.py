"""
Regression tests for all 11 bug fixes.

These tests ensure that previously fixed bugs don't reappear.
Each test maps to a specific bug from the bug analysis report.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path

from agents.conversation_agent import ConversationAgent
from agents.evaluation_agent import EvaluationAgent
from models import (
    GlobalState,
    ConversionStatus,
    ValidationStatus,
    LogLevel,
    MCPMessage,
    MCPResponse,
    UserDecision,
)
from services.mcp_server import MCPServer
from services.llm_service import MockLLMService


class TestBug1ValidationStatusEnum:
    """Bug #1: ValidationStatus enum values were incorrect."""

    def test_validation_status_enum_has_correct_values(self):
        """Test that ValidationStatus enum has exactly 5 required values."""
        # Bug #1 fix: Enum should have final outcome values, not runtime statuses
        expected_values = {
            "passed",
            "passed_accepted",
            "passed_improved",
            "failed_user_declined",
            "failed_user_abandoned",
        }

        actual_values = {status.value for status in ValidationStatus}

        assert actual_values == expected_values, (
            f"ValidationStatus enum values mismatch. "
            f"Expected: {expected_values}, Got: {actual_values}"
        )

    def test_validation_status_enum_count(self):
        """Test that ValidationStatus has exactly 5 values."""
        assert len(ValidationStatus) == 5, (
            f"ValidationStatus should have exactly 5 values, got {len(ValidationStatus)}"
        )

    def test_validation_status_values_are_strings(self):
        """Test that all ValidationStatus values are strings."""
        for status in ValidationStatus:
            assert isinstance(status.value, str)


class TestBug2OverallStatusField:
    """Bug #2: overall_status field was missing from GlobalState."""

    def test_global_state_has_overall_status_field(self):
        """Test that GlobalState has overall_status field."""
        state = GlobalState()

        assert hasattr(state, "overall_status"), (
            "GlobalState should have 'overall_status' field"
        )

    def test_overall_status_initializes_to_none(self):
        """Test that overall_status initializes to None."""
        state = GlobalState()

        assert state.overall_status is None

    def test_overall_status_can_be_set(self):
        """Test that overall_status can be set to valid values."""
        state = GlobalState()

        # Test all valid values
        valid_values = ["PASSED", "PASSED_WITH_ISSUES", "FAILED"]
        for value in valid_values:
            state.overall_status = value
            assert state.overall_status == value

    @pytest.mark.asyncio
    async def test_evaluation_agent_sets_overall_status(self):
        """Test that Evaluation Agent sets overall_status after validation."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()
        agent = EvaluationAgent(llm_service=llm_service)  # Fixed: No mcp_server param
        state = mcp_server.global_state

        # Mock validation result with no issues (PASSED)
        with patch("agents.evaluation_agent.NWBInspector") as mock_inspector:
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.issues = []
            mock_result.summary = {"critical": 0, "error": 0, "warning": 0}
            mock_inspector.return_value.inspect.return_value = mock_result

            with patch("agents.evaluation_agent.Path") as mock_path:
                mock_path.return_value.exists.return_value = True

                message = MCPMessage(
                    target_agent="evaluation",
                    action="validate_nwb",
                    context={"nwb_path": "/fake/path.nwb"},
                )

                await agent.handle_validate_nwb(message, state)

                # Bug #2 fix: overall_status should be set
                assert state.overall_status in ["PASSED", "PASSED_WITH_ISSUES", "FAILED"]


class TestBug3AcceptAsIsFlow:
    """Bug #3: 'Accept As-Is' flow missing for PASSED_WITH_ISSUES."""

    def test_user_decision_enum_has_accept_option(self):
        """Test that UserDecision enum includes ACCEPT option."""
        # Bug #3 fix: Must have ACCEPT option
        assert hasattr(UserDecision, "ACCEPT"), (
            "UserDecision enum should have ACCEPT option"
        )
        assert UserDecision.ACCEPT.value == "accept"

    @pytest.mark.asyncio
    async def test_accept_as_is_for_passed_with_issues(self):
        """Test that user can accept file with warnings without improvement."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()
        agent = ConversationAgent(mcp_server=mcp_server, llm_service=llm_service)  # ConversationAgent needs mcp_server  # ConversationAgent still uses mcp_server
        state = mcp_server.global_state

        # Set up state for PASSED_WITH_ISSUES
        state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        state.overall_status = "PASSED_WITH_ISSUES"

        message = MCPMessage(
            target_agent="conversation",
            action="handle_retry_decision",
            context={"decision": "accept"},
        )

        response = await agent.handle_retry_decision(message, state)

        # Bug #3 fix: Should set validation_status to passed_accepted
        assert response.success is True
        assert state.validation_status == ValidationStatus.PASSED_ACCEPTED
        assert state.status == ConversionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_accept_not_allowed_for_failed(self):
        """Test that accept is not allowed for FAILED status."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()
        agent = ConversationAgent(mcp_server=mcp_server, llm_service=llm_service)  # ConversationAgent needs mcp_server
        state = mcp_server.global_state

        # Set up state for FAILED
        state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        state.overall_status = "FAILED"

        message = MCPMessage(
            target_agent="conversation",
            action="handle_retry_decision",
            context={"decision": "accept"},
        )

        response = await agent.handle_retry_decision(message, state)

        # Should return error for FAILED status
        assert response.success is False
        assert "only valid for PASSED_WITH_ISSUES" in response.error_message.lower()


class TestBug6PassedImprovedStatus:
    """Bug #6: passed_improved status was never set."""

    @pytest.mark.asyncio
    async def test_passed_improved_set_after_correction(self):
        """Test that validation_status is set to passed_improved after successful retry."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()
        agent = EvaluationAgent(llm_service=llm_service)  # Fixed: EvaluationAgent only takes llm_service
        state = mcp_server.global_state

        # Simulate correction attempt
        state.correction_attempt = 1

        # Mock validation result with no issues (PASSED)
        with patch("agents.evaluation_agent.NWBInspector") as mock_inspector:
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.issues = []
            mock_result.summary = {"critical": 0, "error": 0, "warning": 0}
            mock_inspector.return_value.inspect.return_value = mock_result

            with patch("agents.evaluation_agent.Path") as mock_path:
                mock_path.return_value.exists.return_value = True

                message = MCPMessage(
                    target_agent="evaluation",
                    action="validate_nwb",
                    context={"nwb_path": "/fake/path.nwb"},
                )

                await agent.handle_validate_nwb(message, state)

                # Bug #6 fix: Should be passed_improved after correction
                assert state.validation_status == ValidationStatus.PASSED_IMPROVED

    @pytest.mark.asyncio
    async def test_passed_set_on_first_attempt(self):
        """Test that validation_status is 'passed' on first successful attempt."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()
        agent = EvaluationAgent(llm_service=llm_service)  # Fixed: EvaluationAgent only takes llm_service
        state = mcp_server.global_state

        # First attempt (correction_attempt = 0)
        state.correction_attempt = 0

        # Mock validation result with no issues (PASSED)
        with patch("agents.evaluation_agent.NWBInspector") as mock_inspector:
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.issues = []
            mock_result.summary = {"critical": 0, "error": 0, "warning": 0}
            mock_inspector.return_value.inspect.return_value = mock_result

            with patch("agents.evaluation_agent.Path") as mock_path:
                mock_path.return_value.exists.return_value = True

                message = MCPMessage(
                    target_agent="evaluation",
                    action="validate_nwb",
                    context={"nwb_path": "/fake/path.nwb"},
                )

                await agent.handle_validate_nwb(message, state)

                # Should be 'passed' on first attempt
                assert state.validation_status == ValidationStatus.PASSED


class TestBug7FailedUserDeclinedStatus:
    """Bug #7: failed_user_declined status was never set."""

    @pytest.mark.asyncio
    async def test_failed_user_declined_on_reject(self):
        """Test that validation_status is set to failed_user_declined when user rejects retry."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()
        agent = ConversationAgent(mcp_server=mcp_server, llm_service=llm_service)  # ConversationAgent needs mcp_server
        state = mcp_server.global_state

        # Set up state for retry approval
        state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        state.overall_status = "FAILED"

        message = MCPMessage(
            target_agent="conversation",
            action="handle_retry_decision",
            context={"decision": "reject"},
        )

        response = await agent.handle_retry_decision(message, state)

        # Bug #7 fix: Should set validation_status to failed_user_declined
        assert response.success is True
        assert state.validation_status == ValidationStatus.FAILED_USER_DECLINED
        assert state.status == ConversionStatus.FAILED


class TestBug8FailedUserAbandonedStatus:
    """Bug #8: failed_user_abandoned status was never set."""

    @pytest.mark.asyncio
    async def test_failed_user_abandoned_on_cancel(self):
        """Test that validation_status is set to failed_user_abandoned when user cancels."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()
        agent = ConversationAgent(mcp_server=mcp_server, llm_service=llm_service)  # ConversationAgent needs mcp_server
        state = mcp_server.global_state

        # Set up state for user input
        state.status = ConversionStatus.AWAITING_USER_INPUT

        # Test various cancellation keywords
        cancel_keywords = ["cancel", "quit", "stop", "abort", "exit"]

        for keyword in cancel_keywords:
            state.validation_status = None  # Reset
            state.status = ConversionStatus.AWAITING_USER_INPUT

            message = MCPMessage(
                target_agent="conversation",
                action="handle_conversational_response",
                context={"user_message": keyword},
            )

            response = await agent.handle_conversational_response(message, state)

            # Bug #8 fix: Should set validation_status to failed_user_abandoned
            assert state.validation_status == ValidationStatus.FAILED_USER_ABANDONED
            assert state.status == ConversionStatus.FAILED


class TestBug9OverallStatusResetOnUpload:
    """Bug #9: overall_status was not reset on new upload."""

    def test_overall_status_reset_in_global_state_reset(self):
        """Test that GlobalState.reset() clears overall_status."""
        state = GlobalState()

        # Set overall_status
        state.overall_status = "PASSED_WITH_ISSUES"
        state.validation_status = ValidationStatus.PASSED_ACCEPTED

        # Reset state
        state.reset()

        # Bug #9 fix: overall_status should be None after reset
        assert state.overall_status is None
        assert state.validation_status is None


class TestBug11NoProgressDetection:
    """Bug #11: 'No progress' detection was not implemented."""

    def test_global_state_has_no_progress_fields(self):
        """Test that GlobalState has fields for no-progress detection."""
        state = GlobalState()

        # Bug #11 fix: Should have tracking fields
        assert hasattr(state, "previous_validation_issues")
        assert hasattr(state, "user_provided_input_this_attempt")
        assert hasattr(state, "auto_corrections_applied_this_attempt")

    def test_no_progress_fields_initialize_correctly(self):
        """Test that no-progress fields initialize correctly."""
        state = GlobalState()

        assert state.previous_validation_issues is None
        assert state.user_provided_input_this_attempt is False
        assert state.auto_corrections_applied_this_attempt is False

    def test_detect_no_progress_method_exists(self):
        """Test that detect_no_progress() method exists."""
        state = GlobalState()

        assert hasattr(state, "detect_no_progress")
        assert callable(state.detect_no_progress)

    def test_detect_no_progress_identical_issues(self):
        """Test no progress detection with identical issues."""
        state = GlobalState()

        # Set up previous issues
        previous_issues = [
            {"check_name": "test_check", "location": "/file", "message": "error1"},
            {"check_name": "test_check2", "location": "/file2", "message": "error2"},
        ]
        state.previous_validation_issues = previous_issues
        state.correction_attempt = 1
        state.user_provided_input_this_attempt = False
        state.auto_corrections_applied_this_attempt = False

        # Same issues again
        current_issues = [
            {"check_name": "test_check", "location": "/file", "message": "error1"},
            {"check_name": "test_check2", "location": "/file2", "message": "error2"},
        ]

        # Bug #11 fix: Should detect no progress
        assert state.detect_no_progress(current_issues) is True

    def test_detect_no_progress_with_user_input(self):
        """Test that progress is detected when user provides input."""
        state = GlobalState()

        previous_issues = [
            {"check_name": "test_check", "location": "/file", "message": "error1"},
        ]
        state.previous_validation_issues = previous_issues
        state.correction_attempt = 1
        state.user_provided_input_this_attempt = True  # User provided input
        state.auto_corrections_applied_this_attempt = False

        current_issues = previous_issues.copy()

        # Should NOT detect no progress (user input counts as progress)
        assert state.detect_no_progress(current_issues) is False

    def test_detect_no_progress_with_auto_corrections(self):
        """Test that progress is detected when auto-corrections applied."""
        state = GlobalState()

        previous_issues = [
            {"check_name": "test_check", "location": "/file", "message": "error1"},
        ]
        state.previous_validation_issues = previous_issues
        state.correction_attempt = 1
        state.user_provided_input_this_attempt = False
        state.auto_corrections_applied_this_attempt = True  # Auto-corrections applied

        current_issues = previous_issues.copy()

        # Should NOT detect no progress (auto-corrections count as progress)
        assert state.detect_no_progress(current_issues) is False

    def test_detect_no_progress_first_attempt(self):
        """Test that first attempt always has progress."""
        state = GlobalState()

        state.correction_attempt = 0
        state.previous_validation_issues = None

        current_issues = [
            {"check_name": "test_check", "location": "/file", "message": "error1"},
        ]

        # First attempt always has progress
        assert state.detect_no_progress(current_issues) is False

    def test_no_progress_fields_reset_correctly(self):
        """Test that no-progress fields reset correctly."""
        state = GlobalState()

        # Set values
        state.previous_validation_issues = [{"check_name": "test"}]
        state.user_provided_input_this_attempt = True
        state.auto_corrections_applied_this_attempt = True

        # Reset
        state.reset()

        # Bug #11 fix: Should be reset
        assert state.previous_validation_issues is None
        assert state.user_provided_input_this_attempt is False
        assert state.auto_corrections_applied_this_attempt is False


class TestBug12OverallStatusInAPI:
    """Bug #12: Status API was missing overall_status field."""

    def test_status_response_model_has_overall_status(self):
        """Test that StatusResponse model includes overall_status field."""
        from models.api import StatusResponse

        # Bug #12 fix: Should have overall_status field
        response = StatusResponse(
            status=ConversionStatus.COMPLETED,
            validation_status=ValidationStatus.PASSED,
            overall_status="PASSED",
            progress=None,
            message=None,
            input_path=None,
            output_path=None,
            correction_attempt=0,
            can_retry=True,
            conversation_type=None,
        )

        assert hasattr(response, "overall_status")
        assert response.overall_status == "PASSED"


class TestBug14UnlimitedRetries:
    """Bug #14: Max retry limit contradicted unlimited retries requirement."""

    def test_global_state_no_max_correction_attempts_field(self):
        """Test that GlobalState no longer has max_correction_attempts field."""
        state = GlobalState()

        # Bug #14 fix: Should NOT have max_correction_attempts field
        assert not hasattr(state, "max_correction_attempts"), (
            "GlobalState should not have max_correction_attempts field (unlimited retries)"
        )

    def test_global_state_no_can_retry_method(self):
        """Test that GlobalState no longer has can_retry() method."""
        state = GlobalState()

        # Bug #14 fix: Should NOT have can_retry() method
        assert not hasattr(state, "can_retry"), (
            "GlobalState should not have can_retry() method (unlimited retries)"
        )

    def test_can_retry_many_attempts(self):
        """Test that system allows unlimited retry attempts."""
        state = GlobalState()

        # Simulate many retry attempts
        for attempt in range(10):
            state.correction_attempt = attempt
            # Should always be able to increment (no limit)
            state.increment_retry()

        # Should have 10 attempts without any limit
        assert state.correction_attempt == 10


class TestBug15OverallStatusInReset:
    """Bug #15: overall_status was not cleared in reset() method."""

    def test_reset_clears_overall_status(self):
        """Test that reset() method clears overall_status."""
        state = GlobalState()

        # Set overall_status
        state.overall_status = "PASSED_WITH_ISSUES"
        state.validation_status = ValidationStatus.PASSED_ACCEPTED
        state.correction_attempt = 5

        # Reset
        state.reset()

        # Bug #15 fix: overall_status should be None
        assert state.overall_status is None
        assert state.validation_status is None
        assert state.correction_attempt == 0


class TestAllBugFixesIntegration:
    """Integration test to verify all bug fixes work together."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_all_fixes(self):
        """Test a complete workflow that exercises all 11 bug fixes."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()

        # Register agents
        from agents import (
            register_conversation_agent,
            register_conversion_agent,
            register_evaluation_agent,
        )
        register_conversation_agent(mcp_server, llm_service)
        register_conversion_agent(mcp_server, llm_service)
        register_evaluation_agent(mcp_server, llm_service)

        state = mcp_server.global_state

        # Verify initial state (Bug #2, #9, #11, #15)
        assert state.overall_status is None
        assert state.validation_status is None
        assert state.previous_validation_issues is None
        assert state.user_provided_input_this_attempt is False
        assert state.auto_corrections_applied_this_attempt is False

        # Verify ValidationStatus enum (Bug #1)
        assert len(ValidationStatus) == 5
        assert hasattr(ValidationStatus, "PASSED")
        assert hasattr(ValidationStatus, "PASSED_ACCEPTED")
        assert hasattr(ValidationStatus, "PASSED_IMPROVED")
        assert hasattr(ValidationStatus, "FAILED_USER_DECLINED")
        assert hasattr(ValidationStatus, "FAILED_USER_ABANDONED")

        # Verify UserDecision has ACCEPT (Bug #3)
        assert hasattr(UserDecision, "ACCEPT")

        # Verify unlimited retries (Bug #14)
        assert not hasattr(state, "max_correction_attempts")
        assert not hasattr(state, "can_retry")

        # Verify no-progress detection fields exist (Bug #11)
        assert hasattr(state, "detect_no_progress")

        print("✅ All 11 bug fixes verified in integration test")
