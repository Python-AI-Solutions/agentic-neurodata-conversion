# Edge Case Datasets

Challenging datasets that test pipeline robustness and error handling
capabilities.

## Purpose

This directory contains datasets that represent challenging conversion
scenarios:

- **Unusual Data Formats**: Rare or custom acquisition systems
- **Corrupted Data**: Files with intentional corruption for robustness testing
- **Incomplete Metadata**: Datasets missing critical experimental information
- **Complex Experiments**: Multi-modal, multi-session, or unusual experimental
  designs
- **Legacy Formats**: Older data formats with limited documentation

## Dataset Categories

### Format Edge Cases

- Custom or proprietary data formats
- Mixed format datasets within single experiments
- Formats with non-standard file extensions or structures
- Datasets with unusual directory organizations

### Data Quality Issues

- Files with missing or corrupted headers
- Datasets with inconsistent sampling rates
- Recordings with gaps or discontinuities
- Files with encoding or endianness issues

### Metadata Challenges

- Experiments with minimal or missing metadata
- Conflicting metadata across files
- Non-standard parameter naming conventions
- Missing critical NWB-required fields

### Scale and Complexity

- Extremely large datasets that push memory limits
- Very small datasets with minimal data
- Datasets with unusual channel counts or configurations
- Multi-day or continuous recordings

## Testing Strategy

Edge case datasets are used to:

1. **Validate Error Handling**: Ensure graceful failure modes
2. **Test Recovery Mechanisms**: Verify partial conversion capabilities
3. **Stress Test Pipeline**: Push system limits and identify bottlenecks
4. **Improve Robustness**: Identify and fix edge case failures

## Usage Guidelines

1. **Expect Failures**: These datasets are designed to challenge the pipeline
2. **Document Behavior**: Record how the pipeline handles each edge case
3. **Iterative Improvement**: Use failures to improve pipeline robustness
4. **Safety First**: Run edge case tests in isolated environments
5. **Monitor Resources**: Watch for memory leaks or resource exhaustion

## Creating Edge Case Datasets

When adding new edge case datasets:

1. **Document the Challenge**: Clearly describe what makes the dataset difficult
2. **Provide Context**: Explain the real-world scenario the edge case represents
3. **Include Expected Behavior**: Document how the pipeline should handle the
   case
4. **Safety Considerations**: Ensure edge cases don't damage the testing
   environment
5. **Recovery Testing**: Include tests for graceful failure and recovery

## Integration with Testing

```bash
# Run edge case tests
pixi run pytest tests/edge_cases/ -m edge_case

# Test specific edge case categories
pixi run pytest tests/edge_cases/ -k "corrupted_data"
pixi run pytest tests/edge_cases/ -k "missing_metadata"
pixi run pytest tests/edge_cases/ -k "unusual_format"
```
