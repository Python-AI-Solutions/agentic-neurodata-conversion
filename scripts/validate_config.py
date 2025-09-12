#!/usr/bin/env python3
"""Validate configuration files for the project."""

import json
from pathlib import Path
import sys


def validate_json_file(file_path: Path) -> tuple[bool, str]:
    """Validate a JSON configuration file.

    Args:
        file_path: Path to the JSON file to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            json.load(f)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"JSON syntax error in {file_path}: {e}"
    except FileNotFoundError:
        return False, f"Configuration file not found: {file_path}"
    except Exception as e:
        return False, f"Error validating {file_path}: {e}"


def validate_config_structure(file_path: Path) -> tuple[bool, str]:
    """Validate the structure of configuration files.

    Args:
        file_path: Path to the configuration file

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            config = json.load(f)

        # Basic structure validation based on file name
        if file_path.name == "default.json":
            required_keys = ["agents", "logging", "mcp", "http"]
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                return False, f"Missing required keys in {file_path}: {missing_keys}"

        # Validate HTTP configuration if present
        if "http" in config:
            http_config = config["http"]
            if not isinstance(http_config.get("port"), int):
                return False, f"HTTP port must be an integer in {file_path}"
            if http_config.get("port", 0) <= 0 or http_config.get("port", 0) > 65535:
                return False, f"HTTP port must be between 1 and 65535 in {file_path}"

        # Validate agents configuration
        if "agents" in config:
            agents_config = config["agents"]
            if "timeout_seconds" in agents_config and not isinstance(
                agents_config["timeout_seconds"], (int, float)
            ):
                return False, f"Agent timeout_seconds must be a number in {file_path}"

        return True, ""

    except Exception as e:
        return False, f"Error validating config structure in {file_path}: {e}"


def main() -> int:
    """Main validation function."""
    config_dir = Path("config")

    if not config_dir.exists():
        print(f"Configuration directory not found: {config_dir}")
        return 1

    # Find all JSON files in config directory
    json_files = list(config_dir.glob("*.json"))

    if not json_files:
        print("No JSON configuration files found in config directory")
        return 0

    errors: list[str] = []

    for json_file in json_files:
        print(f"Validating {json_file}...")

        # Validate JSON syntax
        is_valid, error_msg = validate_json_file(json_file)
        if not is_valid:
            errors.append(error_msg)
            continue

        # Validate configuration structure
        is_valid, error_msg = validate_config_structure(json_file)
        if not is_valid:
            errors.append(error_msg)

    if errors:
        print("\nConfiguration validation errors:")
        for error in errors:
            print(f"  ❌ {error}")
        return 1

    print(f"\n✅ All {len(json_files)} configuration files are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
