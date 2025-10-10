# Quickstart Guide: MCP Server Architecture

**Version**: 1.0.0 **Date**: 2025-10-10 **Feature**: MCP Server Architecture -
End-to-End Example

This guide walks through a complete conversion workflow using Scenario 1 from
the specification: converting a single neuroscience dataset to NWB format with
automatic format detection, metadata collection, conversion, and validation.

---

## Prerequisites

### System Requirements

- Python 3.11+
- 8GB RAM minimum (16GB recommended)
- 50GB free disk space
- Linux, macOS, or Windows with WSL2

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/agentic-neurodata-conversion.git
cd agentic-neurodata-conversion

# Install with pixi (recommended)
pixi install

# Activate environment
pixi shell

# Verify installation
python -c "import pynwb, nwbinspector; print('Installation successful')"
```

### Sample Dataset

Download a sample SpikeGLX dataset for this tutorial:

```bash
# Create data directory
mkdir -p data/quickstart

# Download sample dataset (fictional URL - replace with actual)
wget https://example.com/sample-spikeglx-dataset.zip -O data/quickstart/sample.zip

# Extract
unzip data/quickstart/sample.zip -d data/quickstart/experiment_001

# Verify structure
ls -la data/quickstart/experiment_001
# Expected output:
# experiment_001_g0_t0.imec0.ap.bin
# experiment_001_g0_t0.imec0.ap.meta
# experiment_001_g0_t0.imec0.lf.bin
# experiment_001_g0_t0.imec0.lf.meta
```

---

## Step 1: Start the MCP Server

### Option A: MCP Protocol (stdio)

For use with Claude Desktop or MCP-compatible clients:

```bash
# Start MCP server with stdio transport
pixi run mcp-server

# Server starts and waits for MCP protocol messages on stdin/stdout
# [2025-10-10 10:00:00] INFO: MCP server started (stdio transport)
# [2025-10-10 10:00:00] INFO: Registered 7 MCP tools
# [2025-10-10 10:00:00] INFO: Waiting for messages...
```

**MCP Client Configuration** (for Claude Desktop):

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "neurodata-conversion": {
      "command": "pixi",
      "args": ["run", "mcp-server"],
      "cwd": "/path/to/agentic-neurodata-conversion"
    }
  }
}
```

### Option B: HTTP REST API

For programmatic access or web integrations:

```bash
# Start HTTP server
pixi run http-server

# Server starts on http://localhost:8000
# [2025-10-10 10:00:00] INFO: HTTP server started on http://0.0.0.0:8000
# [2025-10-10 10:00:00] INFO: OpenAPI docs available at http://localhost:8000/docs
# [2025-10-10 10:00:00] INFO: WebSocket endpoint: ws://localhost:8000/api/v1/ws/conversions/{session_id}
```

Open browser to http://localhost:8000/docs to view interactive API
documentation.

### Option C: Both Protocols (Recommended for Development)

```bash
# Start both MCP and HTTP servers
pixi run start-all

# [2025-10-10 10:00:00] INFO: Starting MCP server (background)...
# [2025-10-10 10:00:01] INFO: Starting HTTP server...
# [2025-10-10 10:00:02] INFO: All servers running. Press Ctrl+C to stop.
```

---

## Step 2: Submit Dataset for Conversion

### Via MCP Protocol

Using Claude Desktop with MCP server configured:

```
User: Convert the dataset at /path/to/data/quickstart/experiment_001 to NWB format

Claude (uses convert-dataset tool internally):
I'll convert your SpikeGLX dataset to NWB format. I've submitted the conversion workflow.

Session ID: 123e4567-e89b-12d3-a456-426614174000
Initial Status: Analyzing (5% complete)

The workflow is now running. I'll monitor the progress...
```

### Via HTTP REST API

```bash
# Submit conversion request
curl -X POST http://localhost:8000/api/v1/conversions \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_path": "/path/to/data/quickstart/experiment_001",
    "workflow_config": {
      "validation_config": {
        "run_dandi_validation": true
      }
    }
  }'
```

**Response**:

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "initial_status": {
    "state": "analyzing",
    "current_step": "format_detection",
    "progress_percentage": 5.0,
    "created_at": "2025-10-10T10:00:00Z",
    "expires_at": "2025-10-10T12:00:00Z"
  }
}
```

**Save the session_id** for tracking progress!

---

## Step 3: Monitor Progress

### Via MCP Protocol

Claude will automatically poll and report progress:

```
Claude: The conversion is progressing:

Format Detection (Complete):
- Detected format: SpikeGLX
- Confidence: 95%
- Detected .meta and .bin file pairs

Metadata Collection (In Progress):
- Progress: 35%
- The metadata questioner agent needs some information...
```

### Via WebSocket (Real-Time Updates)

```javascript
// Connect to WebSocket for streaming updates
const ws = new WebSocket(
  "ws://localhost:8000/api/v1/ws/conversions/123e4567-e89b-12d3-a456-426614174000",
);

ws.onopen = () => {
  ws.send(
    JSON.stringify({
      type: "subscribe",
      session_id: "123e4567-e89b-12d3-a456-426614174000",
    }),
  );
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log("Progress:", message);

  if (message.type === "progress_update") {
    console.log(`${message.progress_percentage}% - ${message.message}`);
  }
};
```

**Output**:

```
Progress: 5% - Analyzing dataset structure
Progress: 15% - Format detection complete: SpikeGLX (95% confidence)
Progress: 20% - Starting metadata collection
Progress: 35% - Awaiting user input for experiment description
```

### Via HTTP Polling

```bash
# Poll for status updates
while true; do
  curl http://localhost:8000/api/v1/conversions/123e4567-e89b-12d3-a456-426614174000 | jq
  sleep 5
done
```

**Output (format detection complete)**:

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "state": "collecting_metadata",
  "current_step": "metadata_questioner",
  "progress_percentage": 35.0,
  "created_at": "2025-10-10T10:00:00Z",
  "updated_at": "2025-10-10T10:02:30Z",
  "format_detection": {
    "primary_format": "SpikeGLX",
    "confidence": 0.95
  }
}
```

---

## Step 4: Provide Metadata (Interactive)

The metadata questioner agent needs experimental details not found in data
files.

### Via MCP Protocol

```
Claude: The metadata questioner agent needs the following information:

1. Experiment description: What is the scientific goal of this experiment?
2. Subject species: What species was the subject?
3. Subject ID: What is the unique identifier for the subject?

Please provide these details.

User:
- Experiment description: Multi-electrode array recording in motor cortex during reaching task
- Subject species: Mus musculus
- Subject ID: mouse_001

Claude (uses resume-workflow tool with user inputs):
Thank you! I've provided this metadata to the workflow. Conversion is now proceeding...
```

### Via HTTP REST API

```bash
# Resume workflow with user inputs
curl -X POST http://localhost:8000/api/v1/conversions/123e4567-e89b-12d3-a456-426614174000/resume \
  -H "Content-Type: application/json" \
  -d '{
    "user_inputs": {
      "experiment_description": "Multi-electrode array recording in motor cortex during reaching task",
      "subject_species": "Mus musculus",
      "subject_id": "mouse_001",
      "session_description": "Baseline recording session, animal habituated to task",
      "experimenter": "Jane Doe",
      "institution": "University of California, San Francisco",
      "lab": "Motor Control Lab"
    }
  }'
```

**Response**:

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "resumed_status": {
    "state": "converting",
    "resumed_from_step": "metadata_collection",
    "checkpoint_version": 2,
    "progress_percentage": 45.0
  }
}
```

---

## Step 5: Conversion to NWB

Conversion proceeds automatically. Monitor progress:

**Progress Updates** (via WebSocket):

```
Progress: 45% - Starting NWB file generation
Progress: 50% - Writing acquisition metadata
Progress: 60% - Processing electrode data (channel 1/384)
Progress: 70% - Processing electrode data (channel 200/384)
Progress: 80% - Processing LFP data
Progress: 90% - Finalizing NWB file structure
Progress: 92% - Conversion complete, starting validation
```

**HTTP Status Check**:

```bash
curl http://localhost:8000/api/v1/conversions/123e4567-e89b-12d3-a456-426614174000 | jq .state
# Output: "converting"
```

Conversion typically takes 2-10 minutes depending on dataset size.

---

## Step 6: Validation

Multiple validators run automatically:

1. **NWB Inspector**: Checks NWB standards compliance
2. **PyNWB**: Validates schema correctness
3. **DANDI**: Assesses repository readiness

**Progress Updates**:

```
Progress: 92% - Running NWB Inspector validation
Progress: 94% - NWB Inspector: 2 best practice suggestions found
Progress: 96% - Running PyNWB schema validation
Progress: 97% - PyNWB validation: PASSED
Progress: 98% - Running DANDI readiness checks
Progress: 99% - DANDI readiness score: 92/100
Progress: 100% - Workflow completed successfully!
```

---

## Step 7: Retrieve Results

### Via MCP Protocol

```
Claude: The conversion workflow completed successfully!

