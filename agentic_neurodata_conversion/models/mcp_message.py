"""MCP message data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message type enumeration."""

    AGENT_REGISTER = "agent_register"
    AGENT_EXECUTE = "agent_execute"
    AGENT_RESPONSE = "agent_response"
    CONTEXT_UPDATE = "context_update"
    ERROR = "error"
    HEALTH_CHECK = "health_check"
    HEALTH_RESPONSE = "health_response"


class MCPMessage(BaseModel):
    """MCP message model."""

    message_id: str
    source_agent: str
    target_agent: str
    message_type: MessageType
    session_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
        }
