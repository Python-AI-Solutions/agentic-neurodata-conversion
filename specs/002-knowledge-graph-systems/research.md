# Research: Knowledge Graph Systems

**Created**: 2025-09-26
**Phase**: 0 - Technical Research and Decision Making

## Research Areas

### 1. RDF Triple Store Selection

**Decision**: rdflib with file-based storage and optional in-memory graphs
**Rationale**:
- Already in project dependencies (pixi.toml)
- Mature Python library with excellent SPARQL support
- Supports multiple serialization formats (JSON-LD, TTL, N3, XML)
- Good performance for research-scale datasets (1K-100K triples)
- No additional infrastructure requirements

**Alternatives Considered**:
- **Apache Jena Fuseki**: More scalable but requires Java infrastructure
- **Blazegraph**: High performance but heavyweight for initial implementation
- **Neo4j**: Graph database but not RDF-native
- **Stardog**: Commercial solution, overkill for research use case

### 2. NWB-LinkML Schema Integration

**Decision**: Direct LinkML schema processing with artifact generation pipeline
**Rationale**:
- LinkML already in dependencies with rich Python ecosystem
- Native support for generating JSON-LD contexts from schemas
- Built-in SHACL shape generation capabilities
- Version tracking through schema metadata
- Integrates well with existing NWB ecosystem

**Alternatives Considered**:
- **Manual schema mapping**: Too maintenance-heavy, error-prone
- **Generic RDF Schema**: Loses NWB-specific semantics
- **OWL-only approach**: Less tooling support than LinkML

### 3. SPARQL Query Optimization

**Decision**: Query pattern optimization with result caching
**Rationale**:
- rdflib query optimizer handles basic optimizations
- Pattern-based query templates reduce parsing overhead
- In-memory caching for frequently accessed metadata
- Incremental result building for large datasets

**Implementation Patterns**:
```sparql
# Metadata enrichment pattern
PREFIX nwb: <http://schema.neurodata.io/nwb/>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?subject ?species WHERE {
  ?subject nwb:strain ?strain .
  ?mapping nwb:maps ?strain .
  ?mapping nwb:toSpecies ?species .
}

# Quality assessment pattern
PREFIX qa: <http://schema.neurodata.io/qa/>
SELECT ?dataset ?score ?issue WHERE {
  ?dataset qa:hasAssessment ?assessment .
  ?assessment qa:score ?score .
  ?assessment qa:hasIssue ?issue .
  FILTER(?score < 0.8)
}
```

### 4. Neuroscience Ontology Integration

**Decision**: Staged integration with core ontologies first
**Rationale**:
- Start with essential mappings (NCBITaxon for species)
- Add device ontologies (NEMO) for equipment mapping
- Expand to anatomical (UBERON) and chemical (CHEBI) as needed
- Use owl:sameAs and skos:exactMatch for concept alignment

**Integration Approach**:
- **Phase 1**: NCBITaxon for species/strain mapping
- **Phase 2**: Device ontologies for equipment specifications
- **Phase 3**: UBERON for anatomical references
- **Phase 4**: CHEBI for chemical/drug references

**Alternatives Considered**:
- **Full ontology import**: Too heavy, circular dependencies
- **API-based lookups**: Network dependency, slower performance
- **No external ontologies**: Loses semantic richness

### 5. PROV-O Provenance Modeling

**Decision**: Core PROV-O patterns with domain extensions
**Rationale**:
- Standard W3C provenance ontology
- Well-established patterns for data transformation
- Supports attribution, derivation, and activity chains
- Integrates cleanly with RDF graph structure

**Core Patterns**:
```turtle
# Data transformation provenance
:enriched_metadata prov:wasDerivedFrom :original_metadata ;
                   prov:wasGeneratedBy :enrichment_activity .

:enrichment_activity a prov:Activity ;
                    prov:used :knowledge_graph ;
                    prov:wasAssociatedWith :enrichment_agent .

# Quality assessment provenance
:quality_report prov:wasGeneratedBy :validation_activity ;
               prov:wasAttributedTo :validator_agent .
```

### 6. MCP Server Integration Architecture

**Decision**: FastAPI-based MCP server with async SPARQL operations
**Rationale**:
- FastAPI already in project dependencies
- Native async support for concurrent queries
- OpenAPI integration for contract testing
- Clean separation between MCP protocol and graph operations

**Integration Points**:
- `/enrich`: Metadata enrichment endpoint
- `/validate`: Schema validation endpoint
- `/query`: SPARQL query interface
- `/generate`: Knowledge graph generation

## Technical Decisions Summary

| Component | Choice | Key Benefit |
|-----------|--------|-------------|
| RDF Store | rdflib | Zero infrastructure, proven |
| Schema Processing | LinkML direct | Native NWB integration |
| Query Engine | SPARQL + caching | Standards compliance |
| Ontology Integration | Staged approach | Manageable complexity |
| Provenance | PROV-O core | W3C standard |
| API Framework | FastAPI async | Concurrent performance |

## Performance Considerations

- **Query Response**: Sub-second for typical metadata queries
- **Graph Size**: Optimized for 1K-100K triples per dataset
- **Concurrent Access**: Async operations for multiple agents
- **Memory Usage**: Configurable in-memory vs disk-based storage
- **Caching Strategy**: LRU cache for frequent query patterns

## Integration Requirements

- **NWB-LinkML Schema**: Automatic artifact generation on schema updates
- **MCP Server**: Clean API integration with agent workflows
- **External Ontologies**: Controlled integration with quality gates
- **Provenance Tracking**: Complete audit trail for all transformations

---

**Status**: Phase 0 Research Complete ✓
**Next Phase**: Design & Contracts (Phase 1)