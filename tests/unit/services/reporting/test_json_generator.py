"""Unit tests for JSONReportGenerator."""

import json

import pytest

from agentic_neurodata_conversion.services.reporting.json_generator import JSONReportGenerator

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_validation_result():
    """Sample validation result for testing."""
    return {
        "overall_status": "PASSED_WITH_ISSUES",
        "nwb_file_path": "/path/to/test.nwb",
        "session_id": "test-session-123",
        "issues": [
            {
                "severity": "CRITICAL",
                "check_name": "check_session_description",
                "message": "Missing session_description",
                "location": "/",
                "object_type": "NWBFile",
                "context": {"field": "session_description"},
                "suggestion": "Add session description",
                "fix": {"field": "session_description", "value": "Example session"},
            },
            {
                "severity": "WARNING",
                "check_name": "check_keywords",
                "message": "Missing keywords",
                "location": "/",
                "object_type": "NWBFile",
            },
        ],
        "issue_counts": {"CRITICAL": 1, "WARNING": 1},
        "file_info": {
            "nwb_version": "2.6.0",
            "file_size_bytes": 1024000,
            "creation_date": "2024-03-15",
            "identifier": "test-file-001",
            "file_format": "NWB",
            "session_description": "Test session",
            "session_start_time": "2024-03-15T10:00:00",
            "session_id": "session-001",
            "experimenter": ["Doe, John", "Smith, Jane"],
            "institution": "Test University",
            "lab": "Test Lab",
            "experiment_description": "Test experiment",
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
            "age": "P56D",
            "date_of_birth": "2024-01-01",
            "description": "Adult male mouse",
            "genotype": "WT",
            "strain": "C57BL/6",
        },
    }


@pytest.fixture
def sample_quality_metrics():
    """Sample quality metrics."""
    return {
        "completeness": {"score": 85, "grade": "B"},
        "integrity": {"score": 90, "status": "good"},
        "scientific_value": {"score": 80, "rating": "high"},
        "dandi_ready": {"ready": True, "blocking_issues": 0},
    }


@pytest.fixture
def sample_metadata_completeness():
    """Sample metadata completeness info."""
    return {
        "percentage": 75.5,
        "filled": 15,
        "total": 20,
        "required_filled": 8,
        "required_total": 10,
        "critical_missing": 2,
    }


@pytest.fixture
def sample_missing_critical_fields():
    """Sample missing critical fields."""
    return [
        {"field": "session_description", "importance": "required"},
        {"field": "experimenter", "importance": "required"},
    ]


@pytest.fixture
def sample_file_info_with_provenance():
    """Sample file info with provenance."""
    return {
        "experimenter": {"value": "Doe, John", "source": "AI_PARSED", "confidence": 95},
        "institution": {"value": "Test University", "source": "USER_PROVIDED", "confidence": 100},
    }


@pytest.fixture
def sample_recommendations():
    """Sample recommendations."""
    return [
        {"category": "metadata", "priority": "high", "message": "Add session description"},
        {"category": "quality", "priority": "medium", "message": "Include experiment protocol"},
    ]


@pytest.fixture
def sample_llm_guidance():
    """Sample LLM guidance."""
    return {
        "executive_summary": "This file contains neural recordings with good metadata but missing some fields.",
        "quality_assessment": {"overall": "good", "score": 85},
        "recommendations": ["Add session_description", "Include keywords"],
        "key_insights": ["Good data quality", "Minor metadata gaps"],
        "dandi_ready": False,
        "dandi_blocking_issues": ["Missing session_description"],
    }


@pytest.fixture
def sample_workflow_trace():
    """Sample workflow trace."""
    return {
        "upload": {"timestamp": "2024-03-15T09:00:00", "file_count": 1},
        "format_detection": {"method": "llm", "format": "SpikeGLX", "confidence": 0.95},
        "conversion": {"status": "success", "duration_ms": 1500},
        "validation": {"status": "passed_with_issues", "issue_count": 2},
    }


