# Phase 1: Data Model Specification

**Feature**: MCP Server Architecture **Date**: 2025-10-06 **Status**: Design
Complete

## Overview

This document defines the core data entities, their relationships, state
transitions, and validation rules for the MCP Server Architecture. All models
support the transport-agnostic service layer and are persisted using SQLAlchemy
async ORM.

---

## Entity Definitions

### 1. Workflow

**Purpose**: Represents a complete conversion workflow from dataset input to NWB
output

**Fields**:

| Field              | Type               | Required | Description                                       |
| ------------------ | ------------------ | -------- | ------------------------------------------------- |
| id                 | UUID               | Yes      | Primary key, generated on creation                |
| state              | WorkflowState enum | Yes      | Current workflow state                            |
| steps              | List[WorkflowStep] | Yes      | Ordered list of workflow steps (relationship)     |
| checkpoints        | JSON               | Yes      | Checkpoint data for resume capability             |
| metadata           | JSON               | Yes      | User-provided and system-generated metadata       |
| input_path         | str                | Yes      | Path to input dataset                             |
| output_path        | str                | No       | Path to generated NWB file (set on completion)    |
| format_info        | JSON               | No       | Detected format information from format detection |
| validation_summary | JSON               | No       | Summary of validation results                     |
| error_details      | JSON               | No       | Error information if state is FAILED              |
| created_at         | datetime           | Yes      | Workflow creation timestamp (UTC)                 |
| updated_at         | datetime           | Yes      | Last update timestamp (UTC)                       |
| completed_at       | datetime           | No       | Completion timestamp (success or failure)         |
| version            | int                | Yes      | Optimistic locking version for concurrent updates |

**Database Schema**:

```python
class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(Enum(WorkflowState), nullable=False, index=True)
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    checkpoints = Column(JSON, nullable=False, default=dict)
    metadata = Column(JSON, nullable=False, default=dict)
    input_path = Column(String, nullable=False)
    output_path = Column(String, nullable=True)
    format_info = Column(JSON, nullable=True)
    validation_summary = Column(JSON, nullable=True)
    error_details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index('ix_workflows_state_created', 'state', 'created_at'),
    )
```

**Validation Rules**:

- `input_path` must be a valid filesystem path
- `state` transitions must follow state machine rules (see State Transitions)
- `version` must increment on each update (optimistic locking)
- `completed_at` can only be set when state is COMPLETED, FAILED, or CANCELLED
- `output_path` must be set when state is COMPLETED
- `error_details` must be set when state is FAILED

**Indexes**:

- Primary: id
- Secondary: (state, created_at) for querying active workflows
- Secondary: state for filtering by status

---

### 2. WorkflowStep

**Purpose**: Represents a single step in the workflow executed by a specific
agent

**Fields**:

| Field           | Type            | Required | Description                           |
| --------------- | --------------- | -------- | ------------------------------------- |
| id              | UUID            | Yes      | Primary key, generated on creation    |
| workflow_id     | UUID            | Yes      | Foreign key to Workflow               |
| agent_type      | AgentType enum  | Yes      | Type of agent that executed this step |
| status          | StepStatus enum | Yes      | Step execution status                 |
| input_data      | JSON            | Yes      | Input provided to the agent           |
| output_data     | JSON            | No       | Output returned by the agent          |
| context         | JSON            | Yes      | Execution context and metadata        |
| started_at      | datetime        | Yes      | Step start timestamp (UTC)            |
| completed_at    | datetime        | No       | Step completion timestamp (UTC)       |
| duration_ms     | int             | No       | Execution duration in milliseconds    |
| error           | JSON            | No       | Error details if status is FAILED     |
| retry_count     | int             | Yes      | Number of retry attempts              |
| sequence_number | int             | Yes      | Order of step in workflow             |

**Database Schema**:

```python
class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    workflow = relationship("Workflow", back_populates="steps")
    agent_type = Column(Enum(AgentType), nullable=False)
    status = Column(Enum(StepStatus), nullable=False, index=True)
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)
    context = Column(JSON, nullable=False, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error = Column(JSON, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    sequence_number = Column(Integer, nullable=False)

    __table_args__ = (
        Index('ix_workflow_steps_workflow_seq', 'workflow_id', 'sequence_number'),
        UniqueConstraint('workflow_id', 'sequence_number', name='uq_workflow_step_sequence'),
    )
```

