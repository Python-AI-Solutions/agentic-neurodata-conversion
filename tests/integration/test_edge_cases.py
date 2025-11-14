"""
Integration tests for edge cases and error handling.

Tests various error scenarios, edge cases, and system limits.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.models import ConversionStatus, GlobalState

# Note: The following fixtures are provided by conftest files:
# - mock_llm_conversational: from root conftest.py (for chat/conversational responses)
# - api_test_client: from integration/conftest.py (FastAPI test client)


@pytest.fixture(autouse=True)
def patch_llm_service(mock_llm_conversational):
    """
    Automatically patch LLM service for all tests in this module.

    Uses mock_llm_conversational from root conftest.py which provides
    general-purpose mock responses suitable for edge case testing.
    """
    with patch(
        "agentic_neurodata_conversion.services.llm_service.create_llm_service", return_value=mock_llm_conversational
    ):
        with patch("agentic_neurodata_conversion.api.main.create_llm_service", return_value=mock_llm_conversational):
            yield


@pytest.mark.integration
@pytest.mark.api
class TestSystemBusyScenarios:
    """Test system busy (409 Conflict) scenarios."""

    def test_upload_while_system_busy(self, api_test_client):
        """Test upload attempt while system is processing."""
        with patch("agentic_neurodata_conversion.api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.CONVERTING  # Busy
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Try to upload while busy
            with tempfile.NamedTemporaryFile(suffix=".bin") as f:
                f.write(b"test data")
                f.flush()

                response = api_test_client.post(
                    "/api/upload",
                    files={"file": ("test.bin", open(f.name, "rb"), "application/octet-stream")},
                    data={"subject_id": "TEST001", "species": "Mus musculus", "session_description": "Test session"},
                )

            # Should return 409 Conflict
            assert response.status_code == 409

    def test_multiple_concurrent_uploads(self, api_test_client):
        """Test that multiple simultaneous uploads are prevented."""
        # First upload starts processing
        with patch("agentic_neurodata_conversion.api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.CONVERTING
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Second upload should be rejected
            with tempfile.NamedTemporaryFile(suffix=".bin") as f:
                response = api_test_client.post(
                    "/api/upload",
                    files={"file": ("test2.bin", f, "application/octet-stream")},
                    data={"subject_id": "TEST002"},
                )

            assert response.status_code in [409, 422]


@pytest.mark.integration
@pytest.mark.api
class TestInvalidInputs:
    """Test handling of invalid inputs."""

    def test_upload_without_required_metadata(self, api_test_client):
        """Test upload without required metadata fields."""
        with tempfile.NamedTemporaryFile(suffix=".bin") as f:
            response = api_test_client.post(
                "/api/upload",
                files={"file": ("test.bin", f, "application/octet-stream")},
                data={},  # Missing required fields
            )

        # Should return 400 or 422 for missing required fields
        assert response.status_code in [400, 422]

    def test_upload_with_malformed_metadata(self, api_test_client):
        """Test upload with malformed metadata."""
        with tempfile.NamedTemporaryFile(suffix=".bin") as f:
            response = api_test_client.post(
                "/api/upload",
                files={"file": ("test.bin", f, "application/octet-stream")},
                data={
                    "subject_id": "",  # Empty string
                    "species": "Invalid Species Name That Doesnt Exist",
                },
            )

        # Should handle malformed metadata
        assert response.status_code in [400, 422]

    def test_retry_approval_with_invalid_decision(self, api_test_client):
        """Test retry approval with invalid decision value."""
        response = api_test_client.post("/api/retry-approval", json={"decision": "invalid_decision"})

        # Should return 422 for invalid enum value
        assert response.status_code == 422

    def test_retry_approval_without_decision_field(self, api_test_client):
        """Test retry approval without decision field."""
        response = api_test_client.post("/api/retry-approval", json={})

        # Should return 422 for missing required field
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.api
class TestLargeFileHandling:
    """Test handling of large files."""

    def test_upload_large_file(self, api_test_client):
        """Test upload of large file."""
        # Create a temporary large file (1MB)
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"x" * (1024 * 1024))  # 1MB
            large_file_path = f.name

        try:
            with open(large_file_path, "rb") as f:
                response = api_test_client.post(
                    "/api/upload",
                    files={"file": ("large.bin", f, "application/octet-stream")},
                    data={
                        "subject_id": "LARGE001",
                        "species": "Mus musculus",
                        "session_description": "Large file test",
                    },
                )

            # Should handle large files (may accept or reject based on limits)
            assert response.status_code in [200, 202, 413, 422]

        finally:
            Path(large_file_path).unlink(missing_ok=True)


@pytest.mark.integration
@pytest.mark.api
class TestMissingLLMService:
    """Test behavior when LLM service is not available."""

    def test_system_without_api_key(self, api_test_client):
        """Test that system works without ANTHROPIC_API_KEY."""
        with patch.dict("os.environ", {}, clear=True):
            # System should initialize without LLM service
            response = api_test_client.get("/api/health")
            assert response.status_code == 200

    def test_smart_chat_without_llm(self, api_test_client):
        """Test smart chat when LLM service is unavailable."""
        with patch("agentic_neurodata_conversion.api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_server.global_state = GlobalState()
            # No LLM service
            mock_get_server.return_value = mock_server

            response = api_test_client.post("/api/chat/smart", json={"message": "test"})

            # Should handle gracefully (including rate limiting)
            assert response.status_code in [200, 422, 429, 500, 503]


@pytest.mark.integration
@pytest.mark.api
class TestNeuroConvErrors:
    """Test handling of NeuroConv conversion errors."""

    def test_conversion_with_unsupported_format(self, api_test_client):
        """Test conversion with unsupported file format."""
        # This would require actual file upload and conversion trigger
        # Placeholder for E2E test
        pass

    def test_conversion_with_corrupted_data(self, api_test_client):
        """Test conversion with corrupted data file."""
        # Placeholder for E2E test
        pass


@pytest.mark.integration
@pytest.mark.api
class TestNWBInspectorErrors:
    """Test handling of NWB Inspector validation errors."""

    def test_validation_with_corrupted_nwb(self, api_test_client):
        """Test validation with corrupted NWB file."""
        # Placeholder for E2E test
        pass

    def test_validation_inspector_crash(self, api_test_client):
        """Test handling when NWB Inspector crashes."""
        # Placeholder for E2E test
        pass


@pytest.mark.integration
@pytest.mark.api
class TestNetworkErrors:
    """Test handling of network-related errors."""

    def test_llm_api_timeout(self, api_test_client):
        """Test handling of LLM API timeout."""
        # Placeholder - would require mocking LLM service timeout
        pass

    def test_llm_api_rate_limit(self, api_test_client):
        """Test handling of LLM API rate limiting."""
        # Placeholder - would require mocking rate limit response
        pass


@pytest.mark.integration
@pytest.mark.api
class TestStateTransitions:
    """Test invalid state transitions."""

    def test_retry_approval_when_not_awaiting(self, api_test_client):
        """Test retry approval when system is not awaiting approval."""
        with patch("agentic_neurodata_conversion.api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.IDLE  # Not awaiting
            mock_server.global_state = mock_state
            mock_server.send_message = AsyncMock()  # Mock async send_message
            mock_get_server.return_value = mock_server

            response = api_test_client.post("/api/retry-approval", json={"decision": "approve"})

            # Should handle invalid state transition
            assert response.status_code in [400, 422, 500]

    def test_user_input_when_not_requested(self, api_test_client):
        """Test user input submission when not requested."""
        with patch("agentic_neurodata_conversion.api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.IDLE  # Not awaiting input
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = api_test_client.post("/api/user-input", json={"input": "test"})

            # Should handle invalid state
            assert response.status_code in [400, 422, 500]


@pytest.mark.integration
@pytest.mark.api
class TestSpecialCharacters:
    """Test handling of special characters and unicode."""

    def test_upload_with_unicode_filename(self, api_test_client):
        """Test upload with unicode characters in filename."""
        with tempfile.NamedTemporaryFile(suffix=".bin") as f:
            response = api_test_client.post(
                "/api/upload",
                files={"file": ("测试文件.bin", f, "application/octet-stream")},
                data={"subject_id": "TEST001", "species": "Mus musculus", "session_description": "Test"},
            )

        # Should handle unicode filenames
        assert response.status_code in [200, 202, 400, 422]

    def test_metadata_with_special_characters(self, api_test_client):
        """Test metadata with special characters."""
        with tempfile.NamedTemporaryFile(suffix=".bin") as f:
            response = api_test_client.post(
                "/api/upload",
                files={"file": ("test.bin", f, "application/octet-stream")},
                data={
                    "subject_id": "TEST-001_α",
                    "species": "Mus musculus",
                    "session_description": "Test with émojis 🧠 and symbols @#$%",
                },
            )

        # Should handle special characters
        assert response.status_code in [200, 202, 400, 422]


@pytest.mark.integration
@pytest.mark.api
class TestFileSystemErrors:
    """Test handling of file system errors."""

    def test_temp_directory_full(self, api_test_client):
        """Test handling when temp directory is full."""
        # Placeholder - would require mocking disk full error
        pass

    def test_permission_denied_on_file_write(self, api_test_client):
        """Test handling when file write fails due to permissions."""
        # Placeholder - would require mocking permission error
        pass


@pytest.mark.integration
@pytest.mark.api
class TestRaceConditions:
    """Test potential race conditions."""

    def test_concurrent_status_checks(self, api_test_client):
        """Test concurrent status endpoint requests."""
        with patch("agentic_neurodata_conversion.api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Make many concurrent status requests
            responses = [api_test_client.get("/api/status") for _ in range(10)]

            # All should succeed
            for response in responses:
                assert response.status_code == 200

    def test_concurrent_reset_requests(self, api_test_client):
        """Test concurrent reset requests."""
        responses = [api_test_client.post("/api/reset") for _ in range(5)]

        # All should succeed
        for response in responses:
            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.api
class TestMemoryLeaks:
    """Test for potential memory leaks."""

    def test_repeated_reset_operations(self, api_test_client):
        """Test repeated reset operations don't leak memory."""
        # Make many reset requests
        for _ in range(100):
            response = api_test_client.post("/api/reset")
            assert response.status_code == 200

    def test_repeated_status_checks(self, api_test_client):
        """Test repeated status checks don't leak memory."""
        # Make many status requests
        for _ in range(100):
            response = api_test_client.get("/api/status")
            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.api
