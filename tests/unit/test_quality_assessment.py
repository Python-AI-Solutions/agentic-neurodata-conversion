"""Tests for quality assessment system."""

from __future__ import annotations

from unittest.mock import patch

import pytest

# Import components to test
from agentic_neurodata_conversion.evaluation.quality_assessment import (
    IssueCategory,
    IssueSeverity,
    MissingDependencyError,
    QualityAssessment,
    QualityAssessmentEngine,
    QualityBenchmark,
    QualityIssue,
    ScientificQualityEvaluator,
    TechnicalQualityEvaluator,
    UsabilityQualityEvaluator,
    check_critical_dependencies,
)


class TestQualityIssue:
    """Test QualityIssue dataclass functionality."""

    @pytest.mark.unit
    def test_quality_issue_creation(self):
        """Test creating a quality issue."""
        issue = QualityIssue(
            id="test_issue",
            category=IssueCategory.SCHEMA_COMPLIANCE,
            severity=IssueSeverity.HIGH,
            title="Test Issue",
            description="Test description",
            location="test_location",
            recommendation="Fix the issue",
            impact_score=0.8,
        )

        assert issue.id == "test_issue"
        assert issue.category == IssueCategory.SCHEMA_COMPLIANCE
        assert issue.severity == IssueSeverity.HIGH
        assert issue.title == "Test Issue"
        assert issue.description == "Test description"
        assert issue.location == "test_location"
        assert issue.recommendation == "Fix the issue"
        assert issue.impact_score == 0.8

    @pytest.mark.unit
    def test_priority_score_calculation(self):
        """Test priority score calculation."""
        critical_issue = QualityIssue(
            id="critical",
            category=IssueCategory.SCHEMA_COMPLIANCE,
            severity=IssueSeverity.CRITICAL,
            title="Critical Issue",
            description="Critical description",
            impact_score=0.9,
        )

        low_issue = QualityIssue(
            id="low",
            category=IssueCategory.USABILITY,
            severity=IssueSeverity.LOW,
            title="Low Issue",
            description="Low description",
            impact_score=0.2,
        )

        # Critical issue should have higher priority
        assert critical_issue.priority_score > low_issue.priority_score
        assert critical_issue.priority_score == 1.0 * (1.0 + 0.9)  # 1.9
        assert low_issue.priority_score == 0.4 * (1.0 + 0.2)  # 0.48

    @pytest.mark.unit
    def test_issue_to_dict(self):
        """Test converting issue to dictionary."""
        issue = QualityIssue(
            id="test_issue",
            category=IssueCategory.DATA_INTEGRITY,
            severity=IssueSeverity.MEDIUM,
            title="Test Issue",
            description="Test description",
            impact_score=0.5,
        )

        issue_dict = issue.to_dict()

        assert issue_dict["id"] == "test_issue"
        assert issue_dict["category"] == "data_integrity"
        assert issue_dict["severity"] == "medium"
        assert issue_dict["title"] == "Test Issue"
        assert issue_dict["description"] == "Test description"
        assert issue_dict["impact_score"] == 0.5
        assert "priority_score" in issue_dict


class TestQualityBenchmark:
    """Test QualityBenchmark functionality."""

    @pytest.mark.unit
    def test_benchmark_creation(self):
        """Test creating a quality benchmark."""
        benchmark = QualityBenchmark(
            name="test_benchmark",
            description="Test benchmark",
            target_scores={"metric1": 0.8, "metric2": 0.9},
            baseline_scores={"metric1": 0.6, "metric2": 0.7},
        )

        assert benchmark.name == "test_benchmark"
        assert benchmark.description == "Test benchmark"
        assert benchmark.target_scores["metric1"] == 0.8
        assert benchmark.baseline_scores["metric1"] == 0.6

    @pytest.mark.unit
    def test_score_comparison(self):
        """Test score comparison against benchmark."""
        benchmark = QualityBenchmark(
            name="test",
            description="Test",
            target_scores={"metric1": 0.8},
            baseline_scores={"metric1": 0.6},
            percentile_scores={"metric1": {"90": 0.9, "75": 0.8, "50": 0.7}},
        )

        # Test score above target
        comparison = benchmark.compare_score("metric1", 0.85)
        assert comparison["score"] == 0.85
        assert comparison["target"] == 0.8
        assert comparison["baseline"] == 0.6
        assert comparison["meets_target"] is True
        assert comparison["above_baseline"] is True
        assert comparison["percentile_rank"] == 75

        # Test score below baseline
        comparison = benchmark.compare_score("metric1", 0.5)
        assert comparison["meets_target"] is False
        assert comparison["above_baseline"] is False
        assert comparison["percentile_rank"] is None


class TestTechnicalQualityEvaluator:
    """Test TechnicalQualityEvaluator functionality."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return TechnicalQualityEvaluator()

    @pytest.mark.unit
    def test_evaluator_creation(self, evaluator):
        """Test creating technical quality evaluator."""
        assert evaluator is not None
        assert hasattr(evaluator, "evaluate")

    @pytest.mark.unit
    def test_schema_compliance_evaluation(self, evaluator):
        """Test schema compliance evaluation."""
        # Test with no issues
        validation_results = {"nwb_inspector": {"issues": []}}
        score, issues = evaluator._evaluate_schema_compliance(validation_results)
        assert score == 1.0
        assert len(issues) == 0

        # Test with critical issues
        validation_results = {
            "nwb_inspector": {
                "issues": [
                    {
                        "severity": "critical",
                        "message": "Critical schema error",
                        "location": "/test/location",
                    }
                ]
            }
        }
        score, issues = evaluator._evaluate_schema_compliance(validation_results)
        assert score < 1.0
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.CRITICAL

    @pytest.mark.unit
    def test_performance_evaluation(self, evaluator, tmp_path):
        """Test performance evaluation."""
        # Create a test file
        test_file = tmp_path / "test.nwb"
        test_file.write_text("test content")

        score, issues = evaluator._evaluate_performance(str(test_file))
        assert score > 0.0
        assert isinstance(issues, list)

        # Test with non-existent file
        score, issues = evaluator._evaluate_performance("/nonexistent/file.nwb")
        assert score == 0.0
        assert len(issues) > 0
        assert any(issue.severity == IssueSeverity.CRITICAL for issue in issues)

    @pytest.mark.unit
    def test_missing_pynwb_raises_error(self):
        """Test that missing pynwb raises clear error during initialization."""
        with (
            patch(
                "builtins.__import__", side_effect=ImportError("pynwb not available")
            ),
            pytest.raises(MissingDependencyError, match="Cannot perform.*pynwb"),
        ):
            TechnicalQualityEvaluator()

    @pytest.mark.unit
    def test_evaluate_method(self, evaluator):
        """Test main evaluate method."""
        validation_results = {"nwb_inspector": {"issues": []}}

        with (
            patch.object(evaluator, "_evaluate_data_integrity") as mock_integrity,
            patch.object(evaluator, "_evaluate_file_structure") as mock_structure,
            patch.object(evaluator, "_evaluate_performance") as mock_performance,
        ):
            mock_integrity.return_value = (0.9, [])
            mock_structure.return_value = (0.8, [])
            mock_performance.return_value = (0.7, [])

            metrics, issues = evaluator.evaluate("/test/path.nwb", validation_results)

            assert "schema_compliance" in metrics
            assert "data_integrity" in metrics
            assert "file_structure" in metrics
            assert "performance" in metrics
            assert isinstance(issues, list)


class TestScientificQualityEvaluator:
    """Test ScientificQualityEvaluator functionality."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return ScientificQualityEvaluator()

    @pytest.mark.unit
    def test_evaluator_creation(self, evaluator):
        """Test creating scientific quality evaluator."""
        assert evaluator is not None
        assert hasattr(evaluator, "evaluate")

    @pytest.mark.unit
    def test_experimental_completeness_evaluation(self, evaluator):
        """Test experimental completeness evaluation."""
        # Test with complete metadata
        complete_metadata = {
            "experimenter": "Dr. Test",
            "lab": "Test Lab",
            "institution": "Test University",
            "session_description": "Test session",
            "identifier": "test_001",
            "session_start_time": "2024-01-01T10:00:00",
        }

        score, issues = evaluator._evaluate_experimental_completeness(complete_metadata)
        assert score == 1.0
        assert len(issues) == 0

        # Test with incomplete metadata
        incomplete_metadata = {
            "experimenter": "Dr. Test",
            "lab": "Test Lab",
            # Missing other required fields
        }

        score, issues = evaluator._evaluate_experimental_completeness(
            incomplete_metadata
        )
        assert score < 1.0
        assert len(issues) > 0
        assert all(
            issue.category == IssueCategory.METADATA_COMPLETENESS for issue in issues
        )

    @pytest.mark.unit
    def test_scientific_validity_evaluation(self, evaluator):
        """Test scientific validity evaluation."""
        metadata = {
            "subject_id": "subject_001",
            "species": "Mus musculus",
            "session_description": "This is a detailed session description with sufficient information",
        }

        score, issues = evaluator._evaluate_scientific_validity(metadata)
        assert score > 0.0
        assert isinstance(issues, list)

        # Test with missing information
        minimal_metadata = {}
        score, issues = evaluator._evaluate_scientific_validity(minimal_metadata)
        assert score < 0.8
        assert len(issues) > 0

    @pytest.mark.unit
    def test_evaluate_method(self, evaluator):
        """Test main evaluate method."""
        metadata = {
            "experimenter": "Dr. Test",
            "lab": "Test Lab",
            "subject_id": "subject_001",
        }

        metrics, issues = evaluator.evaluate("/test/path.nwb", metadata)

        assert "experimental_completeness" in metrics
        assert "scientific_validity" in metrics
        assert "reproducibility" in metrics
        assert isinstance(issues, list)


