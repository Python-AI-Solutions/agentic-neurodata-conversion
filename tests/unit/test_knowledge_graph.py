"""Unit tests for knowledge graph foundation and data models."""

import pytest

# Import components to test
from agentic_neurodata_conversion.knowledge_graph import (
    ConfidenceScorer,
    Dataset,
    Device,
    EnrichmentResult,
    EntityManager,
    KnowledgeGraph,
    MetadataEnricher,
    RDFStoreManager,
    Subject,
)


@pytest.fixture
def sample_dataset_metadata():
    """Sample dataset metadata for testing."""
    return {
        "identifier": "test_dataset_001",
        "session_description": "Test recording session",
        "experimenter": ["John Doe", "Jane Smith"],
        "lab": "Neuroscience Lab",
        "institution": "Test University",
    }


@pytest.fixture
def sample_subject_metadata():
    """Sample subject metadata for testing."""
    return {
        "subject_id": "mouse_001",
        "species": "Mus musculus",
        "strain": "C57BL/6J",
        "age": "P60",
        "sex": "male",
        "weight": "25g",
    }


@pytest.fixture
def sample_device_metadata():
    """Sample device metadata for testing."""
    return {
        "description": "High-density silicon probe",
        "manufacturer": "IMEC",
        "model": "Neuropixels 1.0",
        "device_type": "extracellular_probe",
    }


@pytest.mark.unit
class TestRDFStoreManager:
    """Test RDF store management functionality."""

    def test_initialization(self):
        """Test RDF store manager initialization."""
        store = RDFStoreManager()
        assert store.store_type == "memory"
        assert store.graph is not None

    def test_add_triple(self):
        """Test adding triples to the store."""
        store = RDFStoreManager()

        # Add a simple triple
        store.add_triple(
            "http://example.org/subject",
            "http://example.org/predicate",
            "http://example.org/object",
        )

        # Verify triple was added
        assert store.get_triples_count() > 0

    def test_query_empty_graph(self):
        """Test querying empty graph."""
        store = RDFStoreManager()

        query = """
        SELECT ?s ?p ?o WHERE {
            ?s ?p ?o .
        }
        """

        results = store.query(query)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_serialize(self):
        """Test graph serialization."""
        store = RDFStoreManager()

        # Add a triple
        store.add_triple(
            "http://example.org/subject", "http://example.org/predicate", "test_value"
        )

        # Serialize to turtle format
        turtle_content = store.serialize("turtle")
        assert isinstance(turtle_content, str)
        assert len(turtle_content) > 0


@pytest.mark.unit
class TestEntityManager:
    """Test entity management functionality."""

    def test_initialization(self):
        """Test entity manager initialization."""
        store = RDFStoreManager()
        entity_manager = EntityManager(store)
        assert entity_manager.store == store

    def test_create_dataset_entity(self, sample_dataset_metadata):
        """Test dataset entity creation."""
        store = RDFStoreManager()
        entity_manager = EntityManager(store)

        dataset_uri = entity_manager.create_dataset_entity(
            "test_dataset", sample_dataset_metadata
        )

        assert dataset_uri is not None
        assert str(dataset_uri).endswith("dataset_test_dataset")

        # Verify triples were added
        assert store.get_triples_count() > 0

    def test_create_subject_entity(self, sample_subject_metadata):
        """Test subject entity creation."""
        store = RDFStoreManager()
        entity_manager = EntityManager(store)

        subject_uri = entity_manager.create_subject_entity(
            "test_subject", sample_subject_metadata
        )

        assert subject_uri is not None
        assert str(subject_uri).endswith("subject_test_subject")

        # Verify triples were added
        assert store.get_triples_count() > 0

    def test_create_device_entity(self, sample_device_metadata):
        """Test device entity creation."""
        store = RDFStoreManager()
        entity_manager = EntityManager(store)

        device_uri = entity_manager.create_device_entity(
            "Neuropixels", sample_device_metadata
        )

        assert device_uri is not None
        assert "device_Neuropixels" in str(device_uri)

        # Verify triples were added
        assert store.get_triples_count() > 0


