# Tasks: Core Project Organization

**Feature**: 001-core-project-organization **Date**: 2025-10-03 **Status**:
Ready for execution **Total Tasks**: 50

This document provides ordered, executable tasks for implementing the core
project organization infrastructure following TDD principles and constitutional
requirements.

---

## Task Execution Order

Tasks are numbered sequentially (T001-T050) and organized into phases:

- **Setup** (T001-T007): Directory structure, environment, and tooling
- **Configuration** (T008-T012): Pydantic-settings implementation
- **Core Infrastructure** (T013-T022): Base classes, decorators, logging
- **Module Structure** (T023-T032): MCP server, agents, clients, utils
- **Testing Infrastructure** (T033-T040): Pytest config, markers, fixtures
- **Documentation** (T041-T045): Docstring setup, API docs, ADRs
- **Integration & Validation** (T046-T050): Quickstart scenarios, CI/CD

**Markers**:

- `[P]` = Can run in parallel with other [P] tasks in same section
- `[S]` = Must run sequentially (has dependencies)

---

## Setup Phase (T001-T007)

### T001: Create Project Directory Structure [P]

**File(s)**: `src/agentic_nwb_converter/`, `tests/`, `docs/`, `examples/`,
`scripts/`, `templates/`, `config/` **Depends**: None **Type**: Setup

**Description**: Create the complete directory structure for the project
following the architecture defined in plan.md. This includes all top-level
directories and core subdirectories.

**Acceptance Criteria**:

- [ ] All source directories created under `src/agentic_nwb_converter/`
- [ ] MCP server subdirectories: `core/`, `adapters/`, `tools/`, `middleware/`,
      `state/`
- [ ] Agent subdirectories: `conversation/`, `conversion/`, `evaluation/`,
      `knowledge_graph/`
- [ ] Test directories: `unit/`, `integration/`, `e2e/`, `performance/`,
      `security/`, `fixtures/`, `mocks/`
- [ ] Documentation directories: `architecture/`, `api/`, `guides/`
- [ ] Template directories: `mcp-tool/`, `agent-module/`, `integration-adapter/`
- [ ] All directories contain `__init__.py` files where appropriate
- [ ] Directory structure matches plan.md specification exactly

**Implementation Notes**: Create directories using Path.mkdir(parents=True,
exist_ok=True). Each Python package directory needs an `__init__.py` file. Use
the structure from plan.md lines 115-163.

---

### T002: Configure Pixi Environment [S]

**File(s)**: `pixi.toml` **Depends**: T001 **Type**: Setup

**Description**: Configure pixi environment with all required dependencies
including Python 3.11+, pydantic-settings, FastAPI, structlog, pytest, ruff,
mypy, bandit, DataLad, and all other dependencies identified in research.md.

**Acceptance Criteria**:

- [ ] Python version constraint: >=3.11
- [ ] All core dependencies specified with version constraints
- [ ] Development dependencies separated from production dependencies
- [ ] Platform targets: linux-64, osx-arm64
- [ ] Task definitions for common operations (test, lint, format, run)
- [ ] Environment activates successfully with `pixi install`
- [ ] All dependencies resolve without conflicts

**Implementation Notes**: Reference research.md for specific package versions.
Include pydantic-settings v2.11+, structlog, FastAPI, pytest with plugins
(pytest-cov, pytest-xdist, pytest-asyncio), ruff, mypy, bandit, DataLad. Define
pixi tasks for development workflow.

---

### T003: Configure Pre-commit Hooks [S]

**File(s)**: `.pre-commit-config.yaml` **Depends**: T002 **Type**: Setup

**Description**: Implement Ruff-centric pre-commit configuration with optimal
hook ordering: format → lint → type → security. Follow the pattern from
research.md section 3.

**Acceptance Criteria**:

- [ ] Ruff format hook configured first (v0.13.0+)
- [ ] Ruff lint hook second with --fix and --unsafe-fixes
- [ ] Mypy type checking third with strict mode
- [ ] Bandit security scanning fourth
- [ ] Standard file checks (trailing-whitespace, end-of-file-fixer, check-yaml,
      etc.)
- [ ] Hook execution order verified: format before lint before type before
      security
- [ ] Pre-commit installs successfully: `pre-commit install`
- [ ] Execution time for fast profile < 10 seconds

**Implementation Notes**: Use the exact configuration from research.md lines
251-318. Set stages appropriately (commit vs push). Skip expensive hooks (mypy,
bandit) for fast feedback; run on push stage instead.

---

### T004: Configure Ruff Linter and Formatter [P]

**File(s)**: `pyproject.toml` (tool.ruff section) **Depends**: None **Type**:
Setup

**Description**: Configure Ruff as primary linting and formatting tool with
project-specific rules. Enable relevant rule sets (pyflakes, pycodestyle, isort,
etc.) and configure formatting options.

**Acceptance Criteria**:

- [ ] Line length set to 100 characters
- [ ] Target Python version: py311
- [ ] Enabled rule sets: F (pyflakes), E/W (pycodestyle), I (isort), N
      (pep8-naming), UP (pyupgrade), ASYNC (async patterns), S (bandit), B
      (bugbear)
- [ ] Exclude patterns: **pycache**, .git, .venv, build, dist
- [ ] Format configuration: quote-style=double, indent-style=space
- [ ] Isort configuration compatible with Black-style formatting
- [ ] Configuration validates with `ruff check --config pyproject.toml`

**Implementation Notes**: Ruff replaces Black, Flake8, isort, pyupgrade. Use
ruff format for formatting, ruff check for linting. Configure select/ignore
rules to match project needs. Add per-file-ignores for test files (S101 for
asserts).

---

### T005: Configure Mypy Type Checker [P]

**File(s)**: `pyproject.toml` (tool.mypy section) **Depends**: None **Type**:
Setup

**Description**: Configure mypy for strict type checking across the codebase
with appropriate strictness levels and plugin support for Pydantic.

**Acceptance Criteria**:

- [ ] Strict mode enabled: disallow_untyped_defs, disallow_any_untyped,
      warn_return_any
- [ ] Python version: 3.11
- [ ] Pydantic plugin enabled for Pydantic v2 models
- [ ] Ignore missing imports for third-party libraries without stubs
- [ ] Exclude patterns: tests, build, dist, .venv
- [ ] Per-module configuration for gradual strictness adoption
- [ ] Configuration validates with `mypy --config-file pyproject.toml --version`

**Implementation Notes**: Use strict = true as baseline. Add pydantic plugin for
BaseModel type inference. Use ignore_missing_imports = true for untyped
third-party packages. Consider per-module overrides for legacy code during
migration.

---

### T006: Configure Pytest with Markers [S]

**File(s)**: `pyproject.toml` (tool.pytest.ini_options section) **Depends**:
T002 **Type**: Setup

