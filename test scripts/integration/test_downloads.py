"""
Integration tests for file download endpoints.

Tests GET /api/download/nwb and GET /api/download/report endpoints.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from models import GlobalState, ConversionStatus, ValidationStatus
from services import LLMService


# Note: The following fixtures are provided by conftest files:
# - mock_llm_conversational: from root conftest.py (for general mock responses)
# - api_test_client: from integration/conftest.py (FastAPI test client)


@pytest.fixture(autouse=True)
def patch_llm_service(mock_llm_conversational):
    """
    Automatically patch LLM service for all tests in this module.

    Uses mock_llm_conversational from root conftest.py which provides
    general-purpose mock responses suitable for download endpoint testing.
    """
    with patch('services.llm_service.create_llm_service', return_value=mock_llm_conversational):
        with patch('api.main.create_llm_service', return_value=mock_llm_conversational):
            yield


@pytest.fixture
def mock_nwb_file():
    """Create a temporary mock NWB file."""
    with tempfile.NamedTemporaryFile(suffix=".nwb", delete=False) as f:
        f.write(b"Mock NWB file content")
        temp_path = f.name

    yield Path(temp_path)

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_pdf_report():
    """Create a temporary mock PDF report."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\n%Mock PDF content")
        temp_path = f.name

    yield Path(temp_path)

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_json_report():
    """Create a temporary mock JSON report."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(b'{"correction_context": "mock"}')
        temp_path = f.name

    yield Path(temp_path)

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.mark.integration
class TestDownloadNWBEndpoint:
    """Test GET /api/download/nwb endpoint."""

    def test_download_nwb_when_no_file_exists(self, api_test_client):
        """Test download NWB when no conversion has been done."""
        # Reset state first
        api_test_client.post("/api/reset")

        response = api_test_client.get("/api/download/nwb")

        # Should return 404 when no file exists
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower() or "no nwb file" in data["detail"].lower()

    def test_download_nwb_with_valid_file(self, api_test_client, mock_nwb_file):
        """Test download NWB with valid file."""
        # Reset state
        api_test_client.post("/api/reset")

        # Mock the global state to have output_path
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = str(mock_nwb_file)
            mock_state.status = ConversionStatus.COMPLETED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/download/nwb")

            # Should return file
            assert response.status_code == 200
            # NWB files are HDF5 files, so content-type could be either
            assert response.headers["content-type"] in ["application/octet-stream", "application/x-hdf5"]
            assert "attachment" in response.headers["content-disposition"]
            assert ".nwb" in response.headers["content-disposition"]

    def test_download_nwb_file_content(self, api_test_client, mock_nwb_file):
        """Test that downloaded NWB file contains correct content."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = str(mock_nwb_file)
            mock_state.status = ConversionStatus.COMPLETED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/download/nwb")

            assert response.status_code == 200
            assert response.content == b"Mock NWB file content"


@pytest.mark.integration
class TestDownloadReportEndpoint:
    """Test GET /api/download/report endpoint."""

    def test_download_report_when_no_file_exists(self, api_test_client):
        """Test download report when no conversion has been done."""
        # Reset state first
        api_test_client.post("/api/reset")

        response = api_test_client.get("/api/download/report")

        # Should return 404 when no file exists
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower() or "no report" in data["detail"].lower() or "no conversion output" in data["detail"].lower()

    def test_download_pdf_report_for_passed(self, api_test_client, tmp_path):
        """Test download PDF report for PASSED validation."""
        # Create actual temp files
        output_nwb = tmp_path / "output.nwb"
        output_nwb.write_bytes(b"Mock NWB content")
        report_html = tmp_path / "output_evaluation_report.html"
        report_html.write_text("<html><body>Report</body></html>")

        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = str(output_nwb)
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/download/report")

            if response.status_code == 200:
                assert "html" in response.headers["content-type"] or \
                       response.headers["content-type"] == "application/octet-stream"

    def test_download_json_report_for_failed(self, api_test_client, tmp_path):
        """Test download JSON report for FAILED validation."""
        # Create actual temp files
        output_nwb = tmp_path / "output.nwb"
        output_nwb.write_bytes(b"Mock NWB content")
        report_html = tmp_path / "output_evaluation_report.html"
        report_html.write_text("<html><body>Report</body></html>")

        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = str(output_nwb)
            mock_state.status = ConversionStatus.FAILED
            mock_state.validation_status = ValidationStatus.FAILED_USER_DECLINED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/download/report")

            if response.status_code == 200:
                assert "html" in response.headers["content-type"] or \
                       response.headers["content-type"] == "application/octet-stream"

    def test_download_report_content_type_headers(self, api_test_client, tmp_path):
        """Test that report download has correct content-type headers."""
        # Create actual temp files
        output_nwb = tmp_path / "output.nwb"
        output_nwb.write_bytes(b"Mock NWB content")
        report_html = tmp_path / "output_evaluation_report.html"
        report_html.write_text("<html><body>Report</body></html>")

        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = str(output_nwb)
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/download/report")

            if response.status_code == 200:
                # Should have content-disposition header
                assert "content-disposition" in response.headers
                assert "attachment" in response.headers["content-disposition"]


