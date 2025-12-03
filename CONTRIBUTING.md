# Contributing to Agentic Neurodata Conversion

Thank you for your interest in contributing! This document provides guidelines and technical details for developers working on this project.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Quality Standards](#code-quality-standards)
- [Testing Requirements](#testing-requirements)
- [Architecture Guidelines](#architecture-guidelines)
- [Submitting Changes](#submitting-changes)

---

## Development Setup

### Prerequisites

- **Pixi Package Manager** (required) - [Install Pixi](https://pixi.sh/)
- **Python 3.13+** (managed by Pixi automatically)
- **Anthropic API Key** (for AI features)
- **Neo4j** (optional, for knowledge graph features)

### Installation

```bash
# Clone the repository
git clone https://github.com/Python-AI-Solutions/agentic-neurodata-conversion.git
cd agentic-neurodata-conversion

# Install all dependencies via Pixi
pixi install


```

### Dependency Management

**CRITICAL:** This project uses Pixi for all dependency management.

- **Single source of truth:** `pixi.toml`
  - Runtime dependencies → `[dependencies]`
  - Dev/test tools → `[feature.dev.dependencies]`
- **DO NOT use pip or conda** - all deps must be in `pixi.toml`
- **`pyproject.toml`** contains tool configs only (Ruff, MyPy, pytest), NO dependencies
- Pre-commit hooks enforce this rule

### Running the Application

#### Option 1: Automated Startup (Recommended)

```bash
python3 scripts/startup/start_app.py
```

This script automatically:

- Configures `.env` file (interactive prompt for API key)
- Kills old processes on ports 8000 and 3000
- Cleans temporary directories
- Starts backend server (FastAPI on port 8000)
- Starts frontend server (HTTP server on port 3000)
- Runs health checks and displays status

**Must run from project root directory** (script checks for `pyproject.toml`)

#### Option 2: Manual Startup

```bash
# Terminal 1: Start backend
pixi run dev

# Terminal 2: Start frontend
cd frontend/public
python3 -m http.server 3000
```

**URLs:**

- Frontend: http://localhost:3000/chat-ui.html
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

#### Stopping Services

```bash
# Kill backend
lsof -ti:8000 | xargs kill

# Kill frontend
lsof -ti:3000 | xargs kill
```

---

## Development Workflow

### Code Quality Commands

```bash
# Lint code (Ruff)
pixi run lint

# Format code (Ruff)
pixi run format

# Type checking (MyPy)
pixi run typecheck

# Security scan (Bandit)
pixi run bandit

# Run all checks
pixi run lint && pixi run format && pixi run typecheck && pixi run test
```

### Pre-Commit Hooks

Install pre-commit hooks to automatically check code before commits:

```bash
pre-commit install
```

Pre-commit runs:

- Ruff (linting and formatting)
- MyPy (type checking)
- Bandit (security scanning)

### Running Tests

```bash
# All tests with coverage (≥60% required)
pixi run test-cov

# Unit tests only
pixi run test-unit

# Integration tests only
pixi run test-integration

# Specific test file
pixi run pytest tests/test_specific.py -v

```

### Test Coverage

```bash
# Generate coverage report
pixi run pytest --cov=agentic_neurodata_conversion --cov-report=html

# View report
open htmlcov/index.html
```

**Coverage requirement:** ≥60% for all new code

---

## Code Quality Standards

### Python Style

- **Linter:** Ruff (replaces flake8, isort, black)
- **Type hints:** Required on all functions
- **Docstrings:** Google-style for all public functions/classes
- **Line length:** 120 characters max

Example:

```python
async def convert_metadata(
    metadata: dict[str, Any],
    schema: NWBSchema,
) -> MetadataResult:
    """Convert raw metadata to NWB-compliant format.

    Args:
        metadata: Raw metadata dictionary from user input
        schema: NWB schema for validation

    Returns:
        MetadataResult with validated fields and provenance info

    Raises:
        ValidationError: If metadata fails schema validation
    """
    # Implementation here
```

### Testing Requirements

**Critical Rules:**

- ✅ Use fixtures from `tests/conftest.py` (`mock_llm_service`, `global_state`, `tmp_path`)
- ✅ `@pytest.mark.asyncio` for async tests
- ✅ `AsyncMock` for async methods
- ❌ NO `if __name__ == "__main__"` blocks
- ❌ NO hardcoded paths (use `tmp_path` fixture)
- ❌ NO shared mutable state between tests
- ❌ NO real LLM calls in unit tests (use mocks)

### Async/Await Patterns

**All I/O operations must be async:**

- File operations: `aiofiles`
- HTTP requests: `httpx.AsyncClient`
- LLM calls: `await llm_service.generate_text()`
- State updates: `await state.update_*()`

---

## Architecture Guidelines

### Agent Communication

**CRITICAL:** Agents communicate ONLY via MCP protocol. NO direct imports.

### Error Handling

- Fail fast, log everything
- Use structured logging with correlation IDs
- LLM failures → graceful degradation (optional features only)

### File Structure

```
agentic_neurodata_conversion/
├── agents/              # 3 main agents + helpers
│   ├── conversation_agent.py
│   ├── conversion_agent.py
│   ├── evaluation_agent.py
│   └── helpers/         # Conversational handler, metadata inference, etc.
├── api/
│   └── main.py          # FastAPI app (only file that imports agents)
├── models/              # State, MCP, API, metadata, validation
├── services/            # LLM service, MCP server, report service
├── prompts/             # YAML prompt templates
└── utils/               # Logging, config, helpers

tests/
├── conftest.py          # Shared fixtures
├── unit/                # Fast, isolated tests
└── integration/         # End-to-end workflow tests
```

---

## Submitting Changes

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes, commit frequently
git add .

# Run pre-commit hook
pixi run pre-commit run --all-files

# On successful pre-commit run , commit with descriptive message
git commit -m "Descriptive message"

# Push to remote
git push origin feature/your-feature-name

# Create pull request on GitHub
```

### Commit Message Guidelines

Follow conventional commits:

```
feat: Add metadata inference from filenames
fix: Resolve validation error in NWB schema
docs: Update architecture diagram
test: Add integration tests for conversion agent
refactor: Simplify MCP message routing
```

### Creating Commits

**Only create commits when requested.** Follow the git safety protocol:

```bash
# 1. Check status and diff
git status
git diff
git log -3 --oneline

# 2. Stage files
git add relevant/files

# 3. Create commit with proper format
git commit -m "$(cat <<'EOF'
Your commit message here.


EOF
)"

# 4. Verify
git status
```

**Git Safety Rules:**

- ❌ NEVER update git config
- ❌ NEVER run destructive commands (push --force, hard reset)
- ❌ NEVER skip hooks (--no-verify) unless explicitly requested
- ❌ NEVER force push to main/master

### Pull Request Process

1. **Ensure all tests pass:**

   ```bash
   pixi run lint && pixi run typecheck && pixi run test
   ```
2. **Update documentation** if needed
3. **Create PR** with description:

   - Summary of changes (2-3 bullets)
   - Test plan (how you verified it works)
   - Link to related issues
4. **Respond to review feedback** promptly
5. **Squash commits** if requested before merge

---

## Additional Resources

- **Technical Reference:** [CLAUDE.md](CLAUDE.md)
- **Project Principles:** [.specify/memory/constitution.md](.specify/memory/constitution.md)
- **Requirements:** [specs/requirements.m](specs/requirements.md)d

---

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Tag issues appropriately: `bug`, `enhancement`, `documentation`, `question`

---

**Thank you for contributing to Agentic Neurodata Conversion!**
