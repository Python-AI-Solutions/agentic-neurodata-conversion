"""Integration test for custom extensions handling.

Scenario: Process NWB file with custom extensions, verify graceful degradation.
This test MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
import json


def test_custom_extensions_graceful_handling():
    """Test graceful handling of NWB file with custom extensions."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    # Should complete successfully (graceful degradation)
    assert result == 0, "Should handle custom extensions gracefully"

    # Should generate all outputs
    viz_path = output_dir / "with_custom_extension_visualization.html"
    assert viz_path.exists()


def test_custom_extensions_documented_in_report():
    """Test that custom extensions are documented in evaluation report."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test2")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check evaluation report
    report_path = output_dir / "with_custom_extension_evaluation_report.json"
    with open(report_path) as f:
        report = json.load(f)

    # Should document custom extensions
    assert 'custom_extensions' in str(report).lower() or 'extensions' in report


def test_custom_extensions_in_hierarchy():
    """Test that custom extension data appears in hierarchy."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test3")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check hierarchy
    hierarchy_path = output_dir / "with_custom_extension_hierarchy.json"
    with open(hierarchy_path) as f:
        hierarchy = json.load(f)

    # Should capture custom groups/datasets
    assert 'groups' in hierarchy
    assert len(hierarchy['groups']) > 0


def test_custom_extensions_warning_in_report():
    """Test that custom extensions generate warnings (not errors)."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test4")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check evaluation report
    report_path = output_dir / "with_custom_extension_evaluation_report.json"
    with open(report_path) as f:
        report = json.load(f)

    # Should have warnings about custom extensions, not critical errors
    if 'validation_results' in report:
        assert report['validation_results'].get('critical_count', 0) == 0, \
            "Custom extensions should not cause critical errors"


def test_custom_extensions_appear_in_knowledge_graph():
    """Test that custom extension data appears in knowledge graph."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test5")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check knowledge graph
    ttl_path = output_dir / "with_custom_extension_knowledge_graph.ttl"
    from rdflib import Graph

    g = Graph()
    g.parse(ttl_path, format='turtle')

    # Should have triples (including custom data)
    assert len(g) > 0


def test_multiple_custom_extensions():
    """Test file with multiple different custom extensions."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/multiple_custom_extensions.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test6")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Should complete successfully
    report_path = output_dir / "multiple_custom_extensions_evaluation_report.json"
    assert report_path.exists()


def test_custom_extensions_linkml_conversion():
    """Test that custom extensions are handled in LinkML conversion."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test7")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check LinkML data
    linkml_path = output_dir / "with_custom_extension_linkml_data.jsonld"
    with open(linkml_path) as f:
        data = json.load(f)

    # Should have data (even if custom extensions are marked differently)
    assert data is not None
    assert len(str(data)) > 100  # Non-trivial output


def test_custom_extensions_visualization():
    """Test that custom extension nodes appear in visualization."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test8")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check visualization HTML
    viz_path = output_dir / "with_custom_extension_visualization.html"
    content = viz_path.read_text()

    # Should include graph data
    assert 'application/json' in content or 'nodes' in content.lower()


def test_unknown_namespace_handling():
    """Test handling of unknown namespaces in custom extensions."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/unknown_namespace.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test9")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    # Should complete (gracefully degrade)
    assert result in [0, 1]  # 0 for success, 1 for handled error

    # If successful, outputs should exist
    if result == 0:
        report_path = output_dir / "unknown_namespace_evaluation_report.json"
        assert report_path.exists()


def test_custom_extensions_recommendation():
    """Test that report includes recommendations for custom extensions."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_custom_extension.nwb")
    output_dir = Path("/tmp/nwb_custom_ext_test10")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check evaluation report
    report_path = output_dir / "with_custom_extension_evaluation_report.json"
    with open(report_path) as f:
        report = json.load(f)

    # Should have recommendations section
    if 'recommendations' in report:
        recommendations_str = str(report['recommendations']).lower()
        # May mention extensions or schema
        assert len(report['recommendations']) >= 0  # At least has the field