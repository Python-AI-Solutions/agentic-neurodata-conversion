"""
Unit tests for AdaptiveRetryStrategy.

Tests intelligent retry logic that learns from failures and recommends strategies.
"""

from unittest.mock import AsyncMock

import pytest

from agentic_neurodata_conversion.agents.adaptive_retry import AdaptiveRetryStrategy
from agentic_neurodata_conversion.services.llm_service import MockLLMService

# Note: The following fixtures are provided by conftest files:
# - global_state: from root conftest.py (Fresh GlobalState for each test)
# - mock_llm_service: from root conftest.py (Mock LLM service)


@pytest.mark.unit
@pytest.mark.service
class TestAdaptiveRetryStrategyInitialization:
    """Tests for AdaptiveRetryStrategy initialization."""

    def test_init_with_llm_service(self):
        """Test initialization with LLM service."""
        llm_service = MockLLMService()
        strategy = AdaptiveRetryStrategy(llm_service=llm_service)

        assert strategy.llm_service is llm_service

    def test_init_without_llm_service(self):
        """Test initialization without LLM service (fallback mode)."""
        strategy = AdaptiveRetryStrategy()

        assert strategy.llm_service is None


@pytest.mark.unit
@pytest.mark.service
class TestAnalyzeAndRecommendStrategy:
    """Tests for analyze_and_recommend_strategy method."""

    @pytest.mark.asyncio
    async def test_analyze_stops_after_5_attempts(self, global_state):
        """Test that strategy stops after 5 attempts."""
        strategy = AdaptiveRetryStrategy()
        global_state.correction_attempt = 5

        validation_result = {"issues": [{"message": "Missing experimenter"}]}

        result = await strategy.analyze_and_recommend_strategy(global_state, validation_result)

        assert result["should_retry"] is False
        assert result["strategy"] == "stop"
        assert result["ask_user"] is True
        assert "5 attempts" in result["message"]

    @pytest.mark.asyncio
    async def test_analyze_with_attempt_3(self, global_state):
        """Test strategy at attempt 3."""
        strategy = AdaptiveRetryStrategy()
        global_state.correction_attempt = 3

        # Current issues
        validation_result = {
            "issues": [{"message": "Missing experimenter", "check_function_name": "check_experimenter"}]
        }

        result = await strategy.analyze_and_recommend_strategy(global_state, validation_result)

        # Should provide a strategy
        assert "should_retry" in result
        assert "strategy" in result

    @pytest.mark.asyncio
    async def test_analyze_with_llm_service(self, global_state):
        """Test analysis with LLM service."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "should_retry": True,
                "strategy": "retry_with_changes",
                "approach": "focus_on_subject_metadata",
                "root_cause": "Missing subject information",
                "message": "Let's try collecting subject metadata with a focused approach",
                "ask_user": False,
                "reasoning": "We can improve subject metadata handling",
            }
        )

        strategy = AdaptiveRetryStrategy(llm_service=llm_service)
        global_state.correction_attempt = 1

        validation_result = {"issues": [{"message": "Missing subject_id", "check_function_name": "check_subject"}]}

        result = await strategy.analyze_and_recommend_strategy(global_state, validation_result)

        assert result["should_retry"] is True
        assert result["strategy"] == "retry_with_changes"
        assert result["approach"] == "focus_on_subject_metadata"

        # Check logging
        assert any("LLM adaptive retry analysis" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_analyze_fallback_when_llm_fails(self, global_state):
        """Test analysis falls back to heuristic when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM error"))

        strategy = AdaptiveRetryStrategy(llm_service=llm_service)
        global_state.correction_attempt = 1

        validation_result = {"issues": [{"message": "Missing metadata"}]}

        result = await strategy.analyze_and_recommend_strategy(global_state, validation_result)

        # Should fall back to heuristic
        assert "should_retry" in result
        assert "strategy" in result

    @pytest.mark.asyncio
    async def test_analyze_exception_handling(self, global_state):
        """Test that exceptions are handled gracefully."""
        strategy = AdaptiveRetryStrategy()
        global_state.correction_attempt = 1

        # Invalid validation result
        validation_result = None

        result = await strategy.analyze_and_recommend_strategy(global_state, validation_result)

        # Should return safe fallback
        assert result["should_retry"] is True
        assert result["strategy"] == "simple_retry"


