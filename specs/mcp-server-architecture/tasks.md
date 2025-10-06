# Tasks: MCP Server Architecture

**Input**: Design documents from
`C:/Users/shahh/Projects/agentic-neurodata-conversion-2/specs/006-mcp-server-architecture/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)

```
1. Load plan.md from feature directory
   → Extract: Python 3.9-3.11, FastAPI, MCP SDK, SQLAlchemy, pytest
   → Structure: agentic_neurodata_conversion/mcp_server/ with core/, adapters/, models/, agents/, workflows/, observability/
2. Load optional design documents:
   → data-model.md: 6 entities (Workflow, WorkflowStep, AgentRequest, AgentResponse, FormatDetection, ValidationResult)
   → contracts/openapi.yaml: 14 HTTP endpoints
   → contracts/mcp-tools.json: 12 MCP tools
   → quickstart.md: 5 integration test scenarios
3. Generate tasks by category:
   → Setup: project init, dependencies, linting, database migrations
   → Tests First: 14 HTTP contract tests + 12 MCP contract tests + 7 integration tests (ALL [P])
   → Core: 6 models + core services + adapters + agents
   → Integration: DB, observability, error handling
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → All tests before implementation (TDD strict)
   → Different files = mark [P] for parallel
   → Tests must fail before implementation
