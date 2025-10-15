"""
Evaluation Agent implementation.

Responsible for:
- NWB file validation using NWB Inspector
- Quality assessment
- Correction analysis (using LLM if available)
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from models import (
    ConversionStatus,
    CorrectionContext,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationResult,
    ValidationStatus,
)
from services import LLMService


class EvaluationAgent:
    """
    Evaluation agent for validation and quality assessment.

    This agent validates NWB files and performs quality checks.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the evaluation agent.

        Args:
            llm_service: Optional LLM service for correction analysis
        """
        self._llm_service = llm_service

    async def handle_run_validation(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Run NWB Inspector validation on an NWB file.

        Args:
            message: MCP message with context containing 'nwb_path'
            state: Global state

        Returns:
            MCPResponse with validation results
        """
        nwb_path = message.context.get("nwb_path")

        if not nwb_path:
            state.add_log(
                LogLevel.ERROR,
                "Missing nwb_path in validation request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_NWB_PATH",
                error_message="nwb_path is required for validation",
            )

        state.update_validation_status(ValidationStatus.RUNNING)
        state.add_log(
            LogLevel.INFO,
            f"Starting NWB validation: {nwb_path}",
            {"nwb_path": nwb_path},
        )

        try:
            validation_result = await self._run_nwb_inspector(nwb_path)

            # Update state based on validation result
            if validation_result.is_valid:
                state.update_validation_status(ValidationStatus.PASSED)
                state.add_log(
                    LogLevel.INFO,
                    "Validation passed",
                    {"nwb_path": nwb_path, "summary": validation_result.summary},
                )
            else:
                # Check severity of issues
                if validation_result.summary.get("critical", 0) > 0 or validation_result.summary.get("error", 0) > 0:
                    state.update_validation_status(ValidationStatus.FAILED_WITH_ERRORS)
                else:
                    state.update_validation_status(ValidationStatus.FAILED_WITH_WARNINGS)

                state.add_log(
                    LogLevel.WARNING,
                    "Validation failed",
                    {
                        "nwb_path": nwb_path,
                        "summary": validation_result.summary,
                        "issue_count": len(validation_result.issues),
                    },
                )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "validation_result": validation_result.model_dump(),
                },
            )

        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"nwb_path": nwb_path, "exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="VALIDATION_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    async def _run_nwb_inspector(self, nwb_path: str) -> ValidationResult:
        """
        Run NWB Inspector validation.

        Args:
            nwb_path: Path to NWB file

        Returns:
            ValidationResult object

        Raises:
            Exception: If validation cannot be run
        """
        from nwbinspector import inspect_nwbfile
        from nwbinspector import __version__ as inspector_version

        # Run NWB Inspector
        results = list(inspect_nwbfile(nwbfile_path=nwb_path))

        # Convert to our format
        inspector_results = []
        for check_result in results:
            inspector_results.append({
                "severity": check_result.severity.name.lower(),
                "message": check_result.message,
                "location": str(check_result.location) if hasattr(check_result, "location") else None,
                "check_function_name": check_result.check_function_name,
            })

        validation_result = ValidationResult.from_inspector_output(
            inspector_results,
            inspector_version,
        )

        return validation_result

    async def handle_analyze_corrections(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Analyze validation issues and suggest corrections (requires LLM).

        Args:
            message: MCP message with context containing validation results
            state: Global state

        Returns:
            MCPResponse with correction suggestions or error
        """
        if not self._llm_service:
            state.add_log(
                LogLevel.ERROR,
                "LLM service not available for correction analysis",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="LLM_NOT_AVAILABLE",
                error_message="Correction analysis requires LLM service",
            )

        validation_result_data = message.context.get("validation_result")
        input_metadata = message.context.get("input_metadata", {})
        conversion_parameters = message.context.get("conversion_parameters", {})

        if not validation_result_data:
            state.add_log(
                LogLevel.ERROR,
                "Missing validation_result in correction analysis request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_VALIDATION_RESULT",
                error_message="validation_result is required",
            )

        state.add_log(
            LogLevel.INFO,
            "Starting correction analysis with LLM",
            {"attempt": state.correction_attempt},
        )

        try:
            # Parse validation result
            validation_result = ValidationResult(**validation_result_data)

            # Create correction context
            correction_context = CorrectionContext(
                validation_result=validation_result,
                input_metadata=input_metadata,
                conversion_parameters=conversion_parameters,
            )

            # Analyze with LLM
            corrections = await self._analyze_with_llm(correction_context, state)

            state.add_log(
                LogLevel.INFO,
                "Correction analysis completed",
                {"corrections_count": len(corrections.get("suggestions", []))},
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "corrections": corrections,
                },
            )

        except Exception as e:
            error_msg = f"Correction analysis failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="ANALYSIS_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    async def _analyze_with_llm(
        self,
        correction_context: CorrectionContext,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze validation issues and suggest corrections.

        Args:
            correction_context: Context for correction analysis
            state: Global state

        Returns:
            Dictionary with correction suggestions
        """
        # Build prompt
        prompt = self._build_correction_prompt(correction_context)

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

        return result

    def _build_correction_prompt(self, context: CorrectionContext) -> str:
        """
        Build LLM prompt for correction analysis.

        Args:
            context: Correction context

        Returns:
            Prompt string
        """
        issues_text = "\n".join([
            f"- [{issue.severity.value.upper()}] {issue.message}"
            + (f" (at {issue.location})" if issue.location else "")
            for issue in context.validation_result.issues[:20]  # Limit to 20 issues
        ])

        if len(context.validation_result.issues) > 20:
            issues_text += f"\n... and {len(context.validation_result.issues) - 20} more issues"

        prompt = f"""# NWB Validation Issues

## Summary
- Total issues: {len(context.validation_result.issues)}
- Critical: {context.validation_result.summary.get('critical', 0)}
- Errors: {context.validation_result.summary.get('error', 0)}
- Warnings: {context.validation_result.summary.get('warning', 0)}

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


def register_evaluation_agent(
    mcp_server,
    llm_service: Optional[LLMService] = None,
) -> EvaluationAgent:
    """
    Register Evaluation Agent handlers with MCP server.

    Args:
        mcp_server: MCP server instance
        llm_service: Optional LLM service for correction analysis

    Returns:
        EvaluationAgent instance
    """
    agent = EvaluationAgent(llm_service=llm_service)

    mcp_server.register_handler(
        "evaluation",
        "run_validation",
        agent.handle_run_validation,
    )

    mcp_server.register_handler(
        "evaluation",
        "analyze_corrections",
        agent.handle_analyze_corrections,
    )

    return agent