**Validation Rules**:

- `workflow_id` must reference an existing Workflow
- `sequence_number` must be unique within a workflow
- `completed_at` can only be set when status is COMPLETED, FAILED, or SKIPPED
- `duration_ms` must be calculated from started_at and completed_at when set
- `error` must be present when status is FAILED
- `output_data` should be present when status is COMPLETED
- `retry_count` must be >= 0

**Indexes**:

- Primary: id
- Secondary: workflow_id for querying steps by workflow
- Secondary: (workflow_id, sequence_number) for ordering steps
- Unique: (workflow_id, sequence_number)

---

### 3. AgentRequest

**Purpose**: Request message sent to an agent for execution

**Fields**:

| Field           | Type           | Required | Description                                      |
| --------------- | -------------- | -------- | ------------------------------------------------ |
| agent_type      | AgentType enum | Yes      | Target agent type                                |
| operation       | str            | Yes      | Operation to perform                             |
| input           | dict           | Yes      | Operation-specific input data                    |
| context         | dict           | Yes      | Execution context (workflow_id, step_id, etc.)   |
| timeout_seconds | int            | Yes      | Maximum execution time                           |
| correlation_id  | str            | Yes      | Unique request identifier for tracing            |
| priority        | int            | No       | Request priority (0-10, higher = more important) |
| retry_policy    | RetryPolicy    | No       | Custom retry configuration                       |

**Pydantic Model**:

```python
class AgentRequest(BaseModel):
    agent_type: AgentType
    operation: str
    input: dict
    context: dict
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = Field(default=5, ge=0, le=10)
    retry_policy: Optional[RetryPolicy] = None

    class Config:
        use_enum_values = True
```

**Validation Rules**:

- `agent_type` must be a valid AgentType enum value
- `operation` must be non-empty string
- `timeout_seconds` must be between 1 and 3600 seconds
- `correlation_id` must be unique for tracing
- `priority` must be between 0 and 10
- `context` must contain at minimum: workflow_id

---

### 4. AgentResponse

**Purpose**: Response returned by an agent after execution

**Fields**:

| Field             | Type           | Required | Description                                |
| ----------------- | -------------- | -------- | ------------------------------------------ |
| agent_type        | AgentType enum | Yes      | Agent that executed the request            |
| success           | bool           | Yes      | Whether execution was successful           |
| output_data       | dict           | No       | Operation output (present if success=True) |
| error             | AgentError     | No       | Error details (present if success=False)   |
| execution_time_ms | int            | Yes      | Actual execution duration                  |
| correlation_id    | str            | Yes      | Matching request correlation_id            |
| metadata          | dict           | Yes      | Additional execution metadata              |

**Pydantic Model**:

```python
class AgentResponse(BaseModel):
    agent_type: AgentType
    success: bool
    output_data: Optional[dict] = None
    error: Optional[AgentError] = None
    execution_time_ms: int = Field(ge=0)
    correlation_id: str
    metadata: dict = Field(default_factory=dict)

    @validator('output_data')
    def check_output_on_success(cls, v, values):
        if values.get('success') and v is None:
            raise ValueError('output_data required when success=True')
        return v

    @validator('error')
    def check_error_on_failure(cls, v, values):
        if not values.get('success') and v is None:
            raise ValueError('error required when success=False')
        return v

    class Config:
        use_enum_values = True
```

**Validation Rules**:

- `success=True` requires `output_data` to be present
- `success=False` requires `error` to be present
- `execution_time_ms` must be >= 0
- `correlation_id` must match the corresponding AgentRequest

---

### 5. FormatDetection

**Purpose**: Results of format detection analysis

**Fields**:

| Field                 | Type             | Required | Description                              |
| --------------------- | ---------------- | -------- | ---------------------------------------- |
| formats_detected      | List[FormatInfo] | Yes      | List of detected formats with confidence |
| primary_format        | FormatInfo       | No       | Highest confidence format                |
| confidence_scores     | dict             | Yes      | Confidence scores by detection layer     |
| recommended_interface | str              | No       | Recommended NeuroConv interface          |
| detection_layers_used | List[str]        | Yes      | Which detection layers were applied      |
| ambiguous_formats     | List[FormatInfo] | No       | Formats with similar confidence          |
| warnings              | List[str]        | No       | Detection warnings or issues             |

**Pydantic Model**:

