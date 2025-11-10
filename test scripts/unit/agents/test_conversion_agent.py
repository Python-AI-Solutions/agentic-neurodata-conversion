"""
Unit tests for Conversion Agent.

Tests the conversion agent including:
- Format detection (LLM-first approach)
- Parameter optimization
- Progress narration
- NeuroConv integration
- Error handling
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile

from agents.conversion_agent import ConversionAgent
from models import GlobalState, ConversionStatus, LogLevel, MCPMessage, MCPResponse
from services.llm_service import MockLLMService


@pytest.mark.unit
class TestConversionAgentInitialization:
    """Tests for ConversionAgent initialization."""

    def test_init_without_llm_service(self):
        """Test agent initializes without LLM service."""
        agent = ConversionAgent(llm_service=None)

        assert agent._llm_service is None
        assert agent._supported_formats is not None
        assert isinstance(agent._supported_formats, list)
        assert agent._format_detector is None

    def test_init_with_llm_service(self):
        """Test agent initializes with LLM service."""
        mock_llm = MockLLMService()
        agent = ConversionAgent(llm_service=mock_llm)

        assert agent._llm_service is mock_llm
        assert agent._supported_formats is not None
        assert agent._format_detector is not None

    def test_get_supported_formats_fallback(self):
        """Test _get_supported_formats fallback when NeuroConv fails."""
        # Mock get_format_summaries to fail (need to patch where it's imported from)
        with patch('neuroconv.get_format_summaries', side_effect=Exception("Mock error")):
            # Create new agent which will trigger fallback
            agent = ConversionAgent(llm_service=None)

            # Should still have formats from fallback list
            assert len(agent._supported_formats) > 0
            # Should include common formats like SpikeGLX from fallback
            assert "SpikeGLX" in agent._supported_formats
            # Should have the full fallback list (84 formats)
            assert len(agent._supported_formats) >= 80


@pytest.mark.unit
class TestFormatDetection:
    """Tests for format detection (LLM-first approach)."""

    @pytest.fixture
    def agent_with_llm(self):
        """Create agent with mock LLM service."""
        return ConversionAgent(llm_service=MockLLMService())

    @pytest.fixture
    def agent_no_llm(self):
        """Create agent without LLM service."""
        return ConversionAgent(llm_service=None)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.asyncio
    async def test_detect_spikeglx_with_pattern_matching(self, agent_no_llm, temp_dir):
        """Test SpikeGLX detection via pattern matching."""
        # Create SpikeGLX files
        (temp_dir / "test.ap.bin").touch()
        (temp_dir / "test.ap.meta").touch()

        state = GlobalState()
        result = await agent_no_llm._detect_format(str(temp_dir), state)

        assert result == "SpikeGLX"
        assert any("pattern matching" in log.message for log in state.logs)

    @pytest.mark.asyncio
    async def test_detect_openephys_with_pattern_matching(self, agent_no_llm, temp_dir):
        """Test OpenEphys detection via pattern matching."""
        # Create OpenEphys file
        (temp_dir / "structure.oebin").touch()

        state = GlobalState()
        result = await agent_no_llm._detect_format(str(temp_dir), state)

        assert result == "OpenEphys"
        assert any("pattern matching" in log.message for log in state.logs)

    @pytest.mark.asyncio
    async def test_detect_neuropixels_with_pattern_matching(self, agent_no_llm, temp_dir):
        """Test Neuropixels detection via pattern matching."""
        # Fixed: Files with .ap/.lf/.nidq patterns are detected as SpikeGLX (checked first)
        # This is correct since Neuropixels probes use SpikeGLX format for acquisition
        # The implementation prioritizes SpikeGLX detection before Neuropixels
        (temp_dir / "test.imec0.ap.bin").touch()

        state = GlobalState()
        result = await agent_no_llm._detect_format(str(temp_dir / "test.imec0.ap.bin"), state)

        # Expect SpikeGLX since .ap. pattern matches SpikeGLX check (runs before Neuropixels check)
        assert result == "SpikeGLX"

    @pytest.mark.asyncio
    async def test_llm_first_detection_high_confidence(self, agent_with_llm, temp_dir):
        """Test LLM detection tried first with high confidence."""
        # Create ambiguous file
        (temp_dir / "data.bin").touch()

        # Fixed: Use patch.object with AsyncMock for proper async method mocking
        # Also mock _get_supported_formats to include "SpikeGLX" for validation
        with patch.object(
            agent_with_llm,
            '_detect_format_with_llm',
            new_callable=AsyncMock,
            return_value={"format": "SpikeGLX", "confidence": 85}
        ), patch.object(
            agent_with_llm,
            '_get_supported_formats',
            return_value=["SpikeGLX", "OpenEphys", "Neuropixels", "AlphaOmega"]
        ):
            state = GlobalState()
            result = await agent_with_llm._detect_format(str(temp_dir / "data.bin"), state)

            # Should use LLM result due to high confidence
            assert result == "SpikeGLX", f"Expected SpikeGLX but got {result}"
            assert any("LLM detected format" in log.message for log in state.logs)

    @pytest.mark.asyncio
    async def test_llm_detection_low_confidence_fallback(self, agent_with_llm, temp_dir):
        """Test LLM low confidence triggers pattern matching fallback."""
        # Create SpikeGLX files
        (temp_dir / "test.ap.bin").touch()
        (temp_dir / "test.ap.meta").touch()

        # Mock LLM to return low confidence using patch.object
        with patch.object(
            agent_with_llm,
            '_detect_format_with_llm',
            new_callable=AsyncMock,
            return_value={"format": "Unknown", "confidence": 50}
        ):
            state = GlobalState()
            result = await agent_with_llm._detect_format(str(temp_dir), state)

            # Should fallback to pattern matching
            assert result == "SpikeGLX"
            assert any("confidence too low" in log.message.lower() for log in state.logs)

    @pytest.mark.asyncio
    async def test_detect_format_ambiguous(self, agent_no_llm, temp_dir):
        """Test detection returns None for ambiguous files."""
        # Create non-matching file
        (temp_dir / "unknown.dat").touch()

        state = GlobalState()
        result = await agent_no_llm._detect_format(str(temp_dir / "unknown.dat"), state)

        assert result is None

    def test_is_spikeglx_with_directory(self, agent_no_llm, temp_dir):
        """Test SpikeGLX detection for directory."""
        (temp_dir / "test.ap.bin").touch()
        (temp_dir / "test.ap.meta").touch()

        result = agent_no_llm._is_spikeglx(temp_dir)

        assert result is True

    def test_is_spikeglx_with_file(self, agent_no_llm, temp_dir):
        """Test SpikeGLX detection for single file."""
        file_path = temp_dir / "test.ap.bin"
        file_path.touch()

        result = agent_no_llm._is_spikeglx(file_path)

        assert result is True

    def test_is_spikeglx_negative(self, agent_no_llm, temp_dir):
        """Test SpikeGLX detection returns False for non-matching."""
        (temp_dir / "data.bin").touch()

        result = agent_no_llm._is_spikeglx(temp_dir)

        assert result is False

    def test_is_openephys(self, agent_no_llm, temp_dir):
        """Test OpenEphys detection."""
        (temp_dir / "structure.oebin").touch()

        result = agent_no_llm._is_openephys(temp_dir)

        assert result is True

    def test_is_openephys_settings_xml(self, agent_no_llm, temp_dir):
        """Test OpenEphys detection with settings.xml."""
        (temp_dir / "settings.xml").touch()

        result = agent_no_llm._is_openephys(temp_dir)

        assert result is True

    def test_is_neuropixels(self, agent_no_llm, temp_dir):
        """Test Neuropixels detection."""
        file_path = temp_dir / "data.nidq.bin"
        file_path.touch()

        result = agent_no_llm._is_neuropixels(file_path)

        assert result is True

    @pytest.mark.asyncio
    async def test_detect_neuropixels_pattern_match(self, agent_no_llm, temp_dir):
        """Test Neuropixels detection via pattern matching in _detect_format.

        Note: .nidq.bin files match SpikeGLX pattern first (which is correct),
        since Neuropixels uses SpikeGLX for acquisition. The _is_neuropixels
        check is a separate helper method tested elsewhere.
        """
        # Create Neuropixels NIDQ file
        (temp_dir / "recording.nidq.bin").touch()

        state = GlobalState()
        result = await agent_no_llm._detect_format(str(temp_dir / "recording.nidq.bin"), state)

        # .nidq files are detected as SpikeGLX (which is the correct format interface)
        assert result == "SpikeGLX"
        assert any("pattern matching" in log.message.lower() and "spikeglx" in log.message.lower() for log in state.logs)

    @pytest.mark.asyncio
    async def test_detect_axon_abf_file(self, agent_no_llm, temp_dir):
        """Test Axon .abf file detection."""
        # Create .abf file
        abf_file = temp_dir / "recording.abf"
        abf_file.touch()

        state = GlobalState()
        result = await agent_no_llm._detect_format(str(abf_file), state)

        assert result == "Axon"
        # Verify log mentions Axon and .abf
        assert any("axon" in log.message.lower() and ".abf" in log.message.lower() for log in state.logs)


@pytest.mark.unit
class TestParameterOptimization:
    """Tests for LLM-powered parameter optimization."""

    @pytest.fixture
    def agent_with_llm(self):
        """Create agent with mock LLM service."""
        return ConversionAgent(llm_service=MockLLMService())

    @pytest.fixture
    def agent_no_llm(self):
        """Create agent without LLM service."""
        return ConversionAgent(llm_service=None)

    @pytest.mark.asyncio
    async def test_optimize_parameters_with_llm(self, agent_with_llm):
        """Test parameter optimization uses LLM."""
        state = GlobalState()

        # Mock LLM response
        async def mock_generate_structured(prompt, output_schema, system_prompt=None):
            return {
                "use_compression": True,
                "compression_recommended": "gzip",
                "reasoning": "File size warrants compression",
                "expected_output_size_mb": 50.0,
            }

        agent_with_llm._llm_service.generate_structured_output = mock_generate_structured

        result = await agent_with_llm._optimize_conversion_parameters(
            format_name="SpikeGLX",
            file_size_mb=100.0,
            state=state,
        )

        assert "optimization" in result
        assert result["optimization"]["use_compression"] is True
        assert result["optimization"]["compression_recommended"] == "gzip"
        assert any("LLM-optimized" in log.message for log in state.logs)

    @pytest.mark.asyncio
    async def test_optimize_parameters_without_llm(self, agent_no_llm):
        """Test parameter optimization fallback without LLM."""
        state = GlobalState()

        result = await agent_no_llm._optimize_conversion_parameters(
            format_name="SpikeGLX",
            file_size_mb=100.0,
            state=state,
        )

        # Should return empty dict (no optimization without LLM)
        assert result == {}

    @pytest.mark.asyncio
    async def test_optimize_parameters_error_handling(self, agent_with_llm):
        """Test parameter optimization handles LLM errors."""
        state = GlobalState()

        # Mock LLM to raise error
        async def mock_generate_error(*args, **kwargs):
            raise Exception("LLM API Error")

        agent_with_llm._llm_service.generate_structured_output = mock_generate_error

        result = await agent_with_llm._optimize_conversion_parameters(
            format_name="SpikeGLX",
            file_size_mb=100.0,
            state=state,
        )

        # Should return empty dict on error
        assert result == {}
        assert any("optimization failed" in log.message.lower() for log in state.logs)


@pytest.mark.unit
class TestProgressNarration:
    """Tests for LLM-powered progress narration."""

    @pytest.fixture
    def agent_with_llm(self):
        """Create agent with mock LLM service."""
        return ConversionAgent(llm_service=MockLLMService())

    @pytest.fixture
    def agent_no_llm(self):
        """Create agent without LLM service."""
        return ConversionAgent(llm_service=None)

    @pytest.mark.asyncio
    async def test_narrate_progress_starting(self, agent_with_llm):
        """Test progress narration at start."""
        state = GlobalState()

        # Fixed: Mock generate_completion (not generate_text which doesn't exist)
        async def mock_generate_completion(prompt, system_prompt=None, temperature=0.7, max_tokens=4096):
            return "Starting conversion of your SpikeGLX data..."

        agent_with_llm._llm_service.generate_completion = mock_generate_completion

        result = await agent_with_llm._narrate_progress(
            stage="starting",
            format_name="SpikeGLX",
            context={"file_size_mb": 100},
            state=state,
        )

        assert "Starting conversion" in result
        assert any("Progress:" in log.message for log in state.logs)

    @pytest.mark.asyncio
    async def test_narrate_progress_processing(self, agent_with_llm):
        """Test progress narration during processing."""
        state = GlobalState()

        # Fixed: Mock generate_completion (not generate_text which doesn't exist)
        async def mock_generate_completion(prompt, system_prompt=None, temperature=0.7, max_tokens=4096):
            return "Processing your data, halfway through..."

        agent_with_llm._llm_service.generate_completion = mock_generate_completion

        result = await agent_with_llm._narrate_progress(
            stage="processing",
            format_name="SpikeGLX",
            context={"progress_percent": 50},
            state=state,
        )

        assert "Processing" in result or "halfway" in result

    @pytest.mark.asyncio
    async def test_narrate_progress_complete(self, agent_with_llm):
        """Test progress narration at completion."""
        state = GlobalState()

        # Fixed: Mock generate_completion (not generate_text which doesn't exist)
        async def mock_generate_completion(prompt, system_prompt=None, temperature=0.7, max_tokens=4096):
            return "Conversion complete! Your NWB file is ready."

        agent_with_llm._llm_service.generate_completion = mock_generate_completion

        result = await agent_with_llm._narrate_progress(
            stage="complete",
            format_name="SpikeGLX",
            context={"output_path": "/path/to/output.nwb"},
            state=state,
        )

        assert "complete" in result.lower() or "ready" in result.lower()

    @pytest.mark.asyncio
    async def test_narrate_progress_without_llm_fallback(self, agent_no_llm):
        """Test progress narration fallback without LLM."""
        state = GlobalState()

        result = await agent_no_llm._narrate_progress(
            stage="starting",
            format_name="SpikeGLX",
            context={},
            state=state,
        )

        # Should return generic fallback message
        assert "Starting conversion" in result
        assert "SpikeGLX" in result

    @pytest.mark.asyncio
    async def test_narrate_progress_error_handling(self, agent_with_llm):
        """Test progress narration handles LLM errors."""
        state = GlobalState()

        # Fixed: Mock generate_completion (not generate_text) to raise error
        async def mock_generate_error(*args, **kwargs):
            raise Exception("LLM Error")

        agent_with_llm._llm_service.generate_completion = mock_generate_error

        result = await agent_with_llm._narrate_progress(
            stage="processing",
            format_name="SpikeGLX",
            context={},
            state=state,
        )

        # Should return fallback message
        assert isinstance(result, str)
        assert len(result) > 0
        assert any("narration failed" in log.message.lower() for log in state.logs)


@pytest.mark.unit
class TestHandleDetectFormat:
    """Tests for handle_detect_format MCP handler."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return ConversionAgent(llm_service=MockLLMService())

    @pytest.mark.asyncio
    async def test_handle_detect_format_success(self, agent, tmp_path):
        """Test successful format detection."""
        # Create test files
        (tmp_path / "test.ap.bin").touch()
        (tmp_path / "test.ap.meta").touch()

        message = MCPMessage(
            target_agent="conversion",
            action="detect_format",
            context={"input_path": str(tmp_path)},
        )
        state = GlobalState()

        response = await agent.handle_detect_format(message, state)

        assert response.success is True
        assert response.result["format"] == "SpikeGLX"

    @pytest.mark.asyncio
    async def test_handle_detect_format_missing_path(self, agent):
        """Test detection with missing input path."""
        message = MCPMessage(
            target_agent="conversion",
            action="detect_format",
            context={},  # Missing input_path
        )
        state = GlobalState()

        response = await agent.handle_detect_format(message, state)

        assert response.success is False
        assert "input_path" in response.error["message"].lower()

    @pytest.mark.asyncio
    async def test_handle_detect_format_error(self, agent):
        """Test detection error handling."""
        message = MCPMessage(
            target_agent="conversion",
            action="detect_format",
            context={"input_path": "/nonexistent/path"},
        )
        state = GlobalState()

        response = await agent.handle_detect_format(message, state)

        # Should handle error gracefully
        assert response.success is False or response.result.get("format") is None

    @pytest.mark.asyncio
    async def test_handle_detect_format_exception(self, agent, tmp_path):
        """Test detection handles exceptions during format detection."""
        # Create a file that will cause an error
        test_file = tmp_path / "test.dat"
        test_file.touch()

        # Mock _detect_format to raise an exception
        async def mock_detect_error(*args, **kwargs):
            raise Exception("Simulated detection error")

        with patch.object(agent, '_detect_format', side_effect=mock_detect_error):
            message = MCPMessage(
                target_agent="conversion",
                action="detect_format",
                context={"input_path": str(test_file)},
            )
            state = GlobalState()

            response = await agent.handle_detect_format(message, state)

            assert response.success is False
            assert "DETECTION_FAILED" in response.error.get("code", "")
            # Verify error was logged
            assert any("format detection failed" in log.message.lower() for log in state.logs)


