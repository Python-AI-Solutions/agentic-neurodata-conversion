<!--
Sync Impact Report:
Version Change: N/A → 1.0.0
Initial Constitution Creation
Added Sections:
  - Core Principles (6 principles)
  - Data Management Standards
  - Development Workflow
  - Governance
Templates Requiring Updates:
  ✅ .specify/templates/plan-template.md - to be validated
  ✅ .specify/templates/spec-template.md - to be validated
  ✅ .specify/templates/tasks-template.md - to be validated
Follow-up TODOs: None
-->

# Agentic Neurodata Conversion Constitution

## Core Principles

### I. MCP-Centric Architecture

All functionality MUST be exposed through standardized MCP (Model Context Protocol) tools. Direct agent invocation from external clients is prohibited. The MCP server acts as the single orchestration layer, ensuring consistent interfaces and enabling horizontal scaling.

**Rationale**: Centralizing all operations through MCP tools creates a unified API surface, simplifies client integration, and allows independent scaling of internal agents.

### II. Agent Specialization

Each internal agent (Conversation, Conversion, Evaluation, Knowledge Graph) MUST handle a single domain of responsibility. Cross-domain operations require coordination through the MCP server, not direct agent-to-agent communication.

**Rationale**: Clear separation of concerns ensures maintainability, testability, and allows independent evolution of agent capabilities.

### III. Test-Driven Development (NON-NEGOTIABLE)

All features MUST follow strict TDD workflow:
1. Write tests that define expected behavior
2. Obtain user approval on test specifications
3. Verify tests fail appropriately
4. Implement feature to pass tests
5. Refactor while maintaining green tests

**Rationale**: Neuroscience data conversion is mission-critical. TDD ensures correctness, prevents regressions, and provides living documentation of system behavior.

### IV. Data Integrity & Validation

All data conversions MUST:
- Validate input data structure before conversion
- Verify NWB schema compliance using NWB Inspector
- Track provenance through DataLad and knowledge graph
- Provide detailed error reporting for validation failures

**Rationale**: Invalid conversions compromise scientific reproducibility. Multi-layered validation catches errors early and maintains data quality standards.

### V. Metadata Completeness

Conversion pipelines MUST:
- Extract all available metadata from source datasets
- Prompt users for missing required fields
- Validate metadata against NWB core schema requirements
- Document metadata gaps in conversion reports

**Rationale**: Complete metadata is essential for scientific utility. Valid NWB structure without proper metadata produces technically correct but scientifically useless outputs.

### VI. Reproducibility & Provenance

All operations MUST:
- Use DataLad Python API for data operations (never CLI commands)
- Record conversion scripts and parameters
- Track data lineage in RDF knowledge graph
- Enable bit-for-bit reproduction of conversions

**Rationale**: Scientific reproducibility requires complete traceability from raw data through conversion to final NWB files.

## Data Management Standards

### DataLad Integration

- ALL data operations MUST use DataLad Python API (`import datalad.api as dl`)
- Large files (>10MB) MUST be annexed and stored on GIN
- Subdatasets MUST be properly initialized before use
- Changes MUST include descriptive commit messages

### Storage Strategy

- Code and configuration: GitHub repository
- Large data files: GIN (G-Node Infrastructure) via git-annex
- Conversion outputs: Annexed in output directories
- Test fixtures: Small samples in git, large datasets annexed

## Development Workflow

### Code Review Requirements

All pull requests MUST:
- Include passing tests for new functionality
- Validate against this constitution's principles
- Document breaking changes to MCP tool interfaces
- Pass CI/CD checks (linting, type checking, security scans)

### Quality Gates

Before merging, verify:
- Test coverage maintained or improved
- No new security vulnerabilities introduced
- Documentation updated for user-facing changes
- Performance benchmarks within acceptable bounds

### Versioning Policy

Follow semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes to MCP tool interfaces or agent protocols
- MINOR: New agents, tools, or backward-compatible features
- PATCH: Bug fixes, documentation, performance improvements

## Governance

### Amendment Process

Constitution amendments require:
1. Documented proposal with rationale
2. Impact analysis on existing specifications and implementations
3. Team review and approval
4. Migration plan for breaking changes
5. Version increment per semantic versioning rules

### Compliance Verification

All code reviews MUST verify:
- TDD workflow was followed (test-first evidence)
- MCP interface consistency maintained
- DataLad API usage (not CLI)
- Validation steps implemented
- Metadata completeness addressed

### Constitutional Authority

This constitution supersedes project-specific guidelines. When conflicts arise between this constitution and other documentation, constitutional principles take precedence. Exceptions require explicit governance approval and documentation.

**Version**: 1.0.0 | **Ratified**: 2025-10-03 | **Last Amended**: 2025-10-03
