#!/usr/bin/env python3
"""
Health check script for Docker containers.

This script performs comprehensive health checks for the MCP server
and related services.
"""

import asyncio
import json
from pathlib import Path
import sys
import time
from typing import Any

try:
    import httpx
except ImportError:
    print("httpx not available, using basic health check")
    httpx = None


class HealthChecker:
    """Performs health checks for the Agentic Neurodata Conversion system."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    async def check_http_endpoint(
        self, endpoint: str, timeout: int = 5
    ) -> dict[str, Any]:
        """Check if an HTTP endpoint is responding."""
        if not httpx:
            return {"status": "unknown", "message": "httpx not available"}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{self.base_url}{endpoint}")

                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "content_length": len(response.content),
                }
        except httpx.TimeoutException:
            return {"status": "timeout", "message": f"Timeout after {timeout}s"}
        except httpx.ConnectError:
            return {"status": "connection_error", "message": "Cannot connect to server"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def check_mcp_server(self) -> dict[str, Any]:
        """Check MCP server health."""
        checks = {}

        # Check basic health endpoint
        checks["health"] = await self.check_http_endpoint("/health")

        # Check status endpoint
        checks["status"] = await self.check_http_endpoint("/status")

        # Check tools endpoint
        checks["tools"] = await self.check_http_endpoint("/tools")

        # Overall health assessment
        healthy_count = sum(
            1 for check in checks.values() if check.get("status") == "healthy"
        )
        total_checks = len(checks)

        overall_status = "healthy" if healthy_count == total_checks else "unhealthy"

        return {
            "overall_status": overall_status,
            "healthy_checks": healthy_count,
            "total_checks": total_checks,
            "checks": checks,
        }

    def check_file_system(self) -> dict[str, Any]:
        """Check file system health."""
        checks = {}

        # Check required directories
        required_dirs = ["/app/data", "/app/temp", "/app/logs"]

        for dir_path in required_dirs:
            path = Path(dir_path)
            checks[dir_path] = {
                "exists": path.exists(),
                "is_directory": path.is_dir() if path.exists() else False,
                "writable": path.is_dir() and os.access(path, os.W_OK)
                if path.exists()
                else False,
            }

        # Check configuration file
        config_file = Path("/app/config/docker.json")
        checks["config_file"] = {
            "exists": config_file.exists(),
            "readable": config_file.is_file() and os.access(config_file, os.R_OK)
            if config_file.exists()
            else False,
        }

        return checks

    def check_environment(self) -> dict[str, Any]:
        """Check environment variables."""
        import os

        required_vars = ["AGENTIC_CONVERTER_ENV", "AGENTIC_CONVERTER_CONFIG_FILE"]

        checks = {}
        for var in required_vars:
            value = os.getenv(var)
            checks[var] = {"set": value is not None, "value": value if value else None}

        return checks

    async def run_comprehensive_check(self) -> dict[str, Any]:
        """Run all health checks."""
        start_time = time.time()

        results = {"timestamp": time.time(), "checks": {}}

        # HTTP/MCP server checks
        try:
            results["checks"]["mcp_server"] = await self.check_mcp_server()
        except Exception as e:
            results["checks"]["mcp_server"] = {
                "overall_status": "error",
                "message": str(e),
            }

        # File system checks
        try:
            results["checks"]["file_system"] = self.check_file_system()
        except Exception as e:
            results["checks"]["file_system"] = {"status": "error", "message": str(e)}

        # Environment checks
        try:
            results["checks"]["environment"] = self.check_environment()
        except Exception as e:
            results["checks"]["environment"] = {"status": "error", "message": str(e)}

        # Overall assessment
        mcp_healthy = results["checks"]["mcp_server"].get("overall_status") == "healthy"

        results["overall_healthy"] = mcp_healthy
        results["check_duration"] = time.time() - start_time

        return results


async def main():
    """Main health check entry point."""
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Health check for Agentic Neurodata Conversion"
    )
    parser.add_argument("--host", default=os.getenv("HEALTH_CHECK_HOST", "localhost"))
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("HEALTH_CHECK_PORT", "8000"))
    )
    parser.add_argument("--timeout", type=int, default=5, help="Timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument(
        "--quiet", action="store_true", help="Quiet mode - only exit codes"
    )

    args = parser.parse_args()

    checker = HealthChecker(args.host, args.port)

    try:
        results = await checker.run_comprehensive_check()

        if args.json:
            print(json.dumps(results, indent=2))
        elif not args.quiet:
            # Human-readable output
            print(f"Health Check Results (took {results['check_duration']:.2f}s)")
            print("=" * 50)

            overall_status = (
                "✅ HEALTHY" if results["overall_healthy"] else "❌ UNHEALTHY"
            )
            print(f"Overall Status: {overall_status}")
            print()

            # MCP Server status
            mcp_status = results["checks"]["mcp_server"]
            if "overall_status" in mcp_status:
                status_icon = (
                    "✅" if mcp_status["overall_status"] == "healthy" else "❌"
                )
                print(
                    f"MCP Server: {status_icon} {mcp_status['overall_status'].upper()}"
                )

                if "checks" in mcp_status:
                    for endpoint, check in mcp_status["checks"].items():
                        check_icon = "✅" if check.get("status") == "healthy" else "❌"
                        print(
                            f"  {endpoint}: {check_icon} {check.get('status', 'unknown')}"
                        )

            print()

            # Environment status
            env_checks = results["checks"]["environment"]
            print("Environment Variables:")
            for var, check in env_checks.items():
                var_icon = "✅" if check["set"] else "❌"
                print(f"  {var}: {var_icon} {'SET' if check['set'] else 'NOT SET'}")

        # Exit with appropriate code
        sys.exit(0 if results["overall_healthy"] else 1)

    except KeyboardInterrupt:
        if not args.quiet:
            print("\nHealth check cancelled")
        sys.exit(1)
    except Exception as e:
        if not args.quiet:
            print(f"Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import os

    asyncio.run(main())
