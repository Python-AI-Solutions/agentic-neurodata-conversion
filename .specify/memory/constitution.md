<!--
Constitution Version: 0.0.1
Format: MVP Core Principles Only
Ratified: 2025-10-09
Last Amended: 2025-10-09
Source: Consolidated from 11 feature requirements (1,389 lines)
-->

# Agentic Neurodata Conversion Constitution (MVP)

**Version**: 0.0.1 **Ratified**: 2025-10-09 **Scope**: All system features and
components

---

## Feature Organization

This constitution governs 11 system features:

1. **MCP Server Architecture** - Core orchestration layer
2. **Agent Implementations** - Specialized AI agents (conversation, conversion,
   evaluation, questioner)
3. **Agent SDK Integration** - Claude Agent SDK wrappers and thin adapters
4. **Client Libraries & Integrations** - Client SDKs
5. **Core Project Organization** - Project infrastructure
6. **Data Management & Provenance** - DataLad integration
7. **Evaluation & Reporting** - Quality metrics
8. **Knowledge Graph Systems** - Semantic data representation
9. **Test Verbosity Optimization** - Testing output management
10. **Testing & Quality Assurance** - Test framework
11. **Validation & Quality Assurance** - NWB validation

## Core Principles

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

All system functionality MUST be exposed through Model Context Protocol (MCP)
tools. The MCP server is the single orchestration point.

**Requirements**:

- All business logic resides in transport-agnostic core services
- Transport adapters are thin (<500 LOC) with ZERO business logic using Claude
  Agent SDK
- Claude Agent SDK handles protocol communication, context management, and tool
  ecosystem
- Direct agent invocation or feature-to-feature communication without MCP
  mediation is PROHIBITED

**Verification**: Contract tests verify adapter behavior; integration tests
verify MCP mediation.

---

### II. Test-Driven Development (NON-NEGOTIABLE)

All features MUST follow strict TDD workflow. Tests MUST be written before
implementation.

**TDD Workflow**:

1. Write tests first (unit, integration, contract)
2. Verify tests fail (RED)
3. Implement minimum code to pass (GREEN)
4. Refactor while maintaining green tests

**Quality Gates**:

- Critical paths: ≥90% coverage
- Standard features: ≥85% coverage
- All API endpoints have contract tests before implementation

**Test Categories**:

- **Unit**: Test individual components
- **Integration**: Test cross-feature workflows
- **Contract**: 100% OpenAPI coverage, schema validation
- **E2E**: Test with real DataLad datasets

**Verification**: CI enforces coverage; code reviews reject untested code.

---

### III. Schema-First Development (NON-NEGOTIABLE)

NWB-LinkML schema is the canonical source. Every data structure MUST start with
schema definition.

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

### IV. Feature-Driven Architecture & Clear Boundaries (NON-NEGOTIABLE)

Each feature MUST be self-contained with well-defined interfaces and ZERO
cross-feature dependencies except through MCP server.

**Requirements**:

- **Single Responsibility**: Each feature handles one domain
- **Defined Interfaces**: All inter-feature communication through MCP tools with
  OpenAPI contracts
- **Isolated Testing**: Each feature testable in isolation with mocked
  dependencies
- **Clear Boundaries**: No direct imports between features

**Feature Organization**:

- Core service layer (business logic)
- Interface layer (MCP tools, contracts)
- Adapter layer (transport-specific, thin)
- Test layer (unit, integration, contract, e2e)

**Verification**: Contract tests verify interfaces; each feature has independent
test suite.

---

### V. Data Integrity & Complete Provenance (NON-NEGOTIABLE)

All data transformations MUST be tracked with complete provenance.

**Requirements**:

- **DataLad Integration**: ALL data operations use DataLad
- **Provenance Tracking**: PROV-O ontology for all transformations, stored in
  RDF knowledge graph
- **Validation Pipeline**: Multi-stage validation (input → schema → NWB
  Inspector → domain rules)
- **Version Control**: All data files annexed (git-annex + GIN storage for
  files >10MB)
- **Reproducibility**: Bit-for-bit reproduction with recorded parameters

**Validation Stages**:

1. Input structure validation
2. Schema compliance (LinkML + NWB schema)
3. NWB Inspector validation
4. Domain-specific rules
5. Metadata completeness

**Verification**: All conversions produce PROV-O provenance; DataLad API usage
enforced by linters.

---

### VI. Quality-First Development (NON-NEGOTIABLE)

Comprehensive quality assurance is mandatory across all features and automated
using pre-commit hooks.

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

**Verification**: CI gates block merges on failures; coverage reports required
in PRs.

---

### VII. Spec-Kit Workflow Gates (NON-NEGOTIABLE)

All features MUST follow Spec-Kit's workflow with mandatory gates before
implementation.

**Required Workflow**:

1. `/speckit.constitution` - Constitution guides all feature development
2. `/speckit.specify` - Create feature specification
3. `/speckit.plan` - Create implementation plan
4. `/speckit.tasks` - Generate task breakdown
5. `/speckit.analyze` - **MUST PASS** before implementation (cross-artifact
   consistency)
6. `/speckit.checklist` - **MUST PASS** before implementation (quality
   validation)
7. `/speckit.implement` - Execute implementation only after gates pass

**Gate Requirements**:

- `/speckit.analyze` verifies specification consistency and completeness
- `/speckit.checklist` validates all quality criteria are met
- Tasks violating non-negotiable principles MUST be revised before
  implementation
- PR checklist MUST include links to latest analyze/checklist artifacts

**Verification**: PRs without passing analyze/checklist gates are blocked from
merge.

---

## Cross-Feature Integration Rules

### 1. MCP Server as Mediator (NON-NEGOTIABLE)

All inter-feature communication flows through MCP server. Direct
feature-to-feature calls are PROHIBITED.

### 2. Contract-Based Interfaces (NON-NEGOTIABLE)

All feature interfaces defined by OpenAPI contracts. Contract tests enforce
compliance.

### 3. DataLad for Data Exchange

All data shared between features tracked in DataLad datasets with provenance.

### 4. Consistent Error Handling

All features use standard error schemas with error codes, messages, and context.

### 5. Schema Compatibility

Feature APIs use schema versioning (MAJOR.MINOR.PATCH).

---

## Governance

### Constitutional Authority

This constitution is the **supreme governance artifact**. Hierarchy:
Constitution > Technical Specifications (feature requirements) > Code Comments.
Constitutional principles override all other documentation.

### Versioning

- **MAJOR** (X.0.0): New principles, breaking changes
- **MINOR** (x.Y.0): Clarifications, additions
- **PATCH** (x.y.Z): Corrections, typos

### Compliance Checklist (Attach to PRs)

**Core Principles**:

- [ ] MCP-mediated (no direct feature calls)
- [ ] Tests written before implementation (TDD)
- [ ] Schema defined before features
- [ ] Feature boundaries respected (no cross-feature imports)
- [ ] Provenance tracking implemented
- [ ] Quality gates passed (coverage ≥85%, linting, type checking)
- [ ] Spec-Kit workflow followed (`/speckit.analyze` + `/speckit.checklist`
      passed)

**Spec-Kit Artifacts**:

- [ ] `/speckit.analyze` passed (link: ******\_******)
- [ ] `/speckit.checklist` passed (link: ******\_******)
