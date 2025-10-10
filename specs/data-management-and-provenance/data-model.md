# Data Model: Data Management and Provenance

**Feature**: Data Management and Provenance **Date**: 2025-10-07

## Overview

This document defines the core entities, their attributes, relationships, and
validation rules for the DataLad-based data management and provenance tracking
system.

---

## Entity Definitions

### 1. DataLadDataset

Represents a versioned test dataset managed by DataLad for development and
testing.

**Attributes**:

- `path`: Path (absolute path to dataset root)
- `name`: str (human-readable dataset name)
- `is_installed`: bool (whether dataset is initialized)
- `subdatasets`: List[DataLadDataset] (nested datasets)
- `annexed_files`: List[Path] (files managed by git-annex)
- `git_files`: List[Path] (files in regular git, not annexed)

**Validation Rules**:

- `path` must exist and be a valid directory
- Dataset must have valid git and git-annex configuration
- Annexed files must be > 10MB
- `name` must be unique within project

**State Transitions**:

1. **Uninitialized** → `create()` → **Installed**
2. **Installed** → `install(subdataset)` → **With Subdatasets**
3. **Installed** → `get(file)` → **Content Available**

**Relationships**:

- Contains 0 or more subdatasets (parent-child hierarchy)
- Referenced by TestFixture (many-to-one)

---

### 2. ConversionRepository

DataLad repository created for each conversion to track outputs, scripts, and
history.

**Attributes**:

- `path`: Path (location in `conversions/` directory)
- `conversion_id`: str (unique identifier, format: `conv_YYYYMMDD_HHMMSS_UUID`)
- `created_at`: datetime (repository creation timestamp)
- `commits`: List[ConversionCommit] (version history)
- `tags`: List[str] (version tags for successful conversions)
- `artifacts`: Dict[str, Path] (organized outputs by type)

**Validation Rules**:

- `path` must be under `conversions/` directory
- `conversion_id` must be unique
- Repository must be valid DataLad dataset
- At least one commit required after finalization

**State Transitions**:

1. **Created** → `initialize()` → **Active**
2. **Active** → `save_iteration()` → **Versioned**
3. **Versioned** → `tag_success()` → **Completed**

**Artifact Structure**:

```python
artifacts = {
    'nwb_files': Path('outputs/nwb/'),
    'scripts': Path('scripts/'),
    'validation_reports': Path('reports/validation/'),
    'evaluation_reports': Path('reports/evaluation/'),
    'knowledge_graphs': Path('graphs/'),
    'provenance': Path('provenance/')
}
```

**Relationships**:

- Contains many ProvenanceRecords (one-to-many)
- Contains many ConversionArtifacts (one-to-many)
- Tracked by PerformanceMetrics (one-to-one)

---

### 3. ConversionCommit

Individual version snapshot within a ConversionRepository.

**Attributes**:

- `hash`: str (git commit SHA)
- `message`: str (descriptive commit message)
- `timestamp`: datetime (commit creation time)
- `author`: str (committer name, typically "system")
- `iteration_number`: int (sequential iteration counter)
- `changes`: List[str] (paths of changed files)

**Validation Rules**:

- `message` must be non-empty and descriptive
- `iteration_number` must increment sequentially
- `hash` must be valid git SHA

---

### 4. ProvenanceRecord

Complete provenance tracking for metadata using PROV-O ontology.

**Attributes**:

- `record_id`: str (unique UUID)
- `entity_uri`: URIRef (PROV Entity IRI)
- `activity_uri`: URIRef (PROV Activity IRI)
- `agent_uri`: URIRef (PROV Agent IRI)
- `confidence_level`: ConfidenceLevel (enum)
- `source_type`: SourceType (enum)
- `derivation_method`: str (description of how derived)
- `reasoning_chain`: List[str] (step-by-step reasoning)
- `evidence_sources`: List[EvidenceSource] (supporting evidence)
- `timestamp`: datetime (record creation time)
- `metadata_field`: str (NWB metadata field name)
- `metadata_value`: Any (actual value recorded)

**Validation Rules**:

- All URI references must be valid IRIs
- `confidence_level` must be from defined enum
- `reasoning_chain` must have at least one step
- `evidence_sources` must not be empty for non-placeholder confidence

**RDF Representation**:

```turtle
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix nwb: <http://example.org/nwb#> .

<urn:entity:metadata-001> a prov:Entity ;
    prov:wasGeneratedBy <urn:activity:conversion-001> ;
    prov:wasAttributedTo <urn:agent:conversion-agent> ;
    nwb:confidenceLevel "high_evidence" ;
    nwb:field "session_start_time" ;
    nwb:value "2025-01-15T10:30:00"^^xsd:dateTime .

<urn:activity:conversion-001> a prov:Activity ;
    prov:used <urn:entity:source-file> ;
    prov:wasAssociatedWith <urn:agent:conversion-agent> ;
    prov:startedAtTime "2025-10-07T10:00:00"^^xsd:dateTime .
```

**Relationships**:

- Stored in ConversionRepository (many-to-one)
- Contains multiple EvidenceSources (one-to-many)
- References ConflictResolution if conflicts exist (one-to-one, optional)

---

### 5. ConfidenceLevel (Enum)

Classification of metadata reliability on defined scale.

**Values**:

- `DEFINITIVE`: Explicitly stated in source data with high certainty
- `HIGH_EVIDENCE`: Strong supporting evidence from multiple sources
- `HUMAN_CONFIRMED`: Validated by human expert
- `HUMAN_OVERRIDE`: Human manually set value overriding automated decision
- `MEDIUM_EVIDENCE`: Reasonable evidence but some uncertainty
- `HEURISTIC`: Derived using heuristic rules
- `LOW_EVIDENCE`: Weak evidence, best guess
- `PLACEHOLDER`: Temporary value, needs review
- `UNKNOWN`: No evidence available

**Ordering**: DEFINITIVE > HUMAN_CONFIRMED > HUMAN_OVERRIDE > HIGH_EVIDENCE >
MEDIUM_EVIDENCE > HEURISTIC > LOW_EVIDENCE > PLACEHOLDER > UNKNOWN

**Usage**:

```python
from enum import Enum

class ConfidenceLevel(str, Enum):
    DEFINITIVE = "definitive"
    HIGH_EVIDENCE = "high_evidence"
    HUMAN_CONFIRMED = "human_confirmed"
    HUMAN_OVERRIDE = "human_override"
    MEDIUM_EVIDENCE = "medium_evidence"
    HEURISTIC = "heuristic"
    LOW_EVIDENCE = "low_evidence"
    PLACEHOLDER = "placeholder"
    UNKNOWN = "unknown"
```

---

### 6. EvidenceSource

Origin of metadata information with associated confidence.

**Attributes**:

- `source_id`: str (unique identifier)
- `source_type`: SourceType (enum: FILE, HUMAN_INPUT, HEURISTIC,
  AUTOMATED_ANALYSIS)
- `source_path`: Optional[Path] (file path if applicable)
- `confidence`: float (0.0 to 1.0)
- `content`: str (relevant excerpt or description)
- `timestamp`: datetime (when evidence was collected)

**Validation Rules**:

- `confidence` must be between 0.0 and 1.0
- If `source_type` is FILE, `source_path` must be provided
- `content` must be non-empty

---

### 7. ConflictResolution

Records how contradictory evidence was resolved.

**Attributes**:

- `conflict_id`: str (unique UUID)
- `conflicting_sources`: List[EvidenceSource] (sources that disagree)
- `resolution_method`: ResolutionMethod (enum: HUMAN_DECISION,
  CONFIDENCE_WEIGHTED, MAJORITY_VOTE)
- `chosen_value`: Any (final decision)
- `resolution_timestamp`: datetime (when resolved)
- `resolver_agent`: Optional[str] (human or agent name)
- `justification`: str (explanation of resolution)

**Validation Rules**:

- `conflicting_sources` must have at least 2 sources
- If `resolution_method` is HUMAN_DECISION, `resolver_agent` must be provided
- `justification` must be non-empty

---

### 8. ConversionArtifact

Output file or report from conversion process.

**Attributes**:

- `artifact_id`: str (unique UUID)
- `artifact_type`: ArtifactType (enum: NWB_FILE, VALIDATION_REPORT,
  EVALUATION_REPORT, KNOWLEDGE_GRAPH, CONVERSION_SCRIPT)
- `file_path`: Path (location within ConversionRepository)
- `created_at`: datetime (artifact creation time)
- `file_size`: int (bytes)
- `checksum`: str (SHA256 hash)
- `metadata`: Dict[str, Any] (artifact-specific metadata)

**Validation Rules**:

- `file_path` must exist
- `checksum` must match actual file SHA256
- `file_size` must be > 0
- `artifact_type` must match file extension/format

**Relationships**:

- Belongs to ConversionRepository (many-to-one)
- May be referenced by ProvenanceRecords (many-to-many)

