"""Ontology Loader Script.

Loads ontology terms from JSON files into Neo4j database.
Creates constraints, indexes, and IS_A relationships for the ontology hierarchy.

This script should be run once during Phase 1 setup to populate the knowledge graph
with ontology terms from NCBITaxonomy, UBERON, and PATO.

Usage:
    pixi run python kg_service/scripts/load_ontologies.py

Expected output:
    ✅ Successfully loaded 44 ontology terms
    - 20 from NCBITaxonomy (species)
    - 20 from UBERON (brain regions)
    - 4 from PATO (sex terms)
"""

import asyncio
import json
import logging
from pathlib import Path

from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_constraints_and_indexes(conn) -> None:
    """Create Neo4j constraints and indexes.

    Creates:
    - UNIQUE constraint on OntologyTerm.term_id
    - Index on OntologyTerm.label for fast lookups
    - Index on OntologyTerm.ontology_name for filtering by ontology

    Args:
        conn: AsyncNeo4jConnection instance
    """
    logger.info("Creating constraints and indexes...")

    # Unique constraint on OntologyTerm.term_id
    await conn.execute_write("""
        CREATE CONSTRAINT ontology_term_id IF NOT EXISTS
        FOR (t:OntologyTerm) REQUIRE t.term_id IS UNIQUE
    """)

    # Index on OntologyTerm.label for fast lookups
    await conn.execute_write("""
        CREATE INDEX ontology_term_label IF NOT EXISTS
        FOR (t:OntologyTerm) ON (t.label)
    """)

    # Index on OntologyTerm.ontology_name for filtering
    await conn.execute_write("""
        CREATE INDEX ontology_term_ontology IF NOT EXISTS
        FOR (t:OntologyTerm) ON (t.ontology_name)
    """)

    logger.info("Constraints and indexes created")


async def load_ontology_file(conn, file_path: Path) -> int:
    """Load a single ontology JSON file.

    Reads JSON file and creates OntologyTerm nodes in Neo4j using MERGE
    to avoid duplicates. Sets all term properties including synonyms and
    parent_terms for hierarchy.

    Args:
        conn: AsyncNeo4jConnection instance
        file_path: Path to JSON ontology file

    Returns:
        Number of terms loaded from file

    Example:
        >>> count = await load_ontology_file(conn, Path("ncbi_taxonomy_subset.json"))
        >>> print(f"Loaded {count} terms")
        Loaded 20 terms
    """
    logger.info(f"Loading {file_path.name}...")

    with open(file_path) as f:
        data = json.load(f)

    ontology_name = data["ontology"]
    terms = data["terms"]

    # Load terms
    for term in terms:
        query = """
        MERGE (t:OntologyTerm {term_id: $term_id})
        SET t.label = $label,
            t.definition = $definition,
            t.synonyms = $synonyms,
            t.ontology_name = $ontology_name,
            t.parent_terms = $parent_terms
        RETURN t.term_id AS term_id
        """

        params = {
            "term_id": term["term_id"],
            "label": term["label"],
            "definition": term.get("definition"),
            "synonyms": term.get("synonyms", []),
            "ontology_name": ontology_name,
            "parent_terms": term.get("parent_terms", []),
        }

        await conn.execute_write(query, params)

    logger.info(f"Loaded {len(terms)} terms from {file_path.name}")
    return len(terms)


async def create_is_a_relationships(conn) -> None:
    """Create IS_A relationships from parent_terms.

    Processes all OntologyTerm nodes and creates IS_A relationships to their
    parent terms based on the parent_terms property. This builds the ontology
    hierarchy for transitive queries.

    Args:
        conn: AsyncNeo4jConnection instance

    Example:
        >>> await create_is_a_relationships(conn)
        INFO:Created 42 IS_A relationships
    """
    logger.info("Creating IS_A relationships...")

    query = """
    MATCH (child:OntologyTerm)
    WHERE size(child.parent_terms) > 0
    UNWIND child.parent_terms AS parent_id
    MATCH (parent:OntologyTerm {term_id: parent_id})
    MERGE (child)-[:IS_A]->(parent)
    RETURN count(*) AS relationships_created
    """

    result = await conn.execute_write(query)
    count = result[0]["relationships_created"] if result else 0
    logger.info(f"Created {count} IS_A relationships")


async def main() -> None:
    """Main loader function.

    Connects to Neo4j, creates schema (constraints/indexes), loads all ontology
    files, and creates IS_A relationships. This is the entry point for the script.

    Raises:
        ServiceUnavailable: If Neo4j is not accessible
        FileNotFoundError: If ontology JSON files are missing
    """
    settings = get_settings()

    # Connect to Neo4j
    conn = get_neo4j_connection(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
    await conn.connect()

    try:
        # Create schema
        await create_constraints_and_indexes(conn)

        # Load ontology files
        ontology_dir = Path(__file__).parent.parent / "ontologies"
        files = [
            ontology_dir / "ncbi_taxonomy_subset.json",
            ontology_dir / "uberon_subset.json",
            ontology_dir / "pato_sex_subset.json",
        ]

        total_terms = 0
        for file_path in files:
            if file_path.exists():
                count = await load_ontology_file(conn, file_path)
                total_terms += count
            else:
                logger.warning(f"File not found: {file_path}")

        # Create relationships
        await create_is_a_relationships(conn)

        logger.info(f"✅ Successfully loaded {total_terms} ontology terms")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
