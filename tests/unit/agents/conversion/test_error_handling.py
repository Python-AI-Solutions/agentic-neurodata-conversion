"""Unit tests for ConversionErrorHandler module.

Tests error handling and recovery workflows including:
- LLM-powered error explanations
- File context gathering (file vs directory)
- Correction application and reconversion
- File versioning during reconversion
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.agents.conversion.error_handling import ConversionErrorHandler
from agentic_neurodata_conversion.models import MCPMessage, MCPResponse
from agentic_neurodata_conversion.services.llm_service import MockLLMService

# Note: The following fixtures are provided by conftest files:
# - global_state: from root conftest.py (Fresh GlobalState for each test)
# - mock_llm_service: from root conftest.py (Mock LLM service)
# - tmp_path: from pytest (Temporary directory)


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestErrorHandlerInitialization:
    """Tests for ConversionErrorHandler initialization."""

    def test_init_with_llm_service(self):
        """Test initialization with LLM service."""
        llm_service = MockLLMService()
        handler = ConversionErrorHandler(llm_service=llm_service)

        assert handler._llm_service is llm_service

    def test_init_without_llm_service(self):
        """Test initialization without LLM service."""
        handler = ConversionErrorHandler(llm_service=None)

        assert handler._llm_service is None


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestExplainConversionError:
    """Tests for explain_conversion_error method."""

    @pytest.mark.asyncio
    async def test_explain_error_without_llm_returns_none(self, global_state):
        """Test error explanation returns None when no LLM available."""
        handler = ConversionErrorHandler(llm_service=None)

        error = ValueError("Test error")
        explanation = await handler.explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path="/test/path",
            state=global_state,
        )

        assert explanation is None

    @pytest.mark.asyncio
    async def test_explain_error_with_llm_success(self, global_state):
        """Test successful error explanation with LLM."""
        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(
            return_value="The file could not be found. Please check the file path and try again."
        )

        handler = ConversionErrorHandler(llm_service=llm_service)

        error = FileNotFoundError("/test/missing.bin")
        explanation = await handler.explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path="/test/missing.bin",
            state=global_state,
        )

        assert explanation is not None
        assert "could not be found" in explanation.lower()
        assert any("user-friendly error explanation" in log.message.lower() for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_explain_error_with_file_context(self, global_state, tmp_path):
        """Test error explanation gathers file context for existing files."""
        # Create test file
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data" * 1000)  # ~9 KB

        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(return_value="Error explanation with file context.")

        handler = ConversionErrorHandler(llm_service=llm_service)

        error = RuntimeError("Conversion failed")
        explanation = await handler.explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path=str(test_file),
            state=global_state,
        )

        assert explanation is not None
        # Verify LLM was called (file context was gathered)
        assert llm_service.generate_completion.called

    @pytest.mark.asyncio
    async def test_explain_error_with_directory_context(self, global_state, tmp_path):
        """Test error explanation gathers directory context."""
        # Create test directory with files
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        (test_dir / "file1.bin").touch()
        (test_dir / "file2.meta").touch()
        (test_dir / "file3.txt").touch()

        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(return_value="Error explanation with directory context.")

        handler = ConversionErrorHandler(llm_service=llm_service)

        error = RuntimeError("Directory processing failed")
        explanation = await handler.explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path=str(test_dir),
            state=global_state,
        )

        assert explanation is not None
        assert llm_service.generate_completion.called

    @pytest.mark.asyncio
    async def test_explain_error_file_context_gathering_fails_gracefully(self, global_state):
        """Test error explanation handles file context gathering failures gracefully."""
        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(return_value="Error explanation without file context.")

        handler = ConversionErrorHandler(llm_service=llm_service)

        # Non-existent path
        error = ValueError("Test error")
        explanation = await handler.explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path="/nonexistent/path/file.bin",
            state=global_state,
        )

        # Should still succeed even if file context fails
        assert explanation is not None

    @pytest.mark.asyncio
    async def test_explain_error_with_sibling_files_context(self, global_state, tmp_path):
        """Test error explanation gathers sibling files for file input."""
        # Create test file with siblings
        test_file = tmp_path / "recording.bin"
        test_file.write_bytes(b"test")
        (tmp_path / "recording.meta").write_text("metadata")
        (tmp_path / "other.txt").write_text("other")

        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(return_value="Error with sibling context.")

        handler = ConversionErrorHandler(llm_service=llm_service)

        error = RuntimeError("Conversion error")
        explanation = await handler.explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path=str(test_file),
            state=global_state,
        )

        assert explanation is not None
        # LLM should have been called with context including sibling files
        assert llm_service.generate_completion.called

    @pytest.mark.asyncio
    async def test_explain_error_llm_failure_returns_none(self, global_state, tmp_path):
        """Test error explanation returns None when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(side_effect=RuntimeError("LLM service error"))

        handler = ConversionErrorHandler(llm_service=llm_service)

        test_file = tmp_path / "test.bin"
        test_file.touch()

        error = ValueError("Test error")
        explanation = await handler.explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path=str(test_file),
            state=global_state,
        )

        # Should return None on LLM failure
        assert explanation is None
        # Should log warning
        assert any("failed to generate error explanation" in log.message.lower() for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_explain_error_uses_correct_llm_parameters(self, global_state, tmp_path):
        """Test error explanation uses correct LLM temperature and max_tokens."""
        llm_service = MockLLMService()
        llm_service.generate_completion = AsyncMock(return_value="Explanation")

        handler = ConversionErrorHandler(llm_service=llm_service)

        test_file = tmp_path / "test.bin"
        test_file.touch()

        error = RuntimeError("Test")
        await handler.explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path=str(test_file),
            state=global_state,
        )

        # Verify LLM was called with correct parameters
        call_kwargs = llm_service.generate_completion.call_args.kwargs
        assert call_kwargs["temperature"] == 0.3  # Lower for focused explanations
        assert call_kwargs["max_tokens"] == 300


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestHandleApplyCorrections:
    """Tests for handle_apply_corrections method."""

    @pytest.fixture
    def mock_conversion_runner(self):
        """Create mock conversion runner."""
        runner = Mock()
        runner.handle_run_conversion = AsyncMock(
            return_value=MCPResponse.success_response(
                reply_to="test_id",
                result={"status": "completed", "output_path": "/output/test.nwb"},
            )
        )
        return runner

    @pytest.mark.asyncio
    async def test_apply_corrections_missing_input_path(self, global_state):
        """Test apply corrections fails when input_path is missing."""
        handler = ConversionErrorHandler()
        runner = Mock()

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {},
            },
        )

        # State has no input_path
        global_state.input_path = None

        response = await handler.handle_apply_corrections(message, global_state, runner)

        assert not response.success
        assert response.error.get("code") == "MISSING_INPUT_PATH"

    @pytest.mark.asyncio
    async def test_apply_corrections_increments_attempt_counter(self, global_state, mock_conversion_runner):
        """Test apply corrections increments correction attempt counter."""
        handler = ConversionErrorHandler()

        global_state.input_path = "/test/input.bin"
        initial_attempt = global_state.correction_attempt

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {"field1": "value1"},
                "user_input": {},
            },
        )

        await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

        assert global_state.correction_attempt == initial_attempt + 1

    @pytest.mark.asyncio
    async def test_apply_corrections_merges_auto_fixes(self, global_state, mock_conversion_runner):
        """Test apply corrections merges auto fixes into metadata."""
        handler = ConversionErrorHandler()

        global_state.input_path = "/test/input.bin"
        global_state.metadata = {"existing_field": "existing_value"}

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {"fix_field1": "fix_value1", "fix_field2": "fix_value2"},
                "user_input": {},
            },
        )

        await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

        # Verify auto fixes were logged
        assert any("automatic fix" in log.message.lower() and "fix_field1" in log.message for log in global_state.logs)
        assert any("automatic fix" in log.message.lower() and "fix_field2" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_corrections_merges_user_input(self, global_state, mock_conversion_runner):
        """Test apply corrections merges user input into metadata."""
        handler = ConversionErrorHandler()

        global_state.input_path = "/test/input.bin"
        global_state.metadata = {"existing_field": "existing_value"}

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {"user_field1": "user_value1", "user_field2": "user_value2"},
            },
        )

        await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

        # Verify user input was logged
        assert any("user input" in log.message.lower() and "user_field1" in log.message for log in global_state.logs)
        assert any("user input" in log.message.lower() and "user_field2" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_corrections_versions_existing_nwb_file(self, global_state, mock_conversion_runner, tmp_path):
        """Test apply corrections versions existing NWB file before reconversion."""
        handler = ConversionErrorHandler()

        # Create existing NWB file
        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"existing NWB content")

        global_state.input_path = "/test/input.bin"
        global_state.output_path = str(output_file)
        global_state.correction_attempt = 0

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {"field": "value"},
                "user_input": {},
            },
        )

        with patch(
            "agentic_neurodata_conversion.agents.conversion.error_handling.create_versioned_file"
        ) as mock_version:
            mock_version.return_value = (tmp_path / "output_v1.nwb", "abc123")

            await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

            # Verify versioning was called
            assert mock_version.called
            # Verify checksum was logged
            assert any("checksum" in log.message.lower() for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_corrections_skips_versioning_if_no_output_file(self, global_state, mock_conversion_runner):
        """Test apply corrections skips versioning when no output file exists."""
        handler = ConversionErrorHandler()

        global_state.input_path = "/test/input.bin"
        global_state.output_path = None  # No output file yet

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {"field": "value"},
                "user_input": {},
            },
        )

        with patch(
            "agentic_neurodata_conversion.agents.conversion.error_handling.create_versioned_file"
        ) as mock_version:
            await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

            # Verify versioning was NOT called
            assert not mock_version.called

    @pytest.mark.asyncio
    async def test_apply_corrections_calls_reconversion(self, global_state, mock_conversion_runner):
        """Test apply corrections calls conversion runner for reconversion."""
        handler = ConversionErrorHandler()

        global_state.input_path = "/test/input.bin"
        global_state.output_path = "/test/output.nwb"
        global_state.metadata = {"format": "SpikeGLX"}

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {"field1": "value1"},
                "user_input": {"field2": "value2"},
            },
        )

        await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

        # Verify runner was called
        assert mock_conversion_runner.handle_run_conversion.called

        # Verify call had correct context
        call_args = mock_conversion_runner.handle_run_conversion.call_args[0]
        reconvert_msg = call_args[0]
        assert reconvert_msg.context["input_path"] == "/test/input.bin"
        assert reconvert_msg.context["format"] == "SpikeGLX"
        assert "field1" in reconvert_msg.context["metadata"]
        assert "field2" in reconvert_msg.context["metadata"]

    @pytest.mark.asyncio
    async def test_apply_corrections_success_computes_checksum(self, global_state, mock_conversion_runner, tmp_path):
        """Test apply corrections computes checksum of new file on success."""
        handler = ConversionErrorHandler()

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"new NWB content")

        global_state.input_path = "/test/input.bin"
        global_state.output_path = str(output_file)

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {},
            },
        )

        with (
            patch("agentic_neurodata_conversion.agents.conversion.error_handling.compute_sha256") as mock_checksum,
            patch(
                "agentic_neurodata_conversion.agents.conversion.error_handling.create_versioned_file"
            ) as mock_version,
        ):
            mock_checksum.return_value = "abc123def456"
            mock_version.return_value = (tmp_path / "output_v1.nwb", "old_checksum")

            response = await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

            assert response.success
            assert response.result["checksum"] == "abc123def456"
            assert any("new nwb file checksum" in log.message.lower() for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_corrections_success_returns_correct_response(
        self, global_state, mock_conversion_runner, tmp_path
    ):
        """Test apply corrections returns correct success response."""
        handler = ConversionErrorHandler()

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"output content")

        global_state.input_path = "/test/input.bin"
        global_state.output_path = str(output_file)
        global_state.correction_attempt = 0

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {},
            },
        )

        with patch(
            "agentic_neurodata_conversion.agents.conversion.error_handling.create_versioned_file"
        ) as mock_version:
            mock_version.return_value = (tmp_path / "output_v1.nwb", "checksum")

            response = await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

            assert response.success
            assert response.result["status"] == "reconversion_successful"
            assert response.result["output_path"] == str(output_file)
            assert response.result["attempt"] == 1  # Incremented from 0

    @pytest.mark.asyncio
    async def test_apply_corrections_reconversion_failure(self, global_state):
        """Test apply corrections handles reconversion failure."""
        handler = ConversionErrorHandler()

        # Mock runner that fails
        runner = Mock()
        runner.handle_run_conversion = AsyncMock(
            return_value=MCPResponse.error_response(
                reply_to="test_id",
                error_code="CONVERSION_FAILED",
                error_message="Conversion failed",
            )
        )

        global_state.input_path = "/test/input.bin"

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {},
            },
        )

        response = await handler.handle_apply_corrections(message, global_state, runner)

        # Should return the error response from runner
        assert not response.success
        assert any("reconversion failed" in log.message.lower() for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_corrections_exception_handling(self, global_state, mock_conversion_runner):
        """Test apply corrections handles exceptions gracefully."""
        handler = ConversionErrorHandler()

        # Mock runner that raises exception
        runner = Mock()
        runner.handle_run_conversion = AsyncMock(side_effect=RuntimeError("Unexpected error during reconversion"))

        global_state.input_path = "/test/input.bin"

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {},
            },
        )

        response = await handler.handle_apply_corrections(message, global_state, runner)

        assert not response.success
        assert response.error.get("code") == "CORRECTION_APPLICATION_FAILED"
        assert "correction application failed" in response.error.get("message").lower()
        assert any("correction application failed" in log.message.lower() for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_corrections_logs_attempt_number(self, global_state, mock_conversion_runner):
        """Test apply corrections logs the attempt number."""
        handler = ConversionErrorHandler()

        global_state.input_path = "/test/input.bin"
        global_state.correction_attempt = 2  # Third attempt

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {},
            },
        )

        await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

        # Should log attempt 3 (2 + 1)
        assert any("attempt 3" in log.message.lower() for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_corrections_uses_format_from_metadata(self, global_state, mock_conversion_runner):
        """Test apply corrections uses format from state metadata."""
        handler = ConversionErrorHandler()

        global_state.input_path = "/test/input.bin"
        global_state.metadata = {"format": "OpenEphys", "other_field": "value"}

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {},
            },
        )

        await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

        # Verify format was passed to runner
        call_args = mock_conversion_runner.handle_run_conversion.call_args[0]
        reconvert_msg = call_args[0]
        assert reconvert_msg.context["format"] == "OpenEphys"

    @pytest.mark.asyncio
    async def test_apply_corrections_defaults_to_spikeglx_format(self, global_state, mock_conversion_runner):
        """Test apply corrections defaults to SpikeGLX when format not in metadata."""
        handler = ConversionErrorHandler()

        global_state.input_path = "/test/input.bin"
        global_state.metadata = {}  # No format specified

        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {},
                "user_input": {},
            },
        )

        await handler.handle_apply_corrections(message, global_state, mock_conversion_runner)

        # Verify default format is SpikeGLX
        call_args = mock_conversion_runner.handle_run_conversion.call_args[0]
        reconvert_msg = call_args[0]
        assert reconvert_msg.context["format"] == "SpikeGLX"


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestErrorHandlerIntegration:
    """Integration tests for ConversionErrorHandler."""

    @pytest.mark.asyncio
    async def test_complete_correction_workflow(self, global_state, tmp_path):
        """Test complete correction workflow from start to finish."""
        llm_service = MockLLMService()
        handler = ConversionErrorHandler(llm_service=llm_service)

        # Setup state
        input_file = tmp_path / "input.bin"
        input_file.write_bytes(b"input data")
        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"original NWB")

        global_state.input_path = str(input_file)
        global_state.output_path = str(output_file)
        global_state.metadata = {"format": "SpikeGLX", "field1": "original"}

        # Mock conversion runner
        runner = Mock()
        runner.handle_run_conversion = AsyncMock(
            return_value=MCPResponse.success_response(
                reply_to="test_id",
                result={"status": "completed"},
            )
        )

        # Create correction message
        message = MCPMessage(
            target_agent="conversion",
            action="apply_corrections",
            context={
                "correction_context": {},
                "auto_fixes": {"field1": "corrected", "field2": "added"},
                "user_input": {"field3": "user_value"},
            },
        )

        # Execute correction
        with patch(
            "agentic_neurodata_conversion.agents.conversion.error_handling.create_versioned_file"
        ) as mock_version:
            mock_version.return_value = (tmp_path / "output_v1.nwb", "checksum123")

            response = await handler.handle_apply_corrections(message, global_state, runner)

        # Verify complete workflow
        assert response.success
        assert global_state.correction_attempt == 1
        assert mock_version.called
        assert runner.handle_run_conversion.called
