"""Health router for health check, root, and session management endpoints.

Handles:
- Health check endpoint
- Root/welcome endpoint
- Session reset endpoint
"""

import logging

from fastapi import APIRouter

from agentic_neurodata_conversion.api.dependencies import get_or_create_mcp_server
from agentic_neurodata_conversion.models import HealthResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Root endpoint - API welcome message.

    Provides basic information about the API including name, version, and status.

    Returns:
        Dictionary with API metadata
    """
    return {
        "name": "Agentic Neurodata Conversion API",
        "version": "0.1.0",
        "status": "running",
    }


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Used by monitoring systems, load balancers, and deployment tools to
    verify the API is running and functioning correctly.

    Provides information about:
    - Overall health status
    - API version
    - Registered agents and their status
    - Registered message handlers

    Returns:
        HealthResponse with health status and component information
    """
    try:
        mcp_server = get_or_create_mcp_server()
        agents = dict.fromkeys(mcp_server.agents.keys(), "active")
        handlers = dict.fromkeys(mcp_server.handlers.keys(), "registered")
    except Exception:
        # Fallback if MCP server not initialized
        agents = {}
        handlers = {}

    return HealthResponse(status="healthy", version="0.1.0", agents=agents, handlers=handlers)


@router.post("/api/reset")
async def reset_session():
    """Reset the conversion session.

    Clears all state and resets the system to initial state. This includes:
    - Clearing conversion status
    - Resetting metadata
    - Clearing conversation history
    - Removing temporary files
    - Resetting retry counters

    Use this to start fresh after a completed or failed conversion.

    Returns:
        Confirmation message
    """
    mcp_server = get_or_create_mcp_server()
    mcp_server.reset_state()

    return {"message": "Session reset successfully"}
