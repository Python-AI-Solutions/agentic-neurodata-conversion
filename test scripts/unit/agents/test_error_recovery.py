"""
Unit tests for IntelligentErrorRecovery.

Tests LLM-powered error analysis and recovery suggestions.
"""

from unittest.mock import AsyncMock

import pytest
from agents.error_recovery import IntelligentErrorRecovery
from services.llm_service import MockLLMService

# Note: The following fixtures are provided by conftest files:
# - global_state: from root conftest.py (Fresh GlobalState for each test)
# - mock_llm_service: from root conftest.py (Mock LLM service)


@pytest.mark.unit
@pytest.mark.service
class TestIntelligentErrorRecoveryInitialization:
    """Tests for IntelligentErrorRecovery initialization."""

    def test_init_with_llm_service(self):
        """Test initialization with LLM service."""
        llm_service = MockLLMService()
        recovery = IntelligentErrorRecovery(llm_service=llm_service)

        assert recovery.llm_service is llm_service
        assert isinstance(recovery.error_history, list)
        assert len(recovery.error_history) == 0

    def test_init_without_llm_service(self):
        """Test initialization without LLM service (fallback mode)."""
        recovery = IntelligentErrorRecovery()

        assert recovery.llm_service is None
        assert isinstance(recovery.error_history, list)


