# Multi-Agent NWB Conversion Pipeline - Feature Specification

## Executive Summary

This specification defines a basic multi-agent system for converting heterogeneous neuroscience data into Neurodata Without Borders (NWB) format. The system uses the Model Context Protocol (MCP) as a communication layer between three specialized agents: Conversation Agent, Conversion Agent, and Evaluation Agent.

## System Overview

### Core Components

1. **MCP Server Layer**: Central orchestration and communication hub
2. **Conversation Agent**: User interaction and data preprocessing
3. **Conversion Agent**: NWB file generation using NeuroConv
4. **Evaluation Agent**: NWB validation using NWB Inspector

### Architecture Principles

- **MCP-Centric Communication**: All inter-agent communication flows through the MCP server
- **Context Persistence**: Each agent receives messages with persistent context files
- **Sequential Pipeline**: Conversation → Conversion → Evaluation workflow
- **Tool-Based Execution**: Agents use specific tools (NeuroConv, NWB Inspector) for their tasks

---

## User Stories

### Epic 1: MCP Server and Communication Protocol

#### Story 1.1: Initialize MCP Server
**As a** system administrator
**I want** to start an MCP server that can route messages between agents
**So that** agents can communicate without direct dependencies

**Acceptance Criteria:**
- [ ] MCP server starts on a configurable port (default: 8000)
- [ ] Server implements JSON-RPC 2.0 protocol for message passing
- [ ] Server maintains a registry of connected agents
- [ ] Server logs all message routing activities
- [ ] Server provides health check endpoint

**Technical Requirements:**
```python
# MCP Server Configuration
{
    "protocol_version": "1.0",
    "server_info": {
        "name": "nwb-conversion-pipeline",
        "version": "0.1.0",
        "capabilities": {
            "tools": true,
            "resources": true,
            "context_management": true
        }
    },
    "agents": [
        "conversation_agent",
        "conversion_agent",
        "evaluation_agent"
    ]
}
```

#### Story 1.2: Implement Message Routing
**As an** MCP server
**I want** to route messages to specific agents based on target specification
**So that** agents can communicate through a central hub

**Acceptance Criteria:**
- [ ] Messages contain `target_agent` field specifying recipient
- [ ] Server validates agent existence before routing
- [ ] Server attaches context files to each message
- [ ] Server handles message delivery failures gracefully
- [ ] Server supports broadcast messages to multiple agents

**Message Format:**
```json
{
    "jsonrpc": "2.0",
    "id": "unique-request-id",
    "method": "agent/execute",
    "params": {
        "target_agent": "conversion_agent",
        "source_agent": "conversation_agent",
        "session_id": "session-uuid",
        "context": {
            "session_state": {},
            "shared_data": {},
            "metadata": {}
        },
        "payload": {
            "action": "convert_dataset",
            "data": {}
        }
    }
}
```

#### Story 1.3: Context File Management
**As an** MCP server
**I want** to maintain and attach context files to agent messages
**So that** agents have access to session state and shared data

**Acceptance Criteria:**
- [ ] Server creates context file on session initialization
- [ ] Context file includes session_id, timestamp, agent_history
- [ ] Context file tracks data_path, metadata, and processing_state
- [ ] Context file is updated after each agent completes its task
- [ ] Context files are persisted to disk for recovery

**Context File Structure:**
```json
{
    "session_id": "uuid",
    "created_at": "2024-01-01T00:00:00Z",
    "last_updated": "2024-01-01T00:10:00Z",
    "current_agent": "conversion_agent",
    "agent_history": [
        {
            "agent": "conversation_agent",
            "started_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T00:05:00Z",
            "status": "success"
        }
    ],
    "data": {
        "input_path": "/path/to/data",
        "data_format": "blackrock",
        "output_path": "/path/to/output",
        "metadata": {},
        "preprocessing_results": {},
        "conversion_results": {},
        "validation_results": {}
    }
}
```

---

### Epic 2: Conversation Agent

#### Story 2.1: Initialize Conversation Session
**As a** user
**I want** to start a conversation with the system
**So that** I can provide information about my dataset

**Acceptance Criteria:**
- [ ] Agent creates a new session with unique ID
- [ ] Agent prompts user for dataset path
- [ ] Agent detects data format automatically or asks user
- [ ] Agent validates that dataset path exists and is accessible
- [ ] Agent initializes context file with session information

