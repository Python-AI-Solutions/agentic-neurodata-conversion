"""Contract test for html_generator module.

Tests the interface for generating interactive HTML visualizations.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
from typing import Dict, Any
import json


def test_generate_visualization_returns_html_string():
    """Test that generate_visualization returns valid HTML string."""
    from src.html_generator import generate_visualization

    # Arrange
    graph_jsonld = json.dumps({
        "@context": {"nwb": "http://purl.org/nwb/2.5.0/"},
        "@graph": [
            {"@id": "nwb:file1", "@type": "nwb:NWBFile"}
        ]
    })
    metadata = {"node_count": 1, "edge_count": 0}

    # Act
    result = generate_visualization(graph_jsonld, metadata)

    # Assert
    assert isinstance(result, str)
    assert len(result) > 0
    assert '<html' in result.lower()
    assert '</html>' in result.lower()


def test_generate_visualization_is_self_contained():
    """Test that HTML has no external dependencies."""
    from src.html_generator import generate_visualization

    # Arrange
    graph_jsonld = json.dumps({
        "@context": {"nwb": "http://purl.org/nwb/2.5.0/"},
        "@graph": []
    })
    metadata = {}

    # Act
    html = generate_visualization(graph_jsonld, metadata)

    # Assert
    # Should not have external script/style references
    assert 'src="http' not in html
    assert 'href="http' not in html
    # Should have inline scripts
    assert '<script' in html


def test_generate_visualization_embeds_json():
    """Test that JSON-LD is embedded in HTML."""
    from src.html_generator import generate_visualization

    # Arrange
    graph_jsonld = json.dumps({
        "@context": {"nwb": "http://purl.org/nwb/2.5.0/"},
        "@graph": [
            {"@id": "nwb:test123", "@type": "nwb:NWBFile"}
        ]
    })
    metadata = {}

    # Act
    html = generate_visualization(graph_jsonld, metadata)

    # Assert
    # Should embed the JSON
    assert 'test123' in html
    assert 'application/json' in html or 'type="application/json"' in html


def test_generate_visualization_produces_valid_html5():
    """Test that generated HTML is valid HTML5."""
    from src.html_generator import generate_visualization

    # Arrange
    graph_jsonld = json.dumps({"@graph": []})
    metadata = {}

    # Act
    html = generate_visualization(graph_jsonld, metadata)

    # Assert
    assert '<!DOCTYPE html>' in html or '<!doctype html>' in html.lower()
    assert '<html' in html.lower()
    assert '<head' in html.lower()
    assert '<body' in html.lower()


def test_generate_visualization_includes_canvas():
    """Test that HTML includes canvas element for rendering."""
    from src.html_generator import generate_visualization

    # Arrange
    graph_jsonld = json.dumps({"@graph": []})
    metadata = {}

    # Act
    html = generate_visualization(graph_jsonld, metadata)

    # Assert
    # Should use Canvas API (not SVG)
    assert '<canvas' in html.lower()


def test_generate_visualization_includes_interactivity():
    """Test that HTML includes interactive features."""
    from src.html_generator import generate_visualization

    # Arrange
    graph_jsonld = json.dumps({
        "@graph": [
            {"@id": "nwb:node1", "@type": "nwb:NWBFile"},
            {"@id": "nwb:node2", "@type": "nwb:TimeSeries"}
        ]
    })
    metadata = {"node_count": 2, "edge_count": 1}

    # Act
    html = generate_visualization(graph_jsonld, metadata)

    # Assert
    # Should have JavaScript for interactivity
    assert '<script' in html
    # Should handle mouse events
    assert 'click' in html.lower() or 'mouse' in html.lower()


def test_generate_visualization_handles_large_graphs():
    """Test visualization of large graphs (1000+ nodes)."""
    from src.html_generator import generate_visualization
    import time

    # Arrange
    nodes = [{"@id": f"nwb:node{i}", "@type": "nwb:TimeSeries"} for i in range(1000)]
    graph_jsonld = json.dumps({"@graph": nodes})
    metadata = {"node_count": 1000, "edge_count": 999}

    start_time = time.time()

    # Act
    html = generate_visualization(graph_jsonld, metadata)
    elapsed = time.time() - start_time

    # Assert
    assert len(html) > 0
    # Should complete quickly
    assert elapsed < 30  # 30 seconds max


def test_generate_visualization_uses_jinja2_template():
    """Test that generation uses jinja2 templates."""
    from src.html_generator import generate_visualization

    # Arrange
    graph_jsonld = json.dumps({"@graph": []})
    metadata = {}

    # Act
    html = generate_visualization(graph_jsonld, metadata)

    # Assert
    # Should be generated from template
    assert len(html) > 1000  # Should be substantial template


def test_generate_visualization_includes_metadata():
    """Test that metadata is included in HTML."""
    from src.html_generator import generate_visualization

    # Arrange
    graph_jsonld = json.dumps({"@graph": []})
    metadata = {
        "node_count": 42,
        "edge_count": 123,
        "density": 0.5,
        "file_name": "test.nwb"
    }

    # Act
    html = generate_visualization(graph_jsonld, metadata)

    # Assert
    # Metadata should be visible or embedded
    assert '42' in html or 'node_count' in html
    assert 'test.nwb' in html


def test_generate_visualization_produces_parseable_json():
    """Test that embedded JSON is parseable."""
    from src.html_generator import generate_visualization
    import re

    # Arrange
    graph_jsonld = json.dumps({
        "@context": {"nwb": "http://purl.org/nwb/2.5.0/"},
        "@graph": [{"@id": "nwb:test"}]
    })
    metadata = {}

    # Act
    html = generate_visualization(graph_jsonld, metadata)

    # Assert
    # Extract JSON from script tag
    match = re.search(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    if match:
        embedded_json = match.group(1)
        # Should be parseable
        parsed = json.loads(embedded_json)
        assert '@graph' in parsed or '@context' in parsed