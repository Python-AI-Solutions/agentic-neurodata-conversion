# Testing and Quality Assurance Framework - Research

## Overview
This document consolidates research findings for implementing a comprehensive testing and quality assurance framework for the agentic neurodata conversion system. The framework must support testing across MCP server, agents, client libraries, end-to-end workflows, CI/CD pipelines, validation, utilities, and monitoring.

## 1. pytest Framework and Coverage Strategy

### Decision
Use pytest as the primary testing framework with pytest-cov for coverage tracking, targeting 90%+ coverage for critical paths and 85%+ for client libraries.

### Rationale
- **pytest**: Industry standard for Python testing with rich plugin ecosystem
- **Fixture system**: Ideal for complex test setup (mock services, test datasets)
- **Parametrization**: Supports testing 50+ scenarios per agent efficiently
- **Plugin architecture**: Extensible for custom markers, reporters, and hooks
- **pytest-cov**: Integrates with coverage.py for line, branch, and path coverage
- **pytest-xdist**: Enables parallel test execution for faster CI/CD

### Implementation Approach
```python
# pytest.ini configuration
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (external dependencies)
    e2e: End-to-end tests (full workflows)
    slow: Slow tests (skip in quick runs)
    contract: Contract tests (API schemas)
addopts =
    --strict-markers
    --cov=agentic_neurodata_conversion
    --cov-report=html
    --cov-report=json
    --cov-report=term-missing
    --cov-branch
    --maxfail=3
    --tb=short
```

### Coverage Targets
- MCP server endpoints: 90%+ (FR-001)
- Agent core functionality: 85%+ (FR-007)
- Client libraries: 85%+ (FR-019)
- Utility functions: 80%+
- Critical paths: 100% (authentication, data integrity)

### Alternatives Considered
- unittest: Less expressive, requires more boilerplate
- nose2: Declining community support
- tox: Used in addition for multi-environment testing

---

## 2. Property-Based Testing with Hypothesis

### Decision
Use Hypothesis for property-based testing of data transformations, particularly for agent data processing and format conversions.

### Rationale
- **Automated test case generation**: Finds edge cases developers miss
- **Shrinking**: Automatically minimizes failing examples
- **Stateful testing**: Models agent state machines (FR-011)
- **Data strategies**: Built-in strategies for complex data types
- **Integration**: Works seamlessly with pytest
- **Scientific data**: Can generate realistic neuroscience data patterns

### Implementation Approach
```python
from hypothesis import given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule

# Property-based data transformation tests
@given(
    nwb_data=st.builds(NWBData),
    metadata=st.dictionaries(st.text(), st.text())
)
def test_conversion_preserves_data_integrity(nwb_data, metadata):
    converted = convert_to_nwb(nwb_data, metadata)
    assert validate_nwb(converted)
    assert data_checksum(converted) == data_checksum(nwb_data)

# Stateful testing for agent state machines
class AgentStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.agent = ConversionAgent()

    @rule(data=st.binary())
    def process_data(self, data):
        # Test state transitions with random data
        pass
```

### Use Cases
- FR-007: Data transformation accuracy validation
- FR-011: Agent state machine validation
- FR-015: NWB file data integrity verification
- FR-035: Numerical precision preservation

### Alternatives Considered
- Manual edge case enumeration: Incomplete coverage
- QuickCheck (Haskell): Not Python native
- PropCheck: Less mature than Hypothesis

---

## 3. Mock Service Patterns

### Decision
Implement a layered mocking strategy using unittest.mock, responses (HTTP), and custom mock services for LLM, filesystem, and network operations.

### Rationale
- **100+ mock scenarios required** (FR-009, FR-020)
- **Deterministic testing**: Essential for CI/CD reliability
- **Fast execution**: No external service dependencies
- **Isolation**: Test components independently
- **Reproducibility**: Consistent test results across environments

### Implementation Approach

#### 3.1 Mock LLM Services
```python
# tests/fixtures/mock_llm.py
class MockLLMService:
    """Deterministic LLM responses for testing"""

    def __init__(self, response_library: Dict[str, str]):
        self.responses = response_library
        self.calls = []
        self.mode = "deterministic"  # or "variation"

    def complete(self, prompt: str, **kwargs) -> str:
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        if self.mode == "deterministic":
            return self.responses.get(prompt, "default_response")
        else:
            return self._generate_variation(prompt)

    def count_tokens(self, text: str) -> int:
        return len(text.split())  # Simplified

    def inject_latency(self, ms: int):
        """Simulate network latency"""
        time.sleep(ms / 1000)
```

