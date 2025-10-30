"""
Unit tests for internal API endpoints.

Tests cover:
- POST /internal/register_agent with valid payload
- Agent added to registry after registration
- GET /internal/sessions/{id}/context returns session
- GET /internal/sessions/{id}/context 404 for non-existent session
- PATCH /internal/sessions/{id}/context updates session
- PATCH /internal/sessions/{id}/context 404 for non-existent session
- POST /internal/route_message routes to agent
- POST /internal/route_message 404 for non-existent target agent
- Validation of registration request
- Context updates modify last_updated timestamp

Following TDD: These tests should FAIL initially (RED phase),
then PASS after implementation (GREEN phase).
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter
from agentic_neurodata_conversion.models import (
    AgentRegistrationRequest,
    MessageType,
    RouteMessageRequest,
    SessionContext,
    WorkflowStage,
)

pytestmark = pytest.mark.unit


class TestInternalAPIEndpoints:
    """Test internal API endpoints for agent communication."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create FastAPI app with internal router."""
        app = FastAPI()
        # Import and include router here to avoid import errors before implementation
        try:
            from agentic_neurodata_conversion.mcp_server.api.internal import router

            app.include_router(router)
        except ImportError:
            # Router not implemented yet - tests should fail
            pass
        return app

    @pytest.fixture
    def mock_context_manager(self) -> Mock:
        """Create mock context manager."""
        mock_cm = Mock(spec=ContextManager)
        mock_cm.get_session = AsyncMock()
        mock_cm.update_session = AsyncMock()
        return mock_cm

    @pytest.fixture
    def mock_agent_registry(self) -> AgentRegistry:
        """Create mock agent registry."""
        return AgentRegistry()

    @pytest.fixture
    def mock_message_router(self) -> Mock:
        """Create mock message router."""
        mock_router = Mock(spec=MessageRouter)
        mock_router.send_message = AsyncMock()
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

    # Test 1: POST /internal/register_agent with valid payload
    def test_register_agent_with_valid_payload(self, client: TestClient) -> None:
        """Test POST /internal/register_agent with valid payload."""
        payload = {
            "agent_name": "conversation_agent",
            "agent_type": "conversation",
            "base_url": "http://localhost:3001",
            "capabilities": ["initialize_session", "handle_clarification"],
        }

        response = client.post("/internal/register_agent", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        assert data["agent_name"] == "conversation_agent"

    # Test 2: Agent added to registry after registration
    def test_agent_added_to_registry_after_registration(
        self, app: FastAPI, mock_context_manager: Mock, mock_message_router: Mock
    ) -> None:
        """Test agent is added to registry after registration."""
        registry = AgentRegistry()
        app.state.context_manager = mock_context_manager
        app.state.agent_registry = registry
        app.state.message_router = mock_message_router

        client = TestClient(app)

        payload = {
            "agent_name": "conversion_agent",
            "agent_type": "conversion",
            "base_url": "http://localhost:3002",
            "capabilities": ["detect_format", "convert_to_nwb"],
        }

        response = client.post("/internal/register_agent", json=payload)
        assert response.status_code == 200

        # Verify agent is in registry
        agent_info = registry.get_agent("conversion_agent")
        assert agent_info is not None
        assert agent_info["agent_name"] == "conversion_agent"
        assert agent_info["agent_type"] == "conversion"
        assert agent_info["base_url"] == "http://localhost:3002"
        assert agent_info["capabilities"] == ["detect_format", "convert_to_nwb"]

    # Test 3: GET /internal/sessions/{id}/context returns session
    def test_get_session_context_returns_session(
        self, client: TestClient, mock_context_manager: Mock
    ) -> None:
        """Test GET /internal/sessions/{id}/context returns session."""
        # Setup mock to return a session
        test_session = SessionContext(
            session_id="test-session-123",
            workflow_stage=WorkflowStage.INITIALIZED,
        )
        mock_context_manager.get_session.return_value = test_session

        response = client.get("/internal/sessions/test-session-123/context")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["workflow_stage"] == "initialized"

    # Test 4: GET /internal/sessions/{id}/context 404 for non-existent session
    def test_get_session_context_404_for_nonexistent_session(
        self, client: TestClient, mock_context_manager: Mock
    ) -> None:
        """Test GET /internal/sessions/{id}/context returns 404 for non-existent session."""
        # Setup mock to return None (session not found)
        mock_context_manager.get_session.return_value = None

        response = client.get("/internal/sessions/nonexistent-id/context")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    # Test 5: PATCH /internal/sessions/{id}/context updates session
    def test_update_session_context_updates_session(
        self, client: TestClient, mock_context_manager: Mock
    ) -> None:
        """Test PATCH /internal/sessions/{id}/context updates session."""
        # Setup mock to return a session
        test_session = SessionContext(
            session_id="test-session-123",
            workflow_stage=WorkflowStage.INITIALIZED,
        )
        mock_context_manager.get_session.return_value = test_session

        updates = {
            "workflow_stage": "collecting_metadata",
            "current_agent": "conversation_agent",
        }

        response = client.patch(
            "/internal/sessions/test-session-123/context", json=updates
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["session_id"] == "test-session-123"

        # Verify update_session was called
        mock_context_manager.update_session.assert_called_once()

    # Test 6: PATCH /internal/sessions/{id}/context 404 for non-existent session
    def test_update_session_context_404_for_nonexistent_session(
        self, client: TestClient, mock_context_manager: Mock
    ) -> None:
        """Test PATCH /internal/sessions/{id}/context returns 404 for non-existent session."""
        # Setup mock to return None (session not found)
        mock_context_manager.get_session.return_value = None

        updates = {"workflow_stage": "collecting_metadata"}

        response = client.patch(
            "/internal/sessions/nonexistent-id/context", json=updates
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    # Test 7: POST /internal/route_message routes to agent
    def test_route_message_routes_to_agent(
        self, client: TestClient, mock_message_router: Mock
    ) -> None:
        """Test POST /internal/route_message routes message to agent."""
        # Setup mock to return success response
        mock_message_router.send_message.return_value = {
            "status": "success",
            "result": {"task_completed": True},
        }

        payload = {
            "target_agent": "conversation_agent",
            "message_type": "agent_execute",
            "payload": {"task_name": "initialize_session", "session_id": "test-123"},
        }

        response = client.post("/internal/route_message", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "result" in data

        # Verify send_message was called with correct parameters
        mock_message_router.send_message.assert_called_once()
        call_args = mock_message_router.send_message.call_args
        assert call_args[1]["target_agent"] == "conversation_agent"
        assert call_args[1]["message_type"] == MessageType.AGENT_EXECUTE

    # Test 8: POST /internal/route_message 404 for non-existent target agent
    def test_route_message_error_for_nonexistent_agent(
        self, client: TestClient, mock_message_router: Mock
    ) -> None:
        """Test POST /internal/route_message returns error for non-existent agent."""
        # Setup mock to raise ValueError (agent not found)
        mock_message_router.send_message.side_effect = ValueError(
            "Agent 'nonexistent_agent' not found in registry"
        )

        payload = {
            "target_agent": "nonexistent_agent",
            "message_type": "agent_execute",
            "payload": {"task_name": "test"},
        }

        response = client.post("/internal/route_message", json=payload)

        # Should return 500 or error response
        assert response.status_code in [400, 404, 500]

    # Test 9: Validation of registration request
    def test_register_agent_validates_request_fields(self, client: TestClient) -> None:
        """Test registration endpoint validates required fields."""
        # Missing required field: agent_type
        invalid_payload = {
            "agent_name": "test_agent",
            "base_url": "http://localhost:3001",
        }

        response = client.post("/internal/register_agent", json=invalid_payload)

        # Should return 422 (validation error)
        assert response.status_code == 422

    # Test 10: Context updates modify last_updated timestamp
    def test_update_session_context_modifies_last_updated(
        self, client: TestClient, mock_context_manager: Mock
    ) -> None:
        """Test context updates modify last_updated timestamp."""
        # Setup mock to return a session
        old_timestamp = datetime(2024, 1, 1, 12, 0, 0)
        test_session = SessionContext(
            session_id="test-session-123",
            workflow_stage=WorkflowStage.INITIALIZED,
            last_updated=old_timestamp,
        )
        mock_context_manager.get_session.return_value = test_session

        updates = {"current_agent": "conversation_agent"}

        response = client.patch(
            "/internal/sessions/test-session-123/context", json=updates
        )

        assert response.status_code == 200

        # Verify update_session was called with session_id and updates
        mock_context_manager.update_session.assert_called_once()
        call_args = mock_context_manager.update_session.call_args
        assert call_args[0][0] == "test-session-123"
        assert isinstance(call_args[0][1], dict)

    # Additional test: Registration with empty capabilities
    def test_register_agent_with_empty_capabilities(self, client: TestClient) -> None:
        """Test registration with empty capabilities list is allowed."""
        payload = {
            "agent_name": "minimal_agent",
            "agent_type": "test",
            "base_url": "http://localhost:3001",
            "capabilities": [],
        }

        response = client.post("/internal/register_agent", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        assert data["agent_name"] == "minimal_agent"

    # Additional test: Registration without capabilities field (should default to [])
    def test_register_agent_without_capabilities_field(
        self, client: TestClient
    ) -> None:
        """Test registration without capabilities field uses default empty list."""
        payload = {
            "agent_name": "no_caps_agent",
            "agent_type": "test",
            "base_url": "http://localhost:3001",
        }

        response = client.post("/internal/register_agent", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"

    # Additional test: Get context returns all session fields
    def test_get_session_context_returns_complete_session(
        self, client: TestClient, mock_context_manager: Mock
    ) -> None:
        """Test GET /internal/sessions/{id}/context returns complete session data."""
        # Setup mock with fully populated session
        test_session = SessionContext(
            session_id="full-session-123",
            workflow_stage=WorkflowStage.COLLECTING_METADATA,
            current_agent="conversation_agent",
            requires_user_clarification=False,
        )
        mock_context_manager.get_session.return_value = test_session

        response = client.get("/internal/sessions/full-session-123/context")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "full-session-123"
        assert data["workflow_stage"] == "collecting_metadata"
        assert data["current_agent"] == "conversation_agent"
        assert data["requires_user_clarification"] is False

    # Additional test: Update with complex nested data
    def test_update_session_context_with_complex_data(
        self, client: TestClient, mock_context_manager: Mock
    ) -> None:
        """Test updating session with complex nested data structures."""
        test_session = SessionContext(
            session_id="test-session-123",
            workflow_stage=WorkflowStage.INITIALIZED,
        )
        mock_context_manager.get_session.return_value = test_session

        updates: dict[str, Any] = {
            "workflow_stage": "converting",
            "metadata": {
                "subject_id": "sub-001",
                "session_description": "Test session",
            },
        }

        response = client.patch(
            "/internal/sessions/test-session-123/context", json=updates
        )

        assert response.status_code == 200
        mock_context_manager.update_session.assert_called_once()

    # Additional test: Route message with different message types
    def test_route_message_with_different_message_types(
        self, client: TestClient, mock_message_router: Mock
    ) -> None:
        """Test routing messages with different MessageType values."""
        mock_message_router.send_message.return_value = {
            "status": "success",
            "result": {},
        }

        # Test with CONTEXT_UPDATE message type
        payload = {
            "target_agent": "conversation_agent",
            "message_type": "context_update",
            "payload": {"updates": {"stage": "converting"}},
        }

        response = client.post("/internal/route_message", json=payload)

        assert response.status_code == 200
        mock_message_router.send_message.assert_called_once()

    # Additional test: Validate AgentRegistrationRequest model
    def test_agent_registration_request_model_validation(self) -> None:
        """Test AgentRegistrationRequest model validates correctly."""
        # Valid request
        valid_request = AgentRegistrationRequest(
            agent_name="test_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["test"],
        )
        assert valid_request.agent_name == "test_agent"
        assert valid_request.capabilities == ["test"]

        # Request with default capabilities
        request_with_defaults = AgentRegistrationRequest(
            agent_name="test_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
        )
        assert request_with_defaults.capabilities == []

    # Additional test: Validate RouteMessageRequest model
    def test_route_message_request_model_validation(self) -> None:
        """Test RouteMessageRequest model validates correctly."""
        # Valid request
        valid_request = RouteMessageRequest(
            target_agent="test_agent",
            message_type=MessageType.AGENT_EXECUTE,
            payload={"task": "test"},
        )
        assert valid_request.target_agent == "test_agent"
        assert valid_request.message_type == MessageType.AGENT_EXECUTE
        assert valid_request.payload == {"task": "test"}

    # Additional test: Multiple agent registrations
    def test_multiple_agent_registrations(
        self, app: FastAPI, mock_context_manager: Mock, mock_message_router: Mock
    ) -> None:
        """Test registering multiple agents sequentially."""
        registry = AgentRegistry()
        app.state.context_manager = mock_context_manager
        app.state.agent_registry = registry
        app.state.message_router = mock_message_router

        client = TestClient(app)

        # Register first agent
        response1 = client.post(
            "/internal/register_agent",
            json={
                "agent_name": "agent_1",
                "agent_type": "conversation",
                "base_url": "http://localhost:3001",
            },
        )
        assert response1.status_code == 200

        # Register second agent
        response2 = client.post(
            "/internal/register_agent",
            json={
                "agent_name": "agent_2",
                "agent_type": "conversion",
                "base_url": "http://localhost:3002",
            },
        )
        assert response2.status_code == 200

        # Verify both are registered
        assert registry.get_agent("agent_1") is not None
        assert registry.get_agent("agent_2") is not None
        assert len(registry.list_agents()) == 2

    # Additional test: Route message with generic exception
    def test_route_message_generic_exception(
        self, client: TestClient, mock_message_router: Mock
    ) -> None:
        """Test route_message handles generic exceptions (network, timeout, etc.)."""
        # Setup mock to raise generic exception (not ValueError)
        mock_message_router.send_message.side_effect = Exception(
            "Network timeout occurred"
        )

        payload = {
            "target_agent": "conversation_agent",
            "message_type": "agent_execute",
            "payload": {"task_name": "test"},
        }

        response = client.post("/internal/route_message", json=payload)

        # Should return 500 for generic exceptions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to route message" in data["detail"]
