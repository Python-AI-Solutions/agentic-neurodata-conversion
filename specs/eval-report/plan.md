# Implementation Plan: NWB Evaluation and Reporting System

**Branch**: `001-eval-report` | **Date**: 2025-10-03 | **Spec**:
[spec.md](spec.md) **Input**: Feature specification from
`/specs/001-eval-report/spec.md`

## Summary

Build a comprehensive NWB file evaluation and reporting system that validates
neuroscience data files using nwb-inspector with circuit breaker fallback (3
consecutive failures), performs multi-dimensional quality assessment (technical,
scientific, usability) with parallel execution and 0-100 scoring scale,
generates reports in multiple formats (Markdown, HTML, PDF, JSON) with Chart.js
visualizations, and integrates with MCP server supporting 5 concurrent requests
with 1-second health check response time.

## Technical Context

**Language/Version**: Python 3.11+ **Primary Dependencies**: nwb-inspector,
pydantic, asyncio, Chart.js (for HTML reports), MCP SDK **Storage**: File system
for NWB files, logs, and generated reports **Testing**: pytest, pytest-asyncio,
pytest-cov (>80% coverage target) **Target Platform**: Linux/macOS servers,
containerizable **Project Type**: single (Python library with MCP server
integration) **Performance Goals**: <1s health check response, 60s default
validation timeout, handle multi-GB NWB files **Constraints**: Circuit breaker
(3 failures), 5 concurrent requests max, 7-day audit log retention, offline HTML
visualizations **Scale/Scope**: Production neuroscience data pipeline,
research-grade quality assessment

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### Initial Check (Pre-Research)

| Principle                                  | Compliance Status | Notes                                                                     |
| ------------------------------------------ | ----------------- | ------------------------------------------------------------------------- |
| I. NWB Data Quality & Scientific Integrity | ✅ PASS           | nwb-inspector as primary validation, 0-100 scoring, audit trails          |
| II. Robust Error Handling                  | ✅ PASS           | Circuit breaker (3 failures), graceful degradation, fallback validation   |
| III. Modular Architecture                  | ✅ PASS           | Independent evaluators, parallel execution, well-defined interfaces       |
| IV. Test-First (NON-NEGOTIABLE)            | ✅ PASS           | TDD approach, contract/integration/unit tests, >80% coverage target       |
| V. Performance Optimization                | ✅ PASS           | Async/await patterns, parallel evaluators, 60s timeout, <1s health checks |
| VI. Scientific Documentation               | ✅ PASS           | User-facing docs for scientists, clear remediation recommendations        |
| VII. MCP Integration                       | ✅ PASS           | MCP protocol, 5 concurrent requests, structured responses, audit logs     |

**Result**: All constitutional principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```
specs/001-eval-report/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── validation.yaml
│   ├── quality_assessment.yaml
│   ├── reporting.yaml
│   └── mcp_integration.yaml
└── tasks.md             # Phase 2 output (/tasks command)
```

### Source Code (repository root)

