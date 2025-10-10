# Testing and Quality Assurance Framework - Data Model

## Overview

This document defines the data entities and their relationships for the testing
and quality assurance framework. These entities support test execution,
validation, reporting, and observability across the entire system.

## Entity Categories

1. **Test Entities**: Core testing infrastructure (Test Case, Test Suite, Test
   Environment, Test Dataset, Mock Service)
2. **Validation Entities**: Quality and compliance assessment (Validation Rule,
   Quality Score, Compliance Certificate, NWB File Validation, RDF Graph
   Validation)
3. **Reporting Entities**: Test results and analysis (Test Report, Coverage
   Report, Quality Report, Evaluation Report, Performance Report)

---

## Test Entities

### 1. Test Case

**Description**: Represents an individual test with all necessary metadata for
execution, tracking, and analysis.

**Fields**:

```python
@dataclass
class TestCase:
    # Identification
    id: str                          # Unique identifier (UUID)
    name: str                        # Human-readable test name
    description: str                 # What the test validates

    # Classification
    test_type: TestType              # unit, integration, e2e, contract, performance
    target_component: str            # Component under test (e.g., "mcp_server.endpoints.convert")
    tags: List[str]                  # Tags for filtering (e.g., ["slow", "requires_gpu"])
    markers: List[str]               # pytest markers (e.g., ["@pytest.mark.asyncio"])

    # Test data
    test_data: Dict[str, Any]        # Input data for the test
    expected_outcome: ExpectedOutcome  # Expected result specification
    fixtures_required: List[str]     # pytest fixtures needed

    # Execution metadata
    execution_status: ExecutionStatus  # pending, running, passed, failed, skipped, error
    execution_time: Optional[float]  # Execution duration in seconds
    retry_count: int = 0             # Number of retries attempted
    last_run: Optional[datetime]     # Timestamp of last execution
    failure_message: Optional[str]   # Error message if failed

    # Relationship
    suite_id: str                    # Parent test suite
    dependencies: List[str]          # Test IDs that must run first

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str
```

**Enums**:

```python
class TestType(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    CONTRACT = "contract"
    PERFORMANCE = "performance"
    CHAOS = "chaos"

class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
```

**Validation Rules**:

- `id` must be unique across all test cases
- `name` must be non-empty and follow naming convention `test_*`
- `test_type` must be valid TestType
- `execution_time` must be non-negative if provided
- `dependencies` must reference existing test case IDs

**State Transitions**:

```
pending → running → {passed, failed, error}
running → skipped (if dependency failed)
{failed, error} → running (on retry)
```

**Relationships**:

- Belongs to one `TestSuite`
- May depend on multiple `TestCase` instances
- Uses multiple `TestDataset` instances
- Generates one or more `TestReport` entries

---

### 2. Test Suite

**Description**: Collection of related test cases organized by component,
feature, or test type.

**Fields**:

```python
@dataclass
class TestSuite:
    # Identification
    id: str                          # Unique identifier
    name: str                        # Suite name (e.g., "MCP Server API Tests")
    description: str                 # Suite purpose

    # Organization
    category: SuiteCategory          # mcp_server, agents, client, e2e, validation
    test_case_ids: List[str]         # Test cases in this suite
    subsuite_ids: List[str]          # Nested test suites

    # Configuration
    suite_config: SuiteConfig        # Execution configuration
    execution_order: ExecutionOrder  # sequential, parallel, dependency_based
    timeout: Optional[int]           # Suite timeout in seconds

    # Execution metadata
    total_tests: int                 # Total number of tests
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0

    # Aggregate results
    total_execution_time: float = 0.0
    coverage_percentage: Optional[float]  # Code coverage for this suite
    last_run: Optional[datetime]

    # Metadata
    created_at: datetime
    updated_at: datetime
```

**Enums**:

```python
class SuiteCategory(Enum):
    MCP_SERVER = "mcp_server"
    AGENTS = "agents"
    CLIENT = "client"
    E2E = "e2e"
    VALIDATION = "validation"
    UTILITIES = "utilities"
    MONITORING = "monitoring"

class ExecutionOrder(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DEPENDENCY_BASED = "dependency_based"
```

**Nested Types**:

```python
@dataclass
class SuiteConfig:
    parallel_workers: int = 1        # Number of parallel workers
    retry_failed: bool = False       # Retry failed tests
    fail_fast: bool = False          # Stop on first failure
    randomize_order: bool = False    # Randomize test execution order
    environment_vars: Dict[str, str] # Environment variables for suite
```

**Validation Rules**:

- `test_case_ids` must reference existing TestCase instances
- `total_tests` must equal length of `test_case_ids` + sum of tests in
  `subsuite_ids`
- `passed_tests + failed_tests + skipped_tests + error_tests` must equal
  `total_tests` after execution
- `execution_order` must be compatible with test dependencies

**Relationships**:

- Contains multiple `TestCase` instances
- May contain multiple `TestSuite` instances (sub-suites)
- Uses one `TestEnvironment`
- Generates one `TestReport` per execution

---

### 3. Test Environment

**Description**: Isolated execution context with all necessary dependencies,
configurations, and resources.

**Fields**:

```python
@dataclass
class TestEnvironment:
    # Identification
    id: str
    name: str                        # e.g., "Python 3.12 Ubuntu Latest"
    description: str

    # Environment configuration
    python_version: str              # e.g., "3.12.1"
    os_platform: Platform            # ubuntu, macos, windows
    os_version: str                  # e.g., "22.04", "13.2", "11"

    # Dependencies
    dependency_versions: Dict[str, str]  # Package name → version
    environment_vars: Dict[str, str]     # Environment variables
    system_resources: SystemResources    # CPU, memory, disk allocations

    # Mock services
    mock_services: List[str]         # Mock service IDs active in this environment
    test_data_paths: List[Path]      # Mounted test datasets

    # State management
    is_provisioned: bool = False
    is_active: bool = False
    cleanup_on_exit: bool = True

    # Resource tracking
    resource_usage: ResourceUsage    # Current resource consumption
    max_concurrent_tests: int = 10

    # Metadata
    created_at: datetime
    destroyed_at: Optional[datetime]
```

**Enums**:

```python
class Platform(Enum):
    UBUNTU = "ubuntu"
    MACOS = "macos"
    WINDOWS = "windows"
    DOCKER = "docker"
```

**Nested Types**:

```python
@dataclass
class SystemResources:
    cpu_cores: int                   # Allocated CPU cores
    memory_mb: int                   # Allocated memory in MB
    disk_gb: int                     # Allocated disk space in GB
    gpu_available: bool = False

@dataclass
class ResourceUsage:
    cpu_percent: float               # CPU usage percentage
    memory_mb: int                   # Memory used in MB
    disk_mb: int                     # Disk used in MB
    network_kb: int                  # Network transferred in KB
    timestamp: datetime
```

