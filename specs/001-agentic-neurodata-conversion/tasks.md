# Implementation Tasks: Agentic Neurodata Conversion System

**Branch**: `001-agentic-neurodata-conversion`
**Date**: 2025-10-15
**Related**: [plan.md](plan.md), [requirements.md](../../requirements.md)

---

## Overview

This document breaks down the implementation into actionable, dependency-ordered tasks. Tasks are organized by functional increments (user stories) to enable independent implementation and testing.

**Task Format**: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Parallelizable (can execute concurrently with other [P] tasks)
- **[Story]**: Maps to epic/user story (e.g., [E1], [E2], [US1.1])

**Total Tasks**: 91 tasks across 9 phases
**Estimated Duration**: 4-6 weeks (1-2 developers)

---

## Task Summary by Phase

| Phase           | Description                | Tasks        | Duration            |
| --------------- | -------------------------- | ------------ | ------------------- |
| 1               | Setup & Infrastructure     | 8            | 2-3 days            |
| 2               | Foundational (MCP + State) | 8            | 2-3 days            |
| 3               | LLM Service Layer          | 4            | 1-2 days            |
| 4               | Conversation Agent         | 12           | 4-5 days            |
| 5               | Conversion Agent           | 11           | 4-5 days            |
| 6               | Evaluation Agent           | 11           | 4-5 days            |
| 7               | API & WebSocket            | 13           | 3-4 days            |
| 8               | Frontend UI                | 15           | 5-7 days            |
| 9               | Integration & Testing      | 9            | 3-4 days            |
| **Total** |                            | **91** | **4-6 weeks** |

---

## Dependencies & Execution Order

```
Phase 1 (Setup) → Phase 2 (Foundation) → Phases 3-8 (Features) → Phase 9 (Integration)
                                              │
                                              ├─→ Phase 3 (LLM) ────────────┐
                                              ├─→ Phase 4 (Conversation) ───┤
                                              ├─→ Phase 5 (Conversion) ─────┼─→ Phase 9
                                              ├─→ Phase 6 (Evaluation) ─────┤
                                              ├─→ Phase 7 (API) ────────────┤
                                              └─→ Phase 8 (Frontend) ───────┘
```

**Parallelization**: Phases 3-8 can start once Phase 2 completes (agents are independent)

---

## Phase 1: Setup & Infrastructure

**Goal**: Initialize project structure, dependencies, and development environment

**Duration**: 2-3 days

### Tasks

- [X] T001 Create backend directory structure per plan.md (backend/src/{agents,mcp,services,models,api,utils})
- [X] T002 [P] Create frontend directory structure per plan.md (frontend/src/{components,services,types})
- [X] T003 [P] Create test directory structure (backend/tests/{unit,integration,fixtures})
- [X] T004 Configure pixi.toml with dependencies (NeuroConv ≥0.4.0, PyNWB ≥2.6.0, NWB Inspector ≥0.4.30, FastAPI, Pydantic ≥2.0, Anthropic SDK ≥0.18.0, PyYAML, Jinja2)
- [X] T005 [P] Configure pyproject.toml with project metadata and test dependencies (pytest, pytest-cov)
- [X] T006 [P] Create .env.example with required environment variables (ANTHROPIC_API_KEY, UPLOAD_DIR, OUTPUT_DIR, LOG_DIR, MAX_UPLOAD_SIZE_GB)
- [X] T007 [P] Create .gitignore for uploads/, outputs/, logs/, .env, __pycache__, node_modules/
- [X] T008 Generate toy SpikeGLX dataset using backend/tests/fixtures/generate_toy_dataset.py script (create ~5 MB dataset: 5 sec, 16 channels, 30kHz) (Research Decision 7)

**Completion Criteria**: Project structure matches plan.md, pixi install succeeds, toy dataset created

---

## Phase 2: Foundational - MCP Server & Global State

**Goal**: Implement core MCP server and global state management (blocking prerequisites)

**Duration**: 2-3 days

**Dependencies**: Phase 1 complete

### Tasks

