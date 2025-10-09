# Agentic Neurodata Conversion Constitution

<!-- Sync Impact Report:
Version change: 1.2.0 → 2.0.0
Last Modified: 2025-10-09
Changes:
- Removed Principle IX (Security and Compliance) - now 8 core principles
- Updated terminology: "modules" → "features" (aligned with spec-kit terminology)
- Principle IV renamed to "Feature-Driven and Extensible Design"
- Removed circuit breakers requirement (too complex for MVP)
- Removed distributed tracing with OpenTelemetry (too complex for MVP)
- Simplified observability to structured logging and basic metrics
- Removed "Security and privacy trump convenience" from conflict resolution
- Updated Python version requirement: 3.8-3.12 → 3.9+ (matches pyproject.toml)
- BREAKING: Simplified to MCP protocol only (removed HTTP/REST, WebSocket, gRPC)
- Changed from multiple adapters to single MCP adapter
- Removed multi-protocol parity requirements
Principles: MCP-centric architecture, testing, quality, feature-driven design, transparency, performance, standards compliance, and documentation
Templates status: ✅ All templates compatible with updated constitution
-->

## Core Principles

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

The MCP server is the **central orchestration hub** for all agent interactions and workflows. All business logic MUST reside in a transport-agnostic core service layer, with a thin adapter layer (<500 lines) for MCP protocol communication (stdin/stdout).

- Agents MUST be called through the MCP server; no direct agent-to-agent communication
- The MCP adapter MUST only handle protocol translation; zero business logic allowed
- All features MUST be accessible through the MCP protocol
- State management MUST be transport-independent
- The MCP adapter MUST be tested for correctness and protocol compliance

**Rationale**: Clean separation ensures maintainability, testability, and protocol compliance while preventing architectural erosion.

### II. Test-First Development (NON-NEGOTIABLE)

Test-Driven Development (TDD) is mandatory across all components. Tests MUST be written and approved by users/stakeholders BEFORE implementation begins.

- Unit tests MUST achieve >90% code coverage for core components
- Integration tests MUST verify agent coordination and multi-component workflows
- End-to-end tests MUST use DataLad-managed real neuroscience datasets
- All tests MUST follow Red-Green-Refactor cycle strictly
- Performance regression tests MUST be part of CI/CD pipeline

**Rationale**: Neuroscience data conversion is mission-critical; bugs can corrupt scientific data. TDD ensures reliability and prevents regressions.

### III. Quality and Validation First

Every conversion MUST go through comprehensive validation and quality assessment before being considered complete. Quality is multi-dimensional: technical, scientific, and usability.

- NWB Inspector validation MUST pass with zero critical issues
- PyNWB schema compliance MUST be verified
- Multi-dimensional quality scoring (technical, scientific, usability) MUST be calculated
- Validation results MUST include specific remediation guidance
- Quality gates MUST be configurable per environment (dev/staging/prod)

**Rationale**: Data quality directly impacts scientific reproducibility and research outcomes. Poor quality data undermines the entire conversion effort.

### IV. Feature-Driven and Extensible Design

The system MUST be organized into clear, focused features with well-defined interfaces and minimal dependencies. Each feature MUST be independently testable and deployable.

- Features MUST follow single responsibility principle
- Interfaces MUST be versioned and backward compatible
- Plugin architecture MUST support custom validators, formatters, and agents
- Feature boundaries MUST be enforced through automated dependency checks
- New data formats MUST be addable without core system changes

**Rationale**: Neuroscience has diverse data formats and workflows. Feature-driven design enables adaptation without system-wide rewrites.

### V. Provenance and Transparency (NON-NEGOTIABLE)

Every decision, transformation, and metadata field MUST have complete provenance tracking. Users MUST be able to understand and validate all automated decisions.

