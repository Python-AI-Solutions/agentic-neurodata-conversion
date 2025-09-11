# Benchmark Datasets

Standard reference datasets for performance evaluation and comparison.

## Purpose

This directory contains curated datasets specifically designed for:
- **Performance Benchmarking**: Measuring conversion speed and throughput
- **Resource Usage Testing**: Evaluating memory and storage efficiency
- **Scalability Analysis**: Testing performance across different dataset sizes
- **Regression Testing**: Detecting performance changes between pipeline versions

## Dataset Categories

### Processing Speed Benchmarks
- Small datasets (< 100MB) for rapid testing
- Medium datasets (100MB - 1GB) for standard benchmarking
- Large datasets (> 1GB) for stress testing

### Memory Usage Benchmarks
- High channel count datasets for memory stress testing
- Long duration recordings for sustained memory usage
- Multi-modal datasets for complex memory patterns

### Accuracy Benchmarks
- Datasets with known correct conversion outputs
- Reference implementations for validation
- Gold standard conversions from domain experts

## Usage Guidelines

1. **Consistent Testing Environment**: Use the same hardware and software configuration
2. **Multiple Runs**: Execute benchmarks multiple times for statistical significance
3. **Resource Monitoring**: Track CPU, memory, and I/O usage during benchmarks
4. **Version Control**: Maintain benchmark results across pipeline versions
5. **Documentation**: Record benchmark conditions and system specifications

## Adding New Benchmarks

To add new benchmark datasets:
1. Ensure datasets represent realistic use cases
2. Include expected performance baselines
3. Document dataset characteristics and complexity
4. Provide reference conversion outputs when available
5. Update benchmark test suites accordingly

## Integration with Testing

Benchmark datasets integrate with the automated testing framework:
```bash
# Run performance benchmarks
pixi run pytest tests/performance/ -m benchmark

# Specific benchmark categories
pixi run pytest tests/performance/ -k "speed_benchmark"
pixi run pytest tests/performance/ -k "memory_benchmark"
```