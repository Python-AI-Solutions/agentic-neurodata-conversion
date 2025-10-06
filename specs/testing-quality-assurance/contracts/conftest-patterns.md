# Conftest.py Organization Patterns

**Version**: 1.0 **Date**: 2025-10-03 **Purpose**: Define standard patterns for
organizing pytest fixtures in conftest.py files

## Overview

The testing framework uses a hierarchical conftest.py structure where fixtures
are organized by scope and shared appropriately across test modules.

## Conftest.py Hierarchy

```
tests/
├── conftest.py                 # Root conftest - session/global fixtures
├── mcp_server/
│   ├── conftest.py            # MCP-specific fixtures
│   └── test_*.py
├── agents/
│   ├── conftest.py            # Agent-specific fixtures
│   └── test_*.py
├── e2e/
│   ├── conftest.py            # E2E-specific fixtures
│   └── test_*.py
└── validation/
    ├── conftest.py            # Validation-specific fixtures
    └── test_*.py
```

## Root Conftest (tests/conftest.py)

**Purpose**: Provide session-scoped and globally-shared fixtures

**Fixture Categories**:

1. **Session-scoped fixtures**: Database connections, test datasets, environment
   setup
2. **Mock services**: Shared mock implementations
3. **Configuration**: Test configuration and settings
4. **Utilities**: Helper functions available to all tests

**Example Structure**:

```python
import pytest
from pathlib import Path
from agentic_neurodata_conversion.testing.mocks import MockKnowledgeGraph, MockDataLad
from agentic_neurodata_conversion.testing.generators import DatasetGenerator

# ============================================================================
# Session-scoped fixtures (expensive setup, shared across all tests)
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Root directory for test data files."""
    return Path(__file__).parent / "data"

@pytest.fixture(scope="session")
def test_datasets_dir(test_data_dir: Path) -> Path:
    """Directory containing test DataLad datasets."""
    return test_data_dir / "datasets"

@pytest.fixture(scope="session")
def temp_output_dir(tmp_path_factory):
    """Temporary directory for test outputs (session-scoped)."""
    return tmp_path_factory.mktemp("outputs")

# ============================================================================
# Module-scoped fixtures (medium setup cost, shared within test module)
# ============================================================================

@pytest.fixture(scope="module")
def mock_knowledge_graph():
    """Provides in-memory Knowledge Graph mock for testing."""
    mock_kg = MockKnowledgeGraph()
    mock_kg.load_test_ontology()
    yield mock_kg
    mock_kg.clear()

@pytest.fixture(scope="module")
def mock_datalad():
    """Provides DataLad operation mock."""
    mock_dl = MockDataLad()
    mock_dl.configure_test_datasets()
    yield mock_dl
    mock_dl.cleanup()

# ============================================================================
# Function-scoped fixtures (fast setup, isolated per test)
# ============================================================================

@pytest.fixture
def dataset_generator():
    """Provides dataset generator for creating test data."""
    return DatasetGenerator()

@pytest.fixture
def clean_temp_dir(tmp_path: Path) -> Path:
    """Clean temporary directory for each test."""
    yield tmp_path
    # Cleanup happens automatically via tmp_path

# ============================================================================
# Pytest configuration hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers",
        "unit: Unit tests - fast, isolated, mocked dependencies"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection - add markers based on test location."""
    for item in items:
        # Auto-mark tests based on directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
```

## Component-Specific Conftest Pattern

**Purpose**: Provide fixtures specific to a test category

### Example: MCP Server Conftest (tests/mcp_server/conftest.py)

```python
import pytest
from fastapi.testclient import TestClient
from agentic_neurodata_conversion.mcp_server import create_app
from agentic_neurodata_conversion.testing.mocks import MockAgent

@pytest.fixture(scope="module")
def mcp_app():
    """MCP server application instance."""
    app = create_app(testing=True)
    return app

@pytest.fixture
def mcp_client(mcp_app):
    """Test client for MCP server."""
    return TestClient(mcp_app)

@pytest.fixture
def mock_agent():
    """Mock agent for MCP endpoint testing."""
    agent = MockAgent(agent_type="conversion")
    yield agent
    agent.reset()

@pytest.fixture
def sample_mcp_request():
    """Sample MCP tool request payload."""
    return {
        "tool": "convert_dataset",
        "parameters": {
            "dataset_id": "test-dataset",
            "output_format": "nwb"
        }
    }

@pytest.fixture
def invalid_mcp_request():
    """Invalid MCP request for error testing."""
    return {
        "tool": "nonexistent_tool",
        "parameters": {}
    }
```

### Example: Agent Conftest (tests/agents/conftest.py)

```python
import pytest
from agentic_neurodata_conversion.agents import ConversionAgent, ValidationAgent
from agentic_neurodata_conversion.testing.fixtures import mock_filesystem

@pytest.fixture
def conversion_agent(mock_knowledge_graph, mock_datalad):
    """Conversion agent with mocked dependencies."""
    agent = ConversionAgent(
        knowledge_graph=mock_knowledge_graph,
        datalad=mock_datalad
    )
    yield agent
    agent.cleanup()

@pytest.fixture
def validation_agent():
    """Validation agent for NWB validation."""
    return ValidationAgent()

@pytest.fixture
def agent_test_context():
    """Test context with common agent setup."""
    return {
        "dataset_id": "test-dataset",
        "conversion_format": "nwb",
        "validation_rules": ["schema", "best_practices"]
    }
```

