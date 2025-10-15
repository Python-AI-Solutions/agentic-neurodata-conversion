# Technical Research: Agentic Neurodata Conversion System

**Phase**: 0 - Outline & Research
**Date**: 2025-10-15
**Status**: Complete
**Related**: [plan.md](plan.md)

## Purpose

This document resolves all technical decisions identified as "NEEDS CLARIFICATION" in the implementation plan. Each decision is documented with chosen solution, rationale, and alternatives considered.

---

## Decision 1: MCP Server Implementation Pattern

### Decision
**Build custom MCP server** tailored to the three-agent architecture requirements.

### Rationale
1. **Specific Requirements**: Our MCP server needs custom features:
   - Agent registry with capability discovery (Story 1.1)
   - Global state context injection on every message (Story 1.3)
   - Single-session constraint enforcement (Epic 2)
   - Structured JSON logging for all message routing (Story 1.2)

2. **Simplicity**: Anthropic's MCP SDK (as of 2025-01) is designed for general-purpose MCP servers with multiple tools and complex routing. Our system has exactly 3 agents with well-defined message patterns - custom implementation is simpler.

3. **Control**: Full control over message routing logic, error handling, and context management. Can enforce defensive error handling (Constitution Principle III) without SDK abstractions.

4. **Minimal Overhead**: ~200-300 lines of Python code for our use case vs learning/configuring SDK

### Alternatives Considered

**Alternative A: Anthropic MCP SDK**
- **Pros**: Standard implementation, maintained by Anthropic, follows best practices
- **Cons**:
  - Overkill for 3-agent system
  - Requires adapting global state injection pattern
  - Additional learning curve for team
  - May abstract away defensive error handling
- **Rejected because**: Adds complexity without benefits for our simple 3-agent use case

**Alternative B: JSON-RPC library (e.g., `jsonrpcserver`)**
- **Pros**: Handles JSON-RPC 2.0 protocol details
- **Cons**:
  - Still need custom agent registry
  - Still need custom context injection
  - Adds dependency without significant value
- **Rejected because**: Doesn't solve our specific MCP requirements, just protocol layer

### Implementation Notes
- Use Pydantic `MCPMessage` schema for type safety (Appendix B)
- MCP server as singleton Python class: `MCPServer` in `src/mcp/server.py`
- Agent registry: `Dict[str, Callable]` mapping agent names to handlers
- Context injection: Attach `GlobalState` snapshot to message context before routing
- Error handling: Raise exceptions immediately on routing failures (no silent errors)

---

## Decision 2: PDF Report Generation Library

### Decision
**Use ReportLab** for PDF generation (not Quarto).

### Rationale
1. **Pure Python**: ReportLab is native Python, no external dependencies (Quarto requires R/Pandoc)
2. **Programmatic Control**: Full control over PDF layout, styling, and content from Python code
3. **LLM Integration**: Easy to integrate LLM-generated content (Stories 9.3, 9.5) directly into PDF without intermediate markdown conversion
4. **Deployment Simplicity**: No external tools needed (Pixi environment installs ReportLab via pip)
5. **Scientific Reports**: ReportLab widely used for scientific report generation in Python ecosystem

### Alternatives Considered

**Alternative A: Quarto**
- **Pros**:
  - Avoids vendor lock-in (mentioned in requirements line 1719)
  - Markdown-based templates easier to edit
  - Reproducible research standard
- **Cons**:
  - Requires external Quarto installation (not pip-installable)
  - Requires Pandoc dependency
  - LLM content needs conversion to markdown first
  - Adds complexity to Pixi environment setup
  - Overkill for programmatic report generation
- **Rejected because**: "Avoid vendor lock-in" concern is minimal (ReportLab is open-source, widely used), and operational complexity outweighs benefits

**Alternative B: WeasyPrint (HTML to PDF)**
- **Pros**: HTML/CSS templates easier than ReportLab's canvas API
- **Cons**: Requires CSS layout expertise, adds web rendering engine dependency
- **Rejected because**: ReportLab's API is simpler for structured scientific reports

