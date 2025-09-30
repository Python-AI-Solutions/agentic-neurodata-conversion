#!/usr/bin/env python3
"""
Direct test of Knowledge Graph Systems core functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_constitutional_compliance():
    """Test constitutional compliance features."""
    print("🏛️  Testing Constitutional Compliance")
    print("=" * 40)

    from knowledge_graph.models.dataset import Dataset

    # Test 1: Valid dataset creation
    print("1. Creating valid dataset...")
    try:
        dataset = Dataset(
            title="Test Dataset",
            description="Constitutional compliance test",
            nwb_files=["session_001.nwb", "session_002.nwb"]
        )
        print(f"   ✅ Valid dataset created: {dataset.title}")
        print(f"   ✅ Dataset ID: {dataset.dataset_id}")
        print(f"   ✅ NWB files: {len(dataset.nwb_files)} (max 100)")
        print(f"   ✅ RDF type: {dataset.rdf_type}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False

    # Test 2: Constitutional violation (>100 NWB files)
    print("\n2. Testing constitutional violation (101 NWB files)...")
    try:
        bad_dataset = Dataset(
            title="Bad Dataset",
            description="Should violate 100-file limit",
            nwb_files=[f"file_{i:03d}.nwb" for i in range(101)]
        )
        print("   ❌ Constitutional violation not caught!")
        return False
    except ValueError as e:
        if "100 NWB files" in str(e) and "constitutional" in str(e):
            print("   ✅ Constitutional compliance enforced!")
            print(f"   ✅ Error: {e}")
        else:
            print(f"   ❌ Wrong error: {e}")
            return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

    return True

def test_semantic_web_standards():
    """Test W3C semantic web standards."""
    print("\n🌐 Testing W3C Semantic Web Standards")
    print("=" * 40)

    from knowledge_graph.models.dataset import Dataset
    from knowledge_graph.services.triple_store import TripleStoreService

    # Test RDF generation
    print("1. Testing RDF generation...")
    dataset = Dataset(
        title="Semantic Web Test",
        description="W3C standards compliance test",
        nwb_files=["semantic_test.nwb"]
    )

    rdf_dict = dataset.to_rdf_dict()
    print("   ✅ RDF dictionary generated")

    required_fields = ["@id", "@type", "kg:title"]
    for field in required_fields:
        if field in rdf_dict:
            print(f"   ✅ {field}: {rdf_dict[field]}")
        else:
            print(f"   ❌ Missing {field}")
            return False

    # Test triple store
    print("\n2. Testing SPARQL triple store...")
    try:
        store = TripleStoreService()
        print("   ✅ Triple store initialized")
        print(f"   ✅ Namespaces: {len(dict(store.graph.namespaces()))}")

        # Test sample queries
        samples = store.get_sample_queries()
        print(f"   ✅ Sample queries: {len(samples)}")
        for name in samples:
            print(f"     - {name}")

    except Exception as e:
        print(f"   ❌ Triple store failed: {e}")
        return False

    return True

def test_fastapi_application():
    """Test FastAPI application setup."""
    print("\n⚡ Testing FastAPI Application")
    print("=" * 40)

    try:
        from knowledge_graph.app import app
        print("   ✅ FastAPI app imported")
        print(f"   ✅ App title: {app.title}")
        print(f"   ✅ App version: {app.version}")

        # Check routes
        routes = [route.path for route in app.routes]
        expected_routes = ["/", "/health", "/sparql", "/datasets"]

        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"   ✅ Route {route} registered")
            else:
                print(f"   ❌ Route {route} missing")
                return False

    except Exception as e:
        print(f"   ❌ FastAPI app failed: {e}")
        return False

    return True

def test_mcp_integration():
    """Test MCP server integration."""
    print("\n🔧 Testing MCP Integration")
    print("=" * 40)

    try:
        from mcp_server.knowledge_graph_server import mcp_app
        print("   ✅ MCP server imported")
        print(f"   ✅ MCP app title: {mcp_app.title}")

        # Check MCP routes
        mcp_routes = [route.path for route in mcp_app.routes]
        expected_mcp_routes = ["/mcp/tools/sparql_query", "/mcp/tools/enrich_metadata"]

        for route in expected_mcp_routes:
            if route in mcp_routes:
                print(f"   ✅ MCP route {route} registered")
            else:
                print(f"   ❌ MCP route {route} missing")
                return False

    except Exception as e:
        print(f"   ❌ MCP integration failed: {e}")
        return False

    return True

def main():
    """Run all tests."""
    print("🧪 Knowledge Graph Systems - Direct Functionality Test")
    print("=" * 60)

    tests = [
        test_constitutional_compliance,
        test_semantic_web_standards,
        test_fastapi_application,
        test_mcp_integration
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"   ❌ Test crashed: {e}")

    print("\n" + "=" * 60)
    print(f"🏆 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ Constitutional compliance verified")
        print("✅ W3C semantic web standards integrated")
        print("✅ FastAPI application ready")
        print("✅ MCP server integration working")
        print("\n🚀 Your Knowledge Graph Systems implementation is working!")
        print("\n📖 Next steps:")
        print("  1. Visit http://localhost:8000/docs for API documentation")
        print("  2. Install dependencies: pixi install")
        print("  3. Run tests: pixi run test")
        print("  4. Start server: pixi run server")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)