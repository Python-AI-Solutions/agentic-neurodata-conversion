"""Quick test to verify logging is working."""

import asyncio
import httpx
import sys

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test():
    """Quick test of session initialization with logging."""

    server_url = "http://localhost:8000"
    dataset_path = "./real_data"

    print("="*80)
    print("QUICK PIPELINE TEST - Session Initialization")
    print("="*80)
    print()

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Check health
        print("[1/2] Checking server health...")
        try:
            response = await client.get(f"{server_url}/health")
            health = response.json()
            print(f"  ✓ Status: {health['status']}")
            print(f"  ✓ Agents: {len(health['agents_registered'])} registered")
            print(f"  ✓ Redis: {'connected' if health['redis_connected'] else 'disconnected'}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return

        # Initialize session
        print()
        print("[2/2] Initializing session...")
        print("  (Watch the service logs for our detailed logging!)")
        print()

        try:
            response = await client.post(
                f"{server_url}/api/v1/sessions/initialize",
                json={"dataset_path": dataset_path},
                timeout=300.0
            )

            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ SUCCESS!")
                print(f"  ✓ Session ID: {result.get('session_id')}")
                print(f"  ✓ Stage: {result.get('workflow_stage')}")
                print(f"  ✓ Message: {result.get('message')}")
            else:
                print(f"  ✗ FAILED: {response.status_code}")
                print(f"  ✗ Response: {response.text}")

        except httpx.ReadTimeout as e:
            print(f"  ✗ TIMEOUT after 300s")
            print(f"  ✗ This is the issue we're debugging!")
            print(f"  ✗ Check the service logs for where it got stuck")
        except Exception as e:
            print(f"  ✗ Error: {type(e).__name__}: {e}")

    print()
    print("="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
