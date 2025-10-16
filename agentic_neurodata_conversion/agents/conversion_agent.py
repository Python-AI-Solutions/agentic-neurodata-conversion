"""Placeholder for ConversionAgent (to be implemented in Phase 5)."""

from typing import Any

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage


class ConversionAgent(BaseAgent):
    """Conversion agent for NWB file generation (Phase 5 implementation pending)."""

    def get_capabilities(self) -> list[str]:
        """
        Return conversion agent capabilities.

        Returns:
            List of capability strings
        """
        return ["convert_to_nwb", "validate_conversion"]

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
            "message": "ConversionAgent not yet implemented (Phase 5)",
            "session_id": message.session_id,
        }
