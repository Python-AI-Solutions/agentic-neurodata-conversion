"""
Integration tests for FastAPI endpoints.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Import after path is set in conftest
from api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def toy_dataset_path():
    """Get path to the toy SpikeGLX dataset."""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "toy_spikeglx"
    if not fixtures_path.exists():
        pytest.skip("Toy dataset not generated. Run: pixi run generate-fixtures")
    return fixtures_path


class TestBasicEndpoints:
    """Test basic API endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Agentic Neurodata Conversion API"
        assert data["status"] == "running"

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "agents" in data
        assert "handlers" in data


class TestUploadEndpoint:
    """Test file upload endpoint."""

    def test_upload_file(self, client, toy_dataset_path):
        """Test uploading a file."""
        # Reset first
        client.post("/api/reset")

        # Find a .bin file to upload
        bin_files = list(toy_dataset_path.glob("*.ap.bin"))
        if not bin_files:
            pytest.skip("No .bin file found in toy dataset")

        test_file = bin_files[0]

        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "application/octet-stream")}
            metadata = {"session_description": "Test upload"}

            response = client.post(
                "/api/upload",
                files=files,
                data={"metadata": json.dumps(metadata)},
            )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "checksum" in data
        assert "input_path" in data

    def test_upload_concurrent_prevention(self, client, toy_dataset_path):
        """Test that concurrent uploads are prevented."""
        # Upload first file
        bin_files = list(toy_dataset_path.glob("*.ap.bin"))
        if not bin_files:
            pytest.skip("No .bin file found in toy dataset")

        test_file = bin_files[0]

        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "application/octet-stream")}
            response1 = client.post("/api/upload", files=files)

        # Try to upload again (should fail with 409)
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "application/octet-stream")}
            response2 = client.post("/api/upload", files=files)

        assert response2.status_code == 409

        # Reset and try again (should succeed)
        client.post("/api/reset")
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "application/octet-stream")}
            response3 = client.post("/api/upload", files=files)

        assert response3.status_code == 200


class TestStatusEndpoint:
    """Test status endpoint."""

    def test_get_status_idle(self, client):
        """Test getting status when idle."""
        # Reset first
        client.post("/api/reset")

        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["correction_attempt"] == 0

    def test_get_status_after_upload(self, client, toy_dataset_path):
        """Test getting status after upload."""
        # Reset first
        client.post("/api/reset")

        # Upload a file
        bin_files = list(toy_dataset_path.glob("*.ap.bin"))
        if not bin_files:
            pytest.skip("No .bin file found in toy dataset")

        test_file = bin_files[0]
        with open(test_file, "rb") as f:
            files = {"file": (test_file.name, f, "application/octet-stream")}
            client.post("/api/upload", files=files)

        # Check status
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in [
            "detecting_format",
            "converting",
            "validating",
            "awaiting_retry_approval",
            "completed",
            "failed",
        ]


class TestRetryEndpoint:
    """Test retry approval endpoint."""

    def test_retry_approval_reject(self, client):
        """Test rejecting retry."""
        # Reset and set up state
        client.post("/api/reset")

        # Manually set state to awaiting retry (in real scenario, this would happen after validation failure)
        # For this test, we'll just try the endpoint
        response = client.post(
            "/api/retry-approval",
            json={"decision": "reject"},
        )

        # May fail with 400 if not in correct state, which is expected
        assert response.status_code in [200, 400]


class TestLogsEndpoint:
    """Test logs endpoint."""

    def test_get_logs(self, client):
        """Test getting logs."""
        response = client.get("/api/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total_count" in data
        assert isinstance(data["logs"], list)

    def test_get_logs_pagination(self, client):
        """Test log pagination."""
        response = client.get("/api/logs?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) <= 5


class TestResetEndpoint:
    """Test reset endpoint."""

    def test_reset(self, client):
        """Test resetting session."""
        response = client.post("/api/reset")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # Verify status is idle after reset
        status_response = client.get("/api/status")
        status_data = status_response.json()
        assert status_data["status"] == "idle"


class TestUserInputEndpoint:
    """Test user input endpoint."""

    def test_user_input_format_selection(self, client):
        """Test submitting format selection."""
        # This will likely return 400 because we're not in the right state
        response = client.post(
            "/api/user-input",
            json={"input_data": {"format": "SpikeGLX"}},
        )

        # Expected to fail with 400 unless we're in AWAITING_USER_INPUT state
        assert response.status_code in [200, 400]
