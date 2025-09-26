# Data Model: Knowledge Graph Systems

**Created**: 2025-09-26
**Phase**: 1 - Design & Contracts

## Core Entities

### Dataset
**Purpose**: Represents NWB datasets with comprehensive metadata and semantic relationships

**Attributes**:
- `dataset_id`: Unique identifier (UUID)
- `name`: Human-readable dataset name
- `description`: Dataset description and purpose
- `creation_date`: Dataset creation timestamp
- `schema_version`: NWB-LinkML schema version used
- `file_path`: Location of NWB file
- `file_size`: Size in bytes
- `checksum`: SHA256 hash for integrity

**Relationships**:
- `has_sessions`: One-to-many with Session entities
- `belongs_to_project`: Many-to-one with Project Context
- `has_quality_assessment`: One-to-many with Quality Assessment
- `derived_from`: Many-to-many with other Datasets (provenance)

**Validation Rules**:
- `dataset_id` must be unique across system
- `schema_version` must match known NWB-LinkML versions
- `file_path` must be accessible and contain valid NWB data

### Session
**Purpose**: Experimental sessions containing temporal data and experimental context

**Attributes**:
- `session_id`: Unique identifier
- `session_start`: Experiment start timestamp
- `session_description`: Session purpose and methodology
- `experimenter`: Researcher conducting session
- `lab`: Laboratory identifier
- `institution`: Institution name
- `keywords`: Searchable tags

**Relationships**:
- `belongs_to_dataset`: Many-to-one with Dataset
- `involves_subject`: Many-to-one with Subject
- `uses_devices`: Many-to-many with Device
- `follows_protocol`: Many-to-one with Protocol
- `has_quality_metrics`: One-to-many with Quality Assessment

**State Transitions**:
- `planned` → `in_progress` → `completed` → `validated`

### Subject
**Purpose**: Research subjects with biological metadata and species information

**Attributes**:
- `subject_id`: Unique identifier within dataset
- `species`: Taxonomic species (linked to NCBITaxon)
- `strain`: Genetic strain information
- `age`: Age at time of experiment
- `sex`: Biological sex
- `weight`: Subject weight
- `genotype`: Genetic modifications
- `description`: Additional subject information

**Relationships**:
- `participates_in_sessions`: One-to-many with Session
- `has_species_mapping`: One-to-one with Ontology Mapping
- `has_strain_mapping`: One-to-one with Ontology Mapping

**Validation Rules**:
- `species` must map to valid NCBITaxon entry
- `age` must be positive numeric value with units
- `sex` must be from controlled vocabulary

### Device
**Purpose**: Recording and stimulation equipment with specifications

**Attributes**:
- `device_id`: Unique device identifier
- `device_name`: Human-readable name
- `device_type`: Category (electrode, stimulator, etc.)
- `manufacturer`: Device manufacturer
- `model`: Device model number
- `serial_number`: Unique serial identifier
- `specifications`: Technical specifications (JSON)
- `calibration_date`: Last calibration timestamp

**Relationships**:
- `used_in_sessions`: Many-to-many with Session
- `has_device_mapping`: One-to-one with Ontology Mapping
- `has_calibration_history`: One-to-many with Quality Assessment

### Lab
**Purpose**: Research laboratories with protocols and institutional context

**Attributes**:
- `lab_id`: Unique laboratory identifier
- `lab_name`: Laboratory name
- `institution`: Parent institution
- `department`: Department or division
- `principal_investigator`: Lab PI name
- `contact_info`: Contact details
- `research_focus`: Primary research areas

**Relationships**:
- `conducts_sessions`: One-to-many with Session
- `follows_protocols`: One-to-many with Protocol
- `operates_devices`: One-to-many with Device

### Protocol
**Purpose**: Experimental procedures with parameters and validation requirements

**Attributes**:
- `protocol_id`: Unique protocol identifier
- `protocol_name`: Human-readable name
- `version`: Protocol version number
- `description`: Detailed methodology
- `parameters`: Protocol parameters (JSON)
- `validation_rules`: Quality checks (JSON)
- `approval_date`: Ethics/institutional approval date

**Relationships**:
- `used_in_sessions`: One-to-many with Session
- `belongs_to_lab`: Many-to-one with Lab
- `has_versions`: Self-referential for version history

## Semantic Relationship Entities

### Ontology Mapping
**Purpose**: Semantic relationships between NWB concepts and external ontologies

**Attributes**:
- `mapping_id`: Unique mapping identifier
- `source_concept`: NWB-LinkML concept URI
- `target_ontology`: External ontology (NIFSTD, UBERON, etc.)
- `target_concept`: External concept URI
- `mapping_type`: Relationship type (exactMatch, closeMatch, etc.)
- `confidence_score`: Mapping confidence (0.0-1.0)
- `evidence`: Supporting evidence (JSON)
- `creation_date`: Mapping creation timestamp

**Relationships**:
- `maps_dataset_concepts`: Many-to-many with Dataset
- `maps_subject_concepts`: Many-to-many with Subject
- `maps_device_concepts`: Many-to-many with Device
- `supported_by_evidence`: One-to-many with Enrichment Evidence