#### 3.2 Mock Filesystem
```python
# tests/fixtures/mock_fs.py
from io import BytesIO
import tempfile

class MockFilesystem:
    """In-memory filesystem for testing"""

    def __init__(self):
        self.files = {}
        self.operations_log = []

    def write(self, path: str, content: bytes):
        self.files[path] = BytesIO(content)
        self.operations_log.append(("write", path, len(content)))

    def read(self, path: str) -> bytes:
        if path not in self.files:
            raise FileNotFoundError(path)
        self.operations_log.append(("read", path))
        return self.files[path].getvalue()

    def exists(self, path: str) -> bool:
        return path in self.files
```

#### 3.3 Mock HTTP Services
```python
# tests/fixtures/mock_http.py
import responses
from requests.exceptions import Timeout, ConnectionError

@responses.activate
def test_client_retry_logic():
    # Simulate 500 error, then success
    responses.add(responses.GET, "http://api/data",
                  status=500)
    responses.add(responses.GET, "http://api/data",
                  json={"data": "success"}, status=200)

    result = client.get_with_retry("/data")
    assert result["data"] == "success"
    assert len(responses.calls) == 2
```

### Mock Scenarios Coverage
- LLM timeout/errors: 10 scenarios
- Filesystem operations: 15 scenarios (permissions, corruption, full disk)
- Network conditions: 20 scenarios (latency, packet loss, timeout)
- External APIs: 25 scenarios (rate limiting, auth failures, versioning)
- Time manipulation: 10 scenarios (time zones, temporal testing)
- Credentials/secrets: 10 scenarios (invalid, expired, rotation)
- Random number generation: 10 scenarios (deterministic seeding)

### Alternatives Considered
- VCR.py: Records HTTP interactions, but less flexible
- moto: AWS-specific mocking
- pytest-mock: Wrapper around unittest.mock, similar capabilities

---

## 4. DataLad Test Dataset Integration

### Decision
Use DataLad for version-controlled test dataset management with on-demand data fetching and reproducible testing.

### Rationale
- **Version control for data**: Git-annex backend tracks dataset versions
- **Reproducibility**: Same dataset versions across all test runs
- **Efficient storage**: Only fetch datasets when needed
- **15+ format combinations** required (FR-014)
- **Up to 1TB test workflows** (FR-016)
- **Scientific standard**: Used in neuroscience community

### Implementation Approach
```python
# tests/conftest.py
import datalad.api as dl

@pytest.fixture(scope="session")
def test_datasets():
    """Load DataLad-managed test datasets"""
    datasets = {}

    # Install datasets if not present
    dataset_configs = [
        ("open-ephys", "https://gin.g-node.org/test/open-ephys-sample"),
        ("spikeglx", "https://gin.g-node.org/test/spikeglx-sample"),
        ("neuralynx", "https://gin.g-node.org/test/neuralynx-sample"),
        # ... 12 more format combinations
    ]

    for name, url in dataset_configs:
        ds_path = Path(f"tests/data/{name}")
        if not ds_path.exists():
            ds = dl.install(path=ds_path, source=url)
        else:
            ds = dl.Dataset(ds_path)

        # Fetch specific files on demand
        datasets[name] = ds

    return datasets

@pytest.fixture
def open_ephys_data(test_datasets):
    """Get Open Ephys test data"""
    ds = test_datasets["open-ephys"]
    ds.get("recording_001.continuous")  # Fetch specific file
    return ds.path / "recording_001.continuous"
```

### Dataset Organization
```
tests/data/
├── open-ephys/           # Multi-channel, multi-session
├── spikeglx/            # Different probe configurations
├── neuralynx/           # Video synchronization
├── calcium-imaging/     # Suite2p, CaImAn processed
├── behavioral/          # DeepLabCut, SLEAP
├── multimodal/          # ephys + imaging + behavior
├── corrupted/           # Missing/corrupted segments
├── legacy/              # Legacy format migrations
└── performance/         # Large datasets for benchmarking
```

### Test Dataset Characteristics
- Minimal valid: <10MB (quick CI tests)
- Typical: 100MB-1GB (integration tests)
- Large-scale: Up to 1TB (performance benchmarks)
- Format coverage: 15+ distinct combinations
- Quality variations: Valid, corrupted, incomplete metadata

### Alternatives Considered
- Git LFS: File size limits, costly for large datasets
- Direct downloads: No version control, not reproducible
- S3/cloud storage: Requires credentials, network dependency

---

## 5. Contract Testing with OpenAPI

### Decision
Use schemathesis and openapi-core for automated contract testing against OpenAPI specifications, achieving 100% specification coverage (FR-003).

### Rationale
- **Automated test generation**: From OpenAPI schema
- **Property-based**: Uses Hypothesis under the hood
- **Request/response validation**: Ensures API compliance
- **Multiple strategies**: Random, positive, negative testing
- **CI/CD integration**: Runs as part of test suite

