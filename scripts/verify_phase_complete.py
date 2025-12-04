#!/usr/bin/env python3
"""Phase Completion Verification Script.

Usage: python scripts/verify_phase_complete.py <phase_number>

This script verifies that all deliverables for a phase are complete,
including the often-forgotten TEST FILES.

Example:
    python scripts/verify_phase_complete.py 2
"""

import argparse
import subprocess  # nosec B404 - Safe: dev script for running pytest
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def find_files(pattern: str) -> list[Path]:
    """Find files matching glob pattern."""
    base_dir = Path.cwd()
    return list(base_dir.glob(pattern))


def check_files(pattern: str, description: str) -> tuple[bool, int]:
    """Check if files matching pattern exist.

    Returns:
        Tuple of (success, file_count)
    """
    files = find_files(pattern)

    if files:
        print(f"{Colors.GREEN}✓{Colors.NC} {description}: {len(files)} file(s) found")
        for f in files:
            size = f.stat().st_size
            size_kb = size / 1024
            print(f"  - {f.relative_to(Path.cwd())} ({size_kb:.1f}KB)")
        return True, len(files)
    else:
        print(f"{Colors.RED}✗{Colors.NC} {description}: NO FILES FOUND")
        print(f"  Expected pattern: {pattern}")
        return False, 0


def count_tests(pattern: str) -> int:
    """Count tests in files matching pattern using pytest."""
    try:
        result = subprocess.run(  # nosec B603, B607 - Safe: trusted dev command, no user input
            ["pixi", "run", "pytest", pattern, "--co", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Parse output for "collected X items"
        for line in result.stdout.split("\n"):
            if "collected" in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        return int(parts[1])
                    except ValueError:
                        pass
        return 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0


def check_tests(pattern: str, description: str, phase: int) -> tuple[bool, int]:
    """Check test files exist and count tests.

    This is the CRITICAL check that was missed in Phase 2.

    Returns:
        Tuple of (success, test_count)
    """
    print("\n" + "=" * 50)
    print(f"{Colors.BLUE}CRITICAL: Test File Check{Colors.NC}")
    print("=" * 50)

    files = find_files(pattern)

    if files:
        print(f"{Colors.GREEN}✓{Colors.NC} {description}: {len(files)} test file(s) found")
        for f in files:
            size = f.stat().st_size
            size_kb = size / 1024
            print(f"  - {f.relative_to(Path.cwd())} ({size_kb:.1f}KB)")

        # Count tests
        print("\nCounting tests...")
        test_count = count_tests(pattern)
        if test_count > 0:
            print(f"{Colors.GREEN}✓{Colors.NC} Collected {test_count} tests")
        else:
            print(f"{Colors.YELLOW}⚠{Colors.NC} Could not count tests (run pytest manually)")

        return True, test_count
    else:
        print(f"{Colors.RED}✗ PHASE INCOMPLETE{Colors.NC}")
        print(f"{Colors.RED}✗{Colors.NC} {description}: NO TEST FILES FOUND")
        print(f"  Expected pattern: {pattern}")
        print()
        print(f"{Colors.YELLOW}⚠ WARNING: Phase {phase} cannot be marked complete without tests!{Colors.NC}")
        print(f"{Colors.YELLOW}⚠ Tests are MANDATORY deliverables, not optional!{Colors.NC}")
        return False, 0


def verify_phase(phase: int) -> bool:
    """Verify phase completion.

    Args:
        phase: Phase number (0, 1, 2, etc.)

    Returns:
        True if verification passes, False otherwise
    """
    print("=" * 50)
    print(f"Phase {phase} Completion Verification")
    print("=" * 50)
    print()

    errors = 0

    # Check implementation files
    print("=== Implementation Files ===")
    success, _ = check_files("kg_service/**/*.py", "KG Service implementation files")
    if not success:
        errors += 1

    # Check test files - THIS IS THE CRITICAL CHECK THAT WAS MISSED
    print()
    success, test_count = check_tests(
        f"tests/kg_service/test_phase{phase}*.py", f"Phase {phase} main test files", phase
    )
    if not success:
        errors += 1

    # Check for any additional test files (unit tests in subdirs)
    print()
    print("=== Additional Test Files (unit tests) ===")
    success, additional_tests = check_files("tests/kg_service/**/test_*.py", f"Phase {phase} unit/API test files")
    # Don't count as error if no additional files, but note them

    # Summary
    print()
    print("=" * 50)
    print("Verification Summary")
    print("=" * 50)

    if errors > 0:
        print(f"{Colors.RED}✗ VERIFICATION FAILED{Colors.NC}")
        print(f"  Errors: {errors}")
        print()
        print(f"Phase {phase} is NOT COMPLETE until all deliverables exist.")
        print("Please:")
        print(f"  1. Review implementation guide for Phase {phase}")
        print("  2. Create missing test files")
        print("  3. Run this script again")
        return False
    else:
        print(f"{Colors.GREEN}✓ All checks passed{Colors.NC}")
        print()
        print(f"Phase {phase} appears complete. Next steps:")
        print(f"  1. Run tests: pixi run pytest tests/kg_service/test_phase{phase}*.py -v")
        print("  2. Verify all tests pass (or skip with clear reason)")
        print("  3. Create implementation review document")
        print("  4. Present verification report to user")
        print("  5. Wait for user confirmation before proceeding to next phase")
        print()
        print(f"{Colors.YELLOW}Remember:{Colors.NC} A phase with failing tests is NOT complete!")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify phase completion including test files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/verify_phase_complete.py 2
  python scripts/verify_phase_complete.py 3

This script checks that all deliverables for a phase are complete,
with special emphasis on TEST FILES which are often forgotten.
        """,
    )
    parser.add_argument("phase", type=int, help="Phase number (0, 1, 2, etc.)")

    args = parser.parse_args()

    success = verify_phase(args.phase)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
