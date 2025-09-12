# Workflows

This directory contains ETL workflow definitions, templates, and automation
scripts for the agentic neurodata conversion pipeline.

## Purpose

The workflows directory provides:

- **Standardized Processes**: Reusable templates for common conversion tasks
- **Automation Scripts**: Batch processing and pipeline orchestration
- **Quality Assurance**: Validation and testing workflows
- **Data Preparation**: Scripts for conditioning and preprocessing data

## Directory Structure

```
workflows/
├── condense-nwb-spec/              # NWB specification condensation
├── condense-nwb-linkml-spec/       # LinkML specification processing
├── create-evaluation-rubric/       # Evaluation criteria generation
├── create-synthetic-messy-datasets/ # Test data generation
├── fine-tune-openai-model/         # Model training workflows
└── [templates/]                    # Workflow templates (to be created)
```

## Workflow Categories

### Data Preparation Workflows

- **Format Detection**: Automated identification of data acquisition systems
- **Metadata Extraction**: Parsing experimental protocols and parameters
- **Data Validation**: Quality checks and integrity verification
- **Preprocessing**: Standardization and conditioning of raw data

### Conversion Workflows

- **Template Generation**: Creating NeuroConv conversion scripts
- **Batch Processing**: Converting multiple datasets efficiently
- **Error Handling**: Robust processing with failure recovery
- **Progress Tracking**: Monitoring conversion pipeline status

### Quality Assurance Workflows

- **Validation Testing**: Ensuring NWB compliance and standards
- **Regression Testing**: Comparing outputs across pipeline versions
- **Performance Benchmarking**: Measuring conversion speed and resource usage
- **Report Generation**: Creating detailed conversion summaries

### Model Training Workflows

- **Data Curation**: Preparing training datasets for LLM fine-tuning
- **Model Training**: Automated training pipeline execution
- **Evaluation**: Testing model performance on conversion tasks
- **Deployment**: Integrating trained models into the pipeline

## Workflow Templates

### Basic Conversion Template

```python
# Template structure for conversion workflows
def conversion_workflow(input_path, output_path, metadata):
    """
    Standard template for neuroscience data conversion.

    Args:
        input_path: Path to raw data files
        output_path: Destination for NWB file
        metadata: Experimental metadata dictionary

    Returns:
        ConversionResult with status and details
    """
    # 1. Validate inputs
    # 2. Detect data format
    # 3. Extract metadata
    # 4. Generate conversion script
    # 5. Execute conversion
    # 6. Validate output
    # 7. Generate report
    pass
```

### Batch Processing Template

```python
# Template for processing multiple datasets
def batch_conversion_workflow(dataset_list, config):
    """
    Process multiple datasets with consistent parameters.

    Args:
        dataset_list: List of dataset paths or configurations
        config: Global configuration parameters

    Returns:
        BatchResult with individual conversion results
    """
    # 1. Initialize batch processing
    # 2. Validate all inputs
    # 3. Process datasets in parallel/sequence
    # 4. Aggregate results
    # 5. Generate batch report
    pass
```

## DataLad Integration

Workflows are version-controlled and tracked through DataLad:

```python
import datalad.api as dl

# Save workflow changes
dl.save(dataset=".", path="etl/workflows/", message="Update conversion template")

# Track workflow execution
dl.run(
    cmd="python workflow_script.py",
    inputs=["input_data/"],
    outputs=["results/"],
    message="Execute conversion workflow"
)

# Create workflow provenance
dl.run_procedure("workflow_template", dataset=".")
```

## Workflow Execution

### Manual Execution

```bash
# Run individual workflows
pixi run python etl/workflows/condense-nwb-spec/condense_spec.py

# Execute with parameters
pixi run python etl/workflows/create-evaluation-rubric/generate_rubric.py --config config.yaml
```

### MCP Server Integration

Workflows integrate with the MCP server for automated execution:

```python
# Execute through MCP tools
await mcp_server.execute_tool("run_conversion_workflow", {
    "workflow_name": "basic_conversion",
    "input_path": "/path/to/data",
    "output_path": "/path/to/output"
})
```

## Creating New Workflows

### Workflow Development Process

1. **Define Requirements**: Specify inputs, outputs, and processing steps
2. **Create Template**: Use existing templates as starting points
3. **Implement Logic**: Write core processing functions
4. **Add Validation**: Include input/output validation
5. **Test Thoroughly**: Validate with test datasets
6. **Document Usage**: Create comprehensive documentation
7. **Integrate with Pipeline**: Connect to MCP server tools

### Workflow Standards

All workflows should include:

- **Clear Documentation**: Purpose, inputs, outputs, and usage examples
- **Error Handling**: Robust error detection and recovery
- **Logging**: Comprehensive logging for debugging and monitoring
- **Configuration**: Flexible parameter management
- **Testing**: Unit tests and integration tests
- **Provenance**: DataLad tracking for reproducibility

## Best Practices

1. **Modular Design**: Create reusable components and functions
2. **Configuration Management**: Use external config files for parameters
3. **Error Recovery**: Implement graceful failure handling
4. **Progress Reporting**: Provide clear status updates during execution
5. **Resource Management**: Optimize memory and CPU usage
6. **Documentation**: Maintain up-to-date usage instructions
7. **Version Control**: Use DataLad for workflow versioning

## Integration Points

### MCP Server Tools

Workflows are exposed as MCP tools for:

- **Dataset Analysis**: Automated metadata extraction
- **Conversion Orchestration**: End-to-end conversion execution
- **Quality Validation**: Automated testing and validation
- **Report Generation**: Summary and analysis reports

### Agent Coordination

Workflows coordinate with internal agents:

- **Conversation Agent**: Interactive metadata collection
- **Conversion Agent**: Script generation and execution
- **Evaluation Agent**: Quality assessment and validation
- **Knowledge Graph Agent**: Metadata enrichment and linking

## Monitoring and Debugging

### Logging Configuration

```python
import logging

# Standard logging setup for workflows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow.log'),
        logging.StreamHandler()
    ]
)
```

### Performance Monitoring

- **Execution Time**: Track workflow duration and bottlenecks
- **Resource Usage**: Monitor memory and CPU consumption
- **Success Rates**: Track conversion success and failure rates
- **Error Analysis**: Categorize and analyze failure modes

## Related Documentation

- [ETL Main README](../README.md)
- [MCP Server Architecture](../../.kiro/specs/mcp-server-architecture/)
- [Agent Implementations](../../.kiro/specs/agent-implementations/)
- [DataLad Handbook](https://handbook.datalad.org/)
