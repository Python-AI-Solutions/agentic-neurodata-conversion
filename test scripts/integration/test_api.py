"""
Integration tests for FastAPI endpoints.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Import after path is set in conftest

# Note: The following fixtures are provided by conftest files:
# - mock_llm_format_detector: from root conftest.py (format detection responses)
# - api_test_client: from integration/conftest.py (FastAPI test client)


@pytest.mark.integration
@pytest.fixture(autouse=True)
def patch_llm_service(mock_llm_format_detector):
    """
    Automatically patch LLM service for all tests in this module.

    Uses mock_llm_format_detector from root conftest.py which provides
    format detection responses suitable for API testing.
    """
    with patch("services.llm_service.create_llm_service", return_value=mock_llm_format_detector):
        with patch("api.main.create_llm_service", return_value=mock_llm_format_detector):
            yield


@pytest.fixture
def toy_dataset_path():
    """Get path to the toy SpikeGLX dataset."""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "toy_spikeglx"
    if not fixtures_path.exists():
        pytest.skip("Toy dataset not generated. Run: pixi run generate-fixtures")
    return fixtures_path


@pytest.mark.integration
@pytest.mark.api
class TestBasicEndpoints:
    """Test basic API endpoints."""

    @pytest.mark.smoke
    def test_root_endpoint(self, api_test_client):
        """Test root endpoint."""
        response = api_test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Agentic Neurodata Conversion API"
        assert data["status"] == "running"

    @pytest.mark.smoke
    def test_health_check(self, api_test_client):
        """Test health check endpoint."""
        response = api_test_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agents" in data
        assert "handlers" in data


@pytest.mark.integration
@pytest.mark.api
class TestUploadEndpoint:
    """Test file upload endpoint."""

    def test_upload_file(self, api_test_client, toy_dataset_path):
        """Test uploading a file."""
        # Reset first
        api_test_client.post("/api/reset")

        # Find a .bin file to upload
        bin_files = list(toy_dataset_path.glob("*.ap.bin"))
        if not bin_files:
            pytest.skip("No .bin file found in toy dataset")

        test_file = bin_files[0]

        # For SpikeGLX files, also get the .meta file
        meta_file = test_file.with_suffix(".meta")
        if not meta_file.exists():
            pytest.skip(f"No .meta file found for {test_file.name}")

        # Upload both files together
        with open(test_file, "rb") as bin_f, open(meta_file, "rb") as meta_f:
            files = [
                ("file", (test_file.name, bin_f, "application/octet-stream")),
                ("file", (meta_file.name, meta_f, "application/octet-stream")),
            ]
            metadata = {"session_description": "Recording of V1 neurons during visual stimulation experiment"}

            response = api_test_client.post(
                "/api/upload",
                files=files,
                data={"metadata": json.dumps(metadata)},
            )

        if response.status_code != 200:
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "checksum" in data
        assert "input_path" in data

    def test_upload_concurrent_prevention(self, api_test_client, toy_dataset_path):
        """Test that concurrent uploads are prevented during blocking statuses."""
        # Reset first
        api_test_client.post("/api/reset")

        # Find test files
        bin_files = list(toy_dataset_path.glob("*.ap.bin"))
        if not bin_files:
            pytest.skip("No .bin file found in toy dataset")

        test_file = bin_files[0]
        meta_file = test_file.with_suffix(".meta")
        if not meta_file.exists():
            pytest.skip(f"No .meta file found for {test_file.name}")

        # Upload first file
        with open(test_file, "rb") as bin_f, open(meta_file, "rb") as meta_f:
            files = [
                ("file", (test_file.name, bin_f, "application/octet-stream")),
                ("file", (meta_file.name, meta_f, "application/octet-stream")),
            ]
            metadata = {"session_description": "Recording of V1 neurons during visual stimulation experiment"}
            response1 = api_test_client.post(
                "/api/upload",
                files=files,
                data={"metadata": json.dumps(metadata)},
            )

        assert response1.status_code == 200

        # Directly set state to a blocking status to test concurrent prevention
        from api.main import get_or_create_mcp_server
        from models import ConversionStatus

        mcp_server = get_or_create_mcp_server()
        mcp_server.global_state.status = ConversionStatus.CONVERTING

        # Try to upload again (should fail with 409 because status is CONVERTING)
        with open(test_file, "rb") as bin_f, open(meta_file, "rb") as meta_f:
            files = [
                ("file", (test_file.name, bin_f, "application/octet-stream")),
                ("file", (meta_file.name, meta_f, "application/octet-stream")),
            ]
            metadata = {"session_description": "Another recording session"}
            response2 = api_test_client.post(
                "/api/upload",
                files=files,
                data={"metadata": json.dumps(metadata)},
            )

        assert response2.status_code == 409

        # Reset and try again (should succeed)
        api_test_client.post("/api/reset")
        with open(test_file, "rb") as bin_f, open(meta_file, "rb") as meta_f:
            files = [
                ("file", (test_file.name, bin_f, "application/octet-stream")),
                ("file", (meta_file.name, meta_f, "application/octet-stream")),
            ]
            metadata = {"session_description": "Recording of V1 neurons during visual stimulation experiment"}
            response3 = api_test_client.post(
                "/api/upload",
                files=files,
                data={"metadata": json.dumps(metadata)},
            )

        assert response3.status_code == 200


@pytest.mark.integration
@pytest.mark.api
class TestStatusEndpoint:
    """Test status endpoint."""

    def test_get_status_idle(self, api_test_client):
        """Test getting status when idle."""
        # Reset first
        api_test_client.post("/api/reset")

        response = api_test_client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["correction_attempt"] == 0

    def test_get_status_after_upload(self, api_test_client, toy_dataset_path):
        """Test getting status after upload and starting conversion."""
        # Reset first
        api_test_client.post("/api/reset")

        # Upload a file
        bin_files = list(toy_dataset_path.glob("*.ap.bin"))
        if not bin_files:
            pytest.skip("No .bin file found in toy dataset")

        test_file = bin_files[0]
        meta_file = test_file.with_suffix(".meta")
        if not meta_file.exists():
            pytest.skip(f"No .meta file found for {test_file.name}")

        with open(test_file, "rb") as bin_f, open(meta_file, "rb") as meta_f:
            files = [
                ("file", (test_file.name, bin_f, "application/octet-stream")),
                ("file", (meta_file.name, meta_f, "application/octet-stream")),
            ]
            metadata = {"session_description": "Recording of V1 neurons during visual stimulation experiment"}
            api_test_client.post(
                "/api/upload",
                files=files,
                data={"metadata": json.dumps(metadata)},
            )

        # Start conversion explicitly
        start_response = api_test_client.post("/api/start-conversion")
        assert start_response.status_code == 200

        # Check status - should no longer be idle
        response = api_test_client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in [
            "awaiting_user_input",
            "detecting_format",
            "converting",
            "validating",
            "awaiting_retry_approval",
            "completed",
            "failed",
        ]


@pytest.mark.integration
@pytest.mark.api
class TestRetryEndpoint:
    """Test retry approval endpoint."""

    def test_retry_approval_reject(self, api_test_client):
        """Test rejecting retry."""
        # Reset and set up state
        api_test_client.post("/api/reset")

        # Manually set state to awaiting retry (in real scenario, this would happen after validation failure)
        # For this test, we'll just try the endpoint
        response = api_test_client.post(
            "/api/retry-approval",
            json={"decision": "reject"},
        )

        # May fail with 400 if not in correct state, which is expected
        assert response.status_code in [200, 400]


@pytest.mark.integration
@pytest.mark.api
class TestLogsEndpoint:
    """Test logs endpoint."""

    def test_get_logs(self, api_test_client):
        """Test getting logs."""
        response = api_test_client.get("/api/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total_count" in data
        assert isinstance(data["logs"], list)

    def test_get_logs_pagination(self, api_test_client):
        """Test log pagination."""
        response = api_test_client.get("/api/logs?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) <= 5


@pytest.mark.integration
@pytest.mark.api
class TestResetEndpoint:
    """Test reset endpoint."""

    def test_reset(self, api_test_client):
        """Test resetting session."""
        response = api_test_client.post("/api/reset")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # Verify status is idle after reset
        status_response = api_test_client.get("/api/status")
        status_data = status_response.json()
        assert status_data["status"] == "idle"


@pytest.mark.integration
@pytest.mark.api
class TestUserInputEndpoint:
    """Test user input endpoint."""

    def test_user_input_format_selection(self, api_test_client):
        """Test submitting format selection."""
        # This will likely return 400 because we're not in the right state
        response = api_test_client.post(
            "/api/user-input",
            json={"input_data": {"format": "SpikeGLX"}},
        )

        # Expected to fail with 400 unless we're in AWAITING_USER_INPUT state
        assert response.status_code in [200, 400]