**User Interaction Flow:**
```
System: Welcome to the NWB Conversion Pipeline. Please provide the path to your dataset.
User: /data/recordings/session_001/
System: Detected format: Blackrock (.nev, .ns5). Is this correct? [Y/n]
User: Y
System: Analyzing dataset structure...
```

#### Story 2.2: Collect Required Metadata
**As a** conversation agent
**I want** to gather required metadata from the user
**So that** the conversion agent has necessary information

**Acceptance Criteria:**
- [ ] Agent identifies missing required fields for NWB conversion
- [ ] Agent prompts user for each missing field interactively
- [ ] Agent validates metadata format (e.g., ISO 8601 dates)
- [ ] Agent provides helpful examples for each field
- [ ] Agent stores collected metadata in context file

**Required Metadata Fields:**
- **Subject Information**: subject_id, species, age, sex
- **Experiment Information**: session_id, session_start_time, experimenter
- **Device Information**: device_name, manufacturer, recording_location
- **Dataset Description**: description, keywords

**Example Interaction:**
```
System: I need some information about the subject. What is the subject ID?
User: mouse_01
System: What is the species? (e.g., Mus musculus)
User: Mus musculus
System: What is the subject's age? (Format: P90D for 90 days)
User: P90D
```

#### Story 2.3: Preprocess and Validate Data
**As a** conversation agent
**I want** to perform basic data validation and preprocessing
**So that** conversion agent receives clean, validated data

**Acceptance Criteria:**
- [ ] Agent checks file integrity (no corruption)
- [ ] Agent verifies file format compatibility with NeuroConv
- [ ] Agent extracts basic information (file size, channel count, sampling rate)
- [ ] Agent identifies potential issues (missing files, incomplete recordings)
- [ ] Agent updates context with preprocessing results

**Preprocessing Checks:**
```python
preprocessing_results = {
    "file_integrity": "valid",
    "format_supported": true,
    "dataset_info": {
        "total_size_bytes": 1073741824,
        "file_count": 12,
        "channel_count": 96,
        "sampling_rate": 30000.0,
        "duration_seconds": 3600.0
    },
    "issues": [],
    "warnings": [
        "Large file size may require significant memory"
    ]
}
```

#### Story 2.4: Hand Off to Conversion Agent
**As a** conversation agent
**I want** to send collected information to the conversion agent
**So that** NWB file generation can begin

**Acceptance Criteria:**
- [ ] Agent updates context with "ready_for_conversion" status
- [ ] Agent sends message to MCP server targeting conversion_agent
- [ ] Message includes complete metadata and data path
- [ ] Agent confirms handoff to user
- [ ] Agent transitions to monitoring state

**Handoff Message:**
```json
{
    "target_agent": "conversion_agent",
    "source_agent": "conversation_agent",
    "session_id": "abc-123",
    "context": { /* full context */ },
    "payload": {
        "action": "convert_dataset",
        "input_path": "/data/recordings/session_001/",
        "output_path": "/output/nwb/session_001.nwb",
        "data_format": "blackrock",
        "metadata": { /* collected metadata */ },
        "preprocessing_results": { /* validation results */ }
    }
}
```

---

### Epic 3: Conversion Agent

#### Story 3.1: Receive Conversion Request
**As a** conversion agent
**I want** to receive validated data and metadata from conversation agent
**So that** I can begin NWB file generation

**Acceptance Criteria:**
- [ ] Agent receives message from MCP server
- [ ] Agent validates all required information is present
- [ ] Agent loads context file for session state
- [ ] Agent confirms dataset accessibility
- [ ] Agent sends acknowledgment back to MCP server

#### Story 3.2: Initialize NeuroConv Interface
**As a** conversion agent
**I want** to select and configure the appropriate NeuroConv data interface
**So that** I can convert the specific data format to NWB

**Acceptance Criteria:**
- [ ] Agent maps data format to NeuroConv interface class
- [ ] Agent instantiates appropriate interface (BlackrockRecordingInterface, IntanRecordingInterface, etc.)
- [ ] Agent configures interface with dataset path
- [ ] Agent validates interface can read source data
- [ ] Agent handles interface initialization errors gracefully

