# Implementation Plan: Agentic Neurodata Conversion System

**Branch**: `001-agentic-neurodata-conversion` | **Date**: 2025-10-15 | **Spec**: [requirements.md](../../requirements.md)
**Input**: Feature specification from `/specs/requirements.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a three-agent system (Conversation, Conversion, Evaluation) that converts neurophysiology data to NWB format with user-controlled error correction loops. The system uses MCP protocol for agent communication, leverages NeuroConv for format detection, validates with NWB Inspector, and generates LLM-enhanced quality reports. MVP scope: single-session web application with local file storage.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- Backend: NeuroConv (≥0.4.0), PyNWB (≥2.6.0), NWB Inspector (≥0.4.30), FastAPI, Pydantic (≥2.0), Anthropic SDK (≥0.18.0)
- Frontend: React 18+, TypeScript, Material-UI (≥5.0), Axios

**Storage**:
- Files: Local filesystem (uploads/, outputs/, logs/)
- State: In-memory Python dict (single session)

**Testing**: pytest, pytest-cov (≥80% coverage), toy datasets (<10 MB)

**Target Platform**:
- Backend: Local server (macOS/Linux)
- Frontend: Modern browsers (Chrome, Firefox, Safari)

**Project Type**: Web application (React frontend + FastAPI backend)

**Performance Goals**:
- Integration tests complete in ≤10 minutes on toy datasets
- WebSocket updates within 1 second
- No hard limits on file size (MVP uses available resources)

**Constraints**:
- Single conversion at a time (409 Conflict on concurrent uploads)
- No authentication (local deployment only)
- Defensive error handling (fail fast, no silent failures)
- LLM required for correction analysis and report generation (critical paths: Stories 4.4, 9.3-9.6)
  - Exception: Story 5.3 (format detection ambiguity) degrades gracefully if LLM unavailable

**Scale/Scope**:
- MVP: 1 user, 1 conversion session at a time
- 12 epics, 120+ user stories
- 3 independent agent modules
- ~2272 lines of requirements

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Three-Agent Architecture ✅
**Status**: PASS
**Evidence**: Requirements explicitly define three agents:
- Conversation Agent (Epic 4): User interaction only
- Conversion Agent (Epics 5-6): Pure technical conversion
- Evaluation Agent (Epic 7): Pure validation logic
- All communication via MCP (Epic 1)

### Principle II: Protocol-Based Communication ✅
**Status**: PASS
**Evidence**: Epic 1 defines MCP server with JSON-RPC 2.0, agent registry, message routing. All agent interactions use MCPMessage schema (Appendix B).

### Principle III: Defensive Error Handling ✅
**Status**: PASS
**Evidence**: Requirements specify (lines 1640-1666):
- Raise exceptions immediately (no silent failures)
- Full diagnostic context in structured JSON
- Preserve logs before raising exceptions
- LLM failures in critical paths raise LLMAPIException
- Only optional LLM usage (Story 5.3) degrades gracefully

### Principle IV: User-Controlled Workflows ✅
**Status**: PASS
**Evidence**: Epic 8 defines user approval for all retry attempts. Stories 8.2-8.3 require user decision before correction loops. No autonomous retries.

### Principle V: Provider-Agnostic Services ✅
**Status**: PASS
**Evidence**: Epic 3 defines abstract LLMService interface. Story 3.1 specifies provider-agnostic design. Anthropic SDK is concrete implementation, not agent dependency.

### Technology Philosophy Alignment ✅
**Status**: PASS
**Evidence**:
- Python 3.11+ backend with specified libraries
- React + TypeScript frontend
- Single session MVP (in-memory state, local files)
- Pydantic models throughout (Appendix B)
- Environment-based configuration (lines 1682-1688)

### Quality Standards Alignment ✅
**Status**: PASS
**Evidence**:
- Code coverage ≥80% (line 1679)
- Integration tests ≤10 minutes on toy datasets (line 1636)
- Structured JSON logging (lines 1681-1682)
- All agents independently testable (line 1680)

**Constitution Check Result**: ✅ **ALL GATES PASS** - No violations, proceed to Phase 0

## Project Structure

### Documentation (this feature)

```
specs/001-agentic-neurodata-conversion/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Symlink to ../../requirements.md
├── research.md          # Phase 0 output (technical decisions, NEEDS CLARIFICATION resolution)
├── data-model.md        # Phase 1 output (Pydantic schemas, state machines)
├── quickstart.md        # Phase 1 output (developer onboarding)
├── contracts/           # Phase 1 output (API contracts, MCP message specs)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Web application structure (frontend + backend)

backend/
├── src/
│   ├── agents/
│   │   ├── conversation_agent.py    # Epic 4
│   │   ├── conversion_agent.py      # Epics 5-6
│   │   └── evaluation_agent.py      # Epic 7
│   ├── mcp/
│   │   ├── server.py                # Epic 1: MCP server
│   │   ├── message.py               # MCPMessage schema
│   │   └── registry.py              # Agent registry
│   ├── services/
│   │   ├── llm_service.py           # Epic 3: Abstract interface
│   │   ├── anthropic_service.py     # Epic 3: Concrete implementation
│   │   └── storage_service.py       # File I/O abstraction
│   ├── models/
│   │   ├── global_state.py          # Epic 2: GlobalState schema
│   │   ├── validation.py            # ValidationResult schema
│   │   └── correction.py            # CorrectionContext schema
│   ├── api/
│   │   ├── main.py                  # FastAPI app (Epic 10)
│   │   ├── endpoints/
│   │   │   ├── upload.py            # Story 10.2
│   │   │   ├── status.py            # Story 10.4
│   │   │   ├── download.py          # Story 10.6
│   │   │   └── logs.py              # Story 10.7
│   │   └── websocket.py             # Story 10.5
│   └── utils/
│       ├── logging.py               # Structured JSON logging
│       └── exceptions.py            # Custom exception classes
└── tests/
    ├── unit/
    │   ├── test_agents.py
    │   ├── test_mcp.py
    │   └── test_services.py
    ├── integration/
    │   ├── test_end_to_end.py       # Story 12.1
    │   └── test_error_recovery.py   # Story 12.5
    └── fixtures/
        └── toy_dataset/             # Story 12.2 (<10 MB)