- [X] T009 Implement MCPMessage Pydantic schema in backend/src/mcp/message.py (data-model.md Schema 1)
- [X] T010 [E2] Implement GlobalState Pydantic schema in backend/src/models/global_state.py with enums (ConversionStatus, ValidationStatus, StageStatus, LogLevel, LogEntry, Stage) (data-model.md Schema 2)
- [X] T010a [E2] Implement global state reset handler in backend/src/models/global_state.py (reset after conversion completes, Story 2.1)
- [X] T010b [P] [E2] Implement state lifecycle tracking in backend/src/api/main.py (idle → processing → completed/failed transitions, Story 2.2)
- [X] T011 Implement MCP server in backend/src/mcp/server.py (agent registry, message routing, context injection) (Story 1.1, 1.2, 1.3, Research Decision 1)
- [X] T012 [P] Implement agent registry in backend/src/mcp/registry.py (register/unregister agents, discovery)
- [X] T013 [P] Implement structured logging utility in backend/src/utils/logging.py (JSON Lines format, log levels)
- [X] T014 [P] Implement custom exceptions in backend/src/utils/exceptions.py (LLMAPIException, FileProcessingException, NWBValidationException)

**Completion Criteria**: MCP server can register agents, route messages, inject context; global state serializable and resets properly

**Test**: Unit test MCP message routing with mock agents, test state reset after completion

---

## Phase 3: LLM Service Layer

**Goal**: Implement provider-agnostic LLM service with Anthropic implementation

**Duration**: 1-2 days

**Dependencies**: Phase 2 complete

### Tasks

- [X] T015 Implement abstract LLMService interface in backend/src/services/llm_service.py (complete(), chat() methods) (Story 3.1, Research Decision 8)
- [X] T016 Implement AnthropicLLMService in backend/src/services/anthropic_service.py (API client, error handling, token tracking) (Story 3.2)
- [X] T017 [P] Create prompt templates in backend/src/prompts/ (evaluation_passed.yaml, evaluation_failed.yaml, format_detection.yaml) (Stories 9.1, 9.2, Research Decision 6)
- [X] T018 [P] Implement PromptService in backend/src/services/prompt_service.py (YAML loading, Jinja2 rendering, validation) (Research Decision 6)

**Completion Criteria**: LLM service can send prompts to Claude, handle errors, load YAML templates

**Test**: Unit test with mock Anthropic API responses

---

## Phase 4: Conversation Agent

**Goal**: Implement Conversation Agent for user interaction and correction orchestration

**Duration**: 4-5 days

**Dependencies**: Phase 2, Phase 3 complete

### Tasks

- [X] T019 [E4] Create ConversationAgent class in backend/src/agents/conversation_agent.py (register with MCP, define actions) (Story 4.1)
- [X] T020 [E4] Implement validate_metadata action (NWB schema validation: subject_id, species, session_description, session_start_time) (Story 4.2)
- [X] T021 [E4] Implement analyze_correction_context action (categorize issues by severity, use LLM for analysis) (Story 4.4)
- [X] T022 [E4] Implement generate_user_prompt action (use LLM to create contextual prompts with examples) (Story 4.5)
- [X] T023 [E4] Implement validate_user_input action (type checking, format validation, domain constraints) (Story 4.6)
- [X] T024 [E4] Implement notify_user action (send WebSocket messages for real-time updates) (Story 4.8)
- [X] T025 [E4] Implement request_retry_approval action (wait for user decision, track attempt number) (Story 8.2)
- [X] T026 [E4] Implement correction_loop_orchestration (coordinate message flow: Evaluation → User → Conversion, track history, detect no-progress) (Story 4.7)
- [X] T027 [P] [E4] Create LLM prompt templates for correction analysis in backend/src/prompts/correction_analysis.yaml
- [X] T028 [P] [E4] Create LLM prompt templates for user input prompts in backend/src/prompts/user_input_prompt.yaml (Story 4.9)
- [X] T029 [E4] Implement session state tracking (waiting_for_approval, waiting_for_input, processing)
- [X] T030 [E4] Implement concurrent request rejection (single session constraint, return 409)

**Completion Criteria**: Conversation Agent can validate metadata, analyze failures with LLM, orchestrate correction loop

**Test**: Unit test each action with mock MCP server and LLM service

---

## Phase 5: Conversion Agent

**Goal**: Implement Conversion Agent for format detection and NWB conversion

**Duration**: 4-5 days

**Dependencies**: Phase 2 complete (independent of Phase 3-4)

### Tasks

