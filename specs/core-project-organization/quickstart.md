# Quickstart: Core Project Organization

**Feature**: 001-core-project-organization **Date**: 2025-10-03 **Purpose**:
Executable validation scenarios for core project organization feature

This document provides step-by-step executable scenarios to validate the
implementation of the core project organization infrastructure.

---

## Prerequisites

Before running these scenarios, ensure:

1. Repository cloned:
   `git clone https://github.com/Python-AI-Solutions/agentic-neurodata-conversion.git`
2. Environment setup: `pixi install`
3. Development tools installed: `pixi run pre-commit install`

---

## Scenario 1: Repository Navigation (5-Minute Understanding)

**User Story**: As a new developer, I can understand the project structure
within 5 minutes.

**Validation Steps**:

```bash
# 1. Navigate to repository root
cd /path/to/agentic-neurodata-conversion

# 2. Examine top-level structure
ls -la
# Expected: src/, tests/, docs/, examples/, scripts/, config/, pyproject.toml, README.md

# 3. Examine MCP server structure
tree -L 3 src/agentic_nwb_converter/mcp_server
# Expected: core/, adapters/, tools/, middleware/, state/ subdirectories

# 4. Examine agents structure
tree -L 2 src/agentic_nwb_converter/agents
# Expected: conversation/, conversion/, evaluation/, knowledge_graph/ subdirectories

# 5. Examine test organization
tree -L 2 tests
# Expected: unit/, integration/, e2e/, performance/, security/, fixtures/, mocks/

# 6. Read main README
cat README.md | head -50
# Expected: Clear project description, architecture overview, getting started section

# 7. Check for architecture documentation
ls docs/architecture/
# Expected: overview.md, mcp-server.md, agents.md, data-flow.md
```

**Success Criteria**:

- All expected directories exist
- README provides clear architectural overview
- Documentation structure is intuitive
- Time to understand: < 5 minutes

---

## Scenario 2: Add New MCP Tool (Seamless Integration)

**User Story**: As a developer, I can add a new MCP tool following standardized
patterns.

**Validation Steps**:

```bash
# 1. Generate tool from template using Copier
cd /path/to/agentic-neurodata-conversion
copier copy templates/mcp-tool src/agentic_nwb_converter/mcp_server/tools/
# Answer prompts:
#   tool_name: validate_nwb
#   tool_category: validation
#   requires_llm: false
#   timeout_seconds: 60

# 2. Verify generated files
ls -la src/agentic_nwb_converter/mcp_server/tools/validate_nwb.py
ls -la tests/unit/mcp_server/tools/test_validate_nwb.py
# Expected: Both files created with boilerplate code

# 3. Verify decorator usage
grep -n "@mcp_tool" src/agentic_nwb_converter/mcp_server/tools/validate_nwb.py
# Expected: Line containing @mcp_tool decorator with proper parameters

# 4. Run tests (should fail - TDD)
pytest tests/unit/mcp_server/tools/test_validate_nwb.py -v
# Expected: Tests fail with NotImplementedError

# 5. Implement tool logic (minimal)
# Edit validate_nwb.py to implement basic validation

# 6. Run tests again (should pass)
pytest tests/unit/mcp_server/tools/test_validate_nwb.py -v
# Expected: Tests pass

# 7. Verify tool registration
python -c "from agentic_nwb_converter.mcp_server.tools import validate_nwb; print(validate_nwb.__name__)"
# Expected: validate_nwb
```

**Success Criteria**:

- Template generates correct file structure
- Decorator automatically registers tool
- Tests follow TDD workflow
- Tool integrates seamlessly with MCP server

---

## Scenario 3: Quality Gates (Pre-commit + CI/CD)

**User Story**: As a developer, code quality checks run automatically and pass
before commit.

**Validation Steps**:

```bash
# 1. Make a code change with intentional issues
cat > test_file.py << 'EOF'
def bad_function(x,y):
    # Missing type hints, bad formatting
    result=x+y
    return result
EOF

# 2. Try to commit without pre-commit
git add test_file.py

# 3. Run pre-commit hooks
pre-commit run --files test_file.py
# Expected: Hooks fix formatting, report type check failures

# 4. Check what was fixed automatically
cat test_file.py
# Expected: Formatting corrected by ruff-format

# 5. Fix remaining issues (type hints)
cat > test_file.py << 'EOF'
def bad_function(x: int, y: int) -> int:
    """Add two numbers."""
    result = x + y
    return result
EOF

# 6. Run pre-commit again
pre-commit run --files test_file.py
# Expected: All hooks pass

# 7. Verify quality checks order
pre-commit run --all-files --verbose | grep "^- hook id:"
# Expected order: ruff-format → ruff → mypy → bandit → trailing-whitespace...

# 8. Test selective test execution
pytest -m "unit and not slow" --collect-only | grep "test session starts"
# Expected: Only fast unit tests collected

# 9. Verify coverage enforcement
pytest tests/unit/ --cov=src --cov-report=term --cov-fail-under=80
# Expected: Coverage meets or exceeds 80% threshold
```

**Success Criteria**:

- Pre-commit hooks run in correct order
- Formatters execute before linters
- Type checking catches missing type hints
- Test markers enable selective execution
- Coverage thresholds are enforced

---

## Scenario 4: Third-Party Integration (Client Patterns)

**User Story**: As a third-party developer, I can implement a client integration
using provided patterns.

**Validation Steps**:

```bash
# 1. Examine example client implementations
ls examples/clients/
# Expected: python/, typescript/, curl/, postman/

# 2. Read Python client example
cat examples/clients/python/basic_client.py
# Expected: Complete working example with imports, connection, tool calls

# 3. Copy example to create custom client
cp examples/clients/python/basic_client.py my_custom_client.py

# 4. Run example client (if MCP server is running)
# Terminal 1: Start MCP server
python -m agentic_nwb_converter.mcp_server

# Terminal 2: Run client
python examples/clients/python/basic_client.py
# Expected: Successful connection, tool list retrieved

# 5. Verify client can call tools
python -c "
from examples.clients.python.basic_client import MCPClient
client = MCPClient('http://localhost:8080')
result = client.call_tool('list-tools', {})
print(f'Available tools: {len(result)}')
"
# Expected: List of available MCP tools

# 6. Check API documentation
cat docs/api/client-integration.md | head -100
# Expected: Clear API reference with authentication, endpoints, examples

# 7. Verify OpenAPI spec exists
ls docs/api/openapi.yaml
curl http://localhost:8080/openapi.json
# Expected: Valid OpenAPI 3.0 specification
```

**Success Criteria**:

- Example clients are complete and working
- Documentation provides clear integration guide
- OpenAPI spec is available and valid
- Client can successfully call MCP tools

---

## Scenario 5: Architecture Review (MCP-Centric Compliance)

**User Story**: As a system architect, I can verify adherence to MCP-centric
architecture principles.

**Validation Steps**:

```bash
# 1. Verify no direct agent-to-agent imports
grep -r "from.*agents.*import" src/agentic_nwb_converter/agents/ | grep -v "__init__" | grep -v "base"
# Expected: Empty output (no cross-agent imports)

# 2. Check all agent communication goes through MCP server
grep -r "mcp_server" src/agentic_nwb_converter/agents/
# Expected: References to MCP server for inter-agent communication

# 3. Verify all tools are decorated
find src/agentic_nwb_converter/mcp_server/tools -name "*.py" -type f -exec grep -L "@mcp_tool" {} \;
# Expected: Only __init__.py (no missing decorators)

# 4. Check agent specialization (single responsibility)
for agent in conversation conversion evaluation knowledge_graph; do
    echo "=== $agent agent ==="
    ls src/agentic_nwb_converter/agents/$agent/
done
# Expected: Each agent has own directory with agent.py, config.py, tests/

# 5. Verify module boundaries
python << 'EOF'
import ast
import sys
from pathlib import Path

def check_imports(module_path):
    violations = []
    for py_file in Path(module_path).rglob("*.py"):
        with open(py_file) as f:
            tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "agents" in node.module:
                        # Check for agent-to-agent imports
                        if "agents" in str(py_file) and node.module.startswith("agentic_nwb_converter.agents"):
                            parts = node.module.split(".")
                            if len(parts) > 3:  # Direct agent import
                                violations.append(f"{py_file}: {node.module}")
    return violations

violations = check_imports("src/agentic_nwb_converter/agents")
if violations:
    print("VIOLATIONS FOUND:")
    for v in violations:
        print(f"  {v}")
    sys.exit(1)
else:
    print("✓ All agents follow MCP-centric architecture")
EOF
# Expected: No violations

# 6. Verify constitution compliance
grep -A 5 "Constitution Check" specs/001-core-project-organization/plan.md
# Expected: All 6 principles marked as COMPLIANT
```

**Success Criteria**:

- No direct agent-to-agent communication
- All functionality exposed through MCP tools
- Each agent has single domain responsibility
- Module boundaries are clearly enforced
- All constitutional principles satisfied

---

## Scenario 6: Agent Module Modification (Test Suite Validation)

**User Story**: As a developer, I can modify an agent and validate changes
through comprehensive test suite.

**Validation Steps**:

```bash
# 1. Identify agent to modify
cd src/agentic_nwb_converter/agents/conversation

# 2. Run existing tests before changes
pytest tests/unit/agents/conversation/ -v --cov=src/agentic_nwb_converter/agents/conversation
# Expected: Tests pass with >80% coverage

# 3. Make a change to agent logic
# Edit conversation/agent.py to add new method

# 4. Write test first (TDD)
cat >> tests/unit/agents/conversation/test_agent.py << 'EOF'

@pytest.mark.unit
@pytest.mark.agents
def test_new_conversation_method():
    """Test new conversation method."""
    agent = ConversationAgent(config=test_config)
    result = agent.new_method("test input")
    assert result is not None
    assert "processed" in result
EOF

# 5. Run tests (should fail)
pytest tests/unit/agents/conversation/test_agent.py::test_new_conversation_method -v
# Expected: Test fails (NotImplementedError or similar)

# 6. Implement the method
# Edit conversation/agent.py to implement new_method

# 7. Run tests again (should pass)
pytest tests/unit/agents/conversation/test_agent.py::test_new_conversation_method -v
# Expected: Test passes

# 8. Run full agent test suite
pytest tests/unit/agents/conversation/ -v --cov=src/agentic_nwb_converter/agents/conversation --cov-report=term
# Expected: All tests pass, coverage maintained/improved

# 9. Run integration tests
pytest tests/integration/agents/ -v -m "agents and integration"
# Expected: Integration tests pass

# 10. Verify markers work correctly
pytest --markers | grep -A 1 "agents:"
# Expected: agents marker defined with description

# 11. Check test execution time
pytest tests/unit/agents/ -v --durations=10
# Expected: Unit tests complete in <5 minutes
```

**Success Criteria**:

- TDD workflow followed (test first, then implement)
- All tests pass after implementation
- Code coverage maintained above 80%
- Integration tests validate agent interactions
- Test markers enable selective execution

---

## Configuration Validation

**Validate configuration system works correctly**:

```bash
# 1. Test configuration loading
python << 'EOF'
from agentic_nwb_converter.config import CoreConfig

# Load development config
config = CoreConfig()
print(f"Environment: {config.environment}")
print(f"Debug mode: {config.debug}")
print(f"Data root: {config.data_directory}")
assert config.debug == True  # Development default
print("✓ Development config loaded successfully")
EOF

# 2. Test environment variable override
export NWB_CONVERTER_DEBUG_MODE=false
export NWB_CONVERTER_LOG_LEVEL=INFO
python << 'EOF'
from agentic_nwb_converter.config import CoreConfig
config = CoreConfig()
assert config.debug == False
assert config.log_level == "INFO"
print("✓ Environment variable override works")
EOF

# 3. Test validation failure
python << 'EOF'
import os
os.environ["NWB_CONVERTER_DATA_ROOT"] = "/nonexistent/path"
try:
    from agentic_nwb_converter.config import CoreConfig
    config = CoreConfig()
    print("ERROR: Validation should have failed")
except Exception as e:
    print(f"✓ Validation correctly failed: {type(e).__name__}")
EOF

# 4. Verify configuration schema
python << 'EOF'
from agentic_nwb_converter.config import CoreConfig
schema = CoreConfig.model_json_schema()
print(f"✓ Configuration schema has {len(schema['properties'])} top-level properties")
print(f"  Required fields: {schema.get('required', [])}")
EOF
```

---

## DataLad Integration

**Validate DataLad Python API integration**:

