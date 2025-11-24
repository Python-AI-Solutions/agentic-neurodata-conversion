"""Unit tests for RetryWorkflow.

Tests retry decision handling, LLM correction analysis,
and re-validation workflow with focus on uncovered code sections.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.conversation.retry_workflow import RetryWorkflow
from agentic_neurodata_conversion.models import (
    ConversionStatus,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationOutcome,
    ValidationStatus,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_server():
    """Create mock MCP server for testing."""
    mock_server = Mock()
    mock_server.send_message = AsyncMock(return_value=MCPResponse(success=True, reply_to="test_msg", result={}))
    return mock_server


@pytest.fixture
def mock_adaptive_retry_strategy():
    """Create mock adaptive retry strategy."""
    mock_strategy = Mock()
    mock_strategy.analyze_and_recommend_strategy = AsyncMock(
        return_value={
            "should_retry": True,
            "strategy": "intelligent_correction",
            "approach": "llm_analysis",
            "ask_user": False,
        }
    )
    return mock_strategy


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    from agentic_neurodata_conversion.services.llm_service import MockLLMService

    return MockLLMService()


@pytest.fixture
def retry_workflow(mock_mcp_server):
    """Create RetryWorkflow instance."""
    return RetryWorkflow(mcp_server=mock_mcp_server)


@pytest.fixture
def retry_workflow_with_llm(mock_mcp_server, mock_llm_service):
    """Create RetryWorkflow with LLM service."""
    return RetryWorkflow(
        mcp_server=mock_mcp_server,
        llm_service=mock_llm_service,
    )


@pytest.fixture
def retry_workflow_with_adaptive(mock_mcp_server, mock_adaptive_retry_strategy, mock_llm_service):
    """Create RetryWorkflow with adaptive strategy and LLM."""
    return RetryWorkflow(
        mcp_server=mock_mcp_server,
        adaptive_retry_strategy=mock_adaptive_retry_strategy,
        llm_service=mock_llm_service,
    )


@pytest.fixture
def sample_validation_result():
    """Sample validation result with issues."""
    return {
        "overall_status": "FAILED",
        "issues": [
            {
                "severity": "critical",
                "message": "Missing required field: session_description",
                "location": "/",
                "issue": "session_description missing",
                "suggestion": "Add session_description field",
            },
            {
                "severity": "critical",
                "message": "Subject ID is empty",
                "location": "/subject",
                "issue": "subject_id field is empty",
                "suggestion": "Provide a unique subject_id",
            },
        ],
    }


# ============================================================================
# Test Decision Validation
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestRetryDecisionValidation:
    """Test decision type validation."""

    async def test_invalid_decision_type(self, retry_workflow, global_state):
        """Test invalid decision type returns error."""
        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "invalid_decision"},
        )

        response = await retry_workflow.handle_retry_decision(message, global_state, None)

        assert not response.success
        assert response.error["code"] == "INVALID_DECISION"
        assert "approve" in response.error["message"]

    async def test_decision_in_wrong_state(self, retry_workflow, global_state):
        """Test decision rejected if state is not AWAITING_RETRY_APPROVAL."""
        global_state.status = ConversionStatus.IDLE

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow.handle_retry_decision(message, global_state, None)

        assert not response.success
        assert response.error["code"] == "INVALID_STATE"


# ============================================================================
# Test Accept Decision (Lines 124-158)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestAcceptDecision:
    """Test 'accept' decision for PASSED_WITH_ISSUES."""

    async def test_accept_decision_passed_with_issues(self, retry_workflow, global_state):
        """Test accepting file with warnings (PASSED_WITH_ISSUES)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.overall_status = ValidationOutcome.PASSED_WITH_ISSUES

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "accept"},
        )

        response = await retry_workflow.handle_retry_decision(message, global_state, None)

        assert response.success
        assert global_state.validation_status == ValidationStatus.PASSED_ACCEPTED
        assert global_state.status == ConversionStatus.COMPLETED
        assert "accepted with warnings" in response.result["message"].lower()

    async def test_accept_decision_string_status(self, retry_workflow, global_state):
        """Test accept with string status (enum conversion)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.overall_status = "PASSED_WITH_ISSUES"

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "accept"},
        )

        response = await retry_workflow.handle_retry_decision(message, global_state, None)

        assert response.success
        assert global_state.validation_status == ValidationStatus.PASSED_ACCEPTED

    async def test_accept_decision_invalid_status(self, retry_workflow, global_state):
        """Test accept rejected if status is not PASSED_WITH_ISSUES."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.overall_status = ValidationOutcome.FAILED

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "accept"},
        )

        response = await retry_workflow.handle_retry_decision(message, global_state, None)

        assert not response.success
        assert response.error["code"] == "INVALID_DECISION"
        assert "only valid for PASSED_WITH_ISSUES" in response.error["message"]

    async def test_accept_decision_invalid_enum(self, retry_workflow, global_state):
        """Test accept with invalid enum value (lines 133-134)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.overall_status = "INVALID_STATUS"

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "accept"},
        )

        response = await retry_workflow.handle_retry_decision(message, global_state, None)

        assert not response.success


# ============================================================================
# Test Reject Decision (Lines 160-175)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestRejectDecision:
    """Test 'reject' decision handling."""

    async def test_reject_decision(self, retry_workflow, global_state):
        """Test user rejecting retry."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "reject"},
        )

        response = await retry_workflow.handle_retry_decision(message, global_state, None)

        assert response.success
        assert global_state.validation_status == ValidationStatus.FAILED_USER_DECLINED
        assert global_state.status == ConversionStatus.FAILED
        assert "terminated by user" in response.result["message"].lower()


