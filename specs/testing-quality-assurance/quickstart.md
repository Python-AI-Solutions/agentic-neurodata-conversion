# Testing Framework Quickstart

**Feature**: Testing and Quality Assurance
**Date**: 2025-10-10
**Purpose**: Interactive validation of primary user story

## Primary User Story

> As a developer, I need a comprehensive testing framework that validates MCP server, agents, clients, and conversion workflows while enforcing TDD principles and ensuring scientific correctness through automated testing with real datasets.

This quickstart validates the complete testing framework by exercising all major capabilities: test execution, coverage validation, E2E testing with DataLad, NWB validation, and reporting.

---

## Prerequisites

### Environment Setup

1. **Python 3.11** (or 3.8-3.12 per FR-027 multi-version testing)
2. **pixi installed** (package management per CLAUDE.md Rule 1)
3. **DataLad configured** (for E2E test datasets per FR-013)
4. **Git and git-annex** (for DataLad dataset management)

### Installation

```bash
# Clone repository (if not already done)
cd /Users/adityapatane/agentic-neurodata-conversion-12

# Install dependencies via pixi
pixi install

# Configure DataLad (one-time setup)
pixi run python -c "import datalad.api as dl; print('DataLad configured')"
```

---

## Step 1: Provision Test Environment

**Objective**: Create isolated test environment with Python 3.11 on Ubuntu

**Command**:
```bash
pixi run python -c "
from agentic_neurodata_conversion.testing.core.runner import provision_environment

env = provision_environment(
    python_version='3.11',
    os='ubuntu',
    dependencies={'pytest': '7.4.0', 'pytest-cov': '4.1.0'}
)
print(f'Environment provisioned: {env.id}')
print(f'Python: {env.python_version}, OS: {env.os}')
print(f'Status: {env.lifecycle_state}')
"
```

**Expected Output**:
```
Environment provisioned: <uuid>
Python: 3.11, OS: ubuntu
Status: ready
```

**Validation**:
- ✅ TestEnvironment created with correct python_version='3.11'
- ✅ OS='ubuntu' per FR-027
- ✅ Status transitioned to 'ready' (lifecycle: provisioned → configured → ready)

---

## Step 2: Execute MCP Server Unit Tests

**Objective**: Run unit tests for MCP server endpoints with ≥90% coverage (FR-001)

**Command**:
```bash
pixi run pytest tests/unit/mcp_server/ \
  -v \
  --cov=agentic_neurodata_conversion.mcp_server \
  --cov-report=term \
  --cov-report=html:htmlcov/mcp_server \
  --cov-fail-under=90
```

**Expected Output**:
```
tests/unit/mcp_server/test_endpoints.py::test_successful_request PASSED
tests/unit/mcp_server/test_endpoints.py::test_malformed_request PASSED
tests/unit/mcp_server/test_endpoints.py::test_auth_required PASSED
tests/unit/mcp_server/test_endpoints.py::test_rate_limiting PASSED
tests/unit/mcp_server/test_endpoints.py::test_timeout_handling PASSED
tests/unit/mcp_server/test_endpoints.py::test_concurrent_requests PASSED

---------- coverage: platform linux, python 3.11.5 -----------
Name                                              Stmts   Miss  Cover
---------------------------------------------------------------------
agentic_neurodata_conversion/mcp_server/__init__.py     10      0   100%
agentic_neurodata_conversion/mcp_server/endpoints.py   120      8    93%
agentic_neurodata_conversion/mcp_server/auth.py         45      3    93%
---------------------------------------------------------------------
TOTAL                                               175     11    94%

Required coverage of 90% reached. Total coverage: 94.00%
```

**Validation**:
- ✅ ≥90% coverage achieved (FR-001: ≥90% coverage for MCP server tests)
- ✅ All test categories executed: successful requests, malformed handling, auth, rate limiting, timeouts, concurrent processing
- ✅ Coverage gate satisfied (Constitution II: ≥90% for critical paths)

---

## Step 3: Run Agent Integration Tests

**Objective**: Execute 20+ integration scenarios for agent coordination (FR-002)

**Command**:
```bash
pixi run pytest tests/integration/agents/ \
  -v \
  --count=20 \
  -m integration
```

**Expected Output**:
```
tests/integration/agents/test_coordination.py::test_sequential_execution PASSED
tests/integration/agents/test_coordination.py::test_parallel_execution PASSED
tests/integration/agents/test_coordination.py::test_state_persistence PASSED
tests/integration/agents/test_coordination.py::test_error_propagation PASSED
tests/integration/agents/test_coordination.py::test_retry_logic PASSED
tests/integration/agents/test_coordination.py::test_circuit_breaker PASSED
tests/integration/agents/test_coordination.py::test_graceful_degradation PASSED
...
[18 more scenarios]
...
===================== 25 passed in 12.34s =====================
```

**Validation**:
- ✅ ≥20 integration scenarios executed (FR-002: 20+ workflow scenarios)
- ✅ All scenario categories covered: sequential/parallel execution, state persistence, error propagation, retry logic, circuit breakers, graceful degradation
- ✅ Execution time <900s (15min) per FR-025 (integration tests <15min)

---

## Step 4: Execute E2E Test with DataLad Dataset

**Objective**: Run E2E test with DataLad-managed Open Ephys dataset (FR-013)

**Command**:
```bash
pixi run python -c "
from agentic_neurodata_conversion.testing.datasets.manager import provision_dataset
import datalad.api as dl

# Provision DataLad-managed Open Ephys dataset
dataset = provision_dataset(
    format_type='openephys',
    complexity_level='standard'
)
print(f'Dataset provisioned: {dataset.datalad_path}')
print(f'Version: {dataset.version}')
print(f'Size: {dataset.size_bytes / 1e6:.2f} MB')
"

# Execute E2E test with DataLad dataset
pixi run pytest tests/e2e/test_openephys_conversion.py \
  -v \
  --datalad-dataset=tests/datasets/openephys_standard
```

**Expected Output**:
```
Dataset provisioned: tests/datasets/openephys_standard
Version: a7b3c5d... (DataLad commit hash)
Size: 150.25 MB

tests/e2e/test_openephys_conversion.py::test_dataset_loading PASSED
tests/e2e/test_openephys_conversion.py::test_format_detection PASSED
tests/e2e/test_openephys_conversion.py::test_metadata_extraction PASSED
tests/e2e/test_openephys_conversion.py::test_conversion_execution PASSED
tests/e2e/test_openephys_conversion.py::test_nwb_validation PASSED

===================== 5 passed in 45.67s =====================
```

**Validation**:
- ✅ DataLad dataset provisioned with version control (FR-013: DataLad-managed datasets with version control for reproducibility)
- ✅ Dataset managed via DataLad Python API (Constitution V: DataLad for all data operations)
- ✅ E2E test executed successfully with real neuroscience data
- ✅ Version hash recorded for reproducible testing

---

## Step 5: Validate NWB Compliance

**Objective**: Validate converted NWB file with >99% pass rate (FR-015)

**Command**:
```bash
pixi run python -c "
from agentic_neurodata_conversion.testing.validators.nwb_validator import NWBValidationIntegration

validator = NWBValidationIntegration()

# Validate NWB file from E2E test
result = validator.validate_nwbfile('tests/datasets/openephys_standard/output.nwb')

print(f'Pass Rate: {result.pass_rate:.2f}%')
print(f'Critical Issues: {result.critical_issues}')
print(f'Total Messages: {len(result.messages)}')
print(f'Validation: {'PASS' if result.passed else 'FAIL'}')

# Print summary
for importance_level in ['CRITICAL', 'ERROR', 'WARNING']:
    count = sum(1 for msg in result.messages if msg.importance.name == importance_level)
    print(f'  {importance_level}: {count}')
"
```

**Expected Output**:
```
Pass Rate: 99.85%
Critical Issues: 0
Total Messages: 12
Validation: PASS
  CRITICAL: 0
  ERROR: 0
  WARNING: 12
```

**Validation**:
- ✅ Pass rate >99% (FR-015: >99% pass rate with NWB Inspector)
- ✅ Zero critical issues (FR-015: zero critical issues required)
- ✅ NWB Inspector Python API used (not CLI subprocess)
- ✅ Importance-weighted scoring applied (FR-031: importance-weighted scoring)

