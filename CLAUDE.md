# Claude Best Practices for LLM-Assisted Data Conversion Project

## Project Overview
This project develops an LLM-assisted tool for converting experimental data to standardized formats (primarily NWB), leveraging LLMs to guide data conversion and prompt users for additional metadata while validating outputs.

## Development Environment & Tools

### Dependency Management
- **Primary Tool**: `pixi` for Python dependency management and task running
- **Configuration**: All dependencies defined in `pixi.toml`
- **Execution**: All Python scripts and workflows should be run through pixi commands
- **Rationale**: Provides reproducible environments and simplified task management

### CRITICAL: DataLad Repository Initialization
**IMPORTANT**: When initializing this project as a DataLad dataset, you MUST configure git-annex properly BEFORE adding any files to avoid development files being annexed:

1. **Set up .gitattributes FIRST** (before any DataLad operations):
```bash
# Create .gitattributes with proper annex configuration
cat > .gitattributes << 'EOF'
# Only use annex for large data files (>10MB)
* annex.backend=MD5E
**/.git* annex.largefiles=nothing

# Keep all development files in git (not annex)
*.py annex.largefiles=nothing
*.md annex.largefiles=nothing
*.txt annex.largefiles=nothing
*.yml annex.largefiles=nothing
*.yaml annex.largefiles=nothing
*.toml annex.largefiles=nothing
*.json annex.largefiles=nothing
*.sh annex.largefiles=nothing
*.cfg annex.largefiles=nothing
*.ini annex.largefiles=nothing
*.rst annex.largefiles=nothing
*.ipynb annex.largefiles=nothing
.gitignore annex.largefiles=nothing
.gitmodules annex.largefiles=nothing
.pre-commit-config.yaml annex.largefiles=nothing

# Default: only annex files larger than 10MB
* annex.largefiles=(largerthan=10mb)
EOF
```

2. **Initialize DataLad with text2git mode**:
```python
import datalad.api as dl

# Create dataset with text2git configuration
dl.create(
    path=".",
    cfg_proc="text2git",  # CRITICAL: Ensures text files stay in git
    description="LLM-guided conversion project",
    force=True
)
```

3. **Verify configuration before saving**:
```bash
# Check that development files are NOT symlinks
ls -la *.md *.toml *.py
# These should be regular files, not symlinks to .git/annex/
```

### Dataset Management
- **Primary Tool**: `datalad` for efficient dataset handling (installed via pixi)
- **IMPORTANT - DataLad Usage with Pixi**:
  - DataLad is installed as a Python package through pixi
  - **DO NOT** use `datalad` CLI commands directly
  - **DO NOT** use `pixi run datalad` or `pixi run python -m datalad` for CLI
  - **ALWAYS** use the Python API: `import datalad.api as dl`
  - Example usage:
    ```python
    import datalad.api as dl
    
    # Create a dataset
    dl.create(path="my-dataset", description="My dataset")
    
    # Save changes
    dl.save(message="Add files")
    
    # Check status
    dl.status()
    
    # Work with subdatasets
    dl.subdatasets()
    ```
  - Run scripts through pixi: `pixi run python your_script.py`
- **Use Cases**:
  - Managing large NWB datasets from DANDI
  - Handling pre-existing conversions as submodules
  - Version control for evaluation datasets
  - Efficient storage of large test datasets on remote annexes (gin.g-node.org)

### Key Technologies Stack
- **LLM Integration**: Anthropic Claude via MCP (Model Context Protocol) servers
- **Schema Definition**: LinkML for data model definitions
- **Validation**: NWB validation tools + JSON Schema validation
- **Framework**: NeuroConv for NWB conversions
- **Evaluation**: Custom evaluation framework using synthetic datasets



## Development Best Practices

### Code Execution
1. **Always use pixi**: Run all Python scripts through pixi environment
   ```bash
   pixi run python script.py
   pixi run jupyter lab
   pixi run pytest
   ```

2. **Task Definition**: Define common tasks in `pixi.toml`:
   ```toml
   [tool.pixi.tasks]
   test = "pytest tests/"
   lint = "ruff check ."
   format = "ruff format ."
   convert = "python -m llm_conversion_tool.cli"
   ```

### Dataset Management
1. **Use datalad for large datasets** (via Python API only):
   ```python
   import datalad.api as dl
   
   # Install a dataset
   dl.install(source="<dataset-url>", path="<local-path>")
   
   # Get specific files
   dl.get(path="<specific-files>")
   ```

2. **Submodule strategy for conversions**:
   - Add existing conversion repositories as datalad subdatasets using Python API
   - Keep large datasets in annexes, only download when needed
   - Example:
     ```python
     import datalad.api as dl
     
     # Add a subdataset
     dl.install(dataset=".", path="path/to/subdataset", source="<url>")
     ```

3. **Version control**: Use datalad's versioning for reproducible dataset states through the Python API

