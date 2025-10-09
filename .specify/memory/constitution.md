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

All functionality MUST be exposed through standardized MCP (Model Context
Protocol) tools. Direct agent invocation from external clients is prohibited.
The MCP server acts as the single orchestration layer, ensuring consistent
interfaces and enabling horizontal scaling.

**Rationale**: Centralizing all operations through MCP tools creates a unified
API surface, simplifies client integration, and allows independent scaling of
internal agents.

### II. Agent Specialization

Each internal agent (Conversation, Conversion, Evaluation, Knowledge Graph) MUST
handle a single domain of responsibility. Cross-domain operations require
coordination through the MCP server, not direct agent-to-agent communication.

**Rationale**: Clear separation of concerns ensures maintainability,
testability, and allows independent evolution of agent capabilities.

### III. Test-Driven Development (NON-NEGOTIABLE)

All features MUST follow strict TDD workflow:

1. Write tests that define expected behavior
2. Obtain user approval on test specifications
3. Verify tests fail appropriately
4. Implement feature to pass tests
5. Refactor while maintaining green tests

**Rationale**: Neuroscience data conversion is mission-critical. TDD ensures
correctness, prevents regressions, and provides living documentation of system
behavior.

### IV. Data Integrity & Validation

All data conversions MUST:

- Validate input data structure before conversion
- Verify NWB schema compliance using NWB Inspector
- Track provenance through DataLad and knowledge graph
- Provide detailed error reporting for validation failures

**Rationale**: Invalid conversions compromise scientific reproducibility.
Multi-layered validation catches errors early and maintains data quality
standards.

### V. Metadata Completeness

Conversion pipelines MUST:

- Extract all available metadata from source datasets
- Prompt users for missing required fields
- Validate metadata against NWB core schema requirements
- Document metadata gaps in conversion reports

**Rationale**: Complete metadata is essential for scientific utility. Valid NWB
structure without proper metadata produces technically correct but
scientifically useless outputs.

### VI. Reproducibility & Provenance

All operations MUST:

- Use DataLad Python API for data operations (never CLI commands)
- Record conversion scripts and parameters
- Track data lineage in RDF knowledge graph
- Enable bit-for-bit reproduction of conversions

**Rationale**: Scientific reproducibility requires complete traceability from
raw data through conversion to final NWB files.

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

This constitution supersedes project-specific guidelines. When conflicts arise
between this constitution and other documentation, constitutional principles
take precedence. Exceptions require explicit governance approval and
documentation.

**Version**: 1.0.0 | **Ratified**: 2025-10-03 | **Last Amended**: 2025-10-03

=== CONSTITUTION.MD FROM PR #29 (specfile_1_knowledge_graph_systems) ===

<!--
Sync Impact Report:
Version change: NEW → 1.0.0
List of modified principles: Initial constitution creation
Added sections: Core Principles (5), Semantic Web Standards, Development Workflow, Governance
Removed sections: None (initial creation)
Templates requiring updates: ✅ updated (plan-template.md references verified)
Follow-up TODOs: None
-->

# Agentic Neurodata Conversion Constitution

## Core Principles

### I. Schema-First Development

Every feature MUST start with LinkML schema definition; All data structures MUST
be validated against NWB-LinkML schema; Clear semantic mappings required between
custom formats and NWB ontology; No implementation without prior schema
validation and SHACL shape generation.

### II. Semantic Web Standards (NON-NEGOTIABLE)

All knowledge graph outputs MUST conform to W3C standards including RDF, OWL,
and SPARQL; JSON-LD contexts MUST be generated from canonical NWB-LinkML schema;
SHACL validation MUST be enforced for all graph data; Provenance tracking using
PROV-O ontology is mandatory for all transformations.

### III. Test-First Development (NON-NEGOTIABLE)

TDD mandatory: Contract tests written → User approved → Tests fail → Then
implement; Red-Green-Refactor cycle strictly enforced; All SPARQL queries,
schema validation, and MCP integrations MUST have failing tests before
implementation; Integration tests required for knowledge graph enrichment
workflows.

### IV. MCP Server Integration

All functionality MUST be exposed through Model Context Protocol interfaces;
Clean separation between knowledge graph core logic and MCP tool layer;
Concurrent access patterns MUST be handled safely; Structured responses
compatible with agent and MCP server interfaces required.

### V. Data Quality Assurance

