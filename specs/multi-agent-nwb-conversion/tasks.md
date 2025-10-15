# Task Breakdown: Multi-Agent NWB Conversion Pipeline

**Feature ID**: multi-agent-nwb-conversion
**Plan Version**: 1.0.0
**Specification Version**: 1.1.0
**Status**: Ready for Implementation
**Created**: 2025-01-15

---

## Overview

This document provides a dependency-ordered task breakdown for implementing the Multi-Agent NWB Conversion Pipeline. Tasks are organized into 8 phases following Test-Driven Development (TDD) principles with no mock services approach.

**Total Tasks**: 54
**Estimated Duration**: 6 weeks
**Test Coverage Requirements**: ≥90% for critical paths, ≥85% for all other components

---

## Phase 1: Foundation & Data Models (Week 1)

### Task 1.1: Define Pydantic Data Models

**Phase**: 1 - Foundation
**Prerequisites**: None
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/models/`
**Coverage Target**: ≥85%

#### Description
Create all Pydantic models for session context, MCP messages, and API request/response schemas. These models provide type safety and validation throughout the system.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_models.py`
   - Test cases to write:
     - [ ] Test SessionContext model validation
     - [ ] Test WorkflowStage enum values
     - [ ] Test AgentHistoryEntry creation and validation
     - [ ] Test DatasetInfo model with all fields
     - [ ] Test MetadataExtractionResult with confidence scores
     - [ ] Test ConversionResults model
     - [ ] Test ValidationIssue and ValidationResults models
     - [ ] Test datetime serialization to ISO format
     - [ ] Test MCPMessage model with all message types
     - [ ] Test API request/response models
   - Mock/fixture strategy: No mocks needed, pure Pydantic validation tests

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/models/session_context.py`
   - File: `src/agentic_neurodata_conversion/models/mcp_message.py`
   - File: `src/agentic_neurodata_conversion/models/api_models.py`
   - Key classes/functions to implement:
     - [ ] WorkflowStage enum
     - [ ] AgentHistoryEntry, DatasetInfo, MetadataExtractionResult
     - [ ] ConversionResults, ValidationIssue, ValidationResults
     - [ ] SessionContext with all nested models
     - [ ] MessageType enum
     - [ ] MCPMessage model
     - [ ] All API request/response models
   - Integration points: Used by all other components

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_models`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- All models defined with proper field types and validation
- Coverage target met
- Code reviewed for quality

#### Notes
- Use `pydantic>=2.0.0` with BaseModel
- Ensure datetime fields have proper JSON encoders
- Add clear field descriptions for documentation

---

### Task 1.2: Implement Context Manager (Redis + Filesystem)

**Phase**: 1 - Foundation
**Prerequisites**: Task 1.1
**Estimated Duration**: 3 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/context_manager.py`
**Coverage Target**: ≥90% (critical path)

#### Description
Implement ContextManager class that provides write-through persistence to both Redis (primary cache) and filesystem (backup). This is a critical component for session state management.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_context_manager.py`
   - Test cases to write:
     - [ ] Test Redis connection and disconnection
     - [ ] Test create_session writes to both Redis and filesystem
     - [ ] Test get_session retrieves from Redis
     - [ ] Test get_session falls back to filesystem when Redis miss
     - [ ] Test get_session restores Redis from filesystem on fallback
     - [ ] Test update_session updates both storages with new timestamp
     - [ ] Test delete_session removes from both storages
     - [ ] Test session TTL is set correctly in Redis
     - [ ] Test filesystem path generation
     - [ ] Test Redis key generation
     - [ ] Test handling of non-existent sessions (returns None)
     - [ ] Test concurrent session operations
   - Mock/fixture strategy: Use real Redis (test database 15) and temp filesystem

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/context_manager.py`
   - Key classes/functions to implement:
     - [ ] ContextManager class with __init__
     - [ ] connect() and disconnect() methods
     - [ ] _get_redis_key() helper
     - [ ] _get_filesystem_path() helper
     - [ ] create_session() with write-through
     - [ ] get_session() with fallback logic
     - [ ] update_session() with timestamp update
     - [ ] delete_session() from both storages
   - Integration points: Used by MCP server and agents

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_context_manager`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥90%)
- [ ] Write-through strategy works correctly
- [ ] Filesystem fallback restores Redis cache
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Context manager fully implemented
- Coverage target met
- Redis and filesystem operations verified

#### Notes
- Use `redis.asyncio` for async operations
- Ensure filesystem directories are created automatically
- TTL should be configurable via settings

---

### Task 1.3: Implement Agent Registry

**Phase**: 1 - Foundation
**Prerequisites**: None
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/agent_registry.py`
**Coverage Target**: ≥85%

#### Description
Implement AgentRegistry class for agent discovery and health tracking. This component maintains the registry of all active agents in the system.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_agent_registry.py`
   - Test cases to write:
     - [ ] Test register_agent adds agent to registry
     - [ ] Test register_agent stores all agent metadata
     - [ ] Test get_agent returns correct agent info
     - [ ] Test get_agent returns None for non-existent agent
     - [ ] Test list_agents returns all registered agents
     - [ ] Test list_agents returns empty list initially
     - [ ] Test unregister_agent removes agent
     - [ ] Test unregister_agent handles non-existent agent gracefully
     - [ ] Test multiple agent registrations
     - [ ] Test agent overwrite on duplicate registration
   - Mock/fixture strategy: No mocks needed, in-memory registry

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/agent_registry.py`
   - Key classes/functions to implement:
     - [ ] AgentRegistry class with __init__
     - [ ] register_agent() method
     - [ ] get_agent() method
     - [ ] list_agents() method
     - [ ] unregister_agent() method
   - Integration points: Used by message router and MCP server

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_agent_registry`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] All CRUD operations work correctly
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Agent registry fully implemented
- Coverage target met
- Code reviewed for quality

#### Notes
- Use simple in-memory dictionary for MVP
- No persistence needed for agent registry
- Agent status tracking can be added later

---

### Task 1.4: Implement Configuration Module

**Phase**: 1 - Foundation
**Prerequisites**: None
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/config.py`
**Coverage Target**: ≥85%

#### Description
Implement configuration management using pydantic-settings for environment-based configuration. This provides type-safe configuration for server and agents.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_config.py`
   - Test cases to write:
     - [ ] Test Settings loads default values
     - [ ] Test Settings loads from environment variables
     - [ ] Test Settings validates Redis URL format
     - [ ] Test AgentConfig for conversation agent
     - [ ] Test AgentConfig for conversion agent
     - [ ] Test AgentConfig for evaluation agent
     - [ ] Test LLM provider validation (only anthropic/openai)
     - [ ] Test temperature value range validation
     - [ ] Test max_tokens positive integer validation
     - [ ] Test get_conversation_agent_config() factory
     - [ ] Test get_conversion_agent_config() factory
     - [ ] Test get_evaluation_agent_config() factory
   - Mock/fixture strategy: Use environment variable mocking

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/config.py`
   - File: `.env.example`
   - Key classes/functions to implement:
     - [ ] Settings class with all server config fields
     - [ ] AgentConfig class with LLM config fields
     - [ ] get_conversation_agent_config() factory
     - [ ] get_conversion_agent_config() factory
     - [ ] get_evaluation_agent_config() factory
     - [ ] Global settings instance
   - Integration points: Used by all components

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_config`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Environment variables loaded correctly
- [ ] Default values work without .env file
- [ ] .env.example template created
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Configuration module fully implemented
- .env.example template complete
- Coverage target met

#### Notes
- Use pydantic-settings BaseSettings
- Include all environment variables from spec
- Add clear comments in .env.example

---

### Task 1.5: Create Test Fixtures and Synthetic Dataset