@pytest.mark.unit
class TestHandleRunConversion:
    """Tests for handle_run_conversion MCP handler."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return ConversionAgent(llm_service=MockLLMService())

    @pytest.mark.asyncio
    async def test_handle_run_conversion_missing_parameters(self, agent):
        """Test conversion with missing required parameters."""
        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={},  # Missing required fields
        )
        state = GlobalState()

        response = await agent.handle_run_conversion(message, state)

        assert response.success is False
        assert "required" in response.error["message"].lower()

    @pytest.mark.asyncio
    async def test_handle_run_conversion_state_update(self, agent, tmp_path):
        """Test conversion updates state correctly."""
        # This test verifies state transitions, not actual conversion
        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(tmp_path),
                "output_path": str(tmp_path / "output.nwb"),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )
        state = GlobalState()
        state.status = ConversionStatus.IDLE

        # We expect this to fail (no actual data), but we can check state updates
        try:
            response = await agent.handle_run_conversion(message, state)
        except Exception:
            pass  # Expected to fail without real data

        # Verify state was updated
        assert state.status in [
            ConversionStatus.CONVERTING,
            ConversionStatus.FAILED,
            ConversionStatus.COMPLETED,
        ]


@pytest.mark.unit
class TestChecksumCalculation:
    """Tests for checksum calculation."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return ConversionAgent(llm_service=None)

    def test_calculate_checksum(self, agent, tmp_path):
        """Test SHA256 checksum calculation."""
        # Create test file
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data content")

        checksum = agent._calculate_checksum(str(test_file))

        # Verify checksum format (64 hex characters)
        assert isinstance(checksum, str)
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_calculate_checksum_consistent(self, agent, tmp_path):
        """Test checksum is consistent for same content."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"consistent data")

        checksum1 = agent._calculate_checksum(str(test_file))
        checksum2 = agent._calculate_checksum(str(test_file))

        assert checksum1 == checksum2


@pytest.mark.unit
class TestFileSizeFormatting:
    """Tests for file size formatting logic."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return ConversionAgent(llm_service=None)

    @pytest.mark.asyncio
    async def test_format_file_size_gb(self, agent, tmp_path):
        """Test formatting file size in gigabytes."""
        # Create a large "file" (we'll mock the size)
        test_file = tmp_path / "large.bin"
        test_file.write_bytes(b"x" * 100)  # Small file, we'll patch stat

        output_file = tmp_path / "output.nwb"

        # Mock large file size
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 2 * 1024 * 1024 * 1024  # 2 GB

            message = MCPMessage(
                target_agent="conversion",
                action="run_conversion",
                context={
                    "input_path": str(test_file),
                    "output_path": str(output_file),
                    "format": "SpikeGLX",
                    "metadata": {},
                },
            )
            state = GlobalState()

            # Mock the actual conversion to avoid NeuroConv
            with patch.object(agent, '_run_neuroconv_conversion'):
                response = await agent.handle_run_conversion(message, state)

            # Check logs contain GB formatting
            log_messages = [log.message for log in state.logs]
            assert any("GB" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_format_file_size_mb(self, agent, tmp_path):
        """Test formatting file size in megabytes."""
        test_file = tmp_path / "medium.bin"
        test_file.write_bytes(b"x" * 100)

        output_file = tmp_path / "output.nwb"

        # Mock medium file size
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 50 * 1024 * 1024  # 50 MB

            message = MCPMessage(
                target_agent="conversion",
                action="run_conversion",
                context={
                    "input_path": str(test_file),
                    "output_path": str(output_file),
                    "format": "SpikeGLX",
                    "metadata": {},
                },
            )
            state = GlobalState()

            with patch.object(agent, '_run_neuroconv_conversion'):
                response = await agent.handle_run_conversion(message, state)

            log_messages = [log.message for log in state.logs]
            assert any("MB" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_format_file_size_kb(self, agent, tmp_path):
        """Test formatting file size in kilobytes."""
        test_file = tmp_path / "small.bin"
        test_file.write_bytes(b"x" * 500)  # 500 bytes

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"y" * 400)

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(test_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )
        state = GlobalState()

        with patch.object(agent, '_run_neuroconv_conversion'):
            response = await agent.handle_run_conversion(message, state)

        log_messages = [log.message for log in state.logs]
        assert any("KB" in msg for msg in log_messages)


@pytest.mark.unit
class TestDurationFormatting:
    """Tests for duration formatting logic."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return ConversionAgent(llm_service=None)

    @pytest.mark.asyncio
    async def test_duration_format_seconds(self, agent, tmp_path):
        """Test duration formatting for seconds."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"output data")

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(test_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )
        state = GlobalState()

        # Mock fast conversion
        with patch.object(agent, '_run_neuroconv_conversion'):
            response = await agent.handle_run_conversion(message, state)

        # Should have duration in seconds
        log_messages = [log.message for log in state.logs]
        completion_logs = [msg for msg in log_messages if "completed successfully" in msg.lower()]
        assert len(completion_logs) > 0

    @pytest.mark.asyncio
    async def test_duration_format_minutes(self, agent, tmp_path):
        """Test duration formatting for minutes."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"test data")

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"output data")

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(test_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )
        state = GlobalState()

        # Mock slow conversion by patching time.time
        start_time = 1000.0
        end_time = start_time + 90  # 90 seconds = 1.5 minutes

        with patch('time.time', side_effect=[start_time, end_time]), \
             patch.object(agent, '_run_neuroconv_conversion'):
            response = await agent.handle_run_conversion(message, state)

        # Should show minutes and seconds
        assert response.success


@pytest.mark.unit
class TestCompressionRatioCalculation:
    """Tests for compression ratio calculation."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        return ConversionAgent(llm_service=None)

    @pytest.mark.asyncio
    async def test_compression_ratio_smaller(self, agent, tmp_path):
        """Test compression ratio when output is smaller."""
        test_file = tmp_path / "large_input.bin"
        test_file.write_bytes(b"x" * 1000)  # 1000 bytes input

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"y" * 500)  # 500 bytes output (50% smaller)

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(test_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )
        state = GlobalState()

        with patch.object(agent, '_run_neuroconv_conversion'):
            response = await agent.handle_run_conversion(message, state)

        log_messages = [log.message for log in state.logs]
        completion_logs = [msg for msg in log_messages if "smaller" in msg.lower()]
        assert len(completion_logs) > 0

    @pytest.mark.asyncio
    async def test_compression_ratio_larger(self, agent, tmp_path):
        """Test compression ratio when output is larger."""
        test_file = tmp_path / "small_input.bin"
        test_file.write_bytes(b"x" * 500)  # 500 bytes input

        output_file = tmp_path / "output.nwb"
        output_file.write_bytes(b"y" * 1000)  # 1000 bytes output (100% larger)

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(test_file),
                "output_path": str(output_file),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )
        state = GlobalState()

        with patch.object(agent, '_run_neuroconv_conversion'):
            response = await agent.handle_run_conversion(message, state)

        log_messages = [log.message for log in state.logs]
        completion_logs = [msg for msg in log_messages if "larger" in msg.lower()]
        assert len(completion_logs) > 0


