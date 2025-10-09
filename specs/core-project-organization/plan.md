# Implementation Plan: Core Project Organization

**Branch**: `001-core-project-organization` | **Date**: 2025-10-03 | **Spec**:
[spec.md](./spec.md) **Input**: Feature specification from
`/specs/001-core-project-organization/spec.md`

## Execution Flow (/plan command scope)

```
1. Load feature spec from Input path
   → Spec loaded successfully from spec.md
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → All technical context determined from existing codebase
3. Fill the Constitution Check section based on constitution.md
   → All 6 constitutional principles verified
4. Evaluate Constitution Check section
   → No violations detected
   → Update Progress Tracking: Initial Constitution Check ✓
5. Execute Phase 0 → research.md
   → Research complete for all 8 topics
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
   → In progress
7. Re-evaluate Constitution Check section
   → Pending completion of Phase 1
8. Plan Phase 2 → Describe task generation approach
   → Ready for /tasks command
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 8. Phases 2-4 are executed by
other commands:

- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

The Core Project Organization feature establishes comprehensive project
structure for the agentic neurodata conversion system with MCP server as primary
orchestration layer. This includes:

**Primary Requirement**: Create well-organized codebase with clear boundaries
between MCP server orchestration layer, internal agent modules, and external
integrations, enabling efficient navigation, contribution, and maintenance.

**Technical Approach** (from research):

- MCP tool decorator pattern with Pydantic schema generation for standardized
  tool interfaces
- pydantic-settings for configuration management with fail-fast validation
- Ruff-centric pre-commit hooks for code quality enforcement
- Multi-dimensional pytest markers for flexible test execution
- DataLad Python API for data management with YODA principles
- structlog for structured logging with OpenTelemetry integration
- FastAPI lifespan for agent lifecycle management
- Copier templates for code scaffolding with update capabilities

## Technical Context

**Language/Version**: Python 3.11+ **Primary Dependencies**: pixi (environment),
pydantic-settings (config), FastAPI (MCP server), structlog (logging), pytest
(testing), ruff (linting), mypy (type checking), DataLad (data management)
**Storage**: Git for code, git-annex for large files, GIN for remote storage
**Testing**: pytest with markers (unit/integration/e2e), pytest-cov for
coverage, pytest-xdist for parallelization **Target Platform**: linux-64,
osx-arm64 **Project Type**: Single project with modular structure (MCP-centric
architecture) **Performance Goals**: Pre-commit <10s (fast), test suite <5min
(unit), <15min (integration), <30min (full) **Constraints**: MCP-centric
architecture (all functionality through MCP tools), TDD mandatory, DataLad
Python API only (no CLI), 80%+ code coverage **Scale/Scope**: Multi-agent system
with 4 specialized agents (Conversation, Conversion, Evaluation, Knowledge
Graph), 30+ MCP tools, comprehensive test infrastructure

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### I. MCP-Centric Architecture ✓

**Status**: COMPLIANT **Evidence**: FR-036 mandates all functionality exposed
through standardized MCP tools; direct agent invocation prohibited
**Implementation**: AgentModule entities communicate exclusively via MCP Server,
tool decorator pattern enforces standardized interfaces

### II. Agent Specialization ✓

**Status**: COMPLIANT **Evidence**: FR-027 defines clear lifecycle management;
FR-003 provides standardized agent structure **Implementation**: 4 agent types
(conversation, conversion, evaluation, knowledge_graph) with single domain
responsibility each

### III. Test-Driven Development (NON-NEGOTIABLE) ✓

**Status**: COMPLIANT **Evidence**: FR-019 enforces TDD workflow with test
markers; FR-021 requires >80% coverage **Implementation**: pytest marker
taxonomy enables TDD workflow, contract tests generated before implementation

### IV. Data Integrity & Validation ✓

**Status**: COMPLIANT **Evidence**: FR-028 provides validation system
foundation; FR-007 requires fail-fast configuration validation
**Implementation**: Pydantic models with field validators, structured error
responses, NWB Inspector integration point defined

### V. Metadata Completeness ✓

**Status**: COMPLIANT **Evidence**: FR-014 requires comprehensive documentation;
ConfigurationProfile entity tracks metadata **Implementation**: Documentation
artifacts tracked, metadata extraction patterns defined in integration points

### VI. Reproducibility & Provenance ✓

**Status**: COMPLIANT **Evidence**: FR-029 mandates DataLad Python API usage;
research phase confirms Python API patterns **Implementation**: DataLad
integration point uses Python API exclusively, provenance tracking via
datalad.api.save()

**Overall Status**: ✅ ALL CONSTITUTIONAL PRINCIPLES SATISFIED

## Project Structure

### Documentation (this feature)

```
specs/001-core-project-organization/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (complete)
├── data-model.md        # Phase 1 output (complete)
├── quickstart.md        # Phase 1 output (to be created)
├── contracts/           # Phase 1 output (to be created)
│   ├── module_structure.schema.json
│   ├── configuration.schema.json
│   ├── testing.schema.json
│   └── documentation.schema.json
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)

