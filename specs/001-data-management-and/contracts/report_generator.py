"""
Report Generator API Contract

Defines the interface for generating interactive HTML provenance reports.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class ReportSection(str, Enum):
    """Available report sections."""
    EXECUTIVE_SUMMARY = "executive_summary"
    CONFIDENCE_DISTRIBUTION = "confidence_distribution"
    DECISION_CHAINS = "decision_chains"
    EVIDENCE_QUALITY = "evidence_quality"
    AGENT_ACTIVITY = "agent_activity"
    TIMELINE = "timeline"
    CONFLICTS_RESOLVED = "conflicts_resolved"
    RAW_PROVENANCE = "raw_provenance"


class VisualizationType(str, Enum):
    """Types of visualizations."""
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    TIMELINE = "timeline"
    NETWORK_GRAPH = "network_graph"
    HEATMAP = "heatmap"
    SCATTER_PLOT = "scatter_plot"


class ReportGeneratorInterface(ABC):
    """Interface for generating HTML provenance reports."""

    @abstractmethod
    def initialize_report(
        self,
        report_id: str,
        title: str,
        template_name: str = "provenance_report.html.j2"
    ) -> None:
        """
        Initialize a new HTML report.

        Args:
            report_id: Unique report identifier
            title: Report title
            template_name: Jinja2 template to use

        Raises:
            TemplateNotFoundError: If template doesn't exist
            ReportExistsError: If report_id already initialized
        """
        pass

    @abstractmethod
    def add_section(
        self,
        section_type: ReportSection,
        content: Dict[str, Any],
        order: Optional[int] = None
    ) -> None:
        """
        Add a section to the report.

        Args:
            section_type: Type of section to add
            content: Section content data
            order: Display order (lower numbers first)

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def add_visualization(
        self,
        viz_type: VisualizationType,
        data: Dict[str, Any],
        title: str,
        section: ReportSection,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add an interactive visualization to the report.

        Args:
            viz_type: Type of visualization
            data: Data for visualization
            title: Visualization title
            section: Section to add visualization to
            config: Plotly configuration options

        Returns:
            HTML string for embedded visualization

        Raises:
            ReportNotInitializedError: If report not initialized
            VisualizationError: If visualization creation fails
        """
        pass

    @abstractmethod
    def add_confidence_chart(
        self,
        confidence_distribution: Dict[str, int]
    ) -> None:
        """
        Add confidence distribution bar chart (convenience method).

        Args:
            confidence_distribution: Map of confidence levels to counts

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def add_timeline_chart(
        self,
        activities: List[Dict[str, Any]]
    ) -> None:
        """
        Add activity timeline visualization (convenience method).

        Args:
            activities: List of activity records with timestamps

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def add_decision_chain(
        self,
        metadata_field: str,
        chain: List[str],
        final_value: Any,
        confidence: str
    ) -> None:
        """
        Add a metadata decision chain to the report.

        Args:
            metadata_field: Name of metadata field
            chain: Reasoning steps
            final_value: Final metadata value
            confidence: Confidence level

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def add_evidence_summary(
        self,
        metadata_field: str,
        evidence_sources: List[Dict[str, Any]],
        conflicts: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Add evidence summary for a metadata field.

        Args:
            metadata_field: Name of metadata field
            evidence_sources: List of evidence with confidence scores
            conflicts: Optional list of conflicts and resolutions

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def add_agent_activity_summary(
        self,
        agent_activities: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """
        Add summary of agent activities.

        Args:
            agent_activities: Map of agent IDs to their activities

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def set_executive_summary(
        self,
        summary: str,
        key_metrics: Dict[str, Any]
    ) -> None:
        """
        Set the executive summary section.

        Args:
            summary: Narrative summary text
            key_metrics: Important metrics to highlight

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def generate_html(
        self,
        output_path: Path,
        embed_assets: bool = True,
        accessibility: bool = True
    ) -> Path:
        """
        Generate final HTML report file.

        Args:
            output_path: Where to save HTML file
            embed_assets: If True, embed JS/CSS (offline-capable)
            accessibility: If True, include ARIA labels and alt text

        Returns:
            Path to generated HTML file

        Raises:
            ReportNotInitializedError: If report not initialized
            GenerationError: If HTML generation fails
        """
        pass

    @abstractmethod
    def generate_html_string(
        self,
        embed_assets: bool = True,
        accessibility: bool = True
    ) -> str:
        """
        Generate HTML report as string (without saving to file).

        Args:
            embed_assets: If True, embed JS/CSS
            accessibility: If True, include ARIA labels and alt text

        Returns:
            Complete HTML as string

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def add_raw_provenance_export(
        self,
        rdf_turtle: str,
        sparql_endpoint_url: Optional[str] = None
    ) -> None:
        """
        Add raw RDF provenance export section.

        Args:
            rdf_turtle: Provenance graph in Turtle format
            sparql_endpoint_url: Optional URL to SPARQL endpoint

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def configure_template_variables(
        self,
        variables: Dict[str, Any]
    ) -> None:
        """
        Set custom template variables for Jinja2 rendering.

        Args:
            variables: Dict of variable names to values

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass

    @abstractmethod
    def validate_report(self) -> List[str]:
        """
        Validate report completeness and structure.

        Returns:
            List of validation warnings (empty if valid)

        Raises:
            ReportNotInitializedError: If report not initialized
        """
        pass
