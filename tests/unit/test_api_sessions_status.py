"""
Unit tests for Session Status Endpoint (Task 2.4).

Tests cover:
- GET /api/v1/sessions/{id}/status with valid session
- Response includes workflow_stage
- Response includes progress_percentage
- Response includes status_message
- Response includes current_agent
- Response includes requires_clarification flag
- 404 error for non-existent session
- Progress calculation for each workflow stage

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
    DatasetInfo,
    SessionContext,
    SessionStatusResponse,
    WorkflowStage,
)

pytestmark = pytest.mark.unit


class TestSessionStatusEndpoint:
    """Test GET /api/v1/sessions/{session_id}/status endpoint."""

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
    def sample_session_initialized(self) -> SessionContext:
        """Create a sample session in INITIALIZED state."""
        return SessionContext(
            session_id="test-session-001",
            workflow_stage=WorkflowStage.INITIALIZED,
            dataset_info=DatasetInfo(
                dataset_path="/data/test",
                format="openephys",
                total_size_bytes=1024000,
                file_count=50,
            ),
        )

    @pytest.fixture
    def sample_session_converting(self) -> SessionContext:
        """Create a sample session in CONVERTING state."""
        return SessionContext(
            session_id="test-session-002",
            workflow_stage=WorkflowStage.CONVERTING,
            current_agent="conversion_agent",
            dataset_info=DatasetInfo(
                dataset_path="/data/test",
                format="openephys",
                total_size_bytes=1024000,
                file_count=50,
            ),
        )

    def test_get_session_status_with_valid_session(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test GET /api/v1/sessions/{id}/status with valid session."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        assert response.status_code == 200

    def test_response_includes_workflow_stage(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test response includes workflow_stage field."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        data = response.json()
        assert "workflow_stage" in data
        assert data["workflow_stage"] == WorkflowStage.INITIALIZED

    def test_response_includes_progress_percentage(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test response includes progress_percentage field."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        data = response.json()
        assert "progress_percentage" in data
        assert isinstance(data["progress_percentage"], int)
        assert 0 <= data["progress_percentage"] <= 100

    def test_response_includes_status_message(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test response includes status_message field."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        data = response.json()
        assert "status_message" in data
        assert isinstance(data["status_message"], str)
        assert len(data["status_message"]) > 0

    def test_response_includes_current_agent(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_converting: SessionContext,
    ) -> None:
        """Test response includes current_agent field."""
        mock_context_manager.get_session.return_value = sample_session_converting

        response = client.get("/api/v1/sessions/test-session-002/status")
        data = response.json()
        assert "current_agent" in data
        # Can be None or a string
        if data["current_agent"] is not None:
            assert isinstance(data["current_agent"], str)

    def test_response_includes_requires_clarification(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test response includes requires_clarification flag."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        data = response.json()
        assert "requires_clarification" in data
        assert isinstance(data["requires_clarification"], bool)

    def test_404_error_for_nonexistent_session(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test 404 error when session doesn't exist."""
        mock_context_manager.get_session.return_value = None

        response = client.get("/api/v1/sessions/nonexistent-session/status")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_progress_calculation_initialized(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test progress is 10% for INITIALIZED stage."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        data = response.json()
        assert data["progress_percentage"] == 10

    def test_progress_calculation_collecting_metadata(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test progress is 25% for COLLECTING_METADATA stage."""
        session = SessionContext(
            session_id="test-session-003",
            workflow_stage=WorkflowStage.COLLECTING_METADATA,
            current_agent="conversation_agent",
        )
        mock_context_manager.get_session.return_value = session

        response = client.get("/api/v1/sessions/test-session-003/status")
        data = response.json()
        assert data["progress_percentage"] == 25

    def test_progress_calculation_converting(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_converting: SessionContext,
    ) -> None:
        """Test progress is 50% for CONVERTING stage."""
        mock_context_manager.get_session.return_value = sample_session_converting

        response = client.get("/api/v1/sessions/test-session-002/status")
        data = response.json()
        assert data["progress_percentage"] == 50

    def test_progress_calculation_evaluating(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test progress is 75% for EVALUATING stage."""
        session = SessionContext(
            session_id="test-session-004",
            workflow_stage=WorkflowStage.EVALUATING,
            current_agent="evaluation_agent",
        )
        mock_context_manager.get_session.return_value = session

        response = client.get("/api/v1/sessions/test-session-004/status")
        data = response.json()
        assert data["progress_percentage"] == 75

    def test_progress_calculation_completed(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test progress is 100% for COMPLETED stage."""
        session = SessionContext(
            session_id="test-session-005",
            workflow_stage=WorkflowStage.COMPLETED,
        )
        mock_context_manager.get_session.return_value = session

        response = client.get("/api/v1/sessions/test-session-005/status")
        data = response.json()
        assert data["progress_percentage"] == 100

    def test_progress_calculation_failed(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test progress calculation for FAILED stage."""
        session = SessionContext(
            session_id="test-session-006",
            workflow_stage=WorkflowStage.FAILED,
        )
        mock_context_manager.get_session.return_value = session

        response = client.get("/api/v1/sessions/test-session-006/status")
        data = response.json()
        # For FAILED, progress should reflect where it failed (use some reasonable value)
        assert 0 <= data["progress_percentage"] <= 100

    def test_response_model_validation(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test that response conforms to SessionStatusResponse model."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        data = response.json()

        # Validate against model
        status_response = SessionStatusResponse(**data)
        assert status_response.session_id == "test-session-001"
        assert status_response.workflow_stage == WorkflowStage.INITIALIZED
        assert 0 <= status_response.progress_percentage <= 100

    def test_session_with_clarification_required(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test status response when clarification is required."""
        session = SessionContext(
            session_id="test-session-007",
            workflow_stage=WorkflowStage.COLLECTING_METADATA,
            requires_user_clarification=True,
            clarification_prompt="Please provide species information",
        )
        mock_context_manager.get_session.return_value = session

        response = client.get("/api/v1/sessions/test-session-007/status")
        data = response.json()
        assert data["requires_clarification"] is True
        assert data["clarification_prompt"] == "Please provide species information"

    def test_session_without_clarification_required(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test status response when no clarification is required."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        data = response.json()
        assert data["requires_clarification"] is False
        assert data["clarification_prompt"] is None

    def test_current_agent_populated_when_agent_executing(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_converting: SessionContext,
    ) -> None:
        """Test current_agent is populated when an agent is executing."""
        mock_context_manager.get_session.return_value = sample_session_converting

        response = client.get("/api/v1/sessions/test-session-002/status")
        data = response.json()
        assert data["current_agent"] == "conversion_agent"

    def test_current_agent_none_when_no_agent_executing(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session_initialized: SessionContext,
    ) -> None:
        """Test current_agent is None when no agent is executing."""
        mock_context_manager.get_session.return_value = sample_session_initialized

        response = client.get("/api/v1/sessions/test-session-001/status")
        data = response.json()
        assert data["current_agent"] is None
