"""
Unit tests for EvaluationAgent - LLM Validation Summary (Task 6.3).

Tests the LLM-based validation summary generation.

Test coverage:
- Generate validation summary with issues
- Summary includes overall status
- Summary highlights critical issues
- Summary provides recommendations
- Summary indicates if file ready for use
- Summary under 150 words
- Summary with no issues
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.agents.evaluation_agent import EvaluationAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.session_context import ValidationIssue


@pytest.fixture
def evaluation_agent(tmp_path: Path) -> EvaluationAgent:
    """Create EvaluationAgent instance for testing."""
    config = AgentConfig(
        agent_name="test-evaluation-agent",
        agent_type="evaluation",
        agent_port=8003,
        mcp_server_url="http://localhost:3000",
        llm_provider="anthropic",
        llm_api_key="test-key",
        llm_model="claude-3-5-sonnet-20241022",
        temperature=0.4,
        max_tokens=8192,
    )
    return EvaluationAgent(config)


@pytest.fixture
def sample_issues_with_critical() -> list[ValidationIssue]:
    """Create sample validation issues including critical ones."""
    return [
        ValidationIssue(
            severity="CRITICAL",
            message="File integrity check failed",
            location="/general/data_collection",
            check_name="check_file_integrity",
        ),
        ValidationIssue(
            severity="BEST_PRACTICE_VIOLATION",
            message="Missing session description",
            location="/general/session_description",
            check_name="check_session_description",
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.mock_llm
async def test_generate_validation_summary_with_issues(
    evaluation_agent: EvaluationAgent,
    sample_issues_with_critical: list[ValidationIssue],
) -> None:
    """Test generate validation summary with issues."""
    # Mock LLM response
    mock_summary = (
        "The NWB file validation failed with 1 critical issue and 1 best practice violation. "
        "Critical: File integrity check failed at /general/data_collection. "
        "This must be resolved before the file can be used. "
        "Also consider adding a session description to improve metadata completeness."
    )

    with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_summary

        # Generate summary
        summary = await evaluation_agent._generate_validation_summary(
            overall_status="failed",
            issue_count={"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 1, "BEST_PRACTICE_SUGGESTION": 0},
            issues=sample_issues_with_critical,
            metadata={"subject_id": "Mouse001"},
        )

        # Verify summary was generated
        assert summary == mock_summary
        assert len(summary) > 0

        # Verify LLM was called
        mock_llm.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.mock_llm
async def test_summary_includes_overall_status(
    evaluation_agent: EvaluationAgent,
    sample_issues_with_critical: list[ValidationIssue],
) -> None:
    """Test summary includes overall status."""
    mock_summary = "Validation status: FAILED. The file has critical issues that must be addressed."

    with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_summary

        summary = await evaluation_agent._generate_validation_summary(
            overall_status="failed",
            issue_count={"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0},
            issues=sample_issues_with_critical[:1],  # Only critical issue
            metadata={},
        )

        # Verify call_llm was called with prompt containing status
        assert mock_llm.called
        call_args = mock_llm.call_args
        prompt = call_args[0][0]  # First positional argument
        assert "failed" in prompt.lower()


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.mock_llm
async def test_summary_highlights_critical_issues(
    evaluation_agent: EvaluationAgent,
    sample_issues_with_critical: list[ValidationIssue],
) -> None:
    """Test summary highlights critical issues."""
    mock_summary = "CRITICAL: File integrity check failed. This is a blocking issue that prevents file usage."

    with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_summary

        summary = await evaluation_agent._generate_validation_summary(
            overall_status="failed",
            issue_count={"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0},
            issues=[sample_issues_with_critical[0]],  # Only critical issue
            metadata={},
        )

        # Verify LLM prompt includes critical issues
        call_args = mock_llm.call_args
        prompt = call_args[0][0]
        assert "CRITICAL" in prompt or "critical" in prompt.lower()


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.mock_llm
async def test_summary_provides_recommendations(
    evaluation_agent: EvaluationAgent,
    sample_issues_with_critical: list[ValidationIssue],
) -> None:
    """Test summary provides recommendations."""
    mock_summary = (
        "Validation failed. Recommendations: "
        "1) Fix file integrity issue at /general/data_collection. "
        "2) Add session description for better documentation."
    )

    with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_summary

        summary = await evaluation_agent._generate_validation_summary(
            overall_status="failed",
            issue_count={"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 1, "BEST_PRACTICE_SUGGESTION": 0},
            issues=sample_issues_with_critical,
            metadata={},
        )

        # Verify LLM was asked for recommendations
        call_args = mock_llm.call_args
        prompt = call_args[0][0]
        assert "recommendation" in prompt.lower() or "actionable" in prompt.lower()


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.mock_llm
async def test_summary_indicates_file_readiness(
    evaluation_agent: EvaluationAgent,
) -> None:
    """Test summary indicates if file ready for use."""
    # Test with failed validation
    mock_summary_failed = "File is NOT ready for use due to critical errors."

    with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_summary_failed

        summary = await evaluation_agent._generate_validation_summary(
            overall_status="failed",
            issue_count={"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0},
            issues=[
                ValidationIssue(
                    severity="CRITICAL",
                    message="Critical error",
                    location="/test",
                    check_name="test_check",
                )
            ],
            metadata={},
        )

        assert mock_llm.called

    # Test with passed validation
    mock_summary_passed = "File passed validation and is ready for use."

    with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_summary_passed

        summary = await evaluation_agent._generate_validation_summary(
            overall_status="passed",
            issue_count={"CRITICAL": 0, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0},
            issues=[],
            metadata={},
        )

        assert mock_llm.called


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.mock_llm
async def test_summary_under_150_words(
    evaluation_agent: EvaluationAgent,
    sample_issues_with_critical: list[ValidationIssue],
) -> None:
    """Test summary under 150 words."""
    # Create a concise summary (under 150 words)
    mock_summary = (
        "Validation failed with 1 critical issue and 1 violation. "
        "The file integrity check failed, preventing safe file usage. "
        "Recommendations: Fix the critical integrity issue and add session description."
    )

    with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_summary

        summary = await evaluation_agent._generate_validation_summary(
            overall_status="failed",
            issue_count={"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 1, "BEST_PRACTICE_SUGGESTION": 0},
            issues=sample_issues_with_critical,
            metadata={},
        )

        # Count words (approximate)
        word_count = len(summary.split())
        assert word_count <= 150

        # Verify LLM was asked for concise summary
        call_args = mock_llm.call_args
        prompt = call_args[0][0]
        assert "150 words" in prompt or "concise" in prompt.lower()


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.mock_llm
async def test_summary_with_no_issues(
    evaluation_agent: EvaluationAgent,
) -> None:
    """Test summary with no issues."""
    mock_summary = (
        "Validation passed successfully with no issues. "
        "The NWB file meets all quality standards and is ready for use."
    )

    with patch.object(evaluation_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_summary

        summary = await evaluation_agent._generate_validation_summary(
            overall_status="passed",
            issue_count={"CRITICAL": 0, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0},
            issues=[],
            metadata={"subject_id": "Mouse001", "species": "Mus musculus"},
        )

        # Verify summary was generated
        assert len(summary) > 0

        # Verify LLM was called with "passed" status
        call_args = mock_llm.call_args
        prompt = call_args[0][0]
        assert "passed" in prompt.lower()