**Validation Rules**:

- `python_version` must match pattern `\d+\.\d+\.\d+`
- `dependency_versions` must specify exact versions (no ranges)
- `system_resources.memory_mb` must be >= 512MB for functional tests
- `resource_usage.memory_mb` must be <= `system_resources.memory_mb`

**State Transitions**:

```
created → provisioning → provisioned → active → cleanup → destroyed
                    ↓           ↓
                  error      inactive
```

**Lifecycle**:

```python
def provision(self):
    """Set up environment (install dependencies, start services)"""
    pass

def activate(self):
    """Make environment active for test execution"""
    pass

def cleanup(self):
    """Clean up resources, stop services, remove temp files"""
    pass

def destroy(self):
    """Completely tear down environment"""
    pass
```

**Relationships**:

- Hosts multiple `TestSuite` executions
- Contains multiple `MockService` instances
- Mounts multiple `TestDataset` instances
- Tracked by `TestReport` for environment information

---

### 4. Test Dataset

**Description**: DataLad-managed test data with version control, format
metadata, and quality attributes.

**Fields**:

```python
@dataclass
class TestDataset:
    # Identification
    id: str
    name: str                        # e.g., "open-ephys-multichannel-001"
    description: str

    # Dataset characteristics
    data_format: DataFormat          # open_ephys, spikeglx, neuralynx, etc.
    dataset_type: DatasetType        # minimal, typical, large, corrupted, multimodal
    size_bytes: int                  # Total dataset size
    file_count: int                  # Number of files in dataset

    # Quality attributes
    quality_level: QualityLevel      # valid, corrupted, incomplete, legacy
    corruption_type: Optional[str]   # If corrupted: "missing_metadata", "binary_corruption", etc.
    metadata_completeness: float     # 0.0 to 1.0

    # DataLad integration
    datalad_url: str                 # DataLad dataset URL
    datalad_version: str             # Specific version/commit hash
    local_path: Optional[Path]       # Local path if fetched
    is_fetched: bool = False

    # Version control
    version: str                     # Dataset version (semantic)
    checksum: str                    # SHA-256 checksum
    last_updated: datetime

    # Usage scenarios
    test_scenarios: List[str]        # Test scenarios this dataset supports
    expected_outcomes: Dict[str, Any]  # Expected conversion outcomes

    # Metadata
    created_at: datetime
```

**Enums**:

```python
class DataFormat(Enum):
    OPEN_EPHYS = "open_ephys"
    SPIKEGLX = "spikeglx"
    NEURALYNX = "neuralynx"
    CALCIUM_IMAGING = "calcium_imaging"
    BEHAVIORAL = "behavioral"
    MULTIMODAL = "multimodal"
    # ... 15+ total formats

class DatasetType(Enum):
    MINIMAL = "minimal"              # <10MB, quick tests
    TYPICAL = "typical"              # 100MB-1GB, integration tests
    LARGE = "large"                  # >1GB, performance tests
    CORRUPTED = "corrupted"          # Error handling tests
    MULTIMODAL = "multimodal"        # Multiple data types

class QualityLevel(Enum):
    VALID = "valid"
    CORRUPTED = "corrupted"
    INCOMPLETE = "incomplete"
    LEGACY = "legacy"
```

**Validation Rules**:

- `size_bytes` must match actual dataset size
- `checksum` must be valid SHA-256 hash
- `metadata_completeness` must be between 0.0 and 1.0
- `datalad_url` must be valid URL
- `version` must follow semantic versioning (X.Y.Z)

**Operations**:

```python
def fetch(self) -> Path:
    """Fetch dataset using DataLad"""
    pass

def validate_checksum(self) -> bool:
    """Verify dataset integrity"""
    pass

def get_metadata(self) -> Dict[str, Any]:
    """Extract dataset metadata"""
    pass
```

**Relationships**:

- Used by multiple `TestCase` instances
- Mounted in `TestEnvironment` instances
- Referenced in `TestReport` for test inputs
- Validated by `NWBFileValidation` after conversion

---

### 5. Mock Service

**Description**: Simulated external dependency providing deterministic
responses, configurable behaviors, and interaction recording.

**Fields**:

```python
@dataclass
class MockService:
    # Identification
    id: str
    name: str                        # e.g., "MockLLMService", "MockHTTPServer"
    service_type: ServiceType        # llm, http, filesystem, database, network
    description: str

    # Configuration
    mode: MockMode                   # deterministic, random_variation, replay
    response_library: Dict[str, Any]  # Request → Response mappings
    latency_ms: int = 0              # Simulated latency
    error_rate: float = 0.0          # Probability of errors (0.0 to 1.0)

    # Behavior configuration
    behaviors: List[MockBehavior]    # Ordered list of behaviors
    state: Dict[str, Any]            # Internal state for stateful mocks

    # Interaction tracking
    call_log: List[MockCall]         # All interactions with the mock
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0

    # Verification
    expected_calls: List[ExpectedCall]  # For verification
    strict_mode: bool = False        # Fail if unexpected calls received

    # Lifecycle
    is_active: bool = False
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
```

**Enums**:

```python
class ServiceType(Enum):
    LLM = "llm"
    HTTP = "http"
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    NETWORK = "network"
    EXTERNAL_API = "external_api"

class MockMode(Enum):
    DETERMINISTIC = "deterministic"  # Same input → same output
    VARIATION = "variation"          # Generate variations
    REPLAY = "replay"                # Replay recorded interactions
    PASSTHROUGH = "passthrough"      # Forward to real service
```

**Nested Types**:

```python
@dataclass
class MockBehavior:
    trigger: str                     # Condition that activates behavior
    action: str                      # Action to perform (e.g., "return_value", "raise_error")
    params: Dict[str, Any]           # Behavior parameters
    priority: int = 0                # Higher priority behaviors evaluated first

@dataclass
class MockCall:
    timestamp: datetime
    method: str                      # Method/endpoint called
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]
    result: Any
    duration_ms: float
    error: Optional[Exception]

@dataclass
class ExpectedCall:
    method: str
    args_matcher: Callable           # Function to match arguments
    min_calls: int = 1
    max_calls: Optional[int] = None
    actual_calls: int = 0
```

**Operations**:

```python
def start(self):
    """Start the mock service"""
    pass

def stop(self):
    """Stop the mock service"""
    pass

def reset(self):
    """Clear call log and reset state"""
    pass

def add_response(self, request_pattern: str, response: Any):
    """Add a response to the library"""
    pass

def inject_error(self, error_type: Exception):
    """Inject an error for next call"""
    pass

def verify_expectations(self) -> List[str]:
    """Verify all expected calls were made"""
    pass

def get_calls_matching(self, pattern: str) -> List[MockCall]:
    """Get calls matching a pattern"""
    pass
```

