"""RDF store management and entity creation for knowledge graph."""

import logging
from typing import Any, Optional, Union

from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.plugins.stores import sparqlstore

# Define namespaces
NEURO = Namespace("http://neuroscience.org/ontology/")
NWB = Namespace("http://nwb.org/ontology/")
PROV = Namespace("http://www.w3.org/ns/prov#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")


class RDFStoreManager:
    """Manages RDF store operations for knowledge graph."""

    def __init__(self, store_type: str = "memory", store_config: Optional[dict] = None):
        """
        Initialize RDF store manager.

        Args:
            store_type: Type of store ("memory", "sparql")
            store_config: Configuration dictionary for the store
        """
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
            endpoint = self.store_config.get(
                "endpoint", "http://localhost:3030/dataset"
            )
            return Graph(store=sparqlstore.SPARQLStore(endpoint))
        else:
            # Default to memory store
            self.logger.warning(
                f"Unknown store type {self.store_type}, using memory store"
            )
            return Graph()

    def _bind_namespaces(self):
        """Bind common namespaces to the graph."""
        self.graph.bind("neuro", NEURO)
        self.graph.bind("nwb", NWB)
        self.graph.bind("prov", PROV)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)

    def add_triple(
        self,
        subject: Union[URIRef, str],
        predicate: Union[URIRef, str],
        obj: Union[URIRef, Literal, str],
    ) -> None:
        """
        Add a triple to the knowledge graph.

        Args:
            subject: Subject URI or string
            predicate: Predicate URI or string
            obj: Object URI, Literal, or string
        """
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

    def query(self, sparql_query: str) -> list[dict[str, Any]]:
        """
        Execute SPARQL query and return results.

        Args:
            sparql_query: SPARQL query string

        Returns:
            List of result dictionaries
        """
        try:
            results = self.graph.query(sparql_query)
            return [dict(row.asdict()) for row in results]
        except Exception as e:
            self.logger.error(f"SPARQL query failed: {e}")
            return []

    def serialize(self, format: str = "turtle") -> str:
        """
        Serialize graph to specified format.

        Args:
            format: RDF serialization format

        Returns:
            Serialized graph content
        """
        return self.graph.serialize(format=format)

    def load_ontology(self, ontology_path: str, format: str = "turtle") -> None:
        """
        Load ontology into the knowledge graph.

        Args:
            ontology_path: Path to ontology file
            format: RDF format of the ontology
        """
        try:
            self.graph.parse(ontology_path, format=format)
            self.logger.info(f"Loaded ontology from {ontology_path}")
        except Exception as e:
            self.logger.error(f"Failed to load ontology: {e}")

    def get_triples_count(self) -> int:
        """Get total number of triples in the graph."""
        return len(self.graph)

    def clear(self) -> None:
        """Clear all triples from the graph."""
        self.graph.remove((None, None, None))
        self.logger.info("Cleared all triples from graph")