### Example: E2E Conftest (tests/e2e/conftest.py)

```python
import pytest
from pathlib import Path
from agentic_neurodata_conversion.testing.fixtures import IntegrationEnvironment

@pytest.fixture(scope="module")
def integration_environment():
    """Full integration test environment."""
    env = IntegrationEnvironment()
    env.setup()
    yield env
    env.teardown()

@pytest.fixture
def real_datalad_dataset(test_datasets_dir: Path):
    """Real lightweight DataLad dataset for E2E testing."""
    dataset_path = test_datasets_dir / "minimal_ephys"
    return dataset_path

@pytest.fixture
def e2e_workflow_config():
    """Configuration for end-to-end workflow tests."""
    return {
        "dataset": "minimal_ephys",
        "conversion_pipeline": "ephys_to_nwb",
        "validation_level": "full",
        "output_dir": "e2e_outputs"
    }
```

## Fixture Scope Guidelines

### When to use each scope:

**session**:

- Database connections (if persistent across tests)
- Large test datasets loaded from disk
- Expensive initialization (> 1 second)
- Shared test configuration
- Example: Loading 100MB test dataset once

**module**:

- Mock service instances shared within test file
- Medium-cost setup (0.1-1 second)
- Per-module configuration
- Example: Mock Knowledge Graph with test ontology

**function** (default):

- Test-specific data
- Isolated state per test
- Fast setup (< 0.1 second)
- Mutable objects that tests modify
- Example: Individual test dataset instances

## Fixture Dependencies

Fixtures can depend on other fixtures. Follow these principles:

**Good Dependencies**:

```python
@pytest.fixture
def nwb_file(temp_output_dir: Path, dataset_generator):
    """NWB file depends on output dir and generator."""
    return dataset_generator.create_nwb_file(temp_output_dir)
```

**Avoid Circular Dependencies**:

```python
# BAD - circular dependency
@pytest.fixture
def fixture_a(fixture_b):
    return fixture_b + 1

@pytest.fixture
def fixture_b(fixture_a):  # CIRCULAR!
    return fixture_a + 1
```

## Fixture Parameterization

Use parameterization for testing multiple scenarios:

```python
@pytest.fixture(params=[
    "minimal_ephys",
    "minimal_ophys",
    "minimal_behavior"
])
def dataset_type(request):
    """Parameterized fixture for different dataset types."""
    return request.param

# Test will run 3 times, once for each dataset type
def test_conversion(dataset_type):
    assert convert_dataset(dataset_type) is not None
```

## Fixture Cleanup Patterns

### Using yield for cleanup:

```python
@pytest.fixture
def database_connection():
    conn = create_connection()
    yield conn
    conn.close()  # Cleanup after test
```

### Using finalizer:

```python
@pytest.fixture
def temp_file(request, tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")

    def cleanup():
        if file_path.exists():
            file_path.unlink()

    request.addfinalizer(cleanup)
    return file_path
```

## Auto-use Fixtures

Fixtures that run automatically for all tests:

```python
@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    ConfigManager.reset()
    CacheManager.clear()
    yield
    # Cleanup after test
```

## Fixture Naming Conventions

- **mock\_\***: Mock implementations (e.g., `mock_knowledge_graph`)
- **sample\_\***: Sample/example data (e.g., `sample_nwb_file`)
- **test\_\***: Test-specific instances (e.g., `test_dataset`)
- **temp\_\***: Temporary resources (e.g., `temp_output_dir`)
- **real\_\***: Real (non-mocked) instances (e.g., `real_datalad_dataset`)

## Fixture Documentation

All fixtures should have docstrings:

```python
@pytest.fixture(scope="module")
def mock_knowledge_graph():
    """
    Provides in-memory Knowledge Graph mock for testing.

    Yields:
        MockKnowledgeGraph: Mock KG instance with test ontology loaded

    Scope: module (shared across test file)

    Cleanup: Automatically clears graph data after module tests complete
    """
    mock_kg = MockKnowledgeGraph()
    mock_kg.load_test_ontology()
    yield mock_kg
    mock_kg.clear()
```

## Validation Rules

1. **No duplicate fixture names** across conftest files at the same level
2. **Session fixtures must be thread-safe** for parallel test execution
3. **Cleanup must be reliable** - use try/finally or yield
4. **Fixtures should be focused** - one responsibility per fixture
5. **Dependencies should be explicit** - don't hide fixture dependencies

## Testing the Fixtures

Fixtures themselves should be tested:

```python
def test_mock_knowledge_graph_fixture(mock_knowledge_graph):
    """Verify mock KG fixture provides expected functionality."""
    assert mock_knowledge_graph is not None
    assert mock_knowledge_graph.is_connected()
    assert len(mock_knowledge_graph.query("SELECT * WHERE {?s ?p ?o}")) > 0
```

This pattern ensures consistent, maintainable test infrastructure across the
entire testing framework.
