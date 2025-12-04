"""Schema Fields Loader Script.

Loads NWB schema field definitions into Neo4j.

Usage:
    pixi run python kg_service/scripts/load_schema_fields.py
"""

import asyncio
import json
import logging
from pathlib import Path

from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_schema_fields(conn):
    """Load schema fields from JSON.

    Args:
        conn: Neo4j connection instance

    Returns:
        Number of schema fields loaded
    """
    logger.info("Loading schema fields...")

    # Load JSON file
    config_path = Path(__file__).parent.parent / "config" / "schema_fields.json"
    with open(config_path) as f:
        data = json.load(f)

    fields = data["fields"]

    # Create SchemaField nodes
    for field in fields:
        # Convert examples to JSON string if they contain nested arrays
        examples = field.get("examples", [])
        # Neo4j can't store nested arrays, so convert to JSON string
        examples_str = json.dumps(examples) if examples else None

        query = """
        MERGE (f:SchemaField {field_path: $field_path})
        SET f.description = $description,
            f.required = $required,
            f.ontology_governed = $ontology_governed,
            f.ontology_name = $ontology_name,
            f.value_type = $value_type,
            f.examples_json = $examples_json
        RETURN f.field_path AS field_path
        """

        params = {
            "field_path": field["field_path"],
            "description": field["description"],
            "required": field["required"],
            "ontology_governed": field["ontology_governed"],
            "ontology_name": field.get("ontology"),
            "value_type": field["value_type"],
            "examples_json": examples_str,
        }

        await conn.execute_write(query, params)

    logger.info(f"✅ Loaded {len(fields)} schema fields")
    return len(fields)


async def main():
    """Main loader function."""
    settings = get_settings()

    # Connect to Neo4j
    conn = get_neo4j_connection(uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password)
    await conn.connect()

    try:
        count = await load_schema_fields(conn)
        logger.info(f"Total schema fields loaded: {count}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
