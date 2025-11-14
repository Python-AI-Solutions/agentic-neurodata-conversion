#!/usr/bin/env python3
"""Pre-commit hook to enforce pixi.toml as single source of truth for dependencies.

This hook prevents accidental addition of dependencies to pyproject.toml,
ensuring all dependencies remain in pixi.toml only.
"""

import re
import sys
from pathlib import Path


def check_pyproject_dependencies(pyproject_path: Path) -> tuple[bool, list[str]]:
    """Check if pyproject.toml contains forbidden dependency sections.

    Args:
        pyproject_path: Path to pyproject.toml

    Returns:
        Tuple of (is_valid, error_messages)
    """
    if not pyproject_path.exists():
        return True, []

    content = pyproject_path.read_text()
    errors = []

    # Check for [project.dependencies] section
    if re.search(r'^\[project\.dependencies\]', content, re.MULTILINE):
        errors.append(
            "❌ [project.dependencies] section found in pyproject.toml\n"
            "   Dependencies must be in pixi.toml only!"
        )

    # Check for dependencies = [...] in [project] section
    project_deps_pattern = r'^\[project\].*?^dependencies\s*=\s*\['
    if re.search(project_deps_pattern, content, re.MULTILINE | re.DOTALL):
        errors.append(
            "❌ dependencies = [...] found in [project] section\n"
            "   Dependencies must be in pixi.toml only!"
        )

    # Check for [project.optional-dependencies] section
    if re.search(r'^\[project\.optional-dependencies\]', content, re.MULTILINE):
        errors.append(
            "❌ [project.optional-dependencies] section found in pyproject.toml\n"
            "   All dependencies (including dev) must be in pixi.toml only!"
        )

    return len(errors) == 0, errors


def main() -> int:
    """Main entry point for the hook."""
    repo_root = Path(__file__).parent.parent
    pyproject_path = repo_root / "pyproject.toml"

    is_valid, errors = check_pyproject_dependencies(pyproject_path)

    if not is_valid:
        print("\n" + "="*70)
        print("🚫 DEPENDENCY POLICY VIOLATION")
        print("="*70)
        for error in errors:
            print(f"\n{error}")
        print("\n" + "-"*70)
        print("ℹ️  Policy: This project uses pixi.toml as the single source of truth")
        print("   for ALL dependencies (runtime and development).")
        print("\n   To fix: Remove dependency sections from pyproject.toml and")
        print("   add them to pixi.toml instead:")
        print("   - Runtime deps  → pixi.toml [dependencies]")
        print("   - Dev/test deps → pixi.toml [feature.dev.dependencies]")
        print("="*70 + "\n")
        return 1

    print("✅ pyproject.toml dependency check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
