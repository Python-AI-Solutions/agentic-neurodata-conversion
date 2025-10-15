"""
Conversation Agent implementation.

Responsible for:
- All user interactions
- Orchestrating conversion workflows
- Managing retry logic
- Gathering user input
"""
from typing import Any, Dict, Optional

from models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationStatus,
)
from services import LLMService, MCPServer


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
            state.update_status(ConversionStatus.AWAITING_USER_INPUT)
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

        # Step 2: Run conversion
        return await self._run_conversion(
            message.message_id,
            input_path,
            detected_format,
            metadata,
            state,
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
            state.update_status(ConversionStatus.FAILED)
            return MCPResponse.error_response(
                reply_to=original_message_id,
                error_code="CONVERSION_FAILED",
                error_message="NWB conversion failed",
                error_context=convert_response.error,
            )

        # Step 3: Run validation
        validate_msg = MCPMessage(
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": output_path},
        )

        validate_response = await self._mcp_server.send_message(validate_msg)

        if not validate_response.success:
            state.update_status(ConversionStatus.FAILED)
            return MCPResponse.error_response(
                reply_to=original_message_id,
                error_code="VALIDATION_FAILED",
                error_message="NWB validation failed",
                error_context=validate_response.error,
            )

        validation_result = validate_response.result.get("validation_result")

        # Check validation status
        if validation_result["is_valid"]:
            state.update_status(ConversionStatus.COMPLETED)
            state.add_log(
                LogLevel.INFO,
                "Conversion completed successfully with valid NWB file",
            )
            return MCPResponse.success_response(
                reply_to=original_message_id,
                result={
                    "status": "completed",
                    "output_path": output_path,
                    "validation": validation_result,
                    "message": "Conversion successful - NWB file is valid",
                },
            )
        else:
            # Validation failed - check if we should retry
            if state.can_retry():
                state.update_status(ConversionStatus.AWAITING_RETRY_APPROVAL)
                state.add_log(
                    LogLevel.WARNING,
                    "Validation failed - awaiting retry approval",
                    {
                        "attempt": state.correction_attempt,
                        "max_attempts": state.max_correction_attempts,
                    },
                )
                return MCPResponse.success_response(
                    reply_to=original_message_id,
                    result={
                        "status": "awaiting_retry_approval",
                        "validation": validation_result,
                        "can_retry": True,
                        "attempt": state.correction_attempt,
                        "message": "Validation failed - retry available",
                    },
                )
            else:
                state.update_status(ConversionStatus.FAILED)
                state.add_log(
                    LogLevel.ERROR,
                    "Validation failed - max retry attempts reached",
                )
                return MCPResponse.success_response(
                    reply_to=original_message_id,
                    result={
                        "status": "failed",
                        "validation": validation_result,
                        "can_retry": False,
                        "message": "Conversion failed - max retry attempts reached",
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

        if decision not in ["approve", "reject"]:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_DECISION",
                error_message="decision must be 'approve' or 'reject'",
            )

        if state.status != ConversionStatus.AWAITING_RETRY_APPROVAL:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_STATE",
                error_message=f"Cannot accept retry decision in state: {state.status}",
            )

        if decision == "reject":
            state.update_status(ConversionStatus.FAILED)
            state.add_log(
                LogLevel.INFO,
                "User rejected retry",
            )
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "failed",
                    "message": "Conversion terminated by user",
                },
            )

        # User approved retry
        state.increment_retry()
        state.add_log(
            LogLevel.INFO,
            f"User approved retry (attempt {state.correction_attempt})",
        )

        # Analyze corrections with LLM if available
        if self._llm_service:
            # Get validation result from state logs
            # For now, return a message that correction analysis will happen
            # In full implementation, this would trigger correction analysis
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "analyzing_corrections",
                    "message": "Analyzing validation issues for corrections",
                },
            )
        else:
            # No LLM available - ask user for manual corrections
            state.update_status(ConversionStatus.AWAITING_USER_INPUT)
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "awaiting_corrections",
                    "message": "Please provide corrections manually",
                },
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

    return agent
