# Implementation Plan: MCP Server Architecture

**Branch**: `mcp-server-architecture` | **Date**: 2025-10-10 | **Spec**:
[spec.md](./spec.md) **Input**: Feature specification from
`/specs/mcp-server-architecture/spec.md`

## Execution Flow (/plan command scope)

```
1. Load feature spec from Input path
   → Loaded: 55 functional requirements across 8 core categories
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type: single (Python-based MCP server)
   → Set Structure Decision: Hexagonal architecture with core/adapters/agents separation
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → No violations: Full alignment with MCP-centric, TDD, schema-first principles
   → Update Progress Tracking: Initial Constitution Check ✓
5. Execute Phase 0 → research.md
   → All critical architectural patterns identified for research
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
   → Design artifacts for 9 key entities and complete API contracts
7. Re-evaluate Constitution Check section
   → Design maintains constitutional compliance
   → Update Progress Tracking: Post-Design Constitution Check ✓
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by
other commands:

- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

The MCP Server Architecture feature implements a transport-agnostic
orchestration hub for coordinating specialized AI agents (conversation, metadata
questioner, conversion, evaluation) in the agentic neurodata conversion
pipeline. The architecture follows hexagonal (ports-and-adapters) design with
100% business logic in the core service layer, thin transport adapters (<500 LOC
each) for MCP, HTTP, and WebSocket protocols, and comprehensive state management
with checkpoint recovery, distributed tracing, and PROV-O provenance tracking.
The system supports multi-format dataset processing (25+ neuroscience formats),
ensemble validation coordination, DAG-based workflow execution, and
observability through structured logging and OpenTelemetry integration.

## Technical Context

**Language/Version**: Python 3.11+ **Primary Dependencies**: FastAPI 0.104+,
Claude Agent SDK (mcp library), pydantic 2.5+, pydantic-settings 2.1+, structlog
23.2+, rdflib 7.0+ (PROV-O), opentelemetry-api 1.21+, aiohttp 3.9+ (async agent
invocation), tenacity 8.2+ (retry logic), pynwb 2.6+, nwbinspector 0.4+, datalad
0.19+ (Python API only) **Storage**: RDF triple store for provenance (rdflib
with persistent backend), filesystem for checkpoints (atomic writes with
tempfile), in-memory session store (Redis-compatible for production scaling),
SQLite for development/testing **Testing**: pytest 7.4+ with pytest-asyncio,
pytest-cov, contract tests using schemathesis (OpenAPI fuzzing), integration
tests with real agent mocks, e2e tests with DataLad datasets **Target
Platform**: Cross-platform (Linux primary, macOS/Windows support), containerized
deployment (Docker + Kubernetes), Python 3.11-3.13 compatibility **Project
Type**: single (unified Python MCP server with modular internal structure)
**Performance Goals**: 50 datasets/hour throughput on 8-core machine, <5 minutes
P95 latency for <1GB files, <30 seconds P50 for small datasets, <10%
orchestration overhead vs agent execution time **Constraints**: Zero network
dependencies for core operations (ontology services optional), streaming
validation for files >10GB, <2GB memory usage per workflow, agent timeouts
configurable (default 5min per agent, 30min workflow timeout) **Scale/Scope**:
100+ concurrent workflows, 25+ data formats with confidence-based detection,
1TB+ dataset support via streaming, 4 coordinated agents (conversation, metadata
questioner, conversion, evaluation), 8 validation systems integration

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

**Status**: ✅ PASS **Evidence**:

- FR-001 explicitly mandates "transport-agnostic core service layer that
  contains 100% of business logic"
- FR-006 limits transport adapters to 500 LOC with "zero business logic"
- FR-007, FR-008, FR-009 define MCP, HTTP, WebSocket adapters as thin protocol
  handlers
- FR-010 requires functional parity verified through contract tests
- All inter-agent communication flows through MCP server (FR-011 to FR-014)

**Compliance Notes**:

- Core service layer handles all workflow orchestration, state management,
  provenance tracking (FR-001 to FR-005)
- Adapters only perform protocol-specific serialization/deserialization (FR-006)
- Claude Agent SDK handles MCP protocol communication (FR-007)

### II. Test-Driven Development (NON-NEGOTIABLE)

**Status**: ✅ PASS **Evidence**:

- Phase 1 generates contract tests BEFORE implementation (step 3 in plan)
- Phase 2 orders tasks as "Tests before implementation" (TDD order)
- FR-010 requires "comprehensive contract tests that confirm identical service
  method invocations"
- Testing strategy includes unit, integration, contract, and e2e test categories

**Compliance Notes**:

- Contract tests written in Phase 1, must fail initially
- Coverage targets: ≥90% for critical paths (agent coordination, state
  management)
- ≥85% for standard features (format detection, configuration)

### III. Schema-First Development (NON-NEGOTIABLE)

**Status**: ✅ PASS **Evidence**:

- Phase 1 step 1: "Extract entities from feature spec → data-model.md" occurs
  BEFORE implementation
- Phase 1 step 2: "Generate API contracts" with OpenAPI schemas before code
- FR-004 requires PROV-O ontology schema for provenance tracking
- All 9 key entities defined with complete attributes (spec.md lines 306-351)

**Compliance Notes**:

- Pydantic models generated from data-model.md definitions
- OpenAPI contracts define all API endpoints before implementation
- PROV-O RDF schema used for provenance records (FR-004)
- LinkML schemas for NWB metadata validation (FR-034)

### IV. Feature-Driven Architecture & Clear Boundaries (NON-NEGOTIABLE)

**Status**: ✅ PASS **Evidence**:

- Self-contained feature with clear boundaries: no cross-feature dependencies
  except through MCP
- Project structure separates core/adapters/agents/validation/observability
  modules
- FR-006 enforces adapter isolation: "contain zero business logic"
- FR-010 requires contract tests verifying interface boundaries

**Compliance Notes**:

- Feature boundaries: core service layer → transport adapters (via interfaces)
- Agent coordination through defined interfaces (FR-011 to FR-014)
- Each module (agents/, validation/, observability/) has isolated
  responsibilities

### V. Data Integrity & Complete Provenance (NON-NEGOTIABLE)

**Status**: ✅ PASS **Evidence**:

- FR-004 mandates "complete provenance for all data transformations using PROV-O
  ontology"
- FR-033 to FR-042 define comprehensive validation pipeline (NWB Inspector,
  PyNWB, DANDI)
- FR-026 to FR-032 implement state management with checkpoint recovery
- DataLad Python API required for all data operations (spec dependencies line
  392-396)

**Compliance Notes**:

- PROV-O tracking records: agent invocations, workflow decisions, data lineage,
  timing (FR-004)
- Multi-stage validation: NWB Inspector (FR-033), PyNWB (FR-034), DANDI
  (FR-035), custom rules (FR-036)
- Atomic checkpoint writes with validation (FR-027)
- DataLad Python API only (no CLI commands) per project guidelines

### VI. Quality-First Development (NON-NEGOTIABLE)

**Status**: ✅ PASS **Evidence**:

- FR-043 defines structured logging with JSON format and contextual information
- FR-044 to FR-049 specify comprehensive monitoring and observability
- FR-005 implements error handling with circuit breakers, retry logic,
  compensating transactions
- Testing strategy includes contract, integration, unit, e2e tests

**Compliance Notes**:

- Structured logging: JSON format, correlation IDs, log levels (FR-043)
- Error tracking: categorization, stack traces, error context (FR-044)
- Distributed tracing: OpenTelemetry with span tracking (FR-047)
- Quality metrics: conversion metrics, usage analytics (FR-045, FR-046)

### VII. Spec-Kit Workflow Gates (NON-NEGOTIABLE)

**Status**: ✅ PASS **Evidence**:

- This plan follows spec-kit workflow: /specify (spec.md complete) → /plan (this
  file) → /tasks (next step)
- Phase 0 generates research.md for technical decisions
- Phase 1 generates design artifacts (data-model.md, contracts/, quickstart.md)
- Phase 2 description outlines task generation strategy for /tasks command

**Compliance Notes**:

- Plan stops at Phase 2 description, awaiting /tasks command execution
- Constitution check performed twice: initial (Phase 0) and post-design
  (Phase 1)
- Progress tracking section documents gate status
- Complexity tracking section available for any constitutional deviations (none
  identified)

**Overall Assessment**: FULL COMPLIANCE - No constitutional violations, ready
for Phase 0 research.

## Phase 0: Outline & Research

### Research Tasks

The following unknowns and technology choices require research to finalize
Technical Context and inform Phase 1 design decisions:

#### 1. Hexagonal Architecture Patterns for Python

**Unknown**: Best practices for implementing ports-and-adapters in Python
**Research Tasks**:

- Survey existing Python implementations (e.g., Netflix Dispatch, FastAPI
  dependency injection)
- Evaluate interface definition approaches (ABC vs Protocol vs runtime checking)
- Research dependency injection patterns (no heavyweight frameworks, pure Python
  preferred)
- Identify testing strategies for port isolation

**Output**: Decision on interface definition approach and DI pattern for
research.md

#### 2. FastAPI + MCP Protocol Integration

**Unknown**: Integration approach for MCP protocol with FastAPI async patterns
**Research Tasks**:

- Analyze Claude Agent SDK (mcp library) API surface and async support
- Evaluate stdio/socket transport options for MCP server
- Research coexistence of MCP server (stdio) with HTTP server (async event loop
  sharing)
- Investigate MCP tool registration patterns and context management

**Output**: Integration architecture decision with event loop management
strategy

#### 3. DAG Workflow Engines

**Unknown**: Whether to use existing DAG library or custom implementation
**Research Tasks**:

- Compare options: Temporal (heavyweight), Prefect (cloud-focused), Airflow
  (overkill), custom (lightweight)
- Evaluate networkx for graph algorithms (topological sort, cycle detection)
- Research DAG persistence patterns for checkpoint recovery
- Assess async DAG execution patterns with Python asyncio

**Output**: Decision on workflow engine approach (likely custom with networkx
for graph algorithms)

#### 4. State Management Patterns

**Unknown**: Optimal approach for checkpoint/recovery with versioning **Research
Tasks**:

- Evaluate state serialization options (pickle vs JSON vs MessagePack)
- Research atomic write patterns with Python (tempfile, fsync, rename)
- Investigate state versioning strategies (event sourcing vs snapshot-based)
- Assess optimistic locking implementations for concurrent workflows

**Output**: State persistence design with serialization format and atomic write
pattern

#### 5. Distributed Tracing with OpenTelemetry in Python

**Unknown**: OpenTelemetry integration best practices for async Python
**Research Tasks**:

- Survey opentelemetry-api and opentelemetry-sdk usage patterns
- Evaluate context propagation across async boundaries (contextvars)
- Research span creation patterns for agent invocations
- Assess exporter options (Jaeger, Zipkin, stdout for development)

**Output**: Tracing integration design with context propagation strategy

#### 6. Agent Coordination Patterns

**Unknown**: Circuit breaker and retry strategy implementations **Research
Tasks**:

- Evaluate libraries: tenacity (retry), pybreaker (circuit breaker), aiobreaker
  (async)
- Research exponential backoff with jitter algorithms (full jitter vs
  decorrelated jitter)
- Investigate health check patterns for agent availability
- Assess failover strategies (backup instances, degraded mode)

**Output**: Resilience pattern decisions with library choices

#### 7. WebSocket Streaming with FastAPI

**Unknown**: WebSocket protocol design for streaming progress updates **Research
Tasks**:

- Research FastAPI WebSocket support and connection management
- Evaluate message framing protocols (JSON lines vs custom binary)
- Investigate reconnection strategies (client-side vs server-side state)
- Assess backpressure handling for slow clients

**Output**: WebSocket protocol specification and reconnection strategy

#### 8. Plugin Architecture in Python

**Unknown**: Plugin discovery and isolation patterns **Research Tasks**:

- Compare approaches: entry_points (setuptools), importlib.metadata, namespace
  packages
- Research plugin isolation techniques (separate processes vs in-process)
- Evaluate plugin API versioning strategies
- Assess plugin lifecycle management (load, validate, unload)

**Output**: Plugin architecture design with discovery mechanism

#### 9. Format Detection Strategies

**Unknown**: Magic byte libraries and heuristic approaches **Research Tasks**:

- Evaluate libraries: python-magic (libmagic wrapper), filetype (pure Python)
- Research neuroscience format characteristics (SpikeGLX, Open Ephys, etc.)
- Investigate confidence scoring algorithms (multi-factor weighted scoring)
- Assess content sampling strategies for large files

**Output**: Format detection algorithm with confidence calculation

#### 10. RDF/PROV-O Libraries for Python

**Unknown**: Best RDF library for PROV-O provenance tracking **Research Tasks**:

- Compare libraries: rdflib (pure Python, stable), prov (PROV-specific), owlrl
  (reasoning)
- Research PROV-O ontology mapping to Python objects
- Evaluate RDF serialization formats (Turtle vs JSON-LD vs N-Triples)
- Assess query capabilities (SPARQL support, graph traversal)

**Output**: RDF library choice and PROV-O integration pattern

### Research Output Format

All findings will be consolidated in `research.md` using this template:

```markdown
# Research Findings: MCP Server Architecture