```
src/nwb_evaluation/
├── validation/
│   ├── __init__.py
│   ├── inspector_validator.py     # nwb-inspector wrapper
│   ├── fallback_validator.py      # Circuit breaker fallback
│   └── circuit_breaker.py         # Circuit breaker implementation
├── quality/
│   ├── __init__.py
│   ├── base_evaluator.py          # Abstract evaluator interface
│   ├── technical_evaluator.py     # Schema, integrity, structure
│   ├── scientific_evaluator.py    # Experimental completeness, design
│   ├── usability_evaluator.py     # Documentation, searchability
│   └── orchestrator.py            # Parallel execution coordinator
├── reporting/
│   ├── __init__.py
│   ├── base_reporter.py           # Abstract reporter interface
│   ├── markdown_reporter.py
│   ├── html_reporter.py           # Chart.js visualizations
│   ├── pdf_reporter.py
│   ├── json_reporter.py
│   └── templates/                 # Report templates
├── mcp/
│   ├── __init__.py
│   ├── server.py                  # MCP server implementation
│   ├── tools.py                   # MCP tool definitions
│   └── schemas.py                 # Request/response schemas
├── models/
│   ├── __init__.py
│   ├── validation_result.py
│   ├── quality_assessment.py
│   ├── evaluation_config.py
│   └── audit_log.py
└── utils/
    ├── __init__.py
    ├── logging.py
    └── config.py

tests/
├── contract/
│   ├── test_validation_contract.py
│   ├── test_quality_contract.py
│   ├── test_reporting_contract.py
│   └── test_mcp_contract.py
├── integration/
│   ├── test_end_to_end_evaluation.py
│   ├── test_circuit_breaker_flow.py
│   ├── test_parallel_execution.py
│   └── test_mcp_workflows.py
└── unit/
    ├── validation/
    ├── quality/
    ├── reporting/
    ├── mcp/
    └── models/
```

**Structure Decision**: Single Python project (Option 1) selected. This is a
focused library with MCP server capabilities, not a multi-tier web/mobile
application. Modular package structure supports independent evaluator
development and testing.

## Phase 0: Outline & Research

### Research Topics

1. **nwb-inspector Integration**
   - Decision: Use nwb-inspector CLI via subprocess with JSON output parsing
   - Rationale: Official NWB validation tool, community standard, JSON output
     for structured parsing
   - Alternatives considered: Direct Python API (less stable), custom validation
     (reinventing wheel)

2. **Circuit Breaker Pattern**
   - Decision: Implement custom circuit breaker with 3-failure threshold,
     exponential backoff for reset
   - Rationale: Matches constitutional requirement for robust error handling
   - Alternatives considered: pybreaker library (added dependency), no circuit
     breaker (violates constitution)

3. **Async/Parallel Execution**
   - Decision: Python asyncio with asyncio.gather for parallel evaluators,
     semaphore for concurrency limit (5)
   - Rationale: Native Python support, efficient for I/O-bound operations,
     precise concurrency control
   - Alternatives considered: multiprocessing (overhead for pickling), threading
     (GIL limitations)

4. **MCP Integration**
   - Decision: Use official MCP Python SDK, implement as standalone server with
     tool-based API
   - Rationale: Standard protocol compliance, agent interoperability
   - Alternatives considered: Custom REST API (not MCP compliant), embedded
     server (deployment complexity)

5. **Report Generation**
   - Decision: Template-based generation (Jinja2), Chart.js CDN-free bundle for
     HTML
   - Rationale: Flexible templating, offline visualization requirement
   - Alternatives considered: Plotly (external dependencies), custom SVG
     (development time)

6. **PDF Generation**
   - Decision: WeasyPrint for HTML-to-PDF conversion
   - Rationale: CSS support, consistent rendering with HTML reports
   - Alternatives considered: ReportLab (low-level API), Pandoc (external binary
     dependency)

7. **Audit Logging**
   - Decision: Structured JSON logs with automatic 7-day rotation
   - Rationale: Machine-readable, standard retention policy
   - Alternatives considered: Database storage (added complexity), plain text
     logs (harder to query)

**Output**: [research.md](research.md)

## Phase 1: Design & Contracts

### Data Model ([data-model.md](data-model.md))

**ValidationResult**

- Fields: nwb_file_path (str), validator_source (enum: nwb_inspector |
  fallback), severity_level (enum: error | warning | info), issues
  (List[ValidationIssue]), timestamp (datetime), execution_time (float)
- ValidationIssue: message (str), file_location (str), remediation (str)
- Validation: Non-empty nwb_file_path, valid timestamp

**QualityDimension**

- Fields: dimension_name (enum: technical | scientific | usability), score (int
  0-100), metrics (Dict[str, MetricResult]), findings (List[Finding])
