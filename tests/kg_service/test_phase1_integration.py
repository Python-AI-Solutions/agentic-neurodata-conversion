"""Phase 1 Integration Tests.

Integration tests for Neo4j database operations, ontology loading,
and graph queries. Requires Neo4j to be running with ontologies loaded.

Run with: PYTHONPATH=. pixi run pytest tests/kg_service/test_phase1_integration.py -m integration -v
"""

import pytest


@pytest.fixture
async def neo4j_connection():
    """Fixture for Neo4j connection."""
    import os

    # Skip if NEO4J_PASSWORD not set (e.g., in CI)
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        pytest.skip("NEO4J_PASSWORD not set - Neo4j tests require local Neo4j instance")

    from agentic_neurodata_conversion.kg_service.config import get_settings
    from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection, reset_neo4j_connection

    # Reset connection to avoid singleton issues
    reset_neo4j_connection()

    settings = get_settings()
    conn = get_neo4j_connection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    # Try to connect, skip if Neo4j isn't running
    try:
        await conn.connect()
    except Exception as e:
        pytest.skip(f"Neo4j not accessible: {e}")

    yield conn
    await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_health_check(neo4j_connection):
    """Verify Neo4j health check works."""
    is_healthy = await neo4j_connection.health_check()
    assert is_healthy is True, "Neo4j health check failed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ontology_terms_loaded(neo4j_connection):
    """Verify all 96 ontology terms are loaded (Phase 1.5: expanded NCBITaxonomy)."""
    query = "MATCH (t:OntologyTerm) RETURN count(t) AS count"
    result = await neo4j_connection.execute_read(query)
    count = result[0]["count"]
    # Phase 1.5: 72 NCBITaxonomy + 20 UBERON + 4 PATO = 96 total
    assert count == 96, f"Expected 96 ontology terms, got {count}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ontology_counts_by_type(neo4j_connection):
    """Verify correct counts for each ontology type (Phase 1.5: expanded NCBITaxonomy)."""
    query = """
    MATCH (t:OntologyTerm)
    RETURN t.ontology_name AS ontology, count(*) AS count
    ORDER BY ontology
    """
    result = await neo4j_connection.execute_read(query)

    counts = {r["ontology"]: r["count"] for r in result}
    # Phase 1.5: Expanded NCBITaxonomy from 20 → 72 terms (added genus, family, order hierarchies)
    assert counts.get("NCBITaxonomy") == 72, f"Expected 72 NCBITaxonomy terms, got {counts.get('NCBITaxonomy', 0)}"
    assert counts.get("UBERON") == 20, f"Expected 20 UBERON terms, got {counts.get('UBERON', 0)}"
    assert counts.get("PATO") == 4, f"Expected 4 PATO terms, got {counts.get('PATO', 0)}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_constraint_exists(neo4j_connection):
    """Verify UNIQUE constraint on term_id exists."""
    query = "SHOW CONSTRAINTS"
    result = await neo4j_connection.execute_read(query)

    # Check if any constraint contains "ontology_term_id"
    constraints = [str(r).lower() for r in result]
    has_constraint = any("ontology_term_id" in c for c in constraints)
    assert has_constraint, "UNIQUE constraint on OntologyTerm.term_id not found"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_indexes_exist(neo4j_connection):
    """Verify indexes on label and ontology_name exist."""
    query = "SHOW INDEXES"
    result = await neo4j_connection.execute_read(query)

    indexes = [str(r).lower() for r in result]
    has_label_index = any("ontology_term_label" in i for i in indexes)
    has_ontology_index = any("ontology_term_ontology" in i for i in indexes)

    assert has_label_index, "Index on OntologyTerm.label not found"
    assert has_ontology_index, "Index on OntologyTerm.ontology_name not found"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_is_a_relationships_created(neo4j_connection):
    """Verify IS_A relationships were created for ontology hierarchy (Phase 1.5)."""
    query = "MATCH ()-[r:IS_A]->() RETURN count(r) AS count"
    result = await neo4j_connection.execute_read(query)
    count = result[0]["count"]
    # Phase 1.5: 70 NCBITaxonomy IS_A + 16 UBERON IS_A = 86 total
    # (2 root terms in NCBITaxonomy have no parents: Chordata, Protostomia)
    assert count == 86, f"Expected 86 IS_A relationships, got {count}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_by_label(neo4j_connection):
    """Test querying ontology term by exact label match."""
    query = """
    MATCH (t:OntologyTerm {label: 'Mus musculus'})
    RETURN t.term_id AS term_id, t.synonyms AS synonyms
    """
    result = await neo4j_connection.execute_read(query)

    assert len(result) == 1, f"Expected 1 result for 'Mus musculus', got {len(result)}"
    assert result[0]["term_id"] == "NCBITaxon:10090", f"Expected NCBITaxon:10090, got {result[0]['term_id']}"
    assert "mouse" in result[0]["synonyms"], "Expected 'mouse' in synonyms"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_by_synonym(neo4j_connection):
    """Test querying ontology term by synonym."""
    query = """
    MATCH (t:OntologyTerm)
    WHERE 'mouse' IN t.synonyms
    RETURN t.term_id AS term_id, t.label AS label
    LIMIT 1
    """
    result = await neo4j_connection.execute_read(query)

    assert len(result) >= 1, "No terms found with 'mouse' synonym"
    assert result[0]["term_id"].startswith("NCBITaxon:"), f"Expected NCBITaxon term, got {result[0]['term_id']}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_loader_idempotent(neo4j_connection):
    """Test that running loader multiple times doesn't duplicate terms.

    This test verifies the MERGE operation is working correctly.
    Note: This test doesn't actually run the loader - it just verifies
    the current state is correct after multiple loads during development.
    """
    query = "MATCH (t:OntologyTerm) RETURN count(t) AS count"
    result = await neo4j_connection.execute_read(query)
    count = result[0]["count"]

    # Phase 1.5: Should always be exactly 96 terms, even if loader was run multiple times
    # (72 NCBITaxonomy + 20 UBERON + 4 PATO)
    assert count == 96, f"Loader may not be idempotent - expected 96 terms, got {count}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hierarchy_query(neo4j_connection):
    """Test querying ontology hierarchy via IS_A relationships."""
    query = """
    MATCH (child:OntologyTerm)-[:IS_A]->(parent:OntologyTerm)
    RETURN child.label AS child, parent.label AS parent
    LIMIT 1
    """
    result = await neo4j_connection.execute_read(query)

    assert len(result) >= 1, "No IS_A relationships found in hierarchy"
    assert "child" in result[0], "Query should return child label"
    assert "parent" in result[0], "Query should return parent label"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_health_check_performance(neo4j_connection):
    """Verify health check is fast (<50ms average over 5 runs)."""
    import time

    durations = []
    for _ in range(5):
        start = time.time()
        await neo4j_connection.health_check()
        duration = (time.time() - start) * 1000
        durations.append(duration)

    avg_duration = sum(durations) / len(durations)
    assert avg_duration < 50, f"Health check too slow: {avg_duration:.2f}ms average (max 50ms)"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_exact_match_performance(neo4j_connection):
    """Verify exact label match is fast (<150ms average over 5 runs)."""
    import time

    query = "MATCH (t:OntologyTerm {label: 'Mus musculus'}) RETURN t"

    durations = []
    for _ in range(5):
        start = time.time()
        await neo4j_connection.execute_read(query)
        duration = (time.time() - start) * 1000
        durations.append(duration)

    avg_duration = sum(durations) / len(durations)
    assert avg_duration < 150, f"Exact match too slow: {avg_duration:.2f}ms average (max 150ms)"