### Implementation Notes
- Install: `reportlab>=3.6.0` in `pixi.toml`
- PDF template structure (Story 9.5):
  - Cover page with status badge
  - Executive summary (LLM-generated)
  - File information table
  - Evaluation results (issue counts by severity)
  - Issues detail list (if PASSED_WITH_ISSUES)
  - Quality assessment (LLM analysis)
  - Recommendations
- Generate in `src/services/report_service.py` (abstraction for future flexibility)

---

## Decision 3: WebSocket Integration with FastAPI

### Decision
**Use FastAPI native WebSocket support** (no external library).

### Rationale
1. **Built-in**: FastAPI has first-class WebSocket support via Starlette
2. **Simplicity**: No additional dependencies needed
3. **Integration**: Seamless integration with existing FastAPI routes and middleware
4. **Documentation**: Well-documented in FastAPI docs with examples
5. **Sufficient**: Our use case (Story 10.5) is simple broadcast of progress updates - no need for complex pub/sub

### Alternatives Considered

**Alternative A: Socket.IO (with python-socketio)**
- **Pros**:
  - Automatic reconnection handling
  - Fallback to HTTP long-polling
  - Room/namespace support
- **Cons**:
  - Adds dependency (python-socketio + socketio.js client)
  - Overkill for MVP (single conversion at a time)
  - Requires JavaScript client library change (not native WebSocket)
- **Rejected because**: Features not needed for MVP, adds complexity

**Alternative B: Redis Pub/Sub + WebSocket**
- **Pros**: Scalable to multi-server deployment
- **Cons**:
  - Requires Redis dependency (violates MVP "in-memory state" constraint)
  - Overkill for single-session system
- **Rejected because**: Post-MVP enhancement, not needed now

### Implementation Notes
- WebSocket endpoint: `@app.websocket("/ws")` in `src/api/websocket.py`
- Message format: `WebSocketMessage` Pydantic schema (Appendix B)
- Broadcasting: Global state updates trigger WebSocket messages to all connected clients
- Connection handling:
  - Accept unlimited connections (multiple browser tabs can watch same conversion)
  - No authentication (local deployment)
  - Close connection on conversion completion
- Client library: Native browser WebSocket API (no Socket.IO.js)

---

## Decision 4: Agent Module Packaging Strategy

### Decision
**Use Python package structure with explicit MCP imports only** - no enforcement mechanism needed.

### Rationale
1. **Convention Over Enforcement**: Python's explicit imports make violations obvious in code review
2. **Testing Catches Violations**: Unit tests import agents individually - circular dependencies fail immediately
3. **MCP Server as Gatekeeper**: All agent communication goes through MCP server - physical separation of concerns
4. **Linting Support**: Add `pylint` check for inter-agent imports (custom rule or manual review)
5. **Simplicity**: No complex plugin systems, entry points, or namespace packages needed

### Alternatives Considered

**Alternative A: Entry Points (setuptools)**
- **Pros**: True plugin architecture, agents loaded dynamically
- **Cons**:
  - Overkill for 3 agents in monorepo
  - Adds installation complexity
  - Harder to debug
- **Rejected because**: Over-engineering for MVP

**Alternative B: Namespace Packages**
- **Pros**: Enforces no cross-imports at package level
- **Cons**:
  - Complex directory structure
  - Breaks IDE autocomplete
  - Difficult to navigate codebase
- **Rejected because**: Developer experience degradation not worth enforcement benefit

**Alternative C: Import Hook (sys.meta_path)**
- **Pros**: Runtime enforcement of import rules
- **Cons**:
  - Fragile (easy to bypass)
  - Adds runtime overhead
  - Complicates debugging
- **Rejected because**: Testing and code review sufficient

### Implementation Notes
- Package structure:
  ```
  backend/src/agents/
  ├── __init__.py              # Empty (no cross-imports)
  ├── conversation_agent.py    # Imports: mcp, services, models ONLY
  ├── conversion_agent.py      # Imports: mcp, services, models ONLY
  └── evaluation_agent.py      # Imports: mcp, services, models ONLY
  ```
