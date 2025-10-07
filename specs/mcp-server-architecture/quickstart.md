# MCP Server Architecture - Quick Start Guide

**Feature**: MCP Server Architecture **Version**: 1.0.0 **Date**: 2025-10-06

## Overview

This guide helps you quickly get started with the MCP Server Architecture for
orchestrating multi-agent neuroscience data conversions. You'll learn how to
submit data, run conversions, and validate results using both the HTTP API and
MCP protocol.

---

## Prerequisites

- Python 3.9-3.11 installed
- Access to neuroscience dataset for conversion
- MCP server running (default: `http://localhost:8000`)

---

## Quick Start: Complete Workflow

### Step 1: Submit Dataset for Conversion

**Using HTTP API:**

```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "input_path": "/data/experiments/exp001",
    "metadata": {
      "experimenter": "Jane Doe",
      "session_description": "Visual cortex recording session",
      "session_id": "exp001_20250106"
    },
    "auto_start": true
  }'
```

**Expected Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "analyzing",
  "input_path": "/data/experiments/exp001",
  "metadata": {
    "experimenter": "Jane Doe",
    "session_description": "Visual cortex recording session",
    "session_id": "exp001_20250106"
  },
  "created_at": "2025-10-06T10:30:00Z",
  "updated_at": "2025-10-06T10:30:00Z",
  "completed_at": null
}
```

**Using MCP Protocol:**

```python
from mcp import Client

async with Client("mcp://localhost:8000") as client:
    result = await client.call_tool(
        "create_workflow",
        input_path="/data/experiments/exp001",
        metadata={
            "experimenter": "Jane Doe",
            "session_description": "Visual cortex recording session"
        },
        auto_start=True
    )
    workflow_id = result["workflow_id"]
    print(f"Created workflow: {workflow_id}")
```

---

### Step 2: Monitor Workflow Progress

**Using HTTP API:**

```bash
# Poll workflow status
curl -X GET http://localhost:8000/api/v1/workflows/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your-api-key"
```

**Expected Response (during execution):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "converting",
  "input_path": "/data/experiments/exp001",
  "output_path": null,
  "metadata": {
    "experimenter": "Jane Doe",
    "session_description": "Visual cortex recording session"
  },
  "format_info": {
    "primary_format": {
      "name": "Intan",
      "version": "2.0",
      "confidence": 0.95,
      "neuroconv_interface": "IntanRecordingInterface",
      "detection_method": "directory_structure"
    },
    "formats_detected": [
      {
        "name": "Intan",
        "confidence": 0.95,
        "neuroconv_interface": "IntanRecordingInterface"
      }
    ],
    "recommended_interface": "IntanRecordingInterface"
  },
  "created_at": "2025-10-06T10:30:00Z",
  "updated_at": "2025-10-06T10:31:15Z",
  "completed_at": null
}
```

**Using MCP Protocol:**

```python
# Monitor workflow state
result = await client.call_tool("get_workflow", workflow_id=workflow_id)
print(f"State: {result['state']}")
print(f"Format: {result['format_info']['primary_format']['name']}")
```

---

### Step 3: View Execution Steps

**Using HTTP API:**

```bash
curl -X GET http://localhost:8000/api/v1/workflows/550e8400-e29b-41d4-a716-446655440000/steps \
  -H "X-API-Key: your-api-key"
```

**Expected Response:**

```json
{
  "steps": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440001",
      "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
      "agent_type": "conversation",
      "status": "completed",
      "sequence_number": 1,
      "started_at": "2025-10-06T10:30:00Z",
      "completed_at": "2025-10-06T10:30:45Z",
      "duration_ms": 45000,
      "retry_count": 0,
      "input_data": {
        "operation": "analyze_dataset",
        "path": "/data/experiments/exp001"
      },
      "output_data": {
        "format": "Intan",
        "version": "2.0",
        "recommended_interface": "IntanRecordingInterface"
      }
    },
    {
      "id": "750e8400-e29b-41d4-a716-446655440002",
      "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
      "agent_type": "conversion",
      "status": "running",
      "sequence_number": 2,
      "started_at": "2025-10-06T10:30:45Z",
      "completed_at": null,
      "duration_ms": null,
      "retry_count": 0
    }
  ]
}
```