class EntityManager:
    """Manages entities in the knowledge graph."""

    def __init__(self, rdf_store: RDFStoreManager):
        """
        Initialize entity manager.

        Args:
            rdf_store: RDF store manager instance
        """
        self.store = rdf_store
        self.logger = logging.getLogger(__name__)

    def create_dataset_entity(
        self, dataset_id: str, metadata: dict[str, Any]
    ) -> URIRef:
        """
        Create dataset entity in knowledge graph.

        Args:
            dataset_id: Unique dataset identifier
            metadata: Dataset metadata dictionary

        Returns:
            Dataset URI
        """
        dataset_uri = NEURO[f"dataset_{dataset_id}"]

        # Add basic type information
        self.store.add_triple(dataset_uri, RDF.type, NEURO.Dataset)
        self.store.add_triple(dataset_uri, RDFS.label, Literal(dataset_id))

        # Add metadata properties
        if "identifier" in metadata:
            self.store.add_triple(
                dataset_uri, NEURO.hasIdentifier, Literal(metadata["identifier"])
            )

        if "session_description" in metadata:
            self.store.add_triple(
                dataset_uri,
                NEURO.hasDescription,
                Literal(metadata["session_description"]),
            )

        if "experimenter" in metadata:
            experimenter_list = metadata["experimenter"]
            if isinstance(experimenter_list, list):
                for experimenter in experimenter_list:
                    experimenter_uri = self._create_person_entity(experimenter)
                    self.store.add_triple(
                        dataset_uri, NEURO.hasExperimenter, experimenter_uri
                    )
            else:
                experimenter_uri = self._create_person_entity(experimenter_list)
                self.store.add_triple(
                    dataset_uri, NEURO.hasExperimenter, experimenter_uri
                )

        if "lab" in metadata:
            lab_uri = self._create_lab_entity(metadata["lab"])
            self.store.add_triple(dataset_uri, NEURO.conductedBy, lab_uri)

        if "institution" in metadata:
            self.store.add_triple(
                dataset_uri, NEURO.hasInstitution, Literal(metadata["institution"])
            )

        return dataset_uri

    def create_subject_entity(
        self, subject_id: str, metadata: dict[str, Any]
    ) -> URIRef:
        """
        Create subject entity in knowledge graph.

        Args:
            subject_id: Unique subject identifier
            metadata: Subject metadata dictionary

        Returns:
            Subject URI
        """
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

        if "weight" in metadata:
            self.store.add_triple(
                subject_uri, NEURO.hasWeight, Literal(metadata["weight"])
            )

        return subject_uri

    def create_device_entity(
        self, device_name: str, metadata: dict[str, Any]
    ) -> URIRef:
        """
        Create device entity in knowledge graph.

        Args:
            device_name: Device name
            metadata: Device metadata dictionary

        Returns:
            Device URI
        """
        device_uri = NEURO[f"device_{device_name.replace(' ', '_')}"]

        self.store.add_triple(device_uri, RDF.type, NEURO.Device)
        self.store.add_triple(device_uri, RDFS.label, Literal(device_name))

        if "description" in metadata:
            self.store.add_triple(
                device_uri, NEURO.hasDescription, Literal(metadata["description"])
            )

        if "manufacturer" in metadata:
            self.store.add_triple(
                device_uri, NEURO.hasManufacturer, Literal(metadata["manufacturer"])
            )

        if "model" in metadata:
            self.store.add_triple(
                device_uri, NEURO.hasModel, Literal(metadata["model"])
            )

        if "device_type" in metadata:
            self.store.add_triple(
                device_uri, NEURO.hasDeviceType, Literal(metadata["device_type"])
            )

        return device_uri

    def create_session_entity(
        self, session_id: str, metadata: dict[str, Any]
    ) -> URIRef:
        """
        Create session entity in knowledge graph.

        Args:
            session_id: Unique session identifier
            metadata: Session metadata dictionary

        Returns:
            Session URI
        """
        session_uri = NEURO[f"session_{session_id}"]

        self.store.add_triple(session_uri, RDF.type, NEURO.Session)
        self.store.add_triple(session_uri, RDFS.label, Literal(session_id))

        if "session_start_time" in metadata:
            self.store.add_triple(
                session_uri, NEURO.hasStartTime, Literal(metadata["session_start_time"])
            )

        if "session_description" in metadata:
            self.store.add_triple(
                session_uri,
                NEURO.hasDescription,
                Literal(metadata["session_description"]),
            )

        if "protocol" in metadata:
            protocol_uri = self._create_protocol_entity(metadata["protocol"])
            self.store.add_triple(session_uri, NEURO.usesProtocol, protocol_uri)

        return session_uri

    def create_lab_entity(
        self, lab_name: str, metadata: Optional[dict[str, Any]] = None
    ) -> URIRef:
        """
        Create lab entity in knowledge graph.

        Args:
            lab_name: Lab name
            metadata: Optional lab metadata dictionary

        Returns:
            Lab URI
        """
        lab_uri = NEURO[f"lab_{lab_name.replace(' ', '_')}"]
        self.store.add_triple(lab_uri, RDF.type, NEURO.Lab)
        self.store.add_triple(lab_uri, RDFS.label, Literal(lab_name))

        if metadata:
            if "institution" in metadata:
                self.store.add_triple(
                    lab_uri, NEURO.hasInstitution, Literal(metadata["institution"])
                )

            if "principal_investigator" in metadata:
                pi_uri = self._create_person_entity(metadata["principal_investigator"])
                self.store.add_triple(lab_uri, NEURO.hasPrincipalInvestigator, pi_uri)

        return lab_uri

    def create_protocol_entity(
        self, protocol_name: str, metadata: Optional[dict[str, Any]] = None
    ) -> URIRef:
        """
        Create protocol entity in knowledge graph.

        Args:
            protocol_name: Protocol name
            metadata: Optional protocol metadata dictionary

        Returns:
            Protocol URI
        """
        protocol_uri = NEURO[f"protocol_{protocol_name.replace(' ', '_')}"]
        self.store.add_triple(protocol_uri, RDF.type, NEURO.Protocol)
        self.store.add_triple(protocol_uri, RDFS.label, Literal(protocol_name))

        if metadata:
            if "description" in metadata:
                self.store.add_triple(
                    protocol_uri, NEURO.hasDescription, Literal(metadata["description"])
                )

            if "protocol_type" in metadata:
                self.store.add_triple(
                    protocol_uri,
                    NEURO.hasProtocolType,
                    Literal(metadata["protocol_type"]),
                )

        return protocol_uri

    def _create_person_entity(self, person_name: str) -> URIRef:
        """Create person entity."""
        person_uri = NEURO[f"person_{person_name.replace(' ', '_')}"]
        self.store.add_triple(person_uri, RDF.type, NEURO.Person)
        self.store.add_triple(person_uri, RDFS.label, Literal(person_name))
        return person_uri

    def _create_lab_entity(self, lab_name: str) -> URIRef:
        """Create lab entity (internal helper)."""
        return self.create_lab_entity(lab_name)

    def _create_protocol_entity(self, protocol_name: str) -> URIRef:
        """Create protocol entity (internal helper)."""
        return self.create_protocol_entity(protocol_name)

    def _resolve_species(self, species_name: str) -> URIRef:
        """
        Resolve species to standard ontology URI.

        Args:
            species_name: Species name

        Returns:
            Species URI (from NCBI Taxonomy or local namespace)
        """
        # Map to NCBI Taxonomy URIs where possible
        species_mapping = {
            "Mus musculus": "http://purl.obolibrary.org/obo/NCBITaxon_10090",
            "Rattus norvegicus": "http://purl.obolibrary.org/obo/NCBITaxon_10116",
            "Homo sapiens": "http://purl.obolibrary.org/obo/NCBITaxon_9606",
            "Macaca mulatta": "http://purl.obolibrary.org/obo/NCBITaxon_9544",
            "Danio rerio": "http://purl.obolibrary.org/obo/NCBITaxon_7955",
        }

        return URIRef(
            species_mapping.get(
                species_name, NEURO[f"species_{species_name.replace(' ', '_')}"]
            )
        )

    def _resolve_strain(self, strain_name: str) -> URIRef:
        """
        Resolve strain to standard ontology URI.

        Args:
            strain_name: Strain name

        Returns:
            Strain URI
        """
        # This would integrate with strain databases in the future
        # For now, create local URIs
        clean_strain = strain_name.replace("/", "_").replace("-", "_").replace(" ", "_")
        return NEURO[f"strain_{clean_strain}"]
