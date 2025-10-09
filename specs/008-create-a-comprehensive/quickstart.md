# Testing and Quality Assurance Framework - Quickstart Guide

## Overview
This guide provides step-by-step instructions to set up the testing environment and run tests for the agentic neurodata conversion system. Follow these steps to execute unit tests, integration tests, end-to-end tests, and generate comprehensive reports.

## Prerequisites
- Python 3.12+ installed
- pixi package manager installed
- Git installed
- 8GB+ RAM recommended
- 20GB+ free disk space for test datasets

## Quick Setup (5 minutes)

### 1. Clone Repository and Install Dependencies
```bash
# Navigate to project directory
cd /path/to/agentic-neurodata-conversion-2

# Install dependencies using pixi
pixi install

# Activate pixi environment
pixi shell

# Verify installation
pytest --version  # Should be 7.4+
python --version  # Should be 3.12+
```

### 2. Configure Test Environment
```bash
# Copy example environment configuration
cp .env.example .env.test

# Edit test configuration (optional)
# Set TEST_DATA_PATH, LLM_ENDPOINT (mock), etc.
```

### 3. Install Test Dataset (DataLad)
```bash
# Install minimal test datasets for quick tests
datalad install -s https://gin.g-node.org/test/minimal-ephys tests/data/minimal-ephys

# Fetch specific test files (on-demand)
cd tests/data/minimal-ephys
datalad get recording_001.continuous
cd ../../..
```

---

## Running Tests

### Unit Tests (Target: <5 minutes, 90%+ coverage)

**Quick Run** (recommended for development):
```bash
# Run all unit tests with coverage
pytest tests/unit -v --cov=agentic_neurodata_conversion --cov-report=term-missing

# Expected output:
# ===== test session starts =====
# tests/unit/test_agents.py::test_agent_initialization PASSED
# tests/unit/test_conversion.py::test_format_detection PASSED
# ...
# Coverage: 92%
# ===== 150 passed in 3.45s =====
```

**Parallel Execution** (faster):
```bash
# Use all CPU cores
pytest tests/unit -n auto --cov

# Expected time: <2 minutes
```

**Specific Component**:
```bash
# Test only MCP server
pytest tests/unit/mcp_server -v

# Test only agents
pytest tests/unit/agents -v

# Test specific file
pytest tests/unit/test_conversion.py::test_nwb_export -v
```

**Coverage Report**:
```bash
# Generate HTML coverage report
pytest tests/unit --cov --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**Expected Results**:
- ✓ 150+ unit tests pass
- ✓ Execution time <5 minutes
- ✓ Code coverage >90% for MCP server endpoints (FR-001)
- ✓ Code coverage >85% for agent core functionality (FR-007)
- ✓ Zero critical failures

---

### Integration Tests (Target: <15 minutes, 20+ scenarios)

**Full Integration Suite**:
```bash
# Run all integration tests
pytest tests/integration -v --maxfail=3

# Expected output:
# tests/integration/test_agent_orchestration.py::test_sequential_workflow PASSED
# tests/integration/test_mcp_server_integration.py::test_conversion_workflow PASSED
# ...
# ===== 45 passed in 12.34s =====
```

**Agent Orchestration Tests**:
```bash
# Test agent coordination (FR-002)
pytest tests/integration/test_agent_orchestration.py -v

# Includes 20+ workflow scenarios:
# - Sequential workflow execution
# - Parallel agent invocation
# - Dependency management
# - State persistence
# - Error propagation
# - Retry logic with exponential backoff
# - Circuit breaker activation
# - Graceful degradation
```

**Contract Testing**:
```bash
# Test API contracts (FR-003)
pytest tests/contract -v --schemathesis

# Validates:
# - OpenAPI specification compliance (100% coverage)
# - Request/response schemas
# - Required fields, data types, enums
# - Pagination consistency
```

**Mock Service Testing**:
```bash
# Test with mock services (FR-009, FR-020)
pytest tests/integration --with-mocks -v

# Uses 100+ mock scenarios:
# - Mock LLM services
# - Mock filesystem
# - Mock HTTP servers
# - Network condition simulation
```

**Expected Results**:
- ✓ 40+ integration tests pass
- ✓ Execution time <15 minutes
- ✓ 20+ workflow scenarios validated (FR-002)
- ✓ 100% OpenAPI specification coverage (FR-003)
- ✓ All mock scenarios tested

---

### End-to-End Tests (DataLad datasets, up to 1TB workflows)

**Quick E2E Test** (minimal dataset):
```bash
# Run E2E test with minimal dataset (<10MB)
pytest tests/e2e/test_conversion_pipeline.py::test_minimal_dataset -v

# Expected time: ~2 minutes
```

**Full E2E Suite** (requires datasets):
```bash
# Fetch required test datasets
./scripts/fetch_test_datasets.sh

# Run full E2E tests
pytest tests/e2e -v --slow

# Includes:
# - Open Ephys multichannel recordings
# - SpikeGLX with different probe configurations
# - Neuralynx with video synchronization
# - Calcium imaging (Suite2p, CaImAn)
# - Behavioral tracking (DeepLabCut, SLEAP)
# - Multimodal recordings
# - Corrupted/incomplete datasets
# - Legacy format migrations