**Validation Rules**:

- `error_rate` must be between 0.0 and 1.0
- `latency_ms` must be non-negative
- If `strict_mode`, all calls must match `expected_calls`
- `successful_calls + failed_calls` must equal `total_calls`

**Example Mock Scenarios** (100+ total):

- LLM: timeout (10 scenarios), invalid response format (10), token limit
  exceeded (5)
- HTTP: 500 errors (5), 503 unavailable (5), timeout (5), rate limiting (5),
  auth failures (5)
- Filesystem: permission denied (5), disk full (5), file not found (5),
  corruption (5)
- Network: connection refused (5), DNS failure (5), packet loss (5), high
  latency (5)
- Database: connection failure (5), query timeout (5), constraint violation (5)

**Relationships**:

- Used by `TestCase` instances
- Hosted in `TestEnvironment`
- Call logs referenced in `TestReport` for debugging
- Behaviors configured per test scenario

---

## Validation Entities

### 6. Validation Rule

**Description**: Defines quality criteria with validation logic and remediation
guidance.

**Fields**:

```python
@dataclass
class ValidationRule:
    # Identification
    id: str
    name: str                        # e.g., "NWB Required Fields Check"
    description: str
    category: ValidationCategory     # schema, data_integrity, metadata, compliance

    # Rule specification
    target_artifact: ArtifactType    # nwb_file, rdf_graph, test_report, etc.
    severity: Severity               # critical, error, warning, info
    validation_logic: Callable       # Function that performs validation
    parameters: Dict[str, Any]       # Rule parameters

    # Remediation
    remediation_guidance: str        # How to fix violations
    automated_fix: Optional[Callable]  # Auto-fix function if available
    documentation_url: Optional[str] # Link to detailed docs

    # Execution
    is_enabled: bool = True
    execution_order: int = 0         # Lower numbers execute first
    timeout_seconds: int = 30

    # Metadata
    created_at: datetime
    updated_at: datetime
    version: str
```

**Enums**:

```python
class ValidationCategory(Enum):
    SCHEMA = "schema"
    DATA_INTEGRITY = "data_integrity"
    METADATA = "metadata"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    SECURITY = "security"

class ArtifactType(Enum):
    NWB_FILE = "nwb_file"
    RDF_GRAPH = "rdf_graph"
    TEST_REPORT = "test_report"
    SOURCE_CODE = "source_code"
    CONFIGURATION = "configuration"

class Severity(Enum):
    CRITICAL = "critical"            # Must be fixed before release
    ERROR = "error"                  # Should be fixed
    WARNING = "warning"              # Should be addressed
    INFO = "info"                    # Informational
```

**Operations**:

```python
def validate(self, artifact: Any) -> ValidationResult:
    """Execute validation on artifact"""
    pass

def apply_fix(self, artifact: Any) -> Any:
    """Apply automated fix if available"""
    pass
```

**Nested Types**:

```python
@dataclass
class ValidationResult:
    rule_id: str
    passed: bool
    violations: List[Violation]
    execution_time: float
    timestamp: datetime

@dataclass
class Violation:
    severity: Severity
    message: str
    location: str                    # Where in artifact (e.g., "/subject/species")
    actual_value: Any
    expected_value: Any
    can_auto_fix: bool
```

**Example Rules**:

- NWB schema compliance (FR-031)
- Required fields presence (FR-032)
- Temporal alignment validation (FR-015)
- Ontology linkage validation (FR-033)
- Code coverage thresholds (FR-001, FR-007, FR-019)
- Performance baseline compliance (FR-012, FR-018, FR-024)

**Relationships**:

- Applied to `NWBFileValidation`, `RDFGraphValidation`
- Results stored in `QualityScore`
- Violations reported in `EvaluationReport`

---

### 7. Quality Score

**Description**: Aggregated quality assessment with component scores, weighted
metrics, and pass/fail thresholds.

**Fields**:

```python
@dataclass
class QualityScore:
    # Identification
    id: str
    artifact_id: str                 # ID of artifact being scored
    artifact_type: ArtifactType

    # Overall score
    overall_score: float             # 0.0 to 1.0 (or 0 to 100)
    passed: bool                     # True if >= threshold

    # Component scores
    component_scores: Dict[str, float]  # Component → score
    weighted_metrics: Dict[str, WeightedMetric]  # Metric → weighted value

    # Thresholds
    pass_threshold: float = 0.95     # Minimum score to pass
    component_thresholds: Dict[str, float]  # Per-component thresholds

    # Trend analysis
    previous_score: Optional[float]
    score_delta: Optional[float]     # Change from previous
    trend: Trend                     # improving, declining, stable

    # Benchmark comparison
    benchmark_score: Optional[float]  # Community/internal benchmark
    percentile: Optional[float]      # Percentile ranking

    # Metadata
    scored_at: datetime
    scoring_method: str              # e.g., "importance_weighted", "average"
    version: str                     # Scoring algorithm version
```

**Enums**:

```python
class Trend(Enum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    NO_HISTORY = "no_history"
```

**Nested Types**:

```python
@dataclass
class WeightedMetric:
    name: str
    raw_value: float
    weight: float                    # Importance weight (0.0 to 1.0)
    weighted_value: float            # raw_value * weight
    unit: Optional[str]              # e.g., "%", "ms", "MB"
```

**Scoring Methods**:

```python
def calculate_overall_score(self) -> float:
    """Calculate weighted average of component scores"""
    pass

def calculate_importance_weighted_score(self, violations: List[Violation]) -> float:
    """NWB Inspector-style importance weighting (FR-031)"""
    pass

def compare_to_benchmark(self, benchmark: float) -> float:
    """Calculate difference from benchmark"""
    pass
```

**Example Component Scores**:

- Schema compliance: 0.0-1.0
- Metadata completeness: 0.0-1.0 (target >0.95)
- Data integrity: 0.0-1.0
- Performance: 0.0-1.0 (based on benchmarks)
- Security: 0.0-1.0 (OWASP compliance)

**Validation Rules**:

- `overall_score` must be between 0.0 and 1.0
- `component_scores` values must be between 0.0 and 1.0
- `pass_threshold` must be between 0.0 and 1.0
- `weighted_metrics` weights must sum to 1.0

**Relationships**:

- Calculated from `ValidationRule` results
- Stored in `EvaluationReport`
- Tracked over time for trend analysis
- Compared against `benchmark_score`

---

### 8. Compliance Certificate

**Description**: Attestation of standards compliance with supporting evidence
and certification authority.

**Fields**:

```python
@dataclass
class ComplianceCertificate:
    # Identification
    id: str
    certificate_number: str          # Unique certificate number
    artifact_id: str                 # Artifact being certified
    artifact_type: ArtifactType

    # Compliance standard
    standard_name: StandardName      # FAIR, BIDS, DANDI, OWASP, etc.
    standard_version: str            # Standard version
    compliance_level: ComplianceLevel  # full, partial, non_compliant

    # Validation
    validation_date: datetime
    expiration_date: Optional[datetime]
    is_valid: bool                   # Not expired and not revoked

    # Supporting evidence
    validation_results: List[ValidationResult]
    evidence_artifacts: List[str]    # Paths to evidence files
    validation_report_id: str        # Detailed validation report

    # Certification authority
    certified_by: str                # Organization/system that certified
    certifier_signature: Optional[str]  # Cryptographic signature
    certification_method: str        # "automated", "manual", "hybrid"

    # Conditions
    conditions: List[str]            # Any conditions/caveats
    deviations: List[Deviation]      # Documented deviations from standard

    # Status
    status: CertificateStatus        # issued, revoked, expired
    revocation_reason: Optional[str]

    # Metadata
    issued_at: datetime
    updated_at: datetime
```

**Enums**:

```python
class StandardName(Enum):
    FAIR = "FAIR"                    # Findability, Accessibility, Interoperability, Reusability
    BIDS = "BIDS"                    # Brain Imaging Data Structure
    DANDI = "DANDI"                  # DANDI Archive requirements
    NWB = "NWB"                      # Neurodata Without Borders
    OWASP = "OWASP"                  # Security standards
    HIPAA = "HIPAA"                  # Healthcare privacy
    GDPR = "GDPR"                    # Data privacy

class ComplianceLevel(Enum):
    FULL = "full"                    # 100% compliant
    PARTIAL = "partial"              # Partially compliant with documented deviations
    NON_COMPLIANT = "non_compliant"  # Does not meet requirements

class CertificateStatus(Enum):
    ISSUED = "issued"
    EXPIRED = "expired"
    REVOKED = "revoked"
```

**Nested Types**:

```python
@dataclass
class Deviation:
    requirement_id: str              # Which requirement deviated from
    description: str                 # Description of deviation
    justification: str               # Why deviation is acceptable
    severity: Severity               # Impact of deviation
```

**Operations**:

```python
def is_currently_valid(self) -> bool:
    """Check if certificate is currently valid"""
    pass

def renew(self) -> 'ComplianceCertificate':
    """Renew certificate with new validation"""
    pass

def revoke(self, reason: str):
    """Revoke certificate"""
    pass
```

**Validation Rules**:

- `expiration_date` must be after `validation_date` if set
- If `status == expired`, `expiration_date` must be in the past
- `compliance_level == full` requires zero critical deviations
- `is_valid == True` only if status is `issued` and not expired

**Standards Compliance** (FR-036):

- FAIR principles (findability, accessibility, interoperability, reusability)
- BIDS compatibility where applicable
- DANDI upload requirements
- Journal data requirements
- Funder data mandates
- Ethical compliance markers
- Privacy regulation compliance (GDPR, HIPAA)
- License compatibility

**Relationships**:

- References validated artifact (NWB file, RDF graph, etc.)
- Contains multiple `ValidationResult` instances
- Referenced in `EvaluationReport`
- May be required for data submission

---

### 9. NWB File Validation

**Description**: Specialized validation for NWB files with schema compliance,
Inspector results, and scientific accuracy verification.

**Fields**:

```python
@dataclass
class NWBFileValidation:
    # Identification
    id: str
    nwb_file_path: Path
    nwb_file_id: str

    # Schema validation
    schema_compliance: SchemaCompliance
    pynwb_validation_errors: List[str]
    required_fields_present: List[str]
    required_fields_missing: List[str]
    recommended_fields_present: List[str]

    # NWB Inspector validation
    inspector_messages: List[InspectorMessage]
    critical_issues_count: int
    error_issues_count: int
    warning_issues_count: int
    importance_weighted_score: float  # 0.0 to 1.0

    # Data integrity
    checksum: str                    # File checksum
    file_size_bytes: int
    data_integrity_checks: List[IntegrityCheck]
    temporal_alignment_drift_ms: float  # Max drift across streams
    spatial_registration_accurate: bool

    # Metadata completeness
    total_fields: int
    populated_fields: int
    metadata_completeness: float     # populated / total

    # Scientific accuracy
    signal_fidelity_preserved: bool
    unit_conversions_correct: bool
    provenance_complete: bool
    reproducibility_validated: bool

    # Validation results
    overall_valid: bool              # Passes all critical checks
    validation_errors: List[ValidationError]
    validation_warnings: List[str]

    # Metadata
    validated_at: datetime
    validator_version: str
```

**Nested Types**:

```python
@dataclass
class SchemaCompliance:
    compliant: bool
    nwb_version: str                 # e.g., "2.6.0"
    schema_violations: List[str]
    custom_extensions: List[str]
    extensions_valid: bool

@dataclass
class InspectorMessage:
    importance: str                  # CRITICAL, BEST_PRACTICE_VIOLATION, BEST_PRACTICE_SUGGESTION
    message: str
    check_function_name: str
    file_path: str
    location: str

@dataclass
class IntegrityCheck:
    check_name: str
    passed: bool
    details: str
    timestamp: datetime

@dataclass
class ValidationError:
    error_type: str
    message: str
    location: str
    severity: Severity
```

**Validation Criteria** (FR-015, FR-031, FR-032):

- ✓ NWB Inspector: Zero critical issues
- ✓ PyNWB validator: Zero schema violations
- ✓ Required fields: 100% compliance
- ✓ Recommended fields: >90% when applicable
- ✓ Data integrity: Checksum verification passed
- ✓ Temporal alignment: <1ms drift
- ✓ Metadata completeness: >95% fields populated
- ✓ Quality score: >99% pass rate for valid input data

**Operations**:

```python
def run_full_validation(self) -> 'NWBFileValidation':
    """Execute all validation checks"""
    pass

def calculate_quality_score(self) -> QualityScore:
    """Calculate importance-weighted quality score"""
    pass

def generate_dandi_validation(self) -> ComplianceCertificate:
    """Check DANDI upload readiness"""
    pass
```

**Relationships**:

- Validates converted NWB files from `TestDataset`
- Generates `QualityScore`
- May generate `ComplianceCertificate` for DANDI
- Results included in `EvaluationReport`

---

### 10. RDF Graph Validation

**Description**: Knowledge graph quality assessment with syntax validation,
semantic consistency, and ontology linkage.

**Fields**:

