"""
Unit tests for ValidationHistoryLearner.

Tests validation history learning system that learns from past validation sessions.
"""

import asyncio
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, mock_open, patch
from datetime import datetime

from agents.validation_history_learning import ValidationHistoryLearner
from models import GlobalState, LogLevel, ValidationResult
from models.validation import ValidationIssue, ValidationSeverity
from services.llm_service import MockLLMService


# Note: The following fixtures are provided by conftest files:
# - global_state: from root conftest.py (Fresh GlobalState for each test)
# - tmp_path: from pytest (temporary directory)


@pytest.mark.unit
class TestValidationHistoryLearnerInitialization:
    """Tests for ValidationHistoryLearner initialization."""

    def test_init_with_llm_and_history_path(self, tmp_path):
        """Test initialization with LLM service and custom history path."""
        llm_service = MockLLMService()
        history_path = tmp_path / "custom_history"

        learner = ValidationHistoryLearner(llm_service=llm_service, history_path=str(history_path))

        assert learner.llm_service is llm_service
        assert learner.history_path == history_path
        assert history_path.exists()

    def test_init_without_llm(self, tmp_path):
        """Test initialization without LLM service."""
        history_path = tmp_path / "history"
        learner = ValidationHistoryLearner(history_path=str(history_path))

        assert learner.llm_service is None
        assert history_path.exists()

    def test_init_with_default_history_path(self):
        """Test initialization with default history path."""
        learner = ValidationHistoryLearner()

        assert learner.history_path == Path("outputs/validation_history")

    def test_init_creates_history_directory(self, tmp_path):
        """Test that initialization creates the history directory."""
        history_path = tmp_path / "nonexistent" / "history"
        assert not history_path.exists()

        learner = ValidationHistoryLearner(history_path=str(history_path))

        assert history_path.exists()


@pytest.mark.unit
class TestRecordValidationSession:
    """Tests for record_validation_session method."""

    @pytest.mark.asyncio
    async def test_record_session_creates_file(self, tmp_path, global_state):
        """Test recording a validation session creates a JSON file."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        validation_result = ValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Missing experimenter",
                    check_function_name="check_experimenter",
                )
            ],
            summary={"critical": 0, "error": 1, "warning": 0},
        )

        file_context = {
            "format": "SpikeGLX",
            "file_size_mb": 100,
            "nwb_version": "2.5.0",
        }

        await learner.record_validation_session(
            validation_result=validation_result,
            file_context=file_context,
            resolution_actions=[{"action": "fix_metadata"}],
            state=global_state,
        )

        # Check file was created
        session_files = list(tmp_path.glob("session_*.json"))
        assert len(session_files) == 1

        # Check file content
        with open(session_files[0]) as f:
            session_data = json.load(f)

        assert session_data["file_info"]["format"] == "SpikeGLX"
        assert session_data["validation"]["is_valid"] is False
        assert len(session_data["issues"]) == 1
        assert session_data["issues"][0]["severity"] == "error"  # Enum value is lowercase

    @pytest.mark.asyncio
    async def test_record_session_with_no_resolution_actions(self, tmp_path, global_state):
        """Test recording session without resolution actions."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        validation_result = ValidationResult(
            is_valid=True,
            issues=[],
            summary={"critical": 0, "error": 0, "warning": 0},
        )

        await learner.record_validation_session(
            validation_result=validation_result,
            file_context={"format": "NWB"},
            resolution_actions=None,
            state=global_state,
        )

        session_files = list(tmp_path.glob("session_*.json"))
        with open(session_files[0]) as f:
            session_data = json.load(f)

        assert session_data["resolution_actions"] == []

    @pytest.mark.asyncio
    async def test_record_session_handles_many_issues(self, tmp_path, global_state):
        """Test recording session limits issues to first 50."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        # Create 100 issues
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Issue {i}",
                check_function_name=f"check_{i}",
            )
            for i in range(100)
        ]

        validation_result = ValidationResult(
            is_valid=False,
            issues=issues,
            summary={"warning": 100},
        )

        await learner.record_validation_session(
            validation_result=validation_result,
            file_context={"format": "NWB"},
            resolution_actions=None,
            state=global_state,
        )

        session_files = list(tmp_path.glob("session_*.json"))
        with open(session_files[0]) as f:
            session_data = json.load(f)

        # Should only store first 50 issues
        assert len(session_data["issues"]) == 50

    @pytest.mark.asyncio
    async def test_record_session_logs_to_state(self, tmp_path, global_state):
        """Test that recording session logs to state."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        validation_result = ValidationResult(
            is_valid=True,
            issues=[],
            summary={},
        )

        await learner.record_validation_session(
            validation_result=validation_result,
            file_context={},
            resolution_actions=None,
            state=global_state,
        )

        # Check logging
        assert any("Recorded validation session" in log.message for log in global_state.logs)


