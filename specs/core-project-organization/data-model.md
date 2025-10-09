# Data Model: Core Project Organization

**Feature**: 001-core-project-organization **Date**: 2025-10-03 **Status**:
Design Phase

This document defines the data models for the core project organization
infrastructure.

---

## Entity Definitions

### 1. ModuleStructure

Represents a logical module in the project hierarchy.

**Fields**:

- `name` (str): Module identifier (e.g., "mcp_server", "agents")
- `path` (Path): Absolute filesystem path to module root
- `type` (enum): Module category -
  `mcp_server | agent | client | util | model | config`
- `dependencies` (List[str]): List of module names this module depends on
- `public_api` (List[str]): Exported symbols in `__init__.py`

**Validation Rules**:

- Path MUST exist on filesystem
- Path MUST contain `__init__.py`
- NO circular dependencies in dependency graph
- Type MUST be one of defined enum values
- Public API symbols MUST be importable

**Relationships**:

- Contains: ConfigurationProfile (config modules)
- ValidatedBy: TestSuite
- Documents: DocumentationArtifact

**State Transitions**: N/A (static structure)

**Example**:

```python
ModuleStructure(
    name="mcp_server",
    path=Path("src/agentic_nwb_converter/mcp_server"),
    type="mcp_server",
    dependencies=["utils", "models"],
    public_api=["MCPServer", "start_server", "@mcp_tool"]
)
```

---

### 2. ConfigurationProfile

Environment-specific configuration settings.

**Fields**:

- `name` (enum): Profile identifier -
  `development | testing | staging | production`
- `settings` (Dict[str, Any]): Configuration key-value pairs
- `env_vars` (Dict[str, str]): Environment variable mappings
- `validation_rules` (List[ValidationRule]): Pydantic validators

**Validation Rules**:

- Required settings MUST be present: `log_level`, `debug_mode`, `data_root`
- Environment variables MUST follow `NWB_CONVERTER_{SECTION}_{KEY}` pattern
- Values MUST match declared types
- Fail-fast on missing required settings with clear error message

**Relationships**:

- BelongsTo: ModuleStructure (config module)
- Inherits: ConfigurationProfile (profile hierarchy)

**State Transitions**: N/A (loaded at startup)

**Example**:

```python
ConfigurationProfile(
    name="development",
    settings={
        "log_level": "DEBUG",
        "debug_mode": True,
        "data_root": "/data/dev"
    },
    env_vars={
        "NWB_CONVERTER_LOG_LEVEL": "DEBUG",
        "NWB_CONVERTER_DEBUG_MODE": "true"
    },
    validation_rules=[
        RequiredField("log_level"),
        PathExists("data_root")
    ]
)
```

---

### 3. MCPTool

MCP (Model Context Protocol) tool definition for exposed functionality.

**Fields**:

- `name` (str): Tool identifier (kebab-case)
- `description` (str): Human-readable tool description
- `parameters_schema` (Dict): JSON Schema for parameters
- `handler_function` (Callable): Async function implementing tool
- `middleware` (List[Callable]): Request/response middleware chain

**Validation Rules**:

- Name MUST be kebab-case
- Parameters schema MUST be valid JSON Schema Draft 7
- Handler function MUST be async (coroutine)
- Handler MUST accept `**kwargs` matching schema
- Middleware MUST accept (request, next) signature

**Relationships**:

- RegisteredWith: MCP Server
- ImplementedIn: ModuleStructure
- TestedBy: TestSuite

**State Transitions**:
`UNREGISTERED → REGISTERED → ACTIVE → DISABLED → UNREGISTERED`

**Example**:

```python
MCPTool(
    name="analyze-dataset",
    description="Analyze neuroscience dataset structure and metadata",
    parameters_schema={
        "type": "object",
        "properties": {
            "dataset_path": {"type": "string"},
            "depth": {"type": "integer", "minimum": 1}
        },
        "required": ["dataset_path"]
    },
    handler_function=analyze_dataset_handler,
    middleware=[logging_middleware, auth_middleware]
)
```

---

### 4. AgentModule

Internal agent component with specialized domain responsibility.

**Fields**:

- `name` (str): Agent identifier
- `agent_type` (enum):
  `conversation | conversion | evaluation | knowledge_graph`
- `interface` (Type): Abstract base class defining agent contract
- `lifecycle_state` (enum): Current state in lifecycle

**Validation Rules**:

- MUST implement base agent interface (AgentBase)
- Agent type MUST be unique (one instance per type)
- Communication MUST route through MCP server (no direct agent-to-agent)
- MUST provide graceful shutdown implementation

**Relationships**:

- RegisteredWith: AgentRegistry
- CommunicatesVia: MCP Server
- Uses: IntegrationPoint

**State Transitions**:

```
UNREGISTERED → REGISTERED → INITIALIZED → ACTIVE → SHUTTING_DOWN → STOPPED
```

**Example**:

```python
AgentModule(
    name="conversation_agent",
    agent_type="conversation",
    interface=AgentBase,
    lifecycle_state="ACTIVE"
)
```

---

### 5. TestSuite

Categorized collection of tests with execution profiles.

**Fields**:

- `name` (str): Test suite identifier
- `test_type` (enum): `unit | integration | e2e | performance | security`
- `markers` (List[str]): Pytest markers for selection
- `fixtures` (List[str]): Required test fixtures
- `coverage_threshold` (float): Minimum coverage % (0-100)

**Validation Rules**:

