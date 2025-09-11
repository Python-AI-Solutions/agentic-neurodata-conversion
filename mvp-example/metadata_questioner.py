from rdflib import Graph


def get_required_fields(kg_file, _experiment_type):
    g = Graph()
    g.parse(kg_file, format="ttl")

    q = """
    PREFIX : <http://example.org/schema#>
    SELECT ?field ?type
    WHERE {
      ?field rdfs:domain :Experiment .
      ?field rdfs:range ?type .
    }
    """
    results = g.query(q)
    return [(str(r["field"]), str(r["type"])) for r in results]


def generate_dynamic_question(field, constraints, inferred=None):
    q = f"We’re missing `{field}`."
    if "allowedValues" in constraints:
        q += f" Allowed values: {constraints['allowedValues']}."
    if inferred:
        q += f" I inferred: {inferred}. Use this?"
    return q
