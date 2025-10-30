"""
Pytest configuration and shared fixtures.

This module provides shared test fixtures for all tests including:
- Event loop for async tests
- Redis client (using fakeredis for tests)
- Context manager with test Redis and temp filesystem
- Agent registry
- Test session context
- Synthetic OpenEphys dataset path
- MCP server URL

All fixtures use isolated test resources (Redis DB 15, temp directories).
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import fakeredis.aioredis
import pytest

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.models.session_context import (
    SessionContext,
    WorkflowStage,
)

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for async tests.

    Uses session scope to share event loop across all tests for better performance.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def redis_client() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """
    Redis client for tests (uses database 15 for isolation).

    Uses fakeredis for unit tests to avoid requiring a real Redis instance.
    Database 15 is used for test isolation (convention for test databases).

    Returns:
        FakeRedis client with decode_responses=False (for JSON handling)
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


@pytest.fixture
async def context_manager(
    redis_client: fakeredis.aioredis.FakeRedis, tmp_path: Path
) -> AsyncGenerator[ContextManager, None]:
    """
    Context manager fixture with test Redis and temp filesystem.

    Provides a fully configured ContextManager instance for testing with:
    - Fake Redis client (isolated, in-memory)
    - Temporary filesystem path (auto-cleaned after test)
    - Standard TTL of 24 hours

    Args:
        redis_client: Fake Redis client fixture
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Connected ContextManager ready for use
    """
    manager = ContextManager(
        redis_url="redis://localhost:6379/15",  # Will be replaced with fake client
        filesystem_base_path=str(tmp_path),
        session_ttl_seconds=86400,  # 24 hours
    )
    # Manually inject the fake Redis client instead of calling connect()
    manager._redis = redis_client
    try:
        yield manager
    finally:
        manager._redis = None


@pytest.fixture
def agent_registry() -> AgentRegistry:
    """
    Agent registry fixture.

    Provides a fresh AgentRegistry instance for each test to ensure test isolation.

    Returns:
        New AgentRegistry instance
    """
    return AgentRegistry()


@pytest.fixture
def message_router(agent_registry: AgentRegistry) -> Any:  # noqa: ARG001
    """
    Message router fixture (for later phases).

    This fixture is a placeholder for Phase 2 when the MessageRouter is implemented.
    For now, it returns None to allow tests to be written.

    Args:
        agent_registry: Agent registry fixture (unused until Phase 2)

    Returns:
        None (will return MessageRouter instance in Phase 2)
    """
    # TODO: Implement in Phase 2
    # from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter
    # return MessageRouter(agent_registry)
    return None


@pytest.fixture
def test_session() -> SessionContext:
    """
    Create test session context.

    Provides a sample SessionContext with realistic test data for use in tests.
    Each test gets a fresh session context.

    Returns:
        SessionContext with test session ID and initialized workflow stage
    """
    return SessionContext(
        session_id="test-session-001",
        workflow_stage=WorkflowStage.INITIALIZED,
    )


@pytest.fixture(scope="session")
def test_dataset_path() -> Path:
    """
    Path to synthetic OpenEphys dataset.

    Returns the path to the synthetic OpenEphys dataset that should be generated
    by running tests/data/generate_synthetic_openephys.py.

    Returns:
        Path to synthetic_openephys directory
    """
    return Path(__file__).parent / "data" / "synthetic_openephys"


@pytest.fixture
def mcp_server_url() -> str:
    """
    MCP server URL for tests.

    Returns the default MCP server URL used for testing. Tests can mock HTTP
    requests to this URL using pytest-httpx or aioresponses.

    Returns:
        MCP server URL (http://localhost:3000)
    """
    return "http://localhost:3000"
