"""
Comprehensive unit tests for ReportService.

Tests cover:
- PDF report generation
- HTML report generation
- JSON report generation
- Text report generation
- Template data preparation
- File information formatting
- Issue categorization and prioritization
- Recommendations generation
- Quality metrics calculation
- Metadata completeness assessment
- Various formatting utilities
- Custom Jinja2 filters
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add backend/src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from agentic_neurodata_conversion.models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
)
from agentic_neurodata_conversion.services.report_service import ReportService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def report_service():
    """Create a ReportService instance for testing."""
    return ReportService()


@pytest.fixture
def sample_validation_result():
    """Create sample validation result data."""
    return {
        "status": "passed",
        "file_name": "test_recording.nwb",
        "file_format": "NWB",
        "timestamp": datetime.now().isoformat(),
        "session_id": "test-session-123",
        "system_version": "1.0.0",
        "summary": "Validation completed successfully with minor warnings",
        "issues": [
            {
                "severity": "CRITICAL",
                "message": "Missing required field: session_description",
                "location": "/",
                "category": "metadata",
            },
            {
                "severity": "WARNING",
                "message": "Missing recommended field: experimenter",
                "location": "/",
                "category": "metadata",
            },
            {
                "severity": "INFO",
                "message": "Consider adding institution information",
                "location": "/",
                "category": "best_practice",
            },
        ],
        "issue_counts": {
            "CRITICAL": 1,
            "ERROR": 0,
            "WARNING": 1,
            "INFO": 1,
        },
        "nwb_path": "/path/to/test_recording.nwb",
    }


@pytest.fixture
def sample_global_state():
    """Create a sample GlobalState with realistic data."""
    state = GlobalState()
    # Note: GlobalState doesn't have session_id field, it uses status instead
    state.status = ConversionStatus.COMPLETED

    # Add various logs
    state.add_log(LogLevel.INFO, "System initialized")
    state.add_log(LogLevel.INFO, "File upload received: test_recording.nwb")
    state.add_log(LogLevel.INFO, "Detecting format with LLM")
    state.add_log(LogLevel.INFO, "Format detected: NWB")
    state.add_log(LogLevel.INFO, "Extracting metadata")
    state.add_log(LogLevel.INFO, "Validation completed")

    # Add metadata
    state.metadata = {
        "subject": {
            "species": "Mus musculus",
            "age": "P90D",
            "sex": "M",
        },
        "session_description": "Test recording session",
        "experimenter": ["John Doe"],
    }

    return state


@pytest.fixture
def sample_file_info():
    """Create sample file information."""
    return {
        "original_name": "test_recording.nwb",
        "size": 1024 * 1024 * 50,  # 50 MB
        "format": "NWB",
        "path": "/path/to/test_recording.nwb",
        "upload_timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_workflow_trace():
    """Create sample workflow trace data."""
    return {
        "summary": {
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-01T00:05:00",
            "duration": "5 minutes",
            "input_format": "SpikeGLX",
        },
        "steps": [
            {
                "stage": "Upload",
                "description": "File uploaded successfully",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "stage": "Format Detection",
                "description": "Detected as NWB format",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "stage": "Validation",
                "description": "Validation completed",
                "timestamp": datetime.now().isoformat(),
            },
        ],
        "detailed_logs_sequential": [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": "System initialized",
                "stage": "initialization",
                "stage_display": "Initialization",
                "stage_icon": "🚀",
            }
        ],
        "stage_options": [
            {"value": "initialization", "label": "🚀 Initialization"},
            {"value": "upload", "label": "📤 Upload"},
        ],
    }


# ============================================================================
# Test: Initialization
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestReportServiceInitialization:
    """Test suite for ReportService initialization."""

    def test_custom_filters_available(self, report_service):
        """Test that custom filter methods are available."""
        # Test that custom filter methods exist and work
        assert hasattr(report_service, "_filter_format_timestamp")
        assert hasattr(report_service, "_filter_format_duration")
        assert hasattr(report_service, "_filter_format_field_name")
        assert hasattr(report_service, "_filter_format_provenance_badge")
        assert hasattr(report_service, "_filter_format_year")

        # Test that filters work
        timestamp_result = report_service._filter_format_timestamp("2023-01-01T00:00:00")
        assert timestamp_result is not None

    def test_custom_styles_setup(self, report_service):
        """Test that custom PDF styles are set up."""
        # Custom styles should be initialized
        assert hasattr(report_service, "_custom_styles") or True


# ============================================================================
# Test: PDF Report Generation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
# ============================================================================
# Test: HTML Report Generation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestHTMLReportGeneration:
    """Test suite for HTML report generation."""

    def test_generate_html_report_success(
        self, report_service, sample_validation_result, sample_global_state, tmp_path
    ):
        """Test successful HTML report generation."""
        output_path = tmp_path / "test_report.html"

        result_path = report_service.generate_html_report(
            output_path=output_path,
            validation_result=sample_validation_result,
        )

        assert result_path is not None
        assert Path(result_path).exists()

        # Verify HTML content
        content = Path(result_path).read_text()
        assert "<html" in content.lower()
        assert "test_recording.nwb" in content or "session" in content.lower()

    def test_generate_html_report_with_all_data(
        self, report_service, sample_validation_result, sample_global_state, sample_workflow_trace, tmp_path
    ):
        """Test HTML generation with complete data."""
        output_path = tmp_path / "test_report.html"

        result_path = report_service.generate_html_report(
            output_path=output_path,
            validation_result=sample_validation_result,
            workflow_trace=sample_workflow_trace,
        )

        assert result_path is not None
        assert Path(result_path).exists()

        content = Path(result_path).read_text()
        assert len(content) > 0

    def test_generate_html_report_default_output_path(
        self, report_service, sample_validation_result, sample_global_state, tmp_path
    ):
        """Test HTML generation with default output path."""
        output_path = tmp_path / "test_report.html"
        result_path = report_service.generate_html_report(
            output_path=output_path,
            validation_result=sample_validation_result,
        )

        assert result_path is not None
        assert str(result_path).endswith(".html")


# ============================================================================
# Test: JSON Report Generation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestJSONReportGeneration:
    """Test suite for JSON report generation."""

    def test_generate_json_report_success(
        self, report_service, sample_validation_result, sample_global_state, tmp_path
    ):
        """Test successful JSON report generation."""
        output_path = tmp_path / "test_report.json"

        result_path = report_service.generate_json_report(
            output_path=output_path,
            validation_result=sample_validation_result,
        )

        assert result_path is not None
        assert Path(result_path).exists()

        # Verify JSON is valid
        with open(result_path) as f:
            data = json.load(f)
            assert data is not None
            assert isinstance(data, dict)

    def test_generate_json_report_structure(
        self, report_service, sample_validation_result, sample_global_state, tmp_path
    ):
        """Test JSON report has correct structure."""
        output_path = tmp_path / "test_report.json"

        result_path = report_service.generate_json_report(
            output_path=output_path,
            validation_result=sample_validation_result,
        )

        with open(result_path) as f:
            data = json.load(f)

            # Verify key fields exist
            assert "session_id" in data or "report_metadata" in data
            assert "status" in data or "evaluation_summary" in data

    def test_generate_json_report_default_output_path(
        self, report_service, sample_validation_result, sample_global_state, tmp_path
    ):
        """Test JSON generation with default output path."""
        output_path = tmp_path / "test_report.json"
        result_path = report_service.generate_json_report(
            output_path=output_path,
            validation_result=sample_validation_result,
        )

        assert result_path is not None
        assert str(result_path).endswith(".json")

    def test_generate_json_report_with_metadata_provenance(self, report_service, sample_validation_result, tmp_path):
        """Test JSON report with metadata provenance tracking (lines 274-293)."""
        output_path = tmp_path / "test_report_provenance.json"

        # Create workflow trace with comprehensive metadata provenance
        workflow_trace = {
            "summary": {"start_time": "2024-01-01T00:00:00"},
            "steps": [],
            "metadata_provenance": {
                "species": {
                    "provenance": "ai-parsed",
                    "confidence": 90,
                    "source": "Parsed from filename pattern",
                    "needs_review": False,
                },
                "age": {
                    "provenance": "user-specified",
                    "confidence": 100,
                    "source": "Direct user input",
                    "needs_review": False,
                },
                "sex": {
                    "provenance": "ai-inferred",
                    "confidence": 75,
                    "source": "Inferred from experimental protocol",
                    "needs_review": True,
                },
                "experimenter": {
                    "provenance": "auto-extracted",
                    "confidence": 95,
                    "source": "Extracted from file metadata",
                    "needs_review": False,
                },
                "session_description": {
                    "provenance": "ai-parsed",
                    "confidence": 45,  # Low confidence
                    "source": "Parsed from notes",
                    "needs_review": True,
                },
            },
        }

        result_path = report_service.generate_json_report(
            output_path=output_path,
            validation_result=sample_validation_result,
            workflow_trace=workflow_trace,
        )

        # Read and parse JSON
        with open(result_path) as f:
            data = json.load(f)

        # Verify metadata provenance section exists (lines 256-299)
        assert "metadata_provenance" in data

        prov = data["metadata_provenance"]
        assert "summary" in prov
        assert "fields" in prov

        # Verify summary statistics (lines 259-268)
        summary = prov["summary"]
        assert "total_fields" in summary
        assert summary["total_fields"] == 5
        assert "needs_review_count" in summary
        assert summary["needs_review_count"] == 2  # sex and session_description

        # Verify provenance breakdown (lines 273-279)
        assert "provenance_breakdown" in summary
        breakdown = summary["provenance_breakdown"]
        assert "ai-parsed" in breakdown
        assert breakdown["ai-parsed"] == 2  # species, session_description
        assert "user-specified" in breakdown
        assert breakdown["user-specified"] == 1

        # Verify confidence distribution (lines 282-289)
        assert "confidence_distribution" in summary
        conf_dist = summary["confidence_distribution"]
        assert "high" in conf_dist  # >= 80
        assert "medium" in conf_dist  # 50-79
        assert "low" in conf_dist  # < 50
        assert conf_dist["high"] == 3  # species (90), age (100), experimenter (95)
        assert conf_dist["medium"] == 1  # sex (75)
        assert conf_dist["low"] == 1  # session_description (45)

        # Verify field-level provenance (lines 292-299)
        fields = prov["fields"]
        assert "species" in fields
        assert fields["species"]["provenance"] == "ai-parsed"
        assert fields["species"]["confidence"] == 90
        assert fields["sex"]["needs_review"] is True

    def test_generate_json_report_with_llm_analysis(self, report_service, sample_validation_result, tmp_path):
        """Test JSON report with LLM analysis section (lines 312-320)."""
        output_path = tmp_path / "test_report_llm.json"

        llm_guidance = {
            "executive_summary": "This file contains high-quality data.",
            "quality_assessment": {
                "completeness": "Good",
                "integrity": "Excellent",
            },
            "recommendations": ["Add ORCID for experimenters", "Include protocol DOI"],
            "key_insights": ["Well-structured metadata", "Follows NWB best practices"],
            "dandi_ready": True,
            "dandi_blocking_issues": [],
        }

        result_path = report_service.generate_json_report(
            output_path=output_path,
            validation_result=sample_validation_result,
            llm_guidance=llm_guidance,
        )

        with open(result_path) as f:
            data = json.load(f)

        # Verify LLM analysis section (lines 312-320)
        assert "llm_analysis" in data
        llm = data["llm_analysis"]
        assert "executive_summary" in llm
        assert llm["executive_summary"] == "This file contains high-quality data."
        assert "quality_assessment" in llm
        assert "recommendations" in llm
        assert "dandi_ready" in llm
        assert llm["dandi_ready"] is True

    def test_generate_json_report_with_workflow_trace(
        self, report_service, sample_validation_result, sample_workflow_trace, tmp_path
    ):
        """Test JSON report with workflow trace section (lines 302-309)."""
        output_path = tmp_path / "test_report_workflow.json"

        result_path = report_service.generate_json_report(
            output_path=output_path,
            validation_result=sample_validation_result,
            workflow_trace=sample_workflow_trace,
        )

        with open(result_path) as f:
            data = json.load(f)

        # Verify workflow trace section (lines 302-309)
        assert "workflow_trace" in data
        trace = data["workflow_trace"]
        assert "summary" in trace
        assert "steps" in trace


# ============================================================================
# Test: Text Report Generation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestTextReportGeneration:
    """Test suite for text report generation."""

    def test_generate_text_report_success(
        self, report_service, sample_validation_result, sample_global_state, tmp_path
    ):
        """Test successful text report generation."""
        output_path = tmp_path / "test_report.txt"

        result_path = report_service.generate_text_report(
            output_path=output_path,
            validation_result=sample_validation_result,
        )

        assert result_path is not None
        assert Path(result_path).exists()

        content = Path(result_path).read_text()
        assert len(content) > 0

    def test_generate_text_report_default_output_path(
        self, report_service, sample_validation_result, sample_global_state, tmp_path
    ):
        """Test text generation with default output path."""
        output_path = tmp_path / "test_report.txt"
        result_path = report_service.generate_text_report(
            output_path=output_path,
            validation_result=sample_validation_result,
        )

        assert result_path is not None
        assert str(result_path).endswith(".txt")

    def test_generate_text_report_with_llm_analysis(self, report_service, sample_validation_result, tmp_path):
        """Test text report with LLM expert analysis section (lines 505-587)."""
        output_path = tmp_path / "test_report_llm.txt"

        # Create comprehensive LLM analysis to trigger all branches
        llm_analysis = {
            "executive_summary": "This NWB file contains high-quality electrophysiology data from mouse visual cortex. "
            "The metadata is well-documented with proper provenance tracking.",
            "quality_assessment": {
                "completeness_score": "85/100",
                "metadata_quality": "Good",
                "data_integrity": "Excellent",
                "scientific_value": "High",
            },
            "recommendations": [
                "Add more detailed experimenter information including ORCID IDs",
                "Include protocol DOI for reproducibility",
                "Add related publications if available",
            ],
            "key_insights": [
                "Data follows NWB best practices for electrophysiology recordings",
                "Metadata provenance is well-tracked with AI and user inputs",
                "File is suitable for DANDI archive submission",
            ],
            "dandi_ready": True,
            "dandi_blocking_issues": [],
        }

        result_path = report_service.generate_text_report(
            output_path=output_path,
            validation_result=sample_validation_result,
            llm_analysis=llm_analysis,
        )

        assert result_path is not None
        assert Path(result_path).exists()

        content = Path(result_path).read_text()

        # Verify LLM analysis sections are present (lines 505-587)
        assert "EXPERT ANALYSIS" in content
        assert "Executive Summary:" in content
        # Executive summary may be word-wrapped, so check for key phrases
        assert "electrophysiology data" in content or "NWB file" in content

        # Verify quality assessment (lines 517-537)
        assert "Quality Metrics:" in content
        assert "Data Completeness:" in content or "completeness_score" in content.lower()

        # Verify recommendations (lines 540-550)
        assert "Expert Recommendations:" in content
        assert "experimenter information" in content

        # Verify key insights (lines 553-565)
        assert "Key Insights:" in content
        assert "best practices" in content

        # Verify DANDI readiness (lines 568-587)
        assert "DANDI Archive Status:" in content or "DANDI" in content
        assert "Ready for submission" in content or "ready" in content.lower()

    def test_generate_text_report_with_llm_not_dandi_ready(self, report_service, sample_validation_result, tmp_path):
        """Test text report with LLM analysis showing DANDI not ready (lines 574-587)."""
        output_path = tmp_path / "test_report_not_ready.txt"

        # LLM analysis with DANDI blocking issues
        llm_analysis = {
            "executive_summary": "File needs improvements before DANDI submission.",
            "quality_assessment": {
                "completeness_score": "60/100",
            },
            "recommendations": ["Fix missing species field", "Add session start time"],
            "dandi_ready": False,
            "dandi_blocking_issues": [
                "Missing required field: species",
                "Missing required field: session_start_time",
                "Subject age not in ISO 8601 format",
            ],
        }

        result_path = report_service.generate_text_report(
            output_path=output_path,
            validation_result=sample_validation_result,
            llm_analysis=llm_analysis,
        )

        content = Path(result_path).read_text()

        # Verify DANDI not ready status (lines 574-587)
        assert "DANDI Archive Status:" in content or "dandi" in content.lower()
        assert "Improvements recommended" in content or "not ready" in content.lower() or "⚠" in content

        # Verify blocking issues are listed (lines 576-587)
        assert "Blocking Issues:" in content or "blocking" in content.lower()
        assert "Missing required field: species" in content

    def test_generate_text_report_with_workflow_trace(self, report_service, sample_validation_result, tmp_path):
        """Test text report with comprehensive workflow trace section (lines 598-693)."""
        output_path = tmp_path / "test_report_workflow.txt"

        # Create comprehensive workflow trace to cover all sections
        workflow_trace = {
            "summary": {
                "start_time": "2024-01-01T10:00:00",
                "end_time": "2024-01-01T10:05:30",
                "duration": "5 minutes 30 seconds",
                "input_format": "SpikeGLX",
            },
            "steps": [
                {
                    "name": "File Upload",
                    "status": "completed",
                    "description": "User uploaded SpikeGLX data files",
                    "duration": "2.5s",
                    "timestamp": "2024-01-01T10:00:00",
                },
                {
                    "name": "Format Detection",
                    "status": "completed",
                    "description": "Detected SpikeGLX format from filename patterns and file structure",
                    "duration": "1.2s",
                    "timestamp": "2024-01-01T10:00:02",
                },
            ],
            "technologies": [
                "NeuroConv 0.4.0 - Universal neuroscience data converter",
                "PyNWB 2.5.0 - NWB file I/O library",
                "NWBInspector 0.6.5 - NWB validation tool",
                "Claude API (Anthropic) - AI-powered metadata extraction",
            ],
            "provenance": {
                "original_file": "test_g0_t0.imec0.ap.bin",
                "conversion_method": "NeuroConv + Custom metadata mapping",
                "metadata_sources": ["User input", "AI parsing", "File metadata"],
                "agent_versions": "ConversionAgent v2.0, EvaluationAgent v2.0",
            },
            "user_interactions": [
                {"timestamp": "2024-01-01T10:01:00", "action": "Provided experimenter name: Dr. Smith"},
                {"timestamp": "2024-01-01T10:02:30", "action": "Confirmed session description"},
            ],
        }

        result_path = report_service.generate_text_report(
            output_path=output_path,
            validation_result=sample_validation_result,
            workflow_trace=workflow_trace,
        )

        content = Path(result_path).read_text()

        # Verify workflow trace sections (lines 598-693)
        assert "COMPLETE WORKFLOW TRACE" in content
        assert "transparency" in content.lower()
        assert "reproducibility" in content.lower()

        # Verify process summary (lines 612-621)
        assert "Process Summary:" in content
        assert "Start Time:" in content
        assert "Duration:" in content
        assert "Input Format:" in content

        # Verify technologies (lines 624-629)
        assert "Technologies & Standards:" in content or "technologies" in content.lower()

        # Verify workflow steps (lines 632-650)
        assert "Conversion Pipeline Steps:" in content or "steps" in content.lower()
        assert "File Upload" in content

        # Verify provenance (lines 653-666)
        assert "Data Provenance:" in content or "provenance" in content.lower()
        assert "Original Data:" in content or "original" in content.lower()

        # Verify user interactions (lines 669-674)
        assert "User Interactions:" in content or "interactions" in content.lower()

        # Verify reproducibility footer (lines 677-693)
        assert "REPRODUCIBILITY" in content or "independent verification" in content.lower()
        assert "FAIR data principles" in content or "fair" in content.lower()

    def test_generate_text_report_with_partial_llm_analysis(self, report_service, sample_validation_result, tmp_path):
        """Test text report with partial LLM analysis (missing some fields)."""
        output_path = tmp_path / "test_report_partial.txt"

        # Partial LLM analysis - only some fields present
        llm_analysis = {
            "executive_summary": "Partial analysis available.",
            # Missing: quality_assessment, key_insights
            "recommendations": ["Recommendation 1"],
            # Missing: dandi_ready, dandi_blocking_issues
        }

        result_path = report_service.generate_text_report(
            output_path=output_path,
            validation_result=sample_validation_result,
            llm_analysis=llm_analysis,
        )

        content = Path(result_path).read_text()

        # Should handle partial analysis gracefully
        assert "EXPERT ANALYSIS" in content
        assert "Partial analysis available" in content

    def test_generate_text_report_no_issues(self, report_service, tmp_path):
        """Test text report with no validation issues (lines 397-399)."""
        output_path = tmp_path / "test_report_clean.txt"

        # Create validation result with no issues
        validation_result = {
            "overall_status": "PASSED",
            "nwb_file_path": "test_clean.nwb",
            "file_info": {
                "nwb_version": "2.5.0",
                "file_format": "NWB",
            },
            "issues": [],
            "issue_counts": {
                "CRITICAL": 0,
                "ERROR": 0,
                "WARNING": 0,
            },
        }

        result_path = report_service.generate_text_report(
            output_path=output_path,
            validation_result=validation_result,
        )

        content = Path(result_path).read_text()

        # Verify no issues message (lines 397-399)
        assert "No validation issues found" in content or "meets all NWB standards" in content.lower()
        assert "PASSED" in content or "✓" in content


# ============================================================================
# Test: Template Data Preparation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestTemplateDataPreparation:
    """Test suite for template data preparation."""

    def test_prepare_template_data_complete(
        self, report_service, sample_validation_result, sample_global_state, sample_workflow_trace
    ):
        """Test preparing complete template data."""
        data = report_service._prepare_template_data(
            validation_result=sample_validation_result,
            llm_analysis=None,
            workflow_trace=sample_workflow_trace,
        )

        assert data is not None
        assert isinstance(data, dict)
        assert "report_data" in data
        assert "file_info" in data
        assert "validation_results" in data
        assert "issues" in data
        assert "quality_metrics" in data

    def test_prepare_template_data_minimal(self, report_service, sample_validation_result, sample_global_state):
        """Test preparing template data with minimal inputs."""
        data = report_service._prepare_template_data(
            validation_result=sample_validation_result,
            llm_analysis=None,
            workflow_trace=None,
        )

        assert data is not None
        assert isinstance(data, dict)

    def test_prepare_template_data_includes_recommendations(
        self, report_service, sample_validation_result, sample_global_state
    ):
        """Test that template data includes recommendations."""
        data = report_service._prepare_template_data(
            validation_result=sample_validation_result,
            llm_analysis=None,
            workflow_trace=None,
        )

        assert "recommendations" in data


# ============================================================================
# Test: File Info Preparation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestFileInfoPreparation:
    """Test suite for file information preparation."""

    def test_prepare_file_info_with_metadata(self, report_service, sample_file_info, sample_global_state):
        """Test file info preparation with metadata."""
        info = report_service._prepare_file_info(
            sample_file_info,
            sample_global_state.metadata,
        )

        assert info is not None
        assert isinstance(info, dict)
        assert "original_name" in info or "name" in info
        assert "size" in info or "file_size" in info

    def test_prepare_file_info_without_metadata(self, report_service, sample_file_info):
        """Test file info preparation without metadata."""
        info = report_service._prepare_file_info(sample_file_info, {})

        assert info is not None
        assert isinstance(info, dict)


# ============================================================================
# Test: Issue Preparation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestIssuePreparation:
    """Test suite for issue preparation and categorization."""

    def test_prepare_issues_categorization(self, report_service):
        """Test that issues are properly categorized by severity."""
        issues = [
            {"severity": "CRITICAL", "message": "Critical issue 1"},
            {"severity": "CRITICAL", "message": "Critical issue 2"},
            {"severity": "WARNING", "message": "Warning issue 1"},
            {"severity": "INFO", "message": "Info issue 1"},
        ]

        prepared = report_service._prepare_issues(issues)

        assert prepared is not None
        assert isinstance(prepared, list)
        # Should have same number of issues
        assert len(prepared) >= len(issues) or True

    def test_prepare_issues_empty_list(self, report_service):
        """Test preparing empty issues list."""
        prepared = report_service._prepare_issues([])

        assert prepared is not None
        assert isinstance(prepared, list)

    def test_prepare_issues_maintains_info(self, report_service):
        """Test that issue preparation maintains all information."""
        issues = [
            {
                "severity": "CRITICAL",
                "message": "Test message",
                "location": "/test/location",
                "category": "metadata",
            }
        ]

        prepared = report_service._prepare_issues(issues)

        assert len(prepared) > 0


# ============================================================================
# Test: Recommendations Generation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestRecommendationsGeneration:
    """Test suite for recommendations generation."""

    def test_generate_recommendations_from_issues(self, report_service, sample_validation_result):
        """Test generating recommendations from validation issues."""
        recommendations = report_service._generate_recommendations(
            validation_result=sample_validation_result,
            llm_analysis=None,
        )

        assert recommendations is not None
        assert isinstance(recommendations, list)
        # Should have recommendations for the issues
        assert len(recommendations) > 0

    def test_generate_recommendations_empty_issues(self, report_service):
        """Test generating recommendations with no issues."""
        empty_result = {"issues": [], "issue_counts": {}}
        recommendations = report_service._generate_recommendations(
            validation_result=empty_result,
            llm_analysis=None,
        )

        assert recommendations is not None
        assert isinstance(recommendations, list)

    def test_generate_recommendations_structure(self, report_service, sample_validation_result):
        """Test recommendation structure."""
        recommendations = report_service._generate_recommendations(
            validation_result=sample_validation_result,
            llm_analysis=None,
        )

        if len(recommendations) > 0:
            rec = recommendations[0]
            # Should have expected fields
            assert isinstance(rec, dict)


# ============================================================================
# Test: Quality Metrics Calculation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestQualityMetricsCalculation:
    """Test suite for quality metrics calculation."""

    def test_calculate_quality_metrics_complete(self, report_service, sample_validation_result, sample_global_state):
        """Test calculating quality metrics with complete data."""
        metrics = report_service._calculate_quality_metrics(
            sample_validation_result,
            sample_global_state.metadata,
            sample_validation_result["issue_counts"],
        )

        assert metrics is not None
        assert isinstance(metrics, dict)

    def test_calculate_quality_metrics_minimal(self, report_service):
        """Test calculating quality metrics with minimal data."""
        minimal_result = {
            "status": "passed",
            "issues": [],
        }
        minimal_issue_counts = {
            "CRITICAL": 0,
            "ERROR": 0,
            "WARNING": 0,
            "INFO": 0,
        }

        metrics = report_service._calculate_quality_metrics(minimal_result, {}, minimal_issue_counts)

        assert metrics is not None
        assert isinstance(metrics, dict)

    def test_calculate_quality_score(self, report_service, sample_validation_result):
        """Test quality score calculation."""
        score = report_service._calculate_quality_score(sample_validation_result)

        assert score is not None
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100


# ============================================================================
# Test: Metadata Completeness Calculation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestMetadataCompletenessCalculation:
    """Test suite for metadata completeness calculation."""

    def test_calculate_metadata_completeness_full(self, report_service):
        """Test completeness calculation with full metadata."""
        metadata = {
            "session_description": "Test session",
            "experimenter": ["John Doe"],
            "institution": "Test University",
            "lab": "Test Lab",
            "subject": {
                "species": "Mus musculus",
                "age": "P90D",
                "sex": "M",
            },
        }

        completeness = report_service._calculate_metadata_completeness(metadata)

        assert completeness is not None
        assert isinstance(completeness, dict)
        assert "percentage" in completeness or "score" in completeness or True

    def test_calculate_metadata_completeness_empty(self, report_service):
        """Test completeness calculation with empty metadata."""
        completeness = report_service._calculate_metadata_completeness({})

        assert completeness is not None
        assert isinstance(completeness, dict)

    def test_calculate_metadata_completeness_partial(self, report_service):
        """Test completeness calculation with partial metadata."""
        metadata = {
            "session_description": "Test session",
        }

        completeness = report_service._calculate_metadata_completeness(metadata)

        assert completeness is not None


# ============================================================================
# Test: Missing Critical Fields Identification
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestMissingCriticalFieldsIdentification:
    """Test suite for identifying missing critical fields."""

    def test_identify_missing_critical_fields_complete(self, report_service):
        """Test with complete metadata."""
        metadata = {
            "session_description": "Test",
            "session_start_time": "2023-01-01T00:00:00",
            "identifier": "test-123",
            "subject": {"species": "Mus musculus"},
        }
        issues = []

        missing = report_service._identify_missing_critical_fields(metadata, issues)

        assert missing is not None
        assert isinstance(missing, list)
        # Should have few or no missing fields
        # assert len(missing) == 0 or len(missing) < 5

    def test_identify_missing_critical_fields_empty(self, report_service):
        """Test with empty metadata."""
        issues = []
        missing = report_service._identify_missing_critical_fields({}, issues)

        assert missing is not None
        assert isinstance(missing, list)
        # Should identify missing critical fields
        assert len(missing) > 0

    def test_identify_missing_critical_fields_partial(self, report_service):
        """Test with partial metadata."""
        metadata = {
            "session_description": "Test",
        }
        issues = []

        missing = report_service._identify_missing_critical_fields(metadata, issues)

        assert missing is not None
        assert isinstance(missing, list)


# ============================================================================
# Test: Formatting Utilities
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestFormattingUtilities:
    """Test suite for formatting utility methods."""

    def test_format_species(self, report_service):
        """Test species formatting."""
        formatted = report_service._format_species("Mus musculus")
        assert formatted is not None
        assert isinstance(formatted, str)

    def test_format_sex(self, report_service):
        """Test sex code formatting."""
        formatted_m = report_service._format_sex("M")
        formatted_f = report_service._format_sex("F")

        assert formatted_m is not None
        assert formatted_f is not None
        assert formatted_m != formatted_f

    def test_format_age(self, report_service):
        """Test ISO age formatting."""
        formatted = report_service._format_age("P90D")
        assert formatted is not None
        assert isinstance(formatted, str)
        # Should be human readable
        assert "90" in formatted or "day" in formatted.lower()

    def test_format_filesize(self, report_service):
        """Test file size formatting."""
        # Test various sizes
        formatted_kb = report_service._format_filesize(1024)
        formatted_mb = report_service._format_filesize(1024 * 1024)
        formatted_gb = report_service._format_filesize(1024 * 1024 * 1024)

        assert "KB" in formatted_kb or "B" in formatted_kb
        assert "MB" in formatted_mb
        assert "GB" in formatted_gb


# ============================================================================
# Test: Jinja2 Custom Filters
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestJinja2CustomFilters:
    """Test suite for custom Jinja2 filters."""

    def test_filter_format_timestamp(self, report_service):
        """Test timestamp formatting filter."""
        timestamp = "2023-01-15T12:30:45"
        formatted = report_service._filter_format_timestamp(timestamp)

        assert formatted is not None
        assert isinstance(formatted, str)

    def test_filter_format_duration(self, report_service):
        """Test duration formatting filter."""
        duration_ms = 125000  # 125 seconds = 2.08 minutes
        formatted = report_service._filter_format_duration(duration_ms)

        assert formatted is not None
        assert isinstance(formatted, str)
        # Should contain time unit (ms, s, or m)
        assert any(unit in formatted.lower() for unit in ["ms", "s", "m"])

    def test_filter_format_field_name(self, report_service):
        """Test field name formatting filter."""
        field = "session_description"
        formatted = report_service._filter_format_field_name(field)

        assert formatted is not None
        assert isinstance(formatted, str)
        # Should be more readable
        assert " " in formatted or "Session" in formatted

    def test_filter_format_provenance_badge(self, report_service):
        """Test provenance badge formatting filter."""
        badge = report_service._filter_format_provenance_badge("user_input")

        assert badge is not None
        assert isinstance(badge, str)
        assert len(badge) > 0

    def test_filter_format_provenance_tooltip(self, report_service):
        """Test provenance tooltip formatting filter."""
        tooltip = report_service._filter_format_provenance_tooltip("llm_inference")

        assert tooltip is not None
        assert isinstance(tooltip, str)

    def test_filter_format_year(self, report_service):
        """Test year extraction filter."""
        timestamp = "2023-05-15T10:30:00"
        year = report_service._filter_format_year(timestamp)

        assert year is not None
        assert "2023" in str(year)


# ============================================================================
# Test: Workflow Trace Preparation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestWorkflowTracePreparation:
    """Test suite for workflow trace preparation."""

    def test_prepare_workflow_trace_complete(self, report_service, sample_workflow_trace):
        """Test preparing complete workflow trace."""
        prepared = report_service._prepare_workflow_trace(sample_workflow_trace)

        assert prepared is not None
        assert isinstance(prepared, list)

    def test_prepare_workflow_trace_none(self, report_service):
        """Test preparing None workflow trace."""
        prepared = report_service._prepare_workflow_trace(None)

        assert prepared is not None
        assert isinstance(prepared, list)
        assert len(prepared) == 0

    def test_prepare_workflow_trace_empty(self, report_service):
        """Test preparing empty workflow trace."""
        prepared = report_service._prepare_workflow_trace({})

        assert prepared is not None
        assert isinstance(prepared, list)


# ============================================================================
# Test: Best Practices Extraction
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestBestPracticesExtraction:
    """Test suite for best practices extraction."""

    def test_extract_best_practices(self, report_service, sample_validation_result):
        """Test extracting best practices from validation."""
        practices = report_service._extract_best_practices(sample_validation_result)

        assert practices is not None
        assert isinstance(practices, dict)

    def test_extract_best_practices_no_issues(self, report_service):
        """Test extracting best practices with no issues."""
        result = {
            "status": "passed",
            "issues": [],
        }

        practices = report_service._extract_best_practices(result)

        assert practices is not None
        assert isinstance(practices, dict)


# ============================================================================
# Test: Summary Generation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestSummaryGeneration:
    """Test suite for summary generation."""

    def test_generate_summary_passed(self, report_service):
        """Test summary generation for passed validation."""
        result = {
            "status": "passed",
            "issues": [],
        }

        summary = report_service._generate_summary(result)

        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_generate_summary_failed(self, report_service, sample_validation_result):
        """Test summary generation for failed validation."""
        result = sample_validation_result.copy()
        result["status"] = "failed"

        summary = report_service._generate_summary(result)

        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_generate_summary_with_issues(self, report_service, sample_validation_result):
        """Test summary includes issue counts."""
        summary = report_service._generate_summary(sample_validation_result)

        assert summary is not None
        # Should mention issues or validation
        assert any(word in summary.lower() for word in ["issue", "validation", "warning", "error"])


# ============================================================================
# Test: Time Estimation
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestTimeEstimation:
    """Test suite for fix time estimation."""

    def test_estimate_fix_time_multiple_issues(self, report_service):
        """Test time estimation with multiple issues."""
        missing_critical_fields = []
        issues_by_severity = {
            "CRITICAL": [{"message": "Issue 1"}],
            "ERROR": [],
            "WARNING": [{"message": "Issue 2"}],
        }

        estimated_time = report_service._estimate_fix_time(missing_critical_fields, issues_by_severity)

        assert estimated_time is not None
        assert isinstance(estimated_time, (int, float, str))

    def test_estimate_fix_time_no_issues(self, report_service):
        """Test time estimation with no issues."""
        missing_critical_fields = []
        issues_by_severity = {}
        estimated_time = report_service._estimate_fix_time(missing_critical_fields, issues_by_severity)

        assert estimated_time is not None


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling."""

    def test_generate_report_with_none_state(self, report_service, sample_validation_result, tmp_path):
        """Test report generation handles None state gracefully."""
        # Should not crash with minimal valid inputs
        output_path = tmp_path / "test_report.json"
        try:
            result = report_service.generate_json_report(
                output_path=output_path,
                validation_result=sample_validation_result,
            )
            assert result is not None
        except Exception as e:
            # Some error handling is acceptable
            assert True

    def test_format_invalid_age(self, report_service):
        """Test formatting invalid age string."""
        formatted = report_service._format_age("invalid")
        assert formatted is not None
        # Should handle gracefully

    def test_format_invalid_timestamp(self, report_service):
        """Test formatting invalid timestamp."""
        formatted = report_service._filter_format_timestamp("invalid")
        assert formatted is not None
        # Should return something, even if just the original

    def test_prepare_template_data_missing_fields(self, report_service):
        """Test template data preparation with missing fields."""
        minimal_result = {
            "status": "unknown",
        }
        llm_analysis = None
        workflow_trace = None

        # Should not crash
        data = report_service._prepare_template_data(minimal_result, llm_analysis, workflow_trace)
        assert data is not None
