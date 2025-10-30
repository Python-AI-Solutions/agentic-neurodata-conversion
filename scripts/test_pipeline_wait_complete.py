"""Test pipeline and wait for complete results."""

import asyncio
import httpx
import json
from pathlib import Path
from datetime import datetime
import sys


async def test_pipeline_complete():
    """Test pipeline and wait for completion with proper error handling."""

    server_url = "http://localhost:8000"
    dataset_path = "./tests/data/synthetic_openephys"

    print("\n" + "="*80)
    print("PIPELINE TEST - WAIT FOR COMPLETION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    # Use longer timeout and retry settings
    timeout = httpx.Timeout(600.0, connect=10.0)  # 10 minute timeout

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Step 1: Check health
        print("[1/4] Checking server health...")
        try:
            response = await client.get(f"{server_url}/health")
            health = response.json()
            print(f"  [OK] Status: {health['status']}")
            print(f"  [OK] Agents: {len(health['agents_registered'])} registered")
        except Exception as e:
            print(f"  [ERROR] {e}")
            return

        # Step 2: Initialize session
        print("\n[2/4] Initializing session...")
        try:
            response = await client.post(
                f"{server_url}/api/v1/sessions/initialize",
                json={"dataset_path": dataset_path}
            )

            if response.status_code != 200:
                print(f"  [ERROR] ERROR: {response.status_code} - {response.text}")
                return

            result = response.json()
            session_id = result.get("session_id")
            print(f"  [OK] Session created: {session_id}")
        except Exception as e:
            print(f"  [ERROR] ERROR: {e}")
            return

        # Step 3: Poll for completion (with long timeout)
        print("\n[3/4] Waiting for pipeline completion...")
        print("  (This may take several minutes for LLM calls and data conversion)")

        max_wait = 600  # 10 minutes
        poll_interval = 5
        elapsed = 0
        last_stage = None

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            try:
                # Set a shorter timeout just for status check
                status_client = httpx.AsyncClient(timeout=30.0)
                response = await status_client.get(
                    f"{server_url}/api/v1/sessions/{session_id}/status"
                )
                await status_client.aclose()

                if response.status_code != 200:
                    print(f"  [{elapsed}s] Status check failed: {response.status_code}")
                    continue

                status = response.json()
                stage = status.get("workflow_stage", "unknown")

                if stage != last_stage:
                    print(f"  [{elapsed}s] Stage: {stage}")
                    last_stage = stage

                # Check if completed or failed
                if stage in ["completed", "failed"]:
                    print(f"  [OK] Pipeline finished at stage: {stage}")
                    break

            except httpx.ReadTimeout:
                print(f"  [{elapsed}s] Status check timed out (server busy), retrying...")
                continue
            except Exception as e:
                print(f"  [{elapsed}s] Error checking status: {type(e).__name__}")
                continue

        if elapsed >= max_wait:
            print(f"  [WARN] Timeout after {max_wait}s - checking final results anyway...")

        # Step 4: Get results (with retry)
        print("\n[4/4] Retrieving final results...")

        for attempt in range(3):
            try:
                result_client = httpx.AsyncClient(timeout=60.0)
                response = await result_client.get(
                    f"{server_url}/api/v1/sessions/{session_id}/result"
                )
                await result_client.aclose()

                if response.status_code == 200:
                    results = response.json()
                    break
                else:
                    print(f"  Attempt {attempt + 1}/3 failed: {response.status_code}")
                    if attempt < 2:
                        await asyncio.sleep(5)
            except Exception as e:
                print(f"  Attempt {attempt + 1}/3 error: {type(e).__name__}: {e}")
                if attempt < 2:
                    await asyncio.sleep(5)
        else:
            print("  [ERROR] Could not retrieve results after 3 attempts")
            return

        # Display results
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)

        print(f"\nSession: {results.get('session_id')}")
        print(f"Stage: {results.get('workflow_stage')}")
        print(f"Status: {results.get('overall_status')}")

        # Dataset info
        dataset_info = results.get("dataset_info", {})
        if dataset_info:
            print(f"\nDataset:")
            print(f"  Format: {dataset_info.get('format')}")
            print(f"  Files: {dataset_info.get('file_count')}")
            print(f"  Size: {dataset_info.get('total_size_bytes', 0) / (1024*1024):.2f} MB")

        # NWB file
        nwb_path = results.get("nwb_file_path")
        print(f"\nNWB File:")
        if nwb_path and Path(nwb_path).exists():
            size_mb = Path(nwb_path).stat().st_size / (1024 * 1024)
            print(f"  [OK] Generated: {nwb_path}")
            print(f"  [OK] Size: {size_mb:.2f} MB")
        else:
            print(f"  [ERROR] Not found")
            if nwb_path:
                print(f"    Expected: {nwb_path}")

        # Validation report
        report_path = results.get("validation_report_path")
        print(f"\nValidation Report:")
        if report_path and Path(report_path).exists():
            with open(report_path) as f:
                report = json.load(f)
            print(f"  [OK] Generated: {report_path}")
            print(f"  [OK] Metadata Score: {report.get('metadata_completeness_score', 0)}/100")
            print(f"  [OK] Best Practices: {report.get('best_practices_score', 0)}/100")
        else:
            print(f"  [ERROR] Not found")

        print("\n" + "="*80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_pipeline_complete())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)
