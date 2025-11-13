"""
Factory for generating mock validation results.

Provides programmatic generation of validation results for testing
retry workflows and error handling.
"""

from typing import Any


class ValidationFactory:
    """Factory for generating validation results."""

    @staticmethod
    def create_passed_result() -> dict[str, Any]:
        """Create a validation result that passed with no issues."""
        return {
            "is_valid": True,
            "issues": [],
            "summary": "All validation checks passed",
            "validation_outcome": "PASSED",
        }

    @staticmethod
    def create_passed_with_warnings() -> dict[str, Any]:
        """Create a validation result that passed but has warnings."""
        return {
            "is_valid": True,
            "issues": [
                {
                    "severity": "BEST_PRACTICE_VIOLATION",
                    "message": "Missing recommended field: subject.age",
                    "location": "subject",
                    "auto_fixable": False,
                },
                {
                    "severity": "BEST_PRACTICE_VIOLATION",
                    "message": "Session description is very brief",
                    "location": "session_description",
                    "auto_fixable": False,
                },
            ],
            "summary": "Validation passed with 2 warnings",
            "validation_outcome": "PASSED_WITH_ISSUES",
        }

    @staticmethod
    def create_failed_result() -> dict[str, Any]:
        """Create a validation result that failed."""
        return {
            "is_valid": False,
            "issues": [
                {
                    "severity": "CRITICAL",
                    "message": "Missing required field: session_description",
                    "location": "root",
                    "auto_fixable": False,
                },
                {
                    "severity": "CRITICAL",
                    "message": "Invalid timestamp format",
                    "location": "session_start_time",
                    "auto_fixable": True,
                },
            ],
            "summary": "Validation failed with 2 critical errors",
            "validation_outcome": "FAILED",
        }

    @staticmethod
    def create_failed_with_auto_fixable() -> dict[str, Any]:
        """Create a validation result with auto-fixable issues."""
        return {
            "is_valid": False,
            "issues": [
                {
                    "severity": "CRITICAL",
                    "message": "Invalid timestamp format",
                    "location": "session_start_time",
                    "auto_fixable": True,
                    "suggested_fix": "Convert to ISO 8601 format",
                },
                {
                    "severity": "CRITICAL",
                    "message": "Probe geometry file path is relative, should be absolute",
                    "location": "electrode_groups",
                    "auto_fixable": True,
                    "suggested_fix": "Convert to absolute path",
                },
            ],
            "summary": "Validation failed with 2 auto-fixable errors",
            "validation_outcome": "FAILED",
        }

    @staticmethod
    def create_failed_needs_user_input() -> dict[str, Any]:
        """Create a validation result requiring user input."""
        return {
            "is_valid": False,
            "issues": [
                {
                    "severity": "CRITICAL",
                    "message": "Missing required field: session_description",
                    "location": "root",
                    "auto_fixable": False,
                    "requires_user_input": True,
                    "field_name": "session_description",
                },
                {
                    "severity": "CRITICAL",
                    "message": "Missing required field: subject.species",
                    "location": "subject",
                    "auto_fixable": False,
                    "requires_user_input": True,
                    "field_name": "subject.species",
                },
            ],
            "summary": "Validation failed - user input required for 2 fields",
            "validation_outcome": "FAILED",
        }

    @staticmethod
    def create_mixed_issues() -> dict[str, Any]:
        """Create a validation result with mixed issue types."""
        return {
            "is_valid": False,
            "issues": [
                {"severity": "CRITICAL", "message": "Invalid timestamp", "auto_fixable": True},
                {
                    "severity": "CRITICAL",
                    "message": "Missing session_description",
                    "auto_fixable": False,
                    "requires_user_input": True,
                },
                {"severity": "BEST_PRACTICE_VIOLATION", "message": "Missing subject.age", "auto_fixable": False},
            ],
            "summary": "Mixed validation issues",
            "validation_outcome": "FAILED",
        }

    @staticmethod
    def create_result_for_retry_attempt(attempt_number: int) -> dict[str, Any]:
        """Create a validation result for a specific retry attempt.

        Args:
            attempt_number: Which retry attempt (1, 2, 3, etc.)

        Returns:
            Validation result that becomes progressively better with retries
        """
        if attempt_number == 1:
            # First retry: Still has 1 critical error
            return {
                "is_valid": False,
                "issues": [{"severity": "CRITICAL", "message": "Missing probe geometry", "auto_fixable": False}],
                "summary": f"Retry attempt {attempt_number}: 1 error remaining",
                "validation_outcome": "FAILED",
            }
        elif attempt_number == 2:
            # Second retry: Only warnings
            return ValidationFactory.create_passed_with_warnings()
        else:
            # Third retry and beyond: Success
            return ValidationFactory.create_passed_result()

    @staticmethod
    def create_custom_result(
        is_valid: bool, critical_count: int = 0, warning_count: int = 0, auto_fixable_count: int = 0
    ) -> dict[str, Any]:
        """Create a custom validation result.

        Args:
            is_valid: Whether validation passed
            critical_count: Number of critical errors
            warning_count: Number of warnings
            auto_fixable_count: Number of auto-fixable issues

        Returns:
            Custom validation result
        """
        issues = []

        # Add critical errors
        for i in range(critical_count):
            is_fixable = i < auto_fixable_count
            issues.append(
                {
                    "severity": "CRITICAL",
                    "message": f"Critical error {i + 1}",
                    "auto_fixable": is_fixable,
                    "requires_user_input": not is_fixable,
                }
            )

        # Add warnings
        for i in range(warning_count):
            issues.append({"severity": "BEST_PRACTICE_VIOLATION", "message": f"Warning {i + 1}", "auto_fixable": False})

        outcome = "PASSED" if is_valid else "FAILED"
        if is_valid and warning_count > 0:
            outcome = "PASSED_WITH_ISSUES"

        return {
            "is_valid": is_valid,
            "issues": issues,
            "summary": f"{critical_count} errors, {warning_count} warnings",
            "validation_outcome": outcome,
        }
