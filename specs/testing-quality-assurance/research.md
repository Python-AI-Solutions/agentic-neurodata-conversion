# Testing Framework Research

**Feature**: Testing and Quality Assurance
**Date**: 2025-10-10
**Phase**: 0 (Research & Best Practices)

## Overview

This document consolidates research findings for implementing a comprehensive testing framework that enforces TDD principles (Constitution II), uses Schema-First for test entities (Constitution III), and validates MCP server, agents, clients, and E2E workflows with ≥85% coverage gates.

---

## 1. pytest Advanced Patterns

### Decision
Use pytest plugin architecture with custom hooks, fixtures, and markers for extensibility (FR-041: plugin architectures for custom assertions, test discovery, scheduling).

### Rationale
- **Extensibility**: pytest plugin system allows custom assertion helpers, test discovery mechanisms, result aggregation systems
- **Fixture Factories**: Factory pattern for generating TestFixture instances with different configurations (minimal/edge_case/performance/multimodal)
- **Custom Markers**: @pytest.mark.critical for ≥90% coverage paths, @pytest.mark.mcp for MCP server tests, @pytest.mark.e2e for DataLad-based tests
- **Hook System**: pytest_collection_modifyitems for test selection, pytest_runtest_makereport for custom reporting

### Implementation Approach
```python
# conftest.py plugin
def pytest_configure(config):
    config.addinivalue_line("markers", "critical: mark test as critical path (≥90% coverage)")
    config.addinivalue_line("markers", "mcp: MCP server endpoint test")
    config.addinivalue_line("markers", "e2e: End-to-end test with DataLad datasets")

# Fixture factory pattern
@pytest.fixture
def test_suite_factory():
    def _create_suite(category, coverage_target=0.85):
        return TestSuite(category=category, coverage_target=coverage_target)
    return _create_suite
```

### Alternatives Considered
- **unittest**: Rejected - less flexible, no plugin system, fixture management inferior
- **nose2**: Rejected - deprecated, smaller ecosystem, pytest dominates

### References
- pytest plugin architecture: https://docs.pytest.org/en/stable/how-to/writing_plugins.html
- pytest fixtures: https://docs.pytest.org/en/stable/how-to/fixtures.html

---

## 2. DataLad Python API for Test Datasets

### Decision
Use DataLad Python API (`datalad.api`) exclusively for test dataset management, following Constitution V (Data Integrity & Complete Provenance) and CLAUDE.md rules (no CLI commands).

### Rationale
- **Version Control**: E2E tests require reproducible datasets (FR-013: Open Ephys, SpikeGLX, behavioral tracking with version control)
- **Git-Annex Integration**: Automatic handling of large files >10MB to GIN storage
- **Provenance**: DataLad tracks all dataset operations with provenance metadata
- **Python API**: Programmatic control without subprocess calls to datalad CLI

### Implementation Approach
```python
import datalad.api as dl

class TestDatasetManager:
    def provision_dataset(self, format_type: str, complexity: str) -> TestDataset:
        """Provision DataLad-managed test dataset"""
        # Create dataset with metadata
        dataset_path = f"tests/datasets/{format_type}_{complexity}"
        ds = dl.create(path=dataset_path, description=f"Test dataset: {format_type}")

        # Add test files
        dl.save(dataset=dataset_path, message=f"Add {format_type} test data")

        # Register with git-annex for large files
        if self._get_size(dataset_path) > 10_000_000:  # >10MB
            dl.siblings(action='add', name='gin', url='gin.g-node.org/...')

        return TestDataset(
            format_type=format_type,
            datalad_path=dataset_path,
            version=ds.repo.get_hexsha(),
            complexity_level=complexity
        )
```

### Alternatives Considered
- **Git LFS**: Rejected - DataLad provides better provenance, scientific data focus, git-annex flexibility
- **Manual git-annex**: Rejected - DataLad API simplifies operations, maintains metadata
- **DVC**: Rejected - DataLad better suited for neuroscience data, stronger provenance

### References
- DataLad Python API: https://docs.datalad.org/en/stable/generated/datalad.api.html
- DataLad for reproducible science: http://handbook.datalad.org/en/latest/

---

## 3. Mock Service Patterns

### Decision
Use layered mocking strategy: `pytest-mock` for function mocks, `responses` for HTTP mocking, `time-machine` for time manipulation, `pyfakefs` for in-memory filesystem (FR-009: 100+ mock scenarios).

