# Testing and Quality Assurance Framework - Research

**Feature**: 005-testing-quality-assurance **Date**: 2025-10-03 **Status**:
Complete

This document consolidates research findings for building a comprehensive
testing and quality assurance framework for the agentic neurodata conversion
system.

## 1. Testing Framework Decision

### Decision

Use **pytest** as the primary testing framework with its rich ecosystem of
plugins.

### Rationale

- **Industry Standard**: pytest is the de facto standard for Python testing with
  extensive community support
- **Plugin Ecosystem**: Rich plugin architecture (pytest-asyncio, pytest-cov,
  pytest-mock, pytest-xdist, pytest-benchmark)
- **Fixture System**: Powerful dependency injection through fixtures enables
  reusable test infrastructure
- **Parametrization**: Built-in support for parameterized tests reduces code
  duplication
- **Async Support**: Native async/await support via pytest-asyncio for testing
  MCP server endpoints
- **Markers**: Custom markers enable flexible test categorization and selective
  execution
- **Integration**: Seamless integration with coverage.py, hypothesis, and CI/CD
  systems

### Alternatives Considered

- **unittest**: Python's built-in framework, but verbose and lacks pytest's
  fixture system
- **nose2**: Declining community support, less active development
- **Custom test runner**: Unnecessary complexity, reinventing the wheel

## 2. Mock Strategy

### Decision

Use **pytest-mock** for general mocking, **responses** for HTTP mocking, and
**pyfakefs** for filesystem mocking.

### Rationale

- **pytest-mock**: Provides pytest-friendly wrapper around unittest.mock with
  fixture integration
- **responses**: Clean API for mocking HTTP requests/responses, ideal for
  testing external API calls
- **pyfakefs**: Creates fake filesystem in memory, perfect for testing file
  operations without disk I/O
- **Separation of Concerns**: Different tools for different mocking needs
  ensures appropriate abstraction levels
- **Test Isolation**: Mocks prevent tests from affecting real systems (Knowledge
  Graph, DataLad, file systems)

### Alternatives Considered

- **unittest.mock only**: Works but less pytest-idiomatic, no fixture
  integration
- **httpx mock**: Alternative to responses, but responses has cleaner API for
  our use case
- **Real filesystem**: Slower, creates test artifacts, potential conflicts
  between parallel tests

## 3. DataLad Integration Approach

### Decision

Use **lightweight test datasets** with **DataLad fixtures** and **result
caching** for integration tests.

### Rationale

- **Speed**: Small datasets (< 100MB) enable fast test execution
- **Realism**: Real DataLad operations without production-scale data
- **Caching**: Cache DataLad get/clone operations to reduce network calls
- **Isolation**: Each test gets clean dataset state through fixtures
- **Coverage**: Multiple dataset formats ensure comprehensive testing

### Implementation Strategy

- Create `tests/fixtures/datasets/` with curated test datasets
- Use pytest fixtures to initialize DataLad datasets
- Implement caching mechanism for dataset retrieval
- Provide both real DataLad tests and mocked versions for unit tests

### Alternatives Considered

- **Mock DataLad entirely**: Loses integration testing value, misses
  DataLad-specific edge cases
- **Production datasets**: Too large, slow tests, requires significant storage
- **Synthetic non-DataLad data**: Doesn't test real DataLad workflows

## 4. CI/CD Platform

### Decision

Use **GitHub Actions** with matrix testing across Python versions and operating
systems.

### Rationale

- **Native Integration**: First-class GitHub integration, no external services
- **Free for Open Source**: Generous free tier for public repositories
- **Matrix Testing**: Built-in support for testing across Python 3.12, 3.13,
  Linux/Windows/macOS
- **Caching**: Action caching for dependencies reduces setup time
- **Parallel Execution**: Run independent test suites in parallel
- **Ecosystem**: Rich marketplace of actions for coverage reporting, artifact
  upload, etc.

### Workflow Structure

- **test-unit.yml**: Fast unit tests on every push (<5 minutes)
- **test-integration.yml**: Integration tests on PR and main (<15 minutes)
- **test-e2e.yml**: End-to-end tests on PR to main only (<30 minutes)
- **quality-gates.yml**: Combined quality checks (coverage, linting, type
  checking)

### Alternatives Considered

- **GitLab CI**: Requires GitLab platform migration
- **Circle CI**: Requires external service, less GitHub integration
- **Jenkins**: Self-hosted complexity, maintenance burden

## 5. Coverage Tools

### Decision

Use **pytest-cov** (wrapper around coverage.py) with HTML, XML, and terminal
reporting.

### Rationale

- **pytest Integration**: Seamless integration with pytest, no separate tool
  invocation