- [X] T031 [E5-6] Create ConversionAgent class in backend/src/agents/conversion_agent.py (register with MCP, define actions)
- [X] T032 [E5] Implement scan_files action (recursive directory scan, file cataloging) (Story 5.1)
- [X] T033 [E5] Implement detect_format action (use NeuroConv automatic interface detection, confidence scores) (Story 5.2)
- [X] T034 [E5] Implement resolve_ambiguity action (optional LLM usage, degrades gracefully) (Story 5.3, Research Decision 1 note)
- [X] T035 [E6] Implement collect_metadata action (validate user metadata, store in session) (Story 6.1)
- [X] T036 [E6] Implement extract_metadata action (auto-extract sampling rate, channel count, duration from files) (Story 6.2)
- [X] T037 [E6] Implement convert_file action (execute NeuroConv conversion, compute SHA256, raise exceptions on failure) (Story 6.3)
- [X] T038 [E6] Implement apply_corrections action (reconvert with corrections, versioned filename, track attempt number) (Story 8.7, Research Decision 5)
- [X] T039 [P] [E6] Implement file versioning utility in backend/src/utils/file_versioning.py (SHA256-based naming: original_attempt2_a3f9d1c8.nwb)
- [X] T040 [P] [E6] Implement storage service abstraction in backend/src/services/storage_service.py (save_file, load_file, checksum verification)
- [X] T041 [E6] Implement conversion orchestration (scan → detect → validate → extract → convert → verify pipeline) (Story 6.4)

**Completion Criteria**: Conversion Agent can detect any NeuroConv format, convert to NWB, version files with SHA256

**Test**: Integration test with toy SpikeGLX dataset

---

## Phase 6: Evaluation Agent

**Goal**: Implement Evaluation Agent for NWB validation and report generation

**Duration**: 4-5 days

**Dependencies**: Phase 2, Phase 3 complete

### Tasks

- [X] T042 [E7] Create EvaluationAgent class in backend/src/agents/evaluation_agent.py (register with MCP, define actions)
- [X] T043 [E7] Implement ValidationResult Pydantic schema in backend/src/models/validation.py (IssueSeverity, OverallStatus, ValidationIssue, FileInfo) (data-model.md Schema 3)
- [X] T044 [E7] Implement CorrectionContext Pydantic schema in backend/src/models/correction.py (FixStrategy, CorrectionContext) (data-model.md Schema 4)
- [X] T045 [E7] Implement extract_file_info action (read NWB metadata: nwb_version, subject, devices, acquisition data) (Story 7.1)
- [X] T046 [E7] Implement validate_file action (run NWB Inspector, categorize by severity, determine overall_status) (Story 7.2)
- [X] T047 [E7] Implement process_results action (count issues, group by category, store in global state) (Story 7.3)
- [X] T048 [E8] Implement generate_correction_context action (identify auto-fixable vs user-input-required issues) (Story 8.1)
- [X] T049 [E9] Implement generate_report_passed action (use LLM to create HTML report) (Story 9.5, Research Decision 2)
- [X] T050 [E9] Implement generate_report_failed action (use LLM to create JSON correction guidance) (Story 9.6)
- [X] T051 [P] [E9] Implement ReportService in backend/src/services/report_service.py (HTML generation, template structure)
- [X] T052 [P] [E9] Create prompt templates for quality evaluation in backend/src/prompts/evaluation_passed.yaml and evaluation_failed.yaml (Stories 9.1, 9.2)

**Completion Criteria**: Evaluation Agent can validate NWB files with Inspector, generate LLM-enhanced reports (HTML/JSON)

**Test**: Integration test with valid, warning-only, and failed NWB files

---

## Phase 7: API Layer & WebSocket

**Goal**: Implement FastAPI REST API and WebSocket for real-time updates

**Duration**: 3-4 days

**Dependencies**: Phase 2, Phase 4, Phase 5, Phase 6 complete (needs all agents)

### Tasks

- [X] T053 [E10] Create FastAPI application in backend/src/api/main.py (app initialization, CORS middleware, static file serving) (Story 10.1)
- [X] T054 [E10] Implement API request/response schemas in backend/src/models/api_schemas.py (UploadRequest, StatusResponse, RetryApprovalRequest, UserInputRequest, WebSocketMessage) (data-model.md Schema 5)
- [X] T055 [E10] Implement health check endpoints in backend/src/api/main.py (/health, /api/info) (Story 10.1)
- [X] T056 [E10] Implement file upload endpoint in backend/src/api/endpoints/upload.py (POST /api/upload, multipart form handling, 409 Conflict check) (Story 10.2)
- [X] T057 [E10] Implement background task processing in backend/src/api/endpoints/upload.py (invoke agents via MCP, update global state) (Story 10.3)
- [X] T058 [E10] Implement status endpoint in backend/src/api/endpoints/status.py (GET /api/status, return GlobalState) (Story 10.4)
- [X] T059 [E10] Implement WebSocket endpoint in backend/src/api/websocket.py (WS /ws, broadcast progress updates) (Story 10.5, Research Decision 3)
- [X] T060 [E10] Implement download endpoints in backend/src/api/endpoints/download.py (GET /api/download/nwb, /api/download/nwb/v{N}, /api/download/report) (Story 10.6)
- [X] T061 [E10] Implement logs endpoint in backend/src/api/endpoints/logs.py (GET /api/logs, filter by level) (Story 10.7)
- [X] T062 [E10] Implement retry approval endpoint in backend/src/api/endpoints/approval.py (POST /api/retry-approval) (Story 8.3)
- [X] T063 [E10] Implement user input endpoint in backend/src/api/endpoints/approval.py (POST /api/user-input) (Story 8.6)
- [X] T064 [E10] Implement correction context endpoint in backend/src/api/endpoints/status.py (GET /api/correction-context) (Story 8.2)
- [X] T065 [P] [E10] Create OpenAPI documentation (auto-generated from FastAPI, verify against contracts/openapi.yaml)