```python
class FormatInfo(BaseModel):
    name: str
    version: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    neuroconv_interface: Optional[str] = None
    detection_method: str

class FormatDetection(BaseModel):
    formats_detected: List[FormatInfo] = Field(min_items=1)
    primary_format: Optional[FormatInfo] = None
    confidence_scores: dict
    recommended_interface: Optional[str] = None
    detection_layers_used: List[str]
    ambiguous_formats: List[FormatInfo] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @validator('primary_format', always=True)
    def set_primary_format(cls, v, values):
        if v is None and 'formats_detected' in values:
            # Set highest confidence format as primary
            return max(values['formats_detected'], key=lambda f: f.confidence)
        return v

    @validator('confidence_scores')
    def validate_scores(cls, v):
        for score in v.values():
            if not 0.0 <= score <= 1.0:
                raise ValueError(f'Confidence score {score} out of range [0.0, 1.0]')
        return v
```

**Validation Rules**:

- `formats_detected` must contain at least one format
- All confidence scores must be between 0.0 and 1.0
- `primary_format` should be the highest confidence format if not explicitly set
- `detection_layers_used` must contain at least one layer name
- If `ambiguous_formats` is present, must contain formats with confidence within
  0.1 of primary

---

### 6. ValidationResult

**Purpose**: Results from validation tools (NWB Inspector, PyNWB, DANDI)

**Fields**:

| Field             | Type                    | Required | Description                        |
| ----------------- | ----------------------- | -------- | ---------------------------------- |
| validator_name    | str                     | Yes      | Name of validation tool            |
| severity          | ValidationSeverity enum | Yes      | Overall severity level             |
| issues            | List[ValidationIssue]   | Yes      | Individual validation issues found |
| quality_score     | float                   | Yes      | Overall quality score (0.0-1.0)    |
| passed            | bool                    | Yes      | Whether validation passed          |
| execution_time_ms | int                     | Yes      | Validation execution time          |
| metadata          | dict                    | Yes      | Validator-specific metadata        |

**Pydantic Models**:

```python
class ValidationIssue(BaseModel):
    severity: ValidationSeverity
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None

class ValidationResult(BaseModel):
    validator_name: str
    severity: ValidationSeverity
    issues: List[ValidationIssue]
    quality_score: float = Field(ge=0.0, le=1.0)
    passed: bool
    execution_time_ms: int = Field(ge=0)
    metadata: dict = Field(default_factory=dict)

    @validator('passed')
    def check_passed_vs_issues(cls, v, values):
        if v and 'issues' in values:
            critical_issues = [i for i in values['issues']
                             if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
            if critical_issues:
                raise ValueError('passed=True but critical issues present')
        return v
```

**Validation Rules**:

- `quality_score` must be between 0.0 and 1.0
- `passed=True` requires no CRITICAL or ERROR severity issues
- `issues` list can be empty if no issues found
- `execution_time_ms` must be >= 0
- `severity` should be the highest severity among all issues

---

## Enumerations

### WorkflowState

**Purpose**: Define valid workflow states

```python
class WorkflowState(str, Enum):
    PENDING = "pending"           # Created, not started
    ANALYZING = "analyzing"       # Format detection in progress
    COLLECTING = "collecting"     # Metadata collection from user
    CONVERTING = "converting"     # NWB conversion in progress
    VALIDATING = "validating"     # Validation checks running
    COMPLETED = "completed"       # Successfully completed
    FAILED = "failed"            # Failed with unrecoverable error
    CANCELLED = "cancelled"       # Cancelled by user
```

### AgentType

**Purpose**: Define supported agent types

```python
class AgentType(str, Enum):
    CONVERSATION = "conversation"               # Dataset analysis and format detection
    CONVERSION = "conversion"                   # Script generation and NWB conversion
    EVALUATION = "evaluation"                   # Validation and quality assessment
    METADATA_QUESTIONER = "metadata_questioner" # Interactive metadata collection
```

### StepStatus

**Purpose**: Define workflow step execution states

```python
class StepStatus(str, Enum):
    PENDING = "pending"       # Queued, not started
    RUNNING = "running"       # Currently executing
    COMPLETED = "completed"   # Successfully completed
    FAILED = "failed"        # Failed execution
    SKIPPED = "skipped"      # Skipped due to conditions
    RETRYING = "retrying"    # Retrying after failure
```

### ValidationSeverity

