"""
Unit tests for ConversionAgent - NeuroConv Integration (Task 5.1).

Tests the _convert_to_nwb method for converting OpenEphys datasets to NWB format
using NeuroConv library.

Test coverage:
- Conversion with valid OpenEphys dataset
- NWB file creation verification
- Conversion duration tracking
- Output path verification
- Gzip compression verification
- Error handling for corrupt dataset
- Error handling for missing files
- Error capture includes full stack trace

Note: Tests mock the OpenEphysRecordingInterface to focus on testing the
ConversionAgent logic rather than the underlying NeuroConv library behavior.
"""

from pathlib import Path
import time
import traceback
from unittest.mock import MagicMock, Mock, patch

import h5py
import pytest

from agentic_neurodata_conversion.agents.conversion_agent import ConversionAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.session_context import ConversionResults


@pytest.fixture
def conversion_agent(tmp_path: Path) -> ConversionAgent:
    """Create ConversionAgent instance for testing."""
    config = AgentConfig(
        agent_name="test-conversion-agent",
        agent_type="conversion",
        agent_port=8002,
        mcp_server_url="http://localhost:3000",
        llm_provider="anthropic",
        llm_api_key="test-key",
        llm_model="claude-3-5-sonnet-20241022",
        temperature=0.3,
        max_tokens=8192,
    )
    return ConversionAgent(config)


@pytest.fixture
def test_metadata() -> dict:
    """Create test metadata for NWB conversion."""
    return {
        "subject_id": "TestMouse001",
        "species": "Mus musculus",
        "age": "P56",
        "sex": "M",
        "session_description": "Test session for conversion",
        "session_start_time": "2024-01-15T12:00:00Z",
        "experimenter": "Test User",
        "lab": "Test Lab",
        "institution": "Test University",
        "device_name": "OpenEphys",
        "device_manufacturer": "Open Ephys",
        "device_description": "Open Ephys Acquisition Board",
    }


