"""Retry workflow module for conversation agent.

Handles:
- User retry approval/rejection decisions
- Adaptive retry strategy analysis
- LLM-powered correction analysis
- Auto-fix extraction
- User input requirement identification
- Reconversion orchestration
- Progress tracking and no-progress detection

This module implements the retry workflow after validation failures,
including intelligent analysis of what failed and how to fix it.
"""

import logging
from typing import TYPE_CHECKING, Any, Optional, cast

from agentic_neurodata_conversion.models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationOutcome,
    ValidationStatus,
)

if TYPE_CHECKING:
    from agentic_neurodata_conversion.agents.error_handling.adaptive_retry import AdaptiveRetryStrategy
    from agentic_neurodata_conversion.services import LLMService, MCPServer

logger = logging.getLogger(__name__)


class RetryWorkflow:
    """Manages the retry workflow after validation failures.

    This class handles the complete retry cycle:
    - User decision processing (approve/reject/accept)
    - No-progress detection
    - Adaptive retry strategy recommendations
    - LLM correction analysis
    - Auto-fix extraction and application
    - User input requirement identification
    - Reconversion orchestration
    - Re-validation

    Features:
    - Intelligent retry recommendations based on issue patterns
    - Automatic extraction of fixable issues
    - Detection of issues requiring user input
    - Progress tracking to avoid infinite loops
    - Graceful degradation when LLM unavailable
    """

    def __init__(
        self,
        mcp_server: "MCPServer",
        adaptive_retry_strategy: Optional["AdaptiveRetryStrategy"] = None,
        llm_service: Optional["LLMService"] = None,
    ):
        """Initialize retry workflow manager.

        Args:
            mcp_server: MCP server for agent communication
            adaptive_retry_strategy: Optional adaptive retry strategy analyzer
            llm_service: Optional LLM service for intelligent analysis
        """
        self._mcp_server = mcp_server
        self._adaptive_retry_strategy = adaptive_retry_strategy
        self._llm_service = llm_service

        logger.info("RetryWorkflow initialized")

    async def handle_retry_decision(
        self,
        message: MCPMessage,
        state: GlobalState,
        handle_start_conversion_callback,  # Callback to start conversion workflow
    ) -> MCPResponse:
        """Handle user's retry approval/rejection.

        Processes the user's decision after validation failure:
        - "approve": Start retry with LLM analysis and corrections
        - "reject": Mark conversion as failed (user declined)
        - "accept": Accept file with warnings (only for PASSED_WITH_ISSUES)

        Workflow for "approve":
        1. Check for no-progress (same issues as last attempt)
        2. Run adaptive retry strategy analysis (if available)
        3. Analyze corrections with LLM
        4. Extract auto-fixes
        5. Identify user input requirements
        6. Apply corrections and reconvert
        7. Re-validate
        8. Report results

        Args:
            message: MCP message with user decision
            state: Global state
            handle_start_conversion_callback: Callback to restart conversion workflow

        Returns:
            MCPResponse with next steps
        """
        decision = message.context.get("decision")

        if decision not in ["approve", "reject", "accept"]:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_DECISION",
                error_message="decision must be 'approve', 'reject', or 'accept'",
            )

        if state.status != ConversionStatus.AWAITING_RETRY_APPROVAL:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_STATE",
                error_message=f"Cannot accept retry decision in state: {state.status}",
            )

        # Bug #3 fix: Handle "accept" for PASSED_WITH_ISSUES
        if decision == "accept":
            # Only valid for PASSED_WITH_ISSUES (has warnings but no critical errors)
            # Use enum comparison
            try:
                status_enum = (
                    ValidationOutcome(state.overall_status)
                    if isinstance(state.overall_status, str)
                    else state.overall_status
                )
            except (ValueError, AttributeError):
                status_enum = state.overall_status

            if status_enum != ValidationOutcome.PASSED_WITH_ISSUES:
                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="INVALID_DECISION",
                    error_message="'accept' decision only valid for PASSED_WITH_ISSUES status",
                )

            # Set validation_status to passed_accepted (Story 8.3a line 840)
            state.validation_status = ValidationStatus.PASSED_ACCEPTED
            await state.update_status(ConversionStatus.COMPLETED)
            state.add_log(
                LogLevel.INFO,
                "User accepted file with warnings (validation_status=passed_accepted)",
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "completed",
                    "validation_status": "passed_accepted",
                    "message": "File accepted with warnings. Download ready.",
                },
            )

        if decision == "reject":
            # Bug #7 fix: Set validation_status to failed_user_declined (Story 8.8 line 958)
            state.validation_status = ValidationStatus.FAILED_USER_DECLINED
            await state.update_status(ConversionStatus.FAILED)
            state.add_log(
                LogLevel.INFO,
                "User rejected retry (validation_status=failed_user_declined)",
            )
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "failed",
                    "validation_status": "failed_user_declined",
                    "message": "Conversion terminated by user",
                },
            )

        # User approved retry
        state.increment_retry()
        state.add_log(
            LogLevel.INFO,
            f"User approved retry (attempt {state.correction_attempt})",
        )

        # Get the most recent validation result from state
        # Note: In a production system, we'd store this more robustly
        validation_result_data = None
        for log in reversed(state.logs):
            if "validation" in log.context:
                validation_result_data = log.context.get("validation")
                break

        # Bug #11 fix: Detect "no progress" before starting retry (Story 4.7 lines 461-466)
        if validation_result_data:
            current_issues = validation_result_data.get("issues", [])

            # Check if we're making no progress
            if state.detect_no_progress(current_issues):
                state.add_log(
                    LogLevel.WARNING,
                    "No progress detected - same validation errors with no changes applied",
                    {
                        "correction_attempt": state.correction_attempt,
                        "issue_count": len(current_issues),
                    },
                )

                # Warn user and ask for confirmation
                (
                    f"⚠️ No changes detected since last attempt (attempt #{state.correction_attempt}).\n\n"
                    f"The same {len(current_issues)} validation errors still exist because:\n"
                    f"- No user input was provided\n"
                    f"- No automatic corrections were applied\n\n"
                    f"Retrying with no changes will likely produce the same errors.\n\n"
                    f"**Recommended actions:**\n"
                    f"1. Provide additional information when prompted\n"
                    f"2. Check if the source data files have the required information\n"
                    f"3. Consider declining this retry if data cannot be corrected\n\n"
                    f"Would you still like to proceed with retry?"
                )

                # For now, log the warning and continue (actual UI confirmation can be added later)
                state.add_log(
                    LogLevel.WARNING,
                    "Proceeding with retry despite no progress warning",
                )

            # Store current issues for next iteration's comparison
            state.previous_validation_issues = current_issues

            # Reset the "changes made" flags for this new attempt
            state.user_provided_input_this_attempt = False
            state.auto_corrections_applied_this_attempt = False

        # Use adaptive retry strategy to determine best approach
        if self._adaptive_retry_strategy and validation_result_data:
            state.add_log(
                LogLevel.INFO,
                "Running adaptive retry analysis",
            )

            try:
                retry_recommendation = await self._adaptive_retry_strategy.analyze_and_recommend_strategy(
                    state=state,
                    current_validation_result=validation_result_data,
                )

                state.add_log(
                    LogLevel.INFO,
                    "Adaptive retry recommendation",
                    {
                        "should_retry": retry_recommendation.get("should_retry"),
                        "strategy": retry_recommendation.get("strategy"),
                        "approach": retry_recommendation.get("approach"),
                    },
                )

                # Check if we should ask user for help instead of retrying
                if retry_recommendation.get("ask_user"):
                    await state.update_status(ConversionStatus.AWAITING_USER_INPUT)

                    user_message = retry_recommendation.get("message", "We need your help to fix these issues.")

                    # Add specific questions if provided
                    questions = retry_recommendation.get("questions_for_user", [])
                    if questions:
                        user_message += "\n\n" + "\n".join(f"• {q}" for q in questions)

                    state.add_log(
                        LogLevel.INFO,
                        "Asking user for help based on adaptive retry analysis",
                    )

                    return MCPResponse.success_response(
                        reply_to=message.message_id,
                        result={
                            "status": "awaiting_user_input",
                            "message": user_message,
                            "needs_user_input": True,
                            "retry_recommendation": retry_recommendation,
                        },
                    )

                # If recommended not to retry, inform user
                if not retry_recommendation.get("should_retry"):
                    state.validation_status = ValidationStatus.FAILED_PERSISTENT
                    await state.update_status(ConversionStatus.FAILED)

                    state.add_log(
                        LogLevel.INFO,
                        "Adaptive retry recommends stopping attempts",
                    )

                    return MCPResponse.success_response(
                        reply_to=message.message_id,
                        result={
                            "status": "failed",
                            "validation_status": "failed_persistent",
                            "message": retry_recommendation.get("message"),
                            "retry_recommendation": retry_recommendation,
                        },
                    )

                # Store the recommended approach for use during retry
                state.metadata["_retry_approach"] = retry_recommendation.get("approach")
                state.metadata["_retry_reasoning"] = retry_recommendation.get("reasoning", "")

            except Exception as e:
                state.add_log(
                    LogLevel.WARNING,
                    f"Adaptive retry analysis failed (non-critical): {e}",
                )
                # Continue with normal retry if analysis fails

        # Analyze corrections with LLM if available
        if self._llm_service:
            await state.update_status(ConversionStatus.CONVERTING)
            state.add_log(
                LogLevel.INFO,
                "Analyzing validation issues with LLM for corrections",
            )

            if validation_result_data:
                # Send message to evaluation agent to analyze corrections
                analysis_response = await self._mcp_server.send_message(
                    MCPMessage(
                        target_agent="evaluation",
                        action="analyze_corrections",
                        context={
                            "validation_result": validation_result_data,
                            "input_metadata": state.metadata,
                            "conversion_parameters": {},
                        },
                    )
                )

                if analysis_response.success:
                    corrections = analysis_response.result.get("corrections", {})
                    state.add_log(
                        LogLevel.INFO,
                        "LLM correction analysis completed",
                        {
                            "analysis": corrections.get("analysis", ""),
                            "suggestions_count": len(corrections.get("suggestions", [])),
                            "recommended_action": corrections.get("recommended_action", ""),
                        },
                    )

                    # Extract automatic fixes from LLM suggestions
                    auto_fixes = self._extract_auto_fixes(corrections)

                    # Check if there are non-fixable issues requiring user input
                    user_input_required = self._identify_user_input_required(corrections)

                    if user_input_required:
                        # Some issues need user input - transition to AWAITING_USER_INPUT state
                        await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                        state.add_log(
                            LogLevel.INFO,
                            f"User input required for {len(user_input_required)} issues",
                            {"required_fields": user_input_required},
                        )
                        return MCPResponse.success_response(
                            reply_to=message.message_id,
                            result={
                                "status": "awaiting_user_input",
                                "required_fields": user_input_required,
                                "auto_fixes": auto_fixes,
                                "message": "Additional user input required to complete correction",
                            },
                        )

                    # Send corrections to conversion agent
                    # Bug #11 fix: Mark if auto-corrections are being applied
                    if auto_fixes:
                        state.auto_corrections_applied_this_attempt = True

                    correction_response = await self._mcp_server.send_message(
                        MCPMessage(
                            target_agent="conversion",
                            action="apply_corrections",
                            context={
                                "correction_context": corrections,
                                "auto_fixes": auto_fixes,
                                "user_input": {},
                            },
                        )
                    )

                    if correction_response.success:
                        state.add_log(
                            LogLevel.INFO,
                            "Corrections applied and reconversion successful",
                        )

                        # Re-run validation on corrected file
                        validation_response = await self._mcp_server.send_message(
                            MCPMessage(
                                target_agent="evaluation",
                                action="run_validation",
                                context={"nwb_path": state.output_path},
                            )
                        )

                        if validation_response.success:
                            validation_result = validation_response.result.get("validation_result", {})
                            overall_status = validation_result.get("overall_status")
                            issues = validation_result.get("issues", [])

                            # Update state with new validation results
                            state.overall_status = overall_status
                            state.metadata["last_validation_result"] = validation_result

                            # Track improvement progress
                            old_issue_count = len(
                                state.metadata.get("previous_validation_result", {}).get("issues", [])
                            )
                            new_issue_count = len(issues)

                            state.add_log(
                                LogLevel.INFO,
                                f"Re-validation completed: {overall_status}, issues: {old_issue_count} → {new_issue_count}",
                                {"overall_status": overall_status, "issue_count": new_issue_count},
                            )

                            # Generate report after validation
                            report_response = await self._mcp_server.send_message(
                                MCPMessage(
                                    target_agent="evaluation",
                                    action="generate_report",
                                    context={
                                        "validation_result": validation_result,
                                        "nwb_path": state.output_path,
                                    },
                                )
                            )

                            if report_response.success:
                                state.add_log(
                                    LogLevel.INFO,
                                    f"Report generated: {report_response.result.get('report_path')}",
                                )

                            # Clear stale state variables
                            state.llm_message = None
                            state.correction_context = None

                            # Handle different validation outcomes
                            if overall_status == "PASSED_WITH_ISSUES":
                                # Still has issues - offer improvement again
                                state.add_log(
                                    LogLevel.INFO,
                                    "Corrections applied but issues remain - offering improvement again",
                                )

                                # Warn if corrections made things worse
                                if new_issue_count > old_issue_count:
                                    state.add_log(
                                        LogLevel.WARNING,
                                        f"Corrections resulted in MORE issues: {old_issue_count} → {new_issue_count}",
                                    )

                                await state.update_validation_status(ValidationStatus.PASSED_WITH_ISSUES)
                                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                                state.conversation_type = "improvement_decision"

                                improvement_msg = f"✅ Corrections applied! The file is improved but still has {new_issue_count} issue(s).\n\n"

                                if new_issue_count > old_issue_count:
                                    improvement_msg += (
                                        f"⚠️ Note: The issue count increased from {old_issue_count} to {new_issue_count}. "
                                        f"This can happen when corrections reveal additional issues.\n\n"
                                    )

                                improvement_msg += "Would you like to improve the file further, or accept it as-is?"

                                return MCPResponse.success_response(
                                    reply_to=message.message_id,
                                    result={
                                        "status": "passed_with_issues",
                                        "message": improvement_msg,
                                        "overall_status": overall_status,
                                        "issue_count": new_issue_count,
                                        "correction_attempt": state.correction_attempt,
                                    },
                                )

                            elif overall_status == "PASSED":
                                # All issues fixed!
                                state.add_log(
                                    LogLevel.INFO,
                                    "All issues fixed after corrections - marking as completed",
                                )
                                await state.update_validation_status(ValidationStatus.PASSED)
                                await state.update_status(ConversionStatus.COMPLETED)
                                state.conversation_type = None

                                return MCPResponse.success_response(
                                    reply_to=message.message_id,
                                    result={
                                        "status": "completed",
                                        "message": "✅ Success! All issues have been fixed. Your NWB file is ready for download.",
                                        "overall_status": overall_status,
                                        "output_path": state.output_path,
                                        "correction_attempt": state.correction_attempt,
                                    },
                                )

                            elif overall_status == "FAILED":
                                # Corrections caused failures
                                state.add_log(
                                    LogLevel.ERROR,
                                    "Corrections caused validation failure",
                                )
                                await state.update_validation_status(ValidationStatus.FAILED)
                                await state.update_status(ConversionStatus.AWAITING_RETRY_APPROVAL)
                                state.conversation_type = "validation_analysis"

                                return MCPResponse.success_response(
                                    reply_to=message.message_id,
                                    result={
                                        "status": "failed",
                                        "message": "❌ After applying corrections, the file now has critical errors. Would you like to retry with different metadata?",
                                        "overall_status": overall_status,
                                        "issue_count": new_issue_count,
                                    },
                                )

                        # If validation failed
                        return MCPResponse.success_response(
                            reply_to=message.message_id,
                            result={
                                "status": "reconversion_completed",
                                "output_path": state.output_path,
                                "attempt": state.correction_attempt,
                            },
                        )
                    else:
                        state.add_log(
                            LogLevel.ERROR,
                            f"Correction application failed: {correction_response.error.get('message', 'Unknown error')}",
                        )
                        return correction_response
                else:
                    state.add_log(
                        LogLevel.WARNING,
                        f"LLM analysis failed: {analysis_response.error.get('message', 'Unknown error')}",
                    )

            # If no LLM analysis, just restart without corrections
            # ✅ FIX: Use pending_conversion_input_path with fallback
            conversion_path = state.pending_conversion_input_path or state.input_path
            if not conversion_path or str(conversion_path) == "None":
                state.add_log(
                    LogLevel.ERROR,
                    "Cannot restart conversion - input_path not available",
                    {
                        "pending_conversion_input_path": (
                            str(state.pending_conversion_input_path) if state.pending_conversion_input_path else "None"
                        ),
                        "input_path": str(state.input_path) if state.input_path else "None",
                    },
                )
                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with retry. The file path is not available. Please try uploading the file again.",
                )

            restart_response = await handle_start_conversion_callback(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(conversion_path),
                        "metadata": state.metadata,
                    },
                ),
                state,
            )
            return cast(MCPResponse, restart_response)
        else:
            # No LLM available - ask user for manual corrections
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
            state.add_log(
                LogLevel.WARNING,
                "No LLM service available - cannot auto-analyze corrections",
            )
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "awaiting_corrections",
                    "message": "Please provide corrections manually (LLM not configured)",
                },
            )

    def _identify_user_input_required(self, corrections: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify issues that require user input to fix.

        Implements Story 8.6: User Input Request

        Args:
            corrections: LLM correction analysis

        Returns:
            List of required user input fields with metadata
        """
        required_fields = []
        suggestions = corrections.get("suggestions", [])

        for suggestion in suggestions:
            # Check if this issue requires user input (not actionable by system)
            if suggestion.get("actionable", False):
                # Skip actionable suggestions - they can be auto-fixed
                continue

            issue = suggestion.get("issue", "").lower()
            suggestion_text = suggestion.get("suggestion", "").lower()

            # Identify specific fields that need user input
            if "subject_id" in issue and ("missing" in issue or "empty" in issue):
                required_fields.append(
                    {
                        "field_name": "subject_id",
                        "label": "Subject ID",
                        "type": "text",
                        "required": True,
                        "help_text": "Unique identifier for the experimental subject",
                        "reason": suggestion.get("issue", ""),
                    }
                )

            elif "session_description" in issue and "too short" in suggestion_text:
                required_fields.append(
                    {
                        "field_name": "session_description",
                        "label": "Session Description",
                        "type": "textarea",
                        "required": True,
                        "help_text": "Detailed description of the experimental session (minimum 20 characters)",
                        "reason": suggestion.get("issue", ""),
                    }
                )

            elif "experimenter" in issue and ("missing" in issue or "empty" in issue):
                required_fields.append(
                    {
                        "field_name": "experimenter",
                        "label": "Experimenter Name(s)",
                        "type": "text",
                        "required": True,
                        "help_text": "Name(s) of experimenter(s) who conducted the session (comma-separated)",
                        "reason": suggestion.get("issue", ""),
                    }
                )

            elif "institution" in issue and "empty" not in suggestion_text:
                required_fields.append(
                    {
                        "field_name": "institution",
                        "label": "Institution",
                        "type": "text",
                        "required": False,
                        "help_text": "Institution where the experiment was conducted",
                        "reason": suggestion.get("issue", ""),
                    }
                )

        return required_fields

    def _extract_auto_fixes(self, corrections: dict[str, Any]) -> dict[str, Any]:
        """Extract automatically fixable corrections from LLM analysis.

        Implements Story 8.5: Automatic Issue Correction

        Args:
            corrections: LLM correction analysis

        Returns:
            Dictionary of auto-fixable metadata fields
        """
        auto_fixes = {}

        suggestions = corrections.get("suggestions", [])

        for suggestion in suggestions:
            if not suggestion.get("actionable", False):
                continue

            issue = suggestion.get("issue", "").lower()
            suggestion_text = suggestion.get("suggestion", "").lower()

            # Parse common fixable issues
            # Note: This is a simple heuristic-based approach
            # In production, would use more sophisticated NLP or structured LLM output

            # Empty/missing fields that can have defaults
            if "subject_id" in issue and "subject_id" in suggestion_text:
                if "unknown" not in suggestion_text:
                    # Extract suggested value (simple parsing)
                    continue  # Skip for now - needs user input

            # Species defaults
            if "species" in issue:
                if "mouse" in suggestion_text or "mus musculus" in suggestion_text:
                    auto_fixes["species"] = "Mus musculus"
                elif "rat" in suggestion_text or "rattus" in suggestion_text:
                    auto_fixes["species"] = "Rattus norvegicus"

            # Session description minimum length
            if "session_description" in issue and "too short" in suggestion_text:
                # Can't auto-fix - needs actual description
                pass

            # Experimenter format
            if "experimenter" in issue and "format" in suggestion_text:
                # Can't auto-fix without knowing actual name
                pass

            # Institution/lab empty values
            if ("institution" in issue or "lab" in issue) and "empty" in suggestion_text:
                if "remove" in suggestion_text:
                    # Mark for removal (set to None)
                    if "institution" in issue:
                        auto_fixes["institution"] = None
                    if "lab" in issue:
                        auto_fixes["lab"] = None

        return auto_fixes
