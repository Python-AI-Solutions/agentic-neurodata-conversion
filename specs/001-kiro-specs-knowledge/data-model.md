# Data Model: Knowledge Graph Systems

## Core Entities

### KnowledgeGraph
- **graph_id**: str (UUID)
- **nwb_file_path**: str
- **schema_version**: str (NWB-LinkML version)
- **created_at**: datetime
- **updated_at**: datetime
- **status**: enum (building, ready, error)
- **triple_count**: int
- **quality_score**: float (0.0-1.0)

**Relationships**:
- Contains multiple Entities
- References SchemaArtifacts
- Tracks Provenance records

### Entity
- **entity_id**: str (IRI)
- **entity_type**: str (from NWB-LinkML)
- **properties**: dict[str, Any]
- **confidence_scores**: dict[str, float]
- **enrichment_status**: enum (original, enriched, conflicted)

**Relationships**:
- Belongs to KnowledgeGraph
- Has EnrichmentSuggestions
- Connected via SemanticRelations

### EnrichmentSuggestion
- **suggestion_id**: str (UUID)
- **entity_id**: str (FK to Entity)
- **property_name**: str
- **suggested_value**: Any
- **confidence**: float (0.0-1.0)
- **source_ontology**: str
- **evidence**: dict[str, Any]
- **created_at**: datetime
- **status**: enum (pending, accepted, rejected)

**Validation Rules**:
- confidence must be between 0.0 and 1.0
- source_ontology must be one of: NIFSTD, UBERON, CHEBI, NCBITaxon
- evidence must contain source IRI

### SemanticRelation
- **relation_id**: str (UUID)
- **subject_id**: str (Entity IRI)
- **predicate**: str (relationship type IRI)
- **object_id**: str (Entity IRI or literal)
- **confidence**: float
- **derived_from**: str (source of relationship)

### SchemaArtifact
- **artifact_id**: str (UUID)
- **schema_version**: str
- **artifact_type**: enum (jsonld_context, shacl_shapes, owl_ontology)
- **content**: str (serialized artifact)
- **checksum**: str (content hash)
- **created_at**: datetime

**Validation Rules**:
- checksum must match content hash
- schema_version must be valid semantic version

### Provenance
- **prov_id**: str (UUID)
- **activity_type**: str (PROV-O activity)
- **entity_id**: str (what was modified)
- **agent**: str (what performed the action)
- **timestamp**: datetime
- **parameters**: dict[str, Any]
- **evidence_chain**: list[str] (linked provenance records)

## State Transitions

### KnowledgeGraph States
```
building → ready (successful triple generation)
building → error (validation failure)
ready → building (schema update triggered)
error → building (retry/fix triggered)
```

### EnrichmentSuggestion States
```
pending → accepted (confidence-based resolution or manual approval)
pending → rejected (lower confidence or manual rejection)
```

## Indexing Strategy

### Primary Indexes
- KnowledgeGraph: graph_id, nwb_file_path
- Entity: entity_id, entity_type
- EnrichmentSuggestion: entity_id, status, confidence DESC
- SemanticRelation: subject_id, object_id, predicate

### Composite Indexes
- Entity: (entity_type, enrichment_status)
- Provenance: (entity_id, timestamp DESC)
- SchemaArtifact: (schema_version, artifact_type)

## Constraints

### Business Rules
1. Each KnowledgeGraph must reference valid NWB file
2. EnrichmentSuggestions with highest confidence win conflicts
3. Schema version changes must maintain backward compatibility
4. All modifications must create Provenance records

### Performance Constraints
- Entity lookups: < 10ms for indexed access
- SPARQL queries: < 1000ms for typical research queries
- Enrichment processing: < 5000ms per entity
- Concurrent read capacity: 10 users minimum