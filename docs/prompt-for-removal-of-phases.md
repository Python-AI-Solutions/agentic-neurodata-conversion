# Knowledge Graph Systems: Unified Product Vision and Migration Guide

## Executive Summary

The knowledge graph systems spec needs to be rewritten as a unified product that
integrates three key insights:

1. **NWB-LinkML Schema-First Architecture**: Use NWB-LinkML as the canonical
   schema source for consistency and interoperability
2. **Proven Data Conversion Patterns**: Build on reliable MVP conversion logic
   for NWB-to-RDF transformation
3. **Rich Semantic Capabilities**: Provide metadata enrichment, provenance
   tracking, and complex querying as core features

## Current State Analysis

### What Works (Keep and Build On)

- **MVP Conversion Logic**: Reliable NWB file parsing and RDF generation
  patterns
- **Basic RDF Infrastructure**: RDFLib-based storage and multiple format export
  (TTL, JSON-LD, N-Triples)
- **Simple Visualization**: PyVis-based graph exploration that users can
  understand
- **MCP Server Foundation**: Basic tool structure for agent integration

### What's Missing (Core Product Gaps)

- **Schema Consistency**: Each NWB file generates different schemas →
  inconsistent IRIs and structure
- **Validation Framework**: No systematic validation of structure or semantic
  correctness
- **Semantic Enrichment**: No automated metadata enhancement or confidence
  scoring
- **Provenance Tracking**: No decision chains or evidence hierarchy recording
- **Domain Integration**: No neuroscience ontology alignment or biological
  plausibility checking

### What's Over-Engineered (Simplify)

- **Complex Phasing**: Remove artificial phase boundaries - build as integrated
  product
- **Excessive Abstraction**: Focus on concrete capabilities rather than
  theoretical frameworks
- **Multiple Validation Layers**: Streamline to essential validation that
  provides real value

## Target Architecture: Schema-First Unified Product

### Core Principle: Single Source of Truth

```
NWB-LinkML Schema → Generated Artifacts → Consistent Processing
                 ↓
    JSON-LD @context + SHACL shapes + OWL ontology
                 ↓
    All conversions use same IRIs, validation, and semantics
```

### Key Components

#### 1. Schema Management System

- **Input**: Official NWB-LinkML schema (single canonical source)
- **Outputs**:
  - JSON-LD @context for consistent IRIs across all tools
  - SHACL shapes for structural validation
  - OWL ontology for semantic reasoning
- **Versioning**: Pin schema version in all outputs and provenance
- **Caching**: Store generated artifacts with hash-based validation

#### 2. Unified Conversion Pipeline

```
NWB File → LinkML Validation → RDF Generation → SHACL Validation → Knowledge Graph
```

- Use MVP's proven parsing logic but with schema-consistent IRI generation
- Validate structure against LinkML schema before conversion
- Generate RDF using schema-derived JSON-LD context
- Validate RDF graph against SHACL shapes
- Fail fast with clear error messages and fix suggestions

#### 3. Semantic Enrichment Engine

- **Strain-to-Species Mapping**: Automatic inference with confidence scoring
- **Device Specification Lookup**: Cross-reference device databases
- **Protocol Enrichment**: Infer experimental protocols from setup data
- **Evidence Tracking**: Record reasoning chains and source attribution
- **Conflict Detection**: Identify and flag inconsistent metadata
- **Human Override**: Support manual corrections with provenance

#### 4. Provenance and Quality System

- **PROV-O Integration**: Record all decisions and evidence in standard
  provenance ontology
- **Confidence Levels**: Multiple levels from definitive to uncertain
- **Evidence Hierarchy**: Track source reliability and reasoning chains
- **Quality Metrics**: Measure conversion success, enrichment accuracy,
  validation pass rates
- **Audit Trails**: Complete traceability from source data to final knowledge
  graph

#### 5. Query and Validation Framework

- **SPARQL Endpoint**: Standard query interface with optimization
- **Custom Validation Rules**: Domain-specific biological plausibility checks
- **Federated Queries**: Cross-repository knowledge integration
- **Performance Monitoring**: Query execution metrics and optimization

#### 6. Integration and Export Services

- **MCP Server Tools**: Agent-friendly APIs for all capabilities
- **Multiple Formats**: TTL, JSON-LD, N-Triples, RDF/XML with consistent
  structure
- **Human-Readable Outputs**: Triple summaries, reasoning explanations, quality
  reports
