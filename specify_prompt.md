# Multi-Agent NWB Conversion Pipeline

## What We're Building

Build an automated multi-agent system that converts heterogeneous neuroscience data formats into standardized Neurodata Without Borders (NWB) format. The system should guide users through data conversion, collect necessary metadata interactively, perform the conversion, and validate the output.

## Why This Matters

Neuroscience researchers work with diverse recording equipment, particularly OpenEphys systems, that produces data in proprietary formats. Converting to NWB enables:
- Data sharing across research labs
- Integration with standardized analysis tools
- Long-term archiving on public repositories like DANDI
- Compliance with FAIR data principles
- Reproducible research practices

## Core Components

The system consists of three specialized agents coordinated by a central server:

1. **MCP Server Layer**: Central orchestration and communication hub
2. **Conversation Agent**: User interaction and data preprocessing
3. **Conversion Agent**: NWB file generation using NeuroConv
4. **Evaluation Agent**: NWB validation using NWB Inspector

## Architecture Requirements

### Model-Agnostic Design
- System must support any LLM provider (Claude, OpenAI, local models via Ollama, etc.)
- Each agent can be configured with a different model independently
- Agent implementation must use direct API calls to configured providers (no abstraction layer for MVP)
- Configuration via environment variables for per-agent model selection

### Agent Communication
- Agents must not directly call or depend on each other
- All inter-agent communication flows through the central MCP server
- Agents run as separate processes (microservices architecture)
- Agents are stateless - all state managed in session context files
- Workflow state tracked in context to determine next agent in pipeline
- The server must route messages between agents based on target specification
- Messages should include sender/recipient identification, session tracking, and payload data
- The server must validate agent existence before routing messages
- Message delivery failures should be handled gracefully with retries or alerts
- Communication via REST API and HTTP (WebSockets are post-MVP)

### Context Management
- Each session must have persistent context shared across all agents
- Context stored in Redis for fast access and persisted to disk
- Context should track session state, current processing stage, and agent history
- Context must include session_id, timestamps, data paths, collected metadata, and processing results
- Context files should be updated after each agent completes its task
- Context must persist to disk for recovery after server restarts
- Session-level recovery: system can restart from any agent failure point

### Server Requirements
- Server should start on port 3000 (configurable via environment variable)
- Server built using MCP Python package (model-agnostic MCP server)
- Server must maintain a registry of connected agents
- Server should log all message routing activities using Python standard logging with JSON format
- Server must provide health check capabilities
- Server should expose capabilities for tools, resources, and context management
- FastAPI for REST endpoints returning prompts for user interaction

---

## User Experience Flow

### Complete Workflow
1. User initiates session by providing dataset path
2. System detects data format automatically or confirms with user
3. System analyzes dataset structure and validates accessibility
4. System identifies required metadata fields and prompts user interactively
5. System validates and preprocesses the data (checks integrity, compatibility)
6. System converts data to NWB format using appropriate tools
7. System validates the generated NWB file for quality and compliance
8. User receives the NWB file and a detailed validation report

### User Receives Clear Status Updates
- At each stage, users should see progress indicators
- Users should be notified when agents hand off work
- Users should receive clear confirmation when each stage completes
- Users should get actionable error messages if anything fails

---

## Conversation Agent Requirements

### Session Initialization
- Create new sessions with unique identifiers
- Prompt users for dataset path
- Validate that dataset path exists and is accessible
- Detect data format from file extensions and structure
- Confirm detected format with user before proceeding
- Initialize context with session information

### Metadata Collection
- Identify which metadata fields are required for NWB conversion
- Prompt users interactively for each missing field
- Provide helpful examples and format guidance for each field (e.g., "P90D for 90 days")
- Validate metadata format (e.g., ISO 8601 dates, species nomenclature)
- Store collected metadata in session context

**Required Metadata:**
- **Subject Information**: subject_id, species, age, sex
- **Experiment Information**: session_id, session_start_time, experimenter
- **Device Information**: device_name, manufacturer, recording_location
- **Dataset Description**: description, keywords

### Data Validation and Preprocessing
- Check file integrity (detect corruption)
- Verify OpenEphys format compatibility with NeuroConv
- For OpenEphys data, validate:
  - Presence of settings.xml
  - Continuous recording files exist
  - Channel configuration is readable
- Extract basic dataset information:
  - Total file size (warn if > 10GB but allow processing)
  - Number of continuous files
  - Channel count
  - Sampling rate
  - Recording duration
- Perform hybrid format detection:
  - Use file extension for binary data files (.continuous)
  - Content inspection for metadata files (settings.xml, channel maps)
- Identify potential issues (missing files, incomplete recordings, unusually large files)
- Report warnings to users (e.g., "Large file size may require significant memory")
- Update context with preprocessing results

### Handoff to Conversion
- Update context with "ready_for_conversion" status
- Send message to MCP server targeting conversion agent
- Include complete metadata, data path, format, and preprocessing results
- Confirm handoff to user
- Transition to monitoring state

---

## Conversion Agent Requirements

### Receiving Conversion Request
- Receive message from MCP server with validated data and metadata
- Validate all required information is present
- Load context file for session state
- Confirm dataset accessibility
- Send acknowledgment back to MCP server

### NeuroConv Interface Selection
- Map data format to appropriate NeuroConv interface
- Support OpenEphys format for MVP:
  - OpenEphys (continuous files, .continuous format) → OpenEphysRecordingInterface
  - Detect OpenEphys directory structure (settings.xml, continuous files)
- Instantiate OpenEphysRecordingInterface with dataset path
- Validate interface can read source data
- Handle interface initialization errors gracefully with clear messages

