# Multi-Agent NWB Conversion Pipeline - Information Flow

This document provides a comprehensive overview of how information flows through the entire multi-agent pipeline, what files are involved at each step, and how data is transformed from input to output.

---

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Complete Information Flow](#complete-information-flow)
3. [File-by-File Breakdown](#file-by-file-breakdown)
4. [Data Structures](#data-structures)
5. [Storage Mechanisms](#storage-mechanisms)
6. [Running the Demo](#running-the-demo)

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User/Client                                 │
│                     (HTTP REST API Calls)                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Server                                   │
│  Files: agentic_neurodata_conversion/mcp_server/                    │
│    - main.py (FastAPI app)                                           │
│    - api/sessions.py (REST endpoints)                                │
│    - api/internal.py (agent communication)                           │
│    - message_router.py (routes messages between agents)              │
│    - context_manager.py (session persistence)                        │
│    - agent_registry.py (tracks available agents)                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Conversation │  │  Conversion  │  │  Evaluation  │
    │    Agent     │  │    Agent     │  │    Agent     │
    └──────────────┘  └──────────────┘  └──────────────┘
         │                  │                  │
         │                  │                  │
    ┌────▼──────────────────▼──────────────────▼────┐
    │           Session Context Storage              │
    │   (Redis Primary + Filesystem Backup)          │
    │   Files: ./sessions/{session_id}.json          │
    └────────────────────────────────────────────────┘
```

---

## Complete Information Flow

### Phase 0: System Initialization

**Files Involved:**
- `agentic_neurodata_conversion/mcp_server/main.py`
- `agentic_neurodata_conversion/config.py`
- `agentic_neurodata_conversion/agents/conversation_agent.py`
- `agentic_neurodata_conversion/agents/conversion_agent.py`
- `agentic_neurodata_conversion/agents/evaluation_agent.py`

**Information Flow:**
1. **MCP Server starts** → Loads configuration from environment variables
2. **Context Manager initializes** → Connects to Redis (localhost:6379)
3. **Agents register** → Each agent registers capabilities with agent_registry
4. **Server ready** → Listening on configured port (default: 8000)

**Data Created:**
- Redis connection pool
- Agent registry mapping: `{"conversation_agent": ["extract_metadata"], ...}`

---

### Phase 1: Session Initialization (User Request)

**API Endpoint:** `POST /api/v1/sessions/initialize`

**Request Body:**
```json
{
  "dataset_path": "/path/to/openephys/data"
}
```

**Files Involved:**
- `agentic_neurodata_conversion/mcp_server/api/sessions.py` (endpoint)
- `agentic_neurodata_conversion/mcp_server/context_manager.py` (create session)
- `agentic_neurodata_conversion/models/session_context.py` (data model)

**Information Flow:**
1. **API receives request** → Validates dataset_path
2. **Generate session_id** → UUID like `session-123e4567-e89b-12d3-a456-426614174000`
3. **Create SessionContext** →
   ```python
   SessionContext(
       session_id=session_id,
       workflow_stage=WorkflowStage.INITIALIZED,
       created_at=datetime.utcnow(),
       last_updated=datetime.utcnow(),
       dataset_info=None,  # Will be populated by Conversation Agent
       metadata=None,      # Will be populated by Conversation Agent
       conversion_results=None,  # Will be populated by Conversion Agent
       validation_results=None,  # Will be populated by Evaluation Agent
   )
   ```
4. **Store in Redis** → Key: `session:{session_id}`, Value: JSON serialized SessionContext
5. **Store in Filesystem** → File: `./sessions/sessions/{session_id}.json`
6. **Create MCP Message** → Route to Conversation Agent
7. **Send to Message Router** → `POST /internal/route_message`

**Data Created:**
- Session context in Redis
- Session context file on disk
- MCP message for agent routing

**Response:**
```json
{
  "session_id": "session-123...",
  "workflow_stage": "initialized",
  "message": "Session initialized"
}
```

---

### Phase 2: Conversation Agent (Metadata Extraction)

**Files Involved:**
- `agentic_neurodata_conversion/agents/conversation_agent.py`
- `agentic_neurodata_conversion/agents/base_agent.py` (parent class)
- `agentic_neurodata_conversion/models/mcp_message.py`
- `agentic_neurodata_conversion/models/session_context.py`

**Information Flow:**

#### Step 2.1: Receive MCP Message
```python
message = MCPMessage(
    message_id="msg-001",
    session_id="session-123...",
    source_agent="mcp_server",
    target_agent="conversation_agent",
    payload={
        "action": "initialize_session",
        "dataset_path": "/path/to/data"
    }
)
```

**Method Called:** `conversation_agent.handle_message(message)`

#### Step 2.2: Format Detection
**Method:** `conversation_agent._detect_format(dataset_path)`

**What it does:**
1. Scans directory structure
2. Looks for `.continuous` files → Indicates OpenEphys format
3. Checks for `settings.xml` file

**Files Read:**
- `/path/to/data/*.continuous` (presence check)
- `/path/to/data/settings.xml` (presence check)

**Data Created:**
```python
format_result = {
    "format": "openephys",
    "confidence": "high"
}
```

#### Step 2.3: Dataset Validation
**Method:** `conversation_agent._validate_dataset_structure(dataset_path, format)`

**What it does:**
1. Verifies required files exist
2. Counts `.continuous` files (channels)
3. Parses `settings.xml` for sampling rate
4. Calculates total size

**Files Read:**
- All `.continuous` files in directory
- `settings.xml` file

**Data Created:**
```python
DatasetInfo(
    dataset_path="/path/to/data",
    format="openephys",
    total_size_bytes=123456789,
    file_count=10,
    channel_count=8,
    sampling_rate_hz=30000.0,
    duration_seconds=60.0,
    has_metadata_files=True,
    metadata_files=["README.md", "experiment_notes.md"]
)
```

#### Step 2.4: Metadata Extraction (LLM-Powered)
**Method:** `conversation_agent._extract_metadata_from_files(dataset_path)`

**What it does:**
1. Finds `.md` files in dataset directory
2. Reads content of each `.md` file
3. Creates LLM prompt requesting structured metadata extraction
4. Calls LLM API (Anthropic Claude or OpenAI GPT-4)
5. Parses LLM response into structured MetadataExtractionResult

**Files Read:**
- `/path/to/data/README.md`
- `/path/to/data/experiment_notes.md`
- Any other `.md` files

**LLM Prompt Example:**
```
Extract metadata from this neuroscience dataset description:

[FILE CONTENT]

Extract the following fields if present:
- subject_id: Identifier for the subject
- species: Species (e.g., mouse, rat, human)
- age: Age of subject
- sex: Sex of subject (M/F/Unknown)
- session_start_time: ISO format datetime
- experimenter: Name of experimenter
- device_name: Recording device name
- manufacturer: Device manufacturer
- recording_location: Brain region or location
- description: Brief session description

Return as JSON with confidence scores.
```

**Data Created:**
```python
MetadataExtractionResult(
    subject_id="mouse_001",
    species="Mus musculus",
    age="P60",
    sex="M",
    session_start_time="2025-01-15T14:30:00",
    experimenter="Dr. Smith",
    device_name="OpenEphys Acquisition Board",
    manufacturer="OpenEphys",
    recording_location="CA1",
    description="Hippocampal recording during spatial navigation",
    extraction_confidence={
        "subject_id": "high",
        "species": "high",
        "age": "medium",
        ...
    },
    llm_extraction_log="Extracted from README.md and experiment_notes.md"
)
```

#### Step 2.5: Update Session Context
**Method:** `conversation_agent.update_session_context(session_id, updates)`

**What it does:**
1. Retrieves current session from Redis/filesystem
2. Updates `dataset_info` field
3. Updates `metadata` field
4. Updates `workflow_stage` to `COLLECTING_METADATA`
5. Updates `last_updated` timestamp
6. Saves back to Redis (with TTL)
7. Saves back to filesystem

**Session Context After Update:**
```json
{
  "session_id": "session-123...",
  "workflow_stage": "collecting_metadata",
  "created_at": "2025-10-17T10:00:00.000Z",
  "last_updated": "2025-10-17T10:00:02.500Z",
  "current_agent": "conversation_agent",
  "dataset_info": {
    "dataset_path": "/path/to/data",
    "format": "openephys",
    "total_size_bytes": 123456789,
    "file_count": 10,
    "channel_count": 8,
    "sampling_rate_hz": 30000.0,
    "duration_seconds": 60.0,
    "has_metadata_files": true,
    "metadata_files": ["README.md", "experiment_notes.md"]
  },
  "metadata": {
    "subject_id": "mouse_001",
    "species": "Mus musculus",
    "age": "P60",
    "sex": "M",
    "session_start_time": "2025-01-15T14:30:00",
    "experimenter": "Dr. Smith",
    "device_name": "OpenEphys Acquisition Board",
    "manufacturer": "OpenEphys",
    "recording_location": "CA1",
    "description": "Hippocampal recording during spatial navigation"
  }
}
```

#### Step 2.6: Agent Handoff to Conversion Agent
**Method:** `conversation_agent._trigger_conversion(session_id)`

**What it does:**
1. Creates new MCP message for Conversion Agent
2. Sends via MCP server `/internal/route_message` endpoint
3. Returns success to caller

**MCP Message Created:**
```python
MCPMessage(
    message_id="msg-002",
    session_id="session-123...",
    source_agent="conversation_agent",
    target_agent="conversion_agent",
    payload={
        "action": "convert_dataset"
    }
)
```

**HTTP Request:**
```
POST http://localhost:8000/internal/route_message
Content-Type: application/json

{
  "message": {
    "message_id": "msg-002",
    "session_id": "session-123...",
    "source_agent": "conversation_agent",
    "target_agent": "conversion_agent",
    "payload": {
      "action": "convert_dataset"
    }
  }
}
```

---

### Phase 3: Conversion Agent (NWB Generation)

**Files Involved:**
- `agentic_neurodata_conversion/agents/conversion_agent.py`
- External library: `neuroconv` (OpenEphysRecordingInterface)
- External library: `pynwb` (NWB file format)

**Information Flow:**

#### Step 3.1: Receive MCP Message & Get Session Context
**Method:** `conversion_agent.handle_message(message)`

**What it does:**
1. Extracts session_id from message
2. Calls `self.get_session_context(session_id)`
3. Retrieves SessionContext from Redis/filesystem
4. Validates that `dataset_info` and `metadata` are present

**Data Retrieved:**
- Complete SessionContext from Phase 2
- dataset_path from `session.dataset_info.dataset_path`
- metadata from `session.metadata`

#### Step 3.2: Update Workflow Stage
**What it does:**
1. Updates `workflow_stage` to `CONVERTING`
2. Updates `current_agent` to `conversion_agent`
3. Saves to Redis + filesystem

#### Step 3.3: Prepare NWB Metadata
**Method:** `conversion_agent._prepare_metadata(session_metadata)`

**What it does:**
Maps session metadata to NWB format requirements:

```python
# NWB requires specific structure
nwb_metadata = {
    "NWBFile": {
        "session_description": metadata.description or "OpenEphys recording session",
        "identifier": session_id,
        "session_start_time": metadata.session_start_time or datetime.utcnow(),
        "experimenter": [metadata.experimenter] if metadata.experimenter else ["Unknown"],
        "lab": "Unknown",
        "institution": "Unknown"
    },
    "Subject": {
        "subject_id": metadata.subject_id or "unknown",
        "species": metadata.species or "unknown",
        "age": metadata.age or "unknown",
        "sex": metadata.sex or "U",
        "description": metadata.description or ""
    },
    "Ecephys": {
        "Device": [{
            "name": metadata.device_name or "OpenEphys",
            "description": "OpenEphys recording device",
            "manufacturer": metadata.manufacturer or "OpenEphys"
        }]
    }
}
```

**Data Created:**
- NWB-compliant metadata dictionary

#### Step 3.4: Convert to NWB using NeuroConv
**Method:** `conversion_agent._convert_to_nwb(session_id, dataset_path, metadata)`

**What it does:**
1. Creates output directory: `./output/nwb_files/`
2. Generates NWB file path: `./output/nwb_files/{session_id}.nwb`
3. Instantiates NeuroConv interface:
   ```python
   from neuroconv.datainterfaces import OpenEphysRecordingInterface

   interface = OpenEphysRecordingInterface(folder_path=dataset_path)
   ```
4. Applies metadata to interface:
   ```python
   interface.add_to_nwbfile(nwbfile, metadata)
   ```
5. Runs conversion with gzip compression:
   ```python
   interface.run_conversion(
       nwbfile_path=nwb_file_path,
       metadata=nwb_metadata,
       overwrite=True,
       compression="gzip"
   )
   ```
6. Tracks conversion duration (start time → end time)

**Files Read:**
- All `.continuous` files in dataset
- `settings.xml` for recording parameters

**Files Written:**
- `./output/nwb_files/{session_id}.nwb` (HDF5 format with gzip compression)

**File Structure of NWB:**
```
{session_id}.nwb (HDF5 file)
├── /general
│   ├── /subject (subject metadata)
│   ├── /devices (recording device info)
│   └── session_start_time
├── /acquisition
│   └── /ElectricalSeries (raw electrophysiology data)
│       ├── data (compressed timeseries)
│       ├── electrodes (channel information)
│       └── timestamps
└── /processing (empty for raw data)
```

**Data Created:**
```python
ConversionResults(
    nwb_file_path="/absolute/path/to/output/nwb_files/session-123.nwb",
    conversion_duration_seconds=15.7,
    conversion_warnings=[],
    conversion_errors=[],
    conversion_log="Conversion completed successfully"
)
```

#### Step 3.5: Update Session Context
**What it does:**
1. Updates `conversion_results` field
2. Updates `workflow_stage` to `CONVERTING` (still in progress)
3. Saves to Redis + filesystem

**Session Context After Update:**
```json
{
  "session_id": "session-123...",
  "workflow_stage": "converting",
  "conversion_results": {
    "nwb_file_path": "/path/to/output/nwb_files/session-123.nwb",
    "conversion_duration_seconds": 15.7,
    "conversion_warnings": [],
    "conversion_errors": [],
    "conversion_log": "Conversion completed successfully"
  }
}
```

#### Step 3.6: Agent Handoff to Evaluation Agent
**Method:** Similar to Step 2.6

**MCP Message Created:**
```python
MCPMessage(
    message_id="msg-003",
    session_id="session-123...",
    source_agent="conversion_agent",
    target_agent="evaluation_agent",
    payload={
        "action": "validate_nwb"
    }
)
```

---

### Phase 4: Evaluation Agent (NWB Validation)

**Files Involved:**
- `agentic_neurodata_conversion/agents/evaluation_agent.py`
- External library: `nwbinspector` (validation tool)

**Information Flow:**

#### Step 4.1: Receive MCP Message & Get Session Context
**Method:** `evaluation_agent.handle_message(message)`

**What it does:**
1. Gets session context
2. Extracts NWB file path from `session.conversion_results.nwb_file_path`
3. Updates `workflow_stage` to `EVALUATING`

#### Step 4.2: Validate NWB File with NWB Inspector
**Method:** `evaluation_agent._validate_nwb(nwb_file_path)`

**What it does:**
1. Runs NWB Inspector validation:
   ```python
   from nwbinspector import inspect_nwbfile

   issues = list(inspect_nwbfile(nwbfile_path=nwb_file_path))
   ```
2. Collects all validation issues
3. Categorizes by severity:
   - CRITICAL: Must be fixed before data can be used
   - BEST_PRACTICE_VIOLATION: Should be fixed for DANDI compliance
   - BEST_PRACTICE_SUGGESTION: Nice to have improvements
4. Counts issues by severity
5. Determines overall status:
   - "failed" if any CRITICAL issues
   - "passed_with_warnings" if only non-critical issues
   - "passed" if no issues

**Files Read:**
- `./output/nwb_files/{session_id}.nwb` (full validation scan)

**Data Created:**
```python
overall_status = "passed_with_warnings"
issue_count = {
    "CRITICAL": 0,
    "BEST_PRACTICE_VIOLATION": 2,
    "BEST_PRACTICE_SUGGESTION": 5
}
issues = [
    ValidationIssue(
        severity="BEST_PRACTICE_VIOLATION",
        message="Subject age should follow ISO 8601 duration format",
        location="/general/subject/age",
        check_name="check_subject_age_format"
    ),
    ValidationIssue(
        severity="BEST_PRACTICE_SUGGESTION",
        message="Consider adding keywords for better searchability",
        location="/general/keywords",
        check_name="check_keywords_present"
    ),
    ...
]
```

#### Step 4.3: Calculate Quality Scores
**Methods:**
- `evaluation_agent._calculate_metadata_score(metadata)`
- `evaluation_agent._calculate_best_practices_score(issue_count)`

**Metadata Score Calculation:**
```python
# Check 5 critical fields
critical_fields = [
    "subject_id",
    "species",
    "session_start_time",
    "session_description",
    "experimenter"
]

present_count = sum(1 for field in critical_fields if metadata.get(field))
metadata_score = (present_count / len(critical_fields)) * 100.0
# Example: 4/5 fields present = 80.0
```

**Best Practices Score Calculation:**
```python
score = 100.0
score -= issue_count.get("CRITICAL", 0) * 15  # -15 per critical
score -= issue_count.get("BEST_PRACTICE_VIOLATION", 0) * 5  # -5 per violation
score -= issue_count.get("BEST_PRACTICE_SUGGESTION", 0) * 2  # -2 per suggestion
score = max(0.0, score)
# Example: 0 critical, 2 violations, 5 suggestions = 100 - 0 - 10 - 10 = 80.0
```

#### Step 4.4: Generate Validation Report (JSON)
**Method:** `evaluation_agent._generate_report(...)`

**What it does:**
1. Creates `./reports/` directory
2. Generates filename: `./reports/{session_id}_validation.json`
3. Writes JSON with complete validation results

**Files Written:**
- `./reports/{session_id}_validation.json`

**File Content:**
```json
{
  "session_id": "session-123...",
  "overall_status": "passed_with_warnings",
  "issue_count": {
    "CRITICAL": 0,
    "BEST_PRACTICE_VIOLATION": 2,
    "BEST_PRACTICE_SUGGESTION": 5
  },
  "issues": [
    {
      "severity": "BEST_PRACTICE_VIOLATION",
      "message": "Subject age should follow ISO 8601 duration format",
      "location": "/general/subject/age",
      "check_name": "check_subject_age_format"
    },
    ...
  ],
  "metadata_completeness_score": 80.0,
  "best_practices_score": 80.0,
  "generated_at": "2025-10-17T10:00:30.123Z"
}
```

#### Step 4.5: Generate LLM Validation Summary
**Method:** `evaluation_agent._generate_validation_summary(...)`

**What it does:**
1. Creates prompt with validation results (first 20 issues)
2. Calls LLM API requesting concise summary under 150 words
3. Requests:
   - Overall assessment
   - Critical issues highlighted
   - Actionable recommendations
   - File readiness indicator

**LLM Prompt Example:**
```
Generate a concise validation summary (under 150 words) for this NWB file validation.

Overall Status: passed_with_warnings

Issue Counts:
- Critical: 0
- Best Practice Violations: 2
- Best Practice Suggestions: 5

Issues:
- [BEST_PRACTICE_VIOLATION] Subject age should follow ISO 8601 duration format (at /general/subject/age)
- [BEST_PRACTICE_SUGGESTION] Consider adding keywords for better searchability (at /general/keywords)
...

Metadata: { ... }

Provide:
1. Overall assessment
2. Highlight critical issues (if any)
3. Actionable recommendations
4. Whether the file is ready for use

Keep it under 150 words and make it actionable.
```

**LLM Response:**
```
The NWB file passed validation with some warnings. No critical issues were found,
indicating the file is structurally sound and ready for use. However, there are
2 best practice violations and 5 suggestions to improve DANDI compliance.

Key recommendations:
1. Update subject age to ISO 8601 duration format (e.g., "P60D" for 60 days)
2. Add keywords to improve dataset searchability

The metadata is 80% complete with good coverage of essential fields. The file
can be used immediately for analysis, but addressing these recommendations will
improve compatibility with DANDI archive and enhance discoverability.

Overall: READY FOR USE with recommended improvements.
```

#### Step 4.6: Update Session Context (Final)
**What it does:**
1. Updates `validation_results` field
2. Updates `workflow_stage` to `COMPLETED`
3. Clears `current_agent` (workflow finished)
4. Saves to Redis + filesystem

**Final Session Context:**
```json
{
  "session_id": "session-123...",
  "workflow_stage": "completed",
  "created_at": "2025-10-17T10:00:00.000Z",
  "last_updated": "2025-10-17T10:00:35.789Z",
  "current_agent": null,
  "dataset_info": { ... },
  "metadata": { ... },
  "conversion_results": { ... },
  "validation_results": {
    "overall_status": "passed_with_warnings",
    "issue_count": {
      "CRITICAL": 0,
      "BEST_PRACTICE_VIOLATION": 2,
      "BEST_PRACTICE_SUGGESTION": 5
    },
    "issues": [ ... ],
    "metadata_completeness_score": 80.0,
    "best_practices_score": 80.0,
    "validation_report_path": "/path/to/reports/session-123_validation.json",
    "llm_validation_summary": "The NWB file passed validation..."
  },
  "requires_user_clarification": false,
  "clarification_prompt": null
}
```

---

### Phase 5: Result Retrieval (User Request)

**API Endpoint:** `GET /api/v1/sessions/{session_id}/result`

**Files Involved:**
- `agentic_neurodata_conversion/mcp_server/api/sessions.py`

**Information Flow:**
1. **API receives request** → Validates session_id
2. **Retrieve session context** → From Redis or filesystem
3. **Check workflow_stage** → Must be `COMPLETED`
4. **Extract result data**:
   - NWB file path
   - Validation report path
   - Overall validation status
   - LLM summary
   - Validation issues list
5. **Return response**

**Response:**
```json
{
  "session_id": "session-123...",
  "nwb_file_path": "/path/to/output/nwb_files/session-123.nwb",
  "validation_report_path": "/path/to/reports/session-123_validation.json",
  "overall_status": "passed_with_warnings",
  "llm_validation_summary": "The NWB file passed validation...",
  "validation_issues": [
    {
      "severity": "BEST_PRACTICE_VIOLATION",
      "message": "Subject age should follow ISO 8601 duration format",
      "location": "/general/subject/age",
      "check_name": "check_subject_age_format"
    },
    ...
  ]
}
```

---

## File-by-File Breakdown

### Configuration Files
1. **`pixi.toml`** - Project dependencies and environment
2. **`.env`** - Environment variables (API keys, ports)
3. **`pyproject.toml`** - Python project metadata

### Data Models (Define data structures used throughout)
1. **`models/session_context.py`**
   - `SessionContext`: Main session state container
   - `WorkflowStage`: Enum for pipeline stages
   - `DatasetInfo`: Dataset metadata
   - `MetadataExtractionResult`: Extracted metadata
   - `ConversionResults`: Conversion output info
   - `ValidationResults`: Validation output info
   - `ValidationIssue`: Single validation issue

2. **`models/mcp_message.py`**
   - `MCPMessage`: Inter-agent communication format

3. **`models/api_models.py`**
   - `SessionInitializeRequest`: API request models
   - `SessionInitializeResponse`: API response models
   - `SessionStatusResponse`
   - `SessionResultResponse`
   - `SessionClarifyRequest`

### MCP Server (Orchestration layer)
1. **`mcp_server/main.py`**
   - FastAPI application setup
   - Registers all API routers
   - Configures CORS, middleware
   - Starts uvicorn server

2. **`mcp_server/api/sessions.py`**
   - `POST /api/v1/sessions/initialize` → Start new conversion
   - `GET /api/v1/sessions/{id}/status` → Check progress
   - `GET /api/v1/sessions/{id}/result` → Get final results
   - `POST /api/v1/sessions/{id}/clarify` → Provide clarifications

3. **`mcp_server/api/internal.py`**
   - `POST /internal/route_message` → Route MCP messages to agents
   - `GET /internal/sessions/{id}/context` → Get session context
   - `PATCH /internal/sessions/{id}/context` → Update session context

4. **`mcp_server/api/health.py`**
   - `GET /health` → Server health check

5. **`mcp_server/context_manager.py`**
   - `create_session()` → Store new session (Redis + filesystem)
   - `get_session()` → Retrieve session (Redis with filesystem fallback)
   - `update_session()` → Update session (write-through both)
   - `delete_session()` → Remove session (both locations)

6. **`mcp_server/message_router.py`**
   - `route_message()` → Routes MCP messages to correct agent via HTTP

7. **`mcp_server/agent_registry.py`**
   - Tracks available agents and their capabilities
   - Used for routing decisions

### Agents (Data processing components)
1. **`agents/base_agent.py`**
   - Abstract base class for all agents
   - Common functionality:
     - `get_session_context()` → Retrieve session via API
     - `update_session_context()` → Update session via API
     - `call_llm()` → Call LLM (Anthropic/OpenAI)
     - `handle_message()` → Abstract method for message handling

2. **`agents/conversation_agent.py`**
   - `handle_message()` → Routes to initialization or clarification
   - `_detect_format()` → Identify dataset format
   - `_validate_dataset_structure()` → Check dataset validity
   - `_extract_metadata_from_files()` → LLM-powered metadata extraction
   - `_initialize_session()` → Complete initialization workflow
   - `_handle_clarification()` → Process user clarifications

3. **`agents/conversion_agent.py`**
   - `handle_message()` → Routes to conversion
   - `_prepare_metadata()` → Map metadata to NWB format
   - `_convert_to_nwb()` → NeuroConv integration
   - `_generate_error_message()` → LLM-powered error messages
   - `_convert_dataset()` → Complete conversion workflow

4. **`agents/evaluation_agent.py`**
   - `handle_message()` → Routes to validation
   - `_validate_nwb()` → NWB Inspector integration
   - `_calculate_metadata_score()` → Score metadata completeness
   - `_calculate_best_practices_score()` → Score based on issues
   - `_generate_report()` → Create JSON validation report
   - `_generate_validation_summary()` → LLM-powered summary
   - `_validate_nwb_full()` → Complete validation workflow

### Configuration
1. **`config.py`**
   - `get_server_config()` → MCP server configuration
   - `get_conversation_agent_config()` → Agent configuration
   - `get_conversion_agent_config()` → Agent configuration
   - `get_evaluation_agent_config()` → Agent configuration

---

## Data Structures

### SessionContext (The Heart of the System)

```python
SessionContext(
    session_id: str,              # Unique identifier
    workflow_stage: WorkflowStage, # Current pipeline stage
    created_at: datetime,         # Session creation time
    last_updated: datetime,       # Last modification time
    current_agent: Optional[str], # Agent currently processing
    agent_history: list[AgentHistoryEntry], # Agent execution log

    # Populated by Conversation Agent
    dataset_info: Optional[DatasetInfo],
    metadata: Optional[MetadataExtractionResult],

    # Populated by Conversion Agent
    conversion_results: Optional[ConversionResults],

    # Populated by Evaluation Agent
    validation_results: Optional[ValidationResults],

    # Error handling
    requires_user_clarification: bool,
    clarification_prompt: Optional[str],

    # Output paths
    output_nwb_path: Optional[str],
    output_report_path: Optional[str]
)
```

### MCPMessage (Inter-Agent Communication)

```python
MCPMessage(
    message_id: str,           # Unique message identifier
    session_id: str,           # Associated session
    source_agent: str,         # Sender agent name
    target_agent: str,         # Recipient agent name
    payload: dict[str, Any],   # Message content (flexible)
    timestamp: datetime,       # Message creation time
    correlation_id: Optional[str] # For request/response tracking
)
```

---

## Storage Mechanisms

### 1. Redis (Primary Storage)
- **Purpose**: Fast access, automatic TTL
- **Key Format**: `session:{session_id}`
- **Value**: JSON-serialized SessionContext
- **TTL**: 24 hours (configurable)
- **Connection**: localhost:6379/0

### 2. Filesystem (Backup Storage)
- **Purpose**: Persistence across Redis restarts
- **Path**: `./sessions/sessions/{session_id}.json`
- **Format**: Pretty-printed JSON
- **Write Strategy**: Write-through (every update goes to both)
- **Read Strategy**: Redis first, filesystem fallback

### 3. Output Files
- **NWB Files**: `./output/nwb_files/{session_id}.nwb`
- **Validation Reports**: `./reports/{session_id}_validation.json`
- **Format**: NWB = HDF5 with gzip compression, Reports = JSON

---

## Running the Demo

### Quick Start

```bash
# Run the demonstration script
pixi run python scripts/demo_full_pipeline.py
```

This will:
1. Initialize all components (MCP server, agents, context manager)
2. Create a demo session with synthetic OpenEphys data
3. Run through all three agents (Conversation → Conversion → Evaluation)
4. Show detailed logs of information flow at each step
5. Display final results and generated files

### Expected Output

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║        Multi-Agent NWB Conversion Pipeline - Full Demonstration              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Using dataset: ./tests/data/synthetic_openephys

================================================================================
PIPELINE INITIALIZATION
================================================================================

[10:00:00.123] ▶ Initializing Context Manager
  └─ Context Manager connected (Redis + Filesystem)
     Storage: Redis (primary) + ./demo_sessions/ (backup)

[10:00:00.234] ▶ Initializing Agents
  └─ ConversationAgent initialized
     Capabilities: ['initialize_session', 'handle_clarification']
  └─ ConversionAgent initialized
     Capabilities: ['convert_to_nwb']
  └─ EvaluationAgent initialized
     Capabilities: ['validate_nwb']

... [detailed logs for each phase] ...

================================================================================
FINAL RESULTS
================================================================================

[10:00:35.789] ▶ Workflow Summary
     Session ID: demo-20251017-100000
     Final Stage: completed
     Total Duration: 35.67s

[10:00:35.790] ▶ Generated Files
  └─ 1. Session Context
     Path: ./demo_sessions/sessions/demo-20251017-100000.json
     Size: 3.45 KB
  └─ 2. NWB File
     Path: ./output/nwb_files/demo-20251017-100000.nwb
     Size: 125.67 MB
  └─ 3. Validation Report
     Path: ./reports/demo-20251017-100000_validation.json
     Size: 12.34 KB

[10:00:35.791] ▶ Information Flow Summary
     1. User Request → MCP Server
     2. MCP Server → Conversation Agent (metadata extraction)
     3. Conversation Agent → Session Context (dataset_info, metadata)
     4. Conversation Agent → Conversion Agent (handoff)
     5. Conversion Agent → Session Context (conversion_results)
     6. Conversion Agent → Evaluation Agent (handoff)
     7. Evaluation Agent → Session Context (validation_results)
     8. Session Context → User (final results)

╔══════════════════════════════════════════════════════════════════════════════╗
║                        Demonstration Complete!                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Summary

The Multi-Agent NWB Conversion Pipeline is a sophisticated system that orchestrates three specialized agents to convert neuroscience datasets to the NWB format with comprehensive validation. Information flows through a well-defined sequence:

1. **User Request** → MCP Server API
2. **Session Created** → Redis + Filesystem
3. **Conversation Agent** → Metadata extraction (LLM-powered)
4. **Conversion Agent** → NWB generation (NeuroConv)
5. **Evaluation Agent** → Validation + scoring (NWB Inspector + LLM)
6. **Results Returned** → User via API

All communication between agents is mediated by the MCP server using the MCPMessage protocol, ensuring proper isolation and testability. Session state persists in both Redis (fast) and filesystem (durable), providing both performance and reliability.
