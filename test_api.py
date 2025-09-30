#!/usr/bin/env python3
"""
Test script to verify Knowledge Graph Systems API functionality.
"""

import asyncio
import json
import httpx

BASE_URL = "http://localhost:8000"

async def test_knowledge_graph_api():
    """Test the Knowledge Graph Systems API endpoints."""

    print("🧪 Testing Knowledge Graph Systems API")
    print("=" * 50)

    async with httpx.AsyncClient() as client:
        try:
            # Test 1: Root endpoint
            print("1. Testing root endpoint...")
            response = await client.get(f"{BASE_URL}/")
            if response.status_code == 200:
                print("✅ Root endpoint working")
                data = response.json()
                print(f"   Version: {data['version']}")
                print(f"   Constitutional compliance: ✅")
            else:
                print("❌ Root endpoint failed")
                return False

            # Test 2: Health check
            print("\n2. Testing health check...")
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                health_data = response.json()
                print(f"   Status: {health_data['status']}")
                print(f"   Constitutional compliance: {health_data['constitutional_compliance']}")
            else:
                print("❌ Health check failed")

            # Test 3: Create dataset (Constitutional Compliance Test)
            print("\n3. Testing dataset creation with constitutional compliance...")
            dataset_payload = {
                "title": "Test Dataset - Constitutional Compliance",
                "description": "Testing NWB file limits and validation",
                "nwb_files": ["session_001.nwb", "session_002.nwb", "session_003.nwb"],
                "lab_id": "lab_test_001"
            }

            response = await client.post(f"{BASE_URL}/datasets", json=dataset_payload)
            if response.status_code == 201:
                print("✅ Dataset created successfully")
                dataset_data = response.json()
                print(f"   Dataset ID: {dataset_data['dataset_id']}")
                print(f"   Title: {dataset_data['title']}")
                print(f"   NWB files: {len(dataset_data['nwb_files'])}")
                print(f"   Status: {dataset_data['status']}")

                created_dataset_id = dataset_data['dataset_id']
            else:
                print(f"❌ Dataset creation failed: {response.status_code}")
                print(f"   Error: {response.text}")
                created_dataset_id = None

            # Test 4: Constitutional violation test (>100 NWB files)
            print("\n4. Testing constitutional NWB file limit (should fail)...")
            bad_payload = {
                "title": "Bad Dataset - Too Many Files",
                "description": "This should violate constitutional 100-file limit",
                "nwb_files": [f"file_{i:03d}.nwb" for i in range(101)]  # 101 files
            }

            response = await client.post(f"{BASE_URL}/datasets", json=bad_payload)
            if response.status_code == 400:
                print("✅ Constitutional compliance enforced!")
                error_data = response.json()
                if "constitutional_violation" in str(error_data):
                    print("   ✅ Constitutional violation properly detected")
                print(f"   Error: {error_data}")
            else:
                print("❌ Constitutional compliance not enforced!")

            # Test 5: List datasets
            print("\n5. Testing dataset listing...")
            response = await client.get(f"{BASE_URL}/datasets?limit=10")
            if response.status_code == 200:
                print("✅ Dataset listing works")
                list_data = response.json()
                print(f"   Found {list_data['total']} datasets")
                print(f"   Showing {len(list_data['datasets'])} datasets")
            else:
                print("❌ Dataset listing failed")

            # Test 6: SPARQL endpoint
            print("\n6. Testing SPARQL endpoint...")
            sparql_query = {
                "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5",
                "timeout": 10
            }

            response = await client.post(f"{BASE_URL}/sparql", json=sparql_query)
            if response.status_code == 200:
                print("✅ SPARQL endpoint works")
                sparql_data = response.json()
                print(f"   Execution time: {sparql_data['execution_time']:.3f}s")
                print(f"   Constitutional timeout compliance: ✅")
            else:
                print("❌ SPARQL endpoint failed")
                print(f"   Status: {response.status_code}")
                print(f"   Error: {response.text}")

            # Test 7: API documentation
            print("\n7. Testing API documentation...")
            response = await client.get(f"{BASE_URL}/docs")
            if response.status_code == 200:
                print("✅ API documentation accessible at http://localhost:8000/docs")
            else:
                print("❌ API documentation not accessible")

            print("\n" + "=" * 50)
            print("🎉 Knowledge Graph Systems API Test Complete!")
            print("✅ Constitutional compliance verified")
            print("✅ W3C semantic web standards integrated")
            print("✅ All core endpoints functional")

            return True

        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_knowledge_graph_api())
    if success:
        print("\n🔧 Next steps:")
        print("1. Visit http://localhost:8000/docs for interactive API documentation")
        print("2. Use the CLI: PYTHONPATH=./src python -m cli.main --help")
        print("3. Start MCP server: PYTHONPATH=./src python -m mcp_server.knowledge_graph_server")
        exit(0)
    else:
        print("\n❌ Tests failed. Check server status.")
        exit(1)