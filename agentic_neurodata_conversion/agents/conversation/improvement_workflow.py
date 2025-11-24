"""Improvement workflow module for conversation agent.

Handles:
- User decision for PASSED_WITH_ISSUES validation
- Auto-fix approval workflow
- Correction analysis and application
- User input collection for issues
- Reconversion orchestration after improvements

This module manages the improvement loop when validation passes
but has warnings that can be fixed.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from agentic_neurodata_conversion.models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationStatus,
)

if TYPE_CHECKING:
    from agentic_neurodata_conversion.services import LLMService, MCPServer

logger = logging.getLogger(__name__)

# Maximum correction attempts (Story 8.4 line 883)
MAX_CORRECTION_ATTEMPTS = 5


class ImprovementWorkflow:
    """Manages the improvement workflow for PASSED_WITH_ISSUES validation.

    This class handles the improvement loop when validation passes but
    has warnings. Users can choose to:
    - "improve": Enter correction loop to fix warnings
    - "accept": Accept file as-is with warnings

    Features:
    - Auto-fix detection and approval
    - User input collection for non-fixable issues
    - LLM-powered correction prompts
    - Maximum attempt limiting
    - Reconversion orchestration
    """

    def __init__(
        self,
        mcp_server: "MCPServer",
        llm_service: Optional["LLMService"] = None,
    ):
        """Initialize improvement workflow manager.

        Args:
            mcp_server: MCP server for agent communication
            llm_service: Optional LLM service for intelligent prompts
        """
        self._mcp_server = mcp_server
        self._llm_service = llm_service

        logger.info("ImprovementWorkflow initialized")

    async def handle_improvement_decision(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Handle user decision for PASSED_WITH_ISSUES validation.

        When validation passes but has warnings, user chooses:
        - "improve" - Enter correction loop to fix warnings
        - "accept" - Accept file as-is and finalize

        Workflow for "improve":
        1. Check maximum correction attempts
        2. Increment correction attempt counter
        3. Analyze corrections via EvaluationAgent
        4. Categorize issues (auto-fixable vs user input required)
        5. Request user input or approval for auto-fixes
        6. Apply corrections and reconvert

        Args:
            message: MCP message with context containing 'decision'
            state: Global state

        Returns:
            MCPResponse with result
        """
        decision = message.context.get("decision")

        if decision == "accept":
            # User accepts file with warnings - finalize
            state.add_log(
                LogLevel.INFO,
                "User accepted file with warnings (PASSED_WITH_ISSUES)",
                {"validation_status": "passed_accepted"},
            )

            # BUG #4 FIX: Generate final PDF and text reports NOW that user has accepted
            # Previously these were generated prematurely before user decision
            eval_msg = MCPMessage(
                target_agent="evaluation",
                action="generate_report",
                context={
                    "validation_result": state.metadata.get("last_validation_result", {}),
                    "nwb_path": state.output_path,
                    "final_accepted": True,  # Flag to indicate this is post-acceptance
                },
            )

            eval_response = await self._mcp_server.send_message(eval_msg)

            if not eval_response.success:
                state.add_log(
                    LogLevel.WARNING,
                    "Failed to generate final reports after acceptance",
                    {"error": eval_response.error},
                )

            # Set final validation status
            await state.update_validation_status(ValidationStatus.PASSED_ACCEPTED)
            await state.update_status(ConversionStatus.COMPLETED)

            # Generate final message
            final_message = (
                "✅ File accepted as-is with warnings. "
                "Your NWB file is ready for download. "
                "You can view the warnings in the validation report."
            )

            # Clear llm_message to prevent duplicate display in status polling
            state.llm_message = None

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "completed",
                    "message": final_message,
                    "validation_status": "passed_accepted",
                },
            )

        elif decision == "improve":
            # User wants to improve - enter correction loop
            state.add_log(
                LogLevel.INFO,
                "User chose to improve warnings (PASSED_WITH_ISSUES)",
                {"entering_correction_loop": True},
            )

            # Check if maximum correction attempts exceeded
            if state.correction_attempt >= MAX_CORRECTION_ATTEMPTS:
                state.add_log(
                    LogLevel.WARNING,
                    f"Maximum correction attempts ({MAX_CORRECTION_ATTEMPTS}) reached",
                    {"current_attempt": state.correction_attempt},
                )

                # Clear stale state
                state.llm_message = None
                state.correction_context = None

                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="MAX_CORRECTIONS_EXCEEDED",
                    error_message=(
                        f"⚠️ Maximum correction attempts ({MAX_CORRECTION_ATTEMPTS}) reached. "
                        f"Your file is technically valid but has {len(state.metadata.get('last_validation_result', {}).get('issues', []))} remaining issue(s). "
                        f"You can:\n\n"
                        f"• **Accept the file as-is** - Click 'Accept As-Is' button\n"
                        f"• **Start fresh** - Upload the file again with different metadata\n"
                        f"• **Download and manually edit** - Fix issues in a local NWB editor"
                    ),
                    error_context={
                        "correction_attempt": state.correction_attempt,
                        "max_attempts": MAX_CORRECTION_ATTEMPTS,
                        "remaining_issues": len(state.metadata.get("last_validation_result", {}).get("issues", [])),
                    },
                )

            # Increment correction attempt
            state.increment_correction_attempt()

            # Get correction context from evaluation agent
            # This will categorize issues and prepare for reconversion
            eval_msg = MCPMessage(
                target_agent="evaluation",
                action="analyze_corrections",
                context={
                    "validation_result": state.metadata.get("last_validation_result", {}),
                    "correction_attempt": state.correction_attempt,
                },
            )

            eval_response = await self._mcp_server.send_message(eval_msg)

            if not eval_response.success:
                # Clear stale state on error
                state.llm_message = None
                state.correction_context = None
                state.conversation_type = None

                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="CORRECTION_ANALYSIS_FAILED",
                    error_message="Failed to analyze corrections",
                    error_context=eval_response.error,  # Include original error
                )

            correction_context = eval_response.result.get("corrections", {})

            # Categorize issues
            auto_fixable = correction_context.get("auto_fixable_issues", [])
            user_input_required = correction_context.get("user_input_required", [])

            # If user input is needed, request it
            if user_input_required:
                # Generate smart prompts for missing data
                if self._llm_service:
                    prompt_msg = await self._generate_correction_prompts(
                        user_input_required,
                        state,
                    )
                else:
                    prompt_msg = self._generate_basic_correction_prompts(user_input_required)

                state.llm_message = prompt_msg
                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                state.conversation_type = "correction_input"

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "awaiting_user_input",
                        "message": prompt_msg,
                        "auto_fixable_count": len(auto_fixable),
                        "user_input_required_count": len(user_input_required),
                    },
                )

            # If only auto-fixable issues, ask user before auto-correcting
            else:
                state.add_log(
                    LogLevel.INFO,
                    f"Found {len(auto_fixable)} auto-fixable issues, asking user for approval",
                )

                # Store correction context for when user approves
                state.correction_context = correction_context

                # Generate summary of auto-fixable issues
                issue_summary = self._generate_auto_fix_summary(auto_fixable)

                # Ask user for approval
                approval_message = (
                    f"I found {len(auto_fixable)} issue(s) that I can fix automatically:\n\n"
                    f"{issue_summary}\n\n"
                    f"Would you like me to:\n"
                    f"• **Apply fixes automatically** - I'll fix these issues and reconvert the file\n"
                    f"• **Show details first** - See exactly what will be changed\n"
                    f"• **Cancel** - Keep the file as-is\n\n"
                    f"Please respond with 'apply', 'show details', or 'cancel'."
                )

                state.llm_message = approval_message
                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                state.conversation_type = "auto_fix_approval"

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "awaiting_user_input",
                        "message": approval_message,
                        "auto_fixable_count": len(auto_fixable),
                        "needs_approval": True,
                    },
                )

        else:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_DECISION",
                error_message=f"Invalid decision: {decision}. Must be 'improve' or 'accept'.",
            )

    async def _generate_correction_prompts(
        self,
        issues: list[dict[str, Any]],
        state: GlobalState,
    ) -> str:
        """Generate smart prompts for correction issues using LLM.

        Args:
            issues: List of issues requiring user input
            state: Global state

        Returns:
            Formatted prompt message
        """
        # If LLM is already processing, fall back to basic prompts
        if state.llm_processing:
            state.add_log(
                LogLevel.WARNING,
                "LLM already processing, using basic correction prompts",
            )
            return self._generate_basic_correction_prompts(issues)

        # Use LLM to generate contextual prompts with examples
        system_prompt = """You are helping a user fix validation warnings in their NWB file.
Generate clear, specific prompts for each issue with helpful examples."""

        user_prompt = f"""The NWB file has {len(issues)} warnings that need user input:

Issues:
{json.dumps(issues, indent=2)}

Generate a friendly message asking for the missing information. Include:
1. What needs to be fixed
2. Why it matters
3. Specific examples for each field

Format as a conversational message."""

        try:
            output_schema = {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Friendly prompt for user input"},
                },
                "required": ["prompt"],
            }

            if self._llm_service:
                response = await self._llm_service.generate_structured_output(
                    prompt=user_prompt,
                    output_schema=output_schema,
                    system_prompt=system_prompt,
                )

                return str(response.get("prompt", ""))

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate LLM correction prompts: {e}",
            )

        # Fallback to basic prompts
        return self._generate_basic_correction_prompts(issues)

    def _generate_basic_correction_prompts(self, issues: list[dict[str, Any]]) -> str:
        """Generate basic correction prompts without LLM.

        Args:
            issues: List of issues requiring user input

        Returns:
            Formatted prompt message
        """
        prompt = f"To improve your NWB file, please provide the following information ({len(issues)} field(s)):\n\n"

        for idx, issue in enumerate(issues, 1):
            field_name = issue.get("field_name", "unknown")
            reason = issue.get("reason", "No reason provided")
            help_text = issue.get("help_text", "")

            prompt += f"{idx}. **{field_name}**: {reason}\n"
            if help_text:
                prompt += f"   {help_text}\n"
            prompt += "\n"

        prompt += "Please provide the missing information in the format: field_name: value"

        return prompt

    def _generate_auto_fix_summary(self, auto_fixable: list[dict[str, Any]]) -> str:
        """Generate summary of auto-fixable issues.

        Args:
            auto_fixable: List of auto-fixable issues

        Returns:
            Formatted summary
        """
        if not auto_fixable:
            return "No auto-fixable issues found."

        summary_parts = []
        for idx, issue in enumerate(auto_fixable[:5], 1):  # Show first 5
            issue_desc = issue.get("issue", "Unknown issue")
            fix_desc = issue.get("suggested_fix", "Will be corrected")
            summary_parts.append(f"{idx}. {issue_desc} → {fix_desc}")

        if len(auto_fixable) > 5:
            summary_parts.append(f"... and {len(auto_fixable) - 5} more issues")

        return "\n".join(summary_parts)
