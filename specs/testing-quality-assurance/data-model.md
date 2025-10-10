# Testing Framework Data Model

**Feature**: Testing and Quality Assurance
**Date**: 2025-10-10
**Phase**: 1 (Design & Contracts)
**Schema-First**: Constitution Principle III applies - LinkML schemas MUST be defined before implementation

## Overview

This data model defines 8 core test entities that require LinkML schemas per Constitution III (Schema-First Development). These entities model test suites, datasets, reports, mocks, fixtures, metrics, environments, and monitoring data for the comprehensive testing framework.

---

## Entity Relationship Diagram

```
TestEnvironment
├── contains TestDataset (1:N)
├── hosts TestSuite execution (1:N)
└── captures MonitoringData (1:N)

TestSuite
├── contains Test instances (1:N)
├── uses TestFixture (N:M)
├── uses MockService (N:M)
├── produces TestReport (1:1)
└── executes in TestEnvironment (N:1)

TestReport
├── belongs to TestSuite (N:1)
├── contains TestResult (1:N)
├── aggregates QualityMetric (1:N)
└── references MonitoringData (1:1)

TestDataset
├── managed by DataLad
├── used by E2E tests (N:M)
└── versioned with git-annex
```

---

## 1. TestSuite

**Purpose**: Collection of tests organized by component and type (unit/integration/contract/e2e)

### Schema Definition (LinkML)

```yaml
# schemas/test_suite.yaml
classes:
  TestSuite:
    description: Collection of tests with execution metadata
    slots:
      - id
      - name
      - category
      - tests
      - metadata
      - execution_time_requirement
      - dependencies
      - coverage_target
      - status
      - created_at
      - updated_at

slots:
  id:
    range: string
    identifier: true
    required: true
  name:
    range: string
    required: true
  category:
    range: TestCategory
    required: true
  tests:
    range: Test
    multivalued: true
  metadata:
    range: string  # JSON-serialized dict
  execution_time_requirement:
    range: float
    minimum_value: 0
    unit: seconds
  dependencies:
    range: string
    multivalued: true
  coverage_target:
    range: float
    minimum_value: 0.85
    maximum_value: 1.0
  status:
    range: TestSuiteStatus
    required: true

enums:
  TestCategory:
    permissible_values:
      unit:
        description: Unit tests for individual components
      integration:
        description: Integration tests for cross-component workflows
      contract:
        description: Contract tests for API compliance
      e2e:
        description: End-to-end tests with real datasets

  TestSuiteStatus:
    permissible_values:
      pending: {}
      running: {}
      completed: {}
      failed: {}
```

### Fields

- **id**: Unique identifier (UUID)
- **name**: Human-readable test suite name (e.g., "MCP Server Unit Tests")
- **category**: Test category (unit|integration|contract|e2e) - enforces categorization
- **tests**: List of Test instances in this suite
- **metadata**: Additional metadata (tags, owner, description) as JSON dict
- **execution_time_requirement**: Expected execution time in seconds (<300 for unit, <900 for integration per FR-025)
- **dependencies**: List of test suite IDs that must run first (for ordered execution)
- **coverage_target**: Minimum coverage required (≥0.85 standard, ≥0.90 critical per Constitution II)
- **status**: Current execution status (pending → running → completed/failed)
- **created_at**: Timestamp of creation
- **updated_at**: Timestamp of last modification

### Validation Rules

- `category` MUST be one of (unit, integration, contract, e2e)
- `coverage_target` MUST be ≥0.85 (Constitution II quality gate)
- `coverage_target` for critical paths MUST be ≥0.90
- `execution_time_requirement` <300s for unit tests, <900s for integration tests (FR-025)
- `status` transitions: pending → running → (completed OR failed)

### State Transitions

```
pending ──[execute]──> running ──[success]──> completed
                           │
                           └──[failure]──> failed
```

---

## 2. TestDataset

**Purpose**: DataLad-managed neuroscience datasets for E2E testing with version control

