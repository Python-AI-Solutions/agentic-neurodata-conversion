# Knowledge Graph System Quickstart

## Prerequisites
- Python 3.12+
- pixi environment setup
- NWB file for testing
- NWB-LinkML schema available

## Quick Start Steps

### 1. Environment Setup
```bash
# Activate pixi environment
pixi shell

# Verify dependencies
python -c "import rdflib, linkml, pynwb; print('Dependencies OK')"
```

### 2. Create Knowledge Graph from NWB File
```bash
# Using the MCP tool endpoint
curl -X POST http://localhost:8000/knowledge-graphs \
  -H "Content-Type: application/json" \
  -d '{
    "nwb_file_path": "/path/to/sample.nwb",
    "schema_version": "2.8.0"
  }'
```

Expected response:
```json
{
  "graph_id": "kg-12345",
  "status": "building",
  "nwb_file_path": "/path/to/sample.nwb",
  "schema_version": "2.8.0",
  "created_at": "2025-09-25T19:30:00Z"
}
```

### 3. Check Graph Status
```bash
curl http://localhost:8000/knowledge-graphs/kg-12345
```

Wait for status to change from "building" to "ready".

### 4. Query with SPARQL
```bash
curl -X POST http://localhost:8000/knowledge-graphs/kg-12345/sparql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT ?subject ?species WHERE { ?subject a nwb:Subject ; nwb:species ?species }"
  }'
```

Expected response:
```json
{
  "bindings": [
    {
      "subject": {"type": "uri", "value": "http://example.org/subject/001"},
      "species": {"type": "literal", "value": "Mus musculus"}
    }
  ],
  "execution_time_ms": 45
}
```

### 5. Enrich Metadata
```bash
curl -X POST http://localhost:8000/knowledge-graphs/kg-12345/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "entity_ids": ["http://example.org/subject/001"],
    "confidence_threshold": 0.8
  }'
```

Expected response:
```json
{
  "suggestions": [
    {
      "suggestion_id": "sug-67890",
      "entity_id": "http://example.org/subject/001",
      "property_name": "strain",
      "suggested_value": "C57BL/6J",
      "confidence": 0.95,
      "source_ontology": "NCBITaxon",
      "evidence": {"source_iri": "http://purl.obolibrary.org/obo/NCBITaxon_10090"},
      "status": "pending"
    }
  ]
}
```

### 6. Validate with SHACL
```bash
curl -X POST http://localhost:8000/knowledge-graphs/kg-12345/validate
```

Expected response:
```json
{
  "conforms": true,
  "violations": []
}
```

## Success Criteria Validation

### Performance Test
```bash
# Test concurrent queries (requires ab tool)
ab -n 100 -c 5 -T application/json \
   -p sparql_query.json \
   http://localhost:8000/knowledge-graphs/kg-12345/sparql
```

Target: < 1000ms average response time

### Scale Test
```bash
# Test with multiple graphs
for i in {1..10}; do
  curl -X POST http://localhost:8000/knowledge-graphs \
    -H "Content-Type: application/json" \
    -d "{\"nwb_file_path\": \"/data/sample_${i}.nwb\", \"schema_version\": \"2.8.0\"}"
done
```

Target: Successfully process 100-1000 NWB files

### Conflict Resolution Test
```bash
# Create conflicting enrichment suggestions
curl -X POST http://localhost:8000/knowledge-graphs/kg-12345/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "entity_ids": ["http://example.org/subject/001"],
    "confidence_threshold": 0.5
  }'
```

Target: Higher confidence suggestions should win

## Troubleshooting

### Common Issues
1. **Status stuck on "building"**: Check NWB file validity and schema compatibility
2. **SPARQL query timeout**: Optimize query or check indexing
3. **Low quality scores**: Review NWB metadata completeness

### Debug Commands
```bash
# Check graph statistics
curl http://localhost:8000/knowledge-graphs/kg-12345 | jq '.triple_count, .quality_score'

# List all graphs
curl http://localhost:8000/knowledge-graphs | jq '.graphs[].status'

# Check enrichment suggestions
curl "http://localhost:8000/knowledge-graphs/kg-12345/enrich?entity_ids=all" | jq '.suggestions | length'
```

## Integration with Agents

### MCP Tool Usage
```python
# From an MCP agent
result = await mcp_client.call_tool(
    "knowledge-graph-query",
    {
        "graph_id": "kg-12345",
        "query": "SELECT ?device WHERE { ?device a nwb:Device }"
    }
)
```

### Expected Agent Workflow
1. Agent receives NWB conversion request
2. Creates knowledge graph via MCP tool
3. Enriches metadata using suggestions
4. Validates enriched data with SHACL
5. Proceeds with conversion using enriched metadata