**Description**: Configure pytest with multi-dimensional marker taxonomy,
execution profiles, and plugins. Implement the marker strategy from research.md
section 4.

**Acceptance Criteria**:

- [ ] All markers registered: unit, integration, e2e, fast, slow, requires_llm,
      requires_datasets, requires_docker, mock_llm, cheap_api, frontier_api,
      mcp_server, agents, data_management, client
- [ ] Test discovery patterns: unit/, integration/, e2e/, performance/,
      security/
- [ ] Plugins enabled: pytest-cov, pytest-asyncio, pytest-xdist
- [ ] Coverage settings: source=src, omit=tests
- [ ] Async mode: auto
- [ ] Strict markers enabled to catch typos
- [ ] Addopts configured: -v, --strict-markers, --tb=short
- [ ] Configuration validates with `pytest --markers`

**Implementation Notes**: Follow research.md lines 390-417 for marker
definitions. Each marker needs description. Configure coverage reporting (term,
html, xml). Set asyncio_mode = auto for async test support. Enable xdist for
parallel execution.

---

### T007: Create Development Environment Validation Script [P]

**File(s)**: `scripts/validate-dev-env.sh` **Depends**: T002, T003, T006
**Type**: Setup

**Description**: Create a script to validate that the development environment is
correctly configured. This script should check all tools, dependencies, and
configurations.

**Acceptance Criteria**:

- [ ] Checks Python version >= 3.11
- [ ] Verifies all required packages installed (pixi list)
- [ ] Validates pre-commit hooks installed
- [ ] Runs ruff check/format in dry-run mode
- [ ] Runs mypy in check mode
- [ ] Runs pytest --collect-only to verify test discovery
- [ ] Checks that all directories exist
- [ ] Exits with status 0 if all checks pass, non-zero otherwise
- [ ] Provides clear error messages for failures

**Implementation Notes**: Use bash script with set -e for fail-fast. Check
command exit codes. Provide informative output for each check. Make executable:
chmod +x scripts/validate-dev-env.sh.

---

## Configuration Phase (T008-T012)

### T008: Write Configuration Schema Contract Test [S]

**File(s)**: `tests/unit/config/test_configuration_contract.py` **Depends**:
T006 **Type**: Test

**Description**: Write contract tests that validate ConfigurationProfile
instances against the JSON Schema in contracts/configuration.schema.json. Follow
TDD - write test first before implementation.

**Acceptance Criteria**:

- [ ] Test validates required fields: name, settings, env_vars, validation_rules
- [ ] Test validates enum values for name field (development, testing, staging,
      production)
- [ ] Test validates required settings: log_level, debug_mode, data_root
- [ ] Test validates env*var naming pattern: NWB_CONVERTER*\*
- [ ] Test validates validation_rules structure
- [ ] Test fails appropriately when run (NotImplementedError or import error)
- [ ] Marked with @pytest.mark.unit and @pytest.mark.config

**Implementation Notes**: Use jsonschema library to validate dict
representations against schema. Load schema from
contracts/configuration.schema.json. Test both valid and invalid configurations.
Verify error messages are clear.

---

### T009: Implement Core Configuration Models [S]

**File(s)**: `src/agentic_nwb_converter/config/models.py` **Depends**: T008
**Type**: Implementation

**Description**: Implement Pydantic BaseSettings models for hierarchical
configuration following pydantic-settings v2.11+ patterns from research.md
section 2.

**Acceptance Criteria**:

- [ ] CoreConfig class inherits from BaseSettings
- [ ] Nested config models: AgentConfig, LoggingConfig, HTTPConfig, DataConfig
- [ ] Environment variable prefix: NWB*CONVERTER*
- [ ] Nested delimiter: \_\_ (double underscore)
- [ ] Field validators for path existence, value ranges
- [ ] Settings from .env file support
- [ ] Validation mode: validate_default=True
- [ ] Extra fields: forbid (fail on unknown config)
- [ ] Contract tests from T008 pass
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Follow research.md lines 138-178. Use Field() with
descriptions. Implement @field_validator for complex validation. Use SecretStr
for sensitive values. Test environment variable override.

---

### T010: Write Configuration Profile Loading Test [P]

**File(s)**: `tests/unit/config/test_profile_loading.py` **Depends**: T008
**Type**: Test

**Description**: Write tests for configuration profile loading from multiple
sources (env vars, .env files, defaults). Test environment-specific profiles
(development, production, testing).

**Acceptance Criteria**:

- [ ] Test loading development profile with defaults
- [ ] Test environment variable override
- [ ] Test .env file loading
- [ ] Test profile inheritance if implemented
- [ ] Test validation failure scenarios
- [ ] Test fail-fast behavior with clear error messages
- [ ] All tests marked with appropriate markers
- [ ] Tests cover >80% of config loading logic

**Implementation Notes**: Use monkeypatch fixture for environment variables.
Create temporary .env files for testing. Test priority order: env vars > .env >
defaults. Verify ValidationError messages are helpful.

---

### T011: Implement Configuration Manager [S]

**File(s)**: `src/agentic_nwb_converter/config/manager.py` **Depends**: T009,
T010 **Type**: Implementation

**Description**: Implement ConfigurationManager class for centralized
configuration access and profile management. Provide singleton pattern for
application-wide config access.

**Acceptance Criteria**:

- [ ] ConfigurationManager class with get_config() method
- [ ] Singleton pattern implementation (one instance per process)
- [ ] Profile selection via environment variable or parameter
- [ ] Lazy loading of configuration
- [ ] Thread-safe configuration access
- [ ] Configuration caching with invalidation
- [ ] Validation occurs at first access (fail-fast)
- [ ] All tests from T010 pass
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use module-level singleton or class-level instance.
Consider using functools.lru_cache for get_config(). Support reload() method for
testing. Integrate with structlog for config loading events.

---

### T012: Create Configuration Usage Examples [P]

**File(s)**: `examples/config/basic_usage.py`, `examples/config/env_override.py`
**Depends**: T011 **Type**: Documentation

**Description**: Create executable examples demonstrating configuration usage
patterns for developers. Show common scenarios like loading config, accessing
nested settings, environment overrides.

**Acceptance Criteria**:

- [ ] basic_usage.py shows standard configuration loading
- [ ] env_override.py demonstrates environment variable overrides
- [ ] Examples are executable and produce output
- [ ] Examples include comments explaining key concepts
- [ ] Examples cover development vs production profiles
- [ ] Each example can run standalone: `python examples/config/basic_usage.py`
- [ ] Examples referenced in documentation

**Implementation Notes**: Use if **name** == "**main**" pattern. Print
configuration values for demonstration. Show both success and validation error
scenarios. Keep examples simple and focused.

---

## Core Infrastructure Phase (T013-T022)

### T013: Write MCP Tool Decorator Contract Test [S]

