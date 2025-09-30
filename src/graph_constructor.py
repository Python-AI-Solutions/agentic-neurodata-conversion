"""Knowledge graph constructor from RDF/TTL.

This module builds knowledge graph structures from RDF/TTL and computes analytics.
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from rdflib import Graph, URIRef, Literal, RDF
import networkx as nx


@dataclass
class Node:
    """Graph node."""
    id: str
    label: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """Graph edge."""
    source: str
    target: str
    predicate: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeGraph:
    """Knowledge graph structure."""
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    triples: list[tuple] = field(default_factory=list)


@dataclass
class GraphMetrics:
    """Analytics metrics for knowledge graph."""
    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0
    degree_centrality: dict[str, float] = field(default_factory=dict)
    avg_degree: float = 0.0


def build_graph_from_ttl(ttl_content: str, enable_reasoning: bool = False) -> KnowledgeGraph:
    """Build knowledge graph from TTL content.

    Args:
        ttl_content: TTL/Turtle RDF content
        enable_reasoning: Whether to enable OWL reasoning

    Returns:
        KnowledgeGraph object
    """
    # Parse TTL
    rdf_graph = Graph()
    rdf_graph.parse(data=ttl_content, format='turtle')

    # Optional: Apply OWL reasoning
    if enable_reasoning:
        try:
            import owlrl
            owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(rdf_graph)
        except ImportError:
            pass  # owlrl not available, skip reasoning

    kg = KnowledgeGraph()

    # Store all triples
    kg.triples = list(rdf_graph)

    # Build nodes and edges
    node_ids = set()

    for s, p, o in rdf_graph:
        # Add subject as node
        if isinstance(s, URIRef):
            subject_id = str(s)
            if subject_id not in node_ids:
                node_type = _get_node_type(s, rdf_graph)
                node = Node(
                    id=subject_id,
                    label=_get_label(s),
                    type=node_type
                )
                _add_properties(node, s, rdf_graph)
                kg.nodes.append(node)
                node_ids.add(subject_id)

        # Add object as node if it's a URI
        if isinstance(o, URIRef):
            object_id = str(o)
            if object_id not in node_ids:
                node_type = _get_node_type(o, rdf_graph)
                node = Node(
                    id=object_id,
                    label=_get_label(o),
                    type=node_type
                )
                _add_properties(node, o, rdf_graph)
                kg.nodes.append(node)
                node_ids.add(object_id)

            # Add edge (only for URI objects, not literals)
            if p != RDF.type:  # Exclude type declarations from edges
                edge = Edge(
                    source=str(s),
                    target=str(o),
                    predicate=str(p)
                )
                kg.edges.append(edge)

    return kg


def compute_graph_analytics(graph: KnowledgeGraph) -> GraphMetrics:
    """Compute analytics metrics for knowledge graph.

    Args:
        graph: KnowledgeGraph object

    Returns:
        GraphMetrics with computed metrics
    """
    metrics = GraphMetrics()

    metrics.node_count = len(graph.nodes)
    metrics.edge_count = len(graph.edges)

    # Compute density
    if metrics.node_count > 1:
        max_edges = metrics.node_count * (metrics.node_count - 1)
        metrics.density = metrics.edge_count / max_edges if max_edges > 0 else 0.0

    # Build NetworkX graph for centrality
    if graph.nodes and graph.edges:
        nx_graph = nx.DiGraph()

        for node in graph.nodes:
            nx_graph.add_node(node.id)

        for edge in graph.edges:
            nx_graph.add_edge(edge.source, edge.target)

        # Compute degree centrality
        if nx_graph.number_of_nodes() > 0:
            centrality = nx.degree_centrality(nx_graph)
            metrics.degree_centrality = centrality

            # Compute average degree
            degrees = [deg for node, deg in nx_graph.degree()]
            metrics.avg_degree = sum(degrees) / len(degrees) if degrees else 0.0

    return metrics


def _get_node_type(uri: URIRef, graph: Graph) -> str:
    """Get type of node from RDF graph.

    Args:
        uri: URI of the node
        graph: RDF graph

    Returns:
        Type string
    """
    for s, p, o in graph.triples((uri, RDF.type, None)):
        return str(o).split('/')[-1]
    return "Unknown"


def _get_label(uri: URIRef) -> str:
    """Get human-readable label from URI.

    Args:
        uri: URI

    Returns:
        Label string
    """
    uri_str = str(uri)
    # Extract last part of URI as label
    if '/' in uri_str:
        return uri_str.split('/')[-1]
    elif '#' in uri_str:
        return uri_str.split('#')[-1]
    return uri_str


def _add_properties(node: Node, uri: URIRef, graph: Graph) -> None:
    """Add properties to node from RDF graph.

    Args:
        node: Node to add properties to
        uri: URI of the node
        graph: RDF graph
    """
    for s, p, o in graph.triples((uri, None, None)):
        if p != RDF.type and isinstance(o, Literal):
            prop_name = _get_label(p)
            node.properties[prop_name] = str(o)