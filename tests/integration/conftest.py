"""
Integration test fixtures and configuration.

This module provides fixtures for integration tests including:
- MCP server with real Redis (fakeredis)
- Mock LLM responses for cost/speed
- Agent server instances
- Shared test client
- Dataset paths
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import httpx
import pytest
from fastapi.testclient import TestClient

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.agents.conversion_agent import ConversionAgent
from agentic_neurodata_conversion.agents.evaluation_agent import EvaluationAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager


@pytest.fixture(scope="function")
async def integration_redis_client() -> (
    AsyncGenerator[fakeredis.aioredis.FakeRedis, None]
):
    """
    Redis client for integration tests.

    Uses fakeredis for integration tests to avoid requiring a real Redis instance.
    Each test gets a fresh Redis instance.

    Returns:
        FakeRedis client
    """
    client = fakeredis.aioredis.FakeRedis(decode_responses=False)
    try:
        # Clean up before tests
        await client.flushdb()
        yield client
    finally:
        # Clean up after tests
        await client.flushdb()
        await client.aclose()


@pytest.fixture(scope="function")
def integration_test_client(
    integration_redis_client: fakeredis.aioredis.FakeRedis, tmp_path: Path
) -> Generator[TestClient, None, None]:
    """
    Create TestClient for integration tests with real components.

    This fixture creates a fully initialized MCP server with:
    - Fake Redis for session persistence
    - Real ContextManager
    - Real AgentRegistry (with registered mock agents)
    - Real MessageRouter

    Args:
        integration_redis_client: Fake Redis client
        tmp_path: Temporary directory for filesystem storage

    Returns:
        TestClient with fully initialized application
    """
    from contextlib import asynccontextmanager

    from agentic_neurodata_conversion.mcp_server import main
    from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter

    # Create test app
    app = main.create_app()

    # Mock the startup sequence to inject fake Redis and register mock agents
    @asynccontextmanager
    async def test_lifespan(app_instance: Any):  # type: ignore
        """Test lifespan manager with fake Redis and mock agents."""
        # Startup: Initialize components with fake Redis
        context_manager = ContextManager(
            redis_url="redis://localhost:6379/15",
            filesystem_base_path=str(tmp_path),
            session_ttl_seconds=86400,
        )
        # Inject fake Redis instead of connecting
        context_manager._redis = integration_redis_client

        agent_registry = AgentRegistry()

        # Register mock agents so integration tests don't fail on agent check
        # These agents won't actually process messages (no HTTP servers running)
        # but they satisfy the registration requirement
        agent_registry.register_agent(
            agent_name="conversation_agent",
            agent_type="conversation",
            base_url="http://localhost:9001",
            capabilities=["initialize_session", "handle_clarification"],
        )
        agent_registry.register_agent(
            agent_name="conversion_agent",
            agent_type="conversion",
            base_url="http://localhost:9002",
            capabilities=["convert_dataset"],
        )
        agent_registry.register_agent(
            agent_name="evaluation_agent",
            agent_type="evaluation",
            base_url="http://localhost:9003",
            capabilities=["validate_nwb"],
        )

        message_router = MessageRouter(agent_registry=agent_registry)

        # Store in app.state
        app_instance.state.context_manager = context_manager
        app_instance.state.agent_registry = agent_registry
        app_instance.state.message_router = message_router

        yield

        # Shutdown: Close resources
        await message_router.close()
        context_manager._redis = None

    # Replace lifespan
    app.router.lifespan_context = test_lifespan

    # Create test client
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_llm_response() -> MagicMock:
    """
    Mock LLM response for testing without actual API calls.

    Returns a mock response that can be customized per test.

    Returns:
        Mock object for LLM responses
    """
    mock = MagicMock()
    # Default response with metadata
    mock.return_value = """{
        "subject_id": "Test Mouse 001",
        "species": "Mus musculus",
        "age": "P56",
        "sex": "Male",
        "session_start_time": "2024-01-15T12:00:00",
        "experimenter": "Test User",
        "device_name": "Open Ephys Acquisition Board",
        "manufacturer": "Open Ephys",
        "recording_location": "CA1",
        "description": "Test session for pipeline validation",
        "extraction_confidence": {
            "subject_id": "high",
            "species": "high",
            "age": "high",
            "sex": "high",
            "session_start_time": "high",
            "experimenter": "high",
            "device_name": "high",
            "manufacturer": "high",
            "recording_location": "high",
            "description": "high"
        }
    }"""
    return mock


@pytest.fixture
async def mock_llm_patch(mock_llm_response: MagicMock) -> AsyncGenerator[Any, None]:
    """
    Patch LLM calls for all agents.

    This fixture mocks the LLM call_llm method for both Anthropic and OpenAI
    providers to avoid actual API calls during integration tests.

    Args:
        mock_llm_response: Mock LLM response fixture

    Yields:
        Patch context manager
    """
    async_mock = AsyncMock(return_value=mock_llm_response.return_value)

    with patch(
        "agentic_neurodata_conversion.agents.base_agent.BaseAgent.call_llm",
        new=async_mock,
    ):
        yield async_mock


@pytest.fixture(autouse=True)
async def mock_agent_http_responses() -> AsyncGenerator[AsyncMock, None]:
    """
    Mock HTTP responses from agents (autouse for all integration tests).

    This fixture mocks the MessageRouter's HTTP client to avoid actual
    HTTP requests to agents during integration tests. It's applied automatically
    to all tests in the integration directory.

    Yields:
        AsyncMock for httpx.AsyncClient.post
    """
    # Mock successful agent responses
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "message": "Task executed successfully",
    }
    mock_response.raise_for_status = AsyncMock()

    async_mock = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=async_mock):
        yield async_mock


@pytest.fixture
def synthetic_dataset_path() -> Path:
    """
    Path to synthetic OpenEphys dataset for integration tests.

    Returns:
        Path to synthetic_openephys directory
    """
    return Path(__file__).parent.parent / "data" / "synthetic_openephys"


@pytest.fixture
def agent_config_factory(tmp_path: Path) -> Any:
    """
    Factory fixture for creating AgentConfig instances.

    Returns:
        Function that creates AgentConfig with given parameters
    """

    def create_config(
        agent_name: str,
        agent_type: str,
        agent_port: int,
        mcp_server_url: str = "http://localhost:3000",
    ) -> AgentConfig:
        """
        Create agent configuration.

        Args:
            agent_name: Name of agent
            agent_type: Type of agent
            agent_port: Port for agent HTTP server
            mcp_server_url: MCP server URL

        Returns:
            AgentConfig instance
        """
        return AgentConfig(
            agent_name=agent_name,
            agent_type=agent_type,
            agent_port=agent_port,
            mcp_server_url=mcp_server_url,
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="test-api-key",  # Will be mocked
            max_tokens=4096,
            temperature=0.0,
        )

    return create_config


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """
    Output directory for generated NWB files and reports.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        Path to output directory
    """
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    return output


@pytest.fixture(scope="function")
def event_loop_integration() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for integration tests.

    Each test gets a fresh event loop for proper isolation.

    Yields:
        Event loop for async tests
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
