# Knowledge Graph Systems Design

## Overview

This design document outlines the knowledge graph systems that provide semantic enrichment, metadata validation, and relationship modeling for the agentic neurodata conversion pipeline. The knowledge graph system maintains a rich semantic model of neuroscience entities, relationships, and provenance while supporting automated metadata enrichment and complex validation queries.

## Architecture

### High-Level Architecture

```
Knowledge Graph Systems
├── Core Knowledge Graph Engine
│   ├── RDF Store (Apache Jena/Blazegraph)
│   ├── SPARQL Query Engine
│   └── Inference Engine
├── Metadata Enrichment Service
│   ├── Entity Resolution
│   ├── Relationship Inference
│   └── Confidence Scoring
├── Domain Knowledge Integration
│   ├── Ontology Management (NIFSTD, UBERON)
│   ├── Controlled Vocabularies
│   └── External Knowledge Sources
└── API and Integration Layer
    ├── REST API for MCP Server
    ├── SPARQL Endpoint
    └── Export Services (TTL, JSON-LD, N-Triples)
```

### Data Flow

```
Metadata Input → Entity Resolution → Relationship Inference → Confidence Scoring → Enriched Metadata
                      ↓
Domain Ontologies → Knowledge Graph → SPARQL Queries → Validation Results
                      ↓
Provenance Tracking → RDF Store → Export Services → Multiple Formats
```## C
ore Components

### 1. Knowledge Graph Engine