# Expected time: 20-30 minutes
```

**Conversion Quality Validation** (FR-015):
```bash
# Run conversion with NWB validation
pytest tests/e2e/test_nwb_validation.py -v

# Validates:
# ✓ NWB Inspector: zero critical issues
# ✓ PyNWB schema compliance
# ✓ Data integrity (checksum verification)
# ✓ Temporal alignment (<1ms drift)
# ✓ Metadata completeness (>95%)
# ✓ Spatial registration accuracy
# ✓ Signal fidelity preservation
```

**Performance Benchmarking** (FR-018):
```bash
# Run performance benchmarks
pytest tests/e2e/test_performance.py --benchmark-only

# Measures:
# - Conversion speed (MB/sec by format)
# - Memory usage (peak and average)
# - Disk I/O patterns
# - CPU utilization
# - Parallel scaling efficiency
```

**Expected Results**:
- ✓ 15+ format combinations tested (FR-014)
- ✓ NWB files pass Inspector validation with zero critical issues
- ✓ >95% metadata completeness achieved
- ✓ <1ms temporal alignment drift maintained
- ✓ >99% pass rate for valid input data (FR-031)

---

### Client Library Tests (Python 3.8-3.12, cross-platform)

**Unit Tests for Clients** (FR-019):
```bash
# Run client library unit tests
pytest tests/client/unit -v --cov=agentic_neurodata_conversion.client

# Expected coverage: >85%
```

**Integration Tests with Mock Servers** (FR-020):
```bash
# Test with mock HTTP servers (50+ scenarios)
pytest tests/client/integration -v

# Includes:
# - Network simulation (latency, packet loss)
# - Error injection (500, 503, timeout)
# - Rate limiting
# - Authentication/authorization mocks
# - WebSocket mocks
# - Protocol version mismatches
```

**Cross-Platform Tests**:
```bash
# Test across Python versions (requires tox)
tox -e py38,py39,py310,py311,py312

# Test across OS platforms (CI/CD handles this)
# GitHub Actions matrix: Ubuntu, macOS, Windows
```

**Chaos Engineering Tests** (FR-023):
```bash
# Run chaos engineering resilience tests
pytest tests/client/chaos -v --chaos

# Tests:
# - Network failures
# - Server maintenance windows
# - Connection pool exhaustion
# - Memory pressure
# - Concurrent request limits
```

**Expected Results**:
- ✓ 85%+ code coverage achieved
- ✓ 50+ error scenarios handled gracefully (FR-021)
- ✓ Chaos tests pass (circuit breakers, fallbacks work)
- ✓ Compatible with Python 3.8-3.12
- ✓ Cross-platform compatibility verified

---

## Generating Reports

### Coverage Reports (FR-028)

**HTML Coverage Report**:
```bash
# Generate interactive HTML report
pytest --cov --cov-report=html

# View report
open htmlcov/index.html
```

**JSON Coverage Report** (for APIs):
```bash
# Generate JSON report
pytest --cov --cov-report=json

# Output: coverage.json
cat coverage.json | jq '.totals'
```

**Coverage by Module**:
```bash
# Show coverage breakdown
pytest --cov --cov-report=term-missing

# Expected output:
# Name                                     Stmts   Miss  Cover
# ------------------------------------------------------------
# agentic_neurodata_conversion/mcp_server    234     12    95%
# agentic_neurodata_conversion/agents        456     45    90%
# agentic_neurodata_conversion/client        189     15    92%
# ------------------------------------------------------------
# TOTAL                                      879     72    92%
```

---

### Quality Reports (FR-028)

**Code Quality Metrics**:
```bash
# Run code quality analysis
ruff check . --output-format=json > quality_report.json

# Check cyclomatic complexity
radon cc agentic_neurodata_conversion -a -nb

# Check code duplication
radon raw agentic_neurodata_conversion -s
```

**Security Scan**:
```bash
# Run security scan (OWASP compliance)
bandit -r agentic_neurodata_conversion -f json -o security_report.json

# Check dependency vulnerabilities
safety check --json > dependency_vulnerabilities.json
```

---

### Evaluation Reports (FR-034)

**NWB File Evaluation**:
```bash
# Run NWB validation and generate evaluation report
pytest tests/validation/test_nwb_evaluation.py -v \
  --nwb-file=output.nwb \
  --report-format=all

# Generates:
# - evaluation_report.html (interactive)
# - evaluation_report.pdf (printable)
# - evaluation_report.json (machine-readable)
```

**Report Contents**:
- ✓ Validation results (NWB Inspector, PyNWB, DANDI)
- ✓ Quality scores with importance weighting
- ✓ Metadata completeness assessment
- ✓ Scientific accuracy verification
- ✓ Compliance certificates (FAIR, BIDS, DANDI)
- ✓ Benchmark comparisons
- ✓ Actionable recommendations with priority scores
- ✓ Visualizations (charts, graphs)
- ✓ Systematic issue identification
- ✓ Code examples for fixes

**View Evaluation Report**:
```bash
# Open HTML report
open evaluation_report.html
```

---

### Performance Reports (FR-012, FR-018, FR-024)

**Run Performance Benchmarks**:
```bash
# Benchmark all components
pytest tests/performance --benchmark-only --benchmark-json=perf_report.json

