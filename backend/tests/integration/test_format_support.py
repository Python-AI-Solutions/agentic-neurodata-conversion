"""
Integration tests for format support.

Tests actual conversion workflows for each supported format.
These tests require test data files to be present.
"""
import pytest
from pathlib import Path
from backend.src.agents.conversion_agent import ConversionAgent
from backend.src.models import GlobalState, MCPMessage


class TestFormatDetection:
    """Test format auto-detection for various neuroscience data formats."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ConversionAgent(llm_service=None)
        self.test_data_dir = Path("test_data")

    def test_spikeglx_detection(self):
        """Test that SpikeGLX format is correctly detected."""
        # Test with directory containing .ap.bin and .meta files
        test_dir = self.test_data_dir / "spikeglx"
        if not test_dir.exists():
            pytest.skip("SpikeGLX test data not available")

        assert self.agent._is_spikeglx(test_dir)

    def test_openephys_detection_new_format(self):
        """Test detection of new OpenEphys format (structure.oebin)."""
        test_dir = self.test_data_dir / "openephys" / "new_format"
        if not test_dir.exists():
            pytest.skip("OpenEphys test data not available")

        assert self.agent._is_openephys(test_dir)

    def test_openephys_detection_old_format(self):
        """Test detection of old OpenEphys format (settings.xml)."""
        test_dir = self.test_data_dir / "openephys" / "old_format"
        if not test_dir.exists():
            pytest.skip("OpenEphys old format test data not available")

        assert self.agent._is_openephys(test_dir)

    def test_neuropixels_detection(self):
        """Test that Neuropixels format is correctly detected."""
        test_dir = self.test_data_dir / "neuropixels"
        if not test_dir.exists():
            pytest.skip("Neuropixels test data not available")

        assert self.agent._is_neuropixels(test_dir)

    def test_false_positive_prevention(self):
        """Test that random directories aren't detected as valid formats."""
        random_dir = self.test_data_dir / "random"
        random_dir.mkdir(exist_ok=True, parents=True)

        # Create a random file that shouldn't match any format
        (random_dir / "random_file.txt").write_text("random content")

        assert not self.agent._is_spikeglx(random_dir)
        assert not self.agent._is_openephys(random_dir)
        assert not self.agent._is_neuropixels(random_dir)

        # Cleanup
        (random_dir / "random_file.txt").unlink()
        random_dir.rmdir()


@pytest.mark.asyncio
@pytest.mark.slow
class TestFormatConversion:
    """
    Integration tests for end-to-end format conversion.

    These tests are marked as slow because they involve actual file conversion.
    Run with: pytest -m slow
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ConversionAgent(llm_service=None)
        self.state = GlobalState()
        self.output_dir = Path("test_output")
        self.output_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up after tests."""
        # Optional: Clean up generated files
        pass

    async def test_spikeglx_conversion(self):
        """Test complete SpikeGLX to NWB conversion."""
        test_data = Path("test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin")
        if not test_data.exists():
            pytest.skip("SpikeGLX test data not available")

        output_path = self.output_dir / "spikeglx_output.nwb"

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(test_data.parent),
                "output_path": str(output_path),
                "format": "SpikeGLX",
                "metadata": {
                    "experimenter": "Test User",
                    "institution": "Test Lab",
                    "session_description": "Integration test",
                },
            },
        )

        response = await self.agent.handle_run_conversion(message, self.state)

        assert response.success, f"Conversion failed: {response.error}"
        assert output_path.exists(), "Output NWB file was not created"
        assert output_path.stat().st_size > 0, "Output file is empty"

    async def test_openephys_conversion(self):
        """Test OpenEphys to NWB conversion."""
        pytest.skip("Implement when OpenEphys test data is available")

    async def test_neuropixels_conversion(self):
        """Test Neuropixels to NWB conversion."""
        pytest.skip("Implement when Neuropixels test data is available")


@pytest.mark.asyncio
class TestProgressTracking:
    """Test that progress is correctly tracked during conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ConversionAgent(llm_service=None)
        self.state = GlobalState()

    async def test_progress_updates(self):
        """Test that progress is updated throughout conversion."""
        test_data = Path("test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin")
        if not test_data.exists():
            pytest.skip("Test data not available")

        output_path = Path("test_output/progress_test.nwb")
        output_path.parent.mkdir(exist_ok=True)

        message = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": str(test_data.parent),
                "output_path": str(output_path),
                "format": "SpikeGLX",
                "metadata": {},
            },
        )

        # Track progress updates
        initial_progress = self.state.progress_percent
        assert initial_progress == 0.0

        response = await self.agent.handle_run_conversion(message, self.state)

        if response.success:
            # Progress should reach 100% on successful completion
            assert self.state.progress_percent == 100.0
            assert self.state.current_stage == "complete"
            assert self.state.progress_message is not None

            # Check that we went through multiple stages
            log_messages = [log.message for log in self.state.logs]
            progress_logs = [msg for msg in log_messages if "Progress:" in msg]
            assert len(progress_logs) > 5, "Expected multiple progress updates"


class TestMetadataMapping:
    """Test that metadata is correctly mapped during conversion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ConversionAgent(llm_service=None)

    def test_metadata_applied_to_nwb(self):
        """Test that user-provided metadata appears in the NWB file."""
        # This is tested in unit tests, but could be extended here
        # to verify by actually reading the NWB file with pynwb
        pytest.skip("Implement NWB file reading verification")


# Mark tests that require actual data files
pytestmark = pytest.mark.integration
