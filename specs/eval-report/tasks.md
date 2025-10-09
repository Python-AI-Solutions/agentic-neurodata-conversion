# Tasks: NWB Evaluation and Reporting System

**Input**: Design documents from `/specs/001-eval-report/` **Prerequisites**:
plan.md ✓, research.md ✓, data-model.md ✓

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- All paths relative to repository root

## Phase 3.1: Setup

- [ ] **T001** Create project structure per plan.md with
      src/nwb_evaluation/{validation,quality,reporting,mcp,models,utils}/ and
      tests/{contract,integration,unit}/
- [ ] **T002** Initialize Python 3.11+ project with pyproject.toml,
      dependencies: nwb-inspector, pydantic, asyncio, jinja2, weasyprint, mcp,
      pytest, pytest-asyncio, pytest-cov
- [ ] **T003** [P] Configure ruff linting, black formatting, mypy type checking
      in pyproject.toml

## Phase 3.2: Data Models (Foundation) ⚠️ MUST COMPLETE BEFORE TESTS

- [ ] **T004** [P] Create enum definitions in
      `src/nwb_evaluation/models/__init__.py`: ValidatorSource, SeverityLevel,
      DimensionName, FindingSeverity, ReportFormat, RequestSource
- [ ] **T005** [P] Create ValidationIssue Pydantic model in
      `src/nwb_evaluation/models/validation_result.py` with fields: message,
      file_location, remediation, severity
- [ ] **T006** [P] Create ValidationResult Pydantic model in
      `src/nwb_evaluation/models/validation_result.py` with fields:
      nwb_file_path, validator_source, severity_level, issues, timestamp,
      execution_time; validate nwb_file_path non-empty, execution_time >= 0
- [ ] **T007** [P] Create MetricResult and Finding Pydantic models in
      `src/nwb_evaluation/models/quality_assessment.py` with score validation
      (0-100 range)
- [ ] **T008** [P] Create QualityDimension Pydantic model in
      `src/nwb_evaluation/models/quality_assessment.py` with score calculation
      from metrics (weighted average, rounded to int)
- [ ] **T009** [P] Create QualityAssessment Pydantic model in
      `src/nwb_evaluation/models/quality_assessment.py` with overall_score
      calculation from dimension_weights (must sum to 1.0 ±0.01)
- [ ] **T010** [P] Create EvaluatorConfiguration Pydantic model in
      `src/nwb_evaluation/models/evaluation_config.py` with defaults:
      timeout=60, threshold=3, weights={'technical': 0.33, 'scientific': 0.33,
      'usability': 0.34}, parallel=True, max_concurrent=5
- [ ] **T011** [P] Create EvaluationReport Pydantic model in
      `src/nwb_evaluation/models/evaluation_config.py` with format-specific
      content validation (pdf=bytes, others=str)
- [ ] **T012** [P] Create MCPEvaluationRequest Pydantic model in
      `src/nwb_evaluation/models/evaluation_config.py` with UUID request_id,
      validate output_formats non-empty
- [ ] **T013** [P] Create EvaluationAuditLog Pydantic model in
      `src/nwb_evaluation/models/audit_log.py` with
      retention_until=timestamp+7days, state enum
      (created/executing/completed/failed/archived)

## Phase 3.3: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE IMPLEMENTATION

### Contract Tests (All [P] - different files)

- [ ] **T014** [P] Write contract test for nwb-inspector validation in
      `tests/contract/test_validation_contract.py`: assert ValidationResult
      schema, timeout handling, JSON parsing from subprocess output
- [ ] **T015** [P] Write contract test for circuit breaker fallback in
      `tests/contract/test_validation_contract.py`: assert ValidationResult with
      validator_source=fallback after 3 failures
- [ ] **T016** [P] Write contract test for technical evaluator in
      `tests/contract/test_quality_contract.py`: assert QualityDimension schema
      with technical metrics (schema_compliance, data_integrity,
      structure_quality)
- [ ] **T017** [P] Write contract test for scientific evaluator in
      `tests/contract/test_quality_contract.py`: assert QualityDimension schema
      with scientific metrics (experimental_completeness, design_consistency,
      documentation_adequacy)
- [ ] **T018** [P] Write contract test for usability evaluator in
      `tests/contract/test_quality_contract.py`: assert QualityDimension schema
      with usability metrics (documentation_clarity, searchability,
      accessibility)
- [ ] **T019** [P] Write contract test for quality orchestrator in
      `tests/contract/test_quality_contract.py`: assert QualityAssessment schema
      with all 3 dimensions, overall_score calculation, parallel execution