### Rationale
- **LLM Mock**: Deterministic responses required for reproducible agent tests (FR-009: mock LLM services with deterministic responses)
- **Filesystem Mock**: In-memory filesystem avoids disk I/O in unit tests (FR-009: fake file systems)
- **Network Mock**: Simulate latency, packet loss, timeouts for resilience testing (FR-020: simulated network conditions)
- **Time Mock**: Deterministic time for testing timeouts, retries, scheduling

### Implementation Approach
```python
# Mock LLM service
class MockLLMService:
    def __init__(self, preset_scenario: str):
        self.responses = self._load_scenario(preset_scenario)
        self.call_count = 0

    def complete(self, prompt: str) -> str:
        """Return deterministic response"""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response

# Filesystem mock with pyfakefs
@pytest.fixture
def mock_filesystem(fs):  # fs is pyfakefs fixture
    fs.create_file('/fake/data.nwb', contents='mock NWB data')
    return fs

# Network mock with responses
@responses.activate
def test_api_timeout():
    responses.add(
        responses.GET,
        'https://api.example.com/data',
        body=requests.exceptions.Timeout('Connection timeout')
    )
```

### Alternatives Considered
- **VCR.py**: Considered for HTTP replay, but `responses` more lightweight for simple scenarios
- **Freezegun**: Alternative to `time-machine`, both acceptable, `time-machine` has better async support
- **Manual mocking**: Rejected - test-specific mocks lead to duplication, harder to maintain 100+ scenarios

### References
- pytest-mock: https://pytest-mock.readthedocs.io/
- responses: https://github.com/getsentry/responses
- pyfakefs: https://pytest-pyfakefs.readthedocs.io/
- time-machine: https://github.com/adamchainz/time-machine

---

## 4. Parallel Test Execution at Scale

### Decision
Use `pytest-xdist` for local parallelization + GitHub Actions matrix strategy for unlimited horizontal scaling with cloud runners (per clarification: unlimited horizontal scaling with cloud runners).

### Rationale
- **pytest-xdist**: Distributes tests across multiple CPU cores locally, supports load balancing
- **GitHub Actions Matrix**: Dynamic worker provisioning based on test queue (FR-029: unlimited horizontal scaling)
- **Load Balancing**: pytest-xdist `--dist loadscope` groups tests by module/class to minimize fixture overhead
- **Resource-Aware Scheduling**: GitHub Actions auto-scales runners, pytest-xdist handles per-worker load

### Implementation Approach
```yaml
# .github/workflows/tests.yaml
jobs:
  test:
    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']
        os: [ubuntu-latest, macos-latest, windows-latest]
      fail-fast: false  # Continue all matrix jobs even if one fails
    runs-on: ${{ matrix.os }}
    steps:
      - name: Run tests with pytest-xdist
        run: |
          pixi run pytest -n auto --dist loadscope  # auto = num CPUs

# pytest.ini
[pytest]
addopts = -n auto --dist loadscope --maxfail=1  # Fail fast on first error
```

### Alternatives Considered
- **pytest-parallel**: Rejected - less mature than pytest-xdist, fewer features
- **Jenkins Pipeline**: Rejected - GitHub Actions native, better cloud runner integration
- **Custom test distribution**: Rejected - pytest-xdist handles complexity, battle-tested

### References
- pytest-xdist: https://pytest-xdist.readthedocs.io/
- GitHub Actions matrix: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstrategymatrix

---

## 5. Flaky Test Detection

### Decision
Implement custom pytest plugin for statistical flaky test detection at 5% failure rate threshold with automatic quarantine and retry with exponential backoff (per clarifications: 5% threshold, retry with exponential backoff).

### Rationale
- **5% Threshold**: Clarification specified flag tests failing ≥1 in 20 runs (5%)
- **Statistical Detection**: Track test pass/fail history over last 100 runs, calculate failure rate
- **Quarantine Mechanism**: Move consistently flaky tests to separate quarantine suite
- **Exponential Backoff**: Retry flaky tests 3-5 times with increasing delays (clarification: retry with exponential backoff)

### Implementation Approach
```python
# conftest.py plugin
class FlakyDetectorPlugin:
    def __init__(self):
        self.test_history = self._load_history()  # Last 100 runs per test
        self.flaky_threshold = 0.05  # 5% failure rate

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report):
        if report.when == 'call':
            self.test_history[report.nodeid].append(report.outcome)

            # Calculate failure rate over last 100 runs
            recent_runs = self.test_history[report.nodeid][-100:]
            failure_rate = recent_runs.count('failed') / len(recent_runs)

            if failure_rate >= self.flaky_threshold:
                self._quarantine_test(report.nodeid)
                self._notify_owners(report.nodeid, failure_rate)

    def _quarantine_test(self, nodeid):
        """Move test to quarantine suite"""
        with open('.quarantine.txt', 'a') as f:
            f.write(f"{nodeid}\n")

# Retry with exponential backoff
@pytest.mark.flaky(reruns=5, reruns_delay=1)  # Using pytest-rerunfailures
def test_potentially_flaky():
    pass
```