@pytest.mark.unit
class TestLoadHistory:
    """Tests for _load_history method."""

    def test_load_history_empty_directory(self, tmp_path):
        """Test loading history from empty directory."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = learner._load_history()

        assert sessions == []

    def test_load_history_with_sessions(self, tmp_path):
        """Test loading history with multiple session files."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        # Create mock session files
        for i in range(3):
            session_file = tmp_path / f"session_2024010{i}_120000.json"
            session_data = {
                "timestamp": f"2024-01-0{i}T12:00:00",
                "validation": {"is_valid": i % 2 == 0},
            }
            with open(session_file, "w") as f:
                json.dump(session_data, f)

        sessions = learner._load_history()

        assert len(sessions) == 3
        assert sessions[0]["validation"]["is_valid"] is True

    def test_load_history_handles_corrupted_files(self, tmp_path):
        """Test loading history skips corrupted JSON files."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        # Create valid session
        valid_session = tmp_path / "session_20240101_120000.json"
        with open(valid_session, "w") as f:
            json.dump({"validation": {"is_valid": True}}, f)

        # Create corrupted session
        corrupted_session = tmp_path / "session_20240102_120000.json"
        with open(corrupted_session, "w") as f:
            f.write("{ invalid json }")

        sessions = learner._load_history()

        # Should load only the valid session
        assert len(sessions) == 1


@pytest.mark.unit
class TestNormalizeIssueMessage:
    """Tests for _normalize_issue_message method."""

    def test_normalize_removes_quoted_values(self, tmp_path):
        """Test normalization removes quoted values."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        message = "Missing field 'experimenter'"
        normalized = learner._normalize_issue_message(message)

        assert normalized == "Missing field '...'"

    def test_normalize_removes_file_paths(self, tmp_path):
        """Test normalization removes file paths."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        message = "File not found: /path/to/file.nwb"
        normalized = learner._normalize_issue_message(message)

        assert "/..." in normalized
        assert "/path/to/file.nwb" not in normalized

    def test_normalize_replaces_numbers(self, tmp_path):
        """Test normalization replaces numbers with N."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        message = "Invalid timestamp 2024-01-01"
        normalized = learner._normalize_issue_message(message)

        assert "N-N-N" in normalized or "NNNN-NN-NN" in normalized

    def test_normalize_handles_complex_message(self, tmp_path):
        """Test normalization handles complex messages."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        message = "Error in '/data/file123.nwb' at line 456: Invalid value 'test123'"
        normalized = learner._normalize_issue_message(message)

        # Should normalize all components
        assert "..." in normalized
        assert "file123" not in normalized
        assert "456" not in normalized


@pytest.mark.unit
class TestIdentifyCommonIssues:
    """Tests for _identify_common_issues method."""

    def test_identify_common_issues_empty_sessions(self, tmp_path):
        """Test identifying common issues with no sessions."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        common = learner._identify_common_issues([])

        assert common == []

    def test_identify_common_issues_single_session(self, tmp_path):
        """Test identifying common issues with single session."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = [
            {
                "issues": [
                    {"message": "Missing experimenter", "severity": "ERROR"},
                    {"message": "Missing institution", "severity": "WARNING"},
                ]
            }
        ]

        common = learner._identify_common_issues(sessions)

        assert len(common) == 2
        assert common[0]["occurrence_count"] == 1

    def test_identify_common_issues_counts_across_sessions(self, tmp_path):
        """Test identifying common issues counts across multiple sessions."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = [
            {
                "issues": [
                    {"message": "Missing experimenter", "severity": "ERROR"},
                    {"message": "Missing institution", "severity": "WARNING"},
                ]
            },
            {
                "issues": [
                    {"message": "Missing experimenter", "severity": "ERROR"},
                ]
            },
            {
                "issues": [
                    {"message": "Missing experimenter", "severity": "ERROR"},
                ]
            },
        ]

        common = learner._identify_common_issues(sessions)

        # "Missing experimenter" should be most common
        assert common[0]["issue_pattern"] == "Missing experimenter"
        assert common[0]["occurrence_count"] == 3
        assert common[0]["percentage"] == 100.0


