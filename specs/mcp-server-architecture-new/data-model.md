# Data Model: MCP Server Architecture

**Date**: 2025-10-10
**Phase**: 1 - Design Artifacts
**Feature**: MCP Server Architecture

This document defines the core domain models using Pydantic 2.5+ for validation and serialization. All models support JSON serialization for API responses and checkpoint persistence.

---

## 1. ConversionSession

Represents a complete conversion workflow from start to finish with state machine management.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

class SessionState(str, Enum):
    """Workflow state machine states"""
    ANALYZING = "analyzing"                  # Format detection in progress
    COLLECTING_METADATA = "collecting_metadata"  # Metadata questioner active
    CONVERTING = "converting"                # Conversion agent executing
    VALIDATING = "validating"                # Evaluation agent running
    COMPLETED = "completed"                  # Workflow finished successfully
    FAILED = "failed"                        # Workflow terminated with errors
    CANCELLED = "cancelled"                  # User-requested termination
    SUSPENDED = "suspended"                  # Awaiting user input

class Checkpoint(BaseModel):
    """Recovery checkpoint within a session"""
    checkpoint_id: UUID = Field(default_factory=uuid4)
    version: int = Field(ge=1, description="Monotonically increasing version")
    state: SessionState
    created_at: datetime = Field(default_factory=datetime.utcnow)
    workflow_step: str = Field(description="Current step identifier")
    step_index: int = Field(ge=0, description="Index in workflow DAG")
    intermediate_results: Dict[str, Any] = Field(default_factory=dict)
    error_context: Optional[Dict[str, Any]] = None

