# Research: NWB Evaluation and Reporting System

## Technology Decisions

### 1. nwb-inspector Integration

**Decision**: Use nwb-inspector CLI via subprocess with JSON output parsing

**Rationale**:
- Official NWB validation tool maintained by NWB community
- Community-accepted standard for validation
- JSON output format provides structured, parseable results
- CLI interface is stable and well-documented

**Alternatives Considered**:
- Direct Python API: Less stable, internal APIs change frequently
- Custom validation: Would reinvent NWB validation logic, not community-accepted
- PyNWB validation only: Less comprehensive than nwb-inspector's checks

**Implementation Notes**:
- Use `subprocess.run()` with timeout parameter (default 60s)
- Parse JSON output using standard `json` library
- Implement proper error handling for subprocess failures
- Circuit breaker wraps subprocess calls

### 2. Circuit Breaker Pattern

**Decision**: Custom circuit breaker with 3-failure threshold, exponential backoff for reset

**Rationale**:
- Matches constitutional requirement (II. Robust Error Handling)
- Spec clarification: 3 consecutive failures trigger fallback
- Simple state machine: Closed → Open → Half-Open
- No additional dependencies needed

**Alternatives Considered**:
- pybreaker library: Added dependency, more features than needed
- No circuit breaker: Violates constitutional principle II
- Retry-only pattern: Doesn't prevent cascading failures

**Implementation Notes**:
- States: CLOSED (normal), OPEN (fallback active), HALF_OPEN (testing recovery)
- Failure count resets on success
- Exponential backoff: 60s, 120s, 240s before half-open attempts
- Thread-safe for concurrent requests

### 3. Async/Parallel Execution

**Decision**: Python asyncio with `asyncio.gather()` for parallel evaluators, `asyncio.Semaphore` for concurrency limit

**Rationale**:
- Native Python 3.11+ support, no extra dependencies
- Efficient for I/O-bound operations (file reading, subprocess calls)
- Precise concurrency control (5 concurrent requests from spec)
- Matches constitutional principle V (Performance Optimization)

**Alternatives Considered**:
- multiprocessing: High overhead for pickling NWB files, overkill for I/O-bound tasks
- threading: Python GIL limits true parallelism, less elegant async code
- Celery/task queue: Infrastructure overhead, unnecessary for in-process parallel evaluation

**Implementation Notes**:
- Evaluators implement async methods: `async def evaluate()`
- Orchestrator uses `asyncio.gather(*evaluator_tasks)` for parallel execution
- Global semaphore limits concurrent MCP requests to 5
- Use `asyncio.timeout()` for per-evaluator timeouts

### 4. MCP Integration

**Decision**: Official MCP Python SDK, standalone server with tool-based API

**Rationale**:
- Standard protocol compliance (constitutional principle VII)
- Agent interoperability across different AI coding agents
- SDK handles protocol details, connection management
- Tools pattern matches evaluation workflow

**Alternatives Considered**:
- Custom REST API: Not MCP compliant, wouldn't integrate with agents
- Embedded server: Deployment complexity, harder to test independently
- Function calling only: Doesn't support full MCP capabilities (resources, prompts)

**Implementation Notes**:
- Define tools: `evaluate_nwb`, `health_check`
- Use Pydantic schemas for request/response validation
- Implement proper error handling with MCP error codes
- Health check MUST respond <1s (spec requirement)

### 5. Report Generation

**Decision**: Jinja2 templates for all formats, Chart.js CDN-free bundle for HTML visualizations

**Rationale**:
- Jinja2: Industry standard, flexible, minimal learning curve
- Chart.js CDN-free: Meets offline requirement (constitutional principle, Quality Standards)
- Template approach: Easy to customize branding, maintain consistency
- Single data model → multiple format outputs

**Alternatives Considered**:
- Plotly: Requires external CDN or large bundle, more complex than needed
- Custom SVG generation: High development time, harder to maintain
- ReportLab for all formats: Low-level API, PDF-focused

**Implementation Notes**:
- Templates: `executive_summary.md.j2`, `report.html.j2`, `report_base.html`
- Chart.js: Download minified bundle, include inline in HTML template
- Color scheme: Green (80-100), Yellow (60-79), Red (0-59)
- Chart types: Bar (dimension scores), Pie (score distribution), Line (trend if applicable)

### 6. PDF Generation

**Decision**: WeasyPrint for HTML-to-PDF conversion

**Rationale**:
- Reuses HTML template, ensures visual consistency
- Full CSS support including flexbox, grid
- Pure Python, no external binaries needed
- Handles embedded Chart.js output (renders to static in PDF)

**Alternatives Considered**:
- ReportLab: Low-level API, would need separate template system
- Pandoc: External binary dependency, deployment complexity
- pdfkit/wkhtmltopdf: Deprecated, security concerns

**Implementation Notes**:
- Render HTML report first with Chart.js
- WeasyPrint converts HTML→PDF preserving layout
- Embed Chart.js output as static image for PDF
- Use CSS @media print for PDF-specific styling

### 7. Audit Logging

**Decision**: Structured JSON logs with automatic 7-day rotation (spec requirement)

**Rationale**:
- Machine-readable for querying, analysis
- 7-day retention from spec clarification
- Standard Python `logging` module with `TimedRotatingFileHandler`
- Matches constitutional principle VII (MCP Integration audit requirements)

**Alternatives Considered**:
- Database storage: Added complexity, overkill for 7-day retention
- Plain text logs: Harder to parse programmatically
- Syslog: External dependency, not always available

**Implementation Notes**:
- Format: JSON lines, one log entry per line
- Fields: request_id, timestamp, evaluators_executed, overall_score, execution_duration, errors, source
- Rotation: `TimedRotatingFileHandler(when='D', interval=7, backupCount=0)`
- Log level: INFO for successful evaluations, ERROR for failures

### 8. Quality Scoring Algorithm

**Decision**: Weighted average of dimension scores (0-100 each), configurable weights (default: equal 1/3 each)

**Rationale**:
- Spec clarification: 0-100 percentage scale
- Constitutional principle I: Clear, measurable quality metrics
- Allows customization via EvaluatorConfiguration.dimension_weights
- Simple, interpretable formula

**Formula**:
```
overall_score = (
    technical_score * technical_weight +
    scientific_score * scientific_weight +
    usability_score * usability_weight
)
where weights sum to 1.0
```

**Implementation Notes**:
- Each dimension calculates 0-100 score from its metrics
- Metrics within dimension use equal weights unless specified
- Rounding: Round to nearest integer for final score
- Validation: Ensure weights sum to 1.0 ± 0.01 (floating point tolerance)

## Best Practices Applied

1. **Python 3.11+ Features**: Use `match/case` for state machines, `Self` type hints
2. **Type Safety**: Full type hints, Pydantic models for data validation
3. **Error Handling**: Custom exceptions, structured error responses
4. **Logging**: Structured logging with context (request_id, nwb_file_path)
5. **Testing**: pytest with fixtures, parametrize for multiple scenarios
6. **Documentation**: Docstrings following NumPy style for scientific users
7. **Configuration**: Environment variables with pydantic-settings, sensible defaults

## Dependencies List

**Core**:
- Python 3.11+
- nwb-inspector (external CLI)
- pydantic (data validation)
- asyncio (built-in, parallel execution)

**Reporting**:
- jinja2 (templates)
- markdown (Markdown parsing if needed)
- weasyprint (PDF generation)

**MCP**:
- mcp (official SDK)

**Testing**:
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock

**Development**:
- ruff (linting)
- black (formatting)
- mypy (type checking)

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| nwb-inspector unavailable/breaks | Medium | High | Circuit breaker, fallback validation |
| Large NWB files timeout | Medium | Medium | Configurable timeout (default 60s), async streaming if needed |
| Concurrent request overload | Low | Medium | Semaphore limit (5 concurrent), queue remaining requests |
| PDF generation memory usage | Low | Medium | Stream large reports, garbage collection between reports |
| MCP protocol changes | Low | High | Pin MCP SDK version, monitor SDK releases |

