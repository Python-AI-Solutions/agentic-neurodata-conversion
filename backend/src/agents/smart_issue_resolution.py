"""
Smart Issue Resolution Engine.

Generates detailed, actionable resolution workflows for NWB validation issues.
Goes beyond simple suggestions to provide step-by-step guides with code examples,
command snippets, and explanations.

Features:
- Step-by-step resolution workflows
- Code examples for common fixes
- Interactive decision trees for complex issues
- Integration with existing metadata
- Validation of proposed fixes before application
"""
from typing import Any, Dict, List, Optional
import json
import logging
from pathlib import Path

from models import GlobalState, LogLevel
from services import LLMService

logger = logging.getLogger(__name__)


class SmartIssueResolution:
    """
    Generates intelligent, actionable resolution plans for validation issues.

    Provides:
    - Step-by-step fix workflows
    - Code examples and commands
    - Prerequisite checks
    - Expected outcomes
    - Validation steps
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the resolution engine.

        Args:
            llm_service: Optional LLM service for intelligent resolution generation
        """
        self.llm_service = llm_service

    async def generate_resolution_plan(
        self,
        issues: List[Any],
        file_context: Dict[str, Any],
        existing_metadata: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive resolution plan for validation issues.

        Args:
            issues: List of validation issues
            file_context: Context about the NWB file
            existing_metadata: Current metadata in the file
            state: Global state

        Returns:
            Resolution plan with:
            - workflows: Step-by-step resolution workflows
            - code_examples: Concrete code snippets
            - prerequisites: What's needed before fixes can be applied
            - estimated_effort: Time estimates
            - success_criteria: How to verify fixes worked
        """
        try:
            if not self.llm_service:
                return self._basic_resolution_plan(issues, state)

            # Generate intelligent resolution plan
            resolution_plan = await self._llm_resolution_planning(
                issues,
                file_context,
                existing_metadata,
                state
            )

            # Enhance with code examples
            resolution_plan = await self._add_code_examples(
                resolution_plan,
                file_context,
                state
            )

            state.add_log(
                LogLevel.INFO,
                "Generated smart resolution plan",
                {
                    "workflows_count": len(resolution_plan.get("workflows", [])),
                    "has_code_examples": len(resolution_plan.get("code_examples", [])) > 0,
                }
            )

            return resolution_plan

        except Exception as e:
            logger.error(f"Resolution plan generation failed: {e}")
            state.add_log(
                LogLevel.WARNING,
                f"Resolution plan generation failed: {e}"
            )
            return self._basic_resolution_plan(issues, state)

    def _basic_resolution_plan(
        self,
        issues: List[Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Basic resolution plan when LLM is not available.
        """
        workflows = []

        for idx, issue in enumerate(issues[:5], 1):
            issue_dict = issue.model_dump() if hasattr(issue, 'model_dump') else issue
            workflows.append({
                "issue_number": idx,
                "issue": issue_dict.get('message', 'Unknown issue'),
                "steps": [
                    "Review the validation error message",
                    "Check NWB Inspector documentation",
                    "Make appropriate metadata corrections",
                    "Re-run validation to verify fix"
                ],
                "estimated_effort": "15-30 minutes",
            })

        return {
            "workflows": workflows,
            "code_examples": [],
            "prerequisites": ["Access to NWB file", "Understanding of NWB format"],
            "success_criteria": "All validation issues resolved",
        }

    async def _llm_resolution_planning(
        self,
        issues: List[Any],
        file_context: Dict[str, Any],
        existing_metadata: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to generate intelligent resolution workflows.
        """
        system_prompt = """You are an expert NWB data engineer and troubleshooter.

Your job is to create **actionable, step-by-step resolution plans** for NWB validation issues.

**Resolution Plan Requirements**:

1. **Concrete Steps**: Specific actions, not vague suggestions
   - Bad: "Fix the metadata"
   - Good: "Add 'experimenter' field to NWB file metadata section with value ['John Smith']"

2. **Prerequisites**: What's needed before starting
   - Required tools (PyNWB, h5py, etc.)
   - Access requirements
   - Information needed from user

3. **Decision Points**: When multiple approaches exist
   - Explain tradeoffs
   - Provide recommendation
   - Show how to choose

4. **Validation**: How to verify the fix worked
   - Specific checks to run
   - Expected outputs
   - How to confirm success

5. **Code Examples**: Concrete Python snippets when applicable

**Example Workflow**:

Issue: "Missing required field 'experimenter'"

Steps:
1. Open NWB file in PyNWB:
   ```python
   from pynwb import NWBHDF5IO
   io = NWBHDF5IO('file.nwb', 'r+')
   nwbfile = io.read()
   ```

2. Add experimenter information:
   ```python
   nwbfile.experimenter = ['Dr. Jane Smith']
   ```

3. Write changes:
   ```python
   io.write(nwbfile)
   io.close()
   ```

4. Re-run validation to confirm fix

Be specific, practical, and actionable."""

        # Format issues for analysis
        issues_text = []
        for idx, issue in enumerate(issues[:15], 1):
            issue_dict = issue.model_dump() if hasattr(issue, 'model_dump') else issue
            issues_text.append(
                f"{idx}. [{issue_dict.get('severity', 'UNKNOWN')}] "
                f"{issue_dict.get('message', 'No message')}\n"
                f"   Location: {issue_dict.get('location', 'Unknown')}"
            )

        user_prompt = f"""Create detailed resolution workflows for these validation issues:

**Issues**:
{chr(10).join(issues_text)}

**File Context**:
- NWB Path: {file_context.get('nwb_path', 'Unknown')}
- File Size: {file_context.get('file_size_mb', 0)} MB
- NWB Version: {file_context.get('nwb_version', 'Unknown')}

**Existing Metadata**:
{json.dumps(existing_metadata, indent=2, default=str)[:500]}

For each issue (or group of related issues):
1. Provide step-by-step resolution workflow
2. Include code examples where applicable
3. List prerequisites
4. Specify validation steps
5. Estimate effort

Focus on the top 5-7 most critical issues."""

        output_schema = {
            "type": "object",
            "properties": {
                "workflows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue_description": {
                                "type": "string",
                                "description": "What issue this workflow addresses"
                            },
                            "severity": {
                                "type": "string",
                                "description": "Issue severity level"
                            },
                            "resolution_approach": {
                                "type": "string",
                                "description": "Overall approach to fixing this"
                            },
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "step_number": {"type": "number"},
                                        "action": {"type": "string"},
                                        "details": {"type": "string"},
                                        "code_snippet": {
                                            "type": "string",
                                            "description": "Python code example (if applicable)"
                                        },
                                        "expected_outcome": {"type": "string"},
                                    },
                                    "required": ["step_number", "action", "details"],
                                },
                            },
                            "prerequisites": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "What's needed before starting"
                            },
                            "estimated_effort": {
                                "type": "string",
                                "description": "Time estimate (e.g., '5 minutes', '30 minutes')"
                            },
                            "difficulty": {
                                "type": "string",
                                "enum": ["easy", "medium", "hard"]
                            },
                            "success_criteria": {
                                "type": "string",
                                "description": "How to verify the fix worked"
                            },
                            "alternative_approaches": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Other ways to solve this (optional)"
                            },
                        },
                        "required": [
                            "issue_description",
                            "resolution_approach",
                            "steps",
                            "prerequisites",
                            "estimated_effort",
                            "difficulty",
                            "success_criteria"
                        ],
                    },
                },
                "overall_strategy": {
                    "type": "string",
                    "description": "High-level strategy for addressing all issues"
                },
                "recommended_order": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Recommended order to tackle workflows (by index)"
                },
            },
            "required": ["workflows", "overall_strategy"],
        }

        try:
            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            return response

        except Exception as e:
            logger.error(f"LLM resolution planning failed: {e}")
            state.add_log(LogLevel.WARNING, f"LLM resolution planning failed: {e}")
            raise

    async def _add_code_examples(
        self,
        resolution_plan: Dict[str, Any],
        file_context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Add concrete, runnable code examples for common fixes.
        """
        system_prompt = """You are an expert Python programmer specializing in PyNWB (Neurodata Without Borders).

Generate complete, runnable Python code examples for NWB file corrections.

**Code Requirements**:
1. Complete and runnable (not pseudocode)
2. Include necessary imports
3. Include error handling
4. Include comments explaining each step
5. Use PyNWB best practices
6. Handle file I/O safely (with context managers)

**Example**:

```python
from pynwb import NWBHDF5IO
from datetime import datetime

# Open NWB file in read/write mode
with NWBHDF5IO('path/to/file.nwb', 'r+') as io:
    nwbfile = io.read()

    # Add missing experimenter information
    nwbfile.experimenter = ['Dr. Jane Smith']

    # Add institution if missing
    if not nwbfile.institution:
        nwbfile.institution = 'University of Example'

    # Write changes back to file
    io.write(nwbfile)

print("✓ Metadata updated successfully")
```

Make examples specific to the actual issues being fixed."""

        workflows = resolution_plan.get("workflows", [])

        # Generate code examples for workflows that need them
        code_examples = []

        for idx, workflow in enumerate(workflows[:5], 1):  # Top 5 workflows
            issue_desc = workflow.get("issue_description", "")
            steps = workflow.get("steps", [])

            # Check if this issue benefits from code example
            needs_code = any(
                keyword in issue_desc.lower()
                for keyword in ['missing', 'metadata', 'field', 'required', 'add']
            )

            if needs_code:
                user_prompt = f"""Generate complete Python code example for this fix:

**Issue**: {issue_desc}

**Resolution Steps**:
{json.dumps(steps, indent=2, default=str)}

**File Context**:
- NWB Path: {file_context.get('nwb_path', 'file.nwb')}
- NWB Version: {file_context.get('nwb_version', '2.5.0')}

Generate a complete, runnable code example that implements this fix."""

                output_schema = {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Complete Python code"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what the code does"
                        },
                        "notes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Important notes or caveats"
                        },
                    },
                    "required": ["code", "explanation"],
                }

                try:
                    code_result = await self.llm_service.generate_structured_output(
                        prompt=user_prompt,
                        output_schema=output_schema,
                        system_prompt=system_prompt,
                    )

                    code_examples.append({
                        "workflow_index": idx,
                        "issue": issue_desc,
                        "code": code_result.get("code", ""),
                        "explanation": code_result.get("explanation", ""),
                        "notes": code_result.get("notes", []),
                    })

                except Exception as e:
                    logger.warning(f"Code example generation failed for workflow {idx}: {e}")

        # Add code examples to resolution plan
        resolution_plan["code_examples"] = code_examples

        return resolution_plan

    async def generate_interactive_decision_tree(
        self,
        issue: Any,
        context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Generate interactive decision tree for complex issues with multiple resolution paths.

        Useful when there are multiple ways to fix an issue and the best approach
        depends on user's situation.
        """
        if not self.llm_service:
            return {}

        issue_dict = issue.model_dump() if hasattr(issue, 'model_dump') else issue

        system_prompt = """You are an expert at creating decision trees for troubleshooting NWB validation issues.

Create an interactive decision tree that guides users through resolving complex issues
based on their specific situation.

**Decision Tree Structure**:

1. **Root Question**: First decision point
2. **Branches**: Different paths based on answers
3. **Leaf Nodes**: Final recommendations

**Example**:

Issue: "Subject age is missing"

Decision Tree:
- Do you know the subject's age?
  - YES → Add exact age in ISO 8601 duration format (e.g., 'P90D' for 90 days)
    - Is it a mouse?
      - YES → Use days (e.g., 'P90D')
      - NO → Use appropriate unit for species
  - NO → Can you estimate from experiment date?
    - YES → Estimate and document as approximate
    - NO → Contact original experimenter or mark as unknown

Make it practical and actionable."""

        user_prompt = f"""Create an interactive decision tree for this issue:

**Issue**: {issue_dict.get('message', 'Unknown')}
**Severity**: {issue_dict.get('severity', 'Unknown')}
**Location**: {issue_dict.get('location', 'Unknown')}

**Context**:
{json.dumps(context, indent=2, default=str)[:300]}

Create a decision tree that helps users choose the right resolution approach."""

        output_schema = {
            "type": "object",
            "properties": {
                "root_question": {
                    "type": "string",
                    "description": "First question to determine path"
                },
                "decision_paths": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "condition": {"type": "string"},
                            "next_question": {"type": "string"},
                            "recommendation": {"type": "string"},
                            "is_terminal": {"type": "boolean"},
                        },
                        "required": ["condition"],
                    },
                },
            },
            "required": ["root_question", "decision_paths"],
        }

        try:
            decision_tree = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            return decision_tree

        except Exception as e:
            logger.error(f"Decision tree generation failed: {e}")
            return {}
