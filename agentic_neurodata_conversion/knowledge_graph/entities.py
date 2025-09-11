"""Entity classes for knowledge graph with RDF mapping."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .graph import KnowledgeGraph


@dataclass
class BaseEntity(ABC):
    """Base class for all knowledge graph entities."""

    id: str
    uri: str
    metadata: dict[str, Any]
    knowledge_graph: Optional["KnowledgeGraph"] = field(default=None, repr=False)

    def __post_init__(self):
        """Post-initialization setup."""
        self._relationships: dict[str, list[str]] = {}

    @abstractmethod
    def get_rdf_type(self) -> str:
        """Get the RDF type URI for this entity."""
        pass

    def add_relationship(self, predicate: str, target_entity: str) -> None:
        """
        Add a relationship to another entity.

        Args:
            predicate: Relationship predicate URI
            target_entity: Target entity ID or URI
        """
        if predicate not in self._relationships:
            self._relationships[predicate] = []

        if target_entity not in self._relationships[predicate]:
            self._relationships[predicate].append(target_entity)

            # Add to knowledge graph if available
            if self.knowledge_graph:
                self.knowledge_graph.add_relationship(self.id, predicate, target_entity)

    def get_relationships(
        self, predicate: Optional[str] = None
    ) -> dict[str, list[str]]:
        """
        Get relationships for this entity.

        Args:
            predicate: Optional predicate to filter by

        Returns:
            Dictionary of relationships
        """
        if predicate:
            return {predicate: self._relationships.get(predicate, [])}
        return self._relationships.copy()

    def get_property(self, property_name: str, default: Any = None) -> Any:
        """
        Get a metadata property value.

        Args:
            property_name: Property name
            default: Default value if property not found

        Returns:
            Property value or default
        """
        return self.metadata.get(property_name, default)

    def set_property(self, property_name: str, value: Any) -> None:
        """
        Set a metadata property value.

        Args:
            property_name: Property name
            value: Property value
        """
        self.metadata[property_name] = value


@dataclass
class Dataset(BaseEntity):
    """Dataset entity representing a neuroscience dataset."""

    def get_rdf_type(self) -> str:
        """Get the RDF type URI for Dataset."""
        return "http://neuroscience.org/ontology/Dataset"

    @property
    def identifier(self) -> Optional[str]:
        """Get dataset identifier."""
        return self.get_property("identifier")

    @property
    def session_description(self) -> Optional[str]:
        """Get session description."""
        return self.get_property("session_description")

    @property
    def experimenter(self) -> Optional[list[str]]:
        """Get experimenter list."""
        return self.get_property("experimenter")

    @property
    def lab(self) -> Optional[str]:
        """Get lab name."""
        return self.get_property("lab")

    @property
    def institution(self) -> Optional[str]:
        """Get institution name."""
        return self.get_property("institution")

    def add_session(self, session_id: str) -> None:
        """Add a session to this dataset."""
        self.add_relationship("http://neuroscience.org/ontology/hasSession", session_id)

    def add_subject(self, subject_id: str) -> None:
        """Add a subject to this dataset."""
        self.add_relationship("http://neuroscience.org/ontology/hasSubject", subject_id)

    def add_device(self, device_id: str) -> None:
        """Add a device used in this dataset."""
        self.add_relationship("http://neuroscience.org/ontology/usesDevice", device_id)


@dataclass
class Session(BaseEntity):
    """Session entity representing an experimental session."""

    def get_rdf_type(self) -> str:
        """Get the RDF type URI for Session."""
        return "http://neuroscience.org/ontology/Session"

    @property
    def session_start_time(self) -> Optional[str]:
        """Get session start time."""
        return self.get_property("session_start_time")

    @property
    def session_description(self) -> Optional[str]:
        """Get session description."""
        return self.get_property("session_description")

    @property
    def protocol(self) -> Optional[str]:
        """Get experimental protocol."""
        return self.get_property("protocol")

    def set_dataset(self, dataset_id: str) -> None:
        """Set the parent dataset for this session."""
        self.add_relationship(
            "http://neuroscience.org/ontology/partOfDataset", dataset_id
        )

    def set_subject(self, subject_id: str) -> None:
        """Set the subject for this session."""
        self.add_relationship("http://neuroscience.org/ontology/hasSubject", subject_id)

    def add_device(self, device_id: str) -> None:
        """Add a device used in this session."""
        self.add_relationship("http://neuroscience.org/ontology/usesDevice", device_id)


@dataclass
class Subject(BaseEntity):
    """Subject entity representing an experimental subject."""

    def get_rdf_type(self) -> str:
        """Get the RDF type URI for Subject."""
        return "http://neuroscience.org/ontology/Subject"

    @property
    def species(self) -> Optional[str]:
        """Get subject species."""
        return self.get_property("species")

    @property
    def strain(self) -> Optional[str]:
        """Get subject strain."""
        return self.get_property("strain")

    @property
    def age(self) -> Optional[str]:
        """Get subject age."""
        return self.get_property("age")

    @property
    def sex(self) -> Optional[str]:
        """Get subject sex."""
        return self.get_property("sex")

    @property
    def weight(self) -> Optional[str]:
        """Get subject weight."""
        return self.get_property("weight")

    def set_species(self, species: str) -> None:
        """Set subject species."""
        self.set_property("species", species)
        # Add semantic relationship
        self.add_relationship("http://neuroscience.org/ontology/hasSpecies", species)

    def set_strain(self, strain: str) -> None:
        """Set subject strain."""
        self.set_property("strain", strain)
        # Add semantic relationship
        self.add_relationship("http://neuroscience.org/ontology/hasStrain", strain)


@dataclass
class Device(BaseEntity):
    """Device entity representing recording or stimulation devices."""

    def get_rdf_type(self) -> str:
        """Get the RDF type URI for Device."""
        return "http://neuroscience.org/ontology/Device"

    @property
    def description(self) -> Optional[str]:
        """Get device description."""
        return self.get_property("description")

    @property
    def manufacturer(self) -> Optional[str]:
        """Get device manufacturer."""
        return self.get_property("manufacturer")

    @property
    def model(self) -> Optional[str]:
        """Get device model."""
        return self.get_property("model")

    @property
    def device_type(self) -> Optional[str]:
        """Get device type."""
        return self.get_property("device_type")

    def add_capability(self, capability: str) -> None:
        """Add a capability to this device."""
        self.add_relationship(
            "http://neuroscience.org/ontology/hasCapability", capability
        )

    def set_manufacturer(self, manufacturer: str) -> None:
        """Set device manufacturer."""
        self.set_property("manufacturer", manufacturer)
        self.add_relationship(
            "http://neuroscience.org/ontology/manufacturedBy", manufacturer
        )


@dataclass
class Lab(BaseEntity):
    """Lab entity representing a research laboratory."""

    def get_rdf_type(self) -> str:
        """Get the RDF type URI for Lab."""
        return "http://neuroscience.org/ontology/Lab"

    @property
    def institution(self) -> Optional[str]:
        """Get lab institution."""
        return self.get_property("institution")

    @property
    def principal_investigator(self) -> Optional[str]:
        """Get principal investigator."""
        return self.get_property("principal_investigator")

    @property
    def address(self) -> Optional[str]:
        """Get lab address."""
        return self.get_property("address")

    def add_member(self, person_id: str) -> None:
        """Add a lab member."""
        self.add_relationship("http://neuroscience.org/ontology/hasMember", person_id)

    def set_institution(self, institution: str) -> None:
        """Set lab institution."""
        self.set_property("institution", institution)
        self.add_relationship(
            "http://neuroscience.org/ontology/affiliatedWith", institution
        )


@dataclass
class Protocol(BaseEntity):
    """Protocol entity representing experimental protocols."""

    def get_rdf_type(self) -> str:
        """Get the RDF type URI for Protocol."""
        return "http://neuroscience.org/ontology/Protocol"

    @property
    def description(self) -> Optional[str]:
        """Get protocol description."""
        return self.get_property("description")

    @property
    def protocol_type(self) -> Optional[str]:
        """Get protocol type."""
        return self.get_property("protocol_type")

    @property
    def parameters(self) -> Optional[dict[str, Any]]:
        """Get protocol parameters."""
        return self.get_property("parameters")

    def add_step(self, step_description: str, step_order: int) -> None:
        """Add a protocol step."""
        step_id = f"{self.id}_step_{step_order}"
        self.add_relationship("http://neuroscience.org/ontology/hasStep", step_id)

        # Store step details in metadata
        if "steps" not in self.metadata:
            self.metadata["steps"] = {}
        self.metadata["steps"][step_order] = {
            "id": step_id,
            "description": step_description,
            "order": step_order,
        }

    def add_required_device(self, device_id: str) -> None:
        """Add a required device for this protocol."""
        self.add_relationship(
            "http://neuroscience.org/ontology/requiresDevice", device_id
        )