class ConversionSession(BaseModel):
    """Complete conversion workflow session"""
    session_id: UUID = Field(default_factory=uuid4)
    user_id: str = Field(description="User or system identifier")
    workflow_definition_id: UUID
    state: SessionState = SessionState.ANALYZING
    version: int = Field(default=1, ge=1, description="Optimistic locking version")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(description="Session timeout")
    completed_at: Optional[datetime] = None

    # Workflow tracking
    current_step: Optional[str] = None
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    checkpoints: List[Checkpoint] = Field(default_factory=list)

    # Results
    format_detection_result: Optional[Dict[str, Any]] = None
    metadata_collection_result: Optional[Dict[str, Any]] = None
    conversion_result: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    @field_validator('state')
    @classmethod
    def validate_state_transition(cls, v: SessionState, info) -> SessionState:
        """Validate state machine transitions"""
        # Valid transitions (simplified, full FSM in implementation)
        valid_transitions = {
            SessionState.ANALYZING: [SessionState.COLLECTING_METADATA, SessionState.FAILED, SessionState.CANCELLED],
            SessionState.COLLECTING_METADATA: [SessionState.CONVERTING, SessionState.SUSPENDED, SessionState.FAILED, SessionState.CANCELLED],
            SessionState.CONVERTING: [SessionState.VALIDATING, SessionState.FAILED, SessionState.CANCELLED],
            SessionState.VALIDATING: [SessionState.COMPLETED, SessionState.FAILED, SessionState.CANCELLED],
            SessionState.SUSPENDED: [SessionState.COLLECTING_METADATA, SessionState.CANCELLED],
            SessionState.COMPLETED: [],  # Terminal state
            SessionState.FAILED: [],     # Terminal state
            SessionState.CANCELLED: [],  # Terminal state
        }
        # Actual validation done in service layer with previous state context
        return v

    def create_checkpoint(self, step: str, step_index: int, results: Dict[str, Any]) -> Checkpoint:
        """Create a new checkpoint for recovery"""
        checkpoint = Checkpoint(
            version=self.version + 1,
            state=self.state,
            workflow_step=step,
            step_index=step_index,
            intermediate_results=results
        )
        self.checkpoints.append(checkpoint)
        self.version = checkpoint.version
        return checkpoint

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Retrieve most recent checkpoint"""
        return self.checkpoints[-1] if self.checkpoints else None

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "researcher@university.edu",
                "workflow_definition_id": "223e4567-e89b-12d3-a456-426614174001",
                "state": "converting",
                "version": 3,
                "current_step": "nwb_generation",
                "progress_percentage": 65.5
            }
        }
```

---

## 2. WorkflowDefinition

Defines the structure and execution order of conversion steps with DAG validation.

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Optional, Any
from uuid import UUID, uuid4
import networkx as nx

class WorkflowStep(BaseModel):
    """Single step in workflow DAG"""
    step_id: str = Field(description="Unique step identifier")
    agent_type: str = Field(description="Agent to invoke: conversation, metadata_questioner, conversion, evaluation")
    configuration: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, gt=0, le=3600)
    retry_policy: Optional[Dict[str, Any]] = None
    required: bool = Field(default=True, description="Whether step is mandatory")

class WorkflowDependency(BaseModel):
    """Dependency edge in workflow DAG"""
    from_step: str = Field(description="Upstream step ID")
    to_step: str = Field(description="Downstream step ID")
    condition: Optional[str] = Field(default=None, description="Conditional dependency expression")

class RetryPolicy(BaseModel):
    """Failure handling configuration"""
    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_delay_seconds: float = Field(default=1.0, gt=0)
    max_delay_seconds: float = Field(default=60.0, gt=0)
    exponential_base: float = Field(default=2.0, gt=1.0)
    jitter: bool = Field(default=True)

class WorkflowDefinition(BaseModel):
    """Complete workflow structure with DAG"""
    workflow_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None

    steps: List[WorkflowStep] = Field(min_length=1)
    dependencies: List[WorkflowDependency] = Field(default_factory=list)

    # Global configuration
    global_timeout_seconds: int = Field(default=1800, gt=0, description="Overall workflow timeout")
    default_retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)

    # Resource requirements
    estimated_duration_seconds: Optional[int] = None
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_dag_structure(self) -> 'WorkflowDefinition':
        """Validate DAG properties: no cycles, valid step references"""
        # Build graph
        G = nx.DiGraph()
        step_ids = {step.step_id for step in self.steps}

        # Add nodes
        for step in self.steps:
            G.add_node(step.step_id)

        # Add edges
        for dep in self.dependencies:
            if dep.from_step not in step_ids:
                raise ValueError(f"Invalid dependency: from_step '{dep.from_step}' not in workflow steps")
            if dep.to_step not in step_ids:
                raise ValueError(f"Invalid dependency: to_step '{dep.to_step}' not in workflow steps")
            G.add_edge(dep.from_step, dep.to_step)

        # Check for cycles
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.simple_cycles(G))
            raise ValueError(f"Workflow contains circular dependencies: {cycles}")

        return self

    def get_execution_order(self) -> List[List[str]]:
        """Return topologically sorted execution levels for parallel execution"""
        G = nx.DiGraph()
        for step in self.steps:
            G.add_node(step.step_id)
        for dep in self.dependencies:
            G.add_edge(dep.from_step, dep.to_step)

        # Group by topological level for parallel execution
        levels = []
        remaining = set(G.nodes())
        while remaining:
            # Find nodes with no incoming edges from remaining nodes
            level = [n for n in remaining if not any(pred in remaining for pred in G.predecessors(n))]
            if not level:
                break  # Should not happen if DAG validation passed
            levels.append(level)
            remaining -= set(level)

        return levels

    def get_step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        """Retrieve step configuration by ID"""
        return next((step for step in self.steps if step.step_id == step_id), None)

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "223e4567-e89b-12d3-a456-426614174001",
                "name": "Standard NWB Conversion",
                "steps": [
                    {"step_id": "format_detection", "agent_type": "conversation", "timeout_seconds": 120},
                    {"step_id": "metadata_collection", "agent_type": "metadata_questioner", "timeout_seconds": 600},
                    {"step_id": "conversion", "agent_type": "conversion", "timeout_seconds": 900},
                    {"step_id": "validation", "agent_type": "evaluation", "timeout_seconds": 300}
                ],
                "dependencies": [
                    {"from_step": "format_detection", "to_step": "metadata_collection"},
                    {"from_step": "metadata_collection", "to_step": "conversion"},
                    {"from_step": "conversion", "to_step": "validation"}
                ]
            }
        }
```

---

## 3. AgentInvocation

Records a single agent call within a workflow with retry tracking.

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4

class AgentType(str, Enum):
    """Supported agent types"""
    CONVERSATION = "conversation"
    METADATA_QUESTIONER = "metadata_questioner"
    CONVERSION = "conversion"
    EVALUATION = "evaluation"

class InvocationStatus(str, Enum):
    """Agent invocation lifecycle states"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class AgentInvocation(BaseModel):
    """Single agent call record with retry tracking"""
    invocation_id: UUID = Field(default_factory=uuid4)
    agent_type: AgentType
    session_id: UUID

    # Request/response
    request: Dict[str, Any] = Field(description="Agent input parameters")
    response: Optional[Dict[str, Any]] = None

    # Status tracking
    status: InvocationStatus = InvocationStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Retry tracking
    attempt_number: int = Field(default=1, ge=1)
    max_attempts: int = Field(default=3, ge=1)
    retry_count: int = Field(default=0, ge=0)
    next_retry_at: Optional[datetime] = None

    # Error handling
    error: Optional[Dict[str, Any]] = None
    timeout_seconds: int = Field(default=300, gt=0)

    # Tracing
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None

    # Metadata
    agent_instance_id: Optional[str] = Field(default=None, description="Specific agent instance used")
    resource_allocation: Optional[Dict[str, Any]] = None

    def mark_started(self, trace_id: str, span_id: str):
        """Mark invocation as started"""
        self.status = InvocationStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.trace_id = trace_id
        self.span_id = span_id

    def mark_completed(self, response: Dict[str, Any]):
        """Mark invocation as successfully completed"""
        self.status = InvocationStatus.SUCCEEDED
        self.completed_at = datetime.utcnow()
        self.response = response
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def mark_failed(self, error: Dict[str, Any], should_retry: bool = False):
        """Mark invocation as failed with retry decision"""
        self.error = error
        self.completed_at = datetime.utcnow()

        if should_retry and self.retry_count < self.max_attempts - 1:
            self.retry_count += 1
            self.attempt_number += 1
            # Calculate next retry time with exponential backoff
            delay = min(2 ** self.retry_count, 60)  # Cap at 60 seconds
            self.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            self.status = InvocationStatus.PENDING
        else:
            self.status = InvocationStatus.FAILED

        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def mark_timeout(self):
        """Mark invocation as timed out"""
        self.status = InvocationStatus.TIMEOUT
        self.completed_at = datetime.utcnow()
        self.error = {
            "error_type": "timeout",
            "message": f"Agent invocation exceeded timeout of {self.timeout_seconds} seconds"
        }
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    class Config:
        json_schema_extra = {
            "example": {
                "invocation_id": "323e4567-e89b-12d3-a456-426614174002",
                "agent_type": "conversation",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "request": {"dataset_path": "/data/experiment_001"},
                "response": {"detected_format": "SpikeGLX", "confidence": 0.95},
                "status": "succeeded",
                "attempt_number": 1,
                "retry_count": 0,
                "duration_seconds": 12.5
            }
        }
