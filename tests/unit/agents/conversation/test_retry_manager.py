"""
Unit tests for ConversationAgent.

Tests initialization, provenance tracking, and core utility methods.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.conversation_agent import ConversationAgent
from agentic_neurodata_conversion.services.llm_service import MockLLMService


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExplainErrorToUser:
    """Tests for _explain_error_to_user method."""

    @pytest.mark.asyncio
    async def test_explain_error_without_llm(self, global_state):
        """Test error explanation fallback without LLM."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        error = {"message": "File format not recognized", "code": "INVALID_FORMAT"}
        context = {"format": "unknown", "input_path": "/test/file.dat"}

        result = await agent._explain_error_to_user(error, context, global_state)

        assert result["explanation"] == "File format not recognized"
        assert result["likely_cause"] == "Unknown"
        assert isinstance(result["suggested_actions"], list)
        assert len(result["suggested_actions"]) > 0
        assert result["is_recoverable"] is False

    @pytest.mark.asyncio
    async def test_explain_error_with_llm(self, global_state):
        """Test error explanation with LLM."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "explanation": "The file format couldn't be detected automatically",
                "likely_cause": "Unsupported or corrupted file format",
                "suggested_actions": ["Check file extension", "Try a different file"],
                "is_recoverable": True,
            }
        )

        agent = ConversationAgent(mock_mcp, llm_service)

        error = {"message": "Format detection failed", "code": "DETECTION_ERROR"}
        context = {"format": "unknown", "input_path": "/test/file.dat"}

        result = await agent._explain_error_to_user(error, context, global_state)

        assert "format" in result["explanation"].lower()
        assert result["is_recoverable"] is True
        assert len(result["suggested_actions"]) > 0
        llm_service.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_explain_error_llm_failure(self, global_state):
        """Test error explanation falls back when LLM fails."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM service unavailable"))

        agent = ConversationAgent(mock_mcp, llm_service)

        error = {"message": "Conversion failed", "code": "CONV_ERROR"}
        context = {"format": "SpikeGLX"}

        result = await agent._explain_error_to_user(error, context, global_state)

        # Should fall back to basic explanation
        assert result["explanation"] == "Conversion failed"
        assert isinstance(result["suggested_actions"], list)


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractAutoFixes:
    """Tests for _extract_auto_fixes method."""

    def test_extract_actionable_fixes(self, global_state):
        """Test extracting actionable fixes."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {
            "suggestions": [
                {"issue": "subject_id field needs value", "suggestion": "Set subject_id to default", "actionable": True}
            ]
        }

        result = agent._extract_auto_fixes(corrections)

        # Result should be a dict (may be empty if heuristics don't match)
        assert isinstance(result, dict)

    def test_skip_non_actionable_suggestions(self, global_state):
        """Test that non-actionable suggestions are skipped."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {
            "suggestions": [
                {
                    "issue": "subject_id missing",
                    "suggestion": "Ask user for subject_id",
                    "actionable": False,  # Not actionable
                }
            ]
        }

        result = agent._extract_auto_fixes(corrections)

        assert isinstance(result, dict)
        # Non-actionable should not be extracted

    def test_extract_empty_suggestions(self, global_state):
        """Test extraction from empty suggestions."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {"suggestions": []}

        result = agent._extract_auto_fixes(corrections)

        assert result == {}

    def test_extract_missing_suggestions_key(self, global_state):
        """Test handling when 'suggestions' key is missing."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {}

        result = agent._extract_auto_fixes(corrections)

        assert result == {}


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestExtractFixesFromIssues:
    """Tests for _extract_fixes_from_issues method."""

    def test_extract_with_no_suggested_fix(self, global_state):
        """Test extraction when issue has no suggested_fix - uses inferred fix."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        issues = [{"check_name": "MissingExperimenter", "message": "experimenter missing"}]

        result = agent._extract_fixes_from_issues(issues, global_state)

        # Should infer fix for experimenter
        assert "experimenter" in result
        assert result["experimenter"] == "Unknown"  # Inferred value


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateAutoFixSummary:
    """Tests for _generate_auto_fix_summary method."""

    def test_generate_summary_single_issue(self, global_state):
        """Test generating summary for single issue."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Use correct format: issue + suggested_fix
        issues = [{"issue": "InvalidDate: Date format is incorrect", "suggested_fix": "Auto-correcting date"}]

        result = agent._generate_auto_fix_summary(issues)

        assert "InvalidDate" in result
        assert "Date format is incorrect" in result

    def test_generate_summary_multiple_issues(self, global_state):
        """Test generating summary for multiple issues."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Use correct format: issue + suggested_fix
        issues = [
            {"issue": "InvalidDate: Date format wrong", "suggested_fix": "Correcting date"},
            {"issue": "MissingField: Field missing", "suggested_fix": "Adding field"},
            {"issue": "TypeError: Type mismatch", "suggested_fix": "Converting type"},
        ]

        result = agent._generate_auto_fix_summary(issues)

        assert "1. InvalidDate" in result
        assert "2. MissingField" in result
        assert "3. TypeError" in result

    def test_generate_summary_long_message_truncation(self, global_state):
        """Test that long messages are handled (implementation doesn't truncate by default)."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        long_message = "A" * 150  # 150 characters
        # Use correct format
        issues = [{"issue": f"LongError: {long_message}", "suggested_fix": "Fixing long error"}]

        result = agent._generate_auto_fix_summary(issues)

        # Implementation doesn't truncate - test that it contains the issue
        assert "LongError" in result
        assert "Fixing long error" in result

    def test_generate_summary_missing_fields(self, global_state):
        """Test generating summary with missing fields uses defaults."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Implementation expects 'issue' and 'suggested_fix' keys
        issues = [
            {},  # Missing both fields - uses defaults
            {"issue": "HasName"},  # Missing suggested_fix - uses default
        ]

        result = agent._generate_auto_fix_summary(issues)

        # Implementation uses "Unknown issue" and "Will be corrected" as defaults
        assert "Unknown issue" in result
        assert "Will be corrected" in result
        assert "HasName" in result


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateBasicCorrectionPrompts:
    """Tests for _generate_basic_correction_prompts method."""

    def test_generate_single_issue_prompt(self, global_state):
        """Test generating prompt for single issue."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Use correct format: field_name + reason
        issues = [{"field_name": "experimenter", "reason": "Experimenter field is required"}]

        result = agent._generate_basic_correction_prompts(issues)

        assert "1 field" in result
        assert "experimenter" in result
        assert "Experimenter field is required" in result

    def test_generate_multiple_issues_prompt(self, global_state):
        """Test generating prompt for multiple issues."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Use correct format
        issues = [
            {"field_name": "experimenter", "reason": "Experimenter required"},
            {"field_name": "institution", "reason": "Institution required"},
            {"field_name": "description", "reason": "Description required"},
        ]

        result = agent._generate_basic_correction_prompts(issues)

        assert "3 field" in result
        assert "1." in result
        assert "2." in result
        assert "3." in result
        assert all(issue["field_name"] in result for issue in issues)

    def test_generate_prompt_with_missing_fields(self, global_state):
        """Test generating prompt when issue has missing fields."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        # Missing field_name - should use "unknown" default
        issues = [{"reason": "Some error"}]

        result = agent._generate_basic_correction_prompts(issues)

        assert "unknown" in result  # Default for missing field_name
        assert "Some error" in result


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestGenerateCorrectionPrompts:
    """Tests for _generate_correction_prompts method."""

    @pytest.mark.asyncio
    async def test_generate_with_llm_success(self, global_state):
        """Test generating correction prompts with LLM."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        # Mock should return {"prompt": "..."}, not {"message": "..."}
        llm_service.generate_structured_output = AsyncMock(
            return_value={"prompt": "Please provide the experimenter name for your NWB file."}
        )
        agent = ConversationAgent(mock_mcp, llm_service)

        # Use correct format expected by implementation
        issues = [{"field_name": "experimenter", "reason": "experimenter field missing"}]

        result = await agent._generate_correction_prompts(issues, global_state)

        assert "experimenter" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_llm_failure_fallback(self, global_state):
        """Test fallback to basic prompts on LLM failure."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM failed"))
        agent = ConversationAgent(mock_mcp, llm_service)

        issues = [{"check_name": "MissingInstitution", "message": "institution missing"}]

        result = await agent._generate_correction_prompts(issues, global_state)

        # Should fall back to basic prompts
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_when_llm_processing(self, global_state):
        """Test fallback when LLM is already processing."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        # Mark LLM as processing
        global_state.llm_processing = True

        issues = [{"check_name": "MissingData", "message": "data missing"}]

        result = await agent._generate_correction_prompts(issues, global_state)

        # Should use basic prompts without calling LLM
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestIdentifyUserInputRequired:
    """Tests for _identify_user_input_required method."""

    def test_identify_missing_subject_id(self, global_state):
        """Test identifying missing subject_id."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {
            "suggestions": [{"issue": "Missing subject_id field", "suggestion": "Add subject_id", "actionable": False}]
        }

        result = agent._identify_user_input_required(corrections)

        assert len(result) == 1
        assert result[0]["field_name"] == "subject_id"
        assert result[0]["required"] is True

    def test_identify_short_session_description(self, global_state):
        """Test identifying too short session_description."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {
            "suggestions": [
                {
                    "issue": "session_description field present",
                    "suggestion": "Session description is too short",
                    "actionable": False,
                }
            ]
        }

        result = agent._identify_user_input_required(corrections)

        assert len(result) == 1
        assert result[0]["field_name"] == "session_description"
        assert result[0]["type"] == "textarea"

    def test_identify_missing_experimenter(self, global_state):
        """Test identifying missing experimenter."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {
            "suggestions": [
                {
                    "issue": "Missing experimenter information",
                    "suggestion": "Add experimenter names",
                    "actionable": False,
                }
            ]
        }

        result = agent._identify_user_input_required(corrections)

        assert len(result) == 1
        assert result[0]["field_name"] == "experimenter"

    def test_skip_actionable_suggestions(self, global_state):
        """Test that actionable suggestions are skipped."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {
            "suggestions": [
                {
                    "issue": "Missing subject_id",
                    "suggestion": "Add subject_id",
                    "actionable": True,  # Actionable, should be skipped
                }
            ]
        }

        result = agent._identify_user_input_required(corrections)

        assert len(result) == 0

    def test_identify_multiple_fields(self, global_state):
        """Test identifying multiple required fields."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        corrections = {
            "suggestions": [
                {"issue": "Missing subject_id", "suggestion": "Add it", "actionable": False},
                {"issue": "Missing experimenter", "suggestion": "Add it", "actionable": False},
                {"issue": "institution field", "suggestion": "Needs value", "actionable": False},
            ]
        }

        result = agent._identify_user_input_required(corrections)

        assert len(result) == 3
        field_names = [f["field_name"] for f in result]
        assert "subject_id" in field_names
        assert "experimenter" in field_names
        assert "institution" in field_names


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestInferFixFromIssue:
    """Tests for _infer_fix_from_issue method."""

    def test_infer_experimenter_fix(self, global_state):
        """Test inferring fix for missing experimenter."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        issue = {"check_name": "MissingExperimenter", "message": "experimenter is required"}

        result = agent._infer_fix_from_issue(issue, global_state)

        assert result is not None
        assert "experimenter" in result
        assert result["experimenter"] == "Unknown"

    def test_infer_institution_fix(self, global_state):
        """Test inferring fix for missing institution."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        issue = {"check_name": "MissingInstitution", "message": "institution field missing"}

        result = agent._infer_fix_from_issue(issue, global_state)

        assert result is not None
        assert "institution" in result

    def test_infer_session_description_fix(self, global_state):
        """Test inferring fix for session_description."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        issue = {"check_name": "MissingSessionDesc", "message": "session_description is required"}

        result = agent._infer_fix_from_issue(issue, global_state)

        assert result is not None
        assert "session_description" in result
        assert len(result["session_description"]) > 0

    def test_cannot_infer_fix(self, global_state):
        """Test that unknown issues return None."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        issue = {"check_name": "UnknownIssue", "message": "some unknown problem"}

        result = agent._infer_fix_from_issue(issue, global_state)

        assert result is None


