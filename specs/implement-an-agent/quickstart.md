# Quickstart Guide

**Feature**: Agent-Based Neurodata Conversion System **Date**: 2025-10-03

## Overview

This guide provides a step-by-step test scenario to validate the agent-based
neurodata conversion system. It covers the primary user story: a researcher
using natural language to request conversion, the agent gathering requirements,
executing the workflow, and reporting results.

## Prerequisites

- Python 3.12+ environment with all dependencies installed
- Sample neurodata files available for testing
- API server running on `http://localhost:8000`

## Test Scenario: Natural Language Conversion Request

### Step 1: Start a Conversation

**Objective**: Initiate a conversation with the agent to describe conversion
needs.

**Action**:

```bash
curl -X POST http://localhost:8000/api/v1/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have some neural recordings from a Blackrock system that I need to convert to NWB format",
    "user_id": "researcher_test"
  }'
```

**Expected Response**:

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_message": "I can help you convert your Blackrock recordings to NWB format. To ensure a proper conversion, I need a few details:\n\n1. Where are your Blackrock files located?\n2. Do you have any specific metadata or experimental details to include?\n3. Where would you like the converted NWB file saved?",
  "requires_response": true,
  "suggested_actions": [
    "Provide file paths",
    "Share experimental metadata",
    "Specify output location"
  ]
}
```

**Validation**:

- [ ] Response status is 201 (Created)
- [ ] Response contains valid `conversation_id` (UUID format)
- [ ] Agent message contains clarifying questions
- [ ] `requires_response` is `true`

### Step 2: Provide File Paths

**Objective**: Answer agent's clarifying questions with specific file
information.

**Action**:

```bash
curl -X POST http://localhost:8000/api/v1/conversation/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "The files are in /data/blackrock/session_2024_01_15/ and I want the output in /data/nwb/session_2024_01_15.nwb"
  }'
```

**Expected Response**:

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_message": "Perfect! I found your Blackrock data files. I detected:\n- 32 channel neural recordings\n- Sampling rate: 30 kHz\n- Recording duration: 45 minutes\n\nI'll use the neuroconv tool with the Blackrock interface to convert this data. Would you like me to proceed with the conversion?",
  "requires_response": true,
  "suggested_actions": [
    "Confirm and start conversion",
    "Add more metadata",
    "Change conversion settings"
  ]
}
```

**Validation**:

- [ ] Response status is 200 (OK)
- [ ] Agent correctly identifies data characteristics
- [ ] Agent proposes specific conversion tool
- [ ] Agent requests confirmation before proceeding

### Step 3: Confirm Conversion

**Objective**: Authorize the agent to start the conversion task.

**Action**:

```bash
curl -X POST http://localhost:8000/api/v1/conversation/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Yes, please proceed with the conversion"
  }'
```

**Expected Response**:

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_message": "Great! I've started the conversion task. Your task ID is 660e8400-e29b-41d4-a716-446655440001. You can check the progress at any time.",
  "requires_response": false,
  "task_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

**Validation**:

- [ ] Response status is 200 (OK)
- [ ] Response includes `task_id`
- [ ] `requires_response` is `false` (conversation complete)
- [ ] Task has been created in the system

### Step 4: Check Task Status

**Objective**: Monitor conversion progress during execution.

**Action**:

```bash
curl http://localhost:8000/api/v1/tasks/660e8400-e29b-41d4-a716-446655440001/status
```

**Expected Response (During Execution)**:

```json
{
  "task_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "executing",
  "progress": 0.45,
  "current_step": "Converting neural data channels (14/32 complete)",
  "estimated_completion_time": "2025-10-03T15:30:00Z",
  "last_error": null
}
```

**Validation**:

- [ ] Response status is 200 (OK)
- [ ] Status shows active conversion state (`executing`)
- [ ] Progress is between 0.0 and 1.0
- [ ] Current step provides meaningful description
- [ ] Estimated completion time is in the future

### Step 5: Retrieve Task Details

**Objective**: Get comprehensive task information including decisions made by
the agent.

**Action**:

```bash
curl http://localhost:8000/api/v1/tasks/660e8400-e29b-41d4-a716-446655440001
```

