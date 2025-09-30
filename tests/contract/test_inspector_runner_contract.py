"""Contract test for inspector_runner module.

Tests the interface for running NWB Inspector validation.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any


def test_run_inspection_returns_inspection_results():
    """Test that run_inspection returns InspectionResults object."""
    from src.inspector_runner import run_inspection

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")

    # Act
    result = run_inspection(test_file)

    # Assert
    assert result is not None
    assert hasattr(result, 'messages')
    assert hasattr(result, 'severity_counts')
    assert hasattr(result, 'file_path')


def test_run_inspection_includes_severity_categorization():
    """Test that inspection results include severity categories."""
    from src.inspector_runner import run_inspection

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")

    # Act
    result = run_inspection(test_file)

    # Assert
    assert hasattr(result, 'severity_counts')
    assert 'CRITICAL' in result.severity_counts
    assert 'ERROR' in result.severity_counts
    assert 'WARNING' in result.severity_counts
    assert 'INFO' in result.severity_counts


def test_run_inspection_returns_structured_results():
    """Test that results include all required fields."""
    from src.inspector_runner import run_inspection

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")

    # Act
    result = run_inspection(test_file)

    # Assert
    assert hasattr(result, 'messages')
    assert isinstance(result.messages, list)

    if len(result.messages) > 0:
        message = result.messages[0]
        assert hasattr(message, 'severity')
        assert hasattr(message, 'message')
        assert hasattr(message, 'check_name')
        assert hasattr(message, 'location')


def test_run_inspection_handles_valid_file():
    """Test inspection of valid NWB file."""
    from src.inspector_runner import run_inspection

    # Arrange
    valid_file = Path("tests/fixtures/valid.nwb")

    # Act
    result = run_inspection(valid_file)

    # Assert
    assert result is not None
    # Valid files should have few or no critical errors
    assert result.severity_counts.get('CRITICAL', 0) == 0


def test_run_inspection_handles_invalid_file():
    """Test inspection of invalid NWB file."""
    from src.inspector_runner import run_inspection

    # Arrange
    invalid_file = Path("tests/fixtures/invalid.nwb")

    # Act
    result = run_inspection(invalid_file)

    # Assert
    assert result is not None
    # Invalid files should have errors
    assert len(result.messages) > 0
    assert result.severity_counts.get('ERROR', 0) + result.severity_counts.get('CRITICAL', 0) > 0


def test_run_inspection_raises_on_nonexistent_file():
    """Test that run_inspection raises exception for nonexistent files."""
    from src.inspector_runner import run_inspection

    # Arrange
    nonexistent = Path("/nonexistent/file.nwb")

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        run_inspection(nonexistent)


def test_run_inspection_handles_custom_extensions():
    """Test inspection of NWB file with custom extensions."""
    from src.inspector_runner import run_inspection

    # Arrange
    custom_ext_file = Path("tests/fixtures/with_custom_extension.nwb")

    # Act
    result = run_inspection(custom_ext_file)

    # Assert
    assert result is not None
    # Should handle gracefully and document custom extensions
    assert hasattr(result, 'messages')


def test_run_inspection_produces_exportable_results():
    """Test that inspection results can be exported to JSON/HTML/TXT."""
    from src.inspector_runner import run_inspection

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")

    # Act
    result = run_inspection(test_file)

    # Assert
    # Results should be serializable
    assert hasattr(result, 'to_dict') or hasattr(result, '__dict__')


def test_run_inspection_performance_on_large_file():
    """Test that inspection completes in reasonable time for large files."""
    from src.inspector_runner import run_inspection
    import time

    # Arrange
    large_file = Path("tests/fixtures/large_1gb.nwb")
    start_time = time.time()

    # Act
    result = run_inspection(large_file)
    elapsed = time.time() - start_time

    # Assert
    assert result is not None
    # Should complete within reasonable time (part of 15-minute budget)
    assert elapsed < 300  # 5 minutes max for inspection phase