**Purpose**: Define validation issue severity levels

```python
class ValidationSeverity(str, Enum):
    INFO = "info"           # Informational message
    WARNING = "warning"     # Warning, but not critical
    ERROR = "error"        # Error that should be fixed
    CRITICAL = "critical"   # Critical issue, must be fixed
```

---

## State Transitions

### Workflow State Machine

**Valid Transitions**:

```
PENDING → ANALYZING
  Initial workflow start

ANALYZING → COLLECTING
  Format detected successfully, need metadata

ANALYZING → CONVERTING
  Format detected, metadata already available

ANALYZING → FAILED
  Format detection failed

COLLECTING → CONVERTING
  Metadata collection complete

COLLECTING → FAILED
  Metadata collection failed or timeout

CONVERTING → VALIDATING
  Conversion complete, starting validation

CONVERTING → FAILED
  Conversion failed

VALIDATING → COMPLETED
  Validation passed

VALIDATING → FAILED
  Validation failed critically

ANY_STATE → CANCELLED
  User cancellation (except COMPLETED, FAILED)
```

**Transition Guards**:

```python
ALLOWED_TRANSITIONS = {
    WorkflowState.PENDING: [WorkflowState.ANALYZING, WorkflowState.CANCELLED],
    WorkflowState.ANALYZING: [WorkflowState.COLLECTING, WorkflowState.CONVERTING,
                              WorkflowState.FAILED, WorkflowState.CANCELLED],
    WorkflowState.COLLECTING: [WorkflowState.CONVERTING, WorkflowState.FAILED,
                               WorkflowState.CANCELLED],
    WorkflowState.CONVERTING: [WorkflowState.VALIDATING, WorkflowState.FAILED,
                               WorkflowState.CANCELLED],
    WorkflowState.VALIDATING: [WorkflowState.COMPLETED, WorkflowState.FAILED,
                               WorkflowState.CANCELLED],
    WorkflowState.COMPLETED: [],  # Terminal state
    WorkflowState.FAILED: [],     # Terminal state
    WorkflowState.CANCELLED: [],  # Terminal state
}

def can_transition(from_state: WorkflowState, to_state: WorkflowState) -> bool:
    return to_state in ALLOWED_TRANSITIONS.get(from_state, [])
```

### Step Status Transitions

**Valid Transitions**:

```
PENDING → RUNNING
  Step execution started

RUNNING → COMPLETED
  Successful completion

RUNNING → FAILED
  Execution failed

RUNNING → RETRYING
  Transient failure, retrying

RETRYING → RUNNING
  Retry attempt started

RETRYING → FAILED
  Max retries exhausted

RUNNING → SKIPPED
  Conditional skip

PENDING → SKIPPED
  Skip without execution
```

---

## Relationships

### Entity Relationship Diagram

```
Workflow (1) ──< (N) WorkflowStep
    │
    │ (contains)
    │
    ├── FormatDetection (embedded JSON)
    ├── ValidationResult[] (embedded JSON)
    └── AgentRequest/Response (transient, not persisted)
```

**Relationship Details**:

1. **Workflow → WorkflowStep**: One-to-Many
   - One workflow has multiple steps
   - Cascade delete: deleting workflow deletes all steps
   - Back-reference: step.workflow
   - Ordered by: sequence_number

2. **Workflow → FormatDetection**: Embedded
   - Stored as JSON in workflow.format_info
   - Not a separate table
   - Lifecycle tied to workflow

3. **Workflow → ValidationResult**: Embedded Collection
   - Stored as JSON array in workflow.validation_summary
   - Multiple validators can run per workflow
   - Aggregated into single quality score

4. **WorkflowStep → AgentRequest/Response**: Transient
   - Not persisted in database
   - Created on-the-fly during step execution
   - Input/output captured in step.input_data and step.output_data

---

## Validation Rules Summary

### Cross-Entity Validation

1. **Workflow Consistency**:
   - If workflow.state = COMPLETED, then workflow.output_path must be set
   - If workflow.state = FAILED, then workflow.error_details must be set
   - workflow.steps must contain at least one step when state != PENDING
   - workflow.completed_at must be >= workflow.created_at

2. **Step Consistency**:
   - All steps in a workflow must have unique sequence_numbers
   - step.completed_at must be >= step.started_at
   - If step.status = COMPLETED, then step.output_data should be present
   - If step.status = FAILED, then step.error must be present

