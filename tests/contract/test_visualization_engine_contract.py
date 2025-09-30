"""Contract test for visualization_engine module.

Tests the interface for graph layout and styling algorithms.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from typing import List, Dict, Any


def test_compute_force_directed_layout_returns_layout_data():
    """Test that compute_force_directed_layout returns LayoutData."""
    from src.visualization_engine import compute_force_directed_layout

    # Arrange
    nodes = [
        {"id": "node1", "label": "Node 1"},
        {"id": "node2", "label": "Node 2"},
        {"id": "node3", "label": "Node 3"}
    ]
    edges = [
        {"source": "node1", "target": "node2"},
        {"source": "node2", "target": "node3"}
    ]

    # Act
    result = compute_force_directed_layout(nodes, edges)

    # Assert
    assert result is not None
    assert hasattr(result, 'positions')
    assert len(result.positions) == len(nodes)


def test_compute_force_directed_layout_assigns_positions():
    """Test that all nodes get x,y positions."""
    from src.visualization_engine import compute_force_directed_layout

    # Arrange
    nodes = [
        {"id": "node1"},
        {"id": "node2"},
        {"id": "node3"}
    ]
    edges = [
        {"source": "node1", "target": "node2"}
    ]

    # Act
    layout = compute_force_directed_layout(nodes, edges)

    # Assert
    for node_id in ["node1", "node2", "node3"]:
        assert node_id in layout.positions
        pos = layout.positions[node_id]
        assert 'x' in pos
        assert 'y' in pos
        assert isinstance(pos['x'], (int, float))
        assert isinstance(pos['y'], (int, float))


def test_compute_force_directed_layout_converges():
    """Test that layout algorithm converges to stable positions."""
    from src.visualization_engine import compute_force_directed_layout

    # Arrange
    nodes = [{"id": f"node{i}"} for i in range(10)]
    edges = [{"source": f"node{i}", "target": f"node{i+1}"} for i in range(9)]

    # Act
    layout = compute_force_directed_layout(nodes, edges, max_iterations=1000)

    # Assert
    assert layout is not None
    assert hasattr(layout, 'converged')
    # Should converge or reach max iterations
    assert layout.converged is True or layout.iterations == 1000


def test_compute_force_directed_layout_handles_large_graphs():
    """Test layout computation for large graphs (1000+ nodes)."""
    from src.visualization_engine import compute_force_directed_layout
    import time

    # Arrange
    nodes = [{"id": f"node{i}"} for i in range(1000)]
    edges = [{"source": f"node{i}", "target": f"node{(i+1)%1000}"} for i in range(1000)]

    start_time = time.time()

    # Act
    layout = compute_force_directed_layout(nodes, edges, max_iterations=500)
    elapsed = time.time() - start_time

    # Assert
    assert layout is not None
    assert len(layout.positions) == 1000
    # Should complete in reasonable time
    assert elapsed < 60  # 1 minute max


def test_compute_force_directed_layout_uses_verlet_integration():
    """Test that layout uses Verlet integration per research.md."""
    from src.visualization_engine import compute_force_directed_layout

    # Arrange
    nodes = [{"id": "node1"}, {"id": "node2"}]
    edges = [{"source": "node1", "target": "node2"}]

    # Act
    layout = compute_force_directed_layout(nodes, edges, algorithm="verlet")

    # Assert
    assert layout is not None
    # Should use Verlet integration
    assert hasattr(layout, 'algorithm') and layout.algorithm == "verlet"


def test_apply_visual_styling_returns_styled_graph():
    """Test that apply_visual_styling returns StyledGraph."""
    from src.visualization_engine import apply_visual_styling

    # Arrange
    graph = {
        "nodes": [
            {"id": "node1", "type": "NWBFile"},
            {"id": "node2", "type": "TimeSeries"}
        ],
        "edges": [
            {"source": "node1", "target": "node2"}
        ]
    }
    config = {
        "node_colors": {"NWBFile": "#FF0000", "TimeSeries": "#00FF00"},
        "node_sizes": {"NWBFile": 10, "TimeSeries": 5}
    }

    # Act
    result = apply_visual_styling(graph, config)

    # Assert
    assert result is not None
    assert 'nodes' in result
    assert 'edges' in result


def test_apply_visual_styling_assigns_colors():
    """Test that styling assigns colors based on node types."""
    from src.visualization_engine import apply_visual_styling

    # Arrange
    graph = {
        "nodes": [
            {"id": "node1", "type": "NWBFile"},
            {"id": "node2", "type": "TimeSeries"}
        ],
        "edges": []
    }
    config = {
        "node_colors": {"NWBFile": "#FF0000", "TimeSeries": "#00FF00"}
    }

    # Act
    styled = apply_visual_styling(graph, config)

    # Assert
    for node in styled['nodes']:
        assert 'color' in node or 'style' in node
        if node['type'] == 'NWBFile':
            assert node.get('color') == '#FF0000' or '#FF0000' in str(node.get('style'))


def test_apply_visual_styling_assigns_sizes():
    """Test that styling assigns sizes based on importance/type."""
    from src.visualization_engine import apply_visual_styling

    # Arrange
    graph = {
        "nodes": [
            {"id": "node1", "type": "NWBFile"},
            {"id": "node2", "type": "TimeSeries"}
        ],
        "edges": []
    }
    config = {
        "node_sizes": {"NWBFile": 20, "TimeSeries": 10}
    }

    # Act
    styled = apply_visual_styling(graph, config)

    # Assert
    for node in styled['nodes']:
        assert 'size' in node or 'radius' in node


def test_apply_visual_styling_handles_edge_styles():
    """Test that styling applies to edges as well."""
    from src.visualization_engine import apply_visual_styling

    # Arrange
    graph = {
        "nodes": [{"id": "node1"}, {"id": "node2"}],
        "edges": [
            {"source": "node1", "target": "node2", "type": "reference"}
        ]
    }
    config = {
        "edge_colors": {"reference": "#0000FF"},
        "edge_widths": {"reference": 2}
    }

    # Act
    styled = apply_visual_styling(graph, config)

    # Assert
    for edge in styled['edges']:
        assert 'color' in edge or 'width' in edge or 'style' in edge


def test_compute_force_directed_layout_handles_disconnected_components():
    """Test layout of graphs with disconnected components."""
    from src.visualization_engine import compute_force_directed_layout

    # Arrange
    nodes = [
        {"id": "node1"}, {"id": "node2"},  # Component 1
        {"id": "node3"}, {"id": "node4"}   # Component 2 (disconnected)
    ]
    edges = [
        {"source": "node1", "target": "node2"},
        {"source": "node3", "target": "node4"}
    ]

    # Act
    layout = compute_force_directed_layout(nodes, edges)

    # Assert
    assert layout is not None
    assert len(layout.positions) == 4
    # Components should be spatially separated