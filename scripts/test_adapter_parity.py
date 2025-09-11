#!/usr/bin/env python3
"""Test runner for adapter parity verification.

This script runs comprehensive adapter parity tests to ensure that both MCP and HTTP
adapters provide identical functionality through different transport protocols.
"""

import asyncio
from pathlib import Path
import sys
import time
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agentic_neurodata_conversion.mcp_server.http_adapter import (  # noqa: E402
    HTTPAdapter,
)
from agentic_neurodata_conversion.mcp_server.mcp_adapter import MCPAdapter  # noqa: E402


class AdapterParityTester:
    """Comprehensive adapter parity testing suite."""

    def __init__(self):
        self.mcp_adapter = None
        self.http_adapter = None
        self.test_results = {}
        self.start_time = None

    async def setup(self):
        """Initialize both adapters for testing."""
        print("🔧 Setting up adapters for parity testing...")

        self.mcp_adapter = MCPAdapter()
        self.http_adapter = HTTPAdapter()

        await self.mcp_adapter.initialize()
        await self.http_adapter.initialize()

        print("✅ Both adapters initialized successfully")

    async def teardown(self):
        """Clean up adapters after testing."""
        print("🧹 Cleaning up adapters...")

        if self.mcp_adapter:
            await self.mcp_adapter.shutdown()
        if self.http_adapter:
            await self.http_adapter.shutdown()

        print("✅ Cleanup completed")

    async def test_initialization_parity(self) -> dict[str, Any]:
        """Test that both adapters initialize identically."""
        print("🧪 Testing initialization parity...")

        results = {"test_name": "initialization_parity", "passed": False, "details": {}}

        try:
            # Check service initialization
            mcp_initialized = self.mcp_adapter.conversion_service._initialized
            http_initialized = self.http_adapter.conversion_service._initialized

            results["details"]["mcp_initialized"] = mcp_initialized
            results["details"]["http_initialized"] = http_initialized
            results["details"]["initialization_match"] = (
                mcp_initialized == http_initialized
            )

            # Check tool system
            mcp_tools = len(self.mcp_adapter.tool_system.registry.list_tools())
            http_tools = len(self.http_adapter.tool_system.registry.list_tools())

            results["details"]["mcp_tool_count"] = mcp_tools
            results["details"]["http_tool_count"] = http_tools
            results["details"]["tool_count_match"] = mcp_tools == http_tools

            # Overall pass/fail
            results["passed"] = (
                mcp_initialized
                and http_initialized
                and mcp_tools == http_tools
                and mcp_tools > 0
            )

            if results["passed"]:
                print(f"  ✅ Initialization parity: PASSED ({mcp_tools} tools each)")
            else:
                print("  ❌ Initialization parity: FAILED")
                print(f"     MCP: initialized={mcp_initialized}, tools={mcp_tools}")
                print(f"     HTTP: initialized={http_initialized}, tools={http_tools}")

        except Exception as e:
            results["error"] = str(e)
            print(f"  ❌ Initialization parity: ERROR - {e}")

        return results

    async def test_tool_registration_parity(self) -> dict[str, Any]:
        """Test that tool registration is identical."""
        print("🧪 Testing tool registration parity...")

        results = {
            "test_name": "tool_registration_parity",
            "passed": False,
            "details": {},
        }

        try:
            mcp_tools = self.mcp_adapter.tool_system.registry.list_tools()
            http_tools = self.http_adapter.tool_system.registry.list_tools()

            # Compare tool names
            mcp_names = {tool.name for tool in mcp_tools}
            http_names = {tool.name for tool in http_tools}

            results["details"]["mcp_tool_names"] = sorted(mcp_names)
            results["details"]["http_tool_names"] = sorted(http_names)
            results["details"]["names_match"] = mcp_names == http_names

            # Compare tool categories
            mcp_categories = {tool.category.value for tool in mcp_tools}
            http_categories = {tool.category.value for tool in http_tools}

            results["details"]["categories_match"] = mcp_categories == http_categories

            # Compare tool configurations
            config_matches = []
            for mcp_tool in mcp_tools:
                http_tool = next(
                    (t for t in http_tools if t.name == mcp_tool.name), None
                )
                if http_tool:
                    config_match = (
                        mcp_tool.description == http_tool.description
                        and mcp_tool.timeout_seconds == http_tool.timeout_seconds
                        and len(mcp_tool.parameters) == len(http_tool.parameters)
                    )
                    config_matches.append(config_match)

            results["details"]["all_configs_match"] = all(config_matches)
            results["details"]["config_match_count"] = sum(config_matches)

            # Overall pass/fail
            results["passed"] = (
                results["details"]["names_match"]
                and results["details"]["categories_match"]
                and results["details"]["all_configs_match"]
            )

            if results["passed"]:
                print(f"  ✅ Tool registration parity: PASSED ({len(mcp_tools)} tools)")
            else:
                print("  ❌ Tool registration parity: FAILED")
                if not results["details"]["names_match"]:
                    print(f"     Tool names differ: MCP={mcp_names}, HTTP={http_names}")
                if not results["details"]["categories_match"]:
                    print(
                        f"     Categories differ: MCP={mcp_categories}, HTTP={http_categories}"
                    )
                if not results["details"]["all_configs_match"]:
                    print(
                        f"     Config matches: {sum(config_matches)}/{len(config_matches)}"
                    )

        except Exception as e:
            results["error"] = str(e)
            print(f"  ❌ Tool registration parity: ERROR - {e}")

        return results

    async def test_service_configuration_parity(self) -> dict[str, Any]:
        """Test that service configurations are identical."""
        print("🧪 Testing service configuration parity...")

        results = {
            "test_name": "service_configuration_parity",
            "passed": False,
            "details": {},
        }

        try:
            mcp_config = self.mcp_adapter.conversion_service.config
            http_config = self.http_adapter.conversion_service.config

            # Compare key configuration values
            config_comparisons = {
                "max_concurrent_sessions": mcp_config.max_concurrent_sessions
                == http_config.max_concurrent_sessions,
                "session_timeout_minutes": mcp_config.session_timeout_minutes
                == http_config.session_timeout_minutes,
                "enable_llm_features": mcp_config.enable_llm_features
                == http_config.enable_llm_features,
                "default_output_format": mcp_config.default_output_format
                == http_config.default_output_format,
            }

            results["details"]["config_comparisons"] = config_comparisons
            results["details"]["mcp_config"] = {
                "max_concurrent_sessions": mcp_config.max_concurrent_sessions,
                "session_timeout_minutes": mcp_config.session_timeout_minutes,
                "enable_llm_features": mcp_config.enable_llm_features,
                "default_output_format": mcp_config.default_output_format,
            }
            results["details"]["http_config"] = {
                "max_concurrent_sessions": http_config.max_concurrent_sessions,
                "session_timeout_minutes": http_config.session_timeout_minutes,
                "enable_llm_features": http_config.enable_llm_features,
                "default_output_format": http_config.default_output_format,
            }

            results["passed"] = all(config_comparisons.values())

            if results["passed"]:
                print("  ✅ Service configuration parity: PASSED")
            else:
                print("  ❌ Service configuration parity: FAILED")
                for key, match in config_comparisons.items():
                    if not match:
                        mcp_val = getattr(mcp_config, key)
                        http_val = getattr(http_config, key)
                        print(f"     {key}: MCP={mcp_val}, HTTP={http_val}")

        except Exception as e:
            results["error"] = str(e)
            print(f"  ❌ Service configuration parity: ERROR - {e}")

        return results

    async def test_agent_status_parity(self) -> dict[str, Any]:
        """Test that agent status reporting is identical."""
        print("🧪 Testing agent status parity...")

        results = {"test_name": "agent_status_parity", "passed": False, "details": {}}

        try:
            mcp_agents = await self.mcp_adapter.conversion_service.get_agent_status()
            http_agents = await self.http_adapter.conversion_service.get_agent_status()

            # Compare agent names
            mcp_agent_names = set(mcp_agents.keys())
            http_agent_names = set(http_agents.keys())

            results["details"]["mcp_agent_names"] = sorted(mcp_agent_names)
            results["details"]["http_agent_names"] = sorted(http_agent_names)
            results["details"]["agent_names_match"] = (
                mcp_agent_names == http_agent_names
            )

            # Compare agent statuses
            status_matches = []
            for agent_name in mcp_agent_names.intersection(http_agent_names):
                mcp_status = mcp_agents[agent_name].get("status")
                http_status = http_agents[agent_name].get("status")
                status_matches.append(mcp_status == http_status)

            results["details"]["status_matches"] = status_matches
            results["details"]["all_statuses_match"] = all(status_matches)

            results["passed"] = (
                results["details"]["agent_names_match"]
                and results["details"]["all_statuses_match"]
            )

            if results["passed"]:
                print(
                    f"  ✅ Agent status parity: PASSED ({len(mcp_agent_names)} agents)"
                )
            else:
                print("  ❌ Agent status parity: FAILED")
                if not results["details"]["agent_names_match"]:
                    print(
                        f"     Agent names differ: MCP={mcp_agent_names}, HTTP={http_agent_names}"
                    )
                if not results["details"]["all_statuses_match"]:
                    print(
                        f"     Status matches: {sum(status_matches)}/{len(status_matches)}"
                    )

        except Exception as e:
            results["error"] = str(e)
            print(f"  ❌ Agent status parity: ERROR - {e}")

        return results

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all parity tests and return comprehensive results."""
        print("🚀 Starting comprehensive adapter parity testing...")
        print("=" * 60)

        self.start_time = time.time()

        # Test suite
        test_methods = [
            self.test_initialization_parity,
            self.test_tool_registration_parity,
            self.test_service_configuration_parity,
            self.test_agent_status_parity,
        ]

        all_results = []
        passed_count = 0

        for test_method in test_methods:
            try:
                result = await test_method()
                all_results.append(result)
                if result.get("passed", False):
                    passed_count += 1
            except Exception as e:
                error_result = {
                    "test_name": test_method.__name__,
                    "passed": False,
                    "error": str(e),
                }
                all_results.append(error_result)
                print(f"  ❌ {test_method.__name__}: EXCEPTION - {e}")

        # Summary
        total_tests = len(test_methods)
        execution_time = time.time() - self.start_time

        print("=" * 60)
        print("📊 Test Summary:")
        print(f"   Total tests: {total_tests}")
        print(f"   Passed: {passed_count}")
        print(f"   Failed: {total_tests - passed_count}")
        print(f"   Success rate: {passed_count / total_tests * 100:.1f}%")
        print(f"   Execution time: {execution_time:.2f}s")

        overall_success = passed_count == total_tests

        if overall_success:
            print(
                "🎉 ALL PARITY TESTS PASSED - Adapters provide identical functionality!"
            )
        else:
            print("⚠️  SOME PARITY TESTS FAILED - Adapters may have differences")

        return {
            "overall_success": overall_success,
            "passed_count": passed_count,
            "total_count": total_tests,
            "success_rate": passed_count / total_tests,
            "execution_time": execution_time,
            "individual_results": all_results,
        }


async def main():
    """Main entry point for adapter parity testing."""
    tester = AdapterParityTester()

    try:
        await tester.setup()
        results = await tester.run_all_tests()

        # Exit with appropriate code
        exit_code = 0 if results["overall_success"] else 1
        sys.exit(exit_code)

    except Exception as e:
        print(f"💥 Fatal error during parity testing: {e}")
        sys.exit(2)

    finally:
        await tester.teardown()


if __name__ == "__main__":
    asyncio.run(main())
