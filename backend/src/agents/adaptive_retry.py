"""Adaptive Retry Strategy for Intelligent Error Recovery.

This module implements smart retry logic that:
1. Analyzes validation failure patterns
2. Learns from previous retry attempts
3. Suggests different approaches based on failure types
4. Determines when to ask user for help vs. retry automatically
"""

import json
import logging
from typing import Any

from models import GlobalState, LogLevel
from services import LLMService

logger = logging.getLogger(__name__)


class AdaptiveRetryStrategy:
    """Intelligent retry strategy that learns from failures.

    Instead of blindly retrying the same approach, this analyzes:
    - What failed and why
    - What we've tried before
    - Whether we're making progress
    - What different approach might work better
    """

    def __init__(self, llm_service: LLMService | None = None):
        """Initialize adaptive retry strategy.

        Args:
            llm_service: Optional LLM service for intelligent analysis
        """
        self.llm_service = llm_service

    async def analyze_and_recommend_strategy(
        self,
        state: GlobalState,
        current_validation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze failure pattern and recommend next retry strategy.

        Args:
            state: Global conversion state with history
            current_validation_result: Latest validation result

        Returns:
            Dictionary with:
            - should_retry: bool - whether to retry at all
            - strategy: str - recommended strategy
            - approach: str - specific approach to try
            - message: str - explanation for user
            - ask_user: bool - whether to ask user for input
        """
        try:
            # Extract failure history
            attempt_num = state.correction_attempt
            previous_issues = self._extract_previous_issues(state)
            current_issues = current_validation_result.get("issues", [])

            # Quick heuristic checks
            if attempt_num >= 5:
                # Too many attempts - likely fundamental problem
                return {
                    "should_retry": False,
                    "strategy": "stop",
                    "approach": "manual_intervention",
                    "message": "After 5 attempts, the issues persist. Manual review of metadata is recommended.",
                    "ask_user": True,
                }

            # Check if we're making progress
            progress_analysis = self._analyze_progress(previous_issues, current_issues)

            if not progress_analysis["making_progress"] and attempt_num >= 3:
                # Stuck - not making progress
                return {
                    "should_retry": False,
                    "strategy": "stop",
                    "approach": "ask_user",
                    "message": "We're not making progress. Would you like to provide more information to help fix these issues?",
                    "ask_user": True,
                }

            # Use LLM for intelligent analysis (if available)
            if self.llm_service:
                llm_recommendation = await self._llm_powered_analysis(
                    state,
                    previous_issues,
                    current_issues,
                    progress_analysis,
                )
                return llm_recommendation

            # Fallback to heuristic strategy
            return self._heuristic_strategy(
                attempt_num,
                current_issues,
                progress_analysis,
            )

        except Exception as e:
            logger.exception(f"Adaptive retry analysis failed: {e}")
            # Safe fallback
            return {
                "should_retry": state.correction_attempt < 3,
                "strategy": "simple_retry",
                "approach": "same_as_before",
                "message": "Retrying with the same approach.",
                "ask_user": False,
            }

    def _extract_previous_issues(self, state: GlobalState) -> list[dict[str, Any]]:
        """Extract issues from previous validation attempts."""
        # Look for previous validation results in logs or state
        previous_issues = []

        # Check if state stores previous validation results
        if hasattr(state, "previous_validation_results"):
            for result in state.previous_validation_results:
                previous_issues.extend(result.get("issues", []))

        return previous_issues

    def _analyze_progress(
        self,
        previous_issues: list[dict[str, Any]],
        current_issues: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze whether we're making progress across retries.

        Args:
            previous_issues: Issues from previous attempts
            current_issues: Issues from current attempt

        Returns:
            Dictionary with progress analysis
        """
        if not previous_issues:
            # First attempt - no comparison possible
            return {
                "making_progress": True,
                "issues_fixed": 0,
                "new_issues": 0,
                "persistent_issues": len(current_issues),
            }

        # Compare issue counts
        prev_count = len(previous_issues)
        curr_count = len(current_issues)

        # Extract issue types
        prev_types = {issue.get("check_function_name") for issue in previous_issues}
        curr_types = {issue.get("check_function_name") for issue in current_issues}

        issues_fixed = len(prev_types - curr_types)
        new_issues = len(curr_types - prev_types)
        persistent = len(prev_types & curr_types)

        making_progress = (
            curr_count < prev_count or issues_fixed > new_issues  # Fewer total issues  # Fixed more than introduced
        )

        return {
            "making_progress": making_progress,
            "issues_fixed": issues_fixed,
            "new_issues": new_issues,
            "persistent_issues": persistent,
            "issue_count_change": curr_count - prev_count,
        }

    async def _llm_powered_analysis(
        self,
        state: GlobalState,
        previous_issues: list[dict[str, Any]],
        current_issues: list[dict[str, Any]],
        progress_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Use LLM to intelligently analyze failure pattern and recommend strategy.

        Args:
            state: Global conversion state
            previous_issues: Previous validation issues
            current_issues: Current validation issues
            progress_analysis: Progress analysis result

        Returns:
            Recommendation dictionary
        """
        system_prompt = """You are an expert at analyzing NWB file validation failures and recommending retry strategies.

Your job is to:
1. Analyze the pattern of validation failures across retry attempts
2. Determine if we're making progress or stuck
3. Identify root causes of persistent issues
4. Recommend a specific retry strategy that addresses the root cause
5. Decide if we should ask the user for help

Be strategic and adaptive - don't just retry the same thing repeatedly."""

        # Format issues for LLM
        prev_summary = self._format_issues_summary(previous_issues)
        curr_summary = self._format_issues_summary(current_issues)

        user_prompt = f"""Analyze this validation failure pattern:

**Attempt #{state.correction_attempt}**

**Progress Analysis:**
- Making progress: {progress_analysis["making_progress"]}
- Issues fixed: {progress_analysis["issues_fixed"]}
- New issues: {progress_analysis["new_issues"]}
- Persistent issues: {progress_analysis["persistent_issues"]}

**Previous Issues:**
{prev_summary}

**Current Issues:**
{curr_summary}

**Metadata State:**
{json.dumps(state.metadata, indent=2, default=str)[:500]}

**Task:**
1. Are we making progress or stuck in a loop?
2. What's the root cause of persistent issues?
3. Should we retry, ask user for help, or stop?
4. If retry, what different approach should we try?

Recommend a specific strategy."""

        output_schema = {
            "type": "object",
            "properties": {
                "should_retry": {
                    "type": "boolean",
                    "description": "Whether to retry at all",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["retry_with_changes", "ask_user", "stop"],
                    "description": "Overall strategy",
                },
                "approach": {
                    "type": "string",
                    "description": "Specific approach to try (e.g., 'focus_on_subject_metadata', 'ask_for_experimenter')",
                },
                "root_cause": {
                    "type": "string",
                    "description": "Identified root cause of failures",
                },
                "message": {
                    "type": "string",
                    "description": "User-friendly explanation",
                },
                "ask_user": {
                    "type": "boolean",
                    "description": "Whether to ask user for input",
                },
                "questions_for_user": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific questions to ask user if ask_user is true",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Explanation of why this strategy was chosen",
                },
            },
            "required": ["should_retry", "strategy", "approach", "message", "ask_user"],
        }

        try:
            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "LLM adaptive retry analysis completed",
                {
                    "strategy": response.get("strategy"),
                    "approach": response.get("approach"),
                    "should_retry": response.get("should_retry"),
                },
            )

            return dict(response)  # Cast Any to dict

        except Exception as e:
            logger.exception(f"LLM retry analysis failed: {e}")
            # Fallback to heuristic
            return self._heuristic_strategy(
                state.correction_attempt,
                current_issues,
                progress_analysis,
            )

    def _heuristic_strategy(
        self,
        attempt_num: int,
        current_issues: list[dict[str, Any]],
        progress_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Fallback heuristic strategy when LLM unavailable.

        Args:
            attempt_num: Current attempt number
            current_issues: Current validation issues
            progress_analysis: Progress analysis result

        Returns:
            Strategy recommendation
        """
        # Simple heuristic rules
        if attempt_num >= 5:
            return {
                "should_retry": False,
                "strategy": "stop",
                "approach": "manual",
                "message": "Maximum retry attempts reached. Manual review recommended.",
                "ask_user": True,
            }

        if not progress_analysis["making_progress"] and attempt_num >= 2:
            return {
                "should_retry": False,
                "strategy": "ask_user",
                "approach": "request_help",
                "message": "We're not making progress. Could you provide additional information?",
                "ask_user": True,
            }

        # Check issue types
        has_metadata_issues = any("metadata" in str(issue.get("message", "")).lower() for issue in current_issues)

        if has_metadata_issues:
            return {
                "should_retry": True,
                "strategy": "retry_with_changes",
                "approach": "focus_on_metadata",
                "message": "Retrying with improved metadata handling.",
                "ask_user": False,
            }

        # Default: simple retry
        return {
            "should_retry": True,
            "strategy": "retry_with_changes",
            "approach": "same_as_before",
            "message": "Retrying the conversion.",
            "ask_user": False,
        }

    def _format_issues_summary(self, issues: list[dict[str, Any]]) -> str:
        """Format issues into readable summary for LLM."""
        if not issues:
            return "No issues"

        # Group by severity
        by_severity: dict[str, list[dict[str, Any]]] = {}
        for issue in issues[:20]:  # Limit to first 20
            severity = issue.get("severity", "UNKNOWN")
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(issue)

        lines = []
        for severity, severity_issues in sorted(by_severity.items()):
            lines.append(f"\n{severity} ({len(severity_issues)} issues):")
            for issue in severity_issues[:5]:  # Show first 5 per severity
                lines.append(f"  - {issue.get('message', 'No message')}")

        if len(issues) > 20:
            lines.append(f"\n... and {len(issues) - 20} more issues")

        return "\n".join(lines)
