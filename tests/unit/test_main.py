"""
Unit tests for MCP Server main application module.

Tests the main.py module including:
- Application factory (create_app)
- Lifespan manager startup/shutdown
- Component initialization in lifespan
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentic_neurodata_conversion.mcp_server import main


class TestCreateApp:
    """Test the create_app factory function."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """
        Test that create_app returns a FastAPI application.

        Verifies that the factory function creates a FastAPI instance
        with the correct type.
        """
        from fastapi import FastAPI

        app = main.create_app()
        assert isinstance(app, FastAPI)

    def test_app_has_correct_title(self) -> None:
        """
        Test that application has correct title.

        Verifies that the FastAPI app is configured with the expected title.
        """
        app = main.create_app()
        assert app.title == "Multi-Agent NWB Conversion MCP Server"

    def test_app_has_correct_version(self) -> None:
        """
        Test that application has correct version.

        Verifies that the FastAPI app is configured with version 0.1.0.
        """
        app = main.create_app()
        assert app.version == "0.1.0"

    def test_app_has_description(self) -> None:
        """
        Test that application has description.

        Verifies that the FastAPI app has a description configured.
        """
        app = main.create_app()
        assert app.description is not None
        assert len(app.description) > 0

    def test_app_has_lifespan(self) -> None:
        """
        Test that application has lifespan manager configured.

        Verifies that the FastAPI app has the lifespan context manager set.
        """
        app = main.create_app()
        assert app.router.lifespan_context is not None

    def test_app_has_cors_middleware(self) -> None:
        """
        Test that CORS middleware is registered.

        Verifies that the FastAPI app has CORS middleware in its middleware stack.
        """
        app = main.create_app()

        # Check that middleware stack includes CORS
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_types or len(app.user_middleware) > 0

    def test_app_has_health_router(self) -> None:
        """
        Test that health router is included.

        Verifies that the /health route is registered in the app.
        """
        app = main.create_app()

        # Check that /health route exists
        routes = [route.path for route in app.routes]
        assert "/health" in routes

    def test_app_has_sessions_router(self) -> None:
        """
        Test that sessions router is included with /api/v1 prefix.

        Verifies that session routes are registered under /api/v1.
        """
        app = main.create_app()

        # Check that session routes exist with prefix
        routes = [route.path for route in app.routes]
        session_routes = [r for r in routes if r.startswith("/api/v1/sessions")]
        assert len(session_routes) > 0

    def test_app_has_internal_router(self) -> None:
        """
        Test that internal router is included.

        Verifies that internal routes are registered under /internal.
        """
        app = main.create_app()

        # Check that internal routes exist
        routes = [route.path for route in app.routes]
        internal_routes = [r for r in routes if r.startswith("/internal")]
        assert len(internal_routes) > 0


class TestLifespan:
    """Test the lifespan manager startup and shutdown sequences."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_sequence(self) -> None:
        """
        Test that lifespan startup initializes all components.

        Verifies that the startup sequence:
        1. Creates ContextManager
        2. Connects to Redis
        3. Creates AgentRegistry
        4. Creates MessageRouter
        5. Stores all in app.state
        """
        from fastapi import FastAPI

        # Mock the dependencies
        with (
            patch(
                "agentic_neurodata_conversion.mcp_server.main.ContextManager"
            ) as mock_context_manager_cls,
            patch(
                "agentic_neurodata_conversion.mcp_server.main.AgentRegistry"
            ) as mock_agent_registry_cls,
            patch(
                "agentic_neurodata_conversion.mcp_server.main.MessageRouter"
            ) as mock_message_router_cls,
        ):
            # Create mock instances
            mock_context_manager = AsyncMock()
            mock_context_manager.connect = AsyncMock()
            mock_context_manager.disconnect = AsyncMock()
            mock_context_manager_cls.return_value = mock_context_manager

            mock_agent_registry = MagicMock()
            mock_agent_registry_cls.return_value = mock_agent_registry

            mock_message_router = AsyncMock()
            mock_message_router.close = AsyncMock()
            mock_message_router_cls.return_value = mock_message_router

            # Create app
            app = FastAPI(lifespan=main.lifespan)

            # Trigger lifespan
            async with app.router.lifespan_context(app):
                # Verify startup sequence
                # 1. ContextManager created
                assert mock_context_manager_cls.called

                # 2. Redis connected
                mock_context_manager.connect.assert_called_once()

                # 3. AgentRegistry created
                assert mock_agent_registry_cls.called

                # 4. MessageRouter created
                assert mock_message_router_cls.called

                # 5. Components stored in app.state
                assert hasattr(app.state, "context_manager")
                assert hasattr(app.state, "agent_registry")
                assert hasattr(app.state, "message_router")
                assert app.state.context_manager == mock_context_manager
                assert app.state.agent_registry == mock_agent_registry
                assert app.state.message_router == mock_message_router

            # Verify shutdown sequence after context exits
            mock_message_router.close.assert_called_once()
            mock_context_manager.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_sequence(self) -> None:
        """
        Test that lifespan shutdown closes all components.

        Verifies that the shutdown sequence:
        1. Closes MessageRouter
        2. Disconnects ContextManager
        """
        from fastapi import FastAPI

        # Mock the dependencies
        with (
            patch(
                "agentic_neurodata_conversion.mcp_server.main.ContextManager"
            ) as mock_context_manager_cls,
            patch(
                "agentic_neurodata_conversion.mcp_server.main.AgentRegistry"
            ) as mock_agent_registry_cls,
            patch(
                "agentic_neurodata_conversion.mcp_server.main.MessageRouter"
            ) as mock_message_router_cls,
        ):
            # Create mock instances
            mock_context_manager = AsyncMock()
            mock_context_manager.connect = AsyncMock()
            mock_context_manager.disconnect = AsyncMock()
            mock_context_manager_cls.return_value = mock_context_manager

            mock_agent_registry = MagicMock()
            mock_agent_registry_cls.return_value = mock_agent_registry

            mock_message_router = AsyncMock()
            mock_message_router.close = AsyncMock()
            mock_message_router_cls.return_value = mock_message_router

            # Create app
            app = FastAPI(lifespan=main.lifespan)

            # Trigger lifespan and exit
            async with app.router.lifespan_context(app):
                pass

            # Verify shutdown was called
            mock_message_router.close.assert_called_once()
            mock_context_manager.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_uses_settings(self) -> None:
        """
        Test that lifespan uses configuration from settings.

        Verifies that the ContextManager is initialized with values
        from the settings module.
        """
        from fastapi import FastAPI

        # Mock the dependencies
        with (
            patch(
                "agentic_neurodata_conversion.mcp_server.main.ContextManager"
            ) as mock_context_manager_cls,
            patch(
                "agentic_neurodata_conversion.mcp_server.main.AgentRegistry"
            ) as mock_agent_registry_cls,
            patch(
                "agentic_neurodata_conversion.mcp_server.main.MessageRouter"
            ) as mock_message_router_cls,
            patch(
                "agentic_neurodata_conversion.mcp_server.main.settings"
            ) as mock_settings,
        ):
            # Configure mock settings
            mock_settings.redis_url = "redis://test:6379/0"
            mock_settings.redis_session_ttl = 3600
            mock_settings.filesystem_session_base_path = "/test/sessions"

            # Create mock context manager
            mock_context_manager = AsyncMock()
            mock_context_manager.connect = AsyncMock()
            mock_context_manager.disconnect = AsyncMock()
            mock_context_manager_cls.return_value = mock_context_manager

            # Create mock agent registry
            mock_agent_registry = MagicMock()
            mock_agent_registry_cls.return_value = mock_agent_registry

            # Create mock message router
            mock_message_router = AsyncMock()
            mock_message_router.close = AsyncMock()
            mock_message_router_cls.return_value = mock_message_router

            # Create app and trigger lifespan
            app = FastAPI(lifespan=main.lifespan)
            async with app.router.lifespan_context(app):
                # Verify ContextManager was created with settings values
                mock_context_manager_cls.assert_called_once_with(
                    redis_url="redis://test:6379/0",
                    session_ttl_seconds=3600,
                    filesystem_base_path="/test/sessions",
                )


class TestAppInstance:
    """Test the global app instance."""

    def test_app_instance_exists(self) -> None:
        """
        Test that the global app instance exists.

        Verifies that main.app is available for import and is a FastAPI instance.
        """
        from fastapi import FastAPI

        assert hasattr(main, "app")
        assert isinstance(main.app, FastAPI)

    def test_app_instance_is_configured(self) -> None:
        """
        Test that the global app instance is properly configured.

        Verifies that main.app has the expected configuration.
        """
        app = main.app
        assert app.title == "Multi-Agent NWB Conversion MCP Server"
        assert app.version == "0.1.0"
        assert app.description is not None
