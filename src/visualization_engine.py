"""Graph visualization engine.

This module implements force-directed layout and visual styling for knowledge graphs.
"""

from typing import Any
from dataclasses import dataclass, field
import math
import random


@dataclass
class LayoutData:
    """Layout data with node positions."""
    positions: dict[str, dict[str, float]] = field(default_factory=dict)
    converged: bool = False
    iterations: int = 0
    algorithm: str = "verlet"


def compute_force_directed_layout(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    max_iterations: int = 1000,
    algorithm: str = "verlet"
) -> LayoutData:
    """Compute force-directed layout using Verlet integration.

    Args:
        nodes: List of node dictionaries
        edges: List of edge dictionaries
        max_iterations: Maximum iterations
        algorithm: Algorithm name (default: "verlet")

    Returns:
        LayoutData with computed positions
    """
    layout = LayoutData(algorithm=algorithm)

    if not nodes:
        return layout

    # Initialize random positions
    positions = {}
    velocities = {}
    for node in nodes:
        node_id = node.get("id", str(id(node)))
        positions[node_id] = {
            "x": random.uniform(-100, 100),
            "y": random.uniform(-100, 100)
        }
        velocities[node_id] = {"x": 0.0, "y": 0.0}

    # Build edge map
    edge_map = {}
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source not in edge_map:
            edge_map[source] = []
        edge_map[source].append(target)

    # Force-directed layout parameters
    k = 50.0  # Optimal distance
    c_repulsion = 5000.0  # Repulsion constant
    c_spring = 0.1  # Spring constant
    damping = 0.9  # Damping factor
    threshold = 0.1  # Convergence threshold

    # Verlet integration
    for iteration in range(max_iterations):
        forces = {node_id: {"x": 0.0, "y": 0.0} for node_id in positions}

        # Repulsion forces (all pairs)
        node_ids = list(positions.keys())
        for i, node1 in enumerate(node_ids):
            for node2 in node_ids[i+1:]:
                dx = positions[node1]["x"] - positions[node2]["x"]
                dy = positions[node1]["y"] - positions[node2]["y"]
                dist = math.sqrt(dx*dx + dy*dy) + 0.01  # Avoid division by zero

                # Repulsion force
                force = c_repulsion / (dist * dist)
                fx = (dx / dist) * force
                fy = (dy / dist) * force

                forces[node1]["x"] += fx
                forces[node1]["y"] += fy
                forces[node2]["x"] -= fx
                forces[node2]["y"] -= fy

        # Attraction forces (edges)
        for source, targets in edge_map.items():
            if source not in positions:
                continue
            for target in targets:
                if target not in positions:
                    continue

                dx = positions[target]["x"] - positions[source]["x"]
                dy = positions[target]["y"] - positions[source]["y"]
                dist = math.sqrt(dx*dx + dy*dy) + 0.01

                # Spring force
                force = c_spring * (dist - k)
                fx = (dx / dist) * force
                fy = (dy / dist) * force

                forces[source]["x"] += fx
                forces[source]["y"] += fy
                forces[target]["x"] -= fx
                forces[target]["y"] -= fy

        # Update positions with Verlet integration
        max_displacement = 0.0
        for node_id in positions:
            # Update velocity
            velocities[node_id]["x"] = velocities[node_id]["x"] * damping + forces[node_id]["x"]
            velocities[node_id]["y"] = velocities[node_id]["y"] * damping + forces[node_id]["y"]

            # Update position
            positions[node_id]["x"] += velocities[node_id]["x"]
            positions[node_id]["y"] += velocities[node_id]["y"]

            # Track max displacement
            displacement = math.sqrt(velocities[node_id]["x"]**2 + velocities[node_id]["y"]**2)
            max_displacement = max(max_displacement, displacement)

        # Check convergence
        if max_displacement < threshold:
            layout.converged = True
            layout.iterations = iteration + 1
            break

    layout.iterations = max_iterations if not layout.converged else layout.iterations
    layout.positions = positions

    return layout


def apply_visual_styling(graph: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Apply visual styling to graph based on configuration.

    Args:
        graph: Graph dictionary with nodes and edges
        config: Styling configuration

    Returns:
        Styled graph dictionary
    """
    styled = {
        "nodes": [],
        "edges": []
    }

    # Style nodes
    node_colors = config.get("node_colors", {})
    node_sizes = config.get("node_sizes", {})

    for node in graph.get("nodes", []):
        styled_node = node.copy()

        # Apply color based on type
        node_type = node.get("type", "default")
        if node_type in node_colors:
            styled_node["color"] = node_colors[node_type]
        else:
            styled_node["color"] = "#999999"  # Default gray

        # Apply size based on type
        if node_type in node_sizes:
            styled_node["size"] = node_sizes[node_type]
        else:
            styled_node["size"] = 5  # Default size

        styled["nodes"].append(styled_node)

    # Style edges
    edge_colors = config.get("edge_colors", {})
    edge_widths = config.get("edge_widths", {})

    for edge in graph.get("edges", []):
        styled_edge = edge.copy()

        # Apply color based on type
        edge_type = edge.get("type", "default")
        if edge_type in edge_colors:
            styled_edge["color"] = edge_colors[edge_type]
        else:
            styled_edge["color"] = "#cccccc"  # Default light gray

        # Apply width based on type
        if edge_type in edge_widths:
            styled_edge["width"] = edge_widths[edge_type]
        else:
            styled_edge["width"] = 1  # Default width

        styled["edges"].append(styled_edge)

    return styled