Quality scoring with configurable thresholds mandatory for all enrichment
operations; Complete lineage tracking from raw NWB to final RDF required;
Evidence trails MUST be maintained for all enrichment decisions; Confidence
levels and reasoning chains required for metadata suggestions.

## Semantic Web Standards

### Ontology Integration Requirements

Core neuroscience ontologies (NIFSTD, UBERON, CHEBI, NCBITaxon) MUST be
integrated with basic concept mapping; OWL equivalence and subsumption
relationships with confidence scoring required; Schema version metadata MUST be
recorded in PROV-O provenance for downstream triples.

### Knowledge Graph Output Standards

JSON-LD with schema-derived @context and TTL formats required; Standard semantic
web protocols (SPARQL endpoints) for knowledge graph access; Efficient query
execution with appropriate indexing and optimization; Runtime schema analysis
for neurodata_type detection and structural pattern recognition.

## Development Workflow

### Validation Gates

All commits MUST pass LinkML schema validation; SHACL shape validation required
before merge; Contract tests for all API endpoints MUST pass; Knowledge graph
queries MUST execute within performance thresholds (<200ms for simple queries,
<30 seconds for complex enrichment operations with human review).

### Code Quality Requirements

Python 3.12+ with type hints enforced via mypy; ruff for linting and formatting;
pytest with coverage requirements for all knowledge graph operations; FastAPI
for HTTP interfaces with proper async handling.

### Branch Protection

All PRs MUST verify constitutional compliance; Schema changes require
regeneration of JSON-LD contexts, SHACL shapes, and RDF/OWL artifacts; Breaking
changes to knowledge graph APIs require deprecation notice and migration path.

## Governance

Constitution supersedes all other development practices; Amendments require
documentation, community review, and migration plan; All PRs and code reviews
MUST verify compliance with semantic web standards and test-first principles;
Complexity deviations MUST be justified with specific rationale and simpler
alternatives analysis; Use CLAUDE.md for runtime development guidance and
technology stack decisions.

**Version**: 1.1.0 | **Ratified**: 2025-09-29 | **Last Amended**: 2025-09-29

=== CONSTITUTION.MD FROM PR #30 (try1_speckit_eval_reporting) === File not found
in this branch

=== CONSTITUTION.MD FROM PR #32 (004-implement-an-agent) ===

# [PROJECT_NAME] Constitution

<!-- Example: Spec Constitution, TaskFlow Constitution, etc. -->

## Core Principles

### [PRINCIPLE_1_NAME]

<!-- Example: I. Library-First -->

[PRINCIPLE_1_DESCRIPTION]

<!-- Example: Every feature starts as a standalone library; Libraries must be self-contained, independently testable, documented; Clear purpose required - no organizational-only libraries -->

### [PRINCIPLE_2_NAME]

<!-- Example: II. CLI Interface -->

[PRINCIPLE_2_DESCRIPTION]

<!-- Example: Every library exposes functionality via CLI; Text in/out protocol: stdin/args → stdout, errors → stderr; Support JSON + human-readable formats -->

### [PRINCIPLE_3_NAME]

<!-- Example: III. Test-First (NON-NEGOTIABLE) -->

[PRINCIPLE_3_DESCRIPTION]

<!-- Example: TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced -->

### [PRINCIPLE_4_NAME]

<!-- Example: IV. Integration Testing -->

[PRINCIPLE_4_DESCRIPTION]

<!-- Example: Focus areas requiring integration tests: New library contract tests, Contract changes, Inter-service communication, Shared schemas -->

### [PRINCIPLE_5_NAME]

<!-- Example: V. Observability, VI. Versioning & Breaking Changes, VII. Simplicity -->

[PRINCIPLE_5_DESCRIPTION]

<!-- Example: Text I/O ensures debuggability; Structured logging required; Or: MAJOR.MINOR.BUILD format; Or: Start simple, YAGNI principles -->

## [SECTION_2_NAME]

<!-- Example: Additional Constraints, Security Requirements, Performance Standards, etc. -->

[SECTION_2_CONTENT]

<!-- Example: Technology stack requirements, compliance standards, deployment policies, etc. -->

## [SECTION_3_NAME]

<!-- Example: Development Workflow, Review Process, Quality Gates, etc. -->

[SECTION_3_CONTENT]

<!-- Example: Code review requirements, testing gates, deployment approval process, etc. -->

