# Implementation Plan: Agent-Based Neurodata Conversion System

**Branch**: `004-implement-an-agent` | **Date**: 2025-10-03 | **Spec**:
[spec.md](./spec.md) **Input**: Feature specification from
`/specs/004-implement-an-agent/spec.md`

## Execution Flow (/plan command scope)

```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app=api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by
other commands:

- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

An agent-based system for autonomous neurodata conversion that accepts natural
language requests, selects appropriate conversion tools, coordinates multi-step
workflows, and provides conversational progress updates. The system integrates
with NWB conversion tools (pynwb, neuroconv) and uses an MCP-based architecture
to enable autonomous task execution with human oversight.

## Technical Context

**Language/Version**: Python 3.12+ **Primary Dependencies**: FastAPI, MCP,
pynwb, neuroconv, linkml, rdflib, typer, rich **Storage**: File-based (NWB
files) + optional state persistence (JSON/SQLite for task state) **Testing**:
pytest with asyncio support, pytest-mock for agent interactions **Target
Platform**: Cross-platform (Linux, Windows, macOS) **Project Type**: single
**Performance Goals**: Handle multiple concurrent conversions, responsive API
(<500ms for status queries) **Constraints**: Configurable resource limits based
on available memory/CPU **Scale/Scope**: Multiple concurrent tasks with FIFO
queue, support for large datasets (GB-scale NWB files)

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

The constitution template is currently empty (contains only placeholders).
Therefore, no specific constitutional principles need to be validated at this
stage. The project will follow standard Python best practices:

- Library-first approach (reusable agent components)
- Test-first development (TDD with pytest)
- Clear separation of concerns (agents, workflows, API)

**Status**: PASS (no constitution defined)

## Project Structure

### Documentation (this feature)

```
specs/004-implement-an-agent/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)

```
agentic_neurodata_conversion/
├── agent/                    # Agent framework and orchestration
│   ├── __init__.py
│   ├── base.py              # Base agent interface
│   ├── conversation.py      # Conversation management
│   ├── decision.py          # Decision making logic
│   └── orchestrator.py      # Workflow orchestration
├── models/                   # Data models
│   ├── __init__.py
│   ├── task.py              # Conversion task model
│   ├── workflow.py          # Workflow definition
│   ├── profile.py           # Data profile
│   ├── validation.py        # Validation report
│   └── metrics.py           # Metrics aggregate
├── services/                 # Business logic services
│   ├── __init__.py
│   ├── task_manager.py      # Task management
│   ├── tool_selector.py     # Tool selection logic
│   ├── validator.py         # NWB validation
│   └── nlp_processor.py     # Natural language processing
├── api/                      # FastAPI endpoints
│   ├── __init__.py
│   ├── conversation.py      # Conversation endpoints
│   ├── tasks.py             # Task management endpoints
│   ├── workflows.py         # Workflow execution endpoints
│   └── metrics.py           # Metrics endpoints
├── mcp_server/              # MCP server implementation
│   ├── __init__.py
│   └── server.py            # MCP server setup
└── cli/                      # CLI interface
    ├── __init__.py
    └── main.py              # Typer CLI

tests/
├── contract/                 # Contract tests for API
│   ├── test_conversation_api.py
│   ├── test_task_api.py
│   └── test_workflow_api.py
├── integration/              # Integration tests
│   ├── test_agent_workflow.py
│   ├── test_tool_integration.py
│   └── test_end_to_end.py
└── unit/                     # Unit tests
    ├── test_agent/
    ├── test_models/
    └── test_services/
```

**Structure Decision**: Using Option 1 (single project) as the codebase already
has an `agentic_neurodata_conversion/` package directory. This is a Python-based
server application with API, agent logic, and CLI components all within a single
project structure.

## Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - Agent framework choice (custom vs framework)
   - Natural language processing approach
   - Workflow orchestration pattern
   - State persistence mechanism
   - NWB tool integration strategy

2. **Generate and dispatch research agents**:

   ```
   Task: "Research agent framework options for Python (LangChain vs custom vs MCP-based)"
   Task: "Find best practices for natural language intent parsing in scientific workflows"
   Task: "Research workflow orchestration patterns for async task execution"
   Task: "Evaluate state persistence options for resumable conversions"
   Task: "Research pynwb and neuroconv integration patterns"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts

_Prerequisites: research.md complete_

1. **Extract entities from feature spec** → `data-model.md`:
   - Conversion Task: source, target, status, progress, errors, timestamps,
     results
   - Workflow: steps, tool invocations, validation checks
   - Data Profile: format, modality, structure, metadata, quality
   - Agent Decision: reasoning, tool selection, error handling
   - Validation Report: schema compliance, data integrity, quality metrics
   - Conversation Context: interaction history, clarifications, preferences
   - Resource Configuration: memory limits, CPU limits, concurrent capacity
   - Metrics Aggregate: weekly summaries, success rates, durations, error
     patterns

2. **Generate API contracts** from functional requirements:
   - POST /conversation - Start new conversation
   - GET /conversation/{id} - Get conversation context
   - POST /tasks - Create conversion task
   - GET /tasks/{id} - Get task details
   - GET /tasks - List all tasks
   - POST /workflows/execute - Execute workflow
   - GET /tasks/{id}/status - Get task status
   - GET /metrics - Get conversion metrics
   - Output OpenAPI schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Scenario 1: Natural language conversion request → tool selection →
     execution → validation
   - Scenario 2: Status query during conversion → progress report
   - Scenario 3: Multiple queued tasks → FIFO execution
   - Scenario 4: Conversion failure → error recovery → user notification
   - Scenario 5: Informal data description → clarifying questions → requirements
     gathering
   - Quickstart test = primary scenario validation

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType codex`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove
     any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/\*, failing tests, quickstart.md,
agent-specific file

## Phase 2: Task Planning Approach

_This section describes what the /tasks command will do - DO NOT execute during
/plan_

**Task Generation Strategy**:

- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P]
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:

- TDD order: Tests before implementation
- Dependency order: Models before services before agents before API
- Mark [P] for parallel execution (independent files)
- Agent framework setup before agent logic
- API contracts before endpoints

**Estimated Output**: 30-35 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

_These phases are beyond the scope of the /plan command_

**Phase 3**: Task execution (/tasks command creates tasks.md) **Phase 4**:
Implementation (execute tasks.md following constitutional principles) **Phase
5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking

_Fill ONLY if Constitution Check has violations that must be justified_

No violations - constitution template is empty.

## Progress Tracking

_This checklist is updated during execution flow_

**Phase Status**:

- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---

_Based on Constitution v2.1.1 - See `/memory/constitution.md`_
