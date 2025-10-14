# Tasks Prompt: Multi-Agent NWB Conversion Pipeline

This prompt should be used with the `/tasks` command to generate a dependency-ordered task breakdown based on the plan generated from `plan_prompt.md`.

## Context for Task Generation

You are breaking down the implementation plan into **concrete, actionable tasks** that:
1. Are ordered by dependencies (can't start task B until task A is complete)
2. Follow TDD workflow (write tests BEFORE implementation)
3. Enable testing without mocks (build in order so earlier components can be tested)
4. Are appropriately sized (1-4 hours of work per task)
5. Have clear acceptance criteria

## Task Generation Principles

### 1. Dependency-First Ordering

**Build order to avoid mocks:**
```
Phase 1: Foundation (can be tested independently)
  → Data models (Pydantic schemas)
  → Context Manager (Redis + filesystem)
  → Agent Registry

Phase 2: Server Core (tests use Phase 1 components)
  → Message Router
  → MCP Server startup
  → REST API endpoints

Phase 3: Agent Base (tests use Phase 2 server)
  → Base Agent class
  → LLM provider integrations
  → Agent registration

Phase 4: Specialized Agents (tests use real server + base agent)
  → Conversation Agent
  → Conversion Agent
  → Evaluation Agent

Phase 5: Integration (tests use all above)
  → End-to-end workflows
  → Error recovery
  → Performance testing
```

### 2. TDD Workflow for Each Task

**Every implementation task must include:**
1. **Write tests FIRST** (Red)
   - Unit tests for the component
   - Integration tests if applicable
   - Expected coverage: ≥90% for agent handlers, ≥85% for others

2. **Implement to pass tests** (Green)
   - Minimum viable implementation
   - Make tests pass

3. **Refactor** (Clean)
   - Improve code quality
   - Maintain green tests

**Task template:**
```
Task: [Component Name]
Prerequisites: [Tasks that must complete first]
Duration: [1-4 hours]

Subtasks:
1. Write unit tests for [component]
   - Test cases: [list specific tests]
   - Coverage target: ≥X%
   - Files: tests/unit/test_[component].py

2. Implement [component]
   - Implementation approach: [brief description]
   - Files: src/agentic_neurodata_conversion/[path]

3. Verify tests pass
   - Run: pixi run test-unit
   - Verify coverage meets target

4. Integration tests (if applicable)
   - Test with dependent components
   - Files: tests/integration/test_[component].py

Acceptance Criteria:
- [ ] All unit tests pass
- [ ] Coverage ≥X%
- [ ] Integration tests pass (if applicable)
- [ ] Code passes pre-commit hooks (ruff, mypy)
```

### 3. Test-First Task Sizing

**Small tasks (1-2 hours):**
- Single class or function
- 5-10 test cases
- Clear, focused functionality

**Medium tasks (2-3 hours):**
- Module with 2-3 classes
- 10-20 test cases
- Multiple related functions

**Large tasks (3-4 hours):**
- Complete component
- 20+ test cases
- Multiple integration points

**If a task exceeds 4 hours, break it down further.**

### 4. No Mock Services

**Key principle: Build bottom-up to enable real testing**

Example:
```
❌ Wrong order:
  1. Implement Conversation Agent
  2. Mock MCP server for agent tests
  3. Implement MCP server later

✅ Correct order:
  1. Implement MCP server
  2. Test Conversation Agent with REAL MCP server
  3. No mocks needed!
```

**Exception:** External services like LLM APIs can use fixtures for tests (to avoid costs), but internal services should be real.

### 5. Critical Path Coverage

**Components requiring ≥90% coverage (critical paths):**
- All agent message handlers (handle_message methods)
- Context manager (CRUD operations)
- Message router (routing logic)
- MCP server core (message handling)

**Components requiring ≥85% coverage:**
- REST API endpoints
- LLM provider integrations
- Format detection
- Data validation

## Task Breakdown Structure

### Phase 1: Foundation & Data Models

**Goals:**
- Establish data structures
- Implement context storage
- Build agent registry
- All testable independently

**Key deliverables:**
- Pydantic models for SessionContext, MCPMessage, API schemas
- ContextManager (Redis + filesystem)
- AgentRegistry
- Test fixtures

### Phase 2: MCP Server Core

**Goals:**
- MCP server startup and registration
- Message routing between agents
- REST API for user interaction
- Health checks

**Key deliverables:**
- FastAPI application
- Message routing logic
- Agent registration endpoint
- Session initialization endpoint
- Health check endpoint

### Phase 3: Agent Base Infrastructure

**Goals:**
- Common agent functionality
- LLM provider integrations
- MCP client communication

**Key deliverables:**
- BaseAgent abstract class
- Anthropic API integration
- OpenAI API integration
- Agent registration with server
- Message sending/receiving

### Phase 4: Conversation Agent

**Goals:**
- Session initialization
- OpenEphys format detection
- Dataset validation
- Metadata collection

**Key deliverables:**
- Session initialization handler
- Format detection (hybrid: extension + content)
- OpenEphys structure validation
- Dataset info extraction
- Metadata collection via LLM
- Handoff to conversion agent

### Phase 5: Conversion Agent

**Goals:**
- NeuroConv integration
- OpenEphys to NWB conversion
- Error handling with LLM messages

**Key deliverables:**
- OpenEphysRecordingInterface integration
- NWB metadata preparation
- Conversion execution
- Progress monitoring
- Error capture and LLM-generated messages
- Handoff to evaluation agent

### Phase 6: Evaluation Agent

**Goals:**
- NWB Inspector integration
- Validation execution
- Report generation

**Key deliverables:**
- NWB Inspector integration
- Validation check execution
- JSON report generation
- LLM-powered summaries
- Results return to conversation agent

### Phase 7: Integration & End-to-End

**Goals:**
- Complete workflow testing
- Error recovery testing
- Performance testing

**Key deliverables:**
- End-to-end test with real OpenEphys data
- Session-level recovery tests
- Large dataset handling (10GB+)
- Error scenario tests
- Performance benchmarks

### Phase 8: Documentation & Polish

**Goals:**
- User-facing documentation
- Deployment guides
- Code cleanup

**Key deliverables:**
- API documentation (OpenAPI)
- Setup guide (README)
- Deployment instructions
- Configuration guide
- Example usage

## Task Format Template

For each task, generate:

```markdown
### Task [ID]: [Task Name]

**Phase**: [Phase number and name]
**Prerequisites**: [List task IDs that must complete first, or "None"]
**Estimated Duration**: [1-4 hours]
**Component**: [File path or module name]
**Coverage Target**: [≥90% or ≥85%]

#### Description
[2-3 sentences describing what needs to be built]

#### Subtasks
1. **Write tests FIRST**
   - File: `tests/[type]/test_[name].py`
   - Test cases to write:
     - [ ] Test case 1 description
     - [ ] Test case 2 description
     - [ ] ...
   - Mock/fixture strategy: [describe what can be mocked vs real]

2. **Implement component**
   - File: `src/agentic_neurodata_conversion/[path]`
   - Key classes/functions to implement:
     - [ ] Class/function 1
     - [ ] Class/function 2
   - Integration points: [what this connects to]

3. **Verify and refactor**
   - Run tests: `pixi run test-unit -k test_[name]`
   - Check coverage: `pixi run test-cov-unit`
   - Run quality checks: `pixi run quality`

#### Acceptance Criteria
- [ ] All unit tests pass
- [ ] Coverage meets target (≥X%)
- [ ] Integration tests pass (if applicable)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Pre-commit hooks pass

#### Definition of Done
- Tests written and passing
- Code implemented and passing tests
- Coverage target met
- Code reviewed for quality
- Documentation updated (if public API)

#### Notes
[Any additional context, decisions, or considerations]
```

## Task Numbering Convention

Use hierarchical numbering:
- **1.x**: Phase 1 - Foundation
- **2.x**: Phase 2 - MCP Server
- **3.x**: Phase 3 - Agent Base
- **4.x**: Phase 4 - Conversation Agent
- **5.x**: Phase 5 - Conversion Agent
- **6.x**: Phase 6 - Evaluation Agent
- **7.x**: Phase 7 - Integration
- **8.x**: Phase 8 - Documentation

Example: Task 4.3 = "Phase 4 (Conversation Agent), Task 3"

## Special Considerations

### Test Data Tasks

Include tasks for creating test fixtures:
- Synthetic OpenEphys dataset (~1MB)
- Sample session contexts
- LLM response fixtures (for cost-effective testing)

### Configuration Tasks

Include tasks for:
- .env.example template
- Settings module with pydantic-settings
- Configuration validation

### Infrastructure Tasks

Include tasks for:
- Redis setup documentation
- Process management script
- Health check implementation
- Logging configuration

## Success Criteria for Task Breakdown

The task list should enable:
1. **Linear execution**: Each task has clear prerequisites
2. **Parallel work**: Independent tasks can be done simultaneously
3. **Testability**: Every task includes test requirements
4. **Completeness**: All plan components covered
5. **Clarity**: Developers know exactly what to build

## Expected Output

Generate a complete task breakdown with:
- 40-60 tasks total
- Organized into 8 phases
- Each task follows the template above
- Clear dependency chains
- Test-first approach for every implementation task
- Realistic time estimates (1-4 hours per task)

The output should be in Markdown format, ready to be used as a checklist for implementation via the `/implement` command.
