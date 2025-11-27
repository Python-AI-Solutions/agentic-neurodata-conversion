"""Chat router for conversational interaction and user input endpoints.

Handles:
- Natural language chat with LLM-driven conversation
- Smart chat that works in all states
- User input submission (format selection, corrections)
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, Form, HTTPException

from agentic_neurodata_conversion.api.dependencies import get_or_create_mcp_server
from agentic_neurodata_conversion.api.middleware.rate_limiter import rate_limit_llm
from agentic_neurodata_conversion.models import (
    ConversionStatus,
    LogLevel,
    MCPMessage,
    UserInputRequest,
    UserInputResponse,
)
from agentic_neurodata_conversion.models.state import ConversationPhase

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/user-input", response_model=UserInputResponse)
async def submit_user_input(request: UserInputRequest):
    """Submit user input (e.g., format selection, corrections).

    Used for structured user input such as format selection during conversion.
    This is different from free-form chat and is typically triggered by
    specific UI actions (dropdowns, buttons, etc.).

    Args:
        request: User input request containing input_data

    Returns:
        Response with acceptance status and new conversion state

    Raises:
        HTTPException 400: If invalid state or input data
    """
    mcp_server = get_or_create_mcp_server()

    # Check if we're awaiting format selection
    if mcp_server.global_state.status == ConversionStatus.AWAITING_USER_INPUT and "format" in request.input_data:
        # Format selection
        format_msg = MCPMessage(
            target_agent="conversation",
            action="user_format_selection",
            context={"format": request.input_data["format"]},
        )

        response = await mcp_server.send_message(format_msg)

        if not response.success:
            raise HTTPException(
                status_code=400,
                detail=response.error["message"],
            )

        return UserInputResponse(
            accepted=True,
            message="Format selection accepted, conversion started",
            new_status=ConversionStatus.CONVERTING,
        )

    raise HTTPException(
        status_code=400,
        detail="Invalid state for user input",
    )


@router.post("/chat")
async def chat_message(message: str = Form(...), _: None = Depends(rate_limit_llm)):
    """Send a conversational message to the LLM-driven chat.

    Enables natural conversation for gathering metadata, answering questions
    about validation issues, and providing corrections. The conversation is
    contextual and aware of the current conversion state.

    Features:
    - Multi-turn conversation support
    - Metadata extraction from natural language
    - Automatic conversion triggering when ready
    - LLM processing lock to prevent concurrent calls

    Args:
        message: User's conversational message

    Returns:
        Dictionary containing:
        - message: LLM's response
        - status: Conversation status (continues, complete, ready_to_convert, etc.)
        - needs_more_info: Whether more user input is needed
        - extracted_metadata: Any metadata extracted from the message
        - ready_to_proceed: Whether user has confirmed readiness to convert
    """
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # Check if LLM is already processing
    if state.llm_processing:
        return {
            "message": "I'm still processing your previous message. Please wait a moment...",
            "status": "busy",
            "needs_more_info": False,
            "extracted_metadata": {},
        }

    # Initialize LLM lock if not already initialized (lazy initialization)
    if state._llm_lock is None:
        # Thread-safe initialization using the lock init lock
        with state._lock_init_lock:
            # Double-check pattern to prevent race condition
            if state._llm_lock is None:
                object.__setattr__(state, "_llm_lock", asyncio.Lock())

    # Acquire LLM lock to prevent concurrent processing
    async with state._llm_lock:
        state.llm_processing = True
        try:
            # Send conversational message
            chat_msg = MCPMessage(
                target_agent="conversation",
                action="conversational_response",
                context={"message": message},
            )

            # Add timeout to prevent indefinite waiting
            response = await asyncio.wait_for(
                mcp_server.send_message(chat_msg),
                timeout=180.0,  # 3 minute timeout for LLM processing
            )

        except TimeoutError:
            state.add_log(
                LogLevel.ERROR,
                "Chat LLM call timed out",
                {"message": message[:100]},
            )
            return {
                "message": "I'm sorry, that request is taking longer than expected. Please try a simpler message or try again in a moment.",
                "status": "error",
                "error": "timeout",
                "needs_more_info": True,
                "extracted_metadata": {},
            }
        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Chat endpoint error: {str(e)}",
                {"message": message[:100], "error_type": type(e).__name__},
            )
            return {
                "message": f"I encountered an error: {str(e)}. Please try rephrasing your message.",
                "status": "error",
                "error": str(e),
                "needs_more_info": True,
                "extracted_metadata": {},
            }
        finally:
            state.llm_processing = False

    # Validate response object
    if not response:
        state.add_log(LogLevel.ERROR, "Empty response from conversation agent")
        return {
            "message": "I'm having trouble processing that. Could you try rephrasing?",
            "status": "error",
            "error": "empty_response",
            "needs_more_info": True,
            "extracted_metadata": {},
        }

    if not response.success:
        error_msg = (
            response.error.get("message", "Failed to process message")
            if hasattr(response, "error") and response.error
            else "Unknown error"
        )
        state.add_log(
            LogLevel.ERROR,
            "Conversation agent returned error",
            {"error": error_msg},
        )
        return {
            "message": f"I encountered an issue: {error_msg}. Please try again.",
            "status": "error",
            "error": error_msg,
            "needs_more_info": True,
            "extracted_metadata": {},
        }

    result = response.result if hasattr(response, "result") else {}

    # Validate result has required fields
    if not isinstance(result, dict):
        state.add_log(LogLevel.ERROR, "Invalid result type from conversation agent", {"type": str(type(result))})
        result = {}

    # Determine status explicitly based on workflow state
    # This ensures frontend can reliably detect conversation continuation vs completion
    ready_to_proceed = result.get("ready_to_proceed", False)
    needs_more_info = result.get("needs_more_info", True)  # Default to True for safety

    # Auto-trigger conversion when user confirms ready
    # This prevents the Agent 1 → Agent 2 handoff failure
    if ready_to_proceed and state.input_path:
        state.add_log(
            LogLevel.INFO,
            "User confirmed ready to proceed - triggering conversion",
            {"ready_to_proceed": ready_to_proceed},
        )

        # Trigger conversion workflow in background
        from agentic_neurodata_conversion.agents import register_conversation_agent

        # Create conversion task message
        register_conversation_agent(mcp_server)

        # Get format from state or detect it
        format_name = state.detected_format if state.detected_format else "unknown"

        # If format is unknown, we need to detect it first
        if format_name == "unknown":
            from agentic_neurodata_conversion.agents import register_conversion_agent

            register_conversion_agent(mcp_server)

            detect_msg = MCPMessage(
                target_agent="conversion",
                action="detect_format",
                context={"input_path": state.input_path},
            )
            detect_response = await mcp_server.send_message(detect_msg)

            if detect_response.success:
                format_name = detect_response.result.get("format", "unknown")
                state.detected_format = format_name
                state.add_log(LogLevel.INFO, f"Detected format: {format_name}")

        # Now trigger actual conversion
        start_msg = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={
                "input_path": state.input_path,
                "metadata": state.metadata,
            },
        )

        # Trigger conversion with proper error handling
        # The frontend will poll /api/status to monitor progress
        try:
            # Use create_task with error callback to prevent silent failures
            task = asyncio.create_task(mcp_server.send_message(start_msg))

            # Add error callback to log failures
            def handle_task_error(t):
                try:
                    t.result()
                except Exception as e:
                    logger.error(f"Conversion task failed: {e}", exc_info=True)
                    # Update state to reflect failure
                    if mcp_server.global_state:
                        mcp_server.global_state.status = ConversionStatus.FAILED
                        mcp_server.global_state.add_log(LogLevel.ERROR, f"Conversion failed: {str(e)}")

            task.add_done_callback(handle_task_error)
        except Exception as e:
            logger.error(f"Failed to start conversion: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to start conversion: {str(e)}")

        response_status = "ready_to_convert"
    elif needs_more_info:
        # Continue multi-turn conversation - frontend keeps chat active
        response_status = "conversation_continues"
    else:
        # Conversation complete but user hasn't confirmed ready yet
        response_status = "conversation_complete"

    # Override with explicit status from result if provided (trust the agent)
    response_status = result.get("status", response_status)

    # Return response with explicit status for frontend compatibility
    return {
        "message": result.get("message", "I processed your message but have no specific response."),
        "status": response_status,
        "needs_more_info": needs_more_info,
        "extracted_metadata": result.get("extracted_metadata", {}),
        "ready_to_proceed": ready_to_proceed,
    }


@router.post("/chat/smart")
async def smart_chat(message: str = Form(...), _: None = Depends(rate_limit_llm)):
    """Smart chat endpoint that works in ALL states, at ANY time.

    This makes the system feel like Claude.ai - always ready to help.
    Users can ask questions before upload, during conversion, after validation.
    The LLM understands context and provides intelligent, state-aware responses.

    Intelligently routes between:
    - Conversational response handler (during active conversations)
    - General query handler (for informational questions)

    Args:
        message: User's message/question

    Returns:
        Dictionary containing:
        - type: Response type (general_query_response, conversation_continues, etc.)
        - answer: LLM's intelligent response
        - suggestions: Optional follow-up suggestions
        - suggested_action: Optional suggested user action
    """
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # Check if LLM is already processing
    if state.llm_processing:
        return {
            "type": "busy",
            "answer": "I'm still processing your previous message. Please wait a moment...",
            "suggestions": [],
            "actions": [],
        }

    # Initialize LLM lock if not already initialized (lazy initialization)
    if state._llm_lock is None:
        # Thread-safe initialization using the lock init lock
        with state._lock_init_lock:
            # Double-check pattern to prevent race condition
            if state._llm_lock is None:
                object.__setattr__(state, "_llm_lock", asyncio.Lock())

    # Acquire LLM lock to prevent concurrent processing
    async with state._llm_lock:
        state.llm_processing = True
        try:
            # Route intelligently based on conversation state
            # If we're in an active conversation (metadata collection, custom metadata, metadata review),
            # route to conversational_response instead of general_query
            active_conversation_types = {
                "metadata_collection",
                "custom_metadata_collection",
                "metadata_review",
                "validation_correction",
            }

            # Check if we're in an active conversation requiring conversational handling
            in_active_conversation = (
                state.conversation_type in active_conversation_types
                or state.conversation_phase == ConversationPhase.METADATA_COLLECTION
            )

            if in_active_conversation:
                # Route to conversational response handler
                query_msg = MCPMessage(
                    target_agent="conversation",
                    action="conversational_response",
                    context={"message": message},
                )
            else:
                # Route to general query handler
                query_msg = MCPMessage(
                    target_agent="conversation",
                    action="general_query",
                    context={"query": message},
                )

            response = await mcp_server.send_message(query_msg)
        finally:
            state.llm_processing = False

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.error.get("message", "Failed to process your question"),
        )

    result = response.result
    return {
        "type": result.get("type", "general_query_response"),
        "answer": result.get("answer"),
        "suggestions": result.get("suggestions", []),
        "suggested_action": result.get("suggested_action"),
    }
