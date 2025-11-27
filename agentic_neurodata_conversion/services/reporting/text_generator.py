"""Text report generator for NWB evaluation results.

Generates NWBInspector-style text reports with clear, structured output.
"""

import platform
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any


class TextReportGenerator:
    """Generates NWBInspector-style text reports for NWB validation results."""

    @staticmethod
    def generate_text_report(
        output_path: Path,
        validation_result: dict[str, Any],
        llm_analysis: dict[str, Any] | None = None,
    ) -> Path:
        """Generate text report in NWBInspector style.

        Args:
            output_path: Path where text report should be saved
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM quality assessment

        Returns:
            Path to generated text report

        Implements enhanced NWBInspector-style report format with:
        - Clear header with timestamp, platform, version
        - Issue summary with counts by severity
        - Detailed issues grouped by severity
        - LLM expert analysis (if available)
        """
        lines = TextReportGenerator._build_report_lines(validation_result, llm_analysis)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path

    @staticmethod
    def _build_report_lines(
        validation_result: dict[str, Any],
        llm_analysis: dict[str, Any] | None = None,
    ) -> list[str]:
        """Build the complete list of lines for the text report.

        Args:
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM analysis

        Returns:
            List of formatted text lines
        """
        lines = []

        # Header
        lines.extend(TextReportGenerator._build_header(validation_result))

        # Summary
        issues = validation_result.get("issues", [])
        issue_counts = validation_result.get("issue_counts", {})
        lines.extend(TextReportGenerator._build_summary(validation_result, issues, issue_counts))

        # Detailed issues
        if issues:
            lines.extend(TextReportGenerator._build_detailed_issues(validation_result, issues, issue_counts))

        # LLM analysis
        if llm_analysis:
            lines.extend(TextReportGenerator._build_llm_analysis(llm_analysis))

        return lines

    @staticmethod
    def _build_header(validation_result: dict[str, Any]) -> list[str]:
        """Build report header.

        Args:
            validation_result: Validation result dictionary

        Returns:
            List of header lines
        """
        lines = []
        lines.append("=" * 80)
        lines.append("NWBInspector Validation Report")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Timestamp:            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Platform:             {platform.platform()}")
        lines.append("NWBInspector version: 0.6.5")

        # Add file info
        file_info = validation_result.get("file_info", {})
        if file_info:
            lines.append(f"NWB version:          {file_info.get('nwb_version', 'Unknown')}")
            lines.append(f"File:                 {validation_result.get('nwb_file_path', 'Unknown')}")

        lines.append("")
        return lines

    @staticmethod
    def _build_summary(
        validation_result: dict[str, Any],
        issues: list[dict[str, Any]],
        issue_counts: dict[str, int],
    ) -> list[str]:
        """Build summary section.

        Args:
            validation_result: Validation result dictionary
            issues: List of validation issues
            issue_counts: Counts by severity

        Returns:
            List of summary lines
        """
        lines = []

        # Overall status
        overall_status = validation_result.get("overall_status", "UNKNOWN")
        if overall_status == "PASSED":
            status_line = f"✓ Status: {overall_status} - No critical issues found"
        elif overall_status == "PASSED_WITH_ISSUES":
            status_line = f"⚠ Status: {overall_status} - File passed with warnings"
        else:
            status_line = f"✗ Status: {overall_status} - Critical issues found"

        lines.append(status_line)
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

        # Issue counts
        total_issues = len(issues)
        if total_issues == 0:
            lines.append("✓ No validation issues found. File meets all NWB standards.")
            lines.append("")
        else:
            files_count = 1  # Single file for now
            lines.append(
                f"Found {total_issues} validation issue{'s' if total_issues != 1 else ''} "
                f"over {files_count} file{'s' if files_count != 1 else ''}:"
            )
            lines.append("")

            # Show counts by severity
            severity_display_order = [
                ("CRITICAL", "Critical errors"),
                ("ERROR", "Errors"),
                ("WARNING", "Warnings"),
                ("BEST_PRACTICE_VIOLATION", "Best practice violations"),
                ("BEST_PRACTICE_SUGGESTION", "Best practice suggestions"),
            ]

            for severity, display_name in severity_display_order:
                count = issue_counts.get(severity, 0)
                if count > 0:
                    lines.append(f"  • {count:3d} {display_name}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("")

        return lines

    @staticmethod
    def _build_detailed_issues(
        validation_result: dict[str, Any],
        issues: list[dict[str, Any]],
        issue_counts: dict[str, int],
    ) -> list[str]:
        """Build detailed issues section.

        Args:
            validation_result: Validation result dictionary
            issues: List of validation issues
            issue_counts: Counts by severity

        Returns:
            List of detailed issue lines
        """
        lines = []

        # Group issues by severity
        issues_by_severity: dict[str, list[dict[str, Any]]] = {}
        for issue in issues:
            severity = issue.get("severity", "UNKNOWN")
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)

        # Print issues by severity
        severity_order = ["CRITICAL", "ERROR", "WARNING", "BEST_PRACTICE_VIOLATION", "BEST_PRACTICE_SUGGESTION"]

        for sev_idx, severity in enumerate(severity_order):
            if severity not in issues_by_severity:
                continue

            issues_list = issues_by_severity[severity]
            if not issues_list:
                continue

            # Section header
            severity_display = severity.replace("_", " ").title()
            lines.append("")
            lines.append(f"[{sev_idx + 1}] {severity_display}")
            lines.append("-" * 80)
            lines.append("")

            for issue_idx, issue in enumerate(issues_list, 1):
                nwb_file = validation_result.get("nwb_file_path", "Unknown file")
                check_name = issue.get("check_name", "unknown_check")
                object_type = issue.get("object_type", "NWBFile")
                location = issue.get("location", "/")
                message = issue.get("message", "No message")

                lines.append(f"[{sev_idx + 1}.{issue_idx}] {check_name}")
                lines.append(f"      File:     {nwb_file}")
                lines.append(f"      Object:   '{object_type}' at location '{location}'")
                lines.append(f"      Message:  {message}")

                # Add impact warning for critical/error
                if severity in ["CRITICAL", "ERROR"]:
                    lines.append("      Impact:   ⚠ This issue may prevent DANDI archive submission")

                lines.append("")

        # Footer summary
        total_issues = len(issues)
        if total_issues > 0:
            lines.append("")
            lines.append("=" * 80)
            lines.append("")
            lines.append("Summary:")
            lines.append(f"  Total issues:          {total_issues}")
            lines.append(f"  Critical/Error issues: {issue_counts.get('CRITICAL', 0) + issue_counts.get('ERROR', 0)}")
            lines.append(
                f"  Best practice issues:  "
                f"{issue_counts.get('BEST_PRACTICE_VIOLATION', 0) + issue_counts.get('BEST_PRACTICE_SUGGESTION', 0)}"
            )
            lines.append("")

            # DANDI readiness
            critical_count = issue_counts.get("CRITICAL", 0) + issue_counts.get("ERROR", 0)
            if critical_count == 0:
                lines.append("✓ DANDI Readiness: This file is ready for DANDI archive submission.")
            else:
                lines.append(
                    f"✗ DANDI Readiness: {critical_count} critical issue{'s' if critical_count != 1 else ''} "
                    f"must be fixed before DANDI submission."
                )

            lines.append("")
            lines.append("=" * 80)

        return lines

    @staticmethod
    def _build_llm_analysis(llm_analysis: dict[str, Any]) -> list[str]:
        """Build LLM analysis section.

        Args:
            llm_analysis: LLM analysis dictionary

        Returns:
            List of LLM analysis lines
        """
        lines = []

        lines.append("")
        lines.append("")
        lines.append("=" * 80)
        lines.append("EXPERT ANALYSIS (AI-Powered)")
        lines.append("=" * 80)
        lines.append("")

        # Executive Summary
        if "executive_summary" in llm_analysis:
            lines.append("Executive Summary:")
            lines.append("-" * 80)
            summary_text = llm_analysis["executive_summary"]
            wrapped_summary = textwrap.fill(summary_text, width=78, initial_indent="  ", subsequent_indent="  ")
            lines.append(wrapped_summary)
            lines.append("")

        # Quality Assessment
        quality_assessment = llm_analysis.get("quality_assessment", {})
        if quality_assessment:
            lines.append("Quality Metrics:")
            lines.append("-" * 80)

            if "completeness_score" in quality_assessment:
                lines.append(f"  • Data Completeness:    {quality_assessment['completeness_score']}")
            if "metadata_quality" in quality_assessment:
                lines.append(f"  • Metadata Quality:     {quality_assessment['metadata_quality']}")
            if "data_integrity" in quality_assessment:
                lines.append(f"  • Data Integrity:       {quality_assessment['data_integrity']}")
            if "scientific_value" in quality_assessment:
                lines.append(f"  • Scientific Value:     {quality_assessment['scientific_value']}")

            lines.append("")

        # Recommendations
        recommendations = llm_analysis.get("recommendations", [])
        if recommendations:
            lines.append("Recommendations:")
            lines.append("-" * 80)
            for i, rec in enumerate(recommendations, 1):
                wrapped_rec = textwrap.fill(f"{i}. {rec}", width=78, initial_indent="  ", subsequent_indent="     ")
                lines.append(wrapped_rec)
            lines.append("")

        # DANDI Readiness
        dandi_ready = llm_analysis.get("dandi_ready", False)
        lines.append("DANDI Readiness Assessment:")
        lines.append("-" * 80)
        if dandi_ready:
            lines.append("  ✓ This file is ready for DANDI archive submission")
        else:
            lines.append("  ⚠ Additional improvements recommended before DANDI submission")
        lines.append("")

        lines.append("=" * 80)

        return lines
