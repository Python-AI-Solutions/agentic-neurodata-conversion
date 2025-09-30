# Research: NWB Knowledge Graph System

**Feature**: 001-nwb-knowledge-graph
**Date**: 2025-09-30
**Status**: Complete

## Overview
This document consolidates research findings for technical decisions required to implement the NWB Knowledge Graph System. All unknowns from the Technical Context have been investigated and resolved.

---

## 1. NWB LinkML Schema Integration

### Decision
Use the official NWB LinkML schema from the `nwb-schema-language` repository maintained by NeurodataWithoutBorders.

### Rationale
- **Official Source**: https://github.com/NeurodataWithoutBorders/nwb-schema-language
- **Version Compatibility**: NWB 2.x files are compatible with nwb-schema-language >= 2.5.0
- **LinkML Runtime Support**: Schemas are in YAML format directly loadable by linkml-runtime
- **Comprehensive Coverage**: Includes all core NWB types and extension mechanisms

### Implementation Approach
```python
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView

# Load official schema
schema_view = SchemaView("https://raw.githubusercontent.com/NeurodataWithoutBorders/nwb-schema-language/main/nwb.schema.yaml")

# Validate instances
schema_view.validate_object(instance, target_class="NWBFile")
```

### Alternatives Considered
- **Custom Schema Generation**: Rejected - violates requirement FR-013 (must use official schema)
- **hdmf-common schema**: Rejected - NWB schema is built on hdmf but NWB-specific schema is required
- **Cached Local Schema**: Accepted as optimization - download once, cache locally with version tracking

---

## 2. LinkML to RDF/TTL Conversion

### Decision
Use linkml's built-in RDF generator combined with rdflib for serialization and validation.

### Rationale
- **Native Support**: LinkML has `linkml.generators.rdfgen.RDFGenerator` for OWL/RDF generation
- **Standard Compliance**: Generates valid RDF/OWL with proper ontology axioms
- **rdflib Integration**: rdflib provides TTL serialization with `rdflib.Graph.serialize(format='turtle')`
- **JSON-LD Support**: rdflib also supports JSON-LD with `format='json-ld'` including @context generation

### Implementation Approach
```python
from linkml.generators.rdfgen import RDFGenerator
from rdflib import Graph

# Generate RDF from LinkML schema + instances
rdf_generator = RDFGenerator(schema_path, format='ttl')
ttl_content = rdf_generator.serialize()

# Load into rdflib for validation and JSON-LD conversion
g = Graph()
g.parse(data=ttl_content, format='turtle')

# Generate JSON-LD
jsonld_content = g.serialize(format='json-ld', indent=2, context={
    "nwb": "http://purl.org/nwb#",
    "linkml": "https://w3id.org/linkml/",
    "schema": "http://schema.org/",
    "dcterms": "http://purl.org/dc/terms/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
})
```

### Alternatives Considered
- **Manual RDF Triple Generation**: Rejected - error-prone, doesn't leverage LinkML's semantic understanding
- **SPARQL Construction Queries**: Rejected - unnecessary complexity for one-time generation
- **pyld Library**: Considered for JSON-LD manipulation but rdflib sufficient for our needs

---

## 3. Vanilla JavaScript Graph Visualization

### Decision
Implement force-directed layout using Verlet integration with Canvas API rendering.

### Rationale
- **Canvas vs SVG**: Canvas chosen for 1000+ nodes - better performance for frequent redraws during pan/zoom
- **Force-Directed Algorithm**: D'Andrade-Fruchterman-Reingold (simple, effective, well-documented)
- **No Dependencies**: Algorithm implementable in ~200 lines of vanilla JavaScript
- **Touch Support**: Canvas supports touch events natively (touchstart, touchmove, touchend)