```

---

## 4. FormatDetectionResult

Captures the outcome of automatic format detection with confidence scoring.

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime

class DetectedFormat(BaseModel):
    """Single format detection candidate"""
    format_name: str = Field(description="Canonical format name (e.g., SpikeGLX, Open Ephys)")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence 0-1")
    detection_method: str = Field(description="How detected: magic_bytes, extension, header, metadata")
    evidence: List[str] = Field(description="Supporting evidence for detection")
    neuroconv_interface: Optional[str] = Field(default=None, description="Recommended NeuroConv interface")

class FileInventoryItem(BaseModel):
    """Analyzed file in dataset"""
    file_path: Path
    file_size_bytes: int = Field(ge=0)
    file_extension: str
    mime_type: Optional[str] = None
    magic_bytes: Optional[str] = None
    analyzed: bool = Field(default=False)

class FormatDetectionResult(BaseModel):
    """Complete format detection outcome with confidence scoring"""
    detection_id: str = Field(description="Unique detection result ID")
    dataset_path: Path
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    # Detection results
    detected_formats: List[DetectedFormat] = Field(min_length=0)
    primary_format: Optional[DetectedFormat] = None

    # Analysis details
    confidence_explanation: str = Field(description="Human-readable detection rationale")
    alternative_formats: List[DetectedFormat] = Field(default_factory=list, description="Lower-confidence alternatives")

    # File analysis
    file_inventory: List[FileInventoryItem] = Field(default_factory=list)
    total_files_analyzed: int = Field(default=0, ge=0)
    total_dataset_size_bytes: int = Field(default=0, ge=0)

    # Metadata extraction
    metadata_found: Dict[str, Any] = Field(default_factory=dict)

    # Manual override
    manual_override: Optional[str] = Field(default=None, description="User-specified format override")
    override_justification: Optional[str] = None

    @field_validator('primary_format', mode='after')
    @classmethod
    def validate_primary_format(cls, v: Optional[DetectedFormat], info) -> Optional[DetectedFormat]:
        """Ensure primary format is highest confidence"""
        if v and info.data.get('detected_formats'):
            detected = info.data['detected_formats']
            if detected and v not in detected:
                raise ValueError("primary_format must be in detected_formats list")
        return v

    def rank_by_confidence(self) -> List[DetectedFormat]:
        """Return formats sorted by confidence (highest first)"""
        return sorted(self.detected_formats, key=lambda f: f.confidence, reverse=True)

    def get_top_n_formats(self, n: int = 3) -> List[DetectedFormat]:
        """Return top N formats by confidence"""
        return self.rank_by_confidence()[:n]

    def suggest_manual_override_needed(self) -> bool:
        """Determine if manual intervention is recommended"""
        if not self.detected_formats:
            return True
        if self.primary_format and self.primary_format.confidence < 0.7:
            return True
        # Check for ambiguous detection (multiple high-confidence formats)
        high_confidence = [f for f in self.detected_formats if f.confidence > 0.75]
        return len(high_confidence) > 1

    class Config:
        json_schema_extra = {
            "example": {
                "detection_id": "det_123e4567",
                "dataset_path": "/data/experiment_001",
                "primary_format": {
                    "format_name": "SpikeGLX",
                    "confidence": 0.95,
                    "detection_method": "metadata_file",
                    "evidence": ["Found .meta file", "Binary .bin file present", "Meta header valid"],
                    "neuroconv_interface": "SpikeGLXRecordingInterface"
                },
                "confidence_explanation": "High confidence based on SpikeGLX .meta file with valid header structure",
                "total_files_analyzed": 15,
                "total_dataset_size_bytes": 524288000
            }
        }
```

