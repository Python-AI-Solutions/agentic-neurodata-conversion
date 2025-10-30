"""Detailed end-to-end pipeline test with progress monitoring."""

import asyncio
import httpx
import json
from pathlib import Path
from datetime import datetime


async def test_pipeline():
    """Test the full pipeline with detailed progress monitoring."""

    server_url = "http://localhost:8000"
    dataset_path = "./tests/data/synthetic_openephys"

    print("\n" + "="*80)
    print("MULTI-AGENT NWB CONVERSION PIPELINE - END-TO-END TEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Check server health
        print("[STEP 1/5] Checking server health...")
        response = await client.get(f"{server_url}/health")
        health = response.json()
        print(f"  - Status: {health['status']}")
        print(f"  - Agents: {', '.join(health['agents_registered'])}")
        print(f"  - Redis: {'Connected' if health['redis_connected'] else 'Disconnected'}")
        print()

        # Step 2: Initialize session
        print("[STEP 2/5] Initializing session with conversation agent...")
        print(f"  - Dataset: {dataset_path}")
        response = await client.post(
            f"{server_url}/api/v1/sessions/initialize",
            json={"dataset_path": dataset_path}
        )

        if response.status_code != 200:
            print(f"  ERROR: {response.status_code}")
            print(f"  Response: {response.text}")
            return

        result = response.json()
        session_id = result.get("session_id")
        print(f"  - Session ID: {session_id}")
        print(f"  - Response: {result}")
        print()

        # Step 3: Monitor progress
        print("[STEP 3/5] Monitoring pipeline progress...")
        max_wait = 120  # 2 minutes
        wait_interval = 3
        elapsed = 0
        last_stage = None

        while elapsed < max_wait:
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

            response = await client.get(f"{server_url}/api/v1/sessions/{session_id}/status")

            if response.status_code != 200:
                print(f"  [{elapsed}s] ERROR: Cannot get status ({response.status_code})")
                continue

            status = response.json()
            stage = status.get("workflow_stage", "unknown")
            current_agent = status.get("current_agent", "none")

            if stage != last_stage:
                print(f"  [{elapsed}s] Stage: {stage.upper()} | Agent: {current_agent}")
                last_stage = stage

            if stage in ["completed", "failed"]:
                print(f"  - Final stage reached: {stage}")
                break

        print()

        # Step 4: Get final results
        print("[STEP 4/5] Retrieving final results...")
        response = await client.get(f"{server_url}/api/v1/sessions/{session_id}/result")

        if response.status_code != 200:
            print(f"  ERROR: {response.status_code}")
            print(f"  Response: {response.text}")
            return

        results = response.json()

        print("\n" + "="*80)
        print("PIPELINE RESULTS")
        print("="*80)

        print(f"\nSession Details:")
        print(f"  - Session ID: {results.get('session_id', 'N/A')}")
        print(f"  - Final Stage: {results.get('workflow_stage', 'N/A')}")
        print(f"  - Overall Status: {results.get('overall_status', 'N/A')}")

        # Dataset Info
        dataset_info = results.get("dataset_info", {})
        if dataset_info:
            print(f"\nDataset Information:")
            print(f"  - Format: {dataset_info.get('format', 'N/A')}")
            print(f"  - Path: {dataset_info.get('dataset_path', 'N/A')}")
            print(f"  - Files: {dataset_info.get('file_count', 0)}")
            print(f"  - Size: {dataset_info.get('total_size_bytes', 0) / (1024*1024):.2f} MB")

        # Metadata
        metadata = results.get("metadata", {})
        if metadata:
            print(f"\nExtracted Metadata:")
            print(f"  - Subject ID: {metadata.get('subject_id', 'N/A')}")
            print(f"  - Session ID: {metadata.get('session_id', 'N/A')}")
            print(f"  - Lab: {metadata.get('lab', 'N/A')}")
            print(f"  - Institution: {metadata.get('institution', 'N/A')}")

        # Conversion Results
        conversion = results.get("conversion_results", {})
        if conversion:
            print(f"\nConversion Results:")
            print(f"  - Status: {conversion.get('status', 'N/A')}")
            print(f"  - Duration: {conversion.get('conversion_duration_seconds', 0):.2f}s")

        # Check NWB file
        nwb_path = results.get("nwb_file_path")
        print(f"\nNWB File:")
        if nwb_path and Path(nwb_path).exists():
            size_mb = Path(nwb_path).stat().st_size / (1024 * 1024)
            print(f"  - Path: {nwb_path}")
            print(f"  - Size: {size_mb:.2f} MB")
            print(f"  - Status: ✓ SUCCESS")
        else:
            print(f"  - Status: ✗ NOT FOUND")
            if nwb_path:
                print(f"  - Expected path: {nwb_path}")

        # Check validation report
        report_path = results.get("validation_report_path")
        print(f"\nValidation Report:")
        if report_path and Path(report_path).exists():
            print(f"  - Path: {report_path}")

            try:
                with open(report_path) as f:
                    report = json.load(f)
                print(f"  - Metadata Completeness: {report.get('metadata_completeness_score', 0)}/100")
                print(f"  - Best Practices: {report.get('best_practices_score', 0)}/100")
                print(f"  - Status: ✓ SUCCESS")
            except Exception as e:
                print(f"  - Error reading report: {e}")
        else:
            print(f"  - Status: ✗ NOT FOUND")
            if report_path:
                print(f"  - Expected path: {report_path}")

        # Validation Results
        validation = results.get("validation_results", {})
        if validation:
            print(f"\nValidation Summary:")
            print(f"  - Status: {validation.get('status', 'N/A')}")
            issues = validation.get('issues', [])
            if issues:
                print(f"  - Issues found: {len(issues)}")
                for issue in issues[:3]:  # Show first 3
                    print(f"    - [{issue.get('severity', 'UNKNOWN')}] {issue.get('message', 'No message')}")
                if len(issues) > 3:
                    print(f"    ... and {len(issues) - 3} more")
            else:
                print(f"  - Issues: None ✓")

        print("\n" + "="*80)
        print(f"TEST COMPLETED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_pipeline())
