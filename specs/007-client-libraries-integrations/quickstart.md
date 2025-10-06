# Quickstart Guide: MCP Client Library and CLI

**Feature**: 007-client-libraries-integrations
**Date**: 2025-10-06
**Status**: Complete

## Overview

This quickstart guide demonstrates how to use the MCP client library and CLI tool for neurodata conversion. It covers installation, basic usage, and common workflows.

---

## Installation

### Using pip

```bash
# Install from PyPI (when released)
pip install neuroconv-client

# Or install from source
git clone https://github.com/org/agentic-neurodata-conversion-2.git
cd agentic-neurodata-conversion-2
pip install -e .
```

### Requirements

- Python 3.8 or higher
- MCP server running (auto-started by client if not running)

---

## Python SDK Usage

### 1. Basic Conversion (Synchronous)

```python
from neuroconv_client import MCPClient, ConversionRequest
from pathlib import Path

# Create client with default configuration
client = MCPClient()

# Create conversion request
request = ConversionRequest(
    input_path=Path("/data/experiment_001.spike2"),
    output_path=Path("/data/output/experiment_001.nwb"),
)

# Perform conversion (blocks until complete)
response = client.convert(request)

# Check result
if response.success:
    print(f"✓ Conversion successful!")
    print(f"  Output: {response.output_path}")
    print(f"  Duration: {response.metrics.duration_seconds:.1f}s")
else:
    print(f"✗ Conversion failed:")
    for error in response.errors:
        print(f"  - {error}")
    for suggestion in response.suggestions:
        print(f"  Suggestion: {suggestion}")
```

### 2. Conversion with Progress Callback

```python
from neuroconv_client import MCPClient, ConversionRequest, ConversionProgress

def on_progress(progress: ConversionProgress):
    """Callback for progress updates."""
    update = progress.update
    print(f"[{update.stage}] {update.percent_complete:.1f}% - {update.message}")

client = MCPClient()
request = ConversionRequest(
    input_path=Path("/data/experiment_001.spike2"),
    output_path=Path("/data/output/experiment_001.nwb"),
)

# Convert with progress callback
response = client.convert(request, progress_callback=on_progress)
```

### 3. Asynchronous Conversion with Streaming

```python
import asyncio
from neuroconv_client import MCPClient, ConversionRequest

async def convert_with_streaming():
    """Async conversion with streaming progress."""

    # Use async context manager for automatic connection management
    async with MCPClient() as client:
        request = ConversionRequest(
            input_path=Path("/data/experiment_001.spike2"),
            output_path=Path("/data/output/experiment_001.nwb"),
        )

        # Stream progress updates
        async for progress in client.convert_async(request):
            update = progress.update
            print(f"[{update.stage}] {update.percent_complete:.1f}%")

            # Check if complete
            if progress.is_complete:
                break

        # Get final result
        result = await client.get_conversion_result(progress.conversion_id)
        return result

# Run async function
response = asyncio.run(convert_with_streaming())
print(f"Conversion complete: {response.success}")
```

### 4. Custom Configuration

```python
from neuroconv_client import MCPClient, MCPConfig, ServerConfig, RetryConfig

# Custom configuration
config = MCPConfig(
    server=ServerConfig(
        command="python -m agentic_neurodata_conversion.mcp_server",
        timeout=60,
    ),
    retry=RetryConfig(
        max_attempts=5,
        backoff_factor=2.0,
    ),
    request_timeout=120,
)

# Create client with custom config
client = MCPClient(config)
```

### 5. Querying Individual Agents

```python
from neuroconv_client import MCPClient, AgentType

async def query_analysis_agent():
    async with MCPClient() as client:
        # Query the analysis agent
        response = await client.query_agent(
            agent=AgentType.ANALYSIS,
            query="What is the sampling rate of this recording?",
            context={"file_path": "/data/experiment_001.spike2"}
        )

        print(f"Agent: {response.agent}")
        print(f"Response: {response.response}")
        print(f"Confidence: {response.confidence}")

        for suggestion in response.suggestions:
            print(f"Suggestion: {suggestion}")

asyncio.run(query_analysis_agent())
```

### 6. Session Management

```python
from neuroconv_client import MCPClient, MessageRole

async def conversation_example():
    async with MCPClient() as client:
        # Create a new session
        session = await client.create_session()
        print(f"Session ID: {session.id}")

        # Query orchestrator with session context
        response1 = await client.query_agent(
            agent=AgentType.ORCHESTRATOR,
            query="Can you convert this spike2 file?",
            context={"file_path": "/data/experiment_001.spike2"},
            session_id=session.id
        )
        print(response1.response)

        # Continue conversation in same session
        response2 = await client.query_agent(
            agent=AgentType.ORCHESTRATOR,
            query="What metadata do I need to provide?",
            session_id=session.id
        )
        print(response2.response)

        # Get session history
        history = await client.get_session_history(session.id)
        print(f"Total messages: {len(history)}")

asyncio.run(conversation_example())
```