---

## 5. ValidationResult

Aggregates validation outcomes from multiple validators.

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from enum import Enum

class IssueSeverity(str, Enum):
    """Validation issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ValidationIssue(BaseModel):
    """Single validation issue"""
    issue_id: str
    severity: IssueSeverity
    validator: str = Field(description="Which validator reported this (nwb_inspector, pynwb, dandi, custom)")
    message: str
    file_location: Optional[str] = Field(default=None, description="Path or internal NWB location")
    suggested_fix: Optional[str] = None
    check_name: Optional[str] = None

class ValidatorRun(BaseModel):
    """Result from single validator execution"""
    validator_name: str
    version: str
    status: str = Field(description="passed, failed, error, skipped")
    issues_found: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    configuration: Dict[str, Any] = Field(default_factory=dict)

class QualityScore(BaseModel):
    """Quality metric scoring"""
    dimension: str = Field(description="completeness, correctness, performance, usability")
    score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    details: Optional[str] = None

class ValidationResult(BaseModel):
    """Aggregated validation outcome from multiple validators"""
    validation_id: str
    file_path: Path
    validated_at: datetime = Field(default_factory=datetime.utcnow)

    # Validator execution
    validators_run: List[ValidatorRun] = Field(min_length=1)
    total_validation_duration_seconds: float = Field(ge=0)

    # Issues
    issues: List[ValidationIssue] = Field(default_factory=list)
    critical_issues: int = Field(default=0, ge=0)
    high_issues: int = Field(default=0, ge=0)
    medium_issues: int = Field(default=0, ge=0)
    low_issues: int = Field(default=0, ge=0)

    # Overall status
    overall_status: str = Field(description="PASS, FAIL, WARNING")
    quality_gate_passed: bool

    # Quality scores
    quality_scores: List[QualityScore] = Field(default_factory=list)
    overall_quality_score: float = Field(ge=0.0, le=100.0)

    # Tool-specific results
    nwb_inspector_results: Optional[Dict[str, Any]] = None
    pynwb_validation_results: Optional[Dict[str, Any]] = None
    dandi_validation_results: Optional[Dict[str, Any]] = None
    dandi_readiness_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    # Comparison
    comparison_to_baseline: Optional[Dict[str, Any]] = None

    def aggregate_issues_by_severity(self) -> Dict[IssueSeverity, int]:
        """Count issues by severity"""
        from collections import Counter
        return dict(Counter(issue.severity for issue in self.issues))

    def get_critical_blockers(self) -> List[ValidationIssue]:
        """Return only critical issues that block acceptance"""
        return [issue for issue in self.issues if issue.severity == IssueSeverity.CRITICAL]

    def calculate_weighted_quality_score(self) -> float:
        """Calculate overall quality from weighted component scores"""
        if not self.quality_scores:
            return 0.0
        total_weight = sum(qs.weight for qs in self.quality_scores)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(qs.score * qs.weight for qs in self.quality_scores)
        return weighted_sum / total_weight

    class Config:
        json_schema_extra = {
            "example": {
                "validation_id": "val_456e7890",
                "file_path": "/output/experiment_001.nwb",
                "validators_run": [
                    {"validator_name": "nwb_inspector", "version": "0.4.30", "status": "passed", "issues_found": 2, "duration_seconds": 15.3},
                    {"validator_name": "pynwb", "version": "2.6.0", "status": "passed", "issues_found": 0, "duration_seconds": 5.1},
                    {"validator_name": "dandi", "version": "0.55.0", "status": "passed", "issues_found": 1, "duration_seconds": 8.2}
                ],
                "critical_issues": 0,
                "overall_status": "PASS",
                "quality_gate_passed": True,
                "overall_quality_score": 87.5,
                "dandi_readiness_score": 92.0
            }
        }
```

---

## 6. ProvenanceRecord

Documents data lineage and transformation history using PROV-O ontology.

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4

class ProvenanceEntity(BaseModel):
    """PROV-O Entity (data artifact)"""
    entity_id: str = Field(description="URI or identifier")
    entity_type: str = Field(description="Dataset, NWBFile, IntermediateResult")
    attributes: Dict[str, Any] = Field(default_factory=dict)
    file_path: Optional[str] = None
    checksum: Optional[str] = Field(default=None, description="SHA-256 hash")

class ProvenanceActivity(BaseModel):
    """PROV-O Activity (transformation process)"""
    activity_id: str
    activity_type: str = Field(description="FormatDetection, MetadataCollection, Conversion, Validation")
    started_at: datetime
    ended_at: Optional[datetime] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

class ProvenanceAgent(BaseModel):
    """PROV-O Agent (actor responsible)"""
    agent_id: str
    agent_type: str = Field(description="ConversationAgent, MetadataQuestionerAgent, ConversionAgent, EvaluationAgent")
    version: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)

class ProvenanceRelationship(BaseModel):
    """PROV-O relationship (used, wasGeneratedBy, etc.)"""
    relationship_type: str = Field(description="used, wasGeneratedBy, wasAssociatedWith, wasAttributedTo, wasDerivedFrom")
    subject: str = Field(description="Entity/Activity/Agent ID")
    object: str = Field(description="Entity/Activity/Agent ID")
    attributes: Dict[str, Any] = Field(default_factory=dict)

class ProvenanceRecord(BaseModel):
    """Complete provenance graph using PROV-O ontology"""
    record_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # PROV-O components
    entities: List[ProvenanceEntity] = Field(default_factory=list)
    activities: List[ProvenanceActivity] = Field(default_factory=list)
    agents: List[ProvenanceAgent] = Field(default_factory=list)
    relationships: List[ProvenanceRelationship] = Field(default_factory=list)

    # Serialization cache
    _rdf_turtle: Optional[str] = None
    _rdf_json_ld: Optional[str] = None

    def add_entity(self, entity_id: str, entity_type: str, **attributes) -> ProvenanceEntity:
        """Add a new entity to the provenance graph"""
        entity = ProvenanceEntity(entity_id=entity_id, entity_type=entity_type, attributes=attributes)
        self.entities.append(entity)
        return entity

    def add_activity(self, activity_id: str, activity_type: str, started_at: datetime, **attributes) -> ProvenanceActivity:
        """Add a new activity to the provenance graph"""
        activity = ProvenanceActivity(
            activity_id=activity_id,
            activity_type=activity_type,
            started_at=started_at,
            attributes=attributes
        )
        self.activities.append(activity)
        return activity

    def add_relationship(self, rel_type: str, subject: str, obj: str, **attributes):
        """Add a new relationship to the provenance graph"""
        rel = ProvenanceRelationship(
            relationship_type=rel_type,
            subject=subject,
            object=obj,
            attributes=attributes
        )
        self.relationships.append(rel)

    def record_agent_invocation(self, agent_type: str, input_entity_id: str, output_entity_id: str):
        """Record a complete agent invocation with PROV-O relationships"""
        activity_id = f"activity_{agent_type}_{datetime.utcnow().isoformat()}"
        agent_id = f"agent_{agent_type}"

        # Add activity
        self.add_activity(activity_id, f"{agent_type}_execution", datetime.utcnow())

        # Add agent if not exists
        if not any(a.agent_id == agent_id for a in self.agents):
            self.agents.append(ProvenanceAgent(agent_id=agent_id, agent_type=agent_type))

        # Add relationships
        self.add_relationship("used", activity_id, input_entity_id)
        self.add_relationship("wasGeneratedBy", output_entity_id, activity_id)
        self.add_relationship("wasAssociatedWith", activity_id, agent_id)

    def to_prov_o_turtle(self) -> str:
        """Serialize to PROV-O RDF Turtle format (implemented in service layer with rdflib)"""
        # Placeholder - actual implementation uses rdflib
        return self._rdf_turtle or "# PROV-O Turtle serialization"

    def to_prov_o_json_ld(self) -> str:
        """Serialize to PROV-O JSON-LD format (implemented in service layer with rdflib)"""
        # Placeholder - actual implementation uses rdflib
        return self._rdf_json_ld or "{}"

    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "567e8901-e89b-12d3-a456-426614174003",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "entities": [
                    {"entity_id": "dataset_001", "entity_type": "Dataset", "attributes": {"path": "/data/exp_001"}},
                    {"entity_id": "nwb_file_001", "entity_type": "NWBFile", "attributes": {"path": "/output/exp_001.nwb"}}
                ],
                "activities": [
                    {"activity_id": "conversion_001", "activity_type": "Conversion", "started_at": "2025-10-10T10:00:00Z"}
                ],
                "agents": [
                    {"agent_id": "conversion_agent", "agent_type": "ConversionAgent", "version": "1.0"}
                ],
                "relationships": [
                    {"relationship_type": "used", "subject": "conversion_001", "object": "dataset_001"},
                    {"relationship_type": "wasGeneratedBy", "subject": "nwb_file_001", "object": "conversion_001"}
                ]
            }
        }
```

---

## 7. QualityMetrics

Quantitative assessment of conversion quality with weighted scoring.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID

class MetricDimension(BaseModel):
    """Single quality dimension metric"""
    name: str = Field(description="completeness, correctness, performance, usability")
    score: float = Field(ge=0.0, le=100.0)
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Importance weight for overall score")
    max_score: float = Field(default=100.0, ge=0.0)
    details: Dict[str, Any] = Field(default_factory=dict)
    contributing_factors: List[str] = Field(default_factory=list)

class BaselineComparison(BaseModel):
    """Comparison to historical baseline"""
    baseline_id: Optional[str] = None
    baseline_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    current_score: float = Field(ge=0.0, le=100.0)
    delta: float = Field(description="current - baseline")
    improvement_percentage: Optional[float] = None
    trend: str = Field(description="improving, degrading, stable")

class QualityMetrics(BaseModel):
    """Comprehensive quality metrics for conversion"""
    metrics_id: str
    session_id: UUID
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

    # Core quality dimensions
    completeness_score: float = Field(ge=0.0, le=100.0, description="Metadata completeness")
    correctness_score: float = Field(ge=0.0, le=100.0, description="Validation pass rate")
    performance_score: float = Field(ge=0.0, le=100.0, description="Efficiency metrics")
    usability_score: float = Field(ge=0.0, le=100.0, description="Documentation quality")

    # Weighted overall score
    overall_quality: float = Field(ge=0.0, le=100.0)

    # Detailed breakdowns
    metric_details: List[MetricDimension] = Field(default_factory=list)

    # Comparison
    comparison_to_baseline: Optional[BaselineComparison] = None

    # Thresholds
    target_quality_threshold: float = Field(default=80.0, ge=0.0, le=100.0)
    quality_gate_passed: bool = Field(description="overall_quality >= threshold")

    # Recommendations
    improvement_recommendations: List[str] = Field(default_factory=list)

    @field_validator('overall_quality', mode='after')
    @classmethod
    def validate_overall_quality(cls, v: float, info) -> float:
        """Ensure overall quality is consistent with dimension scores"""
        # In actual implementation, calculate weighted average
        return v

    def calculate_weighted_score(self) -> float:
        """Calculate overall quality from weighted dimensions"""
        if not self.metric_details:
            # Fallback to simple average
            return (self.completeness_score + self.correctness_score +
                    self.performance_score + self.usability_score) / 4.0

        total_weight = sum(m.weight for m in self.metric_details)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(m.score * m.weight for m in self.metric_details)
        return weighted_sum / total_weight

    def generate_improvement_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on low scores"""
        recommendations = []

        if self.completeness_score < 70:
            recommendations.append("Improve metadata completeness by answering additional questioner agent prompts")
        if self.correctness_score < 80:
            recommendations.append("Address validation errors reported by NWB Inspector and PyNWB")
        if self.performance_score < 60:
            recommendations.append("Optimize data organization and chunking for better performance")
        if self.usability_score < 70:
            recommendations.append("Enhance documentation and descriptive metadata for better usability")

        return recommendations

    class Config:
        json_schema_extra = {
            "example": {
                "metrics_id": "qm_789e0123",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "completeness_score": 92.5,
                "correctness_score": 88.0,
                "performance_score": 75.5,
                "usability_score": 85.0,
                "overall_quality": 87.3,
                "target_quality_threshold": 80.0,
                "quality_gate_passed": True
            }
        }