#### RDF Store
```python
# src/agentic_converter/knowledge_graph/rdf_store.py
from typing import Dict, Any, List, Optional, Union
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.plugins.stores import sparqlstore
import logging

# Define namespaces
NEURO = Namespace("http://neuroscience.org/ontology/")
NWB = Namespace("http://nwb.org/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")

class RDFStoreManager:
    """Manages RDF store operations for knowledge graph."""
    
    def __init__(self, store_type: str = "memory", store_config: Optional[Dict] = None):
        self.store_type = store_type
        self.store_config = store_config or {}
        self.graph = self._initialize_store()
        self.logger = logging.getLogger(__name__)
        
        # Bind common namespaces
        self._bind_namespaces()
    
    def _initialize_store(self) -> Graph:
        """Initialize RDF store based on configuration."""
        if self.store_type == "memory":
            return Graph()
        elif self.store_type == "sparql":
            endpoint = self.store_config.get("endpoint", "http://localhost:3030/dataset")
            return Graph(store=sparqlstore.SPARQLStore(endpoint))
        else:
            # Default to memory store
            return Graph()
    
    def _bind_namespaces(self):
        """Bind common namespaces to the graph."""
        self.graph.bind("neuro", NEURO)
        self.graph.bind("nwb", NWB)
        self.graph.bind("prov", PROV)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
    
    def add_triple(self, subject: Union[URIRef, str], predicate: Union[URIRef, str], 
                   obj: Union[URIRef, Literal, str]):
        """Add a triple to the knowledge graph."""
        # Convert strings to URIRefs if needed
        if isinstance(subject, str):
            subject = URIRef(subject)
        if isinstance(predicate, str):
            predicate = URIRef(predicate)
        if isinstance(obj, str) and obj.startswith("http"):
            obj = URIRef(obj)
        elif isinstance(obj, str):
            obj = Literal(obj)
        
        self.graph.add((subject, predicate, obj))
    
    def query(self, sparql_query: str) -> List[Dict[str, Any]]:
        """Execute SPARQL query and return results."""
        try:
            results = self.graph.query(sparql_query)
            return [dict(row.asdict()) for row in results]
        except Exception as e:
            self.logger.error(f"SPARQL query failed: {e}")
            return []
    
    def serialize(self, format: str = "turtle") -> str:
        """Serialize graph to specified format."""
        return self.graph.serialize(format=format)
    
    def load_ontology(self, ontology_path: str, format: str = "turtle"):
        """Load ontology into the knowledge graph."""
        try:
            self.graph.parse(ontology_path, format=format)
            self.logger.info(f"Loaded ontology from {ontology_path}")
        except Exception as e:
            self.logger.error(f"Failed to load ontology: {e}")

class EntityManager:
    """Manages entities in the knowledge graph."""
    
    def __init__(self, rdf_store: RDFStoreManager):
        self.store = rdf_store
        self.logger = logging.getLogger(__name__)
    
    def create_dataset_entity(self, dataset_id: str, metadata: Dict[str, Any]) -> URIRef:
        """Create dataset entity in knowledge graph."""
        dataset_uri = NEURO[f"dataset_{dataset_id}"]
        
        # Add basic type information
        self.store.add_triple(dataset_uri, RDF.type, NEURO.Dataset)
        self.store.add_triple(dataset_uri, RDFS.label, Literal(dataset_id))
        
        # Add metadata properties
        if "identifier" in metadata:
            self.store.add_triple(dataset_uri, NEURO.hasIdentifier, Literal(metadata["identifier"]))
        
        if "session_description" in metadata:
            self.store.add_triple(dataset_uri, NEURO.hasDescription, Literal(metadata["session_description"]))
        
        if "experimenter" in metadata:
            experimenter_uri = self._create_person_entity(metadata["experimenter"])
            self.store.add_triple(dataset_uri, NEURO.hasExperimenter, experimenter_uri)
        
        if "lab" in metadata:
            lab_uri = self._create_lab_entity(metadata["lab"])
            self.store.add_triple(dataset_uri, NEURO.conductedBy, lab_uri)
        
        return dataset_uri
    
    def create_subject_entity(self, subject_id: str, metadata: Dict[str, Any]) -> URIRef:
        """Create subject entity in knowledge graph."""
        subject_uri = NEURO[f"subject_{subject_id}"]
        
        self.store.add_triple(subject_uri, RDF.type, NEURO.Subject)
        self.store.add_triple(subject_uri, RDFS.label, Literal(subject_id))
        
        # Add subject-specific metadata
        if "species" in metadata:
            species_uri = self._resolve_species(metadata["species"])
            self.store.add_triple(subject_uri, NEURO.hasSpecies, species_uri)
        
        if "strain" in metadata:
            strain_uri = self._resolve_strain(metadata["strain"])
            self.store.add_triple(subject_uri, NEURO.hasStrain, strain_uri)
        
        if "age" in metadata:
            self.store.add_triple(subject_uri, NEURO.hasAge, Literal(metadata["age"]))
        
        if "sex" in metadata:
            self.store.add_triple(subject_uri, NEURO.hasSex, Literal(metadata["sex"]))
        
        return subject_uri
    
    def create_device_entity(self, device_name: str, metadata: Dict[str, Any]) -> URIRef:
        """Create device entity in knowledge graph."""
        device_uri = NEURO[f"device_{device_name.replace(' ', '_')}"]
        
        self.store.add_triple(device_uri, RDF.type, NEURO.Device)
        self.store.add_triple(device_uri, RDFS.label, Literal(device_name))
        
        if "description" in metadata:
            self.store.add_triple(device_uri, NEURO.hasDescription, Literal(metadata["description"]))
        
        if "manufacturer" in metadata:
            self.store.add_triple(device_uri, NEURO.hasManufacturer, Literal(metadata["manufacturer"]))
        
        return device_uri
    
    def _create_person_entity(self, person_name: str) -> URIRef:
        """Create person entity."""
        person_uri = NEURO[f"person_{person_name.replace(' ', '_')}"]
        self.store.add_triple(person_uri, RDF.type, NEURO.Person)
        self.store.add_triple(person_uri, RDFS.label, Literal(person_name))
        return person_uri
    
    def _create_lab_entity(self, lab_name: str) -> URIRef:
        """Create lab entity."""
        lab_uri = NEURO[f"lab_{lab_name.replace(' ', '_')}"]
        self.store.add_triple(lab_uri, RDF.type, NEURO.Lab)
        self.store.add_triple(lab_uri, RDFS.label, Literal(lab_name))
        return lab_uri
    
    def _resolve_species(self, species_name: str) -> URIRef:
        """Resolve species to standard ontology URI."""
        # This would integrate with external ontologies like NCBI Taxonomy
        species_mapping = {
            "Mus musculus": "http://purl.obolibrary.org/obo/NCBITaxon_10090",
            "Rattus norvegicus": "http://purl.obolibrary.org/obo/NCBITaxon_10116",
            "Homo sapiens": "http://purl.obolibrary.org/obo/NCBITaxon_9606"
        }
        
        return URIRef(species_mapping.get(species_name, NEURO[f"species_{species_name.replace(' ', '_')}"]))
    
    def _resolve_strain(self, strain_name: str) -> URIRef:
        """Resolve strain to standard ontology URI."""
        # This would integrate with strain databases
        return NEURO[f"strain_{strain_name.replace('/', '_').replace('-', '_')}"]
```###
 2. Metadata Enrichment Service

