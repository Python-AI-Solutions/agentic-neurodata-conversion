"""
Unit tests for API dependencies module.

Tests dependency injection, service initialization, and helper functions.
"""

import os
import threading
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from agentic_neurodata_conversion.api.dependencies import (
    generate_upload_welcome_message,
    get_or_create_mcp_server,
    sanitize_filename,
    validate_safe_path,
)


@pytest.mark.unit
class TestGenerateUploadWelcomeMessage:
    """Test suite for generate_upload_welcome_message function."""

    @pytest.mark.asyncio
    async def test_generate_welcome_message_without_llm(self):
        """Test fallback path when no LLM service is available (lines 71-75)."""
        result = await generate_upload_welcome_message(
            filename="test_recording.bin",
            file_size_mb=10.5,
            llm_service=None,
        )

        # Should return default fallback message
        assert result["message"] == "File uploaded successfully, conversion started"
        assert result["detected_info"] == {}

    @pytest.mark.asyncio
    async def test_generate_welcome_message_with_llm_success(self):
        """Test successful LLM-powered message generation (lines 78-129)."""
        # Create mock LLM service
        mock_llm = Mock()
        mock_llm.generate_structured_output = AsyncMock(
            return_value={
                "message": "Great! I see you've uploaded a SpikeGLX recording. This looks like electrophysiology data.",
                "detected_format": "SpikeGLX",
                "estimated_time_seconds": 120,
                "data_type": "electrophysiology",
            }
        )

        result = await generate_upload_welcome_message(
            filename="recording_g0_t0.imec0.ap.bin",
            file_size_mb=150.5,
            llm_service=mock_llm,
        )

        # Should use LLM-generated message
        assert "SpikeGLX" in result["message"]
        assert result["detected_info"]["format"] == "SpikeGLX"
        assert result["detected_info"]["estimated_time_seconds"] == 120
        assert result["detected_info"]["data_type"] == "electrophysiology"

        # Verify LLM was called with correct parameters
        mock_llm.generate_structured_output.assert_called_once()
        call_args = mock_llm.generate_structured_output.call_args
        assert "recording_g0_t0.imec0.ap.bin" in call_args.kwargs["prompt"]
        assert "150.5MB" in call_args.kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_generate_welcome_message_with_llm_partial_response(self):
        """Test LLM response with only required fields (lines 122-129)."""
        mock_llm = Mock()
        mock_llm.generate_structured_output = AsyncMock(
            return_value={
                "message": "File uploaded successfully!",
                # No optional fields
            }
        )

        result = await generate_upload_welcome_message(
            filename="data.nwb",
            file_size_mb=50.0,
            llm_service=mock_llm,
        )

        # Should handle missing optional fields gracefully
        assert result["message"] == "File uploaded successfully!"
        assert result["detected_info"]["format"] is None
        assert result["detected_info"]["estimated_time_seconds"] is None
        assert result["detected_info"]["data_type"] is None

    @pytest.mark.asyncio
    async def test_generate_welcome_message_llm_exception(self):
        """Test exception handling when LLM fails (lines 130-136)."""
        # Create mock LLM that raises exception
        mock_llm = Mock()
        mock_llm.generate_structured_output = AsyncMock(side_effect=Exception("LLM service unavailable"))

        result = await generate_upload_welcome_message(
            filename="test.bin",
            file_size_mb=10.0,
            llm_service=mock_llm,
        )

        # Should fallback to default message without crashing
        assert result["message"] == "File uploaded successfully, conversion started"
        assert result["detected_info"] == {}


