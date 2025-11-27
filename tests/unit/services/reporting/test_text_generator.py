"""Unit tests for TextReportGenerator."""

import pytest

from agentic_neurodata_conversion.services.reporting.text_generator import TextReportGenerator

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def validation_result_no_issues():
    """Validation result with zero issues (PASSED status)."""
    return {
        "overall_status": "PASSED",
        "issues": [],
        "issue_counts": {},
        "nwb_file_path": "/path/to/test.nwb",
        "file_info": {"nwb_version": "2.6.0"},
    }


@pytest.fixture
def validation_result_critical_issues():
    """Validation result with critical and error issues (FAILED status)."""
    return {
        "overall_status": "FAILED",
        "issues": [
            {
                "severity": "CRITICAL",
                "check_name": "check_session_description",
                "object_type": "NWBFile",
                "location": "/",
                "message": "Missing required field: session_description",
            },
            {
                "severity": "ERROR",
                "check_name": "check_timestamps",
                "object_type": "TimeSeries",
                "location": "/acquisition/timeseries",
                "message": "Invalid timestamp format",
            },
        ],
        "issue_counts": {"CRITICAL": 1, "ERROR": 1, "WARNING": 0},
        "nwb_file_path": "/path/to/test.nwb",
        "file_info": {"nwb_version": "2.6.0"},
    }


@pytest.fixture
def validation_result_all_severities():
    """Validation result with all 5 severity types."""
    return {
        "overall_status": "PASSED_WITH_ISSUES",
        "issues": [
            {
                "severity": "CRITICAL",
                "check_name": "critical_check",
                "object_type": "NWBFile",
                "location": "/",
                "message": "Critical issue message",
            },
            {
                "severity": "ERROR",
                "check_name": "error_check",
                "object_type": "NWBFile",
                "location": "/",
                "message": "Error issue message",
            },
            {
                "severity": "WARNING",
                "check_name": "warning_check",
                "object_type": "NWBFile",
                "location": "/",
                "message": "Warning issue message",
            },
            {
                "severity": "BEST_PRACTICE_VIOLATION",
                "check_name": "bp_violation_check",
                "object_type": "NWBFile",
                "location": "/",
                "message": "Best practice violation message",
            },
            {
                "severity": "BEST_PRACTICE_SUGGESTION",
                "check_name": "bp_suggestion_check",
                "object_type": "NWBFile",
                "location": "/",
                "message": "Best practice suggestion message",
            },
        ],
        "issue_counts": {
            "CRITICAL": 1,
            "ERROR": 1,
            "WARNING": 1,
            "BEST_PRACTICE_VIOLATION": 1,
            "BEST_PRACTICE_SUGGESTION": 1,
        },
        "nwb_file_path": "/path/to/test.nwb",
        "file_info": {"nwb_version": "2.6.0"},
    }


@pytest.fixture
def validation_result_passed_with_issues():
    """Validation result with PASSED_WITH_ISSUES status (warnings only)."""
    return {
        "overall_status": "PASSED_WITH_ISSUES",
        "issues": [
            {
                "severity": "WARNING",
                "check_name": "check_keywords",
                "object_type": "NWBFile",
                "location": "/",
                "message": "Missing optional keywords field",
            }
        ],
        "issue_counts": {"WARNING": 1},
        "nwb_file_path": "/path/to/test.nwb",
        "file_info": {"nwb_version": "2.6.0"},
    }


@pytest.fixture
def validation_result_single_issue():
    """Validation result with exactly one issue (for singular/plural testing)."""
    return {
        "overall_status": "PASSED_WITH_ISSUES",
        "issues": [
            {
                "severity": "WARNING",
                "check_name": "check_keywords",
                "object_type": "NWBFile",
                "location": "/",
                "message": "Missing optional keywords field",
            }
        ],
        "issue_counts": {"WARNING": 1},
        "nwb_file_path": "/path/to/test.nwb",
        "file_info": {"nwb_version": "2.6.0"},
    }


@pytest.fixture
def validation_result_minimal_file_info():
    """Validation result with minimal file_info (empty dict)."""
    return {
        "overall_status": "PASSED",
        "issues": [],
        "issue_counts": {},
        "nwb_file_path": "/path/to/test.nwb",
        "file_info": {},
    }


@pytest.fixture
def llm_analysis_complete():
    """Complete LLM analysis with all fields populated."""
    return {
        "executive_summary": (
            "This NWB file contains high-quality neural recordings with comprehensive metadata. "
            "Minor improvements recommended for DANDI submission."
        ),
        "quality_assessment": {
            "completeness_score": "85/100",
            "metadata_quality": "Good",
            "data_integrity": "Excellent",
            "scientific_value": "High",
        },
        "recommendations": [
            "Add institution metadata for better provenance tracking",
            "Include experimenter names for reproducibility",
            "Consider adding session description for context",
        ],
        "dandi_ready": True,
    }