@pytest.mark.unit
@pytest.mark.service
class TestExtractPreviousIssues:
    """Tests for _extract_previous_issues method."""

    def test_extract_previous_issues_no_history(self, global_state):
        """Test extracting issues when no history exists."""
        strategy = AdaptiveRetryStrategy()

        issues = strategy._extract_previous_issues(global_state)

        assert isinstance(issues, list)
        assert len(issues) == 0

    def test_extract_previous_issues_when_attr_doesnt_exist(self, global_state):
        """Test extracting issues when attribute doesn't exist on state."""
        strategy = AdaptiveRetryStrategy()

        # GlobalState doesn't have previous_validation_results attribute
        # So this should return empty list
        issues = strategy._extract_previous_issues(global_state)

        # Should return empty list since attribute doesn't exist
        assert isinstance(issues, list)
        assert len(issues) == 0


@pytest.mark.unit
@pytest.mark.service
class TestAnalyzeProgress:
    """Tests for _analyze_progress method."""

    def test_analyze_progress_first_attempt(self):
        """Test progress analysis for first attempt (no previous issues)."""
        strategy = AdaptiveRetryStrategy()

        current_issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
        ]

        result = strategy._analyze_progress([], current_issues)

        assert result["making_progress"] is True
        assert result["issues_fixed"] == 0
        assert result["new_issues"] == 0
        assert result["persistent_issues"] == 2

    def test_analyze_progress_improvement(self):
        """Test progress analysis when issues are being fixed."""
        strategy = AdaptiveRetryStrategy()

        previous_issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
            {"check_function_name": "check_subject"},
        ]

        current_issues = [
            {"check_function_name": "check_subject"}  # Only one remains
        ]

        result = strategy._analyze_progress(previous_issues, current_issues)

        assert result["making_progress"] is True
        assert result["issues_fixed"] == 2  # experimenter, institution fixed
        assert result["new_issues"] == 0
        assert result["persistent_issues"] == 1
        assert result["issue_count_change"] == -2  # Went from 3 to 1

    def test_analyze_progress_no_improvement(self):
        """Test progress analysis when no improvement is made."""
        strategy = AdaptiveRetryStrategy()

        previous_issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
        ]

        current_issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
        ]

        result = strategy._analyze_progress(previous_issues, current_issues)

        assert result["making_progress"] is False
        assert result["issues_fixed"] == 0
        assert result["new_issues"] == 0
        assert result["persistent_issues"] == 2
        assert result["issue_count_change"] == 0

    def test_analyze_progress_new_issues_introduced(self):
        """Test progress analysis when new issues are introduced."""
        strategy = AdaptiveRetryStrategy()

        previous_issues = [{"check_function_name": "check_experimenter"}]

        current_issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
            {"check_function_name": "check_subject"},
        ]

        result = strategy._analyze_progress(previous_issues, current_issues)

        assert result["making_progress"] is False  # More issues now
        assert result["issues_fixed"] == 0
        assert result["new_issues"] == 2
        assert result["persistent_issues"] == 1
        assert result["issue_count_change"] == 2

    def test_analyze_progress_mixed_changes(self):
        """Test progress analysis with mixed changes (some fixed, some new)."""
        strategy = AdaptiveRetryStrategy()

        previous_issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
            {"check_function_name": "check_subject"},
        ]

        current_issues = [
            {"check_function_name": "check_subject"},
            {"check_function_name": "check_session"},  # New issue
        ]

        result = strategy._analyze_progress(previous_issues, current_issues)

        # Fixed 2, introduced 1 - net positive
        assert result["making_progress"] is True
        assert result["issues_fixed"] == 2
        assert result["new_issues"] == 1
        assert result["persistent_issues"] == 1