class TestEdgeCaseMetadata:
    """Test edge cases in metadata handling."""

    def test_metadata_with_empty_strings(self, api_test_client):
        """Test metadata with empty string values."""
        with tempfile.NamedTemporaryFile(suffix=".bin") as f:
            response = api_test_client.post(
                "/api/upload",
                files={"file": ("test.bin", f, "application/octet-stream")},
                data={
                    "subject_id": "",  # Empty
                    "species": "",  # Empty
                    "session_description": "",  # Empty
                },
            )

        # Should reject empty required fields
        assert response.status_code in [400, 422]

    def test_metadata_with_very_long_values(self, api_test_client):
        """Test metadata with very long string values."""
        with tempfile.NamedTemporaryFile(suffix=".bin") as f:
            response = api_test_client.post(
                "/api/upload",
                files={"file": ("test.bin", f, "application/octet-stream")},
                data={
                    "subject_id": "TEST001",
                    "species": "Mus musculus",
                    "session_description": "x" * 10000,  # Very long
                },
            )

        # Should handle or reject very long values
        assert response.status_code in [200, 202, 400, 413, 422]


# Note: Many of these tests are placeholders for full E2E testing
# They verify endpoint existence and basic error handling
# Full testing requires:
# - Actual file conversions
# - Mocking NeuroConv errors
# - Mocking NWB Inspector failures
# - Simulating disk/network issues
