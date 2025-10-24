"""
Internal API endpoints for agent communication.

This module provides internal-only endpoints that agents use to:
- Register themselves with the MCP server
- Access and update session context
- Route messages to other agents

These endpoints are NOT exposed to external users and should only be
accessible within the internal network.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from agentic_neurodata_conversion.models import (
    AgentRegistrationRequest,
    RouteMessageRequest,
)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/register_agent")
async def register_agent(
    request: AgentRegistrationRequest, req: Request
) -> dict[str, str]:
    """
    Internal endpoint for agent registration.

    Registers an agent with the MCP server's agent registry, making it
    discoverable for message routing and health checks.

    Args:
        request: Agent registration information (name, type, base_url, capabilities)
        req: FastAPI request object (contains app.state)

    Returns:
        Dict with registration status and agent name

    Example:
        POST /internal/register_agent
        {
            "agent_name": "conversation_agent",
            "agent_type": "conversation",
            "base_url": "http://localhost:3001",
            "capabilities": ["initialize_session", "handle_clarification"]
        }

        Response:
        {
            "status": "registered",
            "agent_name": "conversation_agent"
        }
    """
    # Get agent_registry from app.state
    agent_registry = req.app.state.agent_registry

    # Register agent with provided info
    agent_registry.register_agent(
        agent_name=request.agent_name,
        agent_type=request.agent_type,
        base_url=request.base_url,
        capabilities=request.capabilities,
    )

    # Return success status
    return {"status": "registered", "agent_name": request.agent_name}


@router.get("/sessions/{session_id}/context")
async def get_session_context(session_id: str, req: Request) -> dict[str, Any]:
    """
    Internal endpoint for agents to get session context.

    Retrieves the current session context from the context manager,
    allowing agents to access session state, metadata, and workflow stage.

    Args:
        session_id: Session identifier
        req: FastAPI request object (contains app.state)

    Returns:
        Session context as dictionary

    Raises:
        HTTPException 404: If session not found

    Example:
        GET /internal/sessions/550e8400-e29b-41d4-a716-446655440000/context

        Response:
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "workflow_stage": "initialized",
            "current_agent": null,
            "dataset_info": {...},
            ...
        }
    """
    # Get context_manager from app.state
    context_manager = req.app.state.context_manager

    # Get session from context_manager
    session = await context_manager.get_session(session_id)

    # Return 404 if not found
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    # Return session as dict
    result: dict[str, Any] = session.model_dump(mode="json")
    return result


@router.patch("/sessions/{session_id}/context")
async def update_session_context(
    session_id: str, updates: dict[str, Any], req: Request
) -> dict[str, str]:
    """
    Internal endpoint for agents to update session context.

    Updates session context with provided changes. Automatically updates
    the last_updated timestamp.

    Args:
        session_id: Session identifier
        updates: Dictionary of fields to update
        req: FastAPI request object (contains app.state)

    Returns:
        Dict with update status and session_id

    Raises:
        HTTPException 404: If session not found

    Example:
        PATCH /internal/sessions/550e8400-e29b-41d4-a716-446655440000/context
        {
            "workflow_stage": "collecting_metadata",
            "current_agent": "conversation_agent"
        }

        Response:
        {
            "status": "updated",
            "session_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """
    # Get context_manager from app.state
    context_manager = req.app.state.context_manager

    # Get current session
    session = await context_manager.get_session(session_id)

    # Return 404 if not found
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    # Update session with provided updates
    # Note: update_session automatically updates last_updated timestamp
    await context_manager.update_session(session_id, updates)

    # Return success status
    return {"status": "updated", "session_id": session_id}


@router.post("/route_message")
async def route_message(request: RouteMessageRequest, req: Request) -> dict[str, Any]:
    """
    Internal endpoint to route messages between agents.

    Routes an MCP message from one agent to another via HTTP POST.
    Uses the message router to handle agent lookup and message delivery.

    Args:
        request: Message routing request (target_agent, message_type, payload)
        req: FastAPI request object (contains app.state)

    Returns:
        Agent response dict with status and result

    Raises:
        HTTPException 400/404/500: If message routing fails

    Example:
        POST /internal/route_message
        {
            "target_agent": "conversion_agent",
            "message_type": "agent_execute",
            "payload": {
                "task_name": "detect_format",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "parameters": {}
            }
        }

        Response:
        {
            "status": "success",
            "result": {
                "format_detected": "openephys",
                "confidence": 0.95
            }
        }
    """
    # Get message_router from app.state
    message_router = req.app.state.message_router

    # Send message using message_router
    try:
        result: dict[str, Any] = await message_router.send_message(
            target_agent=request.target_agent,
            message_type=request.message_type,
            payload=request.payload,
        )
        return result
    except ValueError as e:
        # Agent not found in registry
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except Exception as e:
        # Other errors (network, timeout, etc.)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to route message: {str(e)}",
        ) from e
