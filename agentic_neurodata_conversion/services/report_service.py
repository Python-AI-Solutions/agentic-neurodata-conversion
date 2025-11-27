"""Report generation service for NWB evaluation results.

Implements Tasks T050, T051: HTML, JSON, and Text report generation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Import shared formatters and generators
from .reporting.formatters import ReportFormatters
from .reporting.html_generator import HTMLReportGenerator
from .reporting.json_generator import JSONReportGenerator
from .reporting.text_generator import TextReportGenerator


class ReportService:
    """Service for generating NWB evaluation reports.

    Supports HTML, JSON, and Text formats for all validation outcomes.

    NOTE: This class is being refactored. Formatting utilities have been
    extracted to reporting/formatters.py. Additional refactoring in progress.
    """

    # Keep class constants for backwards compatibility
    # (delegating to ReportFormatters for actual implementation)
    SPECIES_COMMON_NAMES = ReportFormatters.SPECIES_COMMON_NAMES
    SEX_CODES = ReportFormatters.SEX_CODES

    def __init__(self):
        """Initialize report service."""
        self._formatters = ReportFormatters()
        self._html_generator = HTMLReportGenerator()
        self._json_generator = JSONReportGenerator()
        self._text_generator = TextReportGenerator()

    def _format_species(self, species: str) -> str:
        """Format species with common name if known.

        Delegates to ReportFormatters for implementation.
        """
        return self._formatters.format_species(species)

    def _format_sex(self, sex_code: str) -> str:
        """Expand sex code to full word.

        Delegates to ReportFormatters for implementation.
        """
        return self._formatters.format_sex(sex_code)

    def _format_age(self, iso_age: str) -> str:
        """Convert ISO 8601 duration to human-readable format.

        Delegates to ReportFormatters for implementation.
        """
        return self._formatters.format_age(iso_age)

    def _format_with_provenance(
        self,
        value: str,
        provenance: str,
        source_file: str | None = None,
        confidence: float | None = None,
        source_description: str | None = None,
    ) -> str:
        """Format a value with its provenance badge for display in reports.

        Args:
            value: The field value
            provenance: Provenance type (user-specified, ai-parsed, etc.)
            source_file: Source file path for file-extracted provenance
            confidence: Confidence score (0-100) for AI operations
            source_description: Description of where the value came from

        Delegates to ReportFormatters for implementation.
        """
        return self._formatters.format_with_provenance(value, provenance, source_file, confidence, source_description)

    def generate_json_report(
        self,
        output_path: Path,
        validation_result: dict[str, Any],
        llm_guidance: dict[str, Any] | None = None,
        workflow_trace: dict[str, Any] | None = None,
    ) -> Path:
        """Generate comprehensive JSON report for validation results.

        Args:
            output_path: Path where JSON should be saved
            validation_result: Validation result dictionary
            llm_guidance: Optional LLM correction guidance or analysis
            workflow_trace: Optional workflow trace for transparency

        Returns:
            Path to generated JSON

        Implements comprehensive JSON reporting with:
        - Detailed evaluation metadata
        - Quality metrics dashboard
        - Complete file information with provenance
        - All validation issues with context
        - Metadata provenance tracking
        - Workflow trace for reproducibility
        - LLM analysis and recommendations
        """
        file_info_raw = validation_result.get("file_info", {})
        issues = validation_result.get("issues", [])
        issue_counts = validation_result.get("issue_counts", {})
        overall_status = validation_result.get("overall_status", "UNKNOWN")

        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(validation_result, file_info_raw, issue_counts)

        # Calculate metadata completeness
        metadata_completeness = self._calculate_metadata_completeness(file_info_raw)

        # Identify missing critical fields
        missing_critical_fields = self._identify_missing_critical_fields(file_info_raw, issues)

        # Prepare file info with provenance
        file_info_with_provenance = self._prepare_file_info(file_info_raw, workflow_trace)

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
                "summary": self._generate_summary(validation_result),
                "timestamp": datetime.now().isoformat(),
            },
            "quality_metrics": {
                "completeness": quality_metrics.get("completeness", {}),
                "data_integrity": quality_metrics.get("integrity", {}),
                "scientific_value": quality_metrics.get("scientific_value", {}),
                "dandi_readiness": quality_metrics.get("dandi_ready", {}),
                "overall_score": self._calculate_quality_score(validation_result),
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
                    "file_size_readable": self._format_filesize(file_info_raw.get("file_size_bytes", 0)),
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
                "issues_by_severity": {
                    "critical": [
                        {
                            "severity": issue.get("severity"),
                            "check_name": issue.get("check_name", ""),
                            "message": issue.get("message", ""),
                            "location": issue.get("location", ""),
                            "object_type": issue.get("object_type", ""),
                            "context": issue.get("context"),
                            "suggestion": issue.get("suggestion"),
                            "fix": issue.get("fix"),
                        }
                        for issue in issues
                        if issue.get("severity") == "CRITICAL"
                    ],
                    "errors": [
                        {
                            "severity": issue.get("severity"),
                            "check_name": issue.get("check_name", ""),
                            "message": issue.get("message", ""),
                            "location": issue.get("location", ""),
                            "object_type": issue.get("object_type", ""),
                            "context": issue.get("context"),
                            "suggestion": issue.get("suggestion"),
                            "fix": issue.get("fix"),
                        }
                        for issue in issues
                        if issue.get("severity") == "ERROR"
                    ],
                    "warnings": [
                        {
                            "severity": issue.get("severity"),
                            "check_name": issue.get("check_name", ""),
                            "message": issue.get("message", ""),
                            "location": issue.get("location", ""),
                            "object_type": issue.get("object_type", ""),
                            "context": issue.get("context"),
                            "suggestion": issue.get("suggestion"),
                        }
                        for issue in issues
                        if issue.get("severity") == "WARNING"
                    ],
                    "info": [
                        {
                            "severity": issue.get("severity"),
                            "check_name": issue.get("check_name", ""),
                            "message": issue.get("message", ""),
                            "location": issue.get("location", ""),
                        }
                        for issue in issues
                        if issue.get("severity") in ["INFO", "BEST_PRACTICE"]
                    ],
                },
                "best_practices": self._extract_best_practices(validation_result),
            },
            "missing_critical_fields": [
                {
                    "field_name": field["name"],
                    "fix_hint": field["fix_hint"],
                    "impact": field["impact"],
                }
                for field in missing_critical_fields
            ],
        }

        # Add metadata provenance tracking
        if workflow_trace and "metadata_provenance" in workflow_trace:
            metadata_prov = workflow_trace["metadata_provenance"]
            report["metadata_provenance"] = {
                "summary": {
                    "total_fields": len(metadata_prov),
                    "needs_review_count": sum(1 for p in metadata_prov.values() if p.get("needs_review", False)),
                    "provenance_breakdown": {},
                    "confidence_distribution": {
                        "high": 0,  # >= 80%
                        "medium": 0,  # 50-79%
                        "low": 0,  # < 50%
                    },
                },
                "fields": {},
            }

            # Calculate provenance breakdown and confidence distribution
            for field_name, prov_info in metadata_prov.items():
                prov_type = prov_info.get("provenance", "unknown")
                # Type-safe nested dict access
                prov_breakdown: dict[str, int] = report["metadata_provenance"]["summary"]["provenance_breakdown"]  # type: ignore[index]
                if prov_type not in prov_breakdown:
                    prov_breakdown[prov_type] = 0
                prov_breakdown[prov_type] += 1

                # Confidence distribution
                confidence = prov_info.get("confidence", 0)
                conf_dist: dict[str, int] = report["metadata_provenance"]["summary"]["confidence_distribution"]  # type: ignore[index]
                if confidence >= 80:
                    conf_dist["high"] += 1
                elif confidence >= 50:
                    conf_dist["medium"] += 1
                else:
                    conf_dist["low"] += 1

                # Add field-level provenance
                fields_dict: dict[str, Any] = report["metadata_provenance"]["fields"]  # type: ignore[index]
                fields_dict[field_name] = {
                    "value": file_info_raw.get(field_name),
                    "provenance": prov_type,
                    "confidence": confidence,
                    "source": prov_info.get("source"),
                    "needs_review": prov_info.get("needs_review", False),
                }

        # Add workflow trace for transparency and reproducibility
        if workflow_trace:
            report["workflow_trace"] = {
                "summary": workflow_trace.get("summary", {}),
                "steps": workflow_trace.get("steps", []),
                "technologies": workflow_trace.get("technologies", []),
                "provenance": workflow_trace.get("provenance", {}),
                "detailed_logs": workflow_trace.get("detailed_logs", {}),
            }

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

        # Add recommendations
        report["recommendations"] = self._generate_recommendations(validation_result, llm_guidance)

        # Write pretty-printed JSON with custom formatting
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str, ensure_ascii=False)

        return output_path

    def generate_text_report(
        self,
        output_path: Path,
        validation_result: dict[str, Any],
        llm_analysis: dict[str, Any] | None = None,
        workflow_trace: dict[str, Any] | None = None,
    ) -> Path:
        """Generate text report in NWB Inspector style (clear and structured).

        Args:
            output_path: Path where text report should be saved
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM quality assessment and recommendations

        Returns:
            Path to generated text report

        Implements enhanced NWBInspector-style report format with:
        - Clear header with timestamp, platform, version
        - Issue summary with counts by severity
        - Detailed issues grouped by severity with file paths and locations
        - LLM expert analysis and recommendations (if available)
        """
        import platform
        from datetime import datetime

        lines = []

        # Header with stars separator
        lines.append("=" * 80)
        lines.append("NWBInspector Validation Report")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Timestamp:            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Platform:             {platform.platform()}")
        lines.append("NWBInspector version: 0.6.5")

        # Add file info if available
        file_info = validation_result.get("file_info", {})
        if file_info:
            lines.append(f"NWB version:          {file_info.get('nwb_version', 'Unknown')}")
            lines.append(f"File:                 {validation_result.get('nwb_file_path', 'Unknown')}")

        lines.append("")

        # Overall status badge
        overall_status = validation_result.get("overall_status", "UNKNOWN")
        status_line = f"Status: {overall_status}"
        if overall_status == "PASSED":
            status_line = f"✓ {status_line} - No critical issues found"
        elif overall_status == "PASSED_WITH_ISSUES":
            status_line = f"⚠ {status_line} - File passed with warnings"
        else:
            status_line = f"✗ {status_line} - Critical issues found"

        lines.append(status_line)
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

        # Summary of issues
        issues = validation_result.get("issues", [])
        issue_counts = validation_result.get("issue_counts", {})
        total_issues = len(issues)
        files_count = 1  # Single file for now

        if total_issues == 0:
            lines.append("✓ No validation issues found. File meets all NWB standards.")
            lines.append("")
        else:
            lines.append(
                f"Found {total_issues} validation issue{'s' if total_issues != 1 else ''} over {files_count} file{'s' if files_count != 1 else ''}:"
            )
            lines.append("")

            # Sort severity by importance and show counts
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

        # Group issues by severity
        issues_by_severity: dict[str, list[dict[str, Any]]] = {}
        for issue in issues:
            severity = issue.get("severity", "UNKNOWN")
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)

        # Print detailed issues grouped by severity
        severity_order = ["CRITICAL", "ERROR", "WARNING", "BEST_PRACTICE_VIOLATION", "BEST_PRACTICE_SUGGESTION"]

        for sev_idx, severity in enumerate(severity_order):
            if severity not in issues_by_severity:
                continue

            issues_list = issues_by_severity[severity]
            if not issues_list:
                continue

            # Section header for this severity
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

                # Format: [sev_idx.issue_idx] File: check_name
                lines.append(f"[{sev_idx + 1}.{issue_idx}] {check_name}")
                lines.append(f"      File:     {nwb_file}")
                lines.append(f"      Object:   '{object_type}' at location '{location}'")
                lines.append(f"      Message:  {message}")

                # Add importance indicator for critical/error
                if severity in ["CRITICAL", "ERROR"]:
                    lines.append("      Impact:   ⚠ This issue may prevent DANDI archive submission")

                lines.append("")

        # Footer
        if total_issues > 0:
            lines.append("")
            lines.append("=" * 80)
            lines.append("")
            lines.append("Summary:")
            lines.append(f"  Total issues:          {total_issues}")
            lines.append(f"  Critical/Error issues: {issue_counts.get('CRITICAL', 0) + issue_counts.get('ERROR', 0)}")
            lines.append(
                f"  Best practice issues:  {issue_counts.get('BEST_PRACTICE_VIOLATION', 0) + issue_counts.get('BEST_PRACTICE_SUGGESTION', 0)}"
            )
            lines.append("")

            # DANDI readiness assessment
            critical_count = issue_counts.get("CRITICAL", 0) + issue_counts.get("ERROR", 0)
            if critical_count == 0:
                lines.append("✓ DANDI Readiness: This file is ready for DANDI archive submission.")
            else:
                lines.append(
                    f"✗ DANDI Readiness: {critical_count} critical issue{'s' if critical_count != 1 else ''} must be fixed before DANDI submission."
                )

            lines.append("")
            lines.append("=" * 80)

        # LLM Expert Analysis Section (if available)
        if llm_analysis:
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
                # Word wrap the summary to 80 characters
                import textwrap

                wrapped_summary = textwrap.fill(summary_text, width=78, initial_indent="  ", subsequent_indent="  ")
                lines.append(wrapped_summary)
                lines.append("")

            # Quality Assessment Scores
            quality_assessment = llm_analysis.get("quality_assessment", {})
            if quality_assessment:
                lines.append("Quality Metrics:")
                lines.append("-" * 80)

                if "completeness_score" in quality_assessment:
                    score = quality_assessment["completeness_score"]
                    lines.append(f"  • Data Completeness:    {score}")

                if "metadata_quality" in quality_assessment:
                    quality = quality_assessment["metadata_quality"]
                    lines.append(f"  • Metadata Quality:     {quality}")

                if "data_integrity" in quality_assessment:
                    integrity = quality_assessment["data_integrity"]
                    lines.append(f"  • Data Integrity:       {integrity}")

                if "scientific_value" in quality_assessment:
                    value = quality_assessment["scientific_value"]
                    lines.append(f"  • Scientific Value:     {value}")

                lines.append("")

            # Recommendations
            recommendations = llm_analysis.get("recommendations", [])
            if recommendations:
                lines.append("Expert Recommendations:")
                lines.append("-" * 80)
                for i, rec in enumerate(recommendations, 1):
                    # Word wrap recommendations
                    import textwrap

                    wrapped_rec = textwrap.fill(rec, width=76, initial_indent=f"  {i}. ", subsequent_indent="     ")
                    lines.append(wrapped_rec)
                    lines.append("")

            # Key Insights
            if "key_insights" in llm_analysis:
                insights = llm_analysis["key_insights"]
                if isinstance(insights, list) and insights:
                    lines.append("Key Insights:")
                    lines.append("-" * 80)
                    for insight in insights:
                        import textwrap

                        wrapped_insight = textwrap.fill(
                            insight, width=76, initial_indent="  • ", subsequent_indent="    "
                        )
                        lines.append(wrapped_insight)
                    lines.append("")

            # DANDI Readiness from LLM
            if "dandi_ready" in llm_analysis:
                lines.append("")
                dandi_ready = llm_analysis["dandi_ready"]
                if dandi_ready:
                    lines.append("✓ DANDI Archive Status: Ready for submission")
                else:
                    lines.append("⚠ DANDI Archive Status: Improvements recommended before submission")

                if "dandi_blocking_issues" in llm_analysis:
                    blocking = llm_analysis["dandi_blocking_issues"]
                    if blocking:
                        lines.append("")
                        lines.append("  Blocking Issues:")
                        for issue in blocking:
                            import textwrap

                            wrapped_issue = textwrap.fill(
                                issue, width=74, initial_indent="    - ", subsequent_indent="      "
                            )
                            lines.append(wrapped_issue)

            lines.append("")
            lines.append("=" * 80)
            lines.append("")
            lines.append("This analysis was generated by an AI expert system trained on NWB standards")
            lines.append("and DANDI archive requirements. Review recommendations in context of your")
            lines.append("specific research needs.")
            lines.append("=" * 80)

        # Workflow Trace Section (for transparency and reproducibility)
        if workflow_trace:
            lines.append("")
            lines.append("")
            lines.append("=" * 80)
            lines.append("COMPLETE WORKFLOW TRACE")
            lines.append("=" * 80)
            lines.append("")
            lines.append("For scientific transparency and reproducibility, this section documents")
            lines.append("the complete conversion process from start to end.")
            lines.append("")
            lines.append("-" * 80)
            lines.append("")

            # Process Summary
            if "summary" in workflow_trace:
                summary = workflow_trace["summary"]
                lines.append("Process Summary:")
                lines.append("-" * 80)
                lines.append(f"  Start Time:       {summary.get('start_time', 'N/A')}")
                lines.append(f"  End Time:         {summary.get('end_time', 'N/A')}")
                lines.append(f"  Total Duration:   {summary.get('duration', 'N/A')}")
                lines.append(f"  Input Format:     {summary.get('input_format', 'N/A')}")
                lines.append("  Output Format:    NWB (Neurodata Without Borders)")
                lines.append("")

            # Technologies Used
            if "technologies" in workflow_trace:
                lines.append("Technologies & Standards:")
                lines.append("-" * 80)
                for tech in workflow_trace["technologies"]:
                    lines.append(f"  • {tech}")
                lines.append("")

            # Workflow Steps
            if "steps" in workflow_trace:
                lines.append("Conversion Pipeline Steps:")
                lines.append("-" * 80)
                lines.append("")
                for i, step in enumerate(workflow_trace["steps"], 1):
                    lines.append(f"Step {i}: {step.get('name', 'Unknown Step')}")
                    lines.append(f"  Status: {step.get('status', 'N/A')}")
                    if step.get("description"):
                        import textwrap

                        wrapped_desc = textwrap.fill(
                            step["description"], width=76, initial_indent="  ", subsequent_indent="  "
                        )
                        lines.append(wrapped_desc)
                    if step.get("duration"):
                        lines.append(f"  Duration: {step['duration']}")
                    if step.get("timestamp"):
                        lines.append(f"  Timestamp: {step['timestamp']}")
                    lines.append("")

            # Data Provenance
            if "provenance" in workflow_trace:
                lines.append("Data Provenance:")
                lines.append("-" * 80)
                prov = workflow_trace["provenance"]
                if "original_file" in prov:
                    lines.append(f"  Original Data:      {prov['original_file']}")
                if "conversion_method" in prov:
                    lines.append(f"  Conversion Method:  {prov['conversion_method']}")
                if "metadata_sources" in prov:
                    sources = ", ".join(prov["metadata_sources"])
                    lines.append(f"  Metadata Sources:   {sources}")
                if "agent_versions" in prov:
                    lines.append(f"  Agent Versions:     {prov['agent_versions']}")
                lines.append("")

            # User Interactions
            if "user_interactions" in workflow_trace:
                lines.append("User Interactions:")
                lines.append("-" * 80)
                for interaction in workflow_trace["user_interactions"]:
                    lines.append(f"  • {interaction.get('timestamp', 'N/A')}: {interaction.get('action', 'N/A')}")
                lines.append("")

            # Reproducibility Footer
            lines.append("")
            lines.append("=" * 80)
            lines.append("")
            lines.append("NOTE ON REPRODUCIBILITY:")
            lines.append("")
            lines.append("This workflow trace enables independent verification and reproduction")
            lines.append("of the conversion process. All steps, technologies, data sources, and")
            lines.append("user interactions are documented to meet scientific transparency standards")
            lines.append("required by the neuroscience community and DANDI archive.")
            lines.append("")
            lines.append("This level of documentation ensures:")
            lines.append("  • Full transparency of the conversion process")
            lines.append("  • Ability to reproduce results independently")
            lines.append("  • Compliance with FAIR data principles")
            lines.append("  • Trust in the scientific community")
            lines.append("")
            lines.append("=" * 80)

        # Write to file
        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        return output_path

    def generate_html_report(
        self,
        output_path: Path,
        validation_result: dict[str, Any],
        llm_analysis: dict[str, Any] | None = None,
        workflow_trace: dict[str, Any] | None = None,
    ) -> Path:
        """Generate standalone HTML report for NWB evaluation results.

        Args:
            output_path: Path where HTML should be saved
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM quality assessment
            workflow_trace: Optional workflow trace for provenance

        Returns:
            Path to generated HTML

        Implements interactive HTML reporting with embedded CSS/JS.
        Delegates to HTMLReportGenerator for rendering.
        """
        # Prepare template data
        template_data = self._prepare_template_data(validation_result, llm_analysis, workflow_trace)

        # Prepare Jinja2 custom filters
        jinja_filters = {
            "format_timestamp": self._filter_format_timestamp,
            "format_duration": self._filter_format_duration,
            "format_field_name": self._filter_format_field_name,
            "format_provenance_badge": self._filter_format_provenance_badge,
            "format_provenance_tooltip": self._filter_format_provenance_tooltip,
            "format_year": self._filter_format_year,
        }

        # Delegate to HTML generator
        return self._html_generator.generate_html_report(output_path, template_data, jinja_filters)

    def _prepare_template_data(
        self,
        validation_result: dict[str, Any],
        llm_analysis: dict[str, Any] | None,
        workflow_trace: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Prepare data for HTML template rendering.

        Args:
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM quality assessment
            workflow_trace: Optional workflow trace

        Returns:
            Dictionary of template variables
        """
        from datetime import datetime

        # Extract basic info
        file_info_raw = validation_result.get("file_info", {})
        issues = validation_result.get("issues", [])
        issue_counts = validation_result.get("issue_counts", {})

        # Prepare report data
        report_data = {
            "session_id": validation_result.get("session_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "status": validation_result.get("overall_status", "UNKNOWN"),
            "file_name": validation_result.get("nwb_file_path", "Unknown").split("/")[-1],
            "file_format": file_info_raw.get("file_format", "NWB"),
            "summary": self._generate_summary(validation_result),
            "system_version": "1.0.0",
        }

        # Prepare file info with provenance
        file_info = self._prepare_file_info(file_info_raw, workflow_trace)

        # Calculate validation results
        total_checks = sum(issue_counts.values())
        passed_checks = max(0, total_checks - issue_counts.get("CRITICAL", 0) - issue_counts.get("ERROR", 0))
        quality_score = self._calculate_quality_score(validation_result)

        validation_results = {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "warnings": issue_counts.get("WARNING", 0),
            "errors": issue_counts.get("ERROR", 0),
            "critical": issue_counts.get("CRITICAL", 0),
            "quality_score": quality_score,
            "summary": validation_result.get("summary", ""),
            "best_practices": self._extract_best_practices(validation_result),
        }

        # Prepare issues with enhanced formatting
        enhanced_issues = self._prepare_issues(issues)

        # Prepare recommendations
        recommendations = self._generate_recommendations(validation_result, llm_analysis)

        # Prepare workflow trace
        workflow_trace_formatted = self._prepare_workflow_trace(workflow_trace)

        # Extract missing fields
        missing_fields = file_info_raw.get("_missing_fields", [])

        # ===== ENHANCED REPORT DATA =====

        # Calculate missing critical fields for DANDI
        missing_critical_fields = self._identify_missing_critical_fields(file_info_raw, issues)

        # Calculate quality metrics for dashboard
        quality_metrics = self._calculate_quality_metrics(validation_result, file_info_raw, issue_counts)

        # Calculate metadata completeness
        metadata_completeness = self._calculate_metadata_completeness(file_info_raw)

        # Group issues by severity for quick actions
        issues_by_severity: dict[str, list[dict[str, Any]]] = {}
        for issue in enhanced_issues:
            severity = issue.get("severity", "UNKNOWN")
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)

        # Calculate total estimated time to fix all issues
        total_estimated_time = self._estimate_fix_time(missing_critical_fields, issues_by_severity)

        # Extract detailed logs (sequential view) and log file path from workflow_trace if available
        detailed_logs_sequential = workflow_trace.get("detailed_logs_sequential", []) if workflow_trace else []
        stage_options = workflow_trace.get("stage_options", []) if workflow_trace else []
        log_file_path = workflow_trace.get("log_file_path") if workflow_trace else None

        return {
            "report_data": report_data,
            "file_info": file_info,
            "missing_fields": missing_fields,
            "validation_results": validation_results,
            "issues": enhanced_issues,
            "recommendations": recommendations,
            "workflow_trace": workflow_trace_formatted,
            # Enhanced report data
            "missing_critical_fields": missing_critical_fields,
            "quality_metrics": quality_metrics,
            "metadata_completeness": metadata_completeness,
            "issues_by_severity": issues_by_severity,
            "total_estimated_time": total_estimated_time,
            # Detailed process logs for scientific transparency (sequential view)
            "detailed_logs_sequential": detailed_logs_sequential,
            "stage_options": stage_options,
            "log_file_path": log_file_path,
        }

    def _prepare_file_info(
        self, file_info_raw: dict[str, Any], workflow_trace: dict[str, Any] | None
    ) -> dict[str, dict[str, Any]]:
        """Prepare file info with provenance badges."""
        provenance = file_info_raw.get("_provenance", {})
        file_info_raw.get("_source_files", {})
        full_provenance = {}

        # Prioritize _workflow_provenance from file_info_raw (added in main.py for report regeneration)
        # This contains the original AI-parsed provenance with confidence scores and source text
        if "_workflow_provenance" in file_info_raw:
            full_provenance = file_info_raw["_workflow_provenance"]
        elif workflow_trace and "metadata_provenance" in workflow_trace:
            full_provenance = workflow_trace["metadata_provenance"]

        file_info = {}
        for key, value in file_info_raw.items():
            if key.startswith("_"):
                continue

            # Prioritize workflow_trace provenance (original sources: AI-parsed, user-specified, etc.)
            # over file_info_raw provenance (which is all "file-extracted" when reading NWB)
            if key in full_provenance:
                prov_info = full_provenance[key]
                file_info[key] = {
                    "value": value,
                    "provenance": prov_info.get("provenance"),
                    "confidence": prov_info.get("confidence"),
                    "source": prov_info.get("source"),
                    "needs_review": prov_info.get("needs_review", False),
                }
            else:
                # Fallback to file_info_raw provenance if not in workflow_trace
                file_info[key] = {
                    "value": value,
                    "provenance": provenance.get(key, "system-default"),
                    "needs_review": False,
                }

        return file_info

    def _prepare_issues(self, issues: list) -> list:
        """Prepare issues with enhanced formatting."""
        enhanced_issues = []
        for issue in issues:
            enhanced_issues.append(
                {
                    "severity": issue.get("severity", "UNKNOWN"),
                    "title": issue.get("check_name", "Unknown Issue"),
                    "message": issue.get("message", ""),
                    "location": issue.get("location", ""),
                    "context": issue.get("context"),
                    "suggestion": issue.get("suggestion"),
                    "fix": issue.get("fix"),
                    "code_snippet": issue.get("code_snippet"),
                    "references": issue.get("references", []),
                    "check_name": issue.get("check_name", ""),
                    "timestamp": issue.get("timestamp"),
                }
            )
        return enhanced_issues

    def _generate_recommendations(self, validation_result: dict[str, Any], llm_analysis: dict[str, Any] | None) -> list:
        """Generate recommendations based on validation results."""
        recommendations = []
        issue_counts = validation_result.get("issue_counts", {})

        # Critical/Error issues
        if issue_counts.get("CRITICAL", 0) > 0 or issue_counts.get("ERROR", 0) > 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "title": "Fix Critical/Error Issues",
                    "description": "Resolve validation errors before sharing or archiving the file.",
                    "action_items": [
                        "Review each critical and error issue",
                        "Apply suggested fixes",
                        "Re-validate the file",
                    ],
                    "expected_outcome": "File passes validation without critical errors",
                }
            )

        # Warnings
        if issue_counts.get("WARNING", 0) > 0:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "title": "Address Warning Issues",
                    "description": "Review warnings to improve data quality and compatibility.",
                    "action_items": [
                        "Review each warning",
                        "Determine if fixes are needed for your use case",
                    ],
                    "expected_outcome": "Improved data quality and DANDI compliance",
                }
            )

        # Add LLM recommendations if available
        if llm_analysis and "recommendations" in llm_analysis:
            for rec_text in llm_analysis["recommendations"][:3]:
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "title": "Expert Recommendation",
                        "description": rec_text,
                        "action_items": [],
                    }
                )

        return recommendations

    def _prepare_workflow_trace(self, workflow_trace: dict[str, Any] | None) -> list:
        """Prepare workflow trace for timeline display."""
        if not workflow_trace or "steps" not in workflow_trace:
            return []

        formatted_steps = []
        for step in workflow_trace.get("steps", []):
            formatted_steps.append(
                {
                    "step_name": step.get("name", "Unknown Step"),
                    "status": step.get("status", "UNKNOWN"),
                    "description": step.get("description", ""),
                    "details": step.get("details"),
                    "duration_ms": step.get("duration_ms"),
                    "timestamp": step.get("timestamp"),
                    "error": step.get("error"),
                    "warnings": step.get("warnings", []),
                }
            )

        return formatted_steps

    def _calculate_quality_score(self, validation_result: dict[str, Any]) -> float:
        """Calculate overall quality score (0-100)."""
        issue_counts = validation_result.get("issue_counts", {})
        file_info = validation_result.get("file_info", {})

        # Start with 100
        score = 100.0

        # Deduct for issues
        score -= issue_counts.get("CRITICAL", 0) * 20
        score -= issue_counts.get("ERROR", 0) * 10
        score -= issue_counts.get("WARNING", 0) * 5
        score -= issue_counts.get("BEST_PRACTICE", 0) * 2

        # Deduct for missing metadata
        metadata_fields = [
            "experimenter",
            "institution",
            "lab",
            "session_description",
            "subject_id",
            "species",
            "sex",
            "age",
        ]
        missing_metadata = sum(
            1 for field in metadata_fields if not file_info.get(field) or file_info.get(field) in ["N/A", "Unknown", ""]
        )
        score -= missing_metadata * 2

        return float(max(0.0, min(100.0, score)))

    def _extract_best_practices(self, validation_result: dict[str, Any]) -> dict[str, str]:
        """Extract best practices compliance from validation results."""
        # This could be enhanced based on specific checks
        issue_counts = validation_result.get("issue_counts", {})

        return {
            "NWB Standard Compliance": "PASS" if issue_counts.get("CRITICAL", 0) == 0 else "FAIL",
            "Metadata Completeness": "PASS" if issue_counts.get("ERROR", 0) == 0 else "FAIL",
            "DANDI Requirements": "PASS" if issue_counts.get("WARNING", 0) == 0 else "PARTIAL",
            "Best Practices": "PASS" if issue_counts.get("BEST_PRACTICE", 0) == 0 else "FAIL",
        }

    def _generate_summary(self, validation_result: dict[str, Any]) -> str:
        """Generate a human-readable summary of validation results."""
        status = validation_result.get("overall_status", "UNKNOWN")
        issue_counts = validation_result.get("issue_counts", {})
        total_issues = sum(issue_counts.values())

        if status == "PASSED" or total_issues == 0:
            return "All validation checks passed successfully. The file meets NWB standards and is ready for use."
        elif status == "PASSED_WITH_ISSUES":
            return f"Validation passed with {total_issues} warnings. Review recommendations for improvements."
        else:
            critical = issue_counts.get("CRITICAL", 0) + issue_counts.get("ERROR", 0)
            return f"Validation found {critical} critical issues that must be resolved before the file can be used."

    # Custom Jinja2 filters
    def _filter_format_timestamp(self, timestamp_str: str) -> str:
        """Format ISO timestamp to human-readable format."""
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            return timestamp_str

    def _filter_format_duration(self, duration_ms: float) -> str:
        """Format duration in milliseconds to human-readable format."""
        if duration_ms < 1000:
            return f"{duration_ms:.0f}ms"
        elif duration_ms < 60000:
            return f"{duration_ms / 1000:.1f}s"
        else:
            return f"{duration_ms / 60000:.1f}m"

    def _filter_format_field_name(self, field_name: str) -> str:
        """Format field name to title case with spaces."""
        return field_name.replace("_", " ").title()

    def _filter_format_provenance_badge(self, provenance: str) -> str:
        """Format provenance type to badge text."""
        badges = {
            "user-specified": "USER",
            "ai-parsed": "AI",
            "ai-inferred": "AI-INF",
            "auto-extracted": "AUTO",
            "auto-corrected": "FIXED",
            "default": "DEFAULT",
            "system-generated": "SYSTEM",
        }
        return badges.get(provenance, provenance.upper())

    def _filter_format_provenance_tooltip(self, provenance: str) -> str:
        """Format provenance type to tooltip text."""
        tooltips = {
            "user-specified": "Directly provided by user",
            "ai-parsed": "Parsed by AI from text",
            "ai-inferred": "Inferred by AI from context",
            "auto-extracted": "Automatically extracted from file",
            "auto-corrected": "Automatically corrected by system",
            "default": "Default fallback value",
            "system-generated": "Generated by system",
        }
        return tooltips.get(provenance, provenance)

    def _filter_format_year(self, timestamp_str: str) -> str:
        """Extract year from ISO timestamp."""
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return str(dt.year)
        except Exception:
            return "2024"

    def _format_filesize(self, bytes_value: int) -> str:
        """Format file size in human-readable format.

        Delegates to ReportFormatters for implementation.
        """
        return self._formatters.format_filesize(bytes_value)

    # ===== ENHANCED REPORT HELPER METHODS =====

    def _identify_missing_critical_fields(self, file_info_raw: dict[str, Any], issues: list) -> list:
        """Identify missing critical fields required for DANDI submission."""
        critical_fields = []

        # DANDI-required fields
        dandi_required = [
            ("species", "Subject species (e.g., Mus musculus)", "🔴", "DANDI blocker"),
            ("age", "Subject age or date of birth", "🔴", "DANDI blocker"),
            ("sex", "Subject sex (M/F/U/O)", "🟡", "Recommended"),
            ("experimenter", "Experimenter name(s)", "🟡", "Recommended"),
            ("session_description", "Description of recording session", "🟡", "Recommended"),
        ]

        for field_name, hint, icon, impact in dandi_required:
            if field_name not in file_info_raw or not file_info_raw.get(field_name):
                critical_fields.append(
                    {
                        "name": field_name,
                        "fix_hint": hint,
                        "impact_icon": icon,
                        "impact": impact,
                    }
                )

        return critical_fields

    def _calculate_quality_metrics(
        self,
        validation_result: dict[str, Any],
        file_info_raw: dict[str, Any],
        issue_counts: dict[str, int],
    ) -> dict[str, dict[str, Any]]:
        """Calculate quality metrics for the dashboard."""
        # Count filled vs total recommended metadata fields
        recommended_fields = [
            "experimenter",
            "institution",
            "lab",
            "experiment_description",
            "session_description",
            "session_id",
            "session_start_time",
            "identifier",
            "subject_id",
            "species",
            "sex",
            "age",
            "date_of_birth",
            "genotype",
            "strain",
            "weight",
            "keywords",
            "related_publications",
            "notes",
            "protocol",
        ]
        filled_count = sum(1 for f in recommended_fields if f in file_info_raw and file_info_raw.get(f))
        completeness_pct = int((filled_count / len(recommended_fields)) * 100)

        # Determine completeness rating
        if completeness_pct >= 80:
            completeness_rating = "excellent"
            completeness_label = "Excellent"
        elif completeness_pct >= 60:
            completeness_rating = "good"
            completeness_label = "Good"
        elif completeness_pct >= 40:
            completeness_rating = "fair"
            completeness_label = "Fair"
        else:
            completeness_rating = "needs-work"
            completeness_label = "Needs Work"

        # Data integrity (based on critical/error issues)
        critical_errors = issue_counts.get("CRITICAL", 0) + issue_counts.get("ERROR", 0)
        if critical_errors == 0:
            integrity_score = 100
            integrity_rating = "excellent"
            integrity_label = "Excellent"
            integrity_desc = "No validation errors"
        elif critical_errors <= 2:
            integrity_score = 75
            integrity_rating = "good"
            integrity_label = "Good"
            integrity_desc = f"{critical_errors} issue(s) found"
        else:
            integrity_score = 40
            integrity_rating = "needs-work"
            integrity_label = "Needs Work"
            integrity_desc = f"{critical_errors} issues found"

        # Scientific value (based on completeness + descriptions)
        has_descriptions = bool(
            file_info_raw.get("experiment_description") and file_info_raw.get("session_description")
        )
        scientific_value_score = int(completeness_pct * 0.7) + (30 if has_descriptions else 0)
        scientific_value_score = min(100, scientific_value_score)

        if scientific_value_score >= 80:
            sci_rating = "excellent"
            sci_label = "Excellent"
            sci_desc = "Well documented"
        elif scientific_value_score >= 60:
            sci_rating = "good"
            sci_label = "Good"
            sci_desc = "Good documentation"
        else:
            sci_rating = "fair"
            sci_label = "Fair"
            sci_desc = "Limited documentation"

        # DANDI readiness (based on required fields + no critical issues)
        dandi_required_fields = ["species", "subject_id", "session_start_time"]
        dandi_filled = sum(1 for f in dandi_required_fields if f in file_info_raw and file_info_raw.get(f))
        dandi_score = int((dandi_filled / len(dandi_required_fields)) * 70)
        if critical_errors == 0:
            dandi_score += 30

        if dandi_score >= 90:
            dandi_rating = "excellent"
            dandi_label = "Ready"
            dandi_desc = "Ready for DANDI"
        elif dandi_score >= 70:
            dandi_rating = "good"
            dandi_label = "Almost Ready"
            dandi_desc = "Minor fixes needed"
        elif dandi_score >= 50:
            dandi_rating = "fair"
            dandi_label = "Needs Work"
            dandi_desc = "Some fields missing"
        else:
            dandi_rating = "needs-work"
            dandi_label = "Not Ready"
            dandi_desc = "Major fixes needed"

        return {
            "completeness": {
                "score": completeness_pct,
                "rating": completeness_rating,
                "label": completeness_label,
                "description": f"{filled_count} of {len(recommended_fields)} fields filled",
            },
            "integrity": {
                "score": integrity_score,
                "rating": integrity_rating,
                "label": integrity_label,
                "description": integrity_desc,
            },
            "scientific_value": {
                "score": scientific_value_score,
                "rating": sci_rating,
                "label": sci_label,
                "description": sci_desc,
            },
            "dandi_ready": {
                "score": dandi_score,
                "rating": dandi_rating,
                "label": dandi_label,
                "description": dandi_desc,
            },
        }

    def _calculate_metadata_completeness(self, file_info_raw: dict[str, Any]) -> dict[str, Any]:
        """Calculate metadata completeness statistics."""
        recommended_fields = [
            "experimenter",
            "institution",
            "lab",
            "experiment_description",
            "session_description",
            "session_id",
            "session_start_time",
            "identifier",
            "subject_id",
            "species",
            "sex",
            "age",
            "date_of_birth",
            "genotype",
            "strain",
            "weight",
            "keywords",
            "related_publications",
            "notes",
            "protocol",
        ]
        required_fields = ["species", "subject_id", "session_start_time", "identifier", "session_description"]

        filled_count = sum(1 for f in recommended_fields if f in file_info_raw and file_info_raw.get(f))
        required_filled = sum(1 for f in required_fields if f in file_info_raw and file_info_raw.get(f))

        return {
            "percentage": int((filled_count / len(recommended_fields)) * 100),
            "filled": filled_count,
            "total": len(recommended_fields),
            "required_filled": required_filled,
            "required_total": len(required_fields),
            "critical_missing": len(required_fields) - required_filled,
        }

    def _estimate_fix_time(self, missing_critical_fields: list, issues_by_severity: dict[str, list]) -> int:
        """Estimate total time in minutes to fix all issues."""
        time_estimates = {
            "missing_field": 3,  # 3 min per missing field
            "CRITICAL": 5,  # 5 min per critical issue
            "ERROR": 3,  # 3 min per error
            "WARNING": 2,  # 2 min per warning
        }

        total_time = len(missing_critical_fields) * time_estimates["missing_field"]
        total_time += len(issues_by_severity.get("CRITICAL", [])) * time_estimates["CRITICAL"]
        total_time += len(issues_by_severity.get("ERROR", [])) * time_estimates["ERROR"]
        total_time += len(issues_by_severity.get("WARNING", [])) * time_estimates["WARNING"]

        return total_time
