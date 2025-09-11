#!/usr/bin/env python3
"""
Run comprehensive integration tests for the Agentic Neurodata Conversion system.

This script runs both the custom integration test and pytest integration tests
to validate that all components work together correctly.

Usage:
    pixi run python scripts/run_integration_tests.py
    pixi run python scripts/run_integration_tests.py --verbose
    pixi run python scripts/run_integration_tests.py --quick
"""

import argparse
import asyncio
import logging
from pathlib import Path
import subprocess
import sys

# Import our custom integration tester
from integration_test import IntegrationTester


class IntegrationTestRunner:
    """
    Comprehensive integration test runner that validates the complete system.
    """

    def __init__(self, verbose: bool = False, quick: bool = False):
        """
        Initialize the test runner.

        Args:
            verbose: Enable verbose output
            quick: Run only quick tests
        """
        self.verbose = verbose
        self.quick = quick
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the test runner."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        return logging.getLogger(__name__)

    async def run_custom_integration_tests(self) -> bool:
        """
        Run custom integration tests.

        Returns:
            True if all tests passed, False otherwise.
        """
        self.logger.info("Running custom integration tests...")

        try:
            tester = IntegrationTester()
            success = await tester.run_integration_test()
            return success
        except Exception as e:
            self.logger.error(f"Custom integration tests failed: {e}")
            return False

    def run_pytest_integration_tests(self) -> bool:
        """
        Run pytest integration tests.

        Returns:
            True if all tests passed, False otherwise.
        """
        self.logger.info("Running pytest integration tests...")

        try:
            # Build pytest command
            cmd = ["pixi", "run", "pytest"]

            # Add test markers
            if self.quick:
                cmd.extend(["-m", "integration and not slow"])
            else:
                cmd.extend(["-m", "integration"])

            # Add verbosity
            if self.verbose:
                cmd.append("-v")
            else:
                cmd.append("-q")

            # Add specific test files
            test_files = [
                "tests/integration/test_client_server_integration.py",
                "tests/integration/test_mcp_server_integration.py",
            ]

            # Only include existing test files
            existing_files = [f for f in test_files if Path(f).exists()]
            cmd.extend(existing_files)

            # Add coverage if not quick
            if not self.quick:
                cmd.extend(
                    ["--cov=agentic_neurodata_conversion", "--cov-report=term-missing"]
                )

            self.logger.info(f"Running command: {' '.join(cmd)}")

            # Run pytest
            result = subprocess.run(cmd, capture_output=True, text=True)

            if self.verbose:
                self.logger.info(f"Pytest stdout:\n{result.stdout}")
                if result.stderr:
                    self.logger.warning(f"Pytest stderr:\n{result.stderr}")

            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Pytest integration tests failed: {e}")
            return False

    def run_client_validation_tests(self) -> bool:
        """
        Run client example validation tests.

        Returns:
            True if all validations passed, False otherwise.
        """
        self.logger.info("Running client validation tests...")

        try:
            # Test that client examples exist and have valid syntax
            client_dir = Path("examples/python_client")
            if not client_dir.exists():
                self.logger.error("Client examples directory not found")
                return False

            client_files = [
                "simple_client.py",
                "workflow_example.py",
            ]

            for client_file in client_files:
                file_path = client_dir / client_file
                if not file_path.exists():
                    self.logger.error(f"Client example not found: {client_file}")
                    return False

                # Test syntax
                try:
                    with open(file_path) as f:
                        code = f.read()
                    compile(code, str(file_path), "exec")
                    self.logger.info(f"✓ {client_file} syntax valid")
                except SyntaxError as e:
                    self.logger.error(f"✗ {client_file} syntax error: {e}")
                    return False

            # Test that clients can be imported (basic validation)
            try:
                import sys

                sys.path.insert(0, str(client_dir.parent))

                from python_client.simple_client import SimpleMCPClient
                from python_client.workflow_example import MCPWorkflowClient

                # Test basic initialization
                SimpleMCPClient()
                MCPWorkflowClient()

                self.logger.info("✓ Client examples can be imported and initialized")
                return True

            except Exception as e:
                self.logger.error(f"✗ Client import/initialization failed: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Client validation tests failed: {e}")
            return False

    def run_system_health_check(self) -> bool:
        """
        Run system health check to verify all components are available.

        Returns:
            True if system is healthy, False otherwise.
        """
        self.logger.info("Running system health check...")

        try:
            # Check core modules can be imported
            core_modules = [
                "agentic_neurodata_conversion.core.config",
                "agentic_neurodata_conversion.mcp_server.server",
                "agentic_neurodata_conversion.agents.base",
                "agentic_neurodata_conversion.mcp_server.tools.basic_tools",
            ]

            for module_name in core_modules:
                try:
                    __import__(module_name)
                    self.logger.info(f"✓ {module_name} imported successfully")
                except ImportError as e:
                    self.logger.error(f"✗ {module_name} import failed: {e}")
                    return False

            # Check that basic tools are registered
            from agentic_neurodata_conversion.mcp_server.server import mcp
            from agentic_neurodata_conversion.mcp_server.tools import (
                basic_tools,  # noqa: F401
            )

            tools = mcp.list_tools()
            expected_tools = ["server_status", "list_tools", "pipeline_state", "echo"]

            for tool_name in expected_tools:
                if tool_name in tools:
                    self.logger.info(f"✓ Tool {tool_name} registered")
                else:
                    self.logger.error(f"✗ Tool {tool_name} not registered")
                    return False

            self.logger.info("✓ System health check passed")
            return True

        except Exception as e:
            self.logger.error(f"System health check failed: {e}")
            return False

    def run_pre_commit_check(self) -> bool:
        """
        Run pre-commit checks to ensure code quality.

        Returns:
            True if pre-commit checks passed, False otherwise.
        """
        if self.quick:
            self.logger.info("Skipping pre-commit check in quick mode")
            return True

        self.logger.info("Running pre-commit checks...")

        try:
            cmd = ["pixi", "run", "pre-commit", "--", "--all-files"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info("✓ Pre-commit checks passed")
                return True
            else:
                self.logger.error("✗ Pre-commit checks failed")
                if self.verbose:
                    self.logger.error(f"Pre-commit output:\n{result.stdout}")
                    if result.stderr:
                        self.logger.error(f"Pre-commit stderr:\n{result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Pre-commit check failed: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """
        Run all integration tests and validations.

        Returns:
            True if all tests passed, False otherwise.
        """
        self.logger.info("=" * 80)
        self.logger.info(
            "AGENTIC NEURODATA CONVERSION - COMPREHENSIVE INTEGRATION TESTS"
        )
        self.logger.info("=" * 80)

        test_results = {}

        # 1. System health check
        self.logger.info("\n--- System Health Check ---")
        test_results["health_check"] = self.run_system_health_check()

        # 2. Pre-commit checks
        self.logger.info("\n--- Pre-commit Checks ---")
        test_results["pre_commit"] = self.run_pre_commit_check()

        # 3. Client validation
        self.logger.info("\n--- Client Validation ---")
        test_results["client_validation"] = self.run_client_validation_tests()

        # 4. Custom integration tests
        self.logger.info("\n--- Custom Integration Tests ---")
        test_results["custom_integration"] = await self.run_custom_integration_tests()

        # 5. Pytest integration tests
        self.logger.info("\n--- Pytest Integration Tests ---")
        test_results["pytest_integration"] = self.run_pytest_integration_tests()

        # Results summary
        self.logger.info("\n" + "=" * 80)
        self.logger.info("INTEGRATION TEST RESULTS SUMMARY")
        self.logger.info("=" * 80)

        passed_tests = 0
        total_tests = len(test_results)

        for test_name, result in test_results.items():
            status = "✓ PASSED" if result else "✗ FAILED"
            self.logger.info(f"{test_name:25} : {status}")
            if result:
                passed_tests += 1

        self.logger.info("-" * 80)
        self.logger.info(f"TOTAL: {passed_tests}/{total_tests} test suites passed")

        success = passed_tests == total_tests
        if success:
            self.logger.info("🎉 ALL INTEGRATION TESTS PASSED!")
            self.logger.info("The system is ready for use.")
        else:
            self.logger.error("❌ SOME INTEGRATION TESTS FAILED")
            self.logger.error("Please fix the failing tests before proceeding.")

        return success


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive integration tests for Agentic Neurodata Conversion"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Run only quick tests (skip slow tests and coverage)",
    )

    args = parser.parse_args()

    # Run integration tests
    runner = IntegrationTestRunner(verbose=args.verbose, quick=args.quick)

    try:
        success = asyncio.run(runner.run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nIntegration tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Integration tests failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