### Implementation Approach
```javascript
// Force-directed layout (simplified)
class ForceDirectedLayout {
    constructor(nodes, edges) {
        this.nodes = nodes;  // {id, x, y, vx, vy, ...}
        this.edges = edges;  // {source, target, ...}
    }

    step(deltaTime) {
        // Apply forces
        this.applyRepulsion();  // nodes repel each other
        this.applyAttraction();  // edges attract connected nodes
        this.applyDamping();     // velocity damping

        // Update positions (Verlet integration)
        this.nodes.forEach(node => {
            node.x += node.vx * deltaTime;
            node.y += node.vy * deltaTime;
        });
    }

    // Render to canvas
    render(ctx) {
        // Clear canvas
        ctx.clear Rect(0, 0, canvas.width, canvas.height);

        // Draw edges
        this.edges.forEach(edge => {
            ctx.beginPath();
            ctx.moveTo(edge.source.x, edge.source.y);
            ctx.lineTo(edge.target.x, edge.target.y);
            ctx.stroke();
        });

        // Draw nodes
        this.nodes.forEach(node => {
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
            ctx.fill();
        });
    }
}
```

### Performance Optimizations
- **Spatial Hashing**: Quadtree for efficient neighbor lookup (O(log n) vs O(n²))
- **Level of Detail**: Render fewer details when zoomed out
- **Viewport Culling**: Only render nodes within visible canvas area
- **RequestAnimationFrame**: Smooth 60fps animation loop

### Alternatives Considered
- **SVG Rendering**: Rejected - DOM manipulation bottleneck for 1000+ nodes
- **WebGL**: Rejected - unnecessary complexity, broader browser compatibility concerns
- **Barnes-Hut N-Body**: Considered for better O(n log n) complexity but Verlet sufficient for target scale

---

## 4. NWB Inspector Integration

### Decision
Use nwbinspector as a Python library (not CLI) with programmatic API access.

### Rationale
- **Programmatic API**: `nwbinspector.inspect_nwbfile()` returns structured results
- **Severity Levels**: Results include `importance` field ("CRITICAL", "BEST_PRACTICE_SUGGESTION", "BEST_PRACTICE_VIOLATION")
- **Comprehensive Checks**: 50+ built-in checks for NWB compliance
- **Customization**: Can add custom checks via `nwbinspector.register_check()` decorator

### Implementation Approach
```python
from nwbinspector import inspect_nwbfile, Importance

# Run inspection
results = inspect_nwbfile(nwbfile_path=path)

# Categorize by severity
critical = [r for r in results if r.importance == Importance.CRITICAL]
warnings = [r for r in results if r.importance == Importance.BEST_PRACTICE_VIOLATION]
info = [r for r in results if r.importance == Importance.BEST_PRACTICE_SUGGESTION]

# Generate report
report = {
    "health_score": calculate_score(critical, warnings, info),
    "critical_issues": len(critical),
    "warnings": len(warnings),
    "suggestions": len(info),
    "details": [{"check": r.check_function_name,
                 "message": r.message,
                 "severity": r.importance.name,
                 "location": r.location} for r in results]
}
```

### Alternatives Considered
- **CLI Wrapper**: Rejected - loses structured data, requires output parsing
- **Manual Validation**: Rejected - reinventing 50+ validation rules is inefficient
- **PyNWB Validation Only**: Insufficient - nwbinspector includes best practice checks beyond schema

---

## 5. HTML Generation Best Practices

### Decision
Use jinja2 templates with JSON data embedded in `<script type="application/json">` tags.

### Rationale
- **Template Separation**: jinja2 allows clean separation of HTML structure from logic
- **Data Embedding**: JSON in script tags is safe, parseable, and efficient
- **Size Management**: GZIP compression recommended for large JSON (browser automatic)
- **Browser Compatibility**: All modern browsers support ES6+ and JSON parsing

### Implementation Approach
```python
from jinja2 import Environment, FileSystemLoader
import json

# Load template
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('visualization.html')

# Embed graph data
html_content = template.render(
    graph_data=json.dumps(graph_json, separators=(',', ':')),  # Minified JSON
    metadata=metadata,
    timestamp=timestamp
)

# Write self-contained HTML
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)
```

### Template Structure
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NWB Knowledge Graph - {{ metadata.filename }}</title>
    <style>
        /* All CSS embedded here */
    </style>
