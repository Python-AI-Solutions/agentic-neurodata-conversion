# Tasks: MCP Server Architecture

**Input**: Design documents from `/specs/mcp-server-architecture/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/
**Branch**: `mcp-server-architecture` **Status**: Ready for implementation

## Execution Flow (main)

```
1. Load plan.md from feature directory
   → Loaded: 55 functional requirements across 8 core categories
   → Extract: Python 3.11+, FastAPI, Claude Agent SDK, hexagonal architecture
2. Load optional design documents:
   → data-model.md: 9 entities (ConversionSession, WorkflowDefinition, etc.)
   → contracts/: MCP tools, OpenAPI, WebSocket protocol, PROV-O schema
   → research.md: Decisions on DAG engines, state management, tracing
3. Generate tasks by category:
   → Setup: 10 tasks (project structure, dependencies, tooling)
   → Design: 3 tasks (data model, contracts, quickstart)
   → Contract Tests: 15 tasks (MCP, HTTP, WebSocket, parity)
   → Core Models: 9 tasks (9 Pydantic entities)
   → Services: 10 tasks (orchestration, state, provenance, use cases)
   → Agent Coordination: 8 tasks (registry, DAG, 4 clients, tracing)
   → Format Detection: 6 tasks (detectors, interface selection)
   → Validation: 7 tasks (orchestrator, adapters, plugins)
   → Observability: 5 tasks (logging, tracing, metrics, health)
   → Configuration: 5 tasks (config loader, plugins, flags)
   → Transport Adapters: 6 tasks (MCP, HTTP, WebSocket)
   → Integration Tests: 6 tasks (6 acceptance scenarios)
   → CLI/Deployment: 5 tasks (CLI, servers, Docker)
   → Documentation: 5 tasks (docstrings, API docs, guides)
4. Apply task rules:
   → Different files = mark [P] for parallel execution
   → Same file = sequential (no [P] marker)
   → Tests before implementation (TDD order enforced)
5. Number tasks sequentially (T001-T100)
6. Generate dependency graph showing critical path
7. Create parallel execution examples for efficiency
8. Validate task completeness:
   → All contracts have tests? YES (15 contract test tasks)
   → All entities have models? YES (9 model tasks)
   → All endpoints implemented? YES (7 MCP tools, 7 HTTP endpoints)