@pytest.mark.unit
class TestAnalyzeFormatSpecificIssues:
    """Tests for _analyze_format_specific_issues method."""

    def test_analyze_format_issues_groups_by_format(self, tmp_path):
        """Test analyzing format-specific issues groups by format."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = [
            {
                "file_info": {"format": "SpikeGLX"},
                "issues": [{"message": "Missing metadata"}],
            },
            {
                "file_info": {"format": "OpenEphys"},
                "issues": [{"message": "Invalid channel"}],
            },
        ]

        format_issues = learner._analyze_format_specific_issues(sessions)

        assert "SpikeGLX" in format_issues
        assert "OpenEphys" in format_issues

    def test_analyze_format_issues_counts_occurrences(self, tmp_path):
        """Test analyzing format issues counts occurrences."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = [
            {
                "file_info": {"format": "SpikeGLX"},
                "issues": [{"message": "Missing metadata"}],
            },
            {
                "file_info": {"format": "SpikeGLX"},
                "issues": [{"message": "Missing metadata"}],
            },
        ]

        format_issues = learner._analyze_format_specific_issues(sessions)

        assert format_issues["SpikeGLX"][0]["count"] == 2


@pytest.mark.unit
class TestAnalyzeSuccessPatterns:
    """Tests for _analyze_success_patterns method."""

    def test_analyze_success_patterns_file_size(self, tmp_path):
        """Test analyzing success patterns for file size."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = [
            {
                "file_info": {"size_mb": 100},
                "validation": {"is_valid": True},
            },
            {
                "file_info": {"size_mb": 150},
                "validation": {"is_valid": True},
            },
        ]

        patterns = learner._analyze_success_patterns(sessions)

        # Should include average file size pattern
        assert any("File size" in p["pattern"] for p in patterns)

    def test_analyze_success_patterns_format_success_rate(self, tmp_path):
        """Test analyzing success patterns for format success rates."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = [
            {
                "file_info": {"format": "SpikeGLX"},
                "validation": {"is_valid": True},
            },
            {
                "file_info": {"format": "SpikeGLX"},
                "validation": {"is_valid": True},
            },
            {
                "file_info": {"format": "SpikeGLX"},
                "validation": {"is_valid": False},
            },
        ]

        patterns = learner._analyze_success_patterns(sessions)

        # Should include format success rate
        spikeglx_pattern = [p for p in patterns if "SpikeGLX" in p["pattern"]]
        assert len(spikeglx_pattern) > 0
        assert "67%" in spikeglx_pattern[0]["observation"] or "66%" in spikeglx_pattern[0]["observation"]


@pytest.mark.unit
class TestBasicRecommendations:
    """Tests for _basic_recommendations method."""

    def test_basic_recommendations_for_missing_issues(self, tmp_path):
        """Test basic recommendations for missing field issues."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        common_issues = [
            {"issue_pattern": "missing experimenter", "percentage": 75.0}
        ]

        recommendations = learner._basic_recommendations(common_issues)

        assert len(recommendations) > 0
        assert "verify" in recommendations[0].lower()
        assert "75" in recommendations[0]

    def test_basic_recommendations_for_invalid_issues(self, tmp_path):
        """Test basic recommendations for invalid format issues."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        common_issues = [
            {"issue_pattern": "invalid timestamp", "percentage": 50.0}
        ]

        recommendations = learner._basic_recommendations(common_issues)

        assert len(recommendations) > 0
        assert "validate" in recommendations[0].lower()