**Expected Response**:

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "source_path": "/data/blackrock/session_2024_01_15/",
  "source_format": "Blackrock",
  "target_path": "/data/nwb/session_2024_01_15.nwb",
  "status": "executing",
  "progress": 0.45,
  "workflow_id": "770e8400-e29b-41d4-a716-446655440002",
  "error_history": [],
  "submission_time": "2025-10-03T15:00:00Z",
  "start_time": "2025-10-03T15:00:05Z",
  "completion_time": null,
  "result": null,
  "user_id": "researcher_test",
  "priority": 0,
  "metadata": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "detected_channels": 32,
    "sampling_rate_hz": 30000,
    "duration_seconds": 2700
  }
}
```

**Validation**:

- [ ] Response status is 200 (OK)
- [ ] Task contains all required fields
- [ ] Metadata includes profiling information
- [ ] Error history is empty (no errors)
- [ ] Timestamps are consistent (start_time after submission_time)

### Step 6: Wait for Completion and Check Results

**Objective**: Verify successful conversion and validation results.

**Action** (wait for completion, then):

```bash
curl http://localhost:8000/api/v1/tasks/660e8400-e29b-41d4-a716-446655440001
```

**Expected Response**:

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "source_path": "/data/blackrock/session_2024_01_15/",
  "source_format": "Blackrock",
  "target_path": "/data/nwb/session_2024_01_15.nwb",
  "status": "completed",
  "progress": 1.0,
  "workflow_id": "770e8400-e29b-41d4-a716-446655440002",
  "error_history": [],
  "submission_time": "2025-10-03T15:00:00Z",
  "start_time": "2025-10-03T15:00:05Z",
  "completion_time": "2025-10-03T15:28:32Z",
  "result": {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "task_id": "660e8400-e29b-41d4-a716-446655440001",
    "nwb_file_path": "/data/nwb/session_2024_01_15.nwb",
    "schema_version": "2.7.0",
    "is_valid": true,
    "schema_errors": [],
    "data_integrity_checks": {
      "all_channels_present": true,
      "timestamps_monotonic": true,
      "no_missing_data": true
    },
    "quality_metrics": {
      "completeness": 1.0,
      "consistency": 0.98,
      "compliance": 1.0
    },
    "warnings": [
      "Some optional metadata fields are missing (experimenter, institution)"
    ],
    "validation_tool": "nwbinspector",
    "validated_at": "2025-10-03T15:28:25Z",
    "validation_duration_seconds": 3.2
  },
  "user_id": "researcher_test",
  "priority": 0,
  "metadata": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "detected_channels": 32,
    "sampling_rate_hz": 30000,
    "duration_seconds": 2700
  }
}
```

**Validation**:

- [ ] Response status is 200 (OK)
- [ ] Task status is `completed`
- [ ] Progress is 1.0 (100%)
- [ ] `completion_time` is set and after `start_time`
- [ ] Validation report exists and shows `is_valid: true`
- [ ] NWB file exists at target path
- [ ] Data integrity checks all pass
- [ ] Quality metrics are within acceptable ranges

### Step 7: Verify NWB File

**Objective**: Confirm the converted NWB file is readable and contains expected
data.

**Action**:

```python
# Python test script
from pynwb import NWBHDF5IO

with NWBHDF5IO('/data/nwb/session_2024_01_15.nwb', 'r') as io:
    nwbfile = io.read()

    # Verify acquisition data
    assert 'ElectricalSeries' in nwbfile.acquisition
    electrical_series = nwbfile.acquisition['ElectricalSeries']

    # Check data dimensions
    assert electrical_series.data.shape[1] == 32  # 32 channels
    assert electrical_series.rate == 30000.0  # 30 kHz sampling rate

    print("✓ NWB file structure is valid")
    print(f"✓ Contains {electrical_series.data.shape[0]} samples")
    print(f"✓ Across {electrical_series.data.shape[1]} channels")
    print(f"✓ Sampling rate: {electrical_series.rate} Hz")
```

**Expected Output**:

```
✓ NWB file structure is valid
✓ Contains 81000000 samples
✓ Across 32 channels
✓ Sampling rate: 30000.0 Hz
```

**Validation**:

- [ ] NWB file opens without errors
- [ ] Electrical series data present
- [ ] Channel count matches source data (32)
- [ ] Sampling rate matches source data (30 kHz)
- [ ] Sample count is consistent with duration

