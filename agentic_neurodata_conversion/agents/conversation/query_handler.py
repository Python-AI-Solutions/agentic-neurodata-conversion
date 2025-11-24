"""Query handler module for conversation agent.

Handles:
- User format selection (when format detection is ambiguous)
- Simple user queries and responses

This module handles simple query-based interactions that don't
require complex workflows.
"""

import logging
from typing import TYPE_CHECKING, cast

from agentic_neurodata_conversion.models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class QueryHandler:
    """Handles simple query-based user interactions.

    This class manages straightforward user inputs like:
    - Manual format selection when detection is ambiguous
    - Simple yes/no responses
    - Direct field value inputs

    These are simpler than the conversational workflow which handles
    natural language multi-turn conversations.
    """

    def __init__(self):
        """Initialize query handler."""
        logger.info("QueryHandler initialized")

    async def handle_user_format_selection(
        self,
        message: MCPMessage,
        state: GlobalState,
        run_conversion_callback,  # Callback to run conversion
    ) -> MCPResponse:
        """Handle user's manual format selection.

        This is called when format detection is ambiguous and we need
        the user to manually select from a list of supported formats.

        Args:
            message: MCP message with selected format
            state: Global state
            run_conversion_callback: Callback to run conversion

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
        return cast(
            MCPResponse,
            await run_conversion_callback(
                message.message_id,
                state.input_path,
                selected_format,
                state.metadata,
                state,
            ),
        )