```bash
# 1. Verify DataLad is available
python -c "import datalad.api as dl; print(f'DataLad version: {dl.__version__}')"
# Expected: DataLad version printed

# 2. Test dataset creation
python << 'EOF'
import datalad.api as dl
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    dataset_path = Path(tmpdir) / "test_dataset"

    # Create dataset
    ds = dl.create(path=dataset_path, annex=True)
    print(f"✓ Created dataset at {dataset_path}")

    # Verify it's a DataLad dataset
    assert ds.is_installed()
    print("✓ Dataset is properly initialized")

    # Test save operation
    test_file = dataset_path / "test.txt"
    test_file.write_text("test content")
    ds.save(path=test_file, message="Add test file")
    print("✓ File saved with provenance")
EOF

# 3. Verify no CLI usage in code
grep -r "subprocess.*datalad" src/agentic_nwb_converter/ || echo "✓ No DataLad CLI usage found"
grep -r "os.system.*datalad" src/agentic_nwb_converter/ || echo "✓ No DataLad CLI usage found"

# 4. Check DataLad integration point
python << 'EOF'
from agentic_nwb_converter.data_management import DatasetManager
print("✓ DatasetManager available for DataLad operations")
EOF
```

---

## Structured Logging

**Validate structured logging infrastructure**:

```bash
# 1. Test logging configuration
python << 'EOF'
import structlog
from agentic_nwb_converter.logging import configure_development_logging

configure_development_logging()
log = structlog.get_logger()

log.info("test_message", user_id="123", action="test")
print("✓ Structured logging configured")
EOF

# 2. Verify JSON output in production mode
python << 'EOF'
import structlog
import json
from agentic_nwb_converter.logging import configure_production_logging

configure_production_logging()
log = structlog.get_logger()

# Capture log output
import io
from contextlib import redirect_stderr

output = io.StringIO()
with redirect_stderr(output):
    log.info("production_test", request_id="abc123")

# Parse JSON
log_line = output.getvalue().strip()
if log_line:
    log_data = json.loads(log_line)
    assert "request_id" in log_data
    print("✓ Production logging outputs valid JSON")
EOF

# 3. Test correlation ID middleware
python << 'EOF'
import structlog

structlog.contextvars.bind_contextvars(request_id="test-request-123")
log = structlog.get_logger()
log.info("test_with_context")
# Should see request_id in log output
print("✓ Correlation ID context works")
structlog.contextvars.clear_contextvars()
EOF
```

---

## Summary Validation

After running all scenarios, verify:

```bash
# 1. All schemas are valid
for schema in specs/001-core-project-organization/contracts/*.schema.json; do
    python -m json.tool "$schema" > /dev/null && echo "✓ $schema is valid JSON"
done

# 2. All documentation exists
test -f specs/001-core-project-organization/plan.md && echo "✓ plan.md exists"
test -f specs/001-core-project-organization/research.md && echo "✓ research.md exists"
test -f specs/001-core-project-organization/data-model.md && echo "✓ data-model.md exists"
test -f specs/001-core-project-organization/quickstart.md && echo "✓ quickstart.md exists"

# 3. All contracts exist
test -f specs/001-core-project-organization/contracts/module_structure.schema.json && echo "✓ module_structure schema exists"
test -f specs/001-core-project-organization/contracts/configuration.schema.json && echo "✓ configuration schema exists"
test -f specs/001-core-project-organization/contracts/testing.schema.json && echo "✓ testing schema exists"
test -f specs/001-core-project-organization/contracts/documentation.schema.json && echo "✓ documentation schema exists"

# 4. Run full test suite
pytest tests/ -v -m "unit" --cov=src --cov-report=term --cov-fail-under=80
# Expected: All unit tests pass with >80% coverage

echo ""
echo "============================================"
echo "Core Project Organization Validation Complete"
echo "============================================"
```

---

## Troubleshooting

### Common Issues

**Issue**: Pre-commit hooks not running

```bash
# Solution: Reinstall hooks
pre-commit uninstall
pre-commit install
pre-commit run --all-files
```

**Issue**: Tests failing with import errors

```bash
# Solution: Reinstall in development mode
pixi run pip install -e .
```

**Issue**: Configuration validation fails

```bash
# Solution: Check environment variables
env | grep NWB_CONVERTER_
# Ensure required variables are set
```

**Issue**: DataLad operations fail

```bash
# Solution: Initialize git config
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

## Next Steps

After validating all scenarios:

1. Run `/tasks` command to generate tasks.md
2. Execute tasks in TDD order
3. Monitor quality metrics during implementation
4. Update documentation as implementation progresses
5. Run full validation suite before feature completion

---

**Document Status**: Quickstart Complete **Last Updated**: 2025-10-03
**Validation Status**: Ready for execution after implementation
