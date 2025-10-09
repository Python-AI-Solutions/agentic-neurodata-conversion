# Testing Framework Quickstart Guide

**Feature**: 005-testing-quality-assurance **Date**: 2025-10-03 **Audience**:
Developers working on the agentic neurodata conversion system

This guide provides step-by-step instructions for using the testing and quality
assurance framework.

## Table of Contents

1. [Installing Test Dependencies](#installing-test-dependencies)
2. [Running Unit Tests](#running-unit-tests)
3. [Running Integration Tests](#running-integration-tests)
4. [Running End-to-End Tests](#running-end-to-end-tests)
5. [Checking Coverage](#checking-coverage)
6. [Running Specific Test Categories](#running-specific-test-categories)
7. [Debugging Test Failures](#debugging-test-failures)
8. [Using Test Fixtures](#using-test-fixtures)
9. [Mocking External Services](#mocking-external-services)
10. [Writing New Tests](#writing-new-tests)

---

## Installing Test Dependencies

### Prerequisites

- Python 3.12 or higher
- pixi package manager installed
- Git and git-annex (for DataLad integration tests)

### Installation Steps

1. **Clone the repository** (if not already done):

   ```bash
   git clone <repository-url>
   cd agentic-neurodata-conversion-2
   ```

2. **Install test environment with pixi**:

   ```bash
   pixi install -e test
   ```

   This installs all testing dependencies including:
   - pytest and plugins (pytest-cov, pytest-asyncio, pytest-mock, pytest-xdist)
   - hypothesis for property-based testing
   - Testing utilities (responses, pyfakefs)
   - NWB validation tools (pynwb, nwbinspector)

3. **Verify installation**:

   ```bash
   pixi run pytest --version
   ```

   Expected output: `pytest 7.x.x` or higher

4. **Download test datasets** (for integration/E2E tests):
   ```bash
   pixi run setup-test-datasets
   ```

---

## Running Unit Tests

Unit tests are fast, isolated tests with mocked dependencies.

### Run all unit tests:

```bash
pixi run test-unit
```

### Expected output:

```
================================ test session starts =================================
collected 150 items

tests/unit/test_agent_logic.py ..................                            [ 12%]
tests/unit/test_metadata_parser.py .........                                 [ 18%]
...
============================== 150 passed in 45.23s ==============================
```

### Performance:

- Target: < 5 minutes total
- Should see ~150-200 unit tests
- All tests should pass

---

## Running Integration Tests

Integration tests use real services and lightweight datasets.

### Prerequisites:

- Docker (for running GraphDB service) OR
- Local GraphDB instance running on port 7200

### Start services (if using Docker):

```bash
pixi run deploy-dev
```

### Run integration tests:

```bash
pixi run test-integration
```

### Expected output:

```
================================ test session starts =================================
collected 50 items

tests/integration/test_mcp_endpoints.py .................                    [ 34%]
tests/integration/test_kg_integration.py ........                            [ 50%]
...
============================== 50 passed in 8m 12s ================================
```

### Performance:

- Target: < 15 minutes total
- Should see ~50-80 integration tests
- Tests run sequentially to avoid conflicts

### Cleanup:

```bash
pixi run deploy-stop
```

---

## Running End-to-End Tests

E2E tests execute complete workflows with real DataLad datasets.

### Prerequisites:

- All integration test prerequisites
- git-annex installed
- At least 10GB free disk space

### Run E2E tests:

```bash
pixi run test-e2e
```

### Expected output:

```
================================ test session starts =================================
collected 12 items

tests/e2e/test_full_workflow.py ...                                          [ 25%]
tests/e2e/test_validation_pipeline.py ...                                    [ 50%]
...
============================== 12 passed in 18m 34s ================================
```

### Performance:

- Target: < 30 minutes total
- Should see ~10-20 E2E tests
- Generates NWB files in `tests/outputs/`

### View outputs:

```bash
ls tests/outputs/*.nwb
```

---

## Checking Coverage

### Generate coverage report:

```bash
pixi run test-cov
```

### View HTML coverage report:

```bash
# Report is generated in htmlcov/
# Open in browser:
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage requirements:

- **Overall**: ≥ 80%
- **MCP endpoints**: ≥ 90%
- **Client libraries**: ≥ 85%
- **Critical paths**: ≥ 95%

### Example coverage report:

```
Name                                     Stmts   Miss Branch BrPart  Cover
--------------------------------------------------------------------------
agentic_neurodata_conversion/agents.py     245     12     64      4    94%
agentic_neurodata_conversion/mcp.py        180      5     42      2    96%
agentic_neurodata_conversion/kg.py         156     18     38      6    87%
--------------------------------------------------------------------------
TOTAL                                     2450    125    485     28    89%
```

---

## Running Specific Test Categories

Tests are organized with pytest markers for selective execution.

### Available markers:

- `unit`: Fast unit tests
- `integration`: Integration tests
- `e2e`: End-to-end tests
- `slow`: Tests taking > 5 seconds
- `requires_datasets`: Tests needing DataLad datasets
- `requires_llm`: Tests needing LLM API access
- `benchmark`: Performance tests

### Run tests by marker:

```bash
# Only unit tests
pixi run pytest -m unit

# Integration tests, excluding slow ones
pixi run pytest -m "integration and not slow"

# All tests except those requiring datasets
pixi run pytest -m "not requires_datasets"

# Only benchmark tests
pixi run pytest -m benchmark
```

### Run specific test file:

```bash
pixi run pytest tests/unit/test_agent_logic.py
```

### Run specific test function:

```bash
pixi run pytest tests/unit/test_agent_logic.py::test_agent_initialization
```

### Run tests matching pattern:

```bash
# All tests with "validation" in name
pixi run pytest -k validation

# All tests with "nwb" but not "slow"
pixi run pytest -k "nwb and not slow"
```

---

## Debugging Test Failures

### Run with verbose output:

```bash
pixi run test-verbose
```

### Run with detailed traceback:

```bash
pixi run test-detailed
```

### Run failed tests only:

```bash
# Re-run only tests that failed last time
pixi run test-failed
```

### Run with debugger:

```bash
pixi run test-debug
```

This drops into pdb debugger on first failure:

```python
(Pdb) p variable_name  # Print variable
(Pdb) l  # List code around current line
(Pdb) n  # Next line
(Pdb) c  # Continue execution
```

### Enable live logging:

```bash
pixi run pytest --log-cli-level=DEBUG tests/unit/test_agent_logic.py
```

### Stop on first failure:

```bash
pixi run pytest -x  # Stop after first failure
pixi run pytest --maxfail=3  # Stop after 3 failures
```

### View test artifacts:

After test failures, check:

- `tests/logs/pytest.log`: Full test logs
- `tests/results/`: JUnit XML results
- `tests/outputs/`: Test-generated NWB files

---

## Using Test Fixtures

Fixtures provide reusable test setup components.

### Common fixtures available:

**Mock services:**

- `mock_knowledge_graph`: In-memory KG mock
- `mock_datalad`: DataLad operation mock
- `mock_filesystem`: Fake filesystem

**Data fixtures:**

- `test_nwb_file`: Minimal valid NWB file
- `sample_dataset_metadata`: Sample metadata dict
- `test_datasets_dir`: Directory with test datasets

**MCP fixtures:**

- `mcp_client`: Test client for MCP server
- `sample_mcp_request`: Valid MCP request payload

**Agent fixtures:**

- `conversion_agent`: Agent with mocked dependencies
- `validation_agent`: NWB validation agent

### Example using fixtures:

```python
import pytest

def test_agent_conversion(conversion_agent, sample_dataset_metadata):
    """Test agent converts dataset successfully."""
    # Fixtures are automatically injected
    result = conversion_agent.convert(
        dataset=sample_dataset_metadata["dataset_id"],
        format="nwb"
    )
    assert result.success is True
    assert result.output_file.endswith(".nwb")
```

### Fixture scopes:

- **function** (default): New instance per test
- **module**: Shared across test file
- **session**: Shared across entire test run

### View available fixtures:

```bash
pixi run pytest --fixtures
```

---

## Mocking External Services

### Mock Knowledge Graph:

```python
def test_kg_query(mock_knowledge_graph):
    """Test querying Knowledge Graph."""
    # Mock is pre-loaded with test ontology
    results = mock_knowledge_graph.query(
        "SELECT ?s WHERE {?s rdf:type nwb:Dataset}"
    )
    assert len(results) > 0
```

### Mock DataLad:

```python
def test_datalad_clone(mock_datalad):
    """Test DataLad dataset cloning."""
    # Configure mock response
    mock_datalad.configure_dataset_response(
        "test-dataset",
        {"status": "available", "files": ["data.nwb"]}
    )

    # Use mock
    dataset = mock_datalad.clone("test-dataset", Path("/tmp/target"))
    assert dataset is not None
```

### Mock HTTP requests:

```python
import responses

@responses.activate
def test_external_api():
    """Test external API call."""
    # Mock HTTP response
    responses.add(
        responses.GET,
        "http://api.example.com/data",
        json={"result": "success"},
        status=200
    )

    # Make request (automatically uses mock)
    resp = requests.get("http://api.example.com/data")
    assert resp.json()["result"] == "success"
```

### Mock filesystem:

```python
def test_file_operations(fs):  # fs is pyfakefs fixture
    """Test file operations."""
    # Create fake file
    fs.create_file("/test/data.nwb", contents="fake nwb data")

    # File operations work as normal
    assert Path("/test/data.nwb").exists()
    with open("/test/data.nwb") as f:
        assert f.read() == "fake nwb data"
```

---

## Writing New Tests

### Test structure:

```python
import pytest
from agentic_neurodata_conversion.agents import ConversionAgent

class TestConversionAgent:
    """Test suite for ConversionAgent."""

    def test_initialization(self):
        """Test agent initializes correctly."""
        agent = ConversionAgent()
        assert agent is not None
        assert agent.state == AgentState.IDLE

    def test_conversion_success(self, conversion_agent, sample_dataset_metadata):
        """Test successful dataset conversion."""
        result = conversion_agent.convert(
            dataset=sample_dataset_metadata["dataset_id"],
            format="nwb"
        )
        assert result.success is True

    @pytest.mark.slow
    def test_large_dataset_conversion(self, conversion_agent):
        """Test conversion of large dataset (slow test)."""
        # This test is marked 'slow' and skipped by default
        result = conversion_agent.convert("large-dataset", "nwb")
        assert result.success is True
```

### Async tests:

```python
import pytest

@pytest.mark.asyncio
async def test_async_endpoint(mcp_client):
    """Test async MCP endpoint."""
    response = await mcp_client.post(
        "/tools/convert",
        json={"dataset": "test"}
    )
    assert response.status_code == 200
```

### Parametrized tests:

```python
@pytest.mark.parametrize("dataset_type,expected_format", [
    ("ephys", "nwb"),
    ("ophys", "nwb"),
    ("behavior", "nwb"),
])
def test_conversion_formats(conversion_agent, dataset_type, expected_format):
    """Test conversion for different dataset types."""
    result = conversion_agent.convert(f"test-{dataset_type}", expected_format)
    assert result.success is True
```

### Property-based tests:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_metadata_parser_robustness(text):
    """Test metadata parser handles arbitrary input."""
    result = parse_metadata(text)
    # Parser should never crash, even on invalid input
    assert result is not None or result.error is not None
```

---

## Quick Reference

### Common test commands:

| Command                     | Description             |
| --------------------------- | ----------------------- |
| `pixi run test-unit`        | Run unit tests          |
| `pixi run test-integration` | Run integration tests   |
| `pixi run test-e2e`         | Run E2E tests           |
| `pixi run test-cov`         | Run tests with coverage |
| `pixi run test-fast`        | Run fast tests only     |
| `pixi run test-failed`      | Re-run failed tests     |
| `pixi run test-verbose`     | Run with verbose output |
| `pixi run test-debug`       | Run with debugger       |

### Test organization:

```
tests/
├── unit/              # Unit tests (fast, mocked)
├── integration/       # Integration tests (real services)
├── e2e/              # End-to-end tests (full workflows)
├── mcp_server/       # MCP endpoint tests
├── agents/           # Agent tests
├── clients/          # Client library tests
└── validation/       # NWB validation tests
```

### Coverage targets:

- Overall: ≥ 80%
- MCP endpoints: ≥ 90%
- Client libraries: ≥ 85%
- Critical paths: ≥ 95%

### Getting help:

```bash
# View all available test commands
pixi task list | grep test

# View pytest help
pixi run pytest --help

# View available fixtures
pixi run pytest --fixtures

# View available markers
pixi run pytest --markers
```

---

## Next Steps

After mastering the basics:

1. **Write contract tests** for new MCP endpoints
2. **Add integration tests** for new agents
3. **Create E2E tests** for new workflows
4. **Monitor test metrics** in CI dashboard
5. **Review flaky tests** weekly
6. **Update baselines** for performance benchmarks

For more details, see:

- [Data Model](./data-model.md) - Entity definitions
- [Contracts](./contracts/) - Test configuration schemas
- [Research](./research.md) - Technical decisions and rationale

Happy testing!