# ============================================================================
# generate_json_report Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestGenerateJSONReport:
    """Test JSON report file generation."""

    def test_generate_json_report_creates_file(self, tmp_path):
        """Test that JSON file is created."""
        output_path = tmp_path / "report.json"
        report_data = {"test": "data", "number": 123}

        result_path = JSONReportGenerator.generate_json_report(output_path, report_data)

        assert result_path == output_path
        assert output_path.exists()

    def test_generate_json_report_valid_json(self, tmp_path):
        """Test that generated file contains valid JSON."""
        output_path = tmp_path / "report.json"
        report_data = {"key1": "value1", "key2": [1, 2, 3], "key3": {"nested": "data"}}

        JSONReportGenerator.generate_json_report(output_path, report_data)

        # Read and parse JSON
        with open(output_path, encoding="utf-8") as f:
            loaded_data = json.load(f)

        assert loaded_data == report_data

    def test_generate_json_report_pretty_printed(self, tmp_path):
        """Test that JSON is pretty-printed with indentation."""
        output_path = tmp_path / "report.json"
        report_data = {"section1": {"field1": "value1", "field2": "value2"}}

        JSONReportGenerator.generate_json_report(output_path, report_data)

        content = output_path.read_text(encoding="utf-8")

        # Check for indentation (2 spaces)
        assert "  " in content
        assert "\n" in content

    def test_generate_json_report_utf8_encoding(self, tmp_path):
        """Test that JSON is saved with UTF-8 encoding (special characters)."""
        output_path = tmp_path / "report.json"
        report_data = {"experimenter": "José García", "institution": "Université de Paris"}

        JSONReportGenerator.generate_json_report(output_path, report_data)

        content = output_path.read_text(encoding="utf-8")

        assert "José García" in content
        assert "Université de Paris" in content

    def test_generate_json_report_datetime_serialization(self, tmp_path):
        """Test that datetime objects are serialized to strings."""
        from datetime import datetime

        output_path = tmp_path / "report.json"
        timestamp = datetime(2024, 3, 15, 10, 30, 45)
        report_data = {"timestamp": timestamp}

        JSONReportGenerator.generate_json_report(output_path, report_data)

        with open(output_path, encoding="utf-8") as f:
            loaded_data = json.load(f)

        # Datetime should be converted to string
        assert isinstance(loaded_data["timestamp"], str)
        assert "2024-03-15" in loaded_data["timestamp"]


# ============================================================================
# create_json_structure Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestCreateJSONStructure:
    """Test JSON structure creation."""

    def test_create_json_structure_complete(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
        sample_llm_guidance,
        sample_workflow_trace,
    ):
        """Test creating complete JSON structure with all sections."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
            llm_guidance=sample_llm_guidance,
            workflow_trace=sample_workflow_trace,
        )

        # Verify all top-level sections
        assert "report_metadata" in result
        assert "evaluation_summary" in result
        assert "quality_metrics" in result
        assert "metadata_completeness" in result
        assert "file_information" in result
        assert "validation_results" in result
        assert "missing_critical_fields" in result
        assert "recommendations" in result
        assert "llm_analysis" in result
        assert "workflow_trace" in result

    def test_report_metadata_section(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test report_metadata section structure."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
        )

        metadata = result["report_metadata"]
        assert metadata["version"] == "2.0"
        assert "generated_at" in metadata
        assert metadata["session_id"] == "test-session-123"
        assert metadata["system_version"] == "1.0.0"

    def test_evaluation_summary_section(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test evaluation_summary section."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
        )

        summary = result["evaluation_summary"]
        assert summary["status"] == "PASSED_WITH_ISSUES"
        assert summary["nwb_file_path"] == "/path/to/test.nwb"
        assert summary["file_format"] == "NWB"
        assert "timestamp" in summary

    def test_quality_metrics_section(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test quality_metrics section."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
        )

        metrics = result["quality_metrics"]
        assert metrics["completeness"] == {"score": 85, "grade": "B"}
        assert metrics["data_integrity"] == {"score": 90, "status": "good"}
        assert metrics["scientific_value"] == {"score": 80, "rating": "high"}
        assert metrics["dandi_readiness"] == {"ready": True, "blocking_issues": 0}

    def test_metadata_completeness_section(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test metadata_completeness section."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
        )

        completeness = result["metadata_completeness"]
        assert completeness["percentage"] == 75.5
        assert completeness["filled_fields"] == 15
        assert completeness["total_fields"] == 20
        assert completeness["required_filled"] == 8
        assert completeness["required_total"] == 10
        assert completeness["critical_missing"] == 2

    def test_file_information_section(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test file_information section with all subsections."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
        )

        file_info = result["file_information"]

        # Basic info
        assert file_info["basic_info"]["nwb_version"] == "2.6.0"
        assert file_info["basic_info"]["file_size_bytes"] == 1024000
        assert file_info["basic_info"]["creation_date"] == "2024-03-15"

        # Session info
        assert file_info["session_info"]["session_description"] == "Test session"
        assert file_info["session_info"]["session_start_time"] == "2024-03-15T10:00:00"

        # Experiment info
        assert file_info["experiment_info"]["experimenter"] == ["Doe, John", "Smith, Jane"]
        assert file_info["experiment_info"]["institution"] == "Test University"

        # Subject info
        assert file_info["subject_info"]["subject_id"] == "mouse001"
        assert file_info["subject_info"]["species"] == "Mus musculus"
        assert file_info["subject_info"]["sex"] == "M"

        # Provenance
        assert file_info["metadata_with_provenance"] == sample_file_info_with_provenance

    def test_validation_results_section(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test validation_results section."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
        )

        validation = result["validation_results"]
        assert validation["overall_status"] == "PASSED_WITH_ISSUES"
        assert validation["total_issues"] == 2
        assert validation["issue_counts"] == {"CRITICAL": 1, "WARNING": 1}
        assert "issues_by_severity" in validation

    def test_optional_llm_guidance_section(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
        sample_llm_guidance,
    ):
        """Test that LLM guidance section is included when provided."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
            llm_guidance=sample_llm_guidance,
        )

        assert "llm_analysis" in result
        llm = result["llm_analysis"]
        assert "neural recordings" in llm["executive_summary"]
        assert llm["quality_assessment"] == {"overall": "good", "score": 85}
        assert llm["dandi_ready"] is False
        assert len(llm["dandi_blocking_issues"]) == 1

    def test_optional_llm_guidance_omitted(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test that LLM guidance section is omitted when not provided."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
            llm_guidance=None,
        )

        assert "llm_analysis" not in result

    def test_optional_workflow_trace_section(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
        sample_workflow_trace,
    ):
        """Test that workflow trace section is included when provided."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
            workflow_trace=sample_workflow_trace,
        )

        assert "workflow_trace" in result
        trace = result["workflow_trace"]
        assert "upload" in trace
        assert "format_detection" in trace
        assert trace["conversion"]["status"] == "success"

    def test_optional_workflow_trace_omitted(
        self,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test that workflow trace section is omitted when not provided."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
            workflow_trace=None,
        )

        assert "workflow_trace" not in result

    def test_empty_quality_metrics(
        self,
        sample_validation_result,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test with empty quality metrics."""
        result = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics={},
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
        )

        metrics = result["quality_metrics"]
        assert metrics["completeness"] == {}
        assert metrics["data_integrity"] == {}