## 1. [Technology/Pattern Name]

**Decision**: [Chosen approach]

**Rationale**: [Why chosen over alternatives]

**Alternatives Considered**:

- [Alternative 1]: [Pros/cons, why rejected]
- [Alternative 2]: [Pros/cons, why rejected]

**Implementation Notes**: [Key details, caveats, configuration]

**References**: [Documentation links, GitHub repos, articles]
```

**Output**: research.md with all 10 research tasks completed, resolving all
Technical Context uncertainties

## Phase 1: Design & Contracts

_Prerequisites: research.md complete_

### Step 1: Extract Entities to data-model.md

Extract all 9 key entities from spec.md (lines 306-351) and expand with Pydantic
model definitions:

**Entities to Model**:

1. **ConversionSession** (session_id, user_id, workflow_definition, state,
   checkpoints, timestamps, metadata)
2. **WorkflowDefinition** (workflow_id, name, steps, dependencies,
   configuration, timeout, retry_policy)
3. **AgentInvocation** (invocation_id, agent_type, session_id, request,
   response, status, timestamps, retry_count, error)
4. **FormatDetectionResult** (dataset_path, detected_formats, primary_format,
   confidence_explanation, alternatives, method, file_inventory, metadata_found)
5. **ValidationResult** (file_path, validators_run, issues, quality_scores,
   overall_status, validation_duration, tool-specific results)
6. **ProvenanceRecord** (record_id, entity, activity, agent, used_entities,
   generated_entities, timestamps, attributes)
7. **QualityMetrics** (session_id, completeness_score, correctness_score,
   performance_score, usability_score, overall_quality, metric_details,
   comparison_to_baseline)
8. **ResourceAllocation** (allocation_id, workflow_id, cpu_cores, memory_mb,
   disk_gb, gpu_count, network_bandwidth, timestamps)
9. **ConfigurationSnapshot** (snapshot_id, session_id, configuration,
   created_at, source, version, effective_settings)

**data-model.md Contents**:

- Pydantic model class definition for each entity
- Field types with validation rules (e.g., session_id as UUID, state as Enum)
- Relationships between entities (e.g., AgentInvocation.session_id →
  ConversionSession)
- State machine definitions (e.g., ConversionSession states: ANALYZING →
  COLLECTING_METADATA → CONVERTING → VALIDATING → COMPLETED/FAILED)
- Validation constraints from functional requirements (e.g., timeout > 0,
  confidence 0-100%)

### Step 2: Generate API Contracts

Map functional requirements to API endpoints and generate OpenAPI
specifications:

#### MCP Tools (contracts/mcp-tools.json)

From FR-002, FR-011-014, FR-026-032, FR-033-042:

- `convert-dataset`: Submit dataset for conversion (FR-002)
  - Input: dataset_path, workflow_config (optional)
  - Output: session_id, initial_status
- `get-session-status`: Query workflow progress (FR-031)
  - Input: session_id
  - Output: ConversionSession state, current_step, progress_percentage
- `resume-workflow`: Resume from checkpoint (FR-027)
  - Input: session_id
  - Output: resumed_session_status
- `cancel-workflow`: Terminate workflow (FR-032)
  - Input: session_id
  - Output: cancellation_status
- `validate-nwb-file`: Standalone validation (FR-033-042)
  - Input: file_path, validators (optional)
  - Output: ValidationResult
- `list-active-sessions`: Enumerate sessions (FR-031)
  - Input: filters (optional)
  - Output: list of ConversionSession summaries
- `get-provenance`: Retrieve provenance record (FR-004)
  - Input: session_id
  - Output: ProvenanceRecord in PROV-O RDF

#### HTTP REST API (contracts/openapi.yaml)

Functional parity with MCP tools (FR-010):

- POST /api/v1/conversions (convert-dataset)
- GET /api/v1/conversions/{session_id} (get-session-status)
- POST /api/v1/conversions/{session_id}/resume (resume-workflow)
- DELETE /api/v1/conversions/{session_id} (cancel-workflow)
- POST /api/v1/validations (validate-nwb-file)
- GET /api/v1/conversions (list-active-sessions)
- GET /api/v1/conversions/{session_id}/provenance (get-provenance)
- WebSocket /api/v1/ws/conversions/{session_id} (streaming progress, FR-009)

#### WebSocket Protocol (contracts/websocket-protocol.md)

Message types for bidirectional communication (FR-009):

- Client → Server: `subscribe` (session_id), `unsubscribe`, `ping`
- Server → Client: `progress_update` (workflow step, percentage),
  `status_change` (state transition), `error` (error details), `completed`
  (final result), `pong`

#### PROV-O Schema (contracts/prov-schema.ttl)

RDF schema defining provenance structure (FR-004):

- Entities: Dataset (input), NWBFile (output), IntermediateResult
- Activities: FormatDetection, MetadataCollection, Conversion, Validation
- Agents: ConversationAgent, MetadataQuestionerAgent, ConversionAgent,
  EvaluationAgent
- Relationships: used, wasGeneratedBy, wasAssociatedWith, wasAttributedTo

### Step 3: Generate Contract Tests

Create failing tests that enforce contract compliance:

**Contract Test Files**:

1. `tests/contract/test_mcp_tools_contract.py`:
   - Test each MCP tool against schema definition
   - Validate input/output structure with pydantic
   - Assert error responses match expected format

2. `tests/contract/test_http_api_contract.py`:
   - Use schemathesis to fuzz OpenAPI spec
   - Test all endpoints with valid/invalid inputs
   - Validate response schemas and status codes

3. `tests/contract/test_websocket_protocol_contract.py`:
   - Test WebSocket message framing
   - Validate message schemas for each type
   - Test connection lifecycle (connect, subscribe, disconnect)

4. `tests/contract/test_adapter_parity.py` (FR-010):
   - Invoke same use case via MCP, HTTP, WebSocket
   - Assert identical responses (modulo transport-specific fields)
   - Verify consistent error handling across adapters

**Test Execution**: All contract tests must fail initially (no implementation
yet)

### Step 4: Extract Test Scenarios from User Stories

Map acceptance scenarios (spec.md lines 47-157) to integration tests:

**Integration Test Files**:

1. `test_single_dataset_conversion.py` (Scenario 1):
   - Submit dataset → assert format detection → verify agent coordination →
     check validation → assert quality report

2. `test_multi_format_dataset.py` (Scenario 2):
   - Submit multi-format dataset → assert all formats detected → verify parallel
     processing → check cross-format consistency

3. `test_checkpoint_recovery.py` (Scenario 3):
   - Start workflow → simulate failure mid-execution → assert checkpoint saved →
     resume → verify completion without reprocessing

4. `test_multi_protocol_access.py` (Scenario 4):
   - Start via HTTP → query via MCP → stream via WebSocket → assert state
     consistency

5. `test_validation_failure_handling.py` (Scenario 5):
   - Generate invalid NWB → assert error categorization → attempt automated
     fixes → verify re-validation

6. `test_batch_processing.py` (Scenario 6):
   - Queue 100 datasets → assert priority scheduling → verify fair resource
     allocation → check progress tracking

**Quickstart Test**: Scenario 1 becomes the quickstart.md validation test

### Step 5: Update CLAUDE.md

Execute update script to maintain agent context:

```bash
.specify/scripts/bash/update-agent-context.sh claude
```

**Updates to CLAUDE.md** (incremental, O(1) operation):

- Add new technologies from Technical Context: Claude Agent SDK (mcp),
  OpenTelemetry, tenacity, aiohttp
- Update Active Technologies section with MCP server dependencies
- Add new commands: `pixi run mcp-server` (start MCP server),
  `pixi run pytest tests/contract` (contract tests)
- Update Recent Changes: Add "011-create-a-comprehensive: MCP Server
  Architecture with hexagonal design"
- Preserve manual additions between markers
- Keep under 150 lines for token efficiency

**Output Files from Phase 1**:

- `data-model.md`: 9 Pydantic model definitions with validation rules
- `contracts/openapi.yaml`: Complete HTTP REST API specification
- `contracts/mcp-tools.json`: MCP tool definitions with schemas
- `contracts/websocket-protocol.md`: WebSocket message protocol
- `contracts/prov-schema.ttl`: PROV-O RDF schema
- `tests/contract/*.py`: 4 contract test files (failing initially)
- `tests/integration/*.py`: 6 integration test scenario stubs
- `quickstart.md`: End-to-end example using Scenario 1
- `CLAUDE.md`: Updated with new technologies and commands (at repository root)

## Phase 2: Task Planning Approach

_This section describes what the /tasks command will do - DO NOT execute during
/plan_

### Task Generation Strategy

The /tasks command will generate tasks by processing Phase 1 design artifacts in
TDD order:

#### Input Sources

1. **contracts/** directory: Each endpoint/tool/message → contract test task +
   implementation task
2. **data-model.md**: Each entity → model creation task + validation test task
3. **Integration test stubs**: Each scenario → integration test task +
   supporting logic tasks
4. **Project structure**: Each module
   (core/adapters/agents/validation/observability/formats/configuration) →
   module setup tasks

#### Task Categories

**Category A: Project Setup (Tasks 1-10)**

- T001: Initialize project structure with directories (src/, tests/, cli/,
  docker/)
- T002: Configure pixi environment with all dependencies from Technical Context
- T003: Setup pytest with coverage, asyncio, contract testing plugins
- T004: Configure ruff, mypy, black for code quality
- T005: Setup pre-commit hooks for TDD enforcement
- T006: Create base test fixtures in conftest.py (mock agents, DataLad datasets)
- T007: Initialize git-annex and DataLad for test data management
- T008: Create docker/ directory with Dockerfile and docker-compose.yml
- T009: Generate .gitignore for Python, DataLad, IDE files
- T010: Create CLI entry point skeleton (cli/mcp_server.py)

**Category B: Design Documents (Tasks 11-13)**

- T011: Write data-model.md with 9 Pydantic models (from Step 1)
- T012: Generate contracts/ directory with OpenAPI, MCP tools, WebSocket
  protocol, PROV-O schema (from Step 2)
- T013: Write quickstart.md with end-to-end example (from Step 4)

**Category C: Contract Tests - WRITE FIRST (Tasks 14-28)**

- T014-T017: Write contract tests for 7 MCP tools (test_mcp_tools_contract.py)
- T018-T021: Write HTTP API contract tests with schemathesis
  (test_http_api_contract.py)
- T022-T024: Write WebSocket protocol contract tests
  (test_websocket_protocol_contract.py)
- T025-T028: Write adapter parity tests (test_adapter_parity.py) - FR-010
  verification

**Category D: Core Domain Models (Tasks 29-37)**

- T029: Implement ConversionSession entity with state machine
- T030: Implement WorkflowDefinition entity with DAG validation
- T031: Implement AgentInvocation entity with retry tracking
- T032: Implement FormatDetectionResult entity with confidence scoring
- T033: Implement ValidationResult entity with aggregation logic
- T034: Implement ProvenanceRecord entity with PROV-O serialization
- T035: Implement QualityMetrics entity with weighted scoring
- T036: Implement ResourceAllocation entity with utilization tracking
- T037: Implement ConfigurationSnapshot entity with versioning

**Category E: Core Services (Tasks 38-47)**

- T038: Implement WorkflowOrchestrator with DAG execution (FR-016)
- T039: Implement StateManager with checkpoint recovery (FR-026-032)
- T040: Implement ProvenanceTracker with PROV-O RDF generation (FR-004)
- T041: Implement ErrorHandler with circuit breakers and retry (FR-005)
- T042: Implement ports/ interfaces (agent_port, storage_port, validator_port,
  tracing_port)
- T043: Implement convert_dataset use case (FR-002)
- T044: Implement resume_workflow use case (FR-027)
- T045: Implement query_session_status use case (FR-031)
- T046: Implement cancel_workflow use case (FR-032)
- T047: Implement validate_nwb_file use case (FR-033-042)

**Category F: Agent Coordination (Tasks 48-55)**

- T048: Implement agent registry with health checking (FR-015)
- T049: Implement agent invocation with timeout and retry (FR-017-018)
- T050: Implement DAG orchestrator with parallel execution (FR-016)
- T051: Implement conversation agent client (FR-011)
- T052: Implement metadata questioner agent client (FR-012)
- T053: Implement conversion agent client (FR-013)
- T054: Implement evaluation agent client (FR-014)
- T055: Implement distributed tracing with OpenTelemetry (FR-019)

**Category G: Format Detection (Tasks 56-61)**

- T056: Implement base detector interface with confidence scoring (FR-022)
- T057: Implement electrophysiology detectors (SpikeGLX, Open Ephys, etc.)
  (FR-021)
- T058: Implement imaging detectors (TIFF, HDF5, ScanImage, etc.) (FR-021)
- T059: Implement behavioral detectors (DeepLabCut, SLEAP, video) (FR-021)
- T060: Implement generic detectors (CSV, JSON, MAT) (FR-021)
- T061: Implement NeuroConv interface selector (FR-024-025)

**Category H: Validation Coordination (Tasks 62-68)**

- T062: Implement validation orchestrator with ensemble logic (FR-037)
- T063: Implement NWB Inspector adapter (FR-033)
- T064: Implement PyNWB validator adapter (FR-034)
- T065: Implement DANDI validator adapter (FR-035)
- T066: Implement custom validator plugin system (FR-036)
- T067: Implement progressive validation with streaming (FR-038)
- T068: Implement quality report generator (FR-042)

**Category I: Observability (Tasks 69-73)**

- T069: Implement structured logging with JSON format (FR-043)
- T070: Implement distributed tracing with OpenTelemetry (FR-047)
- T071: Implement metrics collection (FR-045-046)
- T072: Implement health check endpoints (FR-048)
- T073: Implement proactive issue detection (FR-049)

**Category J: Configuration & Plugins (Tasks 74-78)**

- T074: Implement hierarchical config loader (FR-050)
- T075: Implement runtime config updates with hot reload (FR-051)
- T076: Implement feature flags system (FR-052)
- T077: Implement plugin architecture with discovery (FR-053)
- T078: Implement workflow customization with templates (FR-054)

**Category K: Transport Adapters (Tasks 79-84)**

- T079: Implement MCP adapter using Claude Agent SDK (<500 LOC) (FR-007)
- T080: Implement MCP tool registration and serialization (FR-007)
- T081: Implement HTTP adapter with FastAPI (<500 LOC) (FR-008)
- T082: Implement HTTP routers and middleware (FR-008)
- T083: Implement WebSocket adapter with reconnection (<500 LOC) (FR-009)
- T084: Implement WebSocket protocol handler (FR-009)

**Category L: Integration Tests (Tasks 85-90)**

- T085: Implement test_single_dataset_conversion (Scenario 1)
- T086: Implement test_multi_format_dataset (Scenario 2)
- T087: Implement test_checkpoint_recovery (Scenario 3)
- T088: Implement test_multi_protocol_access (Scenario 4)
- T089: Implement test_validation_failure_handling (Scenario 5)
- T090: Implement test_batch_processing (Scenario 6)

**Category M: CLI and Deployment (Tasks 91-95)**

- T091: Implement CLI entry point with argument parsing
- T092: Implement MCP server startup with transport selection (stdio/socket/TCP)
- T093: Implement HTTP server startup with ASGI configuration
- T094: Implement WebSocket server integration with HTTP server
- T095: Create Dockerfile with multi-stage build for production

**Category N: Documentation and Polish (Tasks 96-100)**

- T096: Write comprehensive docstrings for all public APIs
- T097: Generate API documentation from docstrings (Sphinx)
- T098: Create deployment guide (Docker, Kubernetes, bare metal)
- T099: Create operational runbook (monitoring, troubleshooting, scaling)
- T100: Execute quickstart.md validation test with real dataset

### Ordering Strategy

**TDD Order Enforcement**:

1. Contract tests (Category C) BEFORE implementation (Categories D-K)
2. Domain models (Category D) BEFORE services (Category E)
3. Core services (Category E) BEFORE adapters (Category K)
4. Integration tests (Category L) AFTER core implementation
5. CLI/deployment (Category M) AFTER all core features

**Dependency Order**:

- Project setup (Category A) → Design docs (Category B) → All other categories
- Data models (Category D) → Services/Agents/Validation (Categories E-H)
- Ports (T042) → Adapters (Category K)
- Core logic (Categories D-J) → Adapters (Category K)
- Implementation complete → Integration tests (Category L)
- All tests passing → Documentation (Category N)

**Parallelization Opportunities** (mark with [P]):

- Within Category C: Contract test files can be written in parallel
- Within Category D: Domain models are independent ([P] for T029-T037)
- Within Category F: Agent clients are independent ([P] for T051-T054)
- Within Category G: Format detectors are independent ([P] for T057-T060)
- Within Category H: Validator adapters are independent ([P] for T063-T065)
- Within Category K: Transport adapters are independent ([P] for T079, T081,
  T083)

### Task Format

Each task will follow this format:

```
### T[###]: [Task Title]
**Type**: [contract_test|unit_test|implementation|documentation]
**Category**: [A-N category name]
**Dependencies**: T[###], T[###]
**Estimated Effort**: [S|M|L] (Small: <2h, Medium: 2-6h, Large: >6h)
**Parallel**: [Yes|No]

**Description**: [Detailed task description with acceptance criteria]

**Acceptance Criteria**:
- [ ] [Specific outcome 1]
- [ ] [Specific outcome 2]

**Implementation Notes**: [Technical guidance, file paths, key considerations]
```

### Estimated Output

**Total Tasks**: 100 tasks across 14 categories (A-N)

**Task Distribution**:

- Setup: 10 tasks (Category A)
- Design: 3 tasks (Category B)
- Contract Tests: 15 tasks (Category C)
- Core Implementation: 52 tasks (Categories D-J)
- Adapters: 6 tasks (Category K)
- Integration Tests: 6 tasks (Category L)
- CLI/Deployment: 5 tasks (Category M)
- Documentation: 5 tasks (Category N)

**Estimated Timeline**: 12-18 days for full implementation (assuming 1
developer, accounting for parallel tasks)

**Critical Path**: Setup → Design → Contract Tests → Domain Models → Core
Services → Adapters → Integration Tests → Documentation

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan. The
/plan command stops here.

## Phase 3+: Future Implementation

_These phases are beyond the scope of the /plan command_

**Phase 3**: Task execution (/tasks command creates tasks.md with 100 numbered
tasks) **Phase 4**: Implementation (execute tasks.md following TDD workflow: RED
→ GREEN → REFACTOR) **Phase 5**: Validation (all tests passing, quickstart.md
executable, performance benchmarks met)

### Phase 4 Implementation Approach

When implementation begins (after /tasks command), follow this workflow for each
task:

1. **Contract Test Task** (e.g., T014-T028):
   - Write test asserting contract compliance
   - Run test → MUST FAIL (RED)
   - Commit: `[T###] Add contract test for [feature]`

2. **Implementation Task** (e.g., T029-T095):
   - Write minimum code to pass contract test
   - Run test → MUST PASS (GREEN)
   - Refactor for quality (type hints, docstrings, error handling)
   - Commit: `[T###] Implement [feature]`

3. **Integration Test Task** (e.g., T085-T090):
   - Write test exercising multiple components
   - Run test → verify PASS (all dependencies implemented)
   - Commit: `[T###] Add integration test for [scenario]`

### Phase 5 Validation Criteria

Implementation is complete when:

1. **Test Coverage**: ≥90% for core/ and agents/, ≥85% for adapters/ and
   validation/
2. **Contract Tests**: 100% passing, all adapters have functional parity
   (FR-010)
3. **Integration Tests**: All 6 scenarios passing with real agent mocks
4. **E2E Test**: quickstart.md executable with sample dataset, produces valid
   NWB file
5. **Performance**: Meets targets (50 datasets/hour, <5min P95 for <1GB files,
   <10% overhead)
6. **Constitution Compliance**: All 7 constitutional principles verified through
   tests
7. **Documentation**: API docs generated, deployment guide complete, runbook
   written

## Complexity Tracking

_Fill ONLY if Constitution Check has violations that must be justified_

No constitutional violations identified. All requirements align with
MCP-centric, TDD, schema-first, feature-driven, provenance-tracking,
quality-first, and spec-kit workflow principles.

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| N/A       | N/A        | N/A                                  |

## Progress Tracking

_This checklist is updated during execution flow_

**Phase Status**:

- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS (full compliance, no violations)
- [ ] Post-Design Constitution Check: PASS (pending Phase 1 completion)
- [ ] All NEEDS CLARIFICATION resolved (pending Phase 0 research.md)
- [x] Complexity deviations documented (none required)

**Research Tasks Pending** (Phase 0):

- [ ] Hexagonal architecture patterns for Python
- [ ] FastAPI + MCP protocol integration
- [ ] DAG workflow engines (custom vs libraries)
- [ ] State management patterns (checkpoint/recovery)
- [ ] Distributed tracing with OpenTelemetry
- [ ] Agent coordination patterns (circuit breakers, retry)
- [ ] WebSocket streaming with FastAPI
- [ ] Plugin architecture in Python
- [ ] Format detection strategies (magic bytes, heuristics)
- [ ] RDF/PROV-O libraries for Python

**Design Artifacts Pending** (Phase 1):

- [ ] data-model.md (9 Pydantic models)
- [ ] contracts/openapi.yaml (HTTP REST API)
- [ ] contracts/mcp-tools.json (MCP tool definitions)
- [ ] contracts/websocket-protocol.md (WebSocket messages)
- [ ] contracts/prov-schema.ttl (PROV-O RDF schema)
- [ ] Contract test files (4 files, must fail initially)
- [ ] Integration test stubs (6 scenarios)
- [ ] quickstart.md (end-to-end example)
- [ ] CLAUDE.md updated (incremental)

---

_Based on Constitution v0.0.1 - See `.specify/memory/constitution.md`_
_Generated by /plan command on 2025-10-10_