**Phase**: 1 - Foundation
**Prerequisites**: None
**Estimated Duration**: 3 hours
**Component**: `tests/conftest.py`, `tests/data/`
**Coverage Target**: N/A (test infrastructure)

#### Description
Create shared pytest fixtures and generate a synthetic OpenEphys dataset for testing. This enables realistic testing without large real datasets.

#### Subtasks
1. **Implement test fixtures**
   - File: `tests/conftest.py`
   - Fixtures to implement:
     - [ ] event_loop fixture for async tests
     - [ ] redis_client fixture (database 15 for isolation)
     - [ ] context_manager fixture with test Redis + temp filesystem
     - [ ] agent_registry fixture
     - [ ] message_router fixture
     - [ ] test_session fixture (creates and cleans up session)
     - [ ] test_dataset_path fixture
     - [ ] mcp_server_url fixture

2. **Generate synthetic OpenEphys dataset**
   - File: `tests/data/generate_synthetic_openephys.py`
   - Implementation:
     - [ ] Generate settings.xml with 2 channels, 30kHz sampling
     - [ ] Generate CH1.continuous and CH2.continuous files
     - [ ] Create 10 seconds of synthetic data per channel
     - [ ] Generate README.md with metadata fields
     - [ ] Keep total size ~1MB for fast tests
   - Run script to create test data in `tests/data/synthetic_openephys/`

3. **Verify test infrastructure**
   - Run tests: `pixi run test-unit`
   - Verify fixtures are available
   - Verify synthetic dataset is valid OpenEphys format

#### Acceptance Criteria
- [ ] All fixtures work correctly
- [ ] Synthetic dataset generated successfully
- [ ] Dataset is valid OpenEphys format
- [ ] Dataset includes metadata in README.md
- [ ] Fixtures use isolated test Redis database
- [ ] Temporary directories cleaned up after tests

#### Definition of Done
- Fixtures implemented and tested
- Synthetic dataset generated
- Test infrastructure ready for use

#### Notes
- Use pytest-asyncio for async test support
- Ensure Redis test database is flushed after tests
- Document dataset structure in comments

---

## Phase 2: MCP Server Core (Week 2)

### Task 2.1: Implement Message Router

**Phase**: 2 - MCP Server
**Prerequisites**: Task 1.2, Task 1.3
**Estimated Duration**: 3 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/message_router.py`
**Coverage Target**: ≥90% (critical path)

#### Description
Implement MessageRouter class that routes MCP messages between agents via HTTP. This is a critical component for agent communication.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_message_router.py`
   - Test cases to write:
     - [ ] Test send_message creates valid MCPMessage
     - [ ] Test send_message sends HTTP POST to agent
     - [ ] Test send_message raises error for unregistered agent
     - [ ] Test execute_agent_task sends AGENT_EXECUTE message
     - [ ] Test execute_agent_task includes session_id and parameters
     - [ ] Test execute_agent_task returns agent response
     - [ ] Test message routing with multiple agents
     - [ ] Test HTTP timeout handling
     - [ ] Test network error handling
     - [ ] Test message ID uniqueness
   - Mock/fixture strategy: Use real agent registry, mock HTTP client for isolated tests

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/message_router.py`
   - Key classes/functions to implement:
     - [ ] MessageRouter class with __init__
     - [ ] send_message() method (creates MCPMessage, sends HTTP POST)
     - [ ] execute_agent_task() convenience method
     - [ ] HTTP client with timeout configuration
   - Integration points: Used by MCP server REST API

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_message_router`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥90%)
- [ ] Messages routed correctly to agents
- [ ] Error handling for network issues
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Message router fully implemented
- Coverage target met
- HTTP communication verified

#### Notes
- Use httpx.AsyncClient for async HTTP
- Set reasonable timeout (60 seconds)
- Include message ID for traceability

---

### Task 2.2: Implement Health Check Endpoint

**Phase**: 2 - MCP Server
**Prerequisites**: Task 1.3, Task 1.4
**Estimated Duration**: 1 hour
**Component**: `src/agentic_neurodata_conversion/mcp_server/api/health.py`
**Coverage Target**: ≥85%

#### Description
Implement health check endpoint that returns server status, registered agents, and Redis connection status.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_api_health.py`
   - Test cases to write:
     - [ ] Test GET /health returns 200 status
     - [ ] Test health response includes status field
     - [ ] Test health response includes version
     - [ ] Test health response includes agents_registered list
     - [ ] Test health response includes redis_connected boolean
     - [ ] Test health check with no agents registered
     - [ ] Test health check with multiple agents registered
     - [ ] Test health check when Redis disconnected
   - Mock/fixture strategy: Use real FastAPI TestClient, real agent registry

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/api/health.py`
   - Key classes/functions to implement:
     - [ ] FastAPI router
     - [ ] GET /health endpoint
     - [ ] HealthCheckResponse model (if not in Task 1.1)
     - [ ] Redis connection check logic
   - Integration points: Used by MCP server main app

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_api_health`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Health check returns correct status
- [ ] Response includes all required fields
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Health endpoint fully implemented
- Coverage target met
- Endpoint ready for monitoring

#### Notes
- Return JSON with clear status indicators
- Include version from package metadata
- Check Redis ping for connection status

---

### Task 2.3: Implement Session Initialization Endpoint

**Phase**: 2 - MCP Server
**Prerequisites**: Task 1.1, Task 1.2, Task 2.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/api/sessions.py`
**Coverage Target**: ≥85%

#### Description
Implement POST /api/v1/sessions/initialize endpoint that creates a new session and triggers conversation agent.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_api_sessions_init.py`
   - Test cases to write:
     - [ ] Test POST /api/v1/sessions/initialize with valid path
     - [ ] Test response includes session_id
     - [ ] Test response includes workflow_stage
     - [ ] Test session context created in storage
     - [ ] Test message sent to conversation agent
     - [ ] Test error handling for invalid dataset path
     - [ ] Test error handling when conversation agent not registered
     - [ ] Test error handling for message routing failure
   - Mock/fixture strategy: Use real context manager and message router

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/api/sessions.py` (partial)
   - Key classes/functions to implement:
     - [ ] FastAPI router
     - [ ] POST /api/v1/sessions/initialize endpoint
     - [ ] Session ID generation (UUID)
     - [ ] SessionContext creation
     - [ ] Message routing to conversation agent
     - [ ] Error handling and HTTP exceptions
   - Integration points: Uses context manager and message router

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_api_sessions_init`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Session created successfully
- [ ] Conversation agent triggered
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Initialization endpoint implemented
- Coverage target met
- Endpoint tested with real components

#### Notes
- Generate UUID for session_id
- Set workflow_stage to INITIALIZED
- Return user-friendly message

---

### Task 2.4: Implement Session Status Endpoint

**Phase**: 2 - MCP Server
**Prerequisites**: Task 1.1, Task 1.2
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/api/sessions.py`
**Coverage Target**: ≥85%

#### Description
Implement GET /api/v1/sessions/{id}/status endpoint that returns current session status and progress.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_api_sessions_status.py`
   - Test cases to write:
     - [ ] Test GET /api/v1/sessions/{id}/status with valid session
     - [ ] Test response includes workflow_stage
     - [ ] Test response includes progress_percentage
     - [ ] Test response includes status_message
     - [ ] Test response includes current_agent
     - [ ] Test response includes requires_clarification flag
     - [ ] Test 404 error for non-existent session
     - [ ] Test progress calculation for each workflow stage
   - Mock/fixture strategy: Use real context manager with test sessions

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/api/sessions.py` (partial)
   - Key classes/functions to implement:
     - [ ] GET /api/v1/sessions/{id}/status endpoint
     - [ ] Progress percentage calculation logic
     - [ ] Status message generation
     - [ ] Error handling for missing sessions
   - Integration points: Uses context manager

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_api_sessions_status`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Status returned correctly
- [ ] Progress percentages accurate
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Status endpoint implemented
- Coverage target met
- Progress calculation verified

#### Notes
- Map workflow stages to progress percentages
- Include clarification prompt if needed
- Return 404 for non-existent sessions

---

### Task 2.5: Implement Session Clarification Endpoint

**Phase**: 2 - MCP Server
**Prerequisites**: Task 1.1, Task 1.2, Task 2.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/api/sessions.py`
**Coverage Target**: ≥85%

