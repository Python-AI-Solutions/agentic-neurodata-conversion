"""HTML report generator for NWB evaluation results.

Generates interactive HTML reports with embedded CSS/JS using Jinja2 templates.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class HTMLReportGenerator:
    """Generates interactive HTML reports for NWB validation results."""

    def __init__(self, template_dir: Path | None = None):
        """Initialize HTML report generator.

        Args:
            template_dir: Directory containing Jinja2 templates.
                         Defaults to services/templates/
        """
        if template_dir is None:
            # Default to templates directory next to this module
            template_dir = Path(__file__).parent.parent / "templates"

        self.template_dir = template_dir

    def generate_html_report(
        self,
        output_path: Path,
        template_data: dict[str, Any],
        jinja_filters: dict[str, Any] | None = None,
    ) -> Path:
        """Generate standalone HTML report.

        Args:
            output_path: Path where HTML should be saved
            template_data: Data dictionary for template rendering
            jinja_filters: Optional custom Jinja2 filters

        Returns:
            Path to generated HTML file

        Examples:
            >>> generator = HTMLReportGenerator()
            >>> template_data = {
            ...     "report_data": {"status": "PASSED", "timestamp": "2024-01-01T00:00:00"},
            ...     "file_info": {...},
            ...     "validation_results": {...}
            ... }
            >>> output_path = generator.generate_html_report(
            ...     Path("report.html"),
            ...     template_data,
            ...     jinja_filters={"format_timestamp": lambda x: x}
            ... )
        """
        # Setup Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Register custom filters if provided
        if jinja_filters:
            for filter_name, filter_func in jinja_filters.items():
                env.filters[filter_name] = filter_func

        # Load main template
        template = env.get_template("report.html.j2")

        # Render HTML
        html_content = template.render(**template_data)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_path

    @staticmethod
    def create_template_data_structure(
        validation_result: dict[str, Any],
        llm_analysis: dict[str, Any] | None = None,
        workflow_trace: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create the basic structure for template data.

        This is a helper method that creates the skeleton structure.
        The actual data preparation logic is delegated to ReportService
        to avoid circular dependencies.

        Args:
            validation_result: Validation result dictionary
            llm_analysis: Optional LLM quality assessment
            workflow_trace: Optional workflow trace

        Returns:
            Basic template data structure (to be filled by ReportService)
        """
        # Extract basic info
        file_info_raw = validation_result.get("file_info", {})
        issue_counts = validation_result.get("issue_counts", {})

        # Create basic report data skeleton
        return {
            "report_data": {
                "session_id": validation_result.get("session_id", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "status": validation_result.get("overall_status", "UNKNOWN"),
                "file_name": validation_result.get("nwb_file_path", "Unknown").split("/")[-1],
                "file_format": file_info_raw.get("file_format", "NWB"),
                "system_version": "1.0.0",
            },
            "validation_result": validation_result,
            "llm_analysis": llm_analysis,
            "workflow_trace": workflow_trace,
            "issue_counts": issue_counts,
        }
