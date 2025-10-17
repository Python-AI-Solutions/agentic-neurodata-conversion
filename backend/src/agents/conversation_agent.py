"""
Conversation Agent implementation.

Responsible for:
- All user interactions
- Orchestrating conversion workflows
- Managing retry logic
- Gathering user input
"""
from typing import Any, Dict, List, Optional

from models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationStatus,
)
from services import LLMService, MCPServer
from agents.conversational_handler import ConversationalHandler


class ConversationAgent:
    """
    Conversation agent for user interaction and workflow orchestration.

    This agent coordinates the conversion workflow by sending messages
    to other agents through the MCP server.
    """

    def __init__(
        self,
        mcp_server: MCPServer,
        llm_service: Optional[LLMService] = None,
    ):
        """
        Initialize the conversation agent.

        Args:
            mcp_server: MCP server for agent communication
            llm_service: Optional LLM service for enhanced interactions
        """
        self._mcp_server = mcp_server
        self._llm_service = llm_service
        self._conversational_handler = (
            ConversationalHandler(llm_service) if llm_service else None
        )
        # Conversation history now managed in GlobalState to prevent memory leaks

    async def handle_start_conversion(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Start the conversion workflow.

        Args:
            message: MCP message with context containing conversion parameters
            state: Global state

        Returns:
            MCPResponse indicating workflow started
        """
        input_path = message.context.get("input_path")
        metadata = message.context.get("metadata", {})

        if not input_path:
            state.add_log(
                LogLevel.ERROR,
                "Missing input_path in start_conversion request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_INPUT_PATH",
                error_message="input_path is required",
            )

        state.input_path = input_path
        state.metadata = metadata

        state.add_log(
            LogLevel.INFO,
            "Starting conversion workflow",
            {"input_path": input_path},
        )

        # Step 1: Detect format
        detect_msg = MCPMessage(
            target_agent="conversion",
            action="detect_format",
            context={"input_path": input_path},
            reply_to=message.message_id,
        )

        detect_response = await self._mcp_server.send_message(detect_msg)

        if not detect_response.success:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="DETECTION_FAILED",
                error_message="Format detection failed",
                error_context=detect_response.error,
            )

        detected_format = detect_response.result.get("format")
        confidence = detect_response.result.get("confidence")

        # Handle ambiguous format detection
        if confidence == "ambiguous" or not detected_format:
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
            state.add_log(
                LogLevel.INFO,
                "Format detection ambiguous - awaiting user input",
                {"supported_formats": detect_response.result.get("supported_formats", [])},
            )
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "awaiting_format_selection",
                    "supported_formats": detect_response.result.get("supported_formats", []),
                    "message": "Please select the data format",
                },
            )

        # Step 1.5: Check for DANDI-required metadata BEFORE conversion
        # This prevents the bug where we convert first, then ask for metadata after
        if self._conversational_handler:
            # Check if we have the 3 essential DANDI fields
            required_fields = {
                "experimenter": metadata.get("experimenter"),
                "institution": metadata.get("institution"),
                "experiment_description": metadata.get("experiment_description") or metadata.get("session_description"),
            }

            # Filter out fields the user already declined
            missing_fields = [
                field for field, value in required_fields.items()
                if not value and field not in state.user_declined_fields
            ]

            # INFINITE LOOP FIX: Check if we're already in a conversation about metadata
            # This prevents re-asking if user accidentally re-uploads or refreshes page
            in_metadata_conversation = (
                state.status == ConversionStatus.AWAITING_USER_INPUT and
                state.conversation_type == "required_metadata" and
                len(state.conversation_history) > 0
            )

            # If critical fields are missing AND we haven't asked yet AND we're not already in a metadata conversation
            # Also check if user wants minimal conversion (skip asking)

            # DETAILED DEBUG LOGGING FOR INFINITE LOOP BUG
            state.add_log(
                LogLevel.DEBUG,
                "Metadata check conditions",
                {
                    "missing_fields": missing_fields,
                    "metadata_requests_count": state.metadata_requests_count,
                    "user_wants_minimal": state.user_wants_minimal,
                    "in_metadata_conversation": in_metadata_conversation,
                    "conversation_type": state.conversation_type,
                    "status": state.status.value,
                    "conversation_history_length": len(state.conversation_history),
                }
            )

            if missing_fields and state.metadata_requests_count < 1 and not state.user_wants_minimal and not in_metadata_conversation:
                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                state.conversation_type = "required_metadata"  # BUG FIX: Set conversation type so we can detect if already in this conversation
                state.metadata_requests_count += 1
                state.add_log(
                    LogLevel.INFO,
                    f"Missing DANDI-required metadata ({', '.join(missing_fields)}) - requesting from user before conversion",
                    {"missing_fields": missing_fields, "request_count": state.metadata_requests_count},
                )

                # Generate friendly message asking for required metadata
                message_text = f"""🔴 **Critical Information Needed**

To create a DANDI-compatible NWB file, I need 3 essential fields:

• **Experimenter Name(s)**: Required by DANDI for attribution and reproducibility
Example: ["Dr. Jane Smith", "Dr. John Doe"]

• **Experiment Description**: Required by DANDI to help others understand your data
Example: Recording of neural activity in mouse V1 during visual stimulation

• **Institution**: Required by DANDI for institutional affiliation
Example: University of California, Berkeley

**How would you like to proceed?**
• Provide all at once (e.g., "Dr. Smith, MIT, recording neural activity")
• Answer one by one (say "ask one by one")
• Skip for now (file won't be DANDI-compatible)"""

                # INFINITE LOOP FIX: Add this assistant message to conversation history
                # This is critical - without this, the conversation history check at line 148 will always fail
                state.add_conversation_message(role="assistant", content=message_text)

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "awaiting_user_input",
                        "conversation_type": "required_metadata",
                        "message": message_text,
                        "needs_user_input": True,
                        "required_fields": missing_fields,
                        "can_skip": False,  # These are critical for DANDI
                        "phase": "pre_conversion",
                    },
                )

        # Step 1.6: Proactive Issue Detection (OPTIONAL - can be disabled)
        # Analyze file BEFORE conversion to predict potential issues
        # This feature can have false positives, so allow users to proceed anyway
        enable_proactive_detection = metadata.get("enable_proactive_detection", False)  # Disabled by default

        if self._llm_service and enable_proactive_detection:
            state.add_log(LogLevel.INFO, "Running proactive issue analysis...")

            prediction = await self._proactive_issue_detection(
                input_path=input_path,
                format_name=detected_format,
                state=state,
            )

            # If high risk or low success probability, warn user BUT allow proceeding
            if prediction["risk_level"] == "high" or prediction.get("success_probability", 100) < 70:
                # Log the warning but don't block conversion
                state.add_log(
                    LogLevel.WARNING,
                    f"Proactive analysis detected risks (can proceed anyway)",
                    {"risk_level": prediction["risk_level"], "success_probability": prediction.get("success_probability")},
                )
                # Store warning in metadata for user to see, but continue conversion
                state.metadata["proactive_warning"] = {
                    "risk_level": prediction["risk_level"],
                    "success_probability": prediction.get("success_probability"),
                    "message": prediction.get("warning_message"),
                    "predicted_issues": prediction.get("predicted_issues", []),
                }

        # Step 2: Run conversion
        return await self._run_conversion(
            message.message_id,
            input_path,
            detected_format,
            metadata,
            state,
        )

    async def _explain_error_to_user(
        self,
        error: Dict[str, Any],
        context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to explain errors in user-friendly terms.

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
- Message: {error.get('message', 'Unknown error')}
- Code: {error.get('code', 'UNKNOWN')}
- Context: {error.get('context', {})}

Conversion Context:
- Format: {context.get('format', 'unknown')}
- Input file: {context.get('input_path', 'unknown')}
- What was happening: {context.get('operation', 'conversion')}

Provide:
1. Simple explanation of what went wrong (no technical jargon)
2. Likely cause (why this might have happened)
3. Specific actions the user can take
4. Whether this issue is fixable

Respond in JSON format."""

            output_schema = {
                "type": "object",
                "properties": {
                    "explanation": {
                        "type": "string",
                        "description": "Simple, clear explanation of what went wrong"
                    },
                    "likely_cause": {
                        "type": "string",
                        "description": "Why this error probably occurred"
                    },
                    "suggested_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific steps user can take to fix or work around the issue"
                    },
                    "is_recoverable": {
                        "type": "boolean",
                        "description": "Whether this error can be fixed by user action"
                    },
                    "help_url": {
                        "type": "string",
                        "description": "Optional URL to relevant documentation"
                    }
                },
                "required": ["explanation", "likely_cause", "suggested_actions", "is_recoverable"]
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

            return explanation

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

    async def _proactive_issue_detection(
        self,
        input_path: str,
        format_name: str,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze file BEFORE conversion and predict potential issues.

        This proactive approach prevents wasted time on conversions that will likely fail.

        Args:
            input_path: Path to input file
            format_name: Detected format name
            state: Global state

        Returns:
            Dictionary with risk_level, predicted_issues, suggested_fixes, success_probability
        """
        # Skip if no LLM
        if not self._llm_service:
            return {"risk_level": "unknown", "should_proceed": True}

        from pathlib import Path
        import os

        # Gather file characteristics
        try:
            file_path = Path(input_path)
            file_size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0

            # Check for companion files
            parent_dir = file_path.parent
            sibling_files = [f.name for f in parent_dir.iterdir() if f.is_file()][:20]

            file_info = {
                "filename": file_path.name,
                "size_mb": round(file_size_mb, 2),
                "format": format_name,
                "sibling_files": sibling_files,
                "has_metadata_file": any(".meta" in f or ".json" in f for f in sibling_files),
            }
        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Could not gather file info: {e}")
            return {"risk_level": "unknown", "should_proceed": True}

        system_prompt = """You are an expert in neuroscience data conversion with deep knowledge of:
- NWB format requirements
- Common data format pitfalls
- File structure issues
- Metadata requirements for DANDI

Analyze files BEFORE conversion to predict issues and prevent failures."""

        user_prompt = f"""Analyze this {format_name} file for potential NWB conversion issues:

File Information:
- Filename: {file_info['filename']}
- Size: {file_info['size_mb']} MB
- Format: {file_info['format']}
- Sibling files: {file_info['sibling_files']}
- Has metadata: {file_info['has_metadata_file']}

Predict:
1. Likely validation issues
2. Missing metadata problems
3. File structure concerns
4. Success probability (0-100%)
5. Risk level (low/medium/high)

Be specific and actionable."""

        output_schema = {
            "type": "object",
            "properties": {
                "success_probability": {
                    "type": "number",
                    "description": "Probability of successful conversion (0-100)",
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Overall risk assessment",
                },
                "predicted_issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "severity": {"type": "string", "enum": ["info", "warning", "error"]},
                            "likelihood": {"type": "string", "enum": ["likely", "possible", "unlikely"]},
                        },
                    },
                    "description": "Potential issues that may occur",
                },
                "suggested_fixes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Actions user can take before conversion",
                },
                "warning_message": {
                    "type": "string",
                    "description": "User-friendly warning message if risks detected",
                },
                "should_proceed": {
                    "type": "boolean",
                    "description": "Whether conversion should proceed",
                },
            },
            "required": ["success_probability", "risk_level", "should_proceed"],
        }

        try:
            prediction = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                f"Proactive analysis: {prediction['risk_level']} risk, {prediction['success_probability']}% success probability",
                {
                    "risk_level": prediction["risk_level"],
                    "success_probability": prediction["success_probability"],
                    "predicted_issues_count": len(prediction.get("predicted_issues", [])),
                },
            )

            return prediction

        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Proactive analysis failed: {e}")
            return {"risk_level": "unknown", "should_proceed": True}

    async def _decide_next_action(
        self,
        current_state: str,
        context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to decide the next best action based on current state.

        This reduces hardcoded orchestration logic by having the LLM analyze
        the situation and suggest the optimal next step.

        Args:
            current_state: Current conversion state
            context: Context information
            state: Global state

        Returns:
            Dictionary with next_action, target_agent, reasoning
        """
        # Fallback if no LLM
        if not self._llm_service:
            return {
                "next_action": "continue",
                "target_agent": None,
                "reasoning": "No LLM available for decision-making",
            }

        system_prompt = """You are an intelligent agent orchestrator for NWB data conversion.
Analyze the current state and decide the best next action.

Consider:
- What just happened?
- What should happen next?
- Which agent should handle it?
- Are there any risks or blockers?

Be strategic and autonomous."""

        recent_logs = [log.message for log in state.logs[-5:]]

        user_prompt = f"""Current state: {current_state}
Context: {context}
Recent activity: {recent_logs}

What should happen next? Which agent should handle it?"""

        output_schema = {
            "type": "object",
            "properties": {
                "next_action": {
                    "type": "string",
                    "enum": [
                        "detect_format",
                        "run_conversion",
                        "validate",
                        "ask_user",
                        "retry",
                        "complete",
                        "fail",
                    ],
                },
                "target_agent": {
                    "type": "string",
                    "description": "Which agent should handle it (conversion/evaluation/conversation)",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why this is the best next step",
                },
                "should_notify_user": {
                    "type": "boolean",
                    "description": "Whether to notify user about this decision",
                },
            },
            "required": ["next_action", "target_agent", "reasoning"],
        }

        try:
            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                f"LLM decided next action: {response.get('next_action')} via {response.get('target_agent')}",
                {"reasoning": response.get("reasoning")},
            )

            return response

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to get LLM decision: {e}",
            )
            return {
                "next_action": "continue",
                "target_agent": None,
                "reasoning": "Fallback to manual orchestration",
            }

    async def _generate_status_message(
        self,
        status: str,
        context: Dict[str, Any],
        state: GlobalState,
    ) -> str:
        """
        Use LLM to generate contextual, engaging status messages.

        Replaces hardcoded templates with intelligent summaries that:
        - Acknowledge what happened
        - Highlight key information
        - Suggest next actions
        - Use friendly, conversational tone

        Args:
            status: Status type (e.g., "success", "failed", "retry_available")
            context: Context information (file paths, validation results, etc.)
            state: Global state

        Returns:
            LLM-generated status message
        """
        # Fallback message if LLM unavailable
        fallback_messages = {
            "success": "Conversion successful - NWB file is valid",
            "failed": "Conversion failed",
            "retry_available": "Validation failed - retry available",
            "completed_with_issues": "Conversion completed but has validation issues",
        }

        # If no LLM service, use fallback
        if not self._llm_service:
            return fallback_messages.get(status, "Operation completed")

        # Build context-rich prompt
        system_prompt = """You are a friendly, helpful AI assistant for neuroscience data conversion.
Generate concise, informative status messages that:
1. Clearly state what happened (success/failure)
2. Highlight key information (file size, format, validation results)
3. Suggest what the user can do next
4. Use a warm, encouraging tone
5. Keep it to 2-3 sentences max

Be specific and helpful, not generic."""

        # Extract relevant context
        format_name = context.get("format", "unknown")
        file_size_mb = context.get("file_size_mb", 0)
        validation_summary = context.get("validation_summary", {})
        output_path = context.get("output_path")
        input_filename = context.get("input_filename", "file")

        user_prompt = f"""Generate a status message for the user.

Status: {status}
Input file: {input_filename}
Format: {format_name}
File size: {file_size_mb:.1f}MB
Validation: {validation_summary}
Output: {output_path}

Create a friendly, informative message."""

        try:
            output_schema = {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The status message (2-3 sentences)",
                    },
                    "next_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional suggested next actions",
                    },
                },
                "required": ["message"],
            }

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "Generated LLM-powered status message",
                {"status": status},
            )

            return response.get("message", fallback_messages.get(status, "Operation completed"))

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate LLM status message: {e}",
            )
            return fallback_messages.get(status, "Operation completed")

    async def _finalize_with_minimal_metadata(
        self,
        original_message_id: str,
        output_path: str,
        validation_result: Dict[str, Any],
        format_name: str,
        input_path: str,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Complete conversion with minimal metadata and create informative report.

        This is called when user declines to provide additional metadata.
        Instead of looping infinitely asking for metadata, we:
        1. Accept the conversion as-is
        2. Generate a comprehensive report showing what's missing
        3. Provide guidance on how to add metadata later if needed

        Args:
            original_message_id: Original message ID for reply
            output_path: Path to generated NWB file
            validation_result: Validation result with issues
            format_name: Data format name
            input_path: Input file path
            state: Global state

        Returns:
            MCPResponse with completion status and guidance
        """
        from pathlib import Path

        state.add_log(
            LogLevel.INFO,
            "Finalizing conversion with minimal metadata",
            {"output_path": output_path},
        )

        # Generate evaluation report (even with warnings)
        report_msg = MCPMessage(
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": validation_result,
                "nwb_path": output_path,
            },
        )

        report_response = await self._mcp_server.send_message(report_msg)
        report_path = None
        if report_response.success:
            report_path = report_response.result.get("report_path")

        # Extract missing fields from validation issues
        missing_fields = []
        for issue in validation_result.get("issues", []):
            issue_msg = issue.get("message", "").lower()
            if "missing" in issue_msg or "not found" in issue_msg:
                # Extract field name from message
                for field in ["experimenter", "institution", "keywords", "subject", "session_description"]:
                    if field in issue_msg:
                        missing_fields.append(field)

        # Generate helpful completion message
        completion_message = f"""Conversion complete! Your NWB file has been created at: {Path(output_path).name}

**Status:** Completed with warnings

**What was created:**
- Valid NWB file structure ✓
- Your {format_name} data successfully converted ✓
- File size: {Path(output_path).stat().st_size / (1024 * 1024):.1f} MB

**Missing recommended metadata:**
{chr(10).join(f"- {field}" for field in missing_fields) if missing_fields else "- Some metadata fields"}

**What this means:**
- Your file is technically valid and can be used for analysis
- It may not meet requirements for data sharing (e.g., DANDI archive)
- You can add metadata later if needed

**How to add metadata later:**
1. Use PyNWB to programmatically update the file
2. Re-run conversion with metadata when available
3. Contact support for assistance

The conversion report has been generated with full details."""

        return MCPResponse.success_response(
            reply_to=original_message_id,
            result={
                "status": "completed_with_warnings",
                "output_path": output_path,
                "validation": validation_result,
                "report_path": report_path,
                "message": completion_message,
                "missing_fields": list(set(missing_fields)),
                "user_declined_metadata": True,
            },
        )

    async def _run_conversion(
        self,
        original_message_id: str,
        input_path: str,
        format_name: str,
        metadata: Dict[str, Any],
        state: GlobalState,
    ) -> MCPResponse:
        """
        Run the conversion and validation steps.

        Args:
            original_message_id: Original message ID for reply
            input_path: Path to input data
            format_name: Data format name
            metadata: Metadata dictionary
            state: Global state

        Returns:
            MCPResponse with conversion and validation results
        """
        import tempfile
        from pathlib import Path

        # Generate output path
        output_dir = Path(tempfile.gettempdir()) / "nwb_conversions"
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / f"converted_{Path(input_path).stem}.nwb")

        # Run conversion
        convert_msg = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": input_path,
                "output_path": output_path,
                "format": format_name,
                "metadata": metadata,
            },
        )

        convert_response = await self._mcp_server.send_message(convert_msg)

        if not convert_response.success:
            await state.update_status(ConversionStatus.FAILED)

            # Use LLM to explain the error in user-friendly terms
            error_explanation = await self._explain_error_to_user(
                error=convert_response.error,
                context={
                    "format": format_name,
                    "input_path": input_path,
                    "operation": "NWB conversion",
                },
                state=state,
            )

            return MCPResponse.error_response(
                reply_to=original_message_id,
                error_code="CONVERSION_FAILED",
                error_message=error_explanation["explanation"],
                error_context={
                    "technical_error": convert_response.error,
                    "user_friendly": error_explanation,
                },
            )

        # Step 3: Run validation
        validate_msg = MCPMessage(
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": output_path},
        )

        validate_response = await self._mcp_server.send_message(validate_msg)

        if not validate_response.success:
            await state.update_status(ConversionStatus.FAILED)

            # Use LLM to explain validation failure
            error_explanation = await self._explain_error_to_user(
                error=validate_response.error,
                context={
                    "format": format_name,
                    "input_path": input_path,
                    "operation": "NWB validation",
                },
                state=state,
            )

            return MCPResponse.error_response(
                reply_to=original_message_id,
                error_code="VALIDATION_FAILED",
                error_message=error_explanation["explanation"],
                error_context={
                    "technical_error": validate_response.error,
                    "user_friendly": error_explanation,
                },
            )

        validation_result = validate_response.result.get("validation_result")

        # Check if there are any issues that could benefit from conversational input
        # Even if is_valid=True, we want to engage user about INFO-level missing metadata
        has_improvable_issues = False
        if validation_result.get("issues"):
            # Look for missing metadata that user could provide
            metadata_keywords = [
                "experimenter",
                "experiment description",
                "institution",
                "keywords",
                "subject",
                "session description",
            ]
            for issue in validation_result["issues"]:
                issue_msg = issue.get("message", "").lower()
                if any(keyword in issue_msg for keyword in metadata_keywords):
                    has_improvable_issues = True
                    break

        # Check validation status - engage conversationally if there are improvable issues
        if validation_result["is_valid"] and not has_improvable_issues:
            await state.update_status(ConversionStatus.COMPLETED)
            state.add_log(
                LogLevel.INFO,
                "Conversion completed successfully with valid NWB file",
            )

            # Generate evaluation report
            report_msg = MCPMessage(
                target_agent="evaluation",
                action="generate_report",
                context={
                    "validation_result": validation_result,
                    "nwb_path": output_path,
                },
            )

            report_response = await self._mcp_server.send_message(report_msg)

            report_path = None
            if report_response.success:
                report_path = report_response.result.get("report_path")
                state.add_log(
                    LogLevel.INFO,
                    f"Evaluation report generated: {report_path}",
                )

            # Generate LLM-powered status message
            from pathlib import Path

            status_message = await self._generate_status_message(
                status="success",
                context={
                    "format": format_name,
                    "file_size_mb": Path(output_path).stat().st_size / (1024 * 1024) if Path(output_path).exists() else 0,
                    "validation_summary": validation_result.get("summary", {}),
                    "output_path": output_path,
                    "input_filename": Path(input_path).name,
                },
                state=state,
            )

            return MCPResponse.success_response(
                reply_to=original_message_id,
                result={
                    "status": "completed",
                    "output_path": output_path,
                    "validation": validation_result,
                    "report_path": report_path,
                    "message": status_message,  # LLM-POWERED!
                },
            )
        else:
            # Validation failed - use LLM to analyze and respond intelligently
            # Bug #14 fix: Always allow retry (unlimited with user permission)
            if self._conversational_handler:
                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                state.add_log(
                    LogLevel.INFO,
                    "Using LLM to analyze validation issues and engage user",
                )

                try:
                    # Get intelligent LLM analysis of validation issues
                    llm_analysis = await self._conversational_handler.analyze_validation_and_respond(
                        validation_result=validation_result,
                        nwb_file_path=output_path,
                        state=state,
                    )

                    # CHECK IF WE SHOULD PROCEED WITH MINIMAL METADATA
                    if llm_analysis.get("proceed_with_minimal", False):
                        await state.update_status(ConversionStatus.COMPLETED)
                        state.add_log(
                            LogLevel.INFO,
                            "User wants minimal conversion - completing with warnings",
                        )

                        # Generate completion report with warnings
                        return await self._finalize_with_minimal_metadata(
                            original_message_id=original_message_id,
                            output_path=output_path,
                            validation_result=validation_result,
                            format_name=format_name,
                            input_path=input_path,
                            state=state,
                        )

                    # Add to conversation history
                    state.add_conversation_message(
                        role="assistant",
                        content=llm_analysis.get("message", ""),
                        context=llm_analysis
                    )

                    # Store conversational state for frontend
                    state.conversation_type = "validation_analysis"
                    state.llm_message = llm_analysis.get("message")

                    return MCPResponse.success_response(
                        reply_to=original_message_id,
                        result={
                            "status": "awaiting_user_input",
                            "conversation_type": "validation_analysis",
                            "message": llm_analysis.get("message"),
                            "needs_user_input": llm_analysis.get("needs_user_input", True),
                            "suggested_fixes": llm_analysis.get("suggested_fixes", []),
                            "required_fields": llm_analysis.get("required_fields", []),  # Smart metadata fields
                            "suggestions": llm_analysis.get("suggestions", []),  # LLM suggestions
                            "detected_data_type": llm_analysis.get("detected_data_type"),  # Inferred data type
                            "severity": llm_analysis.get("severity", "medium"),
                            "validation": validation_result,
                            "can_retry": True,
                        },
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.ERROR,
                        f"LLM analysis failed, falling back to standard flow: {e}",
                    )
                    # Fallback to original rigid behavior
                    pass

            # Bug #14 fix: Always allow retry - unlimited attempts with user permission
            # (Story 8.7 line 933, Story 8.8 line 953)
            await state.update_status(ConversionStatus.AWAITING_RETRY_APPROVAL)
            state.add_log(
                LogLevel.WARNING,
                "Validation failed - awaiting retry approval",
            )

            # Generate LLM-powered retry message
            retry_message = await self._generate_status_message(
                status="retry_available",
                context={
                    "format": format_name,
                    "file_size_mb": Path(output_path).stat().st_size / (1024 * 1024) if Path(output_path).exists() else 0,
                    "validation_summary": validation_result.get("summary", {}),
                    "output_path": output_path,
                    "input_filename": Path(input_path).name,
                    "retry_count": state.correction_attempt,
                },
                state=state,
            )

            return MCPResponse.success_response(
                reply_to=original_message_id,
                result={
                    "status": "awaiting_retry_approval",
                    "validation": validation_result,
                    "can_retry": True,
                    "message": retry_message,  # LLM-POWERED!
                },
            )

    async def handle_user_format_selection(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Handle user's manual format selection.

        Args:
            message: MCP message with selected format
            state: Global state

        Returns:
            MCPResponse with conversion workflow continuation
        """
        selected_format = message.context.get("format")

        if not selected_format:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_FORMAT",
                error_message="format selection is required",
            )

        if state.status != ConversionStatus.AWAITING_USER_INPUT:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_STATE",
                error_message=f"Cannot accept format selection in state: {state.status}",
            )

        state.add_log(
            LogLevel.INFO,
            f"User selected format: {selected_format}",
            {"format": selected_format},
        )

        # Continue with conversion
        return await self._run_conversion(
            message.message_id,
            state.input_path,
            selected_format,
            state.metadata,
            state,
        )

    async def handle_retry_decision(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Handle user's retry approval/rejection.

        Args:
            message: MCP message with user decision
            state: Global state

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
            if state.overall_status != "PASSED_WITH_ISSUES":
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
                warning_message = (
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
                            # Generate report after validation
                            report_response = await self._mcp_server.send_message(
                                MCPMessage(
                                    target_agent="evaluation",
                                    action="generate_report",
                                    context={
                                        "validation_result": validation_response.result.get("validation_result"),
                                        "nwb_path": state.output_path,
                                    },
                                )
                            )

                            if report_response.success:
                                state.add_log(
                                    LogLevel.INFO,
                                    f"Report generated: {report_response.result.get('report_path')}",
                                )

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
            restart_response = await self.handle_start_conversion(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(state.input_path),
                        "metadata": state.metadata,
                    },
                ),
                state,
            )
            return restart_response
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

    def _identify_user_input_required(self, corrections: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify issues that require user input to fix.

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
                required_fields.append({
                    "field_name": "subject_id",
                    "label": "Subject ID",
                    "type": "text",
                    "required": True,
                    "help_text": "Unique identifier for the experimental subject",
                    "reason": suggestion.get("issue", ""),
                })

            elif "session_description" in issue and "too short" in suggestion_text:
                required_fields.append({
                    "field_name": "session_description",
                    "label": "Session Description",
                    "type": "textarea",
                    "required": True,
                    "help_text": "Detailed description of the experimental session (minimum 20 characters)",
                    "reason": suggestion.get("issue", ""),
                })

            elif "experimenter" in issue and ("missing" in issue or "empty" in issue):
                required_fields.append({
                    "field_name": "experimenter",
                    "label": "Experimenter Name(s)",
                    "type": "text",
                    "required": True,
                    "help_text": "Name(s) of experimenter(s) who conducted the session (comma-separated)",
                    "reason": suggestion.get("issue", ""),
                })

            elif "institution" in issue and "empty" not in suggestion_text:
                required_fields.append({
                    "field_name": "institution",
                    "label": "Institution",
                    "type": "text",
                    "required": False,
                    "help_text": "Institution where the experiment was conducted",
                    "reason": suggestion.get("issue", ""),
                })

        return required_fields

    def _extract_auto_fixes(self, corrections: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract automatically fixable corrections from LLM analysis.

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

    async def handle_conversational_response(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Handle user's conversational response to LLM questions.

        This enables natural, flowing conversation where the LLM analyzes
        user responses and decides next steps dynamically.

        Args:
            message: MCP message with user's response
            state: Global state

        Returns:
            MCPResponse with next conversation turn or action
        """
        user_message = message.context.get("message", "")

        if not user_message:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_MESSAGE",
                error_message="User message is required",
            )

        # Input validation: check message length
        if len(user_message) > 10000:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MESSAGE_TOO_LONG",
                error_message="Message too long. Please keep your message under 10,000 characters.",
            )

        # Strip excessive whitespace
        user_message = user_message.strip()
        if not user_message:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="EMPTY_MESSAGE",
                error_message="Message cannot be empty or whitespace only.",
            )

        # Add user message to conversation history
        state.add_conversation_message(role="user", content=user_message)

        state.add_log(
            LogLevel.INFO,
            f"Processing conversational response from user",
            {"message_preview": user_message[:100]},
        )

        # Bug #8 fix: Check for explicit cancellation (Story 8.8 line 959)
        if user_message.lower() in ["cancel", "quit", "stop", "abort", "exit"]:
            state.validation_status = ValidationStatus.FAILED_USER_ABANDONED
            await state.update_status(ConversionStatus.FAILED)
            state.add_log(
                LogLevel.INFO,
                "User abandoned correction loop (validation_status=failed_user_abandoned)",
                {"message": user_message},
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "failed",
                    "validation_status": "failed_user_abandoned",
                    "message": "Conversion cancelled by user",
                },
            )

        if not self._conversational_handler:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="NO_LLM",
                error_message="LLM service not configured for conversational responses",
            )

        # CHECK IF USER IS DECLINING TO PROVIDE METADATA
        # Use LLM-based detection for better understanding of user intent
        conversation_context = "\n".join([
            f"{msg['role']}: {msg['content'][:100]}"
            for msg in state.conversation_history[-3:]  # Last 3 exchanges for context
        ]) if state.conversation_history else ""

        skip_type = await self._conversational_handler.detect_skip_type_with_llm(
            user_message,
            conversation_context
        )

        state.add_log(
            LogLevel.INFO,
            f"User intent detected: {skip_type}",
            {"user_message": user_message[:100], "skip_type": skip_type}
        )

        if skip_type == "global":
            # User wants to skip ALL remaining questions
            state.user_wants_minimal = True
            # Mark all DANDI fields as declined
            state.user_declined_fields.update(["experimenter", "institution", "experiment_description"])

            # DETAILED DEBUG LOGGING
            state.add_log(
                LogLevel.INFO,
                "User requested to skip all remaining questions - proceeding with minimal conversion",
                {
                    "message": user_message[:100],
                    "user_wants_minimal": state.user_wants_minimal,
                    "metadata_requests_count": state.metadata_requests_count,
                    "user_declined_fields": list(state.user_declined_fields),
                },
            )

            # Add assistant response to history
            decline_message = "Understood! I'll complete the conversion with the data you've provided. The NWB file will be created, though it may not include all recommended metadata fields."
            state.add_conversation_message(role="assistant", content=decline_message)

            state.add_log(
                LogLevel.DEBUG,
                "About to restart conversion after global skip",
                {
                    "user_wants_minimal": state.user_wants_minimal,
                    "metadata_requests_count": state.metadata_requests_count,
                    "status_before": state.status.value,
                }
            )

            # Restart conversion WITHOUT asking for more metadata
            return await self.handle_start_conversion(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(state.input_path),
                        "metadata": state.metadata,  # Use existing metadata only
                    },
                ),
                state,
            )

        elif skip_type == "field":
            # User wants to skip THIS specific field only
            # Get the current field being asked from conversation context
            last_context = (
                state.conversation_history[-1].get("context", {})
                if len(state.conversation_history) >= 1
                else {}
            )

            current_field = last_context.get("field")
            if current_field:
                state.user_declined_fields.add(current_field)
                state.add_log(
                    LogLevel.INFO,
                    f"User skipped field: {current_field}",
                    {"message": user_message[:100]},
                )

                # Add assistant response acknowledging the skip
                skip_ack_message = f"No problem! Skipping {current_field}."
                state.add_conversation_message(role="assistant", content=skip_ack_message)

                # Restart conversion to ask for next field
                return await self.handle_start_conversion(
                    MCPMessage(
                        target_agent="conversation",
                        action="start_conversion",
                        context={
                            "input_path": str(state.input_path),
                            "metadata": state.metadata,
                        },
                    ),
                    state,
                )

        elif skip_type == "sequential":
            # User wants to answer questions one by one (for batch requests)
            state.add_log(
                LogLevel.INFO,
                "User requested sequential questioning",
            )

            # Save the sequential preference in state (THIS IS THE FIX!)
            state.user_wants_sequential = True

            # This will be handled by the strategy on next round
            # For now, acknowledge and restart
            sequential_ack = "Sure! I'll ask one question at a time."
            state.add_conversation_message(role="assistant", content=sequential_ack)

            return await self.handle_start_conversion(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(state.input_path),
                        "metadata": state.metadata,
                    },
                ),
                state,
            )

        try:
            # Build conversation context
            last_context = (
                state.conversation_history[-2].get("context", {})
                if len(state.conversation_history) >= 2
                else {}
            )

            context = {
                "validation_result": last_context.get("validation_result", {}),
                "issues": last_context.get("suggested_fixes", []),
                "conversation_history": state.conversation_history,
            }

            # Process user response with LLM
            response = await self._conversational_handler.process_user_response(
                user_message=user_message,
                context=context,
                state=state,
            )

            # Add assistant response to conversation history
            state.add_conversation_message(
                role="assistant",
                content=response.get("follow_up_message", ""),
                context=response
            )

            # Check if we're ready to proceed with fixes
            if response.get("ready_to_proceed", False):
                extracted_metadata = response.get("extracted_metadata", {})

                # BUG FIX: Update metadata if any extracted, even if empty dict
                # Empty dict is valid when user wants to skip/use defaults
                if extracted_metadata:
                    state.metadata.update(extracted_metadata)
                    state.add_log(
                        LogLevel.INFO,
                        "Metadata extracted from conversation",
                        {"metadata_fields": list(extracted_metadata.keys())},
                    )

                # Bug #11 fix: Mark that user provided input for "no progress" detection
                # Mark true regardless of whether metadata was extracted - user engaged with the system
                state.user_provided_input_this_attempt = True

                state.add_log(
                    LogLevel.INFO,
                    "User indicated ready to proceed, starting conversion",
                    {"has_extracted_metadata": bool(extracted_metadata)},
                )

                # Restart conversion with updated metadata (even if none extracted, user said proceed)
                return await self.handle_start_conversion(
                    MCPMessage(
                        target_agent="conversation",
                        action="start_conversion",
                        context={
                            "input_path": str(state.input_path),
                            "metadata": state.metadata,
                        },
                    ),
                    state,
                )

            # Continue conversation
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "conversation_continues",
                    "message": response.get("follow_up_message"),
                    "needs_more_info": response.get("needs_more_info", True),
                    "extracted_metadata": response.get("extracted_metadata", {}),
                },
            )

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Failed to process conversational response: {e}",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="CONVERSATION_FAILED",
                error_message=str(e),
            )

    async def handle_general_query(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Handle general user questions at ANY time, in ANY state.

        This makes the system feel like Claude.ai - always ready to help.
        Users can ask about NWB format, how to use the system, or get
        contextual help based on their current conversion status.

        Args:
            message: MCP message with user query
            state: Global state with conversion context

        Returns:
            MCPResponse with intelligent answer
        """
        user_query = message.context.get("query", "")

        if not user_query:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_QUERY",
                error_message="No query provided",
            )

        state.add_log(
            LogLevel.INFO,
            f"Processing general query: {user_query[:100]}...",
        )

        if not self._llm_service:
            # Fallback to basic responses if no LLM
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "answer": "I'm here to help with NWB file conversion. Please upload a file to get started.",
                    "type": "general_query_response",
                },
            )

        try:
            # Build rich context from current state
            context_info = {
                "current_status": state.status.value,
                "has_input_file": state.input_path is not None,
                "input_path": str(state.input_path) if state.input_path else None,
                "detected_format": state.metadata.get("format"),
                "validation_status": state.validation_status.value if state.validation_status else None,
                "correction_attempt": state.correction_attempt,
                "can_retry": True,  # Bug #14 fix: Always allow retry
                "output_path": str(state.output_path) if state.output_path else None,
            }

            # Recent conversation history for context
            recent_history = "\n".join([
                f"{msg['role']}: {msg['content'][:100]}"
                for msg in state.conversation_history[-3:]  # Last 3 exchanges
            ]) if state.conversation_history else "No previous conversation"

            system_prompt = """You are an expert NWB (Neurodata Without Borders) conversion assistant.

You help neuroscientists convert their electrophysiology data to NWB format.

Your role:
- Answer questions about NWB format, structure, metadata requirements
- Explain the conversion process and current status
- Provide guidance on fixing validation issues
- Be conversational, helpful, and educational like Claude.ai
- Reference the user's current conversion state when relevant

You should:
- Be friendly and encouraging
- Explain technical concepts clearly
- Provide specific, actionable advice
- Acknowledge what stage they're at in the process
- Offer next steps when appropriate"""

            user_prompt = f"""User question: "{user_query}"

Current conversion context:
- Status: {context_info['current_status']}
- Has file uploaded: {context_info['has_input_file']}
- File path: {context_info['input_path'] or 'None'}
- Format detected: {context_info['detected_format'] or 'Not yet detected'}
- Validation status: {context_info['validation_status'] or 'Not yet validated'}
- Correction attempt: {context_info['correction_attempt']}
- Can retry: {context_info['can_retry']}

Recent conversation:
{recent_history}

Provide a helpful, contextual answer. Be conversational and reference their current state if relevant.
Respond in JSON format."""

            output_schema = {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Conversational answer to the user's question"
                    },
                    "follow_up_suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional suggestions for next steps or related questions"
                    },
                    "relevant_action": {
                        "type": "string",
                        "description": "Optional action the user might want to take (e.g., 'upload_file', 'start_conversion')"
                    }
                },
                "required": ["answer"]
            }

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            # Add to conversation history
            state.add_conversation_message(role="user", content=user_query)
            state.add_conversation_message(role="assistant", content=response.get("answer", ""))

            state.add_log(
                LogLevel.INFO,
                "General query answered successfully",
                {"query_preview": user_query[:50]},
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "type": "general_query_response",
                    "answer": response.get("answer"),
                    "suggestions": response.get("follow_up_suggestions", []),
                    "suggested_action": response.get("relevant_action"),
                },
            )

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Failed to process general query: {e}",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="QUERY_PROCESSING_FAILED",
                error_message=f"Failed to process your question: {str(e)}",
            )


def register_conversation_agent(
    mcp_server: MCPServer,
    llm_service: Optional[LLMService] = None,
) -> ConversationAgent:
    """
    Register Conversation Agent handlers with MCP server.

    Args:
        mcp_server: MCP server instance
        llm_service: Optional LLM service

    Returns:
        ConversationAgent instance
    """
    agent = ConversationAgent(
        mcp_server=mcp_server,
        llm_service=llm_service,
    )

    mcp_server.register_handler(
        "conversation",
        "start_conversion",
        agent.handle_start_conversion,
    )

    mcp_server.register_handler(
        "conversation",
        "user_format_selection",
        agent.handle_user_format_selection,
    )

    mcp_server.register_handler(
        "conversation",
        "retry_decision",
        agent.handle_retry_decision,
    )

    mcp_server.register_handler(
        "conversation",
        "conversational_response",
        agent.handle_conversational_response,
    )

    mcp_server.register_handler(
        "conversation",
        "general_query",
        agent.handle_general_query,
    )

    return agent
