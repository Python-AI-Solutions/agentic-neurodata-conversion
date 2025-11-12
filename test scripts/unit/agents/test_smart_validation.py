"""
Unit tests for SmartValidationAnalyzer.

Tests intelligent validation result analysis with LLM-powered insights.
"""

from unittest.mock import AsyncMock

import pytest
from agents.smart_validation import SmartValidationAnalyzer
from models import LogLevel

# Note: The following fixtures are provided by conftest files:
# - mock_llm_quality_assessor: from root conftest.py (for quality/validation assessment)
# - global_state: from root conftest.py (fresh GlobalState instance)


@pytest.mark.unit
class TestSmartValidationAnalyzerInitialization:
    """Test SmartValidationAnalyzer initialization."""

    def test_init_with_llm_service(self, mock_llm_quality_assessor):
        """Test initialization with LLM service."""
        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        assert analyzer.llm_service is not None
        assert analyzer.llm_service == mock_llm_quality_assessor

    def test_init_without_llm_service(self):
        """Test initialization without LLM service."""
        analyzer = SmartValidationAnalyzer(llm_service=None)

        assert analyzer.llm_service is None


@pytest.mark.unit
class TestAnalyzeValidationResultsWithoutLLM:
    """Test analyze_validation_results without LLM (fallback mode)."""

    @pytest.mark.asyncio
    async def test_analyze_no_llm_service_fallback(self, global_state):
        """Test that analysis falls back to basic mode when no LLM."""
        analyzer = SmartValidationAnalyzer(llm_service=None)

        validation_result = {
            "issues": [
                {"severity": "CRITICAL", "message": "Missing session_description"},
                {"severity": "ERROR", "message": "Invalid data format"},
                {"severity": "WARNING", "message": "Missing experimenter"},
            ]
        }

        file_context = {"format": "SpikeGLX", "size_mb": 10.5}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Should return basic analysis
        assert "grouped_issues" in result
        assert "priority_order" in result
        assert "severity_assessment" in result
        assert result["severity_assessment"] == "critical"  # Has critical issues

    @pytest.mark.asyncio
    async def test_analyze_no_issues(self, global_state):
        """Test analysis when no validation issues exist."""
        analyzer = SmartValidationAnalyzer(llm_service=None)

        validation_result = {"issues": []}
        file_context = {"format": "NWB", "size_mb": 5.0}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Should indicate success
        assert result["severity_assessment"] == "low"
        assert result["grouped_issues"] == {"critical": [], "errors": [], "warnings": [], "info": []}

    @pytest.mark.asyncio
    async def test_fallback_groups_by_severity(self, global_state):
        """Test that fallback mode groups issues by severity."""
        analyzer = SmartValidationAnalyzer(llm_service=None)

        validation_result = {
            "issues": [
                {"severity": "CRITICAL", "message": "Critical issue 1"},
                {"severity": "CRITICAL", "message": "Critical issue 2"},
                {"severity": "ERROR", "message": "Error issue 1"},
                {"severity": "WARNING", "message": "Warning issue 1"},
                {"severity": "INFO", "message": "Info issue 1"},
            ]
        }

        file_context = {"format": "NWB", "size_mb": 1.0}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        grouped = result["grouped_issues"]
        assert len(grouped["critical"]) == 2
        assert len(grouped["errors"]) == 1
        assert len(grouped["warnings"]) == 1
        assert len(grouped["info"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "issues,expected_severity",
        [
            ([{"severity": "CRITICAL", "message": "Critical"}], "critical"),
            ([{"severity": "ERROR", "message": "Error"}], "high"),
            ([{"severity": "WARNING", "message": "Warning"}], "medium"),
            ([{"severity": "INFO", "message": "Info"}], "low"),
        ],
    )
    async def test_fallback_severity_assessment(self, global_state, issues, expected_severity):
        """Test severity assessment logic in fallback mode."""
        analyzer = SmartValidationAnalyzer(llm_service=None)

        validation_result = {"issues": issues}
        file_context = {"format": "NWB", "size_mb": 1.0}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        assert result["severity_assessment"] == expected_severity


@pytest.mark.unit
class TestAnalyzeValidationResultsWithLLM:
    """Test analyze_validation_results with LLM service."""

    @pytest.mark.asyncio
    async def test_analyze_with_llm_success(self, mock_llm_quality_assessor, global_state):
        """Test successful LLM-powered validation analysis."""
        # Configure LLM mock to return structured analysis
        mock_llm_quality_assessor.generate_structured_output = AsyncMock(
            return_value={
                "grouped_issues": {
                    "metadata": [{"message": "Missing experimenter"}],
                    "dandi_requirements": [{"message": "Institution not specified"}],
                },
                "priority_order": [
                    {"issue": "Missing experimenter", "priority": "P0", "reason": "Required for DANDI"},
                    {"issue": "Institution not specified", "priority": "P1", "reason": "Best practice"},
                ],
                "quick_fixes": [{"issue": "Empty institution", "fix": "Remove field", "auto_correctable": True}],
                "user_actions_needed": [
                    {
                        "issue": "Missing experimenter",
                        "required_info": "Experimenter name(s)",
                        "example": "['John Doe', 'Jane Smith']",
                    }
                ],
                "severity_assessment": "high",
                "suggested_workflow": "First fix metadata fields (experimenter, institution), then revalidate",
                "estimated_fix_time": "2-5 minutes",
            }
        )

        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        validation_result = {
            "issues": [
                {"severity": "CRITICAL", "message": "Missing experimenter"},
                {"severity": "WARNING", "message": "Institution not specified"},
            ]
        }

        file_context = {"format": "SpikeGLX", "size_mb": 15.2}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Verify LLM was called
        mock_llm_quality_assessor.generate_structured_output.assert_called_once()

        # Verify result structure
        assert "grouped_issues" in result
        assert "priority_order" in result
        assert "quick_fixes" in result
        assert "user_actions_needed" in result
        assert "severity_assessment" in result
        assert "suggested_workflow" in result

        # Verify content
        assert result["severity_assessment"] == "high"
        assert len(result["priority_order"]) == 2
        assert result["priority_order"][0]["priority"] == "P0"

    @pytest.mark.asyncio
    async def test_analyze_with_llm_no_issues(self, mock_llm_quality_assessor, global_state):
        """Test LLM analysis when validation passes with no issues."""
        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        validation_result = {"issues": []}
        file_context = {"format": "NWB", "size_mb": 2.0}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Should skip LLM and return success immediately
        assert result["severity_assessment"] == "success"
        assert result["suggested_workflow"] == "No issues found - file is valid!"
        assert result["grouped_issues"] == {}
        assert result["priority_order"] == []

        # LLM should NOT be called for empty issues
        mock_llm_quality_assessor.generate_structured_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_with_llm_includes_file_context(self, mock_llm_quality_assessor, global_state):
        """Test that LLM analysis includes file context in prompt."""
        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        validation_result = {"issues": [{"severity": "ERROR", "message": "Test issue"}]}

        file_context = {"format": "SpikeGLX", "size_mb": 100.5}

        global_state.correction_attempt = 2

        await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Verify LLM was called with context
        call_args = mock_llm_quality_assessor.generate_structured_output.call_args
        prompt = call_args[1]["prompt"]

        assert "SpikeGLX" in prompt
        assert "100.5" in prompt
        assert "Conversion attempt: 2" in prompt

    @pytest.mark.asyncio
    async def test_analyze_with_llm_limits_issues_in_prompt(self, mock_llm_quality_assessor, global_state):
        """Test that analysis limits issues sent to LLM to avoid token overflow."""
        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        # Create 50 issues (should limit to 20 in prompt)
        validation_result = {"issues": [{"severity": "WARNING", "message": f"Issue {i}"} for i in range(50)]}

        file_context = {"format": "NWB", "size_mb": 5.0}

        await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Check prompt includes summary
        call_args = mock_llm_quality_assessor.generate_structured_output.call_args
        prompt = call_args[1]["prompt"]

        assert "Total issues: 50" in prompt

    @pytest.mark.asyncio
    async def test_analyze_with_llm_provides_system_prompt(self, mock_llm_quality_assessor, global_state):
        """Test that LLM analysis includes expert system prompt."""
        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        validation_result = {"issues": [{"severity": "ERROR", "message": "Test issue"}]}

        file_context = {"format": "NWB", "size_mb": 1.0}

        await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Check system prompt was provided
        call_args = mock_llm_quality_assessor.generate_structured_output.call_args
        system_prompt = call_args[1]["system_prompt"]

        assert "NWB data validator" in system_prompt
        assert "DANDI" in system_prompt
        assert "Prioritize" in system_prompt


@pytest.mark.unit
class TestAnalyzeValidationResultsErrorHandling:
    """Test error handling in validation analysis."""

    @pytest.mark.asyncio
    async def test_analyze_llm_failure_fallback(self, mock_llm_quality_assessor, global_state):
        """Test that LLM failure triggers fallback to basic analysis."""
        # Configure LLM to raise exception
        mock_llm_quality_assessor.generate_structured_output = AsyncMock(side_effect=Exception("LLM API error"))

        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        validation_result = {
            "issues": [
                {"severity": "ERROR", "message": "Test error"},
            ]
        }

        file_context = {"format": "NWB", "size_mb": 1.0}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Should fall back to basic analysis
        assert "grouped_issues" in result
        assert "severity_assessment" in result
        assert result["severity_assessment"] == "high"  # Has errors

        # Check warning was logged
        logs = global_state.logs
        warning_logs = [log for log in logs if log.level == LogLevel.WARNING]
        assert any("fallback" in log.message.lower() for log in warning_logs)

    @pytest.mark.asyncio
    async def test_analyze_handles_malformed_validation_result(self, global_state):
        """Test handling of malformed validation result."""
        analyzer = SmartValidationAnalyzer(llm_service=None)

        # Missing 'issues' key
        validation_result = {}

        file_context = {"format": "NWB", "size_mb": 1.0}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Should handle gracefully
        assert "grouped_issues" in result
        assert result["grouped_issues"] == {"critical": [], "errors": [], "warnings": [], "info": []}


@pytest.mark.unit
class TestAnalyzeValidationResultsLogging:
    """Test logging in validation analysis."""

    @pytest.mark.asyncio
    async def test_analyze_logs_smart_analysis_result(self, mock_llm_quality_assessor, global_state):
        """Test that successful smart analysis is logged."""
        mock_llm_quality_assessor.generate_structured_output = AsyncMock(
            return_value={
                "grouped_issues": {},
                "priority_order": [{"issue": "Test", "priority": "P0", "reason": "Required"}],
                "quick_fixes": [{"issue": "Fix1", "fix": "Solution", "auto_correctable": True}],
                "user_actions_needed": [{"issue": "Action1", "required_info": "Info", "example": "Example"}],
                "severity_assessment": "medium",
                "suggested_workflow": "Fix issues step by step",
            }
        )

        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        validation_result = {"issues": [{"severity": "WARNING", "message": "Test"}]}
        file_context = {"format": "NWB", "size_mb": 1.0}

        await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Check log was added
        logs = global_state.logs
        info_logs = [log for log in logs if log.level == LogLevel.INFO]
        assert any("Smart validation analysis complete" in log.message for log in info_logs)

        # Check log context
        analysis_log = next(log for log in info_logs if "Smart validation analysis complete" in log.message)
        assert analysis_log.context is not None
        assert "priority_issues" in analysis_log.context
        assert "quick_fixes" in analysis_log.context
        assert "user_actions" in analysis_log.context


@pytest.mark.unit
class TestSmartValidationAnalyzerIntegration:
    """Integration tests for complete validation analysis workflow."""

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow_with_llm(self, mock_llm_quality_assessor, global_state):
        """Test complete validation analysis workflow with LLM."""
        # Setup comprehensive mock response
        mock_llm_quality_assessor.generate_structured_output = AsyncMock(
            return_value={
                "grouped_issues": {
                    "metadata": [
                        {"message": "Missing experimenter"},
                        {"message": "Missing institution"},
                    ],
                    "data_structure": [{"message": "Invalid electrode group"}],
                },
                "priority_order": [
                    {"issue": "Missing experimenter", "priority": "P0", "reason": "DANDI requirement"},
                    {"issue": "Missing institution", "priority": "P1", "reason": "Best practice"},
                    {"issue": "Invalid electrode group", "priority": "P2", "reason": "Optional enhancement"},
                ],
                "quick_fixes": [{"issue": "Missing institution", "fix": "Add placeholder", "auto_correctable": True}],
                "user_actions_needed": [
                    {
                        "issue": "Missing experimenter",
                        "required_info": "Experimenter full name",
                        "example": "John Doe",
                    }
                ],
                "severity_assessment": "high",
                "suggested_workflow": "1. Fix experimenter (user input)\n2. Auto-fix institution\n3. Validate electrode group",
                "estimated_fix_time": "5-10 minutes",
            }
        )

        analyzer = SmartValidationAnalyzer(llm_service=mock_llm_quality_assessor)

        validation_result = {
            "issues": [
                {"severity": "CRITICAL", "message": "Missing experimenter"},
                {"severity": "WARNING", "message": "Missing institution"},
                {"severity": "INFO", "message": "Invalid electrode group"},
            ]
        }

        file_context = {"format": "SpikeGLX", "size_mb": 25.5}
        global_state.correction_attempt = 0

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Verify comprehensive result
        assert result["severity_assessment"] == "high"
        assert len(result["grouped_issues"]) == 2
        assert len(result["priority_order"]) == 3
        assert len(result["quick_fixes"]) == 1
        assert len(result["user_actions_needed"]) == 1
        assert "suggested_workflow" in result
        assert "estimated_fix_time" in result

        # Verify priorities are ordered
        priorities = [item["priority"] for item in result["priority_order"]]
        assert priorities == ["P0", "P1", "P2"]

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow_fallback(self, global_state):
        """Test complete validation analysis workflow in fallback mode."""
        analyzer = SmartValidationAnalyzer(llm_service=None)

        validation_result = {
            "issues": [
                {"severity": "ERROR", "message": "Missing required field"},
                {"severity": "WARNING", "message": "Recommended field missing"},
            ]
        }

        file_context = {"format": "NWB", "size_mb": 5.0}

        result = await analyzer.analyze_validation_results(
            validation_result=validation_result,
            file_context=file_context,
            state=global_state,
        )

        # Verify fallback provides basic but complete result
        assert "grouped_issues" in result
        assert "priority_order" in result
        assert "severity_assessment" in result
        assert "suggested_workflow" in result

        assert result["severity_assessment"] == "high"  # Has errors
        assert len(result["grouped_issues"]["errors"]) == 1
        assert len(result["grouped_issues"]["warnings"]) == 1