**Completion Criteria**: All REST endpoints functional, WebSocket broadcasts progress, OpenAPI docs generated

**Test**: API integration tests with curl/Postman, WebSocket client connection test

---

## Phase 8: Frontend UI

**Goal**: Implement web interface for file upload, progress tracking, and results display

**Duration**: 5-7 days

**Dependencies**: Phase 7 complete (needs API)

**Original Plan**: React + TypeScript + Material-UI (see tasks T066-T080 below)
**MVP Implementation**: Static HTML + JavaScript ([frontend/public/chat-ui.html](../../frontend/public/chat-ui.html))

### Tasks

- [ ] T066 [E11] Initialize React app with TypeScript in frontend/ (Create React App or Vite)
- [ ] T067 [E11] Install and configure Material-UI (MUI ≥5.0, theme setup) (Story 11.1)
- [ ] T068 [E11] Create API client service in frontend/src/services/api.ts (Axios, base URL configuration) (Story 11.1)
- [ ] T069 [E11] Create WebSocket client service in frontend/src/services/websocket.ts (native WebSocket API, message handling) (Research Decision 3)
- [ ] T070 [E11] Create TypeScript interfaces in frontend/src/types/models.ts (map API schemas to TypeScript)
- [ ] T071 [E11] Implement FileUpload component in frontend/src/components/FileUpload.tsx (drag-and-drop, file list, validation) (Story 11.2)
- [ ] T072 [E11] Implement MetadataForm component in frontend/src/components/MetadataForm.tsx (required fields, validation, species autocomplete, date picker) (Story 11.3)
- [ ] T073 [E11] Implement ProgressView component in frontend/src/components/ProgressView.tsx (WebSocket connection, stage indicators, real-time updates) (Story 11.4)
- [ ] T074 [E11] Implement ResultsDisplay component in frontend/src/components/ResultsDisplay.tsx (validation status badges, issue breakdown, download buttons, context-aware messages) (Story 11.5)
- [ ] T075 [E11] Implement LogViewer component in frontend/src/components/LogViewer.tsx (fetch logs, color-coded levels, auto-scroll) (Story 11.6)
- [ ] T076 [E11] Implement RetryApprovalDialog component in frontend/src/components/RetryApprovalDialog.tsx (show correction context, approve/decline/accept-as-is buttons) (Story 8.9)
- [ ] T077 [E11] Implement UserInputModal component in frontend/src/components/UserInputModal.tsx (dynamic form fields, validation, examples) (Story 8.9)
- [ ] T078 [E11] Implement error handling in frontend/src/components/ErrorBoundary.tsx (toast notifications, API error display) (Story 11.7)
- [ ] T079 [E11] Create main App component in frontend/src/App.tsx (routing, state management, component integration)
- [ ] T080 [P] [E11] Add component tests in frontend/tests/components/ (React Testing Library, coverage for key interactions)

**Implementation Note**: Frontend was implemented using static HTML + vanilla JavaScript ([frontend/public/chat-ui.html](../../frontend/public/chat-ui.html)) instead of React + TypeScript for faster MVP delivery. UI is functional and meets core requirements. Tasks T066-T080 reflect the original React plan but were not executed. React migration may be considered for v2.0.

**Completion Criteria**: Complete UI workflow (upload → progress → results → download), WebSocket updates functional

**Test**: E2E UI test with toy dataset (Cypress or Playwright)

---

## Phase 9: Integration, Testing & Polish

**Goal**: End-to-end integration tests, documentation, and MVP finalization

**Duration**: 3-4 days

**Dependencies**: Phases 1-8 complete

### Tasks