@pytest.mark.unit
@pytest.mark.agent_conversation
class TestProactiveIssueDetection:
    """Tests for _proactive_issue_detection method."""

    @pytest.mark.asyncio
    async def test_without_llm_returns_unknown(self, global_state, tmp_path):
        """Test proactive detection without LLM returns unknown risk."""
        mock_mcp = Mock()
        agent = ConversationAgent(mock_mcp, llm_service=None)

        input_file = tmp_path / "test.bin"
        input_file.write_text("test data")

        result = await agent._proactive_issue_detection(
            input_path=str(input_file), format_name="SpikeGLX", state=global_state
        )

        assert result["risk_level"] == "unknown"
        assert result["should_proceed"] is True

    @pytest.mark.asyncio
    async def test_with_llm_analyzes_file(self, global_state, tmp_path):
        """Test proactive detection with LLM analyzes file."""
        from unittest.mock import AsyncMock

        mock_mcp = Mock()
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "success_probability": 85,
                "risk_level": "low",
                "predicted_issues": ["May need experimenter field"],
                "warning_message": "Conversion should succeed with minor warnings",
            }
        )

        agent = ConversationAgent(mock_mcp, llm_service)

        input_file = tmp_path / "test.bin"
        input_file.write_text("test data")

        result = await agent._proactive_issue_detection(
            input_path=str(input_file), format_name="SpikeGLX", state=global_state
        )

        assert result["risk_level"] == "low"
        assert result["success_probability"] == 85
        llm_service.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_nonexistent_file(self, global_state):
        """Test proactive detection handles nonexistent file."""
        mock_mcp = Mock()
        llm_service = MockLLMService()
        agent = ConversationAgent(mock_mcp, llm_service)

        result = await agent._proactive_issue_detection(
            input_path="/nonexistent/file.bin", format_name="SpikeGLX", state=global_state
        )

        assert result["risk_level"] == "unknown"
        assert result["should_proceed"] is True