## Additional Test Scenarios

### Scenario 2: Task Status Query During Conversion

Test that status queries return accurate progress information while conversion
is running.

**Commands**:

```bash
# Start conversion (Steps 1-3 from above)
# Then repeatedly query status
watch -n 2 'curl -s http://localhost:8000/api/v1/tasks/{task_id}/status | jq'
```

**Validation**:

- [ ] Progress increases monotonically
- [ ] Current step descriptions change as workflow advances
- [ ] Estimated completion time adjusts based on progress

### Scenario 3: Multiple Queued Tasks (FIFO)

Test that multiple tasks are executed in submission order.

**Commands**:

```bash
# Create 3 tasks rapidly
for i in {1..3}; do
  curl -X POST http://localhost:8000/api/v1/tasks \
    -H "Content-Type: application/json" \
    -d "{
      \"source_path\": \"/data/session_$i/\",
      \"target_path\": \"/data/nwb/session_$i.nwb\",
      \"user_id\": \"researcher_test\"
    }"
  sleep 1
done

# Check task list
curl http://localhost:8000/api/v1/tasks
```

**Validation**:

- [ ] Tasks execute in submission order (FIFO)
- [ ] No more than configured max_concurrent_tasks run simultaneously
- [ ] Earlier submitted tasks complete before later ones start

### Scenario 4: Conversion Failure and Recovery

Test error handling when conversion fails.

**Commands**:

```bash
# Create task with invalid source path
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "/data/nonexistent/",
    "target_path": "/data/nwb/test.nwb",
    "user_id": "researcher_test"
  }'

# Check task for error information
curl http://localhost:8000/api/v1/tasks/{task_id}
```

**Validation**:

- [ ] Task status becomes `failed`
- [ ] Error history contains descriptive error
- [ ] Error message suggests corrective action
- [ ] Recovery attempt was made (if applicable)

### Scenario 5: Informal Data Description with Clarification

Test agent's ability to ask clarifying questions.

**Commands**:

```bash
curl -X POST http://localhost:8000/api/v1/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need to convert some brain recordings to NWB",
    "user_id": "researcher_test"
  }'
```

**Validation**:

- [ ] Agent recognizes vague request
- [ ] Agent asks for data format
- [ ] Agent asks for file locations
- [ ] Agent asks for recording modality
- [ ] Conversation requires multiple turns to gather requirements

## Performance Validation

### Response Time Targets

- [ ] Conversation endpoints respond in <500ms
- [ ] Status queries respond in <200ms
- [ ] Task creation responds in <1s
- [ ] Metrics queries respond in <1s

### Concurrency Tests

- [ ] System handles 5 concurrent tasks (configurable)
- [ ] Queue properly manages 20+ waiting tasks
- [ ] No resource exhaustion under load
- [ ] Graceful degradation when limits reached

## Success Criteria

All validation checkboxes above must be checked for the quickstart to pass. This
ensures:

1. Natural language conversation works end-to-end
2. Agent correctly profiles data and selects tools
3. Conversion executes successfully
4. Validation confirms NWB compliance
5. Error handling works properly
6. Performance meets targets

## Troubleshooting

### Common Issues

**Issue**: Conversation endpoint returns 500 error

- **Check**: API server is running and healthy
- **Check**: LLM/MCP tools are accessible
- **Fix**: Restart server, check logs for details

**Issue**: Task stuck in "profiling" status

- **Check**: Source files are accessible
- **Check**: Sufficient disk space for profiling
- **Fix**: Cancel task and retry with valid source path

**Issue**: Validation fails with schema errors

- **Check**: Source data is complete and not corrupted
- **Check**: Conversion tool version compatibility
- **Fix**: Review error details, adjust conversion parameters

**Issue**: NWB file cannot be opened

- **Check**: File exists at target path
- **Check**: File permissions are correct
- **Fix**: Verify task completed successfully, check error history

## Next Steps

After completing this quickstart:

1. Review agent decision logs to understand tool selection reasoning
2. Examine metrics endpoint for conversion statistics
3. Test with different data formats (Intan, SpikeGLX, etc.)
4. Explore workflow customization for specific use cases
5. Set up monitoring and alerting for production use