- All metadata MUST be marked with source (user-provided, auto-detected, inferred, enriched)
- All automated decisions MUST include reasoning chains and evidence quality
- Confidence levels MUST be tracked for all inferences (definitive, high_evidence, medium_evidence, heuristic, low_evidence, placeholder)
- Complete audit trails MUST be maintained for all conversions
- Knowledge graph enrichments MUST provide citations and confidence scores

**Rationale**: Scientific integrity requires complete transparency. Researchers must trust and verify automated conversions.

### VI. Performance and Scalability

The system MUST handle datasets from MB to TB scale efficiently. Resource usage MUST be monitored and optimized continuously.

- Conversion throughput MUST be benchmarked per data format
- Memory usage MUST support streaming for large files
- Parallel processing MUST be supported where scientifically appropriate
- Performance regression tests MUST catch degradations >10%
- Resource limits MUST be configurable and enforced

**Rationale**: Neuroscience datasets are growing exponentially. Poor performance makes the system unusable for modern experiments.

### VII. Standards Compliance and Interoperability

All outputs MUST comply with NWB standards, FAIR principles, and community best practices. Integration with ecosystem tools MUST be seamless.

- NWB schema compliance MUST be verified automatically
- FAIR principles (Findable, Accessible, Interoperable, Reusable) MUST be validated
- DANDI upload requirements MUST be checked
- NeuroConv, PyNWB, and NWB Inspector MUST be primary integration points
- LinkML schemas MUST be used for metadata validation
- RDF/OWL knowledge graphs MUST follow NWB-LinkML and domain ontologies (NIFSTD, UBERON, CHEBI, NCBITaxon)

**Rationale**: Standards enable data sharing, collaboration, and long-term usability. Non-compliant data isolates research.

### VIII. Developer Experience and Documentation

Documentation MUST be comprehensive, up-to-date, and accessible. Development setup MUST be automated and work reliably.

- All public APIs MUST have docstrings with examples (Google style)
- Architecture diagrams MUST be maintained (C4 model)
- Setup MUST be automated with pixi environment management
- Examples MUST be tested in CI/CD
- ADRs (Architecture Decision Records) MUST document significant decisions
- Integration guides MUST exist for external developers

**Rationale**: Complex systems require excellent documentation to enable contributions and integrations.

## Development Standards

### Code Quality

- Ruff MUST be used for linting and formatting (line length 100)
- Mypy MUST be used for static type checking (strict mode)
- Type hints MUST be provided for all functions
- Cyclomatic complexity MUST not exceed 10
- Pre-commit hooks MUST enforce quality standards

### Configuration Management

- Pydantic-settings MUST be used for configuration with validation
- Environment variables MUST use prefixes (e.g., `NWB_CONVERTER_`)
- Separate configs MUST exist for dev/test/staging/prod
- Secret management MUST be integrated
- Configuration changes MUST be versioned

### Error Handling

- Typed exception hierarchy MUST be implemented
- Error codes MUST be documented
- Structured error responses MUST be returned
- Recovery strategies MUST be implemented where possible
- Debug information MUST be available in development mode

## Component Requirements

### MCP Server

- Transport-agnostic core service layer MUST contain all business logic
- MCP adapter MUST be <500 lines and contain zero business logic
- Multi-agent workflows MUST be orchestrated with proper sequencing
- State MUST be managed with checkpoint recovery
- Error handling MUST provide clear error messages and graceful degradation

### Agents

- Base agent interface MUST be standardized
- Conversation agents MUST minimize repeated questions
- Conversion agents MUST support 25+ neuroscience formats
- Evaluation agents MUST coordinate validation/reporting/knowledge graph systems
- Metadata questioners MUST provide contextual, validated questions
- Mock modes MUST be available for testing without LLMs

### Validation Systems

- NWB Inspector MUST be primary validation engine
- LinkML schemas MUST validate metadata
- SHACL shapes MUST be generated from NWB-LinkML
- Quality assessment MUST cover technical/scientific/usability dimensions
- Domain-specific validators MUST check neuroscience plausibility
- Validation MUST be orchestrated through modular pipeline