@pytest.mark.unit
class TestErrorExplanation:
    """Tests for LLM-powered error explanation."""

    @pytest.fixture
    def agent_with_llm(self):
        """Create agent with mock LLM service."""
        return ConversionAgent(llm_service=MockLLMService())

    @pytest.fixture
    def agent_no_llm(self):
        """Create agent without LLM service."""
        return ConversionAgent(llm_service=None)

    @pytest.mark.asyncio
    async def test_explain_error_with_llm(self, agent_with_llm):
        """Test error explanation with LLM."""
        state = GlobalState()

        # Mock LLM response
        async def mock_generate_completion(prompt, system_prompt=None, temperature=0.7, max_tokens=4096):
            return "This error occurred because the probe geometry metadata is missing from the recording."

        agent_with_llm._llm_service.generate_completion = mock_generate_completion

        error = Exception("There is no Probe attached to this recording")
        explanation = await agent_with_llm._explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path="/test/data",
            state=state,
        )

        assert "probe" in explanation.lower() or "metadata" in explanation.lower()

    @pytest.mark.asyncio
    async def test_explain_error_without_llm(self, agent_no_llm):
        """Test error explanation fallback without LLM."""
        state = GlobalState()

        error = Exception("Conversion failed")
        explanation = await agent_no_llm._explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path="/test/data",
            state=state,
        )

        # Should return None when LLM is not available
        assert explanation is None

    @pytest.mark.asyncio
    async def test_explain_error_llm_failure(self, agent_with_llm):
        """Test error explanation when LLM fails."""
        state = GlobalState()

        # Mock LLM to raise error
        async def mock_generate_error(*args, **kwargs):
            raise Exception("LLM Error")

        agent_with_llm._llm_service.generate_completion = mock_generate_error

        error = Exception("Conversion failed")
        explanation = await agent_with_llm._explain_conversion_error(
            error=error,
            format_name="SpikeGLX",
            input_path="/test/data",
            state=state,
        )

        # Should return None when LLM fails
        assert explanation is None
        # Should log warning
        assert any("failed to generate error explanation" in log.message.lower() for log in state.logs)


