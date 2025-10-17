# Feature Specification: Multi-Agent NWB Conversion Pipeline

**Feature ID**: multi-agent-nwb-conversion
**Version**: 1.1.0
**Status**: Ready for Planning
**Created**: 2025-01-14
**Last Updated**: 2025-01-14 (Metadata extraction workflow, LLM params, Redis config finalized)

---

## Executive Summary

This specification defines a model-agnostic, multi-agent system for converting OpenEphys neuroscience data to Neurodata Without Borders (NWB) format. The system uses the Model Context Protocol (MCP) for agent orchestration, supports any LLM provider, and follows strict test-driven development practices as mandated by the project constitution.

### Key Features
- **Model-Agnostic Architecture**: Supports Claude, OpenAI, and local models
- **MCP-Based Communication**: All agents communicate through central MCP server
- **OpenEphys Support**: MVP focuses on OpenEphys format conversion
- **Intelligent Metadata Extraction**: LLM-powered extraction from .md files with error-driven user prompting
- **Comprehensive Validation**: NWB Inspector integration for quality assurance

### Strategic Value
Enables neuroscience researchers to convert proprietary OpenEphys data to NWB format for:
- Cross-lab data sharing
- Standardized analysis tool integration
- Long-term archiving on DANDI
- FAIR data compliance
- Reproducible research

---

## 1. Feature Overview

### 1.1 Problem Statement

Neuroscience researchers using OpenEphys recording systems face challenges:
- Data locked in proprietary formats incompatible with standard tools
- Manual conversion processes are error-prone and time-consuming
- Lack of automated validation leads to data quality issues
- No systematic metadata collection results in incomplete datasets

### 1.2 Proposed Solution

A multi-agent system that:
1. Automatically extracts metadata from .md files in the dataset using LLM intelligence
2. Prompts users for clarification only when conversion/validation errors occur
3. Automatically converts OpenEphys data to NWB format with reasonable defaults
4. Validates output files for compliance and quality
5. Provides detailed validation reports with actionable feedback

### 1.3 Scope

**In Scope (MVP)**:
- OpenEphys format support (.continuous files, settings.xml)
- Three specialized agents (Conversation, Conversion, Evaluation)
- MCP server for agent orchestration
- REST API for user interaction (initialization, status polling, results)
- Intelligent metadata extraction from .md files using LLM
- Error-driven user prompting (only when conversion/validation fails)
- Redis + filesystem context persistence (24-hour TTL)
- Single session handling
- Reasonable defaults for missing metadata

**Out of Scope (Post-MVP)**:
- Additional formats (Blackrock, Intan, SpikeGLX)
- DataLad integration for provenance
- Knowledge graph integration (RDF, LinkML)
- Concurrent session handling
- WebSocket communication
- DANDI archive upload
- Web UI dashboard

---

## 2. Architecture

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User (REST Client)                      │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/REST (port 3000)
                             │