class TestUsabilityQualityEvaluator:
    """Test UsabilityQualityEvaluator functionality."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return UsabilityQualityEvaluator()

    @pytest.mark.unit
    def test_evaluator_creation(self, evaluator):
        """Test creating usability quality evaluator."""
        assert evaluator is not None
        assert hasattr(evaluator, "evaluate")

    @pytest.mark.unit
    def test_documentation_quality_evaluation(self, evaluator):
        """Test documentation quality evaluation."""
        # Test with good description
        good_metadata = {
            "session_description": "This is a comprehensive session description that provides detailed information about the experimental procedures, conditions, and expected outcomes. It includes sufficient detail for reproducibility."
        }

        score, issues = evaluator._evaluate_documentation_quality(good_metadata)
        assert score == 1.0
        assert len(issues) == 0

        # Test with poor description
        poor_metadata = {"session_description": "Short"}
        score, issues = evaluator._evaluate_documentation_quality(poor_metadata)
        assert score < 1.0
        assert len(issues) > 0

        # Test with no description
        no_metadata = {}
        score, issues = evaluator._evaluate_documentation_quality(no_metadata)
        assert score == 0.0
        assert len(issues) > 0

    @pytest.mark.unit
    def test_discoverability_evaluation(self, evaluator):
        """Test discoverability evaluation."""
        discoverable_metadata = {
            "keywords": ["neuroscience", "electrophysiology"],
            "related_publications": ["doi:10.1000/test"],
            "notes": "Additional notes",
            "experiment_description": "Detailed experiment description",
        }

        score, issues = evaluator._evaluate_discoverability(discoverable_metadata)
        assert score == 1.0
        assert len(issues) == 0

        # Test with minimal discoverability
        minimal_metadata = {}
        score, issues = evaluator._evaluate_discoverability(minimal_metadata)
        assert score == 0.0
        assert len(issues) > 0

    @pytest.mark.unit
    def test_accessibility_evaluation(self, evaluator, tmp_path):
        """Test accessibility evaluation."""
        # Create accessible file
        test_file = tmp_path / "accessible.nwb"
        test_file.write_text("test content")

        score, issues = evaluator._evaluate_accessibility(str(test_file), {})
        assert score > 0.0

        # Test with non-existent file
        score, issues = evaluator._evaluate_accessibility("/nonexistent/file.nwb", {})
        assert score == 0.0
        assert len(issues) > 0

    @pytest.mark.unit
    def test_evaluate_method(self, evaluator, tmp_path):
        """Test main evaluate method."""
        test_file = tmp_path / "test.nwb"
        test_file.write_text("test content")

        metadata = {
            "session_description": "Test session description",
            "keywords": ["test"],
        }

        metrics, issues = evaluator.evaluate(str(test_file), metadata)

        assert "documentation_quality" in metrics
        assert "discoverability" in metrics
        assert "accessibility" in metrics
        assert isinstance(issues, list)


class TestQualityAssessment:
    """Test QualityAssessment dataclass functionality."""

    @pytest.fixture
    def sample_assessment(self):
        """Create sample quality assessment."""
        issues = [
            QualityIssue(
                id="critical_issue",
                category=IssueCategory.SCHEMA_COMPLIANCE,
                severity=IssueSeverity.CRITICAL,
                title="Critical Issue",
                description="Critical description",
            ),
            QualityIssue(
                id="high_issue",
                category=IssueCategory.DATA_INTEGRITY,
                severity=IssueSeverity.HIGH,
                title="High Issue",
                description="High description",
            ),
            QualityIssue(
                id="low_issue",
                category=IssueCategory.USABILITY,
                severity=IssueSeverity.LOW,
                title="Low Issue",
                description="Low description",
            ),
        ]

        return QualityAssessment(
            overall_score=0.75,
            dimension_scores={"technical": 0.8, "scientific": 0.7, "usability": 0.75},
            metric_scores={"metric1": 0.8, "metric2": 0.7},
            issues=issues,
            recommendations=["Fix critical issues", "Improve documentation"],
            strengths=["Good data integrity"],
            weaknesses=["Poor schema compliance"],
        )

    @pytest.mark.unit
    def test_critical_issues_property(self, sample_assessment):
        """Test getting critical issues."""
        critical_issues = sample_assessment.critical_issues
        assert len(critical_issues) == 1
        assert critical_issues[0].severity == IssueSeverity.CRITICAL

    @pytest.mark.unit
    def test_high_priority_issues_property(self, sample_assessment):
        """Test getting high priority issues."""
        high_priority = sample_assessment.high_priority_issues
        assert len(high_priority) == 2  # Critical and high severity
        severities = [issue.severity for issue in high_priority]
        assert IssueSeverity.CRITICAL in severities
        assert IssueSeverity.HIGH in severities

    @pytest.mark.unit
    def test_get_issues_by_category(self, sample_assessment):
        """Test getting issues by category."""
        schema_issues = sample_assessment.get_issues_by_category(
            IssueCategory.SCHEMA_COMPLIANCE
        )
        assert len(schema_issues) == 1
        assert schema_issues[0].category == IssueCategory.SCHEMA_COMPLIANCE

    @pytest.mark.unit
    def test_get_prioritized_issues(self, sample_assessment):
        """Test getting prioritized issues."""
        prioritized = sample_assessment.get_prioritized_issues()
        assert len(prioritized) == 3

        # Should be sorted by priority score (highest first)
        for i in range(len(prioritized) - 1):
            assert prioritized[i].priority_score >= prioritized[i + 1].priority_score

        # Test with limit
        limited = sample_assessment.get_prioritized_issues(limit=2)
        assert len(limited) == 2

    @pytest.mark.unit
    def test_to_dict(self, sample_assessment):
        """Test converting assessment to dictionary."""
        assessment_dict = sample_assessment.to_dict()

        assert assessment_dict["overall_score"] == 0.75
        assert "dimension_scores" in assessment_dict
        assert "metric_scores" in assessment_dict
        assert "issues" in assessment_dict
        assert "recommendations" in assessment_dict
        assert "strengths" in assessment_dict
        assert "weaknesses" in assessment_dict
        assert "summary" in assessment_dict

        # Check summary
        summary = assessment_dict["summary"]
        assert summary["total_issues"] == 3
        assert summary["critical_issues"] == 1
        assert summary["high_priority_issues"] == 2


class TestDependencyChecking:
    """Test dependency checking functionality."""

    @pytest.mark.unit
    def test_check_critical_dependencies_success(self):
        """Test that dependency check passes when pynwb is available."""
        # Should not raise any exception since pynwb is now properly installed
        check_critical_dependencies()

    @pytest.mark.unit
    def test_check_critical_dependencies_failure(self):
        """Test that dependency check fails when pynwb is missing."""
        with patch(
            "builtins.__import__", side_effect=ImportError("pynwb not available")
        ):
            with pytest.raises(MissingDependencyError) as exc_info:
                check_critical_dependencies()

            error_msg = str(exc_info.value)
            assert "pynwb" in error_msg
            assert "pixi add pynwb" in error_msg
            assert "NWB file reading" in error_msg

    @pytest.mark.unit
    def test_missing_dependency_error_message(self):
        """Test MissingDependencyError message format."""
        error = MissingDependencyError("pynwb", "NWB analysis", "pixi add pynwb")
        error_msg = str(error)

        assert "Cannot perform NWB analysis without 'pynwb'" in error_msg
        assert "pixi add pynwb" in error_msg
        assert "pixi run" in error_msg


class TestQualityAssessmentEngine:
    """Test QualityAssessmentEngine functionality."""

    @pytest.fixture
    def engine(self):
        """Create assessment engine instance."""
        return QualityAssessmentEngine()

    @pytest.mark.unit
    def test_engine_creation(self, engine):
        """Test creating quality assessment engine."""
        assert engine is not None
        assert hasattr(engine, "assess_quality")
        assert hasattr(engine, "technical_evaluator")
        assert hasattr(engine, "scientific_evaluator")
        assert hasattr(engine, "usability_evaluator")

    @pytest.mark.unit
    def test_engine_creation_fails_without_pynwb(self):
        """Test that engine creation fails when pynwb is missing."""
        with (
            patch(
                "builtins.__import__", side_effect=ImportError("pynwb not available")
            ),
            pytest.raises(MissingDependencyError, match="Cannot perform.*pynwb"),
        ):
            QualityAssessmentEngine()

    @pytest.mark.unit
    def test_register_benchmark(self, engine):
        """Test registering a benchmark."""
        benchmark = QualityBenchmark(
            name="test_benchmark",
            description="Test benchmark",
            target_scores={"metric1": 0.8},
        )

        engine.register_benchmark(benchmark)
        assert "test_benchmark" in engine.list_benchmarks()

    @pytest.mark.unit
    def test_create_default_benchmark(self, engine):
        """Test creating default benchmark."""
        benchmark = engine.create_default_benchmark()
        assert benchmark.name == "default_nwb_benchmark"
        assert len(benchmark.target_scores) > 0
        assert len(benchmark.baseline_scores) > 0

    @pytest.mark.unit
    def test_assess_quality_success(self, engine, tmp_path):
        """Test successful quality assessment."""
        # Create test file
        test_file = tmp_path / "test.nwb"
        test_file.write_text("test content")

        validation_results = {"nwb_inspector": {"issues": []}}
        metadata = {
            "experimenter": "Dr. Test",
            "lab": "Test Lab",
            "session_description": "Test session description",
        }

        # Mock the evaluators to return predictable results
        with (
            patch.object(engine.technical_evaluator, "evaluate") as mock_tech,
            patch.object(engine.scientific_evaluator, "evaluate") as mock_sci,
            patch.object(engine.usability_evaluator, "evaluate") as mock_usability,
        ):
            mock_tech.return_value = ({"schema_compliance": 0.9}, [])
            mock_sci.return_value = ({"experimental_completeness": 0.8}, [])
            mock_usability.return_value = ({"documentation_quality": 0.7}, [])

            assessment = engine.assess_quality(
                str(test_file), validation_results, metadata
            )

            assert isinstance(assessment, QualityAssessment)
            assert assessment.overall_score > 0.0
            assert len(assessment.dimension_scores) == 3
            assert "technical" in assessment.dimension_scores
            assert "scientific" in assessment.dimension_scores
            assert "usability" in assessment.dimension_scores

    @pytest.mark.unit
    def test_assess_quality_with_benchmark(self, engine, tmp_path):
        """Test quality assessment with benchmark comparison."""
        # Register a benchmark
        benchmark = QualityBenchmark(
            name="test_benchmark",
            description="Test benchmark",
            target_scores={"technical_schema_compliance": 0.8},
        )
        engine.register_benchmark(benchmark)

        # Create test file
        test_file = tmp_path / "test.nwb"
        test_file.write_text("test content")

        validation_results = {"nwb_inspector": {"issues": []}}
        metadata = {"experimenter": "Dr. Test"}

        # Mock evaluators
        with (
            patch.object(engine.technical_evaluator, "evaluate") as mock_tech,
            patch.object(engine.scientific_evaluator, "evaluate") as mock_sci,
            patch.object(engine.usability_evaluator, "evaluate") as mock_usability,
        ):
            mock_tech.return_value = ({"schema_compliance": 0.9}, [])
            mock_sci.return_value = ({"experimental_completeness": 0.8}, [])
            mock_usability.return_value = ({"documentation_quality": 0.7}, [])

            assessment = engine.assess_quality(
                str(test_file),
                validation_results,
                metadata,
                benchmark_name="test_benchmark",
            )

            assert len(assessment.benchmark_comparisons) > 0

    @pytest.mark.unit
    def test_assess_quality_failure(self, engine):
        """Test quality assessment failure handling."""
        # Use invalid file path to trigger error
        validation_results = {}
        metadata = {}

        # Mock evaluators to raise exception
        with patch.object(
            engine.technical_evaluator, "evaluate", side_effect=Exception("Test error")
        ):
            assessment = engine.assess_quality(
                "/invalid/path.nwb", validation_results, metadata
            )

            assert assessment.overall_score == 0.0
            assert len(assessment.issues) > 0
            assert any(
                issue.severity == IssueSeverity.CRITICAL for issue in assessment.issues
            )
            assert "Assessment could not be completed" in assessment.weaknesses

    @pytest.mark.unit
    def test_calculate_dimension_scores(self, engine):
        """Test dimension score calculation."""
        metrics = {
            "technical_schema_compliance": 0.9,
            "technical_data_integrity": 0.8,
            "scientific_experimental_completeness": 0.7,
            "usability_documentation_quality": 0.6,
        }

        dimension_scores = engine._calculate_dimension_scores(metrics)

        assert "technical" in dimension_scores
        assert "scientific" in dimension_scores
        assert "usability" in dimension_scores

        # Technical should be average of 0.9 and 0.8 = 0.85
        assert abs(dimension_scores["technical"] - 0.85) < 0.001
        assert dimension_scores["scientific"] == 0.7
        assert dimension_scores["usability"] == 0.6

    @pytest.mark.unit
    def test_generate_recommendations(self, engine):
        """Test recommendation generation."""
        issues = [
            QualityIssue(
                id="critical_issue",
                category=IssueCategory.SCHEMA_COMPLIANCE,
                severity=IssueSeverity.CRITICAL,
                title="Critical Issue",
                description="Critical description",
                recommendation="Fix critical issue immediately",
            )
        ]

        dimension_scores = {"technical": 0.6, "scientific": 0.8, "usability": 0.9}

        recommendations = engine._generate_recommendations(issues, dimension_scores)

        assert len(recommendations) > 0
        assert any("CRITICAL" in rec for rec in recommendations)
        assert any("technical quality" in rec for rec in recommendations)

    @pytest.mark.unit
    def test_identify_strengths_and_weaknesses(self, engine):
        """Test strength and weakness identification."""
        metrics = {
            "technical_schema_compliance": 0.9,  # Strength
            "technical_data_integrity": 0.4,  # Weakness
            "scientific_experimental_completeness": 0.7,  # Neither
        }

        strengths = engine._identify_strengths(metrics)
        weaknesses = engine._identify_weaknesses(metrics)

        assert len(strengths) > 0
        assert len(weaknesses) > 0
        assert any("schema compliance" in strength for strength in strengths)
        assert any("data integrity" in weakness for weakness in weaknesses)

    @pytest.mark.unit
    def test_analyze_completeness(self, engine):
        """Test completeness analysis."""
        metadata = {
            "experimenter": "Dr. Test",
            "lab": "Test Lab",
            "session_description": "Test description",
            # Missing other fields
        }

        issues = [
            QualityIssue(
                id="missing_identifier",
                category=IssueCategory.METADATA_COMPLETENESS,
                severity=IssueSeverity.MEDIUM,
                title="Missing identifier",
                description="No identifier provided",
            )
        ]

        analysis = engine._analyze_completeness(metadata, issues)

        assert "completeness_percentage" in analysis
        assert "missing_fields" in analysis
        assert "present_fields" in analysis
        assert analysis["completeness_issues_count"] == 1
        assert "identifier" in analysis["missing_fields"]
