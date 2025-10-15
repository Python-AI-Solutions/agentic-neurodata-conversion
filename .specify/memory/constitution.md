<!--
Constitution Version: 0.1.0
Format: MVP Core Principles Only
Ratified: 2025-10-09
Last Amended: 2025-01-14
Source: Consolidated from 11 feature requirements (1,389 lines)
Amendment: Removed Claude Agent SDK requirement, DataLad mandates, and LinkML schema-first for MVP
-->

# Agentic Neurodata Conversion Constitution (MVP)

**Version**: 0.1.0 **Ratified**: 2025-10-09 **Last Amended**: 2025-01-14 **Scope**: All system features and components

---

## Dependencies management

This project uses Python 3.13 (exact version). All dependencies should be managed using pixi.

**Pixi‑only**

- All commands not available on the shell MUST be run via `pixi`:
  `pixi run <task>` or `pixi <subcommand>`. pixi tasks can be used for all
  development related tasks. If too extensive the task can just run a python
  script stored in the scripts directory.
- Do NOT use `pip`, `conda`, `venv`, `python -m pip`, system Python, or
  `PYTHONPATH` hacks.
- Run scripts through pixi which can add custom dependencies to the script:
  `pixi run python your_script.py`
- Project dependencies should be managed using pixi.toml with appropriate
  environments. The development environment with all development dependencies
  should be the default so that people can get up and running quickly.

## Feature Organization

This constitution governs the following system features:

1. **MCP Server Architecture** - Core orchestration layer (model-agnostic)
2. **Agent Implementations** - Specialized AI agents (conversation, conversion, evaluation)
3. **Client Libraries & Integrations** - Client SDKs
4. **Core Project Organization** - Project infrastructure
5. **Evaluation & Reporting** - Quality metrics
6. **Test Verbosity Optimization** - Testing output management
7. **Testing & Quality Assurance** - Test framework
8. **Validation & Quality Assurance** - NWB validation

## Core Principles

### I. MCP-Centric Architecture (NON-NEGOTIABLE)

All system functionality MUST be exposed through Model Context Protocol (MCP)
tools. The MCP server is the single orchestration point.

**Requirements**:

- All business logic resides in transport-agnostic core services
- MCP server implementation MUST be model-agnostic (support any LLM provider)
- Use MCP Python package (`mcp>=1.0.0`) for protocol communication
- Agents communicate with MCP server via HTTP/REST (no direct agent-to-agent calls)
- Direct agent invocation or feature-to-feature communication without MCP
  mediation is PROHIBITED

**Verification**: Contract tests verify API behavior; integration tests
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
- **E2E**: Test with real neuroscience datasets

**Verification**: CI enforces coverage; code reviews reject untested code.

---

### III. Data Validation & Type Safety (NON-NEGOTIABLE)

All data structures MUST be validated and type-safe. Use Pydantic models for runtime validation.

**Validation Workflow**:

1. Define Pydantic models FIRST
2. Add comprehensive type hints
3. Implement validation logic
4. Create tests
5. ONLY THEN implement features

**Standards**:

- **Pydantic**: Runtime validation and serialization
- **Type Hints**: Full type coverage with mypy strict mode
- **NWB Schema**: Follow NWB format specifications for neuroscience data
- **OpenAPI**: Auto-generated from Pydantic models for API contracts

**Verification**: CI enforces type checking and validation test coverage.

---

### IV. Feature-Driven Architecture & Clear Boundaries (NON-NEGOTIABLE)

Each feature MUST be self-contained with well-defined interfaces and ZERO
cross-feature dependencies except through MCP server.

**Requirements**:

- **Single Responsibility**: Each feature handles one domain
- **Defined Interfaces**: All inter-feature communication through MCP tools with
  OpenAPI contracts
- **Isolated Testing**: Each feature testable in isolation (test with real services in dependency order)
- **Clear Boundaries**: No direct imports between features

**Feature Organization**:

- Core service layer (business logic)
- Interface layer (MCP tools, contracts)
- Test layer (unit, integration, contract, e2e)

**Verification**: Contract tests verify interfaces; each feature has independent
test suite.

---

### V. Data Integrity & Validation (NON-NEGOTIABLE)

All data transformations MUST be validated for quality and compliance.

**Requirements**:

- **Session Context Tracking**: All workflow state persisted (Redis + filesystem)
- **Validation Pipeline**: Multi-stage validation (input → conversion → NWB Inspector)
- **Error Recovery**: Session-level recovery from any failure point
- **Reproducibility**: All conversion parameters recorded in session context

**Validation Stages**:

1. Input structure validation (format detection)
2. Conversion with NeuroConv
3. NWB Inspector validation
4. Quality metrics generation
5. Metadata completeness checks

**Verification**: All conversions produce validation reports; session context
persisted at each stage.

---

### VI. Quality-First Development (NON-NEGOTIABLE)

Comprehensive quality assurance is mandatory across all features and automated
using pre-commit hooks.

**Quality Requirements**:

- **Code Quality**: Automated linting, type checking, cyclomatic complexity <10
- **Test Coverage**: ≥85% (≥90% for critical paths)
- **Input Validation**: Pydantic-based validation for all inputs

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

### 3. Session Context for Data Exchange

All data shared between features tracked in session context with state persistence.

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
- [ ] Pydantic models defined before features
- [ ] Feature boundaries respected (no cross-feature imports)
- [ ] Session context tracking implemented
- [ ] Quality gates passed (coverage ≥85%, linting, type checking)
- [ ] Spec-Kit workflow followed (`/speckit.analyze` + `/speckit.checklist`
      passed)

**Spec-Kit Artifacts**:

- [ ] `/speckit.analyze` passed (link: **\*\***\_**\*\***)
- [ ] `/speckit.checklist` passed (link: **\*\***\_**\*\***)