#### Description
Implement POST /api/v1/sessions/{id}/clarify endpoint that accepts user input for error resolution.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_api_sessions_clarify.py`
   - Test cases to write:
     - [ ] Test POST /api/v1/sessions/{id}/clarify with user input
     - [ ] Test response includes acknowledgment message
     - [ ] Test response includes updated workflow_stage
     - [ ] Test message sent to conversation agent
     - [ ] Test user_input passed in message payload
     - [ ] Test updated_metadata passed in message payload
     - [ ] Test 404 error for non-existent session
     - [ ] Test error handling for message routing failure
   - Mock/fixture strategy: Use real context manager and message router

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/api/sessions.py` (partial)
   - Key classes/functions to implement:
     - [ ] POST /api/v1/sessions/{id}/clarify endpoint
     - [ ] Request validation
     - [ ] Message routing to conversation agent
     - [ ] Session context update after clarification
     - [ ] Error handling
   - Integration points: Uses context manager and message router

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_api_sessions_clarify`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Clarification accepted and processed
- [ ] Conversation agent triggered
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Clarification endpoint implemented
- Coverage target met
- Error recovery flow tested

#### Notes
- Accept both user_input text and updated_metadata
- Send handle_clarification task to conversation agent
- Return updated workflow stage

---

### Task 2.6: Implement Session Result Endpoint

**Phase**: 2 - MCP Server
**Prerequisites**: Task 1.1, Task 1.2
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/api/sessions.py`
**Coverage Target**: ≥85%

#### Description
Implement GET /api/v1/sessions/{id}/result endpoint that returns final conversion results and validation report.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_api_sessions_result.py`
   - Test cases to write:
     - [ ] Test GET /api/v1/sessions/{id}/result with completed session
     - [ ] Test response includes nwb_file_path
     - [ ] Test response includes validation_report_path
     - [ ] Test response includes overall_status
     - [ ] Test response includes LLM summary
     - [ ] Test response includes validation_issues list
     - [ ] Test 404 error for non-existent session
     - [ ] Test 400 error for incomplete session
   - Mock/fixture strategy: Use real context manager with completed test session

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/api/sessions.py` (partial)
   - Key classes/functions to implement:
     - [ ] GET /api/v1/sessions/{id}/result endpoint
     - [ ] Validation that session is completed
     - [ ] Result extraction from session context
     - [ ] Error handling for missing/incomplete sessions
   - Integration points: Uses context manager

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_api_sessions_result`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Results returned correctly
- [ ] Validation details included
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Result endpoint implemented
- Coverage target met
- All result fields populated

#### Notes
- Only return results for completed sessions
- Include full validation issue list
- Return LLM-generated summary

---

### Task 2.7: Implement Internal Agent Communication Endpoints

**Phase**: 2 - MCP Server
**Prerequisites**: Task 1.2, Task 1.3, Task 2.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/api/internal.py`
**Coverage Target**: ≥85%

#### Description
Implement internal endpoints for agent registration, context access, and message routing.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_api_internal.py`
   - Test cases to write:
     - [ ] Test POST /internal/register_agent with valid payload
     - [ ] Test agent added to registry after registration
     - [ ] Test GET /internal/sessions/{id}/context returns session
     - [ ] Test PATCH /internal/sessions/{id}/context updates session
     - [ ] Test POST /internal/route_message routes to agent
     - [ ] Test 404 error for non-existent session in context endpoints
     - [ ] Test validation of registration request
   - Mock/fixture strategy: Use real context manager, agent registry, message router

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/api/internal.py`
   - Key classes/functions to implement:
     - [ ] FastAPI router
     - [ ] POST /internal/register_agent endpoint
     - [ ] GET /internal/sessions/{id}/context endpoint
     - [ ] PATCH /internal/sessions/{id}/context endpoint
     - [ ] POST /internal/route_message endpoint
     - [ ] Request validation models
   - Integration points: Used by agents for MCP communication

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_api_internal`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] All internal endpoints working
- [ ] Agents can register and communicate
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Internal endpoints implemented
- Coverage target met
- Agent communication tested

#### Notes
- These endpoints are for agent-to-server communication
- Not exposed to external users
- Enable agents to access/update context

---

### Task 2.8: Implement MCP Server Main Application

**Phase**: 2 - MCP Server
**Prerequisites**: Task 2.1, Task 2.2, Task 2.3, Task 2.4, Task 2.5, Task 2.6, Task 2.7
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/mcp_server/main.py`
**Coverage Target**: ≥85%

#### Description
Implement the main FastAPI application that integrates all server components and provides startup/shutdown lifecycle management.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/integration/test_mcp_server.py`
   - Test cases to write:
     - [ ] Test server startup initializes all components
     - [ ] Test Redis connection established on startup
     - [ ] Test all routers registered correctly
     - [ ] Test health endpoint accessible
     - [ ] Test sessions endpoints accessible
     - [ ] Test internal endpoints accessible
     - [ ] Test CORS middleware configured
     - [ ] Test app state contains required components
     - [ ] Test shutdown closes Redis connection
   - Mock/fixture strategy: Use FastAPI TestClient, real components

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/mcp_server/main.py`
   - Key classes/functions to implement:
     - [ ] FastAPI app initialization
     - [ ] CORS middleware configuration
     - [ ] Component initialization (context manager, registry, router)
     - [ ] App state population
     - [ ] Router inclusion (health, sessions, internal)
     - [ ] startup_event() handler
     - [ ] shutdown_event() handler
   - Integration points: Central application for entire MCP server

3. **Verify and refactor**
   - Run tests: `pixi run test-integration -k test_mcp_server`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All integration tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Server starts and stops cleanly
- [ ] All components initialized
- [ ] All endpoints accessible
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Main application implemented
- Server lifecycle managed
- Coverage target met

#### Notes
- Use singleton pattern for shared components
- Store components in app.state
- Include version information

---

## Phase 3: Agent Base Infrastructure (Week 3)

### Task 3.1: Implement Base Agent Class

**Phase**: 3 - Agent Base
**Prerequisites**: Task 1.1, Task 1.4, Task 2.8
**Estimated Duration**: 3 hours
**Component**: `src/agentic_neurodata_conversion/agents/base_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement BaseAgent abstract class that provides common functionality for all agents including LLM integration, MCP communication, and HTTP server creation.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_base_agent.py`
   - Test cases to write:
     - [ ] Test BaseAgent initialization with Anthropic provider
     - [ ] Test BaseAgent initialization with OpenAI provider
     - [ ] Test register_with_server sends registration request
     - [ ] Test get_session_context retrieves session from server
     - [ ] Test update_session_context sends updates to server
     - [ ] Test call_llm with Anthropic provider
     - [ ] Test call_llm with OpenAI provider
     - [ ] Test call_llm retry logic for rate limits
     - [ ] Test call_llm exponential backoff
     - [ ] Test call_llm fails after max retries
     - [ ] Test create_agent_server creates FastAPI app
     - [ ] Test agent HTTP server has /mcp/message endpoint
     - [ ] Test agent HTTP server has /health endpoint
     - [ ] Test get_capabilities is abstract (must override)
     - [ ] Test handle_message is abstract (must override)
   - Mock/fixture strategy: Mock LLM API calls, mock HTTP client for server communication

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/base_agent.py`
   - Key classes/functions to implement:
     - [ ] BaseAgent abstract class
     - [ ] __init__ with config and LLM client initialization
     - [ ] _initialize_llm_client() for provider abstraction
     - [ ] register_with_server() method
     - [ ] get_session_context() method
     - [ ] update_session_context() method
     - [ ] call_llm() with retry logic and exponential backoff
     - [ ] create_agent_server() FastAPI factory
     - [ ] start_server() method
     - [ ] Abstract get_capabilities() method
     - [ ] Abstract handle_message() method
   - Integration points: Base class for all specialized agents

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_base_agent`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Both Anthropic and OpenAI providers work
- [ ] Retry logic with exponential backoff works
- [ ] Agent can register with server
- [ ] Agent can access/update session context
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Base agent fully implemented
- LLM abstraction working
- MCP communication working
- Coverage target met

