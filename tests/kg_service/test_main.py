"""Tests for KG Service main.py FastAPI application."""

import os
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_app_initialization():
    """Test FastAPI app is initialized correctly."""
    from agentic_neurodata_conversion.kg_service.main import app

    assert app.title == "NWB Knowledge Graph Service"
    assert app.version == "1.0.0"
    assert "Ontology-based metadata validation" in app.description


@pytest.mark.unit
@pytest.mark.asyncio
async def test_app_routes_registered():
    """Test all routes are registered."""
    from agentic_neurodata_conversion.kg_service.main import app

    routes = [route.path for route in app.routes]

    # Check main endpoints
    assert "/" in routes
    assert "/health" in routes

    # Check API v1 endpoints
    assert "/api/v1/normalize" in routes
    assert "/api/v1/validate" in routes
    assert "/api/v1/observations" in routes


@pytest.mark.integration
@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns service info."""
    # Skip if NEO4J_PASSWORD not set
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        pytest.skip("NEO4J_PASSWORD not set - integration tests require local Neo4j instance")

    from agentic_neurodata_conversion.kg_service.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "NWB Knowledge Graph"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert isinstance(data["endpoints"], list)
        assert "/api/v1/normalize" in data["endpoints"]
        assert "/health" in data["endpoints"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Test health check endpoint."""
    # Skip if NEO4J_PASSWORD not set
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        pytest.skip("NEO4J_PASSWORD not set - integration tests require local Neo4j instance")

    from agentic_neurodata_conversion.kg_service.config import reset_settings
    from agentic_neurodata_conversion.kg_service.db.neo4j_connection import reset_neo4j_connection
    from agentic_neurodata_conversion.kg_service.main import app
    from agentic_neurodata_conversion.kg_service.services.kg_service import reset_kg_service

    # Reset singletons
    reset_settings()
    reset_neo4j_connection()
    reset_kg_service()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "neo4j" in data
        assert "version" in data
        assert data["version"] == "1.0.0"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_unhealthy_neo4j():
    """Test health check when Neo4j is unhealthy."""
    from agentic_neurodata_conversion.kg_service.main import app

    # Mock settings to avoid requiring NEO4J_PASSWORD in CI
    with (
        patch("agentic_neurodata_conversion.kg_service.main.get_settings") as mock_get_settings,
        patch("agentic_neurodata_conversion.kg_service.main.get_neo4j_connection") as mock_get_conn,
    ):
        # Mock settings
        mock_settings = Mock()
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_get_settings.return_value = mock_settings

        # Mock Neo4j connection to return unhealthy
        mock_conn = Mock()
        mock_conn.health_check = AsyncMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "unhealthy"
            assert data["neo4j"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lifespan_startup_shutdown():
    """Test lifespan context manager handles startup and shutdown."""
    from agentic_neurodata_conversion.kg_service.config import reset_settings
    from agentic_neurodata_conversion.kg_service.db.neo4j_connection import reset_neo4j_connection
    from agentic_neurodata_conversion.kg_service.main import lifespan

    # Reset singletons
    reset_settings()
    reset_neo4j_connection()

    # Mock settings and Neo4j connection
    with (
        patch("agentic_neurodata_conversion.kg_service.main.get_settings") as mock_get_settings,
        patch("agentic_neurodata_conversion.kg_service.main.get_neo4j_connection") as mock_get_conn,
    ):
        # Mock settings
        mock_settings = Mock()
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_get_settings.return_value = mock_settings

        # Mock Neo4j connection
        mock_conn = Mock()
        mock_conn.connect = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_get_conn.return_value = mock_conn

        # Mock FastAPI app
        mock_app = Mock()

        # Use lifespan context manager
        async with lifespan(mock_app):
            # During lifespan, connection should be established
            mock_conn.connect.assert_called_once()

        # After lifespan, connection should be closed
        mock_conn.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lifespan_handles_connection_error():
    """Test lifespan handles connection errors gracefully."""
    from agentic_neurodata_conversion.kg_service.config import reset_settings
    from agentic_neurodata_conversion.kg_service.db.neo4j_connection import reset_neo4j_connection
    from agentic_neurodata_conversion.kg_service.main import lifespan

    # Reset singletons
    reset_settings()
    reset_neo4j_connection()

    # Mock settings and Neo4j connection that fails to connect
    with (
        patch("agentic_neurodata_conversion.kg_service.main.get_settings") as mock_get_settings,
        patch("agentic_neurodata_conversion.kg_service.main.get_neo4j_connection") as mock_get_conn,
    ):
        # Mock settings
        mock_settings = Mock()
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_get_settings.return_value = mock_settings

        # Mock Neo4j connection that fails to connect
        mock_conn = Mock()
        mock_conn.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_conn.close = AsyncMock()
        mock_get_conn.return_value = mock_conn

        mock_app = Mock()

        # Lifespan should raise error but still cleanup
        with pytest.raises(Exception, match="Connection failed"):
            async with lifespan(mock_app):
                pass

        # Even on error, close should be called
        mock_conn.close.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cors_headers():
    """Test CORS headers are set correctly."""
    # Skip if NEO4J_PASSWORD not set
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        pytest.skip("NEO4J_PASSWORD not set - integration tests require local Neo4j instance")

    from agentic_neurodata_conversion.kg_service.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Send OPTIONS request (preflight)
        response = await client.options(
            "/", headers={"Origin": "http://localhost:8000", "Access-Control-Request-Method": "GET"}
        )

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers


@pytest.mark.unit
def test_app_import_does_not_fail():
    """Test that importing the app doesn't fail."""
    try:
        from agentic_neurodata_conversion.kg_service.main import app

        assert app is not None
        assert hasattr(app, "routes")
    except Exception as e:
        pytest.fail(f"Failed to import app: {e}")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_endpoints_accept_json():
    """Test API endpoints accept JSON content type."""
    from agentic_neurodata_conversion.kg_service.main import app

    # Mock settings and Neo4j connection to avoid requiring NEO4J_PASSWORD in CI
    # Need to mock both main.get_settings and config.get_settings since endpoints call config directly
    with (
        patch("agentic_neurodata_conversion.kg_service.main.get_settings") as mock_get_settings_main,
        patch("agentic_neurodata_conversion.kg_service.config.get_settings") as mock_get_settings_config,
        patch("agentic_neurodata_conversion.kg_service.main.get_neo4j_connection") as mock_get_conn,
    ):
        # Mock settings
        mock_settings = Mock()
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "password"
        mock_get_settings_main.return_value = mock_settings
        mock_get_settings_config.return_value = mock_settings

        # Mock Neo4j connection
        mock_conn = Mock()
        mock_conn.connect = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_get_conn.return_value = mock_conn

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Test that normalize endpoint exists and accepts JSON
            response = await client.post(
                "/api/v1/normalize",
                json={"field_path": "subject.species", "value": "Mus musculus"},
                headers={"Content-Type": "application/json"},
            )

            # Should not be 404 or 415 (Unsupported Media Type)
            assert response.status_code != 404
            assert response.status_code != 415
