"""
Main FastAPI application for Multi-Agent NWB Conversion MCP Server.

This module provides:
- Application factory (create_app)
- Lifespan manager for startup/shutdown
- Router registration
- CORS middleware configuration
- Component initialization

The application integrates:
- ContextManager (Redis + filesystem session persistence)
- AgentRegistry (agent discovery and registration)
- MessageRouter (inter-agent communication)
- REST API endpoints (health, sessions, internal)
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_neurodata_conversion.config import settings
from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.api.health import router as health_router
from agentic_neurodata_conversion.mcp_server.api.internal import (
    router as internal_router,
)
from agentic_neurodata_conversion.mcp_server.api.sessions import (
    router as sessions_router,
)
from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifecycle manager for startup and shutdown events.

    Startup sequence:
    1. Initialize ContextManager with Redis URL and filesystem path
    2. Connect to Redis
    3. Initialize AgentRegistry
    4. Initialize MessageRouter with AgentRegistry
    5. Store all components in app.state for dependency injection

    Shutdown sequence:
    1. Close MessageRouter (closes HTTP client)
    2. Disconnect ContextManager (closes Redis connection)

    Args:
        app: FastAPI application instance

    Yields:
        None (context manager protocol)
    """
    # ===== STARTUP =====

    # 1. Initialize ContextManager
    context_manager = ContextManager(
        redis_url=settings.redis_url,
        session_ttl_seconds=settings.redis_session_ttl,
        filesystem_base_path=settings.filesystem_session_base_path,
    )

    # 2. Connect to Redis
    await context_manager.connect()

    # 3. Initialize AgentRegistry
    agent_registry = AgentRegistry()

    # 4. Initialize MessageRouter
    message_router = MessageRouter(agent_registry=agent_registry)

    # 5. Store in app.state for dependency injection
    app.state.context_manager = context_manager
    app.state.agent_registry = agent_registry
    app.state.message_router = message_router

    # Application is now ready to serve requests
    yield

    # ===== SHUTDOWN =====

    # 1. Close MessageRouter (closes HTTP client)
    await message_router.close()

    # 2. Disconnect ContextManager (closes Redis connection)
    await context_manager.disconnect()


def create_app() -> FastAPI:
    """
    Factory function to create FastAPI application.

    Creates and configures the FastAPI application with:
    - Application metadata (title, version, description)
    - Lifespan manager for startup/shutdown
    - CORS middleware
    - API routers (health, sessions, internal)

    Returns:
        Configured FastAPI application instance
    """
    # Create FastAPI app with metadata and lifespan
    app = FastAPI(
        title="Multi-Agent NWB Conversion MCP Server",
        description=(
            "Model Context Protocol server for orchestrating NWB conversion agents. "
            "Provides REST API for session management, agent communication, and workflow orchestration."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    # Note: In production, configure allowed origins appropriately
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins (configure for production)
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )

    # Include API routers
    app.include_router(health_router)  # /health
    app.include_router(sessions_router, prefix="/api/v1")  # /api/v1/sessions/*
    app.include_router(internal_router)  # /internal/*

    return app


# Create application instance
app = create_app()
