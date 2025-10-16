"""
Unit tests for Session Result Endpoint (Task 2.6).

Tests cover:
- GET /api/v1/sessions/{id}/result with completed session
- Response includes nwb_file_path
- Response includes validation_report_path
- Response includes overall_status
- Response includes LLM summary
- Response includes validation_issues list
- 404 error for non-existent session
- 400 error for incomplete session

Following TDD: These tests should FAIL initially (RED phase),
then PASS after implementation (GREEN phase).
"""

from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.api.sessions import router
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter
from agentic_neurodata_conversion.models import (
    ConversionResults,
    SessionContext,
    SessionResultResponse,
    ValidationIssue,
    ValidationResults,
    WorkflowStage,
)

pytestmark = pytest.mark.unit


class TestSessionResultEndpoint:
    """Test GET /api/v1/sessions/{session_id}/result endpoint."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create FastAPI app with sessions router."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.fixture
    def mock_context_manager(self) -> Mock:
        """Create mock context manager."""
        mock_cm = Mock(spec=ContextManager)
        mock_cm.get_session = AsyncMock()
        return mock_cm

    @pytest.fixture
    def mock_agent_registry(self) -> AgentRegistry:
        """Create mock agent registry."""
        return AgentRegistry()

    @pytest.fixture
    def mock_message_router(self) -> Mock:
        """Create mock message router."""
        return Mock(spec=MessageRouter)

    @pytest.fixture
    def client(
        self,
        app: FastAPI,
        mock_context_manager: Mock,
        mock_agent_registry: AgentRegistry,
        mock_message_router: Mock,
    ) -> TestClient:
        """Create test client with mocked app state."""
        app.state.context_manager = mock_context_manager
        app.state.agent_registry = mock_agent_registry
        app.state.message_router = mock_message_router
        return TestClient(app)

    @pytest.fixture
    def completed_session(self) -> SessionContext:
        """Create a completed session with results."""
        return SessionContext(
            session_id="test-session-001",
            workflow_stage=WorkflowStage.COMPLETED,
            conversion_results=ConversionResults(
                nwb_file_path="/output/test_session.nwb",
                conversion_duration_seconds=45.2,
                conversion_warnings=[],
                conversion_errors=[],
            ),
            validation_results=ValidationResults(
                overall_status="passed",
                issue_count={"critical": 0, "warning": 0, "info": 0},
                issues=[],
                metadata_completeness_score=1.0,
                best_practices_score=0.95,
                validation_report_path="/output/validation_report.json",
                llm_validation_summary="All validation checks passed successfully.",
            ),
            output_nwb_path="/output/test_session.nwb",
            output_report_path="/output/validation_report.json",
        )

    @pytest.fixture
    def completed_session_with_warnings(self) -> SessionContext:
        """Create a completed session with validation warnings."""
        return SessionContext(
            session_id="test-session-002",
            workflow_stage=WorkflowStage.COMPLETED,
            conversion_results=ConversionResults(
                nwb_file_path="/output/test_session2.nwb",
                conversion_duration_seconds=50.1,
                conversion_warnings=["Missing optional metadata field"],
                conversion_errors=[],
            ),
            validation_results=ValidationResults(
                overall_status="passed_with_warnings",
                issue_count={"critical": 0, "warning": 2, "info": 1},
                issues=[
                    ValidationIssue(
                        severity="warning",
                        message="Missing recommended field",
                        location="/NWBFile/experimenter",
                        check_name="check_experimenter",
                    ),
                    ValidationIssue(
                        severity="warning",
                        message="Suboptimal data organization",
                        location="/NWBFile/acquisition",
                        check_name="check_data_organization",
                    ),
                ],
                metadata_completeness_score=0.8,
                best_practices_score=0.75,
                validation_report_path="/output/validation_report2.json",
                llm_validation_summary="Conversion completed with minor warnings.",
            ),
            output_nwb_path="/output/test_session2.nwb",
            output_report_path="/output/validation_report2.json",
        )

    def test_get_result_with_completed_session(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test GET /api/v1/sessions/{id}/result with completed session."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        assert response.status_code == 200

    def test_response_includes_nwb_file_path(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test response includes nwb_file_path."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        data = response.json()
        assert "nwb_file_path" in data
        assert data["nwb_file_path"] == "/output/test_session.nwb"

    def test_response_includes_validation_report_path(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test response includes validation_report_path."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        data = response.json()
        assert "validation_report_path" in data
        assert data["validation_report_path"] == "/output/validation_report.json"

    def test_response_includes_overall_status(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test response includes overall_status."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        data = response.json()
        assert "overall_status" in data
        assert data["overall_status"] == "passed"

    def test_response_includes_llm_summary(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test response includes LLM validation summary."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        data = response.json()
        assert "llm_validation_summary" in data
        assert isinstance(data["llm_validation_summary"], str)
        assert len(data["llm_validation_summary"]) > 0

    def test_response_includes_validation_issues_list(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test response includes validation_issues list."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        data = response.json()
        assert "validation_issues" in data
        assert isinstance(data["validation_issues"], list)

    def test_404_error_for_nonexistent_session(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test 404 error when session doesn't exist."""
        mock_context_manager.get_session.return_value = None

        response = client.get("/api/v1/sessions/nonexistent-session/result")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_400_error_for_incomplete_session(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test 400 error when session is not completed."""
        # Create session in CONVERTING stage (not completed)
        incomplete_session = SessionContext(
            session_id="test-session-003",
            workflow_stage=WorkflowStage.CONVERTING,
        )
        mock_context_manager.get_session.return_value = incomplete_session

        response = client.get("/api/v1/sessions/test-session-003/result")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not completed" in data["detail"].lower()

    def test_response_model_validation(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test that response conforms to SessionResultResponse model."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        data = response.json()

        # Validate against model
        result_response = SessionResultResponse(**data)
        assert result_response.session_id == "test-session-001"
        assert result_response.nwb_file_path == "/output/test_session.nwb"
        assert result_response.overall_status == "passed"

    def test_result_with_validation_warnings(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session_with_warnings: SessionContext,
    ) -> None:
        """Test result response for session with validation warnings."""
        mock_context_manager.get_session.return_value = completed_session_with_warnings

        response = client.get("/api/v1/sessions/test-session-002/result")
        data = response.json()

        assert response.status_code == 200
        assert data["overall_status"] == "passed_with_warnings"
        assert len(data["validation_issues"]) == 2

    def test_validation_issues_include_severity(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session_with_warnings: SessionContext,
    ) -> None:
        """Test that validation issues include severity field."""
        mock_context_manager.get_session.return_value = completed_session_with_warnings

        response = client.get("/api/v1/sessions/test-session-002/result")
        data = response.json()

        for issue in data["validation_issues"]:
            assert "severity" in issue
            assert "message" in issue

    def test_result_for_failed_session(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test result endpoint returns 400 for failed sessions."""
        failed_session = SessionContext(
            session_id="test-session-004",
            workflow_stage=WorkflowStage.FAILED,
        )
        mock_context_manager.get_session.return_value = failed_session

        response = client.get("/api/v1/sessions/test-session-004/result")
        assert response.status_code == 400

    def test_result_includes_session_id_field(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test response includes session_id field."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == "test-session-001"

    def test_validation_issues_empty_for_successful_conversion(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        completed_session: SessionContext,
    ) -> None:
        """Test validation_issues is empty list for successful conversion."""
        mock_context_manager.get_session.return_value = completed_session

        response = client.get("/api/v1/sessions/test-session-001/result")
        data = response.json()
        assert data["validation_issues"] == []

    def test_result_handles_missing_validation_report_path(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test result endpoint handles missing validation_report_path gracefully."""
        session = SessionContext(
            session_id="test-session-005",
            workflow_stage=WorkflowStage.COMPLETED,
            conversion_results=ConversionResults(
                nwb_file_path="/output/test.nwb",
            ),
            validation_results=ValidationResults(
                overall_status="passed",
                issue_count={"critical": 0, "warning": 0, "info": 0},
                issues=[],
                validation_report_path=None,  # No report path
                llm_validation_summary="Validation completed.",
            ),
            output_nwb_path="/output/test.nwb",
        )
        mock_context_manager.get_session.return_value = session

        response = client.get("/api/v1/sessions/test-session-005/result")
        data = response.json()

        # Should still return 200 even if report path is missing
        assert response.status_code == 200
        # validation_report_path field should be present (may be empty string or null)
        assert "validation_report_path" in data
