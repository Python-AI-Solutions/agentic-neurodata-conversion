"""
Unit tests for EvaluationAgent - NWB Inspector Integration (Task 6.1).

Tests the _validate_nwb method for validating NWB files using NWB Inspector.

Test coverage:
- Validation with valid NWB file
- Validation issues collected correctly
- Issue severity categorization (critical/warning/info)
- Issue count by severity
- Overall status determination (passed/passed_with_warnings/failed)
- Validation with missing NWB file
- Validation with corrupt NWB file
"""

from pathlib import Path
from unittest.mock import Mock, patch

import h5py
import pytest

from agentic_neurodata_conversion.agents.evaluation_agent import EvaluationAgent
from agentic_neurodata_conversion.config import AgentConfig


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
def valid_nwb_file(tmp_path: Path) -> Path:
    """Create a minimal valid NWB file for testing."""
    nwb_path = tmp_path / "test_session.nwb"
    with h5py.File(nwb_path, "w") as f:
        # Create minimal NWB structure
        f.attrs["nwb_version"] = "2.5.0"
        f.create_group("acquisition")
        f.create_group("general")
        f.create_group("specifications")
        # Add some test data
        f.create_dataset("acquisition/test_data", data=[1, 2, 3], compression="gzip")
    return nwb_path


@pytest.fixture
def corrupt_nwb_file(tmp_path: Path) -> Path:
    """Create a corrupt NWB file for testing."""
    nwb_path = tmp_path / "corrupt_session.nwb"
    # Create an invalid HDF5 file
    with open(nwb_path, "w") as f:
        f.write("This is not a valid HDF5/NWB file")
    return nwb_path


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validate_nwb_valid_file(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    valid_nwb_file: Path,
) -> None:
    """Test validation with valid NWB file."""
    session_id = "test-session-001"

    # Mock NWB Inspector to return no issues
    mock_inspect.return_value = []

    # Run validation
    overall_status, issue_count, issues = await evaluation_agent._validate_nwb(
        str(valid_nwb_file)
    )

    # Verify validation succeeded
    assert overall_status == "passed"
    assert issue_count == {"CRITICAL": 0, "BEST_PRACTICE_VIOLATION": 0, "BEST_PRACTICE_SUGGESTION": 0}
    assert len(issues) == 0

    # Verify inspect_nwbfile was called with correct path
    mock_inspect.assert_called_once_with(nwbfile_path=str(valid_nwb_file))


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validation_issues_collected(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    valid_nwb_file: Path,
) -> None:
    """Test validation issues collected correctly."""
    session_id = "test-session-002"

    # Mock NWB Inspector to return some issues
    mock_issue1 = Mock()
    mock_issue1.severity = "BEST_PRACTICE_VIOLATION"
    mock_issue1.message = "Missing session description"
    mock_issue1.location = "/general/session_description"
    mock_issue1.check_function_name = "check_session_description"

    mock_issue2 = Mock()
    mock_issue2.severity = "BEST_PRACTICE_SUGGESTION"
    mock_issue2.message = "Consider adding experimenter name"
    mock_issue2.location = "/general/experimenter"
    mock_issue2.check_function_name = "check_experimenter"

    mock_inspect.return_value = [mock_issue1, mock_issue2]

    # Run validation
    overall_status, issue_count, issues = await evaluation_agent._validate_nwb(
        str(valid_nwb_file)
    )

    # Verify issues were collected
    assert len(issues) == 2
    assert issues[0].severity == "BEST_PRACTICE_VIOLATION"
    assert issues[0].message == "Missing session description"
    assert issues[1].severity == "BEST_PRACTICE_SUGGESTION"
    assert issues[1].message == "Consider adding experimenter name"


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_issue_severity_categorization(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    valid_nwb_file: Path,
) -> None:
    """Test issue severity categorization (critical/warning/info)."""
    # Mock NWB Inspector to return issues with different severities
    mock_critical = Mock()
    mock_critical.severity = "CRITICAL"
    mock_critical.message = "Critical error"
    mock_critical.location = "/test"
    mock_critical.check_function_name = "test_check"

    mock_violation = Mock()
    mock_violation.severity = "BEST_PRACTICE_VIOLATION"
    mock_violation.message = "Violation"
    mock_violation.location = "/test"
    mock_violation.check_function_name = "test_check"

    mock_suggestion = Mock()
    mock_suggestion.severity = "BEST_PRACTICE_SUGGESTION"
    mock_suggestion.message = "Suggestion"
    mock_suggestion.location = "/test"
    mock_suggestion.check_function_name = "test_check"

    mock_inspect.return_value = [mock_critical, mock_violation, mock_suggestion]

    # Run validation
    overall_status, issue_count, issues = await evaluation_agent._validate_nwb(
        str(valid_nwb_file)
    )

    # Verify severity categories are distinct
    assert issues[0].severity == "CRITICAL"
    assert issues[1].severity == "BEST_PRACTICE_VIOLATION"
    assert issues[2].severity == "BEST_PRACTICE_SUGGESTION"


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_issue_count_by_severity(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    valid_nwb_file: Path,
) -> None:
    """Test issue count by severity."""
    # Mock NWB Inspector to return multiple issues
    critical_issues = [Mock(severity="CRITICAL", message=f"Critical {i}", location="/test", check_function_name="test") for i in range(2)]
    violation_issues = [Mock(severity="BEST_PRACTICE_VIOLATION", message=f"Violation {i}", location="/test", check_function_name="test") for i in range(3)]
    suggestion_issues = [Mock(severity="BEST_PRACTICE_SUGGESTION", message=f"Suggestion {i}", location="/test", check_function_name="test") for i in range(1)]

    mock_inspect.return_value = critical_issues + violation_issues + suggestion_issues

    # Run validation
    overall_status, issue_count, issues = await evaluation_agent._validate_nwb(
        str(valid_nwb_file)
    )

    # Verify counts by severity
    assert issue_count["CRITICAL"] == 2
    assert issue_count["BEST_PRACTICE_VIOLATION"] == 3
    assert issue_count["BEST_PRACTICE_SUGGESTION"] == 1
    assert len(issues) == 6


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_overall_status_passed(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    valid_nwb_file: Path,
) -> None:
    """Test overall status determination: passed (no issues)."""
    mock_inspect.return_value = []

    # Run validation
    overall_status, issue_count, issues = await evaluation_agent._validate_nwb(
        str(valid_nwb_file)
    )

    # Verify status is "passed"
    assert overall_status == "passed"


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_overall_status_passed_with_warnings(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    valid_nwb_file: Path,
) -> None:
    """Test overall status determination: passed_with_warnings (only non-critical)."""
    # Mock NWB Inspector to return only non-critical issues
    mock_violation = Mock(severity="BEST_PRACTICE_VIOLATION", message="Violation", location="/test", check_function_name="test")
    mock_suggestion = Mock(severity="BEST_PRACTICE_SUGGESTION", message="Suggestion", location="/test", check_function_name="test")

    mock_inspect.return_value = [mock_violation, mock_suggestion]

    # Run validation
    overall_status, issue_count, issues = await evaluation_agent._validate_nwb(
        str(valid_nwb_file)
    )

    # Verify status is "passed_with_warnings"
    assert overall_status == "passed_with_warnings"


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_overall_status_failed(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    valid_nwb_file: Path,
) -> None:
    """Test overall status determination: failed (has critical issues)."""
    # Mock NWB Inspector to return critical issues
    mock_critical = Mock(severity="CRITICAL", message="Critical error", location="/test", check_function_name="test")
    mock_violation = Mock(severity="BEST_PRACTICE_VIOLATION", message="Violation", location="/test", check_function_name="test")

    mock_inspect.return_value = [mock_critical, mock_violation]

    # Run validation
    overall_status, issue_count, issues = await evaluation_agent._validate_nwb(
        str(valid_nwb_file)
    )

    # Verify status is "failed"
    assert overall_status == "failed"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_validation_missing_nwb_file(
    evaluation_agent: EvaluationAgent,
    tmp_path: Path,
) -> None:
    """Test validation with missing NWB file."""
    missing_file = tmp_path / "nonexistent.nwb"

    # Should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        await evaluation_agent._validate_nwb(str(missing_file))


@pytest.mark.asyncio
@pytest.mark.unit
@patch("agentic_neurodata_conversion.agents.evaluation_agent.inspect_nwbfile")
async def test_validation_corrupt_nwb_file(
    mock_inspect: Mock,
    evaluation_agent: EvaluationAgent,
    corrupt_nwb_file: Path,
) -> None:
    """Test validation with corrupt NWB file."""
    # Mock inspect_nwbfile to raise an exception for corrupt files
    mock_inspect.side_effect = OSError("Unable to open file (file signature not found)")

    # Should raise an exception
    with pytest.raises(OSError):
        await evaluation_agent._validate_nwb(str(corrupt_nwb_file))
