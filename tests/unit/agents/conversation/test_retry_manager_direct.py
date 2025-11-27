"""Direct unit tests for RetryManager class.

Tests retry logic, error explanations, correction prompts, and auto-fix management
by directly instantiating and testing RetryManager (not via ConversationAgent).
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.conversation.retry_manager import RetryManager
from agentic_neurodata_conversion.services.llm_service import MockLLMService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def global_state_with_species(global_state):
    """GlobalState with auto-extracted species metadata."""
    global_state.auto_extracted_metadata["species"] = "Mus musculus"
    return global_state


@pytest.fixture
def sample_validation_issues():
    """Sample validation issues for testing."""
    return [
        {
            "severity": "CRITICAL",
            "check_name": "check_session_description",
            "message": "Missing required field: session_description",
            "location": "/",
        },
        {
            "severity": "ERROR",
            "check_name": "check_experimenter",
            "message": "Missing required field: experimenter",
            "location": "/",
        },
        {
            "severity": "WARNING",
            "check_name": "check_keywords",
            "message": "Missing optional field: keywords",
            "location": "/",
        },
    ]


# ============================================================================
# Initialization Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestRetryManagerInit:
    """Test RetryManager initialization."""

    def test_init_without_services(self):
        """Test initialization without LLM service or metadata mapper."""
        manager = RetryManager()

        assert manager._llm_service is None
        assert manager._metadata_mapper is None

    def test_init_with_llm_service(self):
        """Test initialization with LLM service."""
        llm_service = MockLLMService()
        manager = RetryManager(llm_service=llm_service)

        assert manager._llm_service is llm_service
        assert manager._metadata_mapper is None

    def test_init_with_both_services(self):
        """Test initialization with both LLM service and metadata mapper."""
        llm_service = MockLLMService()
        metadata_mapper = Mock()
        manager = RetryManager(llm_service=llm_service, metadata_mapper=metadata_mapper)

        assert manager._llm_service is llm_service
        assert manager._metadata_mapper is metadata_mapper


# ============================================================================
# Error Explanation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExplainErrorToUser:
    """Test error explanation functionality."""

    @pytest.mark.asyncio
    async def test_without_llm_returns_fallback(self, global_state):
        """Test fallback error explanation without LLM."""
        manager = RetryManager()

        error = {"message": "Conversion failed", "code": "CONV_ERROR"}
        context = {"format": "SpikeGLX", "input_path": "/test/file.bin"}

        result = await manager.explain_error_to_user(error, context, global_state)

        assert result["explanation"] == "Conversion failed"
        assert result["likely_cause"] == "Unknown"
        assert isinstance(result["suggested_actions"], list)
        assert len(result["suggested_actions"]) == 2
        assert "logs" in result["suggested_actions"][0].lower()
        assert result["is_recoverable"] is False

    @pytest.mark.asyncio
    async def test_without_llm_missing_error_message(self, global_state):
        """Test fallback when error has no message."""
        manager = RetryManager()

        error = {"code": "UNKNOWN_ERROR"}  # No message
        context = {"format": "unknown"}

        result = await manager.explain_error_to_user(error, context, global_state)

        assert result["explanation"] == "An error occurred during conversion"
        assert result["is_recoverable"] is False

    @pytest.mark.asyncio
    async def test_with_llm_success(self, global_state):
        """Test successful LLM-based error explanation."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "explanation": "The file format could not be detected",
                "likely_cause": "Invalid file structure",
                "suggested_actions": ["Check file integrity", "Try different format"],
                "is_recoverable": True,
                "help_url": "https://docs.example.com/errors",
            }
        )

        manager = RetryManager(llm_service=llm_service)
        error = {"message": "Format detection failed", "code": "DETECTION_ERROR"}
        context = {"format": "unknown", "input_path": "/test/data.bin", "operation": "format_detection"}

        result = await manager.explain_error_to_user(error, context, global_state)

        assert "format" in result["explanation"].lower()
        assert result["likely_cause"] == "Invalid file structure"
        assert result["is_recoverable"] is True
        assert len(result["suggested_actions"]) == 2
        assert result["help_url"] == "https://docs.example.com/errors"
        llm_service.generate_structured_output.assert_called_once()

        # Verify LLM was called with correct prompt structure
        call_args = llm_service.generate_structured_output.call_args
        assert "Format detection failed" in call_args.kwargs["prompt"]
        assert "DETECTION_ERROR" in call_args.kwargs["prompt"]
        assert "output_schema" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_with_llm_logs_success(self, global_state):
        """Test that successful LLM explanation is logged."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "explanation": "Test explanation",
                "likely_cause": "Test cause",
                "suggested_actions": ["Action 1"],
                "is_recoverable": False,
            }
        )

        manager = RetryManager(llm_service=llm_service)
        error = {"message": "Test error", "code": "TEST_ERROR"}
        context = {}

        await manager.explain_error_to_user(error, context, global_state)

        # Check that success was logged
        logs = global_state.logs
        success_logs = [log for log in logs if "error explanation" in log.message.lower()]
        assert len(success_logs) > 0

    @pytest.mark.asyncio
    async def test_with_llm_failure_falls_back(self, global_state):
        """Test fallback when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM service unavailable"))

        manager = RetryManager(llm_service=llm_service)
        error = {"message": "Conversion error", "code": "CONV_FAIL"}
        context = {"format": "SpikeGLX"}

        result = await manager.explain_error_to_user(error, context, global_state)

        # Should fall back to basic explanation
        assert result["explanation"] == "Conversion error"
        assert result["likely_cause"] == "See logs for technical details"
        assert "logs" in result["suggested_actions"][0].lower()
        assert result["is_recoverable"] is False

        # Verify error was logged
        logs = global_state.logs
        error_logs = [log for log in logs if log.level == "error"]
        assert len(error_logs) > 0
        assert "Failed to generate error explanation" in error_logs[0].message

    @pytest.mark.asyncio
    async def test_with_llm_timeout_falls_back(self, global_state):
        """Test fallback when LLM times out."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=TimeoutError("Request timeout"))

        manager = RetryManager(llm_service=llm_service)
        error = {"message": "Timeout error", "code": "TIMEOUT"}
        context = {}

        result = await manager.explain_error_to_user(error, context, global_state)

        assert result["explanation"] == "Timeout error"
        assert result["is_recoverable"] is False


# ============================================================================
# Correction Prompt Generation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateCorrectionPrompts:
    """Test correction prompt generation."""

    @pytest.mark.asyncio
    async def test_without_llm_uses_basic_prompts(self, global_state, sample_validation_issues):
        """Test basic correction prompts without LLM."""
        manager = RetryManager()

        result = await manager.generate_correction_prompts(sample_validation_issues, {}, global_state)

        assert "⚠️" in result
        assert "3 warnings" in result
        assert "check_session_description" in result
        assert "check_experimenter" in result
        assert "Please provide the requested information" in result

    @pytest.mark.asyncio
    async def test_without_llm_empty_issues(self, global_state):
        """Test basic prompts with no issues."""
        manager = RetryManager()

        result = await manager.generate_correction_prompts([], {}, global_state)

        assert "0 warnings" in result

    @pytest.mark.asyncio
    async def test_with_llm_success(self, global_state, sample_validation_issues):
        """Test LLM-based correction prompts."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "message": "Let's fix these validation issues:\n\n1. Add session description\n2. Add experimenter name",
                "required_fields": ["session_description", "experimenter"],
            }
        )

        manager = RetryManager(llm_service=llm_service)
        context = {"format": "SpikeGLX", "total_issues": 3}

        result = await manager.generate_correction_prompts(sample_validation_issues, context, global_state)

        assert "validation issues" in result.lower()
        assert "session description" in result.lower()
        llm_service.generate_structured_output.assert_called_once()

        # Verify LLM prompt includes issue counts
        call_args = llm_service.generate_structured_output.call_args
        prompt = call_args.kwargs["prompt"]
        assert "Critical Issues (2)" in prompt
        assert "Warnings (1)" in prompt

    @pytest.mark.asyncio
    async def test_with_llm_groups_by_severity(self, global_state):
        """Test that issues are grouped by severity for LLM."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(return_value={"message": "Test prompt"})

        issues = [
            {"severity": "CRITICAL", "message": "Critical 1", "location": "/"},
            {"severity": "WARNING", "message": "Warning 1", "location": "/"},
            {"severity": "ERROR", "message": "Error 1", "location": "/"},
            {"severity": "CRITICAL", "message": "Critical 2", "location": "/"},
        ]

        manager = RetryManager(llm_service=llm_service)
        await manager.generate_correction_prompts(issues, {}, global_state)

        # Verify grouping in prompt
        call_args = llm_service.generate_structured_output.call_args
        prompt = call_args.kwargs["prompt"]
        assert "Critical Issues (3)" in prompt  # 2 CRITICAL + 1 ERROR
        assert "Warnings (1)" in prompt

    @pytest.mark.asyncio
    async def test_with_llm_failure_falls_back(self, global_state, sample_validation_issues):
        """Test fallback when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM error"))

        manager = RetryManager(llm_service=llm_service)

        result = await manager.generate_correction_prompts(sample_validation_issues, {}, global_state)

        # Should fall back to basic prompts
        assert "⚠️" in result
        assert "3 warnings" in result

        # Verify warning was logged
        logs = global_state.logs
        warning_logs = [log for log in logs if log.level == "warning"]
        assert any("Failed to generate LLM correction prompt" in log.message for log in warning_logs)