@pytest.mark.unit
@pytest.mark.service
class TestHeuristicStrategy:
    """Tests for _heuristic_strategy fallback method."""

    def test_heuristic_stops_at_5_attempts(self):
        """Test heuristic stops at max attempts."""
        strategy = AdaptiveRetryStrategy()

        result = strategy._heuristic_strategy(
            attempt_num=5,
            current_issues=[],
            progress_analysis={"making_progress": False},
        )

        assert result["should_retry"] is False
        assert result["strategy"] == "stop"
        assert result["ask_user"] is True

    def test_heuristic_asks_user_when_stuck(self):
        """Test heuristic asks user when not making progress."""
        strategy = AdaptiveRetryStrategy()

        result = strategy._heuristic_strategy(
            attempt_num=2,
            current_issues=[],
            progress_analysis={"making_progress": False},
        )

        assert result["should_retry"] is False
        assert result["strategy"] == "ask_user"
        assert result["ask_user"] is True

    def test_heuristic_focuses_on_metadata_issues(self):
        """Test heuristic identifies metadata issues."""
        strategy = AdaptiveRetryStrategy()

        metadata_issues = [{"message": "Missing metadata field: experimenter"}]

        result = strategy._heuristic_strategy(
            attempt_num=1,
            current_issues=metadata_issues,
            progress_analysis={"making_progress": True},
        )

        assert result["should_retry"] is True
        assert result["approach"] == "focus_on_metadata"

    def test_heuristic_default_retry(self):
        """Test heuristic default retry strategy."""
        strategy = AdaptiveRetryStrategy()

        result = strategy._heuristic_strategy(
            attempt_num=1,
            current_issues=[{"message": "Some validation error"}],
            progress_analysis={"making_progress": True},
        )

        assert result["should_retry"] is True
        assert result["strategy"] == "retry_with_changes"
        assert result["ask_user"] is False


@pytest.mark.unit
@pytest.mark.service
class TestFormatIssuesSummary:
    """Tests for _format_issues_summary method."""

    def test_format_issues_no_issues(self):
        """Test formatting with no issues."""
        strategy = AdaptiveRetryStrategy()

        summary = strategy._format_issues_summary([])

        assert summary == "No issues"

    def test_format_issues_single_severity(self):
        """Test formatting issues with single severity."""
        strategy = AdaptiveRetryStrategy()

        issues = [
            {"severity": "ERROR", "message": "Missing experimenter"},
            {"severity": "ERROR", "message": "Missing institution"},
        ]

        summary = strategy._format_issues_summary(issues)

        assert "ERROR" in summary
        assert "2 issues" in summary
        assert "Missing experimenter" in summary
        assert "Missing institution" in summary

    def test_format_issues_multiple_severities(self):
        """Test formatting issues with multiple severities."""
        strategy = AdaptiveRetryStrategy()

        issues = [
            {"severity": "ERROR", "message": "Error 1"},
            {"severity": "ERROR", "message": "Error 2"},
            {"severity": "WARNING", "message": "Warning 1"},
            {"severity": "INFO", "message": "Info 1"},
        ]

        summary = strategy._format_issues_summary(issues)

        assert "ERROR" in summary
        assert "WARNING" in summary
        assert "INFO" in summary

    def test_format_issues_limits_to_20(self):
        """Test that formatting limits to first 20 issues."""
        strategy = AdaptiveRetryStrategy()

        issues = [{"severity": "ERROR", "message": f"Error {i}"} for i in range(30)]

        summary = strategy._format_issues_summary(issues)

        assert "and 10 more issues" in summary

    def test_format_issues_limits_per_severity(self):
        """Test that formatting shows max 5 issues per severity."""
        strategy = AdaptiveRetryStrategy()

        issues = [{"severity": "ERROR", "message": f"Error {i}"} for i in range(10)]

        summary = strategy._format_issues_summary(issues)

        # Should show first 5 errors
        assert "Error 0" in summary
        assert "Error 4" in summary