@pytest.mark.unit
class TestSanitizeFilename:
    """Test suite for sanitize_filename function."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("test_file.bin")
        assert result == "test_file.bin"

    def test_sanitize_filename_removes_path_separators(self):
        """Test removal of path separators."""
        result = sanitize_filename("../../malicious/path.bin")
        # os.path.basename extracts just the filename
        assert result == "path.bin"

    def test_sanitize_filename_removes_dangerous_chars(self):
        """Test removal of dangerous characters."""
        result = sanitize_filename("file$%^&*.bin")
        assert result == "file.bin"

    def test_sanitize_filename_long_truncation(self):
        """Test filename truncation when exceeding max length (lines 160-161)."""
        # Create a filename longer than 255 characters
        long_name = "a" * 300 + ".bin"

        result = sanitize_filename(long_name)

        # Should be truncated to 255 chars with extension preserved
        assert len(result) == 255
        assert result.endswith(".bin")
        # Name part should be truncated
        expected_name_length = 255 - len(".bin")
        assert result == ("a" * expected_name_length) + ".bin"

    def test_sanitize_filename_long_truncation_no_extension(self):
        """Test filename truncation with no extension (lines 160-161)."""
        # Create a filename with no extension
        long_name = "b" * 300

        result = sanitize_filename(long_name)

        # Should be truncated to 255 chars
        assert len(result) == 255
        assert result == "b" * 255

    def test_sanitize_filename_empty_raises_exception(self):
        """Test that empty filename raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename("")

        assert exc_info.value.status_code == 400
        assert "Invalid filename" in exc_info.value.detail

    def test_sanitize_filename_dots_only_raises_exception(self):
        """Test that filename with only dots raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename("..")

        assert exc_info.value.status_code == 400
        assert "Invalid filename" in exc_info.value.detail


@pytest.mark.unit
class TestValidateSafePath:
    """Test suite for validate_safe_path function."""

    def test_validate_safe_path_valid(self, tmp_path):
        """Test validation of safe path within base directory."""
        base_dir = tmp_path / "uploads"
        base_dir.mkdir()

        file_path = base_dir / "test_file.bin"
        file_path.touch()

        result = validate_safe_path(file_path, base_dir)

        assert result == file_path.resolve()

    def test_validate_safe_path_traversal_attempt(self, tmp_path):
        """Test detection of directory traversal attack."""
        base_dir = tmp_path / "uploads"
        base_dir.mkdir()

        # Create a file outside the base directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        file_path = outside_dir / "malicious.bin"

        with pytest.raises(HTTPException) as exc_info:
            validate_safe_path(file_path, base_dir)

        assert exc_info.value.status_code == 400
        assert "path traversal detected" in exc_info.value.detail.lower()

    def test_validate_safe_path_with_relative_paths(self, tmp_path):
        """Test validation with relative paths."""
        base_dir = tmp_path / "uploads"
        base_dir.mkdir()

        # Use relative path with ..
        file_path = base_dir / ".." / "uploads" / "test.bin"

        # Should still validate correctly after resolution
        result = validate_safe_path(file_path, base_dir)
        assert result.is_relative_to(base_dir.resolve())


@pytest.mark.unit
class TestGetOrCreateMCPServer:
    """Test suite for get_or_create_mcp_server function."""

    def test_get_or_create_mcp_server_singleton(self):
        """Test that get_or_create_mcp_server returns singleton instance."""
        # Import here to avoid affecting other tests
        from agentic_neurodata_conversion.api import dependencies

        # Reset the global state
        dependencies._mcp_server = None

        # First call should create server
        server1 = get_or_create_mcp_server()
        assert server1 is not None

        # Second call should return same instance
        server2 = get_or_create_mcp_server()
        assert server2 is server1

    def test_get_or_create_mcp_server_thread_safety(self):
        """Test double-check locking pattern prevents race conditions (lines 35, 48-50)."""
        from agentic_neurodata_conversion.api import dependencies

        # Reset the global state
        dependencies._mcp_server = None

        servers = []
        errors = []

        def create_server():
            """Thread function to create server."""
            try:
                server = get_or_create_mcp_server()
                servers.append(server)
            except Exception as e:
                errors.append(e)

        # Create multiple threads that all try to initialize the server
        threads = [threading.Thread(target=create_server) for _ in range(10)]

        # Start all threads simultaneously
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have no errors
        assert len(errors) == 0

        # All threads should have gotten the same server instance
        assert len(servers) == 10
        assert all(server is servers[0] for server in servers)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"})
    def test_get_or_create_mcp_server_with_api_key(self):
        """Test server initialization with API key present."""
        from agentic_neurodata_conversion.api import dependencies

        # Reset the global state
        dependencies._mcp_server = None

        with (
            patch("agentic_neurodata_conversion.api.dependencies.create_llm_service") as mock_create_llm,
            patch(
                "agentic_neurodata_conversion.api.dependencies.register_conversion_agent"
            ) as mock_register_conversion,
            patch(
                "agentic_neurodata_conversion.api.dependencies.register_evaluation_agent"
            ) as mock_register_evaluation,
            patch(
                "agentic_neurodata_conversion.api.dependencies.register_conversation_agent"
            ) as mock_register_conversation,
        ):
            mock_llm = Mock()
            mock_create_llm.return_value = mock_llm

            server = get_or_create_mcp_server()

            # Verify LLM service was created with correct parameters
            mock_create_llm.assert_called_once_with(
                provider="anthropic",
                api_key="test-key-123",
            )

            # Verify all agents were registered with LLM service (lines 48-50)
            mock_register_conversion.assert_called_once()
            assert mock_register_conversion.call_args.kwargs["llm_service"] == mock_llm

            mock_register_evaluation.assert_called_once()
            assert mock_register_evaluation.call_args.kwargs["llm_service"] == mock_llm

            mock_register_conversation.assert_called_once()
            assert mock_register_conversation.call_args.kwargs["llm_service"] == mock_llm

            assert server is not None

    @patch.dict(os.environ, {}, clear=True)
    def test_get_or_create_mcp_server_without_api_key(self):
        """Test server initialization without API key."""
        from agentic_neurodata_conversion.api import dependencies

        # Reset the global state
        dependencies._mcp_server = None

        with (
            patch("agentic_neurodata_conversion.api.dependencies.create_llm_service") as mock_create_llm,
            patch(
                "agentic_neurodata_conversion.api.dependencies.register_conversion_agent"
            ) as mock_register_conversion,
        ):
            server = get_or_create_mcp_server()

            # LLM service should not be created
            mock_create_llm.assert_not_called()

            # Agents should still be registered but with None as llm_service
            mock_register_conversion.assert_called_once()
            assert mock_register_conversion.call_args.kwargs["llm_service"] is None

            assert server is not None
