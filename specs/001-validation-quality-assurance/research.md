# Technology Research: Validation and Quality Assurance System

**Feature Branch**: `001-validation-quality-assurance`
**Created**: 2025-10-06
**Status**: Complete

## Executive Summary

This document presents comprehensive research findings for the Validation and Quality Assurance System technology stack. Six critical technology areas were investigated to inform implementation decisions for a modular, standards-compliant validation system for NWB (Neurodata Without Borders) files.

**Key Outcomes**:
- All required technologies have mature, production-ready implementations
- Strong alignment with project's existing technology stack (Python 3.9-3.13, Pydantic, FastAPI)
- Clear integration paths identified for all components
- No blocking technical risks identified

---

## 1. NWB Inspector Integration

### Research Scope
Investigation of nwbinspector API, best practices validation, NWB schema version compatibility, and FAIR principles implementation.

### Decision: Use nwbinspector 0.4.0+ with Custom Wrapper

**Technology Stack**:
- **Package**: `nwbinspector>=0.4.0` (already in project dependencies)
- **Integration Pattern**: Wrapper class extending base validator framework
- **NWB Schema Support**: NWB 2.x (current stable: NWB 2.4+)
- **Python Compatibility**: Python 3.9-3.13 (aligns with project requirements)

### Rationale

**1. Official NWB Validation Tool**
- Maintained by Neurodata Without Borders community
- Designated companion to PyNWB validator for best practices checking
- Goes beyond schema compliance to check data quality and completeness
- Latest version (0.5.2, August 2024) shows active development

**2. Comprehensive Validation Coverage**
- **Schema Compliance**: Validates against NWB 2.x specifications
- **Best Practices**: 150+ built-in checks for common issues
- **FAIR Principles**: Built-in checks for Findable, Accessible, Interoperable, Reusable criteria
- **Severity Levels**: Categorizes issues as CRITICAL, BEST_PRACTICE_VIOLATION, BEST_PRACTICE_SUGGESTION

**3. Strong API Design**
```python
# Example integration pattern
from nwbinspector import inspect_nwb, Importance

# Programmatic API with configurable filtering
results = inspect_nwb(
    nwbfile_path="data.nwb",
    importance_threshold=Importance.BEST_PRACTICE_SUGGESTION
)

# Results are structured objects with:
# - check_function_name: identifier for the check
# - message: human-readable description
# - severity: importance level
# - location: specific object in file
```

**4. NWB 2.x Schema Support**
- NWB 2.0 released January 2019 (stable)
- NWB 2.4 current version with PyNWB 2.0+ and MatNWB 2.4+
- Backward compatible with NWB 2.x files
- Schema evolution tracked through official NWB development plan

**5. FAIR Principles Implementation**
- NWB designed specifically to enable FAIR data sharing
- Inspector checks metadata completeness for Findability
- Validates standard compliance for Interoperability
- Ensures documentation for Reusability
- Works with DANDI archive for Accessibility

### Alternatives Considered

**Alternative 1: PyNWB Validator Alone**
- **Pros**: Official schema validator, strict compliance checking
- **Cons**: Only checks schema compliance, not best practices or data quality
- **Verdict**: Insufficient - need both schema AND best practice validation

**Alternative 2: Custom Validation from Scratch**
- **Pros**: Full control, tailored to specific needs
- **Cons**: Duplicates 5+ years of community expertise, maintenance burden
- **Verdict**: Rejected - reinventing the wheel, misses community-validated best practices

**Alternative 3: DANDI Validation API**
- **Pros**: Cloud-based, integrated with DANDI archive
- **Cons**: Network dependency, not designed for local validation workflows
- **Verdict**: Rejected - requires network access, less flexible for development workflows

### Implementation Approach

**Integration Pattern**:
```python
# Wrapper extending base validator
class NWBInspectorValidator(BaseValidator):
    """Wraps nwbinspector for NWB best practices validation."""

    def validate(self, nwb_file_path: str) -> ValidationResult:
        from nwbinspector import inspect_nwb

        # Run nwbinspector with configured thresholds
        inspector_results = inspect_nwb(
            nwbfile_path=nwb_file_path,
            importance_threshold=self.config.importance_threshold
        )

        # Transform to our ValidationResult format
        issues = [
            ValidationIssue(
                severity=self._map_severity(result.severity),
                location=result.location,
                message=result.message,
                remediation=self._get_remediation(result.check_function_name)
            )
            for result in inspector_results
        ]

        return ValidationResult(issues=issues, metadata=...)
```

**Best Practices Mapping**:
- Map nwbinspector importance levels to our severity taxonomy
- Maintain remediation guidance database keyed by check_function_name
- Cache inspection results to avoid redundant file I/O
- Support incremental validation (only check modified sections)

### Key Resources

- **Documentation**: https://nwbinspector.readthedocs.io/
- **GitHub**: https://github.com/NeurodataWithoutBorders/nwbinspector
- **Best Practices Guide**: https://nwbinspector.readthedocs.io/en/dev/best_practices/
- **PyPI**: https://pypi.org/project/nwbinspector/
- **NWB Schema Language**: https://schema-language.readthedocs.io/
- **NWB Format Spec 2.9.0**: https://nwb-schema.readthedocs.io/

---

## 2. LinkML Schema Validation

### Research Scope
Investigation of linkml-runtime API for schema loading, Pydantic class generation from LinkML schemas, and controlled vocabulary validation sources.

### Decision: Use linkml-runtime + PydanticGenerator with Hybrid Vocabulary Strategy

**Technology Stack**:
- **Package**: `linkml-runtime>=1.5.0` (already in project dependencies)
- **Generator**: `linkml.generators.pydanticgen.PydanticGenerator`
- **Validation**: Pydantic v2 models auto-generated from LinkML schemas
- **Type Safety**: Full Python type hints with IDE support

### Rationale

**1. Official LinkML Runtime Library**
- Maintained by LinkML project (stable, active development)
- Lightweight dependency for production use
- Designed specifically for runtime validation and data loading
- Separation of concerns: linkml (authoring) vs linkml-runtime (validation)

**2. Pydantic Generation Strategy**
```python
# Code generation approach (one-time or CI/CD)
from linkml.generators.pydanticgen import PydanticGenerator

generator = PydanticGenerator(schema="nwb_metadata_schema.yaml")
pydantic_code = generator.serialize()

# Generated Pydantic models have:
# - Full type hints (str, int, List, Optional, etc.)
# - Automatic validation via Pydantic v2
# - Enum classes for controlled vocabularies
# - IDE autocomplete support
```