### Alternatives Considered
- **pytest-flaky**: Considered, but custom plugin provides 5% threshold + quarantine features
- **pytest-rerunfailures**: Used for retry logic, combined with custom detection
- **Manual tracking**: Rejected - automation required for CI/CD integration

### References
- pytest-rerunfailures: https://github.com/pytest-dev/pytest-rerunfailures
- Flaky test patterns: https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html

---

## 6. Contract Testing with OpenAPI

### Decision
Use `schemathesis` for property-based contract testing from OpenAPI specs, achieving 100% OpenAPI coverage (FR-003: 100% OpenAPI coverage with schema validation).

### Rationale
- **Property-Based Testing**: schemathesis generates test cases from OpenAPI schema, explores edge cases automatically
- **Schema Validation**: Validates request/response schemas, required fields, data types, enums, formats
- **100% Coverage**: Automatically tests all endpoints, methods, status codes defined in OpenAPI spec
- **Hypothesis Integration**: Uses Hypothesis for data generation strategies

### Implementation Approach
```python
import schemathesis

# Load OpenAPI schema
schema = schemathesis.from_path("specs/testing-quality-assurance/contracts/test-execution-api.yaml")

@schema.parametrize()
def test_api_contract(case):
    """
    Automatically generated test for all endpoints in OpenAPI spec.
    Tests:
    - Schema validation (FR-003)
    - Required fields (FR-003)
    - Data types (FR-003)
    - Enums and formats (FR-003)
    """
    response = case.call()
    case.validate_response(response)

# Custom checks for domain-specific validation
@schema.parametrize()
@case.hooks.register("after_call")
def check_coverage_target(response, case):
    if case.path == "/test-suites/{suite_id}/execute":
        assert response.json()['coverage_target'] >= 0.85
```

### Alternatives Considered
- **Dredd**: Rejected - Python ecosystem focus, schemathesis better Hypothesis integration
- **openapi-core**: Considered for validation only, schemathesis provides test generation + validation
- **Manual contract tests**: Rejected - 100% coverage requires automation, property-based testing finds edge cases

### References
- schemathesis: https://schemathesis.readthedocs.io/
- OpenAPI contract testing: https://swagger.io/docs/specification/about/

---

## 7. Test Data Retention Architecture

### Decision
Use tiered storage strategy: hot storage (recent 30 days) on S3 Standard, cold storage (>30 days) on S3 Glacier Deep Archive with indexed metadata in PostgreSQL for permanent retention (per clarification: indefinite retention with cost optimization).

### Rationale
- **Indefinite Retention**: Clarification specified permanent retention for maximum traceability
- **Cost Optimization**: Glacier Deep Archive ~$1/TB/month vs S3 Standard ~$23/TB/month
- **Indexed Queries**: PostgreSQL stores metadata (test_id, timestamp, suite, outcome) for fast queries without S3 scan
- **Lifecycle Policies**: S3 automatically transitions objects after 30 days

### Implementation Approach
```python
# Test artifact retention manager
class ArtifactRetentionManager:
    def __init__(self, s3_client, db_connection):
        self.s3 = s3_client
        self.db = db_connection

    def store_artifact(self, artifact: TestArtifact):
        """Store artifact with metadata indexing"""
        # Upload to S3 with lifecycle policy
        s3_key = f"artifacts/{artifact.suite_id}/{artifact.test_id}/{artifact.timestamp}.tar.gz"
        self.s3.upload_file(
            artifact.file_path,
            bucket='test-artifacts',
            key=s3_key,
            ExtraArgs={'StorageClass': 'STANDARD'}  # Will transition to GLACIER_DA after 30d
        )

        # Index metadata in PostgreSQL
        self.db.execute("""
            INSERT INTO test_artifacts (test_id, suite_id, timestamp, s3_key, size_bytes, artifact_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (artifact.test_id, artifact.suite_id, artifact.timestamp, s3_key, artifact.size, artifact.type))

    def query_artifacts(self, filters: Dict) -> List[TestArtifact]:
        """Query artifacts using indexed metadata"""
        results = self.db.execute("SELECT s3_key FROM test_artifacts WHERE ...")
        # Retrieve from S3 only for matched results
        return [self._fetch_from_s3(row['s3_key']) for row in results]

# S3 lifecycle policy (applied via Terraform/CloudFormation)
lifecycle_rules:
  - id: transition-to-glacier
    transitions:
      - days: 30
        storage_class: GLACIER_DEEP_ARCHIVE
```

