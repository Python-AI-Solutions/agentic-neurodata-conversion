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

    def _format_with_provenance(self, value: str, provenance: str, source_file: str = None) -> str:
        """Format a value with its provenance badge for display in reports."""
        # Complete 6-tag provenance system with emoji badges
        provenance_badges = {
            'user-specified': '👤',    # User directly provided
            'file-extracted': '📄',    # From source file
            'ai-parsed': '🧠',         # AI parsed from unstructured text
            'ai-inferred': '🤖',       # AI inferred from context
            'schema-default': '📋',    # NWB schema default
            'system-default': '⚪',    # System fallback
            # Legacy mappings for backwards compatibility
            'user-provided': '👤',
            'default': '⚪',
        }

        badge = provenance_badges.get(provenance, '')
        if badge:
            result = f"{value} {badge}"
            # Add source file for file-extracted provenance
            if provenance == 'file-extracted' and source_file:
                result += f" (from: {source_file})"
            return result
        return value

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
        provenance = file_info.get('_provenance', {})
        source_files = file_info.get('_source_files', {})

        story.append(Paragraph("File Information", self.styles['SectionHeading']))

        # Helper to get value with provenance badge and source file
        def get_with_prov(field_name, value):
            if field_name in provenance:
                source_file = source_files.get(field_name)
                return self._format_with_provenance(value, provenance[field_name], source_file)
            return value

        # Format experimenter list
        experimenters = file_info.get('experimenter', [])
        experimenter_str = ', '.join(experimenters) if experimenters else 'N/A'
        experimenter_str = get_with_prov('experimenter', experimenter_str)

        # Format species with common name
        species_str = self._format_species(file_info.get('species', 'N/A'))
        species_str = get_with_prov('species', species_str)

        # Format sex
        sex_str = self._format_sex(file_info.get('sex', 'N/A'))
        sex_str = get_with_prov('sex', sex_str)

        # Format age
        age_str = self._format_age(file_info.get('age', 'N/A'))
        age_str = get_with_prov('age', age_str)

        file_data = [
            # File-level metadata
            ['NWB Version:', file_info.get('nwb_version', 'N/A')],
            ['File Size:', self._format_filesize(file_info.get('file_size_bytes', 0))],
            ['Creation Date:', file_info.get('creation_date', 'N/A')],
            ['Identifier:', file_info.get('identifier', 'Unknown')],
            ['Session Description:', get_with_prov('session_description', file_info.get('session_description', 'N/A'))],
            ['Session Start Time:', file_info.get('session_start_time', 'N/A')],
            ['', ''],  # Spacer row
            # Experimenter and institution info
            ['Experimenter:', experimenter_str],
            ['Institution:', get_with_prov('institution', file_info.get('institution', 'N/A'))],
            ['Lab:', get_with_prov('lab', file_info.get('lab', 'N/A'))],
            ['', ''],  # Spacer row
            # Subject metadata
            ['Subject ID:', get_with_prov('subject_id', file_info.get('subject_id', 'N/A'))],
            ['Species:', species_str],
            ['Sex:', sex_str],
            ['Age:', age_str],
            ['Date of Birth:', get_with_prov('date_of_birth', file_info.get('date_of_birth', 'N/A'))],
            ['Description:', get_with_prov('description', file_info.get('description', 'N/A')[:100] + ('...' if len(file_info.get('description', 'N/A')) > 100 else ''))],
        ]

        # Add provenance legend after the table with complete 6-tag system
        if provenance:
            story.append(Spacer(1, 0.2 * inch))
            legend_text = (
                "<b>Metadata Provenance:</b> "
                "👤 User-specified | "
                "📄 File-extracted | "
                "🧠 AI-parsed | "
                "🤖 AI-inferred | "
                "📋 Schema-default | "
                "⚪ System-default"
            )
            story.append(Paragraph(legend_text, self.styles['Normal']))

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

        # Add custom metadata section if present
        custom_fields = file_info.get('_custom_fields', {})
        if custom_fields:
            story.append(Paragraph("Custom Metadata Fields", self.styles['SectionHeading']))

            custom_data = []
            for field_name, field_value in custom_fields.items():
                # Format field name nicely
                display_name = field_name.replace('_', ' ').title()

                # Truncate long values
                display_value = str(field_value)
                if len(display_value) > 100:
                    display_value = display_value[:97] + '...'

                # Add provenance if available (custom fields are user-custom by default)
                display_value = self._format_with_provenance(display_value, 'user-custom', None)

                custom_data.append([f"{display_name}:", display_value])

            # Add note about custom fields
            custom_data.append(['', ''])  # Spacer row
            custom_data.append(['Note:', 'These are user-defined custom metadata fields'])

            custom_table = Table(custom_data, colWidths=[2 * inch, 4 * inch])
            custom_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), HexColor('#0066cc')),  # Blue for custom fields
                ('TEXTCOLOR', (1, 0), (1, -1), HexColor('#666666')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('FONTNAME', (0, -1), (0, -1), 'Helvetica-Oblique'),  # Italic for note
                ('FONTSIZE', (0, -1), (-1, -1), 9),
            ]))
            story.append(custom_table)
            story.append(Spacer(1, 0.3 * inch))

        # Validation results section with enhanced display
        story.append(Paragraph("Validation Results", self.styles['SectionHeading']))

        issue_counts = validation_result.get('issue_counts', {})

        # Add total count and status indicators
        total_issues = sum(issue_counts.values())

        validation_data = [
            ['Issue Severity', 'Count', 'Status'],
            ['🔴 CRITICAL', str(issue_counts.get('CRITICAL', 0)), '✅' if issue_counts.get('CRITICAL', 0) == 0 else '⚠️'],
            ['🟠 ERROR', str(issue_counts.get('ERROR', 0)), '✅' if issue_counts.get('ERROR', 0) == 0 else '⚠️'],
            ['🟡 WARNING', str(issue_counts.get('WARNING', 0)), '✅' if issue_counts.get('WARNING', 0) == 0 else '⚠️'],
            ['ℹ️ INFO', str(issue_counts.get('INFO', 0)), '-'],
            ['💡 BEST_PRACTICE', str(issue_counts.get('BEST_PRACTICE', 0)), '-'],
            ['', '', ''],  # Separator row
            ['TOTAL', str(total_issues), '✅' if total_issues == 0 else '-'],
        ]

        validation_table = Table(validation_data, colWidths=[2.5 * inch, 1.5 * inch, 1 * inch])
        validation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#f3f4f6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [HexColor('#ffffff'), HexColor('#f9fafb')]),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor('#e5e7eb')),
        ]))
        story.append(validation_table)
        story.append(Spacer(1, 0.3 * inch))

        # Data Quality Metrics Section (NEW)
        story.append(Paragraph("Data Quality Metrics", self.styles['SectionHeading']))

        # Calculate quality metrics
        file_info = validation_result.get('file_info', {})

        # Metadata completeness score
        metadata_fields = ['experimenter', 'institution', 'lab', 'session_description',
                         'subject_id', 'species', 'sex', 'age']
        filled_fields = sum(1 for field in metadata_fields
                          if file_info.get(field) and file_info.get(field) not in ['N/A', 'Unknown', ''])
        metadata_completeness = (filled_fields / len(metadata_fields)) * 100

        # Compliance scores
        nwb_compliance = 100 if issue_counts.get('CRITICAL', 0) == 0 and issue_counts.get('ERROR', 0) == 0 else 80
        if issue_counts.get('WARNING', 0) > 0:
            nwb_compliance -= 5

        dandi_ready = nwb_compliance >= 95 and metadata_completeness >= 80
        best_practices_score = max(0, 100 - (issue_counts.get('BEST_PRACTICE', 0) * 10))

        quality_data = [
            ['Metric', 'Value', 'Rating'],
            ['', '', ''],  # Header separator
            ['📊 Metadata Completeness', f'{metadata_completeness:.0f}%',
             '✅ Excellent' if metadata_completeness >= 90 else '⚠️ Good' if metadata_completeness >= 70 else '❌ Needs Improvement'],
            ['📈 NWB Standard Compliance', f'{nwb_compliance}/100',
             '✅ Compliant' if nwb_compliance >= 95 else '⚠️ Mostly Compliant' if nwb_compliance >= 80 else '❌ Non-Compliant'],
            ['🗄️ DANDI Archive Ready', 'Yes' if dandi_ready else 'No',
             '✅' if dandi_ready else '❌'],
            ['💡 Best Practices Score', f'{best_practices_score}/100',
             '✅ Excellent' if best_practices_score >= 90 else '⚠️ Good' if best_practices_score >= 70 else '❌ Needs Improvement'],
            ['', '', ''],  # Separator
            ['📁 File Size', self._format_filesize(file_info.get('file_size_bytes', 0)), '-'],
            ['🔢 Data Completeness', '100%', '✅'],
        ]

        quality_table = Table(quality_data, colWidths=[2.5 * inch, 1.5 * inch, 2 * inch])
        quality_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e0f2fe')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 2), (-1, -1), [HexColor('#ffffff'), HexColor('#f0f9ff')]),
        ]))
        story.append(quality_table)
        story.append(Spacer(1, 0.3 * inch))

        # Recommendations Section (NEW)
        story.append(Paragraph("Recommendations", self.styles['SectionHeading']))

        # Generate recommendations based on issues and quality metrics
        recommendations = []

        # Based on metadata completeness
        if metadata_completeness < 70:
            recommendations.append({
                'priority': '🔴 High',
                'action': 'Complete Missing Metadata',
                'details': 'Add experimenter, institution, and subject information for better documentation.'
            })

        # Based on validation issues
        if issue_counts.get('CRITICAL', 0) > 0 or issue_counts.get('ERROR', 0) > 0:
            recommendations.append({
                'priority': '🔴 High',
                'action': 'Fix Critical/Error Issues',
                'details': 'Resolve validation errors before sharing or archiving the file.'
            })

        if issue_counts.get('WARNING', 0) > 0:
            recommendations.append({
                'priority': '🟡 Medium',
                'action': 'Address Warning Issues',
                'details': 'Review warnings to improve data quality and compatibility.'
            })

        if issue_counts.get('INFO', 0) > 0:
            recommendations.append({
                'priority': '🔵 Low',
                'action': 'Review Informational Issues',
                'details': 'Consider addressing INFO-level issues for best practices compliance.'
            })

        # Based on DANDI readiness
        if not dandi_ready:
            recommendations.append({
                'priority': '🟡 Medium',
                'action': 'Prepare for DANDI Archive',
                'details': 'Complete metadata and fix validation issues to meet DANDI requirements.'
            })

        # If no issues, provide positive feedback
        if not recommendations:
            recommendations.append({
                'priority': '✅ None',
                'action': 'Your file is excellent!',
                'details': 'The NWB file passes all checks and is ready for use and sharing.'
            })

        # Create recommendations table
        rec_data = [['Priority', 'Action', 'Details']]
        for rec in recommendations[:5]:  # Limit to top 5 recommendations
            rec_data.append([
                rec['priority'],
                rec['action'],
                rec['details'][:60] + ('...' if len(rec['details']) > 60 else '')
            ])

        rec_table = Table(rec_data, colWidths=[1.2 * inch, 2 * inch, 2.8 * inch])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#fef3c7')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#fbbf24')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#fffbeb'), HexColor('#fef3c7')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(rec_table)
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

        # Metadata Provenance Section (for scientific transparency)
        # Pass state through workflow_trace for now
        if workflow_trace and 'metadata_provenance' in workflow_trace:
            story.append(PageBreak())
            story.append(Paragraph("Metadata Provenance Report", self.styles['SectionHeading']))
            story.append(Paragraph(
                "<i>This section documents the source, confidence, and reliability of each metadata field "
                "for scientific transparency and DANDI compliance.</i>",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 0.2 * inch))

            metadata_provenance = workflow_trace['metadata_provenance']

            # Count fields by provenance type
            provenance_counts = {}
            needs_review_fields = []

            for field_name, prov_info in metadata_provenance.items():
                provenance_type = prov_info.get('provenance', 'unknown')
                provenance_counts[provenance_type] = provenance_counts.get(provenance_type, 0) + 1

                if prov_info.get('needs_review', False):
                    needs_review_fields.append((field_name, prov_info))

            # Summary stats
            story.append(Paragraph("<b>Provenance Summary</b>", self.styles['Normal']))

            summary_data = []
            provenance_labels = {
                'user-specified': '✓ User Provided',
                'ai-parsed': '🤖 AI Parsed (High Confidence)',
                'ai-inferred': '🔮 AI Inferred',
                'auto-extracted': '📁 Auto-Extracted from Files',
                'auto-corrected': '🔧 Auto-Corrected',
                'default': '⚙️ Default Values',
                'system-generated': '⚡ System Generated'
            }

            for prov_type, count in sorted(provenance_counts.items()):
                label = provenance_labels.get(prov_type, prov_type.title())
                summary_data.append([label, str(count)])

            if summary_data:
                summary_table = Table(summary_data, colWidths=[3.5 * inch, 1.5 * inch])
                summary_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e5e5e5')),
                ]))
                story.append(summary_table)
                story.append(Spacer(1, 0.3 * inch))

            # Fields needing review
            if needs_review_fields:
                story.append(Paragraph("<b>⚠️ Fields Requiring Review Before DANDI Submission</b>", self.styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))

                # Sort by confidence (lowest first)
                needs_review_fields.sort(key=lambda x: x[1].get('confidence', 0))

                review_data = [['Field Name', 'Provenance', 'Confidence', 'Reason']]

                for field_name, prov_info in needs_review_fields:
                    prov_type = prov_info.get('provenance', 'unknown')
                    confidence = f"{prov_info.get('confidence', 0):.0f}%"
                    source = prov_info.get('source', 'N/A')[:50]  # Truncate long sources

                    review_data.append([
                        field_name,
                        prov_type.replace('-', ' ').title(),
                        confidence,
                        source
                    ])

                review_table = Table(review_data, colWidths=[1.5 * inch, 1.3 * inch, 0.8 * inch, 2.4 * inch])
                review_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#fff3cd')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#856404')),
                    ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e5e5e5')),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(review_table)
                story.append(Spacer(1, 0.3 * inch))

                story.append(Paragraph(
                    "<i><b>Recommendation:</b> Review and update low-confidence fields before submitting to DANDI. "
                    "Fields marked as 'AI-Inferred' or 'Default' should be verified for accuracy.</i>",
                    self.styles['Normal']
                ))
                story.append(Spacer(1, 0.2 * inch))
            else:
                story.append(Paragraph(
                    "<b>✓ All metadata fields are high-confidence!</b> No review required before DANDI submission.",
                    self.styles['Normal']
                ))
                story.append(Spacer(1, 0.2 * inch))

            # Transparency note
            story.append(Paragraph(
                "<i><b>About Metadata Provenance:</b> This provenance tracking ensures scientific transparency "
                "by documenting the origin and reliability of each metadata field. This is essential for "
                "reproducibility and meets the high standards required by the neuroscience community and DANDI archive.</i>",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 0.2 * inch))

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

            # Add metadata provenance if available
            if 'metadata_provenance' in workflow_trace:
                report['metadata_provenance'] = {
                    'summary': {
                        'total_fields': len(workflow_trace['metadata_provenance']),
                        'needs_review_count': sum(
                            1 for p in workflow_trace['metadata_provenance'].values()
                            if p.get('needs_review', False)
                        ),
                        'provenance_breakdown': {}
                    },
                    'fields': workflow_trace['metadata_provenance']
                }

                # Calculate provenance breakdown
                for field_name, prov_info in workflow_trace['metadata_provenance'].items():
                    prov_type = prov_info.get('provenance', 'unknown')
                    if prov_type not in report['metadata_provenance']['summary']['provenance_breakdown']:
                        report['metadata_provenance']['summary']['provenance_breakdown'][prov_type] = 0
                    report['metadata_provenance']['summary']['provenance_breakdown'][prov_type] += 1

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

    def generate_html_report(
        self,
        output_path: Path,
        validation_result: Dict[str, Any],
        llm_analysis: Optional[Dict[str, Any]] = None,
        workflow_trace: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Generate standalone HTML report for NWB evaluation results.

        Args:
            output_path: Path where HTML should be saved
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM quality assessment
            workflow_trace: Optional workflow trace for provenance

        Returns:
            Path to generated HTML

        Implements interactive HTML reporting with embedded CSS/JS.
        """
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        import json

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
        )

        # Register custom filters
        env.filters['format_timestamp'] = self._filter_format_timestamp
        env.filters['format_duration'] = self._filter_format_duration
        env.filters['format_field_name'] = self._filter_format_field_name
        env.filters['format_provenance_badge'] = self._filter_format_provenance_badge
        env.filters['format_provenance_tooltip'] = self._filter_format_provenance_tooltip
        env.filters['format_year'] = self._filter_format_year

        # Load main template
        template = env.get_template('report.html.j2')

        # Prepare template data
        template_data = self._prepare_template_data(
            validation_result, llm_analysis, workflow_trace
        )

        # Render HTML
        html_content = template.render(**template_data)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return output_path

    def _prepare_template_data(
        self,
        validation_result: Dict[str, Any],
        llm_analysis: Optional[Dict[str, Any]],
        workflow_trace: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Prepare data for HTML template rendering.

        Args:
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM quality assessment
            workflow_trace: Optional workflow trace

        Returns:
            Dictionary of template variables
        """
        from datetime import datetime

        # Extract basic info
        file_info_raw = validation_result.get('file_info', {})
        issues = validation_result.get('issues', [])
        issue_counts = validation_result.get('issue_counts', {})

        # Prepare report data
        report_data = {
            'session_id': validation_result.get('session_id', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'status': validation_result.get('overall_status', 'UNKNOWN'),
            'file_name': validation_result.get('nwb_file_path', 'Unknown').split('/')[-1],
            'file_format': file_info_raw.get('file_format', 'NWB'),
            'summary': self._generate_summary(validation_result),
            'system_version': '1.0.0',
        }

        # Prepare file info with provenance
        file_info = self._prepare_file_info(file_info_raw, workflow_trace)

        # Calculate validation results
        total_checks = sum(issue_counts.values())
        passed_checks = max(0, total_checks - issue_counts.get('CRITICAL', 0) - issue_counts.get('ERROR', 0))
        quality_score = self._calculate_quality_score(validation_result)

        validation_results = {
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'warnings': issue_counts.get('WARNING', 0),
            'errors': issue_counts.get('ERROR', 0),
            'critical': issue_counts.get('CRITICAL', 0),
            'quality_score': quality_score,
            'summary': validation_result.get('summary', ''),
            'best_practices': self._extract_best_practices(validation_result),
        }

        # Prepare issues with enhanced formatting
        enhanced_issues = self._prepare_issues(issues)

        # Prepare recommendations
        recommendations = self._generate_recommendations(
            validation_result, llm_analysis
        )

        # Prepare workflow trace
        workflow_trace_formatted = self._prepare_workflow_trace(workflow_trace)

        # Extract missing fields
        missing_fields = file_info_raw.get('_missing_fields', [])

        return {
            'report_data': report_data,
            'file_info': file_info,
            'missing_fields': missing_fields,
            'validation_results': validation_results,
            'issues': enhanced_issues,
            'recommendations': recommendations,
            'workflow_trace': workflow_trace_formatted,
        }

    def _prepare_file_info(
        self, file_info_raw: Dict[str, Any], workflow_trace: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Prepare file info with provenance badges."""
        provenance = file_info_raw.get('_provenance', {})
        source_files = file_info_raw.get('_source_files', {})
        full_provenance = {}

        # Prioritize _workflow_provenance from file_info_raw (added in main.py for report regeneration)
        # This contains the original AI-parsed provenance with confidence scores and source text
        if '_workflow_provenance' in file_info_raw:
            full_provenance = file_info_raw['_workflow_provenance']
        elif workflow_trace and 'metadata_provenance' in workflow_trace:
            full_provenance = workflow_trace['metadata_provenance']

        file_info = {}
        for key, value in file_info_raw.items():
            if key.startswith('_'):
                continue

            # Prioritize workflow_trace provenance (original sources: AI-parsed, user-specified, etc.)
            # over file_info_raw provenance (which is all "file-extracted" when reading NWB)
            if key in full_provenance:
                prov_info = full_provenance[key]
                file_info[key] = {
                    'value': value,
                    'provenance': prov_info.get('provenance'),
                    'confidence': prov_info.get('confidence'),
                    'source': prov_info.get('source'),
                }
            else:
                # Fallback to file_info_raw provenance if not in workflow_trace
                file_info[key] = {
                    'value': value,
                    'provenance': provenance.get(key, 'system-default'),
                }

        return file_info

    def _prepare_issues(self, issues: list) -> list:
        """Prepare issues with enhanced formatting."""
        enhanced_issues = []
        for issue in issues:
            enhanced_issues.append({
                'severity': issue.get('severity', 'UNKNOWN'),
                'title': issue.get('check_name', 'Unknown Issue'),
                'message': issue.get('message', ''),
                'location': issue.get('location', ''),
                'context': issue.get('context'),
                'suggestion': issue.get('suggestion'),
                'fix': issue.get('fix'),
                'code_snippet': issue.get('code_snippet'),
                'references': issue.get('references', []),
                'check_name': issue.get('check_name', ''),
                'timestamp': issue.get('timestamp'),
            })
        return enhanced_issues

    def _generate_recommendations(
        self, validation_result: Dict[str, Any], llm_analysis: Optional[Dict[str, Any]]
    ) -> list:
        """Generate recommendations based on validation results."""
        recommendations = []
        issue_counts = validation_result.get('issue_counts', {})

        # Critical/Error issues
        if issue_counts.get('CRITICAL', 0) > 0 or issue_counts.get('ERROR', 0) > 0:
            recommendations.append({
                'priority': 'HIGH',
                'title': 'Fix Critical/Error Issues',
                'description': 'Resolve validation errors before sharing or archiving the file.',
                'action_items': [
                    'Review each critical and error issue',
                    'Apply suggested fixes',
                    'Re-validate the file',
                ],
                'expected_outcome': 'File passes validation without critical errors',
            })

        # Warnings
        if issue_counts.get('WARNING', 0) > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'title': 'Address Warning Issues',
                'description': 'Review warnings to improve data quality and compatibility.',
                'action_items': [
                    'Review each warning',
                    'Determine if fixes are needed for your use case',
                ],
                'expected_outcome': 'Improved data quality and DANDI compliance',
            })

        # Add LLM recommendations if available
        if llm_analysis and 'recommendations' in llm_analysis:
            for rec_text in llm_analysis['recommendations'][:3]:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'title': 'Expert Recommendation',
                    'description': rec_text,
                    'action_items': [],
                })

        return recommendations

    def _prepare_workflow_trace(self, workflow_trace: Optional[Dict[str, Any]]) -> list:
        """Prepare workflow trace for timeline display."""
        if not workflow_trace or 'steps' not in workflow_trace:
            return []

        formatted_steps = []
        for step in workflow_trace.get('steps', []):
            formatted_steps.append({
                'step_name': step.get('name', 'Unknown Step'),
                'status': step.get('status', 'UNKNOWN'),
                'description': step.get('description', ''),
                'details': step.get('details'),
                'duration_ms': step.get('duration_ms'),
                'timestamp': step.get('timestamp'),
                'error': step.get('error'),
                'warnings': step.get('warnings', []),
            })

        return formatted_steps

    def _calculate_quality_score(self, validation_result: Dict[str, Any]) -> float:
        """Calculate overall quality score (0-100)."""
        issue_counts = validation_result.get('issue_counts', {})
        file_info = validation_result.get('file_info', {})

        # Start with 100
        score = 100.0

        # Deduct for issues
        score -= issue_counts.get('CRITICAL', 0) * 20
        score -= issue_counts.get('ERROR', 0) * 10
        score -= issue_counts.get('WARNING', 0) * 5
        score -= issue_counts.get('BEST_PRACTICE', 0) * 2

        # Deduct for missing metadata
        metadata_fields = ['experimenter', 'institution', 'lab', 'session_description',
                          'subject_id', 'species', 'sex', 'age']
        missing_metadata = sum(
            1 for field in metadata_fields
            if not file_info.get(field) or file_info.get(field) in ['N/A', 'Unknown', '']
        )
        score -= missing_metadata * 2

        return max(0.0, min(100.0, score))

    def _extract_best_practices(self, validation_result: Dict[str, Any]) -> Dict[str, str]:
        """Extract best practices compliance from validation results."""
        # This could be enhanced based on specific checks
        issue_counts = validation_result.get('issue_counts', {})

        return {
            'NWB Standard Compliance': 'PASS' if issue_counts.get('CRITICAL', 0) == 0 else 'FAIL',
            'Metadata Completeness': 'PASS' if issue_counts.get('ERROR', 0) == 0 else 'FAIL',
            'DANDI Requirements': 'PASS' if issue_counts.get('WARNING', 0) == 0 else 'PARTIAL',
            'Best Practices': 'PASS' if issue_counts.get('BEST_PRACTICE', 0) == 0 else 'FAIL',
        }

    def _generate_summary(self, validation_result: Dict[str, Any]) -> str:
        """Generate a human-readable summary of validation results."""
        status = validation_result.get('overall_status', 'UNKNOWN')
        issue_counts = validation_result.get('issue_counts', {})
        total_issues = sum(issue_counts.values())

        if status == 'PASSED' or total_issues == 0:
            return 'All validation checks passed successfully. The file meets NWB standards and is ready for use.'
        elif status == 'PASSED_WITH_ISSUES':
            return f'Validation passed with {total_issues} warnings. Review recommendations for improvements.'
        else:
            critical = issue_counts.get('CRITICAL', 0) + issue_counts.get('ERROR', 0)
            return f'Validation found {critical} critical issues that must be resolved before the file can be used.'

    # Custom Jinja2 filters
    def _filter_format_timestamp(self, timestamp_str: str) -> str:
        """Format ISO timestamp to human-readable format."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%B %d, %Y at %I:%M %p')
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
        return field_name.replace('_', ' ').title()

    def _filter_format_provenance_badge(self, provenance: str) -> str:
        """Format provenance type to badge text."""
        badges = {
            'user-specified': 'USER',
            'file-extracted': 'FILE',
            'ai-parsed': 'AI',
            'ai-inferred': 'AI-INF',
            'schema-default': 'SCHEMA',
            'system-default': 'DEFAULT',
        }
        return badges.get(provenance, provenance.upper())

    def _filter_format_provenance_tooltip(self, provenance: str) -> str:
        """Format provenance type to tooltip text."""
        tooltips = {
            'user-specified': 'Directly provided by user',
            'file-extracted': 'Extracted from source file',
            'ai-parsed': 'Parsed by AI from text',
            'ai-inferred': 'Inferred by AI from context',
            'schema-default': 'NWB schema default value',
            'system-default': 'System fallback value',
        }
        return tooltips.get(provenance, provenance)

    def _filter_format_year(self, timestamp_str: str) -> str:
        """Extract year from ISO timestamp."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return str(dt.year)
        except Exception:
            return '2024'

    def _format_filesize(self, bytes_value: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
