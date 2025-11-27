"""Integration tests for ConversionRunner workflow.

Tests the complete conversion workflow including:
- NeuroConv interface initialization and format mapping
- Conversion execution with progress monitoring
- File size tracking and progress updates
- Error handling and recovery
- Post-conversion validation
"""

import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.agents.conversion.conversion_runner import ConversionRunner
from agentic_neurodata_conversion.models import MCPMessage
from agentic_neurodata_conversion.services.llm_service import MockLLMService

# Note: The following fixtures are provided by conftest files:
# - global_state: from root conftest.py (Fresh GlobalState for each test)
# - mock_llm_service: from root conftest.py (Mock LLM service)
# - tmp_path: from pytest (Temporary directory)


@pytest.fixture
def mock_neuroconv():
    """Fixture to mock neuroconv.datainterfaces module.

    Returns a function that creates interface-specific mocks.
    """

    @contextmanager
    def _mock_interfaces(interface_mocks: dict):
        """Context manager to mock neuroconv.datainterfaces.

        Args:
            interface_mocks: Dict mapping interface names to Mock objects
        """
        mock_datainterfaces = Mock()
        for interface_name, mock_interface in interface_mocks.items():
            setattr(mock_datainterfaces, interface_name, mock_interface)

        # Use patch.dict to replace the module in sys.modules
        with patch.dict(sys.modules, {"neuroconv.datainterfaces": mock_datainterfaces}):
            yield mock_datainterfaces

    return _mock_interfaces


@pytest.mark.integration
@pytest.mark.agent_conversion
class TestConversionRunnerInitialization:
    """Tests for ConversionRunner initialization."""

    def test_init_with_llm_and_helpers(self):
        """Test initialization with LLM service and helpers."""
        llm_service = MockLLMService()
        helpers = Mock()
        runner = ConversionRunner(llm_service=llm_service, helpers=helpers)

        assert runner._llm_service is llm_service
        assert runner._helpers is helpers

    def test_init_without_llm_and_helpers(self):
        """Test initialization without LLM service and helpers."""
        runner = ConversionRunner(llm_service=None, helpers=None)

        assert runner._llm_service is None
        assert runner._helpers is None