@pytest.fixture
def llm_analysis_partial():
    """Partial LLM analysis (only executive summary)."""
    return {"executive_summary": "Brief summary of validation results."}


@pytest.fixture
def llm_analysis_minimal():
    """Minimal LLM analysis (only DANDI readiness)."""
    return {"dandi_ready": False}


# ============================================================================
# Happy Path Tests (30% coverage)
# ============================================================================


@pytest.mark.unit
@pytest.mark.service
class TestTextReportGenerator:
    """Test suite for TextReportGenerator."""

    def test_generate_text_report_no_issues(self, tmp_path, validation_result_no_issues):
        """Test report generation with zero issues (PASSED status).

        Covers:
        - Lines 17-44: generate_text_report method
        - Lines 46-78: _build_report_lines method
        - Lines 80-106: _build_header method
        - Lines 142-144: No issues message
        """
        output_path = tmp_path / "report_no_issues.txt"

        result_path = TextReportGenerator.generate_text_report(output_path, validation_result_no_issues)

        # Verify file was created
        assert result_path == output_path
        assert output_path.exists()

        # Read and verify content
        content = output_path.read_text(encoding="utf-8")

        # Check header
        assert "NWBInspector Validation Report" in content
        assert "=" * 80 in content
        assert "Timestamp:" in content
        assert "Platform:" in content
        assert "NWBInspector version: 0.6.5" in content
        assert "NWB version:          2.6.0" in content
        assert "/path/to/test.nwb" in content

        # Check status
        assert "✓ Status: PASSED - No critical issues found" in content

        # Check no issues message
        assert "✓ No validation issues found. File meets all NWB standards." in content

    def test_generate_text_report_critical_issues(self, tmp_path, validation_result_critical_issues):
        """Test report generation with critical/error issues (FAILED status).

        Covers:
        - Lines 173-263: _build_detailed_issues method
        - Lines 230-231: Impact warning for CRITICAL/ERROR
        - Lines 251-258: DANDI readiness logic
        """
        output_path = tmp_path / "report_critical.txt"

        result_path = TextReportGenerator.generate_text_report(output_path, validation_result_critical_issues)

        assert result_path == output_path
        assert output_path.exists()

        content = output_path.read_text(encoding="utf-8")

        # Check status
        assert "✗ Status: FAILED - Critical issues found" in content

        # Check detailed issues
        assert "check_session_description" in content
        assert "check_timestamps" in content
        assert "Missing required field: session_description" in content
        assert "Invalid timestamp format" in content

        # Check impact warnings
        assert "⚠ This issue may prevent DANDI archive submission" in content

        # Check DANDI readiness (should be negative with 2 critical issues)
        assert "✗ DANDI Readiness:" in content
        assert "2 critical issues must be fixed before DANDI submission" in content

    def test_generate_text_report_with_llm_analysis(self, tmp_path, validation_result_no_issues, llm_analysis_complete):
        """Test report generation with complete LLM analysis.

        Covers:
        - Lines 265-332: _build_llm_analysis method
        - All LLM analysis sections
        """
        output_path = tmp_path / "report_with_llm.txt"

        result_path = TextReportGenerator.generate_text_report(
            output_path, validation_result_no_issues, llm_analysis=llm_analysis_complete
        )

        assert result_path == output_path
        content = output_path.read_text(encoding="utf-8")

        # Check LLM analysis section header
        assert "EXPERT ANALYSIS (AI-Powered)" in content

        # Check executive summary
        assert "Executive Summary:" in content
        assert "high-quality neural recordings" in content

        # Check quality metrics
        assert "Quality Metrics:" in content
        assert "Data Completeness:    85/100" in content
        assert "Metadata Quality:     Good" in content
        assert "Data Integrity:       Excellent" in content
        assert "Scientific Value:     High" in content

        # Check recommendations
        assert "Recommendations:" in content
        assert "1. Add institution metadata" in content
        assert "2. Include experimenter names" in content
        assert "3. Consider adding session description" in content

        # Check DANDI readiness
        assert "DANDI Readiness Assessment:" in content
        assert "✓ This file is ready for DANDI archive submission" in content

    # ========================================================================
    # Boundary Condition Tests (20% coverage)
    # ========================================================================

    def test_build_summary_passed_with_issues(self, tmp_path, validation_result_passed_with_issues):
        """Test summary with PASSED_WITH_ISSUES status.

        Covers:
        - Lines 128-133: Status badge logic for PASSED_WITH_ISSUES
        """
        output_path = tmp_path / "report_passed_with_issues.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result_passed_with_issues)

        content = output_path.read_text(encoding="utf-8")

        # Check status message
        assert "⚠ Status: PASSED_WITH_ISSUES - File passed with warnings" in content

    def test_build_summary_single_vs_plural(self, tmp_path, validation_result_single_issue):
        """Test singular vs plural formatting for single issue.

        Covers:
        - Lines 147-149: Singular/plural logic
        """
        output_path = tmp_path / "report_single.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result_single_issue)

        content = output_path.read_text(encoding="utf-8")

        # Should use singular "issue" not "issues"
        assert "Found 1 validation issue over 1 file:" in content

    def test_build_detailed_issues_all_severities(self, tmp_path, validation_result_all_severities):
        """Test detailed issues with all 5 severity types in correct order.

        Covers:
        - Lines 200-234: Severity iteration and ordering
        """
        output_path = tmp_path / "report_all_severities.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result_all_severities)

        content = output_path.read_text(encoding="utf-8")

        # Check all severity sections appear
        assert "[1] Critical" in content
        assert "[2] Error" in content
        assert "[3] Warning" in content
        assert "[4] Best Practice Violation" in content
        assert "[5] Best Practice Suggestion" in content

        # Check issue counts
        assert "1 Critical errors" in content
        assert "1 Errors" in content
        assert "1 Warnings" in content
        assert "1 Best practice violations" in content
        assert "1 Best practice suggestions" in content

    # ========================================================================
    # Edge Case Tests (15% coverage)
    # ========================================================================

    def test_build_header_minimal_file_info(self, tmp_path, validation_result_minimal_file_info):
        """Test header with empty file_info dict.

        Covers:
        - Lines 100-103: file_info conditional
        """
        output_path = tmp_path / "report_minimal_info.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result_minimal_file_info)

        content = output_path.read_text(encoding="utf-8")

        # Should not include NWB version or file path when file_info is empty
        # (or should show "Unknown")
        assert "NWBInspector Validation Report" in content

    def test_build_summary_zero_severity_counts(self, tmp_path):
        """Test summary when some severity counts are zero.

        Covers:
        - Lines 162-165: Skip zero severity counts
        """
        validation_result = {
            "overall_status": "PASSED_WITH_ISSUES",
            "issues": [
                {
                    "severity": "WARNING",
                    "check_name": "check_keywords",
                    "object_type": "NWBFile",
                    "location": "/",
                    "message": "Missing keywords",
                }
            ],
            "issue_counts": {
                "CRITICAL": 0,
                "ERROR": 0,
                "WARNING": 1,
                "BEST_PRACTICE_VIOLATION": 0,
                "BEST_PRACTICE_SUGGESTION": 0,
            },
            "nwb_file_path": "/path/to/test.nwb",
            "file_info": {"nwb_version": "2.6.0"},
        }

        output_path = tmp_path / "report_zero_counts.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result)

        content = output_path.read_text(encoding="utf-8")

        # Should only show WARNING, not CRITICAL/ERROR with 0 count
        assert "1 Warnings" in content
        assert "0 Critical" not in content
        assert "0 Errors" not in content

    def test_build_llm_analysis_partial_data(self, tmp_path, validation_result_no_issues):
        """Test LLM analysis with partial data (only some fields).

        Covers:
        - Lines 285-291: Executive summary conditional
        - Lines 294-308: Quality metrics conditionals
        - Lines 311-318: Recommendations conditional
        """
        # Test with only executive summary
        llm_partial = {"executive_summary": "Brief summary only."}
        output_path = tmp_path / "report_llm_partial.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result_no_issues, llm_analysis=llm_partial)

        content = output_path.read_text(encoding="utf-8")

        assert "Executive Summary:" in content
        assert "Brief summary only." in content
        # Should not have quality metrics or recommendations sections
        assert "Quality Metrics:" not in content
        assert "Recommendations:" not in content

        # Test with only recommendations
        llm_rec_only = {"recommendations": ["Add metadata", "Improve quality"], "dandi_ready": True}
        output_path2 = tmp_path / "report_llm_rec.txt"

        TextReportGenerator.generate_text_report(output_path2, validation_result_no_issues, llm_analysis=llm_rec_only)

        content2 = output_path2.read_text(encoding="utf-8")

        assert "Recommendations:" in content2
        assert "1. Add metadata" in content2
        assert "2. Improve quality" in content2
        assert "Executive Summary:" not in content2

    def test_build_detailed_issues_empty_severity_list(self, tmp_path):
        """Test detailed issues when severity key exists but list is empty.

        Covers:
        - Lines 207-208: Skip empty severity lists
        """
        validation_result = {
            "overall_status": "PASSED_WITH_ISSUES",
            "issues": [
                {
                    "severity": "WARNING",
                    "check_name": "check_keywords",
                    "object_type": "NWBFile",
                    "location": "/",
                    "message": "Missing keywords",
                }
            ],
            "issue_counts": {"WARNING": 1},
            "nwb_file_path": "/path/to/test.nwb",
            "file_info": {"nwb_version": "2.6.0"},
        }

        output_path = tmp_path / "report_empty_severity.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result)

        content = output_path.read_text(encoding="utf-8")

        # Should only show WARNING section, not CRITICAL/ERROR (they don't exist)
        assert "[3] Warning" in content
        assert "[1] Critical" not in content
        assert "[2] Error" not in content

    # ========================================================================
    # Integration Tests (15% coverage)
    # ========================================================================

    def test_complete_workflow_all_sections(self, tmp_path, validation_result_all_severities, llm_analysis_complete):
        """Test complete workflow with all sections populated.

        Covers:
        - All lines: Complete integration test
        """
        output_path = tmp_path / "report_complete.txt"

        result_path = TextReportGenerator.generate_text_report(
            output_path, validation_result_all_severities, llm_analysis=llm_analysis_complete
        )

        assert result_path == output_path
        assert output_path.exists()

        content = output_path.read_text(encoding="utf-8")

        # Verify all major sections are present
        assert "NWBInspector Validation Report" in content
        assert "⚠ Status: PASSED_WITH_ISSUES" in content
        assert "Found 5 validation issues" in content
        assert "[1] Critical" in content
        assert "[2] Error" in content
        assert "[3] Warning" in content
        assert "[4] Best Practice Violation" in content
        assert "[5] Best Practice Suggestion" in content
        assert "EXPERT ANALYSIS (AI-Powered)" in content
        assert "Executive Summary:" in content
        assert "Quality Metrics:" in content
        assert "Recommendations:" in content
        assert "DANDI Readiness Assessment:" in content

    def test_file_writing_utf8_encoding(self, tmp_path, validation_result_no_issues):
        """Test file is written with UTF-8 encoding (special characters).

        Covers:
        - Lines 41-42: File writing with UTF-8
        """
        output_path = tmp_path / "report_utf8.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result_no_issues)

        # Read with explicit UTF-8 encoding
        content = output_path.read_text(encoding="utf-8")

        # Verify special characters are present (✓, ✗, ⚠)
        assert "✓" in content

    def test_line_formatting_consistency(self, tmp_path, validation_result_critical_issues):
        """Test line formatting and separator consistency.

        Covers:
        - Lines 91-94: Header separators
        - Lines 137-138: Section separators
        """
        output_path = tmp_path / "report_formatting.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result_critical_issues)

        content = output_path.read_text(encoding="utf-8")

        # Check 80-character separators
        assert "=" * 80 in content
        assert "-" * 80 in content

        # Verify consistent formatting
        lines = content.split("\n")
        # First line should be 80 equals signs
        assert lines[0] == "=" * 80

    def test_dandi_readiness_with_single_critical_issue(self, tmp_path):
        """Test DANDI readiness message with exactly 1 critical issue (singular).

        Covers:
        - Lines 256-257: Singular vs plural for critical issue count
        """
        validation_result = {
            "overall_status": "FAILED",
            "issues": [
                {
                    "severity": "CRITICAL",
                    "check_name": "check_session_description",
                    "object_type": "NWBFile",
                    "location": "/",
                    "message": "Missing session_description",
                }
            ],
            "issue_counts": {"CRITICAL": 1},
            "nwb_file_path": "/path/to/test.nwb",
            "file_info": {"nwb_version": "2.6.0"},
        }

        output_path = tmp_path / "report_single_critical.txt"

        TextReportGenerator.generate_text_report(output_path, validation_result)

        content = output_path.read_text(encoding="utf-8")

        # Should use singular "issue" not "issues"
        assert "1 critical issue must be fixed" in content

    def test_llm_analysis_dandi_not_ready(self, tmp_path, validation_result_no_issues, llm_analysis_minimal):
        """Test LLM analysis when DANDI not ready (dandi_ready=False).

        Covers:
        - Lines 321-327: DANDI readiness logic in LLM analysis
        """
        output_path = tmp_path / "report_llm_not_ready.txt"

        TextReportGenerator.generate_text_report(
            output_path, validation_result_no_issues, llm_analysis=llm_analysis_minimal
        )

        content = output_path.read_text(encoding="utf-8")

        assert "DANDI Readiness Assessment:" in content
        assert "⚠ Additional improvements recommended before DANDI submission" in content
