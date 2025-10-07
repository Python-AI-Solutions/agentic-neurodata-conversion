# Phase 0 Research: Core Project Organization

**Research Date**: 2025-10-03 **Status**: Complete **Purpose**: Inform
implementation decisions for Phase 0 of Core Project Organization

---

## 1. MCP Tool Decorator Implementation Patterns

### Decision

Implement a **FastMCP-inspired decorator pattern** with automatic JSON Schema
generation from Pydantic models and Python type hints, using `@mcp_tool()`
decorator for tool registration with the MCP server.

### Rationale

**Technical Merits:**

- **Automatic Schema Generation**: FastMCP (2025) demonstrates that decorators
  can automatically generate MCP-compliant JSON Schema from function signatures
  and docstrings, eliminating manual schema writing
- **Type Safety with Pydantic**: Pydantic v2 models provide runtime validation
  and automatic JSON Schema export, ensuring type-safe tool parameters
- **Minimal Boilerplate**: Single decorator reduces registration overhead
  compared to manual tool registration patterns
- **Docstring Integration**: Parameter descriptions automatically extracted from
  docstrings and added to schema (following PydanticAI pattern)

**Ecosystem Fit:**

- Aligns with existing `agentic_neurodata_conversion/core/tools.py` architecture
  which already uses ToolDefinition with Pydantic models
- Compatible with current ToolRegistry/ToolExecutor pattern - decorator can
  populate registry at import time
- Integrates seamlessly with async/await patterns already established in
  codebase

**Maintenance Burden:**

- Low maintenance - decorator logic centralized in single module
- Pydantic handles schema evolution automatically when types change
- Type hints serve as single source of truth for both runtime validation and
  schema generation

### Alternatives Considered

**Manual Registration (Current Pattern):**

- _Rejected_: Requires explicit ToolDefinition instantiation and
  registry.register_tool() calls, leading to verbose boilerplate
- Creates disconnect between function signature and tool definition
- Current codebase shows this pattern in
  `ConversionToolSystem._register_conversion_tools()` - results in 100+ lines
  per tool

**Class-Based Tools:**

- _Rejected_: Inheritance-based approach (e.g., `class MyTool(BaseTool)`)
  increases complexity
- Harder to compose and test compared to decorated functions
- Not aligned with MCP's function-oriented protocol

**Metadata Annotations (Python 3.9+):**

- _Rejected_: Using `Annotated[Type, ToolMetadata(...)]` is more verbose than
  decorator
- Less discoverable than decorator pattern
- Doesn't integrate well with existing ToolRegistry pattern

### Implementation Notes

**Decorator Design Pattern:**

```python
from typing import Annotated
from pydantic import Field
from agentic_neurodata_conversion.core.tools import mcp_tool, ToolCategory

@mcp_tool(
    category=ToolCategory.ANALYSIS,
    timeout_seconds=300,
    tags=["analysis", "metadata"]
)
async def dataset_analysis(
    dataset_dir: Annotated[str, Field(description="Path to dataset directory")],
    use_llm: Annotated[bool, Field(description="Use LLM for extraction")] = False,
    session_id: str | None = None
) -> dict[str, Any]:
    """Analyze dataset structure and extract metadata for NWB conversion.

    Returns analysis results including detected formats, metadata, and file information.
    """
    # Implementation
    pass
```

**Key Considerations:**

- **Import-Time Registration**: Decorator should register tools with global
  registry on module import, avoiding explicit registration calls
- **Validation Strategy**: Use Pydantic's `field_validator` for complex
  parameter validation beyond type checking
- **Error Handling**: Decorator should wrap functions with try/except to convert
  exceptions to structured ToolExecution error responses
- **Async Support**: Must handle both sync and async functions (check with
  `asyncio.iscoroutinefunction()`)
- **Parameter Extraction**: Parse function signature using `inspect.signature()`
  to build ToolParameter list
- **Docstring Parsing**: Use `inspect.getdoc()` and parse Google/NumPy style
  docstrings for parameter descriptions

**Gotchas:**

- Avoid circular imports by lazy-loading registry (use `get_registry()`
  function)
- Don't use decorator on class methods directly - create standalone functions or
  use `@staticmethod`
- Ensure RunContext or server parameters are excluded from schema (mark with
  leading underscore)
- Test schema generation separately from business logic for better test
  isolation

---

## 2. Pydantic-Settings Configuration Architecture

### Decision

Adopt **pydantic-settings v2.11+ BaseSettings** with hierarchical configuration
model, environment variable prefixing (`NWB_CONVERTER_`), and multi-source
configuration merging (env vars → .env files → config files → defaults).

### Rationale

**Technical Merits:**

- **Fail-Fast Validation**: Pydantic-settings validates all configuration at
  startup with clear error messages indicating missing/invalid settings
- **Type Safety**: Full type checking and IDE autocomplete for configuration
  access
- **Hierarchical Models**: Nested configuration models (e.g., `AgentConfig`,
  `LoggingConfig`) provide intuitive organization already demonstrated in
  `core/config.py`
- **Multi-Source Support**: Automatic loading from environment variables, .env
  files, JSON/YAML/TOML files, and cloud secret managers

**Ecosystem Fit:**

- Already partially implemented in `agentic_neurodata_conversion/core/config.py`
  with dataclass-based approach
- Migration path: Convert existing dataclasses to pydantic-settings BaseSettings
  models
- Compatible with existing environment variable pattern (`ANC_*` prefix)

**Maintenance Burden:**

- Medium - requires discipline in maintaining env_prefix consistency
- Built-in validation reduces runtime configuration errors
- Schema evolution supported through Pydantic's migration tools

### Alternatives Considered

**Dataclasses with Manual Loading (Current):**

- _Rejected_: Current `ConfigurationManager` in `core/config.py` manually
  implements env loading, lacks automatic validation
- No fail-fast validation - errors discovered at runtime when accessing config
- Manual type conversion prone to bugs (see `_dict_to_config` complexity)

**Dynaconf:**

- _Rejected_: Extra dependency with overlapping functionality
- Less type-safe than pydantic-settings (dynamic attribute access)
- Overkill for project needs - we don't need dynamic runtime reloading

**Hydra (Facebook):**

- _Rejected_: Designed for ML experiment configuration, not service
  configuration
- YAML-centric approach doesn't align with our environment-variable-first
  strategy
- Heavier dependency footprint

**Python-decouple:**