- MetricResult: metric_name (str), score (int 0-100), details (str)
- Finding: severity (enum: critical | major | minor), description (str),
  remediation (str)
- Validation: Score range 0-100, non-empty metrics

**QualityAssessment**

- Fields: validation_result (ValidationResult), technical_quality
  (QualityDimension), scientific_quality (QualityDimension), usability_quality
  (QualityDimension), overall_score (int 0-100), dimension_weights (Dict[str,
  float]), timestamp (datetime)
- Validation: Weights sum to 1.0, overall score computed from weighted
  dimensions

**EvaluatorConfiguration**

- Fields: enabled_evaluators (List[str]), nwb_inspector_timeout (int,
  default=60), circuit_breaker_threshold (int, default=3), dimension_weights
  (Dict[str, float], default equal), parallel_execution (bool, default=True)
- Validation: Timeout > 0, threshold > 0, weights sum to 1.0

**EvaluationReport**

- Fields: quality_assessment (QualityAssessment), format (enum: markdown | html
  | pdf | json), content (str | bytes), generated_at (datetime),
  executive_summary (str), detailed_findings (List[str])
- Validation: Format-specific content validation

**MCPEvaluationRequest**

- Fields: request_id (UUID), nwb_file_path (str), evaluator_config
  (EvaluatorConfiguration), output_formats (List[str]), timestamp (datetime)
- Validation: Valid file path, at least one output format

**EvaluationAuditLog**

- Fields: request_id (UUID), request_timestamp (datetime), evaluators_executed
  (List[str]), overall_score (int), execution_duration (float), errors
  (List[str]), source (enum: mcp | direct), retention_until (datetime, +7 days)
- State transitions: created → executing → completed/failed → archived (after 7
  days)

### API Contracts ([contracts/](contracts/))

**validation.yaml** (OpenAPI 3.0)

```yaml
/validate:
  post:
    summary: Validate NWB file
    requestBody:
      nwb_file_path: string
      timeout: integer (default 60)
    responses:
      200: ValidationResult
      408: Timeout with partial results
      503: Circuit breaker open, fallback used
```

**quality_assessment.yaml**

```yaml
/assess:
  post:
    summary: Perform quality assessment
    requestBody:
      validation_result: ValidationResult
      config: EvaluatorConfiguration
    responses:
      200: QualityAssessment
      206: Partial assessment (some evaluators failed)
```

**reporting.yaml**

```yaml
/generate_report:
  post:
    summary: Generate evaluation report
    requestBody:
      quality_assessment: QualityAssessment
      formats: array of (markdown | html | pdf | json)
    responses:
      200: List[EvaluationReport]
      207: Multi-status (some formats failed)
```

**mcp_integration.yaml** (MCP Protocol)

```yaml
tools:
  evaluate_nwb:
    description: Complete NWB file evaluation
    input_schema:
      nwb_file_path: string
      output_formats: array
      config: object (optional)
    output_schema: QualityAssessment + List[EvaluationReport]

  health_check:
    description: Server health status
    input_schema: {}
    output_schema:
      status: string (healthy | degraded)
      response_time_ms: integer (<1000)
```

### Contract Tests (Failing - TDD)

Generated in `tests/contract/`:

- test_validation_contract.py: Validates request/response schemas for /validate
- test_quality_contract.py: Validates /assess schemas
- test_reporting_contract.py: Validates /generate_report multi-format output
- test_mcp_contract.py: Validates MCP tool input/output schemas, health check
  <1s

### Quickstart ([quickstart.md](quickstart.md))

```markdown
# NWB Evaluation Quickstart

## Installation

pip install nwb-evaluation

## Basic Usage

from nwb_evaluation import evaluate_nwb_file

result = evaluate_nwb_file("path/to/file.nwb", output_formats=["html", "json"])
print(f"Overall Quality Score: {result.quality_assessment.overall_score}/100")

## MCP Server

nwb-eval-server --port 8080

# Agent can now call evaluate_nwb tool

## Test Scenarios

1. Valid NWB file → Score >80, all green metrics
2. Invalid file with circuit breaker → Fallback validation, partial score
3. Concurrent requests (5) → All complete within SLA
```

