"""
Unit tests for Session Clarification Endpoint (Task 2.5).

Tests cover:
- POST /api/v1/sessions/{id}/clarify with user input
- Response includes acknowledgment message
- Response includes updated workflow_stage
- Message sent to conversation agent
- user_input passed in message payload
- updated_metadata passed in message payload
- 404 error for non-existent session
- Error handling for message routing failure

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
    SessionClarifyResponse,
    SessionContext,
    WorkflowStage,
)

pytestmark = pytest.mark.unit


class TestSessionClarifyEndpoint:
    """Test POST /api/v1/sessions/{session_id}/clarify endpoint."""

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
        """Create mock agent registry with conversation agent."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="conversation_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["handle_clarification"],
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
    def sample_session(self) -> SessionContext:
        """Create a sample session requiring clarification."""
        return SessionContext(
            session_id="test-session-001",
            workflow_stage=WorkflowStage.COLLECTING_METADATA,
            requires_user_clarification=True,
            clarification_prompt="Please provide species information",
            dataset_info=DatasetInfo(
                dataset_path="/data/test",
                format="openephys",
                total_size_bytes=1024000,
                file_count=50,
            ),
        )

    def test_clarify_session_with_user_input(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test POST /api/v1/sessions/{id}/clarify with user input."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Species is Mus musculus"},
        )
        assert response.status_code == 200

    def test_response_includes_acknowledgment_message(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test response includes acknowledgment message."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Species is Mus musculus"},
        )
        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    def test_response_includes_workflow_stage(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test response includes updated workflow_stage."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Species is Mus musculus"},
        )
        data = response.json()
        assert "workflow_stage" in data
        assert isinstance(data["workflow_stage"], str)

    def test_message_sent_to_conversation_agent(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        mock_message_router: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test that message is sent to conversation agent."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Species is Mus musculus"},
        )
        assert response.status_code == 200

        # Verify execute_agent_task was called
        mock_message_router.execute_agent_task.assert_called_once()

        # Verify the call parameters
        call_args = mock_message_router.execute_agent_task.call_args
        assert call_args.kwargs["target_agent"] == "conversation_agent"
        assert call_args.kwargs["task_name"] == "handle_clarification"
        assert call_args.kwargs["session_id"] == "test-session-001"

    def test_user_input_passed_in_message_payload(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        mock_message_router: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test that user_input is passed in message payload."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Species is Mus musculus"},
        )
        assert response.status_code == 200

        # Verify user_input in parameters
        call_args = mock_message_router.execute_agent_task.call_args
        assert call_args.kwargs["parameters"]["user_input"] == "Species is Mus musculus"

    def test_updated_metadata_passed_in_message_payload(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        mock_message_router: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test that updated_metadata is passed in message payload."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={
                "user_input": "Corrected metadata",
                "updated_metadata": {"species": "Mus musculus", "age": "P90"},
            },
        )
        assert response.status_code == 200

        # Verify updated_metadata in parameters
        call_args = mock_message_router.execute_agent_task.call_args
        assert call_args.kwargs["parameters"]["updated_metadata"] == {
            "species": "Mus musculus",
            "age": "P90",
        }

    def test_404_error_for_nonexistent_session(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test 404 error when session doesn't exist."""
        mock_context_manager.get_session.return_value = None

        response = client.post(
            "/api/v1/sessions/nonexistent-session/clarify",
            json={"user_input": "Some input"},
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_error_handling_for_message_routing_failure(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        mock_message_router: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test error handling when message routing fails."""
        mock_context_manager.get_session.return_value = sample_session
        mock_message_router.execute_agent_task.side_effect = Exception(
            "Connection refused"
        )

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Some input"},
        )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_response_model_validation(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test that response conforms to SessionClarifyResponse model."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Species is Mus musculus"},
        )
        data = response.json()

        # Validate against model
        clarify_response = SessionClarifyResponse(**data)
        assert clarify_response.message is not None
        assert clarify_response.workflow_stage is not None

    def test_request_with_only_user_input(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test request with only user_input (no updated_metadata)."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Just text input"},
        )
        assert response.status_code == 200

    def test_request_with_only_updated_metadata(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test request with only updated_metadata (no user_input)."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"updated_metadata": {"species": "Mus musculus"}},
        )
        assert response.status_code == 200

    def test_request_with_both_user_input_and_metadata(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test request with both user_input and updated_metadata."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={
                "user_input": "Updated species info",
                "updated_metadata": {"species": "Mus musculus"},
            },
        )
        assert response.status_code == 200

    def test_workflow_stage_returned_from_session(
        self,
        client: TestClient,
        mock_context_manager: Mock,
        sample_session: SessionContext,
    ) -> None:
        """Test that workflow_stage in response matches session state."""
        mock_context_manager.get_session.return_value = sample_session

        response = client.post(
            "/api/v1/sessions/test-session-001/clarify",
            json={"user_input": "Some input"},
        )
        data = response.json()
        assert data["workflow_stage"] == WorkflowStage.COLLECTING_METADATA

    def test_clarification_for_session_in_different_stages(
        self,
        client: TestClient,
        mock_context_manager: Mock,
    ) -> None:
        """Test clarification works for sessions in different workflow stages."""
        # Test with CONVERTING stage
        session = SessionContext(
            session_id="test-session-002",
            workflow_stage=WorkflowStage.CONVERTING,
            requires_user_clarification=True,
            clarification_prompt="Please confirm output path",
        )
        mock_context_manager.get_session.return_value = session

        response = client.post(
            "/api/v1/sessions/test-session-002/clarify",
            json={"user_input": "Use /output/test.nwb"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_stage"] == WorkflowStage.CONVERTING