```python
@dataclass
class RDFGraphValidation:
    # Identification
    id: str
    graph_file_path: Path
    graph_format: RDFFormat          # turtle, n-triples, json-ld, etc.

    # Syntax validation
    syntactically_correct: bool
    syntax_errors: List[str]
    triple_count: int
    entity_count: int
    property_count: int

    # Semantic validation
    semantically_valid: bool
    ontology_consistency: bool
    reasoning_errors: List[str]

    # Ontology linkage
    total_entities: int
    linked_entities: int
    ontology_linkage_rate: float     # linked / total (target >0.8)
    ontologies_used: List[OntologyReference]

    # SPARQL query validation
    example_queries_tested: List[SPARQLQuery]
    all_queries_successful: bool
    query_performance: Dict[str, float]  # Query → execution time

    # Structure preservation
    nwb_relationships_preserved: bool
    metadata_as_triples_complete: bool
    provenance_statements_present: bool

    # Round-trip conversion
    round_trip_successful: bool
    round_trip_metadata_loss: float  # 0.0 = no loss, 1.0 = complete loss

    # Graph metrics
    graph_metrics: GraphMetrics

    # Validation results
    overall_valid: bool
    validation_errors: List[ValidationError]

    # Metadata
    validated_at: datetime
    validator_version: str
```

**Enums**:

```python
class RDFFormat(Enum):
    TURTLE = "turtle"
    NTRIPLES = "n-triples"
    JSONLD = "json-ld"
    RDFXML = "rdf-xml"
    N3 = "n3"
```

**Nested Types**:

```python
@dataclass
class OntologyReference:
    namespace: str                   # e.g., "http://purl.org/nidash/nidm#"
    prefix: str                      # e.g., "nidm"
    version: Optional[str]
    entity_count: int                # Entities using this ontology

@dataclass
class SPARQLQuery:
    name: str
    query_string: str
    expected_results: int            # Expected result count
    actual_results: int
    execution_time_ms: float
    successful: bool

@dataclass
class GraphMetrics:
    average_out_degree: float        # Average edges per node
    graph_diameter: int              # Longest shortest path
    connected_components: int        # Should be 1 for fully connected
    node_clustering_coefficient: float
    density: float                   # Actual edges / possible edges
```

**Validation Criteria** (FR-033):

- ✓ Syntactically correct: Valid Turtle/N-Triples
- ✓ Semantically meaningful: Proper ontology use
- ✓ SPARQL-queryable: Example queries successful
- ✓ Ontology linking: >80% entities linked to standards
- ✓ Metadata coverage: All NWB metadata as triples
- ✓ Relationships preserved: NWB structure maintained
- ✓ Provenance: Complete provenance statements
- ✓ Round-trip: RDF ↔ NWB bidirectional conversion

**Operations**:

```python
def validate_syntax(self) -> bool:
    """Validate RDF syntax"""
    pass

def validate_semantics(self) -> bool:
    """Validate ontology usage and consistency"""
    pass

def test_sparql_queries(self, queries: List[str]) -> List[SPARQLQuery]:
    """Test SPARQL queryability"""
    pass

def calculate_ontology_linkage(self) -> float:
    """Calculate percentage of entities linked to standard ontologies"""
    pass

def test_round_trip_conversion(self) -> bool:
    """Test RDF → NWB → RDF conversion"""
    pass
```

**Standard Ontologies** (>80% linkage target):

- NIDM: Neuroimaging Data Model
- PROV: Provenance Ontology
- NWB: NWB Ontology
- NCIT: NCI Thesaurus
- UBERON: Anatomy ontology

**Relationships**:

- Validates RDF graphs generated from NWB files
- Generates `QualityScore` for graph quality
- Results included in `EvaluationReport`
- References standard ontologies

---

## Reporting Entities

### 11. Test Report

**Description**: Comprehensive test execution summary with pass/fail statistics,
coverage metrics, and performance data.

**Fields**:

```python
@dataclass
class TestReport:
    # Identification
    id: str
    report_type: ReportType          # unit, integration, e2e, full
    name: str
    description: str

    # Execution metadata
    started_at: datetime
    completed_at: datetime
    duration_seconds: float

    # Environment
    test_environment_id: str
    python_version: str
    os_platform: str
    git_commit: str                  # Git commit hash
    git_branch: str

    # Test statistics
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    flaky_tests: List[str]           # Flaky test IDs

    # Coverage metrics
    line_coverage: float             # 0.0 to 1.0
    branch_coverage: float
    path_coverage: float
    coverage_by_module: Dict[str, float]

    # Performance data
    total_execution_time: float
    average_test_time: float
    slowest_tests: List[Tuple[str, float]]  # (test_id, duration)
    fastest_tests: List[Tuple[str, float]]

    # Failure details
    failures: List[FailureDetail]
    error_messages: List[str]

    # Test suites
    suite_results: List[SuiteResult]

    # Artifacts
    log_file_path: Optional[Path]
    coverage_report_path: Optional[Path]
    junit_xml_path: Optional[Path]

    # Metadata
    generated_by: str                # e.g., "pytest 7.4.0"
    report_version: str
```

**Enums**:

```python
class ReportType(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    FULL = "full"                    # All test types
```

**Nested Types**:

```python
@dataclass
class FailureDetail:
    test_id: str
    test_name: str
    failure_message: str
    stack_trace: str
    failure_type: str                # assertion, exception, timeout
    reproduction_steps: List[str]

@dataclass
class SuiteResult:
    suite_id: str
    suite_name: str
    total: int
    passed: int
    failed: int
    skipped: int
    duration: float
```

**Operations**:

```python
def calculate_pass_rate(self) -> float:
    """Calculate test pass rate"""
    return self.passed_tests / self.total_tests if self.total_tests > 0 else 0.0

def identify_flaky_tests(self, historical_results: List['TestReport']) -> List[str]:
    """Identify tests with inconsistent results"""
    pass

def generate_html_report(self) -> Path:
    """Generate HTML report"""
    pass

def generate_json_report(self) -> Path:
    """Generate JSON report for APIs"""
    pass
```

**Coverage Targets**:

- MCP server: 90%+ (FR-001)
- Agents: 85%+ (FR-007)
- Client libraries: 85%+ (FR-019)
- Overall: 85%+ for critical paths

**Relationships**:

- Contains results from multiple `TestSuite` instances
- References `TestEnvironment` used
- May link to `CoverageReport` for detailed coverage
- Stored for historical trend analysis

---

### 12. Coverage Report

**Description**: Code coverage analysis with line, branch, and path coverage,
file-level breakdown, and trend analysis.

**Fields**:

```python
@dataclass
class CoverageReport:
    # Identification
    id: str
    test_report_id: str              # Associated test report

    # Overall coverage
    overall_line_coverage: float     # 0.0 to 1.0
    overall_branch_coverage: float
    overall_path_coverage: float
    total_lines: int
    covered_lines: int
    total_branches: int
    covered_branches: int

    # Module-level coverage
    module_coverage: List[ModuleCoverage]

    # File-level coverage
    file_coverage: List[FileCoverage]

    # Uncovered areas
    uncovered_lines: List[UncoveredArea]
    uncovered_branches: List[UncoveredArea]

    # Trend analysis
    previous_coverage: Optional[float]
    coverage_delta: Optional[float]
    trend: Trend

    # Gap identification
    coverage_gaps: List[CoverageGap]

    # Artifacts
    html_report_path: Optional[Path]
    xml_report_path: Optional[Path]  # Cobertura/JaCoCo format
    json_report_path: Optional[Path]

    # Metadata
    generated_at: datetime
    coverage_tool: str               # e.g., "coverage.py 7.3.0"
```

**Nested Types**:

```python
@dataclass
class ModuleCoverage:
    module_name: str                 # e.g., "agentic_neurodata_conversion.agents"
    line_coverage: float
    branch_coverage: float
    total_lines: int
    covered_lines: int
    total_branches: int
    covered_branches: int
    meets_threshold: bool            # Based on component type

@dataclass
class FileCoverage:
    file_path: Path
    line_coverage: float
    branch_coverage: float
    covered_lines: List[int]
    uncovered_lines: List[int]
    partial_lines: List[int]         # Partially covered branches

@dataclass
class UncoveredArea:
    file_path: Path
    line_number: int
    code_snippet: str
    reason: str                      # e.g., "Error handling path", "Edge case"
    priority: str                    # high, medium, low

@dataclass
class CoverageGap:
    component: str
    current_coverage: float
    target_coverage: float
    gap_percentage: float
    recommended_tests: List[str]     # Suggested tests to close gap
```

**Operations**:

```python
def calculate_coverage_delta(self, previous_report: 'CoverageReport') -> float:
    """Calculate change in coverage"""
    pass

def identify_gaps(self) -> List[CoverageGap]:
    """Identify components below coverage targets"""
    pass

def generate_html_report(self) -> Path:
    """Generate interactive HTML coverage report"""
    pass
```

**Coverage Thresholds** (per component):

```python
COVERAGE_THRESHOLDS = {
    "mcp_server.endpoints": 0.90,    # FR-001
    "agents": 0.85,                  # FR-007
    "client": 0.85,                  # FR-019
    "utils": 0.80,
    "critical_paths": 1.00,          # 100% for auth, data integrity
}
```

**Relationships**:

- Associated with one `TestReport`
- Tracks coverage by `TestCase` and `TestSuite`
- Historical reports stored for trend analysis
- Gaps inform new `TestCase` creation

---

### 13. Quality Report

**Description**: Multi-dimensional quality assessment with code quality metrics,
technical debt, security findings, and performance analysis.

**Fields**:

```python
@dataclass
class QualityReport:
    # Identification
    id: str
    artifact_id: str                 # Codebase, component, etc.
    report_date: datetime

    # Code quality metrics
    cyclomatic_complexity: ComplexityMetrics
    code_duplication: DuplicationMetrics
    maintainability_index: float     # 0-100 scale
    technical_debt_ratio: float      # 0.0 to 1.0

    # Security findings
    security_issues: List[SecurityIssue]
    vulnerability_count: int
    critical_vulnerabilities: int
    owasp_compliance: bool

    # Performance analysis
    performance_issues: List[PerformanceIssue]
    performance_score: float         # 0.0 to 1.0

    # Code smells
    code_smells: List[CodeSmell]
    smell_density: float             # Smells per KLOC

    # Dependencies
    dependency_vulnerabilities: List[DependencyVulnerability]
    outdated_dependencies: List[str]

    # Recommendations
    improvement_recommendations: List[Recommendation]
    refactoring_candidates: List[str]  # Functions/classes to refactor

    # Overall quality
    overall_quality_score: float     # Composite score 0.0 to 1.0
    quality_gate_passed: bool

    # Trend
    previous_score: Optional[float]
    trend: Trend

    # Metadata
    generated_by: str                # e.g., "SonarQube", "Bandit"
    tool_versions: Dict[str, str]
```

**Nested Types**:

```python
@dataclass
class ComplexityMetrics:
    average_complexity: float
    max_complexity: int
    high_complexity_functions: List[Tuple[str, int]]  # (function, complexity)
    complexity_by_module: Dict[str, float]

@dataclass
class DuplicationMetrics:
    duplication_percentage: float    # 0.0 to 1.0
    duplicated_lines: int
    duplicated_blocks: int
    largest_duplicates: List[DuplicationBlock]

@dataclass
class DuplicationBlock:
    file_path: Path
    start_line: int
    end_line: int
    duplicated_in: List[Path]

@dataclass
class SecurityIssue:
    issue_id: str
    severity: Severity
    category: str                    # e.g., "SQL Injection", "XSS"
    description: str
    file_path: Path
    line_number: int
    cwe_id: Optional[str]            # Common Weakness Enumeration ID
    owasp_category: Optional[str]
    remediation: str

@dataclass
class PerformanceIssue:
    issue_type: str                  # e.g., "N+1 queries", "Memory leak"
    severity: Severity
    location: str
    impact: str
    recommendation: str

@dataclass
class CodeSmell:
    smell_type: str                  # e.g., "Long method", "God class"
    severity: Severity
    location: str
    description: str

@dataclass
class DependencyVulnerability:
    package_name: str
    current_version: str
    vulnerable_version_range: str
    cve_id: str
    severity: Severity
    fixed_version: str

@dataclass
class Recommendation:
    priority: str                    # high, medium, low
    category: str                    # performance, security, maintainability
    description: str
    effort_estimate: str             # small, medium, large
    impact: str                      # low, medium, high
```

**Quality Metrics** (FR-028):

- Cyclomatic complexity: Target <10 per function
- Code duplication: Target <3%
- Maintainability index: Target >70
- Technical debt ratio: Target <5%
- Security vulnerabilities: Zero critical
- OWASP compliance: 100%

**Operations**:

```python
def calculate_overall_score(self) -> float:
    """Calculate composite quality score"""
    pass

def check_quality_gates(self) -> bool:
    """Verify all quality gates passed"""
    pass

def generate_executive_dashboard(self) -> Dict[str, Any]:
    """Generate KPI dashboard data"""
    pass
```

**Relationships**:

- Generated from source code analysis
- References `TestReport` for test quality
- May trigger creation of new `ValidationRule` instances
- Trends tracked over time

---

### 14. Evaluation Report