# ============================================================================
# Basic Correction Prompts Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateBasicCorrectionPrompts:
    """Test basic correction prompt generation (static method)."""

    def test_empty_issues(self):
        """Test with no issues."""
        result = RetryManager._generate_basic_correction_prompts([])

        assert "0 warnings" in result
        assert "⚠️" in result

    def test_single_issue(self):
        """Test with single issue."""
        issues = [{"check_name": "check_experimenter", "message": "Missing experimenter field"}]

        result = RetryManager._generate_basic_correction_prompts(issues)

        assert "1 warnings" in result
        assert "check_experimenter" in result
        assert "Missing experimenter field" in result
        assert "1." in result

    def test_multiple_issues(self):
        """Test with multiple issues."""
        issues = [
            {"check_name": "check_1", "message": "Message 1"},
            {"check_name": "check_2", "message": "Message 2"},
            {"check_name": "check_3", "message": "Message 3"},
        ]

        result = RetryManager._generate_basic_correction_prompts(issues)

        assert "3 warnings" in result
        assert "check_1" in result
        assert "check_2" in result
        assert "check_3" in result
        assert "1." in result
        assert "2." in result
        assert "3." in result

    def test_missing_check_name(self):
        """Test issue with missing check_name."""
        issues = [{"message": "Some message"}]  # No check_name

        result = RetryManager._generate_basic_correction_prompts(issues)

        assert "Unknown" in result
        assert "Some message" in result