### 7. Error Handling

```python
from neuroconv_client import MCPClient, ConversionRequest
from neuroconv_client.exceptions import (
    ConnectionError,
    ValidationError,
    ServerError,
)

client = MCPClient()

try:
    request = ConversionRequest(
        input_path=Path("/data/experiment_001.spike2"),
        output_path=Path("/data/output/experiment_001.nwb"),
    )
    response = client.convert(request)

except ValidationError as e:
    print(f"Validation error: {e.error.message}")
    for suggestion in e.error.suggestions:
        print(f"  Try: {suggestion}")

except ConnectionError as e:
    print(f"Connection error: {e.error.message}")
    if e.error.retry_after:
        print(f"  Retry after {e.error.retry_after} seconds")

except ServerError as e:
    print(f"Server error: {e.error.message}")
    print(f"  Details: {e.error.details}")
```

---

## CLI Tool Usage

### 1. Basic Conversion

```bash
# Simple conversion
neuroconv convert /data/experiment_001.spike2 /data/output/experiment_001.nwb

# With data format specified
neuroconv convert /data/experiment_001.dat /data/output/experiment_001.nwb \
    --format spike2

# With validation
neuroconv convert input.spike2 output.nwb --validate

# Overwrite existing file
neuroconv convert input.spike2 output.nwb --overwrite
```

### 2. Interactive Mode

```bash
# Start interactive mode
neuroconv interactive

# The CLI will prompt for inputs:
# > Input file: /data/experiment_001.spike2
# > Output file: /data/output/experiment_001.nwb
# > Data format (auto-detect): [Enter]
# > Validate output (yes): [Enter]
# > Proceeding with conversion...
```

### 3. Batch Conversion

```bash
# Convert multiple files using a config file
neuroconv batch convert-config.yaml

# With parallel processing
neuroconv batch convert-config.yaml --parallel --workers 4

# Stop on first error
neuroconv batch convert-config.yaml --stop-on-error

# Resume from checkpoint
neuroconv batch convert-config.yaml --resume
```

**Example batch config** (`convert-config.yaml`):

```yaml
items:
  - input_path: /data/experiment_001.spike2
    output_path: /data/output/experiment_001.nwb
    metadata:
      experimenter: Jane Doe
      lab: Neuroscience Lab

  - input_path: /data/experiment_002.spike2
    output_path: /data/output/experiment_002.nwb
    metadata:
      experimenter: John Smith
      lab: Neuroscience Lab

parallel: true
max_workers: 4
stop_on_error: false
checkpoint_file: /data/.batch_checkpoint.json
```

### 4. Query Agents

```bash
# Query the analysis agent
neuroconv query analysis "What is the sampling rate?" \
    --context '{"file_path": "/data/experiment_001.spike2"}'

# Query orchestrator
neuroconv query orchestrator "Can you convert this file?" \
    --session-id sess-abc123
```

### 5. Session Management

```bash
# Create a new session
neuroconv session create --metadata '{"user": "researcher_001"}'
# Output: Session created: sess-abc123

# Get session history
neuroconv session history sess-abc123

# Delete session
neuroconv session delete sess-abc123
```

### 6. Health Check

```bash
# Basic health check
neuroconv health

# Detailed health check
neuroconv health --detailed

# Output format options
neuroconv health --format json
neuroconv health --format yaml
neuroconv health --format table
```

### 7. Configuration Management

```bash
# Show current configuration
neuroconv config show

# Set configuration values
neuroconv config set server.timeout 60
neuroconv config set logging.level DEBUG

# Save configuration to file
neuroconv config save ~/.neuroconv/config.yaml

# Load configuration from file
neuroconv config load ~/.neuroconv/custom-config.yaml
```

### 8. Verbose Logging

```bash
# Enable verbose output
neuroconv convert input.spike2 output.nwb --verbose

# Set log level
neuroconv convert input.spike2 output.nwb --log-level DEBUG

# Save logs to file
neuroconv convert input.spike2 output.nwb --log-file conversion.log
```

### 9. Output Formatting

```bash
# JSON output (for piping to other tools)
neuroconv convert input.spike2 output.nwb --format json

# YAML output
neuroconv convert input.spike2 output.nwb --format yaml

# Table output (default)
neuroconv convert input.spike2 output.nwb --format table

# Plain text (minimal)
neuroconv convert input.spike2 output.nwb --format text
```

