# Data Model: Knowledge Graph Systems

## Core Entities

### Dataset

**Purpose**: Represents complete experimental datasets with metadata,
provenance, and quality metrics **Attributes**:

- `id`: Unique identifier (URI)
- `title`: Human-readable dataset name
- `description`: Scientific description of the dataset
- `nwb_files`: List of NWB file references (max 100 per clarifications)
- `metadata`: Rich metadata dictionary
- `provenance`: PROV-O provenance graph
- `quality_metrics`: Quality assessment scores
- `created_at`: Timestamp of dataset creation
- `updated_at`: Timestamp of last modification

**Relationships**:

- `contains` → Session (1:many)
- `hasSubject` → Subject (many:many)
- `usedDevice` → Device (many:many)
- `followsProtocol` → Protocol (many:many)
- `associatedLab` → Lab (many:1)

**Validation Rules**:

- Must contain at least one NWB file
- Maximum 100 NWB files per dataset (from clarifications)
- All referenced files must exist and be accessible
- Provenance chain must be complete and valid

### Session

**Purpose**: Individual recording sessions with temporal boundaries and
experimental conditions **Attributes**:

- `id`: Unique session identifier (URI)
- `start_time`: Session start timestamp
- `end_time`: Session end timestamp
- `session_type`: Type of experimental session
- `experimental_conditions`: Structured conditions data
- `metadata`: Session-specific metadata
- `data_files`: Associated NWB data files

**Relationships**:

- `partOf` → Dataset (many:1)
- `involves` → Subject (many:many)
- `uses` → Device (many:many)
- `implements` → Protocol (many:1)

**Validation Rules**:

- End time must be after start time
- Must be associated with exactly one dataset
- Must have at least one associated subject

### Subject

**Purpose**: Research subjects with biological characteristics, strain
information, and species mappings **Attributes**:

- `id`: Unique subject identifier (URI)
- `species`: Species information with ontology mapping
- `strain`: Strain information for species mapping enrichment
- `genotype`: Genetic characteristics
- `age`: Subject age at experiment time
- `sex`: Biological sex
- `weight`: Subject weight
- `biological_metadata`: Rich biological characteristics

**Relationships**:

- `participatesIn` → Session (many:many)
- `memberOf` → Dataset (many:many)
- `hasSpecies` → Species (NCBITaxon ontology)

**Validation Rules**:

- Species must map to valid NCBITaxon entry
- Strain-to-species mappings must be consistent
- Age and weight must be positive values

### Device

**Purpose**: Recording and stimulation devices with specifications and
calibration data **Attributes**:

- `id`: Unique device identifier (URI)
- `name`: Device name
- `manufacturer`: Device manufacturer
- `model`: Device model number
- `specifications`: Technical specifications
- `calibration_data`: Calibration information
- `serial_number`: Device serial number

**Relationships**:

- `usedIn` → Session (many:many)
- `ownedBy` → Lab (many:1)

**Validation Rules**:

- Calibration data must be current and valid
- Specifications must include required technical parameters

### Lab

**Purpose**: Laboratory entities with protocols, personnel, and institutional
affiliations **Attributes**:

- `id`: Unique lab identifier (URI)
- `name`: Laboratory name
- `institution`: Institutional affiliation
- `principal_investigator`: PI information
- `contact_information`: Lab contact details
- `research_focus`: Scientific research areas

**Relationships**:

- `owns` → Device (1:many)
- `conducts` → Dataset (1:many)
- `develops` → Protocol (1:many)

**Validation Rules**:

- Must have valid institutional affiliation
- Contact information must be current

### Protocol

**Purpose**: Experimental protocols with procedures, parameters, and validation
criteria **Attributes**:

- `id`: Unique protocol identifier (URI)
- `name`: Protocol name
- `version`: Protocol version
- `description`: Detailed protocol description
- `parameters`: Protocol parameters and settings
- `validation_criteria`: Success criteria for protocol execution
- `references`: Scientific references

**Relationships**:

- `implementedIn` → Session (1:many)
- `developedBy` → Lab (many:1)

**Validation Rules**:

- Version must follow semantic versioning
- Validation criteria must be measurable

### KnowledgeGraph

**Purpose**: Semantic representation with RDF triples, ontology mappings, and
SPARQL endpoints **Attributes**:

- `id`: Knowledge graph identifier (URI)
- `schema_version`: NWB-LinkML schema version
- `ontology_mappings`: Mappings to external ontologies
- `triple_count`: Number of RDF triples
- `last_updated`: Last update timestamp
- `sparql_endpoint`: SPARQL query endpoint URL

**Relationships**:

- `describes` → Dataset (1:many)
- `uses` → SchemaVersion (many:1)
- `integrates` → ExternalOntology (many:many)

**Validation Rules**:

- Must conform to W3C RDF standards
- SPARQL endpoint must be accessible
- Schema version must be valid and tracked

### EnrichmentSuggestion

**Purpose**: Metadata enhancement proposals with confidence scores and evidence
chains **Attributes**:

- `id`: Unique suggestion identifier (URI)
- `target_entity`: Entity being enriched
- `suggested_value`: Proposed metadata value
- `confidence_score`: Confidence level (0-1)
- `evidence_chain`: Supporting evidence
- `source`: Knowledge source for suggestion
- `review_status`: Human review status (pending/approved/rejected)

**Relationships**:

- `enriches` → Entity (many:1)
- `basedOn` → ExternalSource (many:many)
- `reviewedBy` → Human (many:1)

**Validation Rules**:

- Confidence score must be between 0 and 1
- All suggestions require human review (from clarifications)
- Evidence chain must be traceable and complete

### ValidationReport

**Purpose**: Quality assessment results with issue identification and
recommendation **Attributes**:

- `id`: Unique report identifier (URI)
- `target`: Validated entity or data
- `validation_type`: Type of validation performed
- `status`: Overall validation status (pass/fail/warning)
- `issues`: List of identified issues
- `recommendations`: Suggested improvements
- `timestamp`: Validation execution time

**Relationships**:

- `validates` → Entity (many:1)
- `uses` → ValidationRule (many:many)

**Validation Rules**:

- Issues must be categorized and prioritized
- Recommendations must be actionable
- Validation type must be supported

### SchemaVersion

**Purpose**: NWB-LinkML schema versions with artifact generation metadata and
compatibility tracking **Attributes**:

- `version`: Schema version identifier
- `release_date`: Schema release date
- `artifacts`: Generated semantic web artifacts
- `compatibility`: Backward compatibility information
- `changes`: Change log from previous version

**Relationships**:

- `generates` → SemanticArtifact (1:many)
- `succeeds` → SchemaVersion (many:1)

**Validation Rules**:

- Version must follow semantic versioning
- Artifacts must be regenerated when schema changes
- Compatibility information must be accurate

### MCPTool

**Purpose**: Model Context Protocol interfaces for agent integration with
structured response formats **Attributes**:

- `name`: Tool name
- `description`: Tool functionality description
- `input_schema`: Expected input format
- `output_schema`: Response format specification
- `endpoint`: Tool execution endpoint

**Relationships**:

- `exposes` → KnowledgeGraphFunction (1:1)
- `supports` → Agent (many:many)

**Validation Rules**:

- Input/output schemas must be valid JSON Schema
- Endpoints must be accessible and responsive
- Responses must conform to MCP protocol standards

## State Transitions

### Enrichment Workflow States

1. **Pending**: Suggestion generated, awaiting review
2. **Under Review**: Human reviewer examining suggestion
3. **Approved**: Suggestion accepted and applied
4. **Rejected**: Suggestion declined with rationale
5. **Conflict**: Multiple conflicting suggestions require resolution

### Quality Assurance States

1. **Unvalidated**: Data not yet quality checked
2. **Validating**: Quality assessment in progress
3. **Passed**: Quality requirements met
4. **Failed**: Quality issues identified, requires correction
5. **Quarantined**: Data isolated pending expert review

### Schema Synchronization States

1. **Current**: Using latest schema version
2. **Outdated**: Schema update available
3. **Regenerating**: Artifacts being updated
4. **Synchronized**: All artifacts current with schema
5. **Conflict**: Schema changes incompatible with existing data

## Ontology Mappings

### Core Neuroscience Ontologies

- **NIFSTD**: Neuroscience Information Framework Standard ontology
- **UBERON**: Anatomical entity ontology
- **CHEBI**: Chemical entities of biological interest
- **NCBITaxon**: Taxonomic classification

### Mapping Relationships

- **owl:equivalentClass**: Direct concept equivalence
- **rdfs:subClassOf**: Hierarchical relationships
- **skos:closeMatch**: Approximate concept matching
- **custom:confidenceScore**: Mapping confidence level

## Validation Constraints

### Constitutional Compliance

- All entities must have valid LinkML schema representation
- RDF generation must conform to W3C standards
- SHACL shapes must validate structural integrity
- Provenance tracking must use PROV-O ontology

### Performance Constraints

- Query execution must complete within 30 seconds
- Support for 1-10 concurrent users
- Efficient handling of up to 100 NWB files per dataset
- Optimized SPARQL query patterns for common operations
