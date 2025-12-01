"""Phase 1 Verification Script.

Verifies that Phase 1: Graph Foundation completed successfully by checking:
- OntologyTerm nodes are loaded (44 total)
- Constraints are created
- Indexes are created
- Sample queries return expected results

Usage:
    PYTHONPATH=. pixi run python kg_service/scripts/verify_phase1.py
"""

import asyncio
import logging

from kg_service.config import get_settings
from kg_service.db.neo4j_connection import get_neo4j_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_ontology_terms(conn) -> bool:
    """Verify OntologyTerm nodes are loaded correctly."""
    logger.info("\n=== Verifying OntologyTerm nodes ===")

    # Count by ontology
    query = """
    MATCH (t:OntologyTerm)
    RETURN t.ontology_name AS ontology, count(*) AS term_count
    ORDER BY ontology
    """

    result = await conn.execute_read(query)

    expected = {
        "NCBITaxonomy": 20,
        "PATO": 4,
        "UBERON": 20
    }

    success = True
    for record in result:
        ontology = record["ontology"]
        count = record["term_count"]
        expected_count = expected.get(ontology, 0)

        if count == expected_count:
            logger.info(f"✅ {ontology}: {count} terms (expected {expected_count})")
        else:
            logger.error(f"❌ {ontology}: {count} terms (expected {expected_count})")
            success = False

    # Verify total
    total_query = "MATCH (t:OntologyTerm) RETURN count(*) AS total"
    total_result = await conn.execute_read(total_query)
    total = total_result[0]["total"]

    if total == 44:
        logger.info(f"✅ Total: {total} terms (expected 44)")
    else:
        logger.error(f"❌ Total: {total} terms (expected 44)")
        success = False

    return success


async def verify_constraints(conn) -> bool:
    """Verify constraints are created."""
    logger.info("\n=== Verifying Constraints ===")

    query = "SHOW CONSTRAINTS"
    result = await conn.execute_read(query)

    # Look for ontology_term_id constraint
    found = False
    for record in result:
        if "ontology_term_id" in str(record).lower():
            logger.info(f"✅ Found constraint: ontology_term_id")
            found = True
            break

    if not found:
        logger.error("❌ Constraint ontology_term_id not found")

    return found


async def verify_indexes(conn) -> bool:
    """Verify indexes are created."""
    logger.info("\n=== Verifying Indexes ===")

    query = "SHOW INDEXES"
    result = await conn.execute_read(query)

    expected_indexes = ["ontology_term_label", "ontology_term_ontology"]
    found_indexes = []

    for record in result:
        for expected in expected_indexes:
            if expected in str(record).lower():
                found_indexes.append(expected)
                logger.info(f"✅ Found index: {expected}")

    success = len(found_indexes) >= 2
    if not success:
        logger.error("❌ Not all expected indexes found")

    return success


async def verify_sample_queries(conn) -> bool:
    """Verify sample queries return expected results."""
    logger.info("\n=== Verifying Sample Queries ===")

    # Test 1: Query Mus musculus
    query1 = """
    MATCH (t:OntologyTerm {label: 'Mus musculus'})
    RETURN t.term_id AS term_id, t.synonyms AS synonyms
    """
    result1 = await conn.execute_read(query1)

    if result1 and result1[0]["term_id"] == "NCBITaxon:10090":
        logger.info(f"✅ Query 'Mus musculus': term_id={result1[0]['term_id']}")
        logger.info(f"   Synonyms: {result1[0]['synonyms'][:3]}...")  # Show first 3
    else:
        logger.error("❌ Query 'Mus musculus' failed")
        return False

    # Test 2: Query hippocampus
    query2 = """
    MATCH (t:OntologyTerm)
    WHERE 'hippocampus' IN t.synonyms OR t.label =~ '(?i).*hippocampus.*'
    RETURN t.term_id AS term_id, t.label AS label
    LIMIT 1
    """
    result2 = await conn.execute_read(query2)

    if result2:
        logger.info(f"✅ Query 'hippocampus': term_id={result2[0]['term_id']}, label={result2[0]['label']}")
    else:
        logger.error("❌ Query 'hippocampus' failed")
        return False

    # Test 3: Query male sex
    query3 = """
    MATCH (t:OntologyTerm {term_id: 'PATO:0000384'})
    RETURN t.label AS label
    """
    result3 = await conn.execute_read(query3)

    if result3 and result3[0]["label"] == "male":
        logger.info(f"✅ Query 'PATO:0000384': label={result3[0]['label']}")
    else:
        logger.error("❌ Query 'PATO:0000384' failed")
        return False

    return True


async def verify_relationships(conn) -> bool:
    """Verify IS_A relationships are created."""
    logger.info("\n=== Verifying IS_A Relationships ===")

    query = """
    MATCH ()-[r:IS_A]->()
    RETURN count(r) AS relationship_count
    """
    result = await conn.execute_read(query)

    count = result[0]["relationship_count"]

    if count > 0:
        logger.info(f"✅ IS_A relationships: {count}")
        return True
    else:
        logger.error("❌ No IS_A relationships found")
        return False


async def main() -> None:
    """Run all verification checks."""
    settings = get_settings()

    # Connect to Neo4j
    conn = get_neo4j_connection(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password
    )
    await conn.connect()

    try:
        # Run health check first
        is_healthy = await conn.health_check()
        if not is_healthy:
            logger.error("❌ Neo4j health check failed")
            return

        logger.info("✅ Neo4j health check passed")

        # Run all verification checks
        checks = [
            ("OntologyTerm nodes", await verify_ontology_terms(conn)),
            ("Constraints", await verify_constraints(conn)),
            ("Indexes", await verify_indexes(conn)),
            ("Sample queries", await verify_sample_queries(conn)),
            ("IS_A relationships", await verify_relationships(conn))
        ]

        # Summary
        logger.info("\n=== Phase 1 Verification Summary ===")
        all_passed = True
        for check_name, passed in checks:
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"{status}: {check_name}")
            if not passed:
                all_passed = False

        if all_passed:
            logger.info("\n🎉 Phase 1: Graph Foundation - ALL CHECKS PASSED")
        else:
            logger.error("\n❌ Phase 1: Graph Foundation - SOME CHECKS FAILED")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