#### Entity Resolution and Relationship Inference
```python
# src/agentic_converter/knowledge_graph/enrichment.py
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

@dataclass
class EnrichmentResult:
    """Result of metadata enrichment."""
    field: str
    original_value: Any
    enriched_value: Any
    confidence: float
    source: str
    reasoning: str

class MetadataEnricher:
    """Enriches metadata using knowledge graph and external sources."""
    
    def __init__(self, rdf_store: RDFStoreManager):
        self.store = rdf_store
        self.logger = logging.getLogger(__name__)
        self.domain_knowledge = self._load_domain_knowledge()
    
    def enrich_metadata(self, metadata: Dict[str, Any]) -> List[EnrichmentResult]:
        """Enrich metadata with knowledge graph information."""
        enrichments = []
        
        # Species-strain consistency
        if "strain" in metadata and "species" not in metadata:
            species_enrichment = self._infer_species_from_strain(metadata["strain"])
            if species_enrichment:
                enrichments.append(species_enrichment)
        
        # Device capabilities
        if "device" in metadata:
            device_enrichments = self._enrich_device_information(metadata["device"])
            enrichments.extend(device_enrichments)
        
        # Protocol inference
        if "experimental_setup" in metadata:
            protocol_enrichments = self._infer_protocol(metadata["experimental_setup"])
            enrichments.extend(protocol_enrichments)
        
        # Lab information
        if "experimenter" in metadata and "lab" not in metadata:
            lab_enrichment = self._infer_lab_from_experimenter(metadata["experimenter"])
            if lab_enrichment:
                enrichments.append(lab_enrichment)
        
        return enrichments
    
    def _infer_species_from_strain(self, strain: str) -> Optional[EnrichmentResult]:
        """Infer species from strain information."""
        strain_species_mapping = {
            "C57BL/6J": "Mus musculus",
            "BALB/c": "Mus musculus", 
            "DBA/2J": "Mus musculus",
            "Wistar": "Rattus norvegicus",
            "Sprague-Dawley": "Rattus norvegicus",
            "Long-Evans": "Rattus norvegicus"
        }
        
        species = strain_species_mapping.get(strain)
        if species:
            return EnrichmentResult(
                field="species",
                original_value=None,
                enriched_value=species,
                confidence=0.95,
                source="strain_species_mapping",
                reasoning=f"Species inferred from strain {strain}"
            )
        
        return None
    
    def _enrich_device_information(self, device_name: str) -> List[EnrichmentResult]:
        """Enrich device information with capabilities and specifications."""
        enrichments = []
        
        # Query knowledge graph for device information
        query = f"""
        SELECT ?property ?value WHERE {{
            ?device rdfs:label "{device_name}" .
            ?device ?property ?value .
        }}
        """
        
        results = self.store.query(query)
        
        for result in results:
            property_name = str(result["property"]).split("/")[-1]
            if property_name not in ["type", "label"]:
                enrichments.append(EnrichmentResult(
                    field=f"device_{property_name}",
                    original_value=None,
                    enriched_value=str(result["value"]),
                    confidence=0.8,
                    source="knowledge_graph",
                    reasoning=f"Device property from knowledge graph"
                ))
        
        return enrichments
    
    def _infer_protocol(self, experimental_setup: Dict[str, Any]) -> List[EnrichmentResult]:
        """Infer experimental protocol from setup information."""
        enrichments = []
        
        # Simple protocol inference based on setup
        if "recording_type" in experimental_setup:
            recording_type = experimental_setup["recording_type"]
            
            if "extracellular" in recording_type.lower():
                enrichments.append(EnrichmentResult(
                    field="protocol_type",
                    original_value=None,
                    enriched_value="extracellular_recording",
                    confidence=0.9,
                    source="protocol_inference",
                    reasoning="Inferred from extracellular recording type"
                ))
        
        return enrichments
    
    def _infer_lab_from_experimenter(self, experimenter: str) -> Optional[EnrichmentResult]:
        """Infer lab from experimenter information."""
        # This would query external databases or internal mappings
        # For now, return None as this requires external data
        return None
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """Load domain-specific knowledge for enrichment."""
        return {
            "strain_species": {
                "C57BL/6J": "Mus musculus",
                "BALB/c": "Mus musculus",
                "Wistar": "Rattus norvegicus"
            },
            "device_capabilities": {
                "Neuropixels": ["high_density_recording", "silicon_probe"],
                "Open Ephys": ["multichannel_recording", "real_time_processing"]
            }
        }

class ConfidenceScorer:
    """Assigns confidence scores to enrichments and inferences."""
    
    def __init__(self):
        self.scoring_rules = self._initialize_scoring_rules()
    
    def score_enrichment(self, enrichment: EnrichmentResult) -> float:
        """Score the confidence of an enrichment."""
        base_confidence = enrichment.confidence
        
        # Adjust based on source reliability
        source_multipliers = {
            "strain_species_mapping": 1.0,
            "knowledge_graph": 0.9,
            "external_database": 0.85,
            "inference": 0.7,
            "ai_suggestion": 0.6
        }
        
        multiplier = source_multipliers.get(enrichment.source, 0.5)
        adjusted_confidence = base_confidence * multiplier
        
        return min(1.0, adjusted_confidence)
    
    def _initialize_scoring_rules(self) -> Dict[str, float]:
        """Initialize confidence scoring rules."""
        return {
            "exact_match": 1.0,
            "fuzzy_match": 0.8,
            "inference": 0.7,
            "ai_suggestion": 0.6,
            "default": 0.5
        }

### 3. SPARQL Query Engine

class SPARQLQueryEngine:
    """Handles SPARQL queries for validation and enrichment."""
    
    def __init__(self, rdf_store: RDFStoreManager):
        self.store = rdf_store
        self.logger = logging.getLogger(__name__)
    
    def validate_metadata_consistency(self, dataset_uri: str) -> List[Dict[str, Any]]:
        """Validate metadata consistency using SPARQL queries."""
        validation_results = []
        
        # Check for missing required relationships
        missing_sessions_query = f"""
        SELECT ?dataset WHERE {{
            BIND(<{dataset_uri}> AS ?dataset)
            ?dataset a neuro:Dataset .
            FILTER NOT EXISTS {{ ?dataset neuro:hasSession ?session }}
        }}
        """
        
        results = self.store.query(missing_sessions_query)
        if results:
            validation_results.append({
                "type": "missing_relationship",
                "severity": "warning",
                "message": "Dataset has no associated sessions",
                "query": missing_sessions_query
            })
        
        # Check species-strain consistency
        species_strain_query = f"""
        SELECT ?subject ?strain ?species ?expectedSpecies WHERE {{
            ?dataset a neuro:Dataset .
            ?dataset neuro:hasSession ?session .
            ?session neuro:hasSubject ?subject .
            ?subject neuro:hasStrain ?strain .
            ?subject neuro:hasSpecies ?species .
            ?strain neuro:belongsToSpecies ?expectedSpecies .
            FILTER (?species != ?expectedSpecies)
        }}
        """
        
        results = self.store.query(species_strain_query)
        for result in results:
            validation_results.append({
                "type": "inconsistency",
                "severity": "error",
                "message": f"Species-strain mismatch for subject {result['subject']}",
                "details": {
                    "declared_species": str(result["species"]),
                    "expected_species": str(result["expectedSpecies"]),
                    "strain": str(result["strain"])
                }
            })
        
        return validation_results
    
    def find_similar_experiments(self, dataset_uri: str, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Find similar experiments based on metadata."""
        similarity_query = f"""
        SELECT ?similarDataset ?similarity WHERE {{
            BIND(<{dataset_uri}> AS ?dataset)
            ?dataset neuro:hasSession ?session .
            ?session neuro:hasSubject ?subject .
            ?subject neuro:hasSpecies ?species .
            
            ?similarDataset neuro:hasSession ?similarSession .
            ?similarSession neuro:hasSubject ?similarSubject .
            ?similarSubject neuro:hasSpecies ?species .
            
            FILTER (?dataset != ?similarDataset)
            
            # Calculate similarity score (simplified)
            BIND(1.0 AS ?similarity)
        }}
        """
        
        results = self.store.query(similarity_query)
        similar_experiments = []
        
        for result in results:
            if float(result.get("similarity", 0)) >= similarity_threshold:
                similar_experiments.append({
                    "dataset": str(result["similarDataset"]),
                    "similarity": float(result["similarity"])
                })
        
        return similar_experiments
    
    def suggest_missing_metadata(self, dataset_uri: str) -> List[Dict[str, Any]]:
        """Suggest missing metadata based on similar experiments."""
        suggestions_query = f"""
        SELECT ?property ?value (COUNT(*) AS ?frequency) WHERE {{
            BIND(<{dataset_uri}> AS ?dataset)
            ?dataset neuro:hasSession ?session .
            ?session neuro:hasSubject ?subject .
            ?subject neuro:hasSpecies ?species .
            
            ?similarDataset neuro:hasSession ?similarSession .
            ?similarSession neuro:hasSubject ?similarSubject .
            ?similarSubject neuro:hasSpecies ?species .
            ?similarSession ?property ?value .
            
            FILTER (?dataset != ?similarDataset)
            FILTER NOT EXISTS {{ ?session ?property ?value }}
        }} 
        GROUP BY ?property ?value 
        ORDER BY DESC(?frequency)
        """
        
        results = self.store.query(suggestions_query)
        suggestions = []
        
        for result in results:
            suggestions.append({
                "property": str(result["property"]).split("/")[-1],
                "suggested_value": str(result["value"]),
                "frequency": int(result["frequency"]),
                "confidence": min(1.0, int(result["frequency"]) / 10.0)
            })
        
        return suggestions[:10]  # Return top 10 suggestions
```### 4. 
Integration with MCP Server