@pytest.mark.unit
@pytest.mark.service
class TestAnalyzeError:
    """Tests for analyze_error method."""

    @pytest.mark.asyncio
    async def test_analyze_error_with_llm(self, global_state):
        """Test error analysis with LLM service."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "user_message": "The file could not be found at the specified path",
                "likely_cause": "The file path is incorrect or the file was moved",
                "recovery_actions": [
                    {
                        "action": "Verify the file path is correct",
                        "description": "Check that the file exists at the specified location",
                        "type": "user_action",
                    },
                    {
                        "action": "Try uploading the file again",
                        "description": "Re-upload the file to ensure it's available",
                        "type": "user_action",
                    },
                ],
                "severity": "high",
                "is_recoverable": True,
                "technical_details": "FileNotFoundError: /path/to/file.nwb",
            }
        )

        recovery = IntelligentErrorRecovery(llm_service=llm_service)

        error = FileNotFoundError("/path/to/file.nwb")
        context = {
            "operation": "file_read",
            "file_path": "/path/to/file.nwb",
            "format": "NWB",
        }

        result = await recovery.analyze_error(error, context, global_state)

        assert result["user_message"] == "The file could not be found at the specified path"
        assert result["severity"] == "high"
        assert result["is_recoverable"] is True
        assert len(result["recovery_actions"]) == 2
        assert result["recovery_actions"][0]["type"] == "user_action"

        # Check error was recorded in history
        assert len(recovery.error_history) == 1
        assert recovery.error_history[0]["error_type"] == "FileNotFoundError"

        # Check logging
        assert any("Intelligent error analysis complete" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_analyze_error_without_llm_fallback(self, global_state):
        """Test error analysis falls back to basic when no LLM."""
        recovery = IntelligentErrorRecovery()  # No LLM

        error = ValueError("Invalid metadata format")
        context = {"operation": "metadata_validation"}

        result = await recovery.analyze_error(error, context, global_state)

        assert "user_message" in result
        assert "An error occurred" in result["user_message"]
        assert result["severity"] in ["low", "medium", "high", "critical"]
        assert result["is_recoverable"] is True
        assert len(result["recovery_actions"]) > 0

        # Check error was recorded
        assert len(recovery.error_history) == 1

    @pytest.mark.asyncio
    async def test_analyze_error_llm_failure_fallback(self, global_state):
        """Test error analysis falls back when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM service error"))

        recovery = IntelligentErrorRecovery(llm_service=llm_service)

        error = RuntimeError("Conversion failed")
        context = {"operation": "conversion"}

        result = await recovery.analyze_error(error, context, global_state)

        # Should fall back to basic analysis
        assert "user_message" in result
        assert "severity" in result
        assert result["is_recoverable"] is True

        # Check warning logged
        assert any("LLM error analysis failed" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_analyze_error_records_history(self, global_state):
        """Test that analyze_error records errors in history."""
        recovery = IntelligentErrorRecovery()

        error1 = ValueError("Error 1")
        error2 = RuntimeError("Error 2")
        error3 = FileNotFoundError("Error 3")

        await recovery.analyze_error(error1, {"operation": "op1"}, global_state)
        await recovery.analyze_error(error2, {"operation": "op2"}, global_state)
        await recovery.analyze_error(error3, {"operation": "op3"}, global_state)

        assert len(recovery.error_history) == 3
        assert recovery.error_history[0]["error_type"] == "ValueError"
        assert recovery.error_history[1]["error_type"] == "RuntimeError"
        assert recovery.error_history[2]["error_type"] == "FileNotFoundError"


@pytest.mark.unit
@pytest.mark.service
class TestBasicErrorAnalysis:
    """Tests for _basic_error_analysis fallback method."""

    def test_basic_error_analysis_file_not_found(self):
        """Test basic analysis for FileNotFoundError."""
        recovery = IntelligentErrorRecovery()

        error = FileNotFoundError("/test/file.nwb")
        context = {"operation": "file_read", "file_path": "/test/file.nwb"}

        result = recovery._basic_error_analysis(error, context)

        assert result["severity"] == "high"
        assert "FileNotFoundError" in result["likely_cause"]
        assert result["is_recoverable"] is True
        assert len(result["recovery_actions"]) > 0

    def test_basic_error_analysis_permission_error(self):
        """Test basic analysis for PermissionError."""
        recovery = IntelligentErrorRecovery()

        error = PermissionError("Access denied")
        context = {"operation": "file_write"}

        result = recovery._basic_error_analysis(error, context)

        assert result["severity"] == "high"
        assert "PermissionError" in result["likely_cause"]

    def test_basic_error_analysis_validation_error(self):
        """Test basic analysis for validation errors."""
        recovery = IntelligentErrorRecovery()

        error = ValueError("ValidationError: Invalid metadata")
        context = {"operation": "validation"}

        result = recovery._basic_error_analysis(error, context)

        assert result["severity"] == "medium"

    def test_basic_error_analysis_generic_error(self):
        """Test basic analysis for generic errors."""
        recovery = IntelligentErrorRecovery()

        error = RuntimeError("Something went wrong")
        context = {"operation": "conversion"}

        result = recovery._basic_error_analysis(error, context)

        assert result["severity"] == "medium"
        assert "user_message" in result
        assert "recovery_actions" in result


@pytest.mark.unit
@pytest.mark.service
class TestGetErrorPatterns:
    """Tests for _get_error_patterns method."""

    def test_get_error_patterns_no_history(self):
        """Test error patterns with no error history."""
        recovery = IntelligentErrorRecovery()

        patterns = recovery._get_error_patterns()

        assert patterns == "No previous errors"

    def test_get_error_patterns_single_error(self):
        """Test error patterns with single error."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [{"error_type": "ValueError", "error_message": "Test error"}]

        patterns = recovery._get_error_patterns()

        assert "Recent errors: 1 total" in patterns
        assert "ValueError: 1 occurrences" in patterns

    def test_get_error_patterns_multiple_same_type(self):
        """Test error patterns with multiple errors of same type."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [
            {"error_type": "FileNotFoundError", "error_message": "File 1"},
            {"error_type": "FileNotFoundError", "error_message": "File 2"},
            {"error_type": "FileNotFoundError", "error_message": "File 3"},
        ]

        patterns = recovery._get_error_patterns()

        assert "Recent errors: 3 total" in patterns
        assert "FileNotFoundError: 3 occurrences" in patterns

    def test_get_error_patterns_mixed_types(self):
        """Test error patterns with mixed error types."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [
            {"error_type": "ValueError", "error_message": "Error 1"},
            {"error_type": "RuntimeError", "error_message": "Error 2"},
            {"error_type": "ValueError", "error_message": "Error 3"},
            {"error_type": "FileNotFoundError", "error_message": "Error 4"},
            {"error_type": "ValueError", "error_message": "Error 5"},
        ]

        patterns = recovery._get_error_patterns()

        assert "Recent errors: 5 total" in patterns
        assert "ValueError: 3 occurrences" in patterns
        assert "RuntimeError: 1 occurrences" in patterns
        assert "FileNotFoundError: 1 occurrences" in patterns

    def test_get_error_patterns_limits_to_last_5(self):
        """Test that error patterns only considers last 5 errors."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [
            {"error_type": "OldError", "error_message": "Old 1"},
            {"error_type": "OldError", "error_message": "Old 2"},
            {"error_type": "RecentError", "error_message": "Recent 1"},
            {"error_type": "RecentError", "error_message": "Recent 2"},
            {"error_type": "RecentError", "error_message": "Recent 3"},
            {"error_type": "RecentError", "error_message": "Recent 4"},
            {"error_type": "RecentError", "error_message": "Recent 5"},
        ]

        patterns = recovery._get_error_patterns()

        # Should only count last 5 errors
        assert "Recent errors: 5 total" in patterns
        assert "RecentError: 5 occurrences" in patterns
        # OldError should not appear
        assert "OldError" not in patterns