**File(s)**: `tests/unit/mcp_server/tools/test_decorator_contract.py`
**Depends**: T006 **Type**: Test

**Description**: Write contract tests for the @mcp_tool decorator functionality.
Test automatic schema generation, parameter validation, and tool registration.
Follow TDD - test first.

**Acceptance Criteria**:

- [ ] Test decorator registers tool with ToolRegistry
- [ ] Test automatic JSON Schema generation from type hints
- [ ] Test parameter extraction from function signature
- [ ] Test docstring parsing for descriptions
- [ ] Test async function wrapping
- [ ] Test error handling and conversion to structured responses
- [ ] Test timeout enforcement
- [ ] Tests fail initially (no decorator implementation yet)
- [ ] Marked with @pytest.mark.unit and @pytest.mark.mcp_server

**Implementation Notes**: Use mock ToolRegistry for isolation. Test both sync
and async decorated functions. Verify generated schema matches MCP protocol
spec. Test edge cases: missing docstrings, complex types.

---

### T014: Implement MCP Tool Decorator [S]

**File(s)**: `src/agentic_nwb_converter/mcp_server/core/decorator.py`
**Depends**: T013 **Type**: Implementation

**Description**: Implement @mcp_tool decorator with automatic JSON Schema
generation from Pydantic models and Python type hints. Follow FastMCP-inspired
pattern from research.md section 1.

**Acceptance Criteria**:

- [ ] @mcp_tool decorator function implemented
- [ ] Accepts parameters: category, timeout_seconds, tags
- [ ] Extracts function signature using inspect.signature()
- [ ] Generates JSON Schema from type hints and Pydantic models
- [ ] Parses docstrings for parameter descriptions
- [ ] Wraps both sync and async functions
- [ ] Registers tool with global ToolRegistry at import time
- [ ] Handles errors and converts to structured responses
- [ ] All contract tests from T013 pass
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use functools.wraps to preserve function metadata.
Check asyncio.iscoroutinefunction() for async. Use Pydantic's TypeAdapter for
schema generation. Lazy-load registry to avoid circular imports. Reference
research.md lines 52-87.

---

### T015: Write Structured Logging Configuration Test [P]

**File(s)**: `tests/unit/logging/test_logging_config.py` **Depends**: T006
**Type**: Test

**Description**: Write tests for structured logging configuration with
structlog. Test development and production configurations, JSON output,
correlation ID injection, OpenTelemetry context.

**Acceptance Criteria**:

- [ ] Test development logging configuration (human-readable)
- [ ] Test production logging configuration (JSON)
- [ ] Test correlation ID injection via contextvars
- [ ] Test log level filtering
- [ ] Test processor pipeline execution order
- [ ] Test structured context binding
- [ ] Test exception logging with stack traces
- [ ] Marked with @pytest.mark.unit

**Implementation Notes**: Capture log output using io.StringIO and
contextlib.redirect_stderr. Parse JSON logs to verify structure. Test
structlog.contextvars.bind_contextvars() functionality. Verify processor order
matters.

---

### T016: Implement Structured Logging Infrastructure [S]

**File(s)**: `src/agentic_nwb_converter/logging/config.py`,
`src/agentic_nwb_converter/logging/processors.py` **Depends**: T015 **Type**:
Implementation

**Description**: Implement structlog-based logging infrastructure with
development and production configurations, correlation ID tracking, and
OpenTelemetry integration. Follow research.md section 6.

**Acceptance Criteria**:

- [ ] configure_development_logging() function with ConsoleRenderer
- [ ] configure_production_logging() function with JSONRenderer
- [ ] Custom processor for OpenTelemetry trace context injection
- [ ] Correlation ID support via contextvars
- [ ] Log level configuration per module
- [ ] Processor pipeline: merge_contextvars → add_log_level → add_logger_name →
      timestamp → format
- [ ] Exception formatting with stack traces
- [ ] All tests from T015 pass
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Follow research.md lines 715-767. Use
structlog.contextvars.merge_contextvars as first processor. Create
add_opentelemetry_context processor. Configure stdlib logging integration. Cache
logger on first use.

---

### T017: Write Agent Lifecycle Management Test [S]

**File(s)**: `tests/unit/agents/test_lifecycle.py` **Depends**: T006 **Type**:
Test

**Description**: Write tests for agent lifecycle management using FastAPI
lifespan pattern. Test agent registration, initialization, health monitoring,
graceful shutdown, and timeout handling.

**Acceptance Criteria**:

- [ ] Test AgentRegistry registration and discovery
- [ ] Test agent initialization in lifespan startup
- [ ] Test agent state transitions: UNREGISTERED → REGISTERED → INITIALIZED →
      ACTIVE
- [ ] Test graceful shutdown with timeout
- [ ] Test shutdown cancellation and cleanup
- [ ] Test health monitoring background task
- [ ] Test force shutdown on timeout
- [ ] Marked with @pytest.mark.unit and @pytest.mark.agents

**Implementation Notes**: Use pytest-asyncio for async tests. Mock FastAPI
app.state for testing. Create minimal agent implementation for testing. Test
timeout scenarios with asyncio.wait_for(). Reference research.md section 7.

---

### T018: Implement Base Agent Class [S]

**File(s)**: `src/agentic_nwb_converter/agents/base.py` **Depends**: T017
**Type**: Implementation

**Description**: Implement BaseAgent abstract class with lifecycle management,
state tracking, and graceful shutdown. This is the foundation for all
specialized agents.

**Acceptance Criteria**:

- [ ] BaseAgent abstract class with required methods
- [ ] Agent state enum: UNREGISTERED, REGISTERED, INITIALIZED, ACTIVE,
      SHUTTING_DOWN, STOPPED
- [ ] Abstract methods: initialize(), process(), shutdown()
- [ ] State transition tracking with callbacks
- [ ] Graceful shutdown with timeout support
- [ ] Background task management and cancellation
- [ ] Error tracking: error_count, success_count, last_activity
- [ ] All tests from T017 pass
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use abc.ABC for abstract base class. Track lifecycle
state with enum. Provide default shutdown() implementation. Store asyncio.Task
references for background tasks. Emit events on state transitions.

---

### T019: Implement Agent Registry [S]

**File(s)**: `src/agentic_nwb_converter/agents/registry.py` **Depends**: T018
**Type**: Implementation

**Description**: Implement AgentRegistry for centralized agent management,
discovery, and coordinated shutdown. Provides singleton access to all registered
agents.

**Acceptance Criteria**:

- [ ] AgentRegistry class with register/unregister methods
- [ ] Agent discovery by ID and type
- [ ] Agent status tracking and health queries
- [ ] Coordinated shutdown_all_agents() with timeout
- [ ] Force shutdown for stuck agents
- [ ] Iterator support for agent enumeration
- [ ] Thread-safe operations
- [ ] Integration with lifecycle tests from T017
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use dict[str, BaseAgent] for storage. Implement
**iter** for iteration. Use asyncio.gather() for parallel shutdown. Track
shutdown failures. Consider using asyncio.Lock for thread safety.