- **Interactive Visualization**: Enhanced version of MVP's PyVis approach
- **DataLad Integration**: Correlate semantic provenance with file-level
  provenance

## Migration Strategy

### Step 1: Rewrite Requirements (Unified Product)

Remove phased approach and rewrite as integrated product requirements:

**Core User Stories:**

1. **Schema Consistency**: "As a researcher, I want all my NWB conversions to
   use consistent schemas and IRIs so that knowledge graphs from different
   sources can be combined and queried together."

2. **Reliable Conversion**: "As a data manager, I want robust NWB-to-RDF
   conversion with validation and error reporting so that I can trust the
   semantic representation of my data."

3. **Semantic Enrichment**: "As a domain expert, I want automatic metadata
   enrichment with evidence tracking so that gaps in my data are filled with
   scientifically accurate information."

4. **Quality Assurance**: "As a system administrator, I want comprehensive
   validation and quality metrics so that I can ensure data integrity and system
   reliability."

5. **Agent Integration**: "As a developer, I want clean MCP server integration
   so that semantic capabilities are seamlessly available to conversion
   workflows."

### Step 2: Update Design Document

Restructure design around unified architecture:

- **Remove Phase Sections**: Integrate all capabilities into single coherent
  design
- **Schema-First Flow**: Start with NWB-LinkML schema management as foundation
- **Proven Patterns**: Incorporate MVP's successful conversion logic
- **Clear Data Flow**: Show how data moves from NWB → validation → enrichment →
  knowledge graph
- **Integration Points**: Define clean interfaces with MCP server and DataLad

### Step 3: Restructure Task List

Organize tasks by component rather than phases:

1. **Schema Management Tasks**: NWB-LinkML integration, artifact generation,
   versioning
2. **Conversion Pipeline Tasks**: Validation, RDF generation, quality checking
3. **Enrichment Engine Tasks**: Metadata enhancement, confidence scoring,
   evidence tracking
4. **Query Framework Tasks**: SPARQL endpoint, validation rules, performance
   optimization
5. **Integration Tasks**: MCP server tools, export services, visualization
6. **Testing Tasks**: Comprehensive validation across all components

### Step 4: Implementation Priorities

Focus on core value delivery:

1. **Schema Consistency** (Immediate Value): Solve the IRI inconsistency problem
2. **Reliable Conversion** (Foundation): Build on MVP patterns with validation
3. **Basic Enrichment** (Quick Wins): Strain-species mapping, device lookup
4. **Advanced Features** (Enhanced Value): Complex reasoning, federated queries

## Success Criteria

### Technical Metrics

- **Consistency**: 100% of conversions use schema-derived IRIs
- **Reliability**: >95% conversion success rate with clear error reporting
- **Quality**: Measurable improvement in metadata completeness and accuracy
- **Performance**: Sub-second response for typical conversion and enrichment
  operations

### User Experience

- **Simplicity**: Single command converts NWB to validated knowledge graph
- **Transparency**: Clear explanations of enrichments and confidence levels
- **Integration**: Seamless operation within existing conversion workflows
- **Scalability**: Handles datasets from single files to large repositories

## Key Implementation Insights

### From MVP Analysis

- **File-based workflows work**: Don't over-complicate with complex databases
- **Visualization matters**: Users need to see and explore their knowledge
  graphs
- **Error handling is critical**: Clear messages and recovery suggestions are
  essential
- **Performance is important**: Keep conversion times reasonable for interactive
  use

### From Schema-First Approach

- **Consistency enables federation**: Same IRIs = combinable knowledge graphs
- **Validation prevents problems**: Catch issues early rather than debug later
- **Versioning enables evolution**: Track schema changes and provide migration
  paths
- **Standards compliance matters**: Align with NWB community rather than
  creating parallel systems

### From Semantic Requirements

- **Evidence matters more than automation**: Users need to understand and trust
  enrichments
- **Confidence scoring is essential**: Different levels of certainty for
  different use cases
- **Provenance enables debugging**: When something is wrong, users need to trace
  the source
- **Domain knowledge is valuable**: Neuroscience-specific validation catches
  real problems

## Next Steps

1. **Rewrite requirements.md** as unified product specification
2. **Update design.md** to reflect schema-first unified architecture
3. **Restructure tasks.md** by component rather than artificial phases
4. **Begin implementation** with schema management and conversion pipeline as
   foundation

The goal is a single, coherent product that solves real problems for
neuroscience researchers while providing a foundation for advanced semantic
capabilities.
