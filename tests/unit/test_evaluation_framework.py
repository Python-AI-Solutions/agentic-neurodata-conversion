"""Unit tests for evaluation framework."""

from datetime import datetime
from pathlib import Path

import pytest

try:
    from agentic_neurodata_conversion.evaluation.framework import (
        EvaluationConfig,
        EvaluationCriteria,
        EvaluationFramework,
        EvaluationResult,
        EvaluationStatus,
        QualityDimension,
        QualityMetrics,
    )

    EVALUATION_AVAILABLE = True
except ImportError:
    EVALUATION_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not EVALUATION_AVAILABLE, reason="Evaluation framework not implemented yet"
)


class MockEvaluator:
    """Mock evaluator for testing."""

    def evaluate(
        self, nwb_path: str, validation_results: dict, conversion_metadata: dict
    ):
        """Mock evaluation that returns test metrics."""
        return [
            QualityMetrics(
                name="test_metric",
                value=0.8,
                max_value=1.0,
                description="Test metric for validation",
                dimension=QualityDimension.TECHNICAL,
            ),
            QualityMetrics(
                name="completeness_metric",
                value=0.6,
                max_value=1.0,
                description="Test completeness metric",
                dimension=QualityDimension.SCIENTIFIC,
            ),
        ]


@pytest.mark.unit
class TestQualityMetrics:
    """Test QualityMetrics dataclass."""

    def test_quality_metrics_creation(self):
        """Test creating QualityMetrics instance."""
        metric = QualityMetrics(
            name="test_metric",
            value=0.8,
            max_value=1.0,
            description="Test metric",
            dimension=QualityDimension.TECHNICAL,
        )

        assert metric.name == "test_metric"
        assert metric.value == 0.8
        assert metric.max_value == 1.0
        assert metric.normalized_score == 0.8
        assert metric.percentage_score == 80.0
        assert metric.dimension == QualityDimension.TECHNICAL

    def test_quality_metrics_to_dict(self):
        """Test converting QualityMetrics to dictionary."""
        metric = QualityMetrics(
            name="test_metric",
            value=0.8,
            max_value=1.0,
            description="Test metric",
            dimension=QualityDimension.TECHNICAL,
        )

        result = metric.to_dict()

        assert result["name"] == "test_metric"
        assert result["value"] == 0.8
        assert result["normalized_score"] == 0.8
        assert result["percentage_score"] == 80.0
        assert result["dimension"] == "technical"


@pytest.mark.unit
class TestEvaluationCriteria:
    """Test EvaluationCriteria dataclass."""

    def test_evaluation_criteria_creation(self):
        """Test creating EvaluationCriteria instance."""
        criteria = EvaluationCriteria(
            name="test_criteria",
            description="Test evaluation criteria",
        )

        assert criteria.name == "test_criteria"
        assert criteria.description == "Test evaluation criteria"
        # Should have default dimension weights
        assert QualityDimension.TECHNICAL in criteria.dimension_weights
        assert criteria.dimension_weights[QualityDimension.TECHNICAL] == 1.0

    def test_evaluation_criteria_custom_weights(self):
        """Test EvaluationCriteria with custom weights."""
        criteria = EvaluationCriteria(
            name="test_criteria",
            description="Test evaluation criteria",
            dimension_weights={
                QualityDimension.TECHNICAL: 2.0,
                QualityDimension.SCIENTIFIC: 1.5,
                QualityDimension.USABILITY: 1.0,
            },
            metric_weights={"test_metric": 2.0},
        )

        assert criteria.get_dimension_weight(QualityDimension.TECHNICAL) == 2.0
        assert criteria.get_metric_weight("test_metric") == 2.0
        assert criteria.get_metric_weight("unknown_metric") == 1.0  # Default


@pytest.mark.unit
class TestEvaluationConfig:
    """Test EvaluationConfig dataclass."""

    def test_evaluation_config_creation(self):
        """Test creating EvaluationConfig instance."""
        criteria = EvaluationCriteria(
            name="test_criteria",
            description="Test evaluation criteria",
        )
        config = EvaluationConfig(criteria=criteria)

        assert config.criteria == criteria
        assert "json" in config.output_formats
        assert "markdown" in config.output_formats
        assert config.include_visualizations is True

    def test_evaluation_config_invalid_format(self):
        """Test EvaluationConfig with invalid output format."""
        criteria = EvaluationCriteria(
            name="test_criteria",
            description="Test evaluation criteria",
        )

        with pytest.raises(ValueError, match="Invalid output formats"):
            EvaluationConfig(criteria=criteria, output_formats=["invalid_format"])


