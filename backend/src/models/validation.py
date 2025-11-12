"""Validation result models.

Models for NWB Inspector validation results and correction contexts.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """Individual validation issue from NWB Inspector."""

    severity: ValidationSeverity
    message: str
    location: str | None = Field(
        default=None,
        description="Path to the issue location in the NWB file",
    )
    check_name: str | None = Field(
        default=None,
        description="Name of the validation check that found this issue",
    )


class ValidationResult(BaseModel):
    """Complete validation result from NWB Inspector."""

    is_valid: bool = Field(
        description="Overall validation status",
    )
    issues: list[ValidationIssue] = Field(
        default_factory=list,
        description="List of validation issues",
    )
    summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count of issues by severity",
    )
    inspector_version: str | None = Field(
        default=None,
        description="Version of NWB Inspector used",
    )

    @classmethod
    def from_inspector_output(
        cls,
        inspector_results: list[dict[str, Any]],
        inspector_version: str,
    ) -> "ValidationResult":
        """Create ValidationResult from NWB Inspector output.

        Args:
            inspector_results: List of check results from NWB Inspector
            inspector_version: Version string of NWB Inspector

        Returns:
            ValidationResult instance
        """
        issues = []
        summary = {
            "critical": 0,
            "error": 0,
            "warning": 0,
            "info": 0,
        }

        for result in inspector_results:
            severity_str = result.get("severity", "info").lower()
            try:
                severity = ValidationSeverity(severity_str)
            except ValueError:
                severity = ValidationSeverity.INFO

            issue = ValidationIssue(
                severity=severity,
                message=result.get("message", "Unknown issue"),
                location=result.get("location"),
                check_name=result.get("check_function_name"),
            )
            issues.append(issue)
            summary[severity.value] += 1

        # Consider valid if no critical or error issues
        is_valid = summary["critical"] == 0 and summary["error"] == 0

        return cls(
            is_valid=is_valid,
            issues=issues,
            summary=summary,
            inspector_version=inspector_version,
        )


class CorrectionContext(BaseModel):
    """Context for LLM-assisted correction analysis.

    Contains the validation issues and relevant metadata for the LLM
    to analyze and suggest corrections.
    """

    validation_result: ValidationResult
    input_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata extracted from input files",
    )
    conversion_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters used for conversion",
    )
    previous_attempts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="History of previous correction attempts",
    )

    def add_attempt(self, attempt_data: dict[str, Any]) -> None:
        """Record a correction attempt.

        Args:
            attempt_data: Details of the correction attempt
        """
        self.previous_attempts.append(attempt_data)
