"""
Unit tests for Session Initialization Endpoint (Task 2.3).

Tests cover:
- POST /api/v1/sessions/initialize with valid path
- Response includes session_id
- Response includes workflow_stage
- Session context created in storage
- Message sent to conversation agent
- Error handling for invalid dataset path
- Error handling when conversation agent not registered
- Error handling for message routing failure

Following TDD: These tests should FAIL initially (RED phase),
then PASS after implementation (GREEN phase).
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.api.sessions import router
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter
from agentic_neurodata_conversion.models import (
    SessionInitializeResponse,
    WorkflowStage,
)

pytestmark = pytest.mark.unit


class TestSessionInitializeEndpoint:
    """Test POST /api/v1/sessions/initialize endpoint."""

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
        mock_cm.create_session = AsyncMock()
        mock_cm.get_session = AsyncMock()
        return mock_cm

    @pytest.fixture
    def mock_agent_registry(self) -> AgentRegistry:
        """Create mock agent registry with conversation agent."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="conversation_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["initialize_session"],
        )
        return registry

    @pytest.fixture
    def mock_message_router(self) -> Mock:
        """Create mock message router."""
        mock_router = Mock(spec=MessageRouter)
        mock_router.execute_agent_task = AsyncMock(
            return_value={"status": "success", "result": {}}
        )
        return mock_router

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
    def valid_dataset_path(self, tmp_path: Path) -> str:
        """Create a valid dataset directory path."""
        dataset_dir = tmp_path / "test_dataset"
        dataset_dir.mkdir()
        # Create a dummy file to make it look like a dataset
        (dataset_dir / "structure.oebin").write_text("{}")
        return str(dataset_dir)

    def test_initialize_session_with_valid_path(
        self, client: TestClient, valid_dataset_path: str
    ) -> None:
        """Test POST /api/v1/sessions/initialize with valid dataset path."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        assert response.status_code == 200

    def test_response_includes_session_id(
        self, client: TestClient, valid_dataset_path: str
    ) -> None:
        """Test response includes session_id field."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        data = response.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        # Verify it's a valid UUID
        uuid.UUID(data["session_id"])

    def test_response_includes_workflow_stage(
        self, client: TestClient, valid_dataset_path: str
    ) -> None:
        """Test response includes workflow_stage field."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        data = response.json()
        assert "workflow_stage" in data
        assert data["workflow_stage"] == WorkflowStage.INITIALIZED

    def test_response_includes_message(
        self, client: TestClient, valid_dataset_path: str
    ) -> None:
        """Test response includes user-friendly message."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    def test_session_context_created_in_storage(
        self,
        client: TestClient,
        valid_dataset_path: str,
        mock_context_manager: Mock,
    ) -> None:
        """Test that session context is created in context manager."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        assert response.status_code == 200

        # Verify create_session was called
        mock_context_manager.create_session.assert_called_once()

        # Verify the session context passed to create_session
        call_args = mock_context_manager.create_session.call_args
        session_context = call_args[0][0]
        assert session_context.workflow_stage == WorkflowStage.INITIALIZED
        assert session_context.dataset_info is not None
        assert session_context.dataset_info.dataset_path == valid_dataset_path

    def test_message_sent_to_conversation_agent(
        self,
        client: TestClient,
        valid_dataset_path: str,
        mock_message_router: Mock,
    ) -> None:
        """Test that message is sent to conversation agent via message router."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        assert response.status_code == 200

        # Verify execute_agent_task was called
        mock_message_router.execute_agent_task.assert_called_once()

        # Verify the call parameters
        call_args = mock_message_router.execute_agent_task.call_args
        assert call_args.kwargs["target_agent"] == "conversation_agent"
        assert call_args.kwargs["task_name"] == "initialize_session"
        assert "session_id" in call_args.kwargs
        assert call_args.kwargs["parameters"]["dataset_path"] == valid_dataset_path

    def test_error_handling_for_invalid_dataset_path(self, client: TestClient) -> None:
        """Test error handling when dataset path doesn't exist."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": "/nonexistent/path/to/dataset"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert (
            "not found" in data["detail"].lower()
            or "does not exist" in data["detail"].lower()
        )

    def test_error_handling_for_dataset_path_not_directory(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Test error handling when dataset path is a file, not a directory."""
        # Create a file instead of directory
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("test")

        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": str(file_path)},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "directory" in data["detail"].lower()

    def test_error_handling_when_conversation_agent_not_registered(
        self,
        app: FastAPI,
        mock_context_manager: Mock,
        mock_message_router: Mock,
        valid_dataset_path: str,
    ) -> None:
        """Test error handling when conversation agent is not registered."""
        # Create registry WITHOUT conversation agent
        empty_registry = AgentRegistry()

        app.state.context_manager = mock_context_manager
        app.state.agent_registry = empty_registry
        app.state.message_router = mock_message_router

        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "conversation_agent" in data["detail"].lower()

    def test_error_handling_for_message_routing_failure(
        self,
        client: TestClient,
        valid_dataset_path: str,
        mock_message_router: Mock,
    ) -> None:
        """Test error handling when message routing fails."""
        # Make message router raise an exception
        mock_message_router.execute_agent_task.side_effect = Exception(
            "Connection refused"
        )

        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_response_model_validation(
        self, client: TestClient, valid_dataset_path: str
    ) -> None:
        """Test that response conforms to SessionInitializeResponse model."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        data = response.json()

        # Validate against model
        init_response = SessionInitializeResponse(**data)
        assert init_response.session_id is not None
        assert init_response.workflow_stage == WorkflowStage.INITIALIZED
        assert init_response.message is not None

    def test_request_model_validation_missing_dataset_path(
        self, client: TestClient
    ) -> None:
        """Test that request without dataset_path is rejected."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={},
        )
        assert response.status_code == 422  # Validation error

    def test_unique_session_ids_for_multiple_requests(
        self, client: TestClient, valid_dataset_path: str
    ) -> None:
        """Test that each initialization creates a unique session ID."""
        response1 = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        response2 = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        session_id1 = response1.json()["session_id"]
        session_id2 = response2.json()["session_id"]

        assert session_id1 != session_id2

    def test_dataset_info_populated_in_session_context(
        self,
        client: TestClient,
        valid_dataset_path: str,
        mock_context_manager: Mock,
    ) -> None:
        """Test that dataset_info is populated in the session context."""
        response = client.post(
            "/api/v1/sessions/initialize",
            json={"dataset_path": valid_dataset_path},
        )
        assert response.status_code == 200

        # Get the session context that was created
        call_args = mock_context_manager.create_session.call_args
        session_context = call_args[0][0]

        # Verify dataset_info is populated
        assert session_context.dataset_info is not None
        assert session_context.dataset_info.dataset_path == valid_dataset_path
        assert session_context.dataset_info.format is not None
        assert session_context.dataset_info.total_size_bytes >= 0
        assert session_context.dataset_info.file_count >= 0
