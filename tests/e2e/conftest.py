"""
E2E test fixtures and configuration.

This module provides fixtures for end-to-end tests including:
- TestClient with mocked agent HTTP calls (same as integration tests)
- Real MCP server components (ContextManager, AgentRegistry, MessageRouter)
- Synthetic datasets for testing
- Shared test resources
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

# Import integration fixtures
from tests.integration.conftest import (
    integration_redis_client,
    integration_test_client,
    mock_agent_http_responses,
    mock_llm_patch,
    mock_llm_response,
)


@pytest.fixture(scope="session")
def synthetic_dataset_e2e() -> Path:
    """
    Path to synthetic OpenEphys dataset for E2E tests.

    Returns:
        Path to synthetic_openephys directory
    """
    return Path(__file__).parent.parent / "data" / "synthetic_openephys"


@pytest.fixture
def e2e_output_dir(tmp_path: Path) -> Path:
    """
    Output directory for E2E test results.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        Path to output directory
    """
    output = tmp_path / "e2e_output"
    output.mkdir(exist_ok=True)
    return output


@pytest.fixture
def mcp_server_url() -> str:
    """
    MCP server URL for E2E tests.

    Returns:
        MCP server base URL
    """
    return "http://localhost:3000"


@pytest.fixture(scope="function")
def event_loop_e2e() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create event loop for E2E tests.

    Each test gets a fresh event loop for proper isolation.

    Yields:
        Event loop for async tests
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# Re-export integration fixtures for E2E tests to use
__all__ = [
    "integration_redis_client",
    "integration_test_client",
    "mock_agent_http_responses",
    "mock_llm_patch",
    "mock_llm_response",
    "synthetic_dataset_e2e",
    "e2e_output_dir",
    "mcp_server_url",
    "event_loop_e2e",
]