# ============================================================================
# Test No-Progress Detection (Lines 192-232)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestNoProgressDetection:
    """Test no-progress detection logic."""

    async def test_no_progress_detected(self, retry_workflow_with_llm, global_state):
        """Test detection of no progress (same issues)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # Set up previous issues
        issues = [{"message": "Missing session_description"}]
        global_state.previous_validation_issues = issues

        # Add validation result to logs
        global_state.add_log(
            LogLevel.INFO,
            "Validation completed",
            {"validation": {"issues": issues}},
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        # Mock callback
        mock_callback = AsyncMock(return_value=MCPResponse(success=True, reply_to="test", result={}))

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, mock_callback)

        # Should detect no progress and log warning
        warnings = [log for log in global_state.logs if log.level == LogLevel.WARNING]
        assert any("No progress detected" in log.message for log in warnings)

    async def test_no_progress_flags_reset(self, retry_workflow_with_llm, global_state):
        """Test that progress flags are reset after detection."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.user_provided_input_this_attempt = True
        global_state.auto_corrections_applied_this_attempt = True

        # Add validation result
        issues = [{"message": "Test issue"}]
        global_state.add_log(
            LogLevel.INFO,
            "Validation",
            {"validation": {"issues": issues}},
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        mock_callback = AsyncMock(return_value=MCPResponse(success=True, reply_to="test", result={}))

        await retry_workflow_with_llm.handle_retry_decision(message, global_state, mock_callback)

        # Flags should be reset
        assert not global_state.user_provided_input_this_attempt
        assert not global_state.auto_corrections_applied_this_attempt


# ============================================================================
# Test Adaptive Retry Strategy (Lines 234-312)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestAdaptiveRetryStrategy:
    """Test adaptive retry strategy integration."""

    async def test_adaptive_retry_ask_user(self, retry_workflow_with_adaptive, global_state):
        """Test adaptive retry requesting user input (lines 258-281)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # Add validation result
        validation_result = {"issues": [{"message": "Test issue"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})

        # Configure strategy to ask user
        retry_workflow_with_adaptive._adaptive_retry_strategy.analyze_and_recommend_strategy.return_value = {
            "should_retry": True,
            "ask_user": True,
            "message": "We need your help",
            "questions_for_user": ["What is the subject ID?", "What is the session description?"],
        }

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_adaptive.handle_retry_decision(message, global_state, None)

        assert response.success
        assert global_state.status == ConversionStatus.AWAITING_USER_INPUT
        assert "We need your help" in response.result["message"]
        assert response.result["needs_user_input"]

    async def test_adaptive_retry_should_not_retry(self, retry_workflow_with_adaptive, global_state):
        """Test adaptive retry recommending to stop (lines 283-301)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # Add validation result
        validation_result = {"issues": [{"message": "Persistent issue"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})

        # Configure strategy to not retry
        retry_workflow_with_adaptive._adaptive_retry_strategy.analyze_and_recommend_strategy.return_value = {
            "should_retry": False,
            "ask_user": False,
            "message": "These issues cannot be automatically fixed",
        }

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_adaptive.handle_retry_decision(message, global_state, None)

        assert response.success
        assert global_state.status == ConversionStatus.FAILED
        assert global_state.validation_status == ValidationStatus.FAILED_PERSISTENT

    async def test_adaptive_retry_exception_handling(self, retry_workflow_with_adaptive, global_state):
        """Test adaptive retry handles exceptions gracefully (lines 307-312)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # Add validation result
        validation_result = {"issues": [{"message": "Test issue"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})

        # Make strategy raise exception
        retry_workflow_with_adaptive._adaptive_retry_strategy.analyze_and_recommend_strategy.side_effect = Exception(
            "Strategy analysis failed"
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        mock_callback = AsyncMock(return_value=MCPResponse(success=True, reply_to="test", result={}))

        # Should continue despite exception
        response = await retry_workflow_with_adaptive.handle_retry_decision(message, global_state, mock_callback)

        # Should have logged warning
        warnings = [log for log in global_state.logs if log.level == LogLevel.WARNING]
        assert any("Adaptive retry analysis failed" in log.message for log in warnings)


# ============================================================================
# Test LLM Correction Analysis - Auto-Corrections Path (Lines 374-544)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestLLMCorrectionAnalysis:
    """Test LLM correction analysis and auto-fix workflow."""

    async def test_llm_corrections_applied_successfully(self, retry_workflow_with_llm, global_state):
        """Test successful application of auto-corrections (lines 374-393)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.output_path = "/test/output.nwb"

        # Add validation result
        validation_result = {"issues": [{"message": "Species missing"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})

        # Mock MCP server responses
        retry_workflow_with_llm._mcp_server.send_message = AsyncMock(
            side_effect=[
                # analyze_corrections response
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={
                        "corrections": {
                            "suggestions": [
                                {
                                    "issue": "species missing",
                                    "suggestion": "Set species to Mus musculus (mouse)",
                                    "actionable": True,
                                }
                            ],
                            "analysis": "Species field is missing",
                            "recommended_action": "apply_corrections",
                        }
                    },
                ),
                # apply_corrections response
                MCPResponse(success=True, reply_to="test", result={"status": "success"}),
                # run_validation response - PASSED
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={
                        "validation_result": {
                            "overall_status": "PASSED",
                            "issues": [],
                        }
                    },
                ),
                # generate_report response
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={"report_path": "/test/report.html"},
                ),
            ]
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        # Should complete successfully (lines 487-506)
        assert response.success
        assert global_state.status == ConversionStatus.COMPLETED
        assert global_state.validation_status == ValidationStatus.PASSED
        assert "All issues have been fixed" in response.result["message"]
        assert global_state.auto_corrections_applied_this_attempt

    async def test_llm_corrections_passed_with_issues(self, retry_workflow_with_llm, global_state):
        """Test corrections result in PASSED_WITH_ISSUES (lines 448-485)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.output_path = "/test/output.nwb"

        # Add validation result with 2 issues
        validation_result = {"issues": [{"message": "Issue 1"}, {"message": "Issue 2"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})
        global_state.metadata["previous_validation_result"] = validation_result

        # Mock responses
        retry_workflow_with_llm._mcp_server.send_message = AsyncMock(
            side_effect=[
                # analyze_corrections
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={"corrections": {"suggestions": [], "analysis": "Test"}},
                ),
                # apply_corrections
                MCPResponse(success=True, reply_to="test", result={}),
                # run_validation - PASSED_WITH_ISSUES with 1 issue
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={
                        "validation_result": {
                            "overall_status": "PASSED_WITH_ISSUES",
                            "issues": [{"message": "Remaining issue"}],
                        }
                    },
                ),
                # generate_report
                MCPResponse(success=True, reply_to="test", result={"report_path": "/test/report.html"}),
            ]
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        assert response.success
        assert global_state.status == ConversionStatus.AWAITING_USER_INPUT
        assert global_state.validation_status == ValidationStatus.PASSED_WITH_ISSUES
        assert "improved but still has" in response.result["message"].lower()

    async def test_llm_corrections_worsened(self, retry_workflow_with_llm, global_state):
        """Test corrections increased issue count (lines 456-472)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.output_path = "/test/output.nwb"

        # Start with 1 issue
        initial_issues = [{"message": "Initial issue"}]
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": {"issues": initial_issues}})
        global_state.metadata["previous_validation_result"] = {"issues": initial_issues}

        # Mock responses - result in 3 issues (worse)
        retry_workflow_with_llm._mcp_server.send_message = AsyncMock(
            side_effect=[
                # analyze_corrections
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={"corrections": {"suggestions": [], "analysis": "Test"}},
                ),
                # apply_corrections
                MCPResponse(success=True, reply_to="test", result={}),
                # run_validation - MORE issues
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={
                        "validation_result": {
                            "overall_status": "PASSED_WITH_ISSUES",
                            "issues": [
                                {"message": "Issue 1"},
                                {"message": "Issue 2"},
                                {"message": "Issue 3"},
                            ],
                        }
                    },
                ),
                # generate_report
                MCPResponse(success=True, reply_to="test", result={"report_path": "/test/report.html"}),
            ]
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        # Should warn about increased issues
        warnings = [log for log in global_state.logs if log.level == LogLevel.WARNING]
        assert any("MORE issues" in log.message for log in warnings)
        assert "increased from 1 to 3" in response.result["message"]

    async def test_llm_corrections_failed(self, retry_workflow_with_llm, global_state):
        """Test corrections result in FAILED status (lines 508-526)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.output_path = "/test/output.nwb"

        # Add validation result
        validation_result = {"issues": [{"message": "Test issue"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})

        # Mock responses - fail after corrections
        retry_workflow_with_llm._mcp_server.send_message = AsyncMock(
            side_effect=[
                # analyze_corrections
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={"corrections": {"suggestions": [], "analysis": "Test"}},
                ),
                # apply_corrections
                MCPResponse(success=True, reply_to="test", result={}),
                # run_validation - FAILED
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={
                        "validation_result": {
                            "overall_status": "FAILED",
                            "issues": [{"message": "Critical error"}],
                        }
                    },
                ),
                # generate_report
                MCPResponse(success=True, reply_to="test", result={"report_path": "/test/report.html"}),
            ]
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        assert response.success
        assert global_state.status == ConversionStatus.AWAITING_RETRY_APPROVAL
        assert global_state.validation_status == ValidationStatus.FAILED
        assert "critical errors" in response.result["message"].lower()

    async def test_correction_application_failed(self, retry_workflow_with_llm, global_state):
        """Test handling when correction application fails (lines 537-542)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # Add validation result
        validation_result = {"issues": [{"message": "Test issue"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})

        # Mock responses - correction application fails
        retry_workflow_with_llm._mcp_server.send_message = AsyncMock(
            side_effect=[
                # analyze_corrections succeeds
                MCPResponse(
                    success=True,
                    reply_to="test",
                    result={"corrections": {"suggestions": [], "analysis": "Test"}},
                ),
                # apply_corrections fails
                MCPResponse(
                    success=False,
                    reply_to="test",
                    result={},
                    error={"message": "Correction application failed"},
                ),
            ]
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        # Should propagate error
        assert not response.success
        errors = [log for log in global_state.logs if log.level == LogLevel.ERROR]
        assert any("Correction application failed" in log.message for log in errors)

    async def test_llm_analysis_failed(self, retry_workflow_with_llm, global_state):
        """Test handling when LLM analysis fails (lines 543-547)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.input_path = "/test/input.dat"
        global_state.pending_conversion_input_path = "/test/input.dat"

        # Add validation result
        validation_result = {"issues": [{"message": "Test issue"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})

        # Mock responses - analysis fails
        retry_workflow_with_llm._mcp_server.send_message = AsyncMock(
            return_value=MCPResponse(
                success=False,
                reply_to="test",
                result={},
                error={"message": "LLM analysis failed"},
            )
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        mock_callback = AsyncMock(return_value=MCPResponse(success=True, reply_to="test", result={}))

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, mock_callback)

        # Should have logged warning and continued
        warnings = [log for log in global_state.logs if log.level == LogLevel.WARNING]
        assert any("LLM analysis failed" in log.message for log in warnings)


# ============================================================================
# Test User Input Required (Lines 354-370)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserInputRequired:
    """Test user input requirement detection."""

    async def test_user_input_required(self, retry_workflow_with_llm, global_state):
        """Test transition to AWAITING_USER_INPUT when needed."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL

        # Add validation result
        validation_result = {"issues": [{"message": "Test issue"}]}
        global_state.add_log(LogLevel.INFO, "Validation", {"validation": validation_result})

        # Mock analyze_corrections to return non-actionable suggestions
        retry_workflow_with_llm._mcp_server.send_message = AsyncMock(
            return_value=MCPResponse(
                success=True,
                reply_to="test",
                result={
                    "corrections": {
                        "suggestions": [
                            {
                                "issue": "subject_id missing",
                                "suggestion": "Please provide subject_id",
                                "actionable": False,
                            }
                        ],
                        "analysis": "User input needed",
                    }
                },
            )
        )

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        assert response.success
        assert global_state.status == ConversionStatus.AWAITING_USER_INPUT
        assert response.result["status"] == "awaiting_user_input"
        assert "required_fields" in response.result


# ============================================================================
# Test Fallback Without LLM (Lines 549-594)
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestFallbackWithoutLLM:
    """Test retry workflow without LLM service."""

    async def test_restart_without_llm(self, retry_workflow, global_state):
        """Test fallback message when no LLM available (lines 581-594)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.input_path = "/test/input.dat"
        global_state.pending_conversion_input_path = "/test/input.dat"

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow.handle_retry_decision(message, global_state, None)

        # Without LLM, should ask for manual corrections
        assert response.success
        assert response.result["status"] == "awaiting_corrections"
        assert "LLM not configured" in response.result["message"]
        assert global_state.status == ConversionStatus.AWAITING_USER_INPUT

    async def test_restart_missing_input_path(self, retry_workflow_with_llm, global_state):
        """Test error when input_path is missing with LLM (lines 552-567)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.input_path = None
        global_state.pending_conversion_input_path = None

        # DON'T add validation result - this triggers fallback restart path (lines 549-580)

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        assert not response.success
        assert response.error["code"] == "INVALID_STATE"
        assert "file path is not available" in response.error["message"]

    async def test_restart_empty_string_path(self, retry_workflow_with_llm, global_state):
        """Test error when input_path is empty string with LLM (lines 552-567)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.input_path = ""
        global_state.pending_conversion_input_path = ""

        # DON'T add validation result

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        assert not response.success
        assert response.error["code"] == "INVALID_STATE"

    async def test_restart_none_string_path(self, retry_workflow_with_llm, global_state):
        """Test error when path is string 'None' with LLM (lines 552-567)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.input_path = "None"
        global_state.pending_conversion_input_path = None

        # DON'T add validation result

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, None)

        assert not response.success

    async def test_restart_with_valid_path(self, retry_workflow_with_llm, global_state):
        """Test successful restart with valid path (lines 569-580)."""
        global_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        global_state.input_path = "/test/input.dat"
        global_state.pending_conversion_input_path = "/test/input.dat"

        # DON'T add validation result - triggers fallback restart

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={"decision": "approve"},
        )

        mock_callback = AsyncMock(
            return_value=MCPResponse(success=True, reply_to="test", result={"status": "restarted"})
        )

        response = await retry_workflow_with_llm.handle_retry_decision(message, global_state, mock_callback)

        # Should restart conversion
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args[0][0]
        assert call_args.action == "start_conversion"
        assert call_args.context["input_path"] == "/test/input.dat"


