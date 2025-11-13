# Technical Reference - Agentic Neurodata Conversion

**Setup**: Python 3.13+ via Pixi (not pip). Copy `.env.example` → `.env`, add `ANTHROPIC_API_KEY`

**Start**: `pixi run dev` (backend) | `cd frontend/public && python3 -m http.server 3000` (frontend)

**Full Restart**: Kill processes (`lsof -ti:8000 | xargs kill`, `lsof -ti:3000 | xargs kill`) → Start backend → Start frontend

**Docs**: [TESTING.md](docs/guides/TESTING.md) | [Constitution](.specify/memory/constitution.md)

---

## Architecture

**3 Agents** (NO cross-imports, MCP protocol only):

- **Conversation** ([conversation_agent.py](agentic_neurodata_conversion/agents/conversation_agent.py)): User interaction, orchestration
- **Conversion** ([conversion_agent.py](agentic_neurodata_conversion/agents/conversion_agent.py)): Format detection (84+ formats), NWB conversion
- **Evaluation** ([evaluation_agent.py](agentic_neurodata_conversion/agents/evaluation_agent.py)): Validation, quality assessment

**Communication**: `MCPMessage` via `mcp_server.send_message()`. Only [api/main.py](agentic_neurodata_conversion/api/main.py) imports agents.

**State**: Centralized `GlobalState` ([models/state.py](agentic_neurodata_conversion/models/state.py)) - thread-safe, async-only

- Use enums: `ConversationPhase`, `ValidationOutcome`, `MetadataRequestPolicy`
- Track metadata provenance (`ProvenanceInfo`) for DANDI compliance
- ✅ `await state.update_*()` | ❌ Deprecated: `update_status_sync()`, `add_conversation_message()`

**Services**: Provider-agnostic (`LLMService`, `MCPServer`, `ReportService`)

- Create: `create_llm_service()` | Mock: `MockLLMService()`
- Retry: `call_with_retry()` with exponential backoff

**Error Handling**: Fail fast, log everything. LLM failures → graceful degradation (optional features only)

**I/O**: All async/await (files, network, LLM, state)

---

## Development Workflow

### Code Quality

**Commands**: `pixi run lint` | `pixi run format` | `pixi run typecheck`

**Pre-commit**: `pre-commit install` - Runs Ruff (lint & format), MyPy, Bandit before commit. Override: `git commit --no-verify`

**Full check**: `pixi run lint && pixi run format && pixi run typecheck && pixi run test`

### Testing

**Commands**:

- `pixi run test` - All tests with coverage (≥60% required)
- `pixi run test-unit` | `pixi run test-integration` - Subset only
- `pixi run pytest -n auto` - Parallel execution (pytest-xdist)

**Critical Rules**:

- ✅ Use fixtures from [conftest.py](tests/conftest.py) (mock_llm_service, global_state, tmp_path)
- ✅ `@pytest.mark.asyncio` for async tests | `AsyncMock` for async methods
- ❌ NO `if __name__ == "__main__"` blocks | NO hardcoded paths | NO shared mutable state


### Running Services

**Backend**: `pixi run dev` → http://localhost:8000 (API at `/api/*`, WebSocket at `/ws`)

**Frontend**: `cd frontend/public && python3 -m http.server 3000` → http://localhost:3000/chat-ui.html

---

## File Structure

**Main Package** (`agentic_neurodata_conversion/`):

- `agents/` - 3 main + 15 helpers (conversational_handler, metadata_inference, format_detector, etc.)
- `api/main.py` - FastAPI app, agent registration
- `models/` - state, mcp, api, metadata, validation
- `services/` - llm_service, mcp_server, report_service, log_manager, templates
- `prompts/` - YAML templates

**Frontend**: `frontend/public/chat-ui.html` (static, WebSocket client)

**Tests**: `tests/` (unit, integration, conftest.py)

**Config**: `pixi.toml`, `pyproject.toml`, `.pre-commit-config.yaml`, `.env`

---

## API Overview

**REST Endpoints**:

- `POST /api/upload` - File upload
- `POST /api/start-conversion` - Start workflow
- `POST /api/chat` - User interaction
- `GET /api/status` - Current state
- `GET /api/download/nwb` - Download converted file
- `GET /api/reports/view` - HTML report
- `POST /api/reset` - Reset session

**WebSocket**: `/ws` - Real-time updates (status, progress, validation)

---

## Critical Rules

### Architecture

- ❌ NO agent cross-imports (use MCP only)
- ✅ All I/O is async/await
- ✅ Use enums, not strings
- ✅ Log everything (structured)

### Testing

- ❌ NO `if __name__ == "__main__"` in test files
- ❌ NO hardcoded paths (use `tmp_path`)
- ❌ NO real LLM calls in unit tests
- ✅ Use conftest.py fixtures
- ✅ Mock external services

### Code

- ✅ Type hints on all functions
- ✅ Google-style docstrings
- ✅ Metadata provenance tracking
- ❌ NO silent failures
- ❌ Max 5 retries

## Environment Variables

**Required**: `ANTHROPIC_API_KEY`

## Git

**Don't commit**: `.env`, `outputs/`, `logs/`, `test_data/`, `__pycache__/`, `.pixi/`, `htmlcov/`

**Pre-commit**: Enforced automatically (Ruff, MyPy, Bandit)

---

## Quick Reference

**Constitution**: [.specify/memory/constitution.md](.specify/memory/constitution.md) - supersedes all docs

**Config Files**: [pixi.toml](pixi.toml) | [pyproject.toml](pyproject.toml)

**Version**: 2.0.0 | Python 3.13+ | Claude Sonnet 4.5
