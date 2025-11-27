"""Unit tests for validation router endpoints.

Tests validation, retry approval, and improvement decision endpoints
with focus on error handling and edge cases.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentic_neurodata_conversion.api.routers.validation import router
from agentic_neurodata_conversion.models import (
    ConversionStatus,
    LogEntry,
    MCPResponse,
)

# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_server_with_logs():
    """Mock MCP server with sample logs for correction context."""
    mock_server = Mock()
    mock_state = Mock()

    # Create sample logs with LogEntry objects
    logs = [
        LogEntry(
            level="info",
            message="LLM correction guidance available",
            context={
                "suggestions": [
                    {
                        "issue": "Missing experimenter",
                        "suggestion": "Add experimenter name",
                        "severity": "error",
                        "actionable": True,
                    },
                    {
                        "issue": "Missing keywords",
                        "suggestion": "Provide keywords",
                        "severity": "warning",
                        "actionable": False,
                    },
                ]
            },
        ),
        LogEntry(
            level="info",
            message="Validation completed",
            context={"overall_status": "FAILED", "summary": {"error": 5, "warning": 2}},
        ),
    ]

    mock_state.logs = logs
    mock_state.correction_attempt = 1
    mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
    mock_state.metadata = {}
    mock_server.global_state = mock_state

    return mock_server


@pytest.fixture
def mock_mcp_server_empty():
    """Mock MCP server with no logs."""
    mock_server = Mock()
    mock_state = Mock()
    mock_state.logs = []
    mock_state.correction_attempt = 0
    mock_state.status = ConversionStatus.IDLE
    mock_state.metadata = {}
    mock_server.global_state = mock_state
    return mock_server


@pytest.fixture
def mock_mcp_server_with_validation():
    """Mock MCP server with validation result in metadata."""
    mock_server = Mock()
    mock_state = Mock()
    mock_state.logs = []
    mock_state.correction_attempt = 0
    mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
    mock_state.metadata = {
        "last_validation_result": {
            "summary": {"CRITICAL": 2, "ERROR": 3, "WARNING": 1},
            "issues": [
                {"severity": "CRITICAL", "check_name": "check_1", "message": "Critical issue 1"},
                {"severity": "CRITICAL", "check_name": "check_2", "message": "Critical issue 2"},
                {"severity": "ERROR", "check_name": "check_3", "message": "Error issue"},
                {"severity": "WARNING", "check_name": "check_4", "message": "Warning issue"},
            ],
        }
    }
    mock_server.global_state = mock_state
    return mock_server


# ============================================================================
# GET /api/validation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestGetValidationResults:
    """Test GET /api/validation endpoint."""

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_get_validation_results_returns_mvp_response(self, mock_get_server):
        """Test that MVP implementation returns simplified validation info."""
        mock_get_server.return_value = Mock()

        response = client.get("/api/validation")

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["issues"] == []
        assert data["summary"] == {"critical": 0, "error": 0, "warning": 0, "info": 0}


# ============================================================================
# GET /api/correction-context Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestGetCorrectionContext:
    """Test GET /api/correction-context endpoint."""

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_no_context_when_no_logs(self, mock_get_server, mock_mcp_server_empty):
        """Test response when no correction context is available."""
        mock_get_server.return_value = mock_mcp_server_empty

        response = client.get("/api/correction-context")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_context"
        assert data["message"] == "No correction context available"
        assert data["auto_fixable"] == []
        assert data["user_input_required"] == []

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_extracts_context_from_llm_guidance(self, mock_get_server, mock_mcp_server_with_logs):
        """Test extraction of correction context from LLM guidance logs."""
        mock_get_server.return_value = mock_mcp_server_with_logs

        response = client.get("/api/correction-context")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "available"
        assert data["correction_attempt"] == 1
        assert data["can_retry"] is True

        # Check auto-fixable issues (actionable=True)
        assert len(data["auto_fixable"]) == 1
        assert data["auto_fixable"][0]["issue"] == "Missing experimenter"
        assert data["auto_fixable"][0]["severity"] == "error"

        # Check user input required (actionable=False)
        assert len(data["user_input_required"]) == 1
        assert data["user_input_required"][0]["issue"] == "Missing keywords"

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_extracts_validation_result_from_logs(self, mock_get_server):
        """Test extraction of validation results from logs."""
        mock_server = Mock()
        mock_state = Mock()
        logs = [
            LogEntry(
                level="info",
                message="Validation results available",
                context={"overall_status": "FAILED", "summary": {"error": 3, "warning": 1}},
            )
        ]
        mock_state.logs = logs
        mock_state.correction_attempt = 2
        mock_state.metadata = {}
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/correction-context")

        assert response.status_code == 200
        data = response.json()
        assert data["validation_summary"] == {"error": 3, "warning": 1}

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_fallback_to_validation_result_when_no_suggestions(self, mock_get_server):
        """Test fallback to validation result when no specific suggestions."""
        mock_server = Mock()
        mock_state = Mock()
        logs = [
            LogEntry(
                level="info",
                message="Validation completed",
                context={"overall_status": "FAILED", "summary": {"error": 5, "warning": 0}},
            )
        ]
        mock_state.logs = logs
        mock_state.correction_attempt = 0
        mock_state.metadata = {}
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/correction-context")

        assert response.status_code == 200
        data = response.json()
        # Should auto-generate auto_fixable from error count
        assert len(data["auto_fixable"]) == 1
        assert "5 validation errors" in data["auto_fixable"][0]["issue"]
        assert data["auto_fixable"][0]["severity"] == "error"


# ============================================================================
# POST /api/retry-approval Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestRetryApproval:
    """Test POST /api/retry-approval endpoint."""

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_retry_approval_success(self, mock_get_server):
        """Test successful retry approval."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.CONVERTING
        mock_state.metadata = {}
        mock_server.global_state = mock_state

        mock_response = MCPResponse(
            success=True,
            reply_to="test-msg-id",
            result={"status": "analyzing_corrections", "message": "Retry approved"},
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/retry-approval", json={"decision": "approve"})

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        assert data["message"] == "Retry approved"
        assert "new_status" in data

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_retry_approval_failure_without_validation(self, mock_get_server):
        """Test retry approval failure without validation result in metadata."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.FAILED
        mock_state.metadata = {}  # No last_validation_result
        mock_server.global_state = mock_state

        mock_response = MCPResponse(
            success=False, reply_to="test-msg-id", error={"message": "Retry failed", "error_code": "RETRY_ERROR"}
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/retry-approval", json={"decision": "approve"})

        assert response.status_code == 400
        data = response.json()
        assert "message" in data["detail"]
        assert data["detail"]["error_code"] == "RETRY_ERROR"

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_retry_approval_failure_with_validation(self, mock_get_server, mock_mcp_server_with_validation):
        """Test retry approval failure with validation result in metadata."""
        mock_response = MCPResponse(
            success=False, reply_to="test-msg-id", error={"message": "Retry failed", "error_code": "RETRY_ERROR"}
        )
        mock_mcp_server_with_validation.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_mcp_server_with_validation

        response = client.post("/api/retry-approval", json={"decision": "approve"})

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["message"] == "Retry failed"
        assert "validation_summary" in data["detail"]
        assert data["detail"]["validation_summary"]["CRITICAL"] == 2

        # Should include critical issues (top 5)
        assert "critical_issues" in data["detail"]
        critical_issues = data["detail"]["critical_issues"]
        assert len(critical_issues) == 3  # 2 CRITICAL + 1 ERROR from top 5
        assert critical_issues[0]["severity"] == "CRITICAL"

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_retry_approval_with_error_context(self, mock_get_server):
        """Test retry approval failure with additional error context."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.FAILED
        mock_state.metadata = {}
        mock_server.global_state = mock_state

        mock_response = MCPResponse(
            success=False,
            reply_to="test-msg-id",
            error={
                "message": "Retry failed",
                "error_code": "RETRY_ERROR",
                "error_context": {"details": "Additional context"},
            },
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/retry-approval", json={"decision": "approve"})

        assert response.status_code == 400
        assert "context" in response.json()["detail"]
        assert response.json()["detail"]["context"]["details"] == "Additional context"

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_retry_approval_status_mapping(self, mock_get_server):
        """Test status mapping for different response statuses."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
        mock_state.metadata = {}
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        # Test "failed" status
        mock_response = MCPResponse(
            success=True, reply_to="test-msg-id", result={"status": "failed", "message": "Conversion failed"}
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)

        response = client.post("/api/retry-approval", json={"decision": "reject"})
        assert response.status_code == 200
        assert response.json()["new_status"] == "failed"

        # Test "analyzing_corrections" status
        mock_response = MCPResponse(
            success=True, reply_to="test-msg-id", result={"status": "analyzing_corrections", "message": "Analyzing"}
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)

        response = client.post("/api/retry-approval", json={"decision": "approve"})
        assert response.status_code == 200
        assert response.json()["new_status"] == "converting"

        # Test "awaiting_corrections" status
        mock_response = MCPResponse(
            success=True, reply_to="test-msg-id", result={"status": "awaiting_corrections", "message": "Awaiting"}
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)

        response = client.post("/api/retry-approval", json={"decision": "approve"})
        assert response.status_code == 200
        assert response.json()["new_status"] == "awaiting_user_input"

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_retry_approval_unknown_status_preserves_current(self, mock_get_server):
        """Test that unknown status preserves current state status."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.CONVERTING
        mock_state.metadata = {}
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        mock_response = MCPResponse(
            success=True, reply_to="test-msg-id", result={"status": "unknown_status", "message": "Unknown"}
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)

        response = client.post("/api/retry-approval", json={"decision": "approve"})

        assert response.status_code == 200
        # Should preserve current status (CONVERTING)
        assert response.json()["new_status"] == "converting"


# ============================================================================
# POST /api/improvement-decision Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestImprovementDecision:
    """Test POST /api/improvement-decision endpoint."""

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_improvement_decision_accept(self, mock_get_server):
        """Test accepting file with warnings."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.COMPLETED
        mock_state.metadata = {}
        mock_server.global_state = mock_state

        mock_response = MCPResponse(success=True, reply_to="test-msg-id", result={"message": "File accepted"})
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/improvement-decision", data={"decision": "accept"})

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True
        assert data["message"] == "File accepted"
        assert data["status"] == "completed"

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_improvement_decision_improve(self, mock_get_server):
        """Test choosing to improve file."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.CONVERTING
        mock_state.metadata = {}
        mock_server.global_state = mock_state

        mock_response = MCPResponse(success=True, reply_to="test-msg-id", result={"message": "Starting improvement"})
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/improvement-decision", data={"decision": "improve"})

        assert response.status_code == 200
        data = response.json()
        assert data["accepted"] is True

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_improvement_decision_invalid_value(self, mock_get_server):
        """Test invalid decision value."""
        mock_get_server.return_value = Mock()

        response = client.post("/api/improvement-decision", data={"decision": "invalid"})

        assert response.status_code == 400
        assert "must be 'improve' or 'accept'" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_improvement_decision_failure_without_validation(self, mock_get_server):
        """Test improvement decision failure without validation result."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.FAILED
        mock_state.metadata = {}  # No validation result
        mock_server.global_state = mock_state

        mock_response = MCPResponse(
            success=False, reply_to="test-msg-id", error={"message": "Decision failed", "error_code": "DECISION_ERROR"}
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/improvement-decision", data={"decision": "accept"})

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["message"] == "Decision failed"
        assert data["detail"]["error_code"] == "DECISION_ERROR"

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_improvement_decision_failure_with_validation(self, mock_get_server):
        """Test improvement decision failure with validation result."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.FAILED
        mock_state.metadata = {
            "last_validation_result": {
                "summary": {"WARNING": 5, "INFO": 3, "BEST_PRACTICE": 2},
                "issues": [
                    {"severity": "WARNING", "check_name": "warn_1", "message": "Warning 1"},
                    {"severity": "WARNING", "check_name": "warn_2", "message": "Warning 2"},
                    {"severity": "INFO", "check_name": "info_1", "message": "Info 1"},
                    {"severity": "BEST_PRACTICE", "check_name": "bp_1", "message": "BP 1"},
                ],
            }
        }
        mock_server.global_state = mock_state

        mock_response = MCPResponse(
            success=False, reply_to="test-msg-id", error={"message": "Decision failed", "error_code": "DECISION_ERROR"}
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/improvement-decision", data={"decision": "improve"})

        assert response.status_code == 500
        data = response.json()
        assert "validation_summary" in data["detail"]
        assert data["detail"]["validation_summary"]["WARNING"] == 5

        # Should include warning issues (not critical, since this is PASSED_WITH_ISSUES)
        assert "warning_issues" in data["detail"]
        warning_issues = data["detail"]["warning_issues"]
        assert len(warning_issues) == 4  # All warnings/info/bp (≤ 10)
        assert all(issue["severity"] in ["WARNING", "BEST_PRACTICE", "INFO"] for issue in warning_issues)

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_improvement_decision_with_error_context(self, mock_get_server):
        """Test improvement decision failure with additional error context."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = ConversionStatus.FAILED
        mock_state.metadata = {}
        mock_server.global_state = mock_state

        mock_response = MCPResponse(
            success=False,
            reply_to="test-msg-id",
            error={
                "message": "Decision failed",
                "error_code": "DECISION_ERROR",
                "error_context": {"reason": "Some specific reason"},
            },
        )
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/improvement-decision", data={"decision": "accept"})

        assert response.status_code == 500
        assert "context" in response.json()["detail"]
        assert response.json()["detail"]["context"]["reason"] == "Some specific reason"

    @patch("agentic_neurodata_conversion.api.routers.validation.get_or_create_mcp_server")
    def test_improvement_decision_with_none_status(self, mock_get_server):
        """Test improvement decision when state status is None."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.status = None  # None status
        mock_state.metadata = {}
        mock_server.global_state = mock_state

        mock_response = MCPResponse(success=True, reply_to="test-msg-id", result={"message": "Decision accepted"})
        mock_server.send_message = AsyncMock(return_value=mock_response)
        mock_get_server.return_value = mock_server

        response = client.post("/api/improvement-decision", data={"decision": "accept"})

        assert response.status_code == 200
        assert response.json()["status"] == "unknown"
