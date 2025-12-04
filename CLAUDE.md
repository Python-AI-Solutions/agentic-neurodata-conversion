# Technical Reference - Agentic Neurodata Conversion

**Setup**: Python 3.13+ via Pixi (not pip). Copy `.env.example` → `.env`, add `ANTHROPIC_API_KEY`

**Dependencies**: Single source of truth in `pixi.toml` - runtime deps in `[dependencies]`, dev/test tools in `[feature.dev.dependencies]`. `pyproject.toml` has NO dependencies (tool configs only). Never duplicate deps. Pre-commit hook enforces this.

**Start**: `pixi run dev` (backend) | `cd frontend/public && python3 -m http.server 3000` (frontend)

**Full Restart**: Kill processes (`lsof -ti:8000 | xargs kill`, `lsof -ti:3000 | xargs kill`) → Start backend → Start frontend

**Docs**: [Constitution](.specify/memory/constitution.md)

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

**KG Service**: `export NEO4J_PASSWORD=<password> && pixi run uvicorn agentic_neurodata_conversion.kg_service.main:app --host 0.0.0.0 --port 8001`
- Requires Neo4j running at bolt://localhost:7687
- Access at http://localhost:8001 (endpoints: /api/v1/normalize, /api/v1/validate, /api/v1/observations)

**Frontend**: `cd frontend/public && python3 -m http.server 3000` → http://localhost:3000/chat-ui.html

### Phase-Based Development Protocol

**CRITICAL**: When working on multi-phase implementations (identified by phase numbers in docs/implementation guides):

**Before Starting Any Phase:**

1. ✅ **Read complete phase requirements** from implementation guide
2. ✅ **List all deliverables** (files, database state, tests, verification commands)
3. ✅ **Check current state** - what exists vs. what needs creation
4. ✅ **Present scope to user** before beginning implementation

**After Completing a Phase:**

1. ✅ **Run verification checklist** against implementation guide
2. ✅ **Verify each deliverable** in this EXACT order:
   - **Implementation Files**: Use `ls`, `cat`, or `Read` to confirm existence and content
   - **Database State**: Query Neo4j/DB to confirm data loaded (e.g., `MATCH (n:NodeType) RETURN count(n)`)
   - **Services**: Start services and test endpoints/health checks
   - **⚠️ TESTS (MANDATORY)**: If implementation guide specifies tests, they MUST be created and passing
     - Create test files (unit + integration as specified)
     - Run tests: `pixi run pytest tests/kg_service/test_phase*.py -v`
     - Verify all tests pass (or skip gracefully with clear reason)
     - ❌ Phase is NOT complete until tests exist and pass
3. ✅ **Present verification to user** in this format:

   ```
   ## Phase X Verification

   **Deliverables** (from implementation guide):
   - [✅] Implementation File 1 - Created at path/to/file (X lines)
   - [✅] Implementation File 2 - Created at path/to/file (X lines)
   - [✅] Database State - Y nodes loaded (verification query result)
   - [✅] Service Running - Health check passes
   - [✅] **TESTS** - Z tests created and passing
     - Unit tests: path/to/test_unit.py (N tests)
     - Integration tests: path/to/test_integration.py (M tests)
   - [❌] Missing item - Not found/failed

   **Verification Evidence:**
   ```bash
   # 1. Files created
   $ ls -lh agentic_neurodata_conversion/kg_service/services/*.py tests/kg_service/*.py
   [output showing all files including test files]

   # 2. Database state
   $ MATCH (n:NodeType) RETURN count(n)
   [output showing node counts]

   # 3. Service health
   $ curl -s http://localhost:8001/health
   [output showing healthy status]

   # 4. TESTS PASSING (CRITICAL)
   $ pixi run pytest tests/kg_service/test_phaseX*.py -v
   [output showing all tests passing]
   ```

   **Status**: X of Y deliverables complete (❌ NOT COMPLETE if tests missing)
   ```

4. ✅ **Wait for user confirmation** before proceeding to next phase
5. ✅ **Fix any gaps immediately** if verification shows missing deliverables

**Absolute Rules:**

- ❌ **NEVER** trust session summaries stating "Phase X Complete" without verification
- ❌ **NEVER** proceed to next phase with incomplete deliverables
- ❌ **NEVER** skip verification steps "to save time"
- ❌ **NEVER** mark a phase complete without creating tests if the implementation guide specifies them
- ❌ **NEVER** accept "I'll add tests later" - tests are part of the phase deliverables
- ✅ **ALWAYS** verify against the source implementation guide, not memory
- ✅ **ALWAYS** run actual commands to verify state (don't assume)
- ✅ **ALWAYS** list test files explicitly in verification report

**Example Verification Commands:**

```bash
# 1. File verification (implementation + tests)
ls -lh agentic_neurodata_conversion/kg_service/scripts/*.py tests/kg_service/test_phase*.py
wc -l agentic_neurodata_conversion/kg_service/services/kg_service.py

# 2. Database verification (Neo4j)
MATCH (t:OntologyTerm) RETURN count(t)
MATCH (f:SchemaField) RETURN count(f)

# 3. Service verification
curl -s http://localhost:8001/health | python -m json.tool

# 4. TEST VERIFICATION (MANDATORY for phase completion)
# Count test files for this phase
ls tests/kg_service/test_phaseX*.py tests/kg_service/**/test_*.py 2>/dev/null | wc -l

# Run all phase tests
pixi run pytest tests/kg_service/test_phaseX*.py -v --tb=short

# Verify test count matches implementation guide
pixi run pytest tests/kg_service/test_phaseX*.py --co -q | grep "collected"
```

**When to Use This Protocol:**

- Any work with numbered phases (Phase 0, Phase 1, Phase 2, etc.)
- Multi-step implementations following a guide/plan
- When user says "proceed step by step" or "thoroughly according to [guide]"

---

## File Structure

**Main Package** (`agentic_neurodata_conversion/`):

- `agents/` - 3 main + 15 helpers (conversational_handler, metadata_inference, format_detector, etc.)
- `api/main.py` - FastAPI app, agent registration
- `kg_service/` - Knowledge Graph service (Neo4j ontology validation)
  - `api/v1/` - normalize, validate, observations endpoints
  - `models/` - observation, ontology_term, schema_field
  - `services/` - kg_service, observation_service
  - `db/` - neo4j_connection
  - `ontologies/` - JSON ontology subsets (NCBI, UBERON, PATO)
- `models/` - state, mcp, api, metadata, validation
- `services/` - llm_service, mcp_server, report_service, log_manager, templates
- `prompts/` - YAML templates

**Frontend**: `frontend/public/chat-ui.html` (static, WebSocket client)

**Tests**: `tests/` (unit, integration, conftest.py)
- `tests/kg_service/` - KG service tests (unit + integration)

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