### Implementation Approach
```python
# tests/contract/test_mcp_server_api.py
import schemathesis
from pathlib import Path

schema = schemathesis.from_path(
    "contracts/mcp_server_api.yaml",
    base_url="http://localhost:8000"
)

@schema.parametrize()
def test_api_contract(case):
    """Test all endpoints against OpenAPI spec"""
    response = case.call()
    case.validate_response(response)

@pytest.mark.contract
def test_endpoint_schemas():
    """Validate specific endpoint schemas"""
    from openapi_core import OpenAPI

    spec = OpenAPI.from_file_path("contracts/mcp_server_api.yaml")

    # Test request validation
    request = spec.unmarshal_request("/api/convert", "POST", {
        "headers": {"Content-Type": "application/json"},
        "body": {"dataset": "test", "format": "nwb"}
    })
    assert request.body.dataset == "test"

    # Test response validation
    response = spec.unmarshal_response(request, 200, {
        "body": {"job_id": "12345", "status": "queued"}
    })
    assert response.data.job_id == "12345"
```

### Contract Coverage
- All MCP server HTTP endpoints
- Request schema validation (required fields, types, enums, formats)
- Response schema validation (status codes, data structures)
- Pagination consistency
- HATEOAS link validity
- Versioning headers
- Error response formats

### OpenAPI Schema Structure
```yaml
# contracts/mcp_server_api.yaml
openapi: 3.0.0
info:
  title: MCP Server API
  version: 1.0.0

paths:
  /api/convert:
    post:
      operationId: createConversion
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ConversionRequest'
      responses:
        '200':
          description: Conversion job created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ConversionJob'

components:
  schemas:
    ConversionRequest:
      type: object
      required: [dataset, format]
      properties:
        dataset: {type: string}
        format: {type: string, enum: [nwb, bids]}
```

### Alternatives Considered
- Manual contract tests: Time-consuming, incomplete
- Dredd: Language-agnostic but less Python integration
- Postman/Newman: GUI-based, less suited for CI/CD

---

## 6. Chaos Engineering for Python

### Decision
Implement chaos engineering using pytest-chaos and custom fault injection for client resilience testing (FR-023, FR-025).

### Rationale
- **Resilience validation**: Test failure modes systematically
- **Real-world conditions**: Network failures, resource exhaustion
- **Circuit breaker testing**: Validate fallback mechanisms
- **Client robustness**: 50+ error scenarios (FR-020, FR-021)

### Implementation Approach
```python
# tests/chaos/test_client_resilience.py
import pytest
from chaos import inject_network_failure, inject_resource_exhaustion

class TestClientChaos:

    @pytest.mark.chaos
    def test_network_partition(self, client):
        """Test client behavior during network partition"""
        with inject_network_failure(duration=5):
            with pytest.raises(ConnectionError):
                client.get("/data")

        # Verify recovery
        response = client.get("/data")
        assert response.status_code == 200

    @pytest.mark.chaos
    def test_connection_pool_exhaustion(self, client):
        """Test connection pool exhaustion handling"""
        # Exhaust connection pool
        connections = [client.get_async("/data") for _ in range(100)]

        # Verify graceful degradation
        response = client.get("/data", timeout=10)
        assert response or client.circuit_breaker.is_open()

    @pytest.mark.chaos
    def test_memory_pressure(self, agent):
        """Test agent behavior under memory pressure"""
        with inject_resource_exhaustion(memory_limit="100MB"):
            result = agent.process_large_dataset(size="1GB")
            assert result.status == "partial" or result.status == "error"
            assert agent.cleanup_called
```

### Chaos Scenarios
- **Network**: DNS failure, connection refused, timeout, packet loss, high latency
- **Server**: 500/503 errors, rate limiting, maintenance mode
- **Resources**: Memory limits, disk space, CPU throttling
- **Concurrency**: Race conditions, deadlocks, concurrent access
- **Data**: Corruption, partial transfers, encoding issues

### Custom Fault Injection
```python
# tests/fixtures/chaos.py
import contextlib
import resource

@contextlib.contextmanager
def inject_network_failure(duration: int):
    """Simulate network failure"""
    import socket
    original = socket.socket

    def failing_socket(*args, **kwargs):
        raise ConnectionError("Network unreachable")

    socket.socket = failing_socket
    try:
        yield
    finally:
        socket.socket = original

@contextlib.contextmanager
def inject_resource_exhaustion(memory_limit: str):
    """Limit available memory"""
    limit_bytes = parse_size(memory_limit)
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, hard))
    try:
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_AS, (soft, hard))
```

### Alternatives Considered
- Toxiproxy: Requires separate service, more complex setup
- Chaos Monkey: Infrastructure-focused, less applicable to unit tests
- Manual mocking: Less realistic failure modes

---

## 7. Performance Benchmarking and Regression Detection

### Decision
Use pytest-benchmark with custom performance baseline tracking and automated regression detection (FR-012, FR-018, FR-024).

