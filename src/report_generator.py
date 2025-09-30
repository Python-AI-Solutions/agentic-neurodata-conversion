"""Evaluation report generator.

This module generates evaluation reports in multiple formats (JSON, HTML, TXT).
"""

from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
import json
from src.inspector_runner import InspectionResults
from src.hierarchical_parser import HierarchyTree
from src.graph_constructor import GraphMetrics


@dataclass
class ValidationResultsSummary:
    """Summary of validation results."""
    critical: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0


@dataclass
class ReportSummary:
    """Overall report summary."""
    status: str = "UNKNOWN"
    file_path: str = ""
    total_issues: int = 0
    critical_issues: int = 0


@dataclass
class Report:
    """Complete evaluation report."""
    summary: ReportSummary = field(default_factory=ReportSummary)
    validation_results: ValidationResultsSummary = field(default_factory=ValidationResultsSummary)
    hierarchy_info: dict[str, Any] = field(default_factory=dict)
    graph_metrics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


def generate_evaluation_report(
    inspection: InspectionResults,
    hierarchy: HierarchyTree,
    metrics: GraphMetrics
) -> Report:
    """Generate comprehensive evaluation report.

    Args:
        inspection: Inspection results from nwbinspector
        hierarchy: Hierarchical structure information
        metrics: Graph analytics metrics

    Returns:
        Report object
    """
    report = Report()

    # Summary
    report.summary.file_path = str(inspection.file_path)
    report.summary.critical_issues = inspection.severity_counts.get('CRITICAL', 0)
    report.summary.total_issues = sum(inspection.severity_counts.values())

    # Determine overall status
    if report.summary.critical_issues == 0 and inspection.severity_counts.get('ERROR', 0) == 0:
        report.summary.status = 'PASS'
    elif report.summary.critical_issues > 0:
        report.summary.status = 'FAIL'
    else:
        report.summary.status = 'WARNING'

    # Validation results
    for msg in inspection.messages:
        if msg.severity == 'CRITICAL':
            report.validation_results.critical.append(msg.message)
        elif msg.severity == 'ERROR':
            report.validation_results.errors.append(msg.message)
        elif msg.severity == 'WARNING':
            report.validation_results.warnings.append(msg.message)
        else:
            report.validation_results.info.append(msg.message)

    report.validation_results.critical_count = len(report.validation_results.critical)
    report.validation_results.error_count = len(report.validation_results.errors)
    report.validation_results.warning_count = len(report.validation_results.warnings)
    report.validation_results.info_count = len(report.validation_results.info)

    # Hierarchy info
    report.hierarchy_info = {
        "total_groups": len(hierarchy.groups),
        "total_datasets": len(hierarchy.datasets),
        "total_links": len(hierarchy.links)
    }

    # Graph metrics
    report.graph_metrics = {
        "node_count": metrics.node_count,
        "edge_count": metrics.edge_count,
        "density": metrics.density,
        "avg_degree": metrics.avg_degree
    }

    # Recommendations
    if report.summary.critical_issues > 0:
        report.recommendations.append("Critical issues must be resolved before using this file")
    if inspection.severity_counts.get('ERROR', 0) > 0:
        report.recommendations.append("Errors should be addressed to ensure data quality")
    if len(hierarchy.datasets) == 0:
        report.recommendations.append("File contains no datasets - verify data was written correctly")

    return report


def export_report(report: Report, format: str, output_path: Path) -> bool:
    """Export report to file in specified format.

    Args:
        report: Report object
        format: Output format ('json', 'html', 'txt')
        output_path: Path to write file

    Returns:
        True if successful, False otherwise
    """
    try:
        if format == 'json':
            return _export_json(report, output_path)
        elif format == 'html':
            return _export_html(report, output_path)
        elif format == 'txt':
            return _export_txt(report, output_path)
        else:
            return False
    except Exception:
        return False


def _export_json(report: Report, output_path: Path) -> bool:
    """Export report as JSON."""
    data = asdict(report)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    return True


def _export_html(report: Report, output_path: Path) -> bool:
    """Export report as HTML."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>NWB Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .status-pass {{ color: green; font-weight: bold; }}
        .status-fail {{ color: red; font-weight: bold; }}
        .status-warning {{ color: orange; font-weight: bold; }}
        .section {{ margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>NWB Evaluation Report</h1>
    <div class="section">
        <h2>Summary</h2>
        <p><strong>File:</strong> {report.summary.file_path}</p>
        <p><strong>Status:</strong> <span class="status-{report.summary.status.lower()}">{report.summary.status}</span></p>
        <p><strong>Total Issues:</strong> {report.summary.total_issues}</p>
        <p><strong>Critical Issues:</strong> {report.summary.critical_issues}</p>
    </div>
    <div class="section">
        <h2>Validation Results</h2>
        <table>
            <tr><th>Severity</th><th>Count</th></tr>
            <tr><td>Critical</td><td>{report.validation_results.critical_count}</td></tr>
            <tr><td>Errors</td><td>{report.validation_results.error_count}</td></tr>
            <tr><td>Warnings</td><td>{report.validation_results.warning_count}</td></tr>
            <tr><td>Info</td><td>{report.validation_results.info_count}</td></tr>
        </table>
    </div>
    <div class="section">
        <h2>Structure</h2>
        <p><strong>Groups:</strong> {report.hierarchy_info.get('total_groups', 0)}</p>
        <p><strong>Datasets:</strong> {report.hierarchy_info.get('total_datasets', 0)}</p>
        <p><strong>Links:</strong> {report.hierarchy_info.get('total_links', 0)}</p>
    </div>
    <div class="section">
        <h2>Knowledge Graph Metrics</h2>
        <p><strong>Nodes:</strong> {report.graph_metrics.get('node_count', 0)}</p>
        <p><strong>Edges:</strong> {report.graph_metrics.get('edge_count', 0)}</p>
        <p><strong>Density:</strong> {report.graph_metrics.get('density', 0):.4f}</p>
    </div>
</body>
</html>"""

    with open(output_path, 'w') as f:
        f.write(html)
    return True


def _export_txt(report: Report, output_path: Path) -> bool:
    """Export report as plain text."""
    txt = f"""NWB EVALUATION REPORT
{'='*80}

FILE: {report.summary.file_path}
STATUS: {report.summary.status}
TOTAL ISSUES: {report.summary.total_issues}
CRITICAL ISSUES: {report.summary.critical_issues}

VALIDATION RESULTS
{'-'*80}
Critical: {report.validation_results.critical_count}
Errors: {report.validation_results.error_count}
Warnings: {report.validation_results.warning_count}
Info: {report.validation_results.info_count}

STRUCTURE
{'-'*80}
Groups: {report.hierarchy_info.get('total_groups', 0)}
Datasets: {report.hierarchy_info.get('total_datasets', 0)}
Links: {report.hierarchy_info.get('total_links', 0)}

KNOWLEDGE GRAPH METRICS
{'-'*80}
Nodes: {report.graph_metrics.get('node_count', 0)}
Edges: {report.graph_metrics.get('edge_count', 0)}
Density: {report.graph_metrics.get('density', 0):.4f}
"""

    with open(output_path, 'w') as f:
        f.write(txt)
    return True