**Supported Data Formats:**
```python
INTERFACE_MAPPING = {
    "blackrock": "BlackrockRecordingInterface",
    "intan": "IntanRecordingInterface",
    "openephys": "OpenEphysRecordingInterface",
    "spikeglx": "SpikeGLXRecordingInterface"
}
```

#### Story 3.3: Configure NWB Conversion
**As a** conversion agent
**I want** to configure NeuroConv conversion parameters
**So that** the output NWB file meets specifications

**Acceptance Criteria:**
- [ ] Agent creates NWBConverter with selected interface
- [ ] Agent injects user-provided metadata into conversion
- [ ] Agent configures output path and file name
- [ ] Agent sets compression options (default: gzip level 4)
- [ ] Agent enables provenance tracking

**Conversion Configuration:**
```python
conversion_config = {
    "interface": "BlackrockRecordingInterface",
    "source_data": {
        "file_path": "/data/recordings/session_001/"
    },
    "conversion_options": {
        "stub_test": false,
        "write_electrical_series": true,
        "compression": "gzip",
        "compression_opts": 4
    },
    "metadata": {
        "NWBFile": {
            "session_description": "...",
            "identifier": "session_001",
            "session_start_time": "2024-01-01T00:00:00Z"
        },
        "Subject": {
            "subject_id": "mouse_01",
            "species": "Mus musculus"
        }
    }
}
```

#### Story 3.4: Execute NWB Conversion
**As a** conversion agent
**I want** to execute the NeuroConv conversion process
**So that** source data is transformed into NWB format

**Acceptance Criteria:**
- [ ] Agent calls converter.run_conversion() with configuration
- [ ] Agent monitors conversion progress and reports status
- [ ] Agent captures conversion logs and warnings
- [ ] Agent handles conversion errors with detailed messages
- [ ] Agent verifies output NWB file was created successfully

**Conversion Execution:**
```python
try:
    converter = NWBConverter(data_interfaces={"Recording": interface})
    converter.run_conversion(
        nwbfile_path=output_path,
        metadata=metadata,
        overwrite=False,
        conversion_options=conversion_options
    )
    conversion_result = {
        "status": "success",
        "nwb_file_path": output_path,
        "duration_seconds": elapsed_time,
        "warnings": conversion_warnings,
        "logs": conversion_logs
    }
except Exception as e:
    conversion_result = {
        "status": "failed",
        "error": str(e),
        "traceback": traceback.format_exc()
    }
```

#### Story 3.5: Hand Off to Evaluation Agent
**As a** conversion agent
**I want** to send the generated NWB file to the evaluation agent
**So that** validation can be performed

**Acceptance Criteria:**
- [ ] Agent updates context with conversion results
- [ ] Agent sends message to MCP server targeting evaluation_agent
- [ ] Message includes NWB file path and conversion metadata
- [ ] Agent handles handoff failure (retry or alert)
- [ ] Agent transitions to completed state

**Handoff Message:**
```json
{
    "target_agent": "evaluation_agent",
    "source_agent": "conversion_agent",
    "session_id": "abc-123",
    "context": { /* updated context */ },
    "payload": {
        "action": "validate_nwb",
        "nwb_file_path": "/output/nwb/session_001.nwb",
        "conversion_metadata": {
            "duration_seconds": 45.2,
            "source_format": "blackrock",
            "neuroconv_version": "0.4.0"
        }
    }
}
```

---

### Epic 4: Evaluation Agent

#### Story 4.1: Receive Validation Request
**As an** evaluation agent
**I want** to receive NWB file path from conversion agent
**So that** I can validate the generated file

**Acceptance Criteria:**
- [ ] Agent receives message from MCP server
- [ ] Agent loads context file for session state
- [ ] Agent verifies NWB file exists at specified path
- [ ] Agent confirms file is readable
- [ ] Agent sends acknowledgment to MCP server

#### Story 4.2: Initialize NWB Inspector
**As an** evaluation agent
**I want** to configure NWB Inspector for validation
**So that** I can check file compliance and quality

**Acceptance Criteria:**
- [ ] Agent imports NWB Inspector tools
- [ ] Agent configures validation level (basic/comprehensive)
- [ ] Agent sets up validation report output format
- [ ] Agent initializes validation checks suite
- [ ] Agent handles inspector initialization errors

