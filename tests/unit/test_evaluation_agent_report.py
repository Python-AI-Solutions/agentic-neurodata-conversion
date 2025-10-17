"""
Unit tests for EvaluationAgent - Validation Report Generation (Task 6.2).

Tests the report generation methods for validation results.

Test coverage:
- Generate report creates JSON file
- Report includes session_id
- Report includes overall_status
- Report includes all issues with details
- Report path generated correctly
- Metadata completeness score calculation
- Best practices score calculation
- Scores based on issue counts
"""

import json
from pathlib import Path

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
def sample_issues() -> list[ValidationIssue]:
    """Create sample validation issues for testing."""
    return [
        ValidationIssue(
            severity="CRITICAL",
            message="Critical issue 1",
            location="/test/location1",
            check_name="test_check1",
        ),
        ValidationIssue(
            severity="BEST_PRACTICE_VIOLATION",
            message="Violation issue 1",
            location="/test/location2",
            check_name="test_check2",
        ),
        ValidationIssue(
            severity="BEST_PRACTICE_SUGGESTION",
            message="Suggestion issue 1",
            location="/test/location3",
            check_name="test_check3",
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_report_creates_json_file(
    evaluation_agent: EvaluationAgent,
    sample_issues: list[ValidationIssue],
    tmp_path: Path,
) -> None:
    """Test generate report creates JSON file."""
    session_id = "test-session-001"
    overall_status = "failed"
    issue_count = {"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 1, "BEST_PRACTICE_SUGGESTION": 1}
    metadata_score = 85.0
    best_practices_score = 70.0

    # Generate report
    report_path = await evaluation_agent._generate_report(
        session_id=session_id,
        overall_status=overall_status,
        issue_count=issue_count,
        issues=sample_issues,
        metadata_score=metadata_score,
        best_practices_score=best_practices_score,
    )

    # Verify file was created
    report_file = Path(report_path)
    assert report_file.exists()
    assert report_file.suffix == ".json"
    assert report_file.stat().st_size > 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_report_includes_session_id(
    evaluation_agent: EvaluationAgent,
    sample_issues: list[ValidationIssue],
    tmp_path: Path,
) -> None:
    """Test report includes session_id."""
    session_id = "test-session-002"
    # Use issues with warnings only (no critical) to match "passed_with_warnings" status
    issues_with_warnings = [
        ValidationIssue(
            severity="BEST_PRACTICE_VIOLATION",
            message="Violation issue 1",
            location="/test/location2",
            check_name="test_check2",
        ),
        ValidationIssue(
            severity="BEST_PRACTICE_SUGGESTION",
            message="Suggestion issue 1",
            location="/test/location3",
            check_name="test_check3",
        ),
    ]
    overall_status = "passed_with_warnings"
    issue_count = {"CRITICAL": 0, "BEST_PRACTICE_VIOLATION": 1, "BEST_PRACTICE_SUGGESTION": 1}
    metadata_score = 90.0
    best_practices_score = 80.0

    # Generate report
    report_path = await evaluation_agent._generate_report(
        session_id=session_id,
        overall_status=overall_status,
        issue_count=issue_count,
        issues=issues_with_warnings,
        metadata_score=metadata_score,
        best_practices_score=best_practices_score,
    )

    # Read and verify JSON content
    with open(report_path, "r") as f:
        report_data = json.load(f)

    assert "session_id" in report_data
    assert report_data["session_id"] == session_id


@pytest.mark.asyncio
@pytest.mark.unit
async def test_report_includes_overall_status(
    evaluation_agent: EvaluationAgent,
    sample_issues: list[ValidationIssue],
    tmp_path: Path,
) -> None:
    """Test report includes overall_status."""
    session_id = "test-session-003"
    overall_status = "passed"
    issue_count = {"CRITICAL": 0, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0}
    metadata_score = 100.0
    best_practices_score = 100.0

    # Generate report
    report_path = await evaluation_agent._generate_report(
        session_id=session_id,
        overall_status=overall_status,
        issue_count=issue_count,
        issues=[],
        metadata_score=metadata_score,
        best_practices_score=best_practices_score,
    )

    # Read and verify JSON content
    with open(report_path, "r") as f:
        report_data = json.load(f)

    assert "overall_status" in report_data
    assert report_data["overall_status"] == overall_status


@pytest.mark.asyncio
@pytest.mark.unit
async def test_report_includes_all_issues(
    evaluation_agent: EvaluationAgent,
    sample_issues: list[ValidationIssue],
    tmp_path: Path,
) -> None:
    """Test report includes all issues with details."""
    session_id = "test-session-004"
    overall_status = "failed"
    issue_count = {"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 1, "BEST_PRACTICE_SUGGESTION": 1}
    metadata_score = 75.0
    best_practices_score = 65.0

    # Generate report
    report_path = await evaluation_agent._generate_report(
        session_id=session_id,
        overall_status=overall_status,
        issue_count=issue_count,
        issues=sample_issues,
        metadata_score=metadata_score,
        best_practices_score=best_practices_score,
    )

    # Read and verify JSON content
    with open(report_path, "r") as f:
        report_data = json.load(f)

    assert "issues" in report_data
    assert len(report_data["issues"]) == 3

    # Verify issue details
    for i, issue in enumerate(report_data["issues"]):
        assert issue["severity"] == sample_issues[i].severity
        assert issue["message"] == sample_issues[i].message
        assert issue["location"] == sample_issues[i].location
        assert issue["check_name"] == sample_issues[i].check_name


@pytest.mark.asyncio
@pytest.mark.unit
async def test_report_path_generated_correctly(
    evaluation_agent: EvaluationAgent,
    sample_issues: list[ValidationIssue],
    tmp_path: Path,
) -> None:
    """Test report path generated correctly."""
    session_id = "test-session-005"
    overall_status = "passed"
    issue_count = {"CRITICAL": 0, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0}
    metadata_score = 95.0
    best_practices_score = 92.0

    # Generate report
    report_path = await evaluation_agent._generate_report(
        session_id=session_id,
        overall_status=overall_status,
        issue_count=issue_count,
        issues=[],
        metadata_score=metadata_score,
        best_practices_score=best_practices_score,
    )

    # Verify path contains session ID
    assert session_id in report_path
    assert report_path.endswith("_validation.json")

    # Verify path is absolute
    assert Path(report_path).is_absolute()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_metadata_completeness_score_calculation(
    evaluation_agent: EvaluationAgent,
) -> None:
    """Test metadata completeness score calculation."""
    # Test with complete metadata (all critical fields present)
    metadata = {
        "subject_id": "Mouse001",
        "species": "Mus musculus",
        "session_start_time": "2024-01-15T12:00:00Z",
        "session_description": "Test session",
        "experimenter": "Test User",
    }
    score = evaluation_agent._calculate_metadata_score(metadata)
    assert score == 100.0

    # Test with partial metadata (missing some fields)
    partial_metadata = {
        "subject_id": "Mouse001",
        "species": "Mus musculus",
    }
    score = evaluation_agent._calculate_metadata_score(partial_metadata)
    assert score < 100.0
    assert score >= 0.0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_best_practices_score_calculation(
    evaluation_agent: EvaluationAgent,
) -> None:
    """Test best practices score calculation."""
    # Test with no issues (perfect score)
    issue_count_perfect = {"CRITICAL": 0, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0}
    score = evaluation_agent._calculate_best_practices_score(issue_count_perfect)
    assert score == 100.0

    # Test with some issues (score should be lower)
    issue_count_with_issues = {"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 2, "BEST_PRACTICE_SUGGESTION": 3}
    score = evaluation_agent._calculate_best_practices_score(issue_count_with_issues)
    assert score < 100.0
    assert score >= 0.0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_scores_based_on_issue_counts(
    evaluation_agent: EvaluationAgent,
) -> None:
    """Test scores based on issue counts."""
    # More critical issues should result in lower score
    few_issues = {"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0}
    many_issues = {"CRITICAL": 5, "BEST_PRACTICE_VIOLATION": 3, "BEST_PRACTICE_SUGGESTION": 2}

    score_few = evaluation_agent._calculate_best_practices_score(few_issues)
    score_many = evaluation_agent._calculate_best_practices_score(many_issues)

    # More issues should lead to lower score
    assert score_many < score_few

    # Critical issues should have more weight than violations
    critical_only = {"CRITICAL": 1, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0}
    violations_only = {"CRITICAL": 0, "BEST_PRACTICE_VIOLATION": 1, "BEST_PRACTICE_SUGGESTION": 0}

    score_critical = evaluation_agent._calculate_best_practices_score(critical_only)
    score_violation = evaluation_agent._calculate_best_practices_score(violations_only)

    assert score_critical < score_violation
