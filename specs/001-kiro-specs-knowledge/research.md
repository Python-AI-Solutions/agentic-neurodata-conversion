# Research: Knowledge Graph Systems for NWB Data

## RDF Triple Store Selection

**Decision**: Use rdflib with optional persistent backend (SQLite/PostgreSQL)
**Rationale**:
- rdflib already in dependencies, mature Python RDF library
- Supports SPARQL 1.1 queries natively
- Can scale from in-memory to persistent storage
- Good integration with existing Python ecosystem

**Alternatives considered**:
- Apache Jena Fuseki: More scalable but adds Java dependency
- GraphDB: Commercial solution with better performance but licensing costs
- Virtuoso: High performance but complex setup

## LinkML Integration Patterns

**Decision**: Use LinkML-runtime for schema validation and RDF generation
**Rationale**:
- Direct integration with NWB-LinkML schemas
- Built-in JSON-LD context generation
- SHACL shape generation from schema definitions
- Active development by LinkML community

**Alternatives considered**:
- Manual RDF mapping: Too error-prone and maintenance-heavy
- pydantic-to-RDF: Limited LinkML integration
- Direct PyLD usage: Lower-level, more implementation work

## SPARQL Query Optimization

**Decision**: Implement query planning with indexing on frequent access patterns
**Rationale**:
- Sub-second response requirement for 1-10GB graphs
- Common neuroscience query patterns (by species, device, protocol)
- rdflib supports custom stores with indexing

**Alternatives considered**:
- No optimization: Likely too slow for requirements
- Full-text indexing: Overkill for structured metadata
- Graph database: Would require major architecture change

## Ontology Integration Strategy

**Decision**: Use ontology mappings with confidence scoring and caching
**Rationale**:
- NIFSTD, UBERON, CHEBI, NCBITaxon are large ontologies
- Confidence-based conflict resolution requirement
- Network requests should be cached for performance

**Alternatives considered**:
- Full ontology loading: Too memory intensive
- No confidence scoring: Doesn't meet requirements
- Real-time lookups: Too slow for user experience

## MCP Server Integration Architecture

**Decision**: Knowledge graph service as MCP tool with dedicated endpoints
**Rationale**:
- Fits existing MCP server architecture
- Clean separation of concerns
- Supports concurrent agent access
- Standard MCP protocol compliance

**Alternatives considered**:
- Direct database access by agents: Violates MCP architecture
- Separate microservice: Adds deployment complexity
- Embedded in each agent: Duplication and consistency issues

## Concurrency and State Management

**Decision**: Async/await with read-write locks for graph modifications
**Rationale**:
- 5-10 concurrent user requirement
- Most operations are read-heavy (queries)
- Write operations (enrichment) need consistency
- Python asyncio fits existing codebase patterns

**Alternatives considered**:
- Threading: GIL limitations in Python
- Process-based: Higher memory overhead
- No concurrency control: Data corruption risk

## Schema Version Management

**Decision**: Schema versioning with backward compatibility validation
**Rationale**:
- Backward compatibility requirement from clarifications
- Need to track schema versions in provenance
- Automated artifact regeneration on schema updates

**Alternatives considered**:
- Multiple schema versions: Storage complexity
- Manual migration: Violates automation requirements
- Breaking changes allowed: Violates clarified requirements