### Rationale
- **Automated benchmarking**: Integrated with pytest
- **Statistical analysis**: Multiple iterations, outlier detection
- **Comparison**: Against historical baselines
- **Regression detection**: Fails tests on performance degradation
- **Multiple metrics**: Time, memory, throughput, latency

### Implementation Approach
```python
# tests/performance/test_conversion_benchmarks.py
import pytest
from pytest_benchmark import benchmark

@pytest.mark.benchmark(group="conversion")
def test_conversion_speed(benchmark, test_dataset):
    """Benchmark conversion speed (MB/sec)"""
    result = benchmark(convert_dataset, test_dataset)

    # Assert performance target
    speed_mbps = test_dataset.size_mb / result.stats.median
    assert speed_mbps >= 50, f"Conversion too slow: {speed_mbps} MB/s"

@pytest.mark.benchmark(group="agent")
def test_agent_response_time(benchmark, agent):
    """Benchmark agent response times under load"""
    def run_agent_task():
        return agent.process({"action": "analyze", "data": "sample"})

    result = benchmark.pedantic(run_agent_task, iterations=100, rounds=10)

    # Assert p95 latency < 200ms
    assert result.stats.percentile_95 < 0.2

# Performance baselines stored in JSON
# .benchmarks/Linux-CPython-3.12-64bit/0001_baseline.json
```

### Benchmark Organization
```
tests/performance/
├── test_conversion_benchmarks.py   # Conversion speed by format
├── test_agent_benchmarks.py        # Agent response times
├── test_client_benchmarks.py       # Client latency/throughput
├── test_memory_usage.py            # Memory profiling
└── baselines/                      # Historical performance data
    ├── conversion_baselines.json
    ├── agent_baselines.json
    └── client_baselines.json
```

### Performance Metrics
- **Conversion speed**: MB/sec by format (FR-018)
- **Agent response time**: p50, p95, p99 under various loads (FR-012)
- **Client latency**: Request latency distributions (FR-024)
- **Memory usage**: Peak and average (FR-018, FR-012)
- **Throughput**: Requests per second, batch efficiency
- **Scalability**: Parallel scaling efficiency

### Regression Detection
```python
# conftest.py
def pytest_benchmark_compare_failed(config, benchmarkgroup, result):
    """Fail build on performance regression"""
    for bench in result:
        if bench['change'] > 0.1:  # 10% regression threshold
            pytest.fail(f"Performance regression detected: {bench['name']} "
                       f"is {bench['change']*100:.1f}% slower")
```

### Alternatives Considered
- timeit: Manual, no statistical analysis
- cProfile: Profiling-focused, not benchmarking
- locust: Load testing-focused, overkill for unit benchmarks

---

## 8. CI/CD Optimization Strategies

### Decision
Implement multi-stage CI/CD pipeline with test selection, parallel execution, caching, and fail-fast mechanisms to achieve 50% feedback time reduction (FR-030).

### Rationale
- **Unit tests < 5 minutes** (FR-025)
- **Integration tests < 15 minutes** (FR-025)
- **Parallel execution**: Utilize multi-core CI runners
- **Incremental testing**: Only run affected tests
- **Result caching**: Avoid redundant test runs
- **Fail-fast**: Stop on first critical failure

### Implementation Approach

#### 8.1 Test Selection (pytest-testmon)
```python
# pytest.ini
[pytest]
addopts = --testmon

# Tracks file changes and runs only affected tests
# Example: Changing agent/converter.py only runs tests that import it
```

#### 8.2 Parallel Execution (pytest-xdist)
```python
# pytest.ini
[pytest]
addopts = -n auto  # Use all available cores

# Or specify exact number
addopts = -n 4

# With load balancing
addopts = -n auto --dist loadgroup
```

#### 8.3 Test Ordering and Fail-Fast
```python
# pytest.ini
[pytest]
# Run fast tests first
addopts = --ff --maxfail=1

# Custom ordering
@pytest.mark.order(1)  # Run first
def test_critical_path():
    pass

@pytest.mark.order(-1)  # Run last
def test_slow_integration():
    pass
```

#### 8.4 GitHub Actions Workflow
```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -e ".[test]"

      - name: Run unit tests
        run: |
          pytest tests/unit -n auto --testmon --maxfail=3
        timeout-minutes: 5

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Cache DataLad datasets
        uses: actions/cache@v3
        with:
          path: tests/data
          key: datasets-${{ hashFiles('tests/data/**/*.datalad') }}

      - name: Run integration tests
        run: |
          pytest tests/integration -n auto --dist loadgroup
        timeout-minutes: 15

  e2e-tests:
    needs: integration-tests
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - name: Run E2E tests
        run: |
          pytest tests/e2e --slow
        timeout-minutes: 30
```

