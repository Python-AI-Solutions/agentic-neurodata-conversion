"""JSON report generator for NWB evaluation results.

Generates machine-readable JSON reports with complete validation data.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class JSONReportGenerator:
    """Generates comprehensive JSON reports for NWB validation results."""

    @staticmethod
    def generate_json_report(
        output_path: Path,
        report_data: dict[str, Any],
    ) -> Path:
        """Generate comprehensive JSON report.

        Args:
            output_path: Path where JSON should be saved
            report_data: Complete report data dictionary

        Returns:
            Path to generated JSON file

        Examples:
            >>> generator = JSONReportGenerator()
            >>> report_data = {
            ...     "report_metadata": {...},
            ...     "evaluation_summary": {...},
            ...     "quality_metrics": {...}
            ... }
            >>> output_path = generator.generate_json_report(
            ...     Path("report.json"),
            ...     report_data
            ... )
        """
        # Write pretty-printed JSON with custom formatting
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str, ensure_ascii=False)

        return output_path

    @staticmethod
    def create_json_structure(
        validation_result: dict[str, Any],
        quality_metrics: dict[str, Any],
        metadata_completeness: dict[str, Any],
        missing_critical_fields: list[dict[str, Any]],
        file_info_with_provenance: dict[str, Any],
        recommendations: list[dict[str, Any]],
        llm_guidance: dict[str, Any] | None = None,
        workflow_trace: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create the complete JSON report structure.

        Args:
            validation_result: Validation result dictionary
            quality_metrics: Calculated quality metrics
            metadata_completeness: Metadata completeness info
            missing_critical_fields: List of missing critical fields
            file_info_with_provenance: File info with provenance tracking
            recommendations: List of recommendations
            llm_guidance: Optional LLM correction guidance
            workflow_trace: Optional workflow trace

        Returns:
            Complete JSON report structure
        """
        file_info_raw = validation_result.get("file_info", {})
        issues = validation_result.get("issues", [])
        issue_counts = validation_result.get("issue_counts", {})
        overall_status = validation_result.get("overall_status", "UNKNOWN")

        # Build comprehensive report
        report = {
            "report_metadata": {
                "version": "2.0",
                "generated_at": datetime.now().isoformat(),
                "session_id": validation_result.get("session_id", "unknown"),
                "system_version": "1.0.0",
            },
            "evaluation_summary": {
                "status": overall_status,
                "nwb_file_path": validation_result.get("nwb_file_path", ""),
                "file_format": file_info_raw.get("file_format", "NWB"),
                "timestamp": datetime.now().isoformat(),
            },
            "quality_metrics": {
                "completeness": quality_metrics.get("completeness", {}),
                "data_integrity": quality_metrics.get("integrity", {}),
                "scientific_value": quality_metrics.get("scientific_value", {}),
                "dandi_readiness": quality_metrics.get("dandi_ready", {}),
            },
            "metadata_completeness": {
                "percentage": metadata_completeness.get("percentage", 0),
                "filled_fields": metadata_completeness.get("filled", 0),
                "total_fields": metadata_completeness.get("total", 0),
                "required_filled": metadata_completeness.get("required_filled", 0),
                "required_total": metadata_completeness.get("required_total", 0),
                "critical_missing": metadata_completeness.get("critical_missing", 0),
            },
            "file_information": {
                "basic_info": {
                    "nwb_version": file_info_raw.get("nwb_version", "Unknown"),
                    "file_size_bytes": file_info_raw.get("file_size_bytes", 0),
                    "creation_date": file_info_raw.get("creation_date", "Unknown"),
                    "identifier": file_info_raw.get("identifier", "Unknown"),
                },
                "session_info": {
                    "session_description": file_info_raw.get("session_description"),
                    "session_start_time": file_info_raw.get("session_start_time"),
                    "session_id": file_info_raw.get("session_id"),
                },
                "experiment_info": {
                    "experimenter": file_info_raw.get("experimenter", []),
                    "institution": file_info_raw.get("institution"),
                    "lab": file_info_raw.get("lab"),
                    "experiment_description": file_info_raw.get("experiment_description"),
                },
                "subject_info": {
                    "subject_id": file_info_raw.get("subject_id"),
                    "species": file_info_raw.get("species"),
                    "sex": file_info_raw.get("sex"),
                    "age": file_info_raw.get("age"),
                    "date_of_birth": file_info_raw.get("date_of_birth"),
                    "description": file_info_raw.get("description"),
                    "genotype": file_info_raw.get("genotype"),
                    "strain": file_info_raw.get("strain"),
                },
                "metadata_with_provenance": file_info_with_provenance,
            },
            "validation_results": {
                "overall_status": overall_status,
                "total_issues": len(issues),
                "issue_counts": issue_counts,
                "issues_by_severity": JSONReportGenerator._group_issues_by_severity(issues),
            },
            "missing_critical_fields": missing_critical_fields,
            "recommendations": recommendations,
        }

        # Add workflow trace if available
        if workflow_trace:
            report["workflow_trace"] = workflow_trace

        # Add LLM analysis if available
        if llm_guidance:
            report["llm_analysis"] = {
                "executive_summary": llm_guidance.get("executive_summary", ""),
                "quality_assessment": llm_guidance.get("quality_assessment", {}),
                "recommendations": llm_guidance.get("recommendations", []),
                "key_insights": llm_guidance.get("key_insights", []),
                "dandi_ready": llm_guidance.get("dandi_ready", False),
                "dandi_blocking_issues": llm_guidance.get("dandi_blocking_issues", []),
            }

        return report

    @staticmethod
    def _group_issues_by_severity(issues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group issues by severity for the JSON report.

        Args:
            issues: List of validation issues

        Returns:
            Dictionary of issues grouped by severity
        """
        severity_groups: dict[str, list[dict[str, Any]]] = {
            "critical": [],
            "errors": [],
            "warnings": [],
            "info": [],
            "best_practice": [],
        }

        severity_mapping = {
            "CRITICAL": "critical",
            "ERROR": "errors",
            "WARNING": "warnings",
            "INFO": "info",
            "BEST_PRACTICE": "best_practice",
            "BEST_PRACTICE_VIOLATION": "best_practice",
            "BEST_PRACTICE_SUGGESTION": "best_practice",
        }

        for issue in issues:
            severity = issue.get("severity", "UNKNOWN")
            group = severity_mapping.get(severity, "info")

            issue_data = {
                "severity": issue.get("severity"),
                "check_name": issue.get("check_name", ""),
                "message": issue.get("message", ""),
                "location": issue.get("location", ""),
                "object_type": issue.get("object_type", ""),
                "context": issue.get("context"),
                "suggestion": issue.get("suggestion"),
                "fix": issue.get("fix"),
            }

            severity_groups[group].append(issue_data)

        return severity_groups
