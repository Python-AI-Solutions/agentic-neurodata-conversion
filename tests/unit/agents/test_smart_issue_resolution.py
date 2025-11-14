"""
Unit tests for SmartIssueResolution.

Tests intelligent resolution plan generation for NWB validation issues.
"""

from unittest.mock import AsyncMock

import pytest

from agentic_neurodata_conversion.agents.smart_issue_resolution import SmartIssueResolution
from agentic_neurodata_conversion.services.llm_service import MockLLMService


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestSmartIssueResolutionInitialization:
    """Tests for SmartIssueResolution initialization."""

    def test_init_with_llm_service(self):
        """Test initialization with LLM service."""
        llm_service = MockLLMService()
        resolver = SmartIssueResolution(llm_service=llm_service)

        assert resolver.llm_service is llm_service

    def test_init_without_llm_service(self):
        """Test initialization without LLM service."""
        resolver = SmartIssueResolution()

        assert resolver.llm_service is None


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestBasicResolutionPlan:
    """Tests for _basic_resolution_plan method."""

    def test_basic_resolution_plan_with_issues(self, global_state):
        """Test basic resolution plan generation with issues."""
        resolver = SmartIssueResolution()

        issues = [
            {"message": "Missing experimenter", "severity": "ERROR"},
            {"message": "Missing institution", "severity": "ERROR"},
            {"message": "Invalid age format", "severity": "WARNING"},
        ]

        plan = resolver._basic_resolution_plan(issues, global_state)

        assert "workflows" in plan
        assert "code_examples" in plan
        assert "prerequisites" in plan
        assert "success_criteria" in plan
        assert len(plan["workflows"]) == 3

    def test_basic_resolution_plan_with_pydantic_issues(self, global_state):
        """Test basic resolution plan with Pydantic model issues."""
        from agentic_neurodata_conversion.models.validation import ValidationIssue, ValidationSeverity

        resolver = SmartIssueResolution()

        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Missing required field",
                check_function_name="check_required",
            )
        ]

        plan = resolver._basic_resolution_plan(issues, global_state)

        assert len(plan["workflows"]) == 1
        assert plan["workflows"][0]["issue"] == "Missing required field"

    def test_basic_resolution_plan_limits_to_5_issues(self, global_state):
        """Test basic plan limits to first 5 issues."""
        resolver = SmartIssueResolution()

        issues = [{"message": f"Issue {i}", "severity": "ERROR"} for i in range(10)]

        plan = resolver._basic_resolution_plan(issues, global_state)

        assert len(plan["workflows"]) == 5

    def test_basic_resolution_plan_includes_effort_estimates(self, global_state):
        """Test basic plan includes effort estimates."""
        resolver = SmartIssueResolution()

        issues = [{"message": "Test issue", "severity": "ERROR"}]

        plan = resolver._basic_resolution_plan(issues, global_state)

        assert "estimated_effort" in plan["workflows"][0]
        assert "15-30 minutes" in plan["workflows"][0]["estimated_effort"]


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestGenerateResolutionPlan:
    """Tests for generate_resolution_plan method."""

    @pytest.mark.asyncio
    async def test_generate_resolution_plan_without_llm_fallback(self, global_state):
        """Test resolution plan generation falls back when no LLM."""
        resolver = SmartIssueResolution()

        issues = [{"message": "Test issue", "severity": "ERROR"}]
        file_context = {"nwb_path": "/test/file.nwb"}
        existing_metadata = {}

        plan = await resolver.generate_resolution_plan(issues, file_context, existing_metadata, global_state)

        assert "workflows" in plan
        assert len(plan["workflows"]) == 1
        assert plan["code_examples"] == []

    @pytest.mark.asyncio
    async def test_generate_resolution_plan_with_llm(self, global_state):
        """Test resolution plan generation with LLM."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            side_effect=[
                # First call: resolution planning
                {
                    "workflows": [
                        {
                            "issue_description": "Missing experimenter field",
                            "severity": "ERROR",
                            "resolution_approach": "Add experimenter metadata",
                            "steps": [
                                {
                                    "step_number": 1,
                                    "action": "Open NWB file",
                                    "details": "Use PyNWB to open file",
                                }
                            ],
                            "prerequisites": ["PyNWB installed"],
                            "estimated_effort": "5 minutes",
                            "difficulty": "easy",
                            "success_criteria": "Validation passes",
                        }
                    ],
                    "overall_strategy": "Fix metadata fields",
                },
                # Second call: code examples
                {
                    "code": "nwbfile.experimenter = ['Dr. Smith']",
                    "explanation": "Add experimenter",
                    "notes": ["Use list format"],
                },
            ]
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        issues = [{"message": "Missing experimenter", "severity": "ERROR"}]
        file_context = {"nwb_path": "/test/file.nwb", "nwb_version": "2.5.0"}
        existing_metadata = {}

        plan = await resolver.generate_resolution_plan(issues, file_context, existing_metadata, global_state)

        assert "workflows" in plan
        assert len(plan["workflows"]) == 1
        assert plan["workflows"][0]["issue_description"] == "Missing experimenter field"
        assert "code_examples" in plan

    @pytest.mark.asyncio
    async def test_generate_resolution_plan_logs_success(self, global_state):
        """Test resolution plan generation logs success."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            side_effect=[
                {
                    "workflows": [
                        {
                            "issue_description": "Test issue",
                            "severity": "ERROR",
                            "resolution_approach": "Test approach",
                            "steps": [],
                            "prerequisites": [],
                            "estimated_effort": "5 min",
                            "difficulty": "easy",
                            "success_criteria": "Pass",
                        }
                    ],
                    "overall_strategy": "Test",
                },
                {"code": "test", "explanation": "test"},
            ]
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        issues = [{"message": "Test", "severity": "ERROR"}]
        await resolver.generate_resolution_plan(issues, {}, {}, global_state)

        # Check logs
        assert len(global_state.logs) > 0

    @pytest.mark.asyncio
    async def test_generate_resolution_plan_handles_llm_failure(self, global_state):
        """Test resolution plan falls back on LLM failure."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM failed"))

        resolver = SmartIssueResolution(llm_service=llm_service)

        issues = [{"message": "Test issue", "severity": "ERROR"}]

        plan = await resolver.generate_resolution_plan(issues, {}, {}, global_state)

        # Should fall back to basic plan
        assert "workflows" in plan
        assert len(plan["workflows"]) == 1

    @pytest.mark.asyncio
    async def test_generate_resolution_plan_handles_code_example_failure(self, global_state):
        """Test resolution plan continues when code example generation fails."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            side_effect=[
                # Resolution planning succeeds
                {
                    "workflows": [
                        {
                            "issue_description": "Missing metadata field",
                            "severity": "ERROR",
                            "resolution_approach": "Add field",
                            "steps": [],
                            "prerequisites": [],
                            "estimated_effort": "5 min",
                            "difficulty": "easy",
                            "success_criteria": "Pass",
                        }
                    ],
                    "overall_strategy": "Fix",
                },
                # Code example fails
                Exception("Code generation failed"),
            ]
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        issues = [{"message": "Missing field", "severity": "ERROR"}]

        plan = await resolver.generate_resolution_plan(issues, {"nwb_path": "test.nwb"}, {}, global_state)

        # Plan should still be generated
        assert "workflows" in plan
        assert "code_examples" in plan


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestLLMResolutionPlanning:
    """Tests for _llm_resolution_planning method."""

    @pytest.mark.asyncio
    async def test_llm_resolution_planning_formats_issues(self, global_state):
        """Test LLM resolution planning formats issues correctly."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "workflows": [],
                "overall_strategy": "Test",
            }
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        issues = [
            {
                "severity": "ERROR",
                "message": "Test issue",
                "location": "/nwbfile/subject",
            }
        ]
        file_context = {"nwb_path": "/test/file.nwb", "file_size_mb": 100}
        existing_metadata = {"experimenter": ["Dr. Smith"]}

        result = await resolver._llm_resolution_planning(issues, file_context, existing_metadata, global_state)

        # Verify LLM was called
        assert llm_service.generate_structured_output.called
        assert result["workflows"] == []

    @pytest.mark.asyncio
    async def test_llm_resolution_planning_limits_issues(self, global_state):
        """Test LLM resolution planning limits to 15 issues."""
        llm_service = MockLLMService()
        call_count = 0

        def check_prompt(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            prompt = kwargs.get("prompt", "")
            # Should only include first 15 issues
            assert "16." not in prompt
            return {"workflows": [], "overall_strategy": "Test"}

        llm_service.generate_structured_output = AsyncMock(side_effect=check_prompt)

        resolver = SmartIssueResolution(llm_service=llm_service)

        issues = [{"message": f"Issue {i}", "severity": "ERROR"} for i in range(20)]

        await resolver._llm_resolution_planning(issues, {}, {}, global_state)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_llm_resolution_planning_raises_on_failure(self, global_state):
        """Test LLM resolution planning raises exception on failure."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("LLM error"))

        resolver = SmartIssueResolution(llm_service=llm_service)

        issues = [{"message": "Test", "severity": "ERROR"}]

        with pytest.raises(Exception, match="LLM error"):
            await resolver._llm_resolution_planning(issues, {}, {}, global_state)


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestAddCodeExamples:
    """Tests for _add_code_examples method."""

    @pytest.mark.asyncio
    async def test_add_code_examples_generates_for_metadata_issues(self, global_state):
        """Test code examples generated for metadata issues."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "code": "nwbfile.experimenter = ['Test']",
                "explanation": "Add experimenter",
                "notes": ["Use list"],
            }
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        resolution_plan = {
            "workflows": [
                {
                    "issue_description": "Missing required field experimenter",
                    "steps": [],
                }
            ]
        }

        result = await resolver._add_code_examples(resolution_plan, {"nwb_path": "test.nwb"}, global_state)

        assert "code_examples" in result
        assert len(result["code_examples"]) == 1
        assert result["code_examples"][0]["code"] == "nwbfile.experimenter = ['Test']"

    @pytest.mark.asyncio
    async def test_add_code_examples_skips_non_metadata_issues(self, global_state):
        """Test code examples skipped for non-metadata issues."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock()

        resolver = SmartIssueResolution(llm_service=llm_service)

        resolution_plan = {
            "workflows": [
                {
                    "issue_description": "File corrupted",  # No metadata keywords
                    "steps": [],
                }
            ]
        }

        result = await resolver._add_code_examples(resolution_plan, {}, global_state)

        # Should not call LLM for non-metadata issues
        assert not llm_service.generate_structured_output.called
        assert result["code_examples"] == []

    @pytest.mark.asyncio
    async def test_add_code_examples_limits_to_5_workflows(self, global_state):
        """Test code examples limited to first 5 workflows."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "code": "test",
                "explanation": "test",
            }
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        resolution_plan = {"workflows": [{"issue_description": f"Missing field {i}", "steps": []} for i in range(10)]}

        result = await resolver._add_code_examples(resolution_plan, {}, global_state)

        # Should only generate code for first 5
        assert len(result["code_examples"]) <= 5

    @pytest.mark.asyncio
    async def test_add_code_examples_handles_failure_gracefully(self, global_state):
        """Test code example generation continues on individual failure."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            side_effect=[
                {"code": "success1", "explanation": "test"},
                Exception("Failed"),  # Second one fails
                {"code": "success2", "explanation": "test"},
            ]
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        resolution_plan = {
            "workflows": [
                {"issue_description": "Missing field 1", "steps": []},
                {"issue_description": "Missing field 2", "steps": []},
                {"issue_description": "Missing field 3", "steps": []},
            ]
        }

        result = await resolver._add_code_examples(resolution_plan, {}, global_state)

        # Should have 2 successful code examples
        assert len(result["code_examples"]) == 2

    @pytest.mark.asyncio
    async def test_add_code_examples_includes_workflow_index(self, global_state):
        """Test code examples include workflow index."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "code": "test",
                "explanation": "test",
            }
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        resolution_plan = {
            "workflows": [
                {"issue_description": "Missing metadata", "steps": []},
            ]
        }

        result = await resolver._add_code_examples(resolution_plan, {}, global_state)

        assert result["code_examples"][0]["workflow_index"] == 1


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestGenerateInteractiveDecisionTree:
    """Tests for generate_interactive_decision_tree method."""

    @pytest.mark.asyncio
    async def test_generate_decision_tree_without_llm(self, global_state):
        """Test decision tree returns empty when no LLM."""
        resolver = SmartIssueResolution()

        issue = {"message": "Test issue", "severity": "ERROR"}
        context = {}

        result = await resolver.generate_interactive_decision_tree(issue, context, global_state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_generate_decision_tree_with_llm(self, global_state):
        """Test decision tree generation with LLM."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "root_question": "Do you know the subject's age?",
                "decision_paths": [
                    {
                        "condition": "YES",
                        "recommendation": "Add exact age",
                        "is_terminal": True,
                    },
                    {
                        "condition": "NO",
                        "next_question": "Can you estimate?",
                        "is_terminal": False,
                    },
                ],
            }
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        issue = {"message": "Missing age", "severity": "WARNING", "location": "/subject"}
        context = {"species": "Mus musculus"}

        result = await resolver.generate_interactive_decision_tree(issue, context, global_state)

        assert "root_question" in result
        assert "decision_paths" in result
        assert len(result["decision_paths"]) == 2

    @pytest.mark.asyncio
    async def test_generate_decision_tree_with_pydantic_issue(self, global_state):
        """Test decision tree with Pydantic model issue."""
        from agentic_neurodata_conversion.models.validation import ValidationIssue, ValidationSeverity

        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            return_value={
                "root_question": "Test question",
                "decision_paths": [],
            }
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            message="Missing optional field",
            check_function_name="check_optional",
        )

        result = await resolver.generate_interactive_decision_tree(issue, {}, global_state)

        assert "root_question" in result

    @pytest.mark.asyncio
    async def test_generate_decision_tree_handles_failure(self, global_state):
        """Test decision tree returns empty on failure."""
        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(side_effect=Exception("Failed"))

        resolver = SmartIssueResolution(llm_service=llm_service)

        issue = {"message": "Test", "severity": "ERROR"}

        result = await resolver.generate_interactive_decision_tree(issue, {}, global_state)

        assert result == {}