</head>
<body>
    <div id="app">
        <canvas id="graph-canvas"></canvas>
        <div id="controls"><!-- Control panel --></div>
        <div id="tooltip" class="hidden"></div>
    </div>

    <!-- Embedded graph data -->
    <script type="application/json" id="graph-data">
    {{ graph_data | safe }}
    </script>

    <!-- All JavaScript embedded -->
    <script>
        // Parse embedded data
        const graphData = JSON.parse(document.getElementById('graph-data').textContent);

        // Initialize visualization
        const viz = new GraphVisualization(graphData);
        viz.render();
    </script>
</body>
</html>
```

### Alternatives Considered
- **Inline JavaScript Data**: `const data = {...}` - Rejected, escaping issues with quotes
- **Base64 Encoding**: Rejected - increases size by 33%, unnecessary complexity
- **External JSON File**: Rejected - violates self-contained requirement

---

## 6. Additional Technical Decisions

### 6.1 Error Severity Handling

**Decision**: Use Python's logging module with custom handlers for severity levels.

```python
import logging

# Configure severity levels
logging.addLevelName(50, 'CRITICAL')  # Stop processing
logging.addLevelName(40, 'ERROR')     # Skip component
logging.addLevelName(30, 'WARNING')   # Note in report
logging.addLevelName(20, 'INFO')      # Log progress

# Custom handler for processing log
class ProcessingLogHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.CRITICAL:
            raise ProcessingException(record.message)
        elif record.levelno >= logging.ERROR:
            self.errors.append(record)
            # Skip current component but continue
        # ... continue for WARNING/INFO
```

### 6.2 Progress Indicators

**Decision**: Use `tqdm` library for progress bars with custom callbacks.

```python
from tqdm import tqdm

with tqdm(total=100, desc="Processing NWB file") as pbar:
    pbar.update(10)  # Validation complete
    pbar.update(20)  # Deep inspection complete
    # ... etc
```

### 6.3 Configuration Management

**Decision**: Use `pydantic` for configuration validation with YAML/JSON support.

```python
from pydantic import BaseModel, Field
from pathlib import Path

class Config(BaseModel):
    output_dir: Path
    skip_inspector: bool = False
    skip_linkml: bool = False
    skip_kg: bool = False
    max_viz_nodes: int = Field(default=1000, ge=10, le=10000)
    enable_reasoning: bool = False
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")

    @classmethod
    def from_file(cls, path: Path):
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

---

## Summary of Resolved Unknowns

| Area | Decision | Key Technology |
|------|----------|----------------|
| **NWB LinkML Schema** | Official nwb-schema-language repo | linkml-runtime, SchemaView |
| **LinkML → RDF** | linkml.generators.rdfgen + rdflib | RDFGenerator, rdflib.Graph |
| **Visualization** | Canvas + Force-Directed (Verlet) | Vanilla JavaScript, Canvas API |
| **NWB Inspector** | Programmatic API | nwbinspector.inspect_nwbfile() |
| **HTML Generation** | jinja2 + embedded JSON | jinja2, json module |
| **Error Handling** | Python logging with custom levels | logging module |
| **Progress** | tqdm progress bars | tqdm library |
| **Configuration** | pydantic with YAML support | pydantic, PyYAML |

---

## Dependencies Summary

### Core Dependencies
- `pynwb>=2.5.0` - NWB file I/O
- `h5py>=3.0` - HDF5 low-level access
- `nwbinspector>=0.4.0` - Validation
- `linkml-runtime>=1.5.0` - LinkML schema handling
- `linkml>=1.5.0` - LinkML to RDF generation
- `rdflib>=6.0` - RDF/TTL/JSON-LD manipulation
- `networkx>=3.0` - Graph algorithms
- `jinja2>=3.0` - HTML templating
- `pyyaml>=6.0` - YAML configuration
- `pydantic>=2.0` - Configuration validation
- `tqdm>=4.60` - Progress indicators
- `owlrl>=6.0` - Optional OWL reasoning

### Development Dependencies
- `pytest>=7.0` - Testing framework
- `pytest-cov` - Code coverage
- `black` - Code formatting
- `ruff` - Linting
- `mypy` - Type checking

---

**Status**: All research complete. Ready for Phase 1 (Design & Contracts).