### Optimization Techniques
1. **Test selection**: pytest-testmon tracks dependencies
2. **Parallel execution**: pytest-xdist with auto-scaling
3. **Test caching**: Cache DataLad datasets, pip packages
4. **Fail-fast**: --maxfail=3 stops after 3 failures
5. **Priority ordering**: Critical tests first with --ff
6. **Resource-aware scheduling**: --dist loadgroup balances load
7. **Distributed execution**: Matrix strategy for OS/Python versions
8. **Incremental testing**: Only changed files with --testmon

### CI/CD Metrics
- Unit test execution time: Target <5 min
- Integration test time: Target <15 min
- Total pipeline time: Target <30 min (50% reduction from baseline)
- Parallel efficiency: >80% core utilization
- Cache hit rate: >90% for dependencies

### Alternatives Considered
- tox: Useful for multi-environment, but slower
- Jenkins: More complex setup than GitHub Actions
- CircleCI: Similar to GitHub Actions, chose GHA for integration

---

## 9. NWB Validation Tools

### Decision
Use NWB Inspector for importance-weighted scoring, PyNWB for schema compliance, and DANDI CLI for upload readiness validation (FR-031).

### Rationale
- **NWB Inspector**: Official validation tool with configurable importance levels
- **PyNWB**: Reference implementation for schema validation
- **DANDI**: Upload readiness for community standard
- **>99% pass rate** required for valid input data (FR-031)
- **Zero critical issues** threshold (FR-015)

### Implementation Approach
```python
# tests/validation/test_nwb_quality.py
from nwbinspector import inspect_nwbfile, Importance
from pynwb import validate
import dandi.validate

def test_nwb_inspector_validation(converted_nwb_file):
    """Run NWB Inspector with importance-weighted scoring"""
    messages = list(inspect_nwbfile(
        nwbfile_path=converted_nwb_file,
        importance_threshold=Importance.CRITICAL
    ))

    # Assert zero critical issues
    critical_issues = [m for m in messages
                       if m.importance == Importance.CRITICAL]
    assert len(critical_issues) == 0, f"Critical issues found: {critical_issues}"

    # Calculate quality score
    score = calculate_quality_score(messages)
    assert score >= 0.99, f"Quality score {score} below threshold"

def test_pynwb_schema_compliance(converted_nwb_file):
    """Validate against PyNWB schema"""
    errors = validate(converted_nwb_file)
    assert len(errors) == 0, f"Schema violations: {errors}"

def test_dandi_upload_readiness(converted_nwb_file):
    """Validate DANDI upload requirements"""
    results = dandi.validate.validate(converted_nwb_file)
    errors = [r for r in results if r.severity == "error"]
    assert len(errors) == 0, f"DANDI validation errors: {errors}"

def calculate_quality_score(messages):
    """Calculate importance-weighted quality score"""
    weights = {
        Importance.CRITICAL: 1.0,
        Importance.BEST_PRACTICE_VIOLATION: 0.5,
        Importance.BEST_PRACTICE_SUGGESTION: 0.1
    }

    total_deductions = sum(weights.get(m.importance, 0) for m in messages)
    max_possible = 100  # Assume 100 point scale
    score = (max_possible - total_deductions) / max_possible
    return max(0, score)
```

### Validation Checklist
- ✓ NWB Inspector: Zero critical issues
- ✓ PyNWB validator: Zero schema violations
- ✓ Required fields: 100% compliance (FR-032)
- ✓ Recommended fields: >90% when applicable (FR-032)
- ✓ Data integrity: Checksum verification (FR-015)
- ✓ Temporal alignment: <1ms drift (FR-015)
- ✓ Metadata completeness: >95% fields (FR-015)
- ✓ DANDI upload: Ready for submission (FR-031)

### Custom Validation Rules
```python
# tests/validation/custom_rules.py
def validate_lab_standards(nwbfile):
    """Custom validation for lab-specific requirements"""
    rules = [
        ("subject.species", lambda s: s in ["Mus musculus", "Rattus norvegicus"]),
        ("session.start_time", lambda t: t.year >= 2020),
        ("devices", lambda d: len(d) > 0),
    ]

    violations = []
    for field, validator in rules:
        value = get_nested_attr(nwbfile, field)
        if not validator(value):
            violations.append(f"Lab standard violation: {field}")

    return violations
```

### Alternatives Considered
- Manual validation: Incomplete, error-prone
- Custom validators: Reinventing wheel, not community-standard
- Pre-validation tools: NWB Inspector is the standard

---

## 10. Knowledge Graph Validation (RDF, SPARQL)

### Decision
Use rdflib for RDF syntax validation, SPARQL query testing, and round-trip conversion validation (FR-033).

### Rationale
- **Syntactic correctness**: Valid Turtle/N-Triples required
- **Semantic validation**: Proper ontology use
- **Queryability**: SPARQL test queries must work
- **>80% ontology linking** target (FR-033)
- **Round-trip conversion**: RDF ↔ NWB bidirectional