---

### 9. PerformanceMetrics

Monitoring data for conversion operations.

**Attributes**:

- `metric_id`: str (unique UUID)
- `conversion_id`: str (reference to ConversionRepository)
- `throughput`: float (datasets/hour)
- `storage_used_bytes`: int (total storage consumed)
- `response_time_seconds`: float (operation duration)
- `operation_type`: str (e.g., "conversion", "validation", "report_generation")
- `timestamp`: datetime (measurement time)
- `exceeded_thresholds`: List[str] (names of thresholds exceeded)

**Validation Rules**:

- Numeric values must be non-negative
- `timestamp` must be recent (< 1 day old for active monitoring)
- `conversion_id` must reference valid ConversionRepository

**Relationships**:

- Associated with ConversionRepository (many-to-one)
- Triggers PerformanceAlerts if thresholds exceeded (one-to-many)

---

### 10. PerformanceAlert

Alert triggered when metrics exceed configured thresholds.

**Attributes**:

- `alert_id`: str (unique UUID)
- `metric_id`: str (reference to PerformanceMetrics)
- `threshold_name`: str (name of exceeded threshold)
- `threshold_value`: float (configured limit)
- `actual_value`: float (measured value)
- `severity`: Severity (enum: WARNING, ERROR, CRITICAL)
- `triggered_at`: datetime (alert timestamp)
- `acknowledged`: bool (whether admin reviewed)

**Validation Rules**:

- `actual_value` must exceed `threshold_value` to trigger alert
- `severity` determined by percentage over threshold
- `threshold_name` must match configured threshold

---

### 11. ReportConfiguration

Settings for HTML report generation.

**Attributes**:

- `template_name`: str (Jinja2 template to use)
- `include_sections`: List[str] (sections to include in report)
- `visualization_config`: Dict[str, Any] (Plotly settings)
- `output_format`: str (default: "html")
- `embed_assets`: bool (whether to embed JS/CSS)
- `accessibility_features`: bool (ARIA labels, alt text)

**Validation Rules**:

- `template_name` must reference existing template file
- `include_sections` must only contain valid section names
- `output_format` must be "html" (others reserved for future)

---

## Entity Relationships Diagram

```
DataLadDataset
  └─ subdatasets (0..*)
  └─ referenced by TestFixture

ConversionRepository
  ├─ commits (1..*)
  │   └─ ConversionCommit
  ├─ artifacts (0..*)
  │   └─ ConversionArtifact
  ├─ provenance_records (0..*)
  │   └─ ProvenanceRecord
  │       ├─ confidence_level: ConfidenceLevel
  │       ├─ evidence_sources (1..*)
  │       │   └─ EvidenceSource
  │       └─ conflict_resolution (0..1)
  │           └─ ConflictResolution
  └─ metrics (0..*)
      └─ PerformanceMetrics
          └─ alerts (0..*)
              └─ PerformanceAlert

ReportConfiguration
  └─ used by report generation (many-to-one)
```

---

## Enumerations

### SourceType

```python
class SourceType(str, Enum):
    FILE = "file"
    HUMAN_INPUT = "human_input"
    HEURISTIC = "heuristic"
    AUTOMATED_ANALYSIS = "automated_analysis"
```

### ResolutionMethod

```python
class ResolutionMethod(str, Enum):
    HUMAN_DECISION = "human_decision"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    MAJORITY_VOTE = "majority_vote"
```

### ArtifactType

```python
class ArtifactType(str, Enum):
    NWB_FILE = "nwb_file"
    VALIDATION_REPORT = "validation_report"
    EVALUATION_REPORT = "evaluation_report"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    CONVERSION_SCRIPT = "conversion_script"
```

### Severity

```python
class Severity(str, Enum):
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

---

## Implementation Notes

1. **Pydantic Models**: All entities should be implemented as Pydantic BaseModel
   classes for validation
2. **RDF Storage**: ProvenanceRecord entities are stored in Oxigraph RDF store
   in addition to structured representation
3. **Path Handling**: Use `pathlib.Path` for all file paths
4. **UUID Generation**: Use `uuid.uuid4()` for all unique identifiers
5. **Timestamps**: Use `datetime.datetime.utcnow()` with timezone awareness
6. **Validation**: Pydantic validators should enforce all validation rules
   listed above

---

## Next Steps

- Define API contracts in `contracts/` directory
- Create Pydantic model implementations
- Define SPARQL query templates for provenance
- Design HTML report templates