#### Notes
- Support both Anthropic and OpenAI APIs
- Implement exponential backoff for rate limits
- Use httpx.AsyncClient for MCP server communication
- Include clear error messages for configuration issues

---

### Task 3.2: Implement Agent Startup Script

**Phase**: 3 - Agent Base
**Prerequisites**: Task 3.1
**Estimated Duration**: 1 hour
**Component**: `src/agentic_neurodata_conversion/agents/__main__.py`
**Coverage Target**: N/A (CLI script)

#### Description
Implement CLI script for starting agents as separate processes. This enables running each agent independently.

#### Subtasks
1. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/__main__.py`
   - Key classes/functions to implement:
     - [ ] start_agent() async function
     - [ ] Agent type validation (conversation, conversion, evaluation)
     - [ ] Config factory selection based on agent type
     - [ ] Agent instantiation based on type
     - [ ] Command-line argument parsing
     - [ ] Main entry point
   - Integration points: Used to start each agent process

2. **Verify manually**
   - Test starting each agent type
   - Verify agent registers with MCP server
   - Verify agent HTTP server responds to health checks

#### Acceptance Criteria
- [ ] Script accepts agent type argument
- [ ] Script starts correct agent
- [ ] Agent registers successfully
- [ ] Agent HTTP server responds
- [ ] Clear error messages for invalid arguments

#### Definition of Done
- Startup script implemented
- All three agent types can be started
- Registration verified

#### Notes
- Use sys.argv for argument parsing
- Print clear status messages
- Handle startup errors gracefully

---

## Phase 4: Conversation Agent (Week 3)

### Task 4.1: Implement Format Detection

**Phase**: 4 - Conversation Agent
**Prerequisites**: Task 3.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversation_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement OpenEphys format detection using hybrid approach (file extensions + content validation).

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversation_agent_format.py`
   - Test cases to write:
     - [ ] Test detect format with settings.xml present returns "openephys"
     - [ ] Test detect format with .continuous files returns "openephys"
     - [ ] Test detect format with neither returns "unknown"
     - [ ] Test detect format with non-existent path raises error
     - [ ] Test detect format with empty directory returns "unknown"
   - Mock/fixture strategy: Use real synthetic OpenEphys dataset

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] ConversationAgent class (skeleton)
     - [ ] get_capabilities() method
     - [ ] _detect_format() method
   - Integration points: Used in session initialization

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversation_agent_format`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] OpenEphys format detected correctly
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Format detection implemented
- Coverage target met
- Works with synthetic dataset

#### Notes
- Check for settings.xml first
- Fall back to .continuous file check
- Return "unknown" for unsupported formats

---

### Task 4.2: Implement OpenEphys Structure Validation

**Phase**: 4 - Conversation Agent
**Prerequisites**: Task 4.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversation_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement validation of OpenEphys dataset structure including required files and dataset information extraction.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversation_agent_validation.py`
   - Test cases to write:
     - [ ] Test validate OpenEphys structure with valid dataset
     - [ ] Test returns DatasetInfo with all fields
     - [ ] Test raises error for missing settings.xml
     - [ ] Test raises error for missing .continuous files
     - [ ] Test calculates total size correctly
     - [ ] Test counts files correctly
     - [ ] Test detects .md files
     - [ ] Test sets has_metadata_files flag correctly
   - Mock/fixture strategy: Use real synthetic OpenEphys dataset

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] _validate_openephys_structure() method
     - [ ] File existence checks
     - [ ] Size calculation logic
     - [ ] File counting logic
     - [ ] Metadata file detection
   - Integration points: Used in session initialization

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversation_agent_validation`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Dataset structure validated correctly
- [ ] DatasetInfo populated with accurate data
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Structure validation implemented
- Coverage target met
- DatasetInfo extraction working

#### Notes
- Check for required files first
- Calculate total size by walking directory
- Find all .md files in dataset root

---

### Task 4.3: Implement Metadata Extraction from .md Files

**Phase**: 4 - Conversation Agent
**Prerequisites**: Task 3.1, Task 4.2
**Estimated Duration**: 3 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversation_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement LLM-powered metadata extraction from all .md files in the dataset with reasonable default application.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversation_agent_metadata.py`
   - Test cases to write:
     - [ ] Test extract metadata from README.md
     - [ ] Test returns MetadataExtractionResult with all fields
     - [ ] Test returns empty metadata when no .md files
     - [ ] Test combines content from multiple .md files
     - [ ] Test LLM extracts subject_id correctly
     - [ ] Test LLM applies reasonable defaults (e.g., "mouse" → "Mus musculus")
     - [ ] Test extraction_confidence tracked per field
     - [ ] Test llm_extraction_log stored
     - [ ] Test handles LLM JSON parsing errors
   - Mock/fixture strategy: Mock LLM calls with fixture responses, use real dataset

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] _extract_metadata_from_md_files() async method
     - [ ] Read all .md files in dataset
     - [ ] Combine .md file content
     - [ ] Create LLM prompt for metadata extraction
     - [ ] Parse LLM JSON response
     - [ ] Handle parsing errors gracefully
   - Integration points: Used in session initialization

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversation_agent_metadata`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Metadata extracted from .md files
- [ ] LLM applies reasonable defaults
- [ ] Confidence scores tracked
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Metadata extraction implemented
- LLM integration working
- Coverage target met

#### Notes
- Use call_llm() from base agent
- Request JSON output from LLM
- Handle both structured and unstructured .md content
- Log extraction reasoning for debugging

---

### Task 4.4: Implement Session Initialization Handler

**Phase**: 4 - Conversation Agent
**Prerequisites**: Task 4.1, Task 4.2, Task 4.3
**Estimated Duration**: 3 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversation_agent.py`
**Coverage Target**: ≥90% (critical path)

#### Description
Implement handle_message() and _initialize_session() that orchestrates format detection, validation, and metadata extraction.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversation_agent_session.py`
   - Test cases to write:
     - [ ] Test handle_message routes to _initialize_session
     - [ ] Test initialize session with valid OpenEphys dataset
     - [ ] Test updates session context with dataset_info
     - [ ] Test updates session context with metadata
     - [ ] Test sets workflow_stage to COLLECTING_METADATA
     - [ ] Test triggers conversion agent after initialization
     - [ ] Test returns success status with results
     - [ ] Test fails for unsupported format
     - [ ] Test fails for invalid dataset structure
     - [ ] Test error handling for missing dataset path
   - Mock/fixture strategy: Mock LLM calls, use real context manager and message router

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] handle_message() method (routes tasks)
     - [ ] _initialize_session() async method
     - [ ] Integration of format detection, validation, metadata extraction
     - [ ] Session context updates via base agent
     - [ ] _trigger_conversion() method for agent handoff
     - [ ] Error handling and response formatting
   - Integration points: Handles AGENT_EXECUTE messages from MCP server

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversation_agent_session`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥90%)
- [ ] Session initialization works end-to-end
- [ ] Conversion agent triggered correctly
- [ ] Session context updated properly
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Session initialization handler implemented
- Coverage target met
- Agent handoff working

