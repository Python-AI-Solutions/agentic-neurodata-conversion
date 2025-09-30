# NWB Knowledge Graph System Requirements

## Overview

A production-ready Python application that performs deep analysis of Neurodata Without Borders (NWB) files, generates evaluation reports, converts to LinkML format using the official NWB LinkML schema, and constructs ontology-based knowledge graphs with interactive visualization.

## Functional Requirements

### FR1: NWB File Processing

- **FR1.1**: Accept NWB 2.x files (HDF5-based) via CLI argument or interactive selection
- **FR1.2**: Validate file integrity before processing
- **FR1.3**: Handle large files efficiently with streaming/chunked reading
- **FR1.4**: Provide clear error messages for invalid or corrupted files

### FR2: Evaluation Report Generation (Primary Step)

- **FR2.1**: Integrate official `nwbinspector` for comprehensive validation checks
- **FR2.2**: Run validation to identify best practices compliance, schema validation, data integrity
- **FR2.3**: Categorize issues by severity (critical, warning, info)
- **FR2.4**: Generate executive summary with file statistics and health score
- **FR2.5**: Include detailed validation results organized by category
- **FR2.6**: Calculate quality metrics (completeness scores, schema compliance)
- **FR2.7**: Generate actionable recommendations
- **FR2.8**: Output initial evaluation in JSON, HTML, and plain text formats

### FR3: Deep File Inspection (Secondary Step)

- **FR3.1**: Recursively traverse entire HDF5 hierarchical structure
- **FR3.2**: Extract all metadata (root-level, groups, subgroups, datasets, attributes)
- **FR3.3**: Capture links, references, data types, shapes, and compression info
- **FR3.4**: Create visual tree representation of HDF5 hierarchy
- **FR3.5**: Perform complete metadata analysis
- **FR3.6**: Provide comprehensive data inventory with dimensions and types
- **FR3.7**: Augment evaluation report with deep inspection results
- **FR3.8**: Update reports with technical details (file size, compression ratios, internal links)

### FR4: LinkML Schema Conversion

- **FR4.1**: Load and use official NWB LinkML schema (not custom schemas)
- **FR4.2**: Parse schema to understand classes, hierarchies, slots, and constraints
- **FR4.3**: Validate input NWB file against schema structure
- **FR4.4**: Map NWB data to LinkML instances following official schema
- **FR4.5**: Preserve all references and relationships as defined in schema
- **FR4.6**: Handle inheritance (e.g., ElectricalSeries → TimeSeries)
- **FR4.7**: Map complex data types (arrays, references, compound types, units)
- **FR4.8**: Output LinkML instances in JSON-LD and YAML formats (raw data mapped to schema, no ontology or inferred relationships)
- **FR4.9**: Validate output against official NWB LinkML schema
- **FR4.10**: Document and handle custom extensions not in official schema

### FR5: RDF/TTL Generation

- **FR5.1**: Generate TTL from LinkML representation (not directly from NWB)
- **FR5.2**: Use LinkML's built-in RDF generation capabilities
- **FR5.3**: Include ontology definitions from NWB LinkML schema
- **FR5.4**: Include instance data from specific NWB file
- **FR5.5**: Define proper namespaces (nwb, linkml, schema, dcterms, rdfs, owl, xsd)
- **FR5.6**: Validate generated TTL against RDF/OWL specifications
- **FR5.7**: Ensure all references resolve correctly
- **FR5.8**: Verify SPARQL query capability
- **FR5.9**: Use persistent, resolvable URIs for NWB entities (format: `http://purl.org/nwb/{version}/{type}/{id}`)
- **FR5.10**: Document namespace conventions in output files

### FR6: Knowledge Graph Construction

- **FR6.1**: Build graph from TTL file (not directly from NWB)
- **FR6.2**: Parse TTL using rdflib to extract RDF triples
- **FR6.3**: Create nodes from RDF resources with all properties
- **FR6.4**: Create edges from RDF object properties
- **FR6.5**: Include ontology class hierarchy in graph structure
- **FR6.6**: Apply optional OWL reasoning (configurable):
  - **FR6.6a**: Use rdflib RDFS reasoner for lightweight RDFS inference (default)
  - **FR6.6b**: Optional: owlrl library for OWL 2 RL reasoning (configurable, disabled by default)
  - **FR6.6c**: Document performance impact and recommend disabling for files >500MB
- **FR6.7**: Compute graph analytics (centrality, communities, statistics)
- **FR6.8**: Ensure completeness (no information loss from LinkML → Graph)
- **FR6.9**: Maintain semantic fidelity with NWB LinkML schema
- **FR6.10**: Organize nodes by type and preserve temporal/spatial hierarchies