**Description**: Conversion quality assessment with validation results, metadata
completeness, scientific accuracy, compliance status, and visualizations.

**Fields**:

```python
@dataclass
class EvaluationReport:
    # Identification
    id: str
    conversion_job_id: str
    nwb_file_id: str
    report_date: datetime

    # Input/Output
    source_dataset_id: str
    source_format: DataFormat
    output_nwb_path: Path
    output_rdf_path: Optional[Path]

    # Validation results
    nwb_validation: NWBFileValidation
    rdf_validation: Optional[RDFGraphValidation]
    quality_score: QualityScore
    compliance_certificates: List[ComplianceCertificate]

    # Metadata assessment
    metadata_completeness: float     # 0.0 to 1.0 (target >0.95)
    required_fields_status: Dict[str, bool]
    recommended_fields_status: Dict[str, bool]
    custom_fields: List[str]

    # Scientific accuracy
    scientific_validation: ScientificValidation
    data_integrity_verified: bool
    temporal_alignment_verified: bool
    spatial_registration_verified: bool

    # Quality assessment
    overall_quality: str             # excellent, good, acceptable, poor
    critical_issues: List[Issue]
    warnings: List[str]
    recommendations: List[Recommendation]

    # Comparison with benchmarks
    benchmark_comparison: BenchmarkComparison
    percentile_ranking: Optional[float]

    # Systematic issues
    systematic_issues: List[SystematicIssue]

    # Actionable recommendations
    priority_fixes: List[Fix]
    optional_improvements: List[str]

    # Visualizations
    visualization_paths: List[Path]  # PNG, SVG charts
    interactive_report_path: Optional[Path]  # HTML

    # Report formats
    html_report_path: Path
    pdf_report_path: Path
    json_report_path: Path

    # Metadata
    generated_by: str
    report_version: str
```

**Nested Types**:

```python
@dataclass
class ScientificValidation:
    spike_sorting_preserved: bool
    behavioral_events_aligned: bool
    stimulus_timing_accurate: bool
    trial_structure_maintained: bool
    metadata_fidelity: float
    provenance_complete: bool
    reproducible: bool
    validation_notes: str

@dataclass
class Issue:
    severity: Severity
    category: str
    description: str
    location: str
    impact: str
    suggested_fix: str

@dataclass
class BenchmarkComparison:
    benchmark_name: str
    user_score: float
    benchmark_score: float
    delta: float
    better_than_benchmark: bool
    percentile: Optional[float]

@dataclass
class SystematicIssue:
    issue_pattern: str               # Pattern observed
    occurrences: int
    affected_components: List[str]
    root_cause: str
    systemic_fix: str

@dataclass
class Fix:
    priority: int                    # 1 = highest
    description: str
    code_example: Optional[str]      # Example fix code
    estimated_effort: str
    expected_impact: str
```

**Quality Levels**:

```python
def determine_quality_level(self) -> str:
    """Determine overall quality based on scores"""
    if self.quality_score.overall_score >= 0.99:
        return "excellent"
    elif self.quality_score.overall_score >= 0.95:
        return "good"
    elif self.quality_score.overall_score >= 0.90:
        return "acceptable"
    else:
        return "poor"
```

**Operations**:

```python
def generate_html_report(self) -> Path:
    """Generate interactive HTML report with charts"""
    pass

def generate_pdf_report(self) -> Path:
    """Generate printable PDF report"""
    pass

def generate_json_report(self) -> Path:
    """Generate machine-readable JSON report"""
    pass

def compare_to_benchmarks(self, benchmarks: List[BenchmarkComparison]):
    """Compare against community/internal benchmarks"""
    pass

def identify_systematic_issues(self) -> List[SystematicIssue]:
    """Identify patterns in issues"""
    pass

def generate_priority_fixes(self) -> List[Fix]:
    """Generate prioritized list of fixes with code examples"""
    pass
```

**Report Requirements** (FR-034):

- ✓ Accurate reflection: No false positives/negatives
- ✓ Actionable recommendations: Priority scores
- ✓ Visualizations: Accurate and clear
- ✓ Benchmark comparison: Against community standards
- ✓ Trend tracking: Quality over time
- ✓ Systematic issues: Pattern identification
- ✓ Code examples: Specific fixes
- ✓ Multiple formats: HTML, PDF, JSON

**Relationships**:

- References `NWBFileValidation` and `RDFGraphValidation`
- Contains `QualityScore`
- Includes `ComplianceCertificate` instances
- Generated from conversion jobs
- Stored for historical analysis

---

### 15. Performance Report

**Description**: System performance analysis with benchmark results, resource
utilization, bottleneck identification, and regression detection.

**Fields**:

```python
@dataclass
class PerformanceReport:
    # Identification
    id: str
    report_type: PerformanceReportType
    benchmark_suite: str
    report_date: datetime

    # Benchmark results
    benchmark_results: List[BenchmarkResult]
    aggregate_metrics: AggregateMetrics

    # Resource utilization
    resource_utilization: ResourceUtilization
    peak_memory_mb: int
    average_memory_mb: int
    cpu_utilization_percent: float
    disk_io_mb: int
    network_io_mb: int

    # Performance metrics
    throughput: ThroughputMetrics
    latency: LatencyMetrics
    scalability: ScalabilityMetrics

    # Bottleneck analysis
    bottlenecks: List[Bottleneck]
    optimization_opportunities: List[Optimization]

    # Regression detection
    baseline_comparison: BaselineComparison
    regressions_detected: List[Regression]
    improvements_detected: List[Improvement]

    # Trend analysis
    historical_comparison: HistoricalComparison
    trend: Trend

    # Environment
    test_environment_id: str
    hardware_specs: HardwareSpecs

    # Artifacts
    flame_graph_path: Optional[Path]
    profile_data_path: Optional[Path]
    metrics_dashboard_path: Optional[Path]

    # Metadata
    profiling_tool: str              # e.g., "pytest-benchmark", "cProfile"
    tool_version: str
```

**Enums**:

```python
class PerformanceReportType(Enum):
    CONVERSION = "conversion"        # Conversion speed benchmarks
    AGENT = "agent"                  # Agent response times
    CLIENT = "client"                # Client latency/throughput
    E2E = "e2e"                      # End-to-end workflow performance
```

**Nested Types**:

