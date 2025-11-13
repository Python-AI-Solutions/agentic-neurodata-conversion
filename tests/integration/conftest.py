"""
Shared fixtures for integration tests.

This conftest.py provides integration test fixtures including FastAPI
test clients, WebSocket mocks, and full workflow setup helpers.

These fixtures are available to all tests in the integration/ directory
and inherit from the root conftest.py fixtures.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from agentic_neurodata_conversion.models import ConversionStatus

# ============================================================================
# API Test Client Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def api_test_client():
    """
    FastAPI TestClient for integration testing.

    Module-scoped for efficiency - client reused across tests in same module.
    Use for API endpoint testing without starting actual server.

    Returns:
        TestClient: FastAPI test client instance

    Scope:
        module - Created once per test module for performance

    Example:
        def test_api_endpoint(api_test_client):
            response = api_test_client.get("/api/status")
            assert response.status_code == 200

    Note:
        This imports from api.main which registers all agents and routes.
        State persists between tests in same module - use api_test_client_with_state
        for isolated tests.
    """
    from agentic_neurodata_conversion.api.main import app

    return TestClient(app)


@pytest.fixture
def api_test_client_with_state(api_test_client):
    """
    TestClient with reset global state before each test.

    Args:
        api_test_client: Module-scoped test client

    Returns:
        TestClient: Test client with fresh state

    Scope:
        function - State reset before each test

    Example:
        def test_upload(api_test_client_with_state):
            # State is fresh - no previous uploads
            response = api_test_client_with_state.post("/api/upload", ...)
            assert response.status_code == 200
    """
    # Reset state before each test
    api_test_client.post("/api/reset")
    return api_test_client


# ============================================================================
# File Upload Fixtures
# ============================================================================


@pytest.fixture
def uploaded_nwb_file(tmp_path, create_test_nwb_file):
    """
    Create and return path to simulated uploaded NWB file.

    Args:
        tmp_path: Pytest's temporary directory
        create_test_nwb_file: Factory fixture from root conftest.py

    Returns:
        Path: Path to created NWB file

    Example:
        def test_upload(api_test_client, uploaded_nwb_file):
            with open(uploaded_nwb_file, "rb") as f:
                response = api_test_client.post(
                    "/api/upload",
                    files={"file": ("recording.nwb", f, "application/octet-stream")}
                )
            assert response.status_code == 200
    """
    return create_test_nwb_file(
        tmp_path,
        "uploaded_recording.nwb",
        b"mock nwb content" * 100,  # Make it reasonably sized
    )


@pytest.fixture
def uploaded_spikeglx_files(sample_spikeglx_files):
    """
    Get sample SpikeGLX files for testing conversion workflow.

    Args:
        sample_spikeglx_files: Session fixture from root conftest.py

    Returns:
        dict: Dictionary with 'bin' and 'meta' file paths

    Example:
        def test_spikeglx_conversion(api_test_client, uploaded_spikeglx_files):
            bin_file = uploaded_spikeglx_files['bin']
            with open(bin_file, "rb") as f:
                response = api_test_client.post("/api/upload", files={"file": f})
            assert response.status_code == 200
    """
    return sample_spikeglx_files


# ============================================================================
# WebSocket Fixtures
# ============================================================================


@pytest.fixture
def mock_websocket():
    """
    Mock WebSocket connection for testing real-time updates.

    Returns:
        Mock: WebSocket mock with common methods

    Example:
        @pytest.mark.asyncio
        async def test_websocket(mock_websocket):
            await mock_websocket.accept()
            await mock_websocket.send_json({"type": "update", "data": {}})
            mock_websocket.send_json.assert_called_once()

    Methods mocked:
        - accept(): AsyncMock
        - send_text(data): AsyncMock
        - send_json(data): AsyncMock
        - receive_text(): AsyncMock returning '{"type": "ping"}'
        - close(): AsyncMock
    """
    ws = Mock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"type": "ping"}')
    ws.receive_json = AsyncMock(return_value={"type": "ping"})
    ws.close = AsyncMock()
    return ws


# ============================================================================
# Workflow Test Helpers
# ============================================================================


@pytest.fixture
def complete_workflow_state(global_state, tmp_path, create_test_nwb_file):
    """
    Create GlobalState with complete workflow simulation.

    Sets up state as if file was uploaded, converted, and validated.
    Useful for testing post-conversion workflows.

    Args:
        global_state: Fresh state from root conftest.py
        tmp_path: Pytest's temporary directory
        create_test_nwb_file: Factory fixture from root conftest.py

    Returns:
        GlobalState: State with complete workflow setup

    Example:
        def test_download(api_test_client, complete_workflow_state):
            # State already has file uploaded and converted
            response = api_test_client.get("/api/download/nwb")
            assert response.status_code == 200
    """
    nwb_file = create_test_nwb_file(tmp_path, "workflow_test.nwb")
    global_state.uploaded_file_path = str(nwb_file)
    global_state.status = ConversionStatus.VALIDATING
    global_state.add_log("INFO", "File uploaded successfully")
    global_state.add_log("INFO", "Conversion completed")
    global_state.add_log("INFO", "Validation in progress")
    return global_state


@pytest.fixture
def mock_file_upload():
    """
    Create mock file upload data for testing.

    Returns:
        tuple: (filename, file_content, content_type) for file upload

    Example:
        def test_upload_endpoint(api_test_client, mock_file_upload):
            filename, content, content_type = mock_file_upload
            response = api_test_client.post(
                "/api/upload",
                files={"file": (filename, content, content_type)}
            )
            assert response.status_code == 200
    """
    return ("test_recording.nwb", b"mock nwb file content" * 50, "application/octet-stream")


@pytest.fixture
def mock_validation_response():
    """
    Create mock validation API response for testing.

    Returns:
        dict: Standard validation response structure

    Example:
        def test_validation_endpoint(api_test_client, mock_validation_response):
            # Use as expected response structure
            expected_keys = set(mock_validation_response.keys())
            response = api_test_client.get("/api/validate")
            assert set(response.json().keys()) == expected_keys
    """
    return {
        "is_valid": False,
        "issues": [
            {
                "severity": "critical",
                "message": "Missing required field",
                "location": "/",
                "check_name": "check_required_field",
            }
        ],
        "summary": {"critical": 1, "error": 0, "warning": 0, "info": 0},
        "overall_status": "FAILED",
    }


@pytest.fixture
def mock_conversion_response():
    """
    Create mock conversion API response for testing.

    Returns:
        dict: Standard conversion response structure

    Example:
        def test_conversion_endpoint(api_test_client, mock_conversion_response):
            expected = mock_conversion_response
            # Compare against actual response
            response = api_test_client.post("/api/convert")
            assert response.json()["status"] == expected["status"]
    """
    return {
        "status": "success",
        "message": "Conversion completed successfully",
        "output_file": "/tmp/converted.nwb",
        "format": "NWB",
        "duration_ms": 1500,
    }
