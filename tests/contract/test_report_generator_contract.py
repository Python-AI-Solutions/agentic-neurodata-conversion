"""Contract test for report_generator module.

Tests the interface for generating evaluation reports.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
from typing import Dict, Any


def test_generate_evaluation_report_returns_report():
    """Test that generate_evaluation_report returns Report object."""
    from src.report_generator import generate_evaluation_report
    from src.inspector_runner import run_inspection
    from src.hierarchical_parser import parse_hdf5_structure
    from src.graph_constructor import build_graph_from_ttl, compute_graph_analytics
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    inspection = run_inspection(test_file)
    hierarchy = parse_hdf5_structure(nwbfile)

    ttl_content = "@prefix nwb: <http://purl.org/nwb/2.5.0/> . nwb:test a nwb:NWBFile ."
    kg = build_graph_from_ttl(ttl_content)
    metrics = compute_graph_analytics(kg)

    # Act
    report = generate_evaluation_report(inspection, hierarchy, metrics)

    # Assert
    assert report is not None
    assert hasattr(report, 'summary')
    assert hasattr(report, 'validation_results')
    assert hasattr(report, 'graph_metrics')


def test_export_report_generates_json():
    """Test that export_report generates JSON format."""
    from src.report_generator import generate_evaluation_report, export_report
    from src.inspector_runner import run_inspection
    from src.hierarchical_parser import parse_hdf5_structure
    from src.graph_constructor import build_graph_from_ttl, compute_graph_analytics
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    inspection = run_inspection(test_file)
    hierarchy = parse_hdf5_structure(nwbfile)
    ttl_content = "@prefix nwb: <http://purl.org/nwb/2.5.0/> ."
    kg = build_graph_from_ttl(ttl_content)
    metrics = compute_graph_analytics(kg)
    report = generate_evaluation_report(inspection, hierarchy, metrics)

    output_path = Path("/tmp/test_report.json")

    # Act
    result = export_report(report, format='json', output_path=output_path)

    # Assert
    assert result is True
    assert output_path.exists()
    # Should be valid JSON
    import json
    with open(output_path) as f:
        data = json.load(f)
        assert isinstance(data, dict)


def test_export_report_generates_html():
    """Test that export_report generates HTML format."""
    from src.report_generator import generate_evaluation_report, export_report
    from src.inspector_runner import run_inspection
    from src.hierarchical_parser import parse_hdf5_structure
    from src.graph_constructor import build_graph_from_ttl, compute_graph_analytics
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    inspection = run_inspection(test_file)
    hierarchy = parse_hdf5_structure(nwbfile)
    ttl_content = "@prefix nwb: <http://purl.org/nwb/2.5.0/> ."
    kg = build_graph_from_ttl(ttl_content)
    metrics = compute_graph_analytics(kg)
    report = generate_evaluation_report(inspection, hierarchy, metrics)

    output_path = Path("/tmp/test_report.html")

    # Act
    result = export_report(report, format='html', output_path=output_path)

    # Assert
    assert result is True
    assert output_path.exists()
    # Should contain HTML tags
    content = output_path.read_text()
    assert '<html' in content.lower()
    assert '</html>' in content.lower()


def test_export_report_generates_txt():
    """Test that export_report generates TXT format."""
    from src.report_generator import generate_evaluation_report, export_report
    from src.inspector_runner import run_inspection
    from src.hierarchical_parser import parse_hdf5_structure
    from src.graph_constructor import build_graph_from_ttl, compute_graph_analytics
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    inspection = run_inspection(test_file)
    hierarchy = parse_hdf5_structure(nwbfile)
    ttl_content = "@prefix nwb: <http://purl.org/nwb/2.5.0/> ."
    kg = build_graph_from_ttl(ttl_content)
    metrics = compute_graph_analytics(kg)
    report = generate_evaluation_report(inspection, hierarchy, metrics)

    output_path = Path("/tmp/test_report.txt")

    # Act
    result = export_report(report, format='txt', output_path=output_path)

    # Assert
    assert result is True
    assert output_path.exists()
    # Should be plain text
    content = output_path.read_text()
    assert len(content) > 0
    assert '<html' not in content.lower()  # Not HTML


def test_generate_evaluation_report_includes_all_sections():
    """Test that report includes all required sections."""
    from src.report_generator import generate_evaluation_report
    from src.inspector_runner import run_inspection
    from src.hierarchical_parser import parse_hdf5_structure
    from src.graph_constructor import build_graph_from_ttl, compute_graph_analytics
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    inspection = run_inspection(test_file)
    hierarchy = parse_hdf5_structure(nwbfile)
    ttl_content = "@prefix nwb: <http://purl.org/nwb/2.5.0/> ."
    kg = build_graph_from_ttl(ttl_content)
    metrics = compute_graph_analytics(kg)

    # Act
    report = generate_evaluation_report(inspection, hierarchy, metrics)

    # Assert
    assert hasattr(report, 'summary')
    assert hasattr(report, 'validation_results')
    assert hasattr(report, 'hierarchy_info')
    assert hasattr(report, 'graph_metrics')
    assert hasattr(report, 'recommendations')


def test_generate_evaluation_report_categorizes_severity():
    """Test that report categorizes issues by severity."""
    from src.report_generator import generate_evaluation_report
    from src.inspector_runner import run_inspection
    from src.hierarchical_parser import parse_hdf5_structure
    from src.graph_constructor import build_graph_from_ttl, compute_graph_analytics
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/invalid.nwb")  # File with issues
    nwbfile = load_nwb_file(test_file)
    inspection = run_inspection(test_file)
    hierarchy = parse_hdf5_structure(nwbfile)
    ttl_content = "@prefix nwb: <http://purl.org/nwb/2.5.0/> ."
    kg = build_graph_from_ttl(ttl_content)
    metrics = compute_graph_analytics(kg)

    # Act
    report = generate_evaluation_report(inspection, hierarchy, metrics)

    # Assert
    assert hasattr(report, 'validation_results')
    assert hasattr(report.validation_results, 'critical')
    assert hasattr(report.validation_results, 'errors')
    assert hasattr(report.validation_results, 'warnings')
    assert hasattr(report.validation_results, 'info')


def test_export_report_handles_all_three_formats():
    """Test that all three formats can be generated from same report."""
    from src.report_generator import generate_evaluation_report, export_report
    from src.inspector_runner import run_inspection
    from src.hierarchical_parser import parse_hdf5_structure
    from src.graph_constructor import build_graph_from_ttl, compute_graph_analytics
    from src.nwb_loader import load_nwb_file

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    inspection = run_inspection(test_file)
    hierarchy = parse_hdf5_structure(nwbfile)
    ttl_content = "@prefix nwb: <http://purl.org/nwb/2.5.0/> ."
    kg = build_graph_from_ttl(ttl_content)
    metrics = compute_graph_analytics(kg)
    report = generate_evaluation_report(inspection, hierarchy, metrics)

    # Act
    json_result = export_report(report, 'json', Path('/tmp/test.json'))
    html_result = export_report(report, 'html', Path('/tmp/test.html'))
    txt_result = export_report(report, 'txt', Path('/tmp/test.txt'))

    # Assert
    assert json_result is True
    assert html_result is True
    assert txt_result is True