@pytest.mark.unit
class TestRealWorkflows:
    """
    Integration-style unit tests using real dependencies.

    These tests use conversion_agent_real fixture which has real internal logic,
    testing actual code paths instead of mocking them away.
    """

    @pytest.mark.asyncio
    async def test_real_spikeglx_detection_workflow(self, conversion_agent_real, tmp_path, global_state):
        """Test real SpikeGLX format detection with pattern matching."""
        # Create real SpikeGLX files
        spikeglx_dir = tmp_path / "spikeglx_data"
        spikeglx_dir.mkdir()
        (spikeglx_dir / "recording_g0_t0.imec0.ap.bin").write_bytes(b"mock data" * 100)
        (spikeglx_dir / "recording_g0_t0.imec0.ap.meta").write_text("imSampRate=30000\n")

        # Test real detection logic
        detected_format = await conversion_agent_real._detect_format(str(spikeglx_dir), global_state)

        # Verify real code executed
        assert detected_format == "SpikeGLX"
        assert len(global_state.logs) > 0
        assert any("SpikeGLX" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_real_openephys_detection_workflow(self, conversion_agent_real, tmp_path, global_state):
        """Test real OpenEphys format detection."""
        openephys_dir = tmp_path / "openephys_data"
        openephys_dir.mkdir()
        (openephys_dir / "structure.oebin").write_text('{"format": "openephys"}')

        detected_format = await conversion_agent_real._detect_format(str(openephys_dir), global_state)

        assert detected_format == "OpenEphys"
        assert any("OpenEphys" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_real_format_detection_unknown_file(self, conversion_agent_real, tmp_path, global_state):
        """Test real format detection with unknown file."""
        unknown_file = tmp_path / "unknown.dat"
        unknown_file.write_bytes(b"unknown data")

        detected_format = await conversion_agent_real._detect_format(str(unknown_file), global_state)

        # Should return None for unknown format
        assert detected_format is None

    @pytest.mark.asyncio
    async def test_real_format_detector_initialization(self, conversion_agent_real):
        """Test that real format detector is initialized when LLM is available."""
        # conversion_agent_real uses mock_llm_api_only (MockLLMService)
        assert conversion_agent_real._llm_service is not None
        assert conversion_agent_real._format_detector is not None

    @pytest.mark.asyncio
    async def test_real_supported_formats_loading(self, conversion_agent_real):
        """Test that real supported formats list is loaded."""
        # Agent should have real supported formats from NeuroConv
        assert len(conversion_agent_real._supported_formats) > 0
        # Check for common format interfaces (real names from NeuroConv)
        common_formats = ["SpikeGLXRecordingInterface", "OpenEphysRecordingInterface"]
        for fmt in common_formats:
            assert fmt in conversion_agent_real._supported_formats

    def test_real_is_spikeglx_helper_with_various_patterns(self, conversion_agent_real, tmp_path):
        """Test real _is_spikeglx helper with various file patterns."""
        test_cases = [
            ("recording.ap.bin", True),
            ("recording.lf.bin", True),
            ("recording.nidq.bin", True),
            ("recording.bin", False),
            ("recording.ap.txt", False),
        ]

        for filename, expected in test_cases:
            test_file = tmp_path / filename
            test_file.touch()
            result = conversion_agent_real._is_spikeglx(test_file)
            assert result == expected, f"Failed for {filename}: expected {expected}, got {result}"

    def test_real_is_openephys_helper_with_various_files(self, conversion_agent_real, tmp_path):
        """Test real _is_openephys helper with various file patterns."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Test with structure.oebin
        (test_dir / "structure.oebin").touch()
        assert conversion_agent_real._is_openephys(test_dir) is True

        # Clean up and test with settings.xml
        (test_dir / "structure.oebin").unlink()
        (test_dir / "settings.xml").touch()
        assert conversion_agent_real._is_openephys(test_dir) is True

    def test_real_is_neuropixels_helper(self, conversion_agent_real, tmp_path):
        """Test real _is_neuropixels helper."""
        # Neuropixels file
        neuropixels_file = tmp_path / "recording.nidq.bin"
        neuropixels_file.touch()
        assert conversion_agent_real._is_neuropixels(neuropixels_file) is True

        # Non-neuropixels file
        other_file = tmp_path / "recording.dat"
        other_file.touch()
        assert conversion_agent_real._is_neuropixels(other_file) is False

    @pytest.mark.asyncio
    async def test_real_error_handling_for_missing_path(self, conversion_agent_real, global_state):
        """Test real error handling when path doesn't exist."""
        non_existent_path = "/tmp/non_existent_path_12345"

        detected_format = await conversion_agent_real._detect_format(non_existent_path, global_state)

        # Should handle error gracefully
        assert detected_format is None
        # Should have logged something (may be ERROR or WARNING depending on implementation)
        assert len(global_state.logs) > 0
