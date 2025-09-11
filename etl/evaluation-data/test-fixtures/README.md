# Test Fixtures

Small, lightweight datasets specifically designed for unit testing and development.

## Purpose

This directory contains minimal datasets optimized for:
- **Unit Testing**: Fast, reliable test data for automated testing
- **Development**: Quick datasets for development and debugging
- **CI/CD**: Lightweight data for continuous integration pipelines
- **Documentation**: Simple examples for tutorials and documentation

## Dataset Characteristics

### Size Constraints
- **Small File Sizes**: Typically < 10MB per dataset
- **Minimal Duration**: Short recordings (seconds to minutes)
- **Low Channel Counts**: Few channels for fast processing
- **Simple Structure**: Straightforward file organization

### Quality Requirements
- **Well-Formed Data**: Clean, properly formatted data files
- **Complete Metadata**: All required fields present
- **Consistent Structure**: Standardized organization across fixtures
- **Fast Processing**: Quick conversion times for rapid testing

## Fixture Categories

### Format-Specific Fixtures
```
test-fixtures/
├── spikeglx/           # SpikeGLX format fixtures
├── open_ephys/         # Open Ephys format fixtures
├── neuralynx/          # Neuralynx format fixtures
├── blackrock/          # Blackrock format fixtures
└── suite2p/            # Suite2p format fixtures
```

### Test Scenario Fixtures
```
test-fixtures/
├── minimal/            # Absolute minimum viable datasets
├── complete/           # Fully featured example datasets
├── multi_modal/        # Multiple data types in one dataset
└── edge_cases/         # Small edge case examples
```

## Usage in Testing

### Unit Tests
```python
import pytest
from pathlib import Path

@pytest.fixture
def spikeglx_fixture():
    """Provide SpikeGLX test fixture."""
    return Path("etl/evaluation-data/test-fixtures/spikeglx/minimal")

@pytest.mark.unit
def test_spikeglx_conversion(spikeglx_fixture):
    """Test SpikeGLX conversion with fixture data."""
    result = convert_spikeglx_data(spikeglx_fixture)
    assert result.success
    assert result.output_path.exists()
```

### Integration Tests
```python
@pytest.mark.integration
def test_full_pipeline_with_fixture():
    """Test complete pipeline with test fixture."""
    fixture_path = "etl/evaluation-data/test-fixtures/complete/example"
    
    # Test full pipeline
    result = run_conversion_pipeline(fixture_path)
    
    assert result.success
    assert validate_nwb_file(result.output_path)
```

### Development Testing
```python
# Quick development test
def test_new_feature():
    """Test new feature with minimal fixture."""
    fixture = load_test_fixture("minimal/basic_recording")
    result = new_feature_function(fixture)
    assert result is not None
```

## Fixture Creation Guidelines

### Creating New Fixtures

1. **Keep It Small**: Minimize file sizes and complexity
2. **Make It Representative**: Include key characteristics of the format
3. **Ensure Completeness**: Include all necessary files and metadata
4. **Document Thoroughly**: Provide clear descriptions and usage examples
5. **Test Thoroughly**: Verify fixtures work correctly in tests

### Fixture Structure Template
```
fixture_name/
├── README.md           # Fixture description and usage
├── data/              # Raw data files
│   ├── recording.dat
│   └── metadata.json
├── expected/          # Expected conversion outputs
│   └── expected.nwb
└── config/            # Configuration files
    └── conversion_config.yaml
```

## Maintenance

### Regular Updates
- **Refresh Data**: Update fixtures to reflect current format standards
- **Add Coverage**: Create fixtures for new formats or edge cases
- **Optimize Size**: Keep fixtures as small as possible while maintaining utility
- **Update Documentation**: Keep fixture descriptions current

### Quality Assurance
- **Validate Fixtures**: Regularly test that fixtures work correctly
- **Check Performance**: Ensure fixtures remain fast for testing
- **Review Relevance**: Remove obsolete or redundant fixtures
- **Monitor Usage**: Track which fixtures are actively used in tests

## Integration with Testing Framework

### Pytest Configuration
```python
# conftest.py
import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def test_fixtures_dir():
    """Provide path to test fixtures directory."""
    return Path("etl/evaluation-data/test-fixtures")

@pytest.fixture
def minimal_fixture(test_fixtures_dir):
    """Provide minimal test fixture."""
    return test_fixtures_dir / "minimal" / "basic_recording"

@pytest.fixture(params=["spikeglx", "open_ephys", "neuralynx"])
def format_fixture(request, test_fixtures_dir):
    """Parametrized fixture for testing multiple formats."""
    return test_fixtures_dir / request.param / "minimal"
```

### Automated Fixture Validation
```bash
# Validate all test fixtures
pixi run pytest tests/fixtures/test_fixture_validation.py

# Test specific fixture category
pixi run pytest tests/fixtures/ -k "spikeglx_fixtures"

# Quick fixture smoke test
pixi run pytest tests/fixtures/test_fixture_smoke.py --fast
```

## Performance Considerations

### Speed Optimization
- **Minimal Data**: Use smallest possible datasets
- **Efficient Formats**: Choose formats that load quickly
- **Cached Results**: Cache conversion results when possible
- **Parallel Testing**: Design fixtures for parallel test execution

### Resource Management
- **Memory Efficiency**: Keep memory usage low
- **Storage Optimization**: Compress fixtures when appropriate
- **Cleanup**: Ensure tests clean up temporary files
- **Isolation**: Prevent test interference between fixtures

## Usage Examples

### Basic Usage
```python
# Load and use a test fixture
fixture_path = "etl/evaluation-data/test-fixtures/spikeglx/minimal"
result = test_conversion_function(fixture_path)
```

### Parametrized Testing
```python
@pytest.mark.parametrize("fixture_name", [
    "minimal/basic_recording",
    "complete/full_session", 
    "multi_modal/ephys_behavior"
])
def test_conversion_with_fixtures(fixture_name):
    """Test conversion with multiple fixtures."""
    fixture_path = f"etl/evaluation-data/test-fixtures/{fixture_name}"
    result = convert_dataset(fixture_path)
    assert result.success
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Run tests with fixtures
  run: |
    pixi run pytest tests/ --fixtures-only --fast
    pixi run pytest tests/unit/ -m "not slow"
```

## Related Documentation

- [Evaluation Data Main README](../README.md)
- [Testing Quality Assurance](../../../.kiro/specs/testing-quality-assurance/)
- [Unit Testing Guidelines](../../../tests/unit/README.md)
- [Pytest Documentation](https://docs.pytest.org/)