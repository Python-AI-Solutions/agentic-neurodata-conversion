# Sample Datasets

This directory contains small sample datasets for testing, documentation, and
development purposes with the Agentic Neurodata Conversion MCP Server.

## Overview

These datasets are designed to be:

- **Small**: Quick to download and process
- **Representative**: Cover common neuroscience data formats
- **Well-documented**: Include clear metadata and structure
- **Test-friendly**: Suitable for automated testing and CI/CD

## Available Datasets

### Synthetic Datasets

- **synthetic_ephys**: Simulated electrophysiology data with spikes and LFP
- **synthetic_behavior**: Simulated behavioral tracking and task events
- **synthetic_imaging**: Simulated calcium imaging time series

### Minimal Real Datasets

- **mini_spikeglx**: Minimal SpikeGLX recording (few seconds)
- **mini_openephys**: Minimal Open Ephys session
- **mini_blackrock**: Minimal Blackrock recording

## Dataset Structure

Each dataset follows this structure:

```
dataset_name/
├── README.md              # Dataset description and metadata
├── data/                  # Raw data files
│   ├── recording.bin      # Primary recording file
│   ├── metadata.json      # Recording metadata
│   └── ...               # Additional data files
├── expected_nwb/          # Expected NWB conversion output
│   ├── converted.nwb      # Expected NWB file
│   └── validation.json    # Expected validation results
└── test_config/           # Test configuration
    ├── files_mapping.json # File mappings for conversion
    └── conversion_params.json # Conversion parameters
```

## Usage

### For Testing

```python
from examples.python_client.simple_client import SimpleMCPClient

client = SimpleMCPClient()

# Test with synthetic dataset
result = client.analyze_dataset("examples/sample-datasets/synthetic_ephys")
print(f"Analysis result: {result}")
```

### For Development

```bash
# Use CLI wrapper for quick testing
python examples/integration_patterns/cli_wrapper.py analyze \
    examples/sample-datasets/synthetic_ephys

# Run full pipeline test
python examples/integration_patterns/cli_wrapper.py pipeline \
    examples/sample-datasets/synthetic_ephys \
    --files-map '{"recording": "data/recording.bin"}'
```

### For Documentation

These datasets are used in:

- Code examples and tutorials
- API documentation
- Integration tests
- Performance benchmarks

## Dataset Details

### synthetic_ephys

- **Size**: ~1MB
- **Duration**: 10 seconds
- **Channels**: 4 electrodes
- **Sampling Rate**: 30kHz
- **Content**: Simulated spikes, LFP, and sync signals
- **Use Case**: Testing electrophysiology conversion pipelines

### synthetic_behavior

- **Size**: ~100KB
- **Duration**: 60 seconds
- **Content**: Simulated position tracking, task events, rewards
- **Use Case**: Testing behavioral data integration

### synthetic_imaging

- **Size**: ~5MB
- **Duration**: 30 seconds
- **Content**: Simulated calcium imaging with ROIs and fluorescence traces
- **Use Case**: Testing imaging data conversion

## Creating New Sample Datasets

To add a new sample dataset:

1. **Keep it small**: Aim for <10MB total size
2. **Document thoroughly**: Include comprehensive README and metadata
3. **Test conversion**: Ensure it works with the MCP server
4. **Include expected outputs**: Provide expected NWB files and validation
   results
5. **Add test configuration**: Include files mapping and conversion parameters

### Dataset Generation Scripts

For synthetic datasets, include generation scripts:

```python
# generate_synthetic_ephys.py
import numpy as np
from pathlib import Path

def generate_synthetic_ephys_data(output_dir: Path, duration: float = 10.0):
    """Generate synthetic electrophysiology data."""
    # Implementation here
    pass
```

## Integration with Testing

These datasets are used in:

- Unit tests for conversion functions
- Integration tests for full pipelines
- Performance benchmarks
- Continuous integration validation

## Data Formats Supported

Sample datasets cover these formats:

- **Binary**: Raw binary recordings (.bin, .dat)
- **HDF5**: Structured data files (.h5, .hdf5)
- **JSON**: Metadata and configuration files
- **CSV**: Behavioral and event data
- **Video**: Behavioral video files (small clips)

## Licensing and Attribution

All sample datasets are:

- **Synthetic**: Generated programmatically, no real subject data
- **Open Source**: Available under project license
- **Attribution**: Credit original data sources where applicable
- **Privacy**: No personally identifiable information

For questions about specific datasets or to contribute new samples, please see
the main project documentation.
