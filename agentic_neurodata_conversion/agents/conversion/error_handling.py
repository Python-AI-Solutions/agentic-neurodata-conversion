"""Error handling and recovery module for conversion agent.

Handles:
- LLM-powered error explanations
- Validation correction application
- File versioning during reconversion
- Reconversion orchestration
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from agentic_neurodata_conversion.services.llm_service import LLMService

from agentic_neurodata_conversion.models import GlobalState, LogLevel, MCPMessage, MCPResponse
from agentic_neurodata_conversion.utils.file_versioning import compute_sha256, create_versioned_file

logger = logging.getLogger(__name__)


class ConversionErrorHandler:
    """Handles conversion errors and recovery workflows."""

    def __init__(self, llm_service: "LLMService | None" = None):
        """Initialize error handler.

        Args:
            llm_service: Optional LLM service for error explanations
        """
        self._llm_service = llm_service

    async def explain_conversion_error(
        self,
        error: Exception,
        format_name: str,
        input_path: str,
        state: GlobalState,
    ) -> str | None:
        """Use LLM to generate user-friendly error explanations.

        Transforms technical error messages into actionable guidance that
        helps users understand what went wrong and how to fix it.

        Args:
            error: The exception that occurred
            format_name: Data format being converted
            input_path: Path to input file
            state: Global state for logging

        Returns:
            User-friendly error explanation, or None if LLM unavailable
        """
        if not self._llm_service:
            return None

        error_type = type(error).__name__
        error_message = str(error)

        # Gather context about the file
        file_context: dict[str, Any] = {}
        try:
            path = Path(input_path)
            if path.exists():
                if path.is_file():
                    file_context["type"] = "file"
                    file_context["name"] = path.name
                    file_context["size_mb"] = round(path.stat().st_size / (1024 * 1024), 2)
                    file_context["parent_dir"] = str(path.parent)
                    # List sibling files for context
                    siblings = [f.name for f in path.parent.iterdir() if f.is_file()][:10]
                    file_context["sibling_files"] = siblings
                else:
                    file_context["type"] = "directory"
                    file_context["name"] = path.name
                    files = [f.name for f in path.iterdir() if f.is_file()][:20]
                    file_context["files"] = files
        except Exception as e:
            # Non-critical - file context is optional
            logger.debug(f"Failed to gather file context: {e}")

        system_prompt = """You are a helpful neuroscience data conversion assistant.

Your job is to explain technical errors in simple, actionable terms.

When explaining errors:
1. Start with what went wrong in plain English
2. Explain the likely cause
3. Provide specific, actionable steps to fix it
4. Be empathetic and encouraging
5. Keep it concise (2-4 sentences)

Focus on helping the user resolve the issue, not on technical jargon."""

        user_prompt = f"""An error occurred during NWB conversion:

Format: {format_name}
Error Type: {error_type}
Error Message: {error_message}
File Context: {file_context}

Please explain what went wrong and how to fix it in user-friendly language."""

        try:
            explanation = await self._llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more focused explanations
                max_tokens=300,
            )

            state.add_log(
                LogLevel.INFO,
                "Generated user-friendly error explanation via LLM",
            )

            return str(explanation).strip()

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate error explanation via LLM: {e}",
            )
            return None

    async def handle_apply_corrections(
        self,
        message: MCPMessage,
        state: GlobalState,
        conversion_runner,
    ) -> MCPResponse:
        """Apply corrections and reconvert NWB file.

        Implements automatic issue correction and reconversion orchestration.
        When validation fails, corrections can be applied (automatic fixes +
        user input) and the file reconverted with updated metadata.

        Features:
        - Merges automatic fixes with user-provided corrections
        - Versions previous NWB file before reconversion
        - Tracks correction attempts
        - Computes checksums for verification

        Args:
            message: MCP message with correction context
            state: Global state
            conversion_runner: ConversionRunner instance for reconversion

        Returns:
            MCPResponse with reconversion result
        """
        message.context.get("correction_context")
        auto_fixes = message.context.get("auto_fixes", {})
        user_input = message.context.get("user_input", {})

        if not state.input_path:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_INPUT_PATH",
                error_message="No input path in state for reconversion",
            )

        state.add_log(
            LogLevel.INFO,
            f"Applying corrections (attempt {state.correction_attempt + 1})",
            {"auto_fixes": len(auto_fixes), "user_input": len(user_input)},
        )

        try:
            # Increment correction attempt
            state.increment_correction_attempt()

            # Build corrected metadata by merging state metadata with fixes
            corrected_metadata = state.metadata.copy()

            # Apply automatic fixes
            for field, value in auto_fixes.items():
                corrected_metadata[field] = value
                state.add_log(
                    LogLevel.INFO,
                    f"Applied automatic fix: {field} = {value}",
                )

            # Apply user-provided input
            for field, value in user_input.items():
                corrected_metadata[field] = value
                state.add_log(
                    LogLevel.INFO,
                    f"Applied user input: {field} = {value}",
                )

            # Version the previous NWB file if it exists
            if state.output_path and Path(state.output_path).exists():
                versioned_path, checksum = create_versioned_file(
                    Path(state.output_path),
                    state.correction_attempt - 1,  # Previous attempt
                    compute_checksum=True,
                )
                state.add_log(
                    LogLevel.INFO,
                    f"Versioned previous NWB file: {versioned_path}",
                    {"checksum": checksum},
                )

            # Re-run conversion with corrected metadata
            # Get format from state metadata
            format_name = state.metadata.get("format", "SpikeGLX")

            reconvert_message = MCPMessage(
                target_agent="conversion",
                action="run_conversion",
                context={
                    "input_path": state.input_path,
                    "output_path": state.output_path,  # Same output path
                    "format": format_name,
                    "metadata": corrected_metadata,
                },
                reply_to=message.message_id,
            )

            # Execute reconversion using the conversion runner
            result = await conversion_runner.handle_run_conversion(reconvert_message, state)

            if result.success:
                state.add_log(
                    LogLevel.INFO,
                    f"Reconversion successful (attempt {state.correction_attempt})",
                    {"output_path": state.output_path},
                )

                # Compute checksum of new file
                checksum = None
                if state.output_path:
                    checksum = compute_sha256(Path(state.output_path))
                    state.add_log(
                        LogLevel.INFO,
                        f"New NWB file checksum: {checksum}",
                    )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "reconversion_successful",
                        "output_path": state.output_path,
                        "attempt": state.correction_attempt,
                        "checksum": checksum,
                    },
                )
            else:
                state.add_log(
                    LogLevel.ERROR,
                    f"Reconversion failed (attempt {state.correction_attempt})",
                    {"error": result.error},
                )
                return cast(MCPResponse, result)

        except Exception as e:
            error_msg = f"Correction application failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"exception": str(e), "attempt": state.correction_attempt},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="CORRECTION_APPLICATION_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )
