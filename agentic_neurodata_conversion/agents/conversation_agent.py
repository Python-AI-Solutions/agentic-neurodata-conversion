"""Placeholder for ConversationAgent (to be implemented in Phase 4)."""

from typing import Any

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage


class ConversationAgent(BaseAgent):
    """Conversation agent for metadata extraction (Phase 4 implementation pending)."""

    def get_capabilities(self) -> list[str]:
        """
        Return conversation agent capabilities.

        Returns:
            List of capability strings
        """
        return ["initialize_session", "handle_clarification"]

    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """
        Handle incoming MCP message (placeholder implementation).

        Args:
            message: MCP message to handle

        Returns:
            Error response indicating agent not yet implemented
        """
        return {
            "status": "error",
            "message": "ConversationAgent not yet implemented (Phase 4)",
            "session_id": message.session_id,
        }