```python
@dataclass
class BenchmarkResult:
    benchmark_name: str
    iterations: int
    median: float                    # Median execution time
    mean: float
    stddev: float
    min: float
    max: float
    percentile_95: float
    percentile_99: float
    passed: bool                     # Met performance target
    target: Optional[float]          # Performance target

@dataclass
class AggregateMetrics:
    total_benchmarks: int
    passed_benchmarks: int
    failed_benchmarks: int
    overall_pass_rate: float

@dataclass
class ResourceUtilization:
    timestamp: datetime
    cpu_percent: float
    memory_mb: int
    disk_read_mb: int
    disk_write_mb: int
    network_sent_mb: int
    network_recv_mb: int
    gpu_utilization_percent: Optional[float]

@dataclass
class ThroughputMetrics:
    requests_per_second: Optional[float]
    mb_per_second: Optional[float]
    conversions_per_hour: Optional[int]
    batch_efficiency: Optional[float]

@dataclass
class LatencyMetrics:
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float

@dataclass
class ScalabilityMetrics:
    parallel_speedup: float          # Actual speedup / theoretical
    efficiency: float                # speedup / num_workers
    scaling_factor: float            # Performance at N cores / 1 core

@dataclass
class Bottleneck:
    location: str                    # Function/module
    bottleneck_type: str             # CPU, memory, I/O, network
    severity: Severity
    time_percentage: float           # % of total time
    recommendation: str

@dataclass
class Optimization:
    target: str                      # What to optimize
    current_performance: float
    potential_gain: float
    effort: str                      # low, medium, high
    approach: str                    # How to optimize

@dataclass
class BaselineComparison:
    baseline_id: str
    baseline_date: datetime
    current_score: float
    baseline_score: float
    delta_percentage: float
    regression_threshold: float = 0.1  # 10% slower = regression

@dataclass
class Regression:
    benchmark_name: str
    current_value: float
    baseline_value: float
    degradation_percentage: float
    severity: Severity
    possible_cause: str

@dataclass
class Improvement:
    benchmark_name: str
    current_value: float
    baseline_value: float
    improvement_percentage: float
    likely_reason: str

@dataclass
class HistoricalComparison:
    period_days: int
    data_points: int
    trend_direction: Trend
    average_change_per_day: float

@dataclass
class HardwareSpecs:
    cpu_model: str
    cpu_cores: int
    cpu_threads: int
    memory_gb: int
    disk_type: str                   # SSD, HDD
    gpu_model: Optional[str]
```

**Performance Targets**:

```python
PERFORMANCE_TARGETS = {
    # Conversion speed (FR-018)
    "conversion_speed_mbps": {
        "open_ephys": 50,
        "spikeglx": 75,
        "neuralynx": 60,
    },
    # Agent response times (FR-012)
    "agent_p95_latency_ms": 200,
    # Client performance (FR-024)
    "client_p95_latency_ms": 100,
    "client_throughput_rps": 1000,
}
```

**Operations**:

```python
def detect_regressions(self, baseline: 'PerformanceReport') -> List[Regression]:
    """Compare to baseline and detect regressions"""
    pass

def identify_bottlenecks(self) -> List[Bottleneck]:
    """Analyze profiling data to find bottlenecks"""
    pass

def recommend_optimizations(self) -> List[Optimization]:
    """Generate optimization recommendations"""
    pass

def generate_flame_graph(self) -> Path:
    """Generate flame graph visualization"""
    pass
```

**Benchmark Coverage**:

- Conversion speed by format (FR-018)
- Agent response times under load (FR-012)
- Client latency distributions (FR-024)
- Memory usage patterns (FR-018, FR-012)
- Disk I/O patterns (FR-018)
- CPU utilization (FR-018)
- Parallel scaling efficiency (FR-018)

**Relationships**:

- References `TestEnvironment` for hardware context
- Stores baselines for regression detection
- Historical reports tracked for trends
- Bottlenecks inform optimization tasks

---

## Entity Relationships Summary

```
TestSuite (1) ─┬─> (N) TestCase
               └─> (N) TestSuite (sub-suites)

TestCase (N) ──> (1) TestSuite
TestCase (N) ──> (N) TestDataset
TestCase (N) ──> (1) TestEnvironment
TestCase (N) ──> (N) MockService

TestEnvironment (1) ──> (N) MockService
TestEnvironment (1) ──> (N) TestDataset

TestCase (N) ──> (N) ValidationRule (applied)
ValidationRule (N) ──> (N) ValidationResult
ValidationResult (N) ──> (1) QualityScore

NWBFileValidation (1) ──> (1) QualityScore
NWBFileValidation (N) ──> (N) ValidationRule
NWBFileValidation (1) ──> (0..N) ComplianceCertificate

RDFGraphValidation (1) ──> (1) QualityScore
RDFGraphValidation (N) ──> (N) ValidationRule

TestReport (1) ──> (N) TestCase
TestReport (1) ──> (1) CoverageReport
TestReport (1) ──> (1) TestEnvironment

EvaluationReport (1) ──> (1) NWBFileValidation
EvaluationReport (0..1) ──> (1) RDFGraphValidation
EvaluationReport (1) ──> (1) QualityScore
EvaluationReport (1) ──> (N) ComplianceCertificate

PerformanceReport (1) ──> (N) BenchmarkResult
PerformanceReport (1) ──> (1) TestEnvironment
```

---

## Storage and Persistence

### Database Schema Considerations

**Primary Storage**: PostgreSQL for relational data, with JSON fields for
flexible metadata

**Key Tables**:

- `test_cases`: TestCase entity storage
- `test_suites`: TestSuite entity storage
- `test_environments`: TestEnvironment entity storage
- `test_datasets`: TestDataset metadata (actual data in DataLad)
- `mock_services`: MockService configurations
- `validation_rules`: ValidationRule definitions
- `quality_scores`: QualityScore tracking
- `compliance_certificates`: ComplianceCertificate records
- `nwb_file_validations`: NWBFileValidation results
- `rdf_graph_validations`: RDFGraphValidation results
- `test_reports`: TestReport storage
- `coverage_reports`: CoverageReport storage
- `quality_reports`: QualityReport storage
- `evaluation_reports`: EvaluationReport storage
- `performance_reports`: PerformanceReport storage

**Indexes**:

- Primary keys: All entity IDs
- Foreign keys: All relationship IDs
- Composite indexes: (suite_id, execution_status), (nwb_file_id,
  validation_date)
- Full-text search: test_name, description fields

**Archival Strategy**:

- Active data: Last 90 days in primary database
- Historical data: >90 days archived to S3/cold storage
- Retention: 2 years for compliance

---

## Data Validation Summary

Each entity includes validation rules to ensure data integrity:

1. **Type validation**: All fields have strict type checking
2. **Range validation**: Numeric fields have valid ranges
3. **Enum validation**: Enumerated fields only accept valid values
4. **Relationship validation**: Foreign keys reference existing entities
5. **State validation**: State transitions follow defined rules
6. **Business logic validation**: Complex rules (e.g., coverage calculations)

This data model supports all 45 functional requirements (FR-001 through FR-045)
across the 8 major testing areas defined in the specification.
