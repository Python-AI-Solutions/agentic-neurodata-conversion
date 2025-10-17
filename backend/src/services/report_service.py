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

    def generate_pdf_report(
        self,
        output_path: Path,
        validation_result: Dict[str, Any],
        llm_analysis: Optional[Dict[str, Any]] = None,
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

        file_data = [
            ['NWB Version:', file_info.get('nwb_version', 'N/A')],
            ['File Size:', self._format_filesize(file_info.get('file_size_bytes', 0))],
            ['Creation Date:', file_info.get('creation_date', 'N/A')],
            ['Identifier:', file_info.get('identifier', 'N/A')],
            ['Session Description:', file_info.get('session_description', 'N/A')],
            ['Subject ID:', file_info.get('subject_id', 'N/A')],
            ['Species:', file_info.get('species', 'N/A')],
            ['Experimenter:', ', '.join(file_info.get('experimenter', [])) or 'N/A'],
            ['Institution:', file_info.get('institution', 'N/A')],
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

        # Build PDF
        doc.build(story)
        return output_path

    def generate_json_report(
        self,
        output_path: Path,
        validation_result: Dict[str, Any],
        llm_guidance: Optional[Dict[str, Any]] = None,
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

        # Write pretty-printed JSON
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return output_path

    def generate_text_report(
        self,
        output_path: Path,
        validation_result: Dict[str, Any],
    ) -> Path:
        """
        Generate text report in NWB Inspector style (clear and structured).

        Args:
            output_path: Path where text report should be saved
            validation_result: Validation result dictionary

        Returns:
            Path to generated text report
        """
        import platform
        from datetime import datetime

        lines = []

        # Header
        lines.append("*" * 50)
        lines.append("NWBInspector Report Summary")
        lines.append("")
        lines.append(f"Timestamp: {datetime.now().isoformat()}")
        lines.append(f"Platform: {platform.platform()}")
        lines.append(f"NWBInspector version: 0.6.5")  # TODO: Get actual version
        lines.append("")

        # Summary
        issues = validation_result.get('issues', [])
        issue_counts = validation_result.get('issue_counts', {})

        total_issues = len(issues)
        files_count = 1  # Single file for now

        lines.append(f"Found {total_issues} issues over {files_count} files:")

        for severity, count in sorted(issue_counts.items()):
            if count > 0:
                lines.append(f"       {count} - {severity}")

        lines.append("*" * 50)
        lines.append("")
        lines.append("")

        # Group issues by severity
        issues_by_severity = {}
        for issue in issues:
            severity = issue.get('severity', 'UNKNOWN')
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)

        # Print issues grouped by severity
        severity_order = ['CRITICAL', 'ERROR', 'WARNING', 'BEST_PRACTICE_VIOLATION', 'BEST_PRACTICE_SUGGESTION']

        for sev_idx, severity in enumerate(severity_order):
            if severity not in issues_by_severity:
                continue

            issues_list = issues_by_severity[severity]
            if not issues_list:
                continue

            lines.append(f"{sev_idx}  {severity}")
            lines.append("=" * 27)
            lines.append("")

            for issue_idx, issue in enumerate(issues_list):
                nwb_file = validation_result.get('nwb_file_path', 'Unknown file')
                check_name = issue.get('check_name', 'unknown_check')
                object_type = issue.get('object_type', 'NWBFile')
                location = issue.get('location', '/')

                lines.append(f"{sev_idx}.{issue_idx}  {nwb_file}: {check_name} - '{object_type}' object at location '{location}'")
                lines.append(f"       Message: {issue.get('message', 'No message')}")
                lines.append("")

            lines.append("")

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