@pytest.mark.unit
class TestEvaluationFramework:
    """Test EvaluationFramework class."""

    def test_framework_creation(self):
        """Test creating EvaluationFramework instance."""
        framework = EvaluationFramework()

        assert framework.config is not None
        assert framework.config.criteria.name == "default"
        assert len(framework.list_evaluators()) == 0

    def test_framework_with_custom_config(self):
        """Test EvaluationFramework with custom configuration."""
        criteria = EvaluationCriteria(
            name="custom_criteria",
            description="Custom evaluation criteria",
        )
        config = EvaluationConfig(criteria=criteria)
        framework = EvaluationFramework(config=config)

        assert framework.config.criteria.name == "custom_criteria"

    def test_register_evaluator(self):
        """Test registering an evaluator."""
        framework = EvaluationFramework()
        evaluator = MockEvaluator()

        framework.register_evaluator("mock_evaluator", evaluator)

        assert "mock_evaluator" in framework.list_evaluators()

    def test_register_invalid_evaluator(self):
        """Test registering invalid evaluator raises error."""
        framework = EvaluationFramework()
        invalid_evaluator = object()  # No evaluate method

        with pytest.raises(ValueError, match="must have an 'evaluate' method"):
            framework.register_evaluator("invalid", invalid_evaluator)

    def test_evaluate_with_mock_evaluator(self):
        """Test evaluation with mock evaluator."""
        framework = EvaluationFramework()
        evaluator = MockEvaluator()
        framework.register_evaluator("mock_evaluator", evaluator)

        # Mock data
        nwb_path = Path("/fake/path/test.nwb")
        validation_results = {"nwb_inspector": {"issues": []}}
        conversion_metadata = {"experimenter": "Test User"}

        result = framework.evaluate(
            nwb_path=nwb_path,
            validation_results=validation_results,
            conversion_metadata=conversion_metadata,
        )

        assert isinstance(result, EvaluationResult)
        assert result.status == EvaluationStatus.COMPLETED
        assert result.overall_score > 0
        assert len(result.metrics) == 2  # From MockEvaluator
        assert result.evaluation_id is not None
        assert isinstance(result.timestamp, datetime)

    def test_evaluate_caching(self):
        """Test evaluation result caching."""
        framework = EvaluationFramework()
        evaluator = MockEvaluator()
        framework.register_evaluator("mock_evaluator", evaluator)

        # Mock data
        nwb_path = Path("/fake/path/test.nwb")
        validation_results = {"nwb_inspector": {"issues": []}}
        conversion_metadata = {"experimenter": "Test User"}
        evaluation_id = "test_eval_123"

        # First evaluation
        result1 = framework.evaluate(
            nwb_path=nwb_path,
            validation_results=validation_results,
            conversion_metadata=conversion_metadata,
            evaluation_id=evaluation_id,
        )

        # Second evaluation with same ID should return cached result
        result2 = framework.evaluate(
            nwb_path=nwb_path,
            validation_results=validation_results,
            conversion_metadata=conversion_metadata,
            evaluation_id=evaluation_id,
        )

        assert result1 is result2  # Same object from cache

        # Test cache retrieval
        cached_result = framework.get_cached_result(evaluation_id)
        assert cached_result is result1

    def test_clear_cache(self):
        """Test clearing evaluation cache."""
        framework = EvaluationFramework()
        evaluator = MockEvaluator()
        framework.register_evaluator("mock_evaluator", evaluator)

        # Mock data
        nwb_path = Path("/fake/path/test.nwb")
        validation_results = {"nwb_inspector": {"issues": []}}
        conversion_metadata = {"experimenter": "Test User"}
        evaluation_id = "test_eval_123"

        # Create cached result
        framework.evaluate(
            nwb_path=nwb_path,
            validation_results=validation_results,
            conversion_metadata=conversion_metadata,
            evaluation_id=evaluation_id,
        )

        assert framework.get_cached_result(evaluation_id) is not None

        # Clear cache
        framework.clear_cache()

        assert framework.get_cached_result(evaluation_id) is None

    def test_evaluate_no_evaluators(self):
        """Test evaluation with no registered evaluators."""
        framework = EvaluationFramework()

        # Mock data
        nwb_path = Path("/fake/path/test.nwb")
        validation_results = {"nwb_inspector": {"issues": []}}
        conversion_metadata = {"experimenter": "Test User"}

        result = framework.evaluate(
            nwb_path=nwb_path,
            validation_results=validation_results,
            conversion_metadata=conversion_metadata,
        )

        assert isinstance(result, EvaluationResult)
        assert result.status == EvaluationStatus.COMPLETED
        assert result.overall_score == 0.0  # No metrics
        assert len(result.metrics) == 0

    def test_update_config(self):
        """Test updating framework configuration."""
        framework = EvaluationFramework()

        new_criteria = EvaluationCriteria(
            name="updated_criteria",
            description="Updated evaluation criteria",
        )
        new_config = EvaluationConfig(criteria=new_criteria)

        framework.update_config(new_config)

        assert framework.config.criteria.name == "updated_criteria"


