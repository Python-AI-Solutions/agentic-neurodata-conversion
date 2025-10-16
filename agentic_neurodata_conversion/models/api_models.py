"""API request/response models."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from agentic_neurodata_conversion.models.session_context import ValidationIssue


class SessionInitializeRequest(BaseModel):
    """Session initialization request model."""

    dataset_path: str


class SessionInitializeResponse(BaseModel):
    """Session initialization response model."""

    session_id: str
    message: str
    workflow_stage: str


class SessionStatusResponse(BaseModel):
    """Session status response model."""

    session_id: str
    workflow_stage: str
    progress_percentage: int
    status_message: str
    current_agent: Optional[str] = None
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None


class SessionClarifyRequest(BaseModel):
    """Session clarification request model."""

    user_input: Optional[str] = None
    updated_metadata: Optional[dict[str, str]] = None


class SessionClarifyResponse(BaseModel):
    """Session clarification response model."""

    message: str
    workflow_stage: str


class SessionResultResponse(BaseModel):
    """Session result response model."""

    session_id: str
    nwb_file_path: Optional[str] = None
    validation_report_path: Optional[str] = None
    overall_status: str
    llm_validation_summary: Optional[str] = None
    validation_issues: list[ValidationIssue] = Field(default_factory=list)


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    agents_registered: list[str] = Field(default_factory=list)
    redis_connected: bool


class AgentRegistrationRequest(BaseModel):
    """Agent registration request model."""

    agent_name: str
    agent_type: str
    base_url: str
    capabilities: list[str] = Field(default_factory=list)


class RouteMessageRequest(BaseModel):
    """Message routing request model."""

    target_agent: str
    message_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