---

### Step 4: Check Completion and Validation

**Using HTTP API:**

```bash
# Check if workflow completed
curl -X GET http://localhost:8000/api/v1/workflows/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your-api-key"
```

**Expected Response (completed):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "completed",
  "input_path": "/data/experiments/exp001",
  "output_path": "/output/exp001_20250106.nwb",
  "validation_summary": [
    {
      "validator_name": "nwb_inspector",
      "severity": "info",
      "issues": [],
      "quality_score": 1.0,
      "passed": true,
      "execution_time_ms": 2340
    },
    {
      "validator_name": "pynwb",
      "severity": "warning",
      "issues": [
        {
          "severity": "warning",
          "message": "Missing optional field: keywords",
          "location": "/general",
          "suggestion": "Add keywords for better discoverability"
        }
      ],
      "quality_score": 0.95,
      "passed": true,
      "execution_time_ms": 1890
    },
    {
      "validator_name": "dandi",
      "severity": "info",
      "issues": [],
      "quality_score": 1.0,
      "passed": true,
      "execution_time_ms": 3120
    }
  ],
  "created_at": "2025-10-06T10:30:00Z",
  "updated_at": "2025-10-06T10:32:30Z",
  "completed_at": "2025-10-06T10:32:30Z"
}
```

**Success Criteria:**

- ✅ `state` is `completed`
- ✅ `output_path` contains path to generated NWB file
- ✅ `validation_summary` shows `passed: true` for all validators
- ✅ `quality_score` >= 0.9 for production use

---

## Advanced Usage Examples

### Example 1: Detect Format Before Conversion

**Scenario:** You want to verify format detection before starting a full
conversion.

```bash
# Detect format
curl -X POST http://localhost:8000/api/v1/formats/detect \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "input_path": "/data/experiments/exp002"
  }'
```

**Response:**

```json
{
  "formats_detected": [
    {
      "name": "SpikeGLX",
      "version": "3.0",
      "confidence": 0.98,
      "neuroconv_interface": "SpikeGLXRecordingInterface",
      "detection_method": "directory_structure"
    }
  ],
  "primary_format": {
    "name": "SpikeGLX",
    "confidence": 0.98,
    "neuroconv_interface": "SpikeGLXRecordingInterface"
  },
  "recommended_interface": "SpikeGLXRecordingInterface",
  "confidence_scores": {
    "extension": 0.85,
    "directory_structure": 0.98,
    "magic_bytes": 0.9
  },
  "warnings": []
}
```

---

### Example 2: Manual Agent Invocation

**Scenario:** You want to test a specific agent independently.

```bash
# Invoke conversion agent directly
curl -X POST http://localhost:8000/api/v1/agents/conversion/invoke \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "operation": "generate_script",
    "input": {
      "format": "Intan",
      "interface": "IntanRecordingInterface",
      "input_path": "/data/test",
      "output_path": "/output/test.nwb"
    },
    "timeout_seconds": 300
  }'
```

**Response:**

```json
{
  "agent_type": "conversion",
  "success": true,
  "output_data": {
    "script_path": "/tmp/conversion_script_123.py",
    "interface_used": "IntanRecordingInterface",
    "estimated_duration_seconds": 180
  },
  "execution_time_ms": 1234,
  "correlation_id": "850e8400-e29b-41d4-a716-446655440003",
  "metadata": {
    "agent_version": "1.0.0",
    "model_used": "claude-3-5-sonnet-20241022"
  }
}
```

---

### Example 3: List and Filter Workflows

**Scenario:** Find all failed workflows for debugging.

```bash
# Get failed workflows
curl -X GET "http://localhost:8000/api/v1/workflows?state=failed&limit=10" \
  -H "X-API-Key: your-api-key"