@pytest.mark.unit
class TestKnowledgeGraph:
    """Test main KnowledgeGraph class functionality."""

    def test_initialization(self):
        """Test knowledge graph initialization."""
        kg = KnowledgeGraph()
        assert kg.rdf_store is not None
        assert kg.entity_manager is not None
        assert kg.enricher is not None
        assert kg.confidence_scorer is not None

    def test_add_dataset(self, sample_dataset_metadata):
        """Test adding dataset to knowledge graph."""
        kg = KnowledgeGraph()

        dataset = kg.add_dataset("test_dataset", sample_dataset_metadata)

        assert isinstance(dataset, Dataset)
        assert dataset.id == "test_dataset"
        assert dataset.identifier == "test_dataset_001"
        assert dataset.lab == "Neuroscience Lab"

    def test_add_subject(self, sample_subject_metadata):
        """Test adding subject to knowledge graph."""
        kg = KnowledgeGraph()

        subject = kg.add_subject("test_subject", sample_subject_metadata)

        assert isinstance(subject, Subject)
        assert subject.id == "test_subject"
        assert subject.species == "Mus musculus"
        assert subject.strain == "C57BL/6J"

    def test_add_device(self, sample_device_metadata):
        """Test adding device to knowledge graph."""
        kg = KnowledgeGraph()

        device = kg.add_device("Neuropixels", sample_device_metadata)

        assert isinstance(device, Device)
        assert device.id == "Neuropixels"
        assert device.manufacturer == "IMEC"
        assert device.model == "Neuropixels 1.0"

    def test_get_entity(self, sample_dataset_metadata):
        """Test retrieving entities by ID."""
        kg = KnowledgeGraph()

        # Add dataset
        dataset = kg.add_dataset("test_dataset", sample_dataset_metadata)

        # Retrieve by ID
        retrieved_dataset = kg.get_entity("test_dataset")
        assert retrieved_dataset == dataset

    def test_get_entities_by_type(
        self, sample_dataset_metadata, sample_subject_metadata
    ):
        """Test retrieving entities by type."""
        kg = KnowledgeGraph()

        # Add entities of different types
        dataset = kg.add_dataset("test_dataset", sample_dataset_metadata)
        subject = kg.add_subject("test_subject", sample_subject_metadata)

        # Get datasets
        datasets = kg.get_entities_by_type(Dataset)
        assert len(datasets) == 1
        assert datasets[0] == dataset

        # Get subjects
        subjects = kg.get_entities_by_type(Subject)
        assert len(subjects) == 1
        assert subjects[0] == subject

    def test_serialize(self, sample_dataset_metadata):
        """Test knowledge graph serialization."""
        kg = KnowledgeGraph()

        # Add some data
        kg.add_dataset("test_dataset", sample_dataset_metadata)

        # Serialize
        turtle_content = kg.serialize("turtle")
        assert isinstance(turtle_content, str)
        assert len(turtle_content) > 0

    def test_get_statistics(self, sample_dataset_metadata, sample_subject_metadata):
        """Test knowledge graph statistics."""
        kg = KnowledgeGraph()

        # Add entities
        kg.add_dataset("test_dataset", sample_dataset_metadata)
        kg.add_subject("test_subject", sample_subject_metadata)

        stats = kg.get_statistics()

        assert stats["total_entities"] == 2
        assert stats["entity_counts"]["Dataset"] == 1
        assert stats["entity_counts"]["Subject"] == 1
        assert stats["total_triples"] > 0
        assert stats["store_type"] == "memory"


@pytest.mark.unit
class TestMetadataEnricher:
    """Test metadata enrichment functionality."""

    def test_initialization(self):
        """Test metadata enricher initialization."""
        store = RDFStoreManager()
        enricher = MetadataEnricher(store)
        assert enricher.store == store
        assert enricher.domain_knowledge is not None

    def test_species_from_strain_enrichment(self):
        """Test species inference from strain."""
        store = RDFStoreManager()
        enricher = MetadataEnricher(store)

        metadata = {"strain": "C57BL/6J"}
        enrichments = enricher.enrich_metadata(metadata)

        # Should find species enrichment
        species_enrichments = [e for e in enrichments if e.field == "species"]
        assert len(species_enrichments) > 0

        species_enrichment = species_enrichments[0]
        assert species_enrichment.enriched_value == "Mus musculus"
        assert species_enrichment.confidence > 0.9

    def test_age_standardization(self):
        """Test age format standardization."""
        store = RDFStoreManager()
        enricher = MetadataEnricher(store)

        metadata = {"age": "60 days"}
        enrichments = enricher.enrich_metadata(metadata)

        # Should find age standardization
        age_enrichments = [e for e in enrichments if e.field == "age_standardized"]
        assert len(age_enrichments) > 0

        age_enrichment = age_enrichments[0]
        assert age_enrichment.enriched_value == "P60D"
        assert age_enrichment.confidence > 0.9

    def test_sex_standardization(self):
        """Test sex value standardization."""
        store = RDFStoreManager()
        enricher = MetadataEnricher(store)

        metadata = {"sex": "M"}
        enrichments = enricher.enrich_metadata(metadata)

        # Should find sex standardization
        sex_enrichments = [e for e in enrichments if e.field == "sex_standardized"]
        assert len(sex_enrichments) > 0

        sex_enrichment = sex_enrichments[0]
        assert sex_enrichment.enriched_value == "male"
        assert sex_enrichment.confidence > 0.9


