"""Validation router for validation results, retry approval, and correction endpoints.

Handles:
- Validation results and issue reporting
- Retry approval decisions
- Improvement decisions for PASSED_WITH_ISSUES status
- Correction context and guidance
"""

import logging

from fastapi import APIRouter, Form, HTTPException

from agentic_neurodata_conversion.api.dependencies import get_or_create_mcp_server
from agentic_neurodata_conversion.models import (
    ConversionStatus,
    MCPMessage,
    RetryApprovalRequest,
    RetryApprovalResponse,
    ValidationResponse,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["validation"])


@router.get("/validation", response_model=ValidationResponse)
async def get_validation_results():
    """Get validation results.

    Retrieves validation results from the evaluation agent, including
    validation issues, severity counts, and overall validation status.

    For MVP, returns simplified validation info. In full implementation,
    this fetches detailed results from the evaluation agent.

    Returns:
        ValidationResponse with:
        - is_valid: Whether file passed validation
        - issues: List of validation issues
        - summary: Count of issues by severity (critical, error, warning, info)
    """
    get_or_create_mcp_server()

    # For MVP, return simplified validation info from logs
    # In full implementation, this would fetch from evaluation agent
    return ValidationResponse(
        is_valid=False,
        issues=[],
        summary={"critical": 0, "error": 0, "warning": 0, "info": 0},
    )


@router.get("/correction-context")
async def get_correction_context():
    """Get detailed correction context including issue breakdown.

    Provides comprehensive information about validation issues and suggested
    corrections. Issues are categorized as:
    - Auto-fixable: System can automatically correct
    - User input required: Requires manual user input or decision

    Returns:
        Dictionary containing:
        - status: Context availability status
        - correction_attempt: Current correction attempt number
        - can_retry: Whether retry is allowed
        - auto_fixable: List of auto-fixable issues with suggestions
        - user_input_required: List of issues requiring user input
        - validation_summary: Summary of validation issue counts
    """
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # Search logs for LLM correction guidance
    llm_guidance = None
    validation_result = None

    for log in reversed(state.logs):
        if "LLM correction guidance" in log.message or "corrections" in log.message.lower():
            # Try to extract correction data from log context
            if log.context:
                llm_guidance = log.context
        if "validation" in log.message.lower() and log.context and "overall_status" in log.context:
            validation_result = log.context

    if not llm_guidance and not validation_result:
        return {
            "status": "no_context",
            "message": "No correction context available",
            "auto_fixable": [],
            "user_input_required": [],
        }

    # Parse LLM guidance to extract issue breakdown
    auto_fixable = []
    user_input_required = []

    if llm_guidance:
        suggestions = llm_guidance.get("suggestions", [])
        for suggestion in suggestions:
            issue_info = {
                "issue": suggestion.get("issue", "Unknown issue"),
                "suggestion": suggestion.get("suggestion", ""),
                "severity": suggestion.get("severity", "info"),
            }

            if suggestion.get("actionable", False):
                auto_fixable.append(issue_info)
            else:
                user_input_required.append(issue_info)

    # If no specific suggestions, extract from validation result
    if not auto_fixable and not user_input_required and validation_result:
        summary = validation_result.get("summary", {})
        if summary.get("error", 0) > 0:
            auto_fixable.append(
                {
                    "issue": f"{summary['error']} validation errors found",
                    "suggestion": "System will attempt automatic corrections",
                    "severity": "error",
                }
            )

    return {
        "status": "available",
        "correction_attempt": state.correction_attempt,
        "can_retry": True,
        "auto_fixable": auto_fixable,
        "user_input_required": user_input_required,
        "validation_summary": validation_result.get("summary", {}) if validation_result else {},
    }