# ============================================================================
# _group_issues_by_severity Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestGroupIssuesBySeverity:
    """Test issue grouping by severity."""

    def test_empty_issues(self):
        """Test with no issues."""
        result = JSONReportGenerator._group_issues_by_severity([])

        assert result == {
            "critical": [],
            "errors": [],
            "warnings": [],
            "info": [],
            "best_practice": [],
        }

    def test_single_critical_issue(self):
        """Test with single critical issue."""
        issues = [
            {
                "severity": "CRITICAL",
                "check_name": "check_1",
                "message": "Critical error",
                "location": "/",
                "object_type": "NWBFile",
            }
        ]

        result = JSONReportGenerator._group_issues_by_severity(issues)

        assert len(result["critical"]) == 1
        assert result["critical"][0]["severity"] == "CRITICAL"
        assert result["critical"][0]["check_name"] == "check_1"
        assert len(result["errors"]) == 0

    def test_all_severity_types(self):
        """Test with all severity types."""
        issues = [
            {
                "severity": "CRITICAL",
                "check_name": "check_critical",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            },
            {
                "severity": "ERROR",
                "check_name": "check_error",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            },
            {
                "severity": "WARNING",
                "check_name": "check_warning",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            },
            {
                "severity": "INFO",
                "check_name": "check_info",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            },
            {
                "severity": "BEST_PRACTICE",
                "check_name": "check_bp",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            },
        ]

        result = JSONReportGenerator._group_issues_by_severity(issues)

        assert len(result["critical"]) == 1
        assert len(result["errors"]) == 1
        assert len(result["warnings"]) == 1
        assert len(result["info"]) == 1
        assert len(result["best_practice"]) == 1

    def test_best_practice_variants(self):
        """Test BEST_PRACTICE_VIOLATION and BEST_PRACTICE_SUGGESTION map to best_practice."""
        issues = [
            {
                "severity": "BEST_PRACTICE",
                "check_name": "bp1",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            },
            {
                "severity": "BEST_PRACTICE_VIOLATION",
                "check_name": "bp2",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            },
            {
                "severity": "BEST_PRACTICE_SUGGESTION",
                "check_name": "bp3",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            },
        ]

        result = JSONReportGenerator._group_issues_by_severity(issues)

        assert len(result["best_practice"]) == 3

    def test_unknown_severity_defaults_to_info(self):
        """Test that unknown severity types default to info group."""
        issues = [
            {
                "severity": "UNKNOWN_TYPE",
                "check_name": "check_1",
                "message": "Msg",
                "location": "/",
                "object_type": "NWBFile",
            }
        ]

        result = JSONReportGenerator._group_issues_by_severity(issues)

        assert len(result["info"]) == 1
        assert result["info"][0]["severity"] == "UNKNOWN_TYPE"

    def test_missing_severity_field(self):
        """Test issue with missing severity field."""
        issues = [{"check_name": "check_1", "message": "Msg", "location": "/", "object_type": "NWBFile"}]  # No severity

        result = JSONReportGenerator._group_issues_by_severity(issues)

        # Should default to info
        assert len(result["info"]) == 1

    def test_issue_data_structure(self):
        """Test that issue data structure includes all fields."""
        issues = [
            {
                "severity": "ERROR",
                "check_name": "test_check",
                "message": "Test message",
                "location": "/test/location",
                "object_type": "TestObject",
                "context": {"field": "test_field"},
                "suggestion": "Fix this issue",
                "fix": {"action": "apply_fix"},
            }
        ]

        result = JSONReportGenerator._group_issues_by_severity(issues)

        issue_data = result["errors"][0]
        assert issue_data["severity"] == "ERROR"
        assert issue_data["check_name"] == "test_check"
        assert issue_data["message"] == "Test message"
        assert issue_data["location"] == "/test/location"
        assert issue_data["object_type"] == "TestObject"
        assert issue_data["context"] == {"field": "test_field"}
        assert issue_data["suggestion"] == "Fix this issue"
        assert issue_data["fix"] == {"action": "apply_fix"}

    def test_issue_data_optional_fields(self):
        """Test that optional fields can be None."""
        issues = [
            {
                "severity": "WARNING",
                "check_name": "test_check",
                "message": "Test message",
                "location": "/",
                "object_type": "NWBFile",
                # context, suggestion, fix are missing
            }
        ]

        result = JSONReportGenerator._group_issues_by_severity(issues)

        issue_data = result["warnings"][0]
        assert issue_data["context"] is None
        assert issue_data["suggestion"] is None
        assert issue_data["fix"] is None

    def test_multiple_issues_same_severity(self):
        """Test multiple issues with same severity."""
        issues = [
            {
                "severity": "ERROR",
                "check_name": "check_1",
                "message": "Msg 1",
                "location": "/",
                "object_type": "NWBFile",
            },
            {
                "severity": "ERROR",
                "check_name": "check_2",
                "message": "Msg 2",
                "location": "/",
                "object_type": "NWBFile",
            },
            {
                "severity": "ERROR",
                "check_name": "check_3",
                "message": "Msg 3",
                "location": "/",
                "object_type": "NWBFile",
            },
        ]

        result = JSONReportGenerator._group_issues_by_severity(issues)

        assert len(result["errors"]) == 3
        assert result["errors"][0]["check_name"] == "check_1"
        assert result["errors"][1]["check_name"] == "check_2"
        assert result["errors"][2]["check_name"] == "check_3"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestJSONGeneratorIntegration:
    """Integration tests for complete workflow."""

    def test_full_workflow_json_generation(
        self,
        tmp_path,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
        sample_llm_guidance,
        sample_workflow_trace,
    ):
        """Test complete workflow from structure creation to file generation."""
        # Create structure
        report_data = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
            llm_guidance=sample_llm_guidance,
            workflow_trace=sample_workflow_trace,
        )

        # Generate JSON file
        output_path = tmp_path / "complete_report.json"
        JSONReportGenerator.generate_json_report(output_path, report_data)

        # Verify file exists and is valid JSON
        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            loaded_data = json.load(f)

        # Verify all sections are present
        assert "report_metadata" in loaded_data
        assert "evaluation_summary" in loaded_data
        assert "quality_metrics" in loaded_data
        assert "llm_analysis" in loaded_data
        assert "workflow_trace" in loaded_data

    def test_minimal_workflow_json_generation(
        self,
        tmp_path,
        sample_validation_result,
        sample_quality_metrics,
        sample_metadata_completeness,
        sample_missing_critical_fields,
        sample_file_info_with_provenance,
        sample_recommendations,
    ):
        """Test minimal workflow without optional sections."""
        # Create structure (no LLM guidance or workflow trace)
        report_data = JSONReportGenerator.create_json_structure(
            validation_result=sample_validation_result,
            quality_metrics=sample_quality_metrics,
            metadata_completeness=sample_metadata_completeness,
            missing_critical_fields=sample_missing_critical_fields,
            file_info_with_provenance=sample_file_info_with_provenance,
            recommendations=sample_recommendations,
        )

        # Generate JSON file
        output_path = tmp_path / "minimal_report.json"
        JSONReportGenerator.generate_json_report(output_path, report_data)

        # Verify file exists
        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            loaded_data = json.load(f)

        # Verify required sections are present
        assert "report_metadata" in loaded_data
        assert "evaluation_summary" in loaded_data

        # Verify optional sections are absent
        assert "llm_analysis" not in loaded_data
        assert "workflow_trace" not in loaded_data
