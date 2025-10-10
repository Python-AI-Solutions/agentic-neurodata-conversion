"""
Provenance Tracker API Contract

Defines the interface for recording and querying provenance using PROV-O ontology.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from rdflib import URIRef


class ConfidenceLevel(str, Enum):
    """Confidence level for metadata reliability."""

    DEFINITIVE = "definitive"
    HIGH_EVIDENCE = "high_evidence"
    HUMAN_CONFIRMED = "human_confirmed"
    HUMAN_OVERRIDE = "human_override"
    MEDIUM_EVIDENCE = "medium_evidence"
    HEURISTIC = "heuristic"
    LOW_EVIDENCE = "low_evidence"
    PLACEHOLDER = "placeholder"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    """Type of evidence source."""

    FILE = "file"
    HUMAN_INPUT = "human_input"
    HEURISTIC = "heuristic"
    AUTOMATED_ANALYSIS = "automated_analysis"


class ProvenanceTrackerInterface(ABC):
    """Interface for provenance tracking and querying."""

    @abstractmethod
    def start_activity(
        self,
        activity_id: str,
        activity_type: str,
        start_time: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> URIRef:
        """
        Record the start of a provenance activity (e.g., conversion, validation).

        Args:
            activity_id: Unique identifier for activity
            activity_type: Type of activity (e.g., "conversion", "validation")
            start_time: Activity start timestamp (defaults to now)
            metadata: Additional activity metadata

        Returns:
            URIRef for the created PROV Activity

        Raises:
            ActivityExistsError: If activity_id already exists
        """
        pass

    @abstractmethod
    def end_activity(
        self,
        activity_id: str,
        end_time: Optional[datetime] = None,
        status: str = "completed",
    ) -> None:
        """
        Record the end of a provenance activity.

        Args:
            activity_id: Activity identifier
            end_time: Activity end timestamp (defaults to now)
            status: Completion status ("completed", "failed", "cancelled")

        Raises:
            ActivityNotFoundError: If activity doesn't exist
        """
        pass

    @abstractmethod
    def record_entity(
        self,
        entity_id: str,
        entity_type: str,
        value: Any,
        metadata: Optional[dict[str, Any]] = None,
    ) -> URIRef:
        """
        Record a provenance entity (data item, file, metadata field).

        Args:
            entity_id: Unique identifier for entity
            entity_type: Type of entity (e.g., "nwb_file", "metadata_field")
            value: Entity value/content
            metadata: Additional entity metadata

        Returns:
            URIRef for the created PROV Entity

        Raises:
            EntityExistsError: If entity_id already exists
        """
        pass

    @abstractmethod
    def record_agent(
        self,
        agent_id: str,
        agent_type: str,
        name: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> URIRef:
        """
        Record a provenance agent (person, software, system).

        Args:
            agent_id: Unique identifier for agent
            agent_type: Type of agent (e.g., "human", "conversion_agent", "system")
            name: Human-readable agent name
            metadata: Additional agent metadata

        Returns:
            URIRef for the created PROV Agent

        Raises:
            AgentExistsError: If agent_id already exists
        """
        pass

    @abstractmethod
    def link_generation(
        self,
        entity_id: str,
        activity_id: str,
        generation_time: Optional[datetime] = None,
    ) -> None:
        """
        Link entity to activity that generated it (prov:wasGeneratedBy).

        Args:
            entity_id: Generated entity identifier
            activity_id: Generating activity identifier
            generation_time: When entity was generated

        Raises:
            EntityNotFoundError: If entity doesn't exist
            ActivityNotFoundError: If activity doesn't exist
        """
        pass

    @abstractmethod
    def link_usage(
        self, activity_id: str, entity_id: str, usage_time: Optional[datetime] = None
    ) -> None:
        """
        Link activity to entity it used (prov:used).

        Args:
            activity_id: Activity identifier
            entity_id: Used entity identifier
            usage_time: When entity was used

        Raises:
            ActivityNotFoundError: If activity doesn't exist
            EntityNotFoundError: If entity doesn't exist
        """
        pass

    @abstractmethod
    def link_association(
        self, activity_id: str, agent_id: str, role: Optional[str] = None
    ) -> None:
        """
        Link activity to agent responsible for it (prov:wasAssociatedWith).

        Args:
            activity_id: Activity identifier
            agent_id: Agent identifier
            role: Agent's role in activity (e.g., "executor", "supervisor")

        Raises:
            ActivityNotFoundError: If activity doesn't exist
            AgentNotFoundError: If agent doesn't exist
        """
        pass

    @abstractmethod
    def link_attribution(self, entity_id: str, agent_id: str) -> None:
        """
        Link entity to agent attributed for it (prov:wasAttributedTo).

        Args:
            entity_id: Entity identifier
            agent_id: Agent identifier

        Raises:
            EntityNotFoundError: If entity doesn't exist
            AgentNotFoundError: If agent doesn't exist
        """
        pass

    @abstractmethod
    def link_derivation(
        self,
        derived_entity_id: str,
        source_entity_id: str,
        activity_id: Optional[str] = None,
    ) -> None:
        """
        Link derived entity to source entity (prov:wasDerivedFrom).

        Args:
            derived_entity_id: Derived entity identifier
            source_entity_id: Source entity identifier
            activity_id: Optional activity that performed derivation

        Raises:
            EntityNotFoundError: If either entity doesn't exist
        """
        pass

    @abstractmethod
    def record_metadata_provenance(
        self,
        metadata_field: str,
        value: Any,
        confidence: ConfidenceLevel,
        source_type: SourceType,
        derivation_method: str,
        reasoning_chain: list[str],
        evidence_sources: list[dict[str, Any]],
        activity_id: str,
        agent_id: str,
    ) -> str:
        """
        Record complete provenance for a metadata field (convenience method).

        Args:
            metadata_field: Name of NWB metadata field
            value: Metadata value
            confidence: Confidence level classification
            source_type: Type of evidence source
            derivation_method: Description of how value was derived
            reasoning_chain: Step-by-step reasoning
            evidence_sources: List of supporting evidence
            activity_id: Activity that generated metadata
            agent_id: Agent responsible

        Returns:
            Entity ID for recorded metadata provenance

        Raises:
            ValidationError: If required fields missing
        """
        pass

    @abstractmethod
    def query_sparql(self, query: str) -> list[dict[str, Any]]:
        """
        Execute SPARQL query on provenance graph.

        Args:
            query: SPARQL query string

        Returns:
            List of query results as dictionaries

        Raises:
            QuerySyntaxError: If SPARQL query is invalid
            QueryExecutionError: If query execution fails
        """
        pass

    @abstractmethod
    def get_entity_provenance(self, entity_id: str, depth: int = 1) -> dict[str, Any]:
        """
        Get complete provenance for an entity (upstream and downstream).

        Args:
            entity_id: Entity identifier
            depth: How many levels deep to traverse (1 = direct only)

        Returns:
            Dict containing:
                - entity: Entity details
                - generated_by: Activity that generated it
                - used_by: Activities that used it
                - derived_from: Source entities
                - derived_to: Derived entities
                - attributed_to: Agents

        Raises:
            EntityNotFoundError: If entity doesn't exist
        """
        pass

    @abstractmethod
    def get_activity_provenance(self, activity_id: str) -> dict[str, Any]:
        """
        Get complete provenance for an activity.

        Args:
            activity_id: Activity identifier

        Returns:
            Dict containing:
                - activity: Activity details
                - generated: Entities generated
                - used: Entities used
                - associated_agents: Agents involved

        Raises:
            ActivityNotFoundError: If activity doesn't exist
        """
        pass

    @abstractmethod
    def export_graph(self, format: str = "turtle") -> str:
        """
        Export provenance graph in RDF format.

        Args:
            format: RDF serialization format ("turtle", "xml", "json-ld")

        Returns:
            Serialized RDF graph as string

        Raises:
            UnsupportedFormatError: If format not supported
        """
        pass

    @abstractmethod
    def get_confidence_distribution(self) -> dict[ConfidenceLevel, int]:
        """
        Get distribution of confidence levels across all metadata.

        Returns:
            Dict mapping confidence levels to counts
        """
        pass
