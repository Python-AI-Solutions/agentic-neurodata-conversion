<!--
Sync Impact Report:
- Version change: 1.1.0 → 2.0.0
- Version bump rationale: MAJOR - Removed implementation details, simplified to core principles only
- Changes: Consolidated 8 verbose principles into 5 concise principles
- Removed: Implementation patterns, story references, tech stack details (moved to requirements.md)
- Templates requiring updates: ✅ All templates remain compatible
-->

# Agentic Neurodata Conversion System Constitution

## Core Principles

### I. Three-Agent Architecture
Three specialized agents with strict separation of concerns:
- **Conversation Agent**: Owns all user interaction
- **Conversion Agent**: Pure technical conversion logic
- **Evaluation Agent**: Pure validation and quality assessment

No agent may bypass this separation. Enables independent testing, scaling, and reuse.

### II. Protocol-Based Communication
All agent communication uses MCP (Model Context Protocol) with JSON-RPC 2.0. No direct imports between agents. Agents remain loosely coupled and independently deployable.

### III. Defensive Error Handling
Fail fast with full diagnostic context. No silent failures, no hiding problems with defaults. Scientific data integrity requires explicit errors over graceful degradation.

**Exception**: Optional LLM usage (format detection) degrades gracefully with logged warnings.

### IV. User-Controlled Workflows
Users explicitly approve all retry attempts. No autonomous retry decisions. Ensures transparency and prevents resource waste on unfixable issues.

### V. Provider-Agnostic Services
External services (LLM, storage, etc.) accessed through abstract interfaces only. Agents inject dependencies at runtime. Ensures testability and prevents vendor lock-in.

## Technology Philosophy

- **Python 3.13+** for backend (NeuroConv, PyNWB, NWB Inspector, FastAPI, Pydantic)
- **React + TypeScript** for frontend
- **Single session MVP** (in-memory state, local files, no authentication)
- **Type safety** via Pydantic models throughout
- **Environment-based configuration** (no hardcoded values)

## Quality Standards

- Code coverage ≥80%
- Integration tests ≤10 minutes on toy datasets
- Structured JSON logging
- All agents independently testable

## Governance

Constitution changes require:
1. Rationale and impact analysis
2. Semantic versioning (MAJOR/MINOR/PATCH)
3. Sync Impact Report update

Constitution supersedes all other documentation.

**Version**: 2.0.0 | **Ratified**: 2025-10-15 | **Last Amended**: 2025-10-15