### Schema Definition (LinkML)

```yaml
# schemas/test_dataset.yaml
classes:
  TestDataset:
    description: DataLad-managed test dataset with version control
    slots:
      - id
      - name
      - format_type
      - size_bytes
      - complexity_level
      - validity_status
      - datalad_path
      - version
      - expected_outcomes
      - created_at
      - git_annex_key

slots:
  format_type:
    range: DataFormat
    required: true
  size_bytes:
    range: integer
    minimum_value: 1
  complexity_level:
    range: ComplexityLevel
    required: true
  validity_status:
    range: ValidityStatus
    required: true
  datalad_path:
    range: string
    required: true
    pattern: "^tests/datasets/.*"
  version:
    range: string
    description: DataLad commit hash or git-annex key
  expected_outcomes:
    range: string  # JSON-serialized expected validation results
  git_annex_key:
    range: string
    description: git-annex key for files >10MB

enums:
  DataFormat:
    permissible_values:
      openephys: {description: "Open Ephys multi-channel recordings"}
      spikeglx: {description: "SpikeGLX probe configurations"}
      behavioral: {description: "DeepLabCut/SLEAP behavioral tracking"}
      multimodal: {description: "Ephys + behavior combined"}
      corrupted: {description: "Intentionally corrupted for error testing"}
      legacy: {description: "Legacy format migration testing"}

  ComplexityLevel:
    permissible_values:
      minimal: {description: "Minimal valid dataset for smoke testing"}
      standard: {description: "Standard complexity for typical workflows"}
      complex: {description: "Complex multi-session/multi-channel data"}
      stress: {description: "Large-scale stress testing (>1TB)"}

  ValidityStatus:
    permissible_values:
      valid: {description: "Valid dataset for positive testing"}
      corrupted: {description: "Corrupted dataset for error handling testing"}
      incomplete: {description: "Missing required files/metadata"}
      malformed: {description: "Malformed structure/format"}
```

### Fields

- **id**: Unique identifier (UUID)
- **name**: Dataset name (e.g., "OpenEphys-MultiChannel-Standard")
- **format_type**: Neuroscience data format (openephys|spikeglx|behavioral|multimodal|corrupted|legacy)
- **size_bytes**: Dataset size in bytes
- **complexity_level**: Dataset complexity (minimal|standard|complex|stress)
- **validity_status**: Whether dataset is valid/corrupted/incomplete/malformed
- **datalad_path**: Path to DataLad dataset (e.g., `tests/datasets/openephys_standard`)
- **version**: DataLad commit hash for reproducible testing
- **expected_outcomes**: JSON dict of expected validation results (pass_rate, critical_issues, etc.)
- **git_annex_key**: git-annex key if file >10MB (stored on GIN)

### Validation Rules

- `validity_status` MUST be in (valid, corrupted, incomplete, malformed)
- `datalad_path` MUST exist and be a valid DataLad dataset
- `size_bytes` MUST be >0
- Files >10MB MUST have `git_annex_key` (Constitution V: git-annex for large files)
- `version` MUST be a valid git commit hash

### Lifecycle

```
provisioned ──[configure]──> available ──[test_start]──> in_use ──[test_end]──> available
                                  │
                                  └──[archive]──> archived
```

---

## 3. TestReport

**Purpose**: Generated output from test execution with coverage, performance, and quality metrics

### Schema Definition (LinkML)