# View results
pytest-benchmark compare perf_report.json
```

**Generate Flame Graph**:
```bash
# Profile code execution
py-spy record -o flamegraph.svg -- pytest tests/e2e/test_conversion.py

# View flame graph
open flamegraph.svg
```

**Performance Dashboard**:
```bash
# Generate performance dashboard
python scripts/generate_performance_dashboard.py \
  --input=perf_report.json \
  --output=performance_dashboard.html

# Opens interactive dashboard with:
# - Benchmark trends over time
# - Regression detection
# - Bottleneck analysis
# - Resource utilization
```

---

## CI/CD Integration (FR-025)

### Local Pre-Commit Checks

**Install Pre-Commit Hooks**:
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files

# Checks include:
# - Code formatting (ruff)
# - Type checking (mypy)
# - Security scan (bandit)
# - Test execution (pytest --quick)
```

### GitHub Actions Workflow

**Trigger Tests**:
```bash
# Push to branch (auto-triggers CI)
git push origin feature-branch

# CI runs:
# 1. Unit tests (<5 min) ✓
# 2. Integration tests (<15 min) ✓
# 3. Code quality checks ✓
# 4. Security scanning ✓
# 5. Documentation generation ✓

# Matrix testing:
# - Python 3.8, 3.9, 3.10, 3.11, 3.12
# - Ubuntu, macOS, Windows
```

**View CI Results**:
- GitHub Actions tab shows test results
- Coverage reports uploaded to Codecov
- Performance benchmarks stored as artifacts

---

## Troubleshooting

### Common Issues

**1. Tests Failing Due to Missing Dependencies**:
```bash
# Reinstall dependencies
pixi install --force
pixi shell
```

**2. DataLad Dataset Not Found**:
```bash
# Check dataset status
datalad status tests/data/minimal-ephys

# Re-fetch dataset
datalad get tests/data/minimal-ephys/*
```

**3. Coverage Below Threshold**:
```bash
# Check which files need more coverage
pytest --cov --cov-report=term-missing | grep "TOTAL"

# Focus on uncovered lines
pytest --cov --cov-report=html
# Open htmlcov/index.html to see uncovered lines highlighted
```

**4. Slow Test Execution**:
```bash
# Use parallel execution
pytest -n auto

# Skip slow tests during development
pytest -m "not slow"

# Run only failed tests from last run
pytest --lf
```

**5. Flaky Tests**:
```bash
# Identify flaky tests
pytest --count=10 tests/integration

# Run with retries
pytest --reruns 3 --reruns-delay 1
```

---

## Quick Reference

### Test Commands by Target

| Target | Command | Time | Coverage |
|--------|---------|------|----------|
| Unit tests | `pytest tests/unit -n auto --cov` | <5 min | >90% |
| Integration tests | `pytest tests/integration -v` | <15 min | 20+ scenarios |
| E2E tests (minimal) | `pytest tests/e2e -k minimal -v` | ~2 min | Smoke test |
| E2E tests (full) | `pytest tests/e2e -v --slow` | 20-30 min | 15+ formats |
| Client tests | `pytest tests/client -v --cov` | <10 min | >85% |
| Performance tests | `pytest tests/performance --benchmark-only` | 10-15 min | Benchmarks |
| All tests | `pytest tests -v` | 30-45 min | Full suite |

### Coverage Targets

| Component | Target | Requirement |
|-----------|--------|-------------|
| MCP Server | 90%+ | FR-001 |
| Agents | 85%+ | FR-007 |
| Client Libraries | 85%+ | FR-019 |
| Utilities | 80%+ | Best practice |
| Critical Paths | 100% | Auth, data integrity |

### Report Generation

| Report Type | Command | Output |
|-------------|---------|--------|
| Coverage | `pytest --cov-report=html` | htmlcov/index.html |
| Quality | `ruff check --output-format=json` | quality_report.json |
| Security | `bandit -r . -f json` | security_report.json |
| Evaluation | `pytest tests/validation --report-format=all` | evaluation_report.html/pdf/json |
| Performance | `pytest-benchmark compare` | Terminal output |

---

## Next Steps

After running tests:

1. **Review Coverage Reports**: Identify gaps and add tests
2. **Fix Failed Tests**: Address failures before committing
3. **Check Quality Reports**: Address code quality issues
4. **Review Evaluation Reports**: Ensure NWB files meet quality standards
5. **Monitor Performance**: Check for regressions in benchmarks
6. **Update Documentation**: Document any test changes

## Support

For issues:
- Check [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines
- Review test logs in `.pytest_cache/`
- Contact team via issue tracker
- Review detailed test documentation in `/docs/testing/`

---

**Last Updated**: 2025-10-07
**Version**: 1.0.0