```

---

## 8. ResourceAllocation

Manages compute resources for workflow execution with utilization tracking.

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4

class ResourceUtilization(BaseModel):
    """Current resource utilization metrics"""
    cpu_utilization_percent: float = Field(ge=0.0, le=100.0)
    memory_used_mb: float = Field(ge=0.0)
    memory_utilization_percent: float = Field(ge=0.0, le=100.0)
    disk_io_read_mbps: float = Field(ge=0.0)
    disk_io_write_mbps: float = Field(ge=0.0)
    network_rx_mbps: float = Field(ge=0.0)
    network_tx_mbps: float = Field(ge=0.0)
    gpu_utilization_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)

class ResourceAllocation(BaseModel):
    """Compute resource allocation for workflow"""
    allocation_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    session_id: UUID

    # Allocated resources
    cpu_cores: int = Field(gt=0, description="Number of CPU cores")
    memory_mb: int = Field(gt=0, description="Memory in megabytes")
    disk_gb: int = Field(gt=0, description="Disk space in gigabytes")
    gpu_count: int = Field(default=0, ge=0, description="Number of GPUs")
    network_bandwidth_mbps: int = Field(default=1000, gt=0, description="Network bandwidth in Mbps")

    # Lifecycle
    allocated_at: datetime = Field(default_factory=datetime.utcnow)
    released_at: Optional[datetime] = None
    allocation_duration_seconds: Optional[float] = None

    # Utilization tracking
    peak_utilization: Optional[ResourceUtilization] = None
    average_utilization: Optional[ResourceUtilization] = None
    current_utilization: Optional[ResourceUtilization] = None

    # Limits and quotas
    max_memory_mb: Optional[int] = Field(default=None, description="Hard limit")
    max_disk_gb: Optional[int] = Field(default=None, description="Hard limit")

    # Overallocation detection
    is_overallocated: bool = Field(default=False)
    overallocation_reason: Optional[str] = None

    @field_validator('cpu_cores')
    @classmethod
    def validate_cpu_cores(cls, v: int) -> int:
        """Ensure CPU cores is reasonable"""
        import os
        max_cores = os.cpu_count() or 1
        if v > max_cores * 2:  # Allow some oversubscription
            raise ValueError(f"Requested {v} CPU cores exceeds system capacity ({max_cores})")
        return v

    def release(self):
        """Release allocated resources"""
        self.released_at = datetime.utcnow()
        if self.allocated_at:
            self.allocation_duration_seconds = (self.released_at - self.allocated_at).total_seconds()

    def update_utilization(self, utilization: ResourceUtilization):
        """Update current utilization metrics"""
        self.current_utilization = utilization

        # Update peak utilization
        if self.peak_utilization is None:
            self.peak_utilization = utilization
        else:
            if utilization.cpu_utilization_percent > self.peak_utilization.cpu_utilization_percent:
                self.peak_utilization.cpu_utilization_percent = utilization.cpu_utilization_percent
            if utilization.memory_used_mb > self.peak_utilization.memory_used_mb:
                self.peak_utilization.memory_used_mb = utilization.memory_used_mb

        # Check for overallocation
        if utilization.memory_used_mb > self.memory_mb:
            self.is_overallocated = True
            self.overallocation_reason = f"Memory usage ({utilization.memory_used_mb}MB) exceeds allocation ({self.memory_mb}MB)"

    def estimate_remaining_capacity(self) -> Dict[str, float]:
        """Estimate remaining resource capacity"""
        if not self.current_utilization:
            return {"cpu": 100.0, "memory": 100.0, "disk": 100.0}

        return {
            "cpu": 100.0 - self.current_utilization.cpu_utilization_percent,
            "memory": 100.0 - self.current_utilization.memory_utilization_percent,
            "disk": 100.0 - (self.current_utilization.disk_io_read_mbps + self.current_utilization.disk_io_write_mbps) / 10.0  # Simplified
        }

    class Config:
        json_schema_extra = {
            "example": {
                "allocation_id": "890e1234-e89b-12d3-a456-426614174004",
                "workflow_id": "223e4567-e89b-12d3-a456-426614174001",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "cpu_cores": 4,
                "memory_mb": 8192,
                "disk_gb": 100,
                "gpu_count": 0,
                "network_bandwidth_mbps": 1000
            }
        }
```