@pytest.mark.unit
@pytest.mark.service
class TestLLMPoweredAnalysis:
    """Tests for _llm_powered_analysis method."""

    @pytest.mark.asyncio
    async def test_llm_analysis_success(self, global_state):
        """Test successful LLM-powered analysis."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "should_retry": True,
                "strategy": "retry_with_changes",
                "approach": "collect_subject_metadata",
                "root_cause": "Subject metadata incomplete",
                "message": "Focusing on subject metadata collection",
                "ask_user": False,
                "reasoning": "Subject fields are the primary issue",
            }
        )

        strategy = AdaptiveRetryStrategy(llm_service=llm_service)
        global_state.correction_attempt = 1
        global_state.metadata = {"experimenter": "Jane Doe"}

        previous_issues = [{"message": "Missing subject", "check_function_name": "check_subject"}]
        current_issues = [{"message": "Missing subject_id", "check_function_name": "check_subject_id"}]
        progress_analysis = {"making_progress": True, "issues_fixed": 0, "new_issues": 1, "persistent_issues": 0}

        result = await strategy._llm_powered_analysis(global_state, previous_issues, current_issues, progress_analysis)

        assert result["should_retry"] is True
        assert result["strategy"] == "retry_with_changes"
        assert result["approach"] == "collect_subject_metadata"

    @pytest.mark.asyncio
    async def test_llm_analysis_recommends_asking_user(self, global_state):
        """Test LLM recommends asking user for help."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "should_retry": False,
                "strategy": "ask_user",
                "approach": "request_experimenter_name",
                "root_cause": "Experimenter information is required but missing",
                "message": "We need your help to provide experimenter information",
                "ask_user": True,
                "questions_for_user": ["What is the experimenter's name?", "What institution?"],
                "reasoning": "This is critical metadata that requires user input",
            }
        )

        strategy = AdaptiveRetryStrategy(llm_service=llm_service)
        global_state.correction_attempt = 2

        progress_analysis = {
            "making_progress": False,
            "issues_fixed": 0,
            "new_issues": 0,
            "persistent_issues": 1,
        }

        result = await strategy._llm_powered_analysis(
            global_state, [], [{"message": "Missing experimenter"}], progress_analysis
        )

        assert result["should_retry"] is False
        assert result["ask_user"] is True
        assert len(result["questions_for_user"]) == 2

    @pytest.mark.asyncio
    async def test_llm_analysis_fallback_on_error(self, global_state):
        """Test LLM analysis falls back to heuristic on error."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM service unavailable"))

        strategy = AdaptiveRetryStrategy(llm_service=llm_service)
        global_state.correction_attempt = 1

        progress_analysis = {
            "making_progress": True,
            "issues_fixed": 0,
            "new_issues": 0,
            "persistent_issues": 1,
        }

        result = await strategy._llm_powered_analysis(global_state, [], [{"message": "Error"}], progress_analysis)

        # Should fall back to heuristic
        assert "should_retry" in result
        assert "strategy" in result


@pytest.mark.unit
@pytest.mark.service
class TestAdaptiveRetryStrategyIntegration:
    """Integration tests for complete adaptive retry workflow."""

    @pytest.mark.asyncio
    async def test_complete_retry_workflow_with_progress(self, global_state):
        """Test complete workflow when making progress."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "should_retry": True,
                "strategy": "retry_with_changes",
                "approach": "continue_current_approach",
                "root_cause": "Minor validation issues",
                "message": "We're making good progress, continuing with current approach",
                "ask_user": False,
                "reasoning": "Issues are decreasing, approach is working",
            }
        )

        strategy = AdaptiveRetryStrategy(llm_service=llm_service)

        # Simulating improvement over attempts
        global_state.correction_attempt = 2
        global_state.previous_validation_issues = [
            {"message": "Error 1", "check_function_name": "check1"},
            {"message": "Error 2", "check_function_name": "check2"},
            {"message": "Error 3", "check_function_name": "check3"},
        ]

        current_validation = {
            "issues": [
                {"message": "Error 3", "check_function_name": "check3"}  # Only 1 remains
            ]
        }

        result = await strategy.analyze_and_recommend_strategy(global_state, current_validation)

        assert result["should_retry"] is True
        assert result["strategy"] == "retry_with_changes"

    @pytest.mark.asyncio
    async def test_complete_retry_workflow_at_attempt_3(self, global_state):
        """Test complete workflow at attempt 3."""
        strategy = AdaptiveRetryStrategy()  # No LLM, use heuristic

        global_state.correction_attempt = 3
        global_state.previous_validation_issues = [{"message": "Same error", "check_function_name": "check1"}]

        current_validation = {"issues": [{"message": "Same error", "check_function_name": "check1"}]}

        result = await strategy.analyze_and_recommend_strategy(global_state, current_validation)

        # Should provide a strategy
        assert "should_retry" in result
        assert "strategy" in result

    @pytest.mark.asyncio
    async def test_max_attempts_reached(self, global_state):
        """Test behavior when max attempts are reached."""
        strategy = AdaptiveRetryStrategy()

        global_state.correction_attempt = 5

        current_validation = {"issues": [{"message": "Persistent error"}]}

        result = await strategy.analyze_and_recommend_strategy(global_state, current_validation)

        assert result["should_retry"] is False
        assert result["strategy"] == "stop"
        assert result["ask_user"] is True
        assert "5 attempts" in result["message"]