```

**Response:**

```json
{
  "workflows": [
    {
      "id": "950e8400-e29b-41d4-a716-446655440004",
      "state": "failed",
      "input_path": "/data/corrupted_exp",
      "error_details": {
        "type": "FormatDetectionError",
        "message": "Unable to detect format with sufficient confidence",
        "details": {
          "max_confidence": 0.45,
          "threshold": 0.7
        }
      },
      "created_at": "2025-10-06T09:15:00Z",
      "updated_at": "2025-10-06T09:15:30Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

---

### Example 4: Run Standalone Validation

**Scenario:** Validate an existing NWB file without running conversion.

```bash
# Validate NWB file
curl -X POST http://localhost:8000/api/v1/validation/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "nwb_file_path": "/output/existing_file.nwb",
    "validators": ["nwb_inspector", "dandi"]
  }'
```

**Response:**

```json
{
  "validation_id": "a50e8400-e29b-41d4-a716-446655440005",
  "results": [
    {
      "validator_name": "nwb_inspector",
      "severity": "error",
      "issues": [
        {
          "severity": "error",
          "message": "Invalid timestamp format in acquisition/TimeSeries",
          "location": "/acquisition/TimeSeries/timestamps",
          "suggestion": "Ensure timestamps are in ISO 8601 format"
        }
      ],
      "quality_score": 0.7,
      "passed": false,
      "execution_time_ms": 2100
    },
    {
      "validator_name": "dandi",
      "severity": "warning",
      "issues": [
        {
          "severity": "warning",
          "message": "Missing recommended field: related_publications",
          "location": "/general",
          "suggestion": "Add related publications for better documentation"
        }
      ],
      "quality_score": 0.85,
      "passed": true,
      "execution_time_ms": 3200
    }
  ],
  "overall_passed": false,
  "overall_quality_score": 0.775,
  "executed_at": "2025-10-06T10:45:00Z"
}
```

---

### Example 5: Cancel Running Workflow

**Scenario:** Cancel a long-running workflow that's no longer needed.

```bash
# Cancel workflow
curl -X POST http://localhost:8000/api/v1/workflows/550e8400-e29b-41d4-a716-446655440000/cancel \
  -H "X-API-Key: your-api-key"
```

**Response:**

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "cancelled",
  "message": "Workflow cancelled successfully. Cleanup operations completed."
}
```

---

## Using MCP Protocol (Python)

### Complete Workflow Example

```python
import asyncio
from mcp import Client

async def run_conversion():
    async with Client("mcp://localhost:8000") as client:
        # Step 1: Create and start workflow
        workflow = await client.call_tool(
            "create_workflow",
            input_path="/data/experiments/exp001",
            metadata={
                "experimenter": "Jane Doe",
                "session_description": "Visual cortex recording"
            },
            auto_start=True
        )
        workflow_id = workflow["workflow_id"]
        print(f"Started workflow: {workflow_id}")

        # Step 2: Poll until completion
        while True:
            status = await client.call_tool("get_workflow", workflow_id=workflow_id)
            state = status["state"]
            print(f"Current state: {state}")

            if state in ["completed", "failed", "cancelled"]:
                break

            await asyncio.sleep(5)  # Poll every 5 seconds

        # Step 3: Get final results
        if state == "completed":
            print(f"✅ Conversion successful!")
            print(f"Output file: {status['output_path']}")

            # Check validation
            for validator in status["validation_summary"]:
                print(f"\n{validator['validator_name']}: {'✅ PASS' if validator['passed'] else '❌ FAIL'}")
                print(f"Quality score: {validator['quality_score']:.2f}")
                if validator['issues']:
                    print("Issues:")
                    for issue in validator['issues']:
                        print(f"  - [{issue['severity']}] {issue['message']}")
        else:
            print(f"❌ Workflow {state}")
            if status.get("error_details"):
                print(f"Error: {status['error_details']['message']}")

# Run the conversion
asyncio.run(run_conversion())
```

---

## Understanding Workflow States

The workflow progresses through these states:

1. **PENDING** → Workflow created, not started
2. **ANALYZING** → Format detection in progress
3. **COLLECTING** → Metadata collection (if needed)
4. **CONVERTING** → NWB conversion in progress
5. **VALIDATING** → Validation checks running
6. **COMPLETED** → Success! ✅
7. **FAILED** → Error occurred ❌
8. **CANCELLED** → User cancelled 🛑

**State Transition Flow:**

```
PENDING → ANALYZING → [COLLECTING] → CONVERTING → VALIDATING → COMPLETED
                  ↓         ↓              ↓            ↓
                  └─────────┴──────────────┴────────────→ FAILED

                  [Any state] → CANCELLED (user action)
```

---

## Expected Outputs

### Successful Conversion

**Indicators:**

- ✅ Final state: `completed`
- ✅ `output_path` points to valid NWB file
- ✅ All validators show `passed: true`
- ✅ Quality score ≥ 0.9

**Output Files:**

- `{output_path}` - Generated NWB file
- `{output_path}.log` - Conversion logs
- `{output_path}_validation.json` - Detailed validation report

### Partial Success (Warnings)

**Indicators:**

- ✅ Final state: `completed`
- ⚠️ Some validators have warnings
- ✅ Overall quality score ≥ 0.8

**Action:** Review warnings and optionally improve metadata

### Failure

**Indicators:**

- ❌ Final state: `failed`
- ❌ `error_details` contains error information
- ❌ No `output_path`

**Common Failure Reasons:**

- Format detection confidence < 0.7
- Missing required metadata
- Conversion script execution error
- Critical validation failures

---

## API Authentication

### Using API Keys (HTTP)

```bash
# Include API key in header
curl -H "X-API-Key: your-api-key" ...
```

### Using JWT Tokens (HTTP)

```bash
# Include Bearer token
curl -H "Authorization: Bearer your-jwt-token" ...
```

### MCP Protocol

```python
# Authentication handled during client connection
async with Client("mcp://localhost:8000", auth_token="your-token") as client:
    # ... use client
```

---

## Error Handling

### Common Errors

**400 Bad Request:**

```json
{
  "error": "BAD_REQUEST",
  "message": "Invalid input parameters",
  "details": {
    "field": "input_path",
    "issue": "Path does not exist"
  }
}
```

**404 Not Found:**

```json
{
  "error": "NOT_FOUND",
  "message": "Workflow not found",
  "details": {
    "workflow_id": "invalid-id"
  }
}
```

**408 Request Timeout:**

```json
{
  "error": "TIMEOUT",
  "message": "Agent invocation timeout",
  "details": {
    "agent_type": "conversion",
    "timeout_seconds": 300
  }
}
```

**409 Conflict:**

```json
{
  "error": "CONFLICT",
  "message": "Workflow was modified by another process",
  "details": {
    "current_version": 3,
    "provided_version": 2
  }
}
```

---

## Performance Considerations

### Timeouts

- **Format Detection:** ~30-60 seconds
- **Metadata Collection:** Variable (user-dependent)
- **Conversion:** ~2-10 minutes (depends on dataset size)
- **Validation:** ~5-30 seconds per validator

### Concurrent Workflows

The server supports **10+ concurrent workflows** with proper resource
management:

```bash
# Create multiple workflows in parallel
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/workflows \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-api-key" \
    -d "{\"input_path\": \"/data/exp$i\", \"auto_start\": true}" &
done
```

### API Latency

- **Expected latency:** < 100ms for API operations
- **Workflow startup:** < 2 seconds
- **Step transitions:** < 500ms

---

## Next Steps

1. **Explore API Documentation:** See `contracts/openapi.yaml` for full API
   specification
2. **Review Data Models:** See `data-model.md` for entity definitions
3. **Check Agent Capabilities:** Use `/agents/health` to verify agent
   availability
4. **Browse Supported Formats:** Use `/formats/supported` to see all format
   options
5. **Set Up Monitoring:** Configure observability tools for production
   deployments

---

## Support

For issues or questions:

- API Documentation: `http://localhost:8000/docs` (Swagger UI)
- GitHub Issues: [project repository]
- Email: support@example.com

---

**Quick Start Complete!** You now know how to:

- ✅ Submit datasets for conversion
- ✅ Monitor workflow progress
- ✅ Check validation results
- ✅ Handle errors and cancellations
- ✅ Use both HTTP and MCP protocols
