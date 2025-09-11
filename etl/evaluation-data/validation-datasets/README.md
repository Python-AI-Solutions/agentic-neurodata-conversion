# Validation Datasets

High-quality datasets with known correct outputs for validation and regression testing.

## Purpose

This directory contains carefully curated datasets that serve as:
- **Reference Standards**: Known correct conversion examples
- **Regression Tests**: Datasets for detecting pipeline changes
- **Quality Baselines**: Minimum quality thresholds for validation
- **Training Examples**: High-quality examples for model training

## Dataset Categories

### Gold Standard Conversions
- Expert-validated NWB files with complete metadata
- Manually curated conversions from domain experts
- Reference implementations from established labs
- Community-approved conversion examples

### Regression Test Datasets
- Datasets with stable, expected conversion outputs
- Version-controlled reference outputs for comparison
- Automated test datasets for CI/CD pipelines
- Historical conversion examples for compatibility testing

### Quality Validation Datasets
- Datasets that define minimum quality standards
- Examples of complete and compliant NWB files
- Datasets covering all major NWB data types
- Examples of proper metadata structure and content

### Format Coverage Datasets
- Representative examples of each supported data format
- Complete coverage of major acquisition systems
- Examples of different experimental paradigms
- Multi-modal dataset examples

## Quality Assurance

All validation datasets must meet strict criteria:

### Data Quality
- Complete and accurate experimental metadata
- Proper file structure and organization
- No missing or corrupted data files
- Consistent naming conventions

### Conversion Quality
- Full compliance with NWB standard
- Complete metadata mapping
- Proper data type assignments
- Validated temporal alignment

### Documentation Quality
- Comprehensive dataset descriptions
- Clear experimental protocols
- Complete parameter specifications
- Proper attribution and licensing

## Usage in Testing

### Automated Validation
```python
@pytest.mark.validation
def test_conversion_accuracy(validation_dataset):
    """Test conversion against known good output."""
    result = convert_dataset(validation_dataset.input_path)
    reference = load_reference_nwb(validation_dataset.reference_path)
    
    assert validate_nwb_equivalence(result, reference)
    assert check_metadata_completeness(result)
    assert verify_data_integrity(result)
```

### Regression Testing
```python
@pytest.mark.regression
def test_conversion_stability(validation_dataset):
    """Test that conversion output remains stable."""
    current_result = convert_dataset(validation_dataset.input_path)
    baseline_result = load_baseline_output(validation_dataset.baseline_path)
    
    assert compare_conversion_outputs(current_result, baseline_result)
```

## Dataset Management

### Adding New Validation Datasets

1. **Source Verification**: Ensure dataset comes from reliable source
2. **Quality Review**: Validate data quality and completeness
3. **Expert Review**: Have domain expert validate conversion
4. **Documentation**: Create comprehensive dataset documentation
5. **Version Control**: Add to DataLad with proper provenance

### Maintaining Validation Datasets

1. **Regular Review**: Periodically review dataset quality and relevance
2. **Update References**: Update reference outputs with pipeline improvements
3. **Expand Coverage**: Add datasets for new formats or use cases
4. **Prune Obsolete**: Remove outdated or redundant datasets

## Integration with Pipeline

### MCP Server Integration
Validation datasets are accessible through MCP tools:
```python
@mcp.tool(name="validate_conversion_quality")
async def validate_conversion_quality(dataset_name: str, conversion_result_path: str):
    """Validate conversion against reference dataset."""
    validation_dataset = load_validation_dataset(dataset_name)
    result = validate_against_reference(conversion_result_path, validation_dataset)
    return result
```

### Agent Coordination
- **Evaluation Agent**: Uses validation datasets for quality assessment
- **Conversion Agent**: References validation examples for script generation
- **Knowledge Graph Agent**: Validates metadata extraction against references

## Validation Metrics

### Data Fidelity Metrics
- **Temporal Accuracy**: Correct timing and synchronization
- **Amplitude Preservation**: Accurate signal amplitudes and units
- **Channel Mapping**: Correct electrode/channel assignments
- **Metadata Completeness**: All required fields present and accurate

### NWB Compliance Metrics
- **Schema Validation**: Compliance with NWB schema requirements
- **Data Type Correctness**: Proper use of NWB data types
- **Hierarchical Structure**: Correct organization of NWB file structure
- **Extension Usage**: Proper use of NWB extensions when needed

## Usage Examples

```bash
# Run validation tests
pixi run pytest tests/validation/ -m validation

# Test specific validation categories
pixi run pytest tests/validation/ -k "gold_standard"
pixi run pytest tests/validation/ -k "regression"

# Validate specific conversion
pixi run python -m etl.validation.validate_conversion \
    --input conversion_result.nwb \
    --reference validation_datasets/gold_standard/example.nwb
```

## Related Documentation

- [Evaluation Data Main README](../README.md)
- [Testing Quality Assurance](../../../.kiro/specs/testing-quality-assurance/)
- [NWB Standard Documentation](https://nwb-schema.readthedocs.io/)
- [NeuroConv Validation Guide](https://neuroconv.readthedocs.io/)