- Code review checklist: "Verify no direct agent-to-agent imports"
- Unit test structure: Each agent test file imports only that agent
- CI check: `grep -r "from agents import" src/agents/` should return no results

---

## Decision 5: File Versioning Strategy

### Decision
**Use SHA256-based immutable versioning** with original filename preserved.

### Rationale
1. **Immutability**: Original files never overwritten (Story 8.7 requirement)
2. **Integrity**: SHA256 checksums detect corruption or tampering
3. **Traceability**: Full history of all conversion attempts with cryptographic verification
4. **Simplicity**: No complex version management system needed

### Filename Convention
```
<original_filename>_<attempt>_<sha256_prefix>.nwb

Examples:
- mouse_001.nwb                    # Attempt 1 (original conversion)
- mouse_001_attempt2_a3f9d1c8.nwb  # Attempt 2 after correction
- mouse_001_attempt3_b7e2f4d9.nwb  # Attempt 3 after second correction
```

### Alternatives Considered

**Alternative A: Semantic Versioning (v1, v2, v3)**
- **Pros**: Human-readable, simple
- **Cons**:
  - No integrity verification
  - Version numbers don't indicate content changes
  - Conflicts if files manually renamed
- **Rejected because**: Lacks cryptographic verification

**Alternative B: Timestamp-based naming**
- **Pros**: Shows when file was created
- **Cons**:
  - No integrity verification
  - Timestamp collisions possible
  - Doesn't indicate attempt number
- **Rejected because**: Less clear than attempt-based naming

**Alternative C: Git-style content-addressable storage**
- **Pros**: Pure content-based addressing (no metadata needed)
- **Cons**:
  - Loses original filename
  - Requires lookup table
  - Overkill for MVP
- **Rejected because**: Filename metadata useful for users

### Implementation Notes
- Compute SHA256 after each successful conversion (Story 6.3, 8.7)
- Store checksums in `GlobalState.checksums: Dict[str, str]` (key=attempt, value=sha256)
- Download endpoint `/api/download/nwb?attempt=N` uses attempt number
- Latest version: Highest attempt number in global state
- Checksum verification on download (optional integrity check)

---

## Decision 6: LLM Prompt Template Storage

### Decision
**Use YAML files with Jinja2 templating** stored in `backend/src/prompts/`.

### Rationale
1. **Human-Readable**: YAML easier to edit than JSON, clearer than Python f-strings
2. **Version Control**: YAML files tracked in git (requirement from Stories 9.1-9.2)
3. **Templating**: Jinja2 supports conditionals, loops for complex prompt logic
4. **Separation of Concerns**: Prompts separate from code (non-developers can edit)
5. **Type Safety**: Load YAML into Pydantic models for validation

### File Structure
```
backend/src/prompts/
├── evaluation_passed.yaml          # Story 9.1 (PASSED/PASSED_WITH_ISSUES)
├── evaluation_failed.yaml          # Story 9.2 (FAILED correction guidance)
└── format_detection.yaml           # Story 5.3 (optional LLM usage)
```

### YAML Template Format
```yaml
version: "1.0"
model: "claude-3-5-sonnet-20241022"
system_role: "You are a neuroscience data quality analyst"
context_variables:
  - file_info
  - evaluation_status
  - issues_breakdown
template: |
  You are analyzing NWB file quality for: {{ file_info.subject_id }}

  Status: {{ evaluation_status }}
  Issues: {{ issues_breakdown | tojson }}

  Generate a scientific assessment with:
  - Executive summary (2-3 sentences)
  - Quality assessment (specific issues + impact)
  - Recommendations (prioritized)

  Output JSON:
  {
    "executive_summary": "...",
    "quality_assessment": "...",
    "recommendations": [...]
  }
output_schema:
  type: "object"
  required: ["executive_summary", "quality_assessment", "recommendations"]
```

### Alternatives Considered

**Alternative A: JSON prompt files**
- **Pros**: Strict schema validation, widely supported
- **Cons**: Less readable for multiline templates, no comments
- **Rejected because**: YAML readability preferred

