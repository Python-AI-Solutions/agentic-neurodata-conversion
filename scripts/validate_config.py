#!/usr/bin/env python3
"""Configuration validation script.

This script validates configuration files for all environments and deployment types,
ensuring they are properly formatted and contain valid values.
"""

import argparse
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_neurodata_conversion.core.config import Environment
from agentic_neurodata_conversion.core.config_loader import (
    DeploymentConfigManager,
    EnvironmentConfigLoader,
    get_config_summary,
    validate_all_configs,
)


def validate_environment_configs() -> bool:
    """Validate all environment configuration files.

    Returns:
        True if all configurations are valid, False otherwise.
    """
    print("Validating environment configurations...")
    print("=" * 50)

    results = validate_all_configs()
    all_valid = True

    for env_name, result in results.items():
        status = "✓" if result["valid"] else "✗"
        exists = "exists" if result["exists"] else "missing"

        print(f"{status} {env_name.upper():<12} ({exists})")

        if result["valid"]:
            print(f"    Environment: {result['environment']}")
            print(f"    Debug: {result['debug']}")
            print(f"    HTTP Port: {result['http_port']}")
            print(f"    MCP Transport: {result['mcp_transport']}")
        elif result["exists"]:
            print(f"    Error: {result['error']}")
            all_valid = False
        else:
            print(f"    Warning: {result['error']}")

        print()

    return all_valid


def validate_deployment_configs() -> bool:
    """Validate deployment-specific configurations.

    Returns:
        True if all deployment configs are valid, False otherwise.
    """
    print("Validating deployment configurations...")
    print("=" * 50)

    manager = DeploymentConfigManager()
    deployment_types = ["docker", "kubernetes", "serverless", "development"]
    all_valid = True

    for deployment_type in deployment_types:
        try:
            if deployment_type == "docker":
                config = manager.get_docker_config()
            elif deployment_type == "kubernetes":
                config = manager.get_kubernetes_config()
            elif deployment_type == "serverless":
                config = manager.get_serverless_config()
            elif deployment_type == "development":
                config = manager.get_development_config()

            print(f"✓ {deployment_type.upper():<12} (valid)")

            # Print key settings
            summary = get_config_summary(config)
            print(f"    Environment: {summary['environment']}")
            print(f"    Debug: {summary['debug']}")
            print(f"    Data Dir: {summary['data_directory']}")
            print(f"    HTTP: {summary['http']['host']}:{summary['http']['port']}")
            print(f"    MCP: {summary['mcp']['transport_type']}")

        except Exception as e:
            print(f"✗ {deployment_type.upper():<12} (error)")
            print(f"    Error: {e}")
            all_valid = False

        print()

    return all_valid


def compare_configurations() -> None:
    """Compare configurations across environments."""
    print("Configuration comparison...")
    print("=" * 50)

    loader = EnvironmentConfigLoader()
    configs = {}

    # Load all available configurations
    for env in Environment:
        try:
            config = loader.load_for_environment(env.value)
            configs[env.value] = get_config_summary(config)
        except Exception as e:
            print(f"Failed to load {env.value} config: {e}")
            continue

    if not configs:
        print("No valid configurations found for comparison")
        return

    # Compare key settings
    settings_to_compare = [
        ("agents.timeout_seconds", "Agent Timeout"),
        ("agents.max_concurrent_tasks", "Max Concurrent Tasks"),
        ("http.port", "HTTP Port"),
        ("mcp.transport_type", "MCP Transport"),
        ("logging.level", "Log Level"),
        ("security.enable_authentication", "Authentication"),
        ("performance.worker_pool_size", "Worker Pool Size"),
    ]

    print(
        f"{'Setting':<25} {'Development':<12} {'Testing':<12} {'Staging':<12} {'Production':<12}"
    )
    print("-" * 80)

    for setting_path, setting_name in settings_to_compare:
        values = {}

        for env_name, config in configs.items():
            # Navigate nested dictionary
            value = config
            for key in setting_path.split("."):
                value = value.get(key, "N/A")
                if value == "N/A":
                    break
            values[env_name] = str(value)

        print(
            f"{setting_name:<25} {values.get('development', 'N/A'):<12} "
            f"{values.get('testing', 'N/A'):<12} {values.get('staging', 'N/A'):<12} "
            f"{values.get('production', 'N/A'):<12}"
        )


def check_environment_variables() -> None:
    """Check for relevant environment variables."""
    print("Environment variables check...")
    print("=" * 50)

    import os

    env_vars = [
        ("ANC_ENVIRONMENT", "Current environment"),
        ("ANC_DEBUG", "Debug mode"),
        ("ANC_DATA_DIRECTORY", "Data directory"),
        ("ANC_LOG_LEVEL", "Log level"),
        ("ANC_HTTP_HOST", "HTTP host"),
        ("ANC_HTTP_PORT", "HTTP port"),
        ("ANC_MCP_TRANSPORT", "MCP transport type"),
        ("ANC_ENABLE_AUTH", "Authentication enabled"),
        ("ANC_API_KEY_HEADER", "API key header"),
        ("ANC_ALLOWED_ORIGINS", "Allowed CORS origins"),
    ]

    for var_name, description in env_vars:
        value = os.getenv(var_name)
        status = "✓" if value else "○"
        value_str = value if value else "not set"
        print(f"{status} {var_name:<20} {description:<25} = {value_str}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Validate configuration files")
    parser.add_argument(
        "--check",
        choices=["env", "deploy", "compare", "envvars", "all"],
        default="all",
        help="What to check (default: all)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )

    args = parser.parse_args()

    if args.json:
        # JSON output for programmatic use
        results = {
            "environment_configs": validate_all_configs(),
            "deployment_configs": {},
            "environment_variables": {},
        }

        # Add deployment config validation
        manager = DeploymentConfigManager()
        for deployment_type in ["docker", "kubernetes", "serverless", "development"]:
            try:
                if deployment_type == "docker":
                    config = manager.get_docker_config()
                elif deployment_type == "kubernetes":
                    config = manager.get_kubernetes_config()
                elif deployment_type == "serverless":
                    config = manager.get_serverless_config()
                elif deployment_type == "development":
                    config = manager.get_development_config()

                results["deployment_configs"][deployment_type] = {
                    "valid": True,
                    "summary": get_config_summary(config),
                }
            except Exception as e:
                results["deployment_configs"][deployment_type] = {
                    "valid": False,
                    "error": str(e),
                }

        # Add environment variables
        import os

        env_vars = [
            "ANC_ENVIRONMENT",
            "ANC_DEBUG",
            "ANC_DATA_DIRECTORY",
            "ANC_LOG_LEVEL",
            "ANC_HTTP_HOST",
            "ANC_HTTP_PORT",
            "ANC_MCP_TRANSPORT",
            "ANC_ENABLE_AUTH",
            "ANC_API_KEY_HEADER",
            "ANC_ALLOWED_ORIGINS",
        ]

        for var in env_vars:
            results["environment_variables"][var] = os.getenv(var)

        print(json.dumps(results, indent=2, default=str))
        return

    # Human-readable output
    success = True

    if args.check in ["env", "all"]:
        success &= validate_environment_configs()

    if args.check in ["deploy", "all"]:
        success &= validate_deployment_configs()

    if args.check in ["compare", "all"]:
        compare_configurations()
        print()

    if args.check in ["envvars", "all"]:
        check_environment_variables()
        print()

    if args.check == "all":
        if success:
            print("✓ All configurations are valid!")
        else:
            print("✗ Some configurations have issues")
            sys.exit(1)


if __name__ == "__main__":
    main()