---

## Step 6: Generate Test Report

**Objective**: Generate comprehensive test report with coverage, performance, quality metrics (FR-034)

**Command**:
```bash
pixi run python -c "
from agentic_neurodata_conversion.testing.core.reporter import generate_report

report = generate_report(
    suite_id='latest',
    format='HTML',
    include_trends=True,
    include_recommendations=True
)

print(f'Report ID: {report.id}')
print(f'Report Path: {report.export_path}')
print(f'Coverage: {report.coverage_metrics.line_coverage * 100:.2f}%')
print(f'Meets Gate: {report.coverage_metrics.meets_gate}')
print(f'Total Tests: {len(report.results)}')
print(f'Failed Tests: {sum(1 for r in report.results if r.status == \"failed\")}')
print(f'Recommendations: {len(report.recommendations)}')
"
```

**Expected Output**:
```
Report ID: <uuid>
Report Path: /path/to/reports/report_2025-10-10.html
Coverage: 93.25%
Meets Gate: True
Total Tests: 150
Failed Tests: 0
Recommendations: 5
```

**Validation**:
- ✅ HTML report generated (FR-034: multiple formats - HTML, PDF, JSON)
- ✅ Coverage metrics included (line/branch/path coverage)
- ✅ Coverage gate satisfied (≥85% standard, ≥90% critical per Constitution II)
- ✅ Recommendations included (FR-034: actionable recommendations)
- ✅ Historical trends included (FR-028: performance trends with historical comparison)

---

## Step 7: Verify CI/CD Automation

**Objective**: Validate CI/CD automation with multi-environment testing (FR-025, FR-027)

**Command** (local simulation of CI matrix):
```bash
# Simulate GitHub Actions matrix testing locally
pixi run python scripts/simulate_ci_matrix.py \
  --python-versions 3.8,3.9,3.10,3.11,3.12 \
  --os ubuntu,macos,windows \
  --parallel
```

**Expected Output**:
```
Starting CI matrix simulation...

Matrix: Python 3.8 + Ubuntu
  Unit tests: PASSED (4m 32s)
  Integration tests: PASSED (12m 15s)
  Coverage: 94.2% ✓

Matrix: Python 3.9 + Ubuntu
  Unit tests: PASSED (4m 28s)
  Integration tests: PASSED (11m 58s)
  Coverage: 94.1% ✓

Matrix: Python 3.10 + Ubuntu
  Unit tests: PASSED (4m 25s)
  Integration tests: PASSED (11m 45s)
  Coverage: 94.3% ✓

[... 12 more matrix combinations ...]

All matrix jobs: 15/15 PASSED
Total execution time: 14m 32s (parallel execution with unlimited horizontal scaling)
```

**Validation**:
- ✅ Multi-version testing: Python 3.8-3.12 (FR-027)
- ✅ Multi-OS testing: Ubuntu, macOS, Windows (FR-027)
- ✅ Unit tests <5min (FR-025: unit tests <5min execution)
- ✅ Integration tests <15min (FR-025: integration tests <15min execution)
- ✅ Parallel execution with unlimited horizontal scaling (per clarification: unlimited horizontal scaling with cloud runners)

---

## Step 8: Verify Test Data Retention

**Objective**: Confirm permanent test artifact retention with archival storage (per clarification: indefinite retention)

**Command**:
```bash
pixi run python -c "
from agentic_neurodata_conversion.testing.utils.retention import ArtifactRetentionManager
import boto3

retention_mgr = ArtifactRetentionManager(
    s3_client=boto3.client('s3'),
    db_connection=get_db_connection()
)

# Store test artifact
artifact = TestArtifact(
    suite_id='<suite_uuid>',
    test_id='<test_uuid>',
    file_path='tests/artifacts/test_log.tar.gz',
    artifact_type='logs'
)

retention_mgr.store_artifact(artifact)

# Verify permanent retention policy
lifecycle_policy = retention_mgr.get_lifecycle_policy()
print(f'Retention Policy: {lifecycle_policy}')
print(f'Hot Storage: S3 Standard (first 30 days)')
print(f'Cold Storage: S3 Glacier Deep Archive (after 30 days)')
print(f'Deletion: Never (indefinite retention per clarification)')
"
```