**3. Runtime Validation API**
```python
# Runtime usage (after code generation)
from linkml_runtime.loaders import yaml_loader
from generated_models import NWBMetadata

# Load and validate data
metadata = yaml_loader.load("metadata.yaml", target_class=NWBMetadata)

# Pydantic handles:
# - Type checking
# - Required field validation
# - Format validation
# - Controlled vocabulary (enum) validation
```

**4. Controlled Vocabulary Support**
- **LinkML Enums**: Define allowed terms in schema as enumerations
- **Pydantic Enums**: Auto-generated Python Enum classes
- **Validation**: Automatic rejection of invalid terms
- **Suggestions**: Enhanced with vocabulary completion (see Hybrid Strategy below)

**5. Schema Versioning**
- LinkML schemas stored in version control
- Generated Pydantic code regenerated on schema updates
- Supports multiple schema versions simultaneously
- Compatibility checking via schema version metadata

### Hybrid Vocabulary Strategy

Based on clarification Q1, implement three-tier vocabulary validation:

**Tier 1: Pre-cached Vocabulary Lists (Local)**
- Store common vocabularies as JSON/YAML files
- Fast lookup (<1ms), zero network dependency
- Cover 95% of common terms
- Examples: standard brain regions, common species, electrode types
```python
# vocabularies/brain_regions.yaml
terms:
  - hippocampus
  - cortex
  - amygdala
  # ... ~500 common terms
```