## Governance

<!-- Example: Constitution supersedes all other practices; Amendments require documentation, approval, migration plan -->

[GOVERNANCE_RULES]

<!-- Example: All PRs/reviews must verify compliance; Complexity must be justified; Use [GUIDANCE_FILE] for runtime development guidance -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last
Amended**: [LAST_AMENDED_DATE]

<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16 -->

=== CONSTITUTION.MD FROM PR #33 (006-mcp-server-architecture) ===

# [PROJECT_NAME] Constitution

<!-- Example: Spec Constitution, TaskFlow Constitution, etc. -->

## Core Principles

### [PRINCIPLE_1_NAME]

<!-- Example: I. Library-First -->

[PRINCIPLE_1_DESCRIPTION]

<!-- Example: Every feature starts as a standalone library; Libraries must be self-contained, independently testable, documented; Clear purpose required - no organizational-only libraries -->

### [PRINCIPLE_2_NAME]

<!-- Example: II. CLI Interface -->

[PRINCIPLE_2_DESCRIPTION]

<!-- Example: Every library exposes functionality via CLI; Text in/out protocol: stdin/args → stdout, errors → stderr; Support JSON + human-readable formats -->

### [PRINCIPLE_3_NAME]

<!-- Example: III. Test-First (NON-NEGOTIABLE) -->

[PRINCIPLE_3_DESCRIPTION]

<!-- Example: TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced -->

### [PRINCIPLE_4_NAME]

<!-- Example: IV. Integration Testing -->

[PRINCIPLE_4_DESCRIPTION]

<!-- Example: Focus areas requiring integration tests: New library contract tests, Contract changes, Inter-service communication, Shared schemas -->

### [PRINCIPLE_5_NAME]

<!-- Example: V. Observability, VI. Versioning & Breaking Changes, VII. Simplicity -->

[PRINCIPLE_5_DESCRIPTION]

<!-- Example: Text I/O ensures debuggability; Structured logging required; Or: MAJOR.MINOR.BUILD format; Or: Start simple, YAGNI principles -->

## [SECTION_2_NAME]

<!-- Example: Additional Constraints, Security Requirements, Performance Standards, etc. -->

[SECTION_2_CONTENT]

<!-- Example: Technology stack requirements, compliance standards, deployment policies, etc. -->

## [SECTION_3_NAME]

<!-- Example: Development Workflow, Review Process, Quality Gates, etc. -->

[SECTION_3_CONTENT]

<!-- Example: Code review requirements, testing gates, deployment approval process, etc. -->

## Governance

<!-- Example: Constitution supersedes all other practices; Amendments require documentation, approval, migration plan -->

[GOVERNANCE_RULES]

<!-- Example: All PRs/reviews must verify compliance; Complexity must be justified; Use [GUIDANCE_FILE] for runtime development guidance -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last
Amended**: [LAST_AMENDED_DATE]

<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16 -->

=== CONSTITUTION.MD FROM PR #34 (005-testing-quality-assurance) ===

# [PROJECT_NAME] Constitution

<!-- Example: Spec Constitution, TaskFlow Constitution, etc. -->

## Core Principles

### [PRINCIPLE_1_NAME]

<!-- Example: I. Library-First -->

[PRINCIPLE_1_DESCRIPTION]

<!-- Example: Every feature starts as a standalone library; Libraries must be self-contained, independently testable, documented; Clear purpose required - no organizational-only libraries -->

### [PRINCIPLE_2_NAME]

<!-- Example: II. CLI Interface -->

[PRINCIPLE_2_DESCRIPTION]

<!-- Example: Every library exposes functionality via CLI; Text in/out protocol: stdin/args → stdout, errors → stderr; Support JSON + human-readable formats -->

### [PRINCIPLE_3_NAME]

<!-- Example: III. Test-First (NON-NEGOTIABLE) -->

[PRINCIPLE_3_DESCRIPTION]

<!-- Example: TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced -->

### [PRINCIPLE_4_NAME]

<!-- Example: IV. Integration Testing -->

[PRINCIPLE_4_DESCRIPTION]

<!-- Example: Focus areas requiring integration tests: New library contract tests, Contract changes, Inter-service communication, Shared schemas -->

### [PRINCIPLE_5_NAME]

<!-- Example: V. Observability, VI. Versioning & Breaking Changes, VII. Simplicity -->