9. Return: SUCCESS (100 tasks ready for execution)
```

## Summary

This feature implements a transport-agnostic MCP server architecture for
orchestrating multi-agent neurodata conversion workflows. The system follows
hexagonal design with 100% business logic in the core, thin adapters (<500 LOC
each) for MCP/HTTP/WebSocket protocols, comprehensive state management with
checkpoint recovery, distributed tracing, and PROV-O provenance tracking.
Implementation follows strict TDD order: contract tests → models → services →
adapters → integration tests → polish.

**Total Tasks**: 100 tasks across 14 categories **Estimated Timeline**: 12-18
days (1 developer) **Critical Path**: Setup → Design → Contract Tests → Domain
Models → Core Services → Adapters → Integration Tests → Documentation **Parallel
Tasks**: 41 tasks can execute in parallel (marked [P])

## Phase 3.1: Project Setup (T001-T010)

- [ ] T001: Create project directory structure with src/mcp_server/ containing
      subdirectories: core/, adapters/, agents/, validation/, observability/,
      formats/, configuration/
- [ ] T002: Initialize pixi environment in pyproject.toml with Python 3.11+ and
      dependencies: fastapi>=0.104, mcp (Claude Agent SDK), pydantic>=2.5,
      pydantic-settings>=2.1, structlog>=23.2, rdflib>=7.0,
      opentelemetry-api>=1.21, aiohttp>=3.9, tenacity>=8.2, pynwb>=2.6,
      nwbinspector>=0.4, datalad>=0.19
- [ ] T003: Configure pytest in pyproject.toml with plugins: pytest-asyncio,
      pytest-cov (coverage targets ≥90% core, ≥85% adapters), schemathesis
      (OpenAPI contract testing)
- [ ] T004: Setup ruff for linting and formatting in pyproject.toml with rules
      for Python 3.11+, line length 100, exclude test fixtures and generated
      code
- [ ] T005: Configure mypy in pyproject.toml for strict type checking with
      Python 3.11+ type hints, disallow untyped defs, require return types
- [ ] T006: Setup pre-commit hooks in .pre-commit-config.yaml with ruff, mypy,
      black, and test execution (contract tests only) to enforce TDD workflow
- [ ] T007: Create tests/conftest.py with base fixtures: mock_agent_clients
      (conversation, metadata questioner, conversion, evaluation),
      mock_dataset_paths, mock_nwb_files, async_test_client (FastAPI)
- [ ] T008: Initialize DataLad dataset for test data using datalad.api (Python
      API only) with subdirectories: test_datasets/, expected_outputs/,
      checkpoints/, provenance/
- [ ] T009: Create docker/ directory with Dockerfile (multi-stage build: builder
      stage for dependencies, runtime stage for execution) and
      docker-compose.yml (MCP server + Redis for session store + OpenTelemetry
      collector)
- [ ] T010: Generate .gitignore with Python cache, pixi environments, IDE
      configs, DataLad annex, pytest cache, coverage reports, and generated
      files

## Phase 3.2: Design Documents (T011-T013)

- [ ] T011: Write specs/mcp-server-architecture/data-model.md with 9 Pydantic
      model definitions: ConversionSession (with state enum: ANALYZING,
      COLLECTING_METADATA, CONVERTING, VALIDATING, COMPLETED, FAILED),
      WorkflowDefinition (with DAG validation), AgentInvocation (with retry
      tracking), FormatDetectionResult (with confidence scoring),
      ValidationResult (with aggregation), ProvenanceRecord (with PROV-O
      serialization), QualityMetrics (with weighted scoring), ResourceAllocation
      (with utilization tracking), ConfigurationSnapshot (with versioning)
- [ ] T012: Generate specs/mcp-server-architecture/contracts/ directory with 4
      files: openapi.yaml (7 HTTP endpoints with schemas), mcp-tools.json (7 MCP
      tools with input/output schemas), websocket-protocol.md (message types and
      lifecycle), prov-schema.ttl (PROV-O RDF ontology definitions)
- [ ] T013: Write specs/mcp-server-architecture/quickstart.md with end-to-end
      example: submit dataset → format detection → metadata collection →
      conversion → validation → quality report (maps to Scenario 1 from spec.md)

## Phase 3.3: Contract Tests - WRITE FIRST (T014-T028)

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation
in Phase 3.4-3.11**

- [ ] T014: [P] Contract test for convert-dataset MCP tool in
      tests/contract/test_mcp_tools_contract.py - assert input schema
      (dataset_path, workflow_config optional), output schema (session_id,
      initial_status), error responses (invalid path, config)
- [ ] T015: [P] Contract test for get-session-status MCP tool in
      tests/contract/test_mcp_tools_contract.py - assert input (session_id),
      output (ConversionSession state, current_step, progress_percentage), error
      (session not found)
- [ ] T016: [P] Contract test for resume-workflow MCP tool in
      tests/contract/test_mcp_tools_contract.py - assert input (session_id),
      output (resumed_session_status), error (no checkpoint, invalid session)
- [ ] T017: [P] Contract test for cancel-workflow MCP tool in
      tests/contract/test_mcp_tools_contract.py - assert input (session_id),
      output (cancellation_status), error (already completed/cancelled)
- [ ] T018: [P] Contract test for validate-nwb-file MCP tool in
      tests/contract/test_mcp_tools_contract.py - assert input (file_path,
      validators optional), output (ValidationResult), error (file not found,
      invalid NWB)
- [ ] T019: [P] Contract test for list-active-sessions MCP tool in
      tests/contract/test_mcp_tools_contract.py - assert input (filters
      optional), output (list of ConversionSession summaries), pagination
      support
- [ ] T020: [P] Contract test for get-provenance MCP tool in
      tests/contract/test_mcp_tools_contract.py - assert input (session_id),
      output (ProvenanceRecord in PROV-O RDF Turtle format), error (session not
      found)
- [ ] T021: [P] HTTP API contract test POST /api/v1/conversions in
      tests/contract/test_http_api_contract.py using schemathesis - fuzz all
      input parameters, validate OpenAPI schema compliance, assert status codes
      (201 success, 400 invalid input, 500 server error)
- [ ] T022: [P] HTTP API contract test GET /api/v1/conversions/{session_id} in
      tests/contract/test_http_api_contract.py using schemathesis - validate
      response schema, assert status codes (200 success, 404 not found)
- [ ] T023: [P] HTTP API contract test POST
      /api/v1/conversions/{session_id}/resume in
      tests/contract/test_http_api_contract.py using schemathesis - validate
      checkpoint resume semantics, assert idempotency
- [ ] T024: [P] HTTP API contract test DELETE /api/v1/conversions/{session_id}
      in tests/contract/test_http_api_contract.py using schemathesis - validate
      cancellation semantics, assert status codes (204 success, 404 not found)
- [ ] T025: [P] WebSocket protocol contract test for connection lifecycle in
      tests/contract/test_websocket_protocol_contract.py - test connect →
      subscribe (session_id) → receive progress_update messages → unsubscribe →
      disconnect, validate message schemas
- [ ] T026: [P] WebSocket protocol contract test for reconnection in
      tests/contract/test_websocket_protocol_contract.py - test disconnect →
      reconnect → resume from last acknowledged message, validate message
      ordering
- [ ] T027: [P] Adapter parity test for convert-dataset use case in
      tests/contract/test_adapter_parity.py - invoke via MCP, HTTP, WebSocket
      and assert identical responses (FR-010 verification)
- [ ] T028: [P] Adapter parity test for error handling in
      tests/contract/test_adapter_parity.py - trigger same error via all three
      adapters and assert equivalent error structures (status, message, details)

## Phase 3.4: Core Domain Models (T029-T037)

**Prerequisites: T014-T028 contract tests written and failing**

- [ ] T029: [P] Implement ConversionSession entity in
      src/mcp_server/core/models/session.py with fields: session_id (UUID),
      user_id (str), workflow_definition (WorkflowDefinition), state (Enum),
      checkpoints (list), timestamps, metadata (dict); behaviors: create(),
      resume(), update_state(), expire(), export()
- [ ] T030: [P] Implement WorkflowDefinition entity in
      src/mcp_server/core/models/workflow.py with fields: workflow_id (UUID),
      name (str), steps (list), dependencies (dict for DAG), configuration
      (dict), timeout (int), retry_policy (dict); behaviors:
      validate_structure() (detect cycles), determine_execution_order()
      (topological sort), identify_parallelizable_steps(),
      calculate_resource_requirements()
- [ ] T031: [P] Implement AgentInvocation entity in
      src/mcp_server/core/models/agent_invocation.py with fields: invocation_id
      (UUID), agent_type (Enum: CONVERSATION, METADATA_QUESTIONER, CONVERSION,
      EVALUATION), session_id (UUID), request (dict), response (dict), status
      (Enum: PENDING, RUNNING, SUCCEEDED, FAILED, TIMEOUT), timestamps,
      retry_count (int), error (str); behaviors: invoke(), cancel(),
      record_trace_span(), collect_metrics()
- [ ] T032: [P] Implement FormatDetectionResult entity in
      src/mcp_server/core/models/format_detection.py with fields: dataset_path
      (Path), detected_formats (list with confidence scores), primary_format
      (str), confidence_explanation (str), alternative_formats (list),
      detection_method (str), file_inventory (list), metadata_found (dict);
      behaviors: rank_formats(), explain_reasoning(), suggest_overrides(),
      export_report()
- [ ] T033: [P] Implement ValidationResult entity in
      src/mcp_server/core/models/validation.py with fields: file_path (Path),
      validators_run (list), issues (list with severity), quality_scores (dict),
      overall_status (Enum: PASS, FAIL, WARNING), validation_duration (float),
      nwb_inspector_results (dict), pynwb_validation_results (dict),
      dandi_readiness_score (float); behaviors: aggregate_issues_by_severity(),
      calculate_composite_score(), generate_report(), compare_with_baseline()
- [ ] T034: [P] Implement ProvenanceRecord entity in
      src/mcp_server/core/models/provenance.py with fields: record_id (UUID),
      entity (str), activity (str), agent (str), used_entities (list),
      generated_entities (list), timestamps, attributes (dict); behaviors:
      serialize_to_prov_o() (RDF Turtle), visualize_graph(), query_lineage(),
      export_formats() (PROV-JSON, PROV-XML), validate_completeness()
- [ ] T035: [P] Implement QualityMetrics entity in
      src/mcp_server/core/models/quality_metrics.py with fields: session_id
      (UUID), completeness_score (float), correctness_score (float),
      performance_score (float), usability_score (float), overall_quality
      (float), metric_details (dict), comparison_to_baseline (dict); behaviors:
      calculate_weighted_scores(), generate_trends(), compare_to_thresholds(),
      recommend_improvements()
- [ ] T036: [P] Implement ResourceAllocation entity in
      src/mcp_server/core/models/resource_allocation.py with fields:
      allocation_id (UUID), workflow_id (UUID), cpu_cores (int), memory_mb
      (int), disk_gb (int), gpu_count (int), network_bandwidth (int),
      timestamps; behaviors: request_resources(), release_resources(),
      monitor_utilization(), detect_contention()
- [ ] T037: [P] Implement ConfigurationSnapshot entity in
      src/mcp_server/core/models/configuration.py with fields: snapshot_id
      (UUID), session_id (UUID), configuration (dict), created_at (datetime),
      source (str), version (str), effective_settings (dict); behaviors:
      capture_current(), apply_to_workflow(), diff_configurations(), rollback(),
      export_for_reproducibility()

## Phase 3.5: Core Services (T038-T047)

**Prerequisites: T029-T037 models implemented**

- [ ] T038: Implement WorkflowOrchestrator service in
      src/mcp_server/core/services/workflow_orchestrator.py with DAG execution
      using networkx for topological sort, parallel step execution with
      asyncio.gather(), dynamic dependency injection, circular dependency
      detection, deadlock prevention; implements FR-016
- [ ] T039: Implement StateManager service in
      src/mcp_server/core/services/state_manager.py with atomic checkpoint
      writes using tempfile+rename, checkpoint validation with checksums,
      checkpoint versioning, incremental checkpointing for large workflows,
      checkpoint pruning; implements FR-026-FR-032
- [ ] T040: Implement ProvenanceTracker service in
      src/mcp_server/core/services/provenance_tracker.py with PROV-O RDF
      generation using rdflib, activity tracking for all agent invocations,
      entity lineage tracking, agent attribution, SPARQL query support;
      implements FR-004
- [ ] T041: Implement ErrorHandler service in
      src/mcp_server/core/services/error_handler.py with circuit breakers using
      pybreaker/aiobreaker, compensating transactions for rollback, retry logic
      with tenacity (exponential backoff + jitter), timeout management, error
      context collection; implements FR-005
- [ ] T042: Implement ports/interfaces in src/mcp_server/core/ports/ with 4
      interface files: agent_port.py (AgentPort protocol: invoke_agent,
      check_health), storage_port.py (StoragePort protocol: save_checkpoint,
      load_checkpoint), validator_port.py (ValidatorPort protocol: validate_nwb,
      aggregate_results), tracing_port.py (TracingPort protocol: create_span,
      propagate_context)
- [ ] T043: Implement convert_dataset use case in
      src/mcp_server/core/use_cases/convert_dataset.py orchestrating
      conversation agent (format detection) → metadata questioner agent
      (metadata collection) → conversion agent (NWB generation) → evaluation
      agent (validation); implements FR-002
- [ ] T044: Implement resume_workflow use case in
      src/mcp_server/core/use_cases/resume_workflow.py loading checkpoint from
      StateManager, reconstructing workflow state, resuming from last successful
      step, maintaining provenance continuity; implements FR-027
- [ ] T045: Implement query_session_status use case in
      src/mcp_server/core/use_cases/query_session_status.py retrieving
      ConversionSession from StateManager, calculating progress percentage,
      determining current step, estimating time remaining; implements FR-031
- [ ] T046: Implement cancel_workflow use case in
      src/mcp_server/core/use_cases/cancel_workflow.py gracefully stopping
      running agents, preserving partial results, updating session state to
      CANCELLED, generating cancellation audit log; implements FR-032
- [ ] T047: Implement validate_nwb_file use case in
      src/mcp_server/core/use_cases/validate_nwb_file.py coordinating NWB
      Inspector, PyNWB, DANDI validators in parallel, aggregating results with
      ensemble logic, generating ValidationResult; implements FR-033-FR-042

## Phase 3.6: Agent Coordination (T048-T055)

**Prerequisites: T038-T047 core services implemented**

- [ ] T048: Implement agent registry in src/mcp_server/agents/registry.py with
      agent discovery, health check endpoints, registration/deregistration APIs,
      agent metadata (capabilities, version, load), load metrics tracking;
      implements FR-015
- [ ] T049: Implement agent invocation logic in
      src/mcp_server/agents/invocation.py with timeout management using
      asyncio.wait_for(), retry logic with tenacity (exponential backoff,
      jitter, max attempts), request prioritization (urgent vs normal), load
      balancing across instances, automatic failover; implements FR-015, FR-017,
      FR-018
- [ ] T050: Implement DAG orchestrator in
      src/mcp_server/agents/dag_orchestrator.py using networkx for graph
      representation, topological sort for execution order, parallel execution
      with asyncio.gather() for independent steps, dynamic dependency
      resolution, progress tracking; implements FR-016
- [ ] T051: [P] Implement conversation agent client in
      src/mcp_server/agents/clients/conversation_agent.py invoking dataset
      analysis endpoint, parsing format detection results with confidence
      scores, extracting structural analysis, handling timeout/retry; implements
      FR-011
- [ ] T052: [P] Implement metadata questioner agent client in
      src/mcp_server/agents/clients/metadata_questioner_agent.py generating
      targeted questions, managing interactive dialogs, validating responses,
      building metadata structures; implements FR-012
- [ ] T053: [P] Implement conversion agent client in
      src/mcp_server/agents/clients/conversion_agent.py providing conversion
      context (format + metadata), monitoring progress with streaming updates,
      handling failures with diagnostics, validating generated NWB files;
      implements FR-013
- [ ] T054: [P] Implement evaluation agent client in
      src/mcp_server/agents/clients/evaluation_agent.py invoking multiple
      validators (NWB Inspector, PyNWB, DANDI), aggregating results, calculating
      quality scores, generating recommendations; implements FR-014
- [ ] T055: Implement distributed tracing in src/mcp_server/agents/tracing.py
      using OpenTelemetry SDK with correlation ID propagation (contextvars),
      span creation for each agent invocation with parent-child relationships,
      span attributes (agent_type, request_id, session_id), trace sampling (1%
      default), exporter configuration (Jaeger/stdout); implements FR-019

## Phase 3.7: Format Detection (T056-T061)

**Prerequisites: T029-T037 models implemented**

- [ ] T056: Implement base detector interface in
      src/mcp_server/formats/detector_base.py with abstract methods:
      detect(dataset_path) → FormatDetectionResult, calculate_confidence() →
      float (0-100), explain_detection() → str; common utilities for file
      extension analysis, magic byte detection, header parsing
- [ ] T057: [P] Implement electrophysiology format detectors in
      src/mcp_server/formats/electrophysiology.py for SpikeGLX (.bin + .meta),
      Open Ephys (.continuous), Blackrock (.nev, .ns\*), Plexon (.plx),
      Neuralynx (.ncs, .nev), Intan (.rhs, .rhd); uses magic bytes + metadata
      file detection; implements FR-021
- [ ] T058: [P] Implement imaging format detectors in
      src/mcp_server/formats/imaging.py for TIFF/TIF (multi-page), HDF5 (.h5,
      .hdf5), ScanImage (.tif with metadata), Bruker (.xml config), Nikon NIS
      (.nd2), Zeiss CZI (.czi); uses header parsing + content sampling;
      implements FR-021
- [ ] T059: [P] Implement behavioral data detectors in
      src/mcp_server/formats/behavioral.py for DeepLabCut (.h5, .csv with
      keypoint names), SLEAP (.slp, .h5 with skeleton), video files (.mp4, .avi,
      .mov with codec detection); uses metadata pattern matching; implements
      FR-021
- [ ] T060: [P] Implement generic format detectors in
      src/mcp_server/formats/generic.py for CSV (delimiter detection), JSON
      (schema inference), MAT-files (.mat with scipy.io), Parquet (.parquet with
      pyarrow); uses content-based analysis; implements FR-021
- [ ] T061: Implement NeuroConv interface selector in
      src/mcp_server/formats/interface_selector.py using confidence-weighted
      matching, capability matrix lookup (NeuroConv interface catalog),
      performance characteristics from historical data, resource requirement
      estimation, quality score history, user preference learning; implements
      FR-024, FR-025

## Phase 3.8: Validation Coordination (T062-T068)

**Prerequisites: T029-T037 models, T042 ports implemented**

- [ ] T062: Implement validation orchestrator in
      src/mcp_server/validation/orchestrator.py with ensemble validation
      (parallel validator execution), result aggregation using weighted voting,
      disagreement detection, validator performance tracking, configurable
      voting strategies; implements FR-037
- [ ] T063: [P] Implement NWB Inspector adapter in
      src/mcp_server/validation/adapters/nwb_inspector_adapter.py wrapping
      nwbinspector.inspect_nwb(), reporting violations with severity levels
      (CRITICAL, BEST_PRACTICE_VIOLATION, BEST_PRACTICE_SUGGESTION), providing
      file location context, tracking check execution time; implements
      ValidatorPort; implements FR-033
- [ ] T064: [P] Implement PyNWB validator adapter in
      src/mcp_server/validation/adapters/pynwb_adapter.py using
      pynwb.validate(), checking schema compliance, validating data types and
      required fields, verifying referential integrity, reporting violations
      with resolution guidance; implements ValidatorPort; implements FR-034
- [ ] T065: [P] Implement DANDI validator adapter in
      src/mcp_server/validation/adapters/dandi_adapter.py using dandi-cli
      validate, checking metadata completeness, validating file
      size/organization, verifying naming conventions, calculating DANDI
      readiness score (0-100%); implements ValidatorPort; implements FR-035
- [ ] T066: Implement custom validator plugin system in
      src/mcp_server/validation/plugin_system.py with plugin discovery
      (entry_points), plugin registration (decorator-based), plugin API
      versioning, plugin lifecycle (load, validate, unload), plugin isolation
      (error handling); implements FR-036, FR-053
- [ ] T067: Implement progressive validation in
      src/mcp_server/validation/progressive.py with incremental validation
      during conversion, early termination on critical errors, partial result
      reporting, streaming validation for large files (>10GB), validation
      caching for repeated checks; implements FR-038
- [ ] T068: Implement quality report generator in
      src/mcp_server/validation/report_generator.py creating executive summaries
      with key metrics, detailed issue listings with remediation, quality score
      breakdowns by category, historical trend comparisons, export formats
      (HTML, PDF, JSON, CSV) using Jinja2 templates; implements FR-042

## Phase 3.9: Observability (T069-T073)

**Prerequisites: T042 ports implemented**

- [ ] T069: [P] Implement structured logging in
      src/mcp_server/observability/logging.py using structlog with JSON
      formatter, log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL), contextual
      information (correlation_id, session_id, user_id), log sampling for
      high-volume events, log aggregation configuration; implements TracingPort
      for log correlation; implements FR-043
- [ ] T070: [P] Implement distributed tracing in
      src/mcp_server/observability/tracing.py using OpenTelemetry SDK with trace
      ID propagation (contextvars), span creation for meaningful operations,
      span attributes (operation_name, parameters, results), trace sampling
      (configurable rate), trace export to Jaeger/Zipkin/stdout; implements
      TracingPort; implements FR-047
- [ ] T071: [P] Implement metrics collection in
      src/mcp_server/observability/metrics.py tracking workflow duration (P50,
      P95, P99), throughput (datasets/hour), resource utilization (CPU, memory,
      disk I/O), success rate (successful/failed workflows), retry statistics,
      agent invocation patterns; exposes Prometheus-compatible metrics endpoint;
      implements FR-045, FR-046
- [ ] T072: [P] Implement health check endpoints in
      src/mcp_server/observability/health.py with liveness check (server
      responding), readiness check (dependencies available: Redis, agents),
      metrics endpoint (/metrics for Prometheus), status page endpoint (/status
      with system info); implements FR-048
- [ ] T073: [P] Implement proactive issue detection in
      src/mcp_server/observability/issue_detection.py with anomaly detection
      (statistical outliers), capacity forecasting (resource trend analysis),
      performance degradation alerts (latency spikes), error rate spike
      detection (threshold-based), predictive maintenance recommendations;
      implements FR-049

## Phase 3.10: Configuration & Plugins (T074-T078)

**Prerequisites: T037 ConfigurationSnapshot model, T066 plugin system**

- [ ] T074: [P] Implement hierarchical config loader in
      src/mcp_server/configuration/config_loader.py using pydantic-settings with
      global defaults (config/defaults.yaml), per-user overrides
      (config/users/{user_id}.yaml), per-workflow settings (runtime),
      environment-based config (development/staging/production), configuration
      inheritance with precedence rules; implements FR-050
- [ ] T075: [P] Implement runtime config updates in
      src/mcp_server/configuration/runtime_updates.py with hot reload (file
      watcher + reload without restart), configuration validation (pydantic
      schema validation), change auditing (log all config changes with
      user/timestamp), rollback capabilities (revert to previous version),
      configuration versioning (semantic versioning); implements FR-051
- [ ] T076: [P] Implement feature flags system in
      src/mcp_server/configuration/feature_flags.py with flag definitions (name,
      description, default value), gradual rollout (percentage-based), A/B
      testing (variant assignment), emergency kill switches (immediate disable),
      user-based targeting (user_id/organization), flag evaluation metrics
      (usage tracking); implements FR-052
- [ ] T077: [P] Implement plugin architecture in
      src/mcp_server/configuration/plugin_architecture.py extending T066 with
      plugin discovery (setuptools entry_points), plugin lifecycle management
      (load, validate, enable, disable, unload), plugin isolation (separate
      error handling), plugin versioning (semver compatibility checks), plugin
      API contracts (stable interfaces); implements FR-053
- [ ] T078: [P] Implement workflow customization in
      src/mcp_server/configuration/workflow_templates.py with workflow templates
      (predefined step sequences), custom step injection (user-defined steps),
      step ordering modification (reorder workflow), conditional step execution
      (runtime predicates), custom agent integration (external agent
      registration); implements FR-054

## Phase 3.11: Transport Adapters (T079-T084)

**Prerequisites: T038-T047 core services, T029-T037 models, contract tests
T014-T028**

- [ ] T079: [P] Implement MCP adapter in src/mcp_server/adapters/mcp_adapter.py
      (<500 LOC) using Claude Agent SDK (mcp library) with stdio transport,
      handling MCP message framing (JSON-RPC), delegating to core services
      (convert_dataset, query_session_status, etc.), zero business logic (pure
      protocol translation); implements FR-006, FR-007
- [ ] T080: Implement MCP tool registration in
      src/mcp_server/adapters/mcp_tool_registration.py registering 7 MCP tools
      from contracts/mcp-tools.json (convert-dataset, get-session-status,
      resume-workflow, cancel-workflow, validate-nwb-file, list-active-sessions,
      get-provenance), mapping tool schemas to service method signatures,
      handling context management; implements FR-007
- [ ] T081: [P] Implement HTTP adapter in
      src/mcp_server/adapters/http_adapter.py (<500 LOC) using FastAPI with
      OpenAPI specification from contracts/openapi.yaml, implementing 7 REST
      endpoints (POST /conversions, GET /conversions/{id}, POST
      /conversions/{id}/resume, DELETE /conversions/{id}, POST /validations, GET
      /conversions, GET /conversions/{id}/provenance), delegating to core
      services, zero business logic; implements FR-006, FR-008
- [ ] T082: Implement HTTP routers and middleware in
      src/mcp_server/adapters/http_routers.py with CORS middleware,
      request/response logging middleware, error handling middleware (format
      errors per OpenAPI), content negotiation middleware (JSON/MessagePack),
      streaming support for large payloads; implements FR-008
- [ ] T083: [P] Implement WebSocket adapter in
      src/mcp_server/adapters/websocket_adapter.py (<500 LOC) using FastAPI
      WebSocket support at /api/v1/ws/conversions/{session_id}, handling
      connection lifecycle (connect, authenticate, disconnect), implementing
      message protocol from contracts/websocket-protocol.md (subscribe,
      progress_update, status_change, error, completed), delegating to core
      services; implements FR-006, FR-009
- [ ] T084: Implement WebSocket protocol handler in
      src/mcp_server/adapters/websocket_protocol.py with message framing (JSON
      lines), reconnection logic (client resumption from last ack), message
      ordering guarantees, backpressure handling (slow client detection +
      throttling), ping/pong keep-alive; implements FR-009

## Phase 3.12: Integration Tests (T085-T090)

**Prerequisites: T079-T084 adapters implemented, all core services implemented**

- [ ] T085: [P] Integration test Scenario 1: Single Dataset Conversion in
      tests/integration/test_single_dataset_conversion.py - submit dataset via
      MCP convert-dataset → assert format detection with confidence > 80% →
      verify conversation agent invoked → verify metadata questioner invoked →
      verify conversion agent invoked → verify evaluation agent invoked → assert
      NWB file generated → assert validation passed → assert quality report with
      DANDI score > 70%
- [ ] T086: [P] Integration test Scenario 2: Multi-Format Dataset in
      tests/integration/test_multi_format_dataset.py - submit dataset with
      electrophysiology + imaging → assert both formats detected → verify
      optimal processing order determined → verify parallel agent execution
      where independent → assert unified NWB file with provenance → verify
      cross-format consistency validation passed
- [ ] T087: [P] Integration test Scenario 3: Checkpoint Recovery in
      tests/integration/test_checkpoint_recovery.py - start workflow with large
      dataset → simulate transient failure mid-conversion (kill conversion
      agent) → assert checkpoint saved with state → resume workflow → verify
      automatic retry with exponential backoff → assert completion without
      reprocessing completed steps → verify provenance includes retry history
- [ ] T088: [P] Integration test Scenario 4: Multi-Protocol Access in
      tests/integration/test_multi_protocol_access.py - start conversion via
      HTTP POST → query status via MCP get-session-status → stream progress via
      WebSocket → assert identical session state across protocols → verify
      equivalent audit logs → assert same quality gates applied
- [ ] T089: [P] Integration test Scenario 5: Validation Failure Handling in
      tests/integration/test_validation_failure_handling.py - submit dataset
      producing invalid NWB → assert validation errors categorized by severity →
      verify automated fix attempts for common issues → assert detailed
      diagnostics with file locations → interact with repair workflow →
      re-validate and assert quality score improved
- [ ] T090: [P] Integration test Scenario 6: Batch Processing in
      tests/integration/test_batch_processing.py - queue 100 datasets via HTTP →
      assert priority-based scheduling (urgent vs normal) → verify resource pool
      management (no agent overload) → verify fair scheduling across workflows →
      assert backpressure applied when agents overwhelmed → check progress
      tracking and ETA for all datasets

## Phase 3.13: CLI and Deployment (T091-T095)

**Prerequisites: T079-T084 adapters, T085-T090 integration tests passing**

- [ ] T091: Implement CLI entry point in cli/mcp_server.py using argparse with
      commands: start (launch server), validate (standalone validation), config
      (show/update configuration), status (server health), version (show version
      info)
- [ ] T092: Implement MCP server startup in src/mcp_server/server/mcp_server.py
      with transport selection (stdio/unix socket/TCP), event loop setup
      (asyncio), agent client initialization, state manager initialization,
      signal handling (SIGTERM, SIGINT for graceful shutdown)
- [ ] T093: Implement HTTP server startup in
      src/mcp_server/server/http_server.py with ASGI configuration (uvicorn),
      middleware registration (CORS, logging, error handling), router mounting
      (REST + WebSocket), health check endpoints, graceful shutdown
- [ ] T094: Implement WebSocket server integration in
      src/mcp_server/server/websocket_server.py integrated with HTTP server from
      T093, connection pool management, message broadcasting to subscribers,
      connection cleanup on disconnect, heartbeat monitoring
- [ ] T095: Create Dockerfile in docker/Dockerfile with multi-stage build:
      builder stage (install dependencies with pixi), runtime stage (copy only
      necessary files, non-root user, expose ports 8000 HTTP + 8001 MCP),
      healthcheck instruction, security best practices (minimal base image, no
      secrets)

## Phase 3.14: Documentation and Polish (T096-T100)

**Prerequisites: All implementation complete (T001-T095)**

- [ ] T096: [P] Write comprehensive docstrings for all public APIs in
      src/mcp_server/ following Google style guide: module-level docstrings
      (purpose, usage examples), class docstrings (attributes, behavior), method
      docstrings (args, returns, raises), type hints for all parameters/returns
- [ ] T097: [P] Generate API documentation in docs/ using Sphinx with autodoc
      extension: API reference (auto-generated from docstrings), architecture
      overview (hexagonal design diagram), data model reference (9 entities with
      relationships), contract reference (OpenAPI/MCP tools/WebSocket protocol),
      plugin development guide (custom validators/agents)
- [ ] T098: Create deployment guide in docs/deployment.md with sections: Docker
      deployment (single container, docker-compose with Redis + OTel),
      Kubernetes deployment (manifests for deployment, service, configmap,
      secret, ingress), bare metal deployment (systemd service, pixi
      environment, reverse proxy nginx/caddy), configuration reference
      (environment variables, config files)
- [ ] T099: Create operational runbook in docs/runbook.md with sections:
      monitoring (key metrics to watch, alert thresholds), troubleshooting
      (common issues and resolutions), scaling (horizontal scaling strategies,
      resource tuning), backup and recovery (checkpoint management, state
      export/import), incident response (escalation procedures)
- [ ] T100: Execute quickstart.md validation test in
      tests/e2e/test_quickstart.py using real sample dataset from DataLad test
      data, following exact steps from quickstart.md, asserting successful
      conversion, validating generated NWB file with nwbinspector, verifying
      quality report generation, measuring performance (P50 latency < 30s for
      small dataset)

## Dependencies

**Critical Path** (tasks that block others):

- T001 (project structure) blocks all implementation tasks
- T002 (pixi dependencies) blocks all Python tasks
- T011-T013 (design docs) block contract tests T014-T028
- T014-T028 (contract tests) must complete before T029-T084 (implementation)
- T029-T037 (models) block T038-T047 (services), T048-T055 (agents), T056-T061
  (formats), T062-T068 (validation)
- T042 (ports) blocks T079-T084 (adapters)
- T038-T047 (services) block T079-T084 (adapters)
- T079-T084 (adapters) block T085-T090 (integration tests)
- All implementation (T029-T084) blocks T091-T095 (CLI/deployment)
- All implementation blocks T096-T100 (documentation)

**Detailed Dependencies by Category**:

- **Setup (T001-T010)**: T001 → all, T002 → all Python tasks, T003-T007 → tests,
  T008 → integration tests
- **Design (T011-T013)**: T011 → models (T029-T037), T012 → contract tests
  (T014-T028), T013 → T100
- **Contract Tests (T014-T028)**: T012 → all contract tests, must fail before
  implementation starts
- **Models (T029-T037)**: T011 → all models, independent within category (can
  parallelize)
- **Services (T038-T047)**: T029-T037 → all services, T038-T041 → use cases
  (T043-T047)
- **Agents (T048-T055)**: T038-T047 → all agent tasks, T048-T050 → clients
  (T051-T054)
- **Formats (T056-T061)**: T029-T037 → all format tasks, T056 → detectors
  (T057-T060)
- **Validation (T062-T068)**: T029-T037 + T042 → all validation tasks, T062 →
  adapters (T063-T065)
- **Observability (T069-T073)**: T042 → all observability tasks, independent
  within category
- **Configuration (T074-T078)**: T037 + T066 → all config tasks, independent
  within category
- **Adapters (T079-T084)**: T038-T047 + T029-T037 + T042 → all adapters, T079 →
  T080, T081 → T082, T083 → T084
- **Integration Tests (T085-T090)**: T079-T084 → all integration tests,
  independent within category
- **CLI/Deployment (T091-T095)**: T079-T084 → all CLI tasks, T092-T094 → T095
- **Documentation (T096-T100)**: T001-T095 → all docs, T096-T097 independent,
  T013 → T100

## Parallel Execution Examples

**Phase 3.1 Parallel Setup** (7 tasks can run simultaneously):

```
T003: Configure pytest
T004: Setup ruff
T005: Configure mypy
T006: Setup pre-commit
T007: Create test fixtures
T009: Create docker files
T010: Generate .gitignore
```

**Phase 3.3 Parallel Contract Tests** (15 tasks can run simultaneously after
T012):

```
T014: Contract test convert-dataset MCP
T015: Contract test get-session-status MCP
T016: Contract test resume-workflow MCP
T017: Contract test cancel-workflow MCP
T018: Contract test validate-nwb-file MCP
T019: Contract test list-active-sessions MCP
T020: Contract test get-provenance MCP
T021: HTTP API contract test POST /conversions
T022: HTTP API contract test GET /conversions/{id}
T023: HTTP API contract test POST /conversions/{id}/resume
T024: HTTP API contract test DELETE /conversions/{id}
T025: WebSocket connection lifecycle test
T026: WebSocket reconnection test
T027: Adapter parity test convert-dataset
T028: Adapter parity test error handling
```

**Phase 3.4 Parallel Model Implementation** (9 tasks can run simultaneously):

```
T029: ConversionSession model
T030: WorkflowDefinition model
T031: AgentInvocation model
T032: FormatDetectionResult model
T033: ValidationResult model
T034: ProvenanceRecord model
T035: QualityMetrics model
T036: ResourceAllocation model
T037: ConfigurationSnapshot model
```

**Phase 3.6 Parallel Agent Clients** (4 tasks can run simultaneously):

```
T051: Conversation agent client
T052: Metadata questioner agent client
T053: Conversion agent client
T054: Evaluation agent client
```

**Phase 3.7 Parallel Format Detectors** (4 tasks can run simultaneously):

```
T057: Electrophysiology detectors
T058: Imaging detectors
T059: Behavioral data detectors
T060: Generic format detectors
```

**Phase 3.8 Parallel Validator Adapters** (3 tasks can run simultaneously):

```
T063: NWB Inspector adapter
T064: PyNWB validator adapter
T065: DANDI validator adapter
```

**Phase 3.9 Parallel Observability** (5 tasks can run simultaneously):

```
T069: Structured logging
T070: Distributed tracing
T071: Metrics collection
T072: Health check endpoints
T073: Proactive issue detection
```

**Phase 3.10 Parallel Configuration** (5 tasks can run simultaneously):

```
T074: Hierarchical config loader
T075: Runtime config updates
T076: Feature flags system
T077: Plugin architecture
T078: Workflow customization
```

**Phase 3.11 Parallel Transport Adapters** (3 tasks can run simultaneously):

```
T079: MCP adapter
T081: HTTP adapter
T083: WebSocket adapter
```

**Phase 3.12 Parallel Integration Tests** (6 tasks can run simultaneously):

```
T085: Test single dataset conversion
T086: Test multi-format dataset
T087: Test checkpoint recovery
T088: Test multi-protocol access
T089: Test validation failure handling
T090: Test batch processing
```

**Phase 3.14 Parallel Documentation** (2 tasks can run simultaneously):

```
T096: Write docstrings
T097: Generate API documentation
```

## Validation Checklist

_GATE: Checked before marking feature complete_

- [ ] All contract tests (T014-T028) were written BEFORE implementation and
      initially failed
- [ ] All 9 entities (T029-T037) have corresponding Pydantic models with
      validation
- [ ] All 7 MCP tools (T014-T020) have contract tests and implementations
- [ ] All 7 HTTP endpoints (T021-T024 + extras) have contract tests and
      implementations
- [ ] WebSocket protocol (T025-T026) has contract tests and implementation
- [ ] Adapter parity (T027-T028, FR-010) verified across MCP, HTTP, WebSocket
- [ ] All 6 integration test scenarios (T085-T090) pass with real agent mocks
- [ ] Quickstart.md (T013, T100) executes successfully with sample dataset
- [ ] Test coverage ≥90% for core/, ≥85% for adapters/, ≥85% for validation/
- [ ] Performance targets met: 50 datasets/hour, P95 < 5min for <1GB, P50 < 30s
      small datasets, <10% orchestration overhead
- [ ] All transport adapters <500 LOC with zero business logic (FR-006)
- [ ] Complete PROV-O provenance tracking for all workflows (FR-004)
- [ ] Distributed tracing with OpenTelemetry integrated (FR-019, FR-047)
- [ ] All 25+ neuroscience formats supported with confidence scoring
      (FR-020-FR-021)
- [ ] Checkpoint recovery working with atomic writes and validation (FR-027)
- [ ] All 7 constitutional principles verified (MCP-centric, TDD, schema-first,
      feature-driven, provenance, quality-first, spec-kit workflow)
- [ ] API documentation generated from docstrings (T097)
- [ ] Deployment guide complete for Docker, Kubernetes, bare metal (T098)
- [ ] Operational runbook written (T099)

## Performance Targets

**Throughput**: 50 datasets/hour on 8-core machine **Latency**: P50 < 30 seconds
for small datasets (<1GB), P95 < 5 minutes for medium datasets (<10GB)
**Orchestration Overhead**: < 10% of total workflow time **Concurrent
Workflows**: Support 100+ concurrent workflows **Memory Usage**: < 2GB per
workflow for standard operations **Resource Utilization**: CPU 60-80% under
load, memory < 80%

## Implementation Timeline Estimate

**Setup & Design (Days 1-2)**: T001-T013 (13 tasks) **Contract Tests (Day 3)**:
T014-T028 (15 tasks, all parallel) **Core Models (Day 4)**: T029-T037 (9 tasks,
all parallel) **Core Services (Days 5-6)**: T038-T047 (10 tasks, sequential with
some parallelism) **Agent Coordination (Days 7-8)**: T048-T055 (8 tasks, clients
parallel) **Format Detection (Day 9)**: T056-T061 (6 tasks, detectors parallel)
**Validation (Day 10)**: T062-T068 (7 tasks, adapters parallel) **Observability
& Config (Day 11)**: T069-T078 (10 tasks, high parallelism) **Transport Adapters
(Day 12)**: T079-T084 (6 tasks, 3 adapters parallel) **Integration Tests
(Day 13)**: T085-T090 (6 tasks, all parallel) **CLI & Deployment (Day 14)**:
T091-T095 (5 tasks, mostly sequential) **Documentation & Polish (Days 15-16)**:
T096-T100 (5 tasks, some parallelism)

**Total Estimated Duration**: 16 days (single developer, accounting for parallel
execution) **With 2 Developers**: 10-12 days (parallel tasks distributed)

## Notes

- **TDD Enforcement**: Pre-commit hooks (T006) will prevent commits without
  passing contract tests
- **Parallel Execution**: 41 tasks marked [P] can execute in parallel, reducing
  timeline by ~40%
- **Critical Path**: Setup → Design → Contract Tests → Models → Services →
  Adapters → Integration → Docs
- **Adapter LOC Limit**: MCP (T079), HTTP (T081), WebSocket (T083) strictly <500
  LOC each (FR-006)
- **DataLad Usage**: Python API only (datalad.api), never CLI commands (per
  project guidelines)
- **Type Safety**: All modules require type hints, mypy strict mode enforced
  (T005)
- **Constitutional Compliance**: All 7 principles enforced through tests and
  architecture reviews
- **Performance Validation**: T100 includes performance benchmarking against
  targets
- **Documentation Quality**: T096 docstrings required for all public APIs before
  T097 can generate docs

---

_Generated by /tasks command on 2025-10-10_ _Based on plan.md v1.0 and spec.md
v1.0_ _Total Tasks: 100 | Parallel Tasks: 41 | Estimated Duration: 16 days (1
dev) | 10-12 days (2 devs)_