**Inspector Configuration:**
```python
from nwbinspector import inspect_nwbfile, Importance

inspector_config = {
    "importance_threshold": Importance.BEST_PRACTICE_SUGGESTION,
    "select_checks": None,  # Run all checks
    "ignore_checks": [],
    "max_messages": 100
}
```

#### Story 4.3: Execute NWB Validation
**As an** evaluation agent
**I want** to run comprehensive validation checks on the NWB file
**So that** quality and compliance issues are identified

**Acceptance Criteria:**
- [ ] Agent runs schema compliance checks
- [ ] Agent runs best practices validation
- [ ] Agent checks metadata completeness
- [ ] Agent validates data integrity
- [ ] Agent identifies time series consistency issues

**Validation Checks:**
```python
validation_suite = [
    "schema_compliance",
    "best_practices",
    "metadata_completeness",
    "data_integrity",
    "timeseries_validation",
    "unit_consistency"
]
```

#### Story 4.4: Generate Validation Report
**As an** evaluation agent
**I want** to create a comprehensive validation report
**So that** users understand file quality and any issues

**Acceptance Criteria:**
- [ ] Report includes overall validation status (pass/fail)
- [ ] Report categorizes issues by severity (critical/warning/info)
- [ ] Report provides specific locations for each issue
- [ ] Report includes suggested fixes for common problems
- [ ] Report is formatted in human-readable and machine-readable formats

**Report Structure:**
```json
{
    "validation_summary": {
        "overall_status": "passed_with_warnings",
        "total_checks": 45,
        "passed": 40,
        "warnings": 5,
        "errors": 0,
        "critical": 0
    },
    "issues": [
        {
            "severity": "warning",
            "check_name": "electrode_table_completeness",
            "location": "/general/extracellular_ephys/electrodes",
            "message": "Electrode table missing optional 'filtering' column",
            "suggested_fix": "Add 'filtering' column with filter specifications"
        }
    ],
    "metadata_completeness": 0.95,
    "best_practices_score": 0.85,
    "nwb_version": "2.6.0",
    "inspector_version": "0.4.11"
}
```

#### Story 4.5: Return Results to User
**As an** evaluation agent
**I want** to send validation results back through the MCP server
**So that** the user receives final conversion status

**Acceptance Criteria:**
- [ ] Agent updates context with validation results
- [ ] Agent sends results to conversation agent for user display
- [ ] Agent marks session as completed in context
- [ ] Agent generates downloadable report files
- [ ] Agent cleans up temporary resources

**Final Response:**
```json
{
    "target_agent": "conversation_agent",
    "source_agent": "evaluation_agent",
    "session_id": "abc-123",
    "context": { /* final context */ },
    "payload": {
        "action": "display_results",
        "validation_status": "passed_with_warnings",
        "nwb_file_path": "/output/nwb/session_001.nwb",
        "report_path": "/output/reports/session_001_validation.json",
        "summary": {
            "conversion_successful": true,
            "validation_passed": true,
            "warnings_count": 5,
            "errors_count": 0
        }
    }
}
```

---

## Epic 5: End-to-End Pipeline Integration

#### Story 5.1: Complete Conversion Workflow
**As a** user
**I want** to convert my neuroscience data to NWB format through a guided process
**So that** my data is standardized and validated

**Full Workflow:**
1. User initiates session with Conversation Agent
2. Conversation Agent collects metadata and validates data
3. Conversation Agent hands off to Conversion Agent via MCP
4. Conversion Agent uses NeuroConv to generate NWB file
5. Conversion Agent hands off to Evaluation Agent via MCP
6. Evaluation Agent uses NWB Inspector to validate file
7. Evaluation Agent returns results to Conversation Agent
8. Conversation Agent displays results to user

**Success Criteria:**
- [ ] Complete workflow executes without manual intervention
- [ ] Each agent communicates only through MCP server
- [ ] Context file is maintained throughout pipeline
- [ ] User receives clear status updates at each stage
- [ ] Final output includes valid NWB file and validation report

#### Story 5.2: Error Recovery and Rollback
**As a** system
**I want** to handle failures at any pipeline stage gracefully
**So that** users receive actionable error information

