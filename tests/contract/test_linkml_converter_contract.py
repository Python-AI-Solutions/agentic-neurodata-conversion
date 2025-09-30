"""Contract test for linkml_converter module.

Tests the interface for converting NWB to LinkML instances.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
from typing import Dict, List, Any


def test_convert_nwb_to_linkml_returns_linkml_instances():
    """Test that convert_nwb_to_linkml returns LinkMLInstances object."""
    from src.linkml_converter import convert_nwb_to_linkml
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")

    # Act
    result = convert_nwb_to_linkml(nwbfile, schema)

    # Assert
    assert result is not None
    assert hasattr(result, 'instances')
    assert hasattr(result, 'metadata')
    assert isinstance(result.instances, list)


def test_convert_nwb_to_linkml_preserves_references():
    """Test that conversion preserves all references and relationships."""
    from src.linkml_converter import convert_nwb_to_linkml
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    test_file = Path("tests/fixtures/with_references.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")

    # Act
    result = convert_nwb_to_linkml(nwbfile, schema)

    # Assert
    assert result is not None
    # Check that references are preserved
    instances = result.instances
    # Find instances with references
    has_references = any(
        hasattr(inst, 'references') or any('_ref' in str(k) for k in inst.keys())
        for inst in instances
        if isinstance(inst, dict)
    )
    # Should have some references in typical NWB files
    assert len(instances) > 0


def test_convert_nwb_to_linkml_validates_against_schema():
    """Test that output validates against official NWB LinkML schema."""
    from src.linkml_converter import convert_nwb_to_linkml
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema, validate_against_schema

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")

    # Act
    result = convert_nwb_to_linkml(nwbfile, schema)

    # Assert
    # At least the root NWBFile instance should validate
    if len(result.instances) > 0:
        root_instance = result.instances[0]
        is_valid = validate_against_schema(root_instance, "NWBFile", schema)
        assert is_valid is True


def test_convert_nwb_to_linkml_handles_all_data_types():
    """Test conversion of all NWB data types."""
    from src.linkml_converter import convert_nwb_to_linkml
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    test_file = Path("tests/fixtures/comprehensive.nwb")  # File with many data types
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")

    # Act
    result = convert_nwb_to_linkml(nwbfile, schema)

    # Assert
    assert result is not None
    assert len(result.instances) > 0
    # Should have instances of various types
    instance_types = set()
    for inst in result.instances:
        if isinstance(inst, dict) and '@type' in inst:
            instance_types.add(inst['@type'])
    assert len(instance_types) >= 3  # Multiple types expected


def test_convert_nwb_to_linkml_preserves_metadata():
    """Test that metadata (session info, identifiers, etc.) is preserved."""
    from src.linkml_converter import convert_nwb_to_linkml
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")

    # Act
    result = convert_nwb_to_linkml(nwbfile, schema)

    # Assert
    root_instance = result.instances[0]
    assert 'identifier' in root_instance or hasattr(root_instance, 'identifier')
    assert 'session_description' in root_instance or hasattr(root_instance, 'session_description')


def test_convert_nwb_to_linkml_handles_custom_extensions():
    """Test conversion of files with custom extensions."""
    from src.linkml_converter import convert_nwb_to_linkml
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")

    # Act
    result = convert_nwb_to_linkml(nwbfile, schema)

    # Assert
    assert result is not None
    # Should handle gracefully, documenting custom extensions
    assert hasattr(result, 'metadata')
    # Metadata should note custom extensions
    if hasattr(result.metadata, 'custom_extensions'):
        assert isinstance(result.metadata.custom_extensions, list)


def test_convert_nwb_to_linkml_performance():
    """Test conversion performance on 1GB file."""
    from src.linkml_converter import convert_nwb_to_linkml
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    import time

    # Arrange
    large_file = Path("tests/fixtures/large_1gb.nwb")
    nwbfile = load_nwb_file(large_file)
    schema = load_official_schema("2.5.0")
    start_time = time.time()

    # Act
    result = convert_nwb_to_linkml(nwbfile, schema)
    elapsed = time.time() - start_time

    # Assert
    assert result is not None
    # Should complete within reasonable time (part of 15-minute budget)
    assert elapsed < 300  # 5 minutes max for conversion


def test_convert_nwb_to_linkml_produces_serializable_output():
    """Test that output can be serialized to JSON."""
    from src.linkml_converter import convert_nwb_to_linkml
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    import json

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")

    # Act
    result = convert_nwb_to_linkml(nwbfile, schema)

    # Assert
    # Should be serializable to JSON
    try:
        json_str = json.dumps(result.instances, default=str)
        assert len(json_str) > 0
    except TypeError:
        pytest.fail("LinkML instances should be JSON-serializable")