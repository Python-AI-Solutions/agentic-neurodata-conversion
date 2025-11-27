"""Unit tests for downloads router endpoints.

Tests download/nwb, reports/view, and download/report endpoints
with focus on error handling, edge cases, and workflow_trace integration.
"""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentic_neurodata_conversion.api.routers.downloads import router

# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_nwb_file(tmp_path):
    """Create a temporary NWB file for testing."""
    nwb_file = tmp_path / "test.nwb"
    nwb_file.write_bytes(b"Mock NWB file content")
    return nwb_file


@pytest.fixture
def mock_html_report(tmp_path):
    """Create a temporary HTML report for testing."""
    html_file = tmp_path / "test_evaluation_report.html"
    html_file.write_text("<html><body>Mock HTML Report</body></html>", encoding="utf-8")
    return html_file


@pytest.fixture
def mock_pdf_report(tmp_path):
    """Create a temporary PDF report for testing."""
    pdf_file = tmp_path / "test_evaluation_report.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%Mock PDF content")
    return pdf_file


@pytest.fixture
def mock_json_report(tmp_path):
    """Create a temporary JSON report for testing."""
    json_file = tmp_path / "test_correction_context.json"
    json_file.write_text('{"correction_context": "mock"}', encoding="utf-8")
    return json_file


@pytest.fixture
def mock_workflow_trace(tmp_path):
    """Create a temporary workflow trace JSON for testing."""
    trace_file = tmp_path / "test_workflow_trace.json"
    trace_data = {
        "metadata_provenance": {
            "experimenter": {"source": "ai_parsed", "confidence": 0.9},
            "institution": {"source": "ai_parsed", "confidence": 0.85},
        }
    }
    trace_file.write_text(json.dumps(trace_data), encoding="utf-8")
    return trace_file


# ============================================================================
# GET /api/download/nwb Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestDownloadNWB:
    """Test GET /api/download/nwb endpoint."""

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_nwb_no_output_path(self, mock_get_server):
        """Test download when output_path is None."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = None
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/nwb")

        assert response.status_code == 404
        assert "No NWB file available" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_nwb_file_not_exists(self, mock_get_server):
        """Test download when file path is set but file doesn't exist."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = "/nonexistent/path/test.nwb"
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/nwb")

        assert response.status_code == 404
        assert "NWB file not found" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_nwb_success(self, mock_get_server, mock_nwb_file):
        """Test successful NWB file download."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(mock_nwb_file)
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/nwb")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-hdf5"
        assert mock_nwb_file.name in response.headers.get("content-disposition", "")

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_nwb_empty_string_path(self, mock_get_server):
        """Test download when output_path is empty string."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = ""
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/nwb")

        assert response.status_code == 404
        assert "No NWB file available" in response.json()["detail"]


