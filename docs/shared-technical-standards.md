## Shared Technical Standards

### Agent Framework

- **SDK**: Claude Agent SDK for agent implementation and MCP protocol handling
- **MCP Integration**: Agent SDK's MCP extensibility for tool calls and
  inter-agent communication
- **Context Management**: Automatic context compaction and management via Agent
  SDK
- **Agent Storage**: `.claude/agents/` directory following Agent SDK conventions

### Code Quality

- **Linting**: Ruff
- **Type Checking**: MyPy with strict mode
- **Complexity Limit**: Cyclomatic complexity <10

### Testing

- **Framework**: Pytest with async support (pytest-asyncio)
- **Coverage**: pytest-cov (≥80% CI threshold, ≥85% constitutional requirement)
- **Contract Testing**: OpenAPI schema validation

### Documentation

- **API Docs**: FastAPI auto-generated OpenAPI specs
- **Code Docs**: Docstrings for all public APIs (mkdocstrings)
- **User Docs**: MkDocs with Material theme

### Performance

- **Benchmarking**: pytest-benchmark for regression detection