### 10. Piping and Unix-Style Chaining

```bash
# Convert and validate in pipeline
neuroconv convert input.spike2 output.nwb --format json | \
    jq '.validation.valid' | \
    grep -q true && echo "Validation passed"

# Batch process with filtering
find /data -name "*.spike2" | \
    while read file; do
        neuroconv convert "$file" "/output/$(basename $file .spike2).nwb"
    done
```

---

## Common Workflows

### Workflow 1: Simple Conversion with Validation

```python
from neuroconv_client import MCPClient, ConversionRequest
from pathlib import Path

client = MCPClient()
request = ConversionRequest(
    input_path=Path("/data/experiment_001.spike2"),
    output_path=Path("/data/output/experiment_001.nwb"),
    validate_output=True,
)

response = client.convert(request)

if response.success:
    if response.validation.valid:
        print("✓ Conversion and validation successful")
    else:
        print("⚠ Conversion succeeded but validation has warnings:")
        for warning in response.validation.warnings:
            print(f"  - {warning}")
else:
    print("✗ Conversion failed")
```

### Workflow 2: Iterative Conversion with Agent Queries

```python
import asyncio
from neuroconv_client import MCPClient, AgentType, ConversionRequest
from pathlib import Path

async def iterative_conversion():
    async with MCPClient() as client:
        # Step 1: Query analysis agent about the data
        analysis = await client.query_agent(
            agent=AgentType.ANALYSIS,
            query="Analyze this spike2 file",
            context={"file_path": "/data/experiment_001.spike2"}
        )
        print(f"Analysis: {analysis.response}")

        # Step 2: Ask orchestrator for conversion plan
        plan = await client.query_agent(
            agent=AgentType.ORCHESTRATOR,
            query="Create conversion plan for this file",
            context=analysis.context
        )
        print(f"Plan: {plan.response}")

        # Step 3: Execute conversion
        request = ConversionRequest(
            input_path=Path("/data/experiment_001.spike2"),
            output_path=Path("/data/output/experiment_001.nwb"),
            metadata=analysis.context,
        )

        async for progress in client.convert_async(request):
            print(f"{progress.update.percent_complete:.0f}% complete")
            if progress.is_complete:
                break

        # Step 4: Get evaluation
        result = await client.get_conversion_result(progress.conversion_id)
        if result.success:
            eval_response = await client.query_agent(
                agent=AgentType.EVALUATION,
                query="Evaluate this conversion result",
                context={"output_path": str(result.output_path)}
            )
            print(f"Evaluation: {eval_response.response}")

        return result

result = asyncio.run(iterative_conversion())
```

### Workflow 3: Batch Processing with Progress Tracking

```bash
#!/bin/bash
# batch_convert.sh

# Create batch config
cat > batch_config.yaml <<EOF
items:
$(find /data/input -name "*.spike2" | while read file; do
    basename=$(basename "$file" .spike2)
    echo "  - input_path: $file"
    echo "    output_path: /data/output/${basename}.nwb"
done)

parallel: true
max_workers: 4
checkpoint_file: /data/.checkpoint.json
EOF

# Run batch conversion with progress
neuroconv batch batch_config.yaml --format json > batch_result.json

# Check results
total=$(jq '.total' batch_result.json)
successful=$(jq '.successful' batch_result.json)
failed=$(jq '.failed' batch_result.json)

echo "Batch conversion complete:"
echo "  Total: $total"
echo "  Successful: $successful"
echo "  Failed: $failed"

# Generate report
if [ $failed -gt 0 ]; then
    echo "Failed conversions:"
    jq -r '.results[] | select(.status == "failed") | .input_path' batch_result.json
fi
```

### Workflow 4: Monitoring Long-Running Conversions

```python
import asyncio
from datetime import datetime
from neuroconv_client import MCPClient, ConversionRequest
from pathlib import Path

async def monitored_conversion():
    async with MCPClient() as client:
        request = ConversionRequest(
            input_path=Path("/data/large_dataset.spike2"),
            output_path=Path("/data/output/large_dataset.nwb"),
        )

        start_time = datetime.now()
        current_stage = None

        async for progress in client.convert_async(request):
            update = progress.update

            # Track stage transitions
            if update.stage != current_stage:
                current_stage = update.stage
                print(f"\n[{datetime.now()}] Entered stage: {update.stage_description}")

            # Show progress within stage
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"  {update.percent_complete:5.1f}% | "
                  f"Step {update.current_step}/{update.total_steps} | "
                  f"Elapsed: {elapsed:.0f}s | "
                  f"{update.message}")

            # Check for retries
            if progress.is_retry:
                print(f"  ⚠ Retry #{progress.retry_count}")

            if progress.is_complete:
                break

        result = await client.get_conversion_result(progress.conversion_id)

        total_time = (datetime.now() - start_time).total_seconds()
        print(f"\nConversion completed in {total_time:.1f}s")
        print(f"Status: {result.status}")

        return result

asyncio.run(monitored_conversion())
```