┌────────────────────────────▼────────────────────────────────┐
│                   MCP Server (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Message Router │ Agent Registry │ Context Manager   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        Context Storage (Redis + Filesystem)          │  │
│  └──────────────────────────────────────────────────────┘  │
└──────┬───────────────────┬───────────────────┬─────────────┘
       │ MCP Protocol      │ MCP Protocol      │ MCP Protocol
       │                   │                   │
┌──────▼───────┐   ┌───────▼────────┐   ┌────▼────────────┐
│ Conversation │   │   Conversion   │   │   Evaluation    │
│    Agent     │   │     Agent      │   │     Agent       │
│ (Process 1)  │   │  (Process 2)   │   │  (Process 3)    │
│              │   │                │   │                 │
│ LLM: Config  │   │ LLM: Config    │   │ LLM: Config     │
└──────────────┘   └────────────────┘   └─────────────────┘
```

### 2.2 Core Components

**MCP Server**
- **Technology**: FastAPI + MCP Python package (mcp>=1.0.0)
- **Port**: 3000 (configurable via `MCP_SERVER_PORT`)
- **Responsibilities**: Message routing, agent registry, context management, health checks

**Agents** (Separate Processes)
- **Conversation Agent**: Session initialization, LLM-based metadata extraction from .md files, data validation, error-driven user prompting
- **Conversion Agent**: NeuroConv integration, NWB file generation
- **Evaluation Agent**: NWB Inspector integration, validation reporting

**Context Storage**
- **Primary**: Redis (fast access, 24-hour TTL per session)
- **Backup**: Filesystem JSON files (persistence)
- **Strategy**: Write-through (Redis + disk simultaneously)

### 2.3 Model-Agnostic Design

**Per-Agent LLM Configuration**:
```env
# Conversation Agent (friendly, natural interaction)
CONVERSATION_AGENT_LLM_PROVIDER=anthropic
CONVERSATION_AGENT_MODEL=claude-3-5-sonnet-20250929
CONVERSATION_AGENT_API_KEY=sk-ant-...
CONVERSATION_AGENT_TEMPERATURE=0.7
CONVERSATION_AGENT_MAX_TOKENS=2048
CONVERSATION_AGENT_TOP_P=0.95

# Conversion Agent (deterministic, consistent error messages)
CONVERSION_AGENT_LLM_PROVIDER=anthropic
CONVERSION_AGENT_MODEL=claude-3-5-sonnet-20250929
CONVERSION_AGENT_API_KEY=sk-ant-...
CONVERSION_AGENT_TEMPERATURE=0.3
CONVERSION_AGENT_MAX_TOKENS=1024
CONVERSION_AGENT_TOP_P=0.9

# Evaluation Agent (clear, readable summaries)
EVALUATION_AGENT_LLM_PROVIDER=anthropic
EVALUATION_AGENT_MODEL=claude-3-5-sonnet-20250929
EVALUATION_AGENT_API_KEY=sk-ant-...
EVALUATION_AGENT_TEMPERATURE=0.4
EVALUATION_AGENT_MAX_TOKENS=1536
EVALUATION_AGENT_TOP_P=0.9

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_TTL_SECONDS=86400  # 24 hours
```

**Supported Providers**: Anthropic Claude, OpenAI, local models via Ollama

**LLM Parameter Rationale**:
- **Conversation Agent**: Higher temperature (0.7) for natural, friendly interaction while staying on-topic
- **Conversion Agent**: Lower temperature (0.3) for consistent, deterministic error messages
- **Evaluation Agent**: Balanced temperature (0.4) for clear technical summaries

---

## 3. User Stories

### Epic 1: Session Management

#### Story 1.1: Initialize Conversion Session
**As a** neuroscience researcher
**I want to** start a new conversion session by providing my dataset path
**So that** the system can analyze my data and guide me through conversion

**Acceptance Criteria**:
- [ ] User calls POST `/api/v1/sessions/initialize` with dataset_path
- [ ] System validates path exists and is accessible
- [ ] System detects OpenEphys format (settings.xml, .continuous files)
- [ ] System returns session_id and initial prompt
- [ ] Session context is created in Redis and persisted to disk

#### Story 1.2: Track Session Status
**As a** user
**I want to** check the current status of my conversion session
**So that** I know what stage the process is in and if any action is needed

**Acceptance Criteria**:
- [ ] User calls GET `/api/v1/sessions/{id}/status`
- [ ] System returns current workflow stage (collecting_metadata, converting, etc.)
- [ ] Response includes progress percentage and status message
- [ ] Any errors or warnings are clearly communicated

### Epic 2: Metadata Extraction

#### Story 2.1: Extract Metadata from .md Files
**As a** conversation agent
**I want to** automatically extract metadata from all .md files in the dataset
**So that** users don't have to manually enter information already documented

**Acceptance Criteria**:
- [ ] Agent finds all .md files in dataset directory (README.md, metadata.md, notes.md, etc.)
- [ ] Agent reads content of all .md files found
- [ ] Agent combines content from multiple .md files if present
- [ ] Agent uses LLM to extract NWB metadata fields: subject_id, species, age, sex, session_start_time, experimenter, device_name, manufacturer, recording_location, description
- [ ] Agent handles both structured (key-value, YAML) and unstructured (prose) formats
- [ ] Agent stores extracted metadata in session context

#### Story 2.2: Apply Reasonable Defaults for Missing Fields
**As a** conversation agent
**I want to** fill in reasonable defaults when metadata cannot be extracted
**So that** conversion can proceed even with incomplete information

**Acceptance Criteria**:
- [ ] If no .md files exist, all metadata fields left empty
- [ ] If .md files exist but field cannot be extracted, leave field empty
- [ ] If ambiguous information (e.g., "young mouse"), apply reasonable defaults (species="Mus musculus" if "mouse" mentioned)
- [ ] Agent logs which fields were extracted vs defaulted vs left empty
- [ ] Metadata stored in session context with extraction confidence scores

#### Story 2.3: Prompt User Only on Conversion/Validation Errors
**As a** conversation agent
**I want to** prompt users for input only when errors occur
**So that** the workflow is automatic unless human intervention is needed

**Acceptance Criteria**:
- [ ] If conversion agent reports error, conversation agent asks user for clarification
- [ ] If evaluation agent reports critical validation failures, conversation agent asks user for corrections
- [ ] User prompting happens via POST `/api/v1/sessions/{id}/clarify` endpoint
- [ ] User can provide additional metadata or corrections
- [ ] System re-attempts conversion/validation with updated information

### Epic 3: Data Validation

#### Story 3.1: Validate OpenEphys Structure
**As a** conversation agent
**I want to** validate the OpenEphys dataset structure
**So that** conversion can proceed without errors

**Acceptance Criteria**:
- [ ] Agent checks for settings.xml presence
- [ ] Agent verifies .continuous files exist
- [ ] Agent validates channel configuration is readable
- [ ] Agent detects file corruption
- [ ] Agent warns if dataset > 10GB but allows processing

#### Story 3.2: Extract Dataset Information
**As a** conversation agent
**I want to** extract basic dataset metrics
**So that** users understand what will be converted

**Acceptance Criteria**:
- [ ] Agent extracts: total size, file count, channel count, sampling rate, duration
- [ ] Information displayed to user before conversion
- [ ] Metrics stored in session context

### Epic 4: NWB Conversion

#### Story 4.1: Execute OpenEphys Conversion
**As a** conversion agent
**I want to** convert OpenEphys data to NWB format using NeuroConv
**So that** researchers have standardized files

**Acceptance Criteria**:
- [ ] Agent instantiates OpenEphysRecordingInterface with dataset path
- [ ] Agent injects user-provided metadata into NWB format
- [ ] Agent configures gzip compression
- [ ] Agent executes conversion with progress monitoring
- [ ] Agent captures logs and warnings
- [ ] Generated NWB file is saved to configured output directory

#### Story 4.2: Handle Conversion Errors
**As a** conversion agent
**I want to** provide detailed error information when conversion fails
**So that** users can fix issues and retry

**Acceptance Criteria**:
- [ ] Agent captures full error message and complete stack trace
- [ ] Agent uses LLM to generate user-friendly error explanation with remediation steps
- [ ] Session context preserves all error details (message, trace, context snapshot) for debugging
- [ ] Error response includes: error message, suggested fix, full stack trace, session context
- [ ] All details displayed to user (no truncation) but formatted for readability
- [ ] Conversation agent prompts user for clarification via `/clarify` endpoint if needed

### Epic 5: NWB Validation

#### Story 5.1: Run NWB Inspector Validation
**As an** evaluation agent
**I want to** validate the generated NWB file for compliance and quality
**So that** users receive high-quality, standards-compliant files

**Acceptance Criteria**:
- [ ] Agent runs NWB Inspector with comprehensive checks
- [ ] Validation covers: schema compliance, best practices, metadata completeness, data integrity, time series consistency, unit consistency
- [ ] Agent categorizes issues by severity (critical/warning/info)
- [ ] Agent generates JSON validation report

#### Story 5.2: Generate Validation Report
**As an** evaluation agent
**I want to** create a detailed validation report
**So that** users understand file quality and any issues

**Acceptance Criteria**:
- [ ] Report includes overall status (passed/passed_with_warnings/failed)
- [ ] Report lists all issues with specific file locations
- [ ] Report provides suggested fixes for common problems
- [ ] Report includes quality scores (metadata completeness, best practices)
- [ ] Report saved as JSON file in output directory

#### Story 5.3: Return Final Results
**As a** user
**I want to** receive the final NWB file and validation report
**So that** I can use my converted data

**Acceptance Criteria**:
- [ ] User calls GET `/api/v1/sessions/{id}/result`
- [ ] System returns NWB file path and report path
- [ ] System provides LLM-generated summary of validation results
- [ ] Session marked as completed in context

### Epic 6: Error Recovery

#### Story 6.1: Recover from Agent Failures
**As a** system
**I want to** enable session-level recovery from any agent failure
**So that** users don't lose progress

**Acceptance Criteria**:
- [ ] Session context persisted to disk after each agent completes
- [ ] System can restart from any workflow stage
- [ ] User can resume session after server restart
- [ ] Context includes full history of agent executions

---

## 4. Technical Requirements

### 4.1 Data Models

**SessionContext**:
```python
{
  "session_id": str,
  "created_at": datetime,
  "last_updated": datetime,
  "current_agent": str | None,
  "workflow_stage": str,  # initialized, collecting_metadata, preprocessing, converting, evaluating, completed, failed
  "agent_history": [AgentHistoryEntry],
  "dataset_info": DatasetInfo | None,
  "metadata": dict,
  "preprocessing_results": PreprocessingResults | None,
  "conversion_results": ConversionResults | None,
  "validation_results": ValidationResults | None,
  "output_nwb_path": str | None,
  "output_report_path": str | None
}
```

**MCPMessage**:
```python
{
  "message_id": str,
  "timestamp": datetime,
  "source_agent": str,
  "target_agent": str,
  "session_id": str,
  "message_type": str,  # agent_register, agent_execute, agent_response, context_update, error
  "payload": dict
}
```

### 4.2 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions/initialize` | Initialize new session with dataset path |
| GET | `/api/v1/sessions/{id}/status` | Get session status and progress |
| POST | `/api/v1/sessions/{id}/clarify` | Provide clarification when errors occur |
| GET | `/api/v1/sessions/{id}/result` | Get final NWB file and validation report |
| GET | `/health` | Server health check |

**Polling Recommendations**:
- **Session initialization**: Poll every 2 seconds
- **Data validation**: Poll every 2 seconds
- **Conversion** (< 5GB): Poll every 5 seconds
- **Conversion** (>5GB): Poll every 10 seconds
- **Evaluation**: Poll every 3 seconds

### 4.3 Technology Stack

**Core Dependencies**:
- `mcp>=1.0.0` - Model Context Protocol
- `fastapi>=0.100.0` - REST API framework
- `redis>=5.0.0` - Context cache
- `anthropic>=0.18.0` - Claude API
- `openai>=1.0.0` - OpenAI API
- `neuroconv>=0.4.0` - NWB conversion
- `nwbinspector>=0.4.0` - NWB validation
- `pydantic>=2.0.0` - Data validation

**Development Tools**:
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `ruff>=0.1.0` - Linting
- `mypy>=1.5.0` - Type checking

---

## 5. Non-Functional Requirements

### 5.1 Performance
- **Dataset Size**: Support up to 10GB (warn but allow larger)
- **Message Routing**: < 100ms latency (P95)
- **Context Updates**: < 50ms (P95)
- **Concurrency**: Single session for MVP

### 5.2 Reliability
- **Agent Failures**: All recoverable via session context
- **Context Persistence**: Survives server restarts
- **Message Delivery**: At-least-once delivery guarantee

### 5.3 Security
- **Credentials**: Never stored in context files
- **Path Validation**: Prevent directory traversal attacks
- **Agent Authentication**: Required for MCP server access
- **Session Isolation**: Users cannot access other sessions

### 5.4 Logging
- **Format**: JSON structured logs
- **Level**: Configurable via environment
- **Content**: Timestamp, agent, session_id, action, status
- **Performance**: Log message routing latency and conversion duration

---

## 6. Testing Strategy

### 6.1 Test Coverage Requirements

**Critical Paths (≥90% coverage)**:
- Agent message handlers (handle_message methods)
- Context manager (CRUD operations)
- Message router (routing logic)
- MCP server core (message handling)

**Standard Components (≥85% coverage)**:
- REST API endpoints
- LLM provider integrations
- Format detection
- Data validation

### 6.2 Test Types

**Unit Tests**:
- Each agent's message handling
- Context updates
- Format detection
- Data validation
- **No mocks** - test with real services

**Integration Tests**:
- Complete pipeline workflow
- Agent handoffs via MCP
- Context persistence (Redis + filesystem)
- Session recovery

**End-to-End Tests**:
- Real OpenEphys dataset conversion
- Complete workflow with LLM interactions
- Error scenarios and recovery
- Large dataset handling (>10GB)

### 6.3 Test Data

**Synthetic OpenEphys Dataset**:
- Create ~1MB test dataset for fast tests
- Include settings.xml and minimal .continuous files
- Cover 2 channels × 10 seconds of data

### 6.4 Build Order (No Mocks)

1. **Phase 1**: Context Manager, Agent Registry
2. **Phase 2**: MCP Server (test with Phase 1)
3. **Phase 3**: Base Agent (test with Phase 2)
4. **Phase 4**: Specialized Agents (test with Phase 3)
5. **Phase 5**: Integration (test with all above)

---

## 7. Success Criteria

The feature is successful when:

- [ ] A user can convert an OpenEphys dataset to NWB via REST API
- [ ] The generated NWB file passes NWB Inspector validation
- [ ] Users receive validation report with error details, suggested fixes, and context (presented concisely)
- [ ] All agents communicate only through MCP server
- [ ] Failed conversions provide clear, actionable error messages
- [ ] Complete workflow executes without manual intervention
- [ ] Context persists throughout pipeline with session-level recovery
- [ ] Agents are stateless with workflow state in context
- [ ] System supports any LLM via per-agent configuration
- [ ] Test coverage meets requirements (≥90% critical, ≥85% overall)
- [ ] All pre-commit hooks pass (ruff, mypy)

---

## 8. Dependencies

### 8.1 External Dependencies
- Redis server (local or remote)
- Python 3.13 (exact version required by constitution)
- OpenEphys dataset for testing (with optional .md files for metadata)
- LLM API keys (Anthropic or OpenAI)

### 8.2 Internal Dependencies
- Constitution compliance (MCP-centric, TDD, quality gates)
- Pixi environment management
- Pre-commit hooks configuration

---

## 9. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM API rate limits | High | Medium | Implement retry logic with exponential backoff |
| Large dataset memory issues | High | High | Stream processing, monitor memory, provide warnings |
| Redis connection failures | Medium | Medium | Automatic reconnection, filesystem fallback |
| NeuroConv compatibility | High | Low | Test with multiple OpenEphys versions, comprehensive error handling |
| MCP protocol changes | Medium | Low | Pin mcp package version |

---

## 10. Implementation Plan

**Phase 1: Foundation (Week 1)**
- Data models (Pydantic schemas)
- Context Manager (Redis + filesystem)
- Agent Registry

**Phase 2: MCP Server (Week 2)**
- Message Router
- REST API endpoints
- Health checks

**Phase 3: Agent Base (Week 2-3)**
- Base Agent class
- LLM provider integrations (Anthropic, OpenAI)
- Agent registration

**Phase 4: Conversation Agent (Week 3)**
- Session initialization
- Format detection
- Metadata collection

**Phase 5: Conversion Agent (Week 4)**
- NeuroConv integration
- OpenEphys conversion
- Error handling

**Phase 6: Evaluation Agent (Week 4-5)**
- NWB Inspector integration
- Report generation

**Phase 7: Integration (Week 5-6)**
- End-to-end tests
- Error recovery tests
- Performance testing

**Phase 8: Documentation (Week 6)**
- API documentation
- Setup guide
- User guide

---

## 11. Configuration Decisions

All open questions have been resolved:

**✓ Metadata Fields**: Only NWB required fields (no custom fields for MVP). Fields extracted from .md files or left empty with reasonable defaults.

**✓ Large Datasets**: Warn users for datasets >10GB but allow processing to continue.

**✓ Progress Reporting**: Polling via `/status` endpoint only (no Server-Sent Events). Polling intervals: 2s (init/validation), 5s (conversion <5GB), 10s (conversion >5GB), 3s (evaluation).

**✓ LLM Parameters**:
- Conversation Agent: temperature=0.7, max_tokens=2048 (natural interaction)
- Conversion Agent: temperature=0.3, max_tokens=1024 (deterministic errors)
- Evaluation Agent: temperature=0.4, max_tokens=1536 (clear summaries)

**✓ Redis Configuration**: 24-hour TTL for session contexts, database 0, write-through to filesystem.

**✓ Error Display**: Always show full stack trace and all error details (no truncation), formatted for readability.

**✓ Metadata Extraction**: Read ALL .md files in dataset, combine content, use LLM to extract. Apply reasonable defaults where ambiguous (e.g., "mouse" → species="Mus musculus").

---

## 12. Glossary

- **MCP (Model Context Protocol)**: Communication standard for agent messaging
- **NWB (Neurodata Without Borders)**: Standardized format for neurophysiology data
- **NeuroConv**: Python package for converting various formats to NWB
- **NWB Inspector**: Validation tool that checks NWB file compliance and quality
- **OpenEphys**: Open-source electrophysiology data acquisition system
- **FAIR Principles**: Findable, Accessible, Interoperable, Reusable data standards

---

## 13. References

1. **NWB Format**: https://nwb-schema.readthedocs.io/
2. **NeuroConv**: https://neuroconv.readthedocs.io/
3. **NWB Inspector**: https://github.com/NeurodataWithoutBorders/nwbinspector
4. **Model Context Protocol**: https://modelcontextprotocol.io/
5. **OpenEphys**: https://open-ephys.github.io/gui-docs/
6. **Constitution**: `.specify/memory/constitution.md`

---

## Approval

**Status**: Ready for Planning Phase

**Next Steps**:
1. Run `/plan` to generate implementation plan
2. Run `/tasks` to generate task breakdown
3. Run `/analyze` and `/checklist` quality gates
4. Begin implementation via `/implement`

---

**Specification Complete**