Results:
- Output File: /output/experiment_001.nwb
- File Size: 512.7 MB
- Validation Status: PASS
- Quality Score: 87.5/100
- DANDI Readiness: 92/100

Validation Details:
- Critical Issues: 0
- Warnings: 3
  1. Missing subject date of birth (optional field)
  2. Electrode impedances not recorded (best practice)
  3. Session start time timezone not specified (best practice)

The NWB file is ready for sharing!
```

### Via HTTP REST API

```bash
# Get final status
curl http://localhost:8000/api/v1/conversions/123e4567-e89b-12d3-a456-426614174000 | jq
```

**Response**:

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "state": "completed",
  "progress_percentage": 100.0,
  "created_at": "2025-10-10T10:00:00Z",
  "updated_at": "2025-10-10T10:15:45Z",
  "completed_at": "2025-10-10T10:15:45Z",
  "format_detection": {
    "primary_format": "SpikeGLX",
    "confidence": 0.95
  },
  "validation_summary": {
    "overall_status": "PASS",
    "quality_score": 87.5,
    "critical_issues": 0,
    "warnings": 3,
    "dandi_readiness_score": 92.0
  }
}
```

### Download Validation Report

```bash
# Get detailed validation report (if available via separate endpoint)
curl http://localhost:8000/api/v1/conversions/123e4567-e89b-12d3-a456-426614174000/report \
  -H "Accept: application/json" > validation_report.json

# Or as HTML
curl http://localhost:8000/api/v1/conversions/123e4567-e89b-12d3-a456-426614174000/report \
  -H "Accept: text/html" > validation_report.html
```

---

## Step 8: Retrieve Provenance

Get complete PROV-O provenance graph:

### JSON Format

```bash
curl http://localhost:8000/api/v1/conversions/123e4567-e89b-12d3-a456-426614174000/provenance?format=json | jq
```

**Response**:

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "format": "json",
  "provenance": {
    "entities": [
      {
        "entity_id": "dataset_experiment_001",
        "entity_type": "Dataset",
        "attributes": {
          "path": "/path/to/data/quickstart/experiment_001",
          "size_bytes": 524288000,
          "checksum": "e3b0c44..."
        }
      },
      {
        "entity_id": "nwb_experiment_001",
        "entity_type": "NWBFile",
        "attributes": {
          "path": "/output/experiment_001.nwb",
          "size_bytes": 537919488,
          "nwb_version": "2.6.0"
        }
      }
    ],
    "activities": [
      {
        "activity_id": "format_detection_001",
        "activity_type": "FormatDetection",
        "started_at": "2025-10-10T10:00:15Z",
        "ended_at": "2025-10-10T10:01:45Z",
        "duration_seconds": 90.0
      },
      {
        "activity_id": "conversion_001",
        "activity_type": "Conversion",
        "started_at": "2025-10-10T10:05:00Z",
        "ended_at": "2025-10-10T10:13:00Z",
        "duration_seconds": 480.0
      }
    ],
    "agents": [
      {
        "agent_id": "conversation_agent",
        "agent_type": "ConversationAgent",
        "version": "1.0.0"
      },
      {
        "agent_id": "conversion_agent",
        "agent_type": "ConversionAgent",
        "version": "1.0.0"
      }
    ],
    "relationships": [
      {
        "relationship_type": "used",
        "subject": "format_detection_001",
        "object": "dataset_experiment_001"
      },
      {
        "relationship_type": "wasGeneratedBy",
        "subject": "nwb_experiment_001",
        "object": "conversion_001"
      }
    ]
  }
}
```

### RDF Turtle Format

```bash
curl http://localhost:8000/api/v1/conversions/123e4567-e89b-12d3-a456-426614174000/provenance?format=turtle > provenance.ttl
```

**Output** (`provenance.ttl`):

```turtle
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix mcp: <http://mcp-server/provenance/> .

mcp:dataset_experiment_001 a mcp:Dataset ;
    mcp:datasetPath "/path/to/data/quickstart/experiment_001" ;
    prov:generatedAtTime "2025-10-10T09:00:00Z"^^xsd:dateTime .