#### Notes
- This is a critical path component (≥90% coverage)
- Update workflow_stage appropriately
- Send route_message request to MCP server for agent handoff

---

### Task 4.5: Implement Clarification Handler

**Phase**: 4 - Conversation Agent
**Prerequisites**: Task 4.4
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversation_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement _handle_clarification() that processes user input when conversion/validation errors occur.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversation_agent_clarify.py`
   - Test cases to write:
     - [ ] Test handle_clarification updates metadata
     - [ ] Test clears requires_user_clarification flag
     - [ ] Test clears clarification_prompt
     - [ ] Test triggers conversion agent retry
     - [ ] Test returns success status
     - [ ] Test handles missing updated_metadata gracefully
   - Mock/fixture strategy: Use real context manager and message router

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] _handle_clarification() async method
     - [ ] Update session metadata from user input
     - [ ] Clear clarification flags
     - [ ] Trigger conversion agent retry
   - Integration points: Handles clarification task from MCP server

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversation_agent_clarify`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Clarification processed correctly
- [ ] Metadata updated
- [ ] Conversion retry triggered
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Clarification handler implemented
- Coverage target met
- Error recovery working

#### Notes
- Accept both text input and structured metadata updates
- Always retry conversion after clarification
- Clear error state before retry

---

## Phase 5: Conversion Agent (Week 4)

### Task 5.1: Implement NeuroConv Integration

**Phase**: 5 - Conversion Agent
**Prerequisites**: Task 3.1
**Estimated Duration**: 3 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversion_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement OpenEphys to NWB conversion using NeuroConv library with proper error handling.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversion_agent_convert.py`
   - Test cases to write:
     - [ ] Test conversion with valid OpenEphys dataset
     - [ ] Test NWB file created successfully
     - [ ] Test conversion duration tracked
     - [ ] Test output path set correctly
     - [ ] Test gzip compression applied
     - [ ] Test error handling for corrupt dataset
     - [ ] Test error handling for missing files
     - [ ] Test error capture includes full stack trace
   - Mock/fixture strategy: Use real synthetic OpenEphys dataset, real NeuroConv

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversion_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] ConversionAgent class skeleton
     - [ ] get_capabilities() method
     - [ ] _convert_to_nwb() async method (partial)
     - [ ] OpenEphysRecordingInterface instantiation
     - [ ] run_conversion() call with compression
     - [ ] Output path generation
     - [ ] Duration tracking
     - [ ] Error capture with full details
   - Integration points: Core conversion logic

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversion_agent_convert`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] NWB files generated successfully
- [ ] Errors captured with full context
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- NeuroConv integration working
- Coverage target met
- NWB files validated

#### Notes
- Use OpenEphysRecordingInterface from NeuroConv
- Apply gzip compression by default
- Track conversion start and end times
- Capture full exception details

---

### Task 5.2: Implement Metadata Preparation

**Phase**: 5 - Conversion Agent
**Prerequisites**: Task 5.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversion_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement metadata preparation that maps session metadata to NWB format requirements.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversion_agent_metadata.py`
   - Test cases to write:
     - [ ] Test prepare metadata with all fields present
     - [ ] Test Subject metadata mapping
     - [ ] Test NWBFile metadata mapping
     - [ ] Test Device metadata mapping
     - [ ] Test handles missing fields gracefully
     - [ ] Test applies defaults for missing session_start_time
     - [ ] Test experimenter converted to list
     - [ ] Test description defaults correctly
   - Mock/fixture strategy: Use sample SessionContext with metadata

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversion_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] _prepare_metadata() method
     - [ ] Subject metadata mapping
     - [ ] NWBFile metadata mapping
     - [ ] Device metadata mapping
     - [ ] Default value application
   - Integration points: Used in _convert_to_nwb()

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversion_agent_metadata`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Metadata mapped correctly to NWB schema
- [ ] Missing fields handled gracefully
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Metadata preparation implemented
- Coverage target met
- NWB metadata validated

#### Notes
- Follow NWB schema requirements
- Apply reasonable defaults
- Handle None values gracefully

---

### Task 5.3: Implement LLM Error Message Generation

**Phase**: 5 - Conversion Agent
**Prerequisites**: Task 3.1, Task 5.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversion_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement LLM-powered generation of user-friendly error messages with remediation steps.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversion_agent_errors.py`
   - Test cases to write:
     - [ ] Test generate error message for conversion failure
     - [ ] Test error message includes plain language explanation
     - [ ] Test error message includes remediation steps
     - [ ] Test error message under 200 words
     - [ ] Test handles various error types
     - [ ] Test includes dataset context in prompt
   - Mock/fixture strategy: Mock LLM calls with fixture responses

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversion_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] _generate_error_message() async method
     - [ ] Create LLM prompt with error context
     - [ ] Include dataset information
     - [ ] Request actionable remediation steps
   - Integration points: Used in _convert_to_nwb() error handling

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversion_agent_errors`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Error messages are user-friendly
- [ ] Remediation steps provided
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Error message generation implemented
- Coverage target met
- LLM integration working

#### Notes
- Use lower temperature for consistent errors (0.3)
- Keep messages concise but actionable
- Include relevant dataset context

---

### Task 5.4: Implement Conversion Message Handler

**Phase**: 5 - Conversion Agent
**Prerequisites**: Task 5.1, Task 5.2, Task 5.3
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/conversion_agent.py`
**Coverage Target**: ≥90% (critical path)

#### Description
Implement handle_message() and complete _convert_to_nwb() that orchestrates conversion workflow and error handling.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_conversion_agent_handler.py`
   - Test cases to write:
     - [ ] Test handle_message routes to _convert_to_nwb
     - [ ] Test conversion updates workflow_stage to CONVERTING
     - [ ] Test successful conversion updates session context
     - [ ] Test successful conversion stores ConversionResults
     - [ ] Test successful conversion triggers evaluation agent
     - [ ] Test failed conversion captures error details
     - [ ] Test failed conversion generates LLM error message
     - [ ] Test failed conversion sets requires_clarification flag
     - [ ] Test failed conversion sets workflow_stage to FAILED
   - Mock/fixture strategy: Mock LLM calls, use real context manager and message router

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/conversion_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] handle_message() method (routes tasks)
     - [ ] Complete _convert_to_nwb() with all steps
     - [ ] Session context updates
     - [ ] _trigger_evaluation() method for agent handoff
     - [ ] Comprehensive error handling
   - Integration points: Handles AGENT_EXECUTE messages from MCP server

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_conversion_agent_handler`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥90%)
- [ ] Conversion workflow complete
- [ ] Error handling comprehensive
- [ ] Evaluation agent triggered
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Conversion handler fully implemented
- Coverage target met
- Agent handoff working

#### Notes
- This is a critical path component (≥90% coverage)
- Always capture full error details
- Send route_message for evaluation agent

---

## Phase 6: Evaluation Agent (Week 5)

### Task 6.1: Implement NWB Inspector Integration

**Phase**: 6 - Evaluation Agent
**Prerequisites**: Task 3.1
**Estimated Duration**: 3 hours
**Component**: `src/agentic_neurodata_conversion/agents/evaluation_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement NWB file validation using NWB Inspector library with comprehensive issue tracking.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_evaluation_agent_validate.py`
   - Test cases to write:
     - [ ] Test validation with valid NWB file
     - [ ] Test validation issues collected correctly
     - [ ] Test issue severity categorization (critical/warning/info)
     - [ ] Test issue count by severity
     - [ ] Test overall status determination (passed/passed_with_warnings/failed)
     - [ ] Test validation with missing NWB file
     - [ ] Test validation with corrupt NWB file
   - Mock/fixture strategy: Use real NWB files from conversion tests

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/evaluation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] EvaluationAgent class skeleton
     - [ ] get_capabilities() method
     - [ ] _validate_nwb() async method (partial)
     - [ ] inspect_nwb() integration
     - [ ] Issue collection and categorization
     - [ ] Overall status determination logic
   - Integration points: Core validation logic

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_evaluation_agent_validate`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] NWB Inspector integrated correctly
- [ ] Issues categorized by severity
- [ ] Overall status accurate
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- NWB Inspector integration working
- Coverage target met
- Validation results accurate