# ============================================================================
# Auto-Fix Identification Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestIdentifyUserInputRequired:
    """Test user input identification."""

    def test_empty_corrections(self):
        """Test with empty corrections dict."""
        manager = RetryManager()

        result = manager.identify_user_input_required({})

        assert result == []

    def test_no_user_required_key(self):
        """Test when user_required key is missing."""
        manager = RetryManager()

        result = manager.identify_user_input_required({"auto_fixes": []})

        assert result == []

    def test_with_user_required_items(self):
        """Test extracting user-required items."""
        manager = RetryManager()
        corrections = {
            "user_required": [
                {"field": "session_description", "message": "Please provide session description"},
                {"field": "keywords", "message": "Please provide keywords"},
            ],
            "auto_fixes": [],
        }

        result = manager.identify_user_input_required(corrections)

        assert len(result) == 2
        assert result[0]["field"] == "session_description"
        assert result[1]["field"] == "keywords"


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractAutoFixes:
    """Test auto-fix extraction."""

    def test_empty_corrections(self):
        """Test with empty corrections dict."""
        manager = RetryManager()

        result = manager.extract_auto_fixes({})

        assert result == {}

    def test_no_auto_fixes_key(self):
        """Test when auto_fixes key is missing."""
        manager = RetryManager()

        result = manager.extract_auto_fixes({"user_required": []})

        assert result == {}

    def test_with_auto_fixes(self):
        """Test extracting auto-fixes."""
        manager = RetryManager()
        corrections = {
            "auto_fixes": {"experimenter": "Unknown, Researcher", "institution": "Unknown Institution"},
            "user_required": [],
        }

        result = manager.extract_auto_fixes(corrections)

        assert result == {"experimenter": "Unknown, Researcher", "institution": "Unknown Institution"}