### Conversion Configuration
- Create converter with selected interface
- Inject user-provided metadata into conversion
- Configure output path and file name
- Set compression options (default: gzip)
- Enable provenance tracking
- Configure to write complete data (not stub/test mode)

### Conversion Execution
- Execute the conversion process
- Monitor conversion progress and report status
- Capture conversion logs and warnings
- Handle conversion errors with detailed diagnostic information
- Verify output NWB file was created successfully
- Record conversion duration and any warnings

### Handoff to Evaluation
- Update context with conversion results (status, file path, duration, warnings)
- Send message to MCP server targeting evaluation agent
- Include NWB file path and conversion metadata
- Handle handoff failures appropriately
- Transition to completed state

---

## Evaluation Agent Requirements

### Receiving Validation Request
- Receive message from MCP server with NWB file path
- Load context file for session state
- Verify NWB file exists at specified path
- Confirm file is readable
- Send acknowledgment to MCP server

### NWB Inspector Configuration
- Configure validation level (basic vs. comprehensive)
- Set up validation report output format
- Initialize validation checks suite
- Handle inspector initialization errors

### Validation Execution
Run comprehensive validation checks:
- **Schema Compliance**: Verify file structure matches NWB specification
- **Best Practices**: Check for recommended patterns and conventions
- **Metadata Completeness**: Ensure required and recommended fields are present
- **Data Integrity**: Validate consistent dimensions, valid ranges, no corruption
- **Time Series Validation**: Check alignment, timestamps, continuity
- **Unit Consistency**: Verify units are specified and consistent

### Validation Report Generation
- Include overall validation status (pass/fail/pass-with-warnings)
- Categorize issues by severity (critical/warning/info)
- Provide specific file locations for each issue
- Include suggested fixes for common problems
- Format report for both human reading and machine parsing
- Calculate quality scores (metadata completeness, best practices score)
- Include NWB version and inspector version used

### Return Results to User
- Update context with validation results
- Send results to conversation agent for user display
- Mark session as completed in context
- Generate downloadable report files
- Clean up temporary resources

---

## Error Handling and Recovery

### Error Requirements
- Each agent must report failures to the MCP server
- Users should receive actionable error messages through conversation agent
- Context must preserve error information for debugging
- System should suggest remediation steps for common errors
- Partial progress should be saved when possible (preprocessed data, incomplete conversions)

### Common Error Scenarios to Handle
- Dataset path not found or inaccessible
- Unsupported data format
- Missing or invalid metadata
- Conversion failures (corrupted data, insufficient memory)
- Validation failures
- Network/communication failures between agents

---

## Non-Functional Requirements

### Performance
- Handle datasets up to 10GB (warn users for larger files but allow processing)
- Message routing latency under 100ms
- Context file updates under 50ms
- Single session support for MVP (concurrent sessions are post-MVP)

### Reliability
- All agent failures must be recoverable
- Context files must survive server restarts
- Message delivery must be guaranteed (at-least-once delivery)

### Logging and Monitoring
- All agent actions logged with timestamps
- Message flow tracked through pipeline
- Performance metrics collected (conversion time, validation time)
- Error rates monitored per agent

### Security
- Context files must not contain sensitive credentials
- Data paths must be validated to prevent directory traversal attacks
- Agents must authenticate through MCP server
- Session isolation must be enforced (users cannot access other sessions)

---

## Testing Requirements

The system must have:
- **Unit tests** for each agent's message handling, context updates, and core functionality (no mocks - test with real services)
- **Integration tests** for complete pipeline workflow, agent handoffs, and context persistence
- **End-to-end tests** with real OpenEphys datasets
- **Error handling tests** for session-level recovery from failures at each stage
- **Performance tests** to verify requirements are met
- All agent message handlers are considered critical paths (≥90% coverage required)

---

## Success Criteria

The system is successful when:
- A user can convert an OpenEphys dataset to NWB through interactive REST API
- The generated NWB file passes NWB Inspector validation
- Users receive a clear, actionable validation report with all error details (message, suggested fix, stack trace, session context) presented concisely
- All agents communicate only through the central MCP server (no direct dependencies)
- Failed conversions provide clear error messages with remediation steps
- The complete workflow executes without requiring manual intervention
- Context is maintained throughout the pipeline with session-level recovery capability
- Agents are stateless with workflow state managed in session context
- System is model-agnostic, supporting any LLM through per-agent configuration

---

## Out of Scope (Future Enhancements)

The following are explicitly NOT part of this initial version:
- DataLad integration for data management and provenance tracking
- Knowledge graph integration (RDF, LinkML, PROV-O) for metadata and provenance
- Tool usage monitoring agent (TUIE)
- Parallel processing for datasets larger than 10GB
- Web-based UI dashboard for monitoring
- Support for additional data formats beyond OpenEphys (Blackrock, Intan, SpikeGLX are post-MVP)
- Automatic upload to DANDI archive
- Concurrent session handling (single session only for MVP)

---

## Glossary

- **MCP (Model Context Protocol)**: Communication standard for agent messaging
- **NWB (Neurodata Without Borders)**: Standardized format for neurophysiology data
- **NeuroConv**: Python package for converting various formats to NWB
- **NWB Inspector**: Validation tool that checks NWB file compliance and quality
- **DANDI**: Open neuroscience data archive for NWB files
- **FAIR Principles**: Findable, Accessible, Interoperable, Reusable data standards

---

## References

- NWB Format Specification: https://nwb-schema.readthedocs.io/
- NeuroConv Documentation: https://neuroconv.readthedocs.io/
- NWB Inspector: https://github.com/NeurodataWithoutBorders/nwbinspector
- Model Context Protocol: https://modelcontextprotocol.io/
- DANDI Archive: https://dandiarchive.org/