#### Notes
- Use nwbinspector.inspect_nwb()
- Collect all issues, don't stop early
- Categorize by severity correctly

---

### Task 6.2: Implement Validation Report Generation

**Phase**: 6 - Evaluation Agent
**Prerequisites**: Task 6.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/evaluation_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement JSON validation report generation with issue details and quality scores.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_evaluation_agent_report.py`
   - Test cases to write:
     - [ ] Test generate report creates JSON file
     - [ ] Test report includes session_id
     - [ ] Test report includes overall_status
     - [ ] Test report includes all issues with details
     - [ ] Test report path generated correctly
     - [ ] Test metadata completeness score calculation
     - [ ] Test best practices score calculation
     - [ ] Test scores based on issue counts
   - Mock/fixture strategy: Use sample validation issues

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/evaluation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] _generate_report() method
     - [ ] JSON serialization of validation results
     - [ ] Report path generation
     - [ ] _calculate_metadata_score() method
     - [ ] _calculate_best_practices_score() method
   - Integration points: Used in _validate_nwb()

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_evaluation_agent_report`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] JSON reports generated correctly
- [ ] Quality scores calculated accurately
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Report generation implemented
- Coverage target met
- Reports are valid JSON

#### Notes
- Use session_id in report filename
- Include all issue details
- Calculate scores based on completeness and issues

---

### Task 6.3: Implement LLM Validation Summary

**Phase**: 6 - Evaluation Agent
**Prerequisites**: Task 3.1, Task 6.1
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/evaluation_agent.py`
**Coverage Target**: ≥85%

#### Description
Implement LLM-powered generation of human-readable validation summaries with actionable recommendations.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_evaluation_agent_summary.py`
   - Test cases to write:
     - [ ] Test generate validation summary with issues
     - [ ] Test summary includes overall status
     - [ ] Test summary highlights critical issues
     - [ ] Test summary provides recommendations
     - [ ] Test summary indicates if file ready for use
     - [ ] Test summary under 150 words
     - [ ] Test summary with no issues
   - Mock/fixture strategy: Mock LLM calls with fixture responses

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/evaluation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] _generate_validation_summary() async method
     - [ ] Create LLM prompt with validation results
     - [ ] Include issue details and counts
     - [ ] Request actionable recommendations
   - Integration points: Used in _validate_nwb()

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_evaluation_agent_summary`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥85%)
- [ ] Summaries are clear and concise
- [ ] Recommendations are actionable
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Summary generation implemented
- Coverage target met
- LLM integration working

#### Notes
- Use balanced temperature for clear summaries (0.4)
- Limit issue list in prompt (first 20)
- Keep summaries concise but complete

---

### Task 6.4: Implement Evaluation Message Handler

**Phase**: 6 - Evaluation Agent
**Prerequisites**: Task 6.1, Task 6.2, Task 6.3
**Estimated Duration**: 2 hours
**Component**: `src/agentic_neurodata_conversion/agents/evaluation_agent.py`
**Coverage Target**: ≥90% (critical path)

#### Description
Implement handle_message() and complete _validate_nwb() that orchestrates validation workflow.

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/unit/test_evaluation_agent_handler.py`
   - Test cases to write:
     - [ ] Test handle_message routes to _validate_nwb
     - [ ] Test validation updates workflow_stage to EVALUATING
     - [ ] Test validation updates session context with results
     - [ ] Test validation generates report file
     - [ ] Test validation generates LLM summary
     - [ ] Test validation sets workflow_stage to COMPLETED
     - [ ] Test validation clears current_agent
     - [ ] Test handles missing NWB file gracefully
   - Mock/fixture strategy: Mock LLM calls, use real context manager

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/agents/evaluation_agent.py` (partial)
   - Key classes/functions to implement:
     - [ ] handle_message() method (routes tasks)
     - [ ] Complete _validate_nwb() with all steps
     - [ ] Session context updates
     - [ ] Workflow stage management
   - Integration points: Handles AGENT_EXECUTE messages from MCP server

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_evaluation_agent_handler`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥90%)
- [ ] Validation workflow complete
- [ ] Session marked as completed
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Evaluation handler fully implemented
- Coverage target met
- Workflow finalization working

#### Notes
- This is a critical path component (≥90% coverage)
- Set workflow_stage to COMPLETED on success
- Clear current_agent to indicate completion

---

## Phase 7: Integration & End-to-End Testing (Week 5-6)

### Task 7.1: Implement Session Workflow Integration Test

**Phase**: 7 - Integration
**Prerequisites**: All Phase 4, 5, 6 tasks
**Estimated Duration**: 3 hours
**Component**: `tests/integration/test_session_workflow.py`
**Coverage Target**: N/A (integration test)

#### Description
Create integration test that verifies complete session lifecycle from initialization to completion.

#### Subtasks
1. **Write integration tests**
   - File: `tests/integration/test_session_workflow.py`
   - Test cases to write:
     - [ ] Test complete session workflow with synthetic dataset
     - [ ] Test session context created correctly
     - [ ] Test workflow_stage progression through all stages
     - [ ] Test agent handoffs work correctly
     - [ ] Test dataset_info populated
     - [ ] Test metadata extracted from .md files
     - [ ] Test NWB file generated
     - [ ] Test validation report generated
     - [ ] Test session marked as completed
     - [ ] Test all output files exist
   - Mock/fixture strategy: Use real MCP server, real agents, synthetic dataset

2. **Verify integration**
   - Run tests: `pixi run test-integration -k test_session_workflow`
   - Verify all agents communicate correctly
   - Verify session state managed properly

#### Acceptance Criteria
- [ ] All integration tests pass
- [ ] Complete workflow executes successfully
- [ ] All agents communicate via MCP server
- [ ] Session context updated at each stage
- [ ] Output files generated correctly

#### Definition of Done
- Integration tests written and passing
- Complete workflow verified
- Agent communication tested

#### Notes
- This tests the "happy path" workflow
- Use synthetic dataset for speed
- Verify session context at each stage

---

### Task 7.2: Implement Agent Handoff Integration Test

**Phase**: 7 - Integration
**Prerequisites**: All Phase 4, 5, 6 tasks
**Estimated Duration**: 2 hours
**Component**: `tests/integration/test_agent_handoffs.py`
**Coverage Target**: N/A (integration test)

#### Description
Create integration test that specifically verifies agent-to-agent communication via MCP server.

#### Subtasks
1. **Write integration tests**
   - File: `tests/integration/test_agent_handoffs.py`
   - Test cases to write:
     - [ ] Test conversation agent triggers conversion agent
     - [ ] Test conversion agent triggers evaluation agent
     - [ ] Test message routing between agents
     - [ ] Test session context accessible to all agents
     - [ ] Test agents can update shared context
     - [ ] Test handoff timing and synchronization
   - Mock/fixture strategy: Use real MCP server and agents

2. **Verify integration**
   - Run tests: `pixi run test-integration -k test_agent_handoffs`
   - Verify message routing works
   - Verify context sharing works

#### Acceptance Criteria
- [ ] All integration tests pass
- [ ] Agent handoffs work correctly
- [ ] Message routing verified
- [ ] Context sharing works
- [ ] No direct agent-to-agent communication