### FR7: Knowledge Graph Outputs

- **FR7.1**: Generate complete TTL file (ontology + instance data + inferred relationships)
- **FR7.2**: Export complete knowledge graph in JSON-LD format with proper @context:
  - **FR7.2a**: Define JSON-LD @context with all namespace mappings (nwb, linkml, schema, dcterms, rdfs, owl, xsd)
  - **FR7.2b**: Ensure JSON-LD is valid and parseable by RDF tools (rdflib, JSON-LD playground)
  - **FR7.2c**: Include all triples from TTL (ontology + instance data + inferred relationships)
- **FR7.3**: Export graph metadata JSON with statistics and structure summary (not full graph data)
- **FR7.4**: Create interactive HTML visualization (single self-contained file)

### FR8: Interactive HTML Visualization

- **FR8.1**: Create single self-contained HTML file working offline
- **FR8.2**: Use only vanilla JavaScript (ES6+), no external libraries
- **FR8.3**: Parse knowledge_graph.jsonld and convert to visualization-friendly JSON format:
  - **FR8.3a**: Extract nodes array from RDF resources with properties
  - **FR8.3b**: Extract edges array from RDF object properties with relationship details
  - **FR8.3c**: Add visual properties (colors, sizes, positions) for rendering
  - **FR8.3d**: Embed complete visualization JSON in HTML `<script>` tag
- **FR8.4**: Implement interactive rendering with pan, zoom, drag nodes
- **FR8.5**: Style nodes by NWB class type (color, size, shape, border)
- **FR8.6**: Style edges by relationship type (color, line style, arrows, thickness)
- **FR8.7**: Display rich tooltips showing all LinkML properties for nodes
- **FR8.8**: Display edge tooltips with relationship details and properties
- **FR8.9**: Support tooltip pinning and scrolling for long property lists
- **FR8.10**: Implement search and filter by ID, label, type, property values
- **FR8.11**: Provide multiple layout options (force-directed, hierarchical, circular, grid)
- **FR8.12**: Include collapsible control panel with legend, statistics, settings
- **FR8.13**: Support node selection and neighbor highlighting
- **FR8.14**: Optimize performance for large graphs (LOD rendering, viewport culling)
- **FR8.15**: Ensure responsive design for desktop and tablet
- **FR8.16**: Support data export (PNG, JSON)
- **FR8.17**: Implement accessibility features (keyboard nav, ARIA labels)

### FR9: Command-Line Interface

- **FR9.1**: Accept NWB file path as primary argument
- **FR9.2**: Support options for output directory, schema path, formats
- **FR9.3**: Allow skipping specific processing steps
- **FR9.4**: Support configuration via JSON/YAML file
- **FR9.5**: Provide comprehensive help and usage information

### FR10: Configuration Management

- **FR10.1**: Support optional JSON/YAML configuration files
- **FR10.2**: Allow specification of LinkML schema source/version
- **FR10.3**: Enable custom namespace definitions
- **FR10.4**: Configure node coloring rules by NWB class
- **FR10.5**: Set graph layout and visualization parameters
- **FR10.6**: Define reasoning rules and output preferences

## Non-Functional Requirements

### NFR1: Performance

- **NFR1.1**: Handle GB-scale files efficiently
- **NFR1.2**: Complete 1GB file processing in under 15 minutes
- **NFR1.3**: Use generators and iterators for memory efficiency
- **NFR1.4**: Provide progress indicators for long operations
- **NFR1.5**: Cache intermediate results where beneficial
- **NFR1.6**: Optimize visualization for thousands of graph nodes
- **NFR1.7**: Use parallel processing where beneficial

### NFR2: Robustness

- **NFR2.1**: Validate at each processing stage
- **NFR2.2**: Handle missing/malformed data gracefully
- **NFR2.3**: Provide informative error messages
- **NFR2.4**: Implement comprehensive logging (DEBUG, INFO, WARNING, ERROR)
- **NFR2.5**: Continue processing on non-critical issues
- **NFR2.6**: Generate partial outputs if processing fails
- **NFR2.7**: Include diagnostics in outputs
- **NFR2.8**: Define error severity levels and handling strategy:
  - **CRITICAL**: Stop processing immediately (file corruption, schema load failure, invalid file format)
  - **ERROR**: Skip current component, continue processing (invalid extension, missing optional field, conversion failure)
  - **WARNING**: Note in report, continue processing (deprecated fields, best practice violations, missing metadata)
  - **INFO**: Log informational messages (processing progress, successful operations)

### NFR3: Code Quality

