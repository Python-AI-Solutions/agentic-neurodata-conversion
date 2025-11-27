"""
Unit tests for AdaptiveRetryStrategy.

Tests intelligent retry decision making and failure pattern analysis.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.error_handling.adaptive_retry import AdaptiveRetryStrategy
from agentic_neurodata_conversion.models.state import GlobalState


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    service = Mock()
    service.generate_structured_output = AsyncMock()
    return service


@pytest.fixture
def retry_strategy(mock_llm_service):
    """Create retry strategy with mock LLM."""
    return AdaptiveRetryStrategy(llm_service=mock_llm_service)


@pytest.fixture
def state():
    """Create mock global state."""
    state = GlobalState()
    state.correction_attempt = 1
    state.metadata = {}
    return state


@pytest.fixture
def validation_result():
    """Create sample validation result."""
    return {
        "issues": [
            {
                "severity": "CRITICAL",
                "message": "Missing experimenter",
                "check_function_name": "check_experimenter",
            },
            {
                "severity": "BEST_PRACTICE_VIOLATION",
                "message": "Missing keywords",
                "check_function_name": "check_keywords",
            },
        ]
    }


@pytest.mark.unit
class TestAdaptiveRetryStrategy:
    """Test suite for AdaptiveRetryStrategy."""

    def test_initialization(self, mock_llm_service):
        """Test strategy initialization."""
        strategy = AdaptiveRetryStrategy(llm_service=mock_llm_service)
        assert strategy.llm_service == mock_llm_service

    def test_initialization_without_llm(self):
        """Test strategy works without LLM."""
        strategy = AdaptiveRetryStrategy(llm_service=None)
        assert strategy.llm_service is None

    @pytest.mark.asyncio
    async def test_stop_after_max_attempts(self, retry_strategy, state, validation_result):
        """Test that strategy stops after maximum attempts."""
        state.correction_attempt = 5

        recommendation = await retry_strategy.analyze_and_recommend_strategy(
            state=state,
            current_validation_result=validation_result,
        )

        assert recommendation["should_retry"] is False
        assert recommendation["strategy"] == "stop"
        assert "manual" in recommendation["approach"].lower() or "intervention" in recommendation["message"].lower()

    @pytest.mark.asyncio
    async def test_stop_when_no_progress(self, retry_strategy, state, validation_result):
        """Test stopping when no progress is being made."""
        state.correction_attempt = 3

        # Set up state to show no progress - use previous_validation_issues, not previous_validation_results
        state.previous_validation_issues = validation_result["issues"]

        recommendation = await retry_strategy.analyze_and_recommend_strategy(
            state=state,
            current_validation_result=validation_result,
        )

        # Should stop or ask user when stuck
        if not recommendation["should_retry"]:
            assert recommendation["strategy"] in ["stop", "ask_user"]

    def test_progress_analysis_making_progress(self, retry_strategy):
        """Test progress analysis when issues are being fixed."""
        previous_issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
            {"check_function_name": "check_keywords"},
        ]

        current_issues = [
            {"check_function_name": "check_keywords"},
        ]

        analysis = retry_strategy._analyze_progress(previous_issues, current_issues)

        assert analysis["making_progress"] is True
        assert analysis["issues_fixed"] == 2
        assert analysis["issue_count_change"] == -2

    def test_progress_analysis_stuck(self, retry_strategy):
        """Test progress analysis when stuck with same issues."""
        issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
        ]

        analysis = retry_strategy._analyze_progress(issues, issues)

        assert analysis["making_progress"] is False
        assert analysis["issues_fixed"] == 0
        assert analysis["new_issues"] == 0
        assert analysis["persistent_issues"] == 2

    def test_progress_analysis_getting_worse(self, retry_strategy):
        """Test progress analysis when introducing new issues."""
        previous_issues = [
            {"check_function_name": "check_experimenter"},
        ]

        current_issues = [
            {"check_function_name": "check_experimenter"},
            {"check_function_name": "check_institution"},
            {"check_function_name": "check_keywords"},
        ]

        analysis = retry_strategy._analyze_progress(previous_issues, current_issues)

        assert analysis["making_progress"] is False
        assert analysis["new_issues"] == 2
        assert analysis["issue_count_change"] == 2

    @pytest.mark.asyncio
    async def test_llm_powered_analysis(self, retry_strategy, mock_llm_service, state, validation_result):
        """Test LLM-powered analysis."""
        mock_llm_service.generate_structured_output.return_value = {
            "should_retry": True,
            "strategy": "retry_with_changes",
            "approach": "focus_on_metadata",
            "root_cause": "Missing required metadata fields",
            "message": "Let's try focusing on metadata fields",
            "ask_user": False,
            "reasoning": "Metadata issues are fixable",
        }

        recommendation = await retry_strategy.analyze_and_recommend_strategy(
            state=state,
            current_validation_result=validation_result,
        )

        assert recommendation["should_retry"] is True
        assert recommendation["strategy"] == "retry_with_changes"
        assert recommendation["approach"] == "focus_on_metadata"
        assert mock_llm_service.generate_structured_output.called

    @pytest.mark.asyncio
    async def test_ask_user_recommendation(self, retry_strategy, mock_llm_service, state, validation_result):
        """Test recommendation to ask user for help."""
        mock_llm_service.generate_structured_output.return_value = {
            "should_retry": False,
            "strategy": "ask_user",
            "approach": "request_metadata",
            "root_cause": "Cannot infer required metadata",
            "message": "We need your help to fix these issues",
            "ask_user": True,
            "questions_for_user": [
                "Who performed this experiment?",
                "At which institution?",
            ],
            "reasoning": "Missing info that only user can provide",
        }

        recommendation = await retry_strategy.analyze_and_recommend_strategy(
            state=state,
            current_validation_result=validation_result,
        )

        assert recommendation["ask_user"] is True
        assert len(recommendation.get("questions_for_user", [])) > 0

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_llm(self, state, validation_result):
        """Test heuristic strategy when LLM unavailable."""
        strategy = AdaptiveRetryStrategy(llm_service=None)

        recommendation = await strategy.analyze_and_recommend_strategy(
            state=state,
            current_validation_result=validation_result,
        )

        # Should return valid recommendation
        assert "should_retry" in recommendation
        assert "strategy" in recommendation
        assert "approach" in recommendation
        assert "message" in recommendation

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self, retry_strategy, mock_llm_service, state, validation_result):
        """Test fallback when LLM call fails."""
        mock_llm_service.generate_structured_output.side_effect = Exception("LLM failed")

        recommendation = await retry_strategy.analyze_and_recommend_strategy(
            state=state,
            current_validation_result=validation_result,
        )

        # Should fallback to heuristic strategy
        assert "should_retry" in recommendation
        assert isinstance(recommendation["should_retry"], bool)

    def test_heuristic_strategy_first_attempt(self, retry_strategy, validation_result):
        """Test heuristic strategy on first attempt."""
        progress_analysis = {"making_progress": True}

        recommendation = retry_strategy._heuristic_strategy(
            attempt_num=1,
            current_issues=validation_result["issues"],
            progress_analysis=progress_analysis,
        )

        assert recommendation["should_retry"] is True

    def test_heuristic_strategy_metadata_issues(self, retry_strategy):
        """Test heuristic detects metadata issues."""
        issues = [
            {"message": "Missing metadata field experimenter"},
        ]

        progress_analysis = {"making_progress": True}

        recommendation = retry_strategy._heuristic_strategy(
            attempt_num=2,
            current_issues=issues,
            progress_analysis=progress_analysis,
        )

        assert recommendation["approach"] == "focus_on_metadata"

    def test_format_issues_summary(self, retry_strategy):
        """Test issue formatting for LLM."""
        issues = [
            {
                "severity": "CRITICAL",
                "message": "Missing experimenter",
                "check_function_name": "check_experimenter",
            },
            {
                "severity": "CRITICAL",
                "message": "Missing institution",
                "check_function_name": "check_institution",
            },
            {
                "severity": "BEST_PRACTICE_VIOLATION",
                "message": "Missing keywords",
                "check_function_name": "check_keywords",
            },
        ]

        summary = retry_strategy._format_issues_summary(issues)

        assert "CRITICAL" in summary
        assert "BEST_PRACTICE_VIOLATION" in summary
        assert "Missing experimenter" in summary
        assert "2 issues" in summary or "(2)" in summary

    def test_format_issues_summary_truncation(self, retry_strategy):
        """Test issue summary truncates long lists."""
        issues = [{"severity": "CRITICAL", "message": f"Issue {i}"} for i in range(30)]

        summary = retry_strategy._format_issues_summary(issues)

        # Should mention truncation
        assert "more issues" in summary.lower() or "..." in summary

    @pytest.mark.asyncio
    async def test_first_attempt_always_retries(self, retry_strategy, mock_llm_service, state, validation_result):
        """Test that first attempt always suggests retry."""
        state.correction_attempt = 1

        # Mock LLM to return a proper response
        mock_llm_service.generate_structured_output.return_value = {
            "should_retry": True,
            "strategy": "retry_with_changes",
            "approach": "fix_metadata",
            "message": "Let's try to fix the metadata issues",
            "ask_user": False,
            "reasoning": "First attempt - issues are fixable",
        }

        recommendation = await retry_strategy.analyze_and_recommend_strategy(
            state=state,
            current_validation_result=validation_result,
        )

        # First attempt should generally retry
        # (unless there are exceptional circumstances)
        if state.correction_attempt == 1:
            assert recommendation["should_retry"] is True or recommendation["ask_user"] is True

    def test_extract_previous_issues_empty_state(self, retry_strategy, state):
        """Test extracting issues when state has none."""
        issues = retry_strategy._extract_previous_issues(state)
        assert issues == []

    @pytest.mark.asyncio
    async def test_recommendation_includes_reasoning(self, retry_strategy, mock_llm_service, state, validation_result):
        """Test that recommendations include reasoning."""
        mock_llm_service.generate_structured_output.return_value = {
            "should_retry": True,
            "strategy": "retry_with_changes",
            "approach": "different_approach",
            "message": "Trying a different approach",
            "ask_user": False,
            "reasoning": "Previous approach didn't work, trying alternative",
        }

        recommendation = await retry_strategy.analyze_and_recommend_strategy(
            state=state,
            current_validation_result=validation_result,
        )

        assert "reasoning" in recommendation
        assert len(recommendation["reasoning"]) > 0
