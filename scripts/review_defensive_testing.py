#!/usr/bin/env python3
"""
Review and improve defensive programming and xfail usage throughout the test suite.

This script analyzes the current test suite and provides recommendations for
better TDD practices with defensive programming.
"""

import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TestAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze test files for defensive programming patterns."""

    def __init__(self):
        self.issues = []
        self.current_file = None
        self.current_class = None
        self.current_function = None
        self.imports = set()
        self.skipif_conditions = []
        self.xfail_markers = []
        self.try_except_blocks = []

    def visit_Import(self, node):
        """Track imports."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from imports."""
        if node.module:
            for alias in node.names:
                self.imports.add(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Track test classes."""
        old_class = self.current_class
        self.current_class = node.name

        # Check for class-level markers
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and hasattr(decorator.func, "attr"):
                if decorator.func.attr in ["skipif", "xfail"]:
                    self._analyze_marker(decorator, "class")

        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Track test functions."""
        old_function = self.current_function
        self.current_function = node.name

        # Check for function-level markers
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and hasattr(decorator.func, "attr"):
                if decorator.func.attr in ["skipif", "xfail"]:
                    self._analyze_marker(decorator, "function")

        # Check for try-except blocks
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                self.try_except_blocks.append(
                    {
                        "file": self.current_file,
                        "class": self.current_class,
                        "function": self.current_function,
                        "line": child.lineno,
                    }
                )

        self.generic_visit(node)
        self.current_function = old_function

    def visit_Try(self, node):
        """Track try-except blocks."""
        self.try_except_blocks.append(
            {
                "file": self.current_file,
                "class": self.current_class,
                "function": self.current_function,
                "line": node.lineno,
                "handlers": [
                    handler.type.id
                    if hasattr(handler.type, "id")
                    else str(handler.type)
                    for handler in node.handlers
                    if handler.type
                ],
            }
        )
        self.generic_visit(node)

    def _analyze_marker(self, decorator, level):
        """Analyze pytest markers."""
        marker_info = {
            "file": self.current_file,
            "class": self.current_class,
            "function": self.current_function,
            "level": level,
            "marker": decorator.func.attr,
            "line": decorator.lineno,
        }

        # Extract reason if present
        for keyword in decorator.keywords:
            if keyword.arg == "reason":
                if isinstance(keyword.value, ast.Str):
                    marker_info["reason"] = keyword.value.s
                elif isinstance(keyword.value, ast.Constant):
                    marker_info["reason"] = keyword.value.value

        if decorator.func.attr == "skipif":
            self.skipif_conditions.append(marker_info)
        elif decorator.func.attr == "xfail":
            self.xfail_markers.append(marker_info)

    def analyze_file(self, file_path: Path):
        """Analyze a single test file."""
        self.current_file = str(file_path)
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            self.visit(tree)

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")


class DefensiveProgrammingReviewer:
    """Review test suite for defensive programming patterns."""

    def __init__(self, test_root: Path):
        self.test_root = test_root
        self.analyzer = TestAnalyzer()
        self.recommendations = []

    def analyze_test_suite(self) -> dict[str, any]:
        """Analyze the entire test suite."""
        test_files = list(self.test_root.rglob("test_*.py"))

        for test_file in test_files:
            self.analyzer.analyze_file(test_file)

        return self._generate_report()

    def _generate_report(self) -> dict[str, any]:
        """Generate comprehensive report with recommendations."""
        report = {
            "summary": self._generate_summary(),
            "skipif_analysis": self._analyze_skipif_usage(),
            "xfail_analysis": self._analyze_xfail_usage(),
            "defensive_patterns": self._analyze_defensive_patterns(),
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_summary(self) -> dict[str, any]:
        """Generate summary statistics."""
        test_files = list(self.test_root.rglob("test_*.py"))

        return {
            "total_test_files": len(test_files),
            "skipif_markers": len(self.analyzer.skipif_conditions),
            "xfail_markers": len(self.analyzer.xfail_markers),
            "try_except_blocks": len(self.analyzer.try_except_blocks),
            "files_with_skipif": len(
                {item["file"] for item in self.analyzer.skipif_conditions}
            ),
            "files_with_xfail": len(
                {item["file"] for item in self.analyzer.xfail_markers}
            ),
        }

    def _analyze_skipif_usage(self) -> dict[str, any]:
        """Analyze skipif marker usage."""
        skipif_by_reason = {}
        skipif_by_file = {}

        for item in self.analyzer.skipif_conditions:
            reason = item.get("reason", "No reason provided")
            file_name = Path(item["file"]).name

            if reason not in skipif_by_reason:
                skipif_by_reason[reason] = []
            skipif_by_reason[reason].append(item)

            if file_name not in skipif_by_file:
                skipif_by_file[file_name] = []
            skipif_by_file[file_name].append(item)

        return {
            "by_reason": skipif_by_reason,
            "by_file": skipif_by_file,
            "common_reasons": self._get_common_reasons(skipif_by_reason),
        }

    def _analyze_xfail_usage(self) -> dict[str, any]:
        """Analyze xfail marker usage."""
        xfail_by_reason = {}
        xfail_by_file = {}

        for item in self.analyzer.xfail_markers:
            reason = item.get("reason", "No reason provided")
            file_name = Path(item["file"]).name

            if reason not in xfail_by_reason:
                xfail_by_reason[reason] = []
            xfail_by_reason[reason].append(item)

            if file_name not in xfail_by_file:
                xfail_by_file[file_name] = []
            xfail_by_file[file_name].append(item)

        return {
            "by_reason": xfail_by_reason,
            "by_file": xfail_by_file,
            "common_reasons": self._get_common_reasons(xfail_by_reason),
        }

    def _analyze_defensive_patterns(self) -> dict[str, any]:
        """Analyze defensive programming patterns."""
        patterns = {
            "import_error_handling": self._find_import_error_patterns(),
            "dependency_checks": self._find_dependency_check_patterns(),
            "graceful_degradation": self._find_graceful_degradation_patterns(),
            "error_handling": self._analyze_error_handling(),
        }

        return patterns

    def _find_import_error_patterns(self) -> list[dict]:
        """Find import error handling patterns."""
        patterns = []

        for test_file in self.test_root.rglob("test_*.py"):
            try:
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()

                # Look for try-except import patterns
                if (
                    "try:" in content
                    and "import" in content
                    and "except ImportError:" in content
                ):
                    patterns.append(
                        {
                            "file": str(test_file),
                            "pattern": "try_except_import",
                            "has_availability_flag": "_AVAILABLE" in content,
                        }
                    )

            except Exception as e:
                logger.error(f"Error reading {test_file}: {e}")

        return patterns

    def _find_dependency_check_patterns(self) -> list[dict]:
        """Find dependency check patterns."""
        patterns = []

        for test_file in self.test_root.rglob("test_*.py"):
            try:
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()

                # Look for availability flags
                if "_AVAILABLE" in content:
                    patterns.append(
                        {
                            "file": str(test_file),
                            "pattern": "availability_flag",
                            "uses_skipif": "pytest.mark.skipif" in content,
                        }
                    )

            except Exception as e:
                logger.error(f"Error reading {test_file}: {e}")

        return patterns

    def _find_graceful_degradation_patterns(self) -> list[dict]:
        """Find graceful degradation patterns."""
        patterns = []

        # Look for tests that check for functionality before using it
        for test_file in self.test_root.rglob("test_*.py"):
            try:
                with open(test_file, encoding="utf-8") as f:
                    content = f.read()

                # Look for conditional execution patterns
                if any(
                    pattern in content
                    for pattern in [
                        "if hasattr(",
                        "if callable(",
                        "if available_tools",
                        "if tool_name in",
                    ]
                ):
                    patterns.append(
                        {"file": str(test_file), "pattern": "conditional_execution"}
                    )

            except Exception as e:
                logger.error(f"Error reading {test_file}: {e}")

        return patterns

    def _analyze_error_handling(self) -> dict[str, any]:
        """Analyze error handling patterns."""
        return {
            "try_except_blocks": len(self.analyzer.try_except_blocks),
            "files_with_error_handling": len(
                {item["file"] for item in self.analyzer.try_except_blocks}
            ),
            "common_exception_types": self._get_common_exception_types(),
        }

    def _get_common_reasons(self, reasons_dict: dict) -> list[tuple[str, int]]:
        """Get most common reasons for markers."""
        return sorted(
            [(reason, len(items)) for reason, items in reasons_dict.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

    def _get_common_exception_types(self) -> list[tuple[str, int]]:
        """Get most common exception types handled."""
        exception_counts = {}

        for block in self.analyzer.try_except_blocks:
            for handler in block.get("handlers", []):
                if handler not in exception_counts:
                    exception_counts[handler] = 0
                exception_counts[handler] += 1

        return sorted(exception_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    def _generate_recommendations(self) -> list[dict[str, str]]:
        """Generate recommendations for improving defensive programming."""
        recommendations = []

        # Check for missing xfail markers
        if len(self.analyzer.skipif_conditions) > len(self.analyzer.xfail_markers) * 2:
            recommendations.append(
                {
                    "category": "TDD Practice",
                    "priority": "High",
                    "issue": "Too many skipif markers compared to xfail markers",
                    "recommendation": "Consider converting some skipif markers to xfail for better TDD workflow. "
                    "Use xfail for functionality that should exist but is not yet implemented.",
                    "rationale": "xfail markers provide better feedback about implementation progress",
                }
            )

        # Check for missing dependency checks
        test_files_count = len(list(self.test_root.rglob("test_*.py")))
        import_patterns_count = len(self._find_import_error_patterns())

        if import_patterns_count < test_files_count * 0.5:
            recommendations.append(
                {
                    "category": "Defensive Programming",
                    "priority": "Medium",
                    "issue": "Many test files lack import error handling",
                    "recommendation": "Add try-except blocks around imports with availability flags and skipif markers",
                    "rationale": "Prevents test failures when optional dependencies are missing",
                }
            )

        # Check for missing error handling
        error_handling_files = len(
            {item["file"] for item in self.analyzer.try_except_blocks}
        )
        if error_handling_files < test_files_count * 0.3:
            recommendations.append(
                {
                    "category": "Error Handling",
                    "priority": "Medium",
                    "issue": "Limited error handling in test files",
                    "recommendation": "Add more comprehensive error handling for edge cases and missing functionality",
                    "rationale": "Better error handling provides clearer feedback when tests fail",
                }
            )

        # Check for specific patterns
        recommendations.extend(self._check_specific_patterns())

        return recommendations

    def _check_specific_patterns(self) -> list[dict[str, str]]:
        """Check for specific anti-patterns and missing patterns."""
        recommendations = []

        # Check for files using skipif without proper reasons
        skipif_without_reason = [
            item
            for item in self.analyzer.skipif_conditions
            if item.get("reason", "").strip() in ["", "No reason provided"]
        ]

        if skipif_without_reason:
            recommendations.append(
                {
                    "category": "Documentation",
                    "priority": "Low",
                    "issue": f"{len(skipif_without_reason)} skipif markers lack descriptive reasons",
                    "recommendation": "Add clear reasons to all skipif markers explaining why tests are skipped",
                    "rationale": "Clear reasons help developers understand what needs to be implemented",
                }
            )

        # Check for integration tests that might benefit from xfail
        integration_files = [
            f for f in self.test_root.rglob("test_*.py") if "integration" in str(f)
        ]
        integration_xfails = [
            item
            for item in self.analyzer.xfail_markers
            if "integration" in item["file"]
        ]

        if len(integration_files) > 0 and len(integration_xfails) == 0:
            recommendations.append(
                {
                    "category": "TDD Practice",
                    "priority": "Medium",
                    "issue": "Integration tests lack xfail markers for unimplemented functionality",
                    "recommendation": "Add xfail markers to integration tests for features not yet fully implemented",
                    "rationale": "Integration tests often depend on multiple components that may not be complete",
                }
            )

        return recommendations


def print_report(report: dict[str, any]):
    """Print a formatted report."""
    print("=" * 80)
    print("DEFENSIVE PROGRAMMING AND XFAIL USAGE REVIEW")
    print("=" * 80)

    # Summary
    summary = report["summary"]
    print("\n📊 SUMMARY")
    print(f"   Total test files: {summary['total_test_files']}")
    print(f"   Files with skipif: {summary['files_with_skipif']}")
    print(f"   Files with xfail: {summary['files_with_xfail']}")
    print(f"   Total skipif markers: {summary['skipif_markers']}")
    print(f"   Total xfail markers: {summary['xfail_markers']}")
    print(f"   Try-except blocks: {summary['try_except_blocks']}")

    # Skipif analysis
    skipif = report["skipif_analysis"]
    print("\n🚫 SKIPIF ANALYSIS")
    print("   Most common reasons:")
    for reason, count in skipif["common_reasons"]:
        print(f"     • {reason}: {count} occurrences")

    # Xfail analysis
    xfail = report["xfail_analysis"]
    print("\n❌ XFAIL ANALYSIS")
    print("   Most common reasons:")
    for reason, count in xfail["common_reasons"]:
        print(f"     • {reason}: {count} occurrences")

    # Defensive patterns
    patterns = report["defensive_patterns"]
    print("\n🛡️  DEFENSIVE PATTERNS")
    print(f"   Import error handling: {len(patterns['import_error_handling'])} files")
    print(f"   Dependency checks: {len(patterns['dependency_checks'])} files")
    print(f"   Graceful degradation: {len(patterns['graceful_degradation'])} files")
    print(
        f"   Error handling blocks: {patterns['error_handling']['try_except_blocks']}"
    )

    # Recommendations
    recommendations = report["recommendations"]
    print(f"\n💡 RECOMMENDATIONS ({len(recommendations)} total)")

    for i, rec in enumerate(recommendations, 1):
        priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(
            rec["priority"], "⚪"
        )
        print(
            f"\n   {i}. {priority_emoji} {rec['category']} - {rec['priority']} Priority"
        )
        print(f"      Issue: {rec['issue']}")
        print(f"      Recommendation: {rec['recommendation']}")
        print(f"      Rationale: {rec['rationale']}")


def main():
    """Main function."""
    logging.basicConfig(level=logging.INFO)

    test_root = Path("tests")
    if not test_root.exists():
        print("❌ Tests directory not found")
        return 1

    print("🔍 Analyzing test suite for defensive programming patterns...")

    reviewer = DefensiveProgrammingReviewer(test_root)
    report = reviewer.analyze_test_suite()

    print_report(report)

    # Generate improvement suggestions
    print("\n🎯 SPECIFIC IMPROVEMENT SUGGESTIONS")
    print("\n1. Convert appropriate skipif to xfail:")
    print("   - Look for tests that skip due to 'not implemented yet'")
    print("   - These should use xfail instead to track implementation progress")

    print("\n2. Add defensive import patterns:")
    print("   - Wrap imports in try-except blocks")
    print("   - Use availability flags with descriptive names")
    print("   - Add skipif markers with clear reasons")

    print("\n3. Improve error handling:")
    print("   - Add try-except blocks for operations that might fail")
    print("   - Use pytest.raises for expected exceptions")
    print("   - Provide clear error messages in assertions")

    print("\n4. Enhance TDD workflow:")
    print("   - Use xfail for tests that define desired behavior")
    print("   - Add strict=True to xfail when implementation is close")
    print("   - Document expected implementation timeline in reasons")

    print("\n✅ Review complete! Use these recommendations to improve test quality.")

    return 0


if __name__ == "__main__":
    exit(main())