- Coverage threshold MUST be >= 80% for unit tests
- Coverage threshold MUST be >= 75% for integration tests
- Test execution time MUST be <5min for unit, <15min for integration
- Markers MUST be registered in pytest.ini

**Relationships**:

- Validates: ModuleStructure
- Uses: Test fixtures, mocks
- Generates: QualityMetric

**State Transitions**: N/A (executed on-demand)

**Example**:

```python
TestSuite(
    name="mcp_server_unit",
    test_type="unit",
    markers=["unit", "mcp_server"],
    fixtures=["mock_agent", "test_config"],
    coverage_threshold=80.0
)
```

---

### 6. DevelopmentStandard

Enforced code quality rule with tooling configuration.

**Fields**:

- `name` (str): Standard identifier
- `tool` (str): Tool name (ruff, mypy, bandit)
- `configuration` (Dict): Tool-specific config
- `severity` (enum): `error | warning`
- `auto_fix_available` (bool): Whether tool can auto-fix violations

**Validation Rules**:

- Tool MUST be installed and accessible in PATH
- Configuration MUST be valid for tool
- Severity MUST block merge on "error"

**Relationships**:

- EnforcedBy: QualityGate (CI/CD)
- Applies: ModuleStructure

**State Transitions**: N/A (static rules)

**Example**:

```python
DevelopmentStandard(
    name="line_length",
    tool="ruff",
    configuration={"line-length": 100},
    severity="error",
    auto_fix_available=True
)
```

---

### 7. DocumentationArtifact

Generated or authored documentation content.

**Fields**:

- `name` (str): Document identifier
- `type` (enum): `api | architecture | adr | tutorial | example`
- `format` (enum): `markdown | html | pdf`
- `auto_generated` (bool): Whether generated from code
- `source_path` (Path): Location of source content

**Validation Rules**:

- Content MUST exist at source_path
- Format MUST be parseable
- Auto-generated docs MUST regenerate on source changes
- Links MUST be valid (no broken links)

**Relationships**:

- Documents: ModuleStructure
- GeneratedFrom: Code (if auto_generated)

**State Transitions**: N/A (versioned content)

**Example**:

```python
DocumentationArtifact(
    name="mcp_server_api",
    type="api",
    format="markdown",
    auto_generated=True,
    source_path=Path("src/agentic_nwb_converter/mcp_server")
)
```

---

### 8. IntegrationPoint

Defined boundary for external system interaction.

**Fields**:

- `name` (str): Integration identifier
- `external_system` (str): External system name (DataLad, NWB Inspector)
- `adapter_type` (enum): `api | cli | library`
- `protocol` (str): Communication protocol
- `authentication` (Dict): Auth configuration

**Validation Rules**:

- Adapter MUST implement required interface
- External system MUST be accessible
- Authentication MUST be configured for protected systems
- Failure modes MUST be handled gracefully

**Relationships**:

- UsedBy: AgentModule
- Implements: Adapter interface

**State Transitions**: `DISCONNECTED → CONNECTING → CONNECTED → DISCONNECTED`

**Example**:

```python
IntegrationPoint(
    name="datalad_integration",
    external_system="DataLad",
    adapter_type="library",
    protocol="python_api",
    authentication={}
)
```

---

### 9. QualityMetric

Measurable indicator of code/test quality.

**Fields**:

- `name` (str): Metric identifier
- `metric_type` (enum):
  `coverage | complexity | execution_time | vulnerability_count | maintainability`
- `threshold` (float): Required minimum/maximum value
- `current_value` (float): Measured value
- `passing` (bool): Whether current_value meets threshold

**Validation Rules**:

- Current value MUST meet threshold to pass quality gate
- Metrics MUST be measurable and reproducible
- Trend MUST be tracked over time

**Relationships**:

- MeasuredFor: ModuleStructure, TestSuite
- EnforcedBy: QualityGate

**State Transitions**: N/A (measured values)

**Example**:

```python
QualityMetric(
    name="line_coverage",
    metric_type="coverage",
    threshold=80.0,
    current_value=85.3,
    passing=True
)
```

---

## Entity Relationships Diagram

```
ModuleStructure
    |-- contains --> ConfigurationProfile
    |-- validated_by --> TestSuite
    |-- documented_by --> DocumentationArtifact
    |-- measured_by --> QualityMetric
    |-- applies --> DevelopmentStandard

AgentModule
    |-- registered_with --> AgentRegistry
    |-- communicates_via --> MCP Server
    |-- uses --> IntegrationPoint

MCPTool
    |-- registered_with --> MCP Server
    |-- implemented_in --> ModuleStructure
    |-- tested_by --> TestSuite

TestSuite
    |-- validates --> ModuleStructure
    |-- generates --> QualityMetric

IntegrationPoint
    |-- used_by --> AgentModule
```

---

## Implementation Considerations

### Type Hints

All entities should be implemented as Pydantic models for:

- Runtime validation
- JSON Schema generation
- Serialization/deserialization
- IDE autocomplete support

### Validation Strategy

- Fail-fast validation at construction time
- Clear error messages with remediation guidance
- Validation composition for complex rules

### Persistence

- ModuleStructure: Derived from filesystem inspection
- ConfigurationProfile: Loaded from config files + env vars
- MCPTool: Registered at import time via decorator
- AgentModule: Registered at startup in lifespan
- TestSuite: Defined in pytest.ini and test files
- Others: Runtime state, not persisted
