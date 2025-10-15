"""
REST API request and response models.

This module defines the Pydantic models for the MCP server's REST API endpoints,
providing type safety and automatic validation for all HTTP requests and responses.
"""

from typing import Optional

from pydantic import BaseModel, Field


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

    user_input: str = Field(..., description="User's clarification or correction text")
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
