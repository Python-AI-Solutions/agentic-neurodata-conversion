# Tasks: Agent-Based Neurodata Conversion System

**Input**: Design documents from `/specs/004-implement-an-agent/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/openapi.yaml

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: Python 3.12+, FastAPI, MCP, pynwb, neuroconv, asyncio
2. Load optional design documents:
   → data-model.md: 8 entities → model tasks
   → contracts/openapi.yaml: 10 endpoints → contract test tasks
   → research.md: MCP-based agent, asyncio orchestration
3. Generate tasks by category:
   → Setup: project structure, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, agents, services, API endpoints
   → Integration: workflows, tool adapters, validation
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests? ✓
   → All entities have models? ✓
   → All endpoints implemented? ✓
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: Repository root contains `agentic_neurodata_conversion/` and `tests/`
- Paths shown below use this structure per implementation plan

## Phase 3.1: Setup & Configuration
- [ ] **T001** Create agent module structure in `agentic_neurodata_conversion/agent/` with `__init__.py`, `base.py`, `conversation.py`, `decision.py`, `orchestrator.py`
- [ ] **T002** Create models module structure in `agentic_neurodata_conversion/models/` with `__init__.py`, `task.py`, `workflow.py`, `profile.py`, `validation.py`, `metrics.py`
- [ ] **T003** Create services module structure in `agentic_neurodata_conversion/services/` with `__init__.py`, `task_manager.py`, `tool_selector.py`, `validator.py`, `nlp_processor.py`
- [ ] **T004** Create API module structure in `agentic_neurodata_conversion/api/` with `__init__.py`, `conversation.py`, `tasks.py`, `workflows.py`, `metrics.py`
- [ ] **T005** Create test directory structure with `tests/contract/`, `tests/integration/`, `tests/unit/agent/`, `tests/unit/models/`, `tests/unit/services/`
- [ ] **T006** [P] Configure pytest with asyncio plugin in `pyproject.toml` or `pytest.ini`
- [ ] **T007** [P] Set up test fixtures for mock data in `tests/conftest.py`

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (API Endpoints)
- [ ] **T008** [P] Contract test POST /conversation in `tests/contract/test_conversation_api.py`
- [ ] **T009** [P] Contract test GET /conversation/{id} in `tests/contract/test_conversation_api.py`
- [ ] **T010** [P] Contract test POST /conversation/{id} in `tests/contract/test_conversation_api.py`
- [ ] **T011** [P] Contract test POST /tasks in `tests/contract/test_task_api.py`
- [ ] **T012** [P] Contract test GET /tasks in `tests/contract/test_task_api.py`
- [ ] **T013** [P] Contract test GET /tasks/{id} in `tests/contract/test_task_api.py`
- [ ] **T014** [P] Contract test DELETE /tasks/{id} in `tests/contract/test_task_api.py`
- [ ] **T015** [P] Contract test GET /tasks/{id}/status in `tests/contract/test_task_api.py`
- [ ] **T016** [P] Contract test POST /workflows/execute in `tests/contract/test_workflow_api.py`
- [ ] **T017** [P] Contract test GET /metrics in `tests/contract/test_metrics_api.py`

### Integration Tests (User Stories)
- [ ] **T018** [P] Integration test: Natural language conversion request → tool selection → execution → validation in `tests/integration/test_agent_workflow.py`
- [ ] **T019** [P] Integration test: Status query during conversion → progress report in `tests/integration/test_status_monitoring.py`
- [ ] **T020** [P] Integration test: Multiple queued tasks → FIFO execution in `tests/integration/test_task_queue.py`
- [ ] **T021** [P] Integration test: Conversion failure → error recovery → user notification in `tests/integration/test_error_handling.py`
- [ ] **T022** [P] Integration test: Informal data description → clarifying questions → requirements gathering in `tests/integration/test_clarification.py`
- [ ] **T023** [P] Integration test: Tool adapter subprocess isolation and timeout in `tests/integration/test_tool_integration.py`

## Phase 3.3: Core Implementation - Data Models (ONLY after tests are failing)
- [ ] **T024** [P] ConversionTask model with status enum and state transitions in `agentic_neurodata_conversion/models/task.py`
- [ ] **T025** [P] Workflow and WorkflowStep models with retry policy in `agentic_neurodata_conversion/models/workflow.py`
- [ ] **T026** [P] DataProfile model with quality indicators in `agentic_neurodata_conversion/models/profile.py`
- [ ] **T027** [P] AgentDecision and Alternative models in `agentic_neurodata_conversion/models/decision.py`
- [ ] **T028** [P] ValidationReport and SchemaError models in `agentic_neurodata_conversion/models/validation.py`
- [ ] **T029** [P] ConversationContext and Message models in `agentic_neurodata_conversion/models/conversation.py`
- [ ] **T030** [P] ResourceConfiguration model in `agentic_neurodata_conversion/models/resource_config.py`
- [ ] **T031** [P] MetricsAggregate model in `agentic_neurodata_conversion/models/metrics.py`
- [ ] **T032** [P] ErrorRecord and RetryPolicy embedded models in `agentic_neurodata_conversion/models/common.py`

## Phase 3.4: Core Implementation - Agent Framework
- [ ] **T033** Base agent interface (perceive, decide, act cycle) in `agentic_neurodata_conversion/agent/base.py`
- [ ] **T034** Conversation agent for NLP and intent classification in `agentic_neurodata_conversion/agent/conversation.py` (depends on T033)
- [ ] **T035** Decision agent for recording reasoning and alternatives in `agentic_neurodata_conversion/agent/decision.py` (depends on T033)
- [ ] **T036** Orchestrator agent for workflow coordination in `agentic_neurodata_conversion/agent/orchestrator.py` (depends on T033)

## Phase 3.5: Core Implementation - Services
- [ ] **T037** [P] NLP processor with pattern matching and LLM fallback in `agentic_neurodata_conversion/services/nlp_processor.py`
- [ ] **T038** [P] Tool selector service with adapter pattern in `agentic_neurodata_conversion/services/tool_selector.py`
- [ ] **T039** [P] NWB validator service using nwbinspector in `agentic_neurodata_conversion/services/validator.py`
- [ ] **T040** Task manager service with asyncio queue and FIFO scheduling in `agentic_neurodata_conversion/services/task_manager.py` (depends on T024, T030)
- [ ] **T041** Data profiler service for format detection in `agentic_neurodata_conversion/services/profiler.py` (depends on T026)
- [ ] **T042** State persistence service (JSON file-based) in `agentic_neurodata_conversion/services/persistence.py`

## Phase 3.6: Core Implementation - API Endpoints
- [ ] **T043** POST /conversation endpoint (start conversation) in `agentic_neurodata_conversion/api/conversation.py` (depends on T034)
- [ ] **T044** GET /conversation/{id} endpoint in `agentic_neurodata_conversion/api/conversation.py` (depends on T034)
- [ ] **T045** POST /conversation/{id} endpoint (continue conversation) in `agentic_neurodata_conversion/api/conversation.py` (depends on T034)
- [ ] **T046** POST /tasks endpoint (create task) in `agentic_neurodata_conversion/api/tasks.py` (depends on T040)
- [ ] **T047** GET /tasks endpoint (list tasks) in `agentic_neurodata_conversion/api/tasks.py` (depends on T040)
- [ ] **T048** GET /tasks/{id} endpoint (get task details) in `agentic_neurodata_conversion/api/tasks.py` (depends on T040)
- [ ] **T049** DELETE /tasks/{id} endpoint (cancel task) in `agentic_neurodata_conversion/api/tasks.py` (depends on T040)
- [ ] **T050** GET /tasks/{id}/status endpoint in `agentic_neurodata_conversion/api/tasks.py` (depends on T040)
- [ ] **T051** POST /workflows/execute endpoint in `agentic_neurodata_conversion/api/workflows.py` (depends on T036)
- [ ] **T052** GET /metrics endpoint with weekly aggregation in `agentic_neurodata_conversion/api/metrics.py` (depends on T031)

## Phase 3.7: Integration - Workflow & Tool Adapters
- [ ] **T053** Workflow executor with state machine pattern in `agentic_neurodata_conversion/workflows/executor.py` (depends on T025, T036)
- [ ] **T054** [P] pynwb tool adapter with subprocess isolation in `agentic_neurodata_conversion/adapters/pynwb_adapter.py`
- [ ] **T055** [P] neuroconv tool adapter with subprocess isolation in `agentic_neurodata_conversion/adapters/neuroconv_adapter.py`
- [ ] **T056** Tool registry and version management in `agentic_neurodata_conversion/adapters/registry.py` (depends on T054, T055)
- [ ] **T057** Workflow builder from DataProfile to tool selection in `agentic_neurodata_conversion/workflows/builder.py` (depends on T038, T053)

## Phase 3.8: Integration - Error Handling & Notifications
- [ ] **T058** Error recovery logic with retry policies in `agentic_neurodata_conversion/services/error_handler.py` (depends on T032)
- [ ] **T059** User-friendly error message formatter in `agentic_neurodata_conversion/services/error_formatter.py`
- [ ] **T060** In-system notification service in `agentic_neurodata_conversion/services/notifier.py`
- [ ] **T061** Notification endpoint for external integration in `agentic_neurodata_conversion/api/notifications.py` (depends on T060)

## Phase 3.9: Integration - FastAPI Application Setup
- [ ] **T062** FastAPI app initialization with CORS and middleware in `agentic_neurodata_conversion/api/app.py`
- [ ] **T063** Router registration for all endpoints in `agentic_neurodata_conversion/api/app.py` (depends on T043-T052, T061)
- [ ] **T064** Request/response logging middleware in `agentic_neurodata_conversion/api/middleware.py`
- [ ] **T065** Error handling middleware with proper HTTP status codes in `agentic_neurodata_conversion/api/middleware.py`

## Phase 3.10: Polish - Testing & Validation
- [ ] **T066** [P] Unit tests for ConversationAgent in `tests/unit/agent/test_conversation.py`
- [ ] **T067** [P] Unit tests for DecisionAgent in `tests/unit/agent/test_decision.py`
- [ ] **T068** [P] Unit tests for Orchestrator in `tests/unit/agent/test_orchestrator.py`
- [ ] **T069** [P] Unit tests for TaskManager FIFO queue in `tests/unit/services/test_task_manager.py`
- [ ] **T070** [P] Unit tests for ToolSelector in `tests/unit/services/test_tool_selector.py`
- [ ] **T071** [P] Unit tests for NLPProcessor pattern matching in `tests/unit/services/test_nlp_processor.py`
- [ ] **T072** [P] Unit tests for state persistence in `tests/unit/services/test_persistence.py`
- [ ] **T073** Performance test: API response times <500ms for conversation, <200ms for status in `tests/integration/test_performance.py`
- [ ] **T074** Performance test: Concurrent task execution within resource limits in `tests/integration/test_concurrency.py`
- [ ] **T075** Run quickstart.md scenarios as end-to-end validation

## Phase 3.11: Polish - Documentation & Cleanup
- [ ] **T076** [P] Add docstrings to all agent classes following Google style
- [ ] **T077** [P] Add docstrings to all service classes following Google style
- [ ] **T078** [P] Add docstrings to all API endpoints following OpenAPI annotations
- [ ] **T079** [P] Update CLAUDE.md or project README with agent architecture overview
- [ ] **T080** Remove code duplication in API endpoints (extract common logic)
- [ ] **T081** Remove code duplication in model validation (extract validators)
- [ ] **T082** Final code quality check: run `ruff check .` and fix issues
- [ ] **T083** Final type check: run `mypy agentic_neurodata_conversion/` and fix issues

## Dependencies
```
Setup (T001-T007)
  ↓