### Knowledge Graph Systems

- NWB-LinkML MUST be the canonical schema source
- JSON-LD contexts and SHACL shapes MUST be generated from schemas
- RDF graphs MUST use schema-derived IRIs
- SPARQL queries MUST be supported for validation and enrichment
- PROV-O MUST be used for provenance tracking
- Core ontologies (NIFSTD, UBERON, CHEBI, NCBITaxon) MUST be integrated

### Data Management

- DataLad MUST be used for development datasets and conversion outputs
- Python API MUST be used exclusively (no CLI commands)
- Each conversion MUST create its own DataLad repository
- Provenance tracking MUST integrate with MCP workflows
- Large files (>10MB) MUST be annexed; development files in git

## Testing Requirements

### Test Categories

- Unit tests MUST run in <5 minutes
- Integration tests MUST run in <15 minutes
- E2E tests with real datasets MUST use DataLad-managed data
- Performance tests MUST establish baselines
- Security tests MUST follow OWASP guidelines

### Test Infrastructure

- Pytest MUST be the testing framework
- Test markers MUST categorize tests (unit, integration, slow, etc.)
- Mock services MUST support deterministic testing
- Fixtures MUST be reusable via factories
- Test data MUST be version controlled with DataLad

### Quality Gates

- Code coverage MUST be >80% overall, >90% for core components
- No critical security vulnerabilities allowed
- Performance must not regress >10%
- All tests must pass before merge
- Documentation must build without errors

## Deployment and Operations

### Environment Management

- Pixi MUST be used for environment management
- Linux-64 and osx-arm64 MUST be supported
- Python 3.9+ MUST be supported (tested: 3.9, 3.10, 3.11, 3.12)
- Dependencies MUST be pinned with lock files
- Vulnerability scanning MUST run regularly

### Observability

- Structured logging MUST use JSON format
- Log levels MUST be configurable per feature
- Correlation IDs MUST track requests across agent calls
- Performance metrics MUST be collected for key operations

### CI/CD Pipeline

- All tests MUST run on every pull request
- Code quality checks MUST pass before merge
- Security scanning MUST run on every commit
- Documentation MUST be generated automatically
- Deployment previews MUST be available for PRs

## External Integration

### Client Libraries

- Example implementations MUST demonstrate MCP server communication
- Error handling MUST be robust with retry logic
- Progress tracking MUST be supported for long operations
- Multiple languages MAY be supported (Python is primary)
- AI-assisted workflows MAY provide intelligent recommendations

### Third-Party Systems

- Jupyter notebooks MUST be supported
- Workflow systems (Snakemake, Nextflow) MUST be integrable
- Cloud storage MUST be supported for datasets
- Container environments (Docker, Singularity) MUST work

## Governance

### Constitution Authority

This constitution supersedes all other development practices and guidelines. All architectural decisions, code reviews, and implementations MUST comply with these principles.

### Amendment Process

1. Amendments MUST be proposed with detailed rationale
2. Breaking changes MUST include migration plans
3. Version MUST be incremented semantically:
   - MAJOR: Breaking principle changes or removals
   - MINOR: New principles or material expansions
   - PATCH: Clarifications, wording improvements, typo fixes
4. All stakeholders MUST review and approve amendments
5. Documentation MUST be updated to reflect amendments

### Compliance Review

- All pull requests MUST verify constitutional compliance
- Architecture reviews MUST check principle adherence
- Complexity MUST be justified against simplicity principles
- Exceptions MUST be documented with ADRs

### Conflict Resolution

When principles conflict in specific situations:
1. NON-NEGOTIABLE principles take absolute priority
2. Scientific correctness and data integrity trump performance
3. Transparency and provenance trump implementation simplicity

**Version**: 2.0.0 | **Ratified**: 2025-10-09 | **Last Amended**: 2025-10-09