- [ ] **T020** [P] Write contract test for markdown reporter in
      `tests/contract/test_reporting_contract.py`: assert EvaluationReport with
      format=markdown, content is string, executive_summary <=500 words
- [ ] **T021** [P] Write contract test for HTML reporter in
      `tests/contract/test_reporting_contract.py`: assert embedded Chart.js,
      offline capability, responsive layout
- [ ] **T022** [P] Write contract test for PDF reporter in
      `tests/contract/test_reporting_contract.py`: assert content is bytes,
      WeasyPrint output
- [ ] **T023** [P] Write contract test for JSON reporter in
      `tests/contract/test_reporting_contract.py`: assert structured data, all
      fields present
- [ ] **T024** [P] Write contract test for MCP evaluate_nwb tool in
      `tests/contract/test_mcp_contract.py`: assert input schema (nwb_file_path,
      output_formats, config), output schema (QualityAssessment + reports)
- [ ] **T025** [P] Write contract test for MCP health_check tool in
      `tests/contract/test_mcp_contract.py`: assert response_time_ms < 1000,
      status field present

### Integration Tests (All [P] - different test files)

- [ ] **T026** [P] Write integration test for end-to-end evaluation in
      `tests/integration/test_end_to_end_evaluation.py`: valid NWB file →
      validation → quality assessment → all 4 report formats generated
- [ ] **T027** [P] Write integration test for circuit breaker flow in
      `tests/integration/test_circuit_breaker_flow.py`: mock nwb-inspector
      failures → 3rd failure triggers fallback → partial quality assessment →
      graceful degradation
- [ ] **T028** [P] Write integration test for parallel execution in
      `tests/integration/test_parallel_execution.py`: 3 evaluators run in
      parallel → all complete → orchestrator aggregates → overall_score
      calculated correctly
- [ ] **T029** [P] Write integration test for MCP workflow in
      `tests/integration/test_mcp_workflows.py`: MCP request → evaluate_nwb tool
      → returns QualityAssessment + reports → audit log created
- [ ] **T030** [P] Write integration test for concurrent MCP requests in
      `tests/integration/test_mcp_workflows.py`: 5 concurrent requests → all
      isolated → no shared state mutations → all complete successfully
- [ ] **T031** [P] Write integration test for audit log retention in
      `tests/integration/test_audit_log_retention.py`: create logs → verify
      7-day retention_until → mock time advance → verify deletion

**CRITICAL CHECKPOINT**: Run all tests (T014-T031). ALL MUST FAIL. If any pass,
investigate why before proceeding.

## Phase 3.4: Core Implementation (ONLY after all tests failing)

### Validation Module

- [ ] **T032** Implement CircuitBreaker class in
      `src/nwb_evaluation/validation/circuit_breaker.py`: states
      (CLOSED/OPEN/HALF_OPEN), 3-failure threshold, exponential backoff
      (60s/120s/240s), thread-safe
- [ ] **T033** Implement InspectorValidator in
      `src/nwb_evaluation/validation/inspector_validator.py`: async validate()
      method, subprocess nwb-inspector CLI, 60s timeout, JSON parsing, returns
      ValidationResult
- [ ] **T034** Implement FallbackValidator in
      `src/nwb_evaluation/validation/fallback_validator.py`: basic NWB file
      structure checks, returns ValidationResult with validator_source=fallback
- [ ] **T035** Integrate CircuitBreaker with InspectorValidator: wrap subprocess
      calls, track failures, switch to FallbackValidator after 3 failures

### Quality Assessment Module

- [ ] **T036** [P] Create BaseEvaluator abstract class in
      `src/nwb_evaluation/quality/base_evaluator.py`: abstract async
      evaluate(validation_result) → QualityDimension
- [ ] **T037** [P] Implement TechnicalEvaluator in
      `src/nwb_evaluation/quality/technical_evaluator.py`: metrics
      (schema_compliance, data_integrity, structure_quality, performance),
      calculate 0-100 scores, generate Findings with remediation
- [ ] **T038** [P] Implement ScientificEvaluator in
      `src/nwb_evaluation/quality/scientific_evaluator.py`: metrics
      (experimental_completeness, design_consistency, documentation_adequacy),
      domain-specific scoring, scientific remediation recommendations
- [ ] **T039** [P] Implement UsabilityEvaluator in
      `src/nwb_evaluation/quality/usability_evaluator.py`: metrics
      (documentation_clarity, searchability, metadata_richness, accessibility),
      NLP-based scoring if applicable
- [ ] **T040** Implement QualityOrchestrator in
      `src/nwb_evaluation/quality/orchestrator.py`: async
      coordinate_evaluators() using asyncio.gather(), apply dimension_weights,
      calculate overall_score, handle partial failures gracefully

