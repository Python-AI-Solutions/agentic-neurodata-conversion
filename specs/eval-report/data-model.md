# Data Model: NWB Evaluation and Reporting System

## Core Entities

### ValidationResult

Represents the outcome of NWB file validation from either nwb-inspector or
fallback validator.

**Fields**:

- `nwb_file_path`: str - Absolute path to the NWB file being validated
- `validator_source`: Enum[nwb_inspector, fallback] - Which validator produced
  this result
- `severity_level`: Enum[error, warning, info] - Highest severity level found
- `issues`: List[ValidationIssue] - All validation issues discovered
- `timestamp`: datetime - When validation was performed
- `execution_time`: float - Validation duration in seconds

**Relationships**:

- Used as input to QualityAssessment
- Referenced in EvaluationAuditLog

**Validation Rules**:

- `nwb_file_path` must be non-empty and point to existing file
- `timestamp` must be valid datetime
- `execution_time` must be >= 0
- If `validator_source == fallback`, must include note in issues

**State**: Immutable after creation

---

### ValidationIssue

Individual validation problem found in NWB file.

**Fields**:

- `message`: str - Human-readable description of the issue
- `file_location`: str - Path within NWB file where issue occurs (e.g.,
  "/acquisition/timeseries")
- `remediation`: str - Actionable guidance for fixing the issue
- `severity`: Enum[error, warning, info] - Issue severity

**Validation Rules**:

- `message` must be non-empty
- `remediation` must provide specific actionable steps

---

### QualityDimension

One dimension of quality assessment (technical, scientific, or usability).

**Fields**:

- `dimension_name`: Enum[technical, scientific, usability] - Which quality
  dimension
- `score`: int (0-100) - Aggregated score for this dimension
- `metrics`: Dict[str, MetricResult] - Individual metric scores
- `findings`: List[Finding] - Issues and recommendations

**Relationships**:

- Three instances per QualityAssessment (one per dimension)

**Validation Rules**:

- `score` must be in range [0, 100]
- `metrics` must be non-empty
- `score` calculated as weighted average of metric scores

**Calculation**:

```python
score = round(sum(metric.score * weight for metric, weight in metrics.items()))
# Default: equal weights for all metrics in dimension
```

---

### MetricResult

Result of evaluating a specific quality metric.

**Fields**:

- `metric_name`: str - Name of the metric (e.g., "schema_compliance",
  "metadata_completeness")
- `score`: int (0-100) - Score for this specific metric
- `details`: str - Explanation of the score and what was evaluated

**Validation Rules**:

- `score` must be in range [0, 100]
- `metric_name` must match registered metric for the dimension
- `details` must explain scoring rationale

---

### Finding

Quality issue or recommendation from an evaluator.

**Fields**:

- `severity`: Enum[critical, major, minor] - Impact level
- `description`: str - What quality issue was found
- `remediation`: str - How to improve this aspect
- `metric_name`: str - Which metric generated this finding

**Validation Rules**:

- Critical severity: Score impact >= 20 points
- Major severity: Score impact 10-19 points
- Minor severity: Score impact < 10 points
- `remediation` must be actionable and specific

---

### QualityAssessment

Complete multi-dimensional quality evaluation of an NWB file.

**Fields**:

- `validation_result`: ValidationResult - Input validation data
- `technical_quality`: QualityDimension - Technical dimension assessment
- `scientific_quality`: QualityDimension - Scientific dimension assessment
- `usability_quality`: QualityDimension - Usability dimension assessment
- `overall_score`: int (0-100) - Weighted average of dimension scores
- `dimension_weights`: Dict[str, float] - Weights used for overall score
  (default: {technical: 0.33, scientific: 0.33, usability: 0.34})
- `timestamp`: datetime - When assessment was performed

**Relationships**:

- References one ValidationResult
- Contains three QualityDimension instances
- Input to EvaluationReport generation
- Referenced in EvaluationAuditLog

**Validation Rules**:

- `dimension_weights` must sum to 1.0 (±0.01 tolerance)
- `overall_score` must equal weighted average of dimension scores (rounded)
- All three quality dimensions must be present

**Calculation**:

```python
overall_score = round(
    technical_quality.score * dimension_weights['technical'] +
    scientific_quality.score * dimension_weights['scientific'] +
    usability_quality.score * dimension_weights['usability']
)
```

---

### EvaluatorConfiguration

Settings controlling evaluation execution.

**Fields**:

- `enabled_evaluators`: List[str] - Which evaluators to run (default: all)
- `nwb_inspector_timeout`: int - Seconds before timeout (default: 60)
- `circuit_breaker_threshold`: int - Consecutive failures before fallback
  (default: 3)
- `dimension_weights`: Dict[str, float] - Weights for overall score (default:
  equal)
- `parallel_execution`: bool - Run evaluators in parallel (default: True)
- `max_concurrent_requests`: int - MCP concurrency limit (default: 5)

**Validation Rules**:

- `nwb_inspector_timeout` > 0
- `circuit_breaker_threshold` > 0
- `dimension_weights` sum to 1.0 if provided
- `max_concurrent_requests` > 0
- `enabled_evaluators` must be valid evaluator names

**Defaults**:

```python
EvaluatorConfiguration(
    enabled_evaluators=['technical', 'scientific', 'usability'],
    nwb_inspector_timeout=60,
    circuit_breaker_threshold=3,
    dimension_weights={'technical': 0.33, 'scientific': 0.33, 'usability': 0.34},
    parallel_execution=True,
    max_concurrent_requests=5
)
```

---

### EvaluationReport

Generated output for stakeholders in a specific format.

**Fields**:

- `quality_assessment`: QualityAssessment - Source assessment data
- `format`: Enum[markdown, html, pdf, json] - Report format
- `content`: Union[str, bytes] - Report content (str for text formats, bytes for
  PDF)
- `generated_at`: datetime - Report generation timestamp
- `executive_summary`: str - High-level summary for non-technical audiences
- `detailed_findings`: List[str] - All findings across dimensions

**Relationships**:

- References one QualityAssessment
- Multiple reports can be generated from same assessment

**Validation Rules**:

- `format == pdf` → `content` must be bytes
- `format in [markdown, html, json]` → `content` must be str
- `executive_summary` must be <= 500 words
- `generated_at` >= `quality_assessment.timestamp`

**Format-Specific Content**:

- **Markdown**: Plain text with tables, bullet lists
- **HTML**: Embedded Chart.js visualizations, responsive layout, offline-capable
- **PDF**: HTML converted via WeasyPrint, print-optimized CSS
- **JSON**: Structured data with all fields, machine-readable

---

### MCPEvaluationRequest

Incoming evaluation request via MCP protocol.

**Fields**:

- `request_id`: UUID - Unique request identifier
- `nwb_file_path`: str - Path to NWB file to evaluate
- `evaluator_config`: EvaluatorConfiguration - Evaluation settings (optional,
  uses defaults)
- `output_formats`: List[str] - Desired report formats (default: ['json'])
- `timestamp`: datetime - Request receipt time

**Relationships**:

- Creates one QualityAssessment
- Generates multiple EvaluationReports
- Creates one EvaluationAuditLog

**Validation Rules**:

- `request_id` must be unique
- `nwb_file_path` must point to valid NWB file
- `output_formats` must contain at least one valid format
- `evaluator_config` must pass EvaluatorConfiguration validation

**MCP Tool Schema**:

```json
{
  "name": "evaluate_nwb",
  "description": "Perform comprehensive NWB file quality evaluation",
  "inputSchema": {
    "type": "object",
    "properties": {
      "nwb_file_path": { "type": "string" },
      "output_formats": {
        "type": "array",
        "items": { "enum": ["markdown", "html", "pdf", "json"] }
      },
      "config": { "type": "object", "optional": true }
    },
    "required": ["nwb_file_path"]
  }
}
```

---

### EvaluationAuditLog

Traceability record for evaluation execution.

**Fields**:

- `request_id`: UUID - Links to MCPEvaluationRequest
- `request_timestamp`: datetime - When request was received
- `evaluators_executed`: List[str] - Which evaluators ran
- `overall_score`: int (0-100) - Final quality score
- `execution_duration`: float - Total execution time in seconds
- `errors`: List[str] - Any errors encountered
- `source`: Enum[mcp, direct] - Request source
- `retention_until`: datetime - Auto-deletion date (request_timestamp + 7 days)

**Relationships**:

- References MCPEvaluationRequest via `request_id`

**Validation Rules**:

- `execution_duration` >= 0
- `retention_until` == `request_timestamp` + 7 days
- `overall_score` in [0, 100]

**State Transitions**:

1. **created**: Log entry initialized
2. **executing**: Evaluation in progress
3. **completed**: Evaluation finished successfully
4. **failed**: Evaluation encountered fatal error
5. **archived**: After 7 days, log is deleted

**Retention Policy**:

- Automatically delete logs where `datetime.now() > retention_until`
- Retention enforced by background task (runs daily)

---

## Entity Relationship Diagram

```
MCPEvaluationRequest
    ├─> EvaluatorConfiguration (optional)
    ├─> QualityAssessment
    │     ├─> ValidationResult
    │     │     └─> ValidationIssue (many)
    │     ├─> QualityDimension (technical)
    │     │     ├─> MetricResult (many)
    │     │     └─> Finding (many)
    │     ├─> QualityDimension (scientific)
    │     │     ├─> MetricResult (many)
    │     │     └─> Finding (many)
    │     └─> QualityDimension (usability)
    │           ├─> MetricResult (many)
    │           └─> Finding (many)
    ├─> EvaluationReport (many)
    └─> EvaluationAuditLog

CircuitBreaker (not persisted, runtime state)
    └─> State: CLOSED | OPEN | HALF_OPEN
```

## Implementation Notes

**Pydantic Models**:

- All entities implemented as Pydantic v2 models
- Validation enforced automatically on instantiation
- JSON serialization/deserialization built-in
- Type hints for IDE support

**Enums**:

```python
from enum import Enum

class ValidatorSource(str, Enum):
    NWB_INSPECTOR = "nwb_inspector"
    FALLBACK = "fallback"

class SeverityLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class DimensionName(str, Enum):
    TECHNICAL = "technical"
    SCIENTIFIC = "scientific"
    USABILITY = "usability"

class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"

class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"

class RequestSource(str, Enum):
    MCP = "mcp"
    DIRECT = "direct"
```