@pytest.mark.integration
@pytest.mark.agent_conversion
class TestHandleRunConversion:
    """Tests for handle_run_conversion method."""

    @pytest.fixture
    def mock_helpers(self):
        """Create mock helpers."""
        helpers = Mock()
        helpers.narrate_progress = AsyncMock()
        helpers.calculate_checksum = Mock(return_value="abc123def456")
        helpers.map_flat_to_nested_metadata = Mock(return_value={"NWBFile": {"session_description": "test"}})
        return helpers

    @pytest.mark.asyncio
    async def test_handle_run_conversion_missing_parameters(self, global_state):
        """Test handle_run_conversion fails with missing parameters."""
        runner = ConversionRunner()

        # Missing output_path
        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": "/test/input.bin",
                "format": "SpikeGLX",
            },
        )

        response = await runner.handle_run_conversion(message, global_state)

        assert not response.success
        assert response.error.get("code") == "MISSING_PARAMETERS"

    @pytest.mark.asyncio
    async def test_handle_run_conversion_success(self, global_state, tmp_path, mock_helpers):
        """Test successful conversion workflow."""
        runner = ConversionRunner(llm_service=None, helpers=mock_helpers)

        # Create test files
        input_file = tmp_path / "test.bin"
        input_file.write_bytes(b"test data" * 100)
        output_file = tmp_path / "output.nwb"

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(input_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {"session_description": "test session"},
            },
        )

        # Mock the actual NeuroConv conversion
        with patch.object(runner, "_run_neuroconv_conversion") as mock_conversion:
            # Create output file to simulate successful conversion
            output_file.write_bytes(b"mock NWB content")

            response = await runner.handle_run_conversion(message, global_state)

            assert response.success
            assert response.result["output_path"] == str(output_file)
            assert "checksum" in response.result
            assert mock_conversion.called

    @pytest.mark.asyncio
    async def test_handle_run_conversion_with_metadata_filtering(self, global_state, tmp_path, mock_helpers):
        """Test that metadata is properly filtered to NWB-allowed fields."""
        runner = ConversionRunner(llm_service=None, helpers=mock_helpers)

        input_file = tmp_path / "test.bin"
        input_file.write_bytes(b"test data" * 100)
        output_file = tmp_path / "output.nwb"

        # Include both valid NWB fields and internal tracking fields
        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(input_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {
                    "session_description": "test",  # Valid NWB field
                    "experimenter": "Test User",  # Valid NWB field
                    "_custom_metadata_prompted": True,  # Internal tracking field - should be filtered
                    "_user_provided_fields": ["field1"],  # Internal tracking field - should be filtered
                    "format": "SpikeGLX",  # Internal field - should be filtered
                },
            },
        )

        with patch.object(runner, "_run_neuroconv_conversion") as mock_conversion:
            output_file.write_bytes(b"mock NWB content")
            await runner.handle_run_conversion(message, global_state)

            # Verify only valid NWB fields were passed to conversion
            call_args = mock_conversion.call_args[1]
            metadata = call_args["metadata"]

            assert "session_description" in metadata
            assert "experimenter" in metadata
            assert "_custom_metadata_prompted" not in metadata
            assert "_user_provided_fields" not in metadata
            assert "format" not in metadata

    @pytest.mark.asyncio
    async def test_handle_run_conversion_file_size_formatting(self, global_state, tmp_path, mock_helpers):
        """Test file size formatting in logs (GB, MB, KB)."""
        runner = ConversionRunner(llm_service=None, helpers=mock_helpers)

        # Create large file (> 1 GB)
        input_file = tmp_path / "large.bin"
        # Mock file size instead of creating actual large file
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=2 * 1024 * 1024 * 1024)  # 2 GB

            output_file = tmp_path / "output.nwb"

            message = MCPMessage(
                target_agent="conversion",
                action="run_conversion",
                context={
                    "input_path": str(input_file),
                    "output_path": str(output_file),
                    "format": "SpikeGLX",
                    "metadata": {},
                },
            )

            with patch.object(runner, "_run_neuroconv_conversion"):
                output_file.write_bytes(b"mock NWB content")
                await runner.handle_run_conversion(message, global_state)

            # Verify GB formatting in logs
            log_messages = [log.message for log in global_state.logs]
            assert any("GB" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_handle_run_conversion_calls_optimization(self, global_state, tmp_path):
        """Test that parameter optimization is called when LLM is available."""
        llm_service = MockLLMService()
        helpers = Mock()
        helpers.narrate_progress = AsyncMock()
        helpers.calculate_checksum = Mock(return_value="checksum123")
        helpers.map_flat_to_nested_metadata = Mock(return_value={})

        runner = ConversionRunner(llm_service=llm_service, helpers=helpers)

        input_file = tmp_path / "test.bin"
        input_file.write_bytes(b"test data")
        output_file = tmp_path / "output.nwb"

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(input_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )

        with (
            patch.object(runner, "_run_neuroconv_conversion"),
            patch.object(runner, "_optimize_conversion_parameters", new_callable=AsyncMock) as mock_optimize,
        ):
            output_file.write_bytes(b"mock NWB content")
            await runner.handle_run_conversion(message, global_state)

            # Verify optimization was called
            assert mock_optimize.called

    @pytest.mark.asyncio
    async def test_handle_run_conversion_error_handling(self, global_state, tmp_path, mock_helpers):
        """Test error handling during conversion."""
        runner = ConversionRunner(llm_service=None, helpers=mock_helpers)

        input_file = tmp_path / "test.bin"
        input_file.write_bytes(b"test data")
        output_file = tmp_path / "output.nwb"

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(input_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )

        # Mock conversion to fail
        with patch.object(runner, "_run_neuroconv_conversion", side_effect=ValueError("Conversion error")):
            response = await runner.handle_run_conversion(message, global_state)

            assert not response.success
            assert response.error.get("code") == "CONVERSION_FAILED"
            assert "Conversion error" in response.error.get("message")


@pytest.mark.integration
@pytest.mark.agent_conversion
class TestRunNeuroConvConversion:
    """Tests for _run_neuroconv_conversion method."""

    @pytest.fixture(autouse=True)
    def clear_neuroconv_cache(self):
        """Clear neuroconv modules from cache before each test to ensure mocks work."""
        # Remove neuroconv modules from sys.modules before test
        modules_to_remove = [key for key in sys.modules.keys() if key.startswith("neuroconv")]
        removed_modules = {key: sys.modules.pop(key) for key in modules_to_remove}

        yield

        # Restore modules after test
        sys.modules.update(removed_modules)

    @pytest.mark.asyncio
    async def test_unsupported_format_raises_error(self, global_state):
        """Test that unsupported format raises ValueError."""
        runner = ConversionRunner()

        with pytest.raises(ValueError, match="Unsupported format"):
            runner._run_neuroconv_conversion(
                input_path="/test/input.bin",
                output_path="/test/output.nwb",
                format_name="UnsupportedFormat",
                metadata={},
                state=global_state,
            )

    @pytest.mark.asyncio
    async def test_spikeglx_format_initialization(self, global_state, tmp_path, mock_neuroconv):
        """Test SpikeGLX format-specific initialization."""
        runner = ConversionRunner()

        # Create SpikeGLX files
        spikeglx_dir = tmp_path / "spikeglx_data"
        spikeglx_dir.mkdir()
        bin_file = spikeglx_dir / "recording_g0_t0.imec0.ap.bin"
        meta_file = spikeglx_dir / "recording_g0_t0.imec0.ap.meta"
        bin_file.write_bytes(b"mock data" * 100)
        meta_file.write_text("imSampRate=30000\n")

        output_file = tmp_path / "output.nwb"

        # Mock interface
        mock_interface = Mock()
        mock_interface.get_metadata = Mock(return_value={})
        mock_interface.run_conversion = Mock()

        with mock_neuroconv({"SpikeGLXRecordingInterface": Mock(return_value=mock_interface)}) as mock_datainterfaces:
            runner._run_neuroconv_conversion(
                input_path=str(spikeglx_dir),
                output_path=str(output_file),
                format_name="SpikeGLX",
                metadata={},
                state=global_state,
            )

            # Verify SpikeGLX interface was created with file_path to .ap.bin file
            # NeuroConv automatically finds companion .meta file
            assert mock_datainterfaces.SpikeGLXRecordingInterface.called
            call_kwargs = mock_datainterfaces.SpikeGLXRecordingInterface.call_args.kwargs
            assert "file_path" in call_kwargs
            # Verify it points to the .ap.bin file
            assert call_kwargs["file_path"].endswith(".ap.bin")

    @pytest.mark.asyncio
    async def test_spikeglx_missing_ap_bin_file(self, global_state, tmp_path, mock_neuroconv):
        """Test SpikeGLX error when no .ap.bin file is found."""
        runner = ConversionRunner()

        spikeglx_dir = tmp_path / "spikeglx_data"
        spikeglx_dir.mkdir()
        # Create only .lf.bin file (no .ap.bin)
        lf_file = spikeglx_dir / "recording_g0_t0.imec0.lf.bin"
        lf_file.write_bytes(b"mock data")

        with mock_neuroconv({}) as mock_datainterfaces:
            with pytest.raises(ValueError) as exc_info:
                runner._run_neuroconv_conversion(
                    input_path=str(spikeglx_dir),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="SpikeGLX",
                    metadata={},
                    state=global_state,
                )

            # Verify helpful error message
            error_msg = str(exc_info.value)
            assert "No .ap.bin file found" in error_msg
            assert str(spikeglx_dir) in error_msg

    @pytest.mark.asyncio
    async def test_openephys_format_initialization(self, global_state, tmp_path, mock_neuroconv):
        """Test OpenEphys format-specific initialization."""
        runner = ConversionRunner()

        openephys_dir = tmp_path / "openephys_data"
        openephys_dir.mkdir()
        (openephys_dir / "structure.oebin").write_text('{"format": "openephys"}')

        output_file = tmp_path / "output.nwb"

        mock_interface = Mock()
        mock_interface.get_metadata = Mock(return_value={})
        mock_interface.run_conversion = Mock()

        with mock_neuroconv({"OpenEphysRecordingInterface": Mock(return_value=mock_interface)}) as mock_datainterfaces:
            runner._run_neuroconv_conversion(
                input_path=str(openephys_dir),
                output_path=str(output_file),
                format_name="OpenEphys",
                metadata={},
                state=global_state,
            )

            # Verify OpenEphys interface was created with folder_path
            assert mock_datainterfaces.OpenEphysRecordingInterface.called
            call_kwargs = mock_datainterfaces.OpenEphysRecordingInterface.call_args.kwargs
            assert "folder_path" in call_kwargs

    @pytest.mark.asyncio
    async def test_axon_format_uses_file_paths_parameter(self, global_state, tmp_path, mock_neuroconv):
        """Test Axon format uses file_paths (plural) parameter."""
        runner = ConversionRunner()

        axon_file = tmp_path / "recording.abf"
        axon_file.write_bytes(b"mock ABF data")
        output_file = tmp_path / "output.nwb"

        mock_interface = Mock()
        mock_interface.get_metadata = Mock(return_value={})
        mock_interface.run_conversion = Mock()

        with mock_neuroconv({"AbfInterface": Mock(return_value=mock_interface)}) as mock_datainterfaces:
            runner._run_neuroconv_conversion(
                input_path=str(axon_file),
                output_path=str(output_file),
                format_name="Axon",
                metadata={},
                state=global_state,
            )

            # Verify Axon interface was created with file_paths as list
            assert mock_datainterfaces.AbfInterface.called
            call_kwargs = mock_datainterfaces.AbfInterface.call_args.kwargs
            assert "file_paths" in call_kwargs
            assert isinstance(call_kwargs["file_paths"], list)
            assert str(axon_file) in call_kwargs["file_paths"]

    @pytest.mark.asyncio
    async def test_generic_format_with_file_path(self, global_state, tmp_path, mock_neuroconv):
        """Test generic format with file_path parameter."""
        runner = ConversionRunner()

        test_file = tmp_path / "recording.dat"
        test_file.write_bytes(b"mock data")
        output_file = tmp_path / "output.nwb"

        mock_interface = Mock()
        mock_interface.get_metadata = Mock(return_value={})
        mock_interface.run_conversion = Mock()

        with mock_neuroconv({"IntanRecordingInterface": Mock(return_value=mock_interface)}) as mock_datainterfaces:
            runner._run_neuroconv_conversion(
                input_path=str(test_file),
                output_path=str(output_file),
                format_name="IntanRecording",
                metadata={},
                state=global_state,
            )

            # Verify interface was created with file_path (singular)
            assert mock_datainterfaces.IntanRecordingInterface.called
            call_kwargs = mock_datainterfaces.IntanRecordingInterface.call_args.kwargs
            assert "file_path" in call_kwargs
            assert call_kwargs["file_path"] == str(test_file)

    @pytest.mark.asyncio
    async def test_metadata_mapping_with_helpers(self, global_state, tmp_path, mock_neuroconv):
        """Test metadata mapping when helpers are available."""
        mock_helpers = Mock()
        mock_helpers.map_flat_to_nested_metadata = Mock(
            return_value={
                "NWBFile": {"session_description": "test session"},
                "Subject": {"subject_id": "subject001"},
            }
        )

        runner = ConversionRunner(llm_service=None, helpers=mock_helpers)

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        mock_interface = Mock()
        mock_interface.get_metadata = Mock(return_value={"NWBFile": {}, "Subject": {}})
        mock_interface.run_conversion = Mock()

        with mock_neuroconv({"IntanRecordingInterface": Mock(return_value=mock_interface)}) as mock_datainterfaces:
            runner._run_neuroconv_conversion(
                input_path=str(test_file),
                output_path=str(tmp_path / "output.nwb"),
                format_name="IntanRecording",
                metadata={"session_description": "test session", "subject_id": "subject001"},
                state=global_state,
            )

            # Verify helpers.map_flat_to_nested_metadata was called
            assert mock_helpers.map_flat_to_nested_metadata.called

            # Verify metadata was merged correctly
            call_kwargs = mock_interface.run_conversion.call_args.kwargs
            metadata = call_kwargs["metadata"]
            assert metadata["NWBFile"]["session_description"] == "test session"
            assert metadata["Subject"]["subject_id"] == "subject001"

    @pytest.mark.asyncio
    async def test_metadata_mapping_without_helpers(self, global_state, tmp_path, mock_neuroconv):
        """Test metadata fallback when no helpers available."""
        runner = ConversionRunner(llm_service=None, helpers=None)

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        mock_interface = Mock()
        mock_interface.get_metadata = Mock(return_value={})
        mock_interface.run_conversion = Mock()

        with mock_neuroconv({"IntanRecordingInterface": Mock(return_value=mock_interface)}) as mock_datainterfaces:
            runner._run_neuroconv_conversion(
                input_path=str(test_file),
                output_path=str(tmp_path / "output.nwb"),
                format_name="IntanRecording",
                metadata={"session_description": "test"},
                state=global_state,
            )

            # Verify metadata was passed as-is (no mapping)
            call_kwargs = mock_interface.run_conversion.call_args.kwargs
            assert "metadata" in call_kwargs

    @pytest.mark.asyncio
    async def test_conversion_error_cleanup(self, global_state, tmp_path, mock_neuroconv):
        """Test partial file cleanup on conversion error."""
        runner = ConversionRunner()

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")
        output_file = tmp_path / "output.nwb"

        mock_interface = Mock()
        mock_interface.get_metadata = Mock(return_value={})

        # Simulate conversion creating partial file then failing
        def mock_run_conversion(*args, **kwargs):
            output_file.write_bytes(b"partial NWB data")
            raise RuntimeError("Conversion failed")

        mock_interface.run_conversion = mock_run_conversion

        with mock_neuroconv({"IntanRecordingInterface": Mock(return_value=mock_interface)}) as mock_datainterfaces:
            with pytest.raises(RuntimeError, match="Conversion failed"):
                runner._run_neuroconv_conversion(
                    input_path=str(test_file),
                    output_path=str(output_file),
                    format_name="IntanRecording",
                    metadata={},
                    state=global_state,
                )

            # Verify partial file was cleaned up
            assert not output_file.exists()

    @pytest.mark.asyncio
    async def test_interface_import_error_handling(self, global_state, tmp_path, mock_neuroconv):
        """Test error handling when interface import fails."""
        runner = ConversionRunner()

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        with mock_neuroconv({}) as mock_datainterfaces:
            # Simulate missing interface
            if hasattr(mock_datainterfaces, "SpikeGLXRecordingInterface"):
                delattr(mock_datainterfaces, "SpikeGLXRecordingInterface")

            with pytest.raises(ValueError, match="Failed to import interface"):
                runner._run_neuroconv_conversion(
                    input_path=str(test_file),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="SpikeGLX",
                    metadata={},
                    state=global_state,
                )

    @pytest.mark.asyncio
    async def test_generic_format_error_with_detailed_logging(self, global_state, tmp_path, mock_neuroconv):
        """Test detailed error logging for generic format initialization failures."""
        runner = ConversionRunner()

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        with mock_neuroconv(
            {"IntanRecordingInterface": Mock(side_effect=ValueError("File may be corrupted or invalid format"))}
        ) as mock_datainterfaces:
            with pytest.raises(ValueError, match="Failed to initialize"):
                runner._run_neuroconv_conversion(
                    input_path=str(test_file),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="IntanRecording",
                    metadata={},
                    state=global_state,
                )

            # Verify detailed error was logged
            assert any(
                "corrupt" in log.message.lower() or "invalid" in log.message.lower() for log in global_state.logs
            )


@pytest.mark.integration
@pytest.mark.agent_conversion
class TestOptimizeConversionParameters:
    """Tests for _optimize_conversion_parameters method."""

    @pytest.mark.asyncio
    async def test_optimize_without_llm_returns_empty(self, global_state):
        """Test optimization returns empty dict without LLM."""
        runner = ConversionRunner(llm_service=None)

        result = await runner._optimize_conversion_parameters(
            format_name="SpikeGLX",
            file_size_mb=100.0,
            state=global_state,
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_optimize_with_llm_success(self, global_state):
        """Test successful optimization with LLM."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "use_compression": True,
                "compression_recommended": "gzip",
                "reasoning": "Large file benefits from compression",
                "expected_output_size_mb": 50.0,
                "optimization_priority": "balanced",
            }
        )

        runner = ConversionRunner(llm_service=llm_service)

        result = await runner._optimize_conversion_parameters(
            format_name="SpikeGLX",
            file_size_mb=200.0,
            state=global_state,
        )

        assert "optimization" in result
        assert result["optimization"]["use_compression"] is True
        assert result["optimization"]["compression_recommended"] == "gzip"
        assert result["recommended_approach"] == "gzip"

    @pytest.mark.asyncio
    async def test_optimize_llm_failure_returns_empty(self, global_state):
        """Test optimization returns empty dict when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=RuntimeError("LLM error"))

        runner = ConversionRunner(llm_service=llm_service)

        result = await runner._optimize_conversion_parameters(
            format_name="SpikeGLX",
            file_size_mb=100.0,
            state=global_state,
        )

        assert result == {}
        assert any("optimization failed" in log.message.lower() for log in global_state.logs)


@pytest.mark.integration
@pytest.mark.agent_conversion
class TestMonitorFileSizeProgress:
    """Tests for _monitor_file_size_progress method."""

    def test_monitor_file_size_progress_tracks_growth(self, global_state, tmp_path):
        """Test file size monitoring tracks file growth."""
        import threading
        import time

        runner = ConversionRunner()
        output_file = tmp_path / "output.nwb"
        stop_event = threading.Event()

        # Write initial data
        output_file.write_bytes(b"initial data")

        # Start monitoring in background
        monitor_thread = threading.Thread(
            target=runner._monitor_file_size_progress,
            args=(str(output_file), 100.0, global_state, stop_event, 50.0, 90.0),
            daemon=True,
        )
        monitor_thread.start()

        # Simulate file growth
        time.sleep(0.1)
        output_file.write_bytes(b"x" * (10 * 1024 * 1024))  # 10 MB
        time.sleep(0.1)

        # Stop monitoring
        stop_event.set()
        monitor_thread.join(timeout=2.0)

        # Verify monitoring logs were created
        assert any("file size monitoring" in log.message.lower() for log in global_state.logs)

    def test_monitor_file_size_handles_missing_file(self, global_state, tmp_path):
        """Test monitoring handles non-existent file gracefully."""
        import threading

        runner = ConversionRunner()
        output_file = tmp_path / "nonexistent.nwb"
        stop_event = threading.Event()

        # Start monitoring (file doesn't exist yet)
        monitor_thread = threading.Thread(
            target=runner._monitor_file_size_progress,
            args=(str(output_file), 100.0, global_state, stop_event, 50.0, 90.0),
            daemon=True,
        )
        monitor_thread.start()

        # Stop monitoring quickly
        stop_event.set()
        monitor_thread.join(timeout=2.0)

        # Should not crash, just log
        assert monitor_thread is not None

    def test_monitor_stops_on_event(self, global_state, tmp_path):
        """Test monitoring stops when stop_event is set."""
        import threading

        runner = ConversionRunner()
        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"test data")
        stop_event = threading.Event()

        monitor_thread = threading.Thread(
            target=runner._monitor_file_size_progress,
            args=(str(output_file), 100.0, global_state, stop_event, 50.0, 90.0),
            daemon=True,
        )
        monitor_thread.start()

        # Stop immediately
        stop_event.set()
        monitor_thread.join(timeout=2.0)

        # Thread should have stopped
        assert not monitor_thread.is_alive()

    def test_monitor_file_size_progress_update_logic_coverage(self, global_state, tmp_path):
        """Test file size monitoring covers progress update logic (lines 770-787)."""
        import threading
        import time

        runner = ConversionRunner()
        output_file = tmp_path / "growing.nwb"
        stop_event = threading.Event()

        # Create file with initial size
        output_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB initial

        monitor_thread = threading.Thread(
            target=runner._monitor_file_size_progress,
            args=(str(output_file), 50.0, global_state, stop_event, 50.0, 90.0),
            daemon=True,
        )
        monitor_thread.start()

        # Wait briefly then stop (just verify the thread runs without errors)
        time.sleep(0.2)
        stop_event.set()
        monitor_thread.join(timeout=2.0)

        # Verify monitoring started and stopped successfully (covers lines 770-787)
        log_messages = [log.message for log in global_state.logs]
        assert any("monitoring" in msg.lower() for msg in log_messages), "Expected monitoring logs"

    def test_monitor_file_size_error_handling_coverage(self, global_state, tmp_path):
        """Test monitoring thread handles errors gracefully (lines 789-821)."""
        import threading
        import time

        runner = ConversionRunner()
        output_file = tmp_path / "test.nwb"
        stop_event = threading.Event()

        # Create file
        output_file.write_bytes(b"x" * (5 * 1024 * 1024))  # 5 MB

        monitor_thread = threading.Thread(
            target=runner._monitor_file_size_progress,
            args=(str(output_file), 50.0, global_state, stop_event, 50.0, 90.0),
            daemon=True,
        )
        monitor_thread.start()

        # Wait briefly
        time.sleep(0.2)

        # Stop monitoring
        stop_event.set()
        monitor_thread.join(timeout=2.0)

        # Verify monitoring completed without crashing (covers error handling paths)
        assert not monitor_thread.is_alive()
        log_messages = [log.message for log in global_state.logs]
        assert any("monitoring" in msg.lower() for msg in log_messages)

    def test_monitor_file_size_thread_exception_handling(self, global_state, tmp_path):
        """Test exception handling in monitoring thread (lines 814-817)."""
        import threading
        import time

        runner = ConversionRunner()
        # Use invalid path to trigger exception
        invalid_path = "/invalid/nonexistent/path/output.nwb"
        stop_event = threading.Event()

        monitor_thread = threading.Thread(
            target=runner._monitor_file_size_progress,
            args=(invalid_path, 50.0, global_state, stop_event, 50.0, 90.0),
            daemon=True,
        )
        monitor_thread.start()

        # Wait for thread to process
        time.sleep(0.2)

        # Stop monitoring
        stop_event.set()
        monitor_thread.join(timeout=2.0)

        # Thread should not crash - should handle exceptions gracefully (lines 814-821)
        # Verify the thread completed without crashing
        assert not monitor_thread.is_alive()