### Reporting Module

- [ ] **T041** [P] Create BaseReporter abstract class in
      `src/nwb_evaluation/reporting/base_reporter.py`: abstract
      generate(quality_assessment) → EvaluationReport
- [ ] **T042** [P] Create Jinja2 templates in
      `src/nwb_evaluation/reporting/templates/`: executive_summary.md.j2,
      detailed_report.md.j2, report.html.j2 (with Chart.js CDN-free bundle),
      report.json.j2
- [ ] **T043** [P] Implement MarkdownReporter in
      `src/nwb_evaluation/reporting/markdown_reporter.py`: use Jinja2 templates,
      generate tables for metrics, bullet lists for findings
- [ ] **T044** [P] Implement HTMLReporter in
      `src/nwb_evaluation/reporting/html_reporter.py`: embed Chart.js bundle
      (download minified), generate bar/pie/line charts, color coding (green
      80-100, yellow 60-79, red 0-59), responsive CSS
- [ ] **T045** [P] Implement PDFReporter in
      `src/nwb_evaluation/reporting/pdf_reporter.py`: reuse HTMLReporter,
      convert to PDF via WeasyPrint, print-optimized CSS
- [ ] **T046** [P] Implement JSONReporter in
      `src/nwb_evaluation/reporting/json_reporter.py`: serialize
      QualityAssessment to JSON, include all fields

### MCP Integration Module

- [ ] **T047** Define MCP tool schemas in `src/nwb_evaluation/mcp/schemas.py`:
      evaluate_nwb input/output schemas using Pydantic, health_check schemas
- [ ] **T048** Implement MCP tools in `src/nwb_evaluation/mcp/tools.py`:
      evaluate_nwb() calls validation → orchestrator → reporters, health_check()
      returns status + response_time_ms
- [ ] **T049** Implement MCP server in `src/nwb_evaluation/mcp/server.py`:
      register tools, asyncio.Semaphore(5) for concurrency limit, proper
      isolation per request, audit logging
- [ ] **T050** Add health check timing in MCP server: measure response time,
      assert < 1000ms, return structured status

### Utils and Configuration

- [ ] **T051** [P] Implement structured logging in
      `src/nwb_evaluation/utils/logging.py`: JSON format,
      TimedRotatingFileHandler with 7-day rotation, include request_id context
- [ ] **T052** [P] Implement configuration management in
      `src/nwb_evaluation/utils/config.py`: load from environment variables
      using pydantic-settings, provide defaults from EvaluatorConfiguration

### Integration and Wiring

- [ ] **T053** Create main evaluation function in
      `src/nwb_evaluation/__init__.py`: evaluate_nwb_file(path, config,
      output_formats) → (QualityAssessment, List[EvaluationReport]), wire all
      components
- [ ] **T054** Create CLI entry point in `src/nwb_evaluation/__main__.py`:
      argparse for file path, formats, config options; call evaluate_nwb_file();
      print results
- [ ] **T055** Create MCP server entry point: `nwb-eval-server` command, parse
      --port argument, start MCP server with asyncio

**CHECKPOINT**: Run all contract and integration tests (T014-T031). ALL MUST
PASS NOW. Fix any failures before continuing.

## Phase 3.5: Unit Tests and Coverage

- [ ] **T056** [P] Unit tests for CircuitBreaker in
      `tests/unit/validation/test_circuit_breaker.py`: state transitions,
      failure counting, backoff timing, thread safety
- [ ] **T057** [P] Unit tests for InspectorValidator in
      `tests/unit/validation/test_inspector_validator.py`: mock subprocess, JSON
      parsing, timeout handling, ValidationResult creation
- [ ] **T058** [P] Unit tests for FallbackValidator in
      `tests/unit/validation/test_fallback_validator.py`: basic structure
      checks, ValidationResult with fallback source
- [ ] **T059** [P] Unit tests for TechnicalEvaluator in
      `tests/unit/quality/test_technical_evaluator.py`: metric calculations,
      score ranges (0-100), Finding generation
- [ ] **T060** [P] Unit tests for ScientificEvaluator in
      `tests/unit/quality/test_scientific_evaluator.py`: scientific metric
      scoring, remediation recommendations
- [ ] **T061** [P] Unit tests for UsabilityEvaluator in
      `tests/unit/quality/test_usability_evaluator.py`: usability metric
      scoring, accessibility checks
- [ ] **T062** [P] Unit tests for QualityOrchestrator in
      `tests/unit/quality/test_orchestrator.py`: parallel execution, weight
      application, overall_score calculation, partial failure handling
