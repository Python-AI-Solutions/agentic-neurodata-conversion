"""
Unit tests for health check endpoint.

Tests cover:
- GET /health returns 200 status
- Health response includes status field
- Health response includes version
- Health response includes agents_registered list
- Health response includes redis_connected boolean
- Health check with no agents registered
- Health check with multiple agents registered
- Health check when Redis disconnected

Following TDD: These tests should FAIL initially (RED phase),
then PASS after implementation (GREEN phase).
"""

from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.api.health import router
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.models import HealthCheckResponse

pytestmark = pytest.mark.unit


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create FastAPI app with health router."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def mock_context_manager(self) -> Mock:
        """Create mock context manager."""
        mock_cm = Mock(spec=ContextManager)
        mock_cm._redis = Mock()
        mock_cm._redis.ping = AsyncMock(return_value=True)
        return mock_cm

    @pytest.fixture
    def mock_agent_registry(self) -> AgentRegistry:
        """Create mock agent registry."""
        return AgentRegistry()

    @pytest.fixture
    def client(
        self,
        app: FastAPI,
        mock_context_manager: Mock,
        mock_agent_registry: AgentRegistry,
    ) -> TestClient:
        """Create test client with mocked app state."""
        app.state.context_manager = mock_context_manager
        app.state.agent_registry = mock_agent_registry
        return TestClient(app)

    def test_health_endpoint_returns_200(self, client: TestClient) -> None:
        """Test GET /health returns 200 status."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_includes_status_field(self, client: TestClient) -> None:
        """Test health response includes status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

    def test_health_response_includes_version(self, client: TestClient) -> None:
        """Test health response includes version."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_health_response_includes_agents_registered(
        self, client: TestClient
    ) -> None:
        """Test health response includes agents_registered list."""
        response = client.get("/health")
        data = response.json()
        assert "agents_registered" in data
        assert isinstance(data["agents_registered"], list)

    def test_health_response_includes_redis_connected(self, client: TestClient) -> None:
        """Test health response includes redis_connected boolean."""
        response = client.get("/health")
        data = response.json()
        assert "redis_connected" in data
        assert isinstance(data["redis_connected"], bool)

    def test_health_check_with_no_agents_registered(self, client: TestClient) -> None:
        """Test health check with no agents registered."""
        response = client.get("/health")
        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert data["agents_registered"] == []
        assert data["redis_connected"] is True

    def test_health_check_with_single_agent_registered(
        self, app: FastAPI, mock_context_manager: Mock
    ) -> None:
        """Test health check with single agent registered."""
        # Create registry with one agent
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="conversation_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["initialize_session"],
        )

        # Set up app state
        app.state.context_manager = mock_context_manager
        app.state.agent_registry = registry

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert data["agents_registered"] == ["conversation_agent"]
        assert data["redis_connected"] is True

    def test_health_check_with_multiple_agents_registered(
        self, app: FastAPI, mock_context_manager: Mock
    ) -> None:
        """Test health check with multiple agents registered."""
        # Create registry with multiple agents
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="conversation_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["initialize_session"],
        )
        registry.register_agent(
            agent_name="conversion_agent",
            agent_type="conversion",
            base_url="http://localhost:3002",
            capabilities=["detect_format"],
        )
        registry.register_agent(
            agent_name="evaluation_agent",
            agent_type="evaluation",
            base_url="http://localhost:3003",
            capabilities=["validate_nwb"],
        )

        # Set up app state
        app.state.context_manager = mock_context_manager
        app.state.agent_registry = registry

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert len(data["agents_registered"]) == 3
        assert "conversation_agent" in data["agents_registered"]
        assert "conversion_agent" in data["agents_registered"]
        assert "evaluation_agent" in data["agents_registered"]
        assert data["redis_connected"] is True

    def test_health_check_when_redis_connected(
        self, app: FastAPI, mock_agent_registry: AgentRegistry
    ) -> None:
        """Test health check when Redis is connected."""
        # Create mock with successful ping
        mock_cm = Mock(spec=ContextManager)
        mock_cm._redis = Mock()
        mock_cm._redis.ping = AsyncMock(return_value=True)

        # Set up app state
        app.state.context_manager = mock_cm
        app.state.agent_registry = mock_agent_registry

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert response.status_code == 200
        assert data["redis_connected"] is True
        assert data["status"] == "healthy"

    def test_health_check_when_redis_disconnected(
        self, app: FastAPI, mock_agent_registry: AgentRegistry
    ) -> None:
        """Test health check when Redis is disconnected."""
        # Create mock with failed ping
        mock_cm = Mock(spec=ContextManager)
        mock_cm._redis = None

        # Set up app state
        app.state.context_manager = mock_cm
        app.state.agent_registry = mock_agent_registry

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert response.status_code == 200
        assert data["redis_connected"] is False
        assert data["status"] == "unhealthy"

    def test_health_check_when_redis_ping_fails(
        self, app: FastAPI, mock_agent_registry: AgentRegistry
    ) -> None:
        """Test health check when Redis ping raises exception."""
        # Create mock with ping that raises exception
        mock_cm = Mock(spec=ContextManager)
        mock_cm._redis = Mock()
        mock_cm._redis.ping = AsyncMock(side_effect=Exception("Connection failed"))

        # Set up app state
        app.state.context_manager = mock_cm
        app.state.agent_registry = mock_agent_registry

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert response.status_code == 200
        assert data["redis_connected"] is False
        assert data["status"] == "unhealthy"

    def test_health_response_model_validation(self, client: TestClient) -> None:
        """Test health response conforms to HealthCheckResponse model."""
        response = client.get("/health")
        data = response.json()

        # Validate against model
        health_response = HealthCheckResponse(**data)

        assert health_response.status in ["healthy", "unhealthy"]
        assert isinstance(health_response.version, str)
        assert isinstance(health_response.agents_registered, list)
        assert isinstance(health_response.redis_connected, bool)

    def test_health_check_version_from_package(self, client: TestClient) -> None:
        """Test health check includes version from package metadata."""
        response = client.get("/health")
        data = response.json()

        # Version should be included in response and match package version
        assert "version" in data
        assert isinstance(data["version"], str)
        # Should match the version from __init__.py (0.1.0)
        assert data["version"] == "0.1.0"

    def test_health_check_returns_correct_agent_names_only(
        self, app: FastAPI, mock_context_manager: Mock
    ) -> None:
        """Test health check returns only agent names, not full info."""
        # Create registry with agents
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="agent_1",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["cap1", "cap2"],
        )
        registry.register_agent(
            agent_name="agent_2",
            agent_type="conversion",
            base_url="http://localhost:3002",
            capabilities=["cap3"],
        )

        # Set up app state
        app.state.context_manager = mock_context_manager
        app.state.agent_registry = registry

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        # Should return list of strings (agent names), not dictionaries
        assert data["agents_registered"] == ["agent_1", "agent_2"]
        assert all(isinstance(name, str) for name in data["agents_registered"])

    def test_health_check_status_unhealthy_when_redis_down(self, app: FastAPI) -> None:
        """Test health check returns unhealthy status when Redis is down."""
        # Create registry and mock context manager with no Redis
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="test_agent",
            agent_type="test",
            base_url="http://localhost:3001",
            capabilities=["test"],
        )

        mock_cm = Mock(spec=ContextManager)
        mock_cm._redis = None

        app.state.context_manager = mock_cm
        app.state.agent_registry = registry

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        # Even with agents registered, status should be unhealthy if Redis is down
        assert data["status"] == "unhealthy"
        assert data["redis_connected"] is False
        assert len(data["agents_registered"]) > 0

    def test_health_check_endpoint_accessible_at_correct_path(
        self, client: TestClient
    ) -> None:
        """Test health check endpoint is accessible at /health."""
        response = client.get("/health")
        assert response.status_code == 200

        # Verify wrong paths return 404
        response_wrong = client.get("/healthcheck")
        assert response_wrong.status_code == 404
