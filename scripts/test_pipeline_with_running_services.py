"""Test the pipeline using already-running MCP server and agents."""

import asyncio
import httpx
import json
from pathlib import Path


async def test_pipeline():
    """Test the full pipeline using HTTP API."""

    server_url = "http://localhost:8000"
    dataset_path = "./tests/data/synthetic_openephys"

    print("\n" + "="*80)
    print("Testing Pipeline with Running Services")
    print("="*80 + "\n")

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Check server health
        print("[1/4] Checking server health...")
        response = await client.get(f"{server_url}/health")
        health = response.json()
        print(f"  Status: {health['status']}")
        print(f"  Agents registered: {', '.join(health['agents_registered'])}")
        print(f"  Redis connected: {health['redis_connected']}\n")

        # Step 2: Initialize session
        print("[2/4] Initializing session...")
        response = await client.post(
            f"{server_url}/api/v1/sessions/initialize",
            json={"dataset_path": dataset_path}
        )

        if response.status_code != 200:
            print(f"  ERROR: {response.status_code}")
            print(f"  Response: {response.text}")
            return

        result = response.json()
        session_id = result["session_id"]
        print(f"  Session ID: {session_id}")
        print(f"  Status: {result['status']}\n")

        # Step 3: Wait and check status
        print("[3/4] Waiting for pipeline to complete...")
        max_wait = 120  # 2 minutes
        wait_interval = 5
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

            response = await client.get(f"{server_url}/api/v1/sessions/{session_id}/status")
            status = response.json()

            stage = status.get("workflow_stage", "unknown")
            print(f"  [{elapsed}s] Stage: {stage}")

            if stage in ["completed", "failed"]:
                break

        # Step 4: Get final results
        print("\n[4/4] Retrieving results...")
        response = await client.get(f"{server_url}/api/v1/sessions/{session_id}/result")

        if response.status_code != 200:
            print(f"  ERROR: {response.status_code}")
            print(f"  Response: {response.text}")
            return

        results = response.json()

        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)

        print(f"\nSession ID: {results.get('session_id')}")
        print(f"Final Stage: {results.get('workflow_stage')}")
        print(f"Overall Status: {results.get('overall_status')}")

        # Check NWB file
        nwb_path = results.get("nwb_file_path")
        if nwb_path and Path(nwb_path).exists():
            size_mb = Path(nwb_path).stat().st_size / (1024 * 1024)
            print(f"\nNWB File:")
            print(f"  Path: {nwb_path}")
            print(f"  Size: {size_mb:.2f} MB")
            print(f"  Status: SUCCESS")
        else:
            print(f"\nNWB File: NOT FOUND")

        # Check validation report
        report_path = results.get("validation_report_path")
        if report_path and Path(report_path).exists():
            print(f"\nValidation Report:")
            print(f"  Path: {report_path}")

            with open(report_path) as f:
                report = json.load(f)
            print(f"  Metadata Completeness: {report.get('metadata_completeness_score', 0)}/100")
            print(f"  Best Practices Score: {report.get('best_practices_score', 0)}/100")
        else:
            print(f"\nValidation Report: NOT FOUND")

        print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_pipeline())