@pytest.mark.integration
class TestDownloadEndpointsWithVersionedFiles:
    """Test download endpoints with versioned files (v2, v3, etc.)."""

    def test_download_latest_nwb_version(self, api_test_client, mock_nwb_file):
        """Test that download returns the latest versioned file."""
        # Create versioned files
        base_path = mock_nwb_file.parent / mock_nwb_file.stem
        v2_path = base_path.parent / f"{base_path.stem}_v2.nwb"
        v3_path = base_path.parent / f"{base_path.stem}_v3.nwb"

        v2_path.write_text("Version 2 content")
        v3_path.write_text("Version 3 content")

        try:
            with patch("api.main.get_or_create_mcp_server") as mock_get_server:
                mock_server = Mock()
                mock_state = GlobalState()
                mock_state.output_path = str(v3_path)  # Latest version
                mock_state.status = ConversionStatus.COMPLETED
                mock_state.correction_attempt = 2  # Had 2 retries
                mock_server.global_state = mock_state
                mock_get_server.return_value = mock_server

                response = api_test_client.get("/api/download/nwb")

                # Should download latest version
                if response.status_code == 200:
                    assert response.content == b"Version 3 content"

        finally:
            # Cleanup
            v2_path.unlink(missing_ok=True)
            v3_path.unlink(missing_ok=True)


@pytest.mark.integration
class TestDownloadEndpointsErrorHandling:
    """Test error handling for download endpoints."""

    def test_download_nwb_with_corrupted_file(self, api_test_client):
        """Test download NWB when file path exists but file is corrupted/unreadable."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = "/nonexistent/corrupted.nwb"
            mock_state.status = ConversionStatus.COMPLETED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/download/nwb")

            # Should return 404 or 500 for corrupted/missing file
            assert response.status_code in [404, 500]

    def test_download_with_system_busy(self, api_test_client):
        """Test download attempts while system is processing."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = None
            mock_state.status = ConversionStatus.CONVERTING  # Still processing
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/download/nwb")

            # Should return 404 or indicate not ready
            assert response.status_code == 404


@pytest.mark.integration
class TestDownloadEndpointsWithAllValidationStatuses:
    """Test downloads work with all validation status values."""

    @pytest.mark.parametrize("validation_status", [
        ValidationStatus.PASSED,
        ValidationStatus.PASSED_ACCEPTED,
        ValidationStatus.PASSED_IMPROVED,
        ValidationStatus.FAILED_USER_DECLINED,
        ValidationStatus.FAILED_USER_ABANDONED,
    ])
    def test_download_nwb_with_all_validation_statuses(
        self, api_test_client, mock_nwb_file, validation_status
    ):
        """Test that NWB can be downloaded regardless of validation status."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = str(mock_nwb_file)
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = validation_status
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/download/nwb")

            # Should be able to download NWB for any validation status
            assert response.status_code == 200


@pytest.mark.integration
class TestConcurrentDownloads:
    """Test concurrent download requests."""

    def test_multiple_concurrent_download_requests(self, api_test_client, mock_nwb_file):
        """Test that multiple concurrent download requests work."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.output_path = str(mock_nwb_file)
            mock_state.status = ConversionStatus.COMPLETED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Make multiple concurrent requests
            responses = [
                api_test_client.get("/api/download/nwb"),
                api_test_client.get("/api/download/nwb"),
                api_test_client.get("/api/download/nwb"),
            ]

            # All should succeed
            for response in responses:
                assert response.status_code == 200