mcp:format_detection_001 a mcp:FormatDetection ;
    prov:used mcp:dataset_experiment_001 ;
    prov:startedAtTime "2025-10-10T10:00:15Z"^^xsd:dateTime ;
    prov:endedAtTime "2025-10-10T10:01:45Z"^^xsd:dateTime .

mcp:nwb_experiment_001 a mcp:NWBFile ;
    prov:wasGeneratedBy mcp:conversion_001 ;
    prov:wasDerivedFrom mcp:dataset_experiment_001 .
```

---

## Step 9: Inspect NWB File

Verify the generated NWB file:

### Using PyNWB

```python
from pynwb import NWBHDF5IO

# Open NWB file
with NWBHDF5IO('/output/experiment_001.nwb', 'r') as io:
    nwbfile = io.read()

    # Print basic info
    print(f"Session: {nwbfile.session_description}")
    print(f"Experimenter: {nwbfile.experimenter}")
    print(f"Subject: {nwbfile.subject.subject_id}")
    print(f"Species: {nwbfile.subject.species}")

    # Print acquisition data
    print(f"\nAcquisition data:")
    for name, data in nwbfile.acquisition.items():
        print(f"  - {name}: {data}")

    # Print electrode info
    print(f"\nElectrodes: {len(nwbfile.electrodes)} channels")
```

**Output**:

```
Session: Baseline recording session, animal habituated to task
Experimenter: ['Jane Doe']
Subject: mouse_001
Species: Mus musculus

Acquisition data:
  - ElectricalSeries: ElectricalSeries (384 channels, 30000 Hz)

Electrodes: 384 channels
```

### Using NWB Inspector (CLI)

```bash
# Run NWB Inspector validation
nwbinspector /output/experiment_001.nwb --report-file-path inspector_report.txt

# View report
cat inspector_report.txt
```

**Output**:

```
NWB Inspector Report
====================

File: /output/experiment_001.nwb
NWB Version: 2.6.0

Summary:
- CRITICAL issues: 0
- BEST_PRACTICE_VIOLATION: 0
- BEST_PRACTICE_SUGGESTION: 2

Issues:
1. [BEST_PRACTICE_SUGGESTION] Subject.date_of_birth is not set (optional)
2. [BEST_PRACTICE_SUGGESTION] Electrode impedances are not recorded

Overall: PASSED with suggestions
```

---

## Step 10: Upload to DANDI Archive (Optional)

If DANDI readiness score is high (>85), upload to DANDI:

```bash
# Install DANDI CLI
pip install dandi

# Organize file in DANDI format
dandi organize /output/experiment_001.nwb -f dry

# Validate with DANDI
dandi validate /output/experiment_001.nwb

# Upload to DANDI (requires DANDI account)
dandi upload /output/experiment_001.nwb --dandiset-id 000123
```

---

## Complete Example Script

Here's a complete Python script automating the entire workflow:

```python
#!/usr/bin/env python3
"""
Automated NWB Conversion Workflow
Usage: python quickstart_example.py /path/to/dataset
"""

import sys
import time
import requests
from pathlib import Path

API_BASE = "http://localhost:8000/api/v1"

def convert_dataset(dataset_path: str):
    """Submit dataset for conversion and monitor progress"""

    # Step 1: Submit conversion
    print(f"📦 Submitting dataset: {dataset_path}")
    response = requests.post(
        f"{API_BASE}/conversions",
        json={"dataset_path": dataset_path}
    )
    response.raise_for_status()

    session_id = response.json()["session_id"]
    print(f"✅ Session created: {session_id}")

    # Step 2: Poll for completion
    while True:
        status_response = requests.get(f"{API_BASE}/conversions/{session_id}")
        status = status_response.json()

        state = status["state"]
        progress = status["progress_percentage"]

        print(f"🔄 {state.upper()}: {progress:.1f}%")

        # Handle interactive metadata collection
        if state == "suspended":
            print("⏸️  Workflow suspended - needs user input")
            metadata = collect_user_metadata()
            requests.post(
                f"{API_BASE}/conversions/{session_id}/resume",
                json={"user_inputs": metadata}
            )
            print("✅ Metadata provided, resuming...")

        # Check completion
        if state in ["completed", "failed", "cancelled"]:
            break

        time.sleep(5)

    # Step 3: Report results
    if state == "completed":
        print("\n🎉 Conversion completed successfully!")
        validation = status.get("validation_summary", {})
        print(f"   Quality Score: {validation.get('quality_score', 'N/A')}/100")
        print(f"   DANDI Readiness: {validation.get('dandi_readiness_score', 'N/A')}/100")
        print(f"   Critical Issues: {validation.get('critical_issues', 'N/A')}")

        # Get provenance
        prov_response = requests.get(
            f"{API_BASE}/conversions/{session_id}/provenance",
            params={"format": "json"}
        )
        provenance = prov_response.json()["provenance"]
        print(f"\n📊 Provenance recorded: {len(provenance['activities'])} activities")

        return True
    else:
        print(f"\n❌ Conversion failed: {status.get('error', {}).get('message')}")
        return False

