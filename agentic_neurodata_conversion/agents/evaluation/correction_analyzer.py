"""Correction analysis module for evaluation agent.

Handles:
- LLM-powered correction analysis for failed validations
- Actionable correction suggestions
- Root cause analysis
- Retry vs manual intervention decisions
"""

import logging
from typing import TYPE_CHECKING, Any

from agentic_neurodata_conversion.models import CorrectionContext, GlobalState

if TYPE_CHECKING:
    from agentic_neurodata_conversion.services import LLMService

logger = logging.getLogger(__name__)


class CorrectionAnalyzer:
    """Handles intelligent correction analysis using LLM.

    Features:
    - Analyzes validation failures for root causes
    - Suggests specific, actionable corrections
    - Determines if issues are auto-fixable
    - Recommends retry vs manual intervention
    """

    def __init__(self, llm_service: "LLMService | None" = None):
        """Initialize correction analyzer.

        Args:
            llm_service: Optional LLM service for intelligent analysis
        """
        self._llm_service = llm_service

    async def analyze_with_llm(
        self,
        correction_context: CorrectionContext,
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to analyze validation issues and suggest corrections.

        Args:
            correction_context: Context for correction analysis
            state: Global state

        Returns:
            Dictionary with correction suggestions including:
            - analysis: Root cause analysis
            - suggestions: List of actionable corrections
            - recommended_action: retry, manual_intervention, or accept_warnings
        """
        if not self._llm_service:
            raise ValueError("LLM service is required for correction analysis")

        # Build prompt
        prompt = self.build_correction_prompt(correction_context)

        # Define output schema
        output_schema = {
            "type": "object",
            "properties": {
                "analysis": {"type": "string"},
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "severity": {"type": "string"},
                            "suggestion": {"type": "string"},
                            "actionable": {"type": "boolean"},
                        },
                    },
                },
                "recommended_action": {
                    "type": "string",
                    "enum": ["retry", "manual_intervention", "accept_warnings"],
                },
            },
        }

        # Call LLM
        result = await self._llm_service.generate_structured_output(
            prompt=prompt,
            output_schema=output_schema,
            system_prompt="You are an expert in NWB (Neurodata Without Borders) file format and validation. Analyze validation issues and suggest corrections.",
        )

        return dict(result)  # Cast Any to dict

    def build_correction_prompt(self, context: CorrectionContext) -> str:
        """Build LLM prompt for correction analysis.

        Args:
            context: Correction context containing:
                    - validation_result: Validation issues
                    - input_metadata: Original metadata
                    - conversion_parameters: Conversion settings
                    - previous_attempts: Prior correction attempts

        Returns:
            Formatted prompt string for LLM
        """
        issues_text = "\n".join(
            [
                f"- [{issue.severity.value.upper()}] {issue.message}"
                + (f" (at {issue.location})" if issue.location else "")
                for issue in context.validation_result.issues[:20]  # Limit to 20 issues
            ]
        )

        if len(context.validation_result.issues) > 20:
            issues_text += f"\n... and {len(context.validation_result.issues) - 20} more issues"

        prompt = f"""# NWB Validation Issues

## Summary
- Total issues: {len(context.validation_result.issues)}
- Critical: {context.validation_result.summary.get("critical", 0)}
- Errors: {context.validation_result.summary.get("error", 0)}
- Warnings: {context.validation_result.summary.get("warning", 0)}

## Issues
{issues_text}

## Conversion Parameters
{context.conversion_parameters}

## Previous Attempts
{len(context.previous_attempts)} previous correction attempts

## Task
Analyze these validation issues and provide:
1. A brief analysis of the root causes
2. Specific, actionable suggestions for each major issue
3. A recommended action (retry, manual_intervention, or accept_warnings)

Focus on the most critical issues first."""

        return prompt
