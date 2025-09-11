"""Core evaluation framework for conversion quality assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from pathlib import Path
from typing import Any

from .quality_assessment import QualityAssessmentEngine, QualityBenchmark

logger = logging.getLogger(__name__)


class QualityDimension(Enum):
    """Quality assessment dimensions."""

    TECHNICAL = "technical"
    SCIENTIFIC = "scientific"
    USABILITY = "usability"


class EvaluationStatus(Enum):
    """Status of evaluation process."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QualityMetrics:
    """Individual quality metric with scoring and metadata."""

    name: str
    value: float
    max_value: float
    description: str
    dimension: QualityDimension
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_score(self) -> float:
        """Get normalized score (0-1)."""
        return self.value / self.max_value if self.max_value > 0 else 0.0

    @property
    def percentage_score(self) -> float:
        """Get percentage score (0-100)."""
        return self.normalized_score * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "value": self.value,
            "max_value": self.max_value,
            "normalized_score": self.normalized_score,
            "percentage_score": self.percentage_score,
            "description": self.description,
            "dimension": self.dimension.value,
            "weight": self.weight,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationResult:
    """Complete evaluation results with quality assessment and metadata."""

    overall_score: float
    dimension_scores: dict[QualityDimension, float]
    metrics: list[QualityMetrics]
    recommendations: list[str]
    strengths: list[str]
    weaknesses: list[str]
    status: EvaluationStatus
    timestamp: datetime = field(default_factory=datetime.now)
    evaluation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_percentage(self) -> float:
        """Get overall score as percentage."""
        return self.overall_score * 100

    def get_metrics_by_dimension(
        self, dimension: QualityDimension
    ) -> list[QualityMetrics]:
        """Get all metrics for a specific dimension."""
        return [m for m in self.metrics if m.dimension == dimension]

    def get_metric_by_name(self, name: str) -> QualityMetrics | None:
        """Get a specific metric by name."""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "evaluation_id": self.evaluation_id,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "overall_score": self.overall_score,
            "overall_percentage": self.overall_percentage,
            "dimension_scores": {
                dim.value: score for dim, score in self.dimension_scores.items()
            },
            "metrics": [metric.to_dict() for metric in self.metrics],
            "recommendations": self.recommendations,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationCriteria:
    """Customizable evaluation criteria for different use cases."""

    name: str
    description: str
    dimension_weights: dict[QualityDimension, float] = field(default_factory=dict)
    metric_weights: dict[str, float] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    enabled_metrics: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Set default weights if not provided."""
        if not self.dimension_weights:
            # Equal weights for all dimensions by default
            self.dimension_weights = {
                QualityDimension.TECHNICAL: 1.0,
                QualityDimension.SCIENTIFIC: 1.0,
                QualityDimension.USABILITY: 1.0,
            }

    def get_dimension_weight(self, dimension: QualityDimension) -> float:
        """Get weight for a specific dimension."""
        return self.dimension_weights.get(dimension, 1.0)

    def get_metric_weight(self, metric_name: str) -> float:
        """Get weight for a specific metric."""
        return self.metric_weights.get(metric_name, 1.0)

    def is_metric_enabled(self, metric_name: str) -> bool:
        """Check if a metric is enabled."""
        if not self.enabled_metrics:
            return True  # All metrics enabled by default
        return metric_name in self.enabled_metrics


@dataclass
class EvaluationConfig:
    """Configuration for evaluation framework."""

    criteria: EvaluationCriteria
    output_formats: list[str] = field(default_factory=lambda: ["json", "markdown"])
    include_visualizations: bool = True
    include_provenance: bool = True
    include_recommendations: bool = True
    parallel_evaluation: bool = False
    cache_results: bool = True
    output_directory: Path | None = None

    def __post_init__(self):
        """Validate configuration."""
        valid_formats = {"json", "markdown", "html", "pdf", "csv"}
        invalid_formats = set(self.output_formats) - valid_formats
        if invalid_formats:
            raise ValueError(f"Invalid output formats: {invalid_formats}")

        if self.output_directory:
            self.output_directory = Path(self.output_directory)


class EvaluationFramework:
    """Main evaluation framework for conversion quality assessment."""

    def __init__(self, config: EvaluationConfig | None = None):
        """Initialize evaluation framework.

        Args:
            config: Evaluation configuration. If None, uses default configuration.
        """
        self.config = config or self._create_default_config()
        self.logger = logging.getLogger(__name__)
        self._evaluators: dict[str, Any] = {}
        self._results_cache: dict[str, EvaluationResult] = {}

        # Initialize quality assessment engine
        self.quality_assessment_engine = QualityAssessmentEngine()

        # Register default benchmark
        default_benchmark = self.quality_assessment_engine.create_default_benchmark()
        self.quality_assessment_engine.register_benchmark(default_benchmark)

    def _create_default_config(self) -> EvaluationConfig:
        """Create default evaluation configuration."""
        default_criteria = EvaluationCriteria(
            name="default",
            description="Default evaluation criteria for general use",
        )
        return EvaluationConfig(criteria=default_criteria)

    def register_evaluator(self, name: str, evaluator: Any) -> None:
        """Register a quality evaluator.

        Args:
            name: Name of the evaluator
            evaluator: Evaluator instance with evaluate() method
        """
        if not hasattr(evaluator, "evaluate"):
            raise ValueError(f"Evaluator {name} must have an 'evaluate' method")

        self._evaluators[name] = evaluator
        self.logger.info(f"Registered evaluator: {name}")

    def evaluate(
        self,
        nwb_path: str | Path,
        validation_results: dict[str, Any],
        conversion_metadata: dict[str, Any],
        provenance_data: dict[str, Any] | None = None,
        evaluation_id: str | None = None,
    ) -> EvaluationResult:
        """Perform comprehensive evaluation of conversion results.

        Args:
            nwb_path: Path to the NWB file
            validation_results: Results from validation systems
            conversion_metadata: Metadata about the conversion
            provenance_data: Optional provenance information
            evaluation_id: Optional unique identifier for this evaluation

        Returns:
            Complete evaluation results
        """
        nwb_path = Path(nwb_path)
        evaluation_id = evaluation_id or self._generate_evaluation_id(nwb_path)

        # Check cache if enabled
        if self.config.cache_results and evaluation_id in self._results_cache:
            self.logger.info(f"Returning cached results for {evaluation_id}")
            return self._results_cache[evaluation_id]

        self.logger.info(f"Starting evaluation {evaluation_id} for {nwb_path}")

        try:
            # Collect metrics from all registered evaluators
            all_metrics = self._collect_metrics(
                nwb_path, validation_results, conversion_metadata, provenance_data
            )

            # Calculate dimension scores
            dimension_scores = self._calculate_dimension_scores(all_metrics)

            # Calculate overall score
            overall_score = self._calculate_overall_score(dimension_scores)

            # Generate insights
            recommendations = self._generate_recommendations(
                all_metrics, dimension_scores
            )
            strengths = self._identify_strengths(all_metrics)
            weaknesses = self._identify_weaknesses(all_metrics)

            # Create result
            result = EvaluationResult(
                evaluation_id=evaluation_id,
                overall_score=overall_score,
                dimension_scores=dimension_scores,
                metrics=all_metrics,
                recommendations=recommendations,
                strengths=strengths,
                weaknesses=weaknesses,
                status=EvaluationStatus.COMPLETED,
                metadata={
                    "nwb_path": str(nwb_path),
                    "conversion_metadata": conversion_metadata,
                    "evaluator_count": len(self._evaluators),
                    "config": {
                        "criteria_name": self.config.criteria.name,
                        "output_formats": self.config.output_formats,
                    },
                },
            )

            # Cache result if enabled
            if self.config.cache_results:
                self._results_cache[evaluation_id] = result

            self.logger.info(f"Completed evaluation {evaluation_id}")
            return result

        except Exception as e:
            self.logger.error(f"Evaluation {evaluation_id} failed: {e}")
            return EvaluationResult(
                evaluation_id=evaluation_id,
                overall_score=0.0,
                dimension_scores=dict.fromkeys(QualityDimension, 0.0),
                metrics=[],
                recommendations=[f"Evaluation failed: {str(e)}"],
                strengths=[],
                weaknesses=["Evaluation could not be completed"],
                status=EvaluationStatus.FAILED,
                metadata={"error": str(e)},
            )

    def _collect_metrics(
        self,
        nwb_path: Path,
        validation_results: dict[str, Any],
        conversion_metadata: dict[str, Any],
        provenance_data: dict[str, Any] | None,
    ) -> list[QualityMetrics]:
        """Collect metrics from all registered evaluators."""
        all_metrics = []

        for evaluator_name, evaluator in self._evaluators.items():
            try:
                self.logger.debug(f"Running evaluator: {evaluator_name}")

                # Call evaluator with available parameters
                if hasattr(evaluator, "evaluate"):
                    metrics = evaluator.evaluate(
                        str(nwb_path), validation_results, conversion_metadata
                    )

                    # Apply criteria filtering and weighting
                    filtered_metrics = self._apply_criteria_to_metrics(metrics)
                    all_metrics.extend(filtered_metrics)

                    self.logger.debug(
                        f"Evaluator {evaluator_name} produced {len(filtered_metrics)} metrics"
                    )

            except Exception as e:
                self.logger.error(f"Evaluator {evaluator_name} failed: {e}")
                # Add error metric
                error_metric = QualityMetrics(
                    name=f"{evaluator_name}_error",
                    value=0.0,
                    max_value=1.0,
                    description=f"Evaluator {evaluator_name} failed: {str(e)}",
                    dimension=QualityDimension.TECHNICAL,
                    metadata={"error": str(e), "evaluator": evaluator_name},
                )
                all_metrics.append(error_metric)

        return all_metrics

    def _apply_criteria_to_metrics(
        self, metrics: list[QualityMetrics]
    ) -> list[QualityMetrics]:
        """Apply evaluation criteria to filter and weight metrics."""
        filtered_metrics = []

        for metric in metrics:
            # Check if metric is enabled
            if not self.config.criteria.is_metric_enabled(metric.name):
                continue

            # Apply custom weight
            custom_weight = self.config.criteria.get_metric_weight(metric.name)
            metric.weight = custom_weight

            filtered_metrics.append(metric)

        return filtered_metrics

    def _calculate_dimension_scores(
        self, metrics: list[QualityMetrics]
    ) -> dict[QualityDimension, float]:
        """Calculate weighted scores for each quality dimension."""
        dimension_scores = {}

        for dimension in QualityDimension:
            dimension_metrics = [m for m in metrics if m.dimension == dimension]

            if not dimension_metrics:
                dimension_scores[dimension] = 0.0
                continue

            # Calculate weighted average
            weighted_sum = sum(m.normalized_score * m.weight for m in dimension_metrics)
            total_weight = sum(m.weight for m in dimension_metrics)

            if total_weight > 0:
                dimension_scores[dimension] = weighted_sum / total_weight
            else:
                dimension_scores[dimension] = 0.0

        return dimension_scores

    def _calculate_overall_score(
        self, dimension_scores: dict[QualityDimension, float]
    ) -> float:
        """Calculate overall weighted score across all dimensions."""
        if not dimension_scores:
            return 0.0

        # Apply dimension weights from criteria
        weighted_sum = 0.0
        total_weight = 0.0

        for dimension, score in dimension_scores.items():
            weight = self.config.criteria.get_dimension_weight(dimension)
            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _generate_recommendations(
        self,
        metrics: list[QualityMetrics],
        dimension_scores: dict[QualityDimension, float],
    ) -> list[str]:
        """Generate improvement recommendations based on evaluation results."""
        if not self.config.include_recommendations:
            return []

        recommendations = []

        # Identify low-scoring metrics
        low_metrics = [m for m in metrics if m.normalized_score < 0.7]

        for metric in low_metrics:
            if metric.name == "schema_compliance":
                recommendations.append(
                    "Address schema validation issues to improve compliance"
                )
            elif metric.name == "experimental_completeness":
                recommendations.append("Add missing experimental metadata fields")
            elif metric.name == "documentation_quality":
                recommendations.append("Improve session description and documentation")
            else:
                recommendations.append(f"Improve {metric.description.lower()}")

        # Dimension-specific recommendations
        for dimension, score in dimension_scores.items():
            if score < 0.7:
                if dimension == QualityDimension.TECHNICAL:
                    recommendations.append("Focus on technical quality improvements")
                elif dimension == QualityDimension.SCIENTIFIC:
                    recommendations.append("Enhance scientific metadata completeness")
                elif dimension == QualityDimension.USABILITY:
                    recommendations.append("Improve documentation and discoverability")

        return recommendations

    def _identify_strengths(self, metrics: list[QualityMetrics]) -> list[str]:
        """Identify conversion strengths based on high-scoring metrics."""
        strengths = []
        high_metrics = [m for m in metrics if m.normalized_score >= 0.8]

        for metric in high_metrics:
            strengths.append(f"Excellent {metric.description.lower()}")

        return strengths

    def _identify_weaknesses(self, metrics: list[QualityMetrics]) -> list[str]:
        """Identify conversion weaknesses based on low-scoring metrics."""
        weaknesses = []
        low_metrics = [m for m in metrics if m.normalized_score < 0.5]

        for metric in low_metrics:
            weaknesses.append(f"Poor {metric.description.lower()}")

        return weaknesses

    def _generate_evaluation_id(self, nwb_path: Path) -> str:
        """Generate unique evaluation ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = nwb_path.stem
        return f"eval_{filename}_{timestamp}"

    def get_cached_result(self, evaluation_id: str) -> EvaluationResult | None:
        """Get cached evaluation result by ID."""
        return self._results_cache.get(evaluation_id)

    def clear_cache(self) -> None:
        """Clear all cached evaluation results."""
        self._results_cache.clear()
        self.logger.info("Cleared evaluation results cache")

    def list_evaluators(self) -> list[str]:
        """List all registered evaluators."""
        return list(self._evaluators.keys())

    def update_config(self, config: EvaluationConfig) -> None:
        """Update evaluation configuration."""
        self.config = config
        self.logger.info("Updated evaluation configuration")

    def assess_conversion_quality(
        self,
        nwb_path: str | Path,
        validation_results: dict[str, Any],
        conversion_metadata: dict[str, Any],
        benchmark_name: str | None = None,
    ) -> Any:
        """Perform comprehensive quality assessment using the quality assessment engine.

        Args:
            nwb_path: Path to the NWB file
            validation_results: Results from validation systems
            conversion_metadata: Metadata about the conversion
            benchmark_name: Optional benchmark to compare against

        Returns:
            QualityAssessment object with comprehensive quality analysis
        """
        return self.quality_assessment_engine.assess_quality(
            str(nwb_path), validation_results, conversion_metadata, benchmark_name
        )

    def register_quality_benchmark(self, benchmark: QualityBenchmark) -> None:
        """Register a quality benchmark for comparison.

        Args:
            benchmark: Quality benchmark to register
        """
        self.quality_assessment_engine.register_benchmark(benchmark)

    def list_quality_benchmarks(self) -> list[str]:
        """List all registered quality benchmarks.

        Returns:
            List of benchmark names
        """
        return self.quality_assessment_engine.list_benchmarks()
