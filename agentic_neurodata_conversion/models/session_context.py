"""Session context data models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowStage(str, Enum):
    """Workflow stage enumeration."""

    INITIALIZED = "initialized"
    COLLECTING_METADATA = "collecting_metadata"
    CONVERTING = "converting"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentHistoryEntry(BaseModel):
    """Agent history entry model."""

    agent_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None


class DatasetInfo(BaseModel):
    """Dataset information model."""

    dataset_path: str
    format: str
    total_size_bytes: int
    file_count: int
    channel_count: Optional[int] = None
    sampling_rate_hz: Optional[float] = None
    duration_seconds: Optional[float] = None
    has_metadata_files: bool = False
    metadata_files: list[str] = Field(default_factory=list)


class MetadataExtractionResult(BaseModel):
    """Metadata extraction result model."""

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
    extraction_confidence: dict[str, str] = Field(default_factory=dict)
    llm_extraction_log: Optional[str] = None


class ConversionResults(BaseModel):
    """Conversion results model."""

    nwb_file_path: Optional[str] = None
    conversion_duration_seconds: Optional[float] = None
    conversion_warnings: list[str] = Field(default_factory=list)
    conversion_errors: list[str] = Field(default_factory=list)
    conversion_log: Optional[str] = None


class ValidationIssue(BaseModel):
    """Validation issue model."""

    severity: str
    message: str
    location: Optional[str] = None
    check_name: str


class ValidationResults(BaseModel):
    """Validation results model."""

    overall_status: str
    issue_count: dict[str, int]
    issues: list[ValidationIssue] = Field(default_factory=list)
    metadata_completeness_score: Optional[float] = None
    best_practices_score: Optional[float] = None
    validation_report_path: Optional[str] = None
    llm_validation_summary: Optional[str] = None


class SessionContext(BaseModel):
    """Session context model."""

    session_id: str
    workflow_stage: WorkflowStage = WorkflowStage.INITIALIZED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    current_agent: Optional[str] = None
    agent_history: list[AgentHistoryEntry] = Field(default_factory=list)
    dataset_info: Optional[DatasetInfo] = None
    metadata: Optional[MetadataExtractionResult] = None
    conversion_results: Optional[ConversionResults] = None
    validation_results: Optional[ValidationResults] = None
    requires_user_clarification: bool = False
    clarification_prompt: Optional[str] = None
    output_nwb_path: Optional[str] = None
    output_report_path: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