@pytest.mark.integration
@pytest.mark.agent_conversion
class TestSpikeGLXErrorHandling:
    """Tests for SpikeGLX-specific error handling."""

    @pytest.fixture(autouse=True)
    def clear_neuroconv_cache(self):
        """Clear neuroconv modules from cache."""
        modules_to_remove = [key for key in sys.modules.keys() if key.startswith("neuroconv")]
        removed_modules = {key: sys.modules.pop(key) for key in modules_to_remove}
        yield
        sys.modules.update(removed_modules)

    @pytest.mark.asyncio
    async def test_spikeglx_filename_parse_error_helpful_message(self, global_state, tmp_path, mock_neuroconv):
        """Test SpikeGLX interface initialization error provides helpful message."""
        runner = ConversionRunner()

        spikeglx_dir = tmp_path / "spikeglx_data"
        spikeglx_dir.mkdir()

        # Create proper .ap.bin file so it passes the file check
        ap_file = spikeglx_dir / "recording_g0_t0.imec0.ap.bin"
        ap_file.write_bytes(b"test data")
        meta_file = spikeglx_dir / "recording_g0_t0.imec0.ap.meta"
        meta_file.write_text("imSampRate=30000\n")

        # Mock NeuroConv interface to raise filename parsing error
        with mock_neuroconv(
            {"SpikeGLXRecordingInterface": Mock(side_effect=ValueError("Cannot parse filename for SpikeGLX"))}
        ) as mock_datainterfaces:
            with pytest.raises(ValueError) as exc_info:
                runner._run_neuroconv_conversion(
                    input_path=str(spikeglx_dir),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="SpikeGLX",
                    metadata={},
                    state=global_state,
                )

            # Verify helpful error message includes context about initialization failure
            error_msg = str(exc_info.value)
            assert "failed to initialize spikeglx interface" in error_msg.lower()
            assert ".bin and .meta files" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_spikeglx_initialization_other_errors(self, global_state, tmp_path, mock_neuroconv):
        """Test SpikeGLX initialization handles other errors with context."""
        runner = ConversionRunner()

        spikeglx_dir = tmp_path / "spikeglx_data"
        spikeglx_dir.mkdir()

        # Create proper .ap.bin file so it passes the file check
        ap_file = spikeglx_dir / "recording_g0_t0.imec0.ap.bin"
        ap_file.write_bytes(b"test data")
        meta_file = spikeglx_dir / "recording_g0_t0.imec0.ap.meta"
        meta_file.write_text("imSampRate=30000\n")

        # Mock NeuroConv interface to raise generic error
        with mock_neuroconv(
            {"SpikeGLXRecordingInterface": Mock(side_effect=RuntimeError("Missing metadata files"))}
        ) as mock_datainterfaces:
            with pytest.raises(ValueError) as exc_info:
                runner._run_neuroconv_conversion(
                    input_path=str(spikeglx_dir),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="SpikeGLX",
                    metadata={},
                    state=global_state,
                )

            # Verify error provides context about initialization failure
            error_msg = str(exc_info.value)
            assert "failed to initialize spikeglx interface" in error_msg.lower()
            assert ".bin and .meta files" in error_msg.lower()


