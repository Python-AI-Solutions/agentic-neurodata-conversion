"""Conversational workflow module for conversation agent.

Handles:
- Natural language user responses
- Multi-turn metadata collection conversations
- Intent detection (skip, proceed, provide data)
- Metadata extraction from natural language
- Auto-fix approval conversations
- Metadata review workflow
- Custom metadata collection
- General user queries (help, questions)

This module enables Claude.ai-like natural conversations throughout
the conversion workflow, making the system feel intelligent and helpful.
"""

import logging
import re
from typing import TYPE_CHECKING, Optional, cast

from agentic_neurodata_conversion.models import (
    ConversationPhase,
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
)

if TYPE_CHECKING:
    from agentic_neurodata_conversion.agents.conversation import (
        MetadataCollector,
        MetadataParser,
        ProvenanceTracker,
    )
    from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler
    from agentic_neurodata_conversion.models.workflow_state_manager import WorkflowStateManager
    from agentic_neurodata_conversion.services import LLMService

logger = logging.getLogger(__name__)


class ConversationalWorkflow:
    """Manages conversational interactions with users throughout the workflow.

    This class handles natural language conversations that make the system
    feel like Claude.ai - intelligent, helpful, and context-aware.

    Key responsibilities:
    - Processing natural language user responses
    - Detecting user intent (skip, proceed, provide metadata)
    - Extracting metadata from conversational input
    - Managing multi-turn conversations
    - Handling metadata review and custom metadata collection
    - Answering general user questions with context

    Features:
    - LLM-powered intent detection
    - Intelligent metadata extraction
    - Context-aware responses
    - Graceful error handling
    - Provenance tracking for all metadata
    """

    def __init__(
        self,
        metadata_collector: "MetadataCollector",
        metadata_parser: "MetadataParser",
        provenance_tracker: "ProvenanceTracker",
        workflow_manager: "WorkflowStateManager",
        conversational_handler: Optional["ConversationalHandler"] = None,
        llm_service: Optional["LLMService"] = None,
    ):
        """Initialize conversational workflow manager.

        Args:
            metadata_collector: Metadata collection and validation
            metadata_parser: Metadata parsing utilities
            provenance_tracker: Provenance tracking
            workflow_manager: Workflow state management
            conversational_handler: Optional conversational AI handler
            llm_service: Optional LLM service for intelligent features
        """
        self._metadata_collector = metadata_collector
        self._metadata_parser = metadata_parser
        self._provenance_tracker = provenance_tracker
        self._workflow_manager = workflow_manager
        self._conversational_handler = conversational_handler
        self._llm_service = llm_service

        logger.info("ConversationalWorkflow initialized")

    async def handle_conversational_response(
        self,
        message: MCPMessage,
        state: GlobalState,
        handle_start_conversion_callback,  # Callback to start conversion
        continue_conversion_workflow_callback,  # Callback to continue workflow
        run_conversion_callback,  # Callback to run conversion
    ) -> MCPResponse:
        """Handle user's conversational response to LLM questions.

        This enables natural, flowing conversation where the LLM analyzes
        user responses and decides next steps dynamically.

        Handles multiple conversation types:
        - auto_fix_approval: User approving/rejecting auto-fixes
        - metadata_review: User reviewing and adding metadata
        - custom_metadata_collection: User providing custom metadata
        - general conversation: LLM-driven metadata collection

        Args:
            message: MCP message with user's response
            state: Global state
            handle_start_conversion_callback: Callback to restart workflow
            continue_conversion_workflow_callback: Callback to continue workflow
            run_conversion_callback: Callback to run conversion

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

        # BUG FIX: Clear the old llm_message to prevent it from repeating in the UI
        # The user has responded, so the previous question/message is no longer relevant
        state.llm_message = None

        state.add_log(
            LogLevel.INFO,
            "Processing conversational response from user",
            {"message_preview": user_message[:100]},
        )

        # Bug #8 fix: Check for explicit cancellation (Story 8.8 line 959)
        if user_message.lower() in ["cancel", "quit", "stop", "abort", "exit"]:
            from agentic_neurodata_conversion.models import ValidationStatus

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

        # Handle auto-fix approval conversation type
        if state.conversation_type == "auto_fix_approval":
            return await self._handle_auto_fix_approval_response(user_message, message.message_id, state)

        # Handle metadata review conversation type
        if state.conversation_type == "metadata_review":
            return await self._handle_metadata_review(
                user_message=user_message,
                message_id=message.message_id,
                state=state,
                run_conversion_callback=run_conversion_callback,
            )

        # Handle custom metadata collection conversation type
        if state.conversation_type == "custom_metadata_collection":
            return await self._handle_custom_metadata_collection(
                user_message=user_message,
                message_id=message.message_id,
                state=state,
                continue_conversion_workflow_callback=continue_conversion_workflow_callback,
                handle_start_conversion_callback=handle_start_conversion_callback,
            )

        if not self._conversational_handler:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="NO_LLM",
                error_message="LLM service not configured for conversational responses",
            )

        # CHECK IF USER IS DECLINING TO PROVIDE METADATA
        # Use LLM-based detection for better understanding of user intent
        conversation_context = (
            "\n".join(
                [
                    f"{msg['role']}: {msg['content'][:100]}"
                    for msg in state.conversation_history[-3:]  # Last 3 exchanges for context
                ]
            )
            if state.conversation_history
            else ""
        )

        skip_type = await self._conversational_handler.detect_skip_type_with_llm(user_message, conversation_context)

        state.add_log(
            LogLevel.INFO,
            f"User intent detected: {skip_type}",
            {"user_message": user_message[:100], "skip_type": skip_type},
        )

        # Handle different skip types
        if skip_type == "global":
            return await self._handle_global_skip(
                user_message=user_message,
                message_id=message.message_id,
                state=state,
                handle_start_conversion_callback=handle_start_conversion_callback,
            )

        elif skip_type == "field":
            return await self._handle_field_skip(
                user_message=user_message,
                message_id=message.message_id,
                state=state,
                handle_start_conversion_callback=handle_start_conversion_callback,
            )

        elif skip_type == "sequential":
            return await self._handle_sequential_request(
                user_message=user_message,
                message_id=message.message_id,
                state=state,
                handle_start_conversion_callback=handle_start_conversion_callback,
            )

        # Process normal conversational response with LLM
        try:
            # Build conversation context
            last_context = (
                state.conversation_history[-2].get("context", {}) if len(state.conversation_history) >= 2 else {}
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

            # DEBUG: Log the full response to understand what's being returned
            state.add_log(
                LogLevel.INFO,
                "Response from conversational_handler.process_user_response",
                {
                    "response_type": response.get("type"),
                    "has_extracted_metadata": bool(response.get("extracted_metadata")),
                    "extracted_metadata_keys": (
                        list(response.get("extracted_metadata", {}).keys())
                        if response.get("extracted_metadata")
                        else []
                    ),
                    "ready_to_proceed": response.get("ready_to_proceed"),
                    "needs_more_info": response.get("needs_more_info"),
                },
            )

            # Add assistant response to conversation history
            state.add_conversation_message(
                role="assistant", content=response.get("follow_up_message", ""), context=response
            )

            # ✅ FIX: ALWAYS persist extracted metadata incrementally, even if not ready to proceed
            # This allows multi-turn metadata collection conversations
            extracted_metadata = response.get("extracted_metadata", {})
            if extracted_metadata:
                # CRITICAL: Track user-provided metadata separately
                state.user_provided_metadata.update(extracted_metadata)

                # Merge: auto-extracted + user-provided (user takes priority)
                combined_metadata = {**state.auto_extracted_metadata, **state.user_provided_metadata}
                state.metadata = combined_metadata

                # PROVENANCE TRACKING: Record provenance, but don't overwrite if already set by IntelligentMetadataParser
                # IntelligentMetadataParser already sets correct provenance (AI_PARSED, AI_INFERRED)
                # Only track as user-specified if provenance wasn't already set by the parser
                for field_name, value in extracted_metadata.items():
                    if field_name not in state.metadata_provenance:
                        self._provenance_tracker.track_user_provided_metadata(
                            state=state,
                            field_name=field_name,
                            value=value,
                            confidence=100.0,
                            source=f"User provided: '{user_message[:100]}'",
                            raw_input=user_message[:200],  # Store original message
                        )

                state.add_log(
                    LogLevel.INFO,
                    "User-provided metadata extracted and persisted incrementally (with provenance)",
                    {
                        "user_provided_fields": list(extracted_metadata.keys()),
                        "total_metadata_fields": list(combined_metadata.keys()),
                    },
                )

            # Check if we're ready to proceed with fixes
            if response.get("ready_to_proceed", False):
                # Bug #11 fix: Mark that user provided input for "no progress" detection
                # Mark true regardless of whether metadata was extracted - user engaged with the system
                state.user_provided_input_this_attempt = True

                # Reset conversation phase since standard metadata collection is complete
                if state.conversation_phase == ConversationPhase.METADATA_COLLECTION:
                    state.conversation_phase = ConversationPhase.IDLE
                    state.conversation_type = None

                state.add_log(
                    LogLevel.INFO,
                    "User indicated ready to proceed, checking next steps",
                    {"has_extracted_metadata": bool(extracted_metadata)},
                )

                # ✅ FIX: Use pending_conversion_input_path with fallback
                # This ensures we use the correct path when user provides metadata
                conversion_path = state.pending_conversion_input_path or state.input_path
                if not conversion_path or str(conversion_path) == "None":
                    state.add_log(
                        LogLevel.ERROR,
                        "Cannot restart conversion - input_path not available",
                        {
                            "pending_conversion_input_path": (
                                str(state.pending_conversion_input_path)
                                if state.pending_conversion_input_path
                                else "None"
                            ),
                            "input_path": str(state.input_path) if state.input_path else "None",
                        },
                    )
                    return MCPResponse.error_response(
                        reply_to=message.message_id,
                        error_code="INVALID_STATE",
                        error_message="Cannot proceed with conversion. The file path is not available. Please try uploading the file again.",
                    )

                # CRITICAL FIX: Don't restart entire workflow (format detection already done!)
                # Instead, continue from where we left off: Step 2 (custom metadata) or Step 3 (review) or Step 4 (conversion)

                # Get the detected format (should be in metadata from previous detection)
                detected_format = state.metadata.get("format", "unknown")

                # Continue with workflow steps without re-running format detection
                return cast(
                    MCPResponse,
                    await continue_conversion_workflow_callback(
                        message_id=message.message_id,
                        input_path=str(conversion_path),
                        detected_format=detected_format,
                        metadata=state.metadata,
                        state=state,
                    ),
                )

            # Continue conversation
            # BUG FIX: Update llm_message so the frontend can display the follow-up question
            follow_up_message = response.get("follow_up_message")
            if follow_up_message:
                state.llm_message = follow_up_message

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "conversation_continues",
                    "message": follow_up_message,
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
        """Handle general user questions at ANY time, in ANY state.

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
            recent_history = (
                "\n".join(
                    [
                        f"{msg['role']}: {msg['content'][:100]}"
                        for msg in state.conversation_history[-3:]  # Last 3 exchanges
                    ]
                )
                if state.conversation_history
                else "No previous conversation"
            )

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
- Status: {context_info["current_status"]}
- Has file uploaded: {context_info["has_input_file"]}
- File path: {context_info["input_path"] or "None"}
- Format detected: {context_info["detected_format"] or "Not yet detected"}
- Validation status: {context_info["validation_status"] or "Not yet validated"}
- Correction attempt: {context_info["correction_attempt"]}
- Can retry: {context_info["can_retry"]}