---

### T020: Write FastAPI Lifespan Integration Test [S]

**File(s)**: `tests/integration/mcp_server/test_lifespan.py` **Depends**: T017,
T019 **Type**: Test

**Description**: Write integration test for FastAPI lifespan with agent
initialization and shutdown. Test complete lifecycle from app startup to
shutdown including health monitoring.

**Acceptance Criteria**:

- [ ] Test lifespan startup initializes agents
- [ ] Test agents registered with AgentRegistry
- [ ] Test app.state.agent_registry is accessible
- [ ] Test health monitoring task starts
- [ ] Test lifespan shutdown triggers agent shutdown
- [ ] Test shutdown timeout handling
- [ ] Test cleanup of background tasks
- [ ] Marked with @pytest.mark.integration and @pytest.mark.mcp_server

**Implementation Notes**: Use FastAPI TestClient with context manager to trigger
lifespan. Create test agents for integration. Verify startup/shutdown order.
Test both successful shutdown and timeout scenarios. Reference research.md lines
896-961.

---

### T021: Implement FastAPI Lifespan with Agent Management [S]

**File(s)**: `src/agentic_nwb_converter/mcp_server/lifespan.py` **Depends**:
T020 **Type**: Implementation

**Description**: Implement FastAPI lifespan context manager for agent lifecycle
management. This manages agent initialization, health monitoring, and graceful
shutdown.

**Acceptance Criteria**:

- [ ] @asynccontextmanager function for lifespan
- [ ] Agent initialization and registration on startup
- [ ] Background health monitoring task
- [ ] AgentRegistry stored in app.state
- [ ] Graceful shutdown with 30-second timeout
- [ ] Force shutdown on timeout
- [ ] Cleanup of background tasks
- [ ] Integration test from T020 passes
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use contextlib.asynccontextmanager. Initialize agents
in try block before yield. Shutdown in finally block after yield. Use
asyncio.create_task for health monitoring. Cancel tasks on shutdown. Follow
research.md lines 906-960.

---

### T022: Write DataLad Integration Test [S]

**File(s)**: `tests/integration/data_management/test_datalad_integration.py`
**Depends**: T006 **Type**: Test

**Description**: Write integration tests for DataLad Python API integration.
Test dataset creation, subdataset installation, file operations, and provenance
tracking using only Python API (no CLI).

**Acceptance Criteria**:

- [ ] Test dataset creation with datalad.api.create()
- [ ] Test subdataset installation with version pinning
- [ ] Test file saving with provenance via datalad.api.save()
- [ ] Test file content retrieval with datalad.api.get()
- [ ] Test git-annex configuration for large files
- [ ] Test YODA principles application
- [ ] Test error handling for missing datasets
- [ ] Marked with @pytest.mark.integration and @pytest.mark.data_management
- [ ] All operations use Python API, not subprocess calls

**Implementation Notes**: Use tempfile.TemporaryDirectory for isolated test
datasets. Import datalad.api as dl. Test both Dataset class methods and
module-level functions. Verify .datalad/config created. Clean up test datasets.
Reference research.md section 5.

---

## Module Structure Phase (T023-T032)

### T023: Write Module Structure Validation Test [S]

**File(s)**: `tests/unit/utils/test_module_structure.py` **Depends**: T006
**Type**: Test

**Description**: Write tests for module structure validation against
contracts/module_structure.schema.json. Test path existence, **init**.py
presence, circular dependency detection, and public API verification.

**Acceptance Criteria**:

- [ ] Test module structure validation against JSON Schema
- [ ] Test path existence check
- [ ] Test **init**.py presence verification
- [ ] Test circular dependency detection
- [ ] Test public API symbol import verification
- [ ] Test module type enum validation
- [ ] Tests fail initially (validator not implemented)
- [ ] Marked with @pytest.mark.unit

**Implementation Notes**: Load schema from
contracts/module_structure.schema.json. Use jsonschema for validation. Test
dependency graph building. Use networkx or custom graph for circular dependency
detection. Test import verification with importlib.

---

### T024: Implement Module Structure Validator [S]

**File(s)**: `src/agentic_nwb_converter/utils/module_validator.py` **Depends**:
T023 **Type**: Implementation

**Description**: Implement module structure validation to ensure modules conform
to architectural standards. Validates against ModuleStructure schema and
enforces dependency rules.

**Acceptance Criteria**:

- [ ] ModuleValidator class with validate() method
- [ ] Path existence and **init**.py presence checks
- [ ] Circular dependency detection using graph analysis
- [ ] Public API symbol import verification
- [ ] Clear error messages for validation failures
- [ ] JSON Schema validation integration
- [ ] All tests from T023 pass
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use pathlib.Path for path operations. Build dependency
graph and check for cycles. Use importlib.import_module() for API verification.
Return validation results as structured dict or Pydantic model.

---

### T025: Create MCP Server Core Module Structure [S]

**File(s)**: `src/agentic_nwb_converter/mcp_server/core/__init__.py`,
`src/agentic_nwb_converter/mcp_server/adapters/__init__.py`,
`src/agentic_nwb_converter/mcp_server/tools/__init__.py`,
`src/agentic_nwb_converter/mcp_server/middleware/__init__.py`,
`src/agentic_nwb_converter/mcp_server/state/__init__.py` **Depends**: T014, T024
**Type**: Implementation

**Description**: Create MCP server module structure with proper **init**.py
exports. Define public APIs for core, adapters, tools, middleware, and state
modules.

**Acceptance Criteria**:

- [ ] All MCP server subdirectories have **init**.py
- [ ] core/**init**.py exports: MCPServer, mcp_tool decorator
- [ ] adapters/**init**.py exports: HTTPAdapter, StdioAdapter
- [ ] tools/**init**.py exports: ToolRegistry, ToolExecutor
- [ ] middleware/**init**.py exports: logging_middleware, auth_middleware
- [ ] state/**init**.py exports: StateManager
- [ ] Module structure validates against schema
- [ ] All exports are importable
- [ ] No circular dependencies detected

**Implementation Notes**: Use **all** to define public API. Import
implementations and re-export. Keep **init**.py files focused on exports only.
Validate with module_validator from T024.

---

### T026: Create Agent Module Structures [P]

**File(s)**:
`src/agentic_nwb_converter/agents/{conversation,conversion,evaluation,knowledge_graph}/__init__.py`,
`src/agentic_nwb_converter/agents/{conversation,conversion,evaluation,knowledge_graph}/agent.py`,
`src/agentic_nwb_converter/agents/{conversation,conversion,evaluation,knowledge_graph}/config.py`
**Depends**: T018, T024 **Type**: Implementation

**Description**: Create module structure for all four specialized agents
(conversation, conversion, evaluation, knowledge_graph) with standardized layout
and public APIs.

**Acceptance Criteria**:

- [ ] All four agent directories created with **init**.py, agent.py, config.py
- [ ] Each **init**.py exports: {Agent}Agent, {Agent}Config
- [ ] Each agent.py contains placeholder agent class inheriting from BaseAgent
- [ ] Each config.py contains Pydantic config model
- [ ] No cross-agent imports (MCP-centric architecture)
- [ ] Module structure validates against schema
- [ ] All agents follow same structure pattern

**Implementation Notes**: Use consistent naming: ConversationAgent,
ConversionAgent, EvaluationAgent, KnowledgeGraphAgent. Each agent has single
domain responsibility. Config models inherit from BaseSettings if needed. Verify
no direct agent-to-agent imports.

---

### T027: Create Client Module Structure [P]

**File(s)**: `src/agentic_nwb_converter/clients/__init__.py`,
`src/agentic_nwb_converter/clients/base.py`,
`src/agentic_nwb_converter/clients/http.py` **Depends**: T024 **Type**:
Implementation

**Description**: Create client module structure for external integrations.
Provide base client interface and HTTP client implementation for MCP server
communication.

**Acceptance Criteria**:

- [ ] clients/**init**.py exports: BaseClient, HTTPClient
- [ ] base.py contains BaseClient abstract class
- [ ] http.py contains HTTPClient implementation
- [ ] BaseClient defines standard interface: connect(), call_tool(),
      disconnect()
- [ ] HTTPClient implements MCP-over-HTTP protocol
- [ ] Module structure validates against schema
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use abc.ABC for BaseClient. HTTPClient uses httpx for
async HTTP. Define standard methods for MCP protocol operations. Include retry
logic and error handling. Support authentication headers.

---

### T028: Create Utils Module Structure [P]

**File(s)**: `src/agentic_nwb_converter/utils/__init__.py`,
`src/agentic_nwb_converter/utils/errors.py`,
`src/agentic_nwb_converter/utils/decorators.py`,
`src/agentic_nwb_converter/utils/async_helpers.py` **Depends**: T024 **Type**:
Implementation

**Description**: Create utilities module with common helpers, error classes,
decorators, and async utilities shared across the codebase.

**Acceptance Criteria**:

- [ ] utils/**init**.py exports key utilities
- [ ] errors.py defines exception hierarchy: BaseError, ConfigurationError,
      ValidationError, etc.
- [ ] decorators.py contains common decorators: retry, timeout, cache
- [ ] async_helpers.py contains async utilities: run_with_timeout,
      gather_with_errors
- [ ] All utilities have docstrings and examples
- [ ] Module structure validates against schema
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Define exception hierarchy with base exception. Create
retry decorator with exponential backoff. Implement timeout decorator using
asyncio.wait_for. Provide async helpers for common patterns. Keep utilities
focused and single-purpose.

---

### T029: Create Models Module Structure [P]

**File(s)**: `src/agentic_nwb_converter/models/__init__.py`,
`src/agentic_nwb_converter/models/tool.py`,
`src/agentic_nwb_converter/models/agent.py`,
`src/agentic_nwb_converter/models/common.py` **Depends**: T024 **Type**:
Implementation

**Description**: Create models module with Pydantic data models for core
entities. These models represent the data structures from data-model.md.

**Acceptance Criteria**:

- [ ] models/**init**.py exports all model classes
- [ ] tool.py defines: MCPTool, ToolParameter, ToolExecution models
- [ ] agent.py defines: AgentModule, AgentStatus, AgentMetrics models
- [ ] common.py defines: ErrorResponse, SuccessResponse, Pagination models
- [ ] All models use Pydantic BaseModel with validation
- [ ] Models include field validators and examples
- [ ] Module structure validates against schema
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use Pydantic v2 BaseModel. Include Field() with
descriptions. Add examples in model_config. Implement custom validators with
@field_validator. Use enums for constrained choices. Generate JSON Schema with
model_json_schema().

---

### T030: Write MCP-Centric Architecture Compliance Test [S]

**File(s)**: `tests/integration/architecture/test_mcp_compliance.py`
**Depends**: T026 **Type**: Test

**Description**: Write integration test to verify MCP-centric architecture
compliance. Ensure no direct agent-to-agent communication and all functionality
exposed through MCP tools.

**Acceptance Criteria**:

- [ ] Test scans agent modules for cross-agent imports
- [ ] Test verifies all agent communication goes through MCP server
- [ ] Test checks all tools are decorated with @mcp_tool
- [ ] Test validates agent specialization (single responsibility)
- [ ] Test ensures module boundaries are enforced
- [ ] Test generates compliance report
- [ ] Marked with @pytest.mark.integration and @pytest.mark.architecture
- [ ] Test fails if constitutional violations found

**Implementation Notes**: Use AST parsing to analyze imports. Scan for "from
agents.X import" patterns. Verify no direct agent method calls. Check decorator
presence on tool functions. Generate detailed violation report. Reference
quickstart.md scenario 5.

---

### T031: Create Data Management Module Structure [S]

**File(s)**: `src/agentic_nwb_converter/data_management/__init__.py`,
`src/agentic_nwb_converter/data_management/dataset_manager.py`,
`src/agentic_nwb_converter/data_management/datalad_integration.py` **Depends**:
T022, T024 **Type**: Implementation

**Description**: Create data management module with DataLad integration.
Implement DatasetManager class for dataset operations using DataLad Python API
only.

**Acceptance Criteria**:

- [ ] data_management/**init**.py exports: DatasetManager
- [ ] dataset_manager.py contains DatasetManager class
- [ ] datalad_integration.py contains DataLad wrapper functions
- [ ] DatasetManager uses DataLad Python API exclusively (no CLI)
- [ ] Methods: setup_dataset(), install_subdataset(), save_changes(), get_file()
- [ ] YODA principles applied in dataset creation
- [ ] Integration test from T022 passes
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Follow research.md lines 543-598 for DataLad patterns.
Use datalad.api methods. Configure git-annex via .gitattributes. Implement error
handling for DataLad exceptions. Support subdataset version pinning.

---

### T032: Create Middleware Module Structure [P]

**File(s)**: `src/agentic_nwb_converter/mcp_server/middleware/__init__.py`,
`src/agentic_nwb_converter/mcp_server/middleware/logging.py`,
`src/agentic_nwb_converter/mcp_server/middleware/correlation.py`,
`src/agentic_nwb_converter/mcp_server/middleware/auth.py` **Depends**: T016,
T024 **Type**: Implementation

**Description**: Create middleware module for MCP server request/response
processing. Implement logging, correlation ID, and authentication middleware.

**Acceptance Criteria**:

- [ ] middleware/**init**.py exports all middleware functions
- [ ] logging.py implements request/response logging middleware
- [ ] correlation.py implements correlation ID injection middleware
- [ ] auth.py implements authentication middleware (placeholder)
- [ ] All middleware follows (request, call_next) signature
- [ ] Middleware integrates with structlog
- [ ] Middleware can be chained in order
- [ ] Type hints complete and mypy clean

**Implementation Notes**: Use FastAPI middleware pattern. Each middleware is
async function. Log request/response with structlog. Inject correlation ID via
structlog.contextvars. Add X-Request-ID header. Auth middleware validates tokens
(implement simple scheme). Reference research.md lines 774-793.

---

## Testing Infrastructure Phase (T033-T040)

### T033: Create Pytest Conftest with Base Fixtures [S]

**File(s)**: `tests/conftest.py` **Depends**: T009, T018 **Type**: Test

**Description**: Create root conftest.py with base fixtures used across all test
types. Include configuration fixtures, mock objects, and test utilities.

**Acceptance Criteria**:

- [ ] test_config fixture providing test configuration
- [ ] mock_agent fixture providing test agent instance
- [ ] temp_directory fixture for isolated file operations
- [ ] event_loop fixture for async tests
- [ ] Fixtures properly scoped (function, module, session)
- [ ] Cleanup implemented with yield fixtures
- [ ] Fixtures documented with docstrings
- [ ] All fixtures work with pytest --fixtures

**Implementation Notes**: Use @pytest.fixture decorator. Scope fixtures
appropriately. Use yield for setup/teardown. Provide test configuration with
safe defaults. Create minimal mock implementations. Use tmpdir or tmp_path for
temporary directories.

---

### T034: Create Unit Test Fixtures [P]

**File(s)**: `tests/unit/conftest.py` **Depends**: T033 **Type**: Test

**Description**: Create unit test specific fixtures including mocks for external
dependencies, test data generators, and isolated test environments.

**Acceptance Criteria**:

- [ ] mock_llm_client fixture for LLM mocking
- [ ] mock_dataset fixture for test data
- [ ] mock_tool_registry fixture for tool testing
- [ ] mock_agent_registry fixture for agent testing
- [ ] test_data_generator fixtures for various entities
- [ ] All fixtures properly isolated (no external calls)
- [ ] Fixtures use factories for customization
- [ ] Documentation included

**Implementation Notes**: Use unittest.mock or pytest-mock. Create factory
fixtures with @pytest.fixture(params=...) for variations. Generate test data
matching schema. Ensure mocks are fast and deterministic. Document fixture usage
in docstrings.

---

### T035: Create Integration Test Fixtures [P]

**File(s)**: `tests/integration/conftest.py` **Depends**: T033 **Type**: Test

**Description**: Create integration test fixtures including test server
instances, database connections, and real (but test-scoped) external services.

**Acceptance Criteria**:

- [ ] test_app fixture providing FastAPI TestClient
- [ ] test_database fixture for database testing
- [ ] test_dataset_manager fixture with real DataLad dataset
- [ ] agent_registry fixture with real agents
- [ ] Fixtures setup and teardown properly
- [ ] Cleanup ensures no test pollution
- [ ] Session-scoped fixtures for expensive setup
- [ ] Documentation included

**Implementation Notes**: Use FastAPI TestClient for HTTP testing. Create
temporary DataLad datasets. Initialize real agents in isolated registry. Use
session scope for expensive fixtures. Implement thorough cleanup in finalizers.

---

### T036: Write Contract Tests for All Schemas [S]

**File(s)**: `tests/unit/contracts/test_all_schemas.py` **Depends**: T006, T008
**Type**: Test

**Description**: Write comprehensive contract tests validating all entities
against their JSON Schemas: module_structure, configuration, testing,
documentation.

**Acceptance Criteria**:

- [ ] Test module_structure.schema.json validation
- [ ] Test configuration.schema.json validation
- [ ] Test testing.schema.json validation
- [ ] Test documentation.schema.json validation
- [ ] Test valid instances pass validation
- [ ] Test invalid instances fail with clear errors
- [ ] Test boundary conditions and edge cases
- [ ] Marked with @pytest.mark.unit and @pytest.mark.contracts
- [ ] Coverage >80% for schema validation logic

**Implementation Notes**: Load all schemas from contracts/ directory. Use
jsonschema.validate(). Test required fields, enums, patterns, ranges. Create
valid and invalid test cases. Verify error messages are helpful. Parametrize
tests for each schema.

---

### T037: Create Test Data Generators [P]

**File(s)**: `tests/fixtures/generators.py` **Depends**: T029 **Type**: Test

**Description**: Create test data generators for Pydantic models following
schema contracts. Use factories or Hypothesis for property-based testing.

**Acceptance Criteria**:

- [ ] Generator functions for all main entities
- [ ] Generators produce schema-valid instances
- [ ] Support for valid and invalid data generation
- [ ] Customization via parameters
- [ ] Integration with Hypothesis for property testing
- [ ] Generators are deterministic with seed
- [ ] Documentation and examples included

**Implementation Notes**: Consider using Hypothesis with hypothesis.strategies.
Create factory functions for each model. Use Pydantic model_validate() for
validation. Support edge cases. Provide sensible defaults. Make generators
composable.

---

### T038: Create Mock Implementations [P]

**File(s)**: `tests/mocks/mock_agents.py`, `tests/mocks/mock_tools.py`,
`tests/mocks/mock_clients.py` **Depends**: T018, T014, T027 **Type**: Test

**Description**: Create mock implementations of agents, tools, and clients for
isolated testing. Mocks should implement same interfaces but with controllable
behavior.

**Acceptance Criteria**:

- [ ] MockAgent class implementing BaseAgent interface
- [ ] MockTool decorator for test tools
- [ ] MockClient implementing BaseClient interface
- [ ] Controllable behavior (success, failure, timeout)
- [ ] State tracking for verification (called_with, call_count)
- [ ] Async support for async methods
- [ ] Clear documentation on usage
- [ ] Integration with test fixtures

**Implementation Notes**: Inherit from real base classes where possible. Use
unittest.mock.Mock for flexible behavior. Track calls and arguments. Support
asyncio for async mocks. Provide convenience methods for common scenarios.
Document in docstrings.

---

### T039: Write Performance Test Suite [P]

**File(s)**: `tests/performance/test_tool_execution.py`,
`tests/performance/test_agent_throughput.py` **Depends**: T014, T018 **Type**:
Test

**Description**: Create performance test suite to validate execution time
requirements. Test tool execution, agent throughput, and system scalability.

**Acceptance Criteria**:

- [ ] Test tool execution time < specified timeout
- [ ] Test agent initialization time < 5 seconds
- [ ] Test concurrent tool execution scalability
- [ ] Test memory usage under load
- [ ] Marked with @pytest.mark.performance
- [ ] Benchmarking with pytest-benchmark if needed
- [ ] Performance metrics logged for tracking
- [ ] Tests have reasonable tolerances

**Implementation Notes**: Use time.perf_counter() for timing. Test with various
concurrency levels. Use pytest-benchmark for statistical analysis. Set realistic
thresholds. Track metrics over time. Mark as slow tests. Consider using
pytest-timeout.

---

### T040: Write Security Test Suite [P]

**File(s)**: `tests/security/test_input_validation.py`,
`tests/security/test_auth.py` **Depends**: T014 **Type**: Test

**Description**: Create security test suite validating input validation,
authentication, and protection against common vulnerabilities.

**Acceptance Criteria**:

- [ ] Test input validation against injection attacks
- [ ] Test authentication and authorization
- [ ] Test rate limiting if implemented
- [ ] Test secure configuration handling
- [ ] Test secrets not logged or exposed
- [ ] Marked with @pytest.mark.security
- [ ] Integration with bandit for static analysis
- [ ] Security findings documented

**Implementation Notes**: Test SQL injection, command injection, path traversal.
Verify authentication failures. Test token validation. Ensure secrets use
SecretStr. Check logs don't contain sensitive data. Run bandit in CI. Document
security requirements.

---

## Documentation Phase (T041-T045)

### T041: Setup Docstring Standards and Validation [S]

**File(s)**: `pyproject.toml` (tool.pydocstyle section),
`scripts/validate-docstrings.py` **Depends**: T004 **Type**: Documentation

**Description**: Configure docstring linting and validation. Establish
Google-style docstring standard and validation tools.

**Acceptance Criteria**:

- [ ] Pydocstyle configured in pyproject.toml
- [ ] Google-style docstrings specified
- [ ] Validation script checks docstring coverage
- [ ] Required elements: description, Args, Returns, Raises, Examples
- [ ] Minimum 80% docstring coverage for public functions
- [ ] Script integrated with pre-commit (optional stage)
- [ ] CI validation of docstrings
- [ ] Documentation of standards in contributing guide

**Implementation Notes**: Use pydocstyle or ruff's pydocstyle rules. Configure
convention = "google". Create validation script with AST parsing. Check public
functions (not starting with \_). Integrate with interrogate for coverage. Add
to CI pipeline.

---

### T042: Generate API Documentation [S]

**File(s)**: `docs/api/`, documentation build scripts **Depends**: T041, T025,
T026, T027 **Type**: Documentation

**Description**: Setup automated API documentation generation from code using
docstrings. Generate documentation for all modules following the documentation
schema.

**Acceptance Criteria**:

- [ ] Documentation generation tool configured (pdoc, sphinx, mkdocs)
- [ ] API docs generated for all modules
- [ ] Docstrings extracted and formatted
- [ ] Type hints displayed in documentation
- [ ] Examples included from docstrings
- [ ] Navigation structure follows module hierarchy
- [ ] Build script: scripts/build-docs.sh
- [ ] Validation against documentation.schema.json

**Implementation Notes**: Use pdoc for lightweight docs or sphinx for
comprehensive. Configure templates for consistent style. Include source links.
Generate during CI. Publish to docs site. Validate generated docs exist and are
complete. Reference contracts/documentation.schema.json.

---

### T043: Create Architecture Documentation [P]

**File(s)**: `docs/architecture/overview.md`, `docs/architecture/mcp-server.md`,
`docs/architecture/agents.md`, `docs/architecture/data-flow.md` **Depends**:
None **Type**: Documentation

**Description**: Create comprehensive architecture documentation describing
system design, components, interactions, and design decisions.

**Acceptance Criteria**:

- [ ] overview.md describes high-level architecture
- [ ] mcp-server.md documents MCP server design
- [ ] agents.md describes agent architecture and specialization
- [ ] data-flow.md shows data flow through system with diagrams
- [ ] All documents in Markdown format
- [ ] Diagrams included (mermaid or embedded images)
- [ ] Links between documents validated
- [ ] Validation against documentation.schema.json

**Implementation Notes**: Use Mermaid for diagrams in Markdown. Describe
MCP-centric architecture. Document agent specialization. Show tool registration
flow. Include sequence diagrams for key workflows. Reference constitution.md
principles. Keep diagrams simple and clear.

---

### T044: Create ADR Template and Initial ADRs [P]

**File(s)**: `docs/architecture/decisions/template.md`,
`docs/architecture/decisions/0001-mcp-centric-architecture.md`,
`docs/architecture/decisions/0002-pydantic-settings.md` **Depends**: None
**Type**: Documentation

**Description**: Create Architecture Decision Record (ADR) template and document
key architectural decisions made during research phase.

**Acceptance Criteria**:

- [ ] ADR template with standard sections: Context, Decision, Consequences,
      Alternatives
- [ ] ADR 0001: MCP-Centric Architecture (from research.md)
- [ ] ADR 0002: Pydantic-Settings Configuration (from research.md)
- [ ] ADRs follow numbering convention: 0001, 0002, etc.
- [ ] Each ADR has status: Proposed, Accepted, Deprecated, Superseded
- [ ] Index of ADRs in decisions/README.md
- [ ] Validation against documentation.schema.json

**Implementation Notes**: Use standard ADR template format. Extract decisions
from research.md. Document context, alternatives considered, rationale,
consequences. Number sequentially. Track status. Create index for easy
discovery. Link to related ADRs.

---

### T045: Create Developer Getting Started Guide [P]

**File(s)**: `docs/guides/getting-started.md`, `docs/guides/contributing.md`,
`docs/guides/testing.md` **Depends**: T007, T041 **Type**: Documentation

**Description**: Create comprehensive developer guides for onboarding,
contributing, and testing. These guides help new developers understand the
project quickly.

**Acceptance Criteria**:

- [ ] getting-started.md covers environment setup, first run, basic workflow
- [ ] contributing.md covers code standards, PR process, commit conventions
- [ ] testing.md covers test structure, running tests, writing tests
- [ ] All guides in Markdown with clear step-by-step instructions
- [ ] Code examples included where appropriate
- [ ] Links to architecture docs and API docs
- [ ] Validation against documentation.schema.json
- [ ] Supports quickstart.md scenario 1 (5-minute understanding)

**Implementation Notes**: Keep guides practical and example-driven. Include
common troubleshooting. Link to relevant documentation. Show actual commands
with expected output. Cover pre-commit hooks, pytest markers, TDD workflow.
Reference validation script from T007.

---

## Integration & Validation Phase (T046-T050)

### T046: Implement Quickstart Scenario 1 - Repository Navigation [S]

**File(s)**: `tests/e2e/test_repository_navigation.py` **Depends**: T001, T025,
T026 **Type**: Test

**Description**: Implement end-to-end test for quickstart scenario 1 validating
that repository structure is intuitive and well-organized for 5-minute
understanding.

**Acceptance Criteria**:

- [ ] Test validates all expected directories exist
- [ ] Test checks README.md exists and contains key sections
- [ ] Test validates architecture documentation presence
- [ ] Test checks test organization structure
- [ ] Test verifies module organization follows plan
- [ ] Marked with @pytest.mark.e2e
- [ ] Test execution represents actual user experience
- [ ] Test passes, confirming scenario 1 success

**Implementation Notes**: Reference quickstart.md scenario 1 (lines 21-61).
Check directory existence with pathlib. Validate README structure. Check for
architecture docs. Time test execution to verify < 5 minutes understanding. Make
test reflect actual developer experience.

---

### T047: Implement Quickstart Scenario 2 - Add New MCP Tool [S]

**File(s)**: `tests/e2e/test_add_mcp_tool.py` **Depends**: T014, T050 **Type**:
Test

**Description**: Implement end-to-end test for quickstart scenario 2 validating
seamless integration of new MCP tools using templates and decorators.

**Acceptance Criteria**:

- [ ] Test simulates Copier template generation
- [ ] Test validates generated files exist and have correct structure
- [ ] Test verifies @mcp_tool decorator usage
- [ ] Test runs generated tests (should fail with NotImplementedError)
- [ ] Test implements minimal tool and verifies tests pass
- [ ] Test validates tool registration with MCP server
- [ ] Marked with @pytest.mark.e2e
- [ ] Test passes, confirming scenario 2 success

**Implementation Notes**: Reference quickstart.md scenario 2 (lines 64-110). Use
temporary directory for test. Generate tool from template (or simulate). Run
pytest on generated tests. Implement minimal tool. Verify registration. Clean up
after test.

---

### T048: Implement Quickstart Scenario 3 - Quality Gates [S]

**File(s)**: `tests/e2e/test_quality_gates.py` **Depends**: T003, T006 **Type**:
Test

**Description**: Implement end-to-end test for quickstart scenario 3 validating
pre-commit hooks and quality gates run automatically and correctly.

**Acceptance Criteria**:

- [ ] Test creates intentionally bad code
- [ ] Test runs pre-commit hooks
- [ ] Test validates hooks fix formatting issues
- [ ] Test validates hooks catch type errors
- [ ] Test validates test markers work
- [ ] Test validates coverage enforcement
- [ ] Marked with @pytest.mark.e2e
- [ ] Test passes, confirming scenario 3 success

**Implementation Notes**: Reference quickstart.md scenario 3 (lines 113-170).
Create test file with issues. Run pre-commit programmatically. Check output for
fixes. Verify type errors caught. Test pytest marker filtering. Verify coverage
thresholds. Use subprocess for pre-commit/pytest.

---

### T049: Create Copier Templates for Code Generation [S]

**File(s)**: `templates/mcp-tool/copier.yml`, `templates/mcp-tool/*.jinja`,
`templates/agent-module/copier.yml`, `templates/agent-module/*.jinja`
**Depends**: T014, T018 **Type**: Implementation

**Description**: Create Copier templates for generating MCP tools and agent
modules. Templates should include all boilerplate with proper structure and
tests.

**Acceptance Criteria**:

- [ ] MCP tool template with copier.yml configuration
- [ ] Tool template generates: tool.py, test_tool.py
- [ ] Agent module template with copier.yml configuration
- [ ] Agent template generates: **init**.py, agent.py, config.py, tests/
- [ ] Templates use Jinja2 for variable substitution
- [ ] Prompts for required information (name, category, etc.)
- [ ] Generated code follows project standards
- [ ] Templates support updates via copier update
- [ ] Documentation on template usage

**Implementation Notes**: Follow research.md section 8 (lines 1140-1306). Use
copier.yml for configuration. Create .jinja templates. Include validators for
inputs. Generate proper imports and structure. Include TODOs for implementation.
Test template generation works.

---

### T050: Create CI/CD Pipeline Configuration [S]

**File(s)**: `.github/workflows/ci.yml`, `.github/workflows/docs.yml`
**Depends**: T003, T006, T042 **Type**: Setup

**Description**: Create GitHub Actions workflows for CI/CD including testing,
linting, type checking, security scanning, and documentation deployment.

**Acceptance Criteria**:

- [ ] ci.yml runs on pull requests and pushes to main
- [ ] Workflow jobs: lint, type-check, unit-tests, integration-tests, security
- [ ] Matrix testing across Python 3.11, 3.12
- [ ] Parallel job execution where possible
- [ ] Coverage reporting integrated
- [ ] Quality gates enforced (80% coverage, no type errors)
- [ ] docs.yml builds and deploys documentation
- [ ] Workflow badges in README
- [ ] Fast feedback: unit tests < 5 min, full pipeline < 15 min

**Implementation Notes**: Use GitHub Actions. Setup pixi environment. Cache
dependencies. Run pre-commit hooks. Execute pytest with markers. Upload coverage
to Codecov. Run security scans with bandit. Build docs and deploy to GitHub
Pages. Use matrix for Python versions. Fail on quality violations.

---

## Summary

**Total Tasks**: 50 **Setup**: 7 tasks (T001-T007) **Configuration**: 5 tasks
(T008-T012) **Core Infrastructure**: 10 tasks (T013-T022) **Module Structure**:
10 tasks (T023-T032) **Testing Infrastructure**: 8 tasks (T033-T040)
**Documentation**: 5 tasks (T041-T045) **Integration & Validation**: 5 tasks
(T046-T050)

**Execution Strategy**:

1. Complete Setup phase first (dependencies for all other work)
2. Implement Configuration phase (needed by most modules)
3. Build Core Infrastructure (foundation for modules)
4. Create Module Structure (parallel where possible)
5. Establish Testing Infrastructure (enables TDD for remaining work)
6. Generate Documentation (can overlap with implementation)
7. Run Integration & Validation (final verification)

**TDD Workflow**:

- Always write tests before implementation (Test type tasks before
  Implementation type)
- Verify tests fail initially (red)
- Implement to pass tests (green)
- Refactor while keeping tests passing (refactor)
- Maintain >80% code coverage

**Constitutional Compliance**:

- All tasks respect MCP-centric architecture (no direct agent-to-agent
  communication)
- Agent specialization enforced (single responsibility per agent)
- TDD mandatory (test tasks before implementation tasks)
- Data validation via Pydantic (fail-fast configuration)
- Metadata completeness (comprehensive docstrings)
- Reproducibility via DataLad Python API

**Parallelization Guide**: Tasks marked [P] can run in parallel with other [P]
tasks in the same phase if different files are modified. Tasks marked [S] must
run sequentially due to dependencies.

---

**Ready for Execution**: All tasks are specific, executable, and ordered for
successful implementation following constitutional principles and technical
standards.