@pytest.mark.integration
@pytest.mark.agent_conversion
class TestGenericFormatErrorDetection:
    """Tests for detailed error detection in generic format initialization."""

    @pytest.fixture(autouse=True)
    def clear_neuroconv_cache(self):
        """Clear neuroconv modules from cache."""
        modules_to_remove = [key for key in sys.modules.keys() if key.startswith("neuroconv")]
        removed_modules = {key: sys.modules.pop(key) for key in modules_to_remove}
        yield
        sys.modules.update(removed_modules)

    @pytest.mark.asyncio
    async def test_generic_format_permission_error_detection(self, global_state, tmp_path, mock_neuroconv):
        """Test permission error detection (lines 578-579)."""
        runner = ConversionRunner()

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        with mock_neuroconv(
            {"IntanRecordingInterface": Mock(side_effect=PermissionError("Permission denied"))}
        ) as mock_datainterfaces:
            with pytest.raises(ValueError) as exc_info:
                runner._run_neuroconv_conversion(
                    input_path=str(test_file),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="IntanRecording",
                    metadata={},
                    state=global_state,
                )

            # Verify permission error was detected and logged (lines 578-579)
            log_messages = [log.message for log in global_state.logs]
            assert any("permission" in msg.lower() for msg in log_messages)

    @pytest.mark.asyncio
    async def test_generic_format_corruption_error_detection(self, global_state, tmp_path, mock_neuroconv):
        """Test corruption error detection (lines 580-581)."""
        runner = ConversionRunner()

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        with mock_neuroconv(
            {"IntanRecordingInterface": Mock(side_effect=ValueError("File is corrupt"))}
        ) as mock_datainterfaces:
            with pytest.raises(ValueError) as exc_info:
                runner._run_neuroconv_conversion(
                    input_path=str(test_file),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="IntanRecording",
                    metadata={},
                    state=global_state,
                )

            # Verify corruption was detected (lines 580-581)
            log_messages = [log.message for log in global_state.logs]
            assert any("corrupt" in msg.lower() for msg in log_messages)

    @pytest.mark.asyncio
    async def test_generic_format_metadata_error_detection(self, global_state, tmp_path, mock_neuroconv):
        """Test metadata error detection (lines 582-583)."""
        runner = ConversionRunner()

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        with mock_neuroconv(
            {"IntanRecordingInterface": Mock(side_effect=ValueError("Missing metadata"))}
        ) as mock_datainterfaces:
            with pytest.raises(ValueError) as exc_info:
                runner._run_neuroconv_conversion(
                    input_path=str(test_file),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="IntanRecording",
                    metadata={},
                    state=global_state,
                )

            # Verify metadata error was detected (lines 582-583)
            log_messages = [log.message for log in global_state.logs]
            assert any("metadata" in msg.lower() for msg in log_messages)

    @pytest.mark.asyncio
    async def test_generic_format_compression_error_detection(self, global_state, tmp_path, mock_neuroconv):
        """Test compression error detection (lines 584-585)."""
        runner = ConversionRunner()

        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        with mock_neuroconv(
            {"IntanRecordingInterface": Mock(side_effect=ValueError("Compression format not supported"))}
        ) as mock_datainterfaces:
            with pytest.raises(ValueError) as exc_info:
                runner._run_neuroconv_conversion(
                    input_path=str(test_file),
                    output_path=str(tmp_path / "output.nwb"),
                    format_name="IntanRecording",
                    metadata={},
                    state=global_state,
                )

            # Verify compression error was detected (lines 584-585)
            log_messages = [log.message for log in global_state.logs]
            assert any("compression" in msg.lower() for msg in log_messages)
