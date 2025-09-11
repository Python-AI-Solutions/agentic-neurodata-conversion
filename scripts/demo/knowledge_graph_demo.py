#!/usr/bin/env python3
"""
Knowledge Graph Demo Script

Demonstrates the knowledge graph foundation and data models functionality.
"""

import logging
from pathlib import Path

from agentic_neurodata_conversion.knowledge_graph import (
    Dataset,
    Device,
    KnowledgeGraph,
    Subject,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Demonstrate knowledge graph functionality."""
    logger.info("Starting Knowledge Graph Demo")

    # Initialize knowledge graph
    kg = KnowledgeGraph()
    logger.info("Initialized knowledge graph")

    # Sample metadata for demonstration
    dataset_metadata = {
        "identifier": "demo_dataset_001",
        "session_description": "Demonstration recording session",
        "experimenter": ["Dr. Jane Smith", "Dr. John Doe"],
        "lab": "Computational Neuroscience Lab",
        "institution": "Demo University",
    }

    subject_metadata = {
        "subject_id": "mouse_001",
        "species": "Mus musculus",
        "strain": "C57BL/6J",
        "age": "P60",
        "sex": "male",
        "weight": "25g",
    }

    device_metadata = {
        "description": "High-density silicon probe for extracellular recording",
        "manufacturer": "IMEC",
        "model": "Neuropixels 1.0",
        "device_type": "extracellular_probe",
    }

    # Add entities to knowledge graph
    logger.info("Adding entities to knowledge graph...")

    dataset = kg.add_dataset("demo_dataset", dataset_metadata)
    logger.info(f"Added dataset: {dataset.identifier}")

    subject = kg.add_subject("demo_subject", subject_metadata)
    logger.info(f"Added subject: {subject.species} ({subject.strain})")

    device = kg.add_device("Neuropixels", device_metadata)
    logger.info(f"Added device: {device.manufacturer} {device.model}")

    # Add relationships
    logger.info("Adding relationships...")
    kg.add_relationship(
        "demo_dataset", "http://neuroscience.org/ontology/hasSubject", "demo_subject"
    )
    kg.add_relationship(
        "demo_dataset", "http://neuroscience.org/ontology/usesDevice", "Neuropixels"
    )

    # Demonstrate metadata enrichment
    logger.info("Testing metadata enrichment...")

    # Test metadata with missing species (should be inferred from strain)
    test_metadata = {"strain": "C57BL/6J", "age": "8 weeks", "sex": "F"}

    # Get enrichment suggestions
    suggestions = kg.get_enrichment_suggestions(test_metadata)
    logger.info(f"Found {len(suggestions)} enrichment suggestions:")
    for suggestion in suggestions:
        logger.info(
            f"  - {suggestion['field']}: {suggestion['suggested_value']} "
            f"(confidence: {suggestion['confidence']:.2f})"
        )

    # Apply automatic enrichment
    enriched_metadata = kg.enrich_metadata(test_metadata, confidence_threshold=0.7)
    logger.info(f"Enriched metadata: {enriched_metadata}")

    # Get knowledge graph statistics
    stats = kg.get_statistics()
    logger.info("Knowledge graph statistics:")
    logger.info(f"  - Total entities: {stats['total_entities']}")
    logger.info(f"  - Total triples: {stats['total_triples']}")
    logger.info(f"  - Entity counts: {stats['entity_counts']}")

    # Demonstrate serialization
    logger.info("Serializing knowledge graph...")

    # Create output directory
    output_dir = Path("knowledge_graph_demo_output")
    output_dir.mkdir(exist_ok=True)

    # Export to different formats
    formats = ["turtle", "json-ld", "n3"]
    for format_name in formats:
        output_file = output_dir / f"demo_graph.{format_name.replace('-', '_')}"
        kg.export_to_file(output_file, format_name)
        logger.info(f"Exported to {output_file}")

    # Demonstrate SPARQL queries
    logger.info("Testing SPARQL queries...")

    # Query for all datasets
    query = """
    PREFIX neuro: <http://neuroscience.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?dataset ?label WHERE {
        ?dataset a neuro:Dataset .
        ?dataset rdfs:label ?label .
    }
    """

    results = kg.query(query)
    logger.info(f"Found {len(results)} datasets:")
    for result in results:
        logger.info(f"  - {result}")

    # Query for subjects and their species
    query = """
    PREFIX neuro: <http://neuroscience.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?subject ?species WHERE {
        ?subject a neuro:Subject .
        ?subject neuro:hasSpecies ?species .
    }
    """

    results = kg.query(query)
    logger.info(f"Found {len(results)} subjects with species:")
    for result in results:
        logger.info(f"  - {result}")

    # Demonstrate entity retrieval
    logger.info("Testing entity retrieval...")

    # Get entity by ID
    retrieved_dataset = kg.get_entity("demo_dataset")
    if retrieved_dataset:
        logger.info(f"Retrieved dataset: {retrieved_dataset.identifier}")

    # Get entities by type
    datasets = kg.get_entities_by_type(Dataset)
    subjects = kg.get_entities_by_type(Subject)
    devices = kg.get_entities_by_type(Device)

    logger.info(
        f"Found {len(datasets)} datasets, {len(subjects)} subjects, {len(devices)} devices"
    )

    logger.info("Knowledge Graph Demo completed successfully!")
    logger.info(f"Output files saved to: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
