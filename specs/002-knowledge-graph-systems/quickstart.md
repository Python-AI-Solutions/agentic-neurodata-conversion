# Quickstart: Knowledge Graph Systems

**Created**: 2025-09-26
**Phase**: 1 - Design & Contracts

## Overview
This quickstart guide validates the core user scenarios for the Knowledge Graph Systems feature through integration test scenarios.

## Test Scenarios

### Scenario 1: Metadata Enrichment Workflow
**User Story**: Enrich incomplete NWB metadata with species information

**Setup**:
```python
# Test dataset with missing species information
incomplete_metadata = {
    "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
    "subject": {
        "subject_id": "mouse_01",
        "strain": "C57BL/6J",
        "age": "P60",
        "sex": "M"
        # Missing: species
    },
    "session": {
        "session_id": "recording_001",
        "experimenter": "Jane Doe"
    }
}
```

**Test Steps**:
1. **POST** `/api/v1/enrich/metadata`
   ```json
   {
     "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
     "metadata": /* incomplete_metadata */,
     "ontologies": ["NCBITaxon"]
   }
   ```

2. **Expected Response**:
   ```json
   {
     "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
     "enriched_metadata": {
       "subject": {
         "subject_id": "mouse_01",
         "strain": "C57BL/6J",
         "species": "Mus musculus",
         "species_id": "NCBITaxon:10090",
         "age": "P60",
         "sex": "M"
       }
     },
     "suggestions": [
       {
         "field": "subject.species",
         "current_value": null,
         "suggested_value": "Mus musculus",
         "confidence_score": 0.95,
         "evidence": [
           {
             "source": "NCBITaxon",
             "reasoning": "C57BL/6J is a well-known laboratory mouse strain",
             "confidence": 0.95
           }
         ]
       }
     ]
   }
   ```

**Validation Criteria**:
- ✓ Species correctly identified as "Mus musculus"
- ✓ Confidence score ≥ 0.8
- ✓ Evidence includes NCBITaxon reference
- ✓ Original metadata preserved
- ✓ Response time < 2 seconds

### Scenario 2: Schema Validation Workflow
**User Story**: Validate converted NWB data against schema using SHACL shapes

**Setup**:
```python
# NWB data to validate
nwb_data = {
    "@context": "https://schema.neurodata.io/nwb/context.jsonld",
    "@type": "NWBFile",
    "identifier": "test-dataset-001",
    "session_description": "Example recording session",
    "timestamps_reference_time": "2025-09-26T10:00:00Z",
    "file_create_date": ["2025-09-26T10:00:00Z"],
    "data_collection": "Extracellular electrophysiology",
    "experiment_description": "Test experiment"
}
```

**Test Steps**:
1. **POST** `/api/v1/validate/schema`
   ```json
   {
     "data": /* nwb_data */,
     "schema_version": "2.7.0"
   }
   ```

2. **Expected Response**:
   ```json
   {
     "valid": true,
     "errors": [],
     "warnings": [
       {
         "path": "subject",
         "message": "Subject information not provided"
       }
     ]
   }
   ```

**Validation Criteria**:
- ✓ Schema validation completes successfully
- ✓ Required fields identified correctly
- ✓ Validation warnings for optional missing fields
- ✓ Response includes validation details

### Scenario 3: SPARQL Query Workflow
**User Story**: Query experimental protocols with device relationships

**Test Steps**:
1. **POST** `/api/v1/query/sparql`
   ```json
   {
     "query": "PREFIX nwb: <http://schema.neurodata.io/nwb/> PREFIX kg: <http://schema.neurodata.io/knowledge-graph/> SELECT ?protocol ?device ?session WHERE { ?session nwb:followsProtocol ?protocol . ?session nwb:usesDevice ?device . ?device nwb:deviceType 'electrode' . } LIMIT 10",
     "format": "json"
   }
   ```

2. **Expected Response**:
   ```json
   {
     "results": {
       "bindings": [
         {
           "protocol": {"type": "uri", "value": "http://example.org/protocol/001"},
           "device": {"type": "uri", "value": "http://example.org/device/electrode_001"},
           "session": {"type": "uri", "value": "http://example.org/session/recording_001"}
         }
       ]
     },
     "execution_time": 150
   }
   ```

**Validation Criteria**:
- ✓ Query executes successfully
- ✓ Results include semantic relationships
- ✓ Execution time < 1000ms
- ✓ Results properly formatted as JSON-LD

### Scenario 4: Schema Update and Artifact Generation
**User Story**: Automatically regenerate artifacts when schema updates

**Test Steps**:
1. **POST** `/api/v1/schema/artifacts`
   ```json
   {
     "schema_version": "2.7.1",
     "artifacts": ["jsonld", "shacl", "owl"]
   }
   ```

2. **Expected Response**:
   ```json
   {
     "schema_version": "2.7.1",
     "artifacts": {
       "jsonld": {
         "@context": {
           "nwb": "http://schema.neurodata.io/nwb/",
           "Dataset": "nwb:Dataset",
           "Session": "nwb:Session"
         }
       },
       "shacl": {
         "@type": "sh:NodeShape",
         "sh:targetClass": "nwb:Dataset",
         "sh:property": []
       },
       "owl": {
         "@type": "owl:Ontology",
         "owl:imports": []
       }
     }
   }
   ```

**Validation Criteria**:
- ✓ All requested artifacts generated
- ✓ Artifacts valid according to their specifications
- ✓ Version information preserved in artifacts
- ✓ Provenance information recorded

## Integration Test Scenarios

### Test Suite 1: End-to-End Metadata Enrichment
1. Load incomplete NWB dataset
2. Enrich metadata using multiple ontologies
3. Validate enriched data against schema
4. Generate RDF representation
5. Query enriched data via SPARQL
6. Assess final data quality

### Test Suite 2: External Service Integration
1. Test with all ontology services available
2. Test with partial ontology service failures (should fail fast)
3. Test conflict resolution between multiple ontology sources
4. Validate confidence scoring and evidence tracking

### Test Suite 3: MCP Server Integration
1. Register MCP tools with server
2. Execute enrichment via MCP tool interface
3. Execute validation via MCP tool interface
4. Execute SPARQL queries via MCP tool interface
5. Test concurrent MCP tool access

### Test Suite 4: Performance and Scalability
1. Test with small datasets (< 1K triples)
2. Test with medium datasets (10K-50K triples)
3. Test with large datasets (50K-100K triples)
4. Test with concurrent users (5-20 simultaneous)
5. Validate response times meet requirements

## Error Scenarios

### External Ontology Service Failures
**Test**: Simulate NCBITaxon service unavailability

**Expected Behavior**:
- API returns HTTP 503
- Error message indicates external service failure
- No partial enrichment performed (fail-fast)
- Operation can be retried when service recovers

### Conflicting Ontology Information
**Test**: Provide conflicting species information from multiple sources

**Expected Behavior**:
- System selects highest confidence mapping
- Evidence provided for decision
- Alternative mappings logged but not used
- Confidence scores reflect uncertainty

### Schema Validation Failures
**Test**: Submit invalid NWB data structure

**Expected Behavior**:
- Validation fails with detailed error messages
- Specific validation rule violations identified
- Suggested corrections provided where possible
- No RDF generation for invalid data

## Success Metrics
- All test scenarios pass within performance requirements
- External service integration handles failures gracefully
- MCP tools integrate seamlessly with agent workflows
- Data quality improvements measurable via assessment scores
- Complete provenance tracking for all operations

## Prerequisites
- NWB-LinkML schema version 2.7.0+ available
- External ontology services (NCBITaxon, NIFSTD) accessible
- MCP server running and configured
- Test datasets prepared with known validation results

---

**Status**: Phase 1 Quickstart Complete ✓
**Next Step**: Update agent context and finalize design phase