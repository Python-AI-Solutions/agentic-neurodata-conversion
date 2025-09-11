# Test Fixtures

This directory contains test fixtures, mock services, and data generators for
the agentic neurodata conversion project.

## Files

- **`test_data_generators.py`** - Synthetic data generators for various
  neuroscience formats (Open Ephys, SpikeGLX, etc.)
- **`test_mock_services.py`** - Mock implementations of external services (LLM
  clients, NeuroConv, NWB Inspector, etc.)
- **`test_cleanup.py`** - Cleanup utilities for test environments

## Usage

### Data Generators

```python
from tests.fixtures.test_data_generators import DatasetFactory

factory = DatasetFactory()
dataset = factory.create_clean_dataset(output_dir, format_type="open_ephys")
```

### Mock Services

```python
from tests.fixtures.test_mock_services import MockLLMClient, MockMCPServer

mock_llm = MockLLMClient(responses={"completion": "test response"})
mock_server = MockMCPServer()
```

## Test Data Types

- **Clean datasets** - Well-formed data for positive testing
- **Corrupted datasets** - Data with various corruption issues for error
  handling tests
- **Minimal datasets** - Small datasets for quick testing
- **Large datasets** - Performance testing datasets

## Mock Services Available

- MockLLMClient - LLM service mocking
- MockNeuroConvInterface - NeuroConv integration mocking
- MockNWBInspector - NWB Inspector mocking
- MockDataLadDataset - DataLad dataset mocking
- MockMCPServer - MCP server mocking
- MockHTTPClient - HTTP client mocking
- MockFileSystem - File system operations mocking
