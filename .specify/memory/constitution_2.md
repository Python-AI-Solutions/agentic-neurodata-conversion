# Agentic Neurodata Conversion Constitution

## Core Principles

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

All functionality MUST be exposed through Model Context Protocol (MCP) tools. The MCP server is the single orchestration point for all operations.

**Requirements**:
- All business logic resides in transport-agnostic core services
- Transport adapters are thin (<500 LOC) with ZERO business logic
- Functional parity across all transports verified by contract tests
- Direct agent invocation or module-to-module communication without MCP mediation is PROHIBITED

**Rationale**: Centralizing through MCP creates a unified API surface, enables horizontal scaling, simplifies client integration, and maintains clean separation between business logic and transport mechanisms.

**Verification**: Contract tests verify adapter parity; integration tests verify MCP mediation.

---

### II. Test-Driven Development (NON-NEGOTIABLE)

All features MUST follow strict TDD workflow. Tests MUST be written before ANY implementation begins.

**TDD Workflow**:
1. Write tests first (unit, integration, contract)
2. Verify tests fail (RED)
3. Implement minimum code to pass (GREEN)
4. Refactor while maintaining green tests

**Quality Gates**:
- Critical paths (MCP server, agents, validation): ≥90% coverage
- Standard modules: ≥85% coverage
- Contract tests: 100% OpenAPI specification coverage
- All API endpoints have contract tests before implementation

**Test Categories**:
- **Unit**: Test individual components with comprehensive coverage
- **Integration**: Test cross-module workflows with 20+ scenarios
- **Contract**: 100% OpenAPI coverage with schema validation
- **E2E**: Test with real DataLad-managed datasets

**Rationale**: Neuroscience data conversion is mission-critical. TDD ensures correctness, prevents regressions, and provides living documentation.

**Verification**: CI enforces coverage; code reviews reject untested code.

---

### III. Schema-First Development (NON-NEGOTIABLE)

NWB-LinkML schema is the canonical source. Every data structure MUST start with schema definition.

**Schema Workflow** (Mandatory Sequence):
1. Define or extend LinkML schema FIRST
2. Generate artifacts (JSON-LD contexts, SHACL shapes, Pydantic validators)
3. Implement validation using schema-derived validators
4. Create tests using schema-derived validators
5. ONLY THEN implement features

**Standards**:
- **NWB-LinkML**: Canonical source with version metadata
- **LinkML Validation**: Runtime validation with Pydantic class generation
- **Semantic Web**: RDF, OWL, SPARQL, SHACL (W3C compliance)
- **JSON-LD Contexts**: Auto-generated from LinkML schemas
- **Version Control**: Schema changes tracked with semantic versioning

**Rationale**: Schema-first prevents validation inconsistencies, enables contract-based development, and ensures interoperability across modules and external tools.

**Verification**: CI rejects features without schema definition; validation logic must use schema-derived validators.

---

### IV. Modular Architecture & Clear Boundaries (NON-NEGOTIABLE)

Each module MUST be self-contained with well-defined interfaces and ZERO cross-module dependencies except through MCP server.

**Requirements**:
- **Single Responsibility**: Each module handles one domain
- **Defined Interfaces**: All inter-module communication through MCP tools with OpenAPI contracts
- **Isolated Testing**: Each module testable in isolation with mocked dependencies
- **Clear Boundaries**: No direct imports between modules; shared code via published libraries only

**Module Organization**:
- Core service layer (business logic, transport-agnostic)
- Interface layer (MCP tools, contracts, schemas)
- Adapter layer (transport-specific, thin)
- Test layer (unit, integration, contract, e2e)

**Rationale**: Modularity enables parallel development, independent scaling, easier testing, and reduces cognitive load.

**Verification**: Dependency analysis tools detect cross-module imports; contract tests verify interfaces.

---

### V. Data Integrity & Complete Provenance (NON-NEGOTIABLE)

All data transformations MUST be tracked with complete provenance. Data integrity is absolute.

**Requirements**:
- **DataLad Integration**: ALL data operations use DataLad Python API (NEVER CLI)
- **Provenance Tracking**: PROV-O ontology for all transformations, stored in RDF knowledge graph
- **Validation Pipeline**: Multi-stage validation (input → schema → NWB Inspector → domain rules)
- **Version Control**: All data files annexed (git-annex + GIN storage for files >10MB)
- **Audit Trail**: Complete lineage from raw data through conversion to final NWB files
- **Reproducibility**: Bit-for-bit reproduction with recorded parameters

**Validation Stages**:
1. Input structure validation (before conversion)
2. Schema compliance (LinkML + NWB schema)
3. NWB Inspector validation (community standards)
4. Domain-specific rules (scientific plausibility)
5. Metadata completeness (required fields)

**Rationale**: Invalid conversions compromise scientific reproducibility. Complete provenance enables verification, debugging, and trust in converted data.

**Verification**: All conversions produce PROV-O provenance; validation failures halt pipeline; DataLad API usage enforced by linters.