# ============================================================================
# Auto-Fix Summary Generation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateAutoFixSummary:
    """Test auto-fix summary generation."""

    def test_empty_issues(self):
        """Test with no issues."""
        manager = RetryManager()

        result = manager.generate_auto_fix_summary([])

        assert result == "No auto-fixable issues found."

    def test_single_issue(self):
        """Test with single issue."""
        manager = RetryManager()
        issues = [{"message": "Missing experimenter", "fix": {"field": "experimenter", "value": "Unknown, Researcher"}}]

        result = manager.generate_auto_fix_summary(issues)

        assert "📝" in result
        assert "Auto-Fix Summary" in result
        assert "(1 issues)" in result
        assert "experimenter" in result
        assert "Unknown, Researcher" in result
        assert "Approve these fixes?" in result

    def test_multiple_issues_under_ten(self):
        """Test with multiple issues (< 10)."""
        manager = RetryManager()
        issues = [{"message": f"Issue {i}", "fix": {"field": f"field_{i}", "value": f"value_{i}"}} for i in range(5)]

        result = manager.generate_auto_fix_summary(issues)

        assert "(5 issues)" in result
        for i in range(5):
            assert f"field_{i}" in result
            assert f"value_{i}" in result
        assert "... and" not in result  # No truncation

    def test_many_issues_truncates(self):
        """Test with > 10 issues (should truncate)."""
        manager = RetryManager()
        issues = [{"message": f"Issue {i}", "fix": {"field": f"field_{i}", "value": f"value_{i}"}} for i in range(15)]

        result = manager.generate_auto_fix_summary(issues)

        assert "(15 issues)" in result
        assert "... and 5 more issues" in result

        # First 10 should be shown
        for i in range(10):
            assert f"field_{i}" in result

        # Last 5 should not be shown
        for i in range(10, 15):
            assert f"field_{i}" not in result

    def test_issue_missing_fix_dict(self):
        """Test issue with missing fix dict."""
        manager = RetryManager()
        issues = [{"message": "Some issue"}]  # No fix dict

        result = manager.generate_auto_fix_summary(issues)

        assert "unknown" in result
        assert "N/A" in result

    def test_fix_missing_field_or_value(self):
        """Test fix dict with missing field or value."""
        manager = RetryManager()
        issues = [{"message": "Issue 1", "fix": {}}]  # Empty fix dict

        result = manager.generate_auto_fix_summary(issues)

        assert "unknown" in result
        assert "N/A" in result


# ============================================================================
# Fix Extraction from Issues Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractFixesFromIssues:
    """Test fix extraction from validation issues."""

    def test_empty_issues(self, global_state):
        """Test with no issues."""
        manager = RetryManager()

        result = manager.extract_fixes_from_issues([], global_state)

        assert result == {}

    def test_single_inferable_issue(self, global_state):
        """Test with single inferable issue."""
        manager = RetryManager()
        issues = [{"message": "Missing required field: experimenter", "location": "/"}]

        result = manager.extract_fixes_from_issues(issues, global_state)

        assert "experimenter" in result
        assert result["experimenter"] == "Unknown, Researcher"

    def test_multiple_inferable_issues(self, global_state):
        """Test with multiple inferable issues."""
        manager = RetryManager()
        issues = [
            {"message": "Missing required field: experimenter", "location": "/"},
            {"message": "Missing required field: institution", "location": "/"},
            {"message": "Missing subject sex", "location": "/subject"},
        ]

        result = manager.extract_fixes_from_issues(issues, global_state)

        assert len(result) == 3
        assert result["experimenter"] == "Unknown, Researcher"
        assert result["institution"] == "Unknown Institution"
        assert result["sex"] == "U"

    def test_issues_with_no_inferable_fixes(self, global_state):
        """Test issues that cannot be auto-fixed."""
        manager = RetryManager()
        issues = [
            {"message": "Invalid timestamp format", "location": "/"},
            {"message": "Data array has wrong shape", "location": "/data"},
        ]

        result = manager.extract_fixes_from_issues(issues, global_state)

        assert result == {}