- **Multiple Formats**: HTML for local viewing, XML for CI reporting, terminal
  for quick feedback
- **Branch Coverage**: Tracks both line and branch coverage
- **Threshold Enforcement**: Can fail builds if coverage drops below threshold
  (80%)
- **Incremental Coverage**: Track coverage changes per PR
- **Exclusion Patterns**: Exclude test files, migrations, generated code from
  coverage

### Configuration

```ini
# pytest.ini
[pytest]
addopts = --cov=agentic_neurodata_conversion --cov-report=html --cov-report=xml --cov-report=term-missing

# .coveragerc
[run]
branch = True
omit = tests/*, */migrations/*, */generated/*

[report]
precision = 2
fail_under = 80
```

### Alternatives Considered

- **coverage.py directly**: Less pytest integration, requires separate
  invocation
- **Different threshold**: 80% balances thoroughness with practicality
- **No branch coverage**: Line coverage alone misses untested code paths

## 6. Performance Testing

### Decision

Use **pytest-benchmark** for micro-benchmarks and **custom timing utilities**
for macro-benchmarks.

### Rationale

- **pytest-benchmark**: Precise timing, statistical analysis, regression
  detection for function-level performance
- **Baseline Tracking**: Store baseline performance metrics, detect regressions
  automatically
- **Warmup/Calibration**: Handles warmup runs and timing calibration
  automatically
- **Custom Utilities**: For end-to-end workflow timing where pytest-benchmark is
  too granular
- **Markers**: Use `@pytest.mark.benchmark` to separate performance tests from
  functional tests

### Performance Test Categories

1. **Unit Performance**: Individual function timing (e.g., metadata extraction <
   100ms)
2. **Integration Performance**: Agent workflow timing (e.g., full conversion <
   30s)
3. **Throughput Testing**: Requests per second for MCP endpoints
4. **Memory Profiling**: Memory usage for large dataset processing

### Alternatives Considered

- **Manual timing**: Inconsistent, no statistical analysis
- **locust/k6**: Overkill for internal library, designed for web load testing
- **timeit**: Less pytest integration, manual baseline management

## 7. NWB Validation Tools

### Decision

Use **multi-layer validation strategy**: pynwb validation → nwbinspector →
dandi-cli → custom rules.

### Rationale

- **pynwb Validation**: Schema conformance, required fields, data types
- **nwbinspector**: Best practices, scientific validity, metadata quality
- **dandi-cli**: DANDI archive compliance for publishable datasets
- **Custom Rules**: Domain-specific validation beyond standard tools
- **Layered Approach**: Each tool catches different classes of issues

### Validation Layers

1. **Layer 1 - Schema**: pynwb schema validation (pass/fail)
2. **Layer 2 - Best Practices**: nwbinspector checks (warnings allowed)
3. **Layer 3 - Archive Compliance**: dandi-cli validation (for publishable
   datasets)
4. **Layer 4 - Custom**: Domain-specific rules (e.g., ephys sample rate > 20kHz)

### Implementation

```python
# Validation pipeline
def validate_nwb_file(nwb_path: Path) -> ValidationReport:
    results = ValidationReport()

    # Layer 1: Schema
    results.schema = validate_schema_pynwb(nwb_path)

    # Layer 2: Best practices
    results.best_practices = validate_nwbinspector(nwb_path)

    # Layer 3: DANDI (optional)
    if publishable:
        results.dandi = validate_dandi_cli(nwb_path)

    # Layer 4: Custom
    results.custom = validate_custom_rules(nwb_path)

    return results
```

### Alternatives Considered

- **Single validator**: Misses different categories of issues
- **Schema only**: Allows scientifically invalid but schema-compliant files
- **No custom rules**: Can't enforce domain-specific requirements

## 8. Property-Based Testing

### Decision

Use **hypothesis** for property-based testing of agent behaviors and invariants.

### Rationale

- **Exhaustive Testing**: Generates hundreds of test cases automatically
- **Shrinking**: Automatically minimizes failing test cases to simplest
  reproduction
- **Strategies**: Rich library of data generators (text, numbers, structures)
- **Custom Strategies**: Can define domain-specific generators (e.g., valid NWB
  metadata)
- **Regression Detection**: Finds edge cases unit tests miss

### Application Areas

1. **Agent State Machines**: Verify state transition invariants hold for all
   input sequences
2. **Metadata Parsing**: Test parsers with fuzzed but structurally valid inputs
3. **Serialization**: Verify round-trip property (deserialize(serialize(x)) ==
   x)
4. **Error Handling**: Verify agents gracefully handle arbitrary invalid inputs

