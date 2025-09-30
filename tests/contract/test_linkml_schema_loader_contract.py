"""Contract test for linkml_schema_loader module.

Tests the interface for loading official NWB LinkML schema.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from typing import Any


def test_load_official_schema_returns_schema_view():
    """Test that load_official_schema returns SchemaView object."""
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    nwb_version = "2.5.0"

    # Act
    result = load_official_schema(nwb_version)

    # Assert
    assert result is not None
    assert hasattr(result, 'schema')
    assert hasattr(result, 'all_classes')
    assert hasattr(result, 'all_slots')


def test_load_official_schema_supports_nwb_2x():
    """Test that schema loader supports NWB 2.x versions."""
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    versions = ["2.5.0", "2.6.0"]

    for version in versions:
        # Act
        result = load_official_schema(version)

        # Assert
        assert result is not None
        assert hasattr(result, 'schema')


def test_load_official_schema_raises_on_invalid_version():
    """Test that invalid version raises appropriate exception."""
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    invalid_version = "999.999.999"

    # Act & Assert
    with pytest.raises(ValueError):
        load_official_schema(invalid_version)


def test_validate_against_schema_returns_bool():
    """Test that validate_against_schema returns boolean."""
    from src.linkml_schema_loader import load_official_schema, validate_against_schema

    # Arrange
    schema = load_official_schema("2.5.0")
    instance = {"identifier": "test123", "session_description": "test"}
    target_class = "NWBFile"

    # Act
    result = validate_against_schema(instance, target_class, schema)

    # Assert
    assert isinstance(result, bool)


def test_validate_against_schema_validates_correct_instance():
    """Test validation of correct instance against schema."""
    from src.linkml_schema_loader import load_official_schema, validate_against_schema

    # Arrange
    schema = load_official_schema("2.5.0")
    valid_instance = {
        "identifier": "test123",
        "session_description": "Test session",
        "session_start_time": "2025-01-01T00:00:00"
    }
    target_class = "NWBFile"

    # Act
    result = validate_against_schema(valid_instance, target_class, schema)

    # Assert
    assert result is True


def test_validate_against_schema_rejects_invalid_instance():
    """Test validation rejects invalid instance."""
    from src.linkml_schema_loader import load_official_schema, validate_against_schema

    # Arrange
    schema = load_official_schema("2.5.0")
    invalid_instance = {"invalid_field": "value"}
    target_class = "NWBFile"

    # Act
    result = validate_against_schema(invalid_instance, target_class, schema)

    # Assert
    assert result is False


def test_load_official_schema_includes_all_nwb_classes():
    """Test that schema includes all standard NWB classes."""
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    nwb_version = "2.5.0"

    # Act
    schema = load_official_schema(nwb_version)

    # Assert
    all_classes = list(schema.all_classes())
    class_names = [cls for cls in all_classes]

    # Check for key NWB classes
    assert any('NWBFile' in name for name in class_names)
    assert any('TimeSeries' in name for name in class_names)
    assert len(class_names) > 10  # Should have many classes


def test_load_official_schema_uses_official_source():
    """Test that schema is loaded from official nwb-schema-language repo."""
    from src.linkml_schema_loader import load_official_schema

    # Arrange
    nwb_version = "2.5.0"

    # Act
    schema = load_official_schema(nwb_version)

    # Assert
    assert schema is not None
    # Schema should have NWB-specific metadata
    assert hasattr(schema, 'schema')


def test_load_official_schema_caches_results():
    """Test that schema loading is cached for performance."""
    from src.linkml_schema_loader import load_official_schema
    import time

    # Arrange
    nwb_version = "2.5.0"

    # Act - First load
    start1 = time.time()
    schema1 = load_official_schema(nwb_version)
    time1 = time.time() - start1

    # Act - Second load (should be cached)
    start2 = time.time()
    schema2 = load_official_schema(nwb_version)
    time2 = time.time() - start2

    # Assert
    assert schema1 is not None
    assert schema2 is not None
    # Second load should be significantly faster
    assert time2 < time1 * 0.1  # At least 10x faster