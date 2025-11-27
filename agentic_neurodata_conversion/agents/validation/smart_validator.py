"""Smart Validation Analysis with LLM.

This module uses LLM to intelligently analyze validation results and provide
context-aware guidance on how to fix issues.
"""

from typing import Any

from agentic_neurodata_conversion.models import GlobalState, LogLevel
from agentic_neurodata_conversion.services import LLMService


class SmartValidationAnalyzer:
    """Intelligent validation result analyzer.

    Instead of just listing validation errors, this analyzer:
    - Groups related issues
    - Prioritizes critical vs. optional fixes
    - Suggests specific actions
    - Provides context-aware guidance
    """

    def __init__(self, llm_service: LLMService | None = None):
        """Initialize the smart validation analyzer.

        Args:
            llm_service: Optional LLM service for intelligent analysis
        """
        self.llm_service = llm_service

    async def analyze_validation_results(
        self,
        validation_result: dict[str, Any],
        file_context: dict[str, Any],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Intelligently analyze validation results and provide actionable guidance.

        Args:
            validation_result: Raw validation result from NWB Inspector
            file_context: Context about the file (format, size, etc.)
            state: Global conversion state

        Returns:
            Dict with:
            - grouped_issues: Issues grouped by category
            - priority_order: Issues sorted by priority
            - quick_fixes: Issues that can be auto-fixed
            - user_actions_needed: Issues requiring user input
            - severity_assessment: Overall severity
            - suggested_workflow: Recommended fix workflow
        """
        if not self.llm_service:
            return self._basic_validation_analysis(validation_result)

        try:
            issues = validation_result.get("issues", [])
            if not issues:
                return {
                    "grouped_issues": {},
                    "priority_order": [],
                    "quick_fixes": [],
                    "user_actions_needed": [],
                    "severity_assessment": "success",
                    "suggested_workflow": "No issues found - file is valid!",
                }

            system_prompt = """You are an expert NWB data validator with deep knowledge of:
- NWB schema requirements
- DANDI archive submission standards
- Common validation issues and their fixes
- Neuroscience metadata best practices

Your job is to analyze NWB validation results and provide intelligent guidance:

1. **Group Related Issues**: Cluster similar issues together
2. **Prioritize**: Critical (blocks DANDI) vs. Recommended vs. Optional
3. **Suggest Quick Fixes**: What can be auto-corrected vs. needs user input
4. **Provide Context**: Explain WHY each issue matters
5. **Recommend Workflow**: What order to fix issues in

Be specific, actionable, and educational."""

            issues_summary = "\n".join(
                [
                    f"- [{issue.get('severity', 'INFO')}] {issue.get('message', 'Unknown issue')}"
                    for issue in issues[:20]  # Limit to 20 issues
                ]
            )

            user_prompt = f"""Analyze these NWB validation results and provide intelligent guidance.

**File Context:**
- Format: {file_context.get("format", "unknown")}
- Size: {file_context.get("size_mb", 0):.1f} MB
- Conversion attempt: {state.correction_attempt}

**Validation Summary:**
- Total issues: {len(issues)}
- Critical: {sum(1 for i in issues if i.get("severity") == "CRITICAL")}
- Errors: {sum(1 for i in issues if i.get("severity") == "ERROR")}
- Warnings: {sum(1 for i in issues if i.get("severity") == "WARNING")}
- Info: {sum(1 for i in issues if i.get("severity") == "INFO")}

**Issues Found:**
{issues_summary}

Analyze and provide:

1. **Grouped Issues**: Organize by category (metadata, data structure, DANDI requirements, etc.)

2. **Priority Order**: Rank issues by importance
   - P0: Must fix (blocks DANDI submission)
   - P1: Should fix (best practices)
   - P2: Nice to have (optional enhancements)

3. **Quick Fixes**: Which issues can be auto-corrected?
   - Example: Empty institution → can remove
   - Example: Missing experimenter → NEEDS user input

4. **User Actions**: Which issues REQUIRE user input?
   - Be specific about what information is needed

5. **Severity Assessment**: Overall file quality (critical/high/medium/low)

6. **Suggested Workflow**: Step-by-step plan to fix all issues
   - Example: "First fix metadata (experimenter, institution), then validate data structure, then check DANDI compliance"

Return detailed analysis in JSON format."""

            output_schema = {
                "type": "object",
                "properties": {
                    "grouped_issues": {
                        "type": "object",
                        "description": "Issues grouped by category",
                        "additionalProperties": {"type": "array", "items": {"type": "object"}},
                    },
                    "priority_order": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "issue": {"type": "string"},
                                "priority": {"type": "string", "enum": ["P0", "P1", "P2"]},
                                "reason": {"type": "string"},
                            },
                        },
                        "description": "Issues sorted by priority",
                    },
                    "quick_fixes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "issue": {"type": "string"},
                                "fix": {"type": "string"},
                                "auto_correctable": {"type": "boolean"},
                            },
                        },
                        "description": "Issues that can be quickly fixed",
                    },
                    "user_actions_needed": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "issue": {"type": "string"},
                                "required_info": {"type": "string"},
                                "example": {"type": "string"},
                            },
                        },
                        "description": "Issues requiring user input",
                    },
                    "severity_assessment": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "success"],
                        "description": "Overall severity",
                    },
                    "suggested_workflow": {"type": "string", "description": "Step-by-step recommended fix workflow"},
                    "estimated_fix_time": {"type": "string", "description": "Estimated time to fix all issues"},
                },
                "required": ["grouped_issues", "priority_order", "severity_assessment", "suggested_workflow"],
            }

            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                f"Smart validation analysis complete: {response.get('severity_assessment')} severity",
                {
                    "priority_issues": len(response.get("priority_order", [])),
                    "quick_fixes": len(response.get("quick_fixes", [])),
                    "user_actions": len(response.get("user_actions_needed", [])),
                },
            )

            return dict(response)  # Cast Any to dict

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Smart validation analysis failed, using fallback: {e}",
            )
            return self._basic_validation_analysis(validation_result)

    def _basic_validation_analysis(
        self,
        validation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Fallback validation analysis without LLM."""
        issues = validation_result.get("issues", [])

        # Basic grouping by severity
        grouped = {
            "critical": [i for i in issues if i.get("severity") == "CRITICAL"],
            "errors": [i for i in issues if i.get("severity") == "ERROR"],
            "warnings": [i for i in issues if i.get("severity") == "WARNING"],
            "info": [i for i in issues if i.get("severity") == "INFO"],
        }

        # Basic severity assessment
        if grouped["critical"]:
            severity = "critical"
        elif grouped["errors"]:
            severity = "high"
        elif grouped["warnings"]:
            severity = "medium"
        else:
            severity = "low"

        return {
            "grouped_issues": grouped,
            "priority_order": [
                {"issue": i.get("message"), "priority": "P0", "reason": "Validation issue"} for i in issues[:10]
            ],
            "quick_fixes": [],
            "user_actions_needed": [],
            "severity_assessment": severity,
            "suggested_workflow": "Review validation issues and provide missing metadata",
        }