#### MCP Tools for Knowledge Graph Operations
```python
# src/agentic_converter/mcp_server/tools/knowledge_graph.py
from ..server import mcp
from ...knowledge_graph.rdf_store import RDFStoreManager, EntityManager
from ...knowledge_graph.enrichment import MetadataEnricher, ConfidenceScorer
from typing import Dict, Any, Optional, List

@mcp.tool(
    name="generate_knowledge_graph",
    description="Generate knowledge graph from NWB file and metadata"
)
async def generate_knowledge_graph(
    nwb_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    output_formats: List[str] = ["turtle", "json-ld"],
    output_dir: str = "knowledge_graph_outputs",
    server=None
) -> Dict[str, Any]:
    """Generate knowledge graph from NWB file and metadata."""
    
    try:
        # Initialize knowledge graph components
        rdf_store = RDFStoreManager()
        entity_manager = EntityManager(rdf_store)
        
        # Extract metadata from NWB file if not provided
        if metadata is None:
            metadata = await _extract_nwb_metadata(nwb_path)
        
        # Create entities in knowledge graph
        dataset_uri = entity_manager.create_dataset_entity(
            dataset_id=metadata.get("identifier", "unknown"),
            metadata=metadata
        )
        
        # Create subject entity if present
        if "subject" in metadata:
            subject_uri = entity_manager.create_subject_entity(
                subject_id=metadata["subject"].get("subject_id", "unknown"),
                metadata=metadata["subject"]
            )
            rdf_store.add_triple(dataset_uri, NEURO.hasSubject, subject_uri)
        
        # Create device entities
        if "devices" in metadata:
            for device_name, device_info in metadata["devices"].items():
                device_uri = entity_manager.create_device_entity(device_name, device_info)
                rdf_store.add_triple(dataset_uri, NEURO.usesDevice, device_uri)
        
        # Generate outputs in requested formats
        outputs = {}
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for format_name in output_formats:
            if format_name == "turtle":
                ttl_content = rdf_store.serialize("turtle")
                ttl_path = output_path / "knowledge_graph.ttl"
                ttl_path.write_text(ttl_content)
                outputs["turtle"] = str(ttl_path)
            
            elif format_name == "json-ld":
                jsonld_content = rdf_store.serialize("json-ld")
                jsonld_path = output_path / "knowledge_graph.jsonld"
                jsonld_path.write_text(jsonld_content)
                outputs["json-ld"] = str(jsonld_path)
            
            elif format_name == "n-triples":
                nt_content = rdf_store.serialize("nt")
                nt_path = output_path / "knowledge_graph.nt"
                nt_path.write_text(nt_content)
                outputs["n-triples"] = str(nt_path)
        
        # Generate summary statistics
        entity_count = len(list(rdf_store.graph.subjects()))
        relationship_count = len(list(rdf_store.graph))
        
        return {
            "status": "success",
            "outputs": outputs,
            "statistics": {
                "entity_count": entity_count,
                "relationship_count": relationship_count,
                "formats_generated": output_formats
            },
            "dataset_uri": str(dataset_uri)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool(
    name="enrich_metadata",
    description="Enrich metadata using knowledge graph and external sources"
)
async def enrich_metadata(
    metadata: Dict[str, Any],
    confidence_threshold: float = 0.7,
    max_suggestions: int = 10,
    server=None
) -> Dict[str, Any]:
    """Enrich metadata using knowledge graph information."""
    
    try:
        # Initialize enrichment components
        rdf_store = RDFStoreManager()
        enricher = MetadataEnricher(rdf_store)
        scorer = ConfidenceScorer()
        
        # Perform enrichment
        enrichments = enricher.enrich_metadata(metadata)
        
        # Filter by confidence threshold
        high_confidence_enrichments = []
        suggestions = []
        
        for enrichment in enrichments:
            confidence = scorer.score_enrichment(enrichment)
            enrichment_data = {
                "field": enrichment.field,
                "original_value": enrichment.original_value,
                "enriched_value": enrichment.enriched_value,
                "confidence": confidence,
                "source": enrichment.source,
                "reasoning": enrichment.reasoning
            }
            
            if confidence >= confidence_threshold:
                high_confidence_enrichments.append(enrichment_data)
            else:
                suggestions.append(enrichment_data)
        
        # Limit suggestions
        suggestions = suggestions[:max_suggestions]
        
        # Apply high-confidence enrichments to metadata
        enriched_metadata = metadata.copy()
        for enrichment in high_confidence_enrichments:
            enriched_metadata[enrichment["field"]] = enrichment["enriched_value"]
        
        return {
            "status": "success",
            "enriched_metadata": enriched_metadata,
            "applied_enrichments": high_confidence_enrichments,
            "suggestions": suggestions,
            "enrichment_summary": {
                "total_enrichments": len(enrichments),
                "applied_count": len(high_confidence_enrichments),
                "suggestion_count": len(suggestions)
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool(
    name="validate_metadata_consistency",
    description="Validate metadata consistency using knowledge graph rules"
)
async def validate_metadata_consistency(
    metadata: Dict[str, Any],
    validation_rules: Optional[List[str]] = None,
    server=None
) -> Dict[str, Any]:
    """Validate metadata consistency using knowledge graph."""
    
    try:
        # Initialize components
        rdf_store = RDFStoreManager()
        entity_manager = EntityManager(rdf_store)
        query_engine = SPARQLQueryEngine(rdf_store)
        
        # Create temporary entities for validation
        dataset_uri = entity_manager.create_dataset_entity(
            dataset_id=metadata.get("identifier", "temp"),
            metadata=metadata
        )
        
        # Run validation queries
        validation_results = query_engine.validate_metadata_consistency(str(dataset_uri))
        
        # Categorize results by severity
        errors = [r for r in validation_results if r["severity"] == "error"]
        warnings = [r for r in validation_results if r["severity"] == "warning"]
        info = [r for r in validation_results if r["severity"] == "info"]
        
        # Determine overall validation status
        is_valid = len(errors) == 0
        
        return {
            "status": "success",
            "is_valid": is_valid,
            "validation_results": {
                "errors": errors,
                "warnings": warnings,
                "info": info
            },
            "summary": {
                "total_issues": len(validation_results),
                "error_count": len(errors),
                "warning_count": len(warnings),
                "info_count": len(info)
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool(
    name="query_knowledge_graph",
    description="Execute SPARQL queries against the knowledge graph"
)
async def query_knowledge_graph(
    sparql_query: str,
    output_format: str = "json",
    server=None
) -> Dict[str, Any]:
    """Execute SPARQL query against knowledge graph."""
    
    try:
        rdf_store = RDFStoreManager()
        
        # Execute query
        results = rdf_store.query(sparql_query)
        
        return {
            "status": "success",
            "query": sparql_query,
            "results": results,
            "result_count": len(results),
            "output_format": output_format
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "query": sparql_query
        }

async def _extract_nwb_metadata(nwb_path: str) -> Dict[str, Any]:
    """Extract metadata from NWB file."""
    try:
        import pynwb
        
        with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
            nwbfile = io.read()
            
            metadata = {
                "identifier": nwbfile.identifier,
                "session_description": nwbfile.session_description,
                "session_start_time": nwbfile.session_start_time.isoformat() if nwbfile.session_start_time else None,
                "experimenter": list(nwbfile.experimenter) if nwbfile.experimenter else [],
                "lab": nwbfile.lab,
                "institution": nwbfile.institution
            }
            
            # Extract subject information
            if nwbfile.subject:
                metadata["subject"] = {
                    "subject_id": nwbfile.subject.subject_id,
                    "species": nwbfile.subject.species,
                    "strain": getattr(nwbfile.subject, 'strain', None),
                    "age": nwbfile.subject.age,
                    "sex": nwbfile.subject.sex
                }
            
            # Extract device information
            if nwbfile.devices:
                metadata["devices"] = {}
                for device_name, device in nwbfile.devices.items():
                    metadata["devices"][device_name] = {
                        "description": device.description,
                        "manufacturer": getattr(device, 'manufacturer', None)
                    }
            
            return metadata
            
    except Exception as e:
        raise ValueError(f"Failed to extract metadata from NWB file: {e}")

### 5. Export and Serialization Services

class KnowledgeGraphExporter:
    """Export knowledge graph in various formats."""
    
    def __init__(self, rdf_store: RDFStoreManager):
        self.store = rdf_store
        self.logger = logging.getLogger(__name__)
    
    def export_summary(self) -> Dict[str, Any]:
        """Export human-readable summary of knowledge graph."""
        
        # Count entities by type
        entity_counts = {}
        type_query = """
        SELECT ?type (COUNT(?entity) AS ?count) WHERE {
            ?entity a ?type .
        } GROUP BY ?type
        """
        
        results = self.store.query(type_query)
        for result in results:
            entity_type = str(result["type"]).split("/")[-1]
            entity_counts[entity_type] = int(result["count"])
        
        # Count relationships
        relationship_count = len(list(self.store.graph))
        
        # Get sample entities
        sample_entities = []
        sample_query = """
        SELECT ?entity ?type ?label WHERE {
            ?entity a ?type .
            OPTIONAL { ?entity rdfs:label ?label }
        } LIMIT 10
        """
        
        results = self.store.query(sample_query)
        for result in results:
            sample_entities.append({
                "uri": str(result["entity"]),
                "type": str(result["type"]).split("/")[-1],
                "label": str(result.get("label", ""))
            })
        
        return {
            "entity_counts": entity_counts,
            "total_entities": sum(entity_counts.values()),
            "total_relationships": relationship_count,
            "sample_entities": sample_entities,
            "namespaces": dict(self.store.graph.namespaces())
        }
    
    def export_provenance_summary(self) -> Dict[str, Any]:
        """Export provenance information summary."""
        
        provenance_query = """
        SELECT ?entity ?source ?confidence WHERE {
            ?entity prov:wasGeneratedBy ?activity .
            ?activity prov:wasAssociatedWith ?source .
            OPTIONAL { ?activity prov:confidence ?confidence }
        }
        """
        
        results = self.store.query(provenance_query)
        
        source_counts = {}
        confidence_distribution = []
        
        for result in results:
            source = str(result["source"]).split("/")[-1]
            source_counts[source] = source_counts.get(source, 0) + 1
            
            if result.get("confidence"):
                confidence_distribution.append(float(result["confidence"]))
        
        avg_confidence = sum(confidence_distribution) / len(confidence_distribution) if confidence_distribution else 0
        
        return {
            "source_distribution": source_counts,
            "average_confidence": avg_confidence,
            "confidence_distribution": {
                "min": min(confidence_distribution) if confidence_distribution else 0,
                "max": max(confidence_distribution) if confidence_distribution else 0,
                "count": len(confidence_distribution)
            }
        }
```

This comprehensive knowledge graph systems design provides semantic enrichment, metadata validation, and relationship modeling capabilities that integrate seamlessly with the MCP server architecture while maintaining complete provenance and confidence tracking.