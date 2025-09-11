# save_kg.py
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS

ttl = Path(input("TTL path: ").strip()).resolve()
base = ttl.with_suffix("")

g = Graph()
g.parse(str(ttl), format="turtle")

# 1) Line-delimited triples (NT)
g.serialize(destination=str(base.with_suffix(".nt")), format="nt")

# 2) JSON-LD
g.serialize(destination=str(base.with_suffix(".jsonld")), format="json-ld", indent=2)


# 3) LLM-friendly text with labels (fallbacks to CURIE/IRI tail)
def lbl(x):
    if isinstance(x, URIRef):
        for o in g.objects(x, RDFS.label):
            return str(o)
        s = str(x)
        return s.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
    return str(x)


with open(base.with_suffix(".triples.txt"), "w", encoding="utf-8") as f:
    for s, p, o in g:
        f.write(f"{lbl(s)}\t{lbl(p)}\t{lbl(o)}\n")

print(
    "Wrote:",
    base.with_suffix(".nt"),
    base.with_suffix(".jsonld"),
    base.with_suffix(".triples.txt"),
)