- [X] T081 [P] [E12] Create mock LLM service in backend/tests/mocks/mock_llm_service.py (returns predefined responses, no API calls) (Story 12.3)
- [X] T082 [P] [E12] Create defensive testing framework in backend/tests/unit/test_defensive_errors.py (verify all agents raise exceptions correctly) (Story 12.4)
- [X] T083 [E12] Implement end-to-end integration test in backend/tests/integration/test_end_to_end.py (happy path: PASSED validation) (Story 12.1)
- [X] T084 [E12] Implement PASSED_WITH_ISSUES integration test (user accepts as-is path) (Story 12.1)
- [X] T085 [E12] Implement FAILED integration test (user approves retry, correction succeeds) (Story 12.1)
- [X] T086 [E12] Implement error recovery tests in backend/tests/integration/test_error_recovery.py (invalid format, LLM API failure, concurrent uploads) (Story 12.5)
- [X] T087 [E12] Verify integration test timeout ≤10 minutes on toy dataset (Story 12.6)
- [X] T088 Verify code coverage ≥80% (run pytest-cov, review report)
- [X] T089 Final constitution compliance check (review all agents for inter-agent imports, defensive errors, provider abstraction)

**Completion Criteria**: All integration tests pass, code coverage ≥80%, constitution compliant

**Test**: Full system test with toy dataset (all three validation paths)

---

## Parallel Execution Opportunities

Tasks marked **[P]** can execute concurrently. Key parallelization:

### Phase 1 (Setup)

- T002 (frontend structure) + T003 (test structure) + T005 (pyproject.toml) + T006 (.env) + T007 (.gitignore) can run together

### Phase 2 (Foundation)

- T012 (registry) + T013 (logging) + T014 (exceptions) after T009-T011 complete

### Phase 3 (LLM)

- T017 (prompt templates) + T018 (PromptService) can run together

### Phases 4-6 (Agents)

- **All three agents (Conversation, Conversion, Evaluation) are independent** - can be developed in parallel by different developers after Phase 2 completes

### Phase 7 (API)

- T065 (OpenAPI docs) independent of endpoint implementation

### Phase 8 (Frontend)

- T080 (component tests) can run alongside component development

---

## MVP Scope Recommendation

**Minimum Viable Product** (demonstrate core value):

**Include**:

- Phase 1-2: Setup + Foundation
- Phase 3: LLM Service
- Phase 4-6: All three agents (core architecture)
- Phase 7: Essential API endpoints (upload, status, download, WebSocket)
- Phase 8: Basic UI (upload + progress + results)
- Phase 9: Basic integration test

**Defer Post-MVP**:

- Advanced error recovery tests
- UI polish (animations, advanced error states)
- Comprehensive logging UI
- Performance optimization

**MVP Delivers**: Working three-agent system with user-controlled correction loop, validating the core architecture.

---

## Implementation Strategy

### Week 1: Foundation

- Days 1-2: Phase 1 (Setup)
- Days 3-5: Phase 2 (MCP + State) + Phase 3 (LLM)

### Week 2-3: Agents (Parallel Development)

- Developer 1: Phase 4 (Conversation) + Phase 5 (Conversion)
- Developer 2: Phase 6 (Evaluation) + Phase 7 (API) start

### Week 4: API & Frontend

- Phase 7 (API) complete
- Phase 8 (Frontend) start

### Week 5-6: Frontend & Integration

- Phase 8 (Frontend) complete
- Phase 9 (Integration + Testing)
- Polish and bug fixes

---

## Progress Tracking

**As you complete tasks**:

1. Check off completed tasks: `- [x] T001 ...`
2. Update phase completion percentage
3. Log blockers/issues in phase notes
4. Track actual vs estimated duration

**Phase Completion Metrics**:

- Phase 1: **8** / 8 tasks complete ✅
- Phase 2: **8** / 8 tasks complete ✅
- Phase 3: **4** / 4 tasks complete ✅
- Phase 4: **12** / 12 tasks complete ✅
- Phase 5: **11** / 11 tasks complete ✅
- Phase 6: **11** / 11 tasks complete ✅
- Phase 7: **13** / 13 tasks complete ✅
- Phase 8: **0** / 15 tasks complete ⚠️ (React plan not executed - MVP used static HTML, see Phase 8 implementation note)
- Phase 9: **9** / 9 tasks complete ✅

**Overall Progress**: **76** / 91 tasks complete (**83.5%**)

**Note**: Phase 8 shows 0/15 because the original React + TypeScript frontend plan (tasks T066-T080) was not executed. The MVP implementation used static HTML + JavaScript ([frontend/public/chat-ui.html](../../frontend/public/chat-ui.html)) instead for faster delivery. All backend functionality (Phases 1-7, 9) is complete.

---


**Tasks Document Version**: 1.1.0 | **Generated**: 2025-10-15 | **Updated**: 2025-10-15