@pytest.mark.unit
@pytest.mark.service
class TestRealAdaptiveRetryWorkflows:
    """
    Integration-style unit tests using real AdaptiveRetryStrategy logic.

    Tests real retry decision logic instead of mocking.
    """

    @pytest.mark.asyncio
    async def test_real_retry_strategy_initialization(self, mock_llm_api_only):
        """Test real adaptive retry strategy initialization."""
        from agentic_neurodata_conversion.agents.adaptive_retry import AdaptiveRetryStrategy

        strategy = AdaptiveRetryStrategy(llm_service=mock_llm_api_only)

        # Verify real initialization
        assert strategy.llm_service is not None

    @pytest.mark.asyncio
    async def test_real_should_retry_decision(self, global_state):
        """Test real should_retry decision logic."""
        from agentic_neurodata_conversion.agents.adaptive_retry import AdaptiveRetryStrategy

        strategy = AdaptiveRetryStrategy(llm_service=None)

        # Test with real decision logic at attempt 2
        global_state.correction_attempt = 2
        validation_result = {"issues": [{"message": "Some error", "check_function_name": "check1"}]}

        result = await strategy.analyze_and_recommend_strategy(global_state, validation_result)

        # Should return a recommendation with should_retry field
        assert isinstance(result, dict)
        assert "should_retry" in result
        assert isinstance(result["should_retry"], bool)

    @pytest.mark.asyncio
    async def test_real_max_attempts_logic(self, global_state):
        """Test real max attempts enforcement."""
        from agentic_neurodata_conversion.agents.adaptive_retry import AdaptiveRetryStrategy

        strategy = AdaptiveRetryStrategy(llm_service=None)

        # Test at max attempts (5)
        global_state.correction_attempt = 5
        validation_result = {"issues": [{"message": "Persistent error"}]}

        result = await strategy.analyze_and_recommend_strategy(global_state, validation_result)

        # Should not retry when at max attempts
        assert result["should_retry"] is False
        assert result["strategy"] == "stop"

    @pytest.mark.asyncio
    async def test_real_analyze_and_recommend(self, mock_llm_api_only, global_state):
        """Test real analyze and recommend strategy."""
        from agentic_neurodata_conversion.agents.adaptive_retry import AdaptiveRetryStrategy

        # Configure mock LLM to return proper structured output
        mock_llm_api_only.generate_structured_output = AsyncMock(
            return_value={
                "should_retry": True,
                "strategy": "retry_with_changes",
                "approach": "focus_on_metadata",
                "root_cause": "Minor validation issue",
                "message": "Retrying with improved approach",
                "ask_user": False,
                "reasoning": "Issues can be resolved automatically",
            }
        )

        strategy = AdaptiveRetryStrategy(llm_service=mock_llm_api_only)

        # Set up state with validation result
        global_state.correction_attempt = 1
        validation_result = {"issues": [{"message": "Minor error", "check_function_name": "check1"}]}

        # Test real analysis
        result = await strategy.analyze_and_recommend_strategy(global_state, validation_result)

        # Should return a recommendation with expected fields
        assert result is not None
        assert "should_retry" in result
        assert result["should_retry"] is True
        assert "strategy" in result
        assert result["strategy"] == "retry_with_changes"
        assert "message" in result
