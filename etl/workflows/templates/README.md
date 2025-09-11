# Workflow Templates

This directory contains standardized workflow templates for common ETL operations in the agentic neurodata conversion pipeline.

## Available Templates

### Basic Conversion Workflow (`basic_conversion_workflow.py`)

A foundational template for single dataset conversion workflows.

**Features:**
- Input validation and format detection
- Metadata extraction and processing
- Conversion execution with error handling
- Output validation and reporting
- Comprehensive logging and status tracking

**Usage:**
```python
from etl.workflows.templates.basic_conversion_workflow import BasicConversionWorkflow, ConversionConfig

config = ConversionConfig(
    input_path="path/to/data",
    output_path="output.nwb",
    metadata={"session_id": "example"},
    validation_enabled=True
)

workflow = BasicConversionWorkflow(config)
result = workflow.execute()
```

### Batch Processing Workflow (`batch_processing_workflow.py`)

Template for processing multiple datasets with parallel execution capabilities.

**Features:**
- Parallel and sequential processing modes
- Comprehensive error handling and recovery
- Progress tracking and reporting
- Multiple report formats (JSON, HTML, CSV)
- Configurable worker pools and resource management

**Usage:**
```python
from etl.workflows.templates.batch_processing_workflow import BatchProcessingWorkflow, BatchConfig

config = BatchConfig(
    datasets=[
        {"input_path": "data1", "output_filename": "output1.nwb"},
        {"input_path": "data2", "output_filename": "output2.nwb"}
    ],
    output_directory="batch_output",
    parallel_workers=4
)

workflow = BatchProcessingWorkflow(config)
result = workflow.execute()
```

### DataLad Integration Workflow (`datalad_integration_workflow.py`)

Template for integrating DataLad data management capabilities into workflows.

**Features:**
- Dataset initialization and management
- Provenance tracking for all operations
- Subdataset installation and management
- Version control integration
- Data retrieval and storage operations

**Usage:**
```python
from etl.workflows.templates.datalad_integration_workflow import DataLadIntegrationWorkflow, DataLadConfig

config = DataLadConfig(
    dataset_path="my_dataset",
    enable_provenance=True,
    auto_save=True
)

workflow = DataLadIntegrationWorkflow(config)
result = workflow.initialize_dataset()
```

## Template Structure

All workflow templates follow a consistent structure:

### Configuration Classes
- **Dataclass-based configuration** with type hints and defaults
- **Validation methods** for configuration parameters
- **Flexible parameter management** with environment variable support

### Workflow Classes
- **Standardized initialization** with configuration and logging setup
- **Execute method** as the main entry point
- **Modular processing steps** with clear separation of concerns
- **Comprehensive error handling** with detailed error messages
- **Result objects** with success status and detailed information

### Result Classes
- **Success/failure status** with boolean flags
- **Detailed error messages** for debugging
- **Processing metrics** (time, memory, etc.)
- **Output paths and metadata** for downstream processing

## Customization Guidelines

### Extending Templates

To create custom workflows based on these templates:

1. **Inherit from template classes**:
   ```python
   class CustomConversionWorkflow(BasicConversionWorkflow):
       def _detect_format(self):
           # Custom format detection logic
           pass
   ```

2. **Override specific methods**:
   - `_validate_inputs()`: Custom input validation
   - `_detect_format()`: Format-specific detection logic
   - `_extract_metadata()`: Custom metadata extraction
   - `_execute_conversion()`: Specialized conversion logic

3. **Add new configuration parameters**:
   ```python
   @dataclass
   class CustomConfig(ConversionConfig):
       custom_parameter: str = "default_value"
       advanced_options: Dict[str, Any] = field(default_factory=dict)
   ```

### Best Practices

1. **Maintain Template Structure**: Keep the standard template interface for consistency
2. **Add Comprehensive Logging**: Use the established logging patterns
3. **Handle Errors Gracefully**: Implement robust error handling and recovery
4. **Document Customizations**: Provide clear documentation for custom logic
5. **Test Thoroughly**: Create unit tests for custom workflow components
6. **Follow Naming Conventions**: Use descriptive names for custom methods and classes

## Integration with MCP Server

Templates are designed to integrate seamlessly with the MCP server:

### Tool Registration
```python
from agentic_neurodata_conversion.mcp_server.server import mcp

@mcp.tool(name="run_conversion_workflow")
async def run_conversion_workflow(input_path: str, output_path: str, **kwargs):
    """Execute conversion workflow through MCP server."""
    config = ConversionConfig(
        input_path=input_path,
        output_path=output_path,
        metadata=kwargs.get("metadata", {})
    )
    
    workflow = BasicConversionWorkflow(config)
    result = workflow.execute()
    
    return {
        "success": result.success,
        "output_path": str(result.output_path) if result.output_path else None,
        "processing_time": result.processing_time,
        "error_message": result.error_message
    }
```

### Agent Coordination
Templates coordinate with internal agents:
- **Conversation Agent**: Interactive metadata collection
- **Conversion Agent**: Script generation and execution
- **Evaluation Agent**: Quality assessment and validation

## Development Workflow

### Creating New Templates

1. **Identify Common Patterns**: Look for repeated workflow logic
2. **Design Configuration**: Create comprehensive configuration classes
3. **Implement Core Logic**: Follow the established template structure
4. **Add Error Handling**: Implement robust error detection and recovery
5. **Create Documentation**: Provide usage examples and customization guides
6. **Write Tests**: Create unit tests and integration tests
7. **Integrate with Pipeline**: Connect to MCP server and agents

### Testing Templates

```bash
# Run template tests
pixi run pytest tests/unit/test_workflow_templates.py

# Test specific template
pixi run pytest tests/unit/test_basic_conversion_workflow.py

# Integration tests
pixi run pytest tests/integration/test_template_integration.py
```

## Related Documentation

- [ETL Main README](../../README.md)
- [Workflows README](../README.md)
- [MCP Server Architecture](../../../.kiro/specs/mcp-server-architecture/)
- [Agent Implementations](../../../.kiro/specs/agent-implementations/)
- [DataLad Handbook](https://handbook.datalad.org/)

## Support

For questions about workflow templates:
- Review existing template implementations
- Check the main ETL documentation
- Refer to MCP server and agent specifications
- Consult DataLad documentation for data management patterns