- **NFR3.1**: Use modular, object-oriented design
- **NFR3.2**: Implement proper error handling throughout
- **NFR3.3**: Include comprehensive docstrings for all modules
- **NFR3.4**: Use type hints throughout codebase
- **NFR3.5**: Achieve code coverage ≥80%

### NFR4: Standards Compliance

- **NFR4.1**: Use official NWB LinkML schema (mandatory)
- **NFR4.2**: Validate LinkML outputs against official schema
- **NFR4.3**: Validate TTL with RDF validators and triple stores
- **NFR4.4**: Ensure TTL loadable in semantic web tools
- **NFR4.5**: Maintain semantic fidelity: NWB → LinkML → TTL → Graph

### NFR5: Usability

- **NFR5.1**: HTML visualization works offline with zero external dependencies
- **NFR5.2**: Test HTML in major browsers (Chrome, Firefox, Safari, Edge)
- **NFR5.3**: Provide clear progress feedback during processing
- **NFR5.4**: Generate human-readable reports alongside machine-readable formats

## Technical Requirements

### TR1: Technology Stack

- **TR1.1**: Python 3.8+ as primary language
- **TR1.2**: Required libraries:
  - `pynwb` - NWB file reading
  - `h5py` - Low-level HDF5 access
  - `nwbinspector` - Validation
  - `linkml-runtime` - LinkML schema handling and validation
  - `linkml-model` - LinkML to RDF conversion
  - `rdflib` - RDF/TTL parsing and generation
  - `networkx` - Graph algorithms
  - `jinja2` - HTML templating
  - `pyyaml`, `jsonschema` - Data handling
  - `owlrl` - Optional OWL 2 RL reasoning (configurable)
  - Standard library: `argparse`, `logging`, `pathlib`, `json`, `datetime`
- **TR1.3**: TTL to JSON-LD conversion method:
  - Use `rdflib.Graph.serialize(format='json-ld')` for TTL → JSON-LD conversion
  - Ensure proper JSON-LD context is included in output
  - Validate output with rdflib and JSON-LD processors

### TR2: Module Architecture

- **TR2.1**: `nwb_loader.py` - Load and validate NWB files
- **TR2.2**: `inspector_runner.py` - Run NWB Inspector
- **TR2.3**: `hierarchical_parser.py` - Deep HDF5 traversal
- **TR2.4**: `linkml_converter.py` - Map NWB to LinkML using official schema
- **TR2.5**: `linkml_schema_loader.py` - Load and manage official NWB LinkML schema
- **TR2.6**: `ttl_generator.py` - Generate TTL from LinkML instances
- **TR2.7**: `graph_constructor.py` - Build graph from TTL/LinkML
- **TR2.8**: `html_generator.py` - Generate self-contained HTML visualization
- **TR2.9**: `visualization_engine.py` - Embed graph layouts
- **TR2.10**: `report_generator.py` - Create evaluation reports
- **TR2.11**: `main.py` - CLI orchestration

### TR3: Data Flow Pipeline

```
NWB File (HDF5)
  ↓ [NWB Loader - Basic Validation]
  ↓ Run NWB Inspector
  ↓ [Evaluation Report Generation - Initial]
  ↓ Deep Hierarchical Parse
  ↓ [Evaluation Report - Augmented with Deep Inspection]
  ↓ Load Official NWB LinkML Schema
  ↓ Map NWB Data → LinkML Instances
  ↓ Validate against LinkML Schema
  ↓ [LinkML Outputs: JSON-LD, YAML]
  ↓ Convert LinkML → RDF/TTL
  ↓ [TTL File Output]
  ↓ Convert TTL → JSON-LD (with @context)
  ↓ [JSON-LD File Output]
  ↓ Parse TTL → Graph Structure
  ↓ Enrich Graph (analytics, inference)
  ↓ [HTML Visualization Generation from JSON-LD]
  ↓ Final Outputs
```

### TR4: Output Deliverables

For each NWB file processed:

- **TR4.1**: `{filename}_evaluation_report.json` - Machine-readable evaluation report
- **TR4.2**: `{filename}_evaluation_report.html` - Human-readable evaluation report
- **TR4.3**: `{filename}_evaluation_report.txt` - Plain text evaluation report
- **TR4.4**: `{filename}_linkml_data.jsonld` - LinkML instances only (raw data mapped to schema, no ontology or inferred relationships)
- **TR4.5**: `{filename}_linkml_data.yaml` - LinkML instances in YAML format
- **TR4.6**: `{filename}_knowledge_graph.ttl` - Complete knowledge graph in Turtle format (ontology + instance data + inferred relationships)
- **TR4.7**: `{filename}_knowledge_graph.jsonld` - Complete knowledge graph in JSON-LD format (TTL converted with proper @context, all triples preserved)
- **TR4.8**: `{filename}_knowledge_graph.html` - Interactive visualization with embedded graph data
- **TR4.9**: `{filename}_graph_metadata.json` - Graph statistics and summary only (not full graph)
- **TR4.10**: `{filename}_processing.log` - Processing logs with all severity levels

