"""
Health check endpoint for MCP server monitoring.

This module provides the /health endpoint for monitoring server status,
including registered agents and Redis connection state.
"""

from fastapi import APIRouter, Request

from agentic_neurodata_conversion import __version__
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.models import HealthCheckResponse

router = APIRouter(tags=["health"])


async def _check_redis_connection(context_manager: ContextManager) -> bool:
    """
    Check if Redis connection is active.

    Args:
        context_manager: ContextManager instance to check

    Returns:
        True if Redis is connected and responsive, False otherwise
    """
    if context_manager._redis is None:
        return False

    try:
        await context_manager._redis.ping()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(request: Request) -> HealthCheckResponse:
    """
    Health check endpoint for monitoring.

    Returns server status including:
    - Overall health status (healthy/unhealthy)
    - Package version
    - List of registered agent names
    - Redis connection status

    Args:
        request: FastAPI request object (contains app.state)

    Returns:
        HealthCheckResponse with current server status
    """
    # Get dependencies from app state
    agent_registry = request.app.state.agent_registry
    context_manager = request.app.state.context_manager

    # Check Redis connection
    redis_connected = await _check_redis_connection(context_manager)

    # Get list of registered agent names
    agents = agent_registry.list_agents()
    agent_names = [agent["agent_name"] for agent in agents]

    # Determine overall status
    status = "healthy" if redis_connected else "unhealthy"

    return HealthCheckResponse(
        status=status,
        version=__version__,
        agents_registered=agent_names,
        redis_connected=redis_connected,
    )