---

## 9. ConfigurationSnapshot

Captures configuration state at workflow execution time with versioning.

```python
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any, List
from datetime import datetime
from uuid import UUID, uuid4

class ConfigurationSource(str, Enum):
    """Configuration origin"""
    DEFAULT = "default"
    GLOBAL = "global"
    USER = "user"
    WORKFLOW = "workflow"
    ENVIRONMENT = "environment"
    RUNTIME = "runtime"

class ConfigurationChange(BaseModel):
    """Single configuration change record"""
    key: str
    old_value: Optional[Any] = None
    new_value: Any
    changed_at: datetime
    changed_by: str

class ConfigurationSnapshot(BaseModel):
    """Complete configuration state at a point in time"""
    snapshot_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Configuration hierarchy
    configuration: Dict[str, Any] = Field(description="Complete flattened configuration")
    source: ConfigurationSource = Field(description="Primary configuration source")
    version: str = Field(description="Configuration schema version")

    # Inheritance tracking
    default_config: Dict[str, Any] = Field(default_factory=dict)
    global_overrides: Dict[str, Any] = Field(default_factory=dict)
    user_overrides: Dict[str, Any] = Field(default_factory=dict)
    workflow_overrides: Dict[str, Any] = Field(default_factory=dict)

    # Effective settings (after inheritance resolution)
    effective_settings: Dict[str, Any] = Field(description="Final computed configuration")

    # Change tracking
    changes_from_default: List[ConfigurationChange] = Field(default_factory=list)

    # Validation
    is_valid: bool = Field(default=True)
    validation_errors: List[str] = Field(default_factory=list)

    def get_effective_value(self, key: str, default: Any = None) -> Any:
        """Retrieve effective configuration value with precedence"""
        return self.effective_settings.get(key, default)

    def apply_override(self, key: str, value: Any, source: ConfigurationSource, changed_by: str):
        """Apply configuration override with tracking"""
        old_value = self.effective_settings.get(key)
        self.effective_settings[key] = value

        # Track change
        change = ConfigurationChange(
            key=key,
            old_value=old_value,
            new_value=value,
            changed_at=datetime.utcnow(),
            changed_by=changed_by
        )
        self.changes_from_default.append(change)

        # Update source-specific overrides
        if source == ConfigurationSource.GLOBAL:
            self.global_overrides[key] = value
        elif source == ConfigurationSource.USER:
            self.user_overrides[key] = value
        elif source == ConfigurationSource.WORKFLOW:
            self.workflow_overrides[key] = value

    def diff_with_snapshot(self, other: 'ConfigurationSnapshot') -> Dict[str, Any]:
        """Compare with another snapshot to find differences"""
        differences = {}

        all_keys = set(self.effective_settings.keys()) | set(other.effective_settings.keys())
        for key in all_keys:
            self_val = self.effective_settings.get(key)
            other_val = other.effective_settings.get(key)

            if self_val != other_val:
                differences[key] = {
                    "current": self_val,
                    "other": other_val
                }

        return differences

    def export_for_reproducibility(self) -> Dict[str, Any]:
        """Export configuration for workflow reproducibility"""
        return {
            "snapshot_id": str(self.snapshot_id),
            "session_id": str(self.session_id),
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "effective_settings": self.effective_settings,
            "changes_from_default": [
                {
                    "key": change.key,
                    "value": change.new_value,
                    "changed_at": change.changed_at.isoformat()
                }
                for change in self.changes_from_default
            ]
        }

    class Config:
        json_schema_extra = {
            "example": {
                "snapshot_id": "901e2345-e89b-12d3-a456-426614174005",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "source": "workflow",
                "version": "1.0",
                "effective_settings": {
                    "workflow.timeout_seconds": 1800,
                    "agents.conversation.timeout_seconds": 120,
                    "agents.conversion.retry_attempts": 3,
                    "validation.run_dandi": True,
                    "validation.quality_threshold": 80.0
                },
                "is_valid": True
            }
        }
```

