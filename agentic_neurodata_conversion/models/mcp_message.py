"""
MCP (Model Context Protocol) message models.

This module defines the message format for communication between agents
and the MCP server following the MCP protocol specification.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """MCP message types for agent communication."""

    AGENT_REGISTER = "agent_register"
    AGENT_EXECUTE = "agent_execute"
    AGENT_RESPONSE = "agent_response"
    CONTEXT_UPDATE = "context_update"
    ERROR = "error"
    HEALTH_CHECK = "health_check"
    HEALTH_RESPONSE = "health_response"


class MCPMessage(BaseModel):
    """
    MCP protocol message for agent communication.

    All communication between agents and the MCP server uses this message format.
    Messages are sent via HTTP POST to agent endpoints or the MCP server.
    """

    message_id: str = Field(..., description="Unique message identifier (UUID)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent: str = Field(..., description="Sending agent name or 'mcp_server'")
    target_agent: str = Field(..., description="Receiving agent name or 'mcp_server'")
    session_id: Optional[str] = Field(
        None, description="Session context identifier (if applicable)"
    )
    message_type: MessageType = Field(..., description="Type of message")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Message-specific payload data"
    )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


# Example payload structures by message type:
#
# AGENT_REGISTER payload:
# {
#     "agent_name": "conversation_agent",
#     "agent_type": "conversation",
#     "capabilities": ["format_detection", "metadata_extraction"],
#     "health_check_url": "http://localhost:3001/health"
# }
#
# AGENT_EXECUTE payload:
# {
#     "task": "initialize_session",
#     "session_id": "550e8400-e29b-41d4-a716-446655440000",
#     "parameters": {
#         "dataset_path": "/data/openephys_dataset"
#     }
# }
#
# AGENT_RESPONSE payload:
# {
#     "task": "initialize_session",
#     "status": "success",  # or "failed"
#     "result": {
#         "dataset_info": {...},
#         "next_agent": "conversion_agent"
#     },
#     "error": None  # or error details if failed
# }
#
# CONTEXT_UPDATE payload:
# {
#     "updates": {
#         "workflow_stage": "converting",
#         "current_agent": "conversion_agent"
#     }
# }
