<!--
Constitution Version: 7.0.0 (MVP)
Format: MVP Core Principles Only
Ratified: 2025-10-09
Last Amended: 2025-10-09
Source: Consolidated from 10 module requirements (1,389 lines)
Change Type: MAJOR - Simplified to MVP essentials only
-->

# Agentic Neurodata Conversion Constitution (MVP)

**Version**: 7.0.0
**Ratified**: 2025-10-09
**Scope**: All system modules and components

---

## Core Principles

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

All system functionality MUST be exposed through Model Context Protocol (MCP) tools. The MCP server is the single orchestration point.

**Requirements**:
- All business logic resides in transport-agnostic core services
- Transport adapters are thin (<500 LOC) with ZERO business logic
- Direct agent invocation or module-to-module communication without MCP mediation is PROHIBITED

**Verification**: Contract tests verify adapter behavior; integration tests verify MCP mediation.

---

### II. Test-Driven Development (NON-NEGOTIABLE)

All features MUST follow strict TDD workflow. Tests MUST be written before implementation.

**TDD Workflow**:
1. Write tests first (unit, integration, contract)
2. Verify tests fail (RED)
3. Implement minimum code to pass (GREEN)
4. Refactor while maintaining green tests

**Quality Gates**:
- Critical paths: ≥90% coverage
- Standard modules: ≥85% coverage
- All API endpoints have contract tests before implementation

**Test Categories**:
- **Unit**: Test individual components
- **Integration**: Test cross-module workflows
- **Contract**: 100% OpenAPI coverage, schema validation
- **E2E**: Test with real DataLad datasets

**Verification**: CI enforces coverage; code reviews reject untested code.

---

### III. Schema-First Development (NON-NEGOTIABLE)

NWB-LinkML schema is the canonical source. Every data structure MUST start with schema definition.

**Schema Workflow**:
1. Define or extend LinkML schema FIRST
2. Generate artifacts (JSON-LD contexts, SHACL shapes, Pydantic validators)
3. Implement validation using schema-derived validators
4. Create tests
5. ONLY THEN implement features

**Standards**:
- **NWB-LinkML**: Canonical source
- **LinkML Validation**: Runtime validation with Pydantic
- **Semantic Web**: RDF, OWL, SPARQL, SHACL support
- **JSON-LD Contexts**: Auto-generated from schemas

**Verification**: CI rejects features without schema definition.

---

### IV. Modular Architecture & Clear Boundaries (NON-NEGOTIABLE)

Each module MUST be self-contained with well-defined interfaces and ZERO cross-module dependencies except through MCP server.

**Requirements**:
- **Single Responsibility**: Each module handles one domain
- **Defined Interfaces**: All inter-module communication through MCP tools with OpenAPI contracts
- **Isolated Testing**: Each module testable in isolation with mocked dependencies
- **Clear Boundaries**: No direct imports between modules

**Module Organization**:
- Core service layer (business logic)
- Interface layer (MCP tools, contracts)
- Adapter layer (transport-specific, thin)
- Test layer (unit, integration, contract, e2e)

**Verification**: Contract tests verify interfaces; each module has independent test suite.

---

### V. Data Integrity & Complete Provenance (NON-NEGOTIABLE)

All data transformations MUST be tracked with complete provenance.

**Requirements**:
- **DataLad Integration**: ALL data operations use DataLad Python API (NEVER CLI)
- **Provenance Tracking**: PROV-O ontology for all transformations, stored in RDF knowledge graph
- **Validation Pipeline**: Multi-stage validation (input → schema → NWB Inspector → domain rules)
- **Version Control**: All data files annexed (git-annex + GIN storage for files >10MB)
- **Reproducibility**: Bit-for-bit reproduction with recorded parameters

**Validation Stages**:
1. Input structure validation
2. Schema compliance (LinkML + NWB schema)
3. NWB Inspector validation
4. Domain-specific rules
5. Metadata completeness

**Verification**: All conversions produce PROV-O provenance; DataLad API usage enforced by linters.

---

### VI. Quality-First Development (NON-NEGOTIABLE)

Comprehensive quality assurance is mandatory across all modules.

**Quality Requirements**:
- **Code Quality**: Automated linting, type checking, cyclomatic complexity <10
- **Test Coverage**: ≥85% (≥90% for critical paths)
- **Input Validation**: Schema-based validation for all inputs

**Logging**:
- **Structured Logging**: Configurable levels with contextual data
- **Error Tracking**: Clear error messages with stack traces

**CI/CD**:
- **PR Pipeline**: Tests, linting, type checking, coverage checks
- **Periodic**: E2E tests, performance benchmarks

**Verification**: CI gates block merges on failures; coverage reports required in PRs.

---

## Shared Technical Standards

### Language & Environment
- **Python**: 3.11+ with type hints enforced
- **Package Manager**: Reproducible environment management
- **Configuration**: Environment-aware configuration

### Code Quality
- **Linting**: Automated code style checks
- **Type Checking**: Strict static type checking
- **Complexity Limit**: Cyclomatic complexity <10

### Testing
- **Framework**: Comprehensive testing framework with async support
- **Coverage**: Coverage tracking and enforcement
- **Contract Testing**: API contract validation against OpenAPI specs

### Documentation
- **API Docs**: OpenAPI specs auto-generated from code
- **Code Docs**: Docstrings for all public APIs
- **User Docs**: User documentation with examples

### Performance
- **Benchmarking**: Performance regression detection

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
Module APIs use schema versioning (MAJOR.MINOR.PATCH).

---

## Governance

### Amendment Process
1. **Propose**: Document change with rationale
2. **Review**: Team review and approval
3. **Update**: Increment version, update documentation

### Versioning Policy
- **MAJOR** (X.0.0): New principles, breaking changes
- **MINOR** (x.Y.0): Clarifications, additions
- **PATCH** (x.y.Z): Corrections, typos

### Compliance Verification Checklist

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

**Hierarchy**:
1. This Constitution (supreme governance)
2. Technical Specifications (module requirements)
3. Code Comments (implementation details)

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
2. **Agent Implementations** - Specialized AI agents
3. **Client Libraries & Integrations** - Client SDKs
4. **Core Project Organization** - Project infrastructure
5. **Data Management & Provenance** - DataLad integration
6. **Evaluation & Reporting** - Quality metrics
7. **Knowledge Graph Systems** - Semantic data representation
8. **Test Verbosity Optimization** - Testing output management
9. **Testing & Quality Assurance** - Test framework
10. **Validation & Quality Assurance** - NWB validation

**See**: `.kiro/specs/*/requirements.md` for detailed module requirements

---

**Version**: 7.0.0 (MVP)
**Ratified**: 2025-10-09
**Supersedes**: All prior versions (1.0.0 - 6.0.0)

**Source**: Core MVP principles from 10 module specifications. Detailed technical requirements in module-specific specification files.