def collect_user_metadata():
    """Interactive metadata collection"""
    return {
        "experiment_description": input("Experiment description: "),
        "subject_species": input("Subject species (e.g., Mus musculus): "),
        "subject_id": input("Subject ID: "),
        "experimenter": input("Experimenter name: "),
        "institution": input("Institution: ")
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quickstart_example.py /path/to/dataset")
        sys.exit(1)

    dataset_path = sys.argv[1]
    success = convert_dataset(dataset_path)
    sys.exit(0 if success else 1)
```

**Run the script**:

```bash
python quickstart_example.py /path/to/data/quickstart/experiment_001
```

---

## Expected Timeline

For the sample SpikeGLX dataset (~500MB):

| Phase               | Duration        | Description                                |
| ------------------- | --------------- | ------------------------------------------ |
| Format Detection    | ~30 seconds     | Analyze file structure, detect SpikeGLX    |
| Metadata Collection | ~2 minutes      | Interactive prompts for missing metadata   |
| Conversion          | ~5 minutes      | Generate NWB file with all data            |
| Validation          | ~2 minutes      | Run NWB Inspector, PyNWB, DANDI validators |
| **Total**           | **~10 minutes** | End-to-end workflow                        |

---

## Troubleshooting

### Issue: Format detection fails

```
Error: Unable to determine format with sufficient confidence
```

**Solution**: Override format manually:

```json
{
  "dataset_path": "/path/to/dataset",
  "workflow_config": {
    "format_override": "SpikeGLX"
  }
}
```

---

### Issue: Validation warnings

```
Warning: Missing subject.date_of_birth
```

**Solution**: Warnings don't block conversion. To fix, provide additional
metadata:

```python
# Resume with additional metadata
requests.post(
    f"{API_BASE}/conversions/{session_id}/resume",
    json={"user_inputs": {"subject_date_of_birth": "2024-01-15"}}
)
```

---

### Issue: Conversion timeout

```
Error: Workflow exceeded timeout of 1800 seconds
```

**Solution**: Increase timeout for large datasets:

```json
{
  "dataset_path": "/path/to/large/dataset",
  "workflow_config": {
    "timeout_seconds": 3600
  }
}
```

---

## Next Steps

1. **Explore Advanced Features**:
   - Custom validators (see Plugin Architecture docs)
   - Batch processing (submit multiple datasets)
   - Workflow customization (modify DAG)

2. **Integration**:
   - Integrate MCP server with Claude Desktop
   - Build custom clients using HTTP API
   - Set up continuous conversion pipelines

3. **Production Deployment**:
   - Deploy with Docker/Kubernetes
   - Configure Redis for session storage
   - Set up OpenTelemetry for monitoring

---

## Validation Checklist

After completing this quickstart, verify:

- [ ] MCP server starts without errors
- [ ] HTTP server accessible at http://localhost:8000
- [ ] Dataset conversion completes successfully
- [ ] NWB file generated in `/output/` directory
- [ ] Validation passes with quality score >80
- [ ] Provenance graph available in JSON/Turtle formats
- [ ] NWB file opens correctly with PyNWB
- [ ] No critical validation errors

---

**Quickstart Complete!** 🎉

You've successfully:

1. ✅ Installed the MCP server
2. ✅ Started both MCP and HTTP transports
3. ✅ Submitted a dataset for conversion
4. ✅ Monitored real-time progress
5. ✅ Provided interactive metadata
6. ✅ Validated the generated NWB file
7. ✅ Retrieved complete provenance records

**Next**: Explore the full API documentation at http://localhost:8000/docs or
review the specification at `specs/mcp-server-architecture-new/spec.md`.
