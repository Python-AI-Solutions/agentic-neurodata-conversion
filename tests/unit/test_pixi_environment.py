"""
Test pixi environment setup and basic functionality.
"""

import pytest
import sys
import os
from pathlib import Path


def test_python_version():
    """Test that we're using the correct Python version."""
    assert sys.version_info >= (3, 12), f"Python version should be >= 3.12, got {sys.version_info}"


def test_pixi_environment():
    """Test that we're running in a pixi environment."""
    python_path = sys.executable
    
    # Should be in .pixi directory
    assert ".pixi" in python_path, f"Not running in pixi environment: {python_path}"


def test_pytest_available():
    """Test that pytest is available and working."""
    import pytest
    assert pytest.__version__ is not None


@pytest.mark.asyncio
async def test_async_support():
    """Test that async tests work."""
    import asyncio
    await asyncio.sleep(0.001)
    assert True


def test_mock_support():
    """Test that mock functionality works."""
    from unittest.mock import Mock, patch
    
    mock_obj = Mock()
    mock_obj.test_method.return_value = "test"
    
    assert mock_obj.test_method() == "test"


def test_temporary_files():
    """Test temporary file creation."""
    import tempfile
    
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(b"test data")
        tmp.flush()
        
        assert Path(tmp.name).exists()


def test_environment_variables():
    """Test that test environment variables are set."""
    # These should be set by conftest.py
    assert os.environ.get("AGENTIC_CONVERTER_ENV") == "test"
    assert os.environ.get("AGENTIC_CONVERTER_LOG_LEVEL") == "DEBUG"


@pytest.mark.unit
def test_unit_marker():
    """Test that unit marker works."""
    assert True


@pytest.mark.slow
def test_slow_marker():
    """Test that slow marker works."""
    import time
    time.sleep(0.01)  # Minimal delay for slow test
    assert True


def test_fixtures_available(temp_dir, mock_settings):
    """Test that custom fixtures are available."""
    assert temp_dir.exists()
    assert temp_dir.is_dir()
    
    assert mock_settings.environment == "test"
    assert mock_settings.debug is True


def test_package_imports():
    """Test that we can import basic packages."""
    # Test standard library
    import json
    import pathlib
    import asyncio
    
    # Test installed packages
    import numpy
    import pandas
    import pytest
    
    # Verify versions
    assert numpy.__version__ is not None
    assert pandas.__version__ is not None
    assert pytest.__version__ is not None


def test_project_structure():
    """Test that project structure is correct."""
    project_root = Path.cwd()
    
    # Check key files exist
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "pixi.toml").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "agentic_neurodata_conversion").exists()


class TestBasicFunctionality:
    """Test basic test class functionality."""
    
    def test_class_method(self):
        """Test method in test class."""
        assert True
    
    def test_class_fixtures(self, temp_dir):
        """Test fixture usage in class."""
        test_file = temp_dir / "class_test.txt"
        test_file.write_text("test content")
        
        assert test_file.exists()
        assert test_file.read_text() == "test content"