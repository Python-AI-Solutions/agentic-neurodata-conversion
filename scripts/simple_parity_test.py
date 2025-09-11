#!/usr/bin/env python3
"""Simple adapter parity test that doesn't require pixi environment setup.

This script provides a basic verification that both MCP and HTTP adapters
can be imported and initialized without errors.
"""

import asyncio
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_basic_imports():
    """Test that both adapters can be imported."""
    print("🧪 Testing basic imports...")

    try:
        from agentic_neurodata_conversion.mcp_server.mcp_adapter import (
            MCPAdapter,  # noqa: F401
        )

        print("  ✅ MCPAdapter imported successfully")
    except ImportError as e:
        print(f"  ❌ MCPAdapter import failed: {e}")
        return False

    try:
        from agentic_neurodata_conversion.mcp_server.http_adapter import (
            HTTPAdapter,  # noqa: F401
        )

        print("  ✅ HTTPAdapter imported successfully")
    except ImportError as e:
        print(f"  ❌ HTTPAdapter import failed: {e}")
        return False

    return True


async def test_basic_initialization():
    """Test that both adapters can be initialized."""
    print("🧪 Testing basic initialization...")

    try:
        from agentic_neurodata_conversion.mcp_server.http_adapter import HTTPAdapter
        from agentic_neurodata_conversion.mcp_server.mcp_adapter import MCPAdapter

        # Test MCP adapter
        MCPAdapter()
        print("  ✅ MCPAdapter created successfully")

        # Test HTTP adapter
        HTTPAdapter()
        print("  ✅ HTTPAdapter created successfully")

        return True

    except Exception as e:
        print(f"  ❌ Adapter initialization failed: {e}")
        return False


async def test_adapter_structure():
    """Test that both adapters have the expected structure."""
    print("🧪 Testing adapter structure...")

    try:
        from agentic_neurodata_conversion.mcp_server.http_adapter import HTTPAdapter
        from agentic_neurodata_conversion.mcp_server.mcp_adapter import MCPAdapter

        mcp_adapter = MCPAdapter()
        http_adapter = HTTPAdapter()

        # Check that both have conversion_service attribute
        assert hasattr(mcp_adapter, "conversion_service"), (
            "MCP adapter missing conversion_service"
        )
        assert hasattr(http_adapter, "conversion_service"), (
            "HTTP adapter missing conversion_service"
        )
        print("  ✅ Both adapters have conversion_service attribute")

        # Check that both have initialize method
        assert hasattr(mcp_adapter, "initialize"), (
            "MCP adapter missing initialize method"
        )
        assert hasattr(http_adapter, "initialize"), (
            "HTTP adapter missing initialize method"
        )
        print("  ✅ Both adapters have initialize method")

        # Check that both have shutdown method
        assert hasattr(mcp_adapter, "shutdown"), "MCP adapter missing shutdown method"
        assert hasattr(http_adapter, "shutdown"), "HTTP adapter missing shutdown method"
        print("  ✅ Both adapters have shutdown method")

        return True

    except Exception as e:
        print(f"  ❌ Adapter structure test failed: {e}")
        return False


async def test_core_service_import():
    """Test that core service components can be imported."""
    print("🧪 Testing core service imports...")

    try:
        from agentic_neurodata_conversion.core.service import (
            ConversionService,  # noqa: F401
        )

        print("  ✅ ConversionService imported successfully")
    except ImportError as e:
        print(f"  ❌ ConversionService import failed: {e}")
        return False

    try:
        from agentic_neurodata_conversion.core.tools import ToolSystem  # noqa: F401

        print("  ✅ ToolSystem imported successfully")
    except ImportError as e:
        print(f"  ❌ ToolSystem import failed: {e}")
        return False

    return True


async def main():
    """Run all basic parity tests."""
    print("🚀 Starting basic adapter parity verification...")
    print("=" * 60)

    tests = [
        test_basic_imports,
        test_core_service_import,
        test_basic_initialization,
        test_adapter_structure,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            print()
        except Exception as e:
            print(f"  💥 Test {test.__name__} crashed: {e}")
            print()

    print("=" * 60)
    print("📊 Basic Verification Summary:")
    print(f"   Total tests: {total}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {total - passed}")
    print(f"   Success rate: {passed / total * 100:.1f}%")

    if passed == total:
        print("🎉 ALL BASIC TESTS PASSED - Adapter structure looks good!")
        return 0
    else:
        print("⚠️  SOME BASIC TESTS FAILED - Check imports and structure")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
