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


class TestConversionAgentInitialization:
    """Tests for ConversionAgent initialization."""

    def test_init_without_llm_service(self):
        """Test agent initializes without LLM service."""
        agent = ConversionAgent(llm_service=None)

        assert agent._llm_service is None
        assert agent._supported_formats is not None
        assert isinstance(agent._supported_formats, list)

    def test_init_with_llm_service(self):
        """Test agent initializes with LLM service."""
        mock_llm = MockLLMService()
        agent = ConversionAgent(llm_service=mock_llm)

        assert agent._llm_service is mock_llm
        assert agent._supported_formats is not None


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
        # Create Neuropixels file
        (temp_dir / "test.nidq.bin").touch()

        state = GlobalState()
        result = await agent_no_llm._detect_format(str(temp_dir / "test.nidq.bin"), state)

        assert result == "Neuropixels"

    @pytest.mark.asyncio
    async def test_llm_first_detection_high_confidence(self, agent_with_llm, temp_dir):
        """Test LLM detection tried first with high confidence."""
        # Create ambiguous file
        (temp_dir / "data.bin").touch()

        # Mock LLM to return high confidence
        agent_with_llm._llm_service.set_response(
            "detect",
            '{"format": "CustomFormat", "confidence": 85, "indicators": ["file pattern"]}'
        )

        # Patch _detect_format_with_llm to return mock result
        async def mock_detect_llm(input_path, state):
            return {"format": "CustomFormat", "confidence": 85}

        agent_with_llm._detect_format_with_llm = mock_detect_llm

        state = GlobalState()
        result = await agent_with_llm._detect_format(str(temp_dir / "data.bin"), state)

        # Should use LLM result due to high confidence
        assert result == "CustomFormat"
        assert any("LLM detected format" in log.message for log in state.logs)

    @pytest.mark.asyncio
    async def test_llm_detection_low_confidence_fallback(self, agent_with_llm, temp_dir):
        """Test LLM low confidence triggers pattern matching fallback."""
        # Create SpikeGLX files
        (temp_dir / "test.ap.bin").touch()
        (temp_dir / "test.ap.meta").touch()

        # Mock LLM to return low confidence
        async def mock_detect_llm(input_path, state):
            return {"format": "Unknown", "confidence": 50}

        agent_with_llm._detect_format_with_llm = mock_detect_llm

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

        # Mock LLM response
        async def mock_generate_text(prompt, system_prompt=None):
            return "Starting conversion of your SpikeGLX data..."

        agent_with_llm._llm_service.generate_text = mock_generate_text

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

        async def mock_generate_text(prompt, system_prompt=None):
            return "Processing your data, halfway through..."

        agent_with_llm._llm_service.generate_text = mock_generate_text

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

        async def mock_generate_text(prompt, system_prompt=None):
            return "Conversion complete! Your NWB file is ready."

        agent_with_llm._llm_service.generate_text = mock_generate_text

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

        # Mock LLM to raise error
        async def mock_generate_error(*args, **kwargs):
            raise Exception("LLM Error")

        agent_with_llm._llm_service.generate_text = mock_generate_error

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
