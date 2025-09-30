"""TTL and JSON-LD generator from LinkML instances.

This module generates RDF/TTL and JSON-LD from LinkML instances.
"""

from typing import Any
from linkml_runtime.utils.schemaview import SchemaView
from rdflib import Graph, Namespace, Literal, URIRef, RDF
from src.linkml_converter import LinkMLInstances


def generate_ttl(linkml_instances: LinkMLInstances, schema: SchemaView) -> str:
    """Generate TTL (Turtle) RDF from LinkML instances.

    Args:
        linkml_instances: LinkML instances to convert
        schema: LinkML schema

    Returns:
        TTL content as string
    """
    # Create RDF graph
    g = Graph()

    # Define namespaces
    NWB = Namespace(f"http://purl.org/nwb/{linkml_instances.metadata.schema_version}/")
    g.bind("nwb", NWB)

    # Convert each instance to triples
    for instance in linkml_instances.instances:
        _add_instance_to_graph(instance, g, NWB)

    # Serialize to TTL
    ttl_content = g.serialize(format='turtle')

    return ttl_content


def generate_jsonld(ttl_content: str) -> str:
    """Generate JSON-LD from TTL content.

    Args:
        ttl_content: TTL/Turtle RDF content

    Returns:
        JSON-LD content as string
    """
    # Parse TTL into graph
    g = Graph()
    g.parse(data=ttl_content, format='turtle')

    # Serialize to JSON-LD
    jsonld_content = g.serialize(format='json-ld', indent=2)

    return jsonld_content


def _add_instance_to_graph(instance: dict[str, Any], graph: Graph, namespace: Namespace) -> None:
    """Add LinkML instance as triples to RDF graph.

    Args:
        instance: Dictionary representing LinkML instance
        graph: RDF Graph to add to
        namespace: Namespace for URIs
    """
    # Get type
    instance_type = instance.get("@type", "Unknown")

    # Create subject URI - prefer @id, then identifier, then name
    if "@id" in instance:
        subject = namespace[instance["@id"]]
    elif "identifier" in instance:
        subject = namespace[instance["identifier"]]
    elif "name" in instance:
        subject = namespace[instance["name"]]
    else:
        # Generate ID
        subject = namespace[f"instance_{id(instance)}"]

    # Add type triple
    type_uri = namespace[instance_type]
    graph.add((subject, RDF.type, type_uri))

    # Add property triples
    for key, value in instance.items():
        if key.startswith("@"):
            continue  # Skip metadata keys

        predicate = namespace[key]

        # Convert value to RDF term
        if isinstance(value, str):
            graph.add((subject, predicate, Literal(value)))
        elif isinstance(value, (int, float)):
            graph.add((subject, predicate, Literal(value)))
        elif isinstance(value, bool):
            graph.add((subject, predicate, Literal(value)))
        elif isinstance(value, list):
            # Add each list item - if it's a reference, create a URI, otherwise literal
            for item in value:
                if isinstance(item, str):
                    # Check if it looks like an ID reference (relationship)
                    if key.startswith('has_') or '_ref' in key.lower():
                        # Create URI reference for relationships
                        graph.add((subject, predicate, namespace[item]))
                    else:
                        graph.add((subject, predicate, Literal(item)))
        # Skip complex objects for now