# Data Model

**Feature**: Agent-Based Neurodata Conversion System **Date**: 2025-10-03

## Core Entities

### 1. Conversion Task

Represents a single conversion job from source data to NWB format.

**Fields**:

- `id`: UUID - Unique task identifier
- `source_path`: Path - Location of source neurodata files
- `source_format`: String - Detected or specified source format (e.g.,
  "Blackrock", "Intan", "SpikeGLX")
- `target_path`: Path - Output location for converted NWB file
- `status`: Enum - Current task state (see State Transitions below)
- `progress`: Float - Completion percentage (0.0 to 1.0)
- `workflow_id`: UUID - Reference to workflow being executed
- `error_history`: List[ErrorRecord] - Chronological list of errors encountered
- `submission_time`: DateTime - When task was created
- `start_time`: DateTime | None - When execution began
- `completion_time`: DateTime | None - When task finished (success or failure)
- `result`: ValidationReport | None - Final validation results
- `user_id`: String | None - Identifier for user who submitted task
- `priority`: Integer - Task priority (default: 0, FIFO uses submission_time)
- `metadata`: Dict[String, Any] - Additional task-specific information

**Validation Rules**:

- `source_path` must exist and be readable
- `target_path` must be writable location
- `progress` must be between 0.0 and 1.0
- `completion_time` must be after `start_time` if both are set
- `status` must follow valid state transitions

**State Transitions**:

```
pending → profiling → tool_selection → executing → validating → completed
pending → profiling → tool_selection → executing → failed
pending → clarification_needed
any_state → cancelled
```

### 2. Workflow

Defines the sequence of conversion steps for a specific data type or conversion
scenario.

**Fields**:

- `id`: UUID - Unique workflow identifier
- `name`: String - Human-readable workflow name
- `description`: String - Workflow purpose and applicability
- `data_format`: String - Source data format this workflow handles
- `steps`: List[WorkflowStep] - Ordered sequence of conversion steps
- `validation_checks`: List[ValidationCheck] - Validation rules to apply
- `created_at`: DateTime - When workflow was defined
- `updated_at`: DateTime - Last modification time
- `version`: String - Semantic version (e.g., "1.0.0")
- `is_active`: Boolean - Whether workflow is currently in use

**WorkflowStep Fields**:

- `step_id`: String - Step identifier within workflow
- `tool_name`: String - Conversion tool to use (e.g., "neuroconv", "pynwb")
- `tool_version`: String | None - Specific tool version or "latest"
- `parameters`: Dict[String, Any] - Tool-specific parameters
- `depends_on`: List[String] - Step IDs that must complete first
- `timeout_seconds`: Integer - Maximum execution time
- `retry_policy`: RetryPolicy - How to handle failures

**Validation Rules**:

- `steps` must not be empty
- Step dependencies must form acyclic graph
- All `depends_on` references must exist in workflow steps
- `version` must follow semantic versioning

**Relationships**:

- One Workflow has many WorkflowSteps
- One Workflow can be used by many Conversion Tasks

### 3. Data Profile

Describes characteristics of source neurodata to inform tool selection.

**Fields**:

- `id`: UUID - Unique profile identifier
- `task_id`: UUID - Reference to associated conversion task
- `file_format`: String - Detected file format
- `recording_modality`: List[String] - Types of recordings (e.g.,
  ["extracellular", "behavioral"])
- `file_structure`: Dict[String, Any] - File/directory organization
- `metadata_available`: Dict[String, Any] - Extracted metadata fields
- `data_quality_indicators`: Dict[String, Float] - Quality metrics
  (completeness, consistency, etc.)
- `estimated_size_bytes`: Integer - Total data size
- `num_channels`: Integer | None - Number of recording channels
- `sampling_rate_hz`: Float | None - Data sampling rate
- `duration_seconds`: Float | None - Recording duration
- `detected_issues`: List[String] - Potential problems identified
- `profiled_at`: DateTime - When profiling was performed

**Validation Rules**:

- `task_id` must reference existing Conversion Task
- `recording_modality` must not be empty
- `estimated_size_bytes` must be positive
- Quality indicators must be between 0.0 and 1.0

**Relationships**:

- One Data Profile belongs to one Conversion Task
- One Data Profile informs one or more Agent Decisions

### 4. Agent Decision

Records the agent's reasoning for transparency and debugging.

**Fields**:

- `id`: UUID - Unique decision identifier
- `task_id`: UUID - Reference to conversion task
- `decision_type`: Enum - Type of decision (tool_selection,
  workflow_construction, error_handling, clarification)
- `reasoning`: String - Natural language explanation of decision
- `confidence_score`: Float - Agent's confidence in decision (0.0 to 1.0)
- `alternatives_considered`: List[Alternative] - Other options evaluated
- `selected_option`: String - What was chosen
- `context_used`: Dict[String, Any] - Inputs that informed decision
- `decided_at`: DateTime - When decision was made
- `outcome`: String | None - Result of decision (filled after execution)

**Alternative Fields**:

- `option_name`: String - Name of alternative
- `score`: Float - Evaluation score
- `pros`: List[String] - Advantages
- `cons`: List[String] - Disadvantages

**Validation Rules**:

- `task_id` must reference existing Conversion Task
- `confidence_score` must be between 0.0 and 1.0
- `selected_option` must appear in `alternatives_considered` or be justified

**Relationships**:

- One Agent Decision belongs to one Conversion Task
- Many Agent Decisions can exist per Conversion Task

### 5. Validation Report

Contains schema compliance and quality results for converted NWB files.

**Fields**:

- `id`: UUID - Unique report identifier
- `task_id`: UUID - Reference to conversion task
- `nwb_file_path`: Path - Location of validated NWB file
- `schema_version`: String - NWB schema version validated against
- `is_valid`: Boolean - Overall validation result
- `schema_errors`: List[SchemaError] - Schema compliance issues
- `data_integrity_checks`: Dict[String, Boolean] - Integrity test results
- `quality_metrics`: Dict[String, Float] - Quality scores
- `warnings`: List[String] - Non-critical issues
- `validation_tool`: String - Tool used for validation (e.g., "nwbinspector")
- `validated_at`: DateTime - When validation was performed
- `validation_duration_seconds`: Float - Time taken to validate

**SchemaError Fields**:

- `error_type`: String - Category of error
- `location`: String - Where in file error occurred
- `message`: String - Error description
- `severity`: Enum - critical, error, warning

**Validation Rules**:

- `task_id` must reference existing Conversion Task
- `nwb_file_path` must exist
- `is_valid` must be False if any critical `schema_errors` exist
- Quality metrics must be between 0.0 and 1.0

**Relationships**:

- One Validation Report belongs to one Conversion Task
- One Conversion Task has zero or one Validation Report

### 6. Conversation Context

Maintains user interaction history for coherent multi-turn dialogues.

**Fields**:

- `id`: UUID - Unique conversation identifier
- `user_id`: String - Identifier for user
- `task_id`: UUID | None - Associated conversion task (if conversation led to
  task creation)
- `messages`: List[Message] - Chronological conversation history
- `clarifications`: Dict[String, Any] - Extracted requirements from conversation
- `user_preferences`: Dict[String, Any] - Learned user preferences
- `current_intent`: String | None - Detected user intent
- `started_at`: DateTime - Conversation start time
- `last_activity_at`: DateTime - Last message time
- `is_active`: Boolean - Whether conversation is ongoing

**Message Fields**:

- `role`: Enum - "user" or "agent"
- `content`: String - Message text
- `timestamp`: DateTime - When message was sent
- `intent`: String | None - Detected intent (for user messages)
- `metadata`: Dict[String, Any] - Additional message data

**Validation Rules**:

- `messages` must not be empty
- Messages must be chronologically ordered
- `last_activity_at` must be >= `started_at`
- If `task_id` is set, referenced task must exist

**Relationships**:

- One Conversation Context may create one Conversion Task
- One Conversation Context belongs to one user

### 7. Resource Configuration

Defines system resource limits for concurrent task management.

**Fields**:

