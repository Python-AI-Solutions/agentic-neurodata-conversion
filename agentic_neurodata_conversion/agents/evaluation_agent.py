"""Placeholder for EvaluationAgent (to be implemented in Phase 6)."""

from typing import Any

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage


class EvaluationAgent(BaseAgent):
    """Evaluation agent for NWB file validation (Phase 6 implementation pending)."""

    def get_capabilities(self) -> list[str]:
        """
        Return evaluation agent capabilities.

        Returns:
            List of capability strings
        """
        return ["validate_nwb", "generate_report"]

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
            "message": "EvaluationAgent not yet implemented (Phase 6)",
            "session_id": message.session_id,
        }
