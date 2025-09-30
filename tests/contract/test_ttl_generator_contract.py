"""Contract test for ttl_generator module.

Tests the interface for generating TTL and JSON-LD from LinkML instances.
These tests MUST FAIL initially (no implementation exists yet).
"""

import pytest
from pathlib import Path
from typing import Dict, List, Any


def test_generate_ttl_returns_ttl_string():
    """Test that generate_ttl returns valid TTL string."""
    from src.ttl_generator import generate_ttl
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    from src.linkml_converter import convert_nwb_to_linkml

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")
    linkml_instances = convert_nwb_to_linkml(nwbfile, schema)

    # Act
    result = generate_ttl(linkml_instances, schema)

    # Assert
    assert isinstance(result, str)
    assert len(result) > 0
    # Should contain TTL syntax markers
    assert '@prefix' in result or 'PREFIX' in result
    assert '<' in result and '>' in result  # URIs


def test_generate_ttl_produces_valid_rdf():
    """Test that generated TTL is valid RDF."""
    from src.ttl_generator import generate_ttl
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    from src.linkml_converter import convert_nwb_to_linkml
    from rdflib import Graph

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")
    linkml_instances = convert_nwb_to_linkml(nwbfile, schema)

    # Act
    ttl_content = generate_ttl(linkml_instances, schema)

    # Assert
    # Should be parseable by rdflib
    g = Graph()
    try:
        g.parse(data=ttl_content, format='turtle')
        assert len(g) > 0  # Should have triples
    except Exception as e:
        pytest.fail(f"Generated TTL is not valid RDF: {e}")


def test_generate_jsonld_returns_jsonld_string():
    """Test that generate_jsonld returns valid JSON-LD string."""
    from src.ttl_generator import generate_jsonld

    # Arrange
    ttl_content = """
    @prefix nwb: <http://purl.org/nwb/2.5.0/> .
    nwb:test a nwb:NWBFile .
    """

    # Act
    result = generate_jsonld(ttl_content)

    # Assert
    assert isinstance(result, str)
    assert len(result) > 0
    # Should be valid JSON
    import json
    try:
        parsed = json.loads(result)
        assert isinstance(parsed, (dict, list))
    except json.JSONDecodeError:
        pytest.fail("Generated JSON-LD is not valid JSON")


def test_generate_jsonld_includes_context():
    """Test that JSON-LD includes proper @context."""
    from src.ttl_generator import generate_jsonld
    import json

    # Arrange
    ttl_content = """
    @prefix nwb: <http://purl.org/nwb/2.5.0/> .
    nwb:test a nwb:NWBFile .
    """

    # Act
    jsonld_str = generate_jsonld(ttl_content)
    parsed = json.loads(jsonld_str)

    # Assert
    # Should have @context
    assert '@context' in parsed or any('@context' in item for item in (parsed if isinstance(parsed, list) else [parsed]))


def test_generate_jsonld_contains_all_triples():
    """Test that JSON-LD contains all triples from TTL."""
    from src.ttl_generator import generate_ttl, generate_jsonld
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    from src.linkml_converter import convert_nwb_to_linkml
    from rdflib import Graph

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")
    linkml_instances = convert_nwb_to_linkml(nwbfile, schema)

    # Act
    ttl_content = generate_ttl(linkml_instances, schema)
    jsonld_content = generate_jsonld(ttl_content)

    # Parse both
    g_ttl = Graph()
    g_ttl.parse(data=ttl_content, format='turtle')

    g_jsonld = Graph()
    g_jsonld.parse(data=jsonld_content, format='json-ld')

    # Assert
    # Should have same number of triples
    assert len(g_ttl) == len(g_jsonld)


def test_generate_ttl_uses_persistent_uris():
    """Test that TTL uses persistent URIs (http://purl.org/nwb/...)."""
    from src.ttl_generator import generate_ttl
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    from src.linkml_converter import convert_nwb_to_linkml

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")
    linkml_instances = convert_nwb_to_linkml(nwbfile, schema)

    # Act
    ttl_content = generate_ttl(linkml_instances, schema)

    # Assert
    # Should use persistent URIs
    assert 'http://purl.org/nwb/' in ttl_content or 'purl.org/nwb' in ttl_content


def test_generate_ttl_handles_large_instances():
    """Test TTL generation for large LinkML instances."""
    from src.ttl_generator import generate_ttl
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    from src.linkml_converter import convert_nwb_to_linkml
    import time

    # Arrange
    large_file = Path("tests/fixtures/large_1gb.nwb")
    nwbfile = load_nwb_file(large_file)
    schema = load_official_schema("2.5.0")
    linkml_instances = convert_nwb_to_linkml(nwbfile, schema)
    start_time = time.time()

    # Act
    ttl_content = generate_ttl(linkml_instances, schema)
    elapsed = time.time() - start_time

    # Assert
    assert len(ttl_content) > 0
    # Should complete within reasonable time
    assert elapsed < 300  # 5 minutes max


def test_generate_jsonld_performance():
    """Test JSON-LD conversion performance."""
    from src.ttl_generator import generate_ttl, generate_jsonld
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    from src.linkml_converter import convert_nwb_to_linkml
    import time

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")
    linkml_instances = convert_nwb_to_linkml(nwbfile, schema)
    ttl_content = generate_ttl(linkml_instances, schema)
    start_time = time.time()

    # Act
    jsonld_content = generate_jsonld(ttl_content)
    elapsed = time.time() - start_time

    # Assert
    assert len(jsonld_content) > 0
    # Should be fast (using rdflib.Graph.serialize)
    assert elapsed < 60  # 1 minute max


def test_generate_ttl_produces_queryable_graph():
    """Test that generated TTL supports SPARQL queries."""
    from src.ttl_generator import generate_ttl
    from src.nwb_loader import load_nwb_file
    from src.linkml_schema_loader import load_official_schema
    from src.linkml_converter import convert_nwb_to_linkml
    from rdflib import Graph

    # Arrange
    test_file = Path("tests/fixtures/sample.nwb")
    nwbfile = load_nwb_file(test_file)
    schema = load_official_schema("2.5.0")
    linkml_instances = convert_nwb_to_linkml(nwbfile, schema)
    ttl_content = generate_ttl(linkml_instances, schema)

    # Act
    g = Graph()
    g.parse(data=ttl_content, format='turtle')

    # Simple SPARQL query
    query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
    results = list(g.query(query))

    # Assert
    assert len(results) > 0  # Should be queryable