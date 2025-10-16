"""
REST API request and response models.

This module defines the Pydantic models for the MCP server's REST API endpoints,
providing type safety and automatic validation for all HTTP requests and responses.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from agentic_neurodata_conversion.models.mcp_message import MessageType


class SessionInitializeRequest(BaseModel):
    """Request to initialize a new conversion session."""

    dataset_path: str = Field(..., description="Absolute path to the dataset directory")


class SessionInitializeResponse(BaseModel):
    """Response from session initialization."""

    session_id: str = Field(..., description="Unique session identifier (UUID)")
    message: str = Field(..., description="User-facing status message")
    workflow_stage: str = Field(..., description="Current workflow stage")


class SessionStatusResponse(BaseModel):
    """Response from session status check."""

    session_id: str = Field(..., description="Session identifier")
    workflow_stage: str = Field(..., description="Current workflow stage")
    progress_percentage: int = Field(
        ..., description="Progress from 0 to 100", ge=0, le=100
    )
    status_message: str = Field(..., description="Human-readable status message")
    current_agent: Optional[str] = Field(None, description="Agent currently executing")
    requires_clarification: bool = Field(
        default=False, description="Whether user clarification is needed"
    )
    clarification_prompt: Optional[str] = Field(
        None, description="Prompt for user clarification (if required)"
    )


class SessionClarifyRequest(BaseModel):
    """Request to provide clarification when errors occur."""

    user_input: Optional[str] = Field(
        None, description="User's clarification or correction text"
    )
    updated_metadata: Optional[dict[str, str]] = Field(
        None, description="Updated metadata fields (key-value pairs)"
    )


class SessionClarifyResponse(BaseModel):
    """Response after clarification is provided."""

    message: str = Field(..., description="Acknowledgment message")
    workflow_stage: str = Field(..., description="Updated workflow stage")


class SessionResultResponse(BaseModel):
    """Response with final conversion results."""

    session_id: str = Field(..., description="Session identifier")
    nwb_file_path: str = Field(..., description="Path to generated NWB file")
    validation_report_path: str = Field(
        ..., description="Path to JSON validation report"
    )
    overall_status: str = Field(
        ...,
        description="Overall validation status: passed, passed_with_warnings, or failed",
    )
    llm_validation_summary: str = Field(
        ..., description="LLM-generated human-readable validation summary"
    )
    validation_issues: list[dict[str, str]] = Field(
        default_factory=list, description="List of validation issues (if any)"
    )


class HealthCheckResponse(BaseModel):
    """Response from health check endpoint."""

    status: str = Field(..., description="Service status: healthy or unhealthy")
    version: str = Field(..., description="Package version (e.g., '0.1.0')")
    agents_registered: list[str] = Field(
        ..., description="List of registered agent names"
    )
    redis_connected: bool = Field(..., description="Whether Redis connection is active")


# Internal API Models (for agent-to-MCP communication)


class AgentRegistrationRequest(BaseModel):
    """Request for internal agent registration."""

    agent_name: str = Field(..., description="Unique agent identifier")
    agent_type: str = Field(
        ..., description="Agent type: conversation, conversion, or evaluation"
    )
    base_url: str = Field(..., description="Base URL for agent communication")
    capabilities: list[str] = Field(
        default_factory=list, description="List of agent capabilities"
    )


class RouteMessageRequest(BaseModel):
    """Request to route a message to another agent."""

    target_agent: str = Field(..., description="Name of target agent")
    message_type: MessageType = Field(..., description="Type of MCP message")
    payload: dict[str, Any] = Field(default_factory=dict, description="Message payload")