### Alternatives Considered
- **Local disk storage**: Rejected - not scalable, no cost optimization, infrastructure burden
- **S3 Standard only**: Rejected - expensive for indefinite retention (~$23/TB/month)
- **Delete after retention period**: Rejected - clarification specified indefinite retention
- **Azure Blob Archive**: Alternative, comparable pricing, S3 chosen for ecosystem maturity

### References
- S3 Glacier pricing: https://aws.amazon.com/s3/pricing/
- S3 Lifecycle policies: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html

---

## 8. NWB Validation Integration

### Decision
Integrate `nwbinspector` Python API with custom importance-weighted scoring for >99% pass rate validation (FR-015: >99% pass rate with NWB Inspector, FR-031: importance-weighted scoring).

### Rationale
- **Python API**: Programmatic validation without subprocess calls to nwbinspector CLI
- **Importance Weighting**: Critical issues (e.g., missing required fields) weighted higher than warnings
- **Zero Critical Issues**: FR-015 requires zero critical issues, importance weighting enforces this
- **Custom Rules**: FR-031 allows custom validation rules for lab standards

### Implementation Approach
```python
from nwbinspector import inspect_nwbfile, Importance

class NWBValidationIntegration:
    def __init__(self):
        self.critical_weight = 10.0  # Critical issues block pass
        self.warning_weight = 1.0
        self.pass_threshold = 99.0  # >99% pass rate

    def validate_nwbfile(self, nwbfile_path: str) -> ValidationResult:
        """Validate NWB file with importance-weighted scoring"""
        # Run NWB Inspector
        messages = list(inspect_nwbfile(nwbfile_path=nwbfile_path))

        # Calculate importance-weighted score
        total_weight = 0
        failed_weight = 0
        critical_count = 0

        for msg in messages:
            if msg.importance == Importance.CRITICAL:
                failed_weight += self.critical_weight
                critical_count += 1
            elif msg.importance == Importance.ERROR:
                failed_weight += self.warning_weight
            total_weight += self.critical_weight if msg.importance == Importance.CRITICAL else self.warning_weight

        pass_rate = 100 * (1 - failed_weight / total_weight) if total_weight > 0 else 100.0

        # FR-015: Zero critical issues + >99% pass rate
        passed = (critical_count == 0) and (pass_rate > self.pass_threshold)

        return ValidationResult(
            passed=passed,
            pass_rate=pass_rate,
            critical_issues=critical_count,
            messages=messages
        )
```

### Alternatives Considered
- **PyNWB validation only**: Insufficient - FR-015 requires NWB Inspector for comprehensive validation
- **CLI subprocess calls**: Rejected - Python API preferred per CLAUDE.md, better error handling
- **DANDI validation**: Complementary (FR-031), not replacement for NWB Inspector

### References
- nwbinspector: https://nwbinspector.readthedocs.io/
- NWB Best Practices: https://www.nwb.org/best-practices/

---

## Summary

All research areas resolved with specific decisions, rationale, and implementation approaches:

1. ✅ **pytest Advanced Patterns**: Plugin architecture, fixture factories, custom markers
2. ✅ **DataLad Python API**: `datalad.api` for test datasets with git-annex/GIN storage
3. ✅ **Mock Service Patterns**: Layered mocking (pytest-mock, responses, pyfakefs, time-machine)
4. ✅ **Parallel Execution**: pytest-xdist + GitHub Actions matrix for unlimited horizontal scaling
5. ✅ **Flaky Test Detection**: Custom plugin with 5% threshold, quarantine, exponential backoff retry
6. ✅ **Contract Testing**: schemathesis for 100% OpenAPI coverage with property-based testing
7. ✅ **Test Data Retention**: Tiered S3 storage (Standard → Glacier Deep Archive) with PostgreSQL indexing
8. ✅ **NWB Validation**: nwbinspector Python API with importance-weighted scoring for >99% pass rate

**No NEEDS CLARIFICATION items remain.** All technical unknowns resolved with concrete implementation paths.

---
*Research Phase Complete - Ready for Phase 1 (Design & Contracts)*
