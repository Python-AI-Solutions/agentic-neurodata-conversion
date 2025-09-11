"""Configuration for integration tests.

This module provides shared fixtures and configuration for integration tests,
particularly for adapter parity testing.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
import tempfile

import pytest

from agentic_neurodata_conversion.mcp_server.http_adapter import HTTPAdapter
from agentic_neurodata_conversion.mcp_server.mcp_adapter import MCPAdapter

# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest for integration tests."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "adapter_parity: Tests that verify adapter parity"
    )
    config.addinivalue_line(
        "markers",
        "slow_integration: Slow integration tests that may take several seconds",
    )


def pytest_collection_modifyitems(items):
    """Modify test collection to add appropriate markers."""
    for item in items:
        # Mark adapter parity tests
        if "parity" in item.name.lower():
            item.add_marker(pytest.mark.adapter_parity)

        # Mark slow tests
        if any(
            keyword in item.name.lower()
            for keyword in ["performance", "concurrent", "comprehensive"]
        ):
            item.add_marker(pytest.mark.slow_integration)


# ============================================================================
# Async Test Support
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Adapter Fixtures
# ============================================================================


@pytest.fixture
async def clean_mcp_adapter() -> AsyncGenerator[MCPAdapter, None]:
    """Create a clean MCP adapter for testing."""
    adapter = MCPAdapter()
    await adapter.initialize()
    yield adapter
    await adapter.shutdown()


@pytest.fixture
async def clean_http_adapter() -> AsyncGenerator[HTTPAdapter, None]:
    """Create a clean HTTP adapter for testing."""
    adapter = HTTPAdapter()
    await adapter.initialize()
    yield adapter
    await adapter.shutdown()


@pytest.fixture
async def isolated_adapters() -> AsyncGenerator[tuple[MCPAdapter, HTTPAdapter], None]:
    """Create isolated adapter instances for parity testing."""
    mcp_adapter = MCPAdapter()
    http_adapter = HTTPAdapter()

    await mcp_adapter.initialize()
    await http_adapter.initialize()

    yield mcp_adapter, http_adapter

    await mcp_adapter.shutdown()
    await http_adapter.shutdown()


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_data_directory() -> Generator[Path, None, None]:
    """Create a temporary directory with test data."""
    with tempfile.TemporaryDirectory(prefix="integration_test_") as temp_dir:
        test_dir = Path(temp_dir)

        # Create comprehensive test dataset
        _create_test_dataset(test_dir)

        yield test_dir


def _create_test_dataset(base_path: Path) -> None:
    """Create a comprehensive test dataset."""
    # Electrophysiology data
    ephys_dir = base_path / "ephys"
    ephys_dir.mkdir()

    # Create binary data file
    (ephys_dir / "continuous.dat").write_bytes(b"\\x00\\x01\\x02\\x03" * 2500)

    # Create channel map
    (ephys_dir / "channel_map.txt").write_text(
        "channel_id,x_coord,y_coord,brain_region\\n"
        "0,100,200,CA1\\n"
        "1,110,200,CA1\\n"
        "2,120,200,CA1\\n"
        "3,130,200,CA1\\n"
    )

    # Behavioral data
    behavior_dir = base_path / "behavior"
    behavior_dir.mkdir()

    (behavior_dir / "position_tracking.csv").write_text(
        "timestamp,x_position,y_position,head_direction,speed\\n"
        "0.000,50.5,75.3,90.0,5.2\\n"
        "0.033,50.7,75.4,91.2,5.3\\n"
        "0.066,50.9,75.5,92.1,5.4\\n"
        "0.100,51.1,75.6,93.0,5.5\\n"
    )

    (behavior_dir / "events.txt").write_text(
        "timestamp,event_type,event_value\\n"
        "10.5,reward,1\\n"
        "25.3,tone,440\\n"
        "45.7,reward,1\\n"
        "67.2,tone,880\\n"
    )

    # Metadata files
    metadata_dir = base_path / "metadata"
    metadata_dir.mkdir()

    (metadata_dir / "session_info.json").write_text(
        """
    {
        "subject_id": "test_mouse_001",
        "session_id": "integration_test_session",
        "experiment_description": "Comprehensive integration test with multi-modal data",
        "experimenter": "Integration Test Suite",
        "institution": "Test Research Institute",
        "session_start_time": "2024-01-01T09:00:00",
        "session_end_time": "2024-01-01T10:30:00",
        "data_format": "custom_test_format",
        "sampling_rates": {
            "ephys": 30000,
            "behavior": 30,
            "events": 1000
        },
        "hardware": {
            "ephys_system": "test_acquisition_system",
            "camera_system": "test_tracking_system",
            "sync_system": "test_sync_box"
        },
        "experimental_conditions": {
            "environment": "open_field",
            "lighting": "dim",
            "temperature": 22.5,
            "humidity": 45
        }
    }
    """
    )

    (metadata_dir / "experiment_protocol.yaml").write_text(
        """
    protocol:
      name: integration_test_protocol
      version: 1.0
      description: Multi-modal data collection for integration testing

    phases:
      - name: baseline
        duration: 600
        description: Baseline recording
      - name: stimulation
        duration: 1800
        description: Experimental stimulation phase
      - name: recovery
        duration: 600
        description: Post-stimulation recovery

    data_streams:
      - name: ephys
        type: electrophysiology
        channels: 4
        sampling_rate: 30000
      - name: behavior
        type: position_tracking
        sampling_rate: 30
      - name: events
        type: experimental_events
        sampling_rate: 1000
    """
    )

    # Configuration files
    config_dir = base_path / "config"
    config_dir.mkdir()

    (config_dir / "acquisition_settings.ini").write_text(
        """
    [Acquisition]
    SamplingRate=30000
    Channels=4
    BufferSize=1024

    [Filtering]
    HighPass=300
    LowPass=6000
    NotchFilter=60

    [Recording]
    Format=binary
    Compression=none
    ChunkSize=1000000
    """
    )

    # Analysis results (simulated)
    analysis_dir = base_path / "analysis"
    analysis_dir.mkdir()

    (analysis_dir / "spike_times.txt").write_text(
        "unit_id,spike_time\\n"
        "1,0.125\\n"
        "1,0.287\\n"
        "1,0.445\\n"
        "2,0.156\\n"
        "2,0.334\\n"
        "2,0.512\\n"
    )

    (analysis_dir / "lfp_power.csv").write_text(
        "frequency,power,channel\\n4,0.85,0\\n8,1.23,0\\n12,0.67,0\\n30,0.34,0\\n"
    )


# ============================================================================
# Test Utilities
# ============================================================================


@pytest.fixture
def test_session_id():
    """Generate a unique session ID for testing."""
    import uuid

    return f"test_session_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_llm_responses():
    """Provide mock LLM responses for testing."""
    return {
        "dataset_analysis": {
            "analysis_summary": "Test dataset contains electrophysiology and behavioral data",
            "detected_formats": ["binary", "csv", "json"],
            "recommendations": [
                "Convert to NWB format",
                "Validate metadata completeness",
            ],
        },
        "metadata_extraction": {
            "extracted_fields": ["subject_id", "session_id", "sampling_rate"],
            "missing_fields": ["electrode_locations"],
            "confidence": 0.85,
        },
        "conversion_script": {
            "script_type": "nwb_conversion",
            "estimated_duration": "5-10 minutes",
            "requirements": ["pynwb", "neo", "spikeinterface"],
        },
    }


# ============================================================================
# Performance Monitoring
# ============================================================================


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during tests."""
    import time

    import psutil

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.metrics = {}

        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss

        def stop(self):
            if self.start_time:
                self.metrics["duration"] = time.time() - self.start_time
                self.metrics["memory_delta"] = (
                    psutil.Process().memory_info().rss - self.start_memory
                )
                return self.metrics
            return {}

    return PerformanceMonitor()


# ============================================================================
# Cleanup Utilities
# ============================================================================


@pytest.fixture(autouse=True)
async def cleanup_sessions():
    """Automatically cleanup test sessions after each test."""
    yield

    # Cleanup logic would go here
    # For now, we rely on adapter shutdown in fixtures
    pass


# ============================================================================
# Test Markers and Configuration
# ============================================================================

# Custom pytest markers for integration tests

# Test timeout configuration
INTEGRATION_TEST_TIMEOUT = 30  # seconds
SLOW_TEST_TIMEOUT = 60  # seconds

# Note: pytest_timeout_set_timer hook is only available when pytest-timeout plugin is loaded
# The timeout configuration is handled via pytest.ini_options in pyproject.toml
