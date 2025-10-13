# Research: Knowledge Graph Systems

## LinkML Schema Integration

**Decision**: Use NWB-LinkML as canonical schema source with automated artifact
generation

**Rationale**:

- Ensures consistency with NWB standards and scientific community adoption
- Enables automatic generation of JSON-LD contexts, SHACL shapes, and OWL
  ontologies
- Provides type-safe Python bindings and validation framework
- Supports schema versioning and provenance tracking required by constitution

**Alternatives considered**:

- Custom schema definition: Rejected due to NWB standard compliance requirements
- Manual RDF generation: Rejected due to maintenance overhead and error
  potential
- Direct NWB schema usage: Rejected due to lack of semantic web artifact
  generation

**Implementation approach**: Use linkml-generate-\* tools for automated artifact
creation with schema version tracking

## RDF Triple Store Selection

**Decision**: rdflib with optional SPARQL endpoint backend for development,
scalable triple store for production

**Rationale**:

- Python ecosystem compatibility aligns with existing pixi.toml configuration
- Development flexibility allows local testing and debugging
- Production scalability path to Jena Fuseki, Blazegraph, or cloud solutions
- Supports W3C standards compliance required by constitution

**Alternatives considered**:

- Native triple stores (Jena, Blazegraph): Rejected for development phase
  complexity
- Embedded solutions (SQLite RDF extensions): Rejected due to SPARQL performance
  limitations
- Cloud-only solutions: Rejected due to development environment requirements

**Implementation approach**: rdflib.Graph for development with configurable
SPARQL endpoint for production deployment

## SHACL Validation Framework

**Decision**: pyshacl library with LinkML-generated shapes for structural
validation

**Rationale**:

- Python integration ensures seamless workflow with LinkML schema processing
- Automatic shape generation from schema reduces manual maintenance
- W3C SHACL compliance meets constitutional semantic web standards
- Supports detailed validation reports required for quality assurance

**Alternatives considered**:

- Manual SHACL shape definition: Rejected due to schema synchronization
  challenges
- Alternative validation approaches (JSON Schema): Rejected due to semantic web
  requirements
- Java-based SHACL validators: Rejected due to Python ecosystem preference

**Implementation approach**: Generate SHACL shapes from LinkML schema, validate
RDF graphs with detailed error reporting

## MCP Server Architecture

**Decision**: Claude Agent SDK with thin MCP adapter layer (<500 LOC)

**Rationale**:

- **Constitutional Requirement**: Constitution Principle I mandates "Claude Agent
  SDK handles protocol communication, context management, and tool ecosystem"
- Transport adapters must be thin (<500 LOC) with ZERO business logic
- Agent SDK provides automatic context compaction and management
- Built-in async support enables concurrent access for 1-10 users
- Eliminates need for custom MCP server implementation
- Clean separation: knowledge graph business logic in service layer, MCP
  integration in thin adapter

**Alternatives considered**:

- Custom FastAPI-based MCP server: **REJECTED** - Violates Constitution
  Principle I requirement for Claude Agent SDK
- Synchronous server: Rejected due to concurrent user requirements
- Direct integration without MCP layer: Rejected due to constitutional
  separation requirements

**Implementation approach**: Register knowledge graph tools with Agent SDK's MCP
extensibility using `@mcp.tool` decorators, business logic remains in separate
`agentic_neurodata_conversion/knowledge_graph/` service layer, thin adapter in
`agentic_neurodata_conversion/mcp_server/tools/kg_tools.py` (<500 LOC)

## Neuroscience Ontology Integration

**Decision**: Basic concept mapping with NIFSTD, UBERON, CHEBI, NCBITaxon
through OWL imports

**Rationale**:

- Semantic richness provides domain-specific validation and enrichment
  capabilities
- Confidence scoring enables evidence-based metadata suggestions
- OWL imports maintain semantic consistency with external ontologies
- Basic mapping approach balances functionality with small lab scale
  requirements

**Alternatives considered**:

- Full ontology reasoning: Rejected due to computational complexity for small
  scale
- Manual concept definitions: Rejected due to scientific accuracy requirements
- Single ontology focus: Rejected due to comprehensive neuroscience coverage
  needs

**Implementation approach**: OWL import statements in generated ontology, basic
subsumption and equivalence mapping with confidence scores

## Performance and Scalability Decisions

**Decision**: 30-second query timeout with optimization for small dataset scale
(100 NWB files)

**Rationale**:

- Aligns with clarified performance requirements for research workflows
- Enables complex SPARQL queries for metadata enrichment without premature
  optimization
- Small dataset scale allows in-memory processing for development
- Provides clear performance boundaries for constitutional compliance

**Implementation approach**: Query timeout configuration, indexing strategy for
common query patterns, memory-efficient RDF processing

## Quality Assurance Framework

**Decision**: Mandatory human review with detailed confidence scoring and
evidence trails

**Rationale**:

- Meets clarified requirement for all suggestions requiring human review
- Provides scientific rigor for research data quality
- Evidence trails support reproducibility and provenance tracking
- Confidence scoring enables informed decision-making

**Implementation approach**: Structured review interface, confidence metrics
calculation, PROV-O based evidence tracking
