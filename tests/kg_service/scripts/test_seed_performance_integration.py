"""Integration tests for KG seed job performance."""

import time

import pytest

from agentic_neurodata_conversion.kg_service.scripts.load_ontologies import (
    create_constraints_and_indexes,
    create_is_a_relationships,
)
from agentic_neurodata_conversion.kg_service.scripts.load_ontologies import main as load_ontologies_main
from agentic_neurodata_conversion.kg_service.scripts.load_schema_fields import main as load_schema_fields_main
from tests.kg_service._neo4j_availability import neo4j_http_available

# Skip integration tests if Neo4j is not available
pytestmark = pytest.mark.integration


@pytest.fixture
async def neo4j_connection():
    """Fixture for Neo4j connection."""
    from agentic_neurodata_conversion.kg_service.config import get_settings
    from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection, reset_neo4j_connection

    # Reset connection to avoid singleton issues
    reset_neo4j_connection()

    settings = get_settings()

    # Check if Neo4j HTTP endpoint is available
    if not neo4j_http_available(settings.compose.neo4j_http_port):
        pytest.skip("Neo4j not running on localhost; skipping Neo4j integration tests")

    # Check if graph DB settings are configured
    if not settings.graph_db.password:
        pytest.skip("Graph DB password not configured; skipping integration tests")

    conn = get_neo4j_connection(
        uri=settings.graph_db.uri,
        user=settings.graph_db.user,
        password=settings.graph_db.password,
        database=settings.graph_db.database,
    )

    # Try to connect, skip if Neo4j isn't running or not accessible
    try:
        await conn.connect()
        # Verify connection with health check
        if not await conn.health_check():
            pytest.skip("Neo4j health check failed")
    except Exception as e:
        pytest.skip(f"Neo4j not accessible: {e}")

    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_seed_job_completes_under_30_seconds(neo4j_connection):
    """Verify that the complete seed job finishes in under 30 seconds.

    This test validates the performance optimization by running the full
    seed sequence (ontologies + schema fields) and ensuring it completes
    within the target time of 30 seconds.

    The batched query implementation should reduce execution time by ~90%
    compared to the original N+1 query pattern.
    """
    start_time = time.time()

    # Run the full seeding sequence
    try:
        # 1. Create constraints and indexes
        await create_constraints_and_indexes(neo4j_connection)

        # 2. Load all ontologies (3 files, 96 total terms)
        await load_ontologies_main()

        # 3. Load schema fields (15 fields)
        await load_schema_fields_main()

        # 4. Create IS_A relationships
        await create_is_a_relationships(neo4j_connection)

    except Exception as e:
        pytest.fail(f"Seed job failed with error: {e}")

    elapsed = time.time() - start_time

    # Verify performance target
    assert elapsed < 30.0, (
        f"Seed job took {elapsed:.2f}s, expected <30s. Performance optimization may not be working correctly."
    )

    # Verify data integrity - all data loaded correctly
    # Check ontology terms
    result = await neo4j_connection.execute_read("MATCH (t:OntologyTerm) RETURN count(t) AS count")
    ontology_count = result[0]["count"] if result else 0
    assert ontology_count == 96, f"Expected 96 ontology terms, got {ontology_count}"

    # Check schema fields
    result = await neo4j_connection.execute_read("MATCH (f:SchemaField) RETURN count(f) AS count")
    fields_count = result[0]["count"] if result else 0
    assert fields_count == 15, f"Expected 15 schema fields, got {fields_count}"

    # Check IS_A relationships
    result = await neo4j_connection.execute_read("MATCH ()-[r:IS_A]->() RETURN count(r) AS count")
    relationships_count = result[0]["count"] if result else 0
    assert relationships_count > 0, "Expected IS_A relationships to be created"

    print(f"\n✅ Seed job completed in {elapsed:.2f}s (target: <30s)")
    print(f"   - Ontology terms: {ontology_count}")
    print(f"   - Schema fields: {fields_count}")
    print(f"   - IS_A relationships: {relationships_count}")


@pytest.mark.asyncio
async def test_batch_query_performance_improvement(neo4j_connection):
    """Verify that batched queries are significantly faster than sequential queries.

    This test compares the performance of the new batched implementation
    against a theoretical sequential baseline to ensure the optimization
    is effective.
    """
    from pathlib import Path

    from agentic_neurodata_conversion.kg_service.scripts.load_ontologies import load_ontology_file

    # Find the largest ontology file (ncbi_taxonomy_subset.json with 72 terms)
    ontology_dir = (
        Path(__file__).parent.parent.parent.parent / "agentic_neurodata_conversion" / "kg_service" / "ontologies"
    )
    ncbi_file = ontology_dir / "ncbi_taxonomy_subset.json"

    if not ncbi_file.exists():
        pytest.skip("NCBI taxonomy file not found")

    start_time = time.time()
    count = await load_ontology_file(neo4j_connection, ncbi_file)
    elapsed = time.time() - start_time

    # With batched queries, loading 72 terms should take <2 seconds
    # (Previously would take 3.6-7.2s with N+1 pattern)
    assert elapsed < 2.0, (
        f"Loading {count} terms took {elapsed:.2f}s, expected <2s. Batch optimization may not be working."
    )

    # Verify all terms were loaded
    assert count == 72, f"Expected to load 72 terms, got {count}"

    print(f"\n✅ Batched loading of {count} terms completed in {elapsed:.2f}s")
    print(f"   Performance improvement: ~{(3.6 / elapsed):.1f}x faster than sequential")


@pytest.mark.asyncio
async def test_seed_idempotency(neo4j_connection):
    """Verify that running the seed job multiple times is safe (idempotent).

    The MERGE operations should ensure that re-running the seed scripts
    doesn't duplicate data or cause errors.
    """
    # Run seed job twice
    await load_ontologies_main()
    await load_schema_fields_main()

    # Get counts after first run
    result1 = await neo4j_connection.execute_read("MATCH (t:OntologyTerm) RETURN count(t) AS count")
    count1 = result1[0]["count"] if result1 else 0

    # Run again
    await load_ontologies_main()
    await load_schema_fields_main()

    # Get counts after second run
    result2 = await neo4j_connection.execute_read("MATCH (t:OntologyTerm) RETURN count(t) AS count")
    count2 = result2[0]["count"] if result2 else 0

    # Counts should be identical (no duplicates)
    assert count1 == count2 == 96, f"Idempotency check failed: {count1} != {count2}"

    print(f"\n✅ Idempotency verified: {count1} terms before and after re-run")