# ============================================================================
# Fix Inference Pattern Matching Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestInferFixFromIssue:
    """Test fix inference from single issue."""

    def test_experimenter_pattern(self, global_state):
        """Test experimenter field pattern matching."""
        manager = RetryManager()
        issue = {"message": "Missing required field: experimenter", "location": "/"}

        result = manager._infer_fix_from_issue(issue, global_state)

        assert result is not None
        assert result["field"] == "experimenter"
        assert result["value"] == "Unknown, Researcher"

    def test_institution_pattern(self, global_state):
        """Test institution field pattern matching."""
        manager = RetryManager()
        issue = {"message": "Missing required field: institution", "location": "/"}

        result = manager._infer_fix_from_issue(issue, global_state)

        assert result is not None
        assert result["field"] == "institution"
        assert result["value"] == "Unknown Institution"

    def test_sex_pattern(self, global_state):
        """Test sex field pattern matching."""
        manager = RetryManager()
        issue = {"message": "Missing subject sex information", "location": "/subject"}

        result = manager._infer_fix_from_issue(issue, global_state)

        assert result is not None
        assert result["field"] == "sex"
        assert result["value"] == "U"  # Unknown

    def test_species_pattern_with_state_metadata(self, global_state_with_species):
        """Test species pattern with auto-extracted metadata."""
        manager = RetryManager()
        issue = {"message": "Missing species information", "location": "/subject"}

        result = manager._infer_fix_from_issue(issue, global_state_with_species)

        assert result is not None
        assert result["field"] == "species"
        assert result["value"] == "Mus musculus"

    def test_species_pattern_without_state_metadata(self, global_state):
        """Test species pattern without auto-extracted metadata."""
        manager = RetryManager()
        issue = {"message": "Missing species field", "location": "/subject"}

        result = manager._infer_fix_from_issue(issue, global_state)

        # Should return None because no species in state
        assert result is None

    def test_unrecognized_pattern(self, global_state):
        """Test issue that doesn't match any pattern."""
        manager = RetryManager()
        issue = {"message": "Invalid data format in acquisition", "location": "/acquisition"}

        result = manager._infer_fix_from_issue(issue, global_state)

        assert result is None

    def test_case_insensitive_matching(self, global_state):
        """Test that pattern matching is case-insensitive."""
        manager = RetryManager()
        issue = {"message": "MISSING REQUIRED FIELD: EXPERIMENTER", "location": "/"}

        result = manager._infer_fix_from_issue(issue, global_state)

        assert result is not None
        assert result["field"] == "experimenter"

    def test_missing_message_field(self, global_state):
        """Test issue with missing message field."""
        manager = RetryManager()
        issue = {"location": "/"}  # No message

        result = manager._infer_fix_from_issue(issue, global_state)

        assert result is None

    def test_partial_keyword_match(self, global_state):
        """Test that 'missing' and 'experimenter' both need to be present."""
        manager = RetryManager()

        # Has 'experimenter' but not 'missing'
        issue1 = {"message": "Invalid experimenter format", "location": "/"}
        result1 = manager._infer_fix_from_issue(issue1, global_state)
        assert result1 is None

        # Has 'missing' but not 'experimenter'
        issue2 = {"message": "Missing some other field", "location": "/"}
        result2 = manager._infer_fix_from_issue(issue2, global_state)
        assert result2 is None

        # Has both
        issue3 = {"message": "Missing experimenter field", "location": "/"}
        result3 = manager._infer_fix_from_issue(issue3, global_state)
        assert result3 is not None
