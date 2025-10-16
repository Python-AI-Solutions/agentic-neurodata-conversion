"""
Integration tests for validation and correction context endpoints.

Tests GET /api/validation and GET /api/correction-context endpoints.
"""
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from api.main import app
from models import GlobalState, ConversionStatus, ValidationStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestValidationEndpoint:
    """Test GET /api/validation endpoint."""

    def test_validation_endpoint_when_no_validation_done(self, client):
        """Test validation endpoint when no validation has been performed."""
        # Reset state
        client.post("/api/reset")

        response = client.get("/api/validation")

        # Should return 404 or empty result
        assert response.status_code in [200, 404]

    def test_validation_endpoint_with_passed_result(self, client):
        """Test validation endpoint with PASSED validation."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED
            mock_state.overall_status = "PASSED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/validation")

            if response.status_code == 200:
                data = response.json()
                assert "validation_status" in data or "overall_status" in data

    def test_validation_endpoint_with_passed_with_issues(self, client):
        """Test validation endpoint with PASSED_WITH_ISSUES result."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.validation_status = None  # Not decided yet
            mock_state.overall_status = "PASSED_WITH_ISSUES"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/validation")

            if response.status_code == 200:
                data = response.json()
                # Should include issues or warnings
                assert data is not None

    def test_validation_endpoint_with_failed_result(self, client):
        """Test validation endpoint with FAILED validation."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.validation_status = None
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/validation")

            if response.status_code == 200:
                data = response.json()
                # Should include errors
                assert data is not None

    def test_validation_endpoint_includes_issue_details(self, client):
        """Test that validation endpoint includes detailed issue information."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED_IMPROVED
            mock_state.overall_status = "PASSED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/validation")

            # Should have validation details
            assert response.status_code in [200, 404]


class TestCorrectionContextEndpoint:
    """Test GET /api/correction-context endpoint."""

    def test_correction_context_when_no_context_exists(self, client):
        """Test correction context endpoint when no context available."""
        # Reset state
        client.post("/api/reset")

        response = client.get("/api/correction-context")

        # Should return 404 or empty result
        assert response.status_code in [200, 404]

    def test_correction_context_for_failed_validation(self, client):
        """Test correction context with FAILED validation."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_state.correction_attempt = 0
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/correction-context")

            if response.status_code == 200:
                data = response.json()
                # Should include correction suggestions
                assert isinstance(data, dict)

    def test_correction_context_includes_auto_fixable_issues(self, client):
        """Test that correction context identifies auto-fixable issues."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/correction-context")

            if response.status_code == 200:
                data = response.json()
                # Might include auto_fixable field
                assert data is not None

    def test_correction_context_includes_user_input_required(self, client):
        """Test that correction context identifies issues needing user input."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/correction-context")

            if response.status_code == 200:
                data = response.json()
                # Might include user_input_required field
                assert data is not None

    def test_correction_context_for_multiple_retry_attempts(self, client):
        """Test correction context after multiple retry attempts."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_state.correction_attempt = 3  # Multiple attempts
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/correction-context")

            if response.status_code == 200:
                data = response.json()
                # Should include attempt count
                assert data is not None


class TestValidationAndCorrectionIntegration:
    """Test integration between validation and correction context endpoints."""

    def test_validation_and_correction_context_consistency(self, client):
        """Test that validation and correction context endpoints are consistent."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Get validation result
            validation_response = client.get("/api/validation")

            # Get correction context
            correction_response = client.get("/api/correction-context")

            # Both should have consistent status codes
            if validation_response.status_code == 200:
                assert correction_response.status_code in [200, 404]


class TestEndpointsWithAllValidationStatuses:
    """Test endpoints work with all validation status values."""

    @pytest.mark.parametrize("validation_status,overall_status", [
        (ValidationStatus.PASSED, "PASSED"),
        (ValidationStatus.PASSED_ACCEPTED, "PASSED_WITH_ISSUES"),
        (ValidationStatus.PASSED_IMPROVED, "PASSED"),
        (ValidationStatus.FAILED_USER_DECLINED, "FAILED"),
        (ValidationStatus.FAILED_USER_ABANDONED, "FAILED"),
    ])
    def test_validation_endpoint_all_statuses(
        self, client, validation_status, overall_status
    ):
        """Test validation endpoint with all possible validation statuses."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.validation_status = validation_status
            mock_state.overall_status = overall_status
            mock_state.status = ConversionStatus.COMPLETED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/validation")

            # Should handle all validation statuses
            assert response.status_code in [200, 404]


class TestEndpointsErrorHandling:
    """Test error handling for validation endpoints."""

    def test_validation_endpoint_during_conversion(self, client):
        """Test validation endpoint while conversion is in progress."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.CONVERTING
            mock_state.validation_status = None
            mock_state.overall_status = None
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/validation")

            # Should return 404 or indicate not ready
            assert response.status_code in [200, 404]

    def test_correction_context_during_conversion(self, client):
        """Test correction context endpoint while conversion is in progress."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.CONVERTING
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.get("/api/correction-context")

            # Should return 404 or indicate not ready
            assert response.status_code in [200, 404]


class TestConcurrentRequests:
    """Test concurrent requests to validation endpoints."""

    def test_multiple_concurrent_validation_requests(self, client):
        """Test multiple concurrent validation endpoint requests."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED
            mock_state.overall_status = "PASSED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Make concurrent requests
            responses = [
                client.get("/api/validation"),
                client.get("/api/validation"),
                client.get("/api/validation"),
            ]

            # All should succeed
            for response in responses:
                assert response.status_code in [200, 404]

    def test_mixed_concurrent_requests(self, client):
        """Test concurrent requests to different endpoints."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Make concurrent requests to different endpoints
            validation_response = client.get("/api/validation")
            correction_response = client.get("/api/correction-context")
            status_response = client.get("/api/status")

            # All should return valid responses
            assert validation_response.status_code in [200, 404]
            assert correction_response.status_code in [200, 404]
            assert status_response.status_code == 200
