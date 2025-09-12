# Evaluation Data

This directory contains curated datasets specifically designed for testing,
evaluation, and benchmarking of the agentic neurodata conversion pipeline.

## Purpose

The evaluation-data directory provides:

- **Test Datasets**: Controlled datasets for validation and testing
- **Benchmarking Data**: Standard datasets for performance comparison
- **Synthetic Data**: Generated datasets with known characteristics
- **Edge Cases**: Challenging datasets that test pipeline robustness

## Directory Structure

```
evaluation-data/
├── synthetic-messy-datasets/    # Generated datasets with known issues
├── benchmark-datasets/          # Standard datasets for performance testing
├── edge-case-datasets/          # Challenging conversion scenarios
├── validation-datasets/         # Known-good datasets for validation
└── test-fixtures/              # Small datasets for unit testing
```

## Dataset Categories

### Synthetic Messy Datasets

Located in `synthetic-messy-datasets/`, these are artificially generated
datasets that simulate common data quality issues:

- **Missing Metadata**: Datasets with incomplete experimental information
- **Format Inconsistencies**: Mixed or non-standard file formats
- **Corrupted Files**: Datasets with intentional data corruption
- **Naming Conflicts**: Files with ambiguous or conflicting names
- **Scale Variations**: Datasets of different sizes and complexities

### Benchmark Datasets

Standard reference datasets for performance evaluation:

- **Processing Speed**: Datasets for measuring conversion throughput
- **Memory Usage**: Large datasets for testing resource efficiency
- **Accuracy Metrics**: Datasets with known correct conversion outputs
- **Scalability Tests**: Datasets of varying sizes for scaling analysis

### Edge Case Datasets

Challenging scenarios that test pipeline robustness:

- **Unusual Formats**: Rare or custom data acquisition systems
- **Complex Experiments**: Multi-modal or multi-session recordings
- **Large Scale Data**: Datasets that push memory and storage limits
- **Legacy Formats**: Older data formats with limited documentation

### Validation Datasets

High-quality datasets with known correct outputs:

- **Reference Conversions**: Manually validated NWB files
- **Gold Standard**: Expert-curated conversion examples
- **Regression Tests**: Datasets for detecting pipeline changes
- **Quality Baselines**: Minimum quality thresholds for validation

## DataLad Integration

Evaluation datasets are managed through DataLad for:

- **Version Control**: Track changes to test datasets over time
- **Reproducibility**: Ensure consistent test conditions across environments
- **Efficient Storage**: Large test files stored in git-annex
- **Provenance Tracking**: Document dataset creation and modification history

### Working with Evaluation Data

```python
import datalad.api as dl

# Get specific evaluation datasets
dl.get(path="etl/evaluation-data/synthetic-messy-datasets/")

# Install benchmark datasets
dl.install(dataset=".", path="etl/evaluation-data/benchmark-datasets")

# Create new test dataset
dl.create(dataset="etl/evaluation-data/new-test-category")

# Save evaluation results
dl.save(dataset=".", path="etl/evaluation-data/", message="Add new test results")
```

## Dataset Creation Guidelines

### Synthetic Dataset Generation

When creating synthetic datasets:

1. **Define Purpose**: Specify what aspect of the pipeline to test
2. **Control Variables**: Ensure known ground truth for validation
3. **Document Properties**: Record all synthetic dataset characteristics
4. **Include Metadata**: Provide complete experimental context
5. **Version Control**: Track generation scripts and parameters

### Real Dataset Curation

For real evaluation datasets:

1. **Obtain Permissions**: Ensure proper licensing and attribution
2. **Anonymize Data**: Remove any personally identifiable information
3. **Validate Quality**: Verify data integrity and completeness
4. **Document Provenance**: Record data source and processing history
5. **Create References**: Generate expected conversion outputs

## Testing Integration

### Automated Testing

Evaluation datasets integrate with the testing framework:

```python
import pytest
from pathlib import Path

@pytest.mark.evaluation
def test_conversion_accuracy(evaluation_dataset):
    """Test conversion accuracy against known good outputs."""
    result = convert_dataset(evaluation_dataset.input_path)
    expected = load_reference_output(evaluation_dataset.reference_path)
    assert validate_conversion_accuracy(result, expected)

@pytest.mark.benchmark
def test_conversion_performance(benchmark_dataset):
    """Test conversion performance metrics."""
    start_time = time.time()
    result = convert_dataset(benchmark_dataset.path)
    duration = time.time() - start_time

    assert duration < benchmark_dataset.max_duration
    assert result.memory_usage < benchmark_dataset.max_memory
```

### Continuous Integration

Evaluation datasets are used in CI/CD pipelines:

- **Regression Testing**: Detect changes in conversion behavior
- **Performance Monitoring**: Track conversion speed and resource usage
- **Quality Assurance**: Validate output quality against baselines
- **Compatibility Testing**: Ensure compatibility across environments

## Evaluation Metrics

### Conversion Quality Metrics

- **Accuracy**: Correctness of converted data values
- **Completeness**: Preservation of all relevant information
- **Compliance**: Adherence to NWB standard specifications
- **Metadata Fidelity**: Accuracy of extracted experimental metadata

### Performance Metrics

- **Processing Speed**: Time required for conversion
- **Memory Usage**: Peak memory consumption during conversion
- **Storage Efficiency**: Size of output files relative to input
- **Scalability**: Performance characteristics with dataset size

### Robustness Metrics

- **Error Handling**: Graceful handling of problematic inputs
- **Recovery Rate**: Ability to process partially corrupted data
- **Edge Case Coverage**: Success rate on challenging datasets
- **Consistency**: Reproducible results across multiple runs

## Dataset Maintenance

### Regular Updates

- **Refresh Synthetic Data**: Regenerate datasets with updated parameters
- **Add New Scenarios**: Include newly discovered edge cases
- **Update References**: Refresh expected outputs with pipeline improvements
- **Prune Obsolete Data**: Remove outdated or redundant datasets

### Quality Assurance

- **Validate Integrity**: Regular checks for data corruption
- **Update Documentation**: Keep dataset descriptions current
- **Review Licensing**: Ensure continued compliance with data licenses
- **Monitor Usage**: Track which datasets are actively used in testing

## Usage Examples

### Running Evaluation Tests

```bash
# Run all evaluation tests
pixi run pytest tests/evaluation/ -m evaluation

# Test specific dataset category
pixi run pytest tests/evaluation/ -k "synthetic_messy"

# Benchmark performance
pixi run pytest tests/evaluation/ -m benchmark --benchmark-only
```

### Creating Custom Evaluations

```python
from etl.evaluation_data import EvaluationDataset

# Load evaluation dataset
dataset = EvaluationDataset.load("synthetic-messy-datasets/missing-metadata")

# Run conversion
result = conversion_pipeline.process(dataset.input_path)

# Evaluate against expected output
score = evaluate_conversion(result, dataset.expected_output)
```

## Integration with Pipeline Components

### MCP Server Tools

Evaluation data integrates with MCP tools:

- **Dataset Analysis**: Automated evaluation of conversion quality
- **Benchmark Execution**: Performance testing through MCP interface
- **Report Generation**: Automated evaluation reports

### Agent Coordination

Evaluation datasets work with pipeline agents:

- **Conversion Agent**: Testing script generation and execution
- **Evaluation Agent**: Automated quality assessment
- **Knowledge Graph Agent**: Validation of metadata extraction

## Related Documentation

- [ETL Main README](../README.md)
- [Testing Quality Assurance](../../.kiro/specs/testing-quality-assurance/)
- [Evaluation and Reporting](../../.kiro/specs/evaluation-reporting/)
- [DataLad Handbook](https://handbook.datalad.org/)
