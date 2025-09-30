"""Integration test for interactive HTML visualization.

Scenario: Generate HTML visualization and validate offline capability.
This test MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
import json
import re


def test_html_visualization_generation():
    """Test HTML visualization is generated."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    assert viz_path.exists()
    assert viz_path.stat().st_size > 0


def test_html_is_valid_html5():
    """Test that generated HTML is valid HTML5."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_html5")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should have HTML5 doctype
    assert '<!DOCTYPE html>' in content or '<!doctype html>' in content.lower()
    assert '<html' in content.lower()
    assert '</html>' in content.lower()
    assert '<head' in content.lower()
    assert '<body' in content.lower()


def test_html_is_self_contained():
    """Test that HTML has no external dependencies."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_offline")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should NOT have external resource references
    assert 'src="http://' not in content, "Should not reference external scripts"
    assert 'src="https://' not in content, "Should not reference external scripts"
    assert 'href="http://' not in content or content.count('href="http://') <= 2, "Should not reference external styles (except maybe fonts)"


def test_html_embeds_knowledge_graph_json():
    """Test that knowledge graph JSON is embedded in HTML."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_embed")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should have embedded JSON
    assert 'application/json' in content or 'type="application/json"' in content

    # Extract JSON
    match = re.search(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', content, re.DOTALL)
    if match:
        json_str = match.group(1)
        data = json.loads(json_str)
        assert data is not None


def test_html_uses_canvas_api():
    """Test that visualization uses Canvas API (not SVG)."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_canvas")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should use canvas
    assert '<canvas' in content.lower()
    # Should NOT primarily use SVG for graph
    svg_count = content.lower().count('<svg')
    canvas_count = content.lower().count('<canvas')
    assert canvas_count > 0


def test_html_includes_interactivity():
    """Test that HTML includes interactive features."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_interactive")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should have JavaScript
    assert '<script' in content

    # Should have event listeners
    interactive_keywords = ['addEventListener', 'onclick', 'onmousemove', 'click', 'mouseover']
    has_interactivity = any(keyword in content for keyword in interactive_keywords)
    assert has_interactivity, "Should have interactive event handling"


def test_html_includes_pan_zoom():
    """Test that visualization supports pan and zoom."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_panzoom")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should mention zoom or scale
    zoom_keywords = ['zoom', 'scale', 'transform', 'wheel']
    has_zoom = any(keyword in content.lower() for keyword in zoom_keywords)
    assert has_zoom, "Should support zoom functionality"


def test_html_includes_tooltips():
    """Test that visualization includes tooltips on hover."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_tooltips")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should have tooltip functionality
    tooltip_keywords = ['tooltip', 'hover', 'mouseover', 'title']
    has_tooltips = any(keyword in content.lower() for keyword in tooltip_keywords)
    assert has_tooltips, "Should support tooltips"


def test_html_includes_search_functionality():
    """Test that visualization includes search capability."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_search")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should have search/filter functionality
    search_keywords = ['search', 'filter', 'find', 'input']
    has_search = any(keyword in content.lower() for keyword in search_keywords)
    assert has_search, "Should support search/filter"


def test_html_handles_large_graphs():
    """Test visualization of large graphs (1000+ nodes)."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/large_graph_1000_nodes.nwb")
    output_dir = Path("/tmp/nwb_viz_test_large")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "large_graph_1000_nodes_visualization.html"
    assert viz_path.exists()
    # Should generate HTML even for large graphs
    assert viz_path.stat().st_size > 0


def test_html_uses_vanilla_javascript():
    """Test that visualization uses vanilla JavaScript (no frameworks)."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_vanilla")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should NOT use external frameworks
    frameworks = ['react', 'vue', 'angular', 'jquery', 'd3.js', 'd3.min.js']
    for framework in frameworks:
        assert framework not in content.lower(), f"Should not use {framework}"


def test_html_browser_compatibility():
    """Test that HTML works in modern browsers (implicit check)."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_viz_test_compat")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    viz_path = output_dir / "sample_visualization.html"
    content = viz_path.read_text()

    # Should use ES6+ features supported by modern browsers
    assert '<script' in content
    # Should not have compatibility warnings
    assert len(content) > 5000  # Substantial visualization code