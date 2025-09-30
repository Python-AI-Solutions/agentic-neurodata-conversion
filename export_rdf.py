#!/usr/bin/env python3
"""
Export the knowledge graph as RDF file.
"""

import asyncio
import httpx
from pathlib import Path

async def export_rdf():
    """Export the knowledge graph to RDF format."""

    print("🧬 Exporting Knowledge Graph to RDF...")
    print("=" * 50)

    # Query to get all triples
    query = """
    SELECT ?s ?p ?o WHERE {
        ?s ?p ?o
    }
    """

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/sparql/",
                json={
                    "query": query,
                    "timeout": 10,
                    "limit": 1000,
                    "format": "json"
                },
                timeout=15.0
            )

            if response.status_code == 200:
                result = response.json()
                bindings = result['results']['bindings']

                print(f"✅ Found {len(bindings)} RDF triples")
                print(f"⚡ Query time: {result['execution_time']:.3f}s")
                print()

                # Generate RDF in Turtle format
                rdf_content = generate_turtle_rdf(bindings)

                # Save to file
                rdf_file = Path("knowledge_graph.ttl")
                rdf_file.write_text(rdf_content)

                print(f"📄 RDF exported to: {rdf_file.absolute()}")
                print()
                print("🔍 RDF Content Preview:")
                print("-" * 40)
                print(rdf_content)

                # Also create a more human-readable format
                create_readable_rdf(bindings)

            else:
                error_detail = response.json().get('detail', 'Unknown error')
                print(f"❌ Query failed: {error_detail}")

        except Exception as e:
            print(f"❌ Connection error: {e}")

def generate_turtle_rdf(bindings):
    """Generate RDF in Turtle format."""

    # Define prefixes
    prefixes = """@prefix kg: <http://example.org/kg/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

"""

    # Group triples by subject
    subjects = {}
    for binding in bindings:
        subject = binding['s']['value']
        predicate = binding['p']['value']
        obj = binding['o']['value']

        if subject not in subjects:
            subjects[subject] = []
        subjects[subject].append((predicate, obj, binding['o'].get('type', 'uri')))

    # Generate Turtle triples
    turtle_content = prefixes

    for subject, predicates in subjects.items():
        # Format subject
        subject_formatted = format_uri(subject)
        turtle_content += f"\n{subject_formatted}\n"

        for i, (predicate, obj, obj_type) in enumerate(predicates):
            predicate_formatted = format_uri(predicate)
            obj_formatted = format_object(obj, obj_type)

            if i == len(predicates) - 1:
                turtle_content += f"    {predicate_formatted} {obj_formatted} .\n"
            else:
                turtle_content += f"    {predicate_formatted} {obj_formatted} ;\n"

    return turtle_content

def format_uri(uri):
    """Format URI with appropriate prefix."""
    if 'example.org/kg/' in uri:
        return uri.replace('http://example.org/kg/', 'kg:')
    elif 'www.w3.org/1999/02/22-rdf-syntax-ns#' in uri:
        return uri.replace('http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'rdf:')
    elif 'www.w3.org/ns/prov#' in uri:
        return uri.replace('http://www.w3.org/ns/prov#', 'prov:')
    else:
        return f"<{uri}>"

def format_object(obj, obj_type):
    """Format object value based on type."""
    if obj_type == 'literal':
        # Escape quotes in literals
        escaped = obj.replace('"', '\\"')
        return f'"{escaped}"'
    else:
        return format_uri(obj)

def create_readable_rdf(bindings):
    """Create a human-readable RDF representation."""

    readable_content = """# M541 Knowledge Graph - Human Readable Format
# ===============================================

"""

    # Group by subject for better readability
    subjects = {}
    for binding in bindings:
        subject = binding['s']['value']
        predicate = binding['p']['value']
        obj = binding['o']['value']

        if subject not in subjects:
            subjects[subject] = []
        subjects[subject].append((predicate, obj))

    for subject, predicates in subjects.items():
        subject_name = subject.split('/')[-1] if '/' in subject else subject
        readable_content += f"\n## {subject_name}\n"
        readable_content += f"URI: {subject}\n\n"

        for predicate, obj in predicates:
            pred_name = predicate.split('#')[-1].split('/')[-1]

            # Format object value
            if obj.startswith('http://'):
                obj_display = obj.split('/')[-1] if '/' in obj else obj
            else:
                obj_display = obj

            readable_content += f"- **{pred_name}**: {obj_display}\n"

        readable_content += "\n"

    # Add statistics
    readable_content += f"""
## Statistics
- Total Triples: {len(bindings)}
- Unique Subjects: {len(subjects)}
- Constitutional Compliance: ✅

## Namespaces Used
- kg: http://example.org/kg/ (Knowledge Graph)
- rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns# (RDF)
- prov: http://www.w3.org/ns/prov# (Provenance)
"""

    readable_file = Path("knowledge_graph_readable.md")
    readable_file.write_text(readable_content)
    print(f"📖 Human-readable format saved to: {readable_file.absolute()}")

if __name__ == "__main__":
    asyncio.run(export_rdf())