---

### VI. Quality-First Development (NON-NEGOTIABLE)

Comprehensive quality assurance is mandatory across all modules.

**Code Quality**:
- **Linting**: Automated code style checks (ruff)
- **Type Checking**: Strict static type checking (mypy)
- **Complexity**: Cyclomatic complexity <10 (exceptions require justification)

**Testing Standards**:
- **Coverage**: ≥85% for standard modules, ≥90% for critical paths
- **Property Testing**: Property-based testing with Hypothesis for complex logic
- **Contract Testing**: API contract validation against OpenAPI specs
- **Performance Testing**: Benchmarks with regression detection

**CI/CD**:
- **PR Pipeline**: Tests, linting, type checking, coverage checks
- **Periodic**: E2E tests, performance benchmarks

**Observability**:
- **Structured Logging**: Configurable levels with contextual data
- **Error Tracking**: Clear error messages with stack traces

**Rationale**: Proactive quality assurance catches issues early. Observability enables debugging and optimization.

**Verification**: CI gates block merges on failures; coverage reports required in PRs.

---

## Development Standards

### Language & Environment
- **Python**: 3.11+ with type hints enforced
- **Package Manager**: pixi for reproducible environments
- **Configuration**: pydantic-settings for environment-aware config

### Documentation
- **API Docs**: OpenAPI specs auto-generated from code
- **Code Docs**: Docstrings (Google style) for all public APIs
- **User Docs**: User documentation with examples

### Performance
- **Benchmarking**: Performance regression detection
- **Response Times**: Documented and enforced per operation type

---

## Cross-Module Integration Rules

### 1. MCP Server as Mediator (NON-NEGOTIABLE)
All inter-module communication flows through MCP server. Direct module-to-module calls are PROHIBITED.

### 2. Contract-Based Interfaces (NON-NEGOTIABLE)
All module interfaces defined by OpenAPI contracts. Contract tests enforce compliance.

### 3. DataLad for Data Exchange
All data shared between modules tracked in DataLad datasets with provenance.

### 4. Consistent Error Handling
All modules use standard error schemas with error codes, messages, and context.

### 5. Schema Compatibility
Module APIs use schema versioning (MAJOR.MINOR.PATCH) with backward compatibility guarantees.

---

## Governance

### Amendment Process
1. **Propose**: Document change with rationale and impact analysis
2. **Review**: Team review and approval
3. **Update**: Increment version, update documentation

### Versioning Policy
- **MAJOR** (X.0.0): New principles, breaking changes
- **MINOR** (x.Y.0): Clarifications, additions
- **PATCH** (x.y.Z): Corrections, typos

### Compliance Checklist

Every feature implementation MUST verify:

**Core Principles**:
- [ ] MCP-mediated (no direct module calls)
- [ ] Tests written before implementation (TDD)
- [ ] Schema defined before features
- [ ] Module boundaries respected (no cross-module imports)
- [ ] Provenance tracking implemented
- [ ] Quality gates passed (coverage ≥85%, linting, type checking)

**Technical Standards**:
- [ ] Python 3.11+ with type hints
- [ ] Code quality checks pass
- [ ] Test coverage requirements met
- [ ] Input validation implemented (schema-based)
- [ ] Documentation updated

**Integration Rules**:
- [ ] MCP server mediation verified
- [ ] Contract-based interfaces used
- [ ] Error handling consistent

### Constitutional Authority

**Hierarchy** (highest to lowest):
1. This Constitution (supreme governance)
2. Technical Specifications (module requirements)
3. Implementation Guidelines (best practices)
4. Code Comments (implementation details)

**Conflict Resolution**: Constitutional principles override all other documentation.

**Exception Process**:
1. **Justification**: Document why alternatives are insufficient
2. **Approval**: Team approval required
3. **Documentation**: Document exception with rationale

**Enforcement**:
- Code reviews verify compliance (violations block merge)
- CI/CD pipelines validate constraints

---

## Module Organization

This constitution governs 10 system modules:

1. **MCP Server Architecture** - Core orchestration layer
2. **Agent Implementations** - Specialized AI agents (conversation, conversion, evaluation, metadata)
3. **Client Libraries & Integrations** - Client SDKs for external integration
4. **Core Project Organization** - Project infrastructure and tooling
5. **Data Management & Provenance** - DataLad integration and tracking
6. **Evaluation & Reporting** - Quality metrics and visualization
7. **Knowledge Graph Systems** - Semantic data representation with NWB ontologies
8. **Test Verbosity Optimization** - Testing output management
9. **Testing & Quality Assurance** - Comprehensive test framework
10. **Validation & Quality Assurance** - NWB file validation system

**See**: `.kiro/specs/*/requirements.md` for detailed module requirements

---

**Version**: 1.0.0
**Ratified**: 2025-10-09
**Last Amended**: 2025-10-09

**Source**: Core principles extracted from 10 module specifications (1,389 lines of requirements). Detailed technical requirements remain in module-specific specification files.