@pytest.mark.unit
class TestConfidenceScorer:
    """Test confidence scoring functionality."""

    def test_initialization(self):
        """Test confidence scorer initialization."""
        scorer = ConfidenceScorer()
        assert scorer.scoring_rules is not None

    def test_score_enrichment(self):
        """Test enrichment confidence scoring."""
        scorer = ConfidenceScorer()

        enrichment = EnrichmentResult(
            field="species",
            original_value=None,
            enriched_value="Mus musculus",
            confidence=0.95,
            source="strain_species_mapping",
            reasoning="Test reasoning",
        )

        score = scorer.score_enrichment(enrichment)

        assert 0.0 <= score <= 1.0
        assert score > 0.9  # Should be high confidence for strain mapping


@pytest.mark.unit
class TestEntityClasses:
    """Test entity class functionality."""

    def test_dataset_entity(self, sample_dataset_metadata):
        """Test Dataset entity functionality."""
        dataset = Dataset(
            id="test_dataset",
            uri="http://example.org/dataset_test",
            metadata=sample_dataset_metadata,
        )

        assert dataset.identifier == "test_dataset_001"
        assert dataset.lab == "Neuroscience Lab"
        assert dataset.get_rdf_type() == "http://neuroscience.org/ontology/Dataset"

    def test_subject_entity(self, sample_subject_metadata):
        """Test Subject entity functionality."""
        subject = Subject(
            id="test_subject",
            uri="http://example.org/subject_test",
            metadata=sample_subject_metadata,
        )

        assert subject.species == "Mus musculus"
        assert subject.strain == "C57BL/6J"
        assert subject.age == "P60"
        assert subject.sex == "male"
        assert subject.get_rdf_type() == "http://neuroscience.org/ontology/Subject"

    def test_device_entity(self, sample_device_metadata):
        """Test Device entity functionality."""
        device = Device(
            id="test_device",
            uri="http://example.org/device_test",
            metadata=sample_device_metadata,
        )

        assert device.manufacturer == "IMEC"
        assert device.model == "Neuropixels 1.0"
        assert device.device_type == "extracellular_probe"
        assert device.get_rdf_type() == "http://neuroscience.org/ontology/Device"

    def test_entity_relationships(self, sample_dataset_metadata):
        """Test entity relationship functionality."""
        dataset = Dataset(
            id="test_dataset",
            uri="http://example.org/dataset_test",
            metadata=sample_dataset_metadata,
        )

        # Add relationship
        dataset.add_relationship("http://example.org/hasSubject", "subject_001")

        # Check relationships
        relationships = dataset.get_relationships()
        assert "http://example.org/hasSubject" in relationships
        assert "subject_001" in relationships["http://example.org/hasSubject"]

    def test_entity_properties(self, sample_dataset_metadata):
        """Test entity property access."""
        dataset = Dataset(
            id="test_dataset",
            uri="http://example.org/dataset_test",
            metadata=sample_dataset_metadata,
        )

        # Test property access
        assert dataset.get_property("lab") == "Neuroscience Lab"
        assert dataset.get_property("nonexistent", "default") == "default"

        # Test property setting
        dataset.set_property("new_property", "new_value")
        assert dataset.get_property("new_property") == "new_value"


@pytest.mark.unit
class TestKnowledgeGraphIntegration:
    """Test integration between knowledge graph components."""

    def test_end_to_end_workflow(
        self, sample_dataset_metadata, sample_subject_metadata
    ):
        """Test complete workflow from metadata to enriched knowledge graph."""
        kg = KnowledgeGraph()

        # Add entities
        kg.add_dataset("test_dataset", sample_dataset_metadata)
        kg.add_subject("test_subject", sample_subject_metadata)

        # Add relationships
        kg.add_relationship(
            "test_dataset",
            "http://neuroscience.org/ontology/hasSubject",
            "test_subject",
        )

        # Test enrichment
        enriched_metadata = kg.enrich_metadata({"strain": "C57BL/6J"})
        assert "species" in enriched_metadata
        assert enriched_metadata["species"] == "Mus musculus"

        # Test serialization
        turtle_content = kg.serialize("turtle")
        assert len(turtle_content) > 0

        # Test statistics
        stats = kg.get_statistics()
        assert stats["total_entities"] == 2
        assert stats["total_triples"] > 0

    def test_metadata_enrichment_integration(self):
        """Test metadata enrichment with knowledge graph."""
        kg = KnowledgeGraph()

        # Test metadata with missing species
        metadata = {"strain": "C57BL/6J", "age": "8 weeks", "sex": "F"}

        # Get enrichment suggestions
        suggestions = kg.get_enrichment_suggestions(metadata)

        # Should have suggestions for species, age standardization, sex standardization
        suggestion_fields = [s["field"] for s in suggestions]
        assert "species" in suggestion_fields
        assert "age_standardized" in suggestion_fields
        assert "sex_standardized" in suggestion_fields

        # Test automatic enrichment
        enriched = kg.enrich_metadata(metadata, confidence_threshold=0.7)
        assert "species" in enriched
        assert enriched["species"] == "Mus musculus"