- _Rejected_: Lightweight but lacks validation and hierarchical configuration
- No schema generation or type safety
- Would still need Pydantic for validation layer

### Implementation Notes

**Configuration Architecture Pattern:**

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class AgentConfig(BaseSettings):
    """Agent-specific configuration."""
    timeout_seconds: int = Field(default=300, ge=1, description="Agent timeout")
    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")
    memory_limit_mb: int | None = Field(default=None, ge=1, description="Memory limit")

    model_config = SettingsConfigDict(
        env_prefix='NWB_CONVERTER_AGENT_',
        env_nested_delimiter='__'
    )

class CoreConfig(BaseSettings):
    """Root configuration with nested models."""
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    data_directory: Path = Field(default=Path("./data"))

    # Nested configurations
    agents: AgentConfig = Field(default_factory=AgentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    http: HTTPConfig = Field(default_factory=HTTPConfig)

    model_config = SettingsConfigDict(
        env_prefix='NWB_CONVERTER_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        validate_default=True,
        extra='forbid'  # Fail on unknown config keys
    )

    @field_validator('data_directory', mode='after')
    @classmethod
    def ensure_directory_exists(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v
```

**Environment Variable Mapping:**

- `NWB_CONVERTER_DEBUG=true` → `CoreConfig.debug`
- `NWB_CONVERTER_AGENT__TIMEOUT_SECONDS=600` →
  `CoreConfig.agents.timeout_seconds`
- `NWB_CONVERTER_HTTP__PORT=8080` → `CoreConfig.http.port`

**Key Considerations:**

- **Prefix Strategy**: Use consistent `NWB_CONVERTER_` prefix for all env vars
  to avoid collisions
- **Nested Delimiter**: Use `__` (double underscore) for nested configuration
  (e.g., `AGENT__TIMEOUT`)
- **Validation Timing**: Set `validate_default=True` to validate defaults at
  model creation
- **Extra Fields**: Use `extra='forbid'` to catch typos in environment variables
  early
- **Secret Handling**: Use pydantic-settings' `SecretStr` type for sensitive
  values, configure to read from Azure Key Vault or AWS Secrets Manager
- **Profile Support**: Create separate config classes per environment
  (DevelopmentConfig, ProductionConfig) inheriting from base
- **Runtime Updates**: For feature flags, implement separate `RuntimeConfig`
  class that can be hot-reloaded without restart

**Gotchas:**

- Environment variables always take precedence over .env files - document this
  clearly
- Nested models require `default_factory` not bare defaults to avoid shared
  state bugs
- Path fields should use `Path` type, not `str`, for automatic path resolution
- Use `@field_validator` with `mode='after'` for validators that need the final
  value
- Don't put business logic in validators - keep them focused on validation only

---

## 3. Pre-commit Hook Integration

### Decision

Implement **Ruff-centric pre-commit configuration** with optimal hook ordering:
format → lint → type → security → test (selective), using
`.pre-commit-config.yaml` with staged execution stages.

### Rationale

**Technical Merits:**

- **Ruff Performance**: 10-100x faster than traditional tool chains
  (Black+Flake8+isort), written in Rust (2025 industry standard)
- **Consolidated Tooling**: Ruff replaces Black, Flake8, isort, pyupgrade,
  bandit (partial), reducing tool count from 5+ to 2 (Ruff + mypy)
- **Optimal Ordering**: Format-first prevents linter/formatter conflicts;
  type-check after formatting ensures consistency
- **Selective Testing**: Use pytest with `--lf` (last-failed) and file-change
  detection to run only affected tests

**Ecosystem Fit:**

- Already have `.pre-commit-config.yaml` with comprehensive hooks
- Current config includes ruff-format (v0.13.0) and ruff linter - modern
  foundation
- Existing pytest configuration with markers supports selective execution

**Maintenance Burden:**

- Low - Ruff updates are stable and backwards compatible
- Pre-commit framework auto-updates hooks weekly (configured in
  `.pre-commit-config.yaml`)
- Single tool (Ruff) reduces maintenance surface compared to multiple linters

### Alternatives Considered

**Black + Flake8 + isort (Traditional Stack):**

- _Rejected_: Slower execution (200x slower than Ruff based on 2025 benchmarks)
- Multiple tools increase CI/CD time and developer friction
- Ruff provides superset of functionality with single configuration

**Pylint:**

- _Rejected_: Slower than Ruff, more opinionated, higher false positive rate
- Configuration complexity higher than Ruff
- Ruff's rule set covers most Pylint checks (PL\* rules)

**Prettier for Python:**

- _Rejected_: Not designed for Python (JS-centric), less community adoption
- Ruff-format provides equivalent functionality with Python-specific
  intelligence

**Full Test Suite on Pre-commit:**

- _Rejected_: Running all tests pre-commit causes 5+ minute delays, breaks flow
- Current best practice: Run fast tests locally, full suite in CI
- Selective test execution via pytest markers is acceptable compromise

### Implementation Notes

**Pre-commit Configuration Template:**

```yaml
repos:
  # Format FIRST - prevents lint conflicts
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.0
    hooks:
      - id: ruff-format
        name: Format code with Ruff
        stages: [commit]

  # Lint SECOND - after formatting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.0
    hooks:
      - id: ruff
        name: Lint with Ruff
        args: [--fix, --unsafe-fixes, --exit-non-zero-on-fix]
        stages: [commit]

  # Type check THIRD - on formatted code
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.17.1
    hooks:
      - id: mypy
        name: Type check with mypy
        args: [--strict, --ignore-missing-imports]
        additional_dependencies: [pydantic>=2.0, types-requests]
        stages: [commit]

  # Security check FOURTH
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.6
    hooks:
      - id: bandit
        name: Security scan
        args: [-r, --skip=B101, --severity-level=high]
        stages: [commit]

  # Selective tests LAST (optional)
  - repo: local
    hooks:
      - id: pytest-changed
        name: Test changed files
        entry: bash -c 'pytest tests/ -m "not slow" --lf --tb=short'
        language: system
        stages: [push] # Only on push, not commit
        pass_filenames: false

  # File checks (parallel with above)
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: detect-private-key
      - id: check-merge-conflict

default_language_version:
  python: python3.12

ci:
  autofix_commit_msg: "[pre-commit.ci] auto fixes"
  autoupdate_schedule: weekly
  skip: [mypy, pytest-changed] # CI runs these separately
```

**Execution Profiles:**

- **Fast (default)**: Format + Lint + File checks (< 10 seconds)
- **Full (pre-push)**: Add Type check + Security + Selective tests (< 60
  seconds)
- **Complete (CI)**: All hooks + full test suite + coverage

**Key Considerations:**

- **Hook Ordering Rationale**: Formatters before linters avoids conflicts; type
  checking after formatting ensures consistent analysis surface
- **Selective Testing Strategy**: Use `git diff --name-only` to detect changed
  Python files, map to test modules, run with `pytest --lf` (last-failed first)
- **Performance Optimization**: Run slow hooks (mypy, bandit) on `pre-push`
  stage, not `commit` stage
- **Auto-fix Behavior**: Ruff's `--fix` flag auto-corrects issues;
  `--unsafe-fixes` enables more aggressive fixes (use cautiously)
- **CI Integration**: Configure `.pre-commit-ci.yaml` for automated hook
  updates, but skip hooks that need special setup (mypy types, full test suite)

**Gotchas:**

- Don't run formatters and linters in parallel - format must complete first
- Mypy requires `additional_dependencies` for type stub packages (types-\*,
  pydantic)
- Bandit's `--skip=B101` skips assert warnings (needed for pytest tests)
- Pytest markers must be registered in `pyproject.toml` to avoid "unknown
  marker" warnings
- Use `pass_filenames: false` for hooks that don't accept file arguments (like
  pytest)
- Test execution time: Limit pre-commit tests to <30 seconds to maintain
  developer flow

---

## 4. Pytest Marker Strategy

### Decision

Implement **multi-dimensional marker taxonomy** with execution profiles: (1)
Test type markers (unit, integration, e2e), (2) Performance markers (fast,
slow), (3) Resource markers (requires_llm, requires_datasets), and (4) Component
markers (mcp_server, agents, data_management) for flexible test selection.

### Rationale

**Technical Merits:**

- **Execution Profiles**: Enable fast feedback loops
  (`pytest -m "unit and not slow"` < 5 min) vs comprehensive validation
  (`pytest -m "integration or e2e"` < 30 min)
- **Resource Awareness**: `requires_llm` and `requires_datasets` markers allow
  selective execution based on available resources (local dev vs CI)
- **Component Isolation**: Component markers enable testing specific subsystems
  without running entire suite
- **CI/CD Optimization**: Different marker combinations for PR checks, nightly
  builds, and release validation

**Ecosystem Fit:**

- Current `pyproject.toml` already defines 14 markers including LLM cost tiers
  and component markers
- Aligns with existing test organization pattern in `tests/unit/`,
  `tests/integration/`, `tests/e2e/`
- Compatible with pytest-xdist for parallel execution within marker groups

**Maintenance Burden:**

- Low - marker registration in `pyproject.toml` prevents accidental marker
  creation
- Clear naming convention (verb_object pattern) maintains consistency
- Pytest's `--strict-markers` flag enforces registered markers only

### Alternatives Considered

**Directory-Based Organization Only:**

- _Rejected_: Insufficient granularity for cross-cutting concerns (e.g., slow
  integration tests vs fast integration tests)
- Can't express resource requirements (LLM, datasets) through directory
  structure alone
- Current codebase already has directory structure; markers provide additional
  dimension

**Pytest Plugins (pytest-category, pytest-groups):**

- _Rejected_: Built-in markers provide equivalent functionality without extra
  dependencies
- Plugin ecosystem fragmented; markers are first-class pytest feature
- Markers more widely understood by developers

**Test Class Inheritance:**

- _Rejected_: `class TestSlow(SlowTestBase)` pattern is verbose and inflexible
- Doesn't support multiple categorizations (e.g., slow integration test)
- Markers allow dynamic composition of test categories

**Tag-Based (pytest-tags):**

- _Rejected_: Markers are tags; separate plugin unnecessary
- Marker syntax (`@pytest.mark.slow`) is standard and well-documented

### Implementation Notes

**Marker Taxonomy Design:**

```python
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    # Test Type Markers (mutually exclusive)
    "unit: Direct functionality tests with no external dependencies",
    "integration: Tests combining multiple components",
    "e2e: End-to-end workflow tests",

    # Performance Markers
    "fast: Tests completing in <1 second (default assumption)",
    "slow: Tests taking >10 seconds (deselect with '-m \"not slow\"')",

    # Resource Requirement Markers
    "requires_llm: Tests needing LLM API access",
    "requires_datasets: Tests needing test dataset downloads",
    "requires_docker: Tests needing Docker daemon",

    # LLM Cost Tier Markers (subset of requires_llm)
    "mock_llm: Tests with mocked LLM responses (free)",
    "cheap_api: Tests with inexpensive cloud APIs (<$0.01/test)",
    "frontier_api: Tests with expensive frontier models (>$0.10/test)",

    # Component Markers
    "mcp_server: MCP server functionality",
    "agents: Agent functionality",
    "data_management: Data management functionality",
    "client: Client library functionality",
]

# Execution Profiles
[tool.pytest.ini_options.markers_profile]
fast_feedback = "unit and not slow and not requires_llm and not requires_datasets"
integration_check = "integration and not requires_llm"
full_suite = ""  # All tests
nightly = "slow or requires_datasets or frontier_api"
```

**Test Marking Pattern:**

```python
import pytest

@pytest.mark.unit
@pytest.mark.mcp_server
async def test_tool_registration():
    """Fast unit test for tool registration."""
    pass

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_llm
@pytest.mark.cheap_api
@pytest.mark.agents
async def test_agent_with_real_llm():
    """Integration test using real LLM API."""
    pass

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.requires_datasets
@pytest.mark.data_management
async def test_full_conversion_pipeline(test_dataset):
    """End-to-end test with real dataset."""
    pass
```

**Execution Commands:**

```bash
# Fast feedback (< 5 min) - local development
pytest -m "unit and not slow"

# Integration check (< 15 min) - PR validation
pytest -m "integration and not requires_llm and not slow"

# Full suite without expensive resources (< 30 min) - CI
pytest -m "not frontier_api and not requires_datasets"

# Nightly comprehensive (< 2 hours) - scheduled CI
pytest -m ""  # All tests

# Component-specific
pytest -m "mcp_server"  # Only MCP server tests
pytest -m "agents and integration"  # Agent integration tests
```

**Key Considerations:**

- **Marker Composition**: Use boolean expressions for complex selections:
  `-m "unit and (mcp_server or agents)"`
- **Coverage Reporting**: Generate separate coverage reports per execution
  profile: `pytest -m "unit" --cov --cov-report=html:htmlcov/unit`
- **Parallel Execution**: Combine markers with pytest-xdist:
  `pytest -m "integration" -n auto` (auto-detect CPU cores)
- **CI Configuration**: Define execution profiles as pytest.ini aliases or CI
  environment variables
- **Cost Management**: Use LLM tier markers to control test costs: run
  `mock_llm` locally, `cheap_api` in PR checks, `frontier_api` only in nightly
  builds

**Gotchas:**

- Always use `--strict-markers` to catch typos in marker names
- Don't over-mark tests - default to `unit` + component markers; add
  `slow`/`requires_*` only when necessary
- Marker expressions use Python boolean logic: `-m "not (slow or requires_llm)"`
  requires parentheses
- When tests fail, include marker info in CI output for debugging:
  `pytest -m "integration" -v --tb=short`
- Document execution profiles in CI/CD configuration and developer docs to
  ensure consistency
- Use `pytest --markers` to list all registered markers with descriptions

---

## 5. DataLad Python API Integration Patterns

### Decision

Adopt **hybrid Python API + CLI pattern** with Python API (`datalad.api`) for
programmatic dataset management and CLI for one-off operations, following **YODA
principles** for subdataset organization and git-annex configuration for large
file handling.

### Rationale

**Technical Merits:**

- **API/CLI Parity**: DataLad provides identical functionality through both
  interfaces - use API for automation, CLI for interactive work
- **Subdataset Precision**: Python API enables programmatic subdataset
  installation with version pinning:
  `dl.install(dataset=root, path=subds, source=url, reckless='ephemeral')`
- **Annex Control**: Programmatic configuration of git-annex rules via
  `.gitattributes` for largefiles policy (>10MB → annex, code → git)
- **YODA Compliance**: Python API supports YODA procedure (`cfg_yoda`) for
  standardized project structure

**Ecosystem Fit:**

- Existing `etl/setup_datalad.py` demonstrates Python API usage for ETL setup
- Current `.datalad/config` and `etl/.datalad_config` show DataLad integration
  already in place
- Compatible with conversion provenance tracking needs in
  `agentic_neurodata_conversion/data_management/`

**Maintenance Burden:**

- Medium - DataLad API changes are infrequent but require migration testing
- git-annex configuration requires deep understanding of annex expressions
- Subdataset management adds operational complexity (install, update, get)

### Alternatives Considered

**CLI-Only Approach:**

- _Rejected_: Shell scripting for subdataset management is brittle, hard to test
- No programmatic access to DataLad status for runtime decisions
- Error handling in shell scripts inferior to Python try/except

**DVC (Data Version Control):**

- _Rejected_: Focuses on ML pipeline versioning, not general data management
- Doesn't support nested subdatasets like DataLad
- Less suitable for neuroscience data provenance tracking

**Git LFS:**

- _Rejected_: No subdataset support, weak provenance tracking
- Requires centralized server; DataLad works with distributed remotes (GIN, S3,
  HTTP)
- Doesn't integrate with existing neuroscience infrastructure (DANDI, OpenNeuro)

**Manual Git Submodules:**

- _Rejected_: No large file handling (would need separate annex setup)
- Submodule updates are manual and error-prone
- DataLad provides higher-level abstractions over submodules

### Implementation Notes

**Python API Integration Pattern:**

```python
import datalad.api as dl
from pathlib import Path

class DatasetManager:
    """Manages DataLad datasets for conversion workflows."""

    def __init__(self, root_path: Path):
        self.root = root_path
        self.dataset = dl.Dataset(root_path)

    def setup_conversion_dataset(self) -> None:
        """Initialize dataset with YODA structure."""
        if not self.dataset.is_installed():
            dl.create(
                dataset=self.root,
                annex=True,
                cfg_proc=['yoda', 'text2git']  # YODA + text files in git
            )

        # Configure annex for large files (>10MB)
        gitattributes = self.root / '.gitattributes'
        gitattributes.write_text("""
            * annex.largefiles=((mimeencoding=binary)and(largerthan=10MB))
            *.py !annex.largefiles
            *.md !annex.largefiles
            *.json !annex.largefiles
        """)

    def install_input_dataset(self, name: str, source_url: str) -> Path:
        """Install subdataset for input data."""
        subds_path = self.root / 'inputs' / name

        dl.install(
            dataset=self.dataset,
            path=subds_path,
            source=source_url,
            recursive=False,  # Don't recursively install nested subdatasets
            get_data=False,   # Don't download file content yet
            reckless='ephemeral'  # For temporary processing datasets
        )

        return subds_path

    def get_file_content(self, file_path: Path) -> None:
        """Download file content from annex."""
        dl.get(
            dataset=self.dataset,
            path=file_path,
            jobs=4  # Parallel downloads
        )

    def save_conversion_result(self, paths: list[Path], message: str) -> None:
        """Save conversion results with provenance."""
        dl.save(
            dataset=self.dataset,
            path=paths,
            message=message,
            recursive=True  # Save changes in subdatasets too
        )
```

**Subdataset Management Best Practices:**

```python
# Install CatalystNeuro conversion repos as subdatasets
def install_conversion_repos(dataset: dl.Dataset, repos: list[str]) -> None:
    """Install conversion repositories as version-pinned subdatasets."""
    base_url = "https://github.com/catalystneuro"
    conversions_path = dataset.path / "inputs" / "catalystneuro-conversions"

    for repo in repos:
        repo_url = f"{base_url}/{repo}"
        local_path = conversions_path / repo

        # Install at specific version tag
        dl.install(
            dataset=dataset,
            path=local_path,
            source=repo_url,
            version='v1.2.3'  # Pin to known-good version
        )

        # Get only Python interface files, not large data
        dl.get(
            dataset=dataset,
            path=local_path / "src",
            recursive=True
        )
```

**Large File Handling with git-annex:**

```bash
# .gitattributes configuration for ETL directory
* annex.largefiles=((mimeencoding=binary)and(largerthan=10MB))

# Always in git (not annex)
*.md !annex.largefiles
*.txt !annex.largefiles
*.py !annex.largefiles
*.yaml !annex.largefiles
*.json !annex.largefiles

# Workflow files
workflows/**/*.py !annex.largefiles

# Test fixtures (small)
evaluation-data/test-fixtures/**/* !annex.largefiles
```

**Key Considerations:**

- **API vs CLI Choice**: Use Python API for repeatable workflows (CI/CD,
  testing), CLI for ad-hoc exploration
- **Reckless Mode**: Use `reckless='ephemeral'` for temporary processing
  datasets that can be re-downloaded
- **Lazy Loading**: Install subdatasets without content (`get_data=False`),
  download files on-demand with `dl.get()`
- **Version Pinning**: Always specify `version` parameter when installing
  subdatasets for reproducibility
- **Parallel Operations**: Use `jobs` parameter for parallel downloads:
  `dl.get(path=paths, jobs=4)`
- **Provenance Tracking**: Use descriptive save messages:
  `dl.save(message="Convert dataset X using method Y")`
- **Remote Configuration**: Configure siblings (remotes) for dataset publishing:
  `dl.siblings('add', name='gin', url='...')`

**Gotchas:**

- `dl.install()` vs `dl.get()`: `install` operates on datasets, `get` operates
  on file content - use `get` after `install` to fetch data
- Subdataset state is tracked by parent as a git commit hash, not branch name -
  updates require explicit `datalad update --merge`
- git-annex expressions are sensitive to whitespace - test `.gitattributes`
  rules with `git annex whereis <file>`
- DataLad operations are git operations under the hood - failed operations may
  leave uncommitted changes, always check `git status`
- Special remotes (S3, GIN) require additional configuration via
  `git annex initremote`
- Use `dl.status()` to check for uncommitted changes before save operations

---

## 6. Structured Logging Infrastructure

### Decision

Implement **structlog-based logging infrastructure** with JSON output for
production, human-readable output for development, correlation ID tracking via
contextvars, and OpenTelemetry integration for distributed tracing.

### Rationale

**Technical Merits:**

- **Context Variables**: structlog's native contextvars support enables
  automatic correlation ID injection across async boundaries (critical for async
  agent system)
- **Processor Pipeline**: Flexible processor chain allows injecting
  trace_id/span_id from OpenTelemetry span context for log-trace correlation
- **Performance**: Lazy formatting and async-aware design outperforms
  python-json-logger for high-throughput services
- **Structured Output**: First-class support for JSON logging with nested
  context, unlike logging.Formatter-based approaches

**Ecosystem Fit:**

- Current `core/logging.py` uses custom StructuredFormatter and
  DevelopmentFormatter - migration path to structlog clear
- Compatible with existing log_context() context manager pattern - can enhance
  with structlog's bind/unbind
- Integrates with FastAPI/Uvicorn for HTTP request correlation

**Maintenance Burden:**

- Low - structlog API stable, mature library (10+ years)
- OpenTelemetry integration requires configuration but is well-documented
- Clear separation between dev/production logging via processor configuration

### Alternatives Considered

**python-json-logger:**

- _Rejected_: Requires manual context injection, no native contextvars support
- Logging.Formatter-based approach limits flexibility compared to structlog's
  processors
- No built-in OpenTelemetry integration

**Standard logging with custom filters:**

- _Rejected_: Current approach in `core/logging.py` is verbose, requires manual
  context management
- ContextFilter class needs thread-local storage workarounds for async code
- Correlation ID tracking difficult across async task boundaries

**loguru:**

- _Rejected_: Great for simple apps, but structured logging support is secondary
- Less suitable for distributed tracing integration
- Weaker ecosystem for APM platform integration (Datadog, Elastic)

**Eliot (Twisted logging):**

- _Rejected_: Designed for action-tree logging, overkill for request tracking
- Less widely adopted, smaller ecosystem
- JSON-only, no human-readable dev format

### Implementation Notes

**Structlog Configuration Pattern:**

```python
import structlog
from structlog.contextvars import merge_contextvars
from opentelemetry import trace
from contextvars import ContextVar

# Correlation ID context var
request_id_var: ContextVar[str | None] = ContextVar('request_id', default=None)

def add_opentelemetry_context(logger, method_name, event_dict):
    """Processor to inject OpenTelemetry trace context."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict['trace_id'] = format(ctx.trace_id, '032x')
        event_dict['span_id'] = format(ctx.span_id, '016x')
    return event_dict

def configure_production_logging():
    """Production: JSON logs with correlation IDs and traces."""
    structlog.configure(
        processors=[
            merge_contextvars,  # Inject contextvars automatically
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            add_opentelemetry_context,  # Add trace_id/span_id
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def configure_development_logging():
    """Development: Human-readable colored logs."""
    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="%H:%M:%S.%f"),
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

**Correlation ID Middleware (FastAPI):**

```python
from fastapi import Request
import structlog
import uuid

async def correlation_id_middleware(request: Request, call_next):
    """Inject correlation ID into request context."""
    correlation_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

    # Bind correlation ID to structlog context
    structlog.contextvars.bind_contextvars(
        request_id=correlation_id,
        request_path=request.url.path,
        request_method=request.method
    )

    try:
        response = await call_next(request)
        response.headers['X-Request-ID'] = correlation_id
        return response
    finally:
        # Clear context after request
        structlog.contextvars.clear_contextvars()
```

**Usage in Application Code:**

```python
import structlog

log = structlog.get_logger()

async def process_conversion(dataset_id: str):
    """Process conversion with automatic context injection."""
    # Bind additional context
    log = log.bind(dataset_id=dataset_id, operation="conversion")

    log.info("conversion_started")

    try:
        result = await run_conversion(dataset_id)
        log.info("conversion_completed", duration_ms=result.duration)
        return result
    except Exception as e:
        log.error("conversion_failed", error=str(e), exc_info=True)
        raise
```

**Log Level Configuration Per Module:**

```python
import logging

# Configure standard library logging levels
logging.getLogger("agentic_neurodata_conversion").setLevel(logging.INFO)
logging.getLogger("agentic_neurodata_conversion.agents").setLevel(logging.DEBUG)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Structlog respects these levels
```

**Key Considerations:**

- **Processor Order**: merge_contextvars must be first to capture context early,
  JSONRenderer must be last
- **Context Isolation**: Use `clear_contextvars()` in finally blocks to prevent
  context leakage between requests
- **OpenTelemetry Setup**: Initialize OTLP exporter before configuring structlog
  to ensure span context available
- **Performance**: Use `cache_logger_on_first_use=True` to avoid logger
  recreation overhead
- **Exception Logging**: Include `structlog.processors.format_exc_info` to
  format tracebacks in JSON
- **Local Development**: Use `ConsoleRenderer(colors=True)` with
  `exception_formatter=structlog.dev.plain_traceback` for readable exceptions

**Gotchas:**

- Don't use `log.bind()` in module scope - it creates shared state across
  requests; use `log = log.bind()` in function scope
- contextvars require Python 3.7+; structlog uses thread-locals as fallback but
  loses async isolation
- Standard library logging handlers must be configured for structlog output to
  appear (use `structlog.stdlib.LoggerFactory()`)
- `merge_contextvars` only works if configured - missing it means correlation
  IDs won't appear in logs
- JSON renderer escapes backslashes - use raw strings for regex patterns in log
  messages
- Avoid logging large objects - structlog serializes entire dictionaries; log
  object IDs instead

---

## 7. Agent Lifecycle Management

### Decision

Implement **FastAPI lifespan-based lifecycle management** with centralized
AgentRegistry, async context manager pattern for initialization/shutdown, and
event-driven communication via message bus for inter-agent coordination.

### Rationale

**Technical Merits:**

- **Lifespan API**: FastAPI's `@asynccontextmanager` lifespan provides clean
  startup/shutdown hooks with proper async support (2025 standard)
- **Registry Pattern**: Centralized AgentRegistry (already in `agents/base.py`)
  enables discovery, health monitoring, and graceful shutdown coordination
- **Event-Driven**: Message bus decouples agents, allowing dynamic
  addition/removal without code changes
- **Timeout-Based Shutdown**: MCP protocol specification (2025-03-26) mandates
  timeout-based graceful shutdown with cancellation notifications

**Ecosystem Fit:**

- Current `agents/base.py` already implements AgentRegistry with registration,
  status tracking, and shutdown methods
- Compatible with MCP server architecture - agents register capabilities as MCP
  tools
- FastAPI's lifespan integrates with existing HTTP adapter in
  `mcp_server/http_adapter.py`

**Maintenance Burden:**

- Medium - lifespan management requires understanding async context managers
- Event bus adds operational complexity (message routing, dead letter queues)
- Agent health monitoring needs background tasks (memory, error rates)

### Alternatives Considered

**@app.on_event decorators (FastAPI legacy):**

- _Rejected_: Deprecated in FastAPI 0.95.0+, replaced by lifespan
- No proper async context manager support, making resource cleanup error-prone
- Cannot share state between startup and shutdown easily

**Manual threading.Thread lifecycle:**

- _Rejected_: Sync threading doesn't integrate with async agents
- No built-in cancellation support, must implement custom shutdown signals
- Error handling during shutdown complex with thread join timeouts

**Celery for agent orchestration:**

- _Rejected_: Heavyweight for in-process agents, designed for distributed task
  queues
- Adds Redis/RabbitMQ dependency unnecessarily
- Over-engineered for single-server multi-agent system

**NATS/Redis Streams for communication:**

- _Rejected_: External message broker not needed for same-process agents
- Increases infrastructure complexity and failure modes
- asyncio.Queue or in-memory event bus sufficient for current scale

### Implementation Notes

**Lifespan-Based Agent Lifecycle:**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog
from agentic_neurodata_conversion.agents.base import AgentRegistry
from agentic_neurodata_conversion.agents.conversation import ConversationAgent
from agentic_neurodata_conversion.agents.conversion import ConversionAgent

log = structlog.get_logger()

@asynccontextmanager
async def agent_lifespan(app: FastAPI):
    """Manage agent lifecycle with startup and shutdown."""
    registry = AgentRegistry()

    # Startup: Initialize and register agents
    log.info("agent_lifecycle_startup")

    try:
        # Initialize agents with configuration
        conversation_agent = ConversationAgent(
            config=app.state.config.agents,
            agent_id="conversation-001"
        )
        conversion_agent = ConversionAgent(
            config=app.state.config.agents,
            agent_id="conversion-001"
        )

        # Register agents
        registry.register_agent(conversation_agent)
        registry.register_agent(conversion_agent)

        # Start background health monitoring
        health_task = asyncio.create_task(monitor_agent_health(registry))

        # Expose registry to app
        app.state.agent_registry = registry

        log.info("agent_lifecycle_startup_complete", agent_count=len(registry))

        # Yield control to application
        yield

    finally:
        # Shutdown: Graceful agent termination
        log.info("agent_lifecycle_shutdown_starting")

        # Cancel health monitoring
        health_task.cancel()

        # Shutdown all agents with timeout
        try:
            await asyncio.wait_for(
                registry.shutdown_all_agents(),
                timeout=30.0  # 30 second shutdown timeout
            )
            log.info("agent_lifecycle_shutdown_complete")
        except asyncio.TimeoutError:
            log.error("agent_lifecycle_shutdown_timeout", timeout_seconds=30)
            # Force shutdown
            await registry.force_shutdown_all()

# Create FastAPI app with lifespan
app = FastAPI(lifespan=agent_lifespan)
```

**Agent Registry with Health Monitoring:**

```python
from datetime import datetime, timedelta
import asyncio

async def monitor_agent_health(registry: AgentRegistry, interval: int = 30):
    """Background task to monitor agent health."""
    log = structlog.get_logger()

    while True:
        try:
            await asyncio.sleep(interval)

            for agent in registry:
                # Check error rate
                if agent.error_count > 0:
                    error_rate = agent.error_count / (agent.success_count + agent.error_count)
                    if error_rate > 0.5:  # >50% error rate
                        log.warning(
                            "agent_high_error_rate",
                            agent_id=agent.agent_id,
                            error_rate=error_rate
                        )

                # Check stale agents (no activity in 1 hour)
                if datetime.utcnow() - agent.last_activity > timedelta(hours=1):
                    log.warning(
                        "agent_stale",
                        agent_id=agent.agent_id,
                        last_activity=agent.last_activity.isoformat()
                    )
        except asyncio.CancelledError:
            log.info("health_monitor_cancelled")
            break
        except Exception as e:
            log.error("health_monitor_error", error=str(e))
```

**Event-Driven Inter-Agent Communication:**

```python
from typing import Protocol
import asyncio

class EventBus:
    """In-memory event bus for agent communication."""

    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, event_type: str) -> asyncio.Queue:
        """Subscribe to event type, returns queue for receiving events."""
        queue = asyncio.Queue(maxsize=100)
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(queue)
        return queue

    async def publish(self, event_type: str, data: dict):
        """Publish event to all subscribers."""
        if event_type in self._subscribers:
            tasks = [
                q.put(data)
                for q in self._subscribers[event_type]
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

# Agent subscribes to events
class ConversionAgent(BaseAgent):
    def __init__(self, config, agent_id, event_bus: EventBus):
        super().__init__(config, agent_id)
        self.event_bus = event_bus
        self.dataset_queue = event_bus.subscribe("dataset.analyzed")

    async def start_listening(self):
        """Background task to process events."""
        while True:
            dataset_info = await self.dataset_queue.get()
            await self.process_dataset(dataset_info)
```

**Graceful Shutdown with Cancellation:**

```python
class BaseAgent:
    async def shutdown(self) -> None:
        """Graceful shutdown with resource cleanup."""
        log = structlog.get_logger().bind(agent_id=self.agent_id)
        log.info("agent_shutdown_starting")

        old_status = self.status
        self.status = AgentStatus.STOPPED

        # Cancel active tasks
        if hasattr(self, '_background_tasks'):
            for task in self._background_tasks:
                task.cancel()

            # Wait for cancellation with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._background_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                log.warning("agent_shutdown_tasks_timeout")

        # Close resources (DB connections, file handles)
        if hasattr(self, '_cleanup'):
            await self._cleanup()

        self._notify_status_change(old_status, self.status)
        log.info("agent_shutdown_complete")
```

**Key Considerations:**

- **Initialization Order**: Register agents in dependency order (base agents
  before dependent agents)
- **Shutdown Timeout**: MCP spec recommends 30-60 second timeout for graceful
  shutdown
- **Error Isolation**: Wrap agent initialization in try/except to prevent one
  agent failure from blocking others
- **Health Metrics**: Track last_activity, error_count, success_count per agent
  for monitoring
- **Event Bus Choice**: Use asyncio.Queue for same-process agents; upgrade to
  Redis Streams if agents move to separate processes
- **Background Tasks**: Store asyncio.Task references to cancel during shutdown

**Gotchas:**

- FastAPI lifespan runs before middleware - can't access request context in
  startup
- `asyncio.gather(..., return_exceptions=True)` prevents one agent shutdown
  failure from blocking others
- Agent registry must be stored in `app.state` to share across request handlers
- Don't await infinite loops directly in lifespan startup - use
  `asyncio.create_task()` for background tasks
- TestClient requires `with TestClient(app) as client:` to trigger lifespan
  events
- Event bus queues must have `maxsize` to prevent memory exhaustion if consumers
  fall behind

---

## 8. Code Scaffolding Tools

### Decision

Adopt **Copier (v9+)** as primary scaffolding tool with version-controlled
templates, replace Cookiecutter templates with Copier equivalents, and provide
update capabilities for existing projects to sync with template evolution.

### Rationale

**Technical Merits:**

- **Template Updates**: Copier's killer feature - projects can update when
  templates evolve, addressing major Cookiecutter limitation
- **Version Tagging**: Templates versioned by git tags, projects always update
  to stable releases not HEAD commits
- **Conflict Resolution**: Git-based merge conflicts instead of .rej files,
  familiar to developers
- **YAML Configuration**: Single `copier.yml` vs Cookiecutter's
  `cookiecutter.json` + `hooks/`, cleaner design

**Ecosystem Fit:**

- CatalystNeuro uses Cookiecutter templates (can reference for conversion
  patterns)
- Migration path: Create Copier equivalents of existing templates, maintain
  Cookiecutter for backwards compatibility
- Compatible with existing CI/CD - Copier is pip-installable, no special
  environment needed

**Maintenance Burden:**

- Low - Copier's update mechanism reduces template drift compared to
  Cookiecutter's one-time generation
- YAML configuration easier to maintain than JSON + pre/post-gen hooks
- Active development, stable API (v9.0+ released 2024)

### Alternatives Considered

**Cookiecutter (Current Standard):**

- _Rejected for new templates_: No update capability - once generated, projects
  diverge from template
- JSON configuration less expressive than YAML
- CatalystNeuro's existing templates valuable as reference, but Copier
  supersedes

**GitHub Templates:**

- _Rejected_: No variable substitution, purely git-based templating
- No update mechanism after initial clone
- Limited to repository structure, not code generation

**Yeoman:**

- _Rejected_: Node.js-based, adds runtime dependency for Python project
- More complex than needed for Python-only templates
- Smaller Python ecosystem adoption

**Project Template (PyPA):**

- _Rejected_: Deprecated, merged into Cookiecutter's successor (Copier)
- No active development or community

### Implementation Notes

**Copier Template Structure:**

```
templates/
├── mcp-tool/              # Template for new MCP tools
│   ├── copier.yml         # Template configuration
│   ├── {{ tool_name }}.py.jinja
│   └── test_{{ tool_name }}.py.jinja
│
├── agent-module/          # Template for new agents
│   ├── copier.yml
│   ├── {{ _copier_conf.answers_file }}.jinja
│   ├── {{ agent_name }}/
│   │   ├── __init__.py.jinja
│   │   ├── agent.py.jinja
│   │   ├── config.py.jinja
│   │   └── tests/
│   │       └── test_{{ agent_name }}.py.jinja
│   └── README.md.jinja
│
└── integration-adapter/   # Template for client integrations
    ├── copier.yml
    └── ...
```

**Template Configuration (copier.yml):**

```yaml
# MCP Tool Template
_templates_suffix: .jinja
_skip_if_exists:
  - tests/conftest.py # Don't overwrite existing conftest

# Prompts
tool_name:
  type: str
  help: Name of the MCP tool (snake_case)
  validator:
    "{% if not tool_name.isidentifier() %}Must be valid Python identifier{%
    endif %}"

tool_category:
  type: str
  help: Tool category
  choices:
    - analysis
    - conversion
    - evaluation
    - pipeline
    - utility

requires_llm:
  type: bool
  help: Does this tool require LLM access?
  default: false

timeout_seconds:
  type: int
  help: Tool execution timeout (seconds)
  default: 300
  when: "{{ tool_category != 'utility' }}" # Conditional prompting

# Template versioning
_min_copier_version: "9.0.0"

# Post-generation message
_message_after_copy: |
  Tool '{{ tool_name }}' created successfully!

  Next steps:
  1. Implement logic in {{ tool_name }}.py
  2. Add tests in test_{{ tool_name }}.py
  3. Register tool in mcp_server/tools/__init__.py
```

**Tool Template ({{ tool_name }}.py.jinja):**

```python
"""{{ tool_name | title | replace('_', ' ') }} - MCP Tool

Generated by Copier on {{ _copier_conf.now }}
"""

from typing import Annotated, Any
from pydantic import Field
from agentic_neurodata_conversion.core.tools import mcp_tool, ToolCategory

@mcp_tool(
    category=ToolCategory.{{ tool_category.upper() }},
    timeout_seconds={{ timeout_seconds }},
    tags=["{{ tool_category }}"]
)
async def {{ tool_name }}(
    # TODO: Add parameters
    dataset_path: Annotated[str, Field(description="Path to dataset")]
) -> dict[str, Any]:
    """{{ tool_name | title | replace('_', ' ') }}.

    TODO: Add detailed description

    Args:
        dataset_path: Path to the dataset to process

    Returns:
        Dictionary with processing results
    """
    # TODO: Implement tool logic
    raise NotImplementedError("Tool logic not implemented")
```

**Using Copier for Code Generation:**

```bash
# Generate new MCP tool
copier copy templates/mcp-tool agentic_neurodata_conversion/mcp_server/tools/

# Generate new agent module
copier copy templates/agent-module agentic_neurodata_conversion/agents/

# Update existing project from template
cd agentic_neurodata_conversion/agents/my_agent
copier update  # Updates to latest template version

# Update to specific template version
copier update --vcs-ref=v1.2.0
```

**Template Update Workflow:**

```bash
# 1. Developer updates template
cd templates/mcp-tool
# Make changes to copier.yml or .jinja files
git commit -m "feat: add async validation to tool template"
git tag v1.3.0
git push --tags

# 2. Existing projects update
cd agentic_neurodata_conversion/mcp_server/tools/my_tool
copier update
# Copier shows diff, developer resolves conflicts in Git
# Commit updated scaffolding
git add .
git commit -m "chore: update tool scaffolding to v1.3.0"
```

**Integration with Pre-commit:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-copier-answers
        name: Check Copier answers file
        entry:
          bash -c 'find . -name .copier-answers.yml -type f -exec copier
          validate {} +'
        language: system
        pass_filenames: false
```

**Key Considerations:**

- **Template Versioning**: Always tag template versions (v1.0.0, v1.1.0) for
  stable update targets
- **Conditional Prompts**: Use `when` key to skip questions based on previous
  answers, reducing cognitive load
- **Answer Files**: Copier stores answers in `.copier-answers.yml` - commit this
  to enable updates
- **Migration Strategy**: Create Copier versions of CatalystNeuro Cookiecutter
  templates, test with pilot projects before wide rollout
- **Update Frequency**: Schedule quarterly template updates to sync all projects
  with latest scaffolding patterns
- **Validation**: Use `validator` key in copier.yml for input validation (regex,
  custom Python expressions)

**Gotchas:**

- Copier update merges template changes into project - conflicts possible if
  project heavily modified scaffolding
- `.copier-answers.yml` must be committed for updates to work - add to git, not
  .gitignore
- Jinja2 template syntax uses `{{ }}` for variables - conflicts with Python
  f-strings, use `{% raw %}{{ }}{% endraw %}` for literal braces
- Template suffix `_templates_suffix: .jinja` required to distinguish template
  files from generated files
- `_skip_if_exists` prevents overwriting critical files (conftest.py,
  **init**.py) during updates
- Copier update runs in non-interactive mode in CI - use
  `copier update --defaults` to accept all default answers

---

## Summary and Next Steps

### Research Synthesis

This research phase evaluated 8 critical technical decisions for Phase 0 of the
Core Project Organization implementation:

1. **MCP Tool Decorators**: FastMCP-inspired pattern with Pydantic schema
   generation
2. **Configuration**: pydantic-settings v2.11+ with hierarchical models and
   fail-fast validation
3. **Pre-commit Hooks**: Ruff-centric toolchain with format → lint → type →
   security ordering
4. **Pytest Markers**: Multi-dimensional taxonomy with execution profiles
   (fast/integration/full)
5. **DataLad Integration**: Hybrid Python API + CLI with YODA principles for
   subdataset management
6. **Structured Logging**: structlog with OpenTelemetry correlation and
   contextvars for async
7. **Agent Lifecycle**: FastAPI lifespan with AgentRegistry and event-driven
   communication
8. **Code Scaffolding**: Copier for version-controlled templates with update
   capabilities

### Implementation Priorities

**Phase 0a (Immediate - Foundation):**

1. Migrate config from dataclasses to pydantic-settings BaseSettings
2. Implement `@mcp_tool` decorator and update existing tools
3. Configure structlog with development/production processors

**Phase 0b (Near-term - Developer Experience):** 4. Finalize pre-commit hook
ordering and document execution profiles 5. Create pytest marker execution
profiles and update CI/CD 6. Build Copier templates for MCP tools and agent
modules

**Phase 0c (Mid-term - Advanced Features):** 7. Implement DataLad Python API
wrappers for dataset management 8. Add OpenTelemetry tracing with correlation ID
middleware 9. Enhance agent lifecycle with health monitoring and event bus

### Validation Criteria

Each implementation should be validated against:

- **Technical Merit**: Does it solve the stated problem effectively?
- **Ecosystem Fit**: Does it integrate with existing codebase patterns?
- **Maintenance Burden**: Is long-term maintenance effort acceptable?
- **Developer Experience**: Does it improve productivity and reduce friction?

### References

**Key Resources:**

- FastMCP Documentation: https://gofastmcp.com/servers/tools
- Pydantic Settings Guide:
  https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Ruff Documentation: https://docs.astral.sh/ruff/
- DataLad Handbook: https://handbook.datalad.org/
- structlog Documentation: https://www.structlog.org/
- Copier Documentation: https://copier.readthedocs.io/

**Industry Benchmarks (2025):**

- Pre-commit hook execution: <10s for fast feedback, <60s for full validation
- Test execution profiles: <5min unit, <15min integration, <30min full suite
- Structured logging overhead: <5% performance impact with async processors
- Template update frequency: Quarterly for active projects

---

**Document Status**: Research Complete **Next Phase**: Implementation Planning
(Phase 0a) **Owner**: Core Development Team **Review Date**: 2025-10-03