@pytest.mark.unit
class TestEvaluationResult:
    """Test EvaluationResult dataclass."""

    def test_evaluation_result_creation(self):
        """Test creating EvaluationResult instance."""
        metrics = [
            QualityMetrics(
                name="test_metric",
                value=0.8,
                max_value=1.0,
                description="Test metric",
                dimension=QualityDimension.TECHNICAL,
            )
        ]

        result = EvaluationResult(
            overall_score=0.8,
            dimension_scores={QualityDimension.TECHNICAL: 0.8},
            metrics=metrics,
            recommendations=["Improve documentation"],
            strengths=["Good technical quality"],
            weaknesses=["Poor usability"],
            status=EvaluationStatus.COMPLETED,
        )

        assert result.overall_score == 0.8
        assert result.overall_percentage == 80.0
        assert result.status == EvaluationStatus.COMPLETED
        assert len(result.metrics) == 1

    def test_get_metrics_by_dimension(self):
        """Test getting metrics by dimension."""
        metrics = [
            QualityMetrics(
                name="tech_metric",
                value=0.8,
                max_value=1.0,
                description="Technical metric",
                dimension=QualityDimension.TECHNICAL,
            ),
            QualityMetrics(
                name="sci_metric",
                value=0.6,
                max_value=1.0,
                description="Scientific metric",
                dimension=QualityDimension.SCIENTIFIC,
            ),
        ]

        result = EvaluationResult(
            overall_score=0.7,
            dimension_scores={
                QualityDimension.TECHNICAL: 0.8,
                QualityDimension.SCIENTIFIC: 0.6,
            },
            metrics=metrics,
            recommendations=[],
            strengths=[],
            weaknesses=[],
            status=EvaluationStatus.COMPLETED,
        )

        tech_metrics = result.get_metrics_by_dimension(QualityDimension.TECHNICAL)
        assert len(tech_metrics) == 1
        assert tech_metrics[0].name == "tech_metric"

        sci_metrics = result.get_metrics_by_dimension(QualityDimension.SCIENTIFIC)
        assert len(sci_metrics) == 1
        assert sci_metrics[0].name == "sci_metric"

    def test_get_metric_by_name(self):
        """Test getting metric by name."""
        metrics = [
            QualityMetrics(
                name="test_metric",
                value=0.8,
                max_value=1.0,
                description="Test metric",
                dimension=QualityDimension.TECHNICAL,
            )
        ]

        result = EvaluationResult(
            overall_score=0.8,
            dimension_scores={QualityDimension.TECHNICAL: 0.8},
            metrics=metrics,
            recommendations=[],
            strengths=[],
            weaknesses=[],
            status=EvaluationStatus.COMPLETED,
        )

        metric = result.get_metric_by_name("test_metric")
        assert metric is not None
        assert metric.name == "test_metric"

        missing_metric = result.get_metric_by_name("missing_metric")
        assert missing_metric is None

    def test_evaluation_result_to_dict(self):
        """Test converting EvaluationResult to dictionary."""
        metrics = [
            QualityMetrics(
                name="test_metric",
                value=0.8,
                max_value=1.0,
                description="Test metric",
                dimension=QualityDimension.TECHNICAL,
            )
        ]

        result = EvaluationResult(
            overall_score=0.8,
            dimension_scores={QualityDimension.TECHNICAL: 0.8},
            metrics=metrics,
            recommendations=["Improve documentation"],
            strengths=["Good technical quality"],
            weaknesses=["Poor usability"],
            status=EvaluationStatus.COMPLETED,
            evaluation_id="test_eval_123",
        )

        result_dict = result.to_dict()

        assert result_dict["evaluation_id"] == "test_eval_123"
        assert result_dict["overall_score"] == 0.8
        assert result_dict["overall_percentage"] == 80.0
        assert result_dict["status"] == "completed"
        assert "technical" in result_dict["dimension_scores"]
        assert len(result_dict["metrics"]) == 1
        assert len(result_dict["recommendations"]) == 1