frontend/
├── src/
│   ├── components/
│   │   ├── FileUpload.tsx           # Story 11.2
│   │   ├── MetadataForm.tsx         # Story 11.3
│   │   ├── ProgressView.tsx         # Story 11.4
│   │   ├── ResultsDisplay.tsx       # Story 11.5
│   │   └── LogViewer.tsx            # Story 11.6
│   ├── services/
│   │   ├── api.ts                   # API client
│   │   └── websocket.ts             # WebSocket client
│   ├── types/
│   │   └── models.ts                # TypeScript interfaces for API
│   └── App.tsx                      # Main React app
└── tests/
    └── components/                  # React component tests

uploads/                             # User file uploads (gitignored)
outputs/                             # Generated NWB files + reports (gitignored)
logs/                                # Structured JSON logs (gitignored)

pixi.toml                            # Environment management
pyproject.toml                       # Python project config
```

**Structure Decision**: Web application structure selected based on requirements specifying React frontend (Epic 11) + FastAPI backend (Epic 10). Backend organized by agent modules (Epic 1-9), MCP infrastructure (Epic 1), and API layer (Epic 10). Frontend organized by UI components (Epic 11). Testing split by scope (unit, integration, fixtures).

## Complexity Tracking

*No constitution violations detected. This section intentionally left empty.*

## Phase 0: Outline & Research

### Research Tasks (NEEDS CLARIFICATION Resolution)

Based on requirements.md analysis, the following technical decisions require research and documentation:

1. **MCP Server Implementation Pattern**
   - Decision needed: Build custom MCP server or use existing library?
   - Research: Anthropic MCP SDK vs custom implementation
   - Rationale: Requirements specify JSON-RPC 2.0, but implementation approach undefined

2. **PDF Report Generation Library**
   - Decision needed: ReportLab vs Quarto (line 1719 mentions both)
   - Research: Best practices for scientific PDF reports in Python
   - Rationale: Requirements recommend Quarto to avoid vendor lock-in

3. **WebSocket Integration with FastAPI**
   - Decision needed: FastAPI native WebSocket vs external library?
   - Research: Patterns for real-time progress updates in FastAPI
   - Rationale: Requirements specify WebSocket (Story 10.5) but not implementation approach

4. **Agent Module Packaging Strategy**
   - Decision needed: How to enforce "no direct imports between agents"?
   - Research: Python module isolation patterns (namespaces, entry points)
   - Rationale: Constitution Principle I requires agent independence

5. **File Versioning Strategy**
   - Decision needed: Naming convention for NWB versions (story 8.7: original.nwb, original_v2.nwb)
   - Research: Best practices for immutable file versioning with checksums
   - Rationale: Requirements specify versioning but not exact implementation

6. **LLM Prompt Template Storage**
   - Decision needed: YAML, JSON, or Python f-strings (Stories 9.1-9.2)?
   - Research: Best practices for versioned prompt templates
   - Rationale: Requirements specify templates should be "versioned in codebase"

7. **Test Fixtures for NeuroConv Formats**
   - Decision needed: Which minimal format to use for toy dataset (SpikeGLX mentioned in Story 12.2)?
   - Research: Simplest NeuroConv-compatible format for <10 MB test data
   - Rationale: Requirements specify toy dataset but not specific format

**Phase 0 Output**: research.md documenting all decisions with rationale and alternatives considered

## Phase 1: Design & Contracts

### Deliverables

1. **data-model.md**: Pydantic schemas (already defined in Appendix B of requirements.md)
   - MCPMessage
   - GlobalState with ConversionStatus, ValidationStatus enums
   - ValidationResult with IssueSeverity, OverallStatus enums
   - CorrectionContext
   - API Request/Response schemas

2. **contracts/**: API and MCP specifications
   - `openapi.yaml`: REST API contract (Epic 10 endpoints)
   - `mcp-messages.json`: MCP message action catalog
   - `websocket-events.json`: WebSocket message types

3. **quickstart.md**: Developer onboarding guide
   - Pixi environment setup
   - Run backend + frontend
   - Run integration tests
   - Agent development workflow

4. **Agent context update**: Run `.specify/scripts/bash/update-agent-context.sh claude`
   - Add technology stack to Claude context
   - Preserve manual additions

**Phase 1 Prerequisites**: research.md complete

## Phase 2: Task Breakdown

**Handled by**: `/speckit.tasks` command (separate from `/speckit.plan`)

This phase generates actionable implementation tasks based on the plan. Not executed as part of the planning phase.

---

**Plan Status**: ✅ Ready for Phase 0 (Research)

**Next Steps**:
1. Execute Phase 0: Create research.md resolving all technical decisions
2. Execute Phase 1: Generate data-model.md, contracts/, quickstart.md
3. Run `/speckit.tasks` for Phase 2 task breakdown