Recent conversation:
{recent_history}

Provide a helpful, contextual answer. Be conversational and reference their current state if relevant.
Respond in JSON format."""

            output_schema = {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "Conversational answer to the user's question"},
                    "follow_up_suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional suggestions for next steps or related questions",
                    },
                    "relevant_action": {
                        "type": "string",
                        "description": "Optional action the user might want to take (e.g., 'upload_file', 'start_conversion')",
                    },
                },
                "required": ["answer"],
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

    # Helper methods

    async def _handle_auto_fix_approval_response(
        self, user_message: str, message_id: str, state: GlobalState
    ) -> MCPResponse:
        """Handle user response to auto-fix approval request.

        Args:
            user_message: User's response
            message_id: Message ID
            state: Global state

        Returns:
            MCPResponse
        """
        # This would be implemented based on auto-fix approval logic
        # Placeholder for now
        logger.warning("Auto-fix approval not yet implemented in modular version")
        return MCPResponse.success_response(
            reply_to=message_id,
            result={"status": "not_implemented", "message": "Auto-fix approval handler not yet implemented"},
        )

    async def _handle_metadata_review(
        self,
        user_message: str,
        message_id: str,
        state: GlobalState,
        run_conversion_callback,
    ) -> MCPResponse:
        """Handle metadata review conversation.

        Args:
            user_message: User's message
            message_id: Message ID
            state: Global state
            run_conversion_callback: Callback to run conversion

        Returns:
            MCPResponse
        """
        # Check if user wants to proceed or add more metadata
        if user_message.lower() in ["no", "proceed", "continue", "skip", "start"]:
            state.add_log(LogLevel.INFO, "User chose to proceed with current metadata")
            state.conversation_type = None  # Reset conversation type

            # Proceed with conversion
            if state.input_path:
                return cast(
                    MCPResponse,
                    await run_conversion_callback(
                        message_id,
                        str(state.input_path),
                        state.metadata.get("format", "unknown"),
                        state.metadata,
                        state,
                    ),
                )
            else:
                return MCPResponse.error_response(
                    reply_to=message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with conversion. File path not found.",
                )

        # Check if user expresses intent to add but hasn't provided data yet
        if self._user_expresses_intent_to_add_more(user_message):
            state.add_log(LogLevel.INFO, "User expressed intent to add metadata without providing concrete data")
            return MCPResponse.success_response(
                reply_to=message_id,
                result={
                    "status": "awaiting_metadata_fields",
                    "message": (
                        "Great! What would you like to add? You can provide:\n\n"
                        "• **Specific fields:** 'age: P90D, description: Visual cortex recording'\n"
                        "• **Natural language:** 'The session lasted 2 hours in the morning'\n"
                        "• **Or say 'proceed'** to continue with current metadata"
                    ),
                    "conversation_type": "metadata_review",  # Stay in same state
                },
            )

        # User wants to add more metadata - parse it
        # Try to extract metadata from the message
        additional_metadata = {}

        # Simple pattern matching for "field: value" format
        pattern = r"(\w+)\s*[:=]\s*(.+?)(?=\w+\s*[:=]|$)"
        matches = re.findall(pattern, user_message)
        for field, value in matches:
            field = field.lower().replace(" ", "_")
            additional_metadata[field] = value.strip()

        # If no pattern matches, try to parse with metadata parser if available
        if not additional_metadata:
            parsed = await self._metadata_parser.handle_custom_metadata_response(user_message, state)
            if parsed.get("standard_fields"):
                additional_metadata.update(parsed["standard_fields"])
            if parsed.get("custom_fields"):
                additional_metadata.update(parsed["custom_fields"])

        if additional_metadata:
            # Update metadata
            state.metadata.update(additional_metadata)

            # Track provenance
            for field, value in additional_metadata.items():
                if field not in state.metadata_provenance:
                    self._provenance_tracker.track_user_provided_metadata(
                        state=state,
                        field_name=field,
                        value=value,
                        confidence=100.0,
                        source=f"User provided during review: '{user_message[:100]}'",
                        raw_input=user_message[:200],
                    )

            state.add_log(
                LogLevel.INFO,
                f"Added {len(additional_metadata)} fields during metadata review",
                {"fields": list(additional_metadata.keys())},
            )

            state.conversation_type = None  # Reset for conversion

            # Proceed with conversion with updated metadata
            if state.input_path:
                return cast(
                    MCPResponse,
                    await run_conversion_callback(
                        message_id,
                        str(state.input_path),
                        state.metadata.get("format", "unknown"),
                        state.metadata,
                        state,
                    ),
                )
            else:
                return MCPResponse.error_response(
                    reply_to=message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with conversion. File path not found.",
                )
        else:
            # No metadata detected - ask for clarification instead of converting
            state.add_log(LogLevel.INFO, "No metadata detected in user message - asking for clarification")
            return MCPResponse.success_response(
                reply_to=message_id,
                result={
                    "status": "metadata_review",
                    "message": (
                        "I didn't detect any metadata fields in your message. "
                        "Please provide metadata in one of these formats:\n\n"
                        "• **Field format:** 'age: P90D'\n"
                        "• **Multiple fields:** 'age: P90D, description: Visual cortex recording'\n"
                        "• **Natural language:** 'The mouse was 3 months old'\n\n"
                        "Or say **'proceed'** to continue with your current metadata."
                    ),
                    "conversation_type": "metadata_review",  # Stay in state, don't convert
                },
            )

    async def _handle_custom_metadata_collection(
        self,
        user_message: str,
        message_id: str,
        state: GlobalState,
        continue_conversion_workflow_callback,
        handle_start_conversion_callback,
    ) -> MCPResponse:
        """Handle custom metadata collection conversation.

        Args:
            user_message: User's message
            message_id: Message ID
            state: Global state
            continue_conversion_workflow_callback: Callback to continue workflow
            handle_start_conversion_callback: Callback to start conversion

        Returns:
            MCPResponse
        """
        # Check if user wants to skip custom metadata
        if user_message.lower() in ["no", "skip", "none", "proceed", "continue"]:
            state.add_log(LogLevel.INFO, "User declined to add custom metadata")
            state.conversation_type = None  # Reset conversation type

            # BUG FIX: Mark both custom metadata and metadata review as complete
            # so _continue_conversion_workflow proceeds directly to conversion
            state.metadata["_custom_metadata_prompted"] = True
            state.metadata["_metadata_review_shown"] = True

            # BUG FIX: Continue workflow instead of restarting from scratch
            # Use _continue_conversion_workflow to proceed to metadata review or conversion
            # instead of handle_start_conversion which would re-run format detection
            if state.input_path:
                detected_format = state.metadata.get("format", "unknown")
                return cast(
                    MCPResponse,
                    await continue_conversion_workflow_callback(
                        message_id=message_id,
                        input_path=str(state.input_path),
                        detected_format=detected_format,
                        metadata=state.metadata,
                        state=state,
                    ),
                )
            else:
                return MCPResponse.error_response(
                    reply_to=message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with conversion. File path not found.",
                )

        # Process custom metadata
        parsed_metadata = await self._metadata_parser.handle_custom_metadata_response(user_message, state)

        state.conversation_type = None  # Reset conversation type
        state.add_log(LogLevel.INFO, "Custom metadata collected, proceeding with conversion")

        # Proceed with conversion with updated metadata
        if state.input_path:
            return cast(
                MCPResponse,
                await handle_start_conversion_callback(
                    MCPMessage(
                        target_agent="conversation",
                        action="start_conversion",
                        context={
                            "input_path": str(state.input_path),
                            "metadata": state.metadata,
                        },
                    ),
                    state,
                ),
            )
        else:
            return MCPResponse.error_response(
                reply_to=message_id,
                error_code="INVALID_STATE",
                error_message="Cannot proceed with conversion. File path not found.",
            )

    async def _handle_global_skip(
        self,
        user_message: str,
        message_id: str,
        state: GlobalState,
        handle_start_conversion_callback,
    ) -> MCPResponse:
        """Handle user request to skip all remaining questions.

        Args:
            user_message: User's message
            message_id: Message ID
            state: Global state
            handle_start_conversion_callback: Callback to start conversion

        Returns:
            MCPResponse
        """
        # User wants to skip ALL remaining questions
        # Use WorkflowStateManager to update metadata policy
        self._workflow_manager.update_metadata_policy_after_user_declined(state)
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

        # ✅ FIX: Validate that we have a valid input_path before proceeding
        # Use pending_conversion_input_path if available, fallback to input_path
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
                reply_to=message_id,
                error_code="INVALID_STATE",
                error_message="Cannot proceed with conversion. The file path is not available. Please try uploading the file again.",
            )

        # Restart conversion WITHOUT asking for more metadata
        return cast(
            MCPResponse,
            await handle_start_conversion_callback(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(conversion_path),
                        "metadata": state.metadata,  # Use existing metadata only
                    },
                ),
                state,
            ),
        )

    async def _handle_field_skip(
        self,
        user_message: str,
        message_id: str,
        state: GlobalState,
        handle_start_conversion_callback,
    ) -> MCPResponse:
        """Handle user request to skip a specific field.

        Args:
            user_message: User's message
            message_id: Message ID
            state: Global state
            handle_start_conversion_callback: Callback to start conversion

        Returns:
            MCPResponse
        """
        # Get the current field being asked from conversation context
        last_context = state.conversation_history[-1].get("context", {}) if len(state.conversation_history) >= 1 else {}

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

            # ✅ FIX: Validate input_path before restarting
            conversion_path = state.pending_conversion_input_path or state.input_path
            if not conversion_path or str(conversion_path) == "None":
                return MCPResponse.error_response(
                    reply_to=message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with conversion. Please upload a file first.",
                )

            # Restart conversion to ask for next field
            return cast(
                MCPResponse,
                await handle_start_conversion_callback(
                    MCPMessage(
                        target_agent="conversation",
                        action="start_conversion",
                        context={
                            "input_path": str(conversion_path),
                            "metadata": state.metadata,
                        },
                    ),
                    state,
                ),
            )

        return MCPResponse.error_response(
            reply_to=message_id,
            error_code="NO_CURRENT_FIELD",
            error_message="Could not determine which field to skip",
        )

    async def _handle_sequential_request(
        self,
        user_message: str,
        message_id: str,
        state: GlobalState,
        handle_start_conversion_callback,
    ) -> MCPResponse:
        """Handle user request for sequential (one-at-a-time) questioning.

        Args:
            user_message: User's message
            message_id: Message ID
            state: Global state
            handle_start_conversion_callback: Callback to start conversion

        Returns:
            MCPResponse
        """
        state.add_log(
            LogLevel.INFO,
            "User requested sequential questioning",
        )

        # Save the sequential preference in state
        state.user_wants_sequential = True

        # Acknowledge and restart
        sequential_ack = "Sure! I'll ask one question at a time."
        state.add_conversation_message(role="assistant", content=sequential_ack)

        # ✅ FIX: Validate input_path before restarting
        conversion_path = state.pending_conversion_input_path or state.input_path
        if not conversion_path or str(conversion_path) == "None":
            return MCPResponse.error_response(
                reply_to=message_id,
                error_code="INVALID_STATE",
                error_message="Cannot proceed with conversion. Please upload a file first.",
            )

        return cast(
            MCPResponse,
            await handle_start_conversion_callback(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(conversion_path),
                        "metadata": state.metadata,
                    },
                ),
                state,
            ),
        )

    def _user_expresses_intent_to_add_more(self, user_message: str) -> bool:
        """Detect if user wants to add metadata but hasn't provided concrete data yet.

        This distinguishes between:
        - "I want to add some more" (intent only, no data) → Returns True
        - "age: P90D" (concrete data) → Returns False
        - "proceed" (wants to continue) → Returns False

        Args:
            user_message: User's message

        Returns:
            True if message expresses intent to add without providing concrete data
        """
        intent_phrases = [
            "want to add",
            "like to add",
            "add more",
            "add some",
            "yes",
            "sure",
            "i'll add",
            "let me add",
            "can i add",
        ]

        msg_lower = user_message.lower().strip()

        # Check if message expresses intent
        has_intent = any(phrase in msg_lower for phrase in intent_phrases)

        # Check if message contains concrete data (field: value format)
        has_concrete_data = ":" in user_message or "=" in user_message

        # Check if message is short (likely just expressing intent, not providing data)
        is_short_message = len(user_message.split()) < 10

        # Return True only if: has intent AND no concrete data AND short message
        return has_intent and not has_concrete_data and is_short_message
