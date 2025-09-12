"""Integration tests for quality assessment system."""

from __future__ import annotations

from unittest.mock import patch

import pytest

# Import components to test
from agentic_neurodata_conversion.evaluation.framework import EvaluationFramework
from agentic_neurodata_conversion.evaluation.quality_assessment import (
    MissingDependencyError,
    QualityBenchmark,
)


class TestQualityAssessmentIntegration:
    """Test integration between evaluation framework and quality assessment."""

    @pytest.fixture
    def evaluation_framework(self):
        """Create evaluation framework instance."""
        return EvaluationFramework()

    @pytest.mark.integration
    def test_framework_has_quality_assessment_engine(self, evaluation_framework):
        """Test that framework includes quality assessment engine."""
        assert hasattr(evaluation_framework, "quality_assessment_engine")
        assert hasattr(evaluation_framework, "assess_conversion_quality")
        assert hasattr(evaluation_framework, "register_quality_benchmark")
        assert hasattr(evaluation_framework, "list_quality_benchmarks")

    @pytest.mark.integration
    def test_default_benchmark_registration(self, evaluation_framework):
        """Test that default benchmark is registered on initialization."""
        benchmarks = evaluation_framework.list_quality_benchmarks()
        assert "default_nwb_benchmark" in benchmarks

    @pytest.mark.integration
    def test_custom_benchmark_registration(self, evaluation_framework):
        """Test registering custom benchmarks."""
        custom_benchmark = QualityBenchmark(
            name="custom_test_benchmark",
            description="Custom benchmark for testing",
            target_scores={"technical_schema_compliance": 0.95},
        )

        evaluation_framework.register_quality_benchmark(custom_benchmark)
        benchmarks = evaluation_framework.list_quality_benchmarks()
        assert "custom_test_benchmark" in benchmarks

    @pytest.mark.integration
    def test_quality_assessment_execution(self, evaluation_framework, tmp_path):
        """Test executing quality assessment through framework."""
        # Create test file
        test_file = tmp_path / "test_integration.nwb"
        test_file.write_text("test content for integration")

        validation_results = {
            "nwb_inspector": {
                "issues": [
                    {
                        "severity": "warning",
                        "message": "Test warning message",
                        "location": "/test/location",
                    }
                ]
            }
        }

        conversion_metadata = {
            "experimenter": "Dr. Integration Test",
            "lab": "Integration Lab",
            "institution": "Test University",
            "session_description": "Integration test session with comprehensive metadata",
            "identifier": "integration_test_001",
            "session_start_time": "2024-01-01T10:00:00",
            "subject_id": "subject_integration_001",
            "species": "Mus musculus",
        }

        # Execute quality assessment
        assessment = evaluation_framework.assess_conversion_quality(
            str(test_file), validation_results, conversion_metadata
        )

        # Verify assessment structure
        assert hasattr(assessment, "overall_score")
        assert hasattr(assessment, "dimension_scores")
        assert hasattr(assessment, "metric_scores")
        assert hasattr(assessment, "issues")
        assert hasattr(assessment, "recommendations")
        assert hasattr(assessment, "strengths")
        assert hasattr(assessment, "weaknesses")

        # Verify dimension scores are present
        assert "technical" in assessment.dimension_scores
        assert "scientific" in assessment.dimension_scores
        assert "usability" in assessment.dimension_scores

        # Verify some metrics are present
        assert len(assessment.metric_scores) > 0

        # Should have at least one issue from the validation results
        assert len(assessment.issues) > 0

    @pytest.mark.integration
    def test_quality_assessment_with_benchmark(self, evaluation_framework, tmp_path):
        """Test quality assessment with benchmark comparison."""
        # Register custom benchmark
        benchmark = QualityBenchmark(
            name="integration_benchmark",
            description="Benchmark for integration testing",
            target_scores={
                "technical_schema_compliance": 0.9,
                "scientific_experimental_completeness": 0.8,
                "usability_documentation_quality": 0.7,
            },
            baseline_scores={
                "technical_schema_compliance": 0.7,
                "scientific_experimental_completeness": 0.6,
                "usability_documentation_quality": 0.5,
            },
        )
        evaluation_framework.register_quality_benchmark(benchmark)

        # Create test file
        test_file = tmp_path / "benchmark_test.nwb"
        test_file.write_text("benchmark test content")

        validation_results = {"nwb_inspector": {"issues": []}}
        conversion_metadata = {
            "experimenter": "Dr. Benchmark Test",
            "session_description": "Comprehensive benchmark test session description",
        }

        # Execute with benchmark
        assessment = evaluation_framework.assess_conversion_quality(
            str(test_file),
            validation_results,
            conversion_metadata,
            benchmark_name="integration_benchmark",
        )

        # Verify benchmark comparisons are included
        assert len(assessment.benchmark_comparisons) > 0

        # Check that some metrics have benchmark comparisons
        for _metric_name, comparison in assessment.benchmark_comparisons.items():
            assert "score" in comparison
            assert "target" in comparison
            assert "baseline" in comparison
            assert "meets_target" in comparison
            assert "above_baseline" in comparison

    @pytest.mark.integration
    def test_framework_fails_without_pynwb(self):
        """Test that framework initialization fails when pynwb is missing."""
        with (
            patch(
                "builtins.__import__", side_effect=ImportError("pynwb not available")
            ),
            pytest.raises(MissingDependencyError, match="Cannot perform.*pynwb"),
        ):
            EvaluationFramework()

    @pytest.mark.integration
    def test_quality_assessment_error_handling(self, evaluation_framework):
        """Test quality assessment error handling for file system issues."""
        # Use non-existent file to trigger file system errors (not dependency errors)
        validation_results = {}
        conversion_metadata = {}

        assessment = evaluation_framework.assess_conversion_quality(
            "/nonexistent/file.nwb", validation_results, conversion_metadata
        )

        # Should return assessment with error information
        assert assessment.overall_score < 0.5  # Should be low due to errors
        assert len(assessment.issues) > 0

        # Should have critical issues
        critical_issues = assessment.critical_issues
        assert len(critical_issues) > 0

        # Should have error in weaknesses
        assert len(assessment.weaknesses) > 0

    @pytest.mark.integration
    def test_comprehensive_quality_metrics(self, evaluation_framework, tmp_path):
        """Test that all expected quality metrics are generated."""
        # Create test file
        test_file = tmp_path / "comprehensive_test.nwb"
        test_file.write_text("comprehensive test content")

        validation_results = {"nwb_inspector": {"issues": []}}
        conversion_metadata = {
            "experimenter": "Dr. Comprehensive Test",
            "lab": "Comprehensive Lab",
            "institution": "Comprehensive University",
            "session_description": "Very detailed comprehensive test session description with lots of information",
            "identifier": "comprehensive_001",
            "session_start_time": "2024-01-01T10:00:00",
            "subject_id": "subject_comprehensive_001",
            "species": "Mus musculus",
            "keywords": ["comprehensive", "test", "neuroscience"],
            "related_publications": ["doi:10.1000/comprehensive"],
            "notes": "Comprehensive test notes",
        }

        assessment = evaluation_framework.assess_conversion_quality(
            str(test_file), validation_results, conversion_metadata
        )

        # Verify expected metric categories are present
        expected_technical_metrics = [
            "technical_schema_compliance",
            "technical_data_integrity",
            "technical_file_structure",
            "technical_performance",
        ]

        expected_scientific_metrics = [
            "scientific_experimental_completeness",
            "scientific_scientific_validity",
            "scientific_reproducibility",
        ]

        expected_usability_metrics = [
            "usability_documentation_quality",
            "usability_discoverability",
            "usability_accessibility",
        ]

        # Check that metrics from each category are present
        for metric in expected_technical_metrics:
            assert metric in assessment.metric_scores

        for metric in expected_scientific_metrics:
            assert metric in assessment.metric_scores

        for metric in expected_usability_metrics:
            assert metric in assessment.metric_scores

        # Verify dimension scores are calculated
        assert 0.0 <= assessment.dimension_scores["technical"] <= 1.0
        assert 0.0 <= assessment.dimension_scores["scientific"] <= 1.0
        assert 0.0 <= assessment.dimension_scores["usability"] <= 1.0

        # Verify overall score is reasonable
        assert 0.0 <= assessment.overall_score <= 1.0

    @pytest.mark.integration
    def test_issue_categorization_and_prioritization(
        self, evaluation_framework, tmp_path
    ):
        """Test that issues are properly categorized and prioritized."""
        # Create test file
        test_file = tmp_path / "issue_test.nwb"
        test_file.write_text("issue test content")

        # Create validation results with various issue types
        validation_results = {
            "nwb_inspector": {
                "issues": [
                    {
                        "severity": "critical",
                        "message": "Critical schema violation",
                        "location": "/critical/location",
                    },
                    {
                        "severity": "warning",
                        "message": "Minor schema warning",
                        "location": "/warning/location",
                    },
                ]
            }
        }

        # Minimal metadata to trigger completeness issues
        conversion_metadata = {
            "experimenter": "Dr. Issue Test",
            # Missing many required fields
        }

        assessment = evaluation_framework.assess_conversion_quality(
            str(test_file), validation_results, conversion_metadata
        )

        # Should have multiple issues
        assert len(assessment.issues) > 0

        # Should have issues from different categories
        categories = {issue.category for issue in assessment.issues}
        assert len(categories) > 1

        # Should have different severity levels
        severities = {issue.severity for issue in assessment.issues}
        assert len(severities) > 1

        # Test prioritization
        prioritized_issues = assessment.get_prioritized_issues()
        assert len(prioritized_issues) == len(assessment.issues)

        # Should be sorted by priority (highest first)
        for i in range(len(prioritized_issues) - 1):
            assert (
                prioritized_issues[i].priority_score
                >= prioritized_issues[i + 1].priority_score
            )

        # Critical issues should be identified
        critical_issues = assessment.critical_issues
        assert len(critical_issues) > 0

    @pytest.mark.integration
    def test_completeness_analysis(self, evaluation_framework, tmp_path):
        """Test metadata completeness analysis."""
        # Create test file
        test_file = tmp_path / "completeness_test.nwb"
        test_file.write_text("completeness test content")

        validation_results = {"nwb_inspector": {"issues": []}}

        # Test with incomplete metadata
        incomplete_metadata = {
            "experimenter": "Dr. Incomplete",
            "lab": "Incomplete Lab",
            # Missing many fields
        }

        assessment = evaluation_framework.assess_conversion_quality(
            str(test_file), validation_results, incomplete_metadata
        )

        # Should have completeness analysis
        assert "completeness_analysis" in assessment.to_dict()
        completeness = assessment.completeness_analysis

        assert "completeness_percentage" in completeness
        assert "missing_fields" in completeness
        assert "present_fields" in completeness
        assert "completeness_issues_count" in completeness

        # Should identify missing fields
        assert len(completeness["missing_fields"]) > 0
        assert completeness["completeness_percentage"] < 100.0

        # Test with complete metadata
        complete_metadata = {
            "experimenter": "Dr. Complete",
            "lab": "Complete Lab",
            "institution": "Complete University",
            "session_description": "Complete session description",
            "identifier": "complete_001",
            "session_start_time": "2024-01-01T10:00:00",
            "subject_id": "subject_complete_001",
            "species": "Mus musculus",
            "keywords": ["complete", "test"],
            "related_publications": ["doi:10.1000/complete"],
            "notes": "Complete notes",
            "experiment_description": "Complete experiment description",
        }

        complete_assessment = evaluation_framework.assess_conversion_quality(
            str(test_file), validation_results, complete_metadata
        )

        complete_completeness = complete_assessment.completeness_analysis

        # Should have higher completeness
        assert (
            complete_completeness["completeness_percentage"]
            > completeness["completeness_percentage"]
        )
        assert len(complete_completeness["missing_fields"]) < len(
            completeness["missing_fields"]
        )

    @pytest.mark.integration
    def test_recommendations_generation(self, evaluation_framework, tmp_path):
        """Test that appropriate recommendations are generated."""
        # Create test file
        test_file = tmp_path / "recommendations_test.nwb"
        test_file.write_text("recommendations test content")

        # Create conditions that should trigger recommendations
        validation_results = {
            "nwb_inspector": {
                "issues": [
                    {
                        "severity": "critical",
                        "message": "Critical schema error",
                        "location": "/error/location",
                    }
                ]
            }
        }

        poor_metadata = {
            "experimenter": "Dr. Poor",
            "session_description": "Bad",  # Very brief description
            # Missing most fields
        }

        assessment = evaluation_framework.assess_conversion_quality(
            str(test_file), validation_results, poor_metadata
        )

        # Should generate recommendations
        assert len(assessment.recommendations) > 0

        # Should have critical recommendations
        critical_recommendations = [
            rec for rec in assessment.recommendations if "CRITICAL" in rec
        ]
        assert len(critical_recommendations) > 0

        # Should have dimension-specific recommendations
        dimension_recommendations = [
            rec
            for rec in assessment.recommendations
            if any(
                dim in rec.lower() for dim in ["technical", "scientific", "usability"]
            )
        ]
        assert len(dimension_recommendations) > 0
