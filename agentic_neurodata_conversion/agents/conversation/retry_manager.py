"""Retry logic and error recovery management.

Handles retry decisions, error explanations, correction prompt generation,
and auto-fix processing for failed conversions.
"""

from typing import Any, cast

from agentic_neurodata_conversion.agents.metadata.intelligent_mapper import IntelligentMetadataMapper
from agentic_neurodata_conversion.models import (
    GlobalState,
    LogLevel,
)
from agentic_neurodata_conversion.services import LLMService


class RetryManager:
    """Manages retry logic, error recovery, and correction workflows."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        metadata_mapper: IntelligentMetadataMapper | None = None,
    ):
        """Initialize retry manager.

        Args:
            llm_service: Optional LLM service for error explanations and corrections
            metadata_mapper: Optional metadata mapper for intelligent corrections
        """
        self._llm_service = llm_service
        self._metadata_mapper = metadata_mapper

    async def explain_error_to_user(
        self,
        error: dict[str, Any],
        context: dict[str, Any],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to explain errors in user-friendly terms.

        Transforms technical error messages into actionable guidance.
        This makes errors understandable and helps users know what to do next.

        Args:
            error: Error details from failed operation
            context: Context about what was being attempted
            state: Global state with conversion details

        Returns:
            Dict with user-friendly explanation and suggested actions
        """
        if not self._llm_service:
            # Fallback to basic explanation without LLM
            return {
                "explanation": error.get("message", "An error occurred during conversion"),
                "likely_cause": "Unknown",
                "suggested_actions": ["Check the logs for more details", "Try uploading a different file"],
                "is_recoverable": False,
            }

        try:
            system_prompt = """You are an expert at explaining technical errors in simple, helpful terms.

Your role is to help neuroscientists understand what went wrong during data conversion and guide them toward a solution.

Be:
- Clear and non-technical (avoid jargon)
- Empathetic and encouraging
- Actionable (tell them what to do next)
- Honest about whether the issue is fixable"""

            user_prompt = f"""A data conversion error occurred. Help the user understand what happened and what to do next.

Error Details:
- Message: {error.get("message", "Unknown error")}
- Code: {error.get("code", "UNKNOWN")}
- Context: {error.get("context", {})}

Conversion Context:
- Format: {context.get("format", "unknown")}
- Input file: {context.get("input_path", "unknown")}
- What was happening: {context.get("operation", "conversion")}

Provide:
1. Simple explanation of what went wrong (no technical jargon)
2. Likely cause (why this might have happened)
3. Specific actions the user can take
4. Whether this issue is fixable

Respond in JSON format."""

            output_schema = {
                "type": "object",
                "properties": {
                    "explanation": {"type": "string", "description": "Simple, clear explanation of what went wrong"},
                    "likely_cause": {"type": "string", "description": "Why this error probably occurred"},
                    "suggested_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific steps user can take to fix or work around the issue",
                    },
                    "is_recoverable": {
                        "type": "boolean",
                        "description": "Whether this error can be fixed by user action",
                    },
                    "help_url": {"type": "string", "description": "Optional URL to relevant documentation"},
                },
                "required": ["explanation", "likely_cause", "suggested_actions", "is_recoverable"],
            }

            explanation = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "Generated user-friendly error explanation",
                {"error_code": error.get("code")},
            )

            return dict(explanation)

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Failed to generate error explanation: {e}",
            )
            # Fallback to basic explanation
            return {
                "explanation": error.get("message", "An error occurred during conversion"),
                "likely_cause": "See logs for technical details",
                "suggested_actions": ["Check the error logs", "Contact support if the issue persists"],
                "is_recoverable": False,
            }

    async def generate_correction_prompts(
        self,
        issues: list[dict[str, Any]],
        context: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """Generate intelligent correction prompts for validation issues using LLM.

        Args:
            issues: List of validation issues
            context: Context about the conversion
            state: Global state

        Returns:
            User-friendly correction prompt message
        """
        if not self._llm_service:
            return self._generate_basic_correction_prompts(issues)

        try:
            system_prompt = """You are helping a neuroscientist fix validation issues in their NWB file.

Generate clear, actionable prompts that:
1. Explain what needs to be fixed (in simple terms)
2. Provide specific examples of correct values
3. Make it clear how to respond
4. Are encouraging and helpful"""

            # Group issues by severity
            critical_issues = [i for i in issues if i.get("severity") in ["CRITICAL", "ERROR"]]
            warning_issues = [i for i in issues if i.get("severity") == "WARNING"]

            user_prompt = f"""Generate a correction prompt for validation issues.

Critical Issues ({len(critical_issues)}):
{[{"message": i.get("message"), "location": i.get("location")} for i in critical_issues[:5]]}

Warnings ({len(warning_issues)}):
{[{"message": i.get("message"), "location": i.get("location")} for i in warning_issues[:3]]}

Context:
- Format: {context.get("format", "unknown")}
- Total issues: {len(issues)}

Create a friendly message that:
1. Highlights the critical issues first
2. Explains what metadata/fixes are needed
3. Provides examples
4. Asks the user to provide corrections"""

            output_schema = {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The correction prompt message"},
                    "required_fields": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["message"],
            }

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            return str(response.get("message", ""))

        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Failed to generate LLM correction prompt: {e}")
            return self._generate_basic_correction_prompts(issues)

    @staticmethod
    def _generate_basic_correction_prompts(issues: list[dict[str, Any]]) -> str:
        """Generate basic correction prompts without LLM.

        Args:
            issues: List of issues requiring user input

        Returns:
            Formatted prompt message
        """
        prompt = f"⚠️ Found {len(issues)} warnings that need your input:\n\n"
        for i, issue in enumerate(issues, 1):
            prompt += f"{i}. **{issue.get('check_name', 'Unknown')}**: {issue.get('message', '')}\n"
        prompt += "\nPlease provide the requested information to continue."
        return prompt

    def identify_user_input_required(self, corrections: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify which corrections require user input (cannot be auto-fixed).

        Args:
            corrections: Corrections dictionary with auto_fixes and user_required

        Returns:
            List of issues requiring user input
        """
        return cast(list[dict[str, Any]], corrections.get("user_required", []))

    def extract_auto_fixes(self, corrections: dict[str, Any]) -> dict[str, Any]:
        """Extract auto-fixable corrections from corrections dict.

        Args:
            corrections: Corrections dictionary

        Returns:
            Dictionary of auto-fixable corrections
        """
        return cast(dict[str, Any], corrections.get("auto_fixes", {}))

    def generate_auto_fix_summary(self, issues: list[dict[str, Any]]) -> str:
        """Generate a summary of auto-fixable issues for user approval.

        Args:
            issues: List of issues with suggested fixes

        Returns:
            Formatted summary message
        """
        if not issues:
            return "No auto-fixable issues found."

        summary = f"📝 **Auto-Fix Summary** ({len(issues)} issues)\n\n"

        for i, issue in enumerate(issues[:10], 1):  # Limit to 10 for readability
            issue_msg = issue.get("message", "Unknown issue")
            fix = issue.get("fix", {})
            field = fix.get("field", "unknown")
            new_value = fix.get("value", "N/A")

            summary += f"{i}. **{field}**: {issue_msg}\n"
            summary += f"   → Suggested fix: `{new_value}`\n\n"

        if len(issues) > 10:
            summary += f"... and {len(issues) - 10} more issues\n\n"

        summary += "**Approve these fixes?** (yes/no)"
        return summary

    def extract_fixes_from_issues(
        self,
        issues: list[dict[str, Any]],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Extract fix suggestions from validation issues.

        Args:
            issues: List of validation issues
            state: Global state

        Returns:
            Dictionary of field -> suggested_value
        """
        fixes = {}

        for issue in issues:
            # Try to infer fix from the issue
            fix = self._infer_fix_from_issue(issue, state)
            if fix:
                fixes[fix["field"]] = fix["value"]

        return fixes

    def _infer_fix_from_issue(self, issue: dict[str, Any], state: GlobalState) -> dict[str, Any] | None:
        """Infer a fix suggestion from a single validation issue.

        Args:
            issue: Validation issue
            state: Global state

        Returns:
            Fix suggestion dict with field and value, or None if cannot infer
        """
        message = issue.get("message", "").lower()

        # Pattern matching for common fixable issues
        if "missing" in message and "experimenter" in message:
            return {"field": "experimenter", "value": "Unknown, Researcher"}

        if "missing" in message and "institution" in message:
            return {"field": "institution", "value": "Unknown Institution"}

        if "missing" in message and "sex" in message:
            return {"field": "sex", "value": "U"}  # Unknown

        if "missing" in message and "species" in message:
            # Try to infer from state metadata
            inferred_species = state.auto_extracted_metadata.get("species")
            if inferred_species:
                return {"field": "species", "value": inferred_species}

        # Cannot infer fix for this issue
        return None