### Example Usage

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=1000))
def test_metadata_parser_never_crashes(text):
    # Property: Parser should never crash, even on invalid input
    result = parse_metadata(text)
    assert result is not None or result.error is not None

@given(st.lists(st.sampled_from(AgentState)))
def test_agent_state_invariant(state_sequence):
    # Property: Agent should always return to idle after completion
    agent = TestAgent()
    for state in state_sequence:
        agent.transition_to(state)
    agent.complete()
    assert agent.state == AgentState.IDLE
```

### Alternatives Considered

- **Manual edge case testing**: Time-consuming, likely misses cases
- **Fuzzing tools**: Less Python-idiomatic, harder integration with pytest
- **No property testing**: Functional tests only, less thorough

## 9. Mock Service Architecture

### Decision

Implement **mock service hierarchy** with **fixture-based injection** and
**behavior recording**.

### Mock Service Types

1. **Knowledge Graph Mock**: In-memory RDF graph with SPARQL query support
2. **DataLad Mock**: Simulated dataset operations with configurable responses
3. **Filesystem Mock**: pyfakefs-based file system simulation
4. **HTTP Mock**: responses-based external API mocking

### Design Principles

- **Fixture Injection**: Mocks injected via pytest fixtures for clean teardown
- **Behavior Recording**: Mocks record calls for verification
- **Configurable Responses**: Fixtures parameterized for different scenarios
- **Failure Simulation**: Mocks can simulate network errors, timeouts, invalid
  data

### Example Structure

```python
@pytest.fixture
def mock_knowledge_graph():
    """Provides in-memory RDF graph mock."""
    graph = MockKnowledgeGraph()
    graph.load_test_data("minimal_ontology.ttl")
    yield graph
    graph.clear()

@pytest.fixture
def mock_datalad():
    """Provides DataLad operation mock."""
    mock = MockDataLad()
    mock.configure_dataset_response("test-dataset", status="available")
    yield mock
    mock.verify_expectations()
```

## 10. Test Organization Strategy

### Decision

Organize tests by **component type** with **shared conftest.py** for fixtures.

### Directory Structure

```
tests/
├── conftest.py                 # Root fixtures (mocks, test data)
├── mcp_server/                 # MCP endpoint tests
│   ├── conftest.py            # MCP-specific fixtures
│   └── test_*.py
├── agents/                     # Agent unit tests
│   ├── conftest.py            # Agent fixtures
│   └── test_*.py
├── e2e/                        # End-to-end workflows
│   ├── conftest.py            # E2E fixtures
│   └── test_*.py
├── clients/                    # Client library tests
│   ├── python/
│   └── typescript/
└── validation/                 # NWB validation tests
    └── test_*.py
```

### Fixture Scoping Strategy

- **session**: Database connections, test datasets (slow setup, shared across
  tests)
- **module**: Mock services (medium setup, shared within file)
- **function**: Test-specific data (fast setup, isolated per test)

### Alternatives Considered

- **Flat structure**: Becomes unwieldy with 50+ test files
- **Feature-based**: Harder to run all tests of one type
- **Single conftest**: Becomes bloated, slow imports

## 11. Flaky Test Handling

### Decision

Implement **automatic retry with quarantine** for flaky tests.

### Strategy

1. **Detection**: Track test history, flag tests with inconsistent results
2. **Retry**: pytest-rerunfailures auto-retry flaky tests up to 3 times
3. **Quarantine**: Separate flaky tests into `@pytest.mark.flaky` for
   investigation
4. **Root Cause**: Investigate timing issues, race conditions, environmental
   dependencies
5. **Fix or Remove**: Either fix root cause or remove test if unfixable

### Configuration

```ini
# pytest.ini
[pytest]
markers =
    flaky: marks tests as flaky (retried up to 3 times)

addopts = --reruns 3 --reruns-delay 1
```

### Monitoring

- CI reports flaky test statistics
- Alert on new flaky tests
- Weekly review of quarantined tests

### Alternatives Considered

- **Ignore failures**: Undermines test suite reliability
- **No retry**: False negatives from timing issues
- **Always retry**: Masks real failures

## Summary

The testing framework combines:

- **pytest ecosystem** for comprehensive, maintainable test infrastructure
- **Multi-layer mocking** for isolated, fast unit tests
- **Real DataLad integration** with lightweight test datasets
- **GitHub Actions** for automated CI/CD with matrix testing
- **Multi-tool NWB validation** for scientific correctness
- **Property-based testing** for thorough edge case coverage
- **Systematic flaky test handling** for reliable test suite

This research provides the foundation for implementing all 46 functional
requirements across 8 test categories.