4. **Handling uninitialized subdatasets**:
   - When subdatasets show as "untracked" or aren't properly initialized:
   ```python
   import datalad.api as dl
   
   # Check subdataset status
   subdatasets = dl.subdatasets(dataset=".", return_type='list')
   
   # Install missing subdatasets
   for subds in subdatasets:
       if subds['state'] == 'absent':
           dl.install(dataset=".", path=subds['path'])
   
   # Or install all recursively (be careful with large datasets)
   dl.install(dataset=".", recursive=True, get_data=False)
   
   # To get actual data files (not just structure)
   dl.get(dataset=".", recursive=True, get_data=True)
   ```
   
   - Common issues and solutions:
     - **Subdataset not found**: Check `.gitmodules` for correct URLs
     - **Permission denied**: Files may be locked by git-annex, use `git annex unlock <file>`
     - **Large file handling**: Use `dl.get()` selectively to avoid downloading unnecessary large files

### LLM Integration
1. **MCP Server Pattern**: Use MCP servers for tool integration
2. **Context Management**: Leverage Context7 for documentation retrieval
3. **Prompt Engineering**: Use structured prompts with clear evaluation criteria
4. **Token Management**: Monitor context window usage (~200k tokens = 500 pages)

### Schema and Validation
1. **LinkML First**: Define schemas in LinkML YAML
2. **Generate Multiple Formats**: Use LinkML to generate JSON Schema and Pydantic models
3. **Validation Pipeline**: LLM output → JSON Schema validation → NWB validation
4. **Iterative Refinement**: Use validation errors to improve LLM responses

## Workflow Guidelines

### Data Preparation
1. Create synthetic "messy" datasets from clean DANDI data
2. Document ground truth for evaluation
3. Store datasets efficiently using datalad annex

### LLM Interaction Flow
1. **Context Loading**: Load relevant specs and examples
2. **User Input Processing**: Parse experimental data and metadata
3. **Iterative Conversion**: LLM guides step-by-step conversion
4. **Validation Loop**: Validate, get feedback, refine
5. **Output Generation**: Produce NWB files with metadata

### Evaluation Strategy
1. **Round-trip Testing (limited real-world madness)**: DANDI → messy → restored → validation
2. **Real-world Testing (likely too challenging to create ourselves but maybe others can share)**: OSF/Zenodo messy datasets
3. **Metrics**: Validation success rate (taken with a pinch of salt), how many of the gotchas from pre-existing conversions can be found to be true.

## Error Handling & Debugging

### Common Issues
1. **Memory Management**: Large datasets may require streaming processing
2. **Context Window**: Monitor token usage, implement chunking strategies
3. **Validation Failures**: Implement clear error messages and suggestions
4. **Dataset Access**: Handle datalad download failures gracefully

### Debugging Tools
1. **MCP Inspector**: For debugging MCP server interactions
2. **NWB Validation**: Use PyNWB validation with detailed error reporting
3. **Logging**: Comprehensive logging for LLM interactions and conversions

## Performance Considerations

### Optimization Strategies
1. **Lazy Loading**: Only load necessary dataset portions
2. **Caching**: Cache processed specs and common conversions
3. **Parallel Processing**: Use multiprocessing for batch conversions
4. **Smart Context**: Use contextual retrieval to minimize token usage

### Resource Management
1. **Memory**: Monitor memory usage with large NWB files
2. **Storage**: Use datalad's efficient storage for large datasets
3. **API Limits**: Implement rate limiting for LLM API calls

## Testing Strategy

### Unit Tests
- Test individual conversion components
- Mock LLM responses for deterministic testing
- Validate schema generation and parsing

### Integration Tests
- End-to-end conversion workflows
- MCP server integration
- Datalad dataset operations

### Evaluation Tests
- Synthetic dataset round-trip accuracy
- Real-world dataset conversion quality
- User experience and effort metrics

## Documentation Standards

### Code Documentation
- Comprehensive docstrings for all functions
- Type hints throughout
- Clear examples in documentation

### User Documentation
- Step-by-step conversion guides
- Troubleshooting common issues
- Best practices for data preparation

### Technical Documentation
- MCP server specifications
- Schema definitions and mappings
- Evaluation methodology and results

## Security & Privacy Considerations

### Data Handling
- No PII in test datasets
- Secure handling of experimental data
- Clear data retention policies

### LLM Interactions
- Sanitize inputs before sending to LLM
- Log interactions for debugging but respect privacy
- Clear consent for data processing

## Future Extensibility

### Modular Design
- Plugin architecture for new data types
- Extensible schema system
- Configurable LLM backends

### Scalability Considerations
- Database backend for large-scale deployments
- Distributed processing capabilities
- Multi-user support architecture

This document should evolve as the project develops and new best practices emerge.

## Development Best Practices for Claude

### Version Control & File Management
- **Never use "_v2.ext" pattern**: Always overwrite files directly - git tracks history
- **Script Management**: Always save utility scripts in the `scripts/` directory and keep them for future reference - do not delete scripts after use
- **Bash Command Quoting**: When using `python -c` in bash, use single quotes for the outer command to safely contain double quotes in Python strings:
  ```bash
  # Correct - single quotes outside, double quotes inside
  pixi run python -c 'print("Hello, world!")'
  
  # Avoid - double quotes outside require escaping
  pixi run python -c "print(\"Hello, world!\")"
  ```

### File Creation Guidelines
- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary for achieving the goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested
