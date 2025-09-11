"""Comprehensive quality assessment system for conversion evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MissingDependencyError(Exception):
    """Raised when a critical dependency is missing."""

    def __init__(self, dependency: str, functionality: str, install_command: str):
        super().__init__(
            f"Cannot perform {functionality} without '{dependency}'. "
            f"This dependency is required for accurate NWB quality assessment. "
            f"Install with: {install_command} "
            f"Then run with: pixi run <your_command>"
        )


def check_critical_dependencies():
    """Check that all critical dependencies for NWB quality assessment are available.

    Raises:
        MissingDependencyError: If any critical dependency is missing
    """
    missing = []

    try:
        import pynwb  # noqa: F401
    except ImportError:
        missing.append(
            ("pynwb", "NWB file reading and data integrity analysis", "pixi add pynwb")
        )

    if missing:
        # For now, just check pynwb as it's the most critical
        dep, functionality, command = missing[0]
        raise MissingDependencyError(dep, functionality, command)


class IssueSeverity(Enum):
    """Severity levels for quality issues."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(Enum):
    """Categories for quality issues."""

    SCHEMA_COMPLIANCE = "schema_compliance"
    DATA_INTEGRITY = "data_integrity"
    METADATA_COMPLETENESS = "metadata_completeness"
    SCIENTIFIC_VALIDITY = "scientific_validity"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    USABILITY = "usability"


@dataclass
class QualityIssue:
    """Individual quality issue with details and prioritization."""

    id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    location: str | None = None
    recommendation: str | None = None
    impact_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def priority_score(self) -> float:
        """Calculate priority score based on severity and impact."""
        severity_weights = {
            IssueSeverity.CRITICAL: 1.0,
            IssueSeverity.HIGH: 0.8,
            IssueSeverity.MEDIUM: 0.6,
            IssueSeverity.LOW: 0.4,
            IssueSeverity.INFO: 0.2,
        }
        return severity_weights[self.severity] * (1.0 + self.impact_score)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "recommendation": self.recommendation,
            "impact_score": self.impact_score,
            "priority_score": self.priority_score,
            "metadata": self.metadata,
        }


@dataclass
class QualityBenchmark:
    """Benchmark data for quality comparison."""

    name: str
    description: str
    target_scores: dict[str, float]
    baseline_scores: dict[str, float] = field(default_factory=dict)
    percentile_scores: dict[str, dict[str, float]] = field(default_factory=dict)

    def compare_score(self, metric_name: str, score: float) -> dict[str, Any]:
        """Compare a score against benchmark data."""
        target = self.target_scores.get(metric_name)
        baseline = self.baseline_scores.get(metric_name)
        percentiles = self.percentile_scores.get(metric_name, {})

        comparison = {
            "score": score,
            "target": target,
            "baseline": baseline,
            "meets_target": target is not None and score >= target,
            "above_baseline": baseline is not None and score > baseline,
            "percentile_rank": None,
        }

        # Calculate percentile rank if data available
        if percentiles:
            for percentile in sorted(percentiles.keys(), reverse=True):
                if score >= percentiles[percentile]:
                    comparison["percentile_rank"] = int(percentile)
                    break

        return comparison


@dataclass
class QualityAssessment:
    """Complete quality assessment with metrics, issues, and benchmarking."""

    overall_score: float
    dimension_scores: dict[str, float]
    metric_scores: dict[str, float]
    issues: list[QualityIssue]
    recommendations: list[str]
    strengths: list[str]
    weaknesses: list[str]
    benchmark_comparisons: dict[str, dict[str, Any]] = field(default_factory=dict)
    completeness_analysis: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_issues(self) -> list[QualityIssue]:
        """Get all critical severity issues."""
        return [
            issue for issue in self.issues if issue.severity == IssueSeverity.CRITICAL
        ]

    @property
    def high_priority_issues(self) -> list[QualityIssue]:
        """Get high priority issues (critical and high severity)."""
        return [
            issue
            for issue in self.issues
            if issue.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]
        ]

    def get_issues_by_category(self, category: IssueCategory) -> list[QualityIssue]:
        """Get all issues for a specific category."""
        return [issue for issue in self.issues if issue.category == category]

    def get_prioritized_issues(self, limit: int | None = None) -> list[QualityIssue]:
        """Get issues sorted by priority score."""
        sorted_issues = sorted(
            self.issues, key=lambda x: x.priority_score, reverse=True
        )
        return sorted_issues[:limit] if limit else sorted_issues

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "metric_scores": self.metric_scores,
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": self.recommendations,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "benchmark_comparisons": self.benchmark_comparisons,
            "completeness_analysis": self.completeness_analysis,
            "metadata": self.metadata,
            "summary": {
                "total_issues": len(self.issues),
                "critical_issues": len(self.critical_issues),
                "high_priority_issues": len(self.high_priority_issues),
            },
        }


