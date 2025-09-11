# Conversion Examples

This directory contains specific conversion workflow examples demonstrating how to convert various types of neuroscience data to NWB format using the Agentic Neurodata Conversion MCP Server.

## Overview

These examples show real-world conversion scenarios with different data formats, experimental setups, and conversion requirements. Each example includes:

- Dataset description and structure
- Required file mappings
- Conversion configuration
- Expected outputs and validation results

## Example Categories

### Electrophysiology Examples
- **SpikeGLX Recordings**: Converting Neuropixels data from SpikeGLX format
- **Open Ephys**: Converting Open Ephys recording sessions
- **Blackrock**: Converting Blackrock Microsystems data
- **Neuralynx**: Converting Neuralynx acquisition system data

### Behavioral Examples
- **Video Tracking**: Converting behavioral video and tracking data
- **Task Events**: Converting behavioral task events and trial structure
- **Stimulus Presentation**: Converting stimulus timing and parameters

### Imaging Examples
- **Two-Photon Calcium Imaging**: Converting calcium imaging data
- **Widefield Imaging**: Converting widefield optical imaging
- **Fiber Photometry**: Converting fiber photometry recordings

## Usage

Each example directory contains:

```
example_name/
├── README.md              # Detailed example documentation
├── dataset_info.json      # Dataset metadata and structure
├── files_mapping.json     # File type to path mappings
├── conversion_config.json # Conversion parameters
└── expected_output/       # Expected NWB structure and validation results
```

### Running Examples

1. **Start MCP Server**:
   ```bash
   pixi run server
   ```

2. **Use Python Client**:
   ```python
   from examples.python_client.workflow_example import MCPWorkflowClient
   
   client = MCPWorkflowClient()
   
   # Load example configuration
   with open("examples/conversion-examples/spikeglx_example/files_mapping.json") as f:
       files_map = json.load(f)
   
   # Run conversion
   result = client.run_full_pipeline(
       dataset_dir="path/to/spikeglx/data",
       files_map=files_map
   )
   ```

3. **Use CLI Wrapper**:
   ```bash
   python examples/integration_patterns/cli_wrapper.py pipeline \
       /path/to/data \
       --files-map '{"recording": "recording.bin", "sync": "sync.dat"}'
   ```

## Adding New Examples

To add a new conversion example:

1. Create a new directory with a descriptive name
2. Add comprehensive documentation in README.md
3. Include all necessary configuration files
4. Test with real or synthetic data
5. Document expected outputs and common issues
6. Update this main README with the new example

## Integration with MCP Server

These examples are designed to work with the MCP server tools:

- **dataset_analysis**: Analyzes dataset structure and extracts metadata
- **conversion_orchestration**: Generates and executes conversion scripts
- **evaluate_nwb_file**: Validates and evaluates output NWB files
- **generate_knowledge_graph**: Creates knowledge graphs from NWB data

## Troubleshooting

Common issues and solutions:

1. **File Path Issues**: Ensure all file paths in mappings are correct and accessible
2. **Format Detection**: Verify that data formats are supported and properly detected
3. **Metadata Extraction**: Check that required metadata is available in source files
4. **Validation Errors**: Review NWB validation results and fix data structure issues

For more help, see:
- Main examples documentation: `examples/README.md`
- Python client guide: `examples/python_client/README.md`
- Integration patterns: `examples/integration_patterns/README.md`
