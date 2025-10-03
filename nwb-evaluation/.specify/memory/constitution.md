<!--
Sync Impact Report:
- Version change: initial → 1.0.0
- Added principles: I. NWB Data Quality & Scientific Integrity, II. Robust Error Handling, III. Modular Architecture, IV. Test-First (NON-NEGOTIABLE), V. Performance Optimization, VI. Scientific Documentation, VII. MCP Integration
- Added sections: Quality Standards, Development Workflow
- Templates requiring updates: ⚠ Will update after constitution finalization
- Follow-up TODOs: None
-->

# NWB Evaluation & Reporting Constitution

## Core Principles

### I. NWB Data Quality & Scientific Integrity
All validation and quality assessment MUST prioritize scientific accuracy and NWB standard compliance. The system SHALL ensure evaluated data meets neuroscience community standards through systematic validation using nwb-inspector as primary tool. Quality assessments MUST be reproducible, traceable, and scientifically defensible with clear audit trails.

**Rationale**: Scientific data quality is non-negotiable; incorrect quality assessments could lead to invalid research conclusions.

### II. Robust Error Handling
The system MUST implement defensive programming with circuit breaker patterns for external dependencies (especially nwb-inspector). All failures SHALL provide graceful degradation with partial results rather than complete failure. Error messages MUST include recovery guidance and actionable remediation steps.

**Rationale**: External validation tools may be unavailable; the system must remain operational and provide value even when primary tools fail.

### III. Modular Architecture
Every evaluator (technical, scientific, usability) MUST be independently testable and replaceable. Components SHALL communicate through well-defined interfaces with minimal coupling. The orchestration layer MUST support parallel execution of independent evaluators without shared state mutations.

**Rationale**: Modular design enables independent testing, parallel development, and easy extension of quality assessment capabilities.

### IV. Test-First (NON-NEGOTIABLE)
TDD mandatory: Contract tests MUST be written first for all evaluator interfaces. Integration tests MUST verify orchestration and MCP integration. Unit tests MUST achieve >80% coverage for core logic. Performance tests MUST validate <1s health check response time requirement. Red-Green-Refactor cycle strictly enforced.

**Rationale**: Quality assessment systems require high reliability; comprehensive testing ensures correctness and prevents regressions.

### V. Performance Optimization
The system MUST handle large NWB files efficiently through async/await patterns for I/O-bound operations, parallel execution of independent quality assessors, configurable timeout handling for long-running validations, and memory-efficient streaming where applicable. Performance targets: <1s health check response, graceful handling of multi-GB NWB files.

**Rationale**: Neuroscience datasets can be extremely large; poor performance would make the system unusable for real-world data.

### VI. Scientific Documentation
All documentation MUST be understandable by domain scientists (neuroscientists, data engineers) without deep software engineering knowledge. Quality reports MUST explain metrics in scientific terms with clear improvement recommendations. API documentation MUST include neuroscience-relevant examples and use cases.

**Rationale**: Primary users are neuroscience researchers and data engineers who need clear, scientifically-grounded quality guidance.

### VII. MCP Integration
All evaluation services MUST expose clean, well-documented MCP protocol interfaces. The system SHALL support concurrent evaluation requests with proper isolation, provide structured responses with validation schemas, handle health checks within 1 second, and maintain request/response audit logs for monitoring.

**Rationale**: Integration with the broader agentic conversion pipeline requires standardized, reliable MCP protocol compliance.

## Quality Standards

**Multi-Dimensional Assessment**: Quality assessment MUST evaluate across three dimensions: Technical Quality (schema compliance, data integrity, structure, performance), Scientific Quality (experimental completeness, design consistency, documentation adequacy), Usability Quality (documentation clarity, searchability, metadata richness, accessibility). Each dimension SHALL provide detailed scoring with specific, actionable remediation recommendations.

**Reporting Flexibility**: The reporting engine MUST support multiple output formats without code changes: Markdown for documentation integration, HTML with embedded visualizations for interactive review, PDF for archival and formal reporting, JSON for programmatic consumption. All formats SHALL maintain consistent information while optimizing for their medium.

**Visualization Simplicity**: HTML reports SHALL use lightweight, offline-capable libraries (Chart.js recommended). Visualizations MUST work without external dependencies and display correctly across modern browsers. Use simple chart types (bar, line, pie) with clear color coding for quality levels.

## Development Workflow

**Feature Development Process**: 1) Specification First - Define requirements with user stories and acceptance criteria; 2) Contract Design - Define evaluator interfaces and MCP protocol contracts; 3) Test Creation - Write contract and integration tests (must fail initially); 4) Implementation - Implement to pass tests following TDD; 5) Documentation - Update user-facing docs and scientific examples; 6) MCP Integration - Verify agent workflow integration.

**Code Review Requirements**: All changes MUST include tests (unit + integration where applicable), pass existing test suite without regressions, include documentation updates for user-facing changes, demonstrate compliance with all 7 core principles, and provide complexity justification if introducing new patterns/dependencies.

**Quality Gates**: Before merging: All tests passing (unit, integration, contract), test coverage ≥80% for new code, MCP protocol compliance verified, performance benchmarks within targets (<1s health checks), documentation review completed.

## Governance

This constitution supersedes all other development practices. Amendments require: 1) Documentation of rationale and impact analysis, 2) Team review and approval, 3) Migration plan for existing code if breaking changes, 4) Version increment following semantic versioning.

All PRs and code reviews MUST verify compliance with constitutional principles. Any complexity additions (new dependencies, architectural patterns) MUST be explicitly justified against simpler alternatives.

**Version**: 1.0.0 | **Ratified**: 2025-10-03 | **Last Amended**: 2025-10-03
