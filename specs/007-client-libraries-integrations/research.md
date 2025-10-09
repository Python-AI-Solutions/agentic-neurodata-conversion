# Research: Client Libraries and Integrations

**Feature**: 007-client-libraries-integrations
**Date**: 2025-10-06
**Status**: Complete

## Research Questions

### 1. MCP Protocol Best Practices

**Decision**: Use official MCP Python SDK with JSON-RPC 2.0 transport layer

**Rationale**:
- MCP (Model Context Protocol) is a standardized protocol for AI agent communication
- JSON-RPC 2.0 provides well-defined request/response patterns with error handling
- Stdio transport is simplest for local process communication
- Official SDK provides client primitives, transport abstractions, and type safety

**Alternatives Considered**:
- Raw WebSocket implementation: More complex, requires additional error handling
- gRPC: Overkill for local communication, adds unnecessary complexity
- REST API: Not real-time friendly, doesn't support streaming well

**Implementation Approach**:
- Use `mcp` package from PyPI (official SDK)
- Implement ClientSession wrapper for connection management
- Use stdio transport for server communication
- Add connection pooling for concurrent requests

**References**:
- MCP SDK documentation: https://modelcontextprotocol.io/
- JSON-RPC 2.0 spec: https://www.jsonrpc.org/specification

---

### 2. Python Async Patterns for Streaming

**Decision**: Use asyncio with aiohttp for async operations, support both sync and async APIs

**Rationale**:
- Asyncio is Python's standard async framework (Python 3.8+)
- Streaming responses require async generators for memory efficiency
- Sync wrapper using asyncio.run() for synchronous API compatibility
- aiohttp provides async HTTP client for potential future REST endpoints

**Alternatives Considered**:
- Sync-only with threading: Doesn't scale well for I/O-bound operations
- Trio/anyio: Additional dependency, asyncio is standard library
- gevent/greenlets: Monkey-patching approach is fragile

**Implementation Approach**:
```python
# Async API (preferred)
async with MCPClient(config) as client:
    async for progress in client.convert_async(request):
        print(progress)

# Sync API (convenience wrapper)
client = MCPClient(config)
result = client.convert(request)  # Blocks until complete
```

**Key Patterns**:
- AsyncContextManager for resource cleanup
- Async generators for streaming
- asyncio.Queue for backpressure handling
- Sync wrappers using asyncio.run() in new event loop

---

### 3. CLI Framework Selection

**Decision**: Use Click framework for CLI implementation

**Rationale**:
- Click is industry standard for Python CLIs (used by Flask, pip, etc.)
- Excellent documentation and ecosystem support
- Automatic help generation and type validation
- Support for nested commands and command groups
- Progress bars and styling built-in (via click.progressbar, click.style)

**Alternatives Considered**:
- Typer: Newer, uses type hints, but less mature ecosystem
- argparse: Standard library but verbose and lacks features
- fire: Too magical, poor error messages

**Implementation Approach**:
```python
@click.group()
@click.option('--config', type=click.Path())
@click.pass_context
def cli(ctx, config):
    """Neurodata conversion CLI tool."""
    ctx.obj = load_config(config)

@cli.command()
@click.argument('input_path')
@click.option('--output', '-o')
@click.pass_obj
def convert(config, input_path, output):
    """Convert neuroscience data to NWB format."""
    # Implementation
```

**Key Features**:
- Command groups for organize subcommands
- Click.Path for file validation
- Click.progressbar for progress indicators
- Click.echo for output (supports colors, paging)
- Click.confirm for interactive prompts

---

### 4. Cross-Platform Compatibility Strategies

**Decision**: Use pathlib for paths, platform.system() for OS detection, subprocess for process management

**Rationale**:
- pathlib is cross-platform and Python 3.4+ standard
- Avoid os.path in favor of pathlib.Path
- subprocess.Popen works consistently across platforms
- Use shutil for file operations (cross-platform)

**Platform-Specific Considerations**:

**Windows**:
- Use `sys.executable` to find Python interpreter
- Handle backslash paths with pathlib
- Use `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` for clean process handling

**macOS/Linux**:
- Use fork/exec for subprocess
- Handle SIGTERM/SIGINT for graceful shutdown
- Respect XDG Base Directory specification for config

**Implementation Approach**:
```python
from pathlib import Path
import platform
import subprocess

# Cross-platform paths
config_dir = Path.home() / ".neuroconv"
if platform.system() == "Windows":
    config_dir = Path(os.getenv("APPDATA")) / "neuroconv"

# Cross-platform subprocess
python_exe = sys.executable
proc = subprocess.Popen(
    [python_exe, "-m", "mcp_server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
```

