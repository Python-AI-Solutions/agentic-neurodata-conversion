# Quickstart Guide: Knowledge Graph Systems

## Overview

This guide demonstrates the end-to-end knowledge graph workflow for NWB data
enrichment, validation, and semantic querying. All examples follow
constitutional requirements for schema-first development and human review.

## Prerequisites

- Python 3.12+ environment
- NWB files for testing (max 100 per dataset)
- Access to knowledge graph server endpoints
- MCP server running for agent integration

## Quick Start Scenarios

### Scenario 1: Dataset Creation and Basic Enrichment

**Step 1: Create a new dataset**

```bash
# Using CLI
python -m knowledge_graph_cli create-dataset \
  --title "Mouse V1 Recordings" \
  --description "Visual cortex recordings from C57BL/6 mice" \
  --nwb-files "session_001.nwb,session_002.nwb"

# Expected output: Dataset ID and basic validation status
```

**Step 2: Validate NWB-LinkML compliance**

```bash
# Validate against current schema
python -m knowledge_graph_cli validate-linkml \
  --dataset-id "dataset_001" \
  --schema-version "2.6.0"

# Expected: Validation report with pass/fail status
# If fails: Reject data and require manual correction (per clarifications)
```

**Step 3: Generate enrichment suggestions**

```bash
# Generate metadata enrichment suggestions
python -m knowledge_graph_cli enrich-metadata \
  --dataset-id "dataset_001" \
  --sources "NCBITaxon,NIFSTD,UBERON" \
  --output-format "review"

# Expected: All suggestions flagged for human review (per clarifications)
```

**Step 4: Human review process**

```bash
# Present suggestions for review
python -m knowledge_graph_cli review-suggestions \
  --dataset-id "dataset_001" \
  --interactive

# Expected: Interactive review interface with evidence chains
# User must approve/reject each suggestion manually
```

**Validation Criteria**:

- Dataset creation completes within 30 seconds
- LinkML validation identifies schema compliance issues
- Enrichment suggestions include confidence scores and evidence
- All suggestions require explicit human approval
- No automatic acceptance regardless of confidence level

### Scenario 2: SPARQL Query and Semantic Exploration

**Step 1: Execute basic SPARQL query**

```bash
# Query for all datasets and their subjects
python -m knowledge_graph_cli sparql-query \
  --query "SELECT ?dataset ?subject ?species WHERE {
    ?dataset rdf:type kg:Dataset .
    ?dataset kg:hasSubject ?subject .
    ?subject kg:hasSpecies ?species .
  } LIMIT 10" \
  --timeout 30

# Expected: Results within 30-second timeout (per clarifications)
```

**Step 2: Complex metadata validation query**

```bash
# Query for potential data quality issues
python -m knowledge_graph_cli sparql-query \
  --query "SELECT ?session ?issue WHERE {
    ?session rdf:type kg:Session .
    ?session kg:hasQualityIssue ?issue .
    ?issue kg:severity 'error' .
  }" \
  --format "json"

# Expected: Structured quality assessment results
```

**Step 3: Ontology relationship exploration**

```bash
# Query neuroscience ontology mappings
python -m knowledge_graph_cli query-ontology \
  --concept "visual cortex" \
  --ontologies "NIFSTD,UBERON" \
  --relationship-type "subclass"

# Expected: Hierarchical relationships with confidence scores
```

**Validation Criteria**:

- All queries complete within 30-second timeout
- Results include proper semantic relationships
- Ontology mappings have confidence scores
- Error handling for malformed queries

### Scenario 3: MCP Agent Integration Workflow

**Step 1: Initialize MCP server**

```bash
# Start knowledge graph MCP server
python -m mcp_server.knowledge_graph_server \
  --port 8000 \
  --config "config/mcp_tools.yaml"

# Expected: MCP server running with knowledge graph tools exposed
```

**Step 2: Agent-driven metadata enrichment**

```python
# Example agent interaction through MCP
import mcp

# Connect to knowledge graph MCP server
client = mcp.Client("http://localhost:8000")

# Request metadata enrichment
response = client.call_tool("enrich_metadata", {
    "entity_type": "subject",
    "entity_data": {
        "strain": "C57BL/6",
        "age": "P60"
    },
    "sources": ["NCBITaxon", "NIFSTD"]
})

# Expected: Structured enrichment suggestions for agent processing
```

**Step 3: Conflict resolution through MCP**

```python
# Handle conflicting suggestions
conflicts = client.call_tool("resolve_conflicts", {
    "entity_id": "subject_001",
    "conflict_type": "enrichment"
})

# Present conflicts to user for manual resolution
for conflict in conflicts["conflicts"]:
    print(f"Field: {conflict['field']}")
    print(f"Options: {conflict['conflicting_values']}")
    # User must manually select resolution

# Expected: All conflicts presented to user for manual resolution
```

**Validation Criteria**:

- MCP tools respond with structured data format
- Agent interactions maintain constitutional compliance
- Concurrent access supported for 1-10 users (per clarifications)
- All enrichment suggestions require human review

### Scenario 4: Schema Evolution and Artifact Regeneration

**Step 1: Schema version update**

```bash
# Check current schema version
python -m knowledge_graph_cli schema-info

# Update to new NWB-LinkML version
python -m knowledge_graph_cli update-schema \
  --version "2.7.0" \
  --regenerate-artifacts

# Expected: Automatic regeneration of JSON-LD, SHACL, RDF artifacts
```

**Step 2: Validate existing data against new schema**

```bash
# Validate all datasets against updated schema
python -m knowledge_graph_cli validate-all \
  --schema-version "2.7.0" \
  --report-format "detailed"

# Expected: Comprehensive validation report with migration guidance
```

**Step 3: SHACL validation with generated shapes**

```bash
# Run SHACL validation with auto-generated shapes
python -m knowledge_graph_cli validate-shacl \
  --dataset-id "dataset_001" \
  --shapes-version "2.7.0"

# Expected: W3C SHACL compliance validation with detailed reports
```

**Validation Criteria**:

- Schema updates trigger artifact regeneration
- Version metadata tracked in PROV-O provenance
- Existing data validated against new schema
- Migration guidance provided for breaking changes

### Scenario 5: Quality Assurance and Lineage Tracking

**Step 1: Generate quality assessment report**

```bash
# Comprehensive quality assessment
python -m knowledge_graph_cli quality-assessment \
  --dataset-id "dataset_001" \
  --include-lineage \
  --confidence-threshold 0.0

# Expected: Quality scores with configurable thresholds
```

**Step 2: Track data lineage and provenance**

```bash
# Query provenance chain
python -m knowledge_graph_cli sparql-query \
  --query "SELECT ?activity ?entity ?agent WHERE {
    ?activity prov:used ?entity .
    ?activity prov:wasAssociatedWith ?agent .
    ?entity rdf:type kg:Dataset .
  }"

# Expected: Complete PROV-O provenance tracking
```

**Step 3: Evidence trail validation**

```bash
# Validate evidence trails for enrichment decisions
python -m knowledge_graph_cli validate-evidence \
  --entity-id "subject_001" \
  --trace-sources

# Expected: Complete evidence chains for all decisions
```

**Validation Criteria**:

- Quality scoring with configurable thresholds
- Complete lineage tracking from raw NWB to RDF
- Evidence trails maintained for all enrichment decisions
- PROV-O ontology compliance for provenance

## Performance Benchmarks

### Expected Performance Targets

- **Query Timeout**: 30 seconds maximum for metadata enrichment
- **Concurrent Users**: Support 1-10 simultaneous users
- **Dataset Scale**: Handle up to 100 NWB files per dataset
- **Response Time**: Interactive operations under 5 seconds
- **Validation Time**: Schema validation under 10 seconds per file

### Performance Testing Commands

```bash
# Test query performance
python -m knowledge_graph_cli benchmark-sparql \
  --query-file "benchmarks/complex_queries.sparql" \
  --iterations 10

# Test concurrent access
python -m knowledge_graph_cli stress-test \
  --concurrent-users 10 \
  --duration 60

# Test dataset scale limits
python -m knowledge_graph_cli scale-test \
  --nwb-files 100 \
  --operation "full-enrichment"
```

## Error Handling and Recovery

### Common Error Scenarios

1. **Schema Validation Failure**: Reject data, require manual correction
2. **SPARQL Query Timeout**: Return partial results with timeout notice
3. **Conflicting Enrichment Sources**: Present all conflicts for manual
   resolution
4. **MCP Tool Unavailable**: Graceful degradation with error reporting
5. **Ontology Mapping Failure**: Log error, continue with available mappings

### Recovery Procedures

```bash
# Recover from validation failures
python -m knowledge_graph_cli repair-dataset \
  --dataset-id "dataset_001" \
  --validation-report "validation_errors.json"

# Restart MCP server with state recovery
python -m mcp_server.knowledge_graph_server \
  --recover-state \
  --backup-file "state_backup.json"
```

## Integration Testing Checklist

- [ ] Dataset creation with NWB file validation
- [ ] LinkML schema compliance checking
- [ ] SHACL shape validation with generated shapes
- [ ] SPARQL query execution within timeout limits
- [ ] Metadata enrichment with human review workflow
- [ ] Conflict resolution for competing suggestions
- [ ] MCP tool integration with structured responses
- [ ] Ontology mapping with confidence scoring
- [ ] Provenance tracking using PROV-O
- [ ] Quality assessment with configurable thresholds
- [ ] Schema evolution with artifact regeneration
- [ ] Concurrent access for multiple users
- [ ] Performance benchmarks within specified limits
- [ ] Error handling and graceful degradation

## Next Steps

After completing this quickstart:

1. Run comprehensive integration tests
2. Deploy to development environment
3. Configure production ontology endpoints
4. Set up monitoring and alerting
5. Train users on review workflow
6. Establish backup and recovery procedures