class TechnicalQualityEvaluator:
    """Evaluates technical quality aspects of NWB conversions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Check critical dependencies at initialization
        check_critical_dependencies()

    def evaluate(
        self, nwb_path: str, validation_results: dict[str, Any]
    ) -> tuple[dict[str, float], list[QualityIssue]]:
        """Evaluate technical quality metrics and identify issues.

        Args:
            nwb_path: Path to the NWB file
            validation_results: Results from validation systems

        Returns:
            Tuple of (metric_scores, quality_issues)
        """
        metrics = {}
        issues = []

        # Schema compliance evaluation
        schema_score, schema_issues = self._evaluate_schema_compliance(
            validation_results
        )
        metrics["schema_compliance"] = schema_score
        issues.extend(schema_issues)

        # Data integrity evaluation
        integrity_score, integrity_issues = self._evaluate_data_integrity(nwb_path)
        metrics["data_integrity"] = integrity_score
        issues.extend(integrity_issues)

        # File structure evaluation
        structure_score, structure_issues = self._evaluate_file_structure(nwb_path)
        metrics["file_structure"] = structure_score
        issues.extend(structure_issues)

        # Performance evaluation
        performance_score, performance_issues = self._evaluate_performance(nwb_path)
        metrics["performance"] = performance_score
        issues.extend(performance_issues)

        return metrics, issues

    def _evaluate_schema_compliance(
        self, validation_results: dict[str, Any]
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate schema compliance and generate issues."""
        issues = []
        nwb_inspector_results = validation_results.get("nwb_inspector", {})
        validation_issues = nwb_inspector_results.get("issues", [])

        if not validation_issues:
            return 1.0, issues

        # Process validation issues
        critical_count = 0
        warning_count = 0

        for i, issue in enumerate(validation_issues):
            severity_map = {
                "critical": IssueSeverity.CRITICAL,
                "error": IssueSeverity.HIGH,
                "warning": IssueSeverity.MEDIUM,
                "info": IssueSeverity.LOW,
            }

            issue_severity = issue.get("severity", "warning")
            mapped_severity = severity_map.get(issue_severity, IssueSeverity.MEDIUM)

            if mapped_severity == IssueSeverity.CRITICAL:
                critical_count += 1
            elif mapped_severity in [IssueSeverity.HIGH, IssueSeverity.MEDIUM]:
                warning_count += 1

            quality_issue = QualityIssue(
                id=f"schema_{i}",
                category=IssueCategory.SCHEMA_COMPLIANCE,
                severity=mapped_severity,
                title=f"Schema validation issue: {issue_severity}",
                description=issue.get("message", "Unknown schema issue"),
                location=issue.get("location", "Unknown location"),
                recommendation=self._get_schema_recommendation(issue_severity),
                impact_score=0.8 if mapped_severity == IssueSeverity.CRITICAL else 0.4,
            )
            issues.append(quality_issue)

        # Calculate score based on issue severity
        penalty = (critical_count * 0.3) + (warning_count * 0.1)
        score = max(0.0, 1.0 - penalty)

        return score, issues

    def _evaluate_data_integrity(
        self, nwb_path: str
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate data integrity and identify issues."""
        issues = []

        try:
            # pynwb should be available due to dependency check in __init__
            import pynwb

            with pynwb.NWBHDF5IO(nwb_path, "r") as io:
                nwbfile = io.read()

                # Check for empty datasets
                empty_datasets = 0
                total_datasets = 0
                corrupted_datasets = 0

                for obj_name, obj in nwbfile.objects.items():
                    if hasattr(obj, "data") and obj.data is not None:
                        total_datasets += 1
                        try:
                            # Check if dataset is empty
                            if hasattr(obj.data, "shape") and 0 in obj.data.shape:
                                empty_datasets += 1
                                issues.append(
                                    QualityIssue(
                                        id=f"empty_dataset_{obj_name}",
                                        category=IssueCategory.DATA_INTEGRITY,
                                        severity=IssueSeverity.MEDIUM,
                                        title="Empty dataset detected",
                                        description=f"Dataset {obj_name} is empty",
                                        location=obj_name,
                                        recommendation="Verify data source and conversion process",
                                        impact_score=0.5,
                                    )
                                )

                            # Try to read a small sample to check for corruption
                            if hasattr(obj.data, "__getitem__"):
                                try:
                                    _ = (
                                        obj.data[0]
                                        if len(obj.data.shape) > 0
                                        else obj.data[()]
                                    )
                                except Exception:
                                    corrupted_datasets += 1
                                    issues.append(
                                        QualityIssue(
                                            id=f"corrupted_dataset_{obj_name}",
                                            category=IssueCategory.DATA_INTEGRITY,
                                            severity=IssueSeverity.HIGH,
                                            title="Corrupted dataset detected",
                                            description=f"Dataset {obj_name} cannot be read",
                                            location=obj_name,
                                            recommendation="Re-run conversion with data validation",
                                            impact_score=0.8,
                                        )
                                    )

                        except Exception as e:
                            self.logger.warning(
                                f"Error checking dataset {obj_name}: {e}"
                            )

                if total_datasets == 0:
                    issues.append(
                        QualityIssue(
                            id="no_datasets",
                            category=IssueCategory.DATA_INTEGRITY,
                            severity=IssueSeverity.HIGH,
                            title="No datasets found",
                            description="NWB file contains no data objects",
                            recommendation="Verify data source contains actual data",
                            impact_score=0.9,
                        )
                    )
                    return 0.3, issues

                # Calculate score
                empty_ratio = empty_datasets / total_datasets
                corrupted_ratio = corrupted_datasets / total_datasets
                score = 1.0 - (empty_ratio * 0.5) - (corrupted_ratio * 0.8)

                return max(0.0, score), issues

        except Exception as e:
            self.logger.error(f"Error evaluating data integrity: {e}")
            issues.append(
                QualityIssue(
                    id="integrity_evaluation_failed",
                    category=IssueCategory.DATA_INTEGRITY,
                    severity=IssueSeverity.HIGH,
                    title="Data integrity evaluation failed",
                    description=f"Could not evaluate data integrity: {str(e)}",
                    recommendation="Check file accessibility and format",
                    impact_score=0.7,
                )
            )
            return 0.0, issues

    def _evaluate_file_structure(
        self, nwb_path: str
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate file structure quality."""
        issues = []

        try:
            # pynwb should be available due to dependency check in __init__
            import pynwb

            with pynwb.NWBHDF5IO(nwb_path, "r") as io:
                nwbfile = io.read()

                score = 0.0
                structure_checks = {
                    "acquisition": (0.3, "Raw acquisition data"),
                    "processing": (0.3, "Processed data modules"),
                    "analysis": (0.2, "Analysis results"),
                    "stimulus": (0.2, "Stimulus information"),
                }

                for attr_name, (weight, description) in structure_checks.items():
                    attr_value = getattr(nwbfile, attr_name, None)
                    if attr_value and len(attr_value) > 0:
                        score += weight
                    else:
                        issues.append(
                            QualityIssue(
                                id=f"missing_{attr_name}",
                                category=IssueCategory.DATA_INTEGRITY,
                                severity=IssueSeverity.LOW,
                                title=f"Missing {attr_name} data",
                                description=f"No {description.lower()} found in file",
                                recommendation=f"Consider adding {description.lower()} if available",
                                impact_score=0.2,
                            )
                        )

                return min(1.0, score), issues

        except Exception as e:
            self.logger.error(f"Error evaluating file structure: {e}")
            issues.append(
                QualityIssue(
                    id="structure_evaluation_failed",
                    category=IssueCategory.DATA_INTEGRITY,
                    severity=IssueSeverity.MEDIUM,
                    title="File structure evaluation failed",
                    description=f"Could not evaluate file structure: {str(e)}",
                    recommendation="Check file format and accessibility",
                    impact_score=0.5,
                )
            )
            return 0.0, issues

    def _evaluate_performance(self, nwb_path: str) -> tuple[float, list[QualityIssue]]:
        """Evaluate file performance characteristics."""
        issues = []

        try:
            file_path = Path(nwb_path)
            if not file_path.exists():
                issues.append(
                    QualityIssue(
                        id="file_not_found",
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.CRITICAL,
                        title="File not found",
                        description=f"NWB file not found at {nwb_path}",
                        recommendation="Verify file path and permissions",
                        impact_score=1.0,
                    )
                )
                return 0.0, issues

            # Check file size
            file_size = file_path.stat().st_size
            size_mb = file_size / (1024 * 1024)

            score = 1.0

            # Flag very large files
            if size_mb > 1000:  # > 1GB
                issues.append(
                    QualityIssue(
                        id="large_file_size",
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.MEDIUM,
                        title="Large file size",
                        description=f"File size is {size_mb:.1f} MB",
                        recommendation="Consider data compression or chunking optimization",
                        impact_score=0.3,
                    )
                )
                score -= 0.2

            # Flag very small files (might indicate incomplete conversion)
            elif size_mb < 0.1:  # < 100KB
                issues.append(
                    QualityIssue(
                        id="small_file_size",
                        category=IssueCategory.PERFORMANCE,
                        severity=IssueSeverity.MEDIUM,
                        title="Unusually small file size",
                        description=f"File size is only {size_mb:.3f} MB",
                        recommendation="Verify conversion completed successfully",
                        impact_score=0.4,
                    )
                )
                score -= 0.3

            return max(0.0, score), issues

        except Exception as e:
            self.logger.error(f"Error evaluating performance: {e}")
            issues.append(
                QualityIssue(
                    id="performance_evaluation_failed",
                    category=IssueCategory.PERFORMANCE,
                    severity=IssueSeverity.MEDIUM,
                    title="Performance evaluation failed",
                    description=f"Could not evaluate performance: {str(e)}",
                    recommendation="Check file accessibility",
                    impact_score=0.5,
                )
            )
            return 0.5, issues

    def _get_schema_recommendation(self, severity: str) -> str:
        """Get recommendation based on schema issue severity."""
        recommendations = {
            "critical": "Immediate action required - file may not be readable",
            "error": "Address this issue to ensure proper file functionality",
            "warning": "Consider fixing to improve file quality",
            "info": "Optional improvement for better compliance",
        }
        return recommendations.get(severity, "Review and address as needed")


class ScientificQualityEvaluator:
    """Evaluates scientific quality aspects of conversions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def evaluate(
        self, nwb_path: str, metadata: dict[str, Any]
    ) -> tuple[dict[str, float], list[QualityIssue]]:
        """Evaluate scientific quality metrics and identify issues."""
        metrics = {}
        issues = []

        # Experimental completeness
        completeness_score, completeness_issues = (
            self._evaluate_experimental_completeness(metadata)
        )
        metrics["experimental_completeness"] = completeness_score
        issues.extend(completeness_issues)

        # Scientific validity
        validity_score, validity_issues = self._evaluate_scientific_validity(metadata)
        metrics["scientific_validity"] = validity_score
        issues.extend(validity_issues)

        # Reproducibility
        reproducibility_score, reproducibility_issues = self._evaluate_reproducibility(
            metadata
        )
        metrics["reproducibility"] = reproducibility_score
        issues.extend(reproducibility_issues)

        return metrics, issues

    def _evaluate_experimental_completeness(
        self, metadata: dict[str, Any]
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate completeness of experimental metadata."""
        issues = []
        required_fields = {
            "experimenter": "Researcher who conducted the experiment",
            "lab": "Laboratory where experiment was conducted",
            "institution": "Institution where experiment was conducted",
            "session_description": "Description of the experimental session",
            "identifier": "Unique identifier for the session",
            "session_start_time": "Start time of the experimental session",
        }

        missing_fields = []
        present_count = 0

        for field_name, description in required_fields.items():
            value = metadata.get(field_name)
            if value and str(value).strip():
                present_count += 1
            else:
                missing_fields.append(field_name)
                issues.append(
                    QualityIssue(
                        id=f"missing_{field_name}",
                        category=IssueCategory.METADATA_COMPLETENESS,
                        severity=IssueSeverity.MEDIUM,
                        title=f"Missing required field: {field_name}",
                        description=f"Required field '{field_name}' is missing or empty. {description}",
                        recommendation=f"Add {field_name} to improve metadata completeness",
                        impact_score=0.6,
                    )
                )

        score = present_count / len(required_fields)
        return score, issues

    def _evaluate_scientific_validity(
        self, metadata: dict[str, Any]
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate scientific validity of experimental design."""
        issues = []
        score = 0.8  # Base score

        # Check for subject information
        if not metadata.get("subject_id"):
            issues.append(
                QualityIssue(
                    id="missing_subject_id",
                    category=IssueCategory.SCIENTIFIC_VALIDITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Missing subject identifier",
                    description="No subject ID provided",
                    recommendation="Add subject identifier for proper experimental tracking",
                    impact_score=0.5,
                )
            )
            score -= 0.2

        # Check for species information
        if not metadata.get("species"):
            issues.append(
                QualityIssue(
                    id="missing_species",
                    category=IssueCategory.SCIENTIFIC_VALIDITY,
                    severity=IssueSeverity.LOW,
                    title="Missing species information",
                    description="No species information provided",
                    recommendation="Add species information for scientific context",
                    impact_score=0.3,
                )
            )
            score -= 0.1

        # Check session description quality
        description = metadata.get("session_description", "")
        if len(description) < 20:
            issues.append(
                QualityIssue(
                    id="poor_session_description",
                    category=IssueCategory.SCIENTIFIC_VALIDITY,
                    severity=IssueSeverity.LOW,
                    title="Insufficient session description",
                    description="Session description is too brief or missing",
                    recommendation="Provide detailed session description for scientific context",
                    impact_score=0.4,
                )
            )
            score -= 0.1

        return max(0.0, score), issues

    def _evaluate_reproducibility(
        self, metadata: dict[str, Any]
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate reproducibility aspects of the experiment."""
        issues = []
        score = 0.7  # Base score

        reproducibility_fields = {
            "protocol": "Experimental protocol information",
            "pharmacology": "Drug/pharmacological interventions",
            "surgery": "Surgical procedures performed",
            "virus": "Viral injections or genetic modifications",
            "stimulus_notes": "Stimulus presentation details",
        }

        present_count = 0
        for field_name, _description in reproducibility_fields.items():
            if metadata.get(field_name):
                present_count += 1

        # Bonus for having reproducibility information
        reproducibility_bonus = (present_count / len(reproducibility_fields)) * 0.3
        score += reproducibility_bonus

        # Check for timestamps
        if not metadata.get("session_start_time"):
            issues.append(
                QualityIssue(
                    id="missing_timestamp",
                    category=IssueCategory.SCIENTIFIC_VALIDITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Missing session timestamp",
                    description="No session start time provided",
                    recommendation="Add session timestamp for temporal context",
                    impact_score=0.4,
                )
            )

        return min(1.0, score), issues


class UsabilityQualityEvaluator:
    """Evaluates usability quality aspects of conversions."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def evaluate(
        self, nwb_path: str, metadata: dict[str, Any]
    ) -> tuple[dict[str, float], list[QualityIssue]]:
        """Evaluate usability quality metrics and identify issues."""
        metrics = {}
        issues = []

        # Documentation quality
        doc_score, doc_issues = self._evaluate_documentation_quality(metadata)
        metrics["documentation_quality"] = doc_score
        issues.extend(doc_issues)

        # Discoverability
        discover_score, discover_issues = self._evaluate_discoverability(metadata)
        metrics["discoverability"] = discover_score
        issues.extend(discover_issues)

        # Accessibility
        access_score, access_issues = self._evaluate_accessibility(nwb_path, metadata)
        metrics["accessibility"] = access_score
        issues.extend(access_issues)

        return metrics, issues

    def _evaluate_documentation_quality(
        self, metadata: dict[str, Any]
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate quality of documentation and descriptions."""
        issues = []
        description = metadata.get("session_description", "")

        if not description:
            issues.append(
                QualityIssue(
                    id="missing_description",
                    category=IssueCategory.DOCUMENTATION,
                    severity=IssueSeverity.MEDIUM,
                    title="Missing session description",
                    description="No session description provided",
                    recommendation="Add detailed session description",
                    impact_score=0.6,
                )
            )
            return 0.0, issues

        # Evaluate description quality based on length and content
        score = 0.0
        if len(description) > 100:
            score = 1.0
        elif len(description) > 50:
            score = 0.7
        elif len(description) > 20:
            score = 0.5
        else:
            score = 0.2
            issues.append(
                QualityIssue(
                    id="brief_description",
                    category=IssueCategory.DOCUMENTATION,
                    severity=IssueSeverity.LOW,
                    title="Brief session description",
                    description="Session description is very brief",
                    recommendation="Expand session description with more details",
                    impact_score=0.3,
                )
            )

        return score, issues

    def _evaluate_discoverability(
        self, metadata: dict[str, Any]
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate how discoverable and searchable the data is."""
        issues = []
        discoverable_fields = {
            "keywords": "Keywords for data discovery",
            "related_publications": "Related publications",
            "notes": "Additional notes",
            "experiment_description": "Experiment description",
        }

        present_count = 0
        for field_name, description in discoverable_fields.items():
            if metadata.get(field_name):
                present_count += 1
            else:
                issues.append(
                    QualityIssue(
                        id=f"missing_{field_name}",
                        category=IssueCategory.USABILITY,
                        severity=IssueSeverity.LOW,
                        title=f"Missing {field_name}",
                        description=f"No {description.lower()} provided",
                        recommendation=f"Add {field_name} to improve discoverability",
                        impact_score=0.2,
                    )
                )

        score = present_count / len(discoverable_fields)
        return score, issues

    def _evaluate_accessibility(
        self, nwb_path: str, metadata: dict[str, Any]
    ) -> tuple[float, list[QualityIssue]]:
        """Evaluate accessibility of the data file."""
        issues = []
        score = 1.0

        # Check file accessibility
        try:
            file_path = Path(nwb_path)
            if not file_path.exists():
                issues.append(
                    QualityIssue(
                        id="file_not_accessible",
                        category=IssueCategory.USABILITY,
                        severity=IssueSeverity.CRITICAL,
                        title="File not accessible",
                        description=f"Cannot access file at {nwb_path}",
                        recommendation="Verify file path and permissions",
                        impact_score=1.0,
                    )
                )
                return 0.0, issues

            # Check file permissions
            if not file_path.is_file():
                issues.append(
                    QualityIssue(
                        id="not_a_file",
                        category=IssueCategory.USABILITY,
                        severity=IssueSeverity.HIGH,
                        title="Path is not a file",
                        description=f"Path {nwb_path} does not point to a file",
                        recommendation="Verify file path is correct",
                        impact_score=0.9,
                    )
                )
                score -= 0.5

        except Exception as e:
            issues.append(
                QualityIssue(
                    id="accessibility_check_failed",
                    category=IssueCategory.USABILITY,
                    severity=IssueSeverity.MEDIUM,
                    title="Accessibility check failed",
                    description=f"Could not check file accessibility: {str(e)}",
                    recommendation="Verify file system permissions",
                    impact_score=0.5,
                )
            )
            score -= 0.3

        return max(0.0, score), issues


class QualityAssessmentEngine:
    """Main engine for comprehensive quality assessment."""

    def __init__(self):
        # Check critical dependencies before initializing evaluators
        check_critical_dependencies()

        self.technical_evaluator = TechnicalQualityEvaluator()
        self.scientific_evaluator = ScientificQualityEvaluator()
        self.usability_evaluator = UsabilityQualityEvaluator()
        self.logger = logging.getLogger(__name__)
        self._benchmarks: dict[str, QualityBenchmark] = {}

    def register_benchmark(self, benchmark: QualityBenchmark) -> None:
        """Register a quality benchmark for comparison."""
        self._benchmarks[benchmark.name] = benchmark
        self.logger.info(f"Registered benchmark: {benchmark.name}")

    def assess_quality(
        self,
        nwb_path: str,
        validation_results: dict[str, Any],
        metadata: dict[str, Any],
        benchmark_name: str | None = None,
    ) -> QualityAssessment:
        """Perform comprehensive quality assessment.

        Args:
            nwb_path: Path to the NWB file
            validation_results: Results from validation systems
            metadata: Conversion metadata
            benchmark_name: Optional benchmark to compare against

        Returns:
            Complete quality assessment
        """
        self.logger.info(f"Starting quality assessment for {nwb_path}")

        all_metrics = {}
        all_issues = []

        try:
            # Technical quality evaluation
            tech_metrics, tech_issues = self.technical_evaluator.evaluate(
                nwb_path, validation_results
            )
            all_metrics.update({f"technical_{k}": v for k, v in tech_metrics.items()})
            all_issues.extend(tech_issues)

            # Scientific quality evaluation
            sci_metrics, sci_issues = self.scientific_evaluator.evaluate(
                nwb_path, metadata
            )
            all_metrics.update({f"scientific_{k}": v for k, v in sci_metrics.items()})
            all_issues.extend(sci_issues)

            # Usability quality evaluation
            usability_metrics, usability_issues = self.usability_evaluator.evaluate(
                nwb_path, metadata
            )
            all_metrics.update(
                {f"usability_{k}": v for k, v in usability_metrics.items()}
            )
            all_issues.extend(usability_issues)

            # Calculate dimension scores
            dimension_scores = self._calculate_dimension_scores(all_metrics)

            # Calculate overall score
            overall_score = sum(dimension_scores.values()) / len(dimension_scores)

            # Generate insights
            recommendations = self._generate_recommendations(
                all_issues, dimension_scores
            )
            strengths = self._identify_strengths(all_metrics)
            weaknesses = self._identify_weaknesses(all_metrics)

            # Perform benchmark comparison if requested
            benchmark_comparisons = {}
            if benchmark_name and benchmark_name in self._benchmarks:
                benchmark = self._benchmarks[benchmark_name]
                benchmark_comparisons = self._compare_with_benchmark(
                    all_metrics, benchmark
                )

            # Analyze completeness
            completeness_analysis = self._analyze_completeness(metadata, all_issues)

            assessment = QualityAssessment(
                overall_score=overall_score,
                dimension_scores=dimension_scores,
                metric_scores=all_metrics,
                issues=all_issues,
                recommendations=recommendations,
                strengths=strengths,
                weaknesses=weaknesses,
                benchmark_comparisons=benchmark_comparisons,
                completeness_analysis=completeness_analysis,
                metadata={
                    "nwb_path": nwb_path,
                    "evaluation_timestamp": logger.handlers[0].formatter.formatTime(
                        logging.LogRecord("", 0, "", 0, "", (), None)
                    )
                    if logger.handlers
                    else "unknown",
                    "total_metrics": len(all_metrics),
                    "benchmark_used": benchmark_name,
                },
            )

            self.logger.info(
                f"Quality assessment completed. Overall score: {overall_score:.3f}, "
                f"Issues: {len(all_issues)}"
            )

            return assessment

        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            # Return minimal assessment with error
            return QualityAssessment(
                overall_score=0.0,
                dimension_scores={
                    "technical": 0.0,
                    "scientific": 0.0,
                    "usability": 0.0,
                },
                metric_scores={},
                issues=[
                    QualityIssue(
                        id="assessment_failed",
                        category=IssueCategory.SCHEMA_COMPLIANCE,
                        severity=IssueSeverity.CRITICAL,
                        title="Quality assessment failed",
                        description=f"Assessment could not be completed: {str(e)}",
                        recommendation="Check file accessibility and system configuration",
                        impact_score=1.0,
                    )
                ],
                recommendations=["Fix assessment errors before proceeding"],
                strengths=[],
                weaknesses=["Assessment could not be completed"],
                metadata={"error": str(e)},
            )

    def _calculate_dimension_scores(
        self, metrics: dict[str, float]
    ) -> dict[str, float]:
        """Calculate scores for each quality dimension."""
        dimensions = {"technical": [], "scientific": [], "usability": []}

        for metric_name, score in metrics.items():
            if metric_name.startswith("technical_"):
                dimensions["technical"].append(score)
            elif metric_name.startswith("scientific_"):
                dimensions["scientific"].append(score)
            elif metric_name.startswith("usability_"):
                dimensions["usability"].append(score)

        dimension_scores = {}
        for dimension, scores in dimensions.items():
            if scores:
                dimension_scores[dimension] = sum(scores) / len(scores)
            else:
                dimension_scores[dimension] = 0.0

        return dimension_scores

    def _generate_recommendations(
        self, issues: list[QualityIssue], dimension_scores: dict[str, float]
    ) -> list[str]:
        """Generate improvement recommendations based on issues and scores."""
        recommendations = []

        # Priority recommendations from critical issues
        critical_issues = [
            issue for issue in issues if issue.severity == IssueSeverity.CRITICAL
        ]
        for issue in critical_issues:
            if issue.recommendation:
                recommendations.append(f"CRITICAL: {issue.recommendation}")

        # Dimension-specific recommendations
        for dimension, score in dimension_scores.items():
            if score < 0.7:
                if dimension == "technical":
                    recommendations.append("Focus on technical quality improvements")
                elif dimension == "scientific":
                    recommendations.append("Enhance scientific metadata completeness")
                elif dimension == "usability":
                    recommendations.append("Improve documentation and discoverability")

        # Category-specific recommendations
        category_counts = {}
        for issue in issues:
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        for category, count in category_counts.items():
            if count >= 3:  # Multiple issues in same category
                recommendations.append(
                    f"Address multiple {category.value} issues ({count} found)"
                )

        return recommendations

    def _identify_strengths(self, metrics: dict[str, float]) -> list[str]:
        """Identify strengths based on high-scoring metrics."""
        strengths = []
        high_metrics = {name: score for name, score in metrics.items() if score >= 0.8}

        metric_descriptions = {
            "technical_schema_compliance": "excellent schema compliance",
            "technical_data_integrity": "excellent data integrity",
            "technical_file_structure": "well-organized file structure",
            "technical_performance": "good performance characteristics",
            "scientific_experimental_completeness": "complete experimental metadata",
            "scientific_scientific_validity": "scientifically valid design",
            "scientific_reproducibility": "good reproducibility information",
            "usability_documentation_quality": "high-quality documentation",
            "usability_discoverability": "good discoverability features",
            "usability_accessibility": "excellent accessibility",
        }

        for metric_name, score in high_metrics.items():
            description = metric_descriptions.get(metric_name, f"good {metric_name}")
            strengths.append(f"Demonstrates {description} ({score:.1%})")

        return strengths

    def _identify_weaknesses(self, metrics: dict[str, float]) -> list[str]:
        """Identify weaknesses based on low-scoring metrics."""
        weaknesses = []
        low_metrics = {name: score for name, score in metrics.items() if score < 0.5}

        metric_descriptions = {
            "technical_schema_compliance": "poor schema compliance",
            "technical_data_integrity": "data integrity issues",
            "technical_file_structure": "poor file organization",
            "technical_performance": "performance concerns",
            "scientific_experimental_completeness": "incomplete experimental metadata",
            "scientific_scientific_validity": "scientific validity concerns",
            "scientific_reproducibility": "limited reproducibility information",
            "usability_documentation_quality": "poor documentation quality",
            "usability_discoverability": "limited discoverability",
            "usability_accessibility": "accessibility issues",
        }

        for metric_name, score in low_metrics.items():
            description = metric_descriptions.get(
                metric_name, f"issues with {metric_name}"
            )
            weaknesses.append(f"Shows {description} ({score:.1%})")

        return weaknesses

    def _compare_with_benchmark(
        self, metrics: dict[str, float], benchmark: QualityBenchmark
    ) -> dict[str, dict[str, Any]]:
        """Compare metrics against benchmark data."""
        comparisons = {}

        for metric_name, score in metrics.items():
            comparison = benchmark.compare_score(metric_name, score)
            if comparison["target"] is not None or comparison["baseline"] is not None:
                comparisons[metric_name] = comparison

        return comparisons

    def _analyze_completeness(
        self, metadata: dict[str, Any], issues: list[QualityIssue]
    ) -> dict[str, Any]:
        """Analyze metadata completeness and missing information."""
        completeness_issues = [
            issue
            for issue in issues
            if issue.category == IssueCategory.METADATA_COMPLETENESS
        ]

        missing_fields = []
        for issue in completeness_issues:
            if "missing" in issue.id:
                field_name = issue.id.replace("missing_", "")
                missing_fields.append(field_name)

        total_expected_fields = 20  # Rough estimate of expected metadata fields
        present_fields = len([k for k, v in metadata.items() if v])
        completeness_percentage = (present_fields / total_expected_fields) * 100

        return {
            "completeness_percentage": min(100.0, completeness_percentage),
            "missing_fields": missing_fields,
            "present_fields": present_fields,
            "total_expected_fields": total_expected_fields,
            "completeness_issues_count": len(completeness_issues),
        }

    def create_default_benchmark(self) -> QualityBenchmark:
        """Create a default benchmark for quality comparison."""
        return QualityBenchmark(
            name="default_nwb_benchmark",
            description="Default benchmark for NWB conversion quality",
            target_scores={
                "technical_schema_compliance": 0.9,
                "technical_data_integrity": 0.95,
                "technical_file_structure": 0.8,
                "technical_performance": 0.7,
                "scientific_experimental_completeness": 0.8,
                "scientific_scientific_validity": 0.85,
                "scientific_reproducibility": 0.7,
                "usability_documentation_quality": 0.75,
                "usability_discoverability": 0.6,
                "usability_accessibility": 0.9,
            },
            baseline_scores={
                "technical_schema_compliance": 0.7,
                "technical_data_integrity": 0.8,
                "technical_file_structure": 0.6,
                "technical_performance": 0.5,
                "scientific_experimental_completeness": 0.6,
                "scientific_scientific_validity": 0.7,
                "scientific_reproducibility": 0.5,
                "usability_documentation_quality": 0.5,
                "usability_discoverability": 0.4,
                "usability_accessibility": 0.8,
            },
        )

    def list_benchmarks(self) -> list[str]:
        """List all registered benchmarks."""
        return list(self._benchmarks.keys())