**Testing Strategy**:
- Use pytest-timeout for cross-platform timeout handling
- Mock subprocess calls in unit tests
- Integration tests on GitHub Actions (Windows, macOS, Linux)

---

### 5. Testing Strategies for MCP Clients

**Decision**: Three-tier testing - unit tests, integration tests with mock server, contract tests

**Rationale**:
- Unit tests verify client logic without I/O
- Mock MCP server for integration tests (fast, deterministic)
- Contract tests verify protocol compliance
- pytest-asyncio for async test support
- pytest-mock for mocking

**Testing Tiers**:

**1. Unit Tests** (fast, isolated):
```python
# Test client logic without MCP server
def test_request_serialization():
    request = ConversionRequest(input_path="/data/test.nwb")
    assert request.to_json_rpc() == {...}

async def test_connection_retry():
    client = MCPClient(config)
    with pytest.raises(ConnectionError):
        await client.connect(max_retries=3)
```

**2. Integration Tests** (mock server):
```python
# Use pytest fixture with mock MCP server
@pytest.fixture
async def mock_mcp_server():
    server = MockMCPServer()
    await server.start()
    yield server
    await server.stop()

async def test_conversion_workflow(mock_mcp_server):
    client = MCPClient(config)
    result = await client.convert_async(request)
    assert result.status == "success"
```

**3. Contract Tests** (protocol compliance):
```python
# Verify JSON-RPC 2.0 compliance
def test_request_contract():
    request = client._build_request("convert", {...})
    assert "jsonrpc" in request
    assert request["jsonrpc"] == "2.0"
    assert "id" in request
    assert "method" in request
```

**Mock Server Implementation**:
- Use asyncio.StreamReader/StreamWriter for stdio simulation
- JSON-RPC message parsing and response generation
- Configurable delays and errors for testing edge cases
- Fixture provides common test scenarios

**Coverage Goals**:
- Unit tests: 90%+ coverage
- Integration tests: All user workflows from spec
- Contract tests: All protocol methods

**Tools**:
- pytest (test framework)
- pytest-asyncio (async test support)
- pytest-mock (mocking)
- pytest-cov (coverage reporting)
- hypothesis (property-based testing for edge cases)

---

## Technical Decisions Summary

| Area | Decision | Key Dependencies |
|------|----------|------------------|
| MCP Protocol | Official MCP SDK with JSON-RPC | `mcp` |
| Async Framework | asyncio + aiohttp | `aiohttp`, `asyncio` |
| CLI Framework | Click | `click` |
| HTTP Client | aiohttp (async) | `aiohttp` |
| Data Validation | Pydantic v2 | `pydantic>=2.0` |
| Testing | pytest + pytest-asyncio | `pytest`, `pytest-asyncio`, `pytest-mock` |
| Path Handling | pathlib (stdlib) | - |
| Process Management | subprocess (stdlib) | - |
| Configuration | YAML/JSON with Pydantic | `pyyaml`, `pydantic` |

---

## Python Version Support

**Decision**: Support Python 3.8 through 3.12

**Rationale**:
- Python 3.8: Oldest version with mature asyncio (released Oct 2019)
- Python 3.12: Latest stable (released Oct 2023)
- Covers 95%+ of current Python installations
- asyncio stable across this range
- Type hints compatible (use `typing.List` not `list` for 3.8)

**Version-Specific Considerations**:
- Python 3.8: Use `typing.List`, `typing.Dict` (not built-in generics)
- Python 3.9+: Can use `list[str]`, `dict[str, any]` syntax
- Python 3.10+: Can use union types `str | None` (use `Optional[str]` for 3.8-3.9)
- Use conditional imports for compatibility

**Testing Matrix**:
- Run tests on Python 3.8, 3.10, 3.12 in CI
- Use pyupgrade to catch version-specific issues

---

## Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Client initialization | <50ms | Time to create MCPClient instance |
| Connection establishment | <200ms | Time to connect to MCP server |
| Sync API overhead | <100ms | Time for sync wrapper around async call |
| Async API response | <500ms | Time to get first response chunk |
| Streaming chunk delivery | <50ms | Time between chunks |
| Memory per connection | <10MB | RSS growth per client instance |
| Concurrent connections | 10+ | Number of simultaneous clients |

**Optimization Strategies**:
- Connection pooling to reduce connection overhead
- Lazy loading of modules to reduce startup time
- Streaming responses to limit memory usage
- Backpressure handling to prevent memory exhaustion

---

## Security Considerations

**Decision**: Input validation, no authentication (local-only communication)