### Agent Context Update

Run: `nwb-evaluation/.specify/scripts/bash/update-agent-context.sh claude`

Updates CLAUDE.md with:

- Python 3.11+, asyncio patterns
- nwb-inspector integration notes
- MCP protocol compliance requirements
- Test coverage expectations (>80%)

**Phase 1 Output**: data-model.md, contracts/, failing contract tests,
quickstart.md, CLAUDE.md updated

### Post-Design Constitution Check

| Principle                                  | Compliance Status | Notes                                                          |
| ------------------------------------------ | ----------------- | -------------------------------------------------------------- |
| I. NWB Data Quality & Scientific Integrity | ✅ PASS           | ValidationResult tracks source, audit logs ensure traceability |
| II. Robust Error Handling                  | ✅ PASS           | Circuit breaker in design, fallback validator defined          |
| III. Modular Architecture                  | ✅ PASS           | Base evaluator interfaces, parallel orchestrator               |
| IV. Test-First (NON-NEGOTIABLE)            | ✅ PASS           | Contract tests written (failing), integration tests planned    |
| V. Performance Optimization                | ✅ PASS           | Asyncio in orchestrator, timeout configs, concurrency limits   |
| VI. Scientific Documentation               | ✅ PASS           | Remediation in Finding model, executive summaries in reports   |
| VII. MCP Integration                       | ✅ PASS           | MCP tools defined, health check contract <1s                   |

**Result**: All principles satisfied. No constitutional violations. Proceed to
Phase 2 planning.

## Phase 2: Task Planning Approach

_This section describes what the /tasks command will do - DO NOT execute during
/plan_

**Task Generation Strategy**:

1. Load `.specify/templates/tasks-template.md`
2. Generate from Phase 1 artifacts:
   - Each contract → contract test implementation task [P]
   - Each data model → Pydantic model creation task [P]
   - Base evaluator interface → abstract class task
   - Each evaluator (technical, scientific, usability) → implementation task
   - Orchestrator → parallel execution logic task
   - Each reporter → format-specific implementation task [P]
   - MCP server → tool registration + health check task
   - Circuit breaker → state machine implementation task
   - Integration tests → end-to-end workflow tasks
   - Documentation → quickstart validation task

**Ordering Strategy**:

- TDD order: Contract tests → Models → Interfaces → Implementations →
  Integration tests
- Dependency order:
  1. Models (no dependencies) [P]
  2. Validation contract tests [P]
  3. Inspector validator + circuit breaker
  4. Quality contract tests [P]
  5. Base evaluator + concrete evaluators [P after base]
  6. Orchestrator (depends on evaluators)
  7. Reporting contract tests [P]
  8. Reporters [P]
  9. MCP contract tests
  10. MCP server (depends on all above)
  11. Integration tests (depends on all components)
  12. Documentation + quickstart

**Parallelization** [P]: Models, contract tests, evaluators (after base),
reporters

**Estimated Output**: 30-35 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

_These phases are beyond the scope of the /plan command_

**Phase 3**: Task execution (/tasks command creates tasks.md) **Phase 4**:
Implementation (execute tasks.md following TDD + constitutional principles)
**Phase 5**: Validation (run tests, verify >80% coverage, performance
benchmarks, execute quickstart.md)

## Complexity Tracking

_Fill ONLY if Constitution Check has violations that must be justified_

No constitutional violations. This section intentionally empty.

## Progress Tracking

_This checklist is updated during execution flow_

**Phase Status**:

- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:

- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (via /clarify)
- [x] Complexity deviations documented (none)

---

_Based on Constitution v1.0.0 - See
`nwb-evaluation/.specify/memory/constitution.md`_