def create_mock_nwb_file(filepath: Path) -> None:
    """Create a minimal valid NWB file for testing."""
    with h5py.File(filepath, "w") as f:
        # Create minimal NWB structure
        f.create_group("acquisition")
        f.create_group("general")
        f.create_group("specifications")
        # Add some compressed datasets
        f.create_dataset(
            "acquisition/test_data",
            data=[1, 2, 3, 4, 5],
            compression="gzip",
        )


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_convert_to_nwb_valid_dataset(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
    test_dataset_path: Path,
    test_metadata: dict,
    tmp_path: Path,
) -> None:
    """Test conversion with valid OpenEphys dataset."""
    session_id = "test-session-001"
    dataset_path = str(test_dataset_path)

    # Create mock interface that generates a real NWB file when run_conversion is called
    mock_interface = Mock()

    def mock_run_conversion(nwbfile_path, metadata, overwrite=True, compression="gzip"):
        # Create a mock NWB file
        create_mock_nwb_file(Path(nwbfile_path))

    mock_interface.run_conversion = mock_run_conversion
    mock_interface_class.return_value = mock_interface

    # Run conversion
    result = await conversion_agent._convert_to_nwb(
        session_id=session_id,
        dataset_path=dataset_path,
        metadata=test_metadata,
    )

    # Verify result type
    assert isinstance(result, ConversionResults)

    # Verify NWB file was created
    assert result.nwb_file_path is not None
    nwb_path = Path(result.nwb_file_path)
    assert nwb_path.exists()
    assert nwb_path.suffix == ".nwb"

    # Verify conversion duration was tracked
    assert result.conversion_duration_seconds is not None
    assert result.conversion_duration_seconds > 0

    # Verify interface was called correctly
    mock_interface_class.assert_called_once_with(folder_path=dataset_path)


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_nwb_file_created_successfully(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
    test_dataset_path: Path,
    test_metadata: dict,
    tmp_path: Path,
) -> None:
    """Test NWB file created successfully."""
    session_id = "test-session-002"
    dataset_path = str(test_dataset_path)

    # Mock interface
    mock_interface = Mock()

    def mock_run_conversion(nwbfile_path, metadata, overwrite=True, compression="gzip"):
        create_mock_nwb_file(Path(nwbfile_path))

    mock_interface.run_conversion = mock_run_conversion
    mock_interface_class.return_value = mock_interface

    result = await conversion_agent._convert_to_nwb(
        session_id=session_id,
        dataset_path=dataset_path,
        metadata=test_metadata,
    )

    # Verify file exists and is not empty
    nwb_path = Path(result.nwb_file_path)
    assert nwb_path.exists()
    assert nwb_path.stat().st_size > 0

    # Verify it's a valid HDF5 file (NWB format)
    with h5py.File(nwb_path, "r") as f:
        # NWB files should have these root groups
        assert "acquisition" in f or "general" in f or "specifications" in f


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_conversion_duration_tracked(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
    test_dataset_path: Path,
    test_metadata: dict,
    tmp_path: Path,
) -> None:
    """Test conversion duration tracked."""
    session_id = "test-session-003"
    dataset_path = str(test_dataset_path)

    # Mock interface with a small delay
    mock_interface = Mock()

    def mock_run_conversion(nwbfile_path, metadata, overwrite=True, compression="gzip"):
        time.sleep(0.1)  # Small delay to simulate conversion
        create_mock_nwb_file(Path(nwbfile_path))

    mock_interface.run_conversion = mock_run_conversion
    mock_interface_class.return_value = mock_interface

    start_time = time.time()
    result = await conversion_agent._convert_to_nwb(
        session_id=session_id,
        dataset_path=dataset_path,
        metadata=test_metadata,
    )
    end_time = time.time()
    actual_duration = end_time - start_time

    # Verify duration is tracked and reasonable
    assert result.conversion_duration_seconds is not None
    assert result.conversion_duration_seconds > 0
    # Should be within a reasonable range
    assert result.conversion_duration_seconds >= 0.1  # At least the sleep time
    assert (
        result.conversion_duration_seconds < actual_duration + 1
    )  # Not too much overhead


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_output_path_set_correctly(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
    test_dataset_path: Path,
    test_metadata: dict,
    tmp_path: Path,
) -> None:
    """Test output path set correctly."""
    session_id = "test-session-004"
    dataset_path = str(test_dataset_path)

    # Mock interface
    mock_interface = Mock()

    def mock_run_conversion(nwbfile_path, metadata, overwrite=True, compression="gzip"):
        create_mock_nwb_file(Path(nwbfile_path))

    mock_interface.run_conversion = mock_run_conversion
    mock_interface_class.return_value = mock_interface

    result = await conversion_agent._convert_to_nwb(
        session_id=session_id,
        dataset_path=dataset_path,
        metadata=test_metadata,
    )

    # Verify path contains session ID
    assert session_id in result.nwb_file_path

    # Verify path is absolute
    nwb_path = Path(result.nwb_file_path)
    assert nwb_path.is_absolute()


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_gzip_compression_applied(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
    test_dataset_path: Path,
    test_metadata: dict,
    tmp_path: Path,
) -> None:
    """Test gzip compression applied."""
    session_id = "test-session-005"
    dataset_path = str(test_dataset_path)

    # Mock interface
    mock_interface = Mock()
    mock_run_conversion = Mock()

    def run_conv_side_effect(
        nwbfile_path, metadata, overwrite=True, compression="gzip"
    ):
        create_mock_nwb_file(Path(nwbfile_path))
        # Store the compression argument for verification
        mock_run_conversion.last_compression = compression

    mock_interface.run_conversion = run_conv_side_effect
    mock_interface_class.return_value = mock_interface

    result = await conversion_agent._convert_to_nwb(
        session_id=session_id,
        dataset_path=dataset_path,
        metadata=test_metadata,
    )

    # Verify HDF5 file has compression enabled
    nwb_path = Path(result.nwb_file_path)
    with h5py.File(nwb_path, "r") as f:
        # Check at least one dataset has compression
        has_compression = False
        for name in f:
            if isinstance(f[name], h5py.Dataset):
                if f[name].compression is not None:
                    has_compression = True
                    break
            elif isinstance(f[name], h5py.Group):
                # Check within group
                for subname in f[name]:
                    if isinstance(f[name][subname], h5py.Dataset):
                        if f[name][subname].compression is not None:
                            has_compression = True
                            break
        assert has_compression, "No compressed datasets found in NWB file"


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_error_handling_corrupt_dataset(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
    tmp_path: Path,
    test_metadata: dict,
) -> None:
    """Test error handling for corrupt dataset."""
    session_id = "test-session-006"

    # Create corrupt dataset directory
    corrupt_path = tmp_path / "corrupt_dataset"
    corrupt_path.mkdir()
    dataset_path = str(corrupt_path)

    # Mock interface to raise an exception for corrupt data
    mock_interface_class.side_effect = ValueError("Invalid OpenEphys dataset structure")

    # Should raise an exception
    with pytest.raises(ValueError, match="Invalid OpenEphys dataset structure"):
        await conversion_agent._convert_to_nwb(
            session_id=session_id,
            dataset_path=dataset_path,
            metadata=test_metadata,
        )


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_error_handling_missing_files(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
    tmp_path: Path,
    test_metadata: dict,
) -> None:
    """Test error handling for missing files."""
    session_id = "test-session-007"

    # Use non-existent directory
    missing_path = tmp_path / "nonexistent_dataset"
    dataset_path = str(missing_path)

    # Mock interface to raise FileNotFoundError
    mock_interface_class.side_effect = FileNotFoundError(
        f"Dataset not found: {dataset_path}"
    )

    # Should raise an exception
    with pytest.raises(FileNotFoundError):
        await conversion_agent._convert_to_nwb(
            session_id=session_id,
            dataset_path=dataset_path,
            metadata=test_metadata,
        )


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_error_capture_includes_stack_trace(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
    tmp_path: Path,
    test_metadata: dict,
) -> None:
    """Test error capture includes full stack trace."""
    session_id = "test-session-008"

    # Create invalid dataset
    invalid_path = tmp_path / "invalid_dataset"
    invalid_path.mkdir()
    dataset_path = str(invalid_path)

    # Mock interface to raise an exception
    mock_interface_class.side_effect = RuntimeError(
        "Conversion failed due to invalid data format"
    )

    # Capture the exception and verify it includes stack trace
    try:
        await conversion_agent._convert_to_nwb(
            session_id=session_id,
            dataset_path=dataset_path,
            metadata=test_metadata,
        )
        pytest.fail("Expected exception to be raised")
    except Exception:
        # Get full stack trace
        stack_trace = traceback.format_exc()

        # Verify stack trace contains expected information
        assert "_convert_to_nwb" in stack_trace
        assert "RuntimeError" in stack_trace
        assert "Conversion failed" in stack_trace
        assert len(stack_trace) > 100  # Should be substantial