5. Number tasks T001-T070
6. Generate dependency graph
7. Validate: All contracts tested, all entities modeled, TDD enforced
```

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions

- **Source code**: `agentic_neurodata_conversion/mcp_server/` at repository root
- **Tests**: `tests/` at repository root with contract/, integration/, unit/
  subdirectories

---

## Phase 3.1: Setup

- [ ] T001 Create MCP server directory structure:
      agentic_neurodata_conversion/mcp_server/ with subdirectories: core/,
      core/services/, core/domain/, core/ports/, core/use_cases/, adapters/,
      adapters/mcp/, adapters/http/, adapters/websocket/, adapters/cli/,
      models/, agents/, workflows/, observability/
- [ ] T002 Create test directory structure: tests/contract/,
      tests/contract/http/, tests/contract/mcp/, tests/integration/, tests/unit/
- [ ] T003 [P] Install FastAPI and uvicorn dependencies in pyproject.toml or
      requirements.txt
- [ ] T004 [P] Install MCP SDK dependency (mcp-python or equivalent) in
      pyproject.toml
- [ ] T005 [P] Install SQLAlchemy async dependencies (sqlalchemy[asyncio],
      aiosqlite, asyncpg) in pyproject.toml
- [ ] T006 [P] Install pytest with pytest-asyncio for async testing in
      pyproject.toml dev dependencies
- [ ] T007 [P] Install OpenTelemetry instrumentation packages
      (opentelemetry-api, opentelemetry-sdk,
      opentelemetry-instrumentation-fastapi) in pyproject.toml
- [ ] T008 [P] Configure ruff for linting in pyproject.toml or ruff.toml
- [ ] T009 [P] Configure black for code formatting in pyproject.toml
- [ ] T010 [P] Configure mypy for type checking in pyproject.toml or mypy.ini
- [ ] T011 Initialize Alembic for database migrations in
      agentic_neurodata_conversion/mcp_server/ directory
- [ ] T012 Create initial Alembic migration for workflows and workflow_steps
      tables in alembic/versions/

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY
implementation**

### HTTP Contract Tests (14 tests from openapi.yaml)

- [ ] T013 [P] Contract test POST /api/v1/workflows in
      tests/contract/http/test_workflows_create.py (expects 201 with
      WorkflowResponse, must fail)
- [ ] T014 [P] Contract test GET /api/v1/workflows in
      tests/contract/http/test_workflows_list.py (expects 200 with paginated
      list, must fail)
- [ ] T015 [P] Contract test GET /api/v1/workflows/{workflow_id} in
      tests/contract/http/test_workflows_get.py (expects 200 with
      WorkflowResponse, must fail)
- [ ] T016 [P] Contract test PUT /api/v1/workflows/{workflow_id} in
      tests/contract/http/test_workflows_update.py (expects 200 or 409 conflict,
      must fail)
- [ ] T017 [P] Contract test POST /api/v1/workflows/{workflow_id}/start in
      tests/contract/http/test_workflows_start.py (expects 200 with
      state=analyzing, must fail)
- [ ] T018 [P] Contract test POST /api/v1/workflows/{workflow_id}/cancel in
      tests/contract/http/test_workflows_cancel.py (expects 200 with
      state=cancelled, must fail)
- [ ] T019 [P] Contract test GET /api/v1/workflows/{workflow_id}/steps in
      tests/contract/http/test_workflows_steps.py (expects 200 with steps array,
      must fail)
- [ ] T020 [P] Contract test POST /api/v1/agents/{agent_type}/invoke in
      tests/contract/http/test_agents_invoke.py (expects 200 with
      AgentInvokeResponse, must fail)
- [ ] T021 [P] Contract test GET /api/v1/agents/health in
      tests/contract/http/test_agents_health.py (expects 200 with health status
      array, must fail)
- [ ] T022 [P] Contract test POST /api/v1/formats/detect in
      tests/contract/http/test_formats_detect.py (expects 200 with
      FormatDetectionResponse, must fail)
- [ ] T023 [P] Contract test GET /api/v1/formats/supported in
      tests/contract/http/test_formats_supported.py (expects 200 with formats
      array, must fail)
- [ ] T024 [P] Contract test POST /api/v1/validation/run in
      tests/contract/http/test_validation_run.py (expects 200 with
      ValidationResponse, must fail)
- [ ] T025 [P] Contract test GET /api/v1/validation/{validation_id}/results in
      tests/contract/http/test_validation_results.py (expects 200 with
      ValidationResponse, must fail)
- [ ] T026 [P] Contract test error responses (400, 404, 409, 500) in
      tests/contract/http/test_error_responses.py (must fail)

### MCP Contract Tests (12 tests from mcp-tools.json)

- [ ] T027 [P] Contract test create_workflow MCP tool in
      tests/contract/mcp/test_create_workflow.py (expects workflow_id and state,
      must fail)
- [ ] T028 [P] Contract test get_workflow MCP tool in
      tests/contract/mcp/test_get_workflow.py (expects full workflow object,
      must fail)
- [ ] T029 [P] Contract test list_workflows MCP tool in
      tests/contract/mcp/test_list_workflows.py (expects workflows array with
      pagination, must fail)
- [ ] T030 [P] Contract test start_workflow MCP tool in
      tests/contract/mcp/test_start_workflow.py (expects state=analyzing, must
      fail)
- [ ] T031 [P] Contract test cancel_workflow MCP tool in
      tests/contract/mcp/test_cancel_workflow.py (expects state=cancelled, must
      fail)
- [ ] T032 [P] Contract test get_workflow_steps MCP tool in
      tests/contract/mcp/test_get_workflow_steps.py (expects steps array, must
      fail)
- [ ] T033 [P] Contract test detect_format MCP tool in
      tests/contract/mcp/test_detect_format.py (expects formats_detected and
      confidence_scores, must fail)
- [ ] T034 [P] Contract test list_supported_formats MCP tool in
      tests/contract/mcp/test_list_supported_formats.py (expects formats array,
      must fail)
- [ ] T035 [P] Contract test invoke_agent MCP tool in
      tests/contract/mcp/test_invoke_agent.py (expects success and
      execution_time_ms, must fail)
- [ ] T036 [P] Contract test get_agent_health MCP tool in
      tests/contract/mcp/test_get_agent_health.py (expects agents health array,
      must fail)
- [ ] T037 [P] Contract test run_validation MCP tool in
      tests/contract/mcp/test_run_validation.py (expects validation_id and
      results, must fail)
- [ ] T038 [P] Contract test get_validation_results MCP tool in
      tests/contract/mcp/test_get_validation_results.py (expects validation
      results, must fail)

### Integration Tests (7 tests from quickstart.md scenarios)

- [ ] T039 [P] Integration test: Complete workflow execution from PENDING to
      COMPLETED in tests/integration/test_complete_workflow.py (must fail)
- [ ] T040 [P] Integration test: Format detection before conversion in
      tests/integration/test_format_detection.py (must fail)
- [ ] T041 [P] Integration test: Manual agent invocation in
      tests/integration/test_manual_agent_invocation.py (must fail)
- [ ] T042 [P] Integration test: List and filter workflows by state in
      tests/integration/test_workflow_filtering.py (must fail)
- [ ] T043 [P] Integration test: Standalone NWB validation in
      tests/integration/test_standalone_validation.py (must fail)
- [ ] T044 [P] Integration test: Cancel running workflow in
      tests/integration/test_workflow_cancellation.py (must fail)
- [ ] T045 [P] Integration test: HTTP and MCP adapter parity verification in
      tests/integration/test_adapter_parity.py (must fail)

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models (6 model files)

- [ ] T046 [P] Implement WorkflowState, AgentType, StepStatus,
      ValidationSeverity enums in
      agentic_neurodata_conversion/mcp_server/models/enums.py (makes no tests
      pass yet)
- [ ] T047 [P] Implement Workflow SQLAlchemy model in
      agentic_neurodata_conversion/mcp_server/models/workflow.py (partial: makes
      T013, T015, T027, T028 closer to passing)
- [ ] T048 [P] Implement WorkflowStep SQLAlchemy model in
      agentic_neurodata_conversion/mcp_server/models/workflow_step.py (makes
      T019, T032 closer to passing)
- [ ] T049 [P] Implement AgentRequest and AgentResponse Pydantic models in
      agentic_neurodata_conversion/mcp_server/models/agent.py (makes T020, T035
      closer to passing)
- [ ] T050 [P] Implement FormatDetection and FormatInfo Pydantic models in
      agentic_neurodata_conversion/mcp_server/models/format_detection.py (makes
      T022, T033 closer to passing)
- [ ] T051 [P] Implement ValidationResult and ValidationIssue Pydantic models in
      agentic_neurodata_conversion/mcp_server/models/validation.py (makes T024,
      T037 closer to passing)

### Core Services (Transport-agnostic business logic)

- [ ] T052 Implement WorkflowOrchestrator service in
      agentic_neurodata_conversion/mcp_server/core/services/workflow_orchestrator.py
      (makes T013-T019, T027-T032, T039, T044 pass)
- [ ] T053 Implement AgentCoordinator service in
      agentic_neurodata_conversion/mcp_server/core/services/agent_coordinator.py
      (makes T020, T035, T036, T041 pass)
- [ ] T054 Implement FormatDetector service in
      agentic_neurodata_conversion/mcp_server/core/services/format_detector.py
      (makes T022, T023, T033, T034, T040 pass)
- [ ] T055 Implement ValidatorAggregator service in
      agentic_neurodata_conversion/mcp_server/core/services/validator_aggregator.py
      (makes T024, T025, T037, T038, T043 pass)
- [ ] T056 Implement state transition validation logic in
      agentic_neurodata_conversion/mcp_server/core/domain/state_machine.py
      (makes T016, T017, T018 fully pass)
- [ ] T057 Implement port interfaces (IWorkflowRepository, IAgentPort,
      IFormatDetectorPort, IValidatorPort) in
      agentic_neurodata_conversion/mcp_server/core/ports/

### Adapter Implementations

- [ ] T058 Implement HTTP adapter with FastAPI routes in
      agentic_neurodata_conversion/mcp_server/adapters/http/routes.py (makes all
      T013-T026 pass)
- [ ] T059 Implement MCP adapter with tool handlers in
      agentic_neurodata_conversion/mcp_server/adapters/mcp/handlers.py (makes
      all T027-T038 pass)
- [ ] T060 [P] Implement WebSocket adapter for real-time updates in
      agentic_neurodata_conversion/mcp_server/adapters/websocket/handler.py
- [ ] T061 [P] Implement CLI adapter for command-line usage in
      agentic_neurodata_conversion/mcp_server/adapters/cli/commands.py

### Agent Implementations

- [ ] T062 [P] Implement ConversationAgent (format detection) in
      agentic_neurodata_conversion/mcp_server/agents/conversation_agent.py
- [ ] T063 [P] Implement ConversionAgent (script generation) in
      agentic_neurodata_conversion/mcp_server/agents/conversion_agent.py
- [ ] T064 [P] Implement EvaluationAgent (validation) in
      agentic_neurodata_conversion/mcp_server/agents/evaluation_agent.py
- [ ] T065 [P] Implement MetadataQuestionerAgent (metadata collection) in
      agentic_neurodata_conversion/mcp_server/agents/metadata_questioner_agent.py

---

## Phase 3.4: Integration

- [ ] T066 Configure SQLAlchemy async engine and session factory in
      agentic_neurodata_conversion/mcp_server/core/database.py (makes T045 pass
      with DB persistence)
- [ ] T067 Implement OpenTelemetry instrumentation in
      agentic_neurodata_conversion/mcp_server/observability/tracing.py
- [ ] T068 Implement error handling middleware for HTTP adapter in
      agentic_neurodata_conversion/mcp_server/adapters/http/middleware.py (makes
      T026 fully pass)
- [ ] T069 Implement circuit breaker for agent invocations in
      agentic_neurodata_conversion/mcp_server/core/services/circuit_breaker.py
- [ ] T070 Implement health check endpoints in
      agentic_neurodata_conversion/mcp_server/adapters/http/health.py (makes
      T021, T036 fully pass)

---

## Phase 3.5: Polish

- [ ] T071 [P] Unit tests for state machine validation logic in
      tests/unit/test_state_machine.py
- [ ] T072 [P] Unit tests for optimistic locking (version checks) in
      tests/unit/test_optimistic_locking.py
- [ ] T073 [P] Unit tests for format detection layers in
      tests/unit/test_format_detection_layers.py
- [ ] T074 [P] Unit tests for validation severity aggregation in
      tests/unit/test_validation_aggregation.py
- [ ] T075 Performance test: API latency <100ms in
      tests/performance/test_api_latency.py
- [ ] T076 Performance test: Workflow startup <2s in
      tests/performance/test_workflow_startup.py
- [ ] T077 Performance test: 10+ concurrent workflows in
      tests/performance/test_concurrent_workflows.py
- [ ] T078 [P] Update API documentation with examples in docs/api-examples.md
- [ ] T079 [P] Create deployment guide in docs/deployment.md
- [ ] T080 Run ruff check and fix any linting issues across
      agentic_neurodata_conversion/mcp_server/
- [ ] T081 Run mypy and fix type checking errors across
      agentic_neurodata_conversion/mcp_server/
- [ ] T082 Review and remove code duplication in service layer

---

## Dependencies

**Setup Phase:**

- T001 blocks T002-T012 (need directory structure)
- T011 blocks T012 (Alembic init before migrations)

**Tests First Phase (TDD Critical):**

- T001-T012 block T013-T045 (setup must complete before tests)
- T013-T045 (ALL tests) block T046-T065 (NO implementation before tests fail)

**Core Implementation Phase:**

- T046 (enums) blocks T047-T051 (models need enums)
- T047-T051 (models) block T052-T057 (services need models)
- T052-T057 (core services) block T058-T061 (adapters need services)
- T052-T057 (core services) block T062-T065 (agents called by services)

**Integration Phase:**

- T047, T048 (DB models) block T066 (DB setup needs models)
- T058, T059 (adapters) block T067, T068 (middleware needs adapters)
- T053 (agent coordinator) block T069 (circuit breaker wraps agent calls)
- T053 (agent coordinator) block T070 (health checks query agents)

**Polish Phase:**

- T056 blocks T071 (state machine tests need implementation)
- T047 blocks T072 (optimistic locking tests need Workflow model)
- T054 blocks T073 (format detection tests need service)
- T055 blocks T074 (validation tests need aggregator)
- T058, T059 block T075-T077 (performance tests need adapters)
- T080-T082 run independently after all implementation

---

## Parallel Execution Examples

### Setup Phase (T003-T010 can run together):

```
Task: "Install FastAPI and uvicorn dependencies"
Task: "Install MCP SDK dependency"
Task: "Install SQLAlchemy async dependencies"
Task: "Install pytest with pytest-asyncio"
Task: "Install OpenTelemetry instrumentation packages"
Task: "Configure ruff for linting"
Task: "Configure black for code formatting"
Task: "Configure mypy for type checking"
```

### Tests First - HTTP Contracts (T013-T026 can run together):

```
Task: "Contract test POST /api/v1/workflows"
Task: "Contract test GET /api/v1/workflows"
Task: "Contract test GET /api/v1/workflows/{workflow_id}"
Task: "Contract test PUT /api/v1/workflows/{workflow_id}"
Task: "Contract test POST /api/v1/workflows/{workflow_id}/start"
Task: "Contract test POST /api/v1/workflows/{workflow_id}/cancel"
Task: "Contract test GET /api/v1/workflows/{workflow_id}/steps"
Task: "Contract test POST /api/v1/agents/{agent_type}/invoke"
Task: "Contract test GET /api/v1/agents/health"
Task: "Contract test POST /api/v1/formats/detect"
Task: "Contract test GET /api/v1/formats/supported"
Task: "Contract test POST /api/v1/validation/run"
Task: "Contract test GET /api/v1/validation/{validation_id}/results"
Task: "Contract test error responses (400, 404, 409, 500)"
```

### Tests First - MCP Contracts (T027-T038 can run together):

```
Task: "Contract test create_workflow MCP tool"
Task: "Contract test get_workflow MCP tool"
Task: "Contract test list_workflows MCP tool"
Task: "Contract test start_workflow MCP tool"
Task: "Contract test cancel_workflow MCP tool"
Task: "Contract test get_workflow_steps MCP tool"
Task: "Contract test detect_format MCP tool"
Task: "Contract test list_supported_formats MCP tool"
Task: "Contract test invoke_agent MCP tool"
Task: "Contract test get_agent_health MCP tool"
Task: "Contract test run_validation MCP tool"
Task: "Contract test get_validation_results MCP tool"
```

### Tests First - Integration Tests (T039-T045 can run together):

```
Task: "Integration test: Complete workflow execution from PENDING to COMPLETED"
Task: "Integration test: Format detection before conversion"
Task: "Integration test: Manual agent invocation"
Task: "Integration test: List and filter workflows by state"
Task: "Integration test: Standalone NWB validation"
Task: "Integration test: Cancel running workflow"
Task: "Integration test: HTTP and MCP adapter parity verification"
```

### Core Implementation - Models (T046-T051 can run together after T046):

```
Task: "Implement Workflow SQLAlchemy model"
Task: "Implement WorkflowStep SQLAlchemy model"
Task: "Implement AgentRequest and AgentResponse Pydantic models"
Task: "Implement FormatDetection and FormatInfo Pydantic models"
Task: "Implement ValidationResult and ValidationIssue Pydantic models"
```

### Core Implementation - Agents (T062-T065 can run together):

```
Task: "Implement ConversationAgent (format detection)"
Task: "Implement ConversionAgent (script generation)"
Task: "Implement EvaluationAgent (validation)"
Task: "Implement MetadataQuestionerAgent (metadata collection)"
```

### Polish - Unit Tests (T071-T074 can run together):

```
Task: "Unit tests for state machine validation logic"
Task: "Unit tests for optimistic locking (version checks)"
Task: "Unit tests for format detection layers"
Task: "Unit tests for validation severity aggregation"
```

### Polish - Documentation (T078-T079 can run together):

```
Task: "Update API documentation with examples"
Task: "Create deployment guide"
```

---

## Notes

- **[P] tasks** = different files, no dependencies, can execute in parallel
- **TDD Critical Path**: ALL tests (T013-T045) MUST be written and MUST FAIL
  before ANY implementation (T046-T065)
- **Verify tests fail** before implementing corresponding functionality
- **Commit after each task** for atomic progress tracking
- **Avoid**: vague tasks, same file conflicts, implementation before tests
- **Test-to-Implementation mapping**:
  - T013-T026 (HTTP contracts) → T058 (HTTP adapter)
  - T027-T038 (MCP contracts) → T059 (MCP adapter)
  - T039-T045 (integration) → T052-T065 (services + agents)

---

## Task Generation Rules Applied

1. **From Contracts**:
   - 14 HTTP endpoints → 14 contract test tasks (T013-T026) [P]
   - 12 MCP tools → 12 contract test tasks (T027-T038) [P]
   - Each contract → corresponding implementation task

2. **From Data Model**:
   - 6 entities → 6 model creation tasks (T046-T051) [P]
   - State machine → validation logic task (T056)
   - Relationships → service layer tasks (T052-T055)

3. **From Quickstart Scenarios**:
   - 5 main scenarios + 2 advanced → 7 integration tests (T039-T045) [P]
   - Each scenario validates end-to-end functionality

4. **Ordering Enforced**:
   - Setup (T001-T012) → Tests (T013-T045) → Models (T046-T051) → Services
     (T052-T057) → Adapters (T058-T061) → Agents (T062-T065) → Integration
     (T066-T070) → Polish (T071-T082)
   - Dependencies strictly block parallel execution where needed

---

## Validation Checklist

_GATE: Checked before task execution_

- [x] All contracts have corresponding tests (14 HTTP + 12 MCP = 26 contract
      tests)
- [x] All entities have model tasks (6 models: Workflow, WorkflowStep,
      AgentRequest/Response, FormatDetection, ValidationResult)
- [x] All tests come before implementation (T013-T045 before T046-T065)
- [x] Parallel tasks truly independent (different files, no shared state)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] TDD principle enforced: tests must fail before implementation
- [x] Integration tests cover all quickstart scenarios
- [x] Performance requirements tested (<100ms latency, <2s startup, 10+
      concurrent)
- [x] All adapters (HTTP, MCP, WebSocket, CLI) have implementation tasks
- [x] All 4 agent types have implementation tasks

---

**Total Tasks**: 82 **Parallel Opportunities**: 54 tasks marked [P] **Estimated
Completion**: 4-6 weeks for complete implementation **Critical Path**: T001 →
T013-T045 (tests) → T046-T065 (implementation) → T066-T070 (integration) →
T071-T082 (polish)