@pytest.mark.unit
class TestAnalyzePatterns:
    """Tests for analyze_patterns method."""

    @pytest.mark.asyncio
    async def test_analyze_patterns_insufficient_history(self, tmp_path, global_state):
        """Test analyzing patterns with insufficient history."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        # Create only 1 session (need at least 2)
        session_file = tmp_path / "session_20240101_120000.json"
        with open(session_file, "w") as f:
            json.dump({"validation": {"is_valid": True}, "issues": []}, f)

        result = await learner.analyze_patterns(global_state)

        assert result["common_issues"] == []
        assert "Insufficient history" in result["note"]

    @pytest.mark.asyncio
    async def test_analyze_patterns_with_llm(self, tmp_path, global_state):
        """Test analyzing patterns with LLM service."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "preventive_recommendations": [
                    {
                        "recommendation": "Always verify experimenter field",
                        "rationale": "Most common missing field",
                        "applies_to": "All formats",
                        "priority": "high",
                    }
                ],
                "key_insights": ["Metadata issues are most common"],
            }
        )

        learner = ValidationHistoryLearner(llm_service=llm_service, history_path=str(tmp_path))

        # Create multiple sessions
        for i in range(3):
            session_file = tmp_path / f"session_2024010{i}_120000.json"
            with open(session_file, "w") as f:
                json.dump({
                    "file_info": {"format": "NWB", "size_mb": 100},
                    "validation": {"is_valid": i % 2 == 0},
                    "issues": [{"message": "Missing experimenter", "severity": "ERROR"}],
                }, f)

        result = await learner.analyze_patterns(global_state)

        assert len(result["preventive_recommendations"]) > 0
        assert result["total_sessions"] == 3

    @pytest.mark.asyncio
    async def test_analyze_patterns_without_llm_fallback(self, tmp_path, global_state):
        """Test analyzing patterns without LLM uses basic recommendations."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        # Create multiple sessions
        for i in range(2):
            session_file = tmp_path / f"session_2024010{i}_120000.json"
            with open(session_file, "w") as f:
                json.dump({
                    "file_info": {"format": "NWB"},
                    "validation": {"is_valid": False},
                    "issues": [{"message": "Missing experimenter", "severity": "ERROR"}],
                }, f)

        result = await learner.analyze_patterns(global_state)

        assert "preventive_recommendations" in result
        assert len(result["common_issues"]) > 0


@pytest.mark.unit
class TestFindSimilarSessions:
    """Tests for _find_similar_sessions method."""

    def test_find_similar_by_format(self, tmp_path):
        """Test finding similar sessions by format."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = [
            {"file_info": {"format": "SpikeGLX", "size_mb": 100}},
            {"file_info": {"format": "OpenEphys", "size_mb": 50}},  # Size outside match range
            {"file_info": {"format": "SpikeGLX", "size_mb": 200}},
        ]

        file_context = {"format": "SpikeGLX", "file_size_mb": 150}

        similar = learner._find_similar_sessions(file_context, sessions)

        # Should find both SpikeGLX sessions
        assert len(similar) == 2

    def test_find_similar_by_size(self, tmp_path):
        """Test finding similar sessions by size."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        sessions = [
            {"file_info": {"format": "NWB", "size_mb": 100}},
            {"file_info": {"format": "NWB", "size_mb": 150}},
            {"file_info": {"format": "NWB", "size_mb": 1000}},
        ]

        file_context = {"format": "", "file_size_mb": 120}

        similar = learner._find_similar_sessions(file_context, sessions)

        # Should find sessions with similar size (within 50%)
        assert len(similar) >= 2


@pytest.mark.unit
class TestExtractCommonIssuesFromSimilar:
    """Tests for _extract_common_issues_from_similar method."""

    def test_extract_issues_calculates_likelihood(self, tmp_path):
        """Test extracting common issues calculates likelihood."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        similar_sessions = [
            {
                "issues": [
                    {"message": "Missing experimenter"},
                    {"message": "Missing institution"},
                ]
            },
            {
                "issues": [
                    {"message": "Missing experimenter"},
                ]
            },
        ]

        issues = learner._extract_common_issues_from_similar(similar_sessions)

        # "Missing experimenter" appears in 2/2 sessions = 100%
        assert issues[0]["likelihood_percent"] == 100.0