Contract Tests (T008-T017) + Integration Tests (T018-T023)
  ↓
Models (T024-T032) [all parallel]
  ↓
Agent Framework (T033 → T034,T035,T036)
  ↓
Services (T037-T042) [T037-T039 parallel, T040-T042 sequential]
  ↓
API Endpoints (T043-T052) [by module]
  ↓
Workflows & Adapters (T053-T057)
  ↓
Error Handling (T058-T061)
  ↓
FastAPI Setup (T062-T065)
  ↓
Testing & Validation (T066-T075)
  ↓
Documentation & Cleanup (T076-T083)
```

## Parallel Execution Examples

### Batch 1: Contract Tests for Conversation API
```bash
# T008, T009, T010 can run in parallel (same file, but independent test functions)
pytest tests/contract/test_conversation_api.py::test_post_conversation \
  tests/contract/test_conversation_api.py::test_get_conversation \
  tests/contract/test_conversation_api.py::test_continue_conversation -v
```

### Batch 2: Contract Tests for Task API
```bash
# T011-T015 can run in parallel
pytest tests/contract/test_task_api.py -v
```

### Batch 3: All Integration Tests
```bash
# T018-T023 can all run in parallel (different files)
pytest tests/integration/ -n 6 -v
```

### Batch 4: All Data Models
```bash
# T024-T032 can all run in parallel (different files)
# Create all model files simultaneously
```

### Batch 5: Parallel Services
```bash
# T037, T038, T039 can run in parallel (different files, no dependencies)
```

### Batch 6: Unit Tests
```bash
# T066-T072 can all run in parallel
pytest tests/unit/ -n auto -v
```

## Notes
- [P] tasks = different files OR independent test functions in same file, no dependencies
- Verify tests fail before implementing (Red-Green-Refactor)
- Commit after each task or logical batch
- Agent framework (T033-T036) is sequential: base → conversation/decision/orchestrator
- API endpoints (T043-T052) grouped by module (conversation, tasks, workflows, metrics)
- Tool adapters (T054-T055) are parallel, registry (T056) depends on them

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts** (openapi.yaml):
   - 10 endpoints → 10 contract test tasks (T008-T017) [P]
   - 10 endpoints → 10 implementation tasks (T043-T052)

2. **From Data Model**:
   - 8 core entities → 8 model creation tasks (T024-T031) [P]
   - 2 embedded models → 1 common models task (T032) [P]

3. **From User Stories** (quickstart.md):
   - 5 scenarios + 1 tool integration → 6 integration tests (T018-T023) [P]
   - Primary scenario → end-to-end validation (T075)

4. **From Research** (research.md):
   - Agent framework → 4 tasks (T033-T036) sequential
   - Services → 6 tasks (T037-T042) mixed parallel/sequential
   - Tool adapters → 4 tasks (T054-T057)

5. **Ordering**:
   - Setup (T001-T007) → Tests (T008-T023) → Models (T024-T032) → Agents (T033-T036) → Services (T037-T042) → API (T043-T052) → Integration (T053-T065) → Polish (T066-T083)

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] All contracts have corresponding tests (T008-T017)
- [x] All entities have model tasks (T024-T032)
- [x] All tests come before implementation (T008-T023 before T024+)
- [x] Parallel tasks truly independent (verified file paths)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task (except test functions)
- [x] Agent framework follows dependency order (base → specializations)
- [x] All integration scenarios from quickstart.md covered (T018-T023, T075)
- [x] Performance targets tested (T073-T074)

## Execution Status
- [ ] Phase 3.1: Setup complete
- [ ] Phase 3.2: All tests written and failing (TDD gate)
- [ ] Phase 3.3: Models implemented
- [ ] Phase 3.4: Agent framework complete
- [ ] Phase 3.5: Services complete
- [ ] Phase 3.6: API endpoints complete
- [ ] Phase 3.7: Workflow integration complete
- [ ] Phase 3.8: Error handling complete
- [ ] Phase 3.9: FastAPI app configured
- [ ] Phase 3.10: Testing & validation complete
- [ ] Phase 3.11: Documentation & cleanup complete

---
**Total Tasks**: 83
**Estimated Parallel Batches**: 12 (significant parallelization opportunity)
**Ready for**: `/implement` or manual task-by-task execution