---

## Model Relationships

```
ConversionSession
├── workflow_definition_id → WorkflowDefinition
├── checkpoints → List[Checkpoint]
├── format_detection_result → FormatDetectionResult (embedded)
├── validation_result → ValidationResult (embedded)
└── quality_metrics → QualityMetrics (embedded)

WorkflowDefinition
├── steps → List[WorkflowStep]
└── dependencies → List[WorkflowDependency] (DAG edges)

AgentInvocation
└── session_id → ConversionSession

ProvenanceRecord
├── session_id → ConversionSession
├── entities → List[ProvenanceEntity]
├── activities → List[ProvenanceActivity]
├── agents → List[ProvenanceAgent]
└── relationships → List[ProvenanceRelationship]

ResourceAllocation
├── workflow_id → WorkflowDefinition
└── session_id → ConversionSession

ConfigurationSnapshot
└── session_id → ConversionSession

QualityMetrics
└── session_id → ConversionSession

ValidationResult
└── (standalone, referenced by session_id)

FormatDetectionResult
└── (standalone, referenced by session_id)
```

---

## Implementation Notes

1. **Serialization**: All models support `.json()` for API responses and `.dict()` for internal use
2. **Validation**: Pydantic validators enforce business rules at model boundary
3. **Immutability**: Consider using `frozen=True` in Config for immutable snapshots (Checkpoint, ConfigurationSnapshot)
4. **Persistence**: Models serialize to JSON for filesystem checkpoints, PostgreSQL JSONB for production
5. **Testing**: Generate model instances using `.Config.json_schema_extra` examples for contract tests
6. **Extensibility**: Use `metadata: Dict[str, Any]` fields for custom extensions without schema changes

---

**Status**: Phase 1 Design - Data Model Complete
**Next**: Generate API contracts (contracts/ directory)
