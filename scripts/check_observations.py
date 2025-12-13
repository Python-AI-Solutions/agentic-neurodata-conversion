#!/usr/bin/env python3
"""Quick script to check observations in Neo4j for debugging."""

import asyncio
import os
import sys

from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection


async def check_observations(subject_id: str):
    """Check if there are any observations for a subject."""
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_password:
        print("ERROR: NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    # Create connection
    neo4j_conn = get_neo4j_connection(uri="bolt://localhost:7687", user="neo4j", password=neo4j_password)

    try:
        # Query for all observations with this subject_id
        query = """
        MATCH (obs:Observation)
        WHERE obs.subject_id = $subject_id
        RETURN obs.field_path AS field_path,
               obs.normalized_value AS normalized_value,
               obs.source_file AS source_file,
               obs.is_active AS is_active,
               obs.created_at AS created_at
        ORDER BY obs.created_at DESC
        LIMIT 20
        """

        results = await neo4j_conn.execute_read(query, {"subject_id": subject_id})

        print(f"\n=== Observations for subject_id='{subject_id}' ===\n")

        if not results:
            print(f"No observations found for subject_id='{subject_id}'")
            print("\nThis explains why historical inference isn't working:")
            print("- First conversion for this subject")
            print("- No prior observations to learn from")
            print("- Need at least 2 observations per field for inference")
            return

        print(f"Found {len(results)} observations:\n")
        for i, obs in enumerate(results, 1):
            print(f"{i}. field_path: {obs['field_path']}")
            print(f"   normalized_value: {obs['normalized_value']}")
            print(f"   source_file: {obs['source_file']}")
            print(f"   is_active: {obs['is_active']}")
            print(f"   created_at: {obs['created_at']}")
            print()

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        await neo4j_conn.close()


if __name__ == "__main__":
    subject_id = sys.argv[1] if len(sys.argv) > 1 else "mouse001"
    asyncio.run(check_observations(subject_id))