## Quality Assurance Requirements

### QA1: Testing

- **QA1.1**: Unit tests for each module
- **QA1.2**: Integration tests with diverse NWB files
- **QA1.3**: Test various NWB types (ecephys, ophys, icephys, behavior)
- **QA1.4**: Validate LinkML outputs against official schema
- **QA1.5**: Validate TTL with RDF validators and triple stores
- **QA1.6**: Test HTML in major browsers (Chrome, Firefox, Safari, Edge)
- **QA1.7**: Test visualization with varying graph sizes (10, 100, 1000+ nodes)
- **QA1.8**: Test tooltip rendering on different devices
- **QA1.9**: Verify graph accurately represents LinkML/TTL content
- **QA1.10**: Benchmark performance with large files
- **QA1.11**: Test NWB files with custom extensions not in official schema
- **QA1.12**: Verify graceful degradation when extensions cannot be mapped
- **QA1.13**: Validate JSON-LD output parseable by RDF tools and JSON-LD playground

### QA2: Success Criteria

The system successfully:

- **QA2.1**: Processes any valid NWB 2.x file without errors
- **QA2.2**: Correctly maps NWB data to official LinkML schema
- **QA2.3**: Generates valid LinkML instances that pass schema validation
- **QA2.4**: Produces valid, loadable TTL files from LinkML
- **QA2.5**: Constructs accurate knowledge graphs from TTL/LinkML
- **QA2.6**: Creates self-contained, functional HTML visualizations
- **QA2.7**: Displays comprehensive properties on hover (nodes and edges)
- **QA2.8**: Maintains semantic fidelity: NWB → LinkML → TTL → Graph
- **QA2.9**: Produces accurate evaluation reports
- **QA2.10**: Adapts to NWB extensions while using official schema as base
- **QA2.11**: Completes 1GB file processing in reasonable time (<15 minutes)
- **QA2.12**: HTML works offline without external dependencies
- **QA2.13**: Provides actionable data quality insights

## Documentation Requirements

### DR1: Required Documentation

- **DR1.1**: README.md with installation, usage, architecture, data flow
- **DR1.2**: API documentation for all modules with examples
- **DR1.3**: LinkML integration guide explaining official schema usage
- **DR1.4**: Visualization user guide for interacting with HTML output
- **DR1.5**: Configuration examples with sample config files
- **DR1.6**: Troubleshooting guide for common issues
- **DR1.7**: Performance tuning guide for large files
- **DR1.8**: Contribution guidelines for developers
- **DR1.9**: Example outputs with screenshots and sample files
- **DR1.10**: Configuration file schema documentation (JSON Schema format or comprehensive YAML example with all options)

## Constraints and Assumptions

### Constraints

- **C1**: Must use official NWB LinkML schema (not custom schemas)
- **C2**: TTL generation must be from LinkML representation
- **C3**: Graph construction must be from TTL file
- **C4**: HTML visualization must use only vanilla JavaScript
- **C5**: HTML must be single self-contained file with zero external dependencies
- **C6**: Must support Python 3.8+

### Assumptions

- **A1**: Input files are valid NWB 2.x format (HDF5-based)
- **A2**: Official NWB LinkML schema is accessible (download or reference)
- **A3**: System runs on platforms with Python 3.8+ support
- **A4**: Sufficient disk space for outputs (evaluation reports, LinkML, TTL, HTML)
- **A5**: Modern web browsers support ES6+ JavaScript

## Implementation Phases

1. **Phase 1**: Core Infrastructure (NWB loading, basic validation)
2. **Phase 2**: Evaluation Report Generation (NWB Inspector integration, initial reporting)
3. **Phase 3**: Deep File Inspection (HDF5 hierarchical parsing, augmented reporting)
4. **Phase 4**: LinkML Integration (schema loading, mapping, validation)
5. **Phase 5**: RDF/TTL Generation (LinkML to RDF conversion)
6. **Phase 6**: Knowledge Graph Construction (TTL parsing, graph building)
7. **Phase 7**: Visualization Core (HTML template, JavaScript renderer)
8. **Phase 8**: Enhanced Interactivity (tooltips, hover effects)
9. **Phase 9**: Search, Filter, Controls (UI features)
10. **Phase 10**: Optimization and Testing (performance, validation)
11. **Phase 11**: Documentation and Release (guides, examples, deployment)