[PRINCIPLE_5_DESCRIPTION]

<!-- Example: Text I/O ensures debuggability; Structured logging required; Or: MAJOR.MINOR.BUILD format; Or: Start simple, YAGNI principles -->

## [SECTION_2_NAME]

<!-- Example: Additional Constraints, Security Requirements, Performance Standards, etc. -->

[SECTION_2_CONTENT]

<!-- Example: Technology stack requirements, compliance standards, deployment policies, etc. -->

## [SECTION_3_NAME]

<!-- Example: Development Workflow, Review Process, Quality Gates, etc. -->

[SECTION_3_CONTENT]

<!-- Example: Code review requirements, testing gates, deployment approval process, etc. -->

## Governance

<!-- Example: Constitution supersedes all other practices; Amendments require documentation, approval, migration plan -->

[GOVERNANCE_RULES]

<!-- Example: All PRs/reviews must verify compliance; Complexity must be justified; Use [GUIDANCE_FILE] for runtime development guidance -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last
Amended**: [LAST_AMENDED_DATE]

<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amended: 2025-07-16 -->

=== CONSTITUTION.MD FROM PR #35 (try1_speckit_validation_quality_assurance) ===

# Agentic Neurodata Conversion - Validation & QA Constitution

## Core Principles

### I. Modular Architecture First

All validation components must follow clear separation of concerns with granular
modularity. Each module (Core Framework, NWB Inspector, LinkML, Quality
Assessment, Domain Validator, Orchestrator, Reporting, MCP Integration) must be:

- Self-contained with defined interfaces
- Independently testable and deployable
- Well-documented with clear purpose
- No cross-module dependencies except through defined contracts

### II. Standards Compliance (NON-NEGOTIABLE)

- All validation must conform to NWB community standards and best practices
- FAIR principles (Findable, Accessible, Interoperable, Reusable) are mandatory
- Schema validation against current NWB versions is required
- LinkML schemas must be machine-readable and version-controlled

### III. Quality-First Development

- Test-Driven Development for all validation logic
- Multi-dimensional quality metrics: completeness, consistency, accuracy,
  compliance
- Scientific plausibility checks required for all neuroscience data
- Remediation guidance must accompany every validation issue

### IV. Traceability & Observability

- Structured logging with configurable levels across all modules
- Validation context tracking for debugging and audit trails
- Detailed error reporting with stack traces and location information
- Analytics and trend tracking for continuous quality improvement

### V. Configuration & Flexibility

- Profile-based configuration management (dev, test, prod)
- Runtime configuration updates without service restart
- Configurable validation thresholds and filters
- Support for custom quality metrics and domain rules

## Technical Standards

### Data Quality Requirements

- Completeness analysis against schemas and standards
- Consistency validation across related fields and structures
- Accuracy verification through domain knowledge rules
- Compliance checking with weighted scoring algorithms

### Validation Pipeline

- Support for parallel and sequential validation workflows
- Dependency management between validators
- Results aggregation with conflict resolution
- Progress tracking and status reporting

### Integration Architecture

- MCP-compliant tools interface for all validation functions
- Standardized input/output formats (JSON, structured data)
- Asynchronous operation support for long-running validations
- Service discovery and health check endpoints

## Development Workflow

### Implementation Requirements

1. All validators extend `BaseValidator` abstract class
2. All results use `ValidationResult` and `ValidationIssue` dataclasses
3. Exception handling with detailed error context is mandatory
4. Error recovery mechanisms for non-critical failures

### Testing Gates

- Unit tests for individual validators
- Integration tests for validator orchestration
- Domain-specific test cases for neuroscience rules
- Performance benchmarks for large NWB files

### Documentation Standards

- User stories and acceptance criteria for all requirements
- API documentation for all public interfaces
- Remediation guidance for validation issues
- Examples and best practices for common scenarios

## Governance

This constitution supersedes all other development practices. All
implementations must:

- Verify compliance with modular architecture principles
- Include validation against NWB and LinkML schemas
- Provide structured, actionable error messages
- Support both automated and interactive workflows

Amendments require:

- Documentation of rationale and impact
- Approval from project maintainers
- Migration plan for existing implementations
- Update to relevant specifications and tests

**Version**: 1.0.0 | **Ratified**: 2025-10-06 | **Last Amended**: 2025-10-06