**Tier 2: Ontology Service APIs (Fallback with Caching)**
- BioPortal REST API (https://bioportal.bioontology.org)
- Neuroscience Information Framework (NIF) Standard Ontologies
- TTL cache (24 hours) to minimize API calls
```python
async def suggest_vocabulary_term(invalid_term: str) -> List[str]:
    # Check local cache first (Tier 1)
    if suggestions := local_vocab.fuzzy_search(invalid_term):
        return suggestions[:5]

    # Fallback to BioPortal API (Tier 2)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://data.bioontology.org/search?q={invalid_term}",
            headers={"Authorization": f"apikey token={api_key}"}
        )
        # Cache results for 24 hours
        cache.set(invalid_term, response.json(), ttl=86400)
        return parse_bioportal_suggestions(response.json())
```

**Tier 3: Manual Lookup Tables (Custom/Specialized)**
- Project-specific vocabularies not in standard ontologies
- Lab-specific equipment, custom experimental paradigms
- Maintained in configuration files
```python
# config/custom_vocabularies.yaml
equipment_types:
  - "CustomRig-V3"
  - "LabSpecificProbe-2024"
```

**Fallback Order**: Local → BioPortal API (cached) → Manual → Suggest "unknown"

### Alternatives Considered

**Alternative 1: JSON Schema Directly**
- **Pros**: Simpler, more universal format
- **Cons**: Less expressive than LinkML, no Python class generation
- **Verdict**: Rejected - LinkML provides richer semantics and better Python integration

**Alternative 2: Pydantic Models Written Manually**
- **Pros**: Full control, no code generation step
- **Cons**: Manual maintenance burden, schema/code drift risk
- **Verdict**: Rejected - violates DRY principle, error-prone for complex schemas

**Alternative 3: Configuration-Only Validation (YAML/JSON)**
- **Pros**: No code generation, simpler deployment
- **Cons**: No type safety, runtime-only errors, poor IDE support
- **Verdict**: Rejected - loses Python's static typing benefits

**Alternative 4: Ontology Services Only (No Local Cache)**
- **Pros**: Always up-to-date vocabularies
- **Cons**: Network dependency, latency, API rate limits
- **Verdict**: Rejected - fails offline, too slow for interactive workflows

### Implementation Approach

**Schema Management**:
```
linkml_schemas/
├── nwb_metadata_v1.yaml      # LinkML schema definitions
├── experimental_params_v1.yaml
└── domain_vocabularies_v1.yaml

generated/
├── __init__.py
├── nwb_metadata.py            # Auto-generated Pydantic models
├── experimental_params.py
└── domain_vocabularies.py     # Generated enums
```

**Code Generation Pipeline**:
```bash
# CI/CD or manual regeneration
linkml-generate-pydantic linkml_schemas/nwb_metadata_v1.yaml > generated/nwb_metadata.py
```

**Validation Integration**:
```python
class LinkMLValidator(BaseValidator):
    """Validates metadata against LinkML schemas using Pydantic."""

    def __init__(self, schema_version: str = "v1"):
        # Load appropriate Pydantic models for schema version
        self.models = import_module(f"generated.nwb_metadata")

    def validate_metadata(self, data: dict) -> ValidationResult:
        try:
            # Pydantic validation happens automatically
            validated = self.models.NWBMetadata(**data)
            return ValidationResult(issues=[], metadata=validated)
        except ValidationError as e:
            # Convert Pydantic errors to our ValidationIssue format
            issues = self._parse_pydantic_errors(e)
            return ValidationResult(issues=issues)
```

### Key Resources

- **LinkML Documentation**: https://linkml.io/linkml/
- **Pydantic Generator**: https://linkml.io/linkml/generators/pydantic.html
- **linkml-runtime**: https://linkml.io/linkml/faq/python.html
- **BioPortal API**: https://bioportal.bioontology.org/
- **NIF Ontologies**: Neuroscience Information Framework Standard Ontologies
- **OLS (Ontology Lookup Service)**: https://www.ebi.ac.uk/ols4/

---

## 3. Quality Metrics Design

### Research Scope
Investigation of quality assessment frameworks, weighted scoring algorithms with confidence intervals, and custom metric registration patterns.

### Decision: Multi-Dimensional Framework with Weighted Scoring + Bootstrap Confidence Intervals

**Technology Stack**:
- **Core Metrics**: Accuracy, Completeness, Consistency, Compliance (4 dimensions)
- **Scoring Algorithm**: Weighted linear combination with configurable weights
- **Confidence Intervals**: Bootstrap resampling for uncertainty quantification
- **Registration Pattern**: Decorator-based with BaseQualityMetric inheritance

### Rationale

**1. Industry-Standard Quality Dimensions**

Based on data quality research, four core dimensions emerged as universally applicable:

**Accuracy**: Data correctly represents real-world values
- **Formula**: `(Total Records - Error Count) / Total Records × 100`
- **NWB Application**: Metadata matches experimental reality, units are correct
- **Example**: Electrode impedance values physically plausible (1kΩ - 10MΩ)

**Completeness**: Required and recommended fields are populated
- **Formula**: `(Populated Fields / Total Expected Fields) × 100`
- **NWB Application**: Subject metadata, experiment description, device information
- **Example**: 45/50 metadata fields populated = 90% completeness

**Consistency**: Data is uniform and coherent across the file
- **Formula**: `(Consistent Fields / Cross-Validated Fields) × 100`
- **NWB Application**: Sampling rates match across modalities, timestamps align
- **Example**: ElectricalSeries sampling_rate matches Device.sampling_rate

**Compliance**: Adherence to NWB standards and FAIR principles
- **Formula**: `(Passed Checks / Total Checks) × 100`
- **NWB Application**: Schema compliance, best practices, FAIR criteria
- **Example**: 180/200 nwbinspector checks passed = 90% compliance

**2. Weighted Scoring Algorithm**

```python
# Overall quality score calculation
def calculate_quality_score(metrics: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    Calculate weighted quality score.

    Args:
        metrics: {"accuracy": 0.95, "completeness": 0.80, ...}
        weights: {"accuracy": 0.3, "completeness": 0.25, ...}  # Sum to 1.0

    Returns:
        Weighted score 0.0-1.0
    """
    return sum(metrics[dim] * weights[dim] for dim in metrics)

# Default weights (configurable per use case)
DEFAULT_WEIGHTS = {
    "accuracy": 0.30,      # Most critical - wrong data is dangerous
    "completeness": 0.25,  # Important for reuse
    "consistency": 0.25,   # Critical for analysis
    "compliance": 0.20     # Important but least critical if others high
}
```

**Rationale for Weights**:
- Accuracy highest: Incorrect data undermines all science
- Completeness/Consistency balanced: Both essential for reproducibility
- Compliance lowest: File can be useful even with minor violations
- **Configurable**: Different contexts (publication, internal use) adjust weights

**3. Confidence Interval Calculation via Bootstrap**

```python
from scipy import stats
import numpy as np

def calculate_confidence_interval(
    quality_scores: List[float],
    confidence_level: float = 0.95,
    n_bootstrap: int = 1000
) -> tuple[float, float, float]:
    """
    Calculate quality score with confidence interval using bootstrap.

    Args:
        quality_scores: Individual metric scores (e.g., per-file section)
        confidence_level: CI level (default 95%)
        n_bootstrap: Bootstrap iterations

    Returns:
        (mean_score, lower_bound, upper_bound)
    """
    scores_array = np.array(quality_scores)

    # Bootstrap resampling
    bootstrap_means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(scores_array, size=len(scores_array), replace=True)
        bootstrap_means.append(np.mean(sample))

    # Calculate percentiles for confidence interval
    alpha = 1 - confidence_level
    lower = np.percentile(bootstrap_means, alpha/2 * 100)
    upper = np.percentile(bootstrap_means, (1 - alpha/2) * 100)

    return (np.mean(scores_array), lower, upper)

# Example usage
# quality_score = 0.87, CI [0.83, 0.91] at 95% confidence
```

**Why Bootstrap?**:
- Non-parametric: No assumptions about score distribution
- Robust: Works with small sample sizes
- Interpretable: "95% confident true quality is between 0.83-0.91"
- Industry standard: Used in ML model evaluation

**4. Custom Metric Registration Pattern**

Based on clarification Q2, use decorator-based inheritance approach:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseQualityMetric(ABC):
    """Base class for all quality metrics."""

    name: str
    description: str
    weight: float = 1.0

    @abstractmethod
    def calculate(self, nwb_file: Any) -> float:
        """
        Calculate metric score.

        Returns:
            Score between 0.0 (worst) and 1.0 (best)
        """
        pass

    def get_recommendations(self, score: float) -> List[str]:
        """Optional: Provide improvement recommendations."""
        return []

# Registry for custom metrics
_METRIC_REGISTRY: Dict[str, type[BaseQualityMetric]] = {}

def register_metric(cls: type[BaseQualityMetric]) -> type[BaseQualityMetric]:
    """Decorator to register custom quality metric."""
    _METRIC_REGISTRY[cls.name] = cls
    return cls

# Usage: Define custom metric
@register_metric
class ElectrodeImpedanceQuality(BaseQualityMetric):
    """Checks electrode impedance values for plausibility."""

    name = "electrode_impedance_quality"
    description = "Validates electrode impedance values"
    weight = 1.0

    def calculate(self, nwb_file) -> float:
        electrodes = nwb_file.electrodes.to_dataframe()
        valid_count = electrodes['imp'].between(1e3, 1e7).sum()
        return valid_count / len(electrodes)

    def get_recommendations(self, score: float) -> List[str]:
        if score < 0.8:
            return ["Check electrode impedance measurements",
                    "Expected range: 1kΩ - 10MΩ"]
        return []
```

**Why Decorator Pattern?**:
- Type-safe: IDE autocomplete, mypy validation
- Explicit: Clear inheritance hierarchy
- Discoverable: `_METRIC_REGISTRY.keys()` lists all metrics
- Testable: Easy to mock and unit test
- Documented: Docstrings in code, not external config

### Alternatives Considered

**Alternative 1: Single Aggregate Score (No Dimensions)**
- **Pros**: Simpler to understand, single number
- **Cons**: Hides important details, can't diagnose problems
- **Verdict**: Rejected - need dimensional breakdown for actionable feedback

**Alternative 2: Unweighted Average**
- **Pros**: Simpler calculation, no weight tuning
- **Cons**: Treats all dimensions equally (accuracy should matter more)
- **Verdict**: Rejected - context-dependent importance requires weighting

**Alternative 3: Normal Distribution Confidence Intervals**
- **Pros**: Faster calculation (no resampling)
- **Cons**: Assumes normality (often violated), less robust
- **Verdict**: Rejected - bootstrap more appropriate for arbitrary distributions

**Alternative 4: Configuration-Based Custom Metrics (YAML)**
- **Pros**: No code changes to add metrics
- **Cons**: Limited expressiveness, no type safety, hard to test
- **Verdict**: Rejected - complex metrics need full Python expressiveness

**Alternative 5: Plugin System (Dynamic Loading)**
- **Pros**: Completely decoupled from main codebase
- **Cons**: Security risks, harder to debug, dependency management issues
- **Verdict**: Rejected - decorator registration provides enough flexibility

### Implementation Approach

**Quality Assessment Engine Architecture**:
```
src/validation_qa/quality/
├── __init__.py
├── base_metric.py              # BaseQualityMetric, @register_metric
├── metrics.py                  # Built-in metric implementations
├── completeness.py             # Completeness metrics
├── consistency.py              # Consistency metrics
├── accuracy.py                 # Accuracy metrics
├── compliance.py               # Compliance metrics (wraps nwbinspector)
└── scoring.py                  # Weighted scoring, confidence intervals
```

**Usage Example**:
```python
from validation_qa.quality import QualityAssessmentEngine

engine = QualityAssessmentEngine()

# Use default metrics
result = engine.assess(nwb_file_path)
print(f"Overall Quality: {result.overall_score:.2f} [{result.ci_lower:.2f}, {result.ci_upper:.2f}]")
print(f"Breakdown: {result.dimension_scores}")

# Output:
# Overall Quality: 0.87 [0.83, 0.91]
# Breakdown: {'accuracy': 0.95, 'completeness': 0.80, 'consistency': 0.88, 'compliance': 0.85}
```

### Key Resources

- **Data Quality Dimensions**: https://www.collibra.com/blog/the-6-dimensions-of-data-quality
- **Quality Metrics Guide**: https://atlan.com/data-quality-metrics/
- **Weighted Scoring Models**: https://productschool.com/blog/product-fundamentals/weighted-scoring-model
- **Bootstrap Confidence Intervals**: https://machinelearningmastery.com/confidence-intervals-for-machine-learning/
- **Scikit-learn Metrics**: https://scikit-learn.org/stable/modules/model_evaluation.html

---

## 4. Domain Validation

### Research Scope
Investigation of neuroscience data plausibility bounds, validation standards for electrophysiology/imaging/behavioral data, and hybrid configuration approaches.

### Decision: Hybrid YAML Config + Python API with Domain-Specific Rule Libraries

**Technology Stack**:
- **Simple Rules**: YAML configuration for range validation, unit consistency
- **Complex Rules**: Python classes inheriting from `BaseDomainRule`
- **Domain Coverage**: Electrophysiology, imaging, behavioral (extensible)
- **Knowledge Base**: Curated plausibility bounds from literature and community standards

### Rationale

**1. Neuroscience Data Requires Domain Expertise**

Scientific plausibility validation cannot rely solely on schema compliance:
- **Electrophysiology**: Spike amplitude ranges, sampling rates, impedance values
- **Imaging**: Frame rates, resolution, exposure times, fluorescence intensities
- **Behavioral**: Response times, movement speeds, experimental durations

Schema compliance ensures data is well-formed; domain validation ensures it's scientifically reasonable.

**2. Hybrid Configuration Approach**

Based on clarification Q3, implement two-tier validation:

**Tier 1: YAML Configuration (Simple Plausibility Checks)**

```yaml
# config/domain_rules/electrophysiology.yaml
electrophysiology:
  electrode_impedance:
    min: 1000  # 1 kΩ
    max: 10000000  # 10 MΩ
    units: "ohms"
    recommendation: "Typical range for extracellular electrodes"

  sampling_rate:
    ephys:
      min: 1000  # 1 kHz
      max: 50000  # 50 kHz
      units: "Hz"
      typical: [20000, 30000]  # Most common

  spike_amplitude:
    min: 50  # 50 µV
    max: 500  # 500 µV
    units: "microvolts"
    context: "Extracellular spikes"

  unit_consistency:
    - field: "ElectricalSeries.unit"
      expected: "volts"
    - field: "ElectricalSeries.conversion"
      expected_type: "float"
```

```yaml
# config/domain_rules/imaging.yaml
imaging:
  two_photon:
    frame_rate:
      min: 1  # 1 Hz
      max: 100  # 100 Hz
      units: "Hz"
      typical: [15, 30]

    resolution:
      width: {min: 64, max: 2048}
      height: {min: 64, max: 2048}
      units: "pixels"

  imaging_plane:
    excitation_lambda:
      min: 400  # nm
      max: 1000  # nm
      typical: [920, 1040]  # Common for GCaMP
      units: "nanometers"
```

**Tier 2: Python API (Complex Multi-Field Validation)**

```python
from validation_qa.domain import BaseDomainRule, register_rule

@register_rule
class SamplingRateConsistency(BaseDomainRule):
    """Validates sampling rate consistency across acquisition devices."""

    domain = "electrophysiology"
    name = "sampling_rate_consistency"
    description = "Device sampling rate must match ElectricalSeries rate"

    def validate(self, nwb_file) -> List[ValidationIssue]:
        issues = []

        for series in nwb_file.acquisition.values():
            if isinstance(series, ElectricalSeries):
                series_rate = series.rate
                device_rate = series.electrodes.table.device.sampling_rate

                if abs(series_rate - device_rate) > 0.01:  # 10ms tolerance
                    issues.append(ValidationIssue(
                        severity="WARNING",
                        location=f"{series.name}.rate",
                        message=f"Sampling rate mismatch: series={series_rate}Hz, device={device_rate}Hz",
                        remediation="Ensure device and series sampling rates match"
                    ))

        return issues

@register_rule
class SpikeTimesPlausibility(BaseDomainRule):
    """Validates spike times are within recording duration."""

    domain = "electrophysiology"
    name = "spike_times_plausibility"

    def validate(self, nwb_file) -> List[ValidationIssue]:
        issues = []
        recording_duration = nwb_file.session_start_time + timedelta(seconds=nwb_file.session_duration)

        if hasattr(nwb_file, 'units') and nwb_file.units is not None:
            for unit_id, spike_times in enumerate(nwb_file.units['spike_times']):
                # Check for spikes outside recording window
                if spike_times.min() < 0:
                    issues.append(ValidationIssue(
                        severity="CRITICAL",
                        location=f"units[{unit_id}].spike_times",
                        message=f"Negative spike times detected: {spike_times.min()}",
                        remediation="Spike times must be >= 0"
                    ))

                if spike_times.max() > recording_duration.total_seconds():
                    issues.append(ValidationIssue(
                        severity="CRITICAL",
                        location=f"units[{unit_id}].spike_times",
                        message=f"Spike times exceed recording duration",
                        remediation="Check recording duration metadata"
                    ))

        return issues
```

**Why Hybrid Approach?**:
- **Accessibility**: Scientists can add simple range checks via YAML (no programming)
- **Power**: Developers can implement complex multi-field logic in Python
- **Maintainability**: Simple rules in config, complex logic in tested code
- **Documentation**: YAML serves as living documentation of plausibility bounds

**3. Domain-Specific Knowledge Base**

Curated from:
- **Literature**: Published ranges from neuroscience papers
- **Community Standards**: NWB best practices, DANDI validation requirements
- **Equipment Specs**: Manufacturer specifications for common devices
- **Expert Review**: Neuroscientist input on typical experimental parameters

**Example Knowledge Base Structure**:
```
domain_knowledge/
├── electrophysiology/
│   ├── ranges.yaml              # Plausibility bounds
│   ├── units.yaml               # Expected units
│   ├── equipment_specs.yaml     # Common device specifications
│   └── references.md            # Literature citations
├── imaging/
│   ├── two_photon.yaml
│   ├── widefield.yaml
│   └── references.md
└── behavioral/
    ├── response_times.yaml
    ├── movement_speeds.yaml
    └── references.md
```

**4. Multi-Modal Consistency Checks**

Many experiments combine modalities (e.g., ephys + imaging + behavior):

```python
@register_rule
class CrossModalityTimestampAlignment(BaseDomainRule):
    """Validates timestamp alignment across modalities."""

    domain = "multi_modal"
    name = "timestamp_alignment"

    def validate(self, nwb_file) -> List[ValidationIssue]:
        # Check that ephys, imaging, and behavioral timestamps are aligned
        # within expected tolerances (e.g., <1ms for synchronized systems)
        pass
```

### Alternatives Considered

**Alternative 1: Configuration-Only (No Python API)**
- **Pros**: Simpler, no code changes for new rules
- **Cons**: Cannot express complex multi-field logic
- **Verdict**: Rejected - many domain rules require programmatic logic

**Alternative 2: Python API Only (No Configuration)**
- **Pros**: Maximum flexibility
- **Cons**: High barrier for neuroscientists to contribute rules
- **Verdict**: Rejected - excludes domain experts from rule authoring

**Alternative 3: Rule Engine / DSL (Domain-Specific Language)**
- **Pros**: Powerful expression, declarative
- **Cons**: Learning curve, additional parsing complexity, debugging difficulty
- **Verdict**: Rejected - overkill for this use case, Python provides enough expressiveness

**Alternative 4: Hard-Coded Rules (No Configuration)**
- **Pros**: Simplest implementation
- **Cons**: Inflexible, requires code changes for new domains
- **Verdict**: Rejected - violates Open-Closed Principle

**Alternative 5: Machine Learning-Based Anomaly Detection**
- **Pros**: Learns plausibility from data, adapts over time
- **Cons**: Requires large training datasets, black-box decisions, harder to trust
- **Verdict**: Deferred - potential future enhancement, but explicit rules preferred for MVP

### Implementation Approach

**Domain Validator Architecture**:
```
src/validation_qa/domain/
├── __init__.py
├── base_rule.py                # BaseDomainRule, @register_rule
├── plausibility.py             # YAML config loader and range checker
├── rules/
│   ├── electrophysiology.py    # Ephys domain rules
│   ├── imaging.py              # Imaging domain rules
│   └── behavioral.py           # Behavioral domain rules
└── config/
    ├── electrophysiology.yaml  # Simple plausibility bounds
    ├── imaging.yaml
    └── behavioral.yaml
```

**Usage Example**:
```python
from validation_qa.domain import DomainValidator

validator = DomainValidator(domains=["electrophysiology", "imaging"])
result = validator.validate(nwb_file)

# Output includes both YAML and Python rule violations
for issue in result.issues:
    print(f"{issue.severity}: {issue.message}")
    print(f"  Location: {issue.location}")
    print(f"  Fix: {issue.remediation}")
```

### Key Resources

- **NWB Best Practices**: https://www.nwb.org/best-practices/
- **DANDI Validation**: Data Archive for BRAIN Initiative standards
- **Neuroscience Data Repositories**: DABI, DANDI, OpenNeuro, Brain-CODE
- **Electrophysiology Standards**: EEG/iEEG/MEG community guidelines
- **Imaging Standards**: Fluorescence microscopy community best practices

---

## 5. Report Generation

### Research Scope
Investigation of Jinja2 HTML templating, visualization libraries (Plotly, Chart.js, matplotlib), and JSON schema for structured reports.

### Decision: Jinja2 + Plotly for HTML, JSON Schema for Structured Reports

**Technology Stack**:
- **Templating**: Jinja2 (Python-native, already familiar in project ecosystem)
- **Visualization**: Plotly (interactive HTML), matplotlib (static fallback)
- **Output Formats**: JSON (MVP), HTML (MVP), PDF (post-MVP)
- **Schema**: JSON Schema Draft 2020-12 for report structure

### Rationale

**1. Jinja2 Templating for HTML Reports**

```python
from jinja2 import Environment, FileSystemLoader

# Template structure
# templates/html_report.jinja2
<!DOCTYPE html>
<html>
<head>
    <title>NWB Validation Report - {{ nwb_filename }}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        /* Embedded CSS for styling */
    </style>
</head>
<body>
    <h1>Validation Report</h1>
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>Overall Quality Score: <strong>{{ quality_score | round(2) }}</strong></p>
        <p>Confidence Interval: [{{ ci_lower | round(2) }}, {{ ci_upper | round(2) }}]</p>
    </div>

    <div class="visualizations">
        <h2>Quality Breakdown</h2>
        {{ plotly_chart_html | safe }}  <!-- Embedded Plotly chart -->
    </div>

    <div class="issues">
        <h2>Validation Issues ({{ issues | length }})</h2>
        <table>
            <tr><th>Severity</th><th>Location</th><th>Message</th><th>Remediation</th></tr>
            {% for issue in issues %}
            <tr class="severity-{{ issue.severity | lower }}">
                <td>{{ issue.severity }}</td>
                <td><code>{{ issue.location }}</code></td>
                <td>{{ issue.message }}</td>
                <td>{{ issue.remediation }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
```

**Why Jinja2?**:
- **Familiar**: Standard Python templating engine (Django, Flask use it)
- **Powerful**: Loops, conditionals, filters, macros
- **Safe**: Auto-escaping prevents XSS vulnerabilities
- **Debuggable**: Clear error messages, line number tracking
- **Ecosystem**: Extensions for markdown, date formatting, etc.

**2. Plotly for Interactive Visualizations**

Based on clarification Q4b, implement interactive HTML visualizations:

```python
import plotly.graph_objects as go
import plotly.express as px

def generate_severity_chart(issues: List[ValidationIssue]) -> str:
    """Generate interactive bar chart of issue severities."""
    severity_counts = Counter(issue.severity for issue in issues)

    fig = go.Figure(data=[
        go.Bar(
            x=list(severity_counts.keys()),
            y=list(severity_counts.values()),
            marker_color=['red', 'orange', 'yellow', 'green']
        )
    ])

    fig.update_layout(
        title="Validation Issues by Severity",
        xaxis_title="Severity Level",
        yaxis_title="Count",
        hovermode='x unified'  # Interactive hover
    )

    # Export as HTML div (embeds in Jinja2 template)
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def generate_quality_breakdown(dimension_scores: Dict[str, float]) -> str:
    """Generate interactive pie chart of quality dimensions."""
    fig = go.Figure(data=[
        go.Pie(
            labels=list(dimension_scores.keys()),
            values=list(dimension_scores.values()),
            hole=0.3,  # Donut chart
            hovertemplate='%{label}: %{value:.1%}<extra></extra>'
        )
    ])

    fig.update_layout(title="Quality Dimension Breakdown")
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def generate_trend_chart(historical_scores: List[tuple[datetime, float]]) -> str:
    """Generate line graph of quality score trends over time."""
    dates, scores = zip(*historical_scores)

    fig = go.Figure(data=[
        go.Scatter(
            x=dates,
            y=scores,
            mode='lines+markers',
            name='Quality Score',
            hovertemplate='%{x}: %{y:.2f}<extra></extra>'
        )
    ])

    fig.update_layout(
        title="Quality Score Trend",
        xaxis_title="Date",
        yaxis_title="Quality Score"
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn')
```

**Why Plotly over Matplotlib?**:
- **Interactive**: Hover, zoom, pan, toggle traces
- **HTML-Native**: Generates standalone HTML/JavaScript
- **Modern**: Better aesthetics out-of-the-box
- **Responsive**: Adapts to screen size
- **User-Friendly**: Non-technical users can explore data

**Matplotlib for Static Fallback** (PDF export):
```python
import matplotlib.pyplot as plt

def generate_static_severity_chart(issues: List[ValidationIssue]) -> str:
    """Generate static PNG for PDF reports."""
    severity_counts = Counter(issue.severity for issue in issues)

    plt.figure(figsize=(10, 6))
    plt.bar(severity_counts.keys(), severity_counts.values())
    plt.title("Validation Issues by Severity")
    plt.xlabel("Severity Level")
    plt.ylabel("Count")

    # Save to BytesIO for embedding
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close()

    # Base64 encode for embedding in HTML/PDF
    return base64.b64encode(buf.getvalue()).decode()
```

**3. JSON Schema for Report Structure**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "NWB Validation Report",
  "type": "object",
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "nwb_file_path": {"type": "string"},
        "validation_timestamp": {"type": "string", "format": "date-time"},
        "validator_version": {"type": "string"},
        "schema_version": {"type": "string"}
      },
      "required": ["nwb_file_path", "validation_timestamp"]
    },
    "quality_assessment": {
      "type": "object",
      "properties": {
        "overall_score": {"type": "number", "minimum": 0, "maximum": 1},
        "confidence_interval": {
          "type": "object",
          "properties": {
            "lower": {"type": "number"},
            "upper": {"type": "number"},
            "confidence_level": {"type": "number", "default": 0.95}
          }
        },
        "dimension_scores": {
          "type": "object",
          "properties": {
            "accuracy": {"type": "number", "minimum": 0, "maximum": 1},
            "completeness": {"type": "number", "minimum": 0, "maximum": 1},
            "consistency": {"type": "number", "minimum": 0, "maximum": 1},
            "compliance": {"type": "number", "minimum": 0, "maximum": 1}
          }
        }
      },
      "required": ["overall_score", "dimension_scores"]
    },
    "validation_issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["CRITICAL", "WARNING", "INFO", "BEST_PRACTICE"]
          },
          "location": {"type": "string"},
          "message": {"type": "string"},
          "remediation": {"type": "string"},
          "validator": {"type": "string"}
        },
        "required": ["severity", "location", "message"]
      }
    },
    "recommendations": {
      "type": "array",
      "items": {"type": "string"}
    },
    "trend_analysis": {
      "type": "object",
      "properties": {
        "historical_scores": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "timestamp": {"type": "string", "format": "date-time"},
              "score": {"type": "number"}
            }
          }
        },
        "common_issues": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    }
  },
  "required": ["metadata", "quality_assessment", "validation_issues"]
}
```

**Why JSON Schema?**:
- **Validation**: Ensures report structure correctness
- **Documentation**: Self-documenting API contract
- **Versioning**: Schema evolution tracking
- **Tooling**: Many libraries support JSON Schema validation
- **Interoperability**: JSON is universal exchange format

**4. Report Format Strategy**

Based on clarification Q4a:

**MVP (Phase 1)**:
- **JSON**: Machine-readable, API integration, programmatic processing
- **HTML**: Human-readable, interactive visualizations, shareable links

**Post-MVP (Phase 2)**:
- **PDF**: Static archival format, publication-ready
  - Use WeasyPrint or ReportLab to convert HTML → PDF
  - Matplotlib static charts for PDF embeds

### Visualization Types (Q4b)

Implement these chart types:

1. **Bar Chart**: Issue counts by severity
   - X-axis: CRITICAL, WARNING, INFO, BEST_PRACTICE
   - Y-axis: Count
   - Interactive: Click to filter issue table

2. **Pie/Donut Chart**: Quality dimension breakdown
   - Slices: Accuracy, Completeness, Consistency, Compliance
   - Values: 0-100% scores
   - Interactive: Hover to see exact percentages

3. **Line Graph**: Quality score trends over time
   - X-axis: Validation timestamps
   - Y-axis: Overall quality score
   - Interactive: Zoom to time ranges, hover for details

4. **Table**: Detailed issue listings
   - Columns: Severity, Location, Message, Remediation
   - Interactive: Sortable, filterable, searchable
   - Color-coded by severity

### Alternatives Considered

**Alternative 1: Markdown Reports**
- **Pros**: Simpler, text-based, version-controllable
- **Cons**: No interactive visualizations, limited formatting
- **Verdict**: Rejected - insufficient for rich visualizations

**Alternative 2: Matplotlib Only (No Plotly)**
- **Pros**: Fewer dependencies, simpler
- **Cons**: No interactivity, less user-friendly
- **Verdict**: Rejected - interactivity is valuable for exploration

**Alternative 3: Chart.js**
- **Pros**: Lightweight JavaScript library
- **Cons**: Requires manual HTML/JS templating, less Python-native
- **Verdict**: Rejected - Plotly provides better Python integration

**Alternative 4: Custom React/Vue Web App**
- **Pros**: Maximum control, modern UI
- **Cons**: Separate frontend project, deployment complexity
- **Verdict**: Rejected - overkill for MVP, Jinja2+Plotly sufficient

**Alternative 5: Jupyter Notebook Reports**
- **Pros**: Interactive, code + visualizations, familiar to scientists
- **Cons**: Not suitable for automated workflows, harder to template
- **Verdict**: Rejected - good for exploration, not automated reporting

### Implementation Approach

**Report Generator Architecture**:
```
src/validation_qa/reporting/
├── __init__.py
├── report_generator.py         # Main report generation logic
├── templates/
│   ├── html_report.jinja2      # HTML template
│   └── email_summary.jinja2    # Email notification template
├── visualizations.py           # Plotly/matplotlib chart functions
├── analytics.py                # Trend analysis, pattern detection
├── executive_summary.py        # Summary text generation
└── schemas/
    └── validation_report_v1.json  # JSON Schema definition
```

**Usage Example**:
```python
from validation_qa.reporting import ReportGenerator

generator = ReportGenerator()

# Generate all formats
report_data = {
    "quality_assessment": quality_result,
    "validation_issues": all_issues,
    "metadata": {...}
}

# JSON (machine-readable)
json_report = generator.generate_json(report_data)
with open("report.json", "w") as f:
    json.dump(json_report, f, indent=2)

# HTML (interactive)
html_report = generator.generate_html(report_data)
with open("report.html", "w") as f:
    f.write(html_report)

# Future: PDF
# pdf_report = generator.generate_pdf(report_data)
```

### Key Resources

- **Jinja2 Documentation**: https://jinja.palletsprojects.com/
- **Plotly Python**: https://plotly.com/python/
- **Plotly vs Matplotlib**: Comparison guides
- **JSON Schema**: https://json-schema.org/draft/2020-12/json-schema-validation
- **Python JSON Schema Validator**: https://python-jsonschema.readthedocs.io/
- **Report Generation Guide**: https://www.justintodata.com/generate-reports-with-python/

---

## 6. MCP Integration

### Research Scope
Investigation of Model Context Protocol specification, async validation patterns in Python, and MCP server implementation best practices.

### Decision: MCP Python SDK with FastMCP + Async/Await Validation Pipeline

**Technology Stack**:
- **SDK**: `mcp>=1.0.0` (official Python SDK, already in project dependencies)
- **Framework**: FastMCP for automatic schema generation
- **Async Pattern**: asyncio with AsyncExitStack for resource management
- **Authentication**: OAuth 2.1 resource server (optional, future)
- **Type Safety**: Pydantic v2 models for input/output validation

### Rationale

**1. Official MCP Python SDK**

```python
# MCP Server with FastMCP
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
import mcp.server.stdio

async def main():
    server = Server("nwb-validation-server")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="validate_nwb_file",
                description="Validate an NWB file against standards and best practices",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "validators": {"type": "array", "items": {"type": "string"}},
                        "config_profile": {"type": "string", "default": "default"}
                    },
                    "required": ["file_path"]
                }
            ),
            # ... more tools
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "validate_nwb_file":
            result = await validate_nwb_async(arguments["file_path"])
            return [TextContent(type="text", text=json.dumps(result))]

    # Run server with stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nwb-validation-server",
                server_version="1.0.0"
            )
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Why Official SDK?**:
- **Standards-Compliant**: Implements MCP specification correctly
- **Maintained**: Active development by Anthropic/MCP team
- **Type-Safe**: Full type hints, Pydantic validation
- **Transport-Agnostic**: Supports stdio, HTTP, SSE
- **Well-Documented**: Comprehensive guides and examples

**2. FastMCP for Type-Safe Tools**

```python
from mcp import FastMCP
from pydantic import BaseModel, Field

# Initialize FastMCP server
mcp = FastMCP("NWB Validation Server")

# Define input schema with Pydantic
class ValidateNWBInput(BaseModel):
    file_path: str = Field(description="Path to NWB file")
    validators: list[str] = Field(
        default=["nwb_inspector", "linkml", "quality", "domain"],
        description="Validators to run"
    )
    config_profile: str = Field(default="default", description="Configuration profile")

class ValidationResult(BaseModel):
    overall_score: float
    dimension_scores: dict[str, float]
    issues: list[dict]
    recommendations: list[str]

# Define tool with automatic schema generation
@mcp.tool()
async def validate_nwb_file(input: ValidateNWBInput) -> ValidationResult:
    """
    Validate an NWB file against standards and best practices.

    Returns comprehensive validation results including quality scores,
    issues, and remediation recommendations.
    """
    # Type hints ensure input validation automatically
    result = await orchestrator.validate(
        file_path=input.file_path,
        validators=input.validators,
        config_profile=input.config_profile
    )

    return ValidationResult(**result)

# Automatic features:
# - Input schema generated from ValidateNWBInput
# - Output schema generated from ValidationResult
# - Automatic validation of inputs/outputs
# - Type-safe: mypy can check this code
```

**Why FastMCP?**:
- **DX (Developer Experience)**: Pythonic decorators, familiar patterns
- **Auto-Schema**: Pydantic models → JSON Schema automatically
- **Type Safety**: Full static type checking with mypy
- **Validation**: Automatic input/output validation
- **Documentation**: Docstrings become tool descriptions

**3. Async Validation Patterns**

```python
import asyncio
from typing import List
from contextlib import AsyncExitStack

class AsyncValidationOrchestrator:
    """Orchestrates async validation across multiple validators."""

    async def validate(
        self,
        file_path: str,
        validators: List[str],
        config_profile: str = "default"
    ) -> dict:
        """Run validation asynchronously with proper resource management."""

        async with AsyncExitStack() as stack:
            # Open NWB file asynchronously (if using async I/O)
            nwb_file = await stack.enter_async_context(
                open_nwb_async(file_path)
            )

            # Run validators in parallel
            tasks = []
            for validator_name in validators:
                validator = self._get_validator(validator_name)
                task = asyncio.create_task(
                    validator.validate_async(nwb_file, config_profile)
                )
                tasks.append(task)

            # Wait for all validators to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle errors gracefully
            validated_results = []
            for result in results:
                if isinstance(result, Exception):
                    # Log error but continue with other validators
                    logger.error(f"Validator error: {result}")
                else:
                    validated_results.append(result)

            # Aggregate results
            return self._aggregate_results(validated_results)

    async def validate_batch(
        self,
        file_paths: List[str],
        **kwargs
    ) -> List[dict]:
        """Validate multiple files concurrently."""
        tasks = [
            self.validate(file_path, **kwargs)
            for file_path in file_paths
        ]
        return await asyncio.gather(*tasks)
```

**Async Patterns Used**:
- **AsyncExitStack**: Proper resource cleanup (file handles, connections)
- **asyncio.gather**: Parallel validation execution
- **Error Handling**: `return_exceptions=True` prevents one failure from blocking others
- **Cancellation**: Support for `asyncio.CancelledError` (user cancels validation)
- **Timeouts**: `asyncio.wait_for` for validator timeouts

**4. MCP Tool Definitions**

Define comprehensive tool suite:

```python
@mcp.tool()
async def validate_nwb_file(input: ValidateNWBInput) -> ValidationResult:
    """Primary validation tool."""
    pass

@mcp.tool()
async def assess_quality(file_path: str) -> QualityAssessment:
    """Run quality assessment only (no validation)."""
    pass

@mcp.tool()
async def generate_report(
    validation_result: dict,
    format: str = "html"
) -> ReportOutput:
    """Generate validation report from results."""
    pass

@mcp.tool()
async def analyze_trends(
    file_paths: list[str],
    start_date: str | None = None
) -> TrendAnalysis:
    """Analyze quality trends across multiple validations."""
    pass

@mcp.tool()
async def get_validator_info() -> ValidatorInfo:
    """Get information about available validators and their capabilities."""
    pass

@mcp.tool()
async def update_config(
    profile: str,
    config: dict
) -> ConfigUpdateResult:
    """Update validation configuration at runtime."""
    pass
```

**5. Health Checks and Monitoring**

```python
from mcp.server import Server

@server.list_resources()
async def handle_list_resources():
    """Expose health check endpoints."""
    return [
        {
            "uri": "health://validator/status",
            "name": "Validator Health Status",
            "mimeType": "application/json"
        }
    ]

@server.read_resource()
async def handle_read_resource(uri: str):
    """Provide health check data."""
    if uri == "health://validator/status":
        return {
            "status": "healthy",
            "validators": {
                "nwb_inspector": "operational",
                "linkml": "operational",
                "quality": "operational",
                "domain": "operational"
            },
            "uptime": get_uptime(),
            "total_validations": get_validation_count()
        }
```

**6. Authentication (Future-Proof)**

```python
from mcp.server.auth import OAuth2ResourceServer

# Optional: OAuth 2.1 resource server
auth = OAuth2ResourceServer(
    issuer="https://auth.example.com",
    audience="nwb-validation-api"
)

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict, auth_context: dict):
    # auth_context contains validated token claims
    user_id = auth_context.get("sub")
    # Implement rate limiting, access control, etc.
    pass
```

### Alternatives Considered

**Alternative 1: Custom Protocol (No MCP)**
- **Pros**: Full control, tailored to exact needs
- **Cons**: Reinventing wheel, no ecosystem integration
- **Verdict**: Rejected - MCP provides standardization and Claude integration

**Alternative 2: REST API (FastAPI)**
- **Pros**: Familiar, well-understood, many clients
- **Cons**: Not MCP-compatible, separate from agent workflows
- **Verdict**: Partial - can offer both MCP and REST (FastAPI already in stack)

**Alternative 3: Synchronous Validation (No Async)**
- **Pros**: Simpler code, easier debugging
- **Cons**: Poor performance for large files, blocks on I/O
- **Verdict**: Rejected - async required for responsive MCP server

**Alternative 4: gRPC**
- **Pros**: High performance, streaming support
- **Cons**: More complex, not MCP-native
- **Verdict**: Rejected - MCP uses simpler JSON-RPC protocol

**Alternative 5: Manual JSON-RPC Implementation**
- **Pros**: Lightweight, no SDK dependency
- **Cons**: Error-prone, misses SDK features (retries, error handling)
- **Verdict**: Rejected - official SDK provides substantial value

### Implementation Approach

**MCP Integration Architecture**:
```
src/validation_qa/mcp/
├── __init__.py
├── server.py                   # FastMCP server setup
├── tools.py                    # MCP tool implementations
├── async_validator.py          # Async validation orchestrator
├── health.py                   # Health checks and monitoring
└── schemas.py                  # Pydantic input/output models
```

**Server Entry Point**:
```python
# cli/mcp_server.py
import asyncio
from validation_qa.mcp import create_mcp_server

async def main():
    server = create_mcp_server()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**Deployment**:
```bash
# Stdio mode (for Claude Desktop integration)
python -m validation_qa.mcp.server

# HTTP mode (for web integration, future)
uvicorn validation_qa.mcp.server:app --host 0.0.0.0 --port 8000
```

### Key Resources

- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **MCP Specification**: https://modelcontextprotocol.io/
- **FastMCP Tutorial**: https://www.datacamp.com/tutorial/mcp-model-context-protocol
- **MCP Client Guide**: https://modelcontextprotocol.io/quickstart/client
- **Python Async Programming**: asyncio documentation
- **OAuth 2.1**: https://oauth.net/2.1/

---

## Summary of Decisions

| Area | Technology | Key Rationale |
|------|------------|---------------|
| **NWB Inspector** | nwbinspector 0.4.0+ | Official tool, 150+ checks, FAIR compliance |
| **LinkML** | linkml-runtime + PydanticGenerator | Type-safe validation, auto-generated models |
| **Vocabularies** | Hybrid (Local + BioPortal + Manual) | Balance speed/coverage/offline capability |
| **Quality Metrics** | 4D framework + weighted scoring + bootstrap CI | Industry-standard dimensions, uncertainty quantification |
| **Custom Metrics** | Decorator-based inheritance | Type-safe, testable, discoverable |
| **Domain Rules** | YAML config + Python API | Accessibility for scientists, power for developers |
| **Report Templates** | Jinja2 | Python-native, powerful, safe |
| **Visualizations** | Plotly (interactive) + matplotlib (static) | Modern UX, HTML-native, PDF fallback |
| **Report Formats** | JSON + HTML (MVP), PDF (later) | Machine + human readable |
| **MCP Server** | MCP Python SDK + FastMCP | Official, type-safe, auto-schema generation |
| **Async Pattern** | asyncio + AsyncExitStack | Proper resource management, parallel execution |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| NWB schema breaking changes | Low | Medium | Version pinning, compatibility tests |
| BioPortal API rate limits | Medium | Low | Local cache, fallback tiers |
| Large file memory issues | Medium | High | Streaming validation, lazy loading |
| MCP spec evolution | Medium | Low | SDK abstracts protocol details |
| Plotly bundle size | Low | Low | CDN hosting, lazy loading |
| Complex domain rules bugs | Medium | Medium | Comprehensive tests, scientist review |

---

## Next Steps

1. **Phase 1 (Design)**:
   - Create data models (data-model.md)
   - Define API contracts (contracts/*.yaml)
   - Write contract tests (tests/contract/)
   - Document quickstart (quickstart.md)

2. **Phase 2 (Implementation)**:
   - Core framework: BaseValidator, ValidationResult
   - Module implementations (following research decisions)
   - Integration tests
   - Documentation

3. **Phase 3 (Validation)**:
   - Performance benchmarks
   - Real-world NWB file testing
   - User acceptance testing with neuroscientists
   - Production deployment

---

## References

**Official Documentation**:
- NWB Inspector: https://nwbinspector.readthedocs.io/
- LinkML: https://linkml.io/linkml/
- Plotly: https://plotly.com/python/
- MCP: https://modelcontextprotocol.io/

**Research Papers**:
- "The Neurodata Without Borders ecosystem for neurophysiological data science" (2022)
- "Core principles for the implementation of the neurodata without borders data standard" (2020)

**Community Resources**:
- DANDI Archive: https://dandiarchive.org/
- NWB Working Groups: https://nwb.org/working-groups/
- BioPortal: https://bioportal.bioontology.org/

---

**Document Status**: Complete
**Reviewed By**: Implementation Planning Phase
**Date**: 2025-10-06
