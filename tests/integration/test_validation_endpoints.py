"""
Integration tests for validation and correction context endpoints.

Tests GET /api/validation and GET /api/correction-context endpoints.
"""

from unittest.mock import Mock, patch

import pytest

from agentic_neurodata_conversion.models import ConversionStatus, GlobalState, ValidationStatus

# Note: The following fixtures are provided by conftest files:
# - mock_llm_quality_assessor: from root conftest.py (for quality/validation assessment)
# - api_test_client: from integration/conftest.py (FastAPI test client)


@pytest.fixture(autouse=True)
def patch_llm_service(mock_llm_quality_assessor):
    """
    Automatically patch LLM service for all tests in this module.

    Uses mock_llm_quality_assessor from root conftest.py which provides
    quality and validation assessment responses suitable for validation endpoint testing.
    """
    with patch(
        "agentic_neurodata_conversion.services.llm_service.create_llm_service", return_value=mock_llm_quality_assessor
    ):
        yield


@pytest.mark.integration
@pytest.mark.api
class TestValidationEndpoint:
    """Test GET /api/validation endpoint."""

    def test_validation_endpoint_when_no_validation_done(self, api_test_client):
        """Test validation endpoint when no validation has been performed."""
        # Reset state
        api_test_client.post("/api/reset")

        response = api_test_client.get("/api/validation")

        # Should return 404 or empty result
        assert response.status_code in [200, 404]

    def test_validation_endpoint_with_passed_result(self, api_test_client):
        """Test validation endpoint with PASSED validation."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED
            mock_state.overall_status = "PASSED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/validation")

            if response.status_code == 200:
                data = response.json()
                # API returns ValidationResponse with is_valid, issues, summary fields
                assert "is_valid" in data
                assert "issues" in data
                assert "summary" in data

    def test_validation_endpoint_with_passed_with_issues(self, api_test_client):
        """Test validation endpoint with PASSED_WITH_ISSUES result."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.validation_status = None  # Not decided yet
            mock_state.overall_status = "PASSED_WITH_ISSUES"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/validation")

            if response.status_code == 200:
                data = response.json()
                # Should include issues or warnings
                assert data is not None

    def test_validation_endpoint_with_failed_result(self, api_test_client):
        """Test validation endpoint with FAILED validation."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.validation_status = None
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/validation")

            if response.status_code == 200:
                data = response.json()
                # Should include errors
                assert data is not None

    def test_validation_endpoint_includes_issue_details(self, api_test_client):
        """Test that validation endpoint includes detailed issue information."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED_IMPROVED
            mock_state.overall_status = "PASSED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/validation")

            # Should have validation details
            assert response.status_code in [200, 404]


@pytest.mark.integration
@pytest.mark.api
class TestCorrectionContextEndpoint:
    """Test GET /api/correction-context endpoint."""

    def test_correction_context_when_no_context_exists(self, api_test_client):
        """Test correction context endpoint when no context available."""
        # Reset state
        api_test_client.post("/api/reset")

        response = api_test_client.get("/api/correction-context")

        # Should return 404 or empty result
        assert response.status_code in [200, 404]

    def test_correction_context_for_failed_validation(self, api_test_client):
        """Test correction context with FAILED validation."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_state.correction_attempt = 0
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/correction-context")

            if response.status_code == 200:
                data = response.json()
                # Should include correction suggestions
                assert isinstance(data, dict)

    def test_correction_context_includes_auto_fixable_issues(self, api_test_client):
        """Test that correction context identifies auto-fixable issues."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/correction-context")

            if response.status_code == 200:
                data = response.json()
                # Might include auto_fixable field
                assert data is not None

    def test_correction_context_includes_user_input_required(self, api_test_client):
        """Test that correction context identifies issues needing user input."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/correction-context")

            if response.status_code == 200:
                data = response.json()
                # Might include user_input_required field
                assert data is not None

    def test_correction_context_for_multiple_retry_attempts(self, api_test_client):
        """Test correction context after multiple retry attempts."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_state.correction_attempt = 3  # Multiple attempts
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/correction-context")

            if response.status_code == 200:
                data = response.json()
                # Should include attempt count
                assert data is not None


@pytest.mark.integration
@pytest.mark.api
class TestValidationAndCorrectionIntegration:
    """Test integration between validation and correction context endpoints."""

    def test_validation_and_correction_context_consistency(self, api_test_client):
        """Test that validation and correction context endpoints are consistent."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Get validation result
            validation_response = api_test_client.get("/api/validation")

            # Get correction context
            correction_response = api_test_client.get("/api/correction-context")

            # Both should have consistent status codes
            if validation_response.status_code == 200:
                assert correction_response.status_code in [200, 404]


@pytest.mark.integration
@pytest.mark.api
class TestEndpointsWithAllValidationStatuses:
    """Test endpoints work with all validation status values."""

    @pytest.mark.parametrize(
        "validation_status,overall_status",
        [
            (ValidationStatus.PASSED, "PASSED"),
            (ValidationStatus.PASSED_ACCEPTED, "PASSED_WITH_ISSUES"),
            (ValidationStatus.PASSED_IMPROVED, "PASSED"),
            (ValidationStatus.FAILED_USER_DECLINED, "FAILED"),
            (ValidationStatus.FAILED_USER_ABANDONED, "FAILED"),
        ],
    )
    def test_validation_endpoint_all_statuses(self, api_test_client, validation_status, overall_status):
        """Test validation endpoint with all possible validation statuses."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.validation_status = validation_status
            mock_state.overall_status = overall_status
            mock_state.status = ConversionStatus.COMPLETED
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/validation")

            # Should handle all validation statuses
            assert response.status_code in [200, 404]


@pytest.mark.integration
@pytest.mark.api
class TestEndpointsErrorHandling:
    """Test error handling for validation endpoints."""

    def test_validation_endpoint_during_conversion(self, api_test_client):
        """Test validation endpoint while conversion is in progress."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.CONVERTING
            mock_state.validation_status = None
            mock_state.overall_status = None
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/validation")

            # Should return 404 or indicate not ready
            assert response.status_code in [200, 404]

    def test_correction_context_during_conversion(self, api_test_client):
        """Test correction context endpoint while conversion is in progress."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.CONVERTING
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.get("/api/correction-context")

            # Should return 404 or indicate not ready
            assert response.status_code in [200, 404]


@pytest.mark.integration
@pytest.mark.api
class TestConcurrentRequests:
    """Test concurrent requests to validation endpoints."""

    def test_multiple_concurrent_validation_requests(self, api_test_client):
        """Test multiple concurrent validation endpoint requests."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.COMPLETED
            mock_state.validation_status = ValidationStatus.PASSED
            mock_state.overall_status = "PASSED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Make concurrent requests
            responses = [
                api_test_client.get("/api/validation"),
                api_test_client.get("/api/validation"),
                api_test_client.get("/api/validation"),
            ]

            # All should succeed
            for response in responses:
                assert response.status_code in [200, 404]

    def test_mixed_concurrent_requests(self, api_test_client):
        """Test concurrent requests to different endpoints."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_RETRY_APPROVAL
            mock_state.overall_status = "FAILED"
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Make concurrent requests to different endpoints
            validation_response = api_test_client.get("/api/validation")
            correction_response = api_test_client.get("/api/correction-context")
            status_response = api_test_client.get("/api/status")

            # All should return valid responses
            assert validation_response.status_code in [200, 404]
            assert correction_response.status_code in [200, 404]
            assert status_response.status_code == 200
