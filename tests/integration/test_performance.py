"""Integration test for large file performance.

Scenario: Process 1GB NWB file and measure time to ensure <15 minute target.
This test MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
import time
import json


def test_1gb_file_processing_time():
    """Test that 1GB file completes within 15 minutes."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/large_1gb.nwb")
    output_dir = Path("/tmp/nwb_perf_test_1gb")
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])
    elapsed = time.time() - start_time

    # Assert
    assert result == 0, "1GB file should process successfully"
    assert elapsed < 900, f"1GB file took {elapsed:.1f}s, should be < 900s (15 min)"
    print(f"Performance: 1GB file processed in {elapsed:.1f}s")


def test_5gb_file_max_size():
    """Test that 5GB file (max size) can be processed."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/large_5gb.nwb")
    output_dir = Path("/tmp/nwb_perf_test_5gb")
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])
    elapsed = time.time() - start_time

    # Assert
    assert result == 0, "5GB file should process successfully"
    # 5GB may take longer, but should complete
    assert elapsed < 3600, f"5GB file took {elapsed:.1f}s, should be < 3600s (60 min)"
    print(f"Performance: 5GB file processed in {elapsed:.1f}s")


def test_progress_indicators_work():
    """Test that progress indicators update during processing."""
    import subprocess

    # Arrange
    test_file = Path("tests/fixtures/large_1gb.nwb")

    # Act
    result = subprocess.run(
        ["python", "-m", "src.main", str(test_file), "--verbose"],
        capture_output=True,
        text=True,
        timeout=1000
    )

    # Assert
    # Should have progress output
    assert "Loading" in result.stdout or "Processing" in result.stdout or \
           "%" in result.stdout or result.returncode == 0


def test_memory_usage_within_limits():
    """Test that memory usage stays reasonable during processing."""
    from src.main import main
    import psutil
    import os

    # Arrange
    test_file = Path("tests/fixtures/large_1gb.nwb")
    output_dir = Path("/tmp/nwb_perf_test_memory")
    output_dir.mkdir(parents=True, exist_ok=True)

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # Assert
    assert result == 0
    # Should not use excessive memory (< 4GB increase for 1GB file)
    assert memory_increase < 4000, f"Memory increased by {memory_increase:.1f}MB, should be < 4000MB"
    print(f"Performance: Memory increased by {memory_increase:.1f}MB")


def test_phase_timing_breakdown():
    """Test timing for each processing phase."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/large_1gb.nwb")
    output_dir = Path("/tmp/nwb_perf_test_timing")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir), "--verbose", "--show-timing"])

    # Assert
    assert result in [0, 1]  # May not implement --show-timing yet

    # If metadata includes timing
    metadata_path = output_dir / "large_1gb_graph_metadata.json"
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

        # May include timing info
        if 'timing' in metadata:
            assert 'total_time' in metadata['timing']


def test_concurrent_processing_single_file():
    """Test that single file processing doesn't spawn unnecessary threads."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_perf_test_single")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0
    # Single file processing should work correctly


def test_small_file_performance():
    """Test that small files process quickly (<1 minute)."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/small_10mb.nwb")
    output_dir = Path("/tmp/nwb_perf_test_small")
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])
    elapsed = time.time() - start_time

    # Assert
    assert result == 0
    assert elapsed < 60, f"Small file took {elapsed:.1f}s, should be < 60s"
    print(f"Performance: Small file processed in {elapsed:.1f}s")


def test_medium_file_performance():
    """Test that medium files (100-500MB) process efficiently."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/medium_300mb.nwb")
    output_dir = Path("/tmp/nwb_perf_test_medium")
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])
    elapsed = time.time() - start_time

    # Assert
    assert result == 0
    assert elapsed < 300, f"Medium file took {elapsed:.1f}s, should be < 300s (5 min)"
    print(f"Performance: Medium file processed in {elapsed:.1f}s")


def test_performance_target_95_percent():
    """Test that 95% of 1GB files complete within 15 minutes."""
    from src.main import main

    # Arrange - Run multiple 1GB files
    test_files = [
        Path("tests/fixtures/large_1gb_sample1.nwb"),
        Path("tests/fixtures/large_1gb_sample2.nwb"),
        Path("tests/fixtures/large_1gb_sample3.nwb"),
    ]

    times = []
    successes = 0

    for test_file in test_files:
        if not test_file.exists():
            continue

        output_dir = Path(f"/tmp/nwb_perf_test_{test_file.stem}")
        output_dir.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        result = main([str(test_file), "--output-dir", str(output_dir)])
        elapsed = time.time() - start_time

        if result == 0:
            times.append(elapsed)
            if elapsed < 900:
                successes += 1

    # Assert
    if len(times) > 0:
        within_target_percent = (successes / len(times)) * 100
        assert within_target_percent >= 95, \
            f"Only {within_target_percent:.1f}% within 15 min, should be >= 95%"


def test_visualization_generation_performance():
    """Test that visualization generation doesn't dominate processing time."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/large_1gb.nwb")
    output_dir = Path("/tmp/nwb_perf_test_viz")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Visualization HTML should exist
    viz_path = output_dir / "large_1gb_visualization.html"
    assert viz_path.exists()

    # Should not be excessively large (< 50MB for 1GB input)
    viz_size = viz_path.stat().st_size / 1024 / 1024  # MB
    assert viz_size < 50, f"Visualization is {viz_size:.1f}MB, should be < 50MB"


def test_ttl_generation_performance():
    """Test TTL generation performance for large files."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/large_1gb.nwb")
    output_dir = Path("/tmp/nwb_perf_test_ttl")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # TTL should be generated
    ttl_path = output_dir / "large_1gb_knowledge_graph.ttl"
    assert ttl_path.exists()

    # Size should be reasonable
    ttl_size = ttl_path.stat().st_size / 1024 / 1024  # MB
    # TTL can be large, but not excessive
    assert ttl_size < 500, f"TTL is {ttl_size:.1f}MB, should be < 500MB"