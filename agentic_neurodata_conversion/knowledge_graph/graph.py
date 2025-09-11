"""Main KnowledgeGraph class for managing semantic relationships and metadata enrichment."""

import logging
from pathlib import Path
from typing import Any, Optional, Union

from .enrichment import ConfidenceScorer, MetadataEnricher
from .entities import Dataset, Device, Lab, Protocol, Session, Subject
from .rdf_store import EntityManager, RDFStoreManager


class KnowledgeGraph:
    """
    Main knowledge graph system for neuroscience data conversion.

    Provides semantic enrichment, metadata validation, and relationship modeling
    for the agentic neurodata conversion pipeline.
    """

    def __init__(
        self,
        store_type: str = "memory",
        store_config: Optional[dict[str, Any]] = None,
    ):
        """
        Initialize knowledge graph system.

        Args:
            store_type: Type of RDF store ("memory", "sparql")
            store_config: Configuration for the RDF store
        """
        self.logger = logging.getLogger(__name__)

        # Initialize core components
        self.rdf_store = RDFStoreManager(store_type, store_config)
        self.entity_manager = EntityManager(self.rdf_store)
        self.enricher = MetadataEnricher(self.rdf_store)
        self.confidence_scorer = ConfidenceScorer()

        # Track entities for efficient access
        self._entities: dict[
            str, Union[Dataset, Session, Subject, Device, Lab, Protocol]
        ] = {}

        self.logger.info(f"Initialized KnowledgeGraph with {store_type} store")

    def add_dataset(self, dataset_id: str, metadata: dict[str, Any]) -> Dataset:
        """
        Add a dataset entity to the knowledge graph.

        Args:
            dataset_id: Unique identifier for the dataset
            metadata: Dataset metadata dictionary

        Returns:
            Dataset entity object
        """
        # Create RDF representation
        dataset_uri = self.entity_manager.create_dataset_entity(dataset_id, metadata)

        # Create entity object
        dataset = Dataset(
            id=dataset_id, uri=str(dataset_uri), metadata=metadata, knowledge_graph=self
        )

        self._entities[dataset_id] = dataset

        self.logger.info(f"Added dataset entity: {dataset_id}")
        return dataset

    def add_subject(self, subject_id: str, metadata: dict[str, Any]) -> Subject:
        """
        Add a subject entity to the knowledge graph.

        Args:
            subject_id: Unique identifier for the subject
            metadata: Subject metadata dictionary

        Returns:
            Subject entity object
        """
        # Create RDF representation
        subject_uri = self.entity_manager.create_subject_entity(subject_id, metadata)

        # Create entity object
        subject = Subject(
            id=subject_id, uri=str(subject_uri), metadata=metadata, knowledge_graph=self
        )

        self._entities[subject_id] = subject

        self.logger.info(f"Added subject entity: {subject_id}")
        return subject

    def add_device(self, device_name: str, metadata: dict[str, Any]) -> Device:
        """
        Add a device entity to the knowledge graph.

        Args:
            device_name: Name of the device
            metadata: Device metadata dictionary

        Returns:
            Device entity object
        """
        # Create RDF representation
        device_uri = self.entity_manager.create_device_entity(device_name, metadata)

        # Create entity object
        device = Device(
            id=device_name, uri=str(device_uri), metadata=metadata, knowledge_graph=self
        )

        self._entities[device_name] = device

        self.logger.info(f"Added device entity: {device_name}")
        return device

    def add_session(self, session_id: str, metadata: dict[str, Any]) -> Session:
        """
        Add a session entity to the knowledge graph.

        Args:
            session_id: Unique identifier for the session
            metadata: Session metadata dictionary

        Returns:
            Session entity object
        """
        # Create RDF representation using entity manager
        session_uri = self.entity_manager.create_session_entity(session_id, metadata)

        # Create entity object
        session = Session(
            id=session_id, uri=str(session_uri), metadata=metadata, knowledge_graph=self
        )

        self._entities[session_id] = session

        self.logger.info(f"Added session entity: {session_id}")
        return session

    def add_lab(self, lab_name: str, metadata: dict[str, Any]) -> Lab:
        """
        Add a lab entity to the knowledge graph.

        Args:
            lab_name: Name of the lab
            metadata: Lab metadata dictionary

        Returns:
            Lab entity object
        """
        # Create RDF representation using entity manager
        lab_uri = self.entity_manager.create_lab_entity(lab_name, metadata)

        # Create entity object
        lab = Lab(
            id=lab_name, uri=str(lab_uri), metadata=metadata, knowledge_graph=self
        )

        self._entities[lab_name] = lab

        self.logger.info(f"Added lab entity: {lab_name}")
        return lab

    def add_protocol(self, protocol_name: str, metadata: dict[str, Any]) -> Protocol:
        """
        Add a protocol entity to the knowledge graph.

        Args:
            protocol_name: Name of the protocol
            metadata: Protocol metadata dictionary

        Returns:
            Protocol entity object
        """
        # Create RDF representation using entity manager
        protocol_uri = self.entity_manager.create_protocol_entity(
            protocol_name, metadata
        )

        # Create entity object
        protocol = Protocol(
            id=protocol_name,
            uri=str(protocol_uri),
            metadata=metadata,
            knowledge_graph=self,
        )

        self._entities[protocol_name] = protocol

        self.logger.info(f"Added protocol entity: {protocol_name}")
        return protocol

    def enrich_metadata(
        self, metadata: dict[str, Any], confidence_threshold: float = 0.7
    ) -> dict[str, Any]:
        """
        Enrich metadata using knowledge graph and external sources.

        Args:
            metadata: Original metadata dictionary
            confidence_threshold: Minimum confidence for automatic enrichment

        Returns:
            Enriched metadata dictionary with applied enrichments
        """
        # Get enrichment suggestions
        enrichments = self.enricher.enrich_metadata(metadata)

        # Score and filter enrichments
        enriched_metadata = metadata.copy()
        applied_enrichments = []

        for enrichment in enrichments:
            confidence = self.confidence_scorer.score_enrichment(enrichment)

            if confidence >= confidence_threshold:
                enriched_metadata[enrichment.field] = enrichment.enriched_value
                applied_enrichments.append(
                    {
                        "field": enrichment.field,
                        "value": enrichment.enriched_value,
                        "confidence": confidence,
                        "reasoning": enrichment.reasoning,
                    }
                )

        self.logger.info(f"Applied {len(applied_enrichments)} enrichments")
        return enriched_metadata

    def get_enrichment_suggestions(
        self, metadata: dict[str, Any], max_suggestions: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get enrichment suggestions without applying them.

        Args:
            metadata: Metadata to analyze
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of enrichment suggestions with confidence scores
        """
        enrichments = self.enricher.enrich_metadata(metadata)
        suggestions = []

        for enrichment in enrichments[:max_suggestions]:
            confidence = self.confidence_scorer.score_enrichment(enrichment)
            suggestions.append(
                {
                    "field": enrichment.field,
                    "original_value": enrichment.original_value,
                    "suggested_value": enrichment.enriched_value,
                    "confidence": confidence,
                    "source": enrichment.source,
                    "reasoning": enrichment.reasoning,
                }
            )

        return suggestions

    def add_relationship(
        self, subject_entity: str, predicate: str, object_entity: str
    ) -> None:
        """
        Add a semantic relationship between entities.

        Args:
            subject_entity: Subject entity ID or URI
            predicate: Relationship predicate
            object_entity: Object entity ID or URI
        """
        # Convert entity IDs to URIs if needed
        subject_uri = self._get_entity_uri(subject_entity)
        object_uri = self._get_entity_uri(object_entity)

        # Add triple to RDF store
        self.rdf_store.add_triple(subject_uri, predicate, object_uri)

        self.logger.info(
            f"Added relationship: {subject_entity} {predicate} {object_entity}"
        )

    def query(self, sparql_query: str) -> list[dict[str, Any]]:
        """
        Execute SPARQL query against the knowledge graph.

        Args:
            sparql_query: SPARQL query string

        Returns:
            Query results as list of dictionaries
        """
        return self.rdf_store.query(sparql_query)

    def serialize(self, format: str = "turtle") -> str:
        """
        Serialize knowledge graph to specified RDF format.

        Args:
            format: RDF serialization format (turtle, json-ld, n3, xml)

        Returns:
            Serialized RDF content as string
        """
        return self.rdf_store.serialize(format)

    def export_to_file(
        self, file_path: Union[str, Path], format: str = "turtle"
    ) -> None:
        """
        Export knowledge graph to file.

        Args:
            file_path: Output file path
            format: RDF serialization format
        """
        content = self.serialize(format)
        Path(file_path).write_text(content, encoding="utf-8")

        self.logger.info(f"Exported knowledge graph to {file_path} in {format} format")

    def load_ontology(
        self, ontology_path: Union[str, Path], format: str = "turtle"
    ) -> None:
        """
        Load external ontology into the knowledge graph.

        Args:
            ontology_path: Path to ontology file
            format: RDF format of the ontology file
        """
        self.rdf_store.load_ontology(str(ontology_path), format)

    def get_entity(
        self, entity_id: str
    ) -> Optional[Union[Dataset, Session, Subject, Device, Lab, Protocol]]:
        """
        Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity object or None if not found
        """
        return self._entities.get(entity_id)

    def get_entities_by_type(
        self, entity_type: type
    ) -> list[Union[Dataset, Session, Subject, Device, Lab, Protocol]]:
        """
        Get all entities of a specific type.

        Args:
            entity_type: Entity class type

        Returns:
            List of entities of the specified type
        """
        return [
            entity
            for entity in self._entities.values()
            if isinstance(entity, entity_type)
        ]

    def get_statistics(self) -> dict[str, Any]:
        """
        Get knowledge graph statistics.

        Returns:
            Dictionary with graph statistics
        """
        # Count entities by type
        entity_counts = {}
        for entity in self._entities.values():
            entity_type = type(entity).__name__
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        # Count total triples
        total_triples = len(list(self.rdf_store.graph))

        return {
            "total_entities": len(self._entities),
            "entity_counts": entity_counts,
            "total_triples": total_triples,
            "store_type": self.rdf_store.store_type,
        }

    def _get_entity_uri(self, entity_identifier: str) -> str:
        """
        Convert entity ID to URI.

        Args:
            entity_identifier: Entity ID or URI

        Returns:
            Entity URI
        """
        if entity_identifier.startswith("http"):
            return entity_identifier

        # Look up entity in our registry
        entity = self._entities.get(entity_identifier)
        if entity:
            return entity.uri

        # Default to creating URI from ID
        from .rdf_store import NEURO

        return str(NEURO[f"entity_{entity_identifier}"])