### Implementation Approach
```python
# tests/validation/test_knowledge_graph.py
from rdflib import Graph, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery

def test_rdf_syntax_validation(rdf_graph_file):
    """Validate RDF syntax (Turtle/N-Triples)"""
    g = Graph()
    try:
        g.parse(rdf_graph_file, format="turtle")
    except Exception as e:
        pytest.fail(f"RDF syntax error: {e}")

    # Assert minimum triple count
    assert len(g) > 0, "Empty RDF graph"

def test_ontology_linking(rdf_graph_file):
    """Validate ontology usage and linking"""
    g = Graph()
    g.parse(rdf_graph_file, format="turtle")

    # Define standard ontologies
    NIDM = Namespace("http://purl.org/nidash/nidm#")
    PROV = Namespace("http://www.w3.org/ns/prov#")
    NWB = Namespace("http://purl.org/nwb#")

    # Count entities linked to standard ontologies
    total_entities = len(set(g.subjects()))
    linked_entities = len(set(
        s for s in g.subjects()
        if any(str(s).startswith(ns) for ns in [NIDM, PROV, NWB])
    ))

    linkage_rate = linked_entities / total_entities
    assert linkage_rate >= 0.8, f"Ontology linkage {linkage_rate:.1%} below 80%"

def test_sparql_queryability(rdf_graph_file):
    """Test SPARQL queries work correctly"""
    g = Graph()
    g.parse(rdf_graph_file, format="turtle")

    # Example queries
    queries = [
        # Find all sessions
        """
        PREFIX nwb: <http://purl.org/nwb#>
        SELECT ?session WHERE {
            ?session a nwb:Session .
        }
        """,
        # Find all subjects with species
        """
        PREFIX nwb: <http://purl.org/nwb#>
        SELECT ?subject ?species WHERE {
            ?subject a nwb:Subject ;
                     nwb:species ?species .
        }
        """,
    ]

    for query_str in queries:
        query = prepareQuery(query_str)
        results = list(g.query(query))
        assert len(results) > 0, f"Query returned no results: {query_str}"

def test_round_trip_conversion(nwb_file):
    """Test NWB → RDF → NWB round-trip"""
    # Convert NWB to RDF
    rdf_graph = convert_nwb_to_rdf(nwb_file)

    # Convert RDF back to NWB
    reconstructed_nwb = convert_rdf_to_nwb(rdf_graph)

    # Assert metadata preserved
    original_metadata = extract_metadata(nwb_file)
    reconstructed_metadata = extract_metadata(reconstructed_nwb)

    assert original_metadata == reconstructed_metadata, \
        "Metadata lost in round-trip conversion"
```

### Graph Metrics
```python
def calculate_graph_metrics(rdf_graph: Graph) -> Dict[str, float]:
    """Calculate knowledge graph quality metrics"""
    return {
        "triple_count": len(rdf_graph),
        "entity_count": len(set(rdf_graph.subjects())),
        "property_count": len(set(rdf_graph.predicates())),
        "ontology_linkage": calculate_ontology_linkage(rdf_graph),
        "graph_connectedness": calculate_connectedness(rdf_graph),
        "completeness": calculate_completeness(rdf_graph),
    }
```

### Validation Rules
- ✓ Syntactic correctness: Valid Turtle/N-Triples
- ✓ Semantic consistency: Proper ontology use
- ✓ SPARQL queryable: Example queries succeed
- ✓ Ontology linking: >80% entities linked to standards
- ✓ Metadata coverage: All NWB metadata as triples
- ✓ Relationships preserved: NWB structure maintained
- ✓ Provenance: Complete provenance statements
- ✓ Round-trip: RDF ↔ NWB bidirectional conversion

### Alternatives Considered
- Apache Jena: Java-based, less Python integration
- Protégé: GUI tool, not suitable for automated testing
- SHACL validation: Considered for advanced constraints

---

## 11. Monitoring with OpenTelemetry and Prometheus

### Decision
Implement OpenTelemetry for distributed tracing and Prometheus for metrics collection in Prometheus format (FR-042, FR-045).

### Rationale
- **OpenTelemetry**: Vendor-neutral standard for observability
- **Distributed tracing**: Track requests across MCP server and agents
- **Prometheus metrics**: Industry-standard time-series database
- **Correlation IDs**: Link logs, traces, and metrics (FR-041)
- **Performance analysis**: Historical trends (FR-042)

### Implementation Approach

#### 11.1 OpenTelemetry Tracing
```python
# agentic_neurodata_conversion/utils/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure exporter
otlp_exporter = OTLPSpanExporter(endpoint="localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Usage in code
@tracer.start_as_current_span("convert_dataset")
def convert_dataset(dataset_path: str):
    span = trace.get_current_span()
    span.set_attribute("dataset.path", dataset_path)
    span.set_attribute("dataset.format", "open-ephys")

    try:
        result = perform_conversion(dataset_path)
        span.set_attribute("conversion.status", "success")
        return result
    except Exception as e:
        span.set_attribute("conversion.status", "error")
        span.record_exception(e)
        raise
```

