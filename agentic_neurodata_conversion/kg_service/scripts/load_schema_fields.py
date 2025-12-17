"""Schema Fields Loader Script.

Loads NWB schema field definitions into Neo4j.

Usage:
    pixi run python kg_service/scripts/load_schema_fields.py
"""

import asyncio
import json
import logging
import time
from pathlib import Path

from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 120


async def connect_with_retry(conn) -> None:
    """Connect to Neo4j with retries to handle slow startup."""
    start = time.time()
    last_error: Exception | None = None

    while time.time() - start < CONNECT_TIMEOUT_S:
        try:
            await conn.connect()
            if await conn.health_check():
                return
        except Exception as e:  # noqa: BLE001 - intentional retry loop
            last_error = e
            try:
                await conn.close()
            except Exception:  # nosec B110 - intentional cleanup, errors can be safely ignored
                pass
        await asyncio.sleep(2)

    raise RuntimeError(f"Neo4j did not become ready within {CONNECT_TIMEOUT_S}s") from last_error


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

    # Create SchemaField nodes in a single batched query using UNWIND
    logger.info(f"  Batching {len(fields)} schema fields...")

    query = """
    UNWIND $fields_batch AS field
    MERGE (f:SchemaField {field_path: field.field_path})
    SET f.description = field.description,
        f.required = field.required,
        f.ontology_governed = field.ontology_governed,
        f.ontology_name = field.ontology_name,
        f.value_type = field.value_type,
        f.examples_json = field.examples_json
    RETURN count(f) AS fields_created
    """

    # Prepare all fields as a batch
    # Convert examples to JSON string if they contain nested arrays (Neo4j can't store nested arrays)
    batch_params = {
        "fields_batch": [
            {
                "field_path": field["field_path"],
                "description": field["description"],
                "required": field["required"],
                "ontology_governed": field["ontology_governed"],
                "ontology_name": field.get("ontology"),
                "value_type": field["value_type"],
                "examples_json": json.dumps(field.get("examples", [])) if field.get("examples") else None,
            }
            for field in fields
        ]
    }

    # Single database roundtrip instead of N separate queries
    result = await conn.execute_write(query, batch_params)
    fields_created = result[0]["fields_created"] if result else 0

    logger.info(f"  ✅ Batch loaded {fields_created} schema fields")
    return len(fields)


async def main():
    """Main loader function."""
    settings = get_settings()

    # Connect to Neo4j
    if not settings.graph_db.password:
        raise ValueError("GRAPH_DB__PASSWORD/NEO4J_PASSWORD is required to load schema fields")
    conn = get_neo4j_connection(
        uri=settings.graph_db.uri,
        user=settings.graph_db.user,
        password=settings.graph_db.password,
        database=settings.graph_db.database,
    )
    await connect_with_retry(conn)

    try:
        count = await load_schema_fields(conn)
        logger.info(f"Total schema fields loaded: {count}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