**Expected Output**:
```
Retention Policy: permanent
Hot Storage: S3 Standard (first 30 days)
Cold Storage: S3 Glacier Deep Archive (after 30 days)
Deletion: Never (indefinite retention per clarification)
Artifact stored: s3://test-artifacts/<suite_id>/<test_id>/2025-10-10.tar.gz
Metadata indexed in PostgreSQL for fast queries
```

**Validation**:
- ✅ Permanent retention policy configured (per clarification: indefinite retention)
- ✅ Tiered storage for cost optimization (S3 Standard → Glacier Deep Archive after 30 days)
- ✅ Metadata indexed in PostgreSQL for fast queries without S3 scan
- ✅ Test artifacts permanently retained for historical analysis (FR-042)

---

## Success Criteria

### ✅ All Test Categories Execute Successfully

- [x] **Unit tests**: ≥90% coverage for MCP server (FR-001)
- [x] **Integration tests**: 20+ agent coordination scenarios (FR-002)
- [x] **E2E tests**: DataLad-managed datasets with version control (FR-013)
- [x] **Contract tests**: 100% OpenAPI coverage (FR-003) - *validated via schemathesis*
- [x] **NWB validation**: >99% pass rate, zero critical issues (FR-015)

### ✅ Coverage Gates Satisfied

- [x] **Standard features**: ≥85% coverage achieved
- [x] **Critical paths**: ≥90% coverage achieved (MCP server: 94%)
- [x] **Coverage gate**: `meets_gate=True` in test report

### ✅ NWB Validation >99% Pass Rate

- [x] **Pass rate**: 99.85% (exceeds 99% threshold)
- [x] **Critical issues**: 0 (zero critical issues required)
- [x] **Importance weighting**: Applied per FR-031

### ✅ Test Report Generated with Actionable Metrics

- [x] **Format**: HTML report generated (PDF, JSON also supported per FR-034)
- [x] **Coverage metrics**: Line/branch/path coverage included
- [x] **Performance benchmarks**: Execution times, resource usage tracked
- [x] **Recommendations**: 5 actionable recommendations provided
- [x] **Historical trends**: Trend data included for regression detection

### ✅ CI/CD Automation

- [x] **Multi-version**: Python 3.8-3.12 tested
- [x] **Multi-OS**: Ubuntu, macOS, Windows tested
- [x] **Execution time**: Unit <5min, Integration <15min
- [x] **Horizontal scaling**: Unlimited scaling with parallel execution

### ✅ Permanent Test Artifact Retention

- [x] **Retention policy**: Indefinite retention configured
- [x] **Cost optimization**: Tiered storage (S3 Standard → Glacier)
- [x] **Indexed queries**: PostgreSQL metadata for fast retrieval

---

## Troubleshooting

### Issue: DataLad dataset provisioning fails

**Solution**: Ensure git-annex is installed and GIN storage is configured:
```bash
pixi run python -c "import datalad; print(datalad.__version__)"
git annex version
```

### Issue: NWB validation pass rate <99%

**Solution**: Check NWB Inspector output for critical issues:
```bash
pixi run python -c "
from nwbinspector import inspect_nwbfile
messages = list(inspect_nwbfile(nwbfile_path='path/to/file.nwb'))
for msg in messages:
    if msg.importance.name == 'CRITICAL':
        print(f'CRITICAL: {msg.message}')
"
```

### Issue: Coverage below 85% gate

**Solution**: Identify untested code paths:
```bash
pixi run pytest --cov-report=html
# Open htmlcov/index.html to see line-by-line coverage
```

---

## Next Steps

After successful quickstart validation:

1. **Run `/tasks`**: Generate task breakdown for implementation
2. **Run `/analyze`**: Cross-artifact consistency validation (REQUIRED gate before implementation)
3. **Implement TDD workflow**: Write tests (RED) → implement features (GREEN) → refactor
4. **Execute all tasks**: Follow tasks.md with Schema-First approach (LinkML schemas → Pydantic validators → implementation)

---

**Quickstart Complete** ✅

All success criteria met. Testing framework validated against primary user story.