# ============================================================================
# GET /api/reports/view Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestViewHTMLReport:
    """Test GET /api/reports/view endpoint."""

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_view_report_no_output_path(self, mock_get_server):
        """Test view report when output_path is None."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = None
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/reports/view")

        assert response.status_code == 404
        assert "No conversion output available" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_view_report_empty_output_path(self, mock_get_server):
        """Test view report when output_path is empty string."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = "   "  # Whitespace that strips to empty
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/reports/view")

        assert response.status_code == 404
        assert "Output path is empty" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_view_report_no_html_file(self, mock_get_server, tmp_path):
        """Test view report when HTML file doesn't exist."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(tmp_path / "test.nwb")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/reports/view")

        assert response.status_code == 404
        assert "No HTML report available" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_view_report_html_without_workflow_trace(self, mock_get_server, mock_html_report):
        """Test view report when HTML exists but no workflow_trace."""
        mock_server = Mock()
        mock_state = Mock()
        # Set output_path to match the HTML report naming pattern
        mock_state.output_path = str(mock_html_report.parent / "test.nwb")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/reports/view")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Mock HTML Report" in response.text

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    @patch("agentic_neurodata_conversion.agents.evaluation_agent.EvaluationAgent")
    @patch("agentic_neurodata_conversion.services.report_service.ReportService")
    def test_view_report_with_workflow_trace(
        self,
        mock_report_service_class,
        mock_eval_agent_class,
        mock_get_server,
        tmp_path,
        mock_html_report,
        mock_workflow_trace,
    ):
        """Test view report with workflow_trace regeneration."""
        # Setup mocks
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(mock_html_report.parent / "test.nwb")
        mock_state.overall_status = Mock(value="PASSED")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        # Mock EvaluationAgent
        mock_eval_agent = Mock()
        mock_eval_agent._extract_file_info.return_value = {
            "nwb_version": "2.5.0",
            "experimenter": ["Test User"],
        }
        mock_eval_agent_class.return_value = mock_eval_agent

        # Mock ReportService
        mock_report_service = Mock()
        mock_report_service_class.return_value = mock_report_service

        response = client.get("/api/reports/view")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Mock HTML Report" in response.text

        # Verify report was regenerated
        mock_eval_agent._extract_file_info.assert_called_once()
        mock_report_service.generate_html_report.assert_called_once()

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_view_report_workflow_trace_without_metadata_provenance(self, mock_get_server, tmp_path, mock_html_report):
        """Test view report when workflow_trace exists but has no metadata_provenance."""
        # Create workflow trace without metadata_provenance
        trace_file = tmp_path / "test_workflow_trace.json"
        trace_file.write_text('{"some_other_data": "value"}', encoding="utf-8")

        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(mock_html_report.parent / "test.nwb")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/reports/view")

        assert response.status_code == 200
        # Should just return existing HTML without regeneration
        assert "Mock HTML Report" in response.text


# ============================================================================
# GET /api/download/report Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestDownloadReport:
    """Test GET /api/download/report endpoint."""

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_report_no_output_path(self, mock_get_server):
        """Test download report when output_path is None."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = None
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/report")

        assert response.status_code == 404
        assert "No conversion output available" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_report_empty_output_path(self, mock_get_server):
        """Test download report when output_path is empty string."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = "  "  # Whitespace
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/report")

        assert response.status_code == 404
        assert "Output path is empty" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_report_html_priority(self, mock_get_server, mock_html_report):
        """Test download report returns HTML when available (highest priority)."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(mock_html_report.parent / "test.nwb")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/report")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert mock_html_report.name in response.headers.get("content-disposition", "")

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_report_json_fallback(self, mock_get_server, mock_json_report):
        """Test download report falls back to JSON when HTML not available."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(mock_json_report.parent / "test.nwb")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/report")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert mock_json_report.name in response.headers.get("content-disposition", "")

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_report_no_file_available(self, mock_get_server, tmp_path):
        """Test download report when no report files exist."""
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(tmp_path / "test.nwb")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/report")

        assert response.status_code == 404
        assert "No report file available" in response.json()["detail"]

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_report_prefers_html_over_others(
        self, mock_get_server, tmp_path, mock_html_report, mock_pdf_report, mock_json_report
    ):
        """Test download report prefers HTML even when PDF and JSON exist."""
        # All files in same directory
        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(mock_html_report.parent / "test.nwb")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/report")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "evaluation_report.html" in response.headers.get("content-disposition", "")


# ============================================================================
# Integration/Edge Case Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestDownloadsEdgeCases:
    """Test edge cases and error scenarios."""

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_download_nwb_with_unicode_filename(self, mock_get_server, tmp_path):
        """Test download NWB with unicode characters in filename."""
        nwb_file = tmp_path / "test_文件.nwb"
        nwb_file.write_bytes(b"Mock NWB content")

        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(nwb_file)
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/download/nwb")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-hdf5"

    @patch("agentic_neurodata_conversion.api.routers.downloads.get_or_create_mcp_server")
    def test_view_report_with_special_chars_in_path(self, mock_get_server, tmp_path):
        """Test view report with special characters in path."""
        special_dir = tmp_path / "test-dir_with.special"
        special_dir.mkdir()
        html_file = special_dir / "test_evaluation_report.html"
        html_file.write_text("<html><body>Test</body></html>", encoding="utf-8")

        mock_server = Mock()
        mock_state = Mock()
        mock_state.output_path = str(special_dir / "test.nwb")
        mock_server.global_state = mock_state
        mock_get_server.return_value = mock_server

        response = client.get("/api/reports/view")

        assert response.status_code == 200
        assert "Test" in response.text
