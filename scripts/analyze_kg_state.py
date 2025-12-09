#!/usr/bin/env python3
"""Analyze current state of the knowledge graph."""

import asyncio
import os
import sys

from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection


async def analyze_kg():
    """Analyze the current state of Neo4j knowledge graph."""
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_password:
        print("ERROR: NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j_conn = get_neo4j_connection(uri="bolt://localhost:7687", user="neo4j", password=neo4j_password)

    # Connect to database
    await neo4j_conn.connect()

    try:
        print("=" * 80)
        print("KNOWLEDGE GRAPH STATE ANALYSIS")
        print("=" * 80)

        # 1. Count all observations by subject
        print("\n1. OBSERVATIONS BY SUBJECT:")
        query1 = """
        MATCH (obs:Observation)
        RETURN obs.subject_id AS subject_id,
               count(*) AS observation_count,
               collect(DISTINCT obs.field_path) AS fields,
               collect(DISTINCT obs.source_file) AS files
        ORDER BY observation_count DESC
        """
        results1 = await neo4j_conn.execute_read(query1, {})
        for r in results1:
            print(f"\n  Subject: {r['subject_id']}")
            print(f"  Total observations: {r['observation_count']}")
            print(f"  Fields tracked: {', '.join(r['fields'])}")
            print(f"  Source files: {len(r['files'])} unique files")

        # 2. Detailed observations for mouse001
        print("\n" + "=" * 80)
        print("2. DETAILED OBSERVATIONS FOR subject_id=mouse001:")
        query2 = """
        MATCH (obs:Observation)
        WHERE obs.subject_id = 'mouse001'
        RETURN obs.observation_id AS id,
               obs.field_path AS field_path,
               obs.raw_value AS raw_value,
               obs.normalized_value AS normalized_value,
               obs.source_file AS source_file,
               obs.confidence AS confidence,
               obs.is_active AS is_active,
               obs.created_at AS created_at
        ORDER BY obs.field_path, obs.created_at
        """
        results2 = await neo4j_conn.execute_read(query2, {})

        current_field = None
        for i, obs in enumerate(results2, 1):
            if obs["field_path"] != current_field:
                print(f"\n  Field: {obs['field_path']}")
                print(f"  {'-' * 70}")
                current_field = obs["field_path"]

            # Extract filename from full path
            filename = obs["source_file"].split("/")[-1]

            print(f"    [{i}] {obs['normalized_value']}")
            print(f"        Source: {filename}")
            print(f"        Raw: {obs['raw_value']}")
            print(f"        Confidence: {obs['confidence']}")
            print(f"        Active: {obs['is_active']}")
            print(f"        Created: {obs['created_at']}")

        # 3. Check inference readiness
        print("\n" + "=" * 80)
        print("3. INFERENCE READINESS CHECK:")
        query3 = """
        MATCH (obs:Observation)
        WHERE obs.subject_id = 'mouse001' AND obs.is_active = true
        WITH obs.field_path AS field_path,
             count(DISTINCT obs.source_file) AS file_count,
             count(*) AS observation_count,
             collect(DISTINCT obs.normalized_value) AS unique_values
        RETURN field_path,
               file_count,
               observation_count,
               unique_values,
               size(unique_values) AS value_diversity,
               CASE
                 WHEN file_count >= 2 AND size(unique_values) = 1 THEN '✅ READY (will suggest: ' + unique_values[0] + ')'
                 WHEN file_count >= 2 AND size(unique_values) > 1 THEN '⚠️ CONFLICTING (' + toString(size(unique_values)) + ' different values)'
                 WHEN file_count < 2 THEN '❌ INSUFFICIENT (need 2+ files, have ' + toString(file_count) + ')'
                 ELSE '❓ UNKNOWN'
               END AS inference_status
        ORDER BY field_path
        """
        results3 = await neo4j_conn.execute_read(query3, {})

        for r in results3:
            print(f"\n  {r['field_path']}")
            print(
                f"    Files: {r['file_count']} | Observations: {r['observation_count']} | Unique values: {r['value_diversity']}"
            )
            print(f"    Values: {r['unique_values']}")
            print(f"    Status: {r['inference_status']}")

        # 4. Test inference for a specific field
        print("\n" + "=" * 80)
        print("4. TEST INFERENCE ENGINE (simulating query for session2 file):")

        # Simulate what the inference engine would do for session2
        test_fields = ["subject.species", "subject.sex", "experimenter", "institution"]

        for field_path in test_fields:
            query4 = """
            MATCH (obs:Observation {field_path: $field_path})
            WHERE obs.subject_id = $subject_id
              AND obs.source_file <> $target_file
              AND obs.is_active = true
            WITH obs.normalized_value AS value, count(*) AS evidence_count
            ORDER BY evidence_count DESC
            LIMIT 1
            WITH value, evidence_count
            WHERE evidence_count >= 2
            MATCH (obs2:Observation {field_path: $field_path})
            WHERE obs2.subject_id = $subject_id
              AND obs2.source_file <> $target_file
              AND obs2.is_active = true
            WITH value, evidence_count, collect(DISTINCT obs2.normalized_value) AS all_values
            WHERE size(all_values) = 1
            RETURN value AS suggested_value, evidence_count
            """

            params = {
                "field_path": field_path,
                "subject_id": "mouse001",
                "target_file": "/private/var/folders/ks/g26dg74n6l9djm0hbp0dz_cm0000gn/T/nwb_uploads/18118024_session2.abf",
            }

            result = await neo4j_conn.execute_read(query4, params)

            if result:
                print(
                    f"\n  {field_path}: ✅ WOULD SUGGEST '{result[0]['suggested_value']}' (evidence: {result[0]['evidence_count']})"
                )
            else:
                print(f"\n  {field_path}: ❌ NO SUGGESTION (insufficient evidence)")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await neo4j_conn.close()


if __name__ == "__main__":
    asyncio.run(analyze_kg())
