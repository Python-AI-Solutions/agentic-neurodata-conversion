# Tasks: Validation and Quality Assurance System

**Input**: Design documents from `/specs/001-validation-quality-assurance/`
**Prerequisites**: ✓ plan.md, ✓ research.md, ✓ spec.md, ✓ clarify.md

## Execution Flow (main)

```
1. ✓ Load plan.md from feature directory
   → Tech stack: Python 3.9-3.13, nwbinspector, linkml-runtime, pydantic, pytest
   → Structure: Single project (src/validation_qa/, tests/, cli/)
2. ✓ Load design documents:
   → spec.md: 44 functional requirements across 8 modules
   → research.md: Technology decisions and implementation patterns
3. ✓ Generate tasks by category:
   → Setup: project init, dependencies, module structure
   → Tests: contract tests for all modules
   → Core: BaseValidator, ValidationResult, config management
   → Modules: NWB Inspector, LinkML, Quality, Domain, Orchestrator, Reporting, MCP
   → Polish: integration tests, documentation, performance validation
4. ✓ Apply task rules:
   → Different files/modules = [P] for parallel
   → TDD order: Tests before implementation
5. ✓ Number tasks sequentially (T001-T065)
6. ✓ Validate task completeness
9. SUCCESS - Tasks ready for execution
```

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Exact file paths included in descriptions

## Phase 3.1: Setup & Project Structure

- [ ] T001 Create module directory structure:
      src/validation_qa/{core,nwb_inspector,linkml,quality,domain,orchestrator,reporting,mcp}/
      with **init**.py files
- [ ] T002 Create test directory structure:
      tests/{contract,integration,unit}/{core,nwb_inspector,linkml,quality,domain,orchestrator,reporting,mcp}/
- [ ] T003 Create contracts directory:
      specs/001-validation-quality-assurance/contracts/
- [ ] T004 Create CLI directory: cli/ with **init**.py
- [ ] T005 [P] Configure pytest in pyproject.toml with test markers (contract,
      integration, unit, slow)
- [ ] T006 [P] Add validation_qa dependencies to pixi.toml: nwbinspector>=0.4.0,
      linkml-runtime>=1.7.0, pydantic>=2.0.0, plotly>=5.0.0, jinja2>=3.1.0
- [ ] T007 [P] Create .specify/templates/ for report templates

## Phase 3.2: Phase 1 Design Documents (from plan.md)

- [ ] T008 Create specs/001-validation-quality-assurance/data-model.md defining:
      ValidationResult, ValidationIssue, QualityMetric, ValidationConfig,
      ValidationWorkflow, DomainRule, ValidationReport entities
- [ ] T009 Create
      specs/001-validation-quality-assurance/contracts/validator-api.yaml
      (OpenAPI spec for validation endpoints)
- [ ] T010 Create
      specs/001-validation-quality-assurance/contracts/orchestrator-api.yaml
      (OpenAPI spec for workflow endpoints)
- [ ] T011 Create
      specs/001-validation-quality-assurance/contracts/mcp-tools.yaml (MCP tool
      definitions)
- [ ] T012 Create specs/001-validation-quality-assurance/quickstart.md with
      installation, basic usage, custom metrics, custom rules examples

## Phase 3.3: Contract Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.4

**CRITICAL: These tests MUST be written and MUST FAIL before ANY
implementation**

### Module 1: Core Framework Contract Tests

- [ ] T013 [P] Contract test for BaseValidator abstract class interface in
      tests/contract/test_base_validator_contract.py
- [ ] T014 [P] Contract test for ValidationResult dataclass structure in
      tests/contract/test_validation_result_contract.py
- [ ] T015 [P] Contract test for ValidationIssue dataclass structure in
      tests/contract/test_validation_issue_contract.py
- [ ] T016 [P] Contract test for ValidationConfig class interface in
      tests/contract/test_validation_config_contract.py

### Module 2-8: Validator Contract Tests

- [ ] T017 [P] Contract test for NWB Inspector validator interface in
      tests/contract/test_nwb_inspector_contract.py
- [ ] T018 [P] Contract test for LinkML validator interface in
      tests/contract/test_linkml_validator_contract.py
- [ ] T019 [P] Contract test for Quality metrics interface in
      tests/contract/test_quality_metrics_contract.py
- [ ] T020 [P] Contract test for Domain validator interface in
      tests/contract/test_domain_validator_contract.py
- [ ] T021 [P] Contract test for Orchestrator interface in
      tests/contract/test_orchestrator_contract.py
- [ ] T022 [P] Contract test for Report generator interface in
      tests/contract/test_report_generator_contract.py
- [ ] T023 [P] Contract test for MCP tools interface in
      tests/contract/test_mcp_tools_contract.py

### Integration Test Scenarios (from spec.md acceptance scenarios)

- [ ] T024 [P] Integration test: Validate NWB file with comprehensive checks in
      tests/integration/test_comprehensive_validation.py
- [ ] T025 [P] Integration test: Validation session with multiple files and
      aggregation in tests/integration/test_multi_file_validation.py
- [ ] T026 [P] Integration test: Validation report with remediation guidance in
      tests/integration/test_report_with_remediation.py
- [ ] T027 [P] Integration test: Runtime configuration updates in
      tests/integration/test_runtime_config.py
- [ ] T028 [P] Integration test: Domain-specific scientific plausibility checks
      in tests/integration/test_scientific_plausibility.py

## Phase 3.4: Core Implementation - Module 1 (ONLY after contract tests are failing)

### Core Framework - Base Classes

- [ ] T029 [P] Implement BaseValidator abstract class in
      src/validation_qa/core/base_validator.py with validate() method, config
      property
- [ ] T030 [P] Implement ValidationResult dataclass in
      src/validation_qa/core/validation_result.py with issues, severity,
      metadata fields
- [ ] T031 [P] Implement ValidationIssue dataclass in
      src/validation_qa/core/validation_result.py with severity, location,
      description, remediation fields
- [ ] T032 [P] Implement ValidationConfig class in
      src/validation_qa/core/config.py with profile-based settings (dev, test,
      prod), runtime updates (FR-004)

### Core Framework - Supporting Infrastructure

- [ ] T033 [P] Implement validation context tracking in
      src/validation_qa/core/context.py for debugging and audit trails
- [ ] T034 [P] Implement structured logging setup in
      src/validation_qa/core/logging.py with configurable levels (FR-005)
- [ ] T035 [P] Implement custom exceptions in
      src/validation_qa/core/exceptions.py with detailed error context
- [ ] T036 Verify all Module 1 contract tests pass for core framework

## Phase 3.5: Module Implementations

### Module 2: NWB Inspector Integration

- [ ] T037 [P] Implement NWB Inspector wrapper in
      src/validation_qa/nwb_inspector/inspector_validator.py extending
      BaseValidator
- [ ] T038 [P] Implement schema compliance validator in
      src/validation_qa/nwb_inspector/schema_compliance.py (FR-007, FR-011)
- [ ] T039 [P] Implement FAIR principles validator in
      src/validation_qa/nwb_inspector/fair_validator.py (FR-009)
- [ ] T040 [P] Implement best practices checker in
      src/validation_qa/nwb_inspector/best_practices.py (FR-008, FR-010)
- [ ] T041 Verify all Module 2 contract tests pass for NWB Inspector

### Module 3: LinkML Schema Validation

- [ ] T042 [P] Implement LinkML schema loader in
      src/validation_qa/linkml/schema_loader.py with versioning support (FR-012,
      FR-014)
- [ ] T043 [P] Implement Pydantic class generator in
      src/validation_qa/linkml/pydantic_gen.py from LinkML schemas
- [ ] T044 [P] Implement runtime metadata validator in
      src/validation_qa/linkml/runtime_validator.py (FR-013)
- [ ] T045 [P] Implement vocabulary validator in
      src/validation_qa/linkml/vocabulary.py with 3-tier suggestion strategy
      (FR-015, FR-016)
- [ ] T046 Verify all Module 3 contract tests pass for LinkML validation

### Module 4: Quality Assessment Engine

- [ ] T047 [P] Implement BaseQualityMetric abstract class in
      src/validation_qa/quality/base_metric.py with decorator registration
- [ ] T048 [P] Implement built-in quality metrics in
      src/validation_qa/quality/metrics.py (completeness, consistency, accuracy,
      compliance) (FR-017)
- [ ] T049 [P] Implement completeness analyzer in
      src/validation_qa/quality/completeness.py (FR-021, FR-022)
- [ ] T050 [P] Implement weighted scoring algorithm in
      src/validation_qa/quality/scoring.py with confidence intervals (FR-018,
      FR-020)
- [ ] T051 [P] Create example custom metric for testing metric registration
      (FR-019)
- [ ] T052 Verify all Module 4 contract tests pass for quality assessment

### Module 5: Domain Knowledge Validator

- [ ] T053 [P] Implement BaseDomainRule abstract class in
      src/validation_qa/domain/base_rule.py
- [ ] T054 [P] Implement scientific plausibility checker in
      src/validation_qa/domain/plausibility.py (FR-023, FR-024, FR-025)
- [ ] T055 [P] Implement electrophysiology rules in
      src/validation_qa/domain/rules/electrophysiology.py (FR-026)
- [ ] T056 [P] Implement imaging rules in
      src/validation_qa/domain/rules/imaging.py (FR-026)
- [ ] T057 [P] Implement behavioral rules in
      src/validation_qa/domain/rules/behavioral.py (FR-026)
- [ ] T058 [P] Create domain_rules.yaml configuration with simple plausibility
      checks (FR-027)
- [ ] T059 Verify all Module 5 contract tests pass for domain validation

### Module 6: Validation Orchestrator

- [ ] T060 [P] Implement workflow definition in
      src/validation_qa/orchestrator/workflow.py with dependencies and execution
      order
- [ ] T061 [P] Implement pipeline manager in
      src/validation_qa/orchestrator/pipeline.py (FR-028, FR-029, FR-030)
- [ ] T062 [P] Implement results aggregator in
      src/validation_qa/orchestrator/aggregator.py (FR-031, FR-032, FR-033)
- [ ] T063 [P] Implement parallel/sequential scheduler in
      src/validation_qa/orchestrator/scheduler.py
- [ ] T064 Verify all Module 6 contract tests pass for orchestration

### Module 7: Reporting and Analytics

- [ ] T065 [P] Create HTML report Jinja2 template in
      src/validation_qa/reporting/templates/html_report.jinja2
- [ ] T066 [P] Implement report generator in
      src/validation_qa/reporting/report_generator.py for JSON and HTML (FR-034)
- [ ] T067 [P] Implement visualization generator in
      src/validation_qa/reporting/visualizations.py using Plotly (bar charts,
      pie charts, line graphs, tables) (FR-036)
- [ ] T068 [P] Implement executive summary generator in
      src/validation_qa/reporting/executive_summary.py (FR-035)
- [ ] T069 [P] Implement analytics engine in
      src/validation_qa/reporting/analytics.py (FR-037, FR-038, FR-039)
- [ ] T070 Verify all Module 7 contract tests pass for reporting

### Module 8: MCP Integration Layer

- [ ] T071 [P] Implement MCP tools in src/validation_qa/mcp/tools.py
      (validate_nwb_file, assess_quality, generate_report, analyze_trends)
      (FR-040, FR-041)
- [ ] T072 [P] Implement async validator in
      src/validation_qa/mcp/async_validator.py with AsyncExitStack pattern
      (FR-042)
- [ ] T073 [P] Implement MCP server integration in
      src/validation_qa/mcp/server.py (FR-043)
- [ ] T074 [P] Implement health checks in src/validation_qa/mcp/health.py with
      monitoring endpoints (FR-044)
- [ ] T075 Verify all Module 8 contract tests pass for MCP integration

## Phase 3.6: CLI and End-to-End Integration

- [ ] T076 Implement CLI entry point in cli/validate.py with commands: validate,
      assess-quality, generate-report
- [ ] T077 Integrate all modules in src/validation_qa/**init**.py with public
      API exports
- [ ] T078 Create example NWB files for testing in tests/fixtures/
- [ ] T079 Run all integration tests (T024-T028) and verify they pass
- [ ] T080 Run quickstart.md examples and verify all scenarios work

## Phase 3.7: Polish & Documentation

### Unit Tests

- [ ] T081 [P] Unit tests for core validation framework in tests/unit/core/
- [ ] T082 [P] Unit tests for NWB Inspector integration in
      tests/unit/nwb_inspector/
- [ ] T083 [P] Unit tests for LinkML validation in tests/unit/linkml/
- [ ] T084 [P] Unit tests for quality metrics in tests/unit/quality/
- [ ] T085 [P] Unit tests for domain validation in tests/unit/domain/
- [ ] T086 [P] Unit tests for orchestrator in tests/unit/orchestrator/
- [ ] T087 [P] Unit tests for reporting in tests/unit/reporting/
- [ ] T088 [P] Unit tests for MCP integration in tests/unit/mcp/

### Performance & Validation

- [ ] T089 Performance test: Validate <1GB NWB file in <30 seconds in
      tests/performance/test_validation_speed.py
- [ ] T090 Performance test: Memory usage <2GB for standard workflows in
      tests/performance/test_memory_usage.py
- [ ] T091 Test concurrent validation of multiple files in
      tests/performance/test_concurrent_validation.py

### Documentation

- [ ] T092 [P] Create API documentation for all public interfaces
- [ ] T093 [P] Create user guide with examples for each module
- [ ] T094 [P] Create developer guide for custom metrics and domain rules
- [ ] T095 Update README.md with validation system overview and quickstart

### Code Quality

- [ ] T096 Run pytest with coverage report (target >80% coverage)
- [ ] T097 Run type checking with mypy on all modules
- [ ] T098 Format code with black and run ruff linting
- [ ] T099 Remove code duplication and refactor for clarity
- [ ] T100 Final constitution compliance check against all 5 principles

## Dependencies

**Critical Path**:

```
Setup (T001-T007)
  → Design Docs (T008-T012)
  → Contract Tests (T013-T028)
  → Core Framework (T029-T036)
  → Module Implementations (T037-T075)
  → CLI Integration (T076-T080)
  → Polish (T081-T100)
```

**Key Blocking Dependencies**:

- T029-T036 (Core Framework) blocks all module implementations (T037+)
- T036 (Core tests pass) blocks Module 2-8 implementations
- T037-T075 (All modules) block T076-T080 (Integration)
- T079-T080 (Integration tests pass) block T089-T091 (Performance)
- All implementation blocks documentation (T092-T095)

**Parallelization Opportunities**:

- T013-T023: All contract tests (11 tasks in parallel)
- T024-T028: All integration test scenarios (5 tasks in parallel)
- T029-T035: Core framework components (7 tasks in parallel)
- T037-T040: NWB Inspector module (4 tasks in parallel)
- T042-T045: LinkML module (4 tasks in parallel)
- T047-T051: Quality module (5 tasks in parallel)
- T053-T058: Domain module (6 tasks in parallel)
- T060-T063: Orchestrator module (4 tasks in parallel)
- T065-T069: Reporting module (5 tasks in parallel)
- T071-T074: MCP module (4 tasks in parallel)
- T081-T088: Unit tests (8 tasks in parallel)
- T089-T091: Performance tests (3 tasks in parallel)
- T092-T095: Documentation (4 tasks in parallel)

## Parallel Execution Example

### Phase 3.3: Launch all contract tests together

```bash
# 11 contract tests in parallel
pytest tests/contract/test_base_validator_contract.py &
pytest tests/contract/test_validation_result_contract.py &
pytest tests/contract/test_validation_issue_contract.py &
pytest tests/contract/test_validation_config_contract.py &
pytest tests/contract/test_nwb_inspector_contract.py &
pytest tests/contract/test_linkml_validator_contract.py &
pytest tests/contract/test_quality_metrics_contract.py &
pytest tests/contract/test_domain_validator_contract.py &
pytest tests/contract/test_orchestrator_contract.py &
pytest tests/contract/test_report_generator_contract.py &
pytest tests/contract/test_mcp_tools_contract.py &
wait
```

### Phase 3.4: Implement core framework in parallel

```bash
# 7 core components in parallel (different files)
# Work on: base_validator.py, validation_result.py, config.py,
# context.py, logging.py, exceptions.py simultaneously
```

## Validation Checklist

_GATE: Verify before execution_

- [x] All contracts have corresponding tests (T013-T023)
- [x] All entities have model tasks (T029-T031 for core, T047, T053, T060)
- [x] All tests come before implementation (Phase 3.3 before 3.4)
- [x] Parallel tasks truly independent (verified - different files/modules)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] 44 functional requirements mapped to tasks
- [x] All 8 modules have implementation tasks
- [x] TDD workflow enforced (contract tests → implementation → integration
      tests)

## Notes

- **Total Tasks**: 100 tasks across 7 phases
- **Estimated Parallel Tasks**: ~40 tasks can run in parallel
- **Critical for TDD**: Run contract tests (T013-T028) and verify failures
  before ANY implementation
- **Module Independence**: Modules 2-8 can be implemented in parallel after Core
  Framework (T036) completes
- **Integration Milestone**: T079-T080 are key validation gates before
  performance testing
- **Constitution Compliance**: Final check at T100 ensures all principles are
  met

**Test-Driven Development Flow**:

1. Write contract test (must fail) ✗
2. Implement minimum code to pass ✓
3. Refactor for quality
4. Commit
5. Next task

**Commit Strategy**: Commit after each task completion with message format:
`[T###] Task description`