**Alternative B: Python f-strings in code**
- **Pros**: No YAML parsing, type-safe at development time
- **Cons**:
  - Hard to edit prompts (need Python knowledge)
  - Violates "versioned in codebase" intent (buried in code)
  - No separation of concerns
- **Rejected because**: Requirements explicitly want templates "versioned in codebase" separately

**Alternative C: Markdown files with frontmatter**
- **Pros**: Very readable, supports comments
- **Cons**: Requires markdown parser, less structured
- **Rejected because**: YAML more structured for programmatic use

### Implementation Notes
- Install: `PyYAML>=6.0`, `Jinja2>=3.1.0`
- Loader: `src/services/prompt_service.py` reads YAML, renders Jinja2
- Validation: Pydantic model `PromptTemplate` validates YAML structure
- Version tracking: Include `version` field in YAML, log with LLM calls
- Testing: Unit tests verify prompt rendering with sample data

---

## Decision 7: Test Fixtures for NeuroConv Formats

### Decision
**Use synthetic SpikeGLX format** for toy dataset (Story 12.2).

### Rationale
1. **Simplicity**: SpikeGLX binary format is straightforward (flat binary + metadata files)
2. **Size**: Can create <1 MB dataset (10 seconds, 32 channels, 30 kHz sampling)
3. **NeuroConv Support**: Well-supported by NeuroConv with stable interface
4. **Fast Conversion**: Minimal processing time (<10 seconds)
5. **Common Format**: Widely used in neuropixels recordings (realistic test case)

### Test Dataset Specification
```
tests/fixtures/toy_spikeglx/
├── recording.bin         # 10 sec, 32 channels, 30kHz int16 = ~19 MB
├── recording.meta        # SpikeGLX metadata (channel map, gains, etc.)
└── README.md             # Dataset documentation
```

**Note**: 19 MB exceeds <10 MB target - use 5 seconds or 16 channels to reduce to ~5 MB.

### Alternatives Considered

**Alternative A: Intan RHD format**
- **Pros**: Also simple binary format
- **Cons**: Less common than SpikeGLX, similar complexity
- **Rejected because**: SpikeGLX more widely recognized

**Alternative B: OpenEphys format**
- **Pros**: Open-source acquisition system
- **Cons**: More complex directory structure, larger files
- **Rejected because**: Harder to create minimal synthetic data

**Alternative C: Real dataset subset**
- **Pros**: Realistic data with actual neural signals
- **Cons**:
  - Licensing/privacy concerns
  - Harder to control size
  - May have existing quality issues (confounds testing)
- **Rejected because**: Synthetic data gives full control over test conditions

### Implementation Notes
- Generation script: `tests/fixtures/generate_toy_dataset.py`
- Synthetic data: Random gaussian noise (no real neural signals needed for testing)
- Metadata: Minimal valid SpikeGLX .meta file with required fields
- Deliberate quality issues for correction loop testing:
  - Missing optional metadata (e.g., subject age)
  - Incorrect units (triggers WARNING in NWB Inspector)
- Committed to git: Small size makes this acceptable
- Documentation: README explains dataset structure and purpose

---

## Summary of Decisions

| # | Decision | Chosen Solution | Key Rationale |
|---|----------|----------------|---------------|
| 1 | MCP Server | Custom implementation | Simplicity for 3-agent system, full control |
| 2 | PDF Generation | ReportLab | Pure Python, programmatic control, simple deployment |
| 3 | WebSocket | FastAPI native | Built-in, sufficient for MVP, no extra dependencies |
| 4 | Agent Isolation | Package structure + testing | Convention over enforcement, simple and effective |
| 5 | File Versioning | SHA256-based immutable | Integrity verification, traceability |
| 6 | Prompt Storage | YAML + Jinja2 | Readable, version-controlled, templating support |
| 7 | Test Fixtures | Synthetic SpikeGLX | Simple, small, NeuroConv-compatible |

**All Phase 0 research complete.** Ready to proceed to Phase 1 (data-model.md, contracts/, quickstart.md).

---

**Research Completed**: 2025-10-15
**Next Phase**: Phase 1 - Design & Contracts
