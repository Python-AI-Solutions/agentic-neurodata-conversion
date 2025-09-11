# ETL (Extract, Transform, Load) Directory

This directory contains the data processing infrastructure for the Agentic
Neurodata Conversion project. It provides organized storage for datasets,
workflow definitions, and evaluation data used throughout the conversion
pipeline.

## Directory Structure

```
etl/
├── input-data/           # Raw datasets for processing and conversion
├── workflows/            # ETL workflow definitions and templates
├── evaluation-data/      # Test and evaluation datasets
└── prompt-input-data/    # Condensed specifications for LLM prompts
```

## Purpose

The ETL directory serves as the central hub for:

- **Data Management**: Organized storage of neuroscience datasets
- **Workflow Orchestration**: Standardized ETL processes and templates
- **Evaluation Framework**: Test datasets and benchmarking data
- **DataLad Integration**: Version-controlled data management with provenance
  tracking

## DataLad Integration

This project uses DataLad for reproducible data management. The ETL directory is
designed to work seamlessly with DataLad's capabilities:

### Key Features

- **Version Control**: Track changes to datasets and workflows
- **Provenance Tracking**: Maintain complete history of data transformations
- **Distributed Storage**: Support for multiple storage backends (GitHub, GIN)
- **Reproducibility**: Ensure consistent data access across environments

### Working with DataLad

```python
import datalad.api as dl

# Install subdatasets (conversion repositories)
dl.install(dataset=".", path="etl/input-data/catalystneuro-conversions/IBL-to-nwb")

# Get specific datasets
dl.get(path="etl/input-data/specific-dataset")

# Save workflow changes
dl.save(dataset=".", path="etl/workflows/", message="Update workflow templates")

# Check status of ETL data
status = dl.status(dataset="etl", return_type='list')
```

## Workflow Templates

The `workflows/` directory contains standardized templates for common ETL
operations:

- **Data Ingestion**: Templates for importing various neuroscience data formats
- **Transformation**: Standard processing pipelines for data normalization
- **Validation**: Quality assurance workflows for converted data
- **Export**: Templates for generating final NWB files

## Data Organization Principles

1. **Separation of Concerns**: Clear distinction between input, processing, and
   output data
2. **Reproducibility**: All workflows are version-controlled and documented
3. **Scalability**: Structure supports both small test datasets and large
   production data
4. **Traceability**: Complete provenance tracking from raw data to final outputs

## Getting Started

1. **Initialize DataLad** (if not already done):

   ```python
   import datalad.api as dl
   dl.create(dataset=".", force=True)
   ```

2. **Install Required Subdatasets**:

   ```python
   # Install conversion repositories
   dl.install(dataset=".", path="etl/input-data/catalystneuro-conversions", recursive=True)
   ```

3. **Access Workflow Templates**:
   - Browse `etl/workflows/` for available templates
   - Copy and customize templates for your specific use case
   - Follow the workflow documentation in each subdirectory

## Integration with MCP Server

The ETL infrastructure integrates with the MCP (Model Context Protocol) server
to provide:

- **Dataset Analysis Tools**: Automated metadata extraction and format detection
- **Conversion Orchestration**: Workflow execution through MCP tools
- **Quality Assurance**: Validation and evaluation through standardized
  pipelines

## Best Practices

1. **Use DataLad Python API**: Always use `datalad.api` instead of CLI commands
2. **Document Workflows**: Include README files for all custom workflows
3. **Version Control**: Commit workflow changes with descriptive messages
4. **Test with Small Data**: Validate workflows with evaluation datasets first
5. **Maintain Provenance**: Use DataLad's tracking capabilities for all data
   operations

## Related Documentation

- [DataLad Handbook](https://handbook.datalad.org/)
- [NeuroConv Documentation](https://neuroconv.readthedocs.io/)
- [Project Main README](../README.md)
- [MCP Server Architecture](../.kiro/specs/mcp-server-architecture/)

## Support

For questions about ETL workflows or DataLad integration, refer to:

- Project documentation in `.kiro/specs/`
- Individual README files in each subdirectory
- DataLad community resources and documentation