# ============================================================================
# Test Helper Methods
# ============================================================================


@pytest.mark.unit
class TestIdentifyUserInputRequired:
    """Test _identify_user_input_required method."""

    def test_subject_id_missing(self, retry_workflow):
        """Test identifying missing subject_id."""
        corrections = {
            "suggestions": [
                {
                    "issue": "subject_id field is missing",
                    "suggestion": "Please provide subject_id",
                    "actionable": False,
                }
            ]
        }

        result = retry_workflow._identify_user_input_required(corrections)

        assert len(result) == 1
        assert result[0]["field_name"] == "subject_id"
        assert result[0]["required"]

    def test_session_description_too_short(self, retry_workflow):
        """Test identifying short session_description."""
        corrections = {
            "suggestions": [
                {
                    "issue": "session_description field exists",
                    "suggestion": "Session description is too short, needs minimum 20 characters",
                    "actionable": False,
                }
            ]
        }

        result = retry_workflow._identify_user_input_required(corrections)

        assert len(result) == 1
        assert result[0]["field_name"] == "session_description"
        assert result[0]["type"] == "textarea"

    def test_experimenter_missing(self, retry_workflow):
        """Test identifying missing experimenter."""
        corrections = {
            "suggestions": [
                {
                    "issue": "experimenter is empty",
                    "suggestion": "Add experimenter name",
                    "actionable": False,
                }
            ]
        }

        result = retry_workflow._identify_user_input_required(corrections)

        assert len(result) == 1
        assert result[0]["field_name"] == "experimenter"

    def test_institution_required(self, retry_workflow):
        """Test identifying institution (lines 656-666)."""
        corrections = {
            "suggestions": [
                {
                    "issue": "institution is missing",
                    "suggestion": "Add institution name",
                    "actionable": False,
                }
            ]
        }

        result = retry_workflow._identify_user_input_required(corrections)

        assert len(result) == 1
        assert result[0]["field_name"] == "institution"
        assert not result[0]["required"]  # institution is optional

    def test_skip_actionable_suggestions(self, retry_workflow):
        """Test that actionable suggestions are skipped."""
        corrections = {
            "suggestions": [
                {
                    "issue": "species missing",
                    "suggestion": "Set to Mus musculus",
                    "actionable": True,
                }
            ]
        }

        result = retry_workflow._identify_user_input_required(corrections)

        assert len(result) == 0

    def test_empty_suggestions(self, retry_workflow):
        """Test empty suggestions list."""
        corrections = {"suggestions": []}

        result = retry_workflow._identify_user_input_required(corrections)

        assert result == []