#### 11.2 Prometheus Metrics
```python
# agentic_neurodata_conversion/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

registry = CollectorRegistry()

# Request metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    registry=registry
)

# Conversion metrics
conversion_count = Counter(
    "conversion_jobs_total",
    "Total conversion jobs",
    ["format", "status"],
    registry=registry
)

conversion_duration = Histogram(
    "conversion_duration_seconds",
    "Conversion job duration",
    ["format"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
    registry=registry
)

# Resource metrics
memory_usage = Gauge(
    "process_memory_bytes",
    "Process memory usage in bytes",
    registry=registry
)

# Usage
@app.post("/convert")
async def convert_endpoint(request):
    with request_duration.labels(method="POST", endpoint="/convert").time():
        try:
            result = await convert_dataset(request.data)
            request_count.labels(method="POST", endpoint="/convert", status="200").inc()
            return result
        except Exception as e:
            request_count.labels(method="POST", endpoint="/convert", status="500").inc()
            raise
```

#### 11.3 Structured Logging with Correlation IDs
```python
# agentic_neurodata_conversion/utils/logging.py
import logging
import json
import uuid
from contextvars import ContextVar

# Correlation ID context
correlation_id_var = ContextVar("correlation_id", default=None)

class StructuredLogger(logging.Formatter):
    """JSON structured logging formatter"""

    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields
        if hasattr(record, "custom_fields"):
            log_data.update(record.custom_fields)

        return json.dumps(log_data)

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(StructuredLogger())
logger = logging.getLogger("agentic_neurodata_conversion")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Middleware to set correlation ID
@app.middleware("http")
async def correlation_id_middleware(request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id_var.set(correlation_id)

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

### Monitoring Test Validation
```python
# tests/monitoring/test_observability.py
def test_structured_logging(caplog):
    """Validate structured logging format"""
    logger.info("Test message", extra={"custom_fields": {"user": "test"}})

    log_entry = json.loads(caplog.records[0].message)
    assert "timestamp" in log_entry
    assert "correlation_id" in log_entry
    assert log_entry["level"] == "INFO"

def test_metrics_collection(prometheus_registry):
    """Validate Prometheus metrics"""
    # Trigger conversion
    convert_dataset("test_data")

    # Check metrics
    metrics = prometheus_registry.get_sample_value(
        "conversion_jobs_total",
        {"format": "nwb", "status": "success"}
    )
    assert metrics >= 1

def test_distributed_tracing(trace_exporter):
    """Validate OpenTelemetry traces"""
    with tracer.start_as_current_span("test_operation"):
        perform_conversion("test")

    spans = trace_exporter.get_finished_spans()
    assert len(spans) > 0
    assert spans[0].name == "test_operation"
    assert spans[0].attributes["conversion.status"] == "success"
```

### Alternatives Considered
- Jaeger: Focused on tracing only, OpenTelemetry more comprehensive
- Datadog: Commercial, vendor lock-in
- ELK Stack: More complex setup, Prometheus simpler for metrics

---

## 12. Test Fixture Design Patterns

### Decision
Implement layered fixture architecture with pytest fixtures for environment setup, mock services, test data, and utilities, targeting 70% reduction in test setup code (FR-037).

### Rationale
- **DRY principle**: Reusable test setup across 100+ fixtures
- **Composition**: Fixtures can depend on other fixtures
- **Scoping**: Session, module, function-level fixtures
- **Parametrization**: Generate multiple test scenarios
- **Cleanup**: Automatic teardown with yield fixtures

### Implementation Approach

#### 12.1 Fixture Organization
```
tests/fixtures/
├── __init__.py
├── environment.py      # Test environment setup
├── mock_services.py    # Mock LLM, HTTP, filesystem
├── test_data.py        # Test dataset generators
├── agents.py           # Agent fixtures
├── validation.py       # Validation utilities
└── assertions.py       # Custom assertion helpers
```

#### 12.2 Core Fixtures
```python
# tests/fixtures/environment.py
@pytest.fixture(scope="session")
def test_config():
    """Load test configuration"""
    return {
        "llm_endpoint": "mock://localhost",
        "dataset_path": "tests/data",
        "timeout": 30,
    }

@pytest.fixture(scope="session")
def test_database(tmp_path_factory):
    """Create temporary test database"""
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    initialize_database(db_path)
    yield db_path
    cleanup_database(db_path)

@pytest.fixture(scope="function")
def clean_environment(test_config, test_database):
    """Clean test environment"""
    reset_database(test_database)
    clear_cache()
    yield
    # Cleanup happens automatically after test