---

## Testing Examples

### Unit Test Example

```python
import pytest
from neuroconv_client import ConversionRequest
from pathlib import Path

def test_conversion_request_validation():
    """Test that ConversionRequest validates paths correctly."""

    # Valid request
    request = ConversionRequest(
        input_path=Path(__file__).parent / "test_data" / "test.spike2",
        output_path=Path("/tmp/test.nwb"),
    )
    assert request.input_path.exists()
    assert request.output_path.suffix == ".nwb"

    # Invalid: missing .nwb extension
    with pytest.raises(ValueError, match="must have .nwb extension"):
        ConversionRequest(
            input_path=Path(__file__),
            output_path=Path("/tmp/test.txt"),
        )
```

### Integration Test with Mock Server

```python
import pytest
import asyncio
from neuroconv_client import MCPClient, ConversionRequest
from neuroconv_client.testing import MockMCPServer

@pytest.fixture
async def mock_server():
    """Fixture providing mock MCP server."""
    server = MockMCPServer()
    await server.start()
    yield server
    await server.stop()

@pytest.mark.asyncio
async def test_conversion_with_mock_server(mock_server):
    """Test conversion using mock server."""

    # Configure client to use mock server
    client = MCPClient()
    client._server_process = mock_server.process

    async with client:
        request = ConversionRequest(
            input_path=Path("test_data/test.spike2"),
            output_path=Path("/tmp/test.nwb"),
        )

        # Collect progress updates
        progress_updates = []
        async for progress in client.convert_async(request):
            progress_updates.append(progress)
            if progress.is_complete:
                break

        # Verify progress updates
        assert len(progress_updates) > 0
        assert progress_updates[0].update.stage == "initializing"
        assert progress_updates[-1].update.stage == "completed"

        # Get final result
        result = await client.get_conversion_result(
            progress_updates[-1].conversion_id
        )
        assert result.success
```

---

## Environment Configuration

### Environment Variables

```bash
# Server configuration
export NEUROCONV_SERVER_COMMAND="python -m agentic_neurodata_conversion.mcp_server"
export NEUROCONV_SERVER_TIMEOUT=60

# Logging configuration
export NEUROCONV_LOG_LEVEL=INFO
export NEUROCONV_LOG_FORMAT=text

# Configuration file location
export NEUROCONV_CONFIG_PATH=~/.neuroconv/config.yaml

# Use in scripts
neuroconv convert input.spike2 output.nwb
```

### Configuration File (~/.neuroconv/config.yaml)

```yaml
server:
  command: "python -m agentic_neurodata_conversion.mcp_server"
  timeout: 30
  working_dir: null

client:
  retry_max_attempts: 3
  retry_backoff_factor: 2.0
  request_timeout: 60

logging:
  level: INFO
  format: text
  file: null

output:
  format: text
  color: true
  show_progress: true
```

---

## Troubleshooting

### Connection Issues

```python
from neuroconv_client import MCPClient
from neuroconv_client.exceptions import ConnectionError

client = MCPClient()

try:
    async with client:
        # Check health
        healthy = await client.health_check()
        print(f"Server healthy: {healthy}")

except ConnectionError as e:
    print(f"Connection failed: {e.error.message}")
    print("Troubleshooting steps:")
    for suggestion in e.error.suggestions:
        print(f"  - {suggestion}")
```

### Debugging with Verbose Logging

```bash
# Enable debug logging
export NEUROCONV_LOG_LEVEL=DEBUG
neuroconv convert input.spike2 output.nwb --verbose
```

### Validation Failures

```python
response = client.convert(request)

if not response.validation.valid:
    print("Validation errors:")
    for error in response.validation.errors:
        print(f"  ✗ {error}")

    print("\nSuggestions:")
    for suggestion in response.suggestions:
        print(f"  → {suggestion}")
```

---

## Completion Checklist

- [x] Installation instructions
- [x] Basic Python SDK examples (sync and async)
- [x] Agent query examples
- [x] Session management examples
- [x] Error handling examples
- [x] CLI usage examples (all major commands)
- [x] Batch processing examples
- [x] Common workflows documented
- [x] Testing examples provided
- [x] Configuration examples
- [x] Troubleshooting guide

**Status**: Quickstart guide complete - ready for implementation
