"""
Global pytest configuration and fixtures.

This module contains pytest configuration, global fixtures, and utilities
that are available to all test modules.
"""

import asyncio
import os
import tempfile
import pytest
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock

# Test environment configuration
TEST_ENV_VARS = {
    "AGENTIC_CONVERTER_ENV": "test",
    "AGENTIC_CONVERTER_LOG_LEVEL": "DEBUG",
    "AGENTIC_CONVERTER_DATABASE_URL": "sqlite:///:memory:",
    "AGENTIC_CONVERTER_DISABLE_TELEMETRY": "true",
    "AGENTIC_CONVERTER_CACHE_DISABLED": "true",
}


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    original_env = {}
    
    # Store original values and set test values
    for key, value in TEST_ENV_VARS.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
async def async_temp_dir() -> AsyncGenerator[Path, None]:
    """Create a temporary directory for async test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_settings():
    """Mock application settings for testing."""
    settings = Mock()
    settings.environment = "test"
    settings.log_level = "DEBUG"
    settings.debug = True
    
    # Server settings
    settings.server = Mock()
    settings.server.host = "127.0.0.1"
    settings.server.port = 8000
    settings.server.workers = 1
    settings.server.timeout = 30
    
    # Agent settings
    settings.agents = Mock()
    settings.agents.conversation = Mock()
    settings.agents.conversion = Mock()
    settings.agents.evaluation = Mock()
    settings.agents.knowledge_graph = Mock()
    
    # Database settings
    settings.database = Mock()
    settings.database.url = "sqlite:///:memory:"
    
    return settings


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing conversions."""
    return {
        "identifier": "test_session_001",
        "session_description": "Test recording session",
        "experimenter": ["Test User"],
        "lab": "Test Lab",
        "institution": "Test Institution",
        "experiment_description": "Test experiment for unit testing",
        "session_start_time": "2024-01-01T10:00:00",
        "keywords": ["test", "neuroscience", "nwb"],
        "related_publications": [],
        "notes": "Generated for testing purposes"
    }


@pytest.fixture
def sample_files_map(temp_dir):
    """Sample files map for testing conversions."""
    # Create sample data files
    recording_file = temp_dir / "recording.dat"
    recording_file.write_bytes(b"mock recording data" * 1000)
    
    events_file = temp_dir / "events.txt"
    events_file.write_text("timestamp,event\n1.0,start\n2.0,end\n")
    
    return {
        "recording": str(recording_file),
        "events": str(events_file)
    }


# Test data cleanup utilities
@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Clean up test artifacts after each test."""
    yield
    
    # Clean up common test artifacts
    artifacts_to_clean = [
        "test_output.nwb",
        "test_output.ttl", 
        "test_conversion_script.py",
        "test_report.html",
        "test_report.json"
    ]
    
    for artifact in artifacts_to_clean:
        if os.path.exists(artifact):
            os.remove(artifact)


# Performance testing utilities
@pytest.fixture
def benchmark_config():
    """Configuration for benchmark tests."""
    return {
        "min_rounds": 3,
        "max_time": 10.0,
        "warmup": True,
        "warmup_iterations": 1
    }


# Mock external services
@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without external API calls."""
    client = AsyncMock()
    
    # Default responses for common operations
    client.generate_completion.return_value = "Mock LLM response"
    client.generate_questions.return_value = [
        {
            "field": "experimenter",
            "question": "Who performed this experiment?",
            "explanation": "Required for NWB metadata",
            "priority": "high"
        }
    ]
    
    return client


@pytest.fixture
def mock_neuroconv_interface():
    """Mock NeuroConv interface for testing."""
    interface = Mock()
    interface.get_metadata.return_value = {"test": "metadata"}
    interface.run_conversion.return_value = None
    interface.validate.return_value = []
    return interface


# Import dataset fixtures
try:
    from tests.datasets.fixtures import *
    DATASET_FIXTURES_AVAILABLE = True
except ImportError:
    DATASET_FIXTURES_AVAILABLE = False

# Test markers for conditional test execution
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", 
        "requires_gpu: mark test as requiring GPU resources"
    )
    config.addinivalue_line(
        "markers",
        "requires_network: mark test as requiring network access"
    )
    config.addinivalue_line(
        "markers",
        "requires_datasets: mark test as requiring test datasets"
    )
    config.addinivalue_line(
        "markers",
        "requires_datalad: mark test as requiring DataLad"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names and paths."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Add markers based on test names
        if "benchmark" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.performance)
        
        if "llm" in item.name.lower():
            item.add_marker(pytest.mark.requires_llm)
        
        if "dataset" in item.name.lower():
            item.add_marker(pytest.mark.requires_datasets)