# Research: Data Management and Provenance

**Feature**: Data Management and Provenance
**Date**: 2025-10-07

## Overview

This document contains research findings and technical decisions for implementing DataLad-based data management with comprehensive provenance tracking using RDF/PROV-O ontology.

## Technical Decisions

### 1. RDF Triple Store: Oxigraph

**Decision**: Use Oxigraph (via pyoxigraph + oxrdflib) for provenance storage

**Rationale**:
- **Performance**: ~100x faster SPARQL queries than vanilla rdflib, easily meeting <2 second requirement
- **File Persistence**: RocksDB-based storage provides efficient on-disk persistence
- **Python Integration**: Drop-in replacement for rdflib with familiar API (`Graph(store="Oxigraph")`)
- **Scale**: Tested with 35M triples; handles thousands of provenance records easily
- **Active Development**: Maintained and actively developed

**Alternatives Considered**:
- **rdflib.Graph (in-memory)**: Too slow for production (won't meet <2s query requirement), no persistence
- **rdflib with SQLite**: Mothballed/obsolete, worse performance than in-memory, no longer maintained

**Implementation**:
```python
from rdflib import Graph

# In-memory for testing
graph = Graph(store="Oxigraph")

# File-based for production
graph = Graph(store="Oxigraph")
graph.open("provenance_store")  # Creates RocksDB database
```

**Dependencies to Add**:
```toml
"pyoxigraph>=0.4.0"
"oxrdflib>=0.3.0"
```

---

### 2. HTML Template Engine: Jinja2

**Decision**: Use Jinja2 for HTML report generation

**Rationale**:
- **Industry Standard**: Most widely adopted Python templating engine, well-maintained
- **Security**: Autoescaping enabled by default prevents XSS attacks (critical for AI-generated content)
- **Complex Reports**: Excellent template composition (inheritance, includes, macros) for modular report components
- **Readability**: Django-style syntax distinct from HTML, highly maintainable

**Alternatives Considered**:
- **Mako**: Slightly faster but inline Python makes templates harder to read/maintain; less secure
- **String formatting**: Too basic for complex provenance reports with nested structures

**Implementation**:
```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates/'))
template = env.get_template('provenance_report.html.j2')
html = template.render(session=session_data, charts=chart_html)
```

**Dependencies to Add**:
```toml
"jinja2>=3.1.0"
```

---

### 3. Visualization Library: Plotly

**Decision**: Use Plotly (Python) for interactive visualizations

**Rationale**:
- **Native Python API**: Generate charts entirely from Python without JavaScript coding
- **Standalone HTML**: Export with all dependencies embedded for offline-capable reports
- **Rich Interactivity**: Built-in zoom, pan, hover tooltips perfect for exploring provenance data
- **Scientific Viz**: Designed for data science with pandas integration, excellent for confidence distributions, timelines, quality metrics

**Alternatives Considered**:
- **D3.js**: Requires JavaScript expertise, no Python API, overkill for standard charts
- **Chart.js**: Poor accessibility (canvas-based), limited Python integration, lacks advanced features

**Implementation**:
```python
import plotly.graph_objects as go
import plotly.express as px

# Create chart
fig = px.bar(
    x=list(confidence_counts.keys()),
    y=list(confidence_counts.values()),
    labels={'x': 'Confidence Level', 'y': 'Count'},
    title='Confidence Distribution'
)

# Export as HTML (embedded for offline use)
chart_html = fig.to_html(include_plotlyjs='cdn', full_html=False)
```

**Dependencies to Add**:
```toml
"plotly>=6.0.0"
```

---

### 4. Performance Configuration: YAML with Pydantic

**Decision**: Use YAML for configuration files with Pydantic for validation

**Rationale**:
- **Human-Readable**: YAML is easy for administrators to edit
- **Type Safety**: Pydantic validates configuration structure and types
- **Existing Pattern**: Project already uses Pydantic extensively
- **Flexibility**: Environment variables can override file settings

**Configuration Structure**:
```yaml
performance:
  thresholds:
    conversion_throughput_min: 1  # datasets/hour
    storage_usage_max_percent: 90
    response_time_max_seconds: 30
  alerts:
    enabled: true
    log_level: "WARNING"
```

**Implementation**:
```python
from pydantic import BaseModel
import yaml

class PerformanceThresholds(BaseModel):
    conversion_throughput_min: float = 1.0
    storage_usage_max_percent: int = 90
    response_time_max_seconds: float = 30.0

class PerformanceConfig(BaseModel):
    thresholds: PerformanceThresholds
    alerts: dict
```

---

### 5. Test Dataset Location: Project Subdirectory

**Decision**: Store test datasets in `tests/fixtures/datasets/` within project

**Rationale**:
- **Co-location**: Keeps test data with test code
- **Version Control**: DataLad manages versioning, selective downloading minimizes repo size
- **CI/CD Friendly**: Tests can access datasets via relative paths
- **Consistent Environment**: All developers work with same dataset structure

**Structure**:
```
tests/
├── fixtures/
│   ├── datasets/
│   │   ├── sample_ephys/      # Small test dataset
│   │   ├── sample_imaging/    # Another test dataset
│   │   └── README.md
│   └── sample_provenance/
└── ...
```

---

## DataLad Python API Best Practices

### Key Patterns

1. **Use Dataset Objects**
   ```python
   import datalad.api as dl
   from datalad.api import Dataset

   ds = Dataset('/path/to/dataset')
   if not ds.is_installed():
       ds.create()
   ```

2. **Distinguish `install()` vs `get()`**
   - `install()`: Clone dataset structure (no content)
   - `get()`: Retrieve actual file content from git-annex
   ```python
   ds.install(path='subds', source='url', get_data=False)
   ds.get(path='subds/file.dat')
   ```

3. **Configure Result Handling**
   ```python
   results = ds.save(
       path='.',
       message="Save changes",
       on_failure='continue',  # Get all results
       result_renderer='disabled'  # Suppress CLI output
   )
   ```

4. **Selective Annexing via .gitattributes**
   ```gitattributes
   * annex.largefiles=(largerthan=10mb)
   README.md annex.largefiles=nothing
   *.py annex.largefiles=nothing
   *.nii.gz annex.largefiles=anything
   ```

5. **Exception Handling**
   ```python
   from datalad.support.exceptions import CapturedException, IncompleteResultsError

   try:
       results = ds.save(message="...", on_failure='continue')
   except IncompleteResultsError as e:
       for result in e.failed:
           print(f"Failed: {result['path']}")
   ```

### Common Pitfalls to Avoid

1. **File Locking**: Use `ds.unlock(path)` before modifying annexed files
2. **Subdataset Confusion**: Parent doesn't auto-download subdataset content
3. **Error Handling**: Catch `IncompleteResultsError` and check `result['status']`
4. **Jupyter Conflicts**: Use `nest_asyncio` if running in Jupyter notebooks

### Resources
- DataLad Handbook: http://handbook.datalad.org
- Python API Reference: http://docs.datalad.org/en/stable/modref.html
- Git-annex largefiles: https://git-annex.branchable.com/tips/largefiles/

---

## PROV-O Ontology Structure

### Core Classes

1. **prov:Entity** - Things (data, files, metadata)
2. **prov:Activity** - Processes (conversions, validations)
3. **prov:Agent** - Actors (humans, software agents)

### Key Relationships

- **prov:wasGeneratedBy**: Entity → Activity
- **prov:used**: Activity → Entity
- **prov:wasAssociatedWith**: Activity → Agent
- **prov:wasAttributedTo**: Entity → Agent
- **prov:wasDerivedFrom**: Entity → Entity

### Implementation Pattern

```python
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, PROV

g = Graph(store="Oxigraph")
g.bind("prov", PROV)

# Record conversion activity
conversion = URIRef("urn:conversion:001")
g.add((conversion, RDF.type, PROV.Activity))
g.add((conversion, PROV.startedAtTime, Literal("2025-10-07T10:00:00")))

# Record input/output
input_file = URIRef("urn:file:input.dat")
output_file = URIRef("urn:file:output.nwb")
g.add((output_file, PROV.wasGeneratedBy, conversion))
g.add((conversion, PROV.used, input_file))

# Record agent
agent = URIRef("urn:agent:conversion-agent")
g.add((conversion, PROV.wasAssociatedWith, agent))
```

---

## Summary

All technical unknowns resolved. Ready for Phase 1 design artifacts:
- ✅ RDF storage: Oxigraph
- ✅ Template engine: Jinja2
- ✅ Visualization: Plotly
- ✅ Configuration: YAML + Pydantic
- ✅ Test datasets: `tests/fixtures/datasets/`
- ✅ DataLad patterns documented
- ✅ PROV-O structure defined

**Next**: Generate data-model.md, contracts/, and quickstart.md
