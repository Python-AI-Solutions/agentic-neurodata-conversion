#!/usr/bin/env python3
import argparse
import html
import json
import webbrowser
from pathlib import Path
from typing import Optional, Tuple, Dict, Set, List

from rdflib import Graph as RDFGraph, URIRef, Literal
from rdflib.namespace import RDFS
from pyvis.network import Network


def guess_format(path: Path) -> Optional[str]:
    suf = path.suffix.lower()
    if suf in {".ttl"}: return "turtle"
    if suf in {".nt"}: return "nt"
    if suf in {".rdf", ".xml"}: return "xml"
    if suf in {".json", ".jsonld"}: return "json-ld"
    return None


def short_label(iri: str) -> str:
    try:
        if "#" in iri: return iri.rsplit("#", 1)[-1]
        if "/" in iri: return iri.rstrip("/").rsplit("/", 1)[-1]
    except Exception:
        pass
    return iri


def load_graph(ttl_path: Path) -> RDFGraph:
    g = RDFGraph()
    fmt = guess_format(ttl_path)
    g.parse(str(ttl_path), format=fmt)
    return g


def build_subgraph(
    g: RDFGraph,
    max_triples: int = 8000,
    include_literals: bool = False,
) -> Tuple[Set[str], List[Tuple[str, str, str]], Dict[str, Dict[str, List[str]]]]:
    node_ids: Set[str] = set()
    edge_triples: List[Tuple[str, str, str]] = []
    props: Dict[str, Dict[str, List[str]]] = {}
    seen: Set[Tuple[str, str, str]] = set()

    def add_prop(nid: str, pred: str, val: str) -> None:
        slot = props.setdefault(nid, {})
        arr = slot.setdefault(pred, [])
        if val not in arr and len(arr) < 50:
            arr.append(val)

    for s, p, o in g:
        if isinstance(s, URIRef):
            sid = str(s)
            node_ids.add(sid)
            if isinstance(o, Literal):
                # Store as tooltip; optionally emit node for literals if requested
                add_prop(sid, short_label(str(p)), str(o))
                if include_literals:
                    lit_node = f"literal:{hash(o)}"
                    if (sid, str(p), lit_node) not in seen:
                        seen.add((sid, str(p), lit_node))
                        edge_triples.append((sid, str(p), lit_node))
                        node_ids.add(lit_node)
                continue
            if isinstance(o, URIRef):
                key = (sid, str(p), str(o))
                if key in seen:
                    continue
                seen.add(key)
                edge_triples.append((sid, str(p), str(o)))
                node_ids.add(str(o))
                if len(edge_triples) >= max_triples:
                    break
    return node_ids, edge_triples, props


def connected_components(nodes: Set[str], edges: List[Tuple[str, str, str]]) -> Dict[str, int]:
    adj: Dict[str, Set[str]] = {n: set() for n in nodes}
    for s, _p, o in edges:
        if s in adj: adj[s].add(o)
        else: adj[s] = {o}
        if o in adj: adj[o].add(s)
        else: adj[o] = {s}
    comp: Dict[str, int] = {}
    cid = 0
    for n in nodes:
        if n in comp: continue
        stack = [n]
        while stack:
            u = stack.pop()
            if u in comp: continue
            comp[u] = cid
            stack.extend(v for v in adj.get(u, ()) if v not in comp)
        cid += 1
    return comp


def main() -> None:
    ap = argparse.ArgumentParser(description="Render TTL to interactive HTML graph (PyVis)")
    ap.add_argument("ttl", nargs="?", default="", help="Path to TTL/NT/JSON-LD file. If omitted, you will be prompted.")
    ap.add_argument("--no-open", action="store_true", help="Do not open the HTML in a browser.")
    args = ap.parse_args()

    ttl_str = (args.ttl or "").strip() or input("Enter path to TTL file (.ttl): ").strip()
    ttl_path = Path(ttl_str).expanduser().resolve()
    if not ttl_path.exists():
        raise SystemExit(f"TTL not found: {ttl_path}")

    out_path = ttl_path.with_suffix(".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    g = load_graph(ttl_path)
    nodes, edges, props = build_subgraph(g, max_triples=12000, include_literals=False)

    # Degree for sizing
    degree: Dict[str, int] = {}
    for s, _p, o in edges:
        degree[s] = degree.get(s, 0) + 1
        degree[o] = degree.get(o, 0) + 1
    # Hierarchy levels by in-degree BFS from roots
    indegree: Dict[str, int] = {n: 0 for n in nodes}
    adj: Dict[str, Set[str]] = {n: set() for n in nodes}
    for s, _p, o in edges:
        adj.setdefault(s, set()).add(o)
        indegree[o] = indegree.get(o, 0) + 1
        indegree.setdefault(s, indegree.get(s, 0))
    roots = [n for n, d in indegree.items() if d == 0] or [
        n for n, d in indegree.items() if d == min(indegree.values())
    ]
    from collections import deque
    level: Dict[str, int] = {}
    dq = deque()
    for r in roots:
        level[r] = 0
        dq.append(r)
    while dq:
        u = dq.popleft()
        for v in adj.get(u, ()): 
            if v not in level:
                level[v] = level[u] + 1
                dq.append(v)
    for n in nodes:
        level.setdefault(n, 0)

    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]

    net = Network(height="800px", width="100%", directed=True, notebook=False, cdn_resources="in_line")
    net.set_options(json.dumps({
        "physics": {
            "enabled": True,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "springLength": 250,
                "springConstant": 0.08,
                "avoidOverlap": 1.0
            },
            "stabilization": {"enabled": True, "iterations": 150, "fit": True}
        },
        "interaction": {"hover": True, "navigationButtons": True},
        "edges": {"smooth": {"enabled": True, "type": "dynamic"}},
        "nodes": {"scaling": {"min": 6, "max": 28}}
    }))

    # Add nodes with tooltips
    for nid in nodes:
        label = short_label(nid) if not nid.startswith("literal:") else "literal"
        tip_lines: List[str] = []
        for k, vs in props.get(nid, {}).items():
            tip_lines.append(f"<b>{html.escape(k)}</b>: {html.escape(', '.join(vs))}")
        title = "<br/>".join(tip_lines) if tip_lines else html.escape(nid)
        lvl_color = palette[level.get(nid, 0) % len(palette)]
        net.add_node(nid, label=label, title=title, color=lvl_color, value=max(1, degree.get(nid, 1)))

    # Add edges with relation labels
    for s, p, o in edges:
        net.add_edge(s, o, label=short_label(p), title=p)

    try:
        net.write_html(str(out_path))
    except Exception:
        # Best-effort write only; do not auto-open
        pass
    if not args.no_open:
        try:
            webbrowser.open(out_path.as_uri())
        except Exception:
            pass
    print(f"Wrote interactive KG: {out_path}")


if __name__ == "__main__":
    main()