**Validation Rules**:
- `confidence_score` must be between 0.0 and 1.0
- `target_concept` must be valid URI in specified ontology
- `mapping_type` must be from SKOS vocabulary

### Quality Assessment
**Purpose**: Data quality metrics and validation results

**Attributes**:
- `assessment_id`: Unique assessment identifier
- `assessment_type`: Type of quality check
- `score`: Quality score (0.0-1.0)
- `threshold`: Pass/fail threshold
- `status`: Assessment result (pass/fail/warning)
- `issues`: Specific problems identified (JSON array)
- `assessment_date`: When assessment was performed
- `validator`: Assessment tool/agent identifier

**Relationships**:
- `assesses_dataset`: Many-to-one with Dataset
- `assesses_session`: Many-to-one with Session
- `has_lineage`: One-to-many with Enrichment Evidence

**Validation Rules**:
- `score` must be between 0.0 and 1.0
- `status` must be from controlled vocabulary
- `threshold` must be positive numeric value

### Schema Version
**Purpose**: NWB-LinkML schema versions with generated artifacts

**Attributes**:
- `version_id`: Schema version identifier
- `version_number`: Semantic version (e.g., 2.7.0)
- `release_date`: Schema release date
- `schema_uri`: Schema location URI
- `jsonld_context`: Generated JSON-LD context
- `shacl_shapes`: Generated SHACL shapes
- `owl_ontology`: Generated OWL ontology
- `changelog`: Version changes description

**Relationships**:
- `used_by_datasets`: One-to-many with Dataset
- `supersedes`: Self-referential for version chains
- `generates_artifacts`: One-to-many artifact files

**State Transitions**:
- `draft` → `published` → `deprecated`

### Enrichment Evidence
**Purpose**: Supporting information for metadata suggestions and decisions

**Attributes**:
- `evidence_id`: Unique evidence identifier
- `evidence_type`: Type of evidence (ontology_lookup, pattern_match, etc.)
- `source`: Evidence source identifier
- `confidence`: Evidence confidence score (0.0-1.0)
- `reasoning`: Human-readable explanation
- `raw_data`: Supporting data (JSON)
- `creation_date`: Evidence creation timestamp
- `expiry_date`: Evidence validity period

**Relationships**:
- `supports_mapping`: Many-to-one with Ontology Mapping
- `supports_assessment`: Many-to-one with Quality Assessment
- `chain_of_reasoning`: Many-to-many self-referential

### Project Context
**Purpose**: Research project boundaries and data retention scope

**Attributes**:
- `project_id`: Unique project identifier
- `project_name`: Human-readable project name
- `start_date`: Project start date
- `end_date`: Project completion date (optional)
- `principal_investigator`: Project PI
- `funding_source`: Grant or funding information
- `retention_policy`: Data retention rules (JSON)
- `access_policy`: Access control rules (JSON)

**Relationships**:
- `contains_datasets`: One-to-many with Dataset
- `involves_labs`: Many-to-many with Lab
- `follows_protocols`: Many-to-many with Protocol

## Provenance Model (PROV-O)

### Activity
**Purpose**: Actions performed on knowledge graph data

**Attributes**:
- `activity_id`: Unique activity identifier
- `activity_type`: Type of activity (enrichment, validation, etc.)
- `start_time`: Activity start timestamp
- `end_time`: Activity completion timestamp
- `status`: Activity status (running, completed, failed)
- `agent`: Performing agent identifier

### Entity
**Purpose**: Data entities involved in activities (specializes core entities)

**Attributes**:
- `entity_id`: References core entity ID
- `entity_type`: Core entity type
- `version`: Entity version for change tracking
- `checksum`: Entity state hash

### Agent
**Purpose**: Actors performing activities (humans, software agents)

**Attributes**:
- `agent_id`: Unique agent identifier
- `agent_type`: Type (human, software, service)
- `name`: Agent name or identifier
- `version`: Software version (if applicable)

## Semantic Web Integration

### RDF Namespace Prefixes
```turtle
@prefix nwb: <http://schema.neurodata.io/nwb/> .
@prefix kg: <http://schema.neurodata.io/knowledge-graph/> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
```

### Key RDF Properties
- `nwb:hasSession` - Dataset to Session relationship
- `nwb:hasSubject` - Session to Subject relationship
- `nwb:usesDevice` - Session to Device relationship
- `kg:hasMapping` - Entity to Ontology Mapping
- `kg:hasQuality` - Entity to Quality Assessment
- `prov:wasDerivedFrom` - Provenance relationships
- `prov:wasGeneratedBy` - Creation activities
- `skos:exactMatch` - Ontology concept mappings

## Validation Schema

### SHACL Constraints
- Cardinality constraints for required relationships
- Data type validation for numeric fields
- URI format validation for ontology references
- Range constraints for confidence scores
- Pattern validation for identifiers

### Business Rules
- Datasets must have at least one Session
- Sessions must reference valid Subject and Protocol
- Quality assessments must have scores within valid range
- Ontology mappings require evidence with confidence > 0.5
- Project contexts must have valid retention policies

---

**Status**: Phase 1 Data Model Complete ✓
**Next Step**: Generate API contracts and test scenarios