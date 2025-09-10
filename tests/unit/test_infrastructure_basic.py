"""
Basic infrastructure tests to verify pytest setup.
"""

import pytest
import tempfile
from pathlib import Path


def test_basic_functionality():
    """Test basic pytest functionality."""
    assert True


def test_temporary_directory():
    """Test temporary directory creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        assert temp_path.exists()
        assert temp_path.is_dir()
        
        # Create a test file
        test_file = temp_path / "test.txt"
        test_file.write_text("test content")
        assert test_file.exists()


@pytest.mark.asyncio
async def test_async_functionality():
    """Test async test functionality."""
    import asyncio
    await asyncio.sleep(0.001)
    assert True


@pytest.mark.unit
def test_unit_marker():
    """Test unit marker functionality."""
    assert True


@pytest.mark.slow
def test_slow_marker():
    """Test slow marker functionality."""
    assert True


class TestBasicClass:
    """Test basic test class functionality."""
    
    def test_method(self):
        """Test method in class."""
        assert True
    
    def test_fixture_usage(self, temp_dir):
        """Test fixture usage."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()


def test_mock_usage():
    """Test mock functionality."""
    from unittest.mock import Mock
    
    mock_obj = Mock()
    mock_obj.test_method.return_value = "test_result"
    
    result = mock_obj.test_method()
    assert result == "test_result"
    assert mock_obj.test_method.called