@router.post("/retry-approval", response_model=RetryApprovalResponse)
async def retry_approval(request: RetryApprovalRequest):
    """Submit retry approval decision.

    After validation fails, this endpoint allows the user to decide whether
    to retry with corrections or abort the conversion.

    Args:
        request: Retry approval request with decision (RETRY or ABORT)

    Returns:
        RetryApprovalResponse with:
        - accepted: Whether decision was accepted
        - message: Response message
        - new_status: New conversion status

    Raises:
        HTTPException 400: If retry decision failed or invalid state
    """
    mcp_server = get_or_create_mcp_server()

    retry_msg = MCPMessage(
        target_agent="conversation",
        action="retry_decision",
        context={"decision": request.decision.value},
    )

    response = await mcp_server.send_message(retry_msg)

    if not response.success:
        # Include validation issues and context in error response
        error_detail = {
            "message": response.error.get("message", "Retry decision failed"),
            "error_code": response.error.get("error_code", "RETRY_FAILED"),
        }

        # Include validation issues from state if available
        if mcp_server.global_state.metadata.get("last_validation_result"):
            validation_result = mcp_server.global_state.metadata["last_validation_result"]
            error_detail["validation_summary"] = validation_result.get("summary", {})

            # Include top critical issues
            issues = validation_result.get("issues", [])
            critical_issues = [
                issue
                for issue in issues[:5]
                if issue.get("severity") in ["CRITICAL", "ERROR"]  # Top 5 issues
            ]
            if critical_issues:
                error_detail["critical_issues"] = critical_issues

        # Add any additional error context
        if "error_context" in response.error:
            error_detail["context"] = response.error["error_context"]

        raise HTTPException(
            status_code=400,
            detail=error_detail,
        )

    new_status_str = response.result.get("status", "unknown")
    # Map string status to enum
    status_map = {
        "failed": ConversionStatus.FAILED,
        "analyzing_corrections": ConversionStatus.CONVERTING,
        "awaiting_corrections": ConversionStatus.AWAITING_USER_INPUT,
    }
    # If unknown status, preserve current status rather than resetting to IDLE
    new_status = status_map.get(
        new_status_str, mcp_server.global_state.status or ConversionStatus.AWAITING_RETRY_APPROVAL
    )

    return RetryApprovalResponse(
        accepted=True,
        message=response.result.get("message", "Decision accepted"),
        new_status=new_status,
    )


@router.post("/improvement-decision")
async def improvement_decision(decision: str = Form(...)):
    """Submit improvement decision for PASSED_WITH_ISSUES validation.

    When validation passes but has warnings, user can choose:
    - "improve" - Enter correction loop to fix warnings
    - "accept" - Accept file as-is and finalize

    This allows users to optionally improve files that are technically valid
    but have quality issues or best practice violations.

    Args:
        decision: "improve" or "accept"

    Returns:
        Dictionary containing:
        - accepted: Whether decision was accepted
        - message: Response message
        - status: Current conversion status

    Raises:
        HTTPException 400: If invalid decision value
        HTTPException 500: If decision processing failed
    """
    mcp_server = get_or_create_mcp_server()

    if decision not in ["improve", "accept"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'improve' or 'accept'",
        )

    # Send message to Conversation Agent
    improvement_msg = MCPMessage(
        target_agent="conversation",
        action="improvement_decision",
        context={"decision": decision},
    )

    response = await mcp_server.send_message(improvement_msg)

    if not response.success:
        # Include validation issues in error response for PASSED_WITH_ISSUES decisions
        error_detail = {
            "message": response.error.get("message", "Failed to process decision"),
            "error_code": response.error.get("error_code", "DECISION_FAILED"),
        }

        # Include validation warnings/issues that user was deciding about
        if mcp_server.global_state.metadata.get("last_validation_result"):
            validation_result = mcp_server.global_state.metadata["last_validation_result"]
            error_detail["validation_summary"] = validation_result.get("summary", {})

            # Include warning/info issues (not critical, since this is PASSED_WITH_ISSUES)
            issues = validation_result.get("issues", [])
            warning_issues = [
                issue
                for issue in issues[:10]  # Top 10 warnings
                if issue.get("severity") in ["WARNING", "BEST_PRACTICE", "INFO"]
            ]
            if warning_issues:
                error_detail["warning_issues"] = warning_issues

        # Add any additional error context
        if "error_context" in response.error:
            error_detail["context"] = response.error["error_context"]

        raise HTTPException(
            status_code=500,
            detail=error_detail,
        )

    return {
        "accepted": True,
        "message": response.result.get("message", "Decision accepted"),
        "status": mcp_server.global_state.status.value if mcp_server.global_state.status else "unknown",
    }
