<!--
Sync Impact Report:
- Version change: [initial] → 1.0.0
- Modified principles: Initial creation with 7 core principles
- Added sections: Core Principles, Data Management Standards, Quality & Validation, Development Workflow, Governance
- Removed sections: None (initial creation)
- Templates requiring updates:
  ✅ .specify/templates/plan-template.md - Reviewed, aligns with principles
  ✅ .specify/templates/spec-template.md - Reviewed, aligns with principles
  ✅ .specify/templates/tasks-template.md - Reviewed, aligns with principles
  ✅ .claude/commands/*.md - Reviewed, no agent-specific references to update
- Follow-up TODOs: None
-->

# Agentic Neurodata Conversion Constitution

## Core Principles

### I. Provenance-First Development

Every data transformation, metadata decision, and conversion step MUST be fully traceable with documented provenance. All automated decisions MUST record confidence levels (definitive, high_evidence, human_confirmed, human_override, medium_evidence, heuristic, low_evidence, placeholder, unknown), source types, derivation methods, and complete reasoning chains. Human overrides MUST be clearly distinguished from evidence-based decisions.

**Rationale**: Scientific reproducibility and trust depend on complete transparency. Researchers must be able to validate every automated decision to meet publication standards and ensure data integrity.

### II. DataLad Python API Exclusively

All DataLad operations MUST use the Python API (`import datalad.api as dl`). CLI commands are prohibited. Large files (>10MB) MUST be annexed. Development files MUST remain in git. Test datasets MUST support selective downloading. Subdatasets MUST be properly managed with explicit installation and updates.

**Rationale**: The Python API provides programmatic control, better error handling, and integration with Python workflows. CLI commands are fragile, difficult to test, and prone to shell injection vulnerabilities.

### III. MCP Server as Central Hub

The MCP server is the single orchestration hub for all agent interactions. Agents MUST NOT communicate directly with each other. All agent coordination MUST flow through the MCP server. HTTP/API is the primary interface. Client libraries proxy MCP operations.

**Rationale**: Centralized orchestration simplifies architecture, ensures consistent error handling, provides single point of observability, and matches the existing working implementation.

### IV. Agent Specialization

Each agent has a single, well-defined responsibility: ConversationAgent (user interaction), ConversionAgent (data transformation), EvaluationAgent (quality assessment), MetadataQuestioner (metadata collection). Agents MUST NOT duplicate functionality. Cross-cutting concerns (validation, knowledge graphs) are separate systems accessed via tools.

**Rationale**: Separation of concerns improves maintainability, enables parallel development, simplifies testing, and allows specialized agents to evolve independently.

### V. Test-Driven Quality Assurance (NON-NEGOTIABLE)

Tests MUST be written and approved before implementation. Red-Green-Refactor cycle strictly enforced. Unit tests required for all components. Integration tests required for: agent interactions, MCP server endpoints, conversion pipelines, validation workflows. Evaluation datasets MUST be versioned with DataLad.

**Rationale**: Complex scientific data conversion requires rigorous testing. TDD ensures requirements are testable, prevents regression, documents expected behavior, and builds confidence in automated systems.

### VI. Standards Compliance

All NWB outputs MUST pass NWB Inspector validation. Conversions MUST follow NeuroConv patterns where applicable. LinkML schemas used for metadata structure validation. Knowledge graphs MUST use standard ontologies (EDAM, OBI, PROV-O, NWB ontology). SPARQL endpoints required for semantic queries.

**Rationale**: Standards ensure interoperability, enable data sharing, facilitate long-term preservation, and leverage existing neuroscience community tools and practices.

### VII. Gradual Automation with Human Oversight

Automation MUST NOT eliminate human judgment. Systems provide evidence and recommendations; humans make final decisions. Confidence levels guide when to request human review. Interactive interfaces required for metadata collection and conflict resolution. Evaluation reports MUST be human-readable with clear actionable insights.

**Rationale**: Neuroscience data is complex and context-dependent. Automated systems can extract and organize information, but domain expertise is essential for validating scientific accuracy and handling edge cases.

## Data Management Standards

All development test datasets MUST be managed with DataLad as datasets or subdatasets. Selective downloading of dataset portions is required for efficiency. Each conversion MUST create its own DataLad repository tracking outputs, scripts, and history with versioned commits for each iteration. Successful conversions MUST be tagged. Output organization MUST follow structured directories: NWB files, conversion scripts, validation reports, evaluation reports, knowledge graph outputs. All outputs from specialized systems (validation, evaluation, knowledge graphs) MUST be properly versioned and accessible.

## Quality & Validation

NWB Inspector validation MUST run on all outputs. LinkML schemas validate metadata structure. Domain-specific validation checks MUST assess data quality beyond format compliance. Evaluation reports MUST include interactive visualizations, quality metrics, and comprehensive assessments. Knowledge graphs MUST track semantic relationships and provenance. Performance monitoring MUST track conversion throughput, storage usage, and response times. Automated cleanup of temporary files is required.

## Development Workflow

Features begin with specification following spec-kit methodology: constitution → specify → plan → tasks → implement. Specifications MUST be technology-agnostic focusing on WHAT and WHY, not HOW. Each user story MUST be independently testable. Requirements MUST be measurable and unambiguous. Success criteria MUST be technology-agnostic and verifiable. Implementation follows prioritized task lists generated from specifications. Agent interactions and tool usage MUST be tracked in provenance when using MCP workflow.

## Governance

This constitution supersedes all other practices and documentation. Amendments require:

1. Documentation of rationale and impact
2. Review of affected templates and commands
3. Version increment following semantic versioning:
   - MAJOR: Backward-incompatible governance changes or principle removals
   - MINOR: New principles or materially expanded guidance
   - PATCH: Clarifications, wording refinements, non-semantic fixes
4. Migration plan for existing code if needed
5. Update of Sync Impact Report

All pull requests and code reviews MUST verify compliance with constitution principles. Complexity and deviations MUST be explicitly justified with documented rationale. Runtime development guidance follows spec-kit command files in `.claude/commands/`.

**Version**: 1.0.0 | **Ratified**: 2025-10-07 | **Last Amended**: 2025-10-07