3. **State Alignment**:
   - If workflow.state = ANALYZING, latest step.agent_type should be
     CONVERSATION
   - If workflow.state = CONVERTING, latest step.agent_type should be CONVERSION
   - If workflow.state = VALIDATING, latest step.agent_type should be EVALUATION

4. **Temporal Consistency**:
   - Workflow timestamps: created_at <= updated_at <= completed_at
   - Step timestamps: started_at <= completed_at
   - Step durations: duration_ms should match (completed_at - started_at)

---

## Data Model Usage Examples

### Creating a New Workflow

```python
# Service layer
async def create_workflow(
    input_path: str,
    metadata: dict,
    session: AsyncSession
) -> Workflow:
    workflow = Workflow(
        id=uuid.uuid4(),
        state=WorkflowState.PENDING,
        input_path=input_path,
        metadata=metadata,
        checkpoints={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    return workflow
```

### Updating Workflow State

```python
async def transition_workflow(
    workflow: Workflow,
    new_state: WorkflowState,
    session: AsyncSession
) -> Workflow:
    # Validate transition
    if not can_transition(workflow.state, new_state):
        raise ValueError(f"Invalid transition: {workflow.state} → {new_state}")

    # Optimistic locking
    stmt = (
        update(Workflow)
        .where(Workflow.id == workflow.id, Workflow.version == workflow.version)
        .values(
            state=new_state,
            updated_at=datetime.utcnow(),
            version=workflow.version + 1
        )
    )
    result = await session.execute(stmt)

    if result.rowcount == 0:
        raise ConcurrentModificationError("Workflow was modified by another process")

    await session.commit()
    await session.refresh(workflow)
    return workflow
```

### Adding a Workflow Step

```python
async def add_workflow_step(
    workflow_id: UUID,
    agent_type: AgentType,
    input_data: dict,
    session: AsyncSession
) -> WorkflowStep:
    # Get next sequence number
    max_seq = await session.execute(
        select(func.max(WorkflowStep.sequence_number))
        .where(WorkflowStep.workflow_id == workflow_id)
    )
    next_seq = (max_seq.scalar() or 0) + 1

    step = WorkflowStep(
        id=uuid.uuid4(),
        workflow_id=workflow_id,
        agent_type=agent_type,
        status=StepStatus.PENDING,
        input_data=input_data,
        context={},
        started_at=datetime.utcnow(),
        retry_count=0,
        sequence_number=next_seq
    )
    session.add(step)
    await session.commit()
    await session.refresh(step)
    return step
```

---

## Performance Considerations

### Indexing Strategy

1. **Hot Path Queries**:
   - Query active workflows: Index on (state, created_at)
   - Query workflow steps: Index on (workflow_id, sequence_number)
   - Query by correlation_id: Would require separate request log table

2. **Composite Indexes**:
   - (state, created_at): Filter and sort active workflows
   - (workflow_id, sequence_number): Order steps efficiently

### JSON Column Usage

**Advantages**:

- Flexible schema for agent-specific data
- No schema migrations for new agent types
- Easy to store complex nested structures

**Considerations**:

- Cannot efficiently query JSON column contents (use PostgreSQL jsonb for this)
- Must validate JSON structure in application layer
- Consider extraction to columns if frequently queried

### Optimistic Locking

**Version Column Strategy**:

- Prevents lost updates in concurrent modifications
- Increment version on each update
- Check version in WHERE clause of UPDATE
- Raise error if rowcount = 0 (concurrent modification)

---

## Migration Strategy

### Schema Versioning

- Use Alembic for database migrations
- Version: `{timestamp}_{description}.py`
- Include both upgrade() and downgrade()
- Test migrations on copy of production data

### Example Migration

```python
# alembic/versions/001_create_workflows.py
def upgrade():
    op.create_table(
        'workflows',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('state', sa.Enum(WorkflowState), nullable=False),
        # ... other columns
    )
    op.create_index('ix_workflows_state_created', 'workflows', ['state', 'created_at'])

def downgrade():
    op.drop_index('ix_workflows_state_created')
    op.drop_table('workflows')
```

---

## Data Model Complete

All entities defined with:

- Complete field specifications
- Validation rules
- State transitions
- Relationships
- Performance considerations

**Next Phase**: Create API contracts (OpenAPI, MCP tools) and quickstart guide