@pytest.mark.unit
@pytest.mark.service
class TestSuggestProactiveFix:
    """Tests for suggest_proactive_fix method."""

    @pytest.mark.asyncio
    async def test_suggest_proactive_fix_no_pattern(self, global_state):
        """Test proactive fix with no error patterns."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [
            {"error_type": "ValueError", "error_message": "Error 1"},
            {"error_type": "RuntimeError", "error_message": "Error 2"},
        ]

        suggestion = await recovery.suggest_proactive_fix(global_state)

        # Not enough errors or no pattern detected
        assert suggestion is None

    @pytest.mark.asyncio
    async def test_suggest_proactive_fix_insufficient_history(self, global_state):
        """Test proactive fix with insufficient error history."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [
            {"error_type": "ValueError", "error_message": "Error 1"},
        ]

        suggestion = await recovery.suggest_proactive_fix(global_state)

        assert suggestion is None

    @pytest.mark.asyncio
    async def test_suggest_proactive_fix_pattern_detected(self, global_state):
        """Test proactive fix when pattern is detected."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [
            {"error_type": "FileNotFoundError", "error_message": "Error 1"},
            {"error_type": "FileNotFoundError", "error_message": "Error 2"},
            {"error_type": "FileNotFoundError", "error_message": "Error 3"},
        ]

        suggestion = await recovery.suggest_proactive_fix(global_state)

        assert suggestion is not None
        assert suggestion["pattern_detected"] == "FileNotFoundError"
        assert suggestion["occurrences"] == 3
        assert "suggestion" in suggestion

        # Check warning logged
        assert any("Detected repeated error pattern" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_suggest_proactive_fix_pattern_in_recent_5(self, global_state):
        """Test proactive fix considers only last 5 errors."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [
            {"error_type": "OldError", "error_message": "Old 1"},
            {"error_type": "OldError", "error_message": "Old 2"},
            {"error_type": "OldError", "error_message": "Old 3"},
            {"error_type": "RecentError", "error_message": "Recent 1"},
            {"error_type": "RecentError", "error_message": "Recent 2"},
            {"error_type": "RecentError", "error_message": "Recent 3"},
        ]

        suggestion = await recovery.suggest_proactive_fix(global_state)

        # Should detect RecentError pattern (3 occurrences in last 5)
        assert suggestion is not None
        assert suggestion["pattern_detected"] == "RecentError"
        assert suggestion["occurrences"] == 3

    @pytest.mark.asyncio
    async def test_suggest_proactive_fix_mixed_errors_no_pattern(self, global_state):
        """Test proactive fix with mixed errors but no pattern."""
        recovery = IntelligentErrorRecovery()
        recovery.error_history = [
            {"error_type": "ValueError", "error_message": "Error 1"},
            {"error_type": "RuntimeError", "error_message": "Error 2"},
            {"error_type": "FileNotFoundError", "error_message": "Error 3"},
            {"error_type": "PermissionError", "error_message": "Error 4"},
        ]

        suggestion = await recovery.suggest_proactive_fix(global_state)

        # No error appears 3+ times
        assert suggestion is None


