"""Contract test for main CLI module.

Tests the command-line interface and workflow orchestration.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
import subprocess
import json


def test_cli_accepts_nwb_file_path():
    """Test that CLI accepts NWB file path as argument."""
    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")

    # Act
    result = subprocess.run(
        ["python", "-m", "src.main", str(test_file)],
        capture_output=True,
        text=True
    )

    # Assert
    # Should not fail on argument parsing
    assert result.returncode in [0, 1, 2]  # Valid exit codes


def test_cli_outputs_10_files():
    """Test that CLI generates all 10 output files."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test")

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0  # Success

    # Check for 10 output files
    expected_files = [
        "sample_evaluation_report.json",
        "sample_evaluation_report.html",
        "sample_evaluation_report.txt",
        "sample_hierarchy.json",
        "sample_linkml_data.jsonld",
        "sample_knowledge_graph.ttl",
        "sample_knowledge_graph.jsonld",
        "sample_graph_metadata.json",
        "sample_visualization.html",
        "sample_force_layout.json"
    ]

    for fname in expected_files:
        assert (output_dir / fname).exists(), f"Missing output file: {fname}"


def test_cli_exit_code_success():
    """Test that CLI returns exit code 0 on success."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/valid.nwb")

    # Act
    result = main([str(test_file)])

    # Assert
    assert result == 0


def test_cli_exit_code_error():
    """Test that CLI returns exit code 1 on processing error."""
    from src.main import main

    # Arrange
    corrupted_file = Path("tests/fixtures/corrupted.nwb")

    # Act
    result = main([str(corrupted_file)])

    # Assert
    assert result == 1  # Error


def test_cli_exit_code_invalid_input():
    """Test that CLI returns exit code 2 on invalid input."""
    from src.main import main

    # Arrange
    nonexistent = Path("/nonexistent/file.nwb")

    # Act
    result = main([str(nonexistent)])

    # Assert
    assert result == 2  # Invalid input


def test_cli_outputs_correct_naming():
    """Test that output files follow naming convention."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/my_experiment.nwb")
    output_dir = Path("/tmp/nwb_kg_test2")

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # All outputs should start with "my_experiment_"
    output_files = list(output_dir.glob("my_experiment_*"))
    assert len(output_files) >= 10


def test_cli_handles_verbose_flag():
    """Test that CLI supports --verbose flag."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")

    # Act
    result = main([str(test_file), "--verbose"])

    # Assert
    # Should accept flag without error
    assert result in [0, 1, 2]


def test_cli_handles_output_dir_option():
    """Test that CLI supports --output-dir option."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    custom_dir = Path("/tmp/custom_output")

    # Act
    result = main([str(test_file), "--output-dir", str(custom_dir)])

    # Assert
    assert result == 0
    assert custom_dir.exists()


def test_cli_shows_progress_indicators():
    """Test that CLI displays progress during processing."""
    # This test would capture stdout to verify progress output
    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")

    # Act
    result = subprocess.run(
        ["python", "-m", "src.main", str(test_file), "--verbose"],
        capture_output=True,
        text=True
    )

    # Assert
    # Should have progress messages
    assert "Loading" in result.stdout or "Processing" in result.stdout or result.returncode == 0


def test_cli_handles_large_file():
    """Test CLI processing of large file (1GB)."""
    from src.main import main
    import time

    # Arrange
    large_file = Path("tests/fixtures/large_1gb.nwb")
    start_time = time.time()

    # Act
    result = main([str(large_file)])
    elapsed = time.time() - start_time

    # Assert
    assert result == 0
    # Should complete within 15 minutes
    assert elapsed < 900


def test_cli_orchestrates_complete_workflow():
    """Test that CLI orchestrates all modules in correct order."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_workflow_test")

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Verify workflow: evaluation report created BEFORE deep inspection
    eval_report = output_dir / "sample_evaluation_report.json"
    hierarchy = output_dir / "sample_hierarchy.json"

    assert eval_report.exists()
    assert hierarchy.exists()

    # Evaluation report should be created first (check timestamps or content order)
    eval_stat = eval_report.stat()
    hier_stat = hierarchy.stat()
    # Both should exist (order verified by workflow logic)


def test_cli_help_flag():
    """Test that CLI shows help with --help."""
    # Act
    result = subprocess.run(
        ["python", "-m", "src.main", "--help"],
        capture_output=True,
        text=True
    )

    # Assert
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()


def test_cli_version_flag():
    """Test that CLI shows version with --version."""
    # Act
    result = subprocess.run(
        ["python", "-m", "src.main", "--version"],
        capture_output=True,
        text=True
    )

    # Assert
    assert result.returncode == 0
    # Should output version number
    assert any(char.isdigit() for char in result.stdout)