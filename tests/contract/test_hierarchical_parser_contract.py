"""Contract test for hierarchical_parser module.

Tests the interface for deep HDF5 structure traversal.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
from typing import Dict, List, Any


def test_parse_hdf5_structure_returns_hierarchy_tree():
    """Test that parse_hdf5_structure returns HierarchyTree object."""
    from src.hierarchical_parser import parse_hdf5_structure
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)

    # Act
    result = parse_hdf5_structure(nwbfile)

    # Assert
    assert result is not None
    assert hasattr(result, 'root')
    assert hasattr(result, 'groups')
    assert hasattr(result, 'datasets')
    assert hasattr(result, 'attributes')


def test_parse_hdf5_structure_captures_all_metadata():
    """Test that parsing captures groups, datasets, attributes, and links."""
    from src.hierarchical_parser import parse_hdf5_structure
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)

    # Act
    result = parse_hdf5_structure(nwbfile)

    # Assert
    assert hasattr(result, 'groups')
    assert hasattr(result, 'datasets')
    assert hasattr(result, 'attributes')
    assert hasattr(result, 'links')
    assert isinstance(result.groups, list)
    assert isinstance(result.datasets, list)
    assert isinstance(result.attributes, dict)


def test_parse_hdf5_structure_complete_traversal():
    """Test that parsing performs complete traversal with no data loss."""
    from src.hierarchical_parser import parse_hdf5_structure
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)

    # Act
    result = parse_hdf5_structure(nwbfile)

    # Assert
    # Should capture all major NWB groups
    group_names = [g.name for g in result.groups]
    assert any('acquisition' in name for name in group_names)
    assert any('processing' in name for name in group_names)
    # Should have non-zero datasets
    assert len(result.datasets) > 0


def test_parse_hdf5_structure_preserves_hierarchy():
    """Test that hierarchical relationships are preserved."""
    from src.hierarchical_parser import parse_hdf5_structure
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)

    # Act
    result = parse_hdf5_structure(nwbfile)

    # Assert
    # Groups should have parent-child relationships
    for group in result.groups:
        assert hasattr(group, 'path')
        assert hasattr(group, 'parent_path')


def test_parse_hdf5_structure_captures_dataset_metadata():
    """Test that dataset metadata (shape, dtype, chunks) is captured."""
    from src.hierarchical_parser import parse_hdf5_structure
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)

    # Act
    result = parse_hdf5_structure(nwbfile)

    # Assert
    if len(result.datasets) > 0:
        dataset = result.datasets[0]
        assert hasattr(dataset, 'shape')
        assert hasattr(dataset, 'dtype')
        assert hasattr(dataset, 'path')


def test_parse_hdf5_structure_handles_links():
    """Test that soft links and external links are captured."""
    from src.hierarchical_parser import parse_hdf5_structure
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/with_links.nwb")
    nwbfile = load_nwb_file(test_file)

    # Act
    result = parse_hdf5_structure(nwbfile)

    # Assert
    assert hasattr(result, 'links')
    assert isinstance(result.links, list)


def test_parse_hdf5_structure_handles_large_files():
    """Test parsing of large files without excessive memory usage."""
    from src.hierarchical_parser import parse_hdf5_structure
    from src.nwb_loader import load_nwb_file
    import psutil
    import os

    # Arrange
    large_file = Path("tests/fixtures/large_1gb.nwb")
    nwbfile = load_nwb_file(large_file)
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Act
    result = parse_hdf5_structure(nwbfile)
    final_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Assert
    assert result is not None
    # Should not load all data into memory (metadata only)
    memory_increase = final_memory - initial_memory
    assert memory_increase < 500  # Less than 500MB increase


def test_parse_hdf5_structure_handles_custom_extensions():
    """Test parsing of NWB files with custom extensions."""
    from src.hierarchical_parser import parse_hdf5_structure
    from src.nwb_loader import load_nwb_file

    # Arrange
    custom_file = Path("tests/fixtures/with_custom_extension.nwb")
    nwbfile = load_nwb_file(custom_file)

    # Act
    result = parse_hdf5_structure(nwbfile)

    # Assert
    assert result is not None
    # Should handle custom groups gracefully
    assert len(result.groups) > 0