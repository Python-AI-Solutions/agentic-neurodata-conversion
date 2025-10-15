"""
Session context and related data models.

This module defines the core data structures for tracking conversion sessions,
including workflow stages, dataset information, metadata, conversion results,
and validation results.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowStage(str, Enum):
    """Workflow stages for the conversion pipeline."""

    INITIALIZED = "initialized"
    COLLECTING_METADATA = "collecting_metadata"
    CONVERTING = "converting"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentHistoryEntry(BaseModel):
    """Record of agent execution within a session."""

    agent_name: str = Field(..., description="Name of agent that executed")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution end time")
    status: str = Field(..., description="success, failed, or in_progress")
    error_message: Optional[str] = Field(None, description="Error if failed")
    stack_trace: Optional[str] = Field(None, description="Stack trace if failed")


class DatasetInfo(BaseModel):
    """Basic dataset information extracted during format detection."""

    dataset_path: str = Field(..., description="Absolute path to dataset")
    format: str = Field(..., description="Detected format (e.g., openephys)")
    total_size_bytes: int = Field(..., description="Total dataset size in bytes")
    file_count: int = Field(..., description="Number of files in dataset")
    channel_count: Optional[int] = Field(
        None, description="Number of recording channels"
    )
    sampling_rate_hz: Optional[float] = Field(None, description="Sampling rate in Hz")
    duration_seconds: Optional[float] = Field(
        None, description="Recording duration in seconds"
    )
    has_metadata_files: bool = Field(False, description="Whether .md files were found")
    metadata_files: list[str] = Field(
        default_factory=list, description="List of .md file paths"
    )


class MetadataExtractionResult(BaseModel):
    """Metadata extracted from .md files using LLM."""

    subject_id: Optional[str] = None
    species: Optional[str] = None
    age: Optional[str] = None
    sex: Optional[str] = None
    session_start_time: Optional[str] = None
    experimenter: Optional[str] = None
    device_name: Optional[str] = None
    manufacturer: Optional[str] = None
    recording_location: Optional[str] = None
    description: Optional[str] = None
    extraction_confidence: dict[str, str] = Field(
        default_factory=dict,
        description="Confidence per field: high, medium, low, default, empty",
    )
    llm_extraction_log: Optional[str] = Field(
        None, description="LLM extraction reasoning and process log"
    )


class ConversionResults(BaseModel):
    """Results from the conversion agent."""

    nwb_file_path: Optional[str] = Field(None, description="Path to generated NWB file")
    conversion_duration_seconds: Optional[float] = None
    conversion_warnings: list[str] = Field(default_factory=list)
    conversion_errors: list[str] = Field(default_factory=list)
    conversion_log: Optional[str] = Field(None, description="Full conversion log")


class ValidationIssue(BaseModel):
    """Single validation issue from NWB Inspector."""

    severity: str = Field(..., description="critical, warning, or info")
    message: str = Field(..., description="Issue description")
    location: Optional[str] = Field(None, description="Location in NWB file")
    check_name: str = Field(..., description="Name of validation check")


class ValidationResults(BaseModel):
    """Results from the evaluation agent."""

    overall_status: str = Field(
        ..., description="passed, passed_with_warnings, or failed"
    )
    issue_count: dict[str, int] = Field(
        default_factory=dict, description="Counts by severity: critical, warning, info"
    )
    issues: list[ValidationIssue] = Field(default_factory=list)
    metadata_completeness_score: Optional[float] = Field(
        None, description="Score from 0.0 to 1.0"
    )
    best_practices_score: Optional[float] = Field(
        None, description="Score from 0.0 to 1.0"
    )
    validation_report_path: Optional[str] = Field(
        None, description="Path to JSON validation report"
    )
    llm_validation_summary: Optional[str] = Field(
        None, description="LLM-generated validation summary"
    )


class SessionContext(BaseModel):
    """
    Complete session context stored in Redis and filesystem.

    This model represents the full state of a conversion session and is
    persisted using a write-through strategy (Redis + filesystem backup).
    """

    session_id: str = Field(..., description="Unique session identifier (UUID)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    current_agent: Optional[str] = Field(None, description="Agent currently executing")
    workflow_stage: WorkflowStage = Field(default=WorkflowStage.INITIALIZED)
    agent_history: list[AgentHistoryEntry] = Field(default_factory=list)

    # Data collected during workflow
    dataset_info: Optional[DatasetInfo] = None
    metadata: Optional[MetadataExtractionResult] = None
    conversion_results: Optional[ConversionResults] = None
    validation_results: Optional[ValidationResults] = None

    # Output paths
    output_nwb_path: Optional[str] = None
    output_report_path: Optional[str] = None

    # Error tracking and user interaction
    requires_user_clarification: bool = Field(default=False)
    clarification_prompt: Optional[str] = Field(
        None, description="Prompt for user when clarification needed"
    )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
