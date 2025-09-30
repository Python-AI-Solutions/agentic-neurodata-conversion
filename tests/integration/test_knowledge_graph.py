"""Integration test for knowledge graph generation.

Scenario: Generate TTL and JSON-LD, validate semantic correctness and SPARQL queries.
This test MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
import json
from rdflib import Graph, Namespace


def test_knowledge_graph_ttl_generation():
    """Test TTL generation from NWB file."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test_ttl")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    ttl_path = output_dir / "sample_knowledge_graph.ttl"
    assert ttl_path.exists()

    # Parse TTL
    g = Graph()
    g.parse(ttl_path, format='turtle')
    assert len(g) > 0, "TTL should contain triples"


def test_knowledge_graph_jsonld_generation():
    """Test JSON-LD generation from TTL."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test_jsonld")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    jsonld_path = output_dir / "sample_knowledge_graph.jsonld"
    assert jsonld_path.exists()

    # Parse JSON-LD
    with open(jsonld_path) as f:
        data = json.load(f)

    assert '@context' in data or (isinstance(data, list) and any('@context' in item for item in data))


def test_semantic_fidelity_ttl_to_jsonld():
    """Test that TTL to JSON-LD conversion maintains semantic fidelity."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test_fidelity")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Load both formats
    ttl_path = output_dir / "sample_knowledge_graph.ttl"
    jsonld_path = output_dir / "sample_knowledge_graph.jsonld"

    g_ttl = Graph()
    g_ttl.parse(ttl_path, format='turtle')

    g_jsonld = Graph()
    g_jsonld.parse(jsonld_path, format='json-ld')

    # Must have same number of triples
    assert len(g_ttl) == len(g_jsonld), "Semantic fidelity: same triple count"

    # Must have same subjects
    ttl_subjects = set(g_ttl.subjects())
    jsonld_subjects = set(g_jsonld.subjects())
    assert ttl_subjects == jsonld_subjects, "Semantic fidelity: same subjects"


def test_sparql_query_on_knowledge_graph():
    """Test SPARQL queries work on generated knowledge graph."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test_sparql")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Load TTL
    ttl_path = output_dir / "sample_knowledge_graph.ttl"
    g = Graph()
    g.parse(ttl_path, format='turtle')

    # Run SPARQL query
    query = """
    SELECT ?s ?p ?o
    WHERE {
        ?s ?p ?o
    }
    LIMIT 10
    """
    results = list(g.query(query))
    assert len(results) > 0, "SPARQL query should return results"


def test_knowledge_graph_uses_persistent_uris():
    """Test that knowledge graph uses persistent URIs."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test_uris")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check TTL content
    ttl_path = output_dir / "sample_knowledge_graph.ttl"
    content = ttl_path.read_text()

    # Should use persistent URIs
    assert 'http://purl.org/nwb/' in content or 'purl.org/nwb' in content


def test_knowledge_graph_includes_all_nwb_entities():
    """Test that knowledge graph includes all major NWB entities."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/comprehensive.nwb")  # File with various entity types
    output_dir = Path("/tmp/nwb_kg_test_entities")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Load graph
    ttl_path = output_dir / "comprehensive_knowledge_graph.ttl"
    g = Graph()
    g.parse(ttl_path, format='turtle')

    # Query for entity types
    query = """
    SELECT DISTINCT ?type
    WHERE {
        ?s a ?type
    }
    """
    results = list(g.query(query))
    types = [str(row[0]) for row in results]

    # Should have multiple entity types
    assert len(types) >= 3, "Should have various NWB entity types"


def test_knowledge_graph_preserves_relationships():
    """Test that relationships between entities are preserved."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/with_references.nwb")
    output_dir = Path("/tmp/nwb_kg_test_relationships")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Load graph
    ttl_path = output_dir / "with_references_knowledge_graph.ttl"
    g = Graph()
    g.parse(ttl_path, format='turtle')

    # Count relationships (edges)
    # Exclude rdf:type statements
    RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    relationships = [triple for triple in g if triple[1] != RDF.type]

    assert len(relationships) > 0, "Should have relationships beyond type declarations"


def test_knowledge_graph_jsonld_has_proper_context():
    """Test that JSON-LD has proper @context."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test_context")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Check JSON-LD
    jsonld_path = output_dir / "sample_knowledge_graph.jsonld"
    with open(jsonld_path) as f:
        data = json.load(f)

    # Should have @context
    if isinstance(data, dict):
        assert '@context' in data
        context = data['@context']
        assert isinstance(context, (dict, str, list))
    elif isinstance(data, list):
        # Check if any item has @context
        has_context = any('@context' in item for item in data if isinstance(item, dict))
        assert has_context


def test_knowledge_graph_supports_owl_reasoning():
    """Test that knowledge graph supports OWL reasoning."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test_owl")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir), "--enable-reasoning"])

    # Assert
    assert result == 0

    # Load graph
    ttl_path = output_dir / "sample_knowledge_graph.ttl"
    g = Graph()
    g.parse(ttl_path, format='turtle')

    # Should be able to parse without errors
    assert len(g) > 0


def test_knowledge_graph_metadata_accuracy():
    """Test that graph metadata is accurate."""
    from src.main import main

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    output_dir = Path("/tmp/nwb_kg_test_metadata")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Act
    result = main([str(test_file), "--output-dir", str(output_dir)])

    # Assert
    assert result == 0

    # Load metadata
    metadata_path = output_dir / "sample_graph_metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)

    # Load actual graph
    ttl_path = output_dir / "sample_knowledge_graph.ttl"
    g = Graph()
    g.parse(ttl_path, format='turtle')

    # Count nodes and edges
    subjects = set(g.subjects())
    objects = set(g.objects())
    nodes = subjects.union(objects)

    # Metadata should match actual counts
    assert metadata['node_count'] == len(nodes), "Node count should match"
    # Edge count might vary based on how we count (with/without rdf:type)
    assert 'edge_count' in metadata