@pytest.mark.unit
@pytest.mark.service
class TestIntelligentErrorRecoveryIntegration:
    """Integration tests for complete error recovery workflow."""

    @pytest.mark.asyncio
    async def test_complete_error_recovery_workflow(self, global_state):
        """Test complete workflow: analyze errors → detect patterns → suggest fix."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "user_message": "The file could not be found",
                "likely_cause": "File path is incorrect",
                "recovery_actions": [
                    {
                        "action": "Check file path",
                        "description": "Verify the file exists",
                        "type": "user_action",
                    }
                ],
                "severity": "high",
                "is_recoverable": True,
                "technical_details": "FileNotFoundError",
            }
        )

        recovery = IntelligentErrorRecovery(llm_service=llm_service)

        # Step 1: Analyze multiple similar errors
        error = FileNotFoundError("File not found")
        context = {"operation": "file_read", "file_path": "/test/file.nwb"}

        for _ in range(3):
            await recovery.analyze_error(error, context, global_state)

        # Step 2: Check error history
        assert len(recovery.error_history) == 3

        # Step 3: Get error patterns
        patterns = recovery._get_error_patterns()
        assert "FileNotFoundError: 3 occurrences" in patterns

        # Step 4: Suggest proactive fix
        suggestion = await recovery.suggest_proactive_fix(global_state)
        assert suggestion is not None
        assert suggestion["pattern_detected"] == "FileNotFoundError"
        assert suggestion["occurrences"] == 3

    @pytest.mark.asyncio
    async def test_error_recovery_with_llm_failure(self, global_state):
        """Test error recovery gracefully handles LLM failures."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM error"))

        recovery = IntelligentErrorRecovery(llm_service=llm_service)

        error = ValueError("Test error")
        context = {"operation": "test"}

        # Should not raise exception, falls back to basic analysis
        result = await recovery.analyze_error(error, context, global_state)

        assert "user_message" in result
        assert result["is_recoverable"] is True

    @pytest.mark.asyncio
    async def test_error_severity_classification(self, global_state):
        """Test that different error types get appropriate severity levels."""
        recovery = IntelligentErrorRecovery()

        # High severity: File errors
        result1 = recovery._basic_error_analysis(
            FileNotFoundError("File not found"),
            {"operation": "read"},
        )
        assert result1["severity"] == "high"

        # High severity: Permission errors
        result2 = recovery._basic_error_analysis(
            PermissionError("Access denied"),
            {"operation": "write"},
        )
        assert result2["severity"] == "high"

        # Medium severity: Validation errors
        result3 = recovery._basic_error_analysis(
            ValueError("ValidationError: Invalid data"),
            {"operation": "validate"},
        )
        assert result3["severity"] == "medium"

        # Medium severity: Generic errors
        result4 = recovery._basic_error_analysis(
            RuntimeError("Unknown error"),
            {"operation": "convert"},
        )
        assert result4["severity"] == "medium"


@pytest.mark.unit
@pytest.mark.service
class TestRealErrorRecoveryWorkflows:
    """
    Integration-style unit tests using real ErrorRecovery logic.

    Tests real error analysis and recovery strategies.
    """

    @pytest.mark.asyncio
    async def test_real_error_recovery_initialization(self, mock_llm_api_only):
        """Test real error recovery initialization."""
        from agents.error_recovery import IntelligentErrorRecovery

        recovery = IntelligentErrorRecovery(llm_service=mock_llm_api_only)

        # Verify real initialization
        assert recovery.llm_service is not None

    @pytest.mark.asyncio
    async def test_real_error_analysis_without_llm(self):
        """Test real error recovery can work without LLM."""
        from agents.error_recovery import IntelligentErrorRecovery

        recovery = IntelligentErrorRecovery(llm_service=None)

        # Verify can initialize without LLM
        assert recovery is not None
        assert recovery.llm_service is None

    @pytest.mark.asyncio
    async def test_real_error_categorization(self, mock_llm_api_only, global_state):
        """Test real error analysis with LLM."""
        from agents.error_recovery import IntelligentErrorRecovery

        recovery = IntelligentErrorRecovery(llm_service=mock_llm_api_only)

        # Configure mock to return analysis
        mock_llm_api_only.generate_structured_output = AsyncMock(
            return_value={
                "error_type": "ValidationError",
                "severity": "high",
                "suggested_actions": ["Check required fields"],
            }
        )

        # Test with real error analysis method
        error = ValueError("Missing required field")
        analysis = await recovery.analyze_error(error=error, context={"operation": "test"}, state=global_state)

        # Should return analysis dict
        assert isinstance(analysis, dict)