- `id`: UUID - Unique configuration identifier
- `max_concurrent_tasks`: Integer - Maximum parallel conversions
- `memory_limit_mb`: Integer - Memory limit per task
- `cpu_limit_percent`: Integer - CPU percentage per task (100 = 1 core)
- `disk_space_required_mb`: Integer - Minimum disk space to start task
- `queue_size_limit`: Integer - Maximum queued tasks
- `timeout_default_seconds`: Integer - Default task timeout
- `created_at`: DateTime - When configuration was set
- `updated_at`: DateTime - Last modification
- `is_active`: Boolean - Whether this configuration is in use

**Validation Rules**:

- `max_concurrent_tasks` must be positive
- `memory_limit_mb` must be positive
- `cpu_limit_percent` must be between 1 and 100 \* num_cores
- `queue_size_limit` must be positive

**Relationships**:

- One Resource Configuration can be active at a time
- Resource Configuration constrains Conversion Task execution

### 8. Metrics Aggregate

Weekly summaries of conversion statistics.

**Fields**:

- `id`: UUID - Unique aggregate identifier
- `week_start_date`: Date - Start of aggregation week (Monday)
- `week_end_date`: Date - End of aggregation week (Sunday)
- `total_tasks`: Integer - Total tasks in period
- `successful_tasks`: Integer - Tasks completed successfully
- `failed_tasks`: Integer - Tasks that failed
- `average_duration_seconds`: Float - Mean task duration
- `median_duration_seconds`: Float - Median task duration
- `p95_duration_seconds`: Float - 95th percentile duration
- `error_type_counts`: Dict[String, Integer] - Frequency of error types
- `data_format_counts`: Dict[String, Integer] - Frequency of source formats
- `total_data_processed_gb`: Float - Total data volume converted
- `created_at`: DateTime - When aggregate was computed

**Validation Rules**:

- `week_end_date` must be after `week_start_date`
- `successful_tasks` + `failed_tasks` must equal `total_tasks`
- Duration percentiles must be: p95 >= median >= average (approximately)
- All counts must be non-negative

**Relationships**:

- One Metrics Aggregate summarizes many Conversion Tasks
- Metrics Aggregates are time-partitioned by week

## Derived Entities

### ErrorRecord

Embedded in Conversion Task to track error history.

**Fields**:

- `error_type`: String - Category of error
- `error_message`: String - Error description
- `error_code`: String | None - Structured error code
- `occurred_at`: DateTime - When error happened
- `recovery_attempted`: Boolean - Whether recovery was tried
- `recovery_successful`: Boolean - Whether recovery worked
- `stack_trace`: String | None - Technical error details

### RetryPolicy

Embedded in WorkflowStep to define failure handling.

**Fields**:

- `max_retries`: Integer - Maximum retry attempts
- `retry_delay_seconds`: Integer - Delay between retries
- `backoff_multiplier`: Float - Exponential backoff factor
- `retry_on_errors`: List[String] - Error types that trigger retry

## State Machine Diagrams

### Conversion Task States

```
┌─────────┐
│ pending │
└────┬────┘
     │
     ▼
┌──────────┐
│profiling │
└────┬─────┘
     │
     ▼
┌────────────────┐      ┌─────────────────────┐
│tool_selection  │─────▶│clarification_needed │
└────┬───────────┘      └──────────┬──────────┘
     │                             │
     │◀────────────────────────────┘
     ▼
┌───────────┐
│executing  │
└────┬──────┘
     │
     ├──────▶(error)───▶┌────────┐
     │                  │failed  │
     │                  └────────┘
     ▼
┌────────────┐
│validating  │
└────┬───────┘
     │
     ▼
┌───────────┐
│completed  │
└───────────┘

(Any state can transition to 'cancelled')
```

## Persistence Strategy

### Storage Format

- **Primary**: JSON files for human readability and debugging
- **Location**: `~/.agentic-neurodata/state/`
- **File naming**: `{entity_type}_{entity_id}.json`
- **Indexing**: In-memory index for fast lookup, rebuilt on startup

### Upgrade Path

When multi-user or high-volume scenarios emerge:

1. Implement SQLite adapter with same interface
2. Migration script to import JSON files
3. Feature flag to switch between JSON and SQLite
4. Eventually remove JSON persistence

### Backup Strategy

- Daily backup of entire state directory
- Retention: Keep last 7 days
- Corruption recovery: Fallback to previous day's backup
