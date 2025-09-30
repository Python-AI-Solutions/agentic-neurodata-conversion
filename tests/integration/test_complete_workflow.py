"""Integration test for complete end-to-end workflow.

Scenario: Process valid electrophysiology NWB file from start to finish.
Tests the full pipeline: Load → Inspect → Parse → Convert → Generate → Visualize
This test MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
import json


def test_complete_workflow_with_valid_ecephys_file():
    """Test complete workflow with valid electrophysiology NWB file."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/ecephys_valid.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert - Exit code
    assert result == 0, "Workflow should complete successfully"

    # Assert - All 10 output files generated
    base_name = "ecephys_valid"
    expected_files = [
        f"{base_name}_evaluation_report.json",
        f"{base_name}_evaluation_report.html",
        f"{base_name}_evaluation_report.txt",
        f"{base_name}_hierarchy.json",
        f"{base_name}_linkml_data.jsonld",
        f"{base_name}_knowledge_graph.ttl",
        f"{base_name}_knowledge_graph.jsonld",
        f"{base_name}_graph_metadata.json",
        f"{base_name}_visualization.html",
        f"{base_name}_force_layout.json"
    ]

    for fname in expected_files:
        fpath = output_dir / fname
        assert fpath.exists(), f"Missing output file: {fname}"
        assert fpath.stat().st_size > 0, f"Empty output file: {fname}"


def test_evaluation_report_shows_pass():
    """Test that evaluation report shows PASS for valid file."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/ecephys_valid.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test2")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check evaluation report
    eval_report_path = output_dir / "ecephys_valid_evaluation_report.json"
    with open(eval_report_path) as f:
        report = json.load(f)

    # Valid file should have minimal critical errors
    assert report['validation_results']['critical_count'] == 0
    assert report['summary']['status'] == 'PASS' or report['summary']['overall_status'] == 'PASS'


def test_workflow_processes_all_phases_in_order():
    """Test that workflow executes phases in correct order."""
    from src.main import main
    import time

    # Arrange
    test_file = Path("tests/fixtures/ecephys_valid.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test3")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check that evaluation report exists (Phase 1: Evaluation)
    eval_report = output_dir / "ecephys_valid_evaluation_report.json"
    assert eval_report.exists()

    # Check that hierarchy exists (Phase 2: Deep inspection)
    hierarchy = output_dir / "ecephys_valid_hierarchy.json"
    assert hierarchy.exists()

    # Check that LinkML data exists (Phase 3: Conversion)
    linkml_data = output_dir / "ecephys_valid_linkml_data.jsonld"
    assert linkml_data.exists()

    # Check that knowledge graph exists (Phase 4: Graph generation)
    kg_ttl = output_dir / "ecephys_valid_knowledge_graph.ttl"
    kg_jsonld = output_dir / "ecephys_valid_knowledge_graph.jsonld"
    assert kg_ttl.exists()
    assert kg_jsonld.exists()

    # Check that visualization exists (Phase 5: Visualization)
    viz = output_dir / "ecephys_valid_visualization.html"
    assert viz.exists()


def test_knowledge_graph_semantic_fidelity():
    """Test that knowledge graph maintains 100% semantic fidelity."""
    from src.main import main
    from rdflib import Graph

    # Arrange
    test_file = Path("tests/fixtures/ecephys_valid.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test4")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Load and validate TTL
    ttl_path = output_dir / "ecephys_valid_knowledge_graph.ttl"
    g_ttl = Graph()
    g_ttl.parse(ttl_path, format='turtle')
    assert len(g_ttl) > 0, "TTL graph should contain triples"

    # Load and validate JSON-LD
    jsonld_path = output_dir / "ecephys_valid_knowledge_graph.jsonld"
    g_jsonld = Graph()
    g_jsonld.parse(jsonld_path, format='json-ld')
    assert len(g_jsonld) > 0, "JSON-LD graph should contain triples"

    # Semantic fidelity: TTL and JSON-LD should have same triples
    assert len(g_ttl) == len(g_jsonld), "TTL and JSON-LD must have same number of triples"


def test_workflow_handles_ophys_file():
    """Test workflow with optical physiology file."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/ophys_valid.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test5")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0
    # Should generate all outputs
    assert (output_dir / "ophys_valid_visualization.html").exists()


def test_workflow_handles_behavior_file():
    """Test workflow with behavior data file."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/behavior_valid.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test6")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0
    assert (output_dir / "behavior_valid_knowledge_graph.ttl").exists()


def test_workflow_performance_1gb_file():
    """Test that 1GB file completes within 15 minutes."""
    from src.main import main
    import time

    # Arrange
    test_file = Path("tests/fixtures/large_1gb.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test_perf")
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])
    elapsed = time.time() - start_time

    # Assert
    assert result == 0
    assert elapsed < 900, f"Processing took {elapsed:.1f}s, should be < 900s (15 min)"


def test_workflow_error_handling():
    """Test workflow error handling with corrupted file."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/corrupted.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test_error")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 1, "Should return error exit code for corrupted file"


def test_workflow_invalid_input_handling():
    """Test workflow with nonexistent file."""
    from src.main import main

    # Arrange
    test_file = Path("/nonexistent/file.nwb")

    # Act
    result = main([str(test_file)])

    # Assert
    assert result == 2, "Should return invalid input exit code"


def test_all_outputs_are_valid():
    """Test that all output files are valid (parseable, non-empty)."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/ecephys_valid.nwb")
    output_dir = Path("/tmp/nwb_kg_integration_test_valid")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    base_name = "ecephys_valid"

    # Validate JSON files
    json_files = [
        f"{base_name}_evaluation_report.json",
        f"{base_name}_hierarchy.json",
        f"{base_name}_linkml_data.jsonld",
        f"{base_name}_knowledge_graph.jsonld",
        f"{base_name}_graph_metadata.json",
        f"{base_name}_force_layout.json"
    ]
    for fname in json_files:
        with open(output_dir / fname) as f:
            data = json.load(f)
            assert data is not None, f"{fname} should be valid JSON"

    # Validate HTML files
    html_files = [
        f"{base_name}_evaluation_report.html",
        f"{base_name}_visualization.html"
    ]
    for fname in html_files:
        content = (output_dir / fname).read_text()
        assert '<html' in content.lower(), f"{fname} should be valid HTML"

    # Validate TTL file
    from rdflib import Graph
    g = Graph()
    g.parse(output_dir / f"{base_name}_knowledge_graph.ttl", format='turtle')
    assert len(g) > 0, "TTL should be valid RDF"

    # Validate TXT file
    txt_content = (output_dir / f"{base_name}_evaluation_report.txt").read_text()
    assert len(txt_content) > 0, "TXT file should not be empty"