@pytest.mark.unit
class TestExtractAutoFixes:
    """Test _extract_auto_fixes method."""

    def test_extract_species_mouse(self, retry_workflow):
        """Test extracting species fix for mouse (lines 703-707)."""
        corrections = {
            "suggestions": [
                {
                    "issue": "species is missing",
                    "suggestion": "Set species to mouse (Mus musculus)",
                    "actionable": True,
                }
            ]
        }

        result = retry_workflow._extract_auto_fixes(corrections)

        assert result.get("species") == "Mus musculus"

    def test_extract_species_rat(self, retry_workflow):
        """Test extracting species fix for rat (lines 706-707)."""
        corrections = {
            "suggestions": [
                {
                    "issue": "species field empty",
                    "suggestion": "Based on metadata, this appears to be a Rattus norvegicus study",
                    "actionable": True,
                }
            ]
        }

        result = retry_workflow._extract_auto_fixes(corrections)

        assert result.get("species") == "Rattus norvegicus"

    def test_extract_institution_removal(self, retry_workflow):
        """Test extracting institution removal (lines 720-726)."""
        corrections = {
            "suggestions": [
                {
                    "issue": "institution field is present",
                    "suggestion": "Institution is empty, remove the field",
                    "actionable": True,
                }
            ]
        }

        result = retry_workflow._extract_auto_fixes(corrections)

        assert result.get("institution") is None

    def test_extract_lab_removal(self, retry_workflow):
        """Test extracting lab removal (lines 725-726)."""
        corrections = {
            "suggestions": [
                {
                    "issue": "lab field exists",
                    "suggestion": "Lab is empty, should remove it",
                    "actionable": True,
                }
            ]
        }

        result = retry_workflow._extract_auto_fixes(corrections)

        assert result.get("lab") is None

    def test_skip_non_actionable(self, retry_workflow):
        """Test skipping non-actionable suggestions."""
        corrections = {
            "suggestions": [
                {
                    "issue": "test issue",
                    "suggestion": "manual fix needed",
                    "actionable": False,
                }
            ]
        }

        result = retry_workflow._extract_auto_fixes(corrections)

        assert result == {}

    def test_session_description_not_auto_fixable(self, retry_workflow):
        """Test that session_description is not auto-fixed (lines 710-712)."""
        corrections = {
            "suggestions": [
                {
                    "issue": "session_description is too short",
                    "suggestion": "Needs longer description",
                    "actionable": True,
                }
            ]
        }

        result = retry_workflow._extract_auto_fixes(corrections)

        # Should not auto-fix session_description
        assert "session_description" not in result

    def test_empty_suggestions(self, retry_workflow):
        """Test empty suggestions."""
        corrections = {"suggestions": []}

        result = retry_workflow._extract_auto_fixes(corrections)

        assert result == {}

    def test_missing_suggestions_key(self, retry_workflow):
        """Test missing suggestions key."""
        corrections = {}

        result = retry_workflow._extract_auto_fixes(corrections)

        assert result == {}