@pytest.mark.unit
@pytest.mark.agent_evaluation
class TestSmartIssueResolutionIntegration:
    """Integration tests for complete resolution workflows."""

    @pytest.mark.asyncio
    async def test_complete_resolution_workflow(self, global_state):
        """Test complete resolution workflow from issues to plan."""
        from agentic_neurodata_conversion.models.validation import ValidationIssue, ValidationSeverity

        llm_service = MockLLMService()
        llm_service.generate_structured_output = AsyncMock(
            side_effect=[
                # Resolution planning
                {
                    "workflows": [
                        {
                            "issue_description": "Missing experimenter",
                            "severity": "ERROR",
                            "resolution_approach": "Add metadata",
                            "steps": [
                                {
                                    "step_number": 1,
                                    "action": "Open file",
                                    "details": "Use PyNWB",
                                }
                            ],
                            "prerequisites": ["PyNWB"],
                            "estimated_effort": "5 min",
                            "difficulty": "easy",
                            "success_criteria": "Pass",
                        }
                    ],
                    "overall_strategy": "Fix metadata",
                    "recommended_order": [0],
                },
                # Code example
                {
                    "code": "nwbfile.experimenter = ['Dr. Smith']",
                    "explanation": "Add experimenter",
                    "notes": [],
                },
            ]
        )

        resolver = SmartIssueResolution(llm_service=llm_service)

        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Missing required field: experimenter",
                check_function_name="check_experimenter",
            )
        ]

        file_context = {
            "nwb_path": "/data/test.nwb",
            "file_size_mb": 50,
            "nwb_version": "2.5.0",
        }

        existing_metadata = {"session_description": "Test session"}

        plan = await resolver.generate_resolution_plan(issues, file_context, existing_metadata, global_state)

        # Verify complete plan structure
        assert "workflows" in plan
        assert "code_examples" in plan
        assert len(plan["workflows"]) == 1
        assert len(plan["code_examples"]) == 1
        assert plan["workflows"][0]["issue_description"] == "Missing experimenter"
        assert "nwbfile.experimenter" in plan["code_examples"][0]["code"]