#### Definition of Done
- Integration tests written and passing
- Agent handoffs verified
- MCP protocol compliance confirmed

#### Notes
- Verify agents only communicate via MCP server
- Test both synchronous and asynchronous handoffs
- Verify message delivery

---

### Task 7.3: Implement Error Recovery Integration Test

**Phase**: 7 - Integration
**Prerequisites**: All Phase 4, 5, 6 tasks
**Estimated Duration**: 3 hours
**Component**: `tests/integration/test_error_recovery.py`
**Coverage Target**: N/A (integration test)

#### Description
Create integration test that verifies error scenarios and recovery mechanisms.

#### Subtasks
1. **Write integration tests**
   - File: `tests/integration/test_error_recovery.py`
   - Test cases to write:
     - [ ] Test recovery from conversion error
     - [ ] Test requires_clarification flag set on error
     - [ ] Test clarification endpoint accepts user input
     - [ ] Test conversion retry after clarification
     - [ ] Test session context persists through errors
     - [ ] Test filesystem fallback when Redis unavailable
     - [ ] Test workflow_stage set to FAILED on error
     - [ ] Test error messages user-friendly
   - Mock/fixture strategy: Use real components, simulate errors

2. **Verify error handling**
   - Run tests: `pixi run test-integration -k test_error_recovery`
   - Verify error scenarios handled gracefully
   - Verify recovery mechanisms work

#### Acceptance Criteria
- [ ] All integration tests pass
- [ ] Error scenarios handled correctly
- [ ] User clarification workflow works
- [ ] Session state preserved during errors
- [ ] Recovery mechanisms functional

#### Definition of Done
- Integration tests written and passing
- Error recovery verified
- Clarification workflow tested

#### Notes
- Test various error types
- Verify session state persists
- Test filesystem fallback for resilience

---

### Task 7.4: Implement End-to-End Pipeline Test

**Phase**: 7 - Integration
**Prerequisites**: Task 7.1, Task 7.2, Task 7.3
**Estimated Duration**: 3 hours
**Component**: `tests/e2e/test_full_pipeline.py`
**Coverage Target**: N/A (e2e test)

#### Description
Create end-to-end test that exercises the complete pipeline via REST API like a real user would.

#### Subtasks
1. **Write e2e tests**
   - File: `tests/e2e/test_full_pipeline.py`
   - Test cases to write:
     - [ ] Test POST /api/v1/sessions/initialize
     - [ ] Test polling GET /api/v1/sessions/{id}/status
     - [ ] Test workflow progression through all stages
     - [ ] Test GET /api/v1/sessions/{id}/result when complete
     - [ ] Test NWB file exists and is valid
     - [ ] Test validation report exists and is valid
     - [ ] Test LLM-generated summary included
     - [ ] Test complete workflow under time budget
   - Mock/fixture strategy: No mocks, complete end-to-end test

2. **Verify e2e workflow**
   - Run tests: `pixi run test-e2e -k test_full_pipeline`
   - Verify complete pipeline works
   - Verify timing is reasonable

#### Acceptance Criteria
- [ ] All e2e tests pass
- [ ] Complete pipeline works via REST API
- [ ] Polling workflow works correctly
- [ ] Results returned as expected
- [ ] Files generated and valid

#### Definition of Done
- E2E tests written and passing
- Full pipeline verified
- REST API workflow tested

#### Notes
- This tests the complete user experience
- Use realistic polling intervals
- Verify all API responses

---

### Task 7.5: Performance Testing with Large Dataset

**Phase**: 7 - Integration
**Prerequisites**: Task 7.4
**Estimated Duration**: 2 hours
**Component**: `tests/e2e/test_performance.py`
**Coverage Target**: N/A (performance test)

#### Description
Create performance test that verifies system handles large datasets (>10GB) with warnings but no failures.

#### Subtasks
1. **Write performance tests**
   - File: `tests/e2e/test_performance.py`
   - Test cases to write:
     - [ ] Test conversion with 10GB+ dataset (warning issued)
     - [ ] Test memory usage stays within bounds
     - [ ] Test conversion completes successfully
     - [ ] Test warning message clear about size
     - [ ] Test conversion duration tracked
     - [ ] Test progress updates during long conversion
   - Mock/fixture strategy: Generate or use large test dataset

2. **Verify performance**
   - Run tests: `pixi run test-e2e -k test_performance`
   - Monitor memory usage
   - Verify completion time reasonable

#### Acceptance Criteria
- [ ] Performance tests pass
- [ ] Large datasets handled correctly
- [ ] Warnings issued appropriately
- [ ] Memory usage acceptable
- [ ] No crashes or failures

#### Definition of Done
- Performance tests written and passing
- Large dataset handling verified
- Memory usage monitored

#### Notes
- May need to generate large synthetic dataset
- Monitor system resources during test
- Test can be marked as optional/slow

---

## Phase 8: Documentation & Polish (Week 6)

### Task 8.1: Verify Test Coverage Requirements

**Phase**: 8 - Documentation & Polish
**Prerequisites**: All previous tasks
**Estimated Duration**: 2 hours
**Component**: All source files
**Coverage Target**: ≥90% critical, ≥85% overall

#### Description
Review and verify test coverage meets requirements across all components. Add tests where coverage gaps exist.

#### Subtasks
1. **Generate coverage report**
   - Run: `pixi run test-cov`
   - Identify components below target coverage
   - List specific lines/functions not covered

2. **Add missing tests**
   - Write tests for uncovered code paths
   - Focus on critical paths first (≥90%)
   - Ensure overall coverage ≥85%

3. **Verify quality gates**
   - Run: `pixi run quality`
   - Fix any linting issues
   - Fix any type checking issues
   - Run: `pixi run pre-commit run --all-files`

#### Acceptance Criteria
- [ ] Critical paths have ≥90% coverage
- [ ] Overall codebase has ≥85% coverage
- [ ] All pre-commit hooks pass
- [ ] No linting errors
- [ ] No type checking errors
- [ ] Coverage report generated and reviewed

#### Definition of Done
- Coverage requirements met
- Quality gates pass
- All tests passing

#### Notes
- Use coverage report to identify gaps
- Prioritize critical paths
- Document any intentionally uncovered code

---

### Task 8.2: Create Deployment Scripts

**Phase**: 8 - Documentation & Polish
**Prerequisites**: None
**Estimated Duration**: 2 hours
**Component**: `scripts/`
**Coverage Target**: N/A (deployment scripts)

#### Description
Create shell scripts for easy deployment and process management.

#### Subtasks
1. **Create start_all.sh**
   - File: `scripts/start_all.sh`
   - Start Redis container
   - Start MCP server
   - Start all three agents
   - Capture PIDs for shutdown

2. **Create stop_all.sh**
   - File: `scripts/stop_all.sh`
   - Stop all agent processes
   - Stop MCP server
   - Stop Redis container

3. **Test scripts**
   - Verify all processes start correctly
   - Verify agents register with server
   - Verify graceful shutdown

#### Acceptance Criteria
- [ ] start_all.sh starts all services
- [ ] stop_all.sh stops all services gracefully
- [ ] Scripts handle errors appropriately
- [ ] Clear status messages printed
- [ ] Scripts documented with comments

#### Definition of Done
- Deployment scripts created and tested
- All services start/stop correctly
- Scripts documented

#### Notes
- Use trap for graceful shutdown
- Wait for server readiness before starting agents
- Print clear status messages

---

### Task 8.3: Generate OpenAPI Documentation

**Phase**: 8 - Documentation & Polish
**Prerequisites**: Phase 2 complete
**Estimated Duration**: 2 hours
**Component**: Documentation
**Coverage Target**: N/A (documentation)

#### Description
Generate and review OpenAPI/Swagger documentation for REST API.