**Rationale**:
- Client communicates with local MCP server over stdio (trusted)
- No network exposure, no authentication needed
- Validate all user inputs to prevent injection
- Sanitize file paths to prevent directory traversal

**Security Measures**:
- Pydantic validation for all inputs
- Path validation using pathlib (resolve, is_relative_to)
- No shell=True in subprocess calls
- JSON-RPC prevents command injection
- Validate server responses to prevent malicious payloads

**Not Required** (out of scope):
- TLS/SSL (stdio transport)
- Authentication/authorization (local-only)
- API keys (no network exposure)

---

## Logging and Observability

**Decision**: Python logging module with structured logging support

**Implementation**:
- Use `logging` standard library
- Structured logging with JSON formatting option
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- CLI flag: `--log-level` to control verbosity
- Environment variable: `NEUROCONV_LOG_LEVEL`

**Log Categories**:
- `neuroconv_client.mcp`: Protocol-level logs
- `neuroconv_client.connection`: Connection management
- `neuroconv_client.cli`: CLI operations
- `neuroconv_client.stream`: Streaming operations

**Example Configuration**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Structured logging for programmatic use
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': record.created,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        })
```

---

## Configuration Management

**Decision**: YAML configuration files with environment variable overrides

**Configuration Hierarchy** (precedence order):
1. CLI flags (highest priority)
2. Environment variables
3. Configuration file (~/.neuroconv/config.yaml)
4. Default values

**Configuration Schema**:
```yaml
# ~/.neuroconv/config.yaml
server:
  command: "python -m agentic_neurodata_conversion.mcp_server"
  timeout: 30

client:
  retry_max_attempts: 3
  retry_backoff_factor: 2
  request_timeout: 60

logging:
  level: INFO
  format: text  # text or json

output:
  format: json  # json, yaml, or text
```

**Environment Variables**:
- `NEUROCONV_SERVER_COMMAND`
- `NEUROCONV_LOG_LEVEL`
- `NEUROCONV_CONFIG_PATH`

**Implementation**:
```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import yaml

class ServerConfig(BaseModel):
    command: str = "python -m agentic_neurodata_conversion.mcp_server"
    timeout: int = 30

class ClientConfig(BaseSettings):
    server: ServerConfig = ServerConfig()

    class Config:
        env_prefix = "NEUROCONV_"
        yaml_file = "~/.neuroconv/config.yaml"
```

---

## Error Handling Strategy

**Error Categories**:

1. **Connection Errors**: Server unreachable, connection lost
   - Retry with exponential backoff
   - Surface clear error messages

2. **Protocol Errors**: Invalid JSON-RPC, unsupported methods
   - Fail fast with protocol error details
   - Log for debugging

3. **Validation Errors**: Invalid inputs, schema mismatches
   - Return validation errors to user
   - Suggest corrections

4. **Server Errors**: Conversion failures, server crashes
   - Surface server error messages
   - Provide retry/recovery options

**Error Response Format**:
```python
class ErrorResponse(BaseModel):
    code: int  # JSON-RPC error code
    message: str
    data: Optional[dict] = None  # Additional context

    # Suggested actions for user
    suggestions: list[str] = []
```

**CLI Error Handling**:
- Exit codes: 0 (success), 1 (user error), 2 (server error), 3 (connection error)
- Colored error output (red for errors)
- Actionable error messages with suggestions

---

## Dependencies Analysis

**Core Dependencies** (required):
- `mcp>=0.1.0` - Official MCP SDK
- `pydantic>=2.0.0` - Data validation
- `click>=8.0.0` - CLI framework
- `aiohttp>=3.8.0` - Async HTTP client
- `pyyaml>=6.0` - YAML configuration

**Development Dependencies** (testing/dev):
- `pytest>=7.0.0` - Test framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-mock>=3.10.0` - Mocking
- `pytest-cov>=4.0.0` - Coverage
- `black>=23.0.0` - Code formatting
- `ruff>=0.1.0` - Linting
- `mypy>=1.0.0` - Type checking

**Optional Dependencies**:
- `hypothesis>=6.0.0` - Property-based testing
- `rich>=13.0.0` - Enhanced CLI output (if needed)

---

## Completion Checklist

- [x] MCP protocol best practices researched
- [x] Async patterns for streaming defined
- [x] CLI framework selected (Click)
- [x] Cross-platform compatibility strategy defined
- [x] Testing strategies documented
- [x] Python version support decided (3.8-3.12)
- [x] Performance targets established
- [x] Security considerations documented
- [x] Logging and observability planned
- [x] Configuration management designed
- [x] Error handling strategy defined
- [x] Dependencies analyzed

**Status**: Research phase complete - ready for Phase 1 (Design)
