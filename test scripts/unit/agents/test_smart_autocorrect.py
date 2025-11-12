"""
Unit tests for SmartAutoCorrectionSystem.

Tests intelligent auto-correction of validation issues using LLM and fallback strategies.
"""

from unittest.mock import AsyncMock

import pytest
from agents.smart_autocorrect import SmartAutoCorrectionSystem
from services.llm_service import MockLLMService

# Note: The following fixtures are provided by conftest files:
# - global_state: from root conftest.py (Fresh GlobalState for each test)
# - mock_llm_service: from root conftest.py (Mock LLM service)


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestSmartAutoCorrectionSystemInitialization:
    """Tests for SmartAutoCorrectionSystem initialization."""

    def test_init_with_llm_service(self):
        """Test initialization with LLM service."""
        llm_service = MockLLMService()
        system = SmartAutoCorrectionSystem(llm_service=llm_service)

        assert system.llm_service is llm_service
        assert isinstance(system.correction_history, list)
        assert len(system.correction_history) == 0

    def test_init_without_llm_service(self):
        """Test initialization without LLM service (fallback mode)."""
        system = SmartAutoCorrectionSystem()

        assert system.llm_service is None
        assert isinstance(system.correction_history, list)


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestAnalyzeAndCorrect:
    """Tests for analyze_and_correct method."""

    @pytest.mark.asyncio
    async def test_analyze_and_correct_with_llm(self, global_state):
        """Test analyze_and_correct with LLM service."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "safe_corrections": {
                    "institution": {
                        "current_value": None,
                        "new_value": "MIT",
                        "action": "add",
                        "reasoning": "Add missing institution",
                        "confidence": 90,
                    }
                },
                "risky_corrections": {},
                "cannot_auto_fix": [],
                "correction_plan": "Add institution field",
                "estimated_success": 95,
            }
        )

        system = SmartAutoCorrectionSystem(llm_service=llm_service)

        validation_issues = [
            {
                "message": "Missing institution",
                "severity": "ERROR",
                "location": "/general/institution",
            }
        ]
        current_metadata = {"experimenter": "Jane Doe"}
        file_context = {"format": "SpikeGLX", "size_mb": 100}

        result = await system.analyze_and_correct(
            validation_issues=validation_issues,
            current_metadata=current_metadata,
            file_context=file_context,
            state=global_state,
        )

        assert "safe_corrections" in result
        assert "risky_corrections" in result
        assert "cannot_auto_fix" in result
        assert "correction_plan" in result
        assert result["safe_corrections"]["institution"]["confidence"] == 90

        # Check logging
        assert any("Smart auto-correction analysis complete" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_analyze_and_correct_without_llm_fallback(self, global_state):
        """Test analyze_and_correct falls back to basic when no LLM."""
        system = SmartAutoCorrectionSystem()  # No LLM

        validation_issues = [
            {
                "message": "Missing experimenter",
                "severity": "ERROR",
                "location": "/general/experimenter",
            }
        ]
        current_metadata = {}
        file_context = {"format": "NWB"}

        result = await system.analyze_and_correct(
            validation_issues=validation_issues,
            current_metadata=current_metadata,
            file_context=file_context,
            state=global_state,
        )

        assert "safe_corrections" in result
        assert "cannot_auto_fix" in result
        assert len(result["cannot_auto_fix"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_and_correct_llm_failure_fallback(self, global_state):
        """Test analyze_and_correct falls back when LLM fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM service error"))

        system = SmartAutoCorrectionSystem(llm_service=llm_service)

        validation_issues = [
            {
                "message": "Missing institution",
                "severity": "ERROR",
                "location": "/general/institution",
            }
        ]
        current_metadata = {}
        file_context = {}

        result = await system.analyze_and_correct(
            validation_issues=validation_issues,
            current_metadata=current_metadata,
            file_context=file_context,
            state=global_state,
        )

        # Should fall back to basic corrections
        assert "safe_corrections" in result
        assert "cannot_auto_fix" in result

        # Check warning logged
        assert any("Smart auto-correction failed" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_analyze_and_correct_empty_issues(self, global_state):
        """Test analyze_and_correct with no validation issues."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "safe_corrections": {},
                "risky_corrections": {},
                "cannot_auto_fix": [],
                "correction_plan": "No corrections needed",
                "estimated_success": 100,
            }
        )

        system = SmartAutoCorrectionSystem(llm_service=llm_service)

        result = await system.analyze_and_correct(
            validation_issues=[],
            current_metadata={"experimenter": "Jane Doe"},
            file_context={},
            state=global_state,
        )

        assert result["safe_corrections"] == {}
        assert result["cannot_auto_fix"] == []


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestLLMSmartCorrections:
    """Tests for _llm_smart_corrections method."""

    @pytest.mark.asyncio
    async def test_llm_smart_corrections_categorizes_issues(self, global_state):
        """Test LLM correctly categorizes issues into safe/risky/cannot."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "safe_corrections": {
                    "session_description": {
                        "current_value": None,
                        "new_value": "Recording session",
                        "action": "add",
                        "reasoning": "Add default description",
                        "confidence": 85,
                    }
                },
                "risky_corrections": {
                    "session_start_time": {
                        "current_value": "2024-01-01T00:00:00",
                        "proposed_value": "2024-01-01T12:00:00",
                        "action": "modify",
                        "risk_reason": "Changing timestamps is risky",
                        "confidence": 70,
                    }
                },
                "cannot_auto_fix": [
                    {
                        "issue": "Missing experimenter",
                        "required_info": "Experimenter name",
                        "why_manual": "Critical DANDI-required field",
                        "example_input": "Dr. Jane Smith",
                    }
                ],
                "correction_plan": "Apply safe corrections, ask approval for risky, request user input for critical",
                "estimated_success": 80,
            }
        )

        system = SmartAutoCorrectionSystem(llm_service=llm_service)

        validation_issues = [
            {"message": "Missing session_description", "severity": "WARNING"},
            {"message": "Invalid session_start_time", "severity": "ERROR"},
            {"message": "Missing experimenter", "severity": "CRITICAL"},
        ]

        result = await system._llm_smart_corrections(
            validation_issues=validation_issues,
            current_metadata={},
            file_context={"format": "NWB"},
            state=global_state,
        )

        assert len(result["safe_corrections"]) == 1
        assert len(result["risky_corrections"]) == 1
        assert len(result["cannot_auto_fix"]) == 1
        assert result["estimated_success"] == 80


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestBasicAutoCorrections:
    """Tests for _basic_auto_corrections fallback method."""

    def test_basic_auto_corrections_empty_institution(self):
        """Test basic corrections for empty institution field."""
        system = SmartAutoCorrectionSystem()

        validation_issues = [
            {
                "message": "Empty institution field",
                "severity": "WARNING",
                "location": "/general/institution",
            }
        ]
        current_metadata = {"institution": ""}

        result = system._basic_auto_corrections(validation_issues, current_metadata)

        assert "institution" in result["safe_corrections"]
        assert result["safe_corrections"]["institution"]["action"] == "remove"
        assert result["safe_corrections"]["institution"]["confidence"] == 80

    def test_basic_auto_corrections_missing_experimenter(self):
        """Test basic corrections classify missing experimenter as cannot_auto_fix."""
        system = SmartAutoCorrectionSystem()

        validation_issues = [
            {
                "message": "Missing experimenter field",
                "severity": "ERROR",
                "location": "/general/experimenter",
            }
        ]
        current_metadata = {}

        result = system._basic_auto_corrections(validation_issues, current_metadata)

        assert len(result["cannot_auto_fix"]) > 0
        assert "experimenter" in result["cannot_auto_fix"][0]["issue"].lower()
        assert "DANDI-required" in result["cannot_auto_fix"][0]["why_manual"]

    def test_basic_auto_corrections_multiple_issues(self):
        """Test basic corrections handles multiple issues."""
        system = SmartAutoCorrectionSystem()

        validation_issues = [
            {"message": "Empty institution", "severity": "WARNING"},
            {"message": "Missing experimenter", "severity": "ERROR"},
        ]
        current_metadata = {"institution": ""}

        result = system._basic_auto_corrections(validation_issues, current_metadata)

        assert "institution" in result["safe_corrections"]
        assert len(result["cannot_auto_fix"]) > 0

    def test_basic_auto_corrections_no_issues(self):
        """Test basic corrections with empty issues list."""
        system = SmartAutoCorrectionSystem()

        result = system._basic_auto_corrections([], {})

        assert result["safe_corrections"] == {}
        assert result["cannot_auto_fix"] == []
        assert result["estimated_success"] == 50


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestApplySafeCorrections:
    """Tests for apply_safe_corrections method."""

    @pytest.mark.asyncio
    async def test_apply_safe_corrections_add_field(self, global_state):
        """Test applying safe corrections to add a field."""
        system = SmartAutoCorrectionSystem()

        safe_corrections = {
            "session_description": {
                "current_value": None,
                "new_value": "Visual cortex recording",
                "action": "add",
                "reasoning": "Add default description",
                "confidence": 90,
            }
        }
        current_metadata = {"experimenter": "Jane Doe"}

        updated = await system.apply_safe_corrections(
            safe_corrections=safe_corrections,
            current_metadata=current_metadata,
            state=global_state,
        )

        assert updated["session_description"] == "Visual cortex recording"
        assert updated["experimenter"] == "Jane Doe"

        # Check logging
        assert any("Applied" in log.message and "safe auto-corrections" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_safe_corrections_modify_field(self, global_state):
        """Test applying safe corrections to modify a field."""
        system = SmartAutoCorrectionSystem()

        safe_corrections = {
            "species": {
                "current_value": "mouse",
                "new_value": "Mus musculus",
                "action": "modify",
                "reasoning": "Use scientific name",
                "confidence": 95,
            }
        }
        current_metadata = {"species": "mouse"}

        updated = await system.apply_safe_corrections(
            safe_corrections=safe_corrections,
            current_metadata=current_metadata,
            state=global_state,
        )

        assert updated["species"] == "Mus musculus"

    @pytest.mark.asyncio
    async def test_apply_safe_corrections_remove_field(self, global_state):
        """Test applying safe corrections to remove a field."""
        system = SmartAutoCorrectionSystem()

        safe_corrections = {
            "empty_field": {
                "current_value": "",
                "new_value": None,
                "action": "remove",
                "reasoning": "Remove empty field",
                "confidence": 100,
            }
        }
        current_metadata = {"empty_field": "", "valid_field": "data"}

        updated = await system.apply_safe_corrections(
            safe_corrections=safe_corrections,
            current_metadata=current_metadata,
            state=global_state,
        )

        assert "empty_field" not in updated
        assert "valid_field" in updated

    @pytest.mark.asyncio
    async def test_apply_safe_corrections_format_field(self, global_state):
        """Test applying safe corrections to format a field."""
        system = SmartAutoCorrectionSystem()

        safe_corrections = {
            "experimenter": {
                "current_value": "jane",
                "new_value": ["Jane Doe"],
                "action": "format",
                "reasoning": "Convert to list format",
                "confidence": 85,
            }
        }
        current_metadata = {"experimenter": "jane"}

        updated = await system.apply_safe_corrections(
            safe_corrections=safe_corrections,
            current_metadata=current_metadata,
            state=global_state,
        )

        assert updated["experimenter"] == ["Jane Doe"]

    @pytest.mark.asyncio
    async def test_apply_safe_corrections_skips_low_confidence(self, global_state):
        """Test apply_safe_corrections skips low-confidence fixes."""
        system = SmartAutoCorrectionSystem()

        safe_corrections = {
            "risky_field": {
                "current_value": "old",
                "new_value": "new",
                "action": "modify",
                "reasoning": "Uncertain correction",
                "confidence": 50,  # Below 70% threshold
            }
        }
        current_metadata = {"risky_field": "old"}

        updated = await system.apply_safe_corrections(
            safe_corrections=safe_corrections,
            current_metadata=current_metadata,
            state=global_state,
        )

        # Should not apply low-confidence correction
        assert updated["risky_field"] == "old"

        # Check warning logged
        assert any("Skipping low-confidence" in log.message for log in global_state.logs)

    @pytest.mark.asyncio
    async def test_apply_safe_corrections_empty_corrections(self, global_state):
        """Test apply_safe_corrections with no corrections."""
        system = SmartAutoCorrectionSystem()

        updated = await system.apply_safe_corrections(
            safe_corrections={},
            current_metadata={"field": "value"},
            state=global_state,
        )

        assert updated == {"field": "value"}

    @pytest.mark.asyncio
    async def test_apply_safe_corrections_multiple_actions(self, global_state):
        """Test apply_safe_corrections with multiple actions."""
        system = SmartAutoCorrectionSystem()

        safe_corrections = {
            "add_field": {
                "current_value": None,
                "new_value": "new value",
                "action": "add",
                "reasoning": "Add field",
                "confidence": 90,
            },
            "remove_field": {
                "current_value": "",
                "new_value": None,
                "action": "remove",
                "reasoning": "Remove empty",
                "confidence": 100,
            },
            "modify_field": {
                "current_value": "old",
                "new_value": "updated",
                "action": "modify",
                "reasoning": "Update value",
                "confidence": 85,
            },
        }
        current_metadata = {"remove_field": "", "modify_field": "old"}

        updated = await system.apply_safe_corrections(
            safe_corrections=safe_corrections,
            current_metadata=current_metadata,
            state=global_state,
        )

        assert updated["add_field"] == "new value"
        assert "remove_field" not in updated
        assert updated["modify_field"] == "updated"


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestGetCorrectionSummary:
    """Tests for get_correction_summary method."""

    def test_get_correction_summary_all_types(self):
        """Test correction summary with all types of corrections."""
        system = SmartAutoCorrectionSystem()

        summary = system.get_correction_summary(safe_count=3, risky_count=2, manual_count=1)

        assert "3 issues can be fixed automatically" in summary
        assert "2 fixes need your approval" in summary
        assert "1 issues require your input" in summary

    def test_get_correction_summary_only_safe(self):
        """Test correction summary with only safe corrections."""
        system = SmartAutoCorrectionSystem()

        summary = system.get_correction_summary(safe_count=5, risky_count=0, manual_count=0)

        assert "5 issues can be fixed automatically" in summary
        assert "⚠️" not in summary
        assert "📝" not in summary

    def test_get_correction_summary_only_manual(self):
        """Test correction summary with only manual corrections."""
        system = SmartAutoCorrectionSystem()

        summary = system.get_correction_summary(safe_count=0, risky_count=0, manual_count=4)

        assert "4 issues require your input" in summary
        assert "✅" not in summary
        assert "⚠️" not in summary

    def test_get_correction_summary_no_corrections(self):
        """Test correction summary with no corrections."""
        system = SmartAutoCorrectionSystem()

        summary = system.get_correction_summary(safe_count=0, risky_count=0, manual_count=0)

        assert summary == "No corrections needed"

    def test_get_correction_summary_safe_and_risky(self):
        """Test correction summary with safe and risky corrections."""
        system = SmartAutoCorrectionSystem()

        summary = system.get_correction_summary(safe_count=2, risky_count=1, manual_count=0)

        assert "2 issues can be fixed automatically" in summary
        assert "1 fixes need your approval" in summary
        assert "📝" not in summary


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestSmartAutoCorrectionIntegration:
    """Integration tests for complete auto-correction workflow."""

    @pytest.mark.asyncio
    async def test_complete_correction_workflow(self, global_state):
        """Test complete workflow: analyze → apply corrections."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "safe_corrections": {
                    "session_description": {
                        "current_value": None,
                        "new_value": "Recording session",
                        "action": "add",
                        "reasoning": "Add default",
                        "confidence": 90,
                    },
                    "empty_field": {
                        "current_value": "",
                        "new_value": None,
                        "action": "remove",
                        "reasoning": "Remove empty",
                        "confidence": 100,
                    },
                },
                "risky_corrections": {
                    "subject_age": {
                        "current_value": "P90",
                        "proposed_value": "P90D",
                        "action": "modify",
                        "risk_reason": "Changing subject metadata",
                        "confidence": 75,
                    }
                },
                "cannot_auto_fix": [
                    {
                        "issue": "Missing experimenter",
                        "required_info": "Experimenter name",
                        "why_manual": "Critical field",
                        "example_input": "Dr. Smith",
                    }
                ],
                "correction_plan": "Apply safe, ask approval for risky, request user input",
                "estimated_success": 85,
            }
        )

        system = SmartAutoCorrectionSystem(llm_service=llm_service)

        # Step 1: Analyze issues
        validation_issues = [
            {"message": "Missing session_description", "severity": "WARNING"},
            {"message": "Empty field detected", "severity": "INFO"},
            {"message": "Invalid subject_age format", "severity": "ERROR"},
            {"message": "Missing experimenter", "severity": "CRITICAL"},
        ]
        current_metadata = {"empty_field": "", "subject_age": "P90"}

        analysis = await system.analyze_and_correct(
            validation_issues=validation_issues,
            current_metadata=current_metadata,
            file_context={"format": "NWB"},
            state=global_state,
        )

        assert len(analysis["safe_corrections"]) == 2
        assert len(analysis["risky_corrections"]) == 1
        assert len(analysis["cannot_auto_fix"]) == 1

        # Step 2: Apply safe corrections
        updated_metadata = await system.apply_safe_corrections(
            safe_corrections=analysis["safe_corrections"],
            current_metadata=current_metadata,
            state=global_state,
        )

        assert updated_metadata["session_description"] == "Recording session"
        assert "empty_field" not in updated_metadata
        assert updated_metadata["subject_age"] == "P90"  # Risky not applied

        # Step 3: Get summary
        summary = system.get_correction_summary(
            safe_count=len(analysis["safe_corrections"]),
            risky_count=len(analysis["risky_corrections"]),
            manual_count=len(analysis["cannot_auto_fix"]),
        )

        assert "2 issues can be fixed automatically" in summary
        assert "1 fixes need your approval" in summary
        assert "1 issues require your input" in summary