#### Subtasks
1. **Configure OpenAPI**
   - Ensure FastAPI auto-generates OpenAPI spec
   - Add descriptions to endpoints
   - Add examples to request/response models
   - Configure tags and groups

2. **Review documentation**
   - Access /docs endpoint
   - Verify all endpoints documented
   - Verify request/response schemas correct
   - Test "Try it out" functionality

3. **Export OpenAPI spec**
   - Export openapi.json
   - Save to docs/openapi.json
   - Add to version control

#### Acceptance Criteria
- [ ] OpenAPI spec generated automatically
- [ ] All endpoints documented
- [ ] Request/response schemas complete
- [ ] Examples included
- [ ] Swagger UI accessible
- [ ] openapi.json exported

#### Definition of Done
- OpenAPI documentation complete
- Swagger UI functional
- API documentation reviewed

#### Notes
- FastAPI generates OpenAPI automatically
- Add clear descriptions to improve docs
- Include example requests/responses

---

### Task 8.4: Write User Guide

**Phase**: 8 - Documentation & Polish
**Prerequisites**: All implementation complete
**Estimated Duration**: 3 hours
**Component**: `docs/user-guide.md`
**Coverage Target**: N/A (documentation)

#### Description
Create comprehensive user guide covering setup, usage, and troubleshooting.

#### Subtasks
1. **Write setup section**
   - Prerequisites (Python, Redis, Pixi)
   - Installation steps
   - Configuration (.env setup)
   - Starting services

2. **Write usage section**
   - Initializing a session
   - Monitoring progress
   - Handling errors/clarifications
   - Retrieving results
   - Example curl commands

3. **Write troubleshooting section**
   - Common errors and solutions
   - Redis connection issues
   - Agent registration failures
   - Conversion errors
   - LLM API issues

#### Acceptance Criteria
- [ ] User guide complete and clear
- [ ] All setup steps documented
- [ ] Usage examples provided
- [ ] Troubleshooting section helpful
- [ ] Code examples tested and working

#### Definition of Done
- User guide written and reviewed
- All examples tested
- Clear and comprehensive

#### Notes
- Target audience: neuroscience researchers
- Use clear, non-technical language where possible
- Include screenshots or diagrams if helpful

---

### Task 8.5: Write Developer Guide

**Phase**: 8 - Documentation & Polish
**Prerequisites**: All implementation complete
**Estimated Duration**: 3 hours
**Component**: `docs/developer-guide.md`
**Coverage Target**: N/A (documentation)

#### Description
Create developer guide covering architecture, testing, and contribution guidelines.

#### Subtasks
1. **Write architecture section**
   - System overview
   - Component responsibilities
   - Data flow diagrams
   - MCP protocol usage

2. **Write testing section**
   - Test structure
   - Running tests
   - Coverage requirements
   - Adding new tests

3. **Write contribution section**
   - Code style guidelines
   - Pre-commit hooks
   - Pull request process
   - Adding new agents

#### Acceptance Criteria
- [ ] Developer guide complete and clear
- [ ] Architecture documented
- [ ] Testing process documented
- [ ] Contribution guidelines clear
- [ ] Diagrams included

#### Definition of Done
- Developer guide written and reviewed
- Technical details accurate
- Contribution process clear

#### Notes
- Target audience: developers extending the system
- Include architecture diagrams from plan
- Document key design decisions

---

### Task 8.6: Create README with Quick Start

**Phase**: 8 - Documentation & Polish
**Prerequisites**: Task 8.4, Task 8.5
**Estimated Duration**: 2 hours
**Component**: `README.md`
**Coverage Target**: N/A (documentation)

#### Description
Create comprehensive README with quick start guide and links to detailed documentation.

#### Subtasks
1. **Write README sections**
   - Project overview and features
   - Quick start (5 minute setup)
   - Architecture overview
   - Links to detailed docs
   - License and credits

2. **Add badges**
   - Test status
   - Coverage
   - License
   - Python version

3. **Review and polish**
   - Ensure clarity
   - Test quick start steps
   - Fix any issues

#### Acceptance Criteria
- [ ] README complete and clear
- [ ] Quick start works
- [ ] Links to detailed docs
- [ ] Badges added
- [ ] Professional appearance

#### Definition of Done
- README written and reviewed
- Quick start tested
- Links verified

#### Notes
- Keep README concise
- Link to detailed documentation
- Make quick start actually quick

---

### Task 8.7: Final Quality Review and Pre-commit Setup

**Phase**: 8 - Documentation & Polish
**Prerequisites**: All previous tasks
**Estimated Duration**: 2 hours
**Component**: All files
**Coverage Target**: N/A (quality review)

#### Description
Perform final quality review and ensure pre-commit hooks are properly configured.

#### Subtasks
1. **Configure pre-commit**
   - File: `.pre-commit-config.yaml`
   - Add ruff for linting
   - Add ruff-format for formatting
   - Add mypy for type checking
   - Add trailing whitespace check
   - Add end-of-file fixer

2. **Run pre-commit on all files**
   - Run: `pixi run pre-commit run --all-files`
   - Fix any issues found
   - Verify all hooks pass

3. **Final test run**
   - Run: `pixi run test`
   - Verify all tests pass
   - Run: `pixi run quality`
   - Verify quality checks pass

#### Acceptance Criteria
- [ ] Pre-commit hooks configured
- [ ] All hooks pass on entire codebase
- [ ] All tests pass
- [ ] All quality checks pass
- [ ] Code properly formatted
- [ ] No type errors
- [ ] No linting errors

#### Definition of Done
- Pre-commit setup complete
- All quality gates pass
- System ready for use

#### Notes
- Pre-commit ensures consistent code quality
- Configure to run on every commit
- Document hook requirements in developer guide

---

## Summary

**Total Tasks**: 54
**Total Estimated Duration**: ~120 hours (6 weeks)

### Phase Breakdown
- **Phase 1 (Foundation)**: 5 tasks, 12 hours
- **Phase 2 (MCP Server)**: 8 tasks, 16 hours
- **Phase 3 (Agent Base)**: 2 tasks, 4 hours
- **Phase 4 (Conversation Agent)**: 5 tasks, 12 hours
- **Phase 5 (Conversion Agent)**: 4 tasks, 9 hours
- **Phase 6 (Evaluation Agent)**: 4 tasks, 9 hours
- **Phase 7 (Integration)**: 5 tasks, 13 hours
- **Phase 8 (Documentation)**: 7 tasks, 16 hours

### Critical Path Tasks (≥90% Coverage Required)
- Task 1.2: Context Manager
- Task 2.1: Message Router
- Task 4.4: Session Initialization Handler
- Task 5.4: Conversion Message Handler
- Task 6.4: Evaluation Message Handler

### Key Milestones
1. **Week 1 End**: Foundation complete, can persist session contexts
2. **Week 2 End**: MCP server operational, REST API working
3. **Week 3 End**: Conversation agent initializes sessions and extracts metadata
4. **Week 4 End**: Conversion agent generates NWB files
5. **Week 5 End**: Evaluation agent validates NWB files, full pipeline works
6. **Week 6 End**: System documented, tested, and production-ready

### Testing Strategy
- Write tests FIRST for every component (TDD)
- No mocks for internal services (build bottom-up)
- Use real Redis, NeuroConv, NWB Inspector
- Only mock LLM calls where needed (cost/speed)
- Test coverage: ≥90% critical paths, ≥85% overall

### Success Criteria
- [ ] All 54 tasks completed
- [ ] All tests passing
- [ ] Coverage requirements met (≥90% critical, ≥85% overall)
- [ ] All pre-commit hooks pass
- [ ] Complete pipeline tested end-to-end
- [ ] Documentation complete
- [ ] System deployed and operational

---

**Ready for `/implement` command**