**Acceptance Criteria:**
- [ ] Each agent reports errors to MCP server
- [ ] MCP server notifies user through conversation agent
- [ ] Context file preserves error information for debugging
- [ ] System suggests remediation steps for common errors
- [ ] Partial progress is saved (preprocessed data, partial conversions)

---

## Technical Specifications

### MCP Server Implementation

**Technology Stack:**
- Python 3.10+
- FastAPI for HTTP endpoints
- WebSocket support for real-time updates
- Redis for context file storage
- PostgreSQL for session persistence

**Endpoints:**
```
POST   /mcp/message        - Send message to agent
GET    /mcp/status         - Get pipeline status
GET    /mcp/context/:id    - Retrieve context file
POST   /mcp/session/start  - Initialize new session
DELETE /mcp/session/:id    - Cleanup session
```

### Agent Implementation

**Base Agent Class:**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    def __init__(self, agent_name: str, mcp_server_url: str):
        self.agent_name = agent_name
        self.mcp_server_url = mcp_server_url
        self.logger = setup_logger(agent_name)

    @abstractmethod
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message and return response"""
        pass

    async def send_message(self, target_agent: str, payload: Dict[str, Any]):
        """Send message through MCP server"""
        pass

    def update_context(self, session_id: str, updates: Dict[str, Any]):
        """Update session context file"""
        pass
```

### Context File Storage

**File Structure:**
```
/data/contexts/
  ├── {session_id}/
  │   ├── context.json          # Current session state
  │   ├── agent_logs/           # Per-agent execution logs
  │   │   ├── conversation.log
  │   │   ├── conversion.log
  │   │   └── evaluation.log
  │   ├── data/                 # Session-specific data
  │   │   └── preprocessing_results.json
  │   └── reports/              # Generated reports
  │       └── validation_report.json
```

---

## Non-Functional Requirements

### Performance
- Conversion should handle datasets up to 10GB
- Message routing latency < 100ms
- Context file updates < 50ms
- Support for concurrent sessions (min 10)

### Reliability
- All agent failures must be recoverable
- Context files must survive server restarts
- Message delivery must be guaranteed (at-least-once)

### Logging & Monitoring
- All agent actions logged with timestamps
- Message flow tracked through pipeline
- Performance metrics collected (conversion time, validation time)
- Error rates monitored per agent

### Security
- Context files contain no sensitive credentials
- Data paths validated to prevent directory traversal
- Agent authentication through MCP server
- Session isolation enforced

---

## Testing Requirements

### Unit Tests
- [ ] Each agent handles messages correctly
- [ ] Context file updates work properly
- [ ] MCP server routes messages accurately
- [ ] Error handling in each component

### Integration Tests
- [ ] Complete pipeline workflow succeeds
- [ ] Agent handoffs work correctly
- [ ] Context persistence across agents
- [ ] Error propagation through pipeline

### End-to-End Tests
- [ ] Real dataset conversion (Blackrock, Intan, OpenEphys)
- [ ] Validation report generation
- [ ] User interaction flow
- [ ] Recovery from failures

---

## Future Enhancements (Out of Scope)

- Knowledge graph integration for metadata suggestions
- TUIE agent for tool usage monitoring
- Parallel processing for large datasets
- Web UI for pipeline monitoring
- REST API for programmatic access
- Support for additional data formats

---

## Glossary

- **MCP**: Model Context Protocol - communication standard for agent messaging
- **NWB**: Neurodata Without Borders - standardized format for neurophysiology data
- **NeuroConv**: Python package for converting various formats to NWB
- **NWB Inspector**: Validation tool for NWB files
- **Context File**: Persistent session state shared across agents
- **Agent**: Autonomous component responsible for specific pipeline stage

---

## References

- NWB Format Specification: https://nwb-schema.readthedocs.io/
- NeuroConv Documentation: https://neuroconv.readthedocs.io/
- NWB Inspector: https://github.com/NeurodataWithoutBorders/nwbinspector
- Model Context Protocol: https://modelcontextprotocol.io/

---

## Approval

This specification must be reviewed and approved before implementation begins.

**Stakeholders:**
- [ ] Product Owner
- [ ] Technical Lead
- [ ] Development Team
- [ ] Quality Assurance

**Estimated Effort:** 6-8 weeks for MVP implementation

**Priority:** High - Foundational feature for pipeline
