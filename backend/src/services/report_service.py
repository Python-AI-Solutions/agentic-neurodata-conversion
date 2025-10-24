"""
Report generation service for NWB evaluation results.

Implements Tasks T049, T050, T051: PDF and JSON report generation.
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import json

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class ReportService:
    """
    Service for generating NWB evaluation reports.

    Supports both PDF (for PASSED/PASSED_WITH_ISSUES) and JSON (for FAILED).
    """

    # Species common names for scientific quality
    SPECIES_COMMON_NAMES = {
        'Mus musculus': 'House mouse',
        'Rattus norvegicus': 'Norway rat',
        'Homo sapiens': 'Human',
        'Macaca mulatta': 'Rhesus macaque',
        'Danio rerio': 'Zebrafish',
        'Drosophila melanogaster': 'Fruit fly',
        'Caenorhabditis elegans': 'Roundworm',
    }

    # Sex code expansion
    SEX_CODES = {
        'M': 'Male',
        'F': 'Female',
        'U': 'Unknown',
        'O': 'Other',
    }

    def __init__(self):
        """Initialize report service."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=20,
        ))

        # Status styles
        self.styles.add(ParagraphStyle(
            name='StatusPassed',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=HexColor('#22c55e'),
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica-Bold',
        ))

        self.styles.add(ParagraphStyle(
            name='StatusWarning',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=HexColor('#f59e0b'),
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica-Bold',
        ))

        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#1a1a1a'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
        ))

    def _format_species(self, species: str) -> str:
        """Format species with common name if known."""
        if species == 'N/A' or not species:
            return 'N/A'

        common_name = self.SPECIES_COMMON_NAMES.get(species)
        if common_name:
            return f"{species} ({common_name})"
        return species

    def _format_sex(self, sex_code: str) -> str:
        """Expand sex code to full word."""
        if not sex_code or sex_code == 'N/A':
            return 'N/A'
        return self.SEX_CODES.get(sex_code.upper(), sex_code)

    def _format_age(self, iso_age: str) -> str:
        """Convert ISO 8601 duration to human-readable format."""
        if not iso_age or iso_age == 'N/A':
            return 'N/A'

        import re
        # Match P90D, P3M, P2Y formats
        match = re.match(r'P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?', iso_age)
        if match:
            years, months, weeks, days = match.groups()
            parts = []
            if years:
                parts.append(f"{years} year{'s' if int(years) != 1 else ''}")
            if months:
                parts.append(f"{months} month{'s' if int(months) != 1 else ''}")
            if weeks:
                parts.append(f"{weeks} week{'s' if int(weeks) != 1 else ''}")
            if days:
                parts.append(f"{days} day{'s' if int(days) != 1 else ''}")

            if parts:
                readable = ', '.join(parts)
                return f"{iso_age} ({readable})"
        return iso_age

    def generate_pdf_report(
        self,
        output_path: Path,
        validation_result: Dict[str, Any],
        llm_analysis: Optional[Dict[str, Any]] = None,
        workflow_trace: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Generate PDF report for PASSED or PASSED_WITH_ISSUES validation.

        Args:
            output_path: Path where PDF should be saved
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM quality assessment

        Returns:
            Path to generated PDF

        Implements Story 9.5: PDF Report Generation
        """
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )

        story = []

        # Title page
        story.append(Paragraph("NWB File Quality Evaluation Report", self.styles['CustomTitle']))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['Subtitle']
        ))
        story.append(Spacer(1, 0.3 * inch))

        # Status badge
        overall_status = validation_result.get('overall_status', 'UNKNOWN')
        if overall_status == 'PASSED':
            story.append(Paragraph("✓ PASSED - No Issues Found", self.styles['StatusPassed']))
        else:
            story.append(Paragraph("⚠ PASSED WITH WARNINGS", self.styles['StatusWarning']))

        story.append(Spacer(1, 0.4 * inch))

        # File information section
        file_info = validation_result.get('file_info', {})
        story.append(Paragraph("File Information", self.styles['SectionHeading']))

        # Format experimenter list
        experimenters = file_info.get('experimenter', [])
        experimenter_str = ', '.join(experimenters) if experimenters else 'N/A'

        # Format species with common name
        species_str = self._format_species(file_info.get('species', 'N/A'))

        # Format sex
        sex_str = self._format_sex(file_info.get('sex', 'N/A'))

        # Format age
        age_str = self._format_age(file_info.get('age', 'N/A'))

        file_data = [
            # File-level metadata
            ['NWB Version:', file_info.get('nwb_version', 'N/A')],
            ['File Size:', self._format_filesize(file_info.get('file_size_bytes', 0))],
            ['Creation Date:', file_info.get('creation_date', 'N/A')],
            ['Identifier:', file_info.get('identifier', 'Unknown')],
            ['Session Description:', file_info.get('session_description', 'N/A')],
            ['Session Start Time:', file_info.get('session_start_time', 'N/A')],
            ['', ''],  # Spacer row
            # Experimenter and institution info
            ['Experimenter:', experimenter_str],
            ['Institution:', file_info.get('institution', 'N/A')],
            ['Lab:', file_info.get('lab', 'N/A')],
            ['', ''],  # Spacer row
            # Subject metadata
            ['Subject ID:', file_info.get('subject_id', 'N/A')],
            ['Species:', species_str],
            ['Sex:', sex_str],
            ['Age:', age_str],
            ['Date of Birth:', file_info.get('date_of_birth', 'N/A')],
            ['Description:', file_info.get('description', 'N/A')[:100] + ('...' if len(file_info.get('description', 'N/A')) > 100 else '')],  # Truncate long descriptions
        ]

        file_table = Table(file_data, colWidths=[2 * inch, 4 * inch])
        file_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), HexColor('#1a1a1a')),
            ('TEXTCOLOR', (1, 0), (1, -1), HexColor('#666666')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(file_table)
        story.append(Spacer(1, 0.3 * inch))

        # Validation results section
        story.append(Paragraph("Validation Results", self.styles['SectionHeading']))

        issue_counts = validation_result.get('issue_counts', {})
        validation_data = [
            ['Issue Severity', 'Count'],
            ['CRITICAL', str(issue_counts.get('CRITICAL', 0))],
            ['ERROR', str(issue_counts.get('ERROR', 0))],
            ['WARNING', str(issue_counts.get('WARNING', 0))],
            ['BEST_PRACTICE', str(issue_counts.get('BEST_PRACTICE', 0))],
        ]

        validation_table = Table(validation_data, colWidths=[3 * inch, 1.5 * inch])
        validation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f9fafb')]),
        ]))
        story.append(validation_table)
        story.append(Spacer(1, 0.3 * inch))

        # Issues detail (if any)
        issues = validation_result.get('issues', [])
        if issues:
            story.append(Paragraph("Issue Details", self.styles['SectionHeading']))
            for i, issue in enumerate(issues[:20], 1):  # Limit to 20 for PDF readability
                issue_text = f"<b>{i}. [{issue.get('severity', 'UNKNOWN')}]</b> {issue.get('message', 'No message')}"
                story.append(Paragraph(issue_text, self.styles['Normal']))
                if issue.get('location'):
                    location_text = f"<i>Location: {issue['location']}</i>"
                    story.append(Paragraph(location_text, self.styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))

            if len(issues) > 20:
                story.append(Paragraph(
                    f"<i>... and {len(issues) - 20} more issues (see full report)</i>",
                    self.styles['Normal']
                ))
            story.append(Spacer(1, 0.2 * inch))

        # LLM Analysis section (if available)
        if llm_analysis:
            story.append(PageBreak())
            story.append(Paragraph("Expert Quality Assessment", self.styles['SectionHeading']))

            if 'executive_summary' in llm_analysis:
                story.append(Paragraph("<b>Executive Summary</b>", self.styles['Normal']))
                story.append(Paragraph(llm_analysis['executive_summary'], self.styles['Normal']))
                story.append(Spacer(1, 0.2 * inch))

            quality_assessment = llm_analysis.get('quality_assessment', {})
            if quality_assessment:
                story.append(Paragraph("<b>Quality Assessment</b>", self.styles['Normal']))

                qa_data = []
                if 'completeness_score' in quality_assessment:
                    qa_data.append(['Completeness Score:', quality_assessment['completeness_score']])
                if 'metadata_quality' in quality_assessment:
                    qa_data.append(['Metadata Quality:', quality_assessment['metadata_quality']])
                if 'data_integrity' in quality_assessment:
                    qa_data.append(['Data Integrity:', quality_assessment['data_integrity']])
                if 'scientific_value' in quality_assessment:
                    qa_data.append(['Scientific Value:', quality_assessment['scientific_value']])

                if qa_data:
                    qa_table = Table(qa_data, colWidths=[2 * inch, 4 * inch])
                    qa_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ]))
                    story.append(qa_table)
                    story.append(Spacer(1, 0.2 * inch))

            recommendations = llm_analysis.get('recommendations', [])
            if recommendations:
                story.append(Paragraph("<b>Recommendations</b>", self.styles['Normal']))
                for i, rec in enumerate(recommendations, 1):
                    story.append(Paragraph(f"{i}. {rec}", self.styles['Normal']))
                    story.append(Spacer(1, 0.05 * inch))
                story.append(Spacer(1, 0.2 * inch))

            dandi_ready = llm_analysis.get('dandi_ready', False)
            dandi_text = "✓ This file is ready for DANDI archive submission" if dandi_ready else "⚠ Additional improvements recommended before DANDI submission"
            story.append(Paragraph(f"<b>DANDI Readiness:</b> {dandi_text}", self.styles['Normal']))

        # Workflow Trace Section (for transparency and reproducibility)
        if workflow_trace:
            story.append(PageBreak())
            story.append(Paragraph("Complete Workflow Trace", self.styles['SectionHeading']))
            story.append(Paragraph(
                "<i>For scientific transparency and reproducibility, this section documents the complete conversion process.</i>",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 0.2 * inch))

            # Process summary
            if 'summary' in workflow_trace:
                summary = workflow_trace['summary']
                story.append(Paragraph("<b>Process Summary</b>", self.styles['Normal']))

                summary_data = [
                    ['Start Time:', summary.get('start_time', 'N/A')],
                    ['End Time:', summary.get('end_time', 'N/A')],
                    ['Total Duration:', summary.get('duration', 'N/A')],
                    ['Input Format:', summary.get('input_format', 'N/A')],
                    ['Output Format:', 'NWB (Neurodata Without Borders)'],
                ]

                summary_table = Table(summary_data, colWidths=[2 * inch, 4 * inch])
                summary_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(summary_table)
                story.append(Spacer(1, 0.2 * inch))

            # Technologies used
            if 'technologies' in workflow_trace:
                story.append(Paragraph("<b>Technologies & Standards</b>", self.styles['Normal']))
                tech_items = []
                for tech in workflow_trace['technologies']:
                    tech_items.append(Paragraph(f"• {tech}", self.styles['Normal']))
                for item in tech_items:
                    story.append(item)
                story.append(Spacer(1, 0.2 * inch))

            # Workflow steps
            if 'steps' in workflow_trace:
                story.append(Paragraph("<b>Conversion Pipeline Steps</b>", self.styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))

                for i, step in enumerate(workflow_trace['steps'], 1):
                    step_title = f"<b>{i}. {step.get('name', 'Unknown Step')}</b>"
                    story.append(Paragraph(step_title, self.styles['Normal']))
                    story.append(Paragraph(f"<i>Status: {step.get('status', 'N/A')}</i>", self.styles['Normal']))
                    if step.get('description'):
                        story.append(Paragraph(step['description'], self.styles['Normal']))
                    if step.get('duration'):
                        story.append(Paragraph(f"<i>Duration: {step['duration']}</i>", self.styles['Normal']))
                    story.append(Spacer(1, 0.1 * inch))

            # Data provenance
            if 'provenance' in workflow_trace:
                story.append(Paragraph("<b>Data Provenance</b>", self.styles['Normal']))
                prov = workflow_trace['provenance']
                prov_items = []
                if 'original_file' in prov:
                    prov_items.append(f"Original Data: {prov['original_file']}")
                if 'conversion_method' in prov:
                    prov_items.append(f"Conversion Method: {prov['conversion_method']}")
                if 'metadata_sources' in prov:
                    prov_items.append(f"Metadata Sources: {', '.join(prov['metadata_sources'])}")

                for item in prov_items:
                    story.append(Paragraph(f"• {item}", self.styles['Normal']))
                story.append(Spacer(1, 0.2 * inch))

            # Reproducibility note
            story.append(Paragraph(
                "<i><b>Note on Reproducibility:</b> This workflow trace enables independent verification "
                "and reproduction of the conversion process. All steps, technologies, and data sources "
                "are documented to meet scientific transparency standards required by the neuroscience "
                "community and DANDI archive.</i>",
                self.styles['Normal']
            ))

        # Build PDF
        doc.build(story)
        return output_path

    def generate_json_report(
        self,
        output_path: Path,
        validation_result: Dict[str, Any],
        llm_guidance: Optional[Dict[str, Any]] = None,
        workflow_trace: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Generate JSON report for FAILED validation.

        Args:
            output_path: Path where JSON should be saved
            validation_result: Validation result dictionary
            llm_guidance: Optional LLM correction guidance

        Returns:
            Path to generated JSON

        Implements Story 9.6: JSON Context Generation
        """
        report = {
            "evaluation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "status": validation_result.get('overall_status', 'FAILED'),
                "nwb_file_path": validation_result.get('nwb_file_path', ''),
            },
            "failure_summary": {
                "total_issues": len(validation_result.get('issues', [])),
                "issue_counts": validation_result.get('issue_counts', {}),
            },
            "critical_issues": [
                {
                    "severity": issue.get('severity', 'UNKNOWN'),
                    "message": issue.get('message', ''),
                    "location": issue.get('location', ''),
                    "check_name": issue.get('check_name', ''),
                }
                for issue in validation_result.get('issues', [])
                if issue.get('severity') in ['CRITICAL', 'ERROR']
            ],
            "file_info": validation_result.get('file_info', {}),
        }

        # Add LLM guidance if available
        if llm_guidance:
            report['llm_guidance'] = llm_guidance

        # Add workflow trace for transparency and reproducibility
        if workflow_trace:
            report['workflow_trace'] = workflow_trace

        # Write pretty-printed JSON
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return output_path

    def generate_text_report(
        self,
        output_path: Path,
        validation_result: Dict[str, Any],
        llm_analysis: Optional[Dict[str, Any]] = None,
        workflow_trace: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Generate text report in NWB Inspector style (clear and structured).

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
        lines.append(f"NWBInspector version: 0.6.5")

        # Add file info if available
        file_info = validation_result.get('file_info', {})
        if file_info:
            lines.append(f"NWB version:          {file_info.get('nwb_version', 'Unknown')}")
            lines.append(f"File:                 {validation_result.get('nwb_file_path', 'Unknown')}")

        lines.append("")

        # Overall status badge
        overall_status = validation_result.get('overall_status', 'UNKNOWN')
        status_line = f"Status: {overall_status}"
        if overall_status == 'PASSED':
            status_line = f"✓ {status_line} - No critical issues found"
        elif overall_status == 'PASSED_WITH_ISSUES':
            status_line = f"⚠ {status_line} - File passed with warnings"
        else:
            status_line = f"✗ {status_line} - Critical issues found"

        lines.append(status_line)
        lines.append("")
        lines.append("-" * 80)
        lines.append("")

        # Summary of issues
        issues = validation_result.get('issues', [])
        issue_counts = validation_result.get('issue_counts', {})
        total_issues = len(issues)
        files_count = 1  # Single file for now

        if total_issues == 0:
            lines.append("✓ No validation issues found. File meets all NWB standards.")
            lines.append("")
        else:
            lines.append(f"Found {total_issues} validation issue{'s' if total_issues != 1 else ''} over {files_count} file{'s' if files_count != 1 else ''}:")
            lines.append("")

            # Sort severity by importance and show counts
            severity_display_order = [
                ('CRITICAL', 'Critical errors'),
                ('ERROR', 'Errors'),
                ('WARNING', 'Warnings'),
                ('BEST_PRACTICE_VIOLATION', 'Best practice violations'),
                ('BEST_PRACTICE_SUGGESTION', 'Best practice suggestions'),
            ]

            for severity, display_name in severity_display_order:
                count = issue_counts.get(severity, 0)
                if count > 0:
                    lines.append(f"  • {count:3d} {display_name}")

        lines.append("")
        lines.append("=" * 80)
        lines.append("")

        # Group issues by severity
        issues_by_severity = {}
        for issue in issues:
            severity = issue.get('severity', 'UNKNOWN')
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)

        # Print detailed issues grouped by severity
        severity_order = ['CRITICAL', 'ERROR', 'WARNING', 'BEST_PRACTICE_VIOLATION', 'BEST_PRACTICE_SUGGESTION']

        for sev_idx, severity in enumerate(severity_order):
            if severity not in issues_by_severity:
                continue

            issues_list = issues_by_severity[severity]
            if not issues_list:
                continue

            # Section header for this severity
            severity_display = severity.replace('_', ' ').title()
            lines.append("")
            lines.append(f"[{sev_idx + 1}] {severity_display}")
            lines.append("-" * 80)
            lines.append("")

            for issue_idx, issue in enumerate(issues_list, 1):
                nwb_file = validation_result.get('nwb_file_path', 'Unknown file')
                check_name = issue.get('check_name', 'unknown_check')
                object_type = issue.get('object_type', 'NWBFile')
                location = issue.get('location', '/')
                message = issue.get('message', 'No message')

                # Format: [sev_idx.issue_idx] File: check_name
                lines.append(f"[{sev_idx + 1}.{issue_idx}] {check_name}")
                lines.append(f"      File:     {nwb_file}")
                lines.append(f"      Object:   '{object_type}' at location '{location}'")
                lines.append(f"      Message:  {message}")

                # Add importance indicator for critical/error
                if severity in ['CRITICAL', 'ERROR']:
                    lines.append(f"      Impact:   ⚠ This issue may prevent DANDI archive submission")

                lines.append("")

        # Footer
        if total_issues > 0:
            lines.append("")
            lines.append("=" * 80)
            lines.append("")
            lines.append("Summary:")
            lines.append(f"  Total issues:          {total_issues}")
            lines.append(f"  Critical/Error issues: {issue_counts.get('CRITICAL', 0) + issue_counts.get('ERROR', 0)}")
            lines.append(f"  Best practice issues:  {issue_counts.get('BEST_PRACTICE_VIOLATION', 0) + issue_counts.get('BEST_PRACTICE_SUGGESTION', 0)}")
            lines.append("")

            # DANDI readiness assessment
            critical_count = issue_counts.get('CRITICAL', 0) + issue_counts.get('ERROR', 0)
            if critical_count == 0:
                lines.append("✓ DANDI Readiness: This file is ready for DANDI archive submission.")
            else:
                lines.append(f"✗ DANDI Readiness: {critical_count} critical issue{'s' if critical_count != 1 else ''} must be fixed before DANDI submission.")

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
            if 'executive_summary' in llm_analysis:
                lines.append("Executive Summary:")
                lines.append("-" * 80)
                summary_text = llm_analysis['executive_summary']
                # Word wrap the summary to 80 characters
                import textwrap
                wrapped_summary = textwrap.fill(summary_text, width=78, initial_indent="  ", subsequent_indent="  ")
                lines.append(wrapped_summary)
                lines.append("")

            # Quality Assessment Scores
            quality_assessment = llm_analysis.get('quality_assessment', {})
            if quality_assessment:
                lines.append("Quality Metrics:")
                lines.append("-" * 80)

                if 'completeness_score' in quality_assessment:
                    score = quality_assessment['completeness_score']
                    lines.append(f"  • Data Completeness:    {score}")

                if 'metadata_quality' in quality_assessment:
                    quality = quality_assessment['metadata_quality']
                    lines.append(f"  • Metadata Quality:     {quality}")

                if 'data_integrity' in quality_assessment:
                    integrity = quality_assessment['data_integrity']
                    lines.append(f"  • Data Integrity:       {integrity}")

                if 'scientific_value' in quality_assessment:
                    value = quality_assessment['scientific_value']
                    lines.append(f"  • Scientific Value:     {value}")

                lines.append("")

            # Recommendations
            recommendations = llm_analysis.get('recommendations', [])
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
            if 'key_insights' in llm_analysis:
                insights = llm_analysis['key_insights']
                if isinstance(insights, list) and insights:
                    lines.append("Key Insights:")
                    lines.append("-" * 80)
                    for insight in insights:
                        import textwrap
                        wrapped_insight = textwrap.fill(insight, width=76, initial_indent="  • ", subsequent_indent="    ")
                        lines.append(wrapped_insight)
                    lines.append("")

            # DANDI Readiness from LLM
            if 'dandi_ready' in llm_analysis:
                lines.append("")
                dandi_ready = llm_analysis['dandi_ready']
                if dandi_ready:
                    lines.append("✓ DANDI Archive Status: Ready for submission")
                else:
                    lines.append("⚠ DANDI Archive Status: Improvements recommended before submission")

                if 'dandi_blocking_issues' in llm_analysis:
                    blocking = llm_analysis['dandi_blocking_issues']
                    if blocking:
                        lines.append("")
                        lines.append("  Blocking Issues:")
                        for issue in blocking:
                            import textwrap
                            wrapped_issue = textwrap.fill(issue, width=74, initial_indent="    - ", subsequent_indent="      ")
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
            if 'summary' in workflow_trace:
                summary = workflow_trace['summary']
                lines.append("Process Summary:")
                lines.append("-" * 80)
                lines.append(f"  Start Time:       {summary.get('start_time', 'N/A')}")
                lines.append(f"  End Time:         {summary.get('end_time', 'N/A')}")
                lines.append(f"  Total Duration:   {summary.get('duration', 'N/A')}")
                lines.append(f"  Input Format:     {summary.get('input_format', 'N/A')}")
                lines.append(f"  Output Format:    NWB (Neurodata Without Borders)")
                lines.append("")

            # Technologies Used
            if 'technologies' in workflow_trace:
                lines.append("Technologies & Standards:")
                lines.append("-" * 80)
                for tech in workflow_trace['technologies']:
                    lines.append(f"  • {tech}")
                lines.append("")

            # Workflow Steps
            if 'steps' in workflow_trace:
                lines.append("Conversion Pipeline Steps:")
                lines.append("-" * 80)
                lines.append("")
                for i, step in enumerate(workflow_trace['steps'], 1):
                    lines.append(f"Step {i}: {step.get('name', 'Unknown Step')}")
                    lines.append(f"  Status: {step.get('status', 'N/A')}")
                    if step.get('description'):
                        import textwrap
                        wrapped_desc = textwrap.fill(
                            step['description'],
                            width=76,
                            initial_indent="  ",
                            subsequent_indent="  "
                        )
                        lines.append(wrapped_desc)
                    if step.get('duration'):
                        lines.append(f"  Duration: {step['duration']}")
                    if step.get('timestamp'):
                        lines.append(f"  Timestamp: {step['timestamp']}")
                    lines.append("")

            # Data Provenance
            if 'provenance' in workflow_trace:
                lines.append("Data Provenance:")
                lines.append("-" * 80)
                prov = workflow_trace['provenance']
                if 'original_file' in prov:
                    lines.append(f"  Original Data:      {prov['original_file']}")
                if 'conversion_method' in prov:
                    lines.append(f"  Conversion Method:  {prov['conversion_method']}")
                if 'metadata_sources' in prov:
                    sources = ', '.join(prov['metadata_sources'])
                    lines.append(f"  Metadata Sources:   {sources}")
                if 'agent_versions' in prov:
                    lines.append(f"  Agent Versions:     {prov['agent_versions']}")
                lines.append("")

            # User Interactions
            if 'user_interactions' in workflow_trace:
                lines.append("User Interactions:")
                lines.append("-" * 80)
                for interaction in workflow_trace['user_interactions']:
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
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

        return output_path

    def _format_filesize(self, bytes_value: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