# tests/fixtures/mock_services.py
@pytest.fixture
def mock_llm_service():
    """Mock LLM service with deterministic responses"""
    service = MockLLMService({
        "analyze dataset": "Dataset contains 5 channels",
        "generate metadata": '{"subject": "mouse01", "session": "2024-01-01"}',
    })
    yield service
    assert service.verify_all_calls()  # Ensure all expected calls made

@pytest.fixture
def mock_filesystem():
    """In-memory filesystem for testing"""
    fs = MockFilesystem()
    # Pre-populate with test files
    fs.write("test_data.bin", b"binary_data_here")
    yield fs
    fs.cleanup()

# tests/fixtures/test_data.py
@pytest.fixture
def minimal_nwb_file(tmp_path):
    """Generate minimal valid NWB file"""
    from pynwb import NWBFile
    from datetime import datetime

    nwbfile = NWBFile(
        session_description="test session",
        identifier=str(uuid.uuid4()),
        session_start_time=datetime.now(),
    )

    filepath = tmp_path / "minimal.nwb"
    with NWBHDF5IO(filepath, "w") as io:
        io.write(nwbfile)

    yield filepath

@pytest.fixture(params=["open-ephys", "spikeglx", "neuralynx"])
def dataset_format(request):
    """Parametrized fixture for testing multiple formats"""
    return request.param

# tests/fixtures/assertions.py
def assert_nwb_valid(nwbfile):
    """Custom assertion for NWB validity"""
    from pynwb import validate
    errors = validate(nwbfile)
    assert len(errors) == 0, f"NWB validation errors: {errors}"

def assert_metadata_complete(nwbfile, threshold=0.95):
    """Custom assertion for metadata completeness"""
    completeness = calculate_completeness(nwbfile)
    assert completeness >= threshold, \
        f"Metadata completeness {completeness:.1%} below {threshold:.0%}"
```

#### 12.3 Fixture Composition
```python
# tests/integration/test_conversion_workflow.py
@pytest.fixture
def conversion_environment(
    clean_environment,
    mock_llm_service,
    mock_filesystem,
    test_config
):
    """Composite fixture for conversion testing"""
    return {
        "llm": mock_llm_service,
        "fs": mock_filesystem,
        "config": test_config,
    }

def test_full_conversion_workflow(conversion_environment, dataset_format):
    """Test complete conversion with all mocks"""
    env = conversion_environment
    result = convert_dataset(
        format=dataset_format,
        llm_service=env["llm"],
        filesystem=env["fs"],
        config=env["config"]
    )
    assert_nwb_valid(result.nwb_file)
    assert_metadata_complete(result.nwb_file)
```

### Fixture Patterns
- **Factory fixtures**: Return functions that create objects
- **Parametrized fixtures**: Test multiple scenarios
- **Dependent fixtures**: Fixtures that use other fixtures
- **Yield fixtures**: Setup and teardown
- **Scoped fixtures**: Control fixture lifetime
- **Autouse fixtures**: Automatically used by all tests

### Code Reduction Example
```python
# Before (manual setup)
def test_conversion():
    config = load_config("test")
    db = create_database()
    llm = MockLLM()
    fs = MockFS()
    try:
        result = convert(config, db, llm, fs)
        assert result.valid
    finally:
        cleanup_db(db)
        llm.shutdown()
        fs.cleanup()

# After (with fixtures) - 70% less code
def test_conversion(conversion_environment):
    result = convert(**conversion_environment)
    assert_nwb_valid(result)
```

### Alternatives Considered
- unittest setUp/tearDown: Less flexible than pytest fixtures
- Manual setup functions: No automatic cleanup, code duplication
- Test classes with methods: More boilerplate than fixtures

---

## Summary

This research phase has identified and documented technology choices, patterns, and approaches for implementing the comprehensive testing and quality assurance framework:

1. **pytest + pytest-cov**: Primary testing framework with 90%+ coverage target
2. **Hypothesis**: Property-based testing for data transformations and state machines
3. **Mock services**: Layered mocking strategy for 100+ scenarios (LLM, filesystem, network)
4. **DataLad**: Version-controlled test datasets with 15+ format combinations
5. **schemathesis**: Contract testing for 100% OpenAPI specification coverage
6. **pytest-chaos**: Chaos engineering for client resilience testing
7. **pytest-benchmark**: Performance regression detection with baselines
8. **CI/CD optimization**: Test selection, parallel execution, caching for 50% time reduction
9. **NWB Inspector + PyNWB + DANDI**: Validation with >99% pass rate target
10. **rdflib + SPARQL**: Knowledge graph validation with >80% ontology linking
11. **OpenTelemetry + Prometheus**: Distributed tracing and metrics collection
12. **pytest fixtures**: Reusable test utilities reducing setup code by 70%

All technology choices support the 45 functional requirements (FR-001 through FR-045) across 8 major testing areas. The implementation plan can now proceed to Phase 1: Design & Contracts.