@pytest.mark.unit
class TestPredictIssues:
    """Tests for predict_issues method."""

    @pytest.mark.asyncio
    async def test_predict_issues_insufficient_history(self, tmp_path, global_state):
        """Test predicting issues with insufficient history."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        # Create only 2 sessions (need at least 3)
        for i in range(2):
            session_file = tmp_path / f"session_2024010{i}_120000.json"
            with open(session_file, "w") as f:
                json.dump({"validation": {"is_valid": True}}, f)

        result = await learner.predict_issues(
            file_context={"format": "NWB"},
            state=global_state,
        )

        assert "Insufficient history" in result["note"]

    @pytest.mark.asyncio
    async def test_predict_issues_with_llm(self, tmp_path, global_state):
        """Test predicting issues with LLM service."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "predictions": [
                    {
                        "predicted_issue": "Missing experimenter",
                        "confidence_percent": 85,
                        "reasoning": "Common in SpikeGLX files",
                        "preventive_action": "Verify experimenter field before conversion",
                    }
                ]
            }
        )

        learner = ValidationHistoryLearner(llm_service=llm_service, history_path=str(tmp_path))

        # Create similar sessions
        for i in range(3):
            session_file = tmp_path / f"session_2024010{i}_120000.json"
            with open(session_file, "w") as f:
                json.dump({
                    "file_info": {"format": "SpikeGLX", "size_mb": 100},
                    "issues": [{"message": "Missing experimenter"}],
                }, f)

        result = await learner.predict_issues(
            file_context={"format": "SpikeGLX", "file_size_mb": 100},
            state=global_state,
        )

        assert len(result["likely_issues"]) > 0
        assert result["likely_issues"][0]["confidence_percent"] == 85

    @pytest.mark.asyncio
    async def test_predict_issues_without_llm_fallback(self, tmp_path, global_state):
        """Test predicting issues without LLM uses basic predictions."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        # Create sessions
        for i in range(3):
            session_file = tmp_path / f"session_2024010{i}_120000.json"
            with open(session_file, "w") as f:
                json.dump({
                    "file_info": {"format": "NWB", "size_mb": 100},
                    "issues": [{"message": "Missing metadata"}],
                }, f)

        result = await learner.predict_issues(
            file_context={"format": "NWB", "file_size_mb": 100},
            state=global_state,
        )

        assert "likely_issues" in result
        assert "preventive_actions" in result


@pytest.mark.unit
class TestValidationHistoryLearnerIntegration:
    """Integration tests for complete validation history learning workflow."""

    @pytest.mark.asyncio
    async def test_complete_learning_workflow(self, tmp_path, global_state):
        """Test complete workflow: record → analyze → predict."""
        learner = ValidationHistoryLearner(history_path=str(tmp_path))

        # Step 1: Record multiple validation sessions
        for i in range(3):
            validation_result = ValidationResult(
                is_valid=i % 2 == 0,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message="Missing experimenter",
                        check_function_name="check_experimenter",
                    )
                ],
                summary={"error": 1},
            )

            await learner.record_validation_session(
                validation_result=validation_result,
                file_context={"format": "SpikeGLX", "file_size_mb": 100},
                resolution_actions=[],
                state=global_state,
            )

            # Delay to ensure unique filenames (timestamp precision is 1 second)
            if i < 2:  # Don't delay after last iteration
                await asyncio.sleep(1.1)

        # Step 2: Analyze patterns
        patterns = await learner.analyze_patterns(global_state)

        assert patterns["total_sessions"] == 3
        assert len(patterns["common_issues"]) > 0

        # Step 3: Predict issues for similar file
        predictions = await learner.predict_issues(
            file_context={"format": "SpikeGLX", "file_size_mb": 100},
            state=global_state,
        )

        assert len(predictions["likely_issues"]) > 0
