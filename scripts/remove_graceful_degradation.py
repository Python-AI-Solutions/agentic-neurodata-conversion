#!/usr/bin/env python3
"""
Remove all graceful degradation patterns from test files.

This script removes try-except import blocks, availability flags, and skipif markers
to implement proper fail-fast behavior for all dependencies.

This version uses a conservative approach that focuses on the most common patterns
and avoids breaking the code structure.
"""

import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)


def remove_graceful_degradation(file_path: Path) -> bool:
    """Remove graceful degradation patterns from a test file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Apply transformations in order - be conservative
        content = remove_simple_try_except_patterns(content)
        content = remove_availability_skipif(content)
        content = remove_availability_flags(content)
        content = clean_empty_lines(content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Removed graceful degradation from {file_path}")
            return True
        else:
            # Debug: check if file has patterns we should be catching
            if "_AVAILABLE" in original_content:
                logger.debug(
                    f"File {file_path} has _AVAILABLE patterns but no changes made"
                )

        return False

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False


def remove_simple_try_except_patterns(content: str) -> str:
    """Remove simple, well-formed try-except import patterns."""

    # Pattern 1: Simple single import with AVAILABLE flag
    # try:
    #     import datalad  # noqa: F401
    #
    #     DATALAD_AVAILABLE = True
    # except ImportError:
    #     DATALAD_AVAILABLE = False
    pattern1 = (
        r"try:\s*\n"
        r"\s*(import\s+[^\n]+(?:\s*#[^\n]*)?)\s*\n"
        r"(?:\s*\n)*"
        r"\s*(\w+_AVAILABLE)\s*=\s*True\s*\n"
        r"except\s+ImportError:\s*\n"
        r"\s*\2\s*=\s*False\s*\n"
    )

    def replace_simple_import(match):
        import_line = match.group(1).strip()
        # Remove noqa comments
        if "# noqa" in import_line:
            import_line = import_line.split("# noqa")[0].strip()
        return import_line + "\n"

    content = re.sub(pattern1, replace_simple_import, content, flags=re.MULTILINE)

    # Pattern 2: Simple from import with AVAILABLE flag
    # try:
    #     from module import something
    #     AVAILABLE = True
    # except ImportError:
    #     AVAILABLE = False
    pattern2 = (
        r"try:\s*\n"
        r"\s*(from\s+[^\n]+\s+import\s+[^\n]+(?:\s*#[^\n]*)?)\s*\n"
        r"(?:\s*\n)*"
        r"\s*(\w+_AVAILABLE)\s*=\s*True\s*\n"
        r"except\s+ImportError:\s*\n"
        r"\s*\2\s*=\s*False\s*\n"
    )

    content = re.sub(pattern2, replace_simple_import, content, flags=re.MULTILINE)

    # Pattern 3: Simple import with None assignment
    # try:
    #     import something
    # except ImportError:
    #     something = None
    pattern3 = (
        r"try:\s*\n"
        r"\s*((?:import|from)\s+[^\n]+)\s*\n"
        r"except\s+ImportError:\s*\n"
        r"\s*\w+\s*=\s*None\s*\n"
    )

    def replace_import_only(match):
        import_line = match.group(1).strip()
        if "# noqa" in import_line:
            import_line = import_line.split("# noqa")[0].strip()
        return import_line + "\n"

    content = re.sub(pattern3, replace_import_only, content, flags=re.MULTILINE)

    return content


def remove_availability_skipif(content: str) -> str:
    """Remove skipif markers that depend on availability flags."""

    patterns = [
        # pytestmark = pytest.mark.skipif(not SOMETHING_AVAILABLE, ...)
        r"pytestmark\s*=\s*pytest\.mark\.skipif\s*\(\s*not\s+\w+_AVAILABLE[^)]*\)[^\n]*\n",
        # @pytest.mark.skipif(not SOMETHING_AVAILABLE, ...)
        r"@pytest\.mark\.skipif\s*\(\s*not\s+\w+_AVAILABLE[^)]*\)[^\n]*\n\s*",
        # if not SOMETHING_AVAILABLE: pytest.skip(...)
        r"\s*if\s+not\s+\w+_AVAILABLE:\s*\n\s*pytest\.skip\([^)]*\)[^\n]*\n",
    ]

    for pattern in patterns:
        content = re.sub(pattern, "", content, flags=re.MULTILINE)

    return content


def remove_availability_flags(content: str) -> str:
    """Remove availability flag variable assignments."""

    # Pattern: Any *_AVAILABLE = True/False
    pattern = r"^\s*\w+_AVAILABLE\s*=\s*(True|False)\s*\n"
    content = re.sub(pattern, "", content, flags=re.MULTILINE)

    return content


def clean_empty_lines(content: str) -> str:
    """Clean up excessive empty lines."""
    # Replace multiple consecutive empty lines with single empty line
    content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)
    return content


def main():
    """Main function."""
    logging.basicConfig(level=logging.INFO)  # Less verbose

    test_files = list(Path("tests").rglob("*.py"))  # Include all Python files in tests

    print(
        f"🔍 Processing {len(test_files)} test files to remove graceful degradation..."
    )

    processed_count = 0
    for test_file in test_files:
        if remove_graceful_degradation(test_file):
            processed_count += 1

    print("\n✅ SUMMARY")
    print(f"   Files processed: {len(test_files)}")
    print(f"   Files modified: {processed_count}")

    if processed_count > 0:
        print("\n💡 CHANGES MADE:")
        print("   ❌ Removed simple try-except blocks around imports")
        print("   ❌ Removed availability flags (_AVAILABLE variables)")
        print("   ❌ Removed skipif markers for missing dependencies")
        print("   ✅ Replaced with direct imports that fail fast")

        print("\n🎯 RESULT:")
        print("   Simple graceful degradation patterns removed")
        print("   Direct imports now fail fast and clearly")
        print("   Missing dependencies cause immediate, clear failures")

        print("\n⚠️  NOTE:")
        print("   Complex multi-line import patterns may remain")
        print("   These can be manually converted to direct imports")
        print("   Run tests to verify everything still works")
    else:
        print("\n✅ No graceful degradation patterns found to remove")

    return 0


if __name__ == "__main__":
    exit(main())
