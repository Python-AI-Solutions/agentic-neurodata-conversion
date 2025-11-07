"""
Model Context Protocol (MCP) message schemas.

This module defines the message format for inter-agent communication
following the JSON-RPC 2.0 protocol structure.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class MCPMessage(BaseModel):
    """
    MCP message for agent-to-agent communication.

    Based on JSON-RPC 2.0 structure with additional fields for tracking.
    """

    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message identifier",
    )
    target_agent: str = Field(
        description="Target agent name (conversation|conversion|evaluation)",
    )
    action: str = Field(
        description="Action to perform (e.g., detect_format, run_conversion)",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific payload data",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Message creation timestamp",
    )
    reply_to: Optional[str] = Field(
        default=None,
        description="Message ID this is replying to",
    )

    # Pydantic V2 configuration
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class MCPResponse(BaseModel):
    """
    Response to an MCP message.

    Follows JSON-RPC 2.0 response structure.
    """

    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique response identifier",
    )
    reply_to: str = Field(
        description="Message ID this response corresponds to",
    )
    success: bool = Field(
        description="Whether the action succeeded",
    )
    result: Optional[dict[str, Any]] = Field(
        default=None,
        description="Action result data (if success=True)",
    )
    error: Optional[dict[str, Any]] = Field(
        default=None,
        description="Error details (if success=False)",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response creation timestamp",
    )

    # Pydantic V2 configuration
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    @classmethod
    def success_response(
        cls,
        reply_to: str,
        result: dict[str, Any],
    ) -> "MCPResponse":
        """
        Create a success response.

        Args:
            reply_to: Original message ID
            result: Result data

        Returns:
            MCPResponse with success=True
        """
        return cls(
            reply_to=reply_to,
            success=True,
            result=result,
        )

    @classmethod
    def error_response(
        cls,
        reply_to: str,
        error_code: str,
        error_message: str,
        error_context: Optional[dict[str, Any]] = None,
    ) -> "MCPResponse":
        """
        Create an error response.

        Args:
            reply_to: Original message ID
            error_code: Error code (e.g., INVALID_FORMAT, CONVERSION_FAILED)
            error_message: Human-readable error message
            error_context: Optional additional error context

        Returns:
            MCPResponse with success=False
        """
        return cls(
            reply_to=reply_to,
            success=False,
            error={
                "code": error_code,
                "message": error_message,
                "context": error_context or {},
            },
        )


class MCPEvent(BaseModel):
    """
    Event notification (one-way, no response expected).

    Used for status updates, progress notifications, etc.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique event identifier",
    )
    event_type: str = Field(
        description="Event type (e.g., status_update, progress_update)",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Event creation timestamp",
    )

    # Pydantic V2 configuration
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