```
agentic-neurodata-conversion-5/
├── src/
│   └── agentic_nwb_converter/
│       ├── mcp_server/              # MCP orchestration layer
│       │   ├── core/                # Business logic
│       │   ├── adapters/            # Transport (HTTP, stdio)
│       │   ├── tools/               # MCP tool definitions
│       │   ├── middleware/          # Cross-cutting concerns
│       │   └── state/               # State management
│       ├── agents/                  # Internal agents
│       │   ├── conversation/
│       │   ├── conversion/
│       │   ├── evaluation/
│       │   └── knowledge_graph/
│       ├── clients/                 # Client implementations
│       ├── utils/                   # Shared utilities
│       ├── models/                  # Data models
│       └── config/                  # Configuration
├── tests/
│   ├── unit/                        # Unit tests
│   ├── integration/                 # Integration tests
│   ├── e2e/                         # End-to-end tests
│   ├── performance/                 # Performance tests
│   ├── security/                    # Security tests
│   ├── fixtures/                    # Test fixtures
│   └── mocks/                       # Test mocks
├── docs/                            # Documentation
│   ├── architecture/                # Architecture docs
│   ├── api/                         # API reference
│   └── guides/                      # User guides
├── examples/                        # Integration examples
├── scripts/                         # Utility scripts
├── templates/                       # Code templates (Copier)
│   ├── mcp-tool/
│   ├── agent-module/
│   └── integration-adapter/
├── etl/                             # Data pipelines
├── config/                          # Config templates
├── .specify/                        # Specify workflow
│   ├── memory/
│   │   └── constitution.md
│   ├── scripts/
│   │   └── bash/
│   │       └── update-agent-context.sh
│   └── templates/
└── pyproject.toml                   # Project metadata
```

**Structure Decision**: Single project structure with clear module boundaries.
The MCP server acts as central orchestration layer with agents, clients, and
utilities as supporting modules. Tests are organized by type
(unit/integration/e2e) with separate directories for fixtures and mocks.

## Phase 0: Outline & Research

### Research Topics Completed

1. **MCP Tool Decorator patterns** ✓
   - Decision: FastMCP-inspired decorator with Pydantic schema generation
   - Rationale: Automatic schema generation, minimal boilerplate, type safety

2. **Pydantic-Settings configuration** ✓
   - Decision: pydantic-settings v2.11+ with hierarchical models
   - Rationale: Fail-fast validation, multi-source merging, type safety

3. **Pre-commit hooks** ✓
   - Decision: Ruff-centric with format → lint → type → security ordering
   - Rationale: 10-100x faster than traditional tools, consolidated tooling

4. **Pytest markers** ✓
   - Decision: Multi-dimensional taxonomy (type, performance, resource,
     component)
   - Rationale: Flexible test selection, execution profiles, CI/CD optimization

5. **DataLad Python API** ✓
   - Decision: Hybrid Python API + CLI with YODA principles
   - Rationale: Programmatic control, subdataset precision, provenance tracking

6. **Structured logging (structlog)** ✓
   - Decision: structlog with JSON output, OpenTelemetry integration
   - Rationale: Context variables for async, processor pipeline, log-trace
     correlation

7. **Agent lifecycle management** ✓
   - Decision: FastAPI lifespan with AgentRegistry and event-driven
     communication
   - Rationale: Clean async support, centralized registry, graceful shutdown

8. **Code scaffolding (Copier vs Cookiecutter)** ✓
   - Decision: Copier v9+ for version-controlled templates with updates
   - Rationale: Template updates (killer feature), version tagging, conflict
     resolution

**Output**: research.md with all 8 topics researched, decisions documented with
rationale and alternatives

## Phase 1: Design & Contracts

_Prerequisites: research.md complete ✓_

### 1. Data Model (data-model.md) ✓

**Entities Extracted from Feature Spec**:

1. **ModuleStructure**: Logical module with path, type, dependencies, public API
2. **ConfigurationProfile**: Environment-specific settings with validation
3. **MCPTool**: Tool definition with schema, handler, middleware
4. **AgentModule**: Specialized agent with lifecycle state
5. **TestSuite**: Test collection with markers, fixtures, coverage threshold
6. **DevelopmentStandard**: Code quality rule with tool configuration
7. **DocumentationArtifact**: Generated/authored docs with format
8. **IntegrationPoint**: External system boundary with adapter
9. **QualityMetric**: Measurable indicator with threshold

All entities defined with fields, validation rules, relationships, and state
transitions.

### 2. API Contracts (contracts/)

**Contract Schemas to Generate**:

1. **module_structure.schema.json**: JSON Schema for ModuleStructure entity
   - Defines module hierarchy, dependencies, public API
   - Validates circular dependencies, path existence

2. **configuration.schema.json**: JSON Schema for ConfigurationProfile entity
   - Defines environment-specific settings structure
   - Validates required fields, env var naming, type matching

3. **testing.schema.json**: JSON Schema for TestSuite entity
   - Defines test organization, markers, coverage requirements
   - Validates marker registration, execution time limits

4. **documentation.schema.json**: JSON Schema for DocumentationArtifact entity
   - Defines documentation structure, auto-generation rules
   - Validates link integrity, format compliance

### 3. Contract Tests

Contract tests will be generated in Phase 2 (tasks.md) for each schema:

- Validate schema compliance for entity instances
- Assert required fields presence
- Test validation rules enforcement
- Verify relationship integrity

### 4. Integration Tests from User Stories

From spec.md user scenarios:

- **Scenario 1**: Repository navigation test (5-minute understanding)
- **Scenario 2**: New MCP tool addition test (seamless integration)
- **Scenario 3**: Quality gates test (pre-commit + CI/CD)
- **Scenario 4**: Third-party integration test (client patterns)
- **Scenario 5**: Architecture review test (MCP-centric compliance)
- **Scenario 6**: Agent module modification test (test suite validation)

### 5. Agent Context File (CLAUDE.md)

Update agent context incrementally:

- Run `.specify/scripts/bash/update-agent-context.sh claude`
- Add new tech stack from this plan
- Preserve manual additions between markers
- Update recent changes section
- Keep under 150 lines for token efficiency

**Output**: data-model.md ✓, contracts/\*.schema.json (pending), quickstart.md
(pending), CLAUDE.md (pending)

## Phase 2: Task Planning Approach

_This section describes what the /tasks command will do - DO NOT execute during
/plan_

### Task Generation Strategy

The /tasks command will:

1. **Load Base Template**: Use `.specify/templates/tasks-template.md`

2. **Generate Contract Test Tasks** (from contracts/):
   - One task per schema: "Write contract tests for {entity}"
   - Validate JSON Schema compliance
   - Test validation rules
   - [P] - Parallel execution (independent)

3. **Generate Model Creation Tasks** (from data-model.md):
   - One task per entity: "Implement {Entity} Pydantic model"
   - Include field validators
   - Implement state transitions
   - [P] - Parallel execution within groups

4. **Generate Integration Test Tasks** (from user scenarios):
   - One task per acceptance scenario
   - Map to test file in tests/integration/
   - Include setup/teardown

5. **Generate Implementation Tasks**:
   - MCP tool decorator implementation
   - Configuration system migration
   - Pre-commit hook configuration
   - Pytest marker setup
   - Logging infrastructure
   - Agent lifecycle implementation
   - Copier templates creation

### Ordering Strategy

**Test-Driven Development Order**:

1. Contract tests (define expectations)
2. Model implementations (pass contract tests)
3. Integration tests (define workflows)
4. Infrastructure implementations (pass integration tests)

**Dependency Order**:

1. Foundation: Configuration, logging, data models
2. Core: MCP tool decorator, agent registry
3. Infrastructure: Pre-commit, pytest markers, templates
4. Integration: Agent lifecycle, external integrations

**Parallelization Markers**:

- [P]: Independent tasks (can run in parallel)
- [S]: Sequential tasks (must run in order)

### Estimated Output

**Task Categories**:

- Contract tests: 4 tasks (1 per schema)
- Model implementations: 9 tasks (1 per entity)
- Integration tests: 6 tasks (1 per scenario)
- Infrastructure: 8 tasks (decorator, config, hooks, markers, logging,
  lifecycle, templates, docs)
- Validation: 3 tasks (test execution, coverage, quality gates)

**Total**: ~30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

_These phases are beyond the scope of the /plan command_

**Phase 3**: Task execution (/tasks command creates tasks.md) **Phase 4**:
Implementation (execute tasks.md following constitutional principles) **Phase
5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking

_Fill ONLY if Constitution Check has violations that must be justified_

| Violation | Why Needed                   | Simpler Alternative Rejected Because |
| --------- | ---------------------------- | ------------------------------------ |
| N/A       | No constitutional violations | All principles satisfied             |

## Progress Tracking

_This checklist is updated during execution flow_

**Phase Status**:

- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command) - data-model.md complete
- [ ] Phase 1: Contracts complete (/plan command) - contracts/ in progress
- [ ] Phase 1: Quickstart complete (/plan command) - quickstart.md pending
- [ ] Phase 1: Agent context complete (/plan command) - CLAUDE.md pending
- [ ] Phase 2: Task planning complete (/plan command - describe approach only) ✓
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS (pending Phase 1 completion)
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)

---

_Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`_
