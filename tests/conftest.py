"""Pytest configuration and shared fixtures for core service tests."""

import asyncio
import pytest
import tempfile
from pathlib import Path


# Configure pytest for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Shared fixtures
@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_dataset_files(temp_directory):
    """Create sample dataset files for testing."""
    # Create various file types that might be in a neuroscience dataset
    files = {
        "ephys_data.bin": b"binary ephys data content",
        "behavior_data.csv": "timestamp,x,y,velocity\n0.0,10.5,20.3,1.2\n0.1,10.6,20.4,1.3\n",
        "metadata.json": '{"subject_id": "mouse001", "session_date": "2024-01-01", "experimenter": "test_user"}',
        "session_info.txt": "Session ID: test_session_001\nDate: 2024-01-01\nDuration: 3600s",
        "notes.md": "# Experiment Notes\n\nThis is a test experiment for unit testing.",
        "config.yaml": "experiment:\n  name: test_experiment\n  duration: 3600\n  sampling_rate: 30000"
    }
    
    created_files = {}
    for filename, content in files.items():
        file_path = temp_directory / filename
        if isinstance(content, str):
            file_path.write_text(content)
        else:
            file_path.write_bytes(content)
        created_files[filename] = str(file_path)
    
    return created_files


@pytest.fixture
def sample_nwb_file(temp_directory):
    """Create a sample NWB file for testing."""
    nwb_path = temp_directory / "test_output.nwb"
    
    # Create a minimal NWB-like file (just for testing, not a real NWB file)
    nwb_content = b"""HDF5 file header (fake)
This is a dummy NWB file for testing purposes.
It contains fake neuroscience data structures.
"""
    
    nwb_path.write_bytes(nwb_content)
    return str(nwb_path)


# Test markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Direct functionality tests with no external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests with multiple components"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests"
    )


# Test collection configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add unit marker to all tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker to performance tests
        if "performance" in item.name.lower() or "benchmark" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        
        # Add slow marker to tests that might be slow
        if any(keyword in item.name.lower() for keyword in ["timeout", "concurrent", "load"]):
            item.add_marker(pytest.mark.slow)