```yaml
# schemas/test_report.yaml
classes:
  TestReport:
    description: Test execution report with metrics and recommendations
    slots:
      - id
      - test_suite_id
      - execution_timestamp
      - results
      - coverage_metrics
      - performance_benchmarks
      - failure_details
      - historical_trends
      - recommendations
      - format
      - export_path

slots:
  test_suite_id:
    range: string
    required: true
  execution_timestamp:
    range: datetime
    required: true
  results:
    range: TestResult
    multivalued: true
  coverage_metrics:
    range: CoverageMetrics
    required: true
  performance_benchmarks:
    range: string  # JSON-serialized dict
  failure_details:
    range: FailureDetail
    multivalued: true
  historical_trends:
    range: TrendData
    multivalued: true
  recommendations:
    range: string
    multivalued: true
  format:
    range: ReportFormat
  export_path:
    range: string

classes:
  CoverageMetrics:
    slots:
      - line_coverage
      - branch_coverage
      - path_coverage
      - meets_gate

  slots:
    line_coverage:
      range: float
      minimum_value: 0.0
      maximum_value: 1.0
    branch_coverage:
      range: float
      minimum_value: 0.0
      maximum_value: 1.0
    path_coverage:
      range: float
      minimum_value: 0.0
      maximum_value: 1.0
    meets_gate:
      range: boolean
      description: True if coverage meets ≥85% gate (≥90% for critical)

enums:
  ReportFormat:
    permissible_values:
      html: {}
      pdf: {}
      json: {}
```

### Fields

- **id**: Unique identifier (UUID)
- **test_suite_id**: Reference to TestSuite that generated this report
- **execution_timestamp**: When test suite executed
- **results**: List of individual TestResult instances
- **coverage_metrics**: CoverageMetrics object (line/branch/path coverage, gate status)
- **performance_benchmarks**: JSON dict of performance metrics (execution time, memory usage, etc.)
- **failure_details**: List of FailureDetail objects for failed tests
- **historical_trends**: List of TrendData comparing current vs historical metrics
- **recommendations**: List of actionable recommendations (e.g., "Increase coverage in module X")
- **format**: Export format (html|pdf|json) per FR-034
- **export_path**: Path to exported report file

### Validation Rules

- `execution_timestamp` MUST be ≤ now()
- `coverage_metrics.meets_gate` MUST be True if line_coverage ≥0.85 (or ≥0.90 for critical tests)
- `format` MUST be one of (html, pdf, json) per FR-034
- `test_suite_id` MUST reference existing TestSuite

---

## 4. MockService

**Purpose**: Simulated external dependency for deterministic testing

### Schema Definition (LinkML)

```yaml
# schemas/mock_service.yaml
classes:
  MockService:
    description: Mock service for testing external dependencies
    slots:
      - id
      - service_type
      - configuration
      - response_patterns
      - error_injection_rules
      - deterministic
      - preset_scenario
      - status

slots:
  service_type:
    range: ServiceType
    required: true
  configuration:
    range: string  # JSON-serialized config
  response_patterns:
    range: ResponsePattern
    multivalued: true
  error_injection_rules:
    range: ErrorRule
    multivalued: true
  deterministic:
    range: boolean
    required: true
  preset_scenario:
    range: string
    description: Name of preset scenario (e.g., "llm_timeout", "network_latency_500ms")
  status:
    range: MockServiceStatus

enums:
  ServiceType:
    permissible_values:
      llm: {description: "Mock LLM service (OpenAI, Anthropic)"}
      filesystem: {description: "In-memory fake filesystem"}
      network: {description: "Simulated network conditions"}
      time: {description: "Time manipulation for testing timeouts"}
      api: {description: "Mock external REST API"}
      database: {description: "Mock database"}

  MockServiceStatus:
    permissible_values:
      initialized: {}
      configured: {}
      active: {}
      stopped: {}
```

### Fields

- **id**: Unique identifier (UUID)
- **service_type**: Type of service being mocked (llm|filesystem|network|time|api|database)
- **configuration**: JSON dict of service configuration (e.g., response delay, error rate)
- **response_patterns**: List of ResponsePattern objects defining mock responses
- **error_injection_rules**: List of ErrorRule objects for failure simulation
- **deterministic**: Boolean indicating if mock produces deterministic outputs (MUST be True for reproducible tests)
- **preset_scenario**: Name of preset scenario from 100+ scenarios (FR-009)
- **status**: Current state (initialized → configured → active → stopped)

### Validation Rules

- `service_type` MUST be in (llm, filesystem, network, time, api, database)
- `deterministic` MUST be True for unit/integration tests (reproducibility requirement)
- `preset_scenario` MUST reference valid scenario name from scenario library
- `status` transitions: initialized → configured → active → stopped

---

## 5. TestFixture

**Purpose**: Reusable test data or environment setup with cleanup management

### Schema Definition (LinkML)

```yaml
# schemas/test_fixture.yaml
classes:
  TestFixture:
    description: Reusable test fixture with lifecycle management
    slots:
      - id
      - name
      - fixture_type
      - data
      - configuration
      - cleanup_callback
      - metadata
      - lifecycle_state

slots:
  fixture_type:
    range: FixtureType
    required: true
  data:
    range: string  # JSON-serialized fixture data
  configuration:
    range: string  # JSON-serialized config
  cleanup_callback:
    range: string
    description: Python callable path for cleanup (e.g., "module.cleanup_func")
  lifecycle_state:
    range: FixtureLifecycle

enums:
  FixtureType:
    permissible_values:
      minimal: {description: "Minimal valid dataset for smoke testing"}
      edge_case: {description: "Edge case or boundary condition testing"}
      performance: {description: "Large-scale performance testing fixture"}
      multimodal: {description: "Multi-modal data combination fixture"}
      regression: {description: "Regression test baseline fixture"}

  FixtureLifecycle:
    permissible_values:
      created: {}
      initialized: {}
      used: {}
      cleaned_up: {}
```

### Fields

- **id**: Unique identifier (UUID)
- **name**: Fixture name (e.g., "minimal-openephys-session")
- **fixture_type**: Type of fixture (minimal|edge_case|performance|multimodal|regression)
- **data**: JSON-serialized fixture data
- **configuration**: JSON dict of fixture configuration
- **cleanup_callback**: Python callable path for resource cleanup (e.g., "tests.fixtures.cleanup_temp_files")
- **metadata**: Additional metadata (author, description, tags)
- **lifecycle_state**: Current lifecycle state (created → initialized → used → cleaned_up)

### Validation Rules

- `fixture_type` MUST be in (minimal, edge_case, performance, multimodal, regression)
- `cleanup_callback` MUST be callable if provided
- Lifecycle: created → initialized → used → cleaned_up (cleanup MUST run after use)

---

## 6. QualityMetric

**Purpose**: Measurable indicator of system quality with trend tracking

### Schema Definition (LinkML)

```yaml
# schemas/quality_metric.yaml
classes:
  QualityMetric:
    description: Quality metric with baseline and trend tracking
    slots:
      - id
      - metric_name
      - metric_type
      - value
      - baseline
      - threshold
      - trend_data
      - status
      - timestamp

slots:
  metric_name:
    range: string
    required: true
  metric_type:
    range: MetricType
    required: true
  value:
    range: float
    minimum_value: 0
  baseline:
    range: float
    minimum_value: 0
  threshold:
    range: float
    minimum_value: 0
  trend_data:
    range: TrendPoint
    multivalued: true
  status:
    range: MetricStatus

enums:
  MetricType:
    permissible_values:
      coverage: {description: "Test coverage percentage"}
      performance: {description: "Execution time, throughput, latency"}
      error_rate: {description: "Test failure rate, flaky test rate"}
      scientific_accuracy: {description: "NWB validation pass rate, data integrity"}
      compliance: {description: "FAIR principles, DANDI requirements"}

  MetricStatus:
    permissible_values:
      pass: {description: "Metric meets threshold"}
      fail: {description: "Metric below threshold"}
      warning: {description: "Metric approaching threshold"}
```

### Fields

- **id**: Unique identifier (UUID)
- **metric_name**: Name of metric (e.g., "line_coverage", "execution_time", "nwb_pass_rate")
- **metric_type**: Category (coverage|performance|error_rate|scientific_accuracy|compliance)
- **value**: Current metric value
- **baseline**: Established baseline value for comparison
- **threshold**: Threshold for pass/fail/warning status
- **trend_data**: List of TrendPoint objects tracking historical values
- **status**: Derived status (pass|fail|warning) based on value vs threshold
- **timestamp**: When metric was measured

### Validation Rules

- `value`, `baseline`, `threshold` MUST be ≥0
- `status` = pass if value ≥ threshold (for "higher is better" metrics like coverage)
- `status` = fail if value < threshold
- `status` = warning if value is within 5% of threshold
- Coverage metrics: threshold MUST be ≥0.85 (≥0.90 for critical)

---

## 7. TestEnvironment

**Purpose**: Isolated execution context with specific Python version, OS, dependencies, services

### Schema Definition (LinkML)

```yaml
# schemas/test_environment.yaml
classes:
  TestEnvironment:
    description: Isolated test execution environment
    slots:
      - id
      - python_version
      - os
      - dependencies
      - services
      - data
      - configuration
      - resource_constraints
      - lifecycle_state

slots:
  python_version:
    range: PythonVersion
    required: true
  os:
    range: OperatingSystem
    required: true
  dependencies:
    range: string  # JSON-serialized dependency dict
  services:
    range: ServiceConfig
    multivalued: true
  data:
    range: TestDataset
    multivalued: true
  configuration:
    range: string  # JSON-serialized config
  resource_constraints:
    range: ResourceLimits
  lifecycle_state:
    range: EnvironmentLifecycle

enums:
  PythonVersion:
    permissible_values:
      "3.8": {}
      "3.9": {}
      "3.10": {}
      "3.11": {}
      "3.12": {}

  OperatingSystem:
    permissible_values:
      ubuntu: {}
      macos: {}
      windows: {}

  EnvironmentLifecycle:
    permissible_values:
      provisioned: {}
      configured: {}
      ready: {}
      in_use: {}
      torn_down: {}
```

### Fields

- **id**: Unique identifier (UUID)
- **python_version**: Python version (3.8|3.9|3.10|3.11|3.12) per FR-027
- **os**: Operating system (ubuntu|macos|windows) per FR-027
- **dependencies**: JSON dict of Python packages with versions
- **services**: List of ServiceConfig objects (databases, message queues, etc.)
- **data**: List of TestDataset instances available in environment
- **configuration**: JSON dict of environment variables, paths, etc.
- **resource_constraints**: ResourceLimits object (CPU, memory, disk limits)
- **lifecycle_state**: Current state (provisioned → configured → ready → in_use → torn_down)

### Validation Rules

- `python_version` MUST be in [3.8, 3.9, 3.10, 3.11, 3.12] per FR-027
- `os` MUST be in (ubuntu, macos, windows) per FR-027
- `lifecycle_state` transitions: provisioned → configured → ready → in_use → torn_down
- Resources MUST be cleaned up when state = torn_down (FR-029)

---

## 8. MonitoringData

**Purpose**: Observability information (logs, metrics, traces, errors) for validation and debugging

### Schema Definition (LinkML)

```yaml
# schemas/monitoring_data.yaml
classes:
  MonitoringData:
    description: Observability data from test execution
    slots:
      - id
      - timestamp
      - logs
      - metrics
      - traces
      - errors
      - diagnostics
      - health_checks
      - retention_policy

slots:
  timestamp:
    range: datetime
    required: true
  logs:
    range: LogEntry
    multivalued: true
  metrics:
    range: Metric
    multivalued: true
  traces:
    range: Trace
    multivalued: true
  errors:
    range: ErrorReport
    multivalued: true
  diagnostics:
    range: string  # JSON-serialized diagnostic data
  health_checks:
    range: HealthCheck
    multivalued: true
  retention_policy:
    range: RetentionPolicy

classes:
  LogEntry:
    slots:
      - severity
      - message
      - correlation_id
      - timestamp

  slots:
    severity:
      range: LogSeverity
    correlation_id:
      range: string
      description: Correlation ID for request tracing

enums:
  LogSeverity:
    permissible_values:
      DEBUG: {}
      INFO: {}
      WARNING: {}
      ERROR: {}
      CRITICAL: {}

  RetentionPolicy:
    permissible_values:
      permanent:
        description: "Indefinite retention per clarification"
```

### Fields

- **id**: Unique identifier (UUID)
- **timestamp**: When monitoring data was captured
- **logs**: List of LogEntry objects with structured logging (JSON format per FR-043)
- **metrics**: List of Metric objects (response times, throughput, error rates per FR-044)
- **traces**: List of Trace objects for distributed tracing (OpenTelemetry format per FR-047)
- **errors**: List of ErrorReport objects with stack traces and context (FR-045)
- **diagnostics**: JSON dict of diagnostic data (health checks, profiling, thread dumps per FR-046)
- **health_checks**: List of HealthCheck objects (liveness, readiness per FR-046)
- **retention_policy**: Retention policy (permanent per clarification - indefinite retention)

### Validation Rules

- `timestamp` MUST be ≤ now()
- `logs` MUST use structured logging format (JSON) per FR-043
- `logs.severity` MUST be in (DEBUG, INFO, WARNING, ERROR, CRITICAL) per FR-043
- `logs.correlation_id` MUST be present for request tracing per FR-043
- `retention_policy` = permanent (indefinite retention per clarification)
- 100% of error paths MUST have corresponding LogEntry (FR-043)

---

## Schema Generation Workflow (Constitution III)

Per Constitution Principle III (Schema-First Development), the implementation workflow is:

1. **Define LinkML Schemas** (FIRST):
   - Create schemas/*.yaml for all 8 entities
   - Define slots, enums, validation rules
   - Specify relationships and cardinalities

2. **Generate Pydantic Validators**:
   ```bash
   pixi run gen-pydantic --input schemas/test_suite.yaml --output agentic_neurodata_conversion/testing/models/test_suite.py
   ```

3. **Implement Validation**:
   - Use generated Pydantic models for runtime validation
   - Validate all entity instances before storage

4. **Create Tests** (TDD - RED phase):
   - Write schema validation tests (must fail initially)
   - Write entity creation tests

5. **Implement Features** (GREEN phase):
   - Implement TestSuite, TestDataset, etc. using validated Pydantic models
   - Tests pass

---

## Cross-Entity Relationships

### TestSuite → TestReport (1:1)
- Each TestSuite execution produces exactly one TestReport
- `TestReport.test_suite_id` references `TestSuite.id`

### TestEnvironment → TestDataset (1:N)
- TestEnvironment contains multiple TestDataset instances
- `TestDataset` references `TestEnvironment.id`

### TestSuite → TestFixture (N:M)
- TestSuite may use multiple TestFixture instances
- TestFixture may be shared across multiple TestSuite instances
- Junction table: `test_suite_fixtures`

### TestSuite → MockService (N:M)
- TestSuite may use multiple MockService instances
- MockService may be shared across multiple TestSuite instances
- Junction table: `test_suite_mocks`

### TestReport → QualityMetric (1:N)
- TestReport aggregates multiple QualityMetric instances
- `QualityMetric` references `TestReport.id`

### TestReport → MonitoringData (1:1)
- Each TestReport has associated MonitoringData
- `MonitoringData` references `TestReport.id`

---

## Summary

✅ **8 entities defined** with LinkML schemas (Constitution III compliance)
✅ **Schema-First workflow** documented (define schemas → generate Pydantic → validate → test → implement)
✅ **Validation rules** specified for each entity
✅ **State transitions** documented for lifecycle management
✅ **Relationships** defined between entities

**Next Step**: Generate OpenAPI contracts for Test Execution, Test Reporting, and Mock Service APIs (Phase 1 continued)