- [ ] **T063** [P] Unit tests for all reporters in
      `tests/unit/reporting/test_reporters.py`: template rendering,
      format-specific validation, Chart.js embedding, WeasyPrint conversion
- [ ] **T064** [P] Unit tests for MCP tools in `tests/unit/mcp/test_tools.py`:
      schema validation, tool execution, health check timing
- [ ] **T065** [P] Unit tests for MCP server in `tests/unit/mcp/test_server.py`:
      concurrency limiting (5 max), request isolation, audit logging

**CHECKPOINT**: Run pytest with coverage:
`pytest --cov=src/nwb_evaluation --cov-report=term-missing`. Assert >= 80%
coverage. Add tests for uncovered lines.

## Phase 3.6: Performance and Documentation

- [ ] **T066** Performance test for health check in
      `tests/integration/test_performance.py`: assert health_check responds <
      1000ms under load
- [ ] **T067** Performance test for large NWB files in
      `tests/integration/test_performance.py`: test with multi-GB file, verify
      timeout handling, memory usage stays reasonable
- [ ] **T068** Performance test for concurrent requests in
      `tests/integration/test_performance.py`: 5 concurrent evaluations complete
      within SLA
- [ ] **T069** [P] Create quickstart.md validation: run all quickstart examples,
      verify outputs match expectations
- [ ] **T070** [P] Update README.md with installation, basic usage, MCP server
      setup, configuration options
- [ ] **T071** [P] Create API documentation in docs/api.md: document all public
      interfaces, include neuroscience-relevant examples per constitutional
      principle VI
- [ ] **T072** [P] Create troubleshooting guide in docs/troubleshooting.md:
      common circuit breaker scenarios, timeout adjustments, audit log queries

## Dependencies

**Critical TDD Dependencies**:

- T004-T013 (models) MUST complete before T014-T031 (tests)
- T014-T031 (all tests) MUST complete and FAIL before T032-T055 (implementation)
- T032-T055 (implementation) MUST make T014-T031 PASS

**Module Dependencies**:

- T032-T035 (validation) before T040 (orchestrator)
- T036-T039 (evaluators) before T040 (orchestrator)
- T040 (orchestrator) before T041-T046 (reporting)
- T032-T052 (all core) before T053 (main function)
- T053 (main function) before T054-T055 (entry points)

**Test Dependencies**:

- T056-T065 (unit tests) after corresponding implementation
- T066-T068 (performance) after T053 (end-to-end working)
- T069-T072 (docs) can run anytime after T053

## Parallel Execution Examples

### Data Models (T004-T013 - all parallel, different files)

```bash
# Launch all 10 model tasks together
```

### Contract Tests (T014-T025 - can group by module)

```bash
# Group 1: Validation contracts
T014, T015

# Group 2: Quality contracts
T016, T017, T018, T019

# Group 3: Reporting contracts
T020, T021, T022, T023

# Group 4: MCP contracts
T024, T025
```

### Integration Tests (T026-T031 - all parallel, different files)

```bash
# All can run in parallel
T026, T027, T028, T029, T030, T031
```

### Core Implementation (Selective parallelization)

```bash
# Parallel group 1: Evaluators (after BaseEvaluator T036)
T037, T038, T039

# Parallel group 2: Reporters (after BaseReporter T041 and templates T042)
T043, T044, T045, T046

# Parallel group 3: Utils
T051, T052
```

### Unit Tests (T056-T065 - all parallel after implementation)

```bash
# All can run in parallel
T056, T057, T058, T059, T060, T061, T062, T063, T064, T065
```

## Task Execution Checklist

- [ ] All T014-T031 tests written and FAILING (TDD Red phase)
- [ ] All T032-T055 implementation makes tests PASS (TDD Green phase)
- [ ] Pytest coverage >= 80% after T056-T065
- [ ] All T066-T068 performance benchmarks pass
- [ ] All T069-T072 documentation complete and validated
- [ ] Constitution compliance verified (all 7 principles)
- [ ] Manual execution of quickstart.md examples successful

## Notes

- **TDD CRITICAL**: Tests MUST fail before implementation. No shortcuts.
- **Parallel [P] tasks**: Different files, no dependencies, can run
  simultaneously
- **Sequential tasks**: Same file modifications, must run in order
- **Commit frequency**: After each task completion
- **Constitutional compliance**: Validate against all 7 principles throughout
- **Coverage target**: >= 80% per constitutional principle IV

Total Tasks: 72 Estimated Parallel Tasks: ~35 (48%) Estimated Time: 3-5 sprints
depending on team size
