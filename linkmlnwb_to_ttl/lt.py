#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess
import shutil
import os

import yaml
import tempfile
import re
import math
from typing import Optional

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD


def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)


def make_base_uri(schema_dict: dict, nwb_path: Path) -> str:
    name = schema_dict.get("name") if isinstance(schema_dict, dict) else None
    if isinstance(name, str) and name:
        stem = sanitize(name)
    else:
        stem = sanitize(nwb_path.stem)
    return f"http://example.org/{stem}#"


def path_to_uri(base: Namespace, h5_path: str) -> URIRef:
    if not h5_path or h5_path == "/":
        return URIRef(str(base) + "root")
    frag = sanitize(h5_path.strip("/")) or "root"
    return URIRef(str(base) + frag)


def make_literal(value) -> Optional[Literal]:
    try:
        import numpy as np
        if isinstance(value, (bytes, bytearray)):
            try:
                return Literal(value.decode("utf-8"))
            except Exception:
                return Literal(str(value))
        if isinstance(value, np.generic):
            return Literal(value.item())
        if isinstance(value, (str, int, float, bool)):
            return Literal(value)
        if isinstance(value, (list, tuple)) and len(value) > 0 and isinstance(value[0], (str, int, float, bool)):
            return Literal(str(list(value)))
        s = str(value)
        if len(s) > 0:
            return Literal(s)
    except Exception:
        return None
    return None


def estimate_nbytes(arr) -> int:
    try:
        import numpy as np  # noqa: F401
        return int(getattr(arr, "nbytes", 0) or 0)
    except Exception:
        return 0


def add_values(g: Graph, subj: URIRef, pred: URIRef, arr, sample_limit: Optional[int], max_bytes: Optional[int] = None):
    import numpy as np
    try:
        flat = np.ravel(arr)
    except Exception:
        flat = arr
    values = []
    if hasattr(flat, "__len__") and not isinstance(flat, (bytes, str)):
        if sample_limit is not None:
            values = flat[:sample_limit]
        else:
            values = flat
    else:
        values = [flat]
    total = 0
    for v in values:
        lit = make_literal(v)
        if lit is None:
            continue
        g.add((subj, pred, lit))
        if max_bytes is not None:
            total += len(str(lit))
            if total >= max_bytes:
                break


def add_stats(g: Graph, subj: URIRef, EX: Namespace, dset, stats_inline_limit: int) -> None:
    import numpy as np
    try:
        data = dset[()]  # may be array-like
        if data is None:
            return
        arr = np.array(data)
        # Always include size when available
        try:
            g.add((subj, EX.stat_size, Literal(int(arr.size))))
        except Exception:
            pass
        # Numeric summary statistics
        try:
            if np.issubdtype(arr.dtype, np.number):
                g.add((subj, EX.stat_min, Literal(float(np.nanmin(arr)))))
                g.add((subj, EX.stat_max, Literal(float(np.nanmax(arr)))))
                g.add((subj, EX.stat_mean, Literal(float(np.nanmean(arr)))))
                g.add((subj, EX.stat_std, Literal(float(np.nanstd(arr)))))
        except Exception:
            pass
        # Inline small arrays or scalars
        try:
            # Scalar: always inline
            if getattr(arr, "ndim", 0) == 0:
                lit = make_literal(data)
                if lit is not None:
                    g.add((subj, EX.hasValue, lit))
            # 1D arrays: inline up to stats_inline_limit elements
            elif getattr(arr, "ndim", 0) == 1 and int(arr.size) <= int(stats_inline_limit):
                count = 0
                for v in arr.tolist():
                    lit = make_literal(v)
                    if lit is not None:
                        g.add((subj, EX.hasValue, lit))
                        count += 1
                    if count >= stats_inline_limit:
                        break
        except Exception:
            pass
    except Exception:
        pass


def build_instance_graph(
    nwb_path: Path,
    base_uri: str,
    include_data: str,
    sample_limit: int,
    max_bytes: int,
    stats_inline_limit: int,
) -> Graph:
    import h5py

    g = Graph()
    BASE = Namespace(base_uri)
    EX = BASE

    Group = EX.Group
    Dataset = EX.Dataset
    hasChild = EX.hasChild
    hasShape = EX.hasShape
    hasDType = EX.hasDType
    hasValue = EX.hasValue
    hasChunks = EX.hasChunks
    hasCompression = EX.hasCompression
    hasCompressionOpts = EX.hasCompressionOpts
    hasFillValue = EX.hasFillValue
    hasMaxShape = EX.hasMaxShape
    hasScaleOffset = EX.hasScaleOffset
    hasShuffle = EX.hasShuffle
    hasFletcher32 = EX.hasFletcher32
    hasDimLabel = EX.hasDimLabel
    hasDimScale = EX.hasDimScale
    hasSoftLinkTo = EX.hasSoftLinkTo
    hasExternalLinkTo = EX.hasExternalLinkTo
    hasReferenceTo = EX.hasReferenceTo
    hasRegionReferenceTo = EX.hasRegionReferenceTo

    with h5py.File(nwb_path, "r") as f:
        # Explicitly add root group and its attributes
        root_subj = path_to_uri(BASE, "/")
        g.add((root_subj, RDF.type, Group))
        try:
            for ak, av in f.attrs.items():
                pred = URIRef(str(EX) + f"attr_{sanitize(str(ak))}")
                lit = make_literal(av)
                if lit is not None:
                    g.add((root_subj, pred, lit))
        except Exception:
            pass

        def visit(name, obj):
            subj = path_to_uri(BASE, name)
            if isinstance(obj, h5py.Group):
                g.add((subj, RDF.type, Group))
                for ak, av in obj.attrs.items():
                    pred = URIRef(str(EX) + f"attr_{sanitize(str(ak))}")
                    lit = make_literal(av)
                    if lit is not None:
                        g.add((subj, pred, lit))
            else:
                g.add((subj, RDF.type, Dataset))
                try:
                    dstr = str(obj.dtype)
                    g.add((subj, hasDType, Literal(dstr)))
                except Exception:
                    pass
                try:
                    shp = tuple(obj.shape) if obj.shape is not None else ()
                    g.add((subj, hasShape, Literal(str(shp))))
                except Exception:
                    pass
                # Dataset storage metadata
                try:
                    if getattr(obj, "chunks", None) is not None:
                        g.add((subj, hasChunks, Literal(str(obj.chunks))))
                except Exception:
                    pass
                try:
                    if getattr(obj, "compression", None) is not None:
                        g.add((subj, hasCompression, Literal(str(obj.compression))))
                except Exception:
                    pass
                try:
                    if getattr(obj, "compression_opts", None) is not None:
                        g.add((subj, hasCompressionOpts, Literal(str(obj.compression_opts))))
                except Exception:
                    pass
                try:
                    if hasattr(obj, "fillvalue"):
                        fv = obj.fillvalue
                        if fv is not None:
                            lit = make_literal(fv)
                            if lit is not None:
                                g.add((subj, hasFillValue, lit))
                except Exception:
                    pass
                try:
                    if getattr(obj, "maxshape", None) is not None:
                        g.add((subj, hasMaxShape, Literal(str(obj.maxshape))))
                except Exception:
                    pass
                try:
                    if getattr(obj, "scaleoffset", None) is not None:
                        g.add((subj, hasScaleOffset, Literal(str(obj.scaleoffset))))
                except Exception:
                    pass
                try:
                    if getattr(obj, "shuffle", None) is not None:
                        g.add((subj, hasShuffle, Literal(bool(obj.shuffle))))
                except Exception:
                    pass
                try:
                    if getattr(obj, "fletcher32", None) is not None:
                        g.add((subj, hasFletcher32, Literal(bool(obj.fletcher32))))
                except Exception:
                    pass
                for ak, av in obj.attrs.items():
                    pred = URIRef(str(EX) + f"attr_{sanitize(str(ak))}")
                    lit = make_literal(av)
                    if lit is not None:
                        g.add((subj, pred, lit))
                # Dimension labels and scales
                try:
                    if hasattr(obj, "dims"):
                        for axis_index, dim in enumerate(obj.dims):
                            try:
                                label = getattr(dim, "label", None)
                                if isinstance(label, (str, bytes)) and len(str(label)) > 0:
                                    g.add((subj, hasDimLabel, Literal(f"{axis_index}:{str(label)}")))
                            except Exception:
                                pass
                            try:
                                for scale in dim:
                                    scale_name = getattr(scale, "name", None)
                                    if isinstance(scale_name, str) and len(scale_name) > 0:
                                        g.add((subj, hasDimScale, path_to_uri(BASE, scale_name)))
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    if include_data == "full":
                        arr = obj[()]
                        if arr is not None and (max_bytes is None or max_bytes <= 0 or estimate_nbytes(arr) <= max_bytes):
                            add_values(g, subj, hasValue, arr, sample_limit=None)
                    elif include_data == "sample":
                        arr = obj[()]
                        if arr is not None:
                            add_values(g, subj, hasValue, arr, sample_limit=sample_limit, max_bytes=max_bytes)
                    elif include_data == "stats":
                        add_stats(g, subj, EX, obj, stats_inline_limit)
                except Exception:
                    pass

                # Extract object and region references
                try:
                    import numpy as np
                    import h5py as _h5
                    ref_dtype = _h5.check_dtype(ref=obj.dtype)
                    reg_dtype = _h5.check_dtype(regionref=obj.dtype)
                    if ref_dtype is not None or reg_dtype is not None:
                        vals = obj[()]
                        flat = np.ravel(vals)
                        for r in flat:
                            try:
                                # Object reference
                                if ref_dtype is not None and isinstance(r, _h5.Reference) and r:
                                    target = obj.file[r].name
                                    g.add((subj, hasReferenceTo, path_to_uri(BASE, target)))
                                # Region reference
                                elif reg_dtype is not None and isinstance(r, _h5.RegionReference) and r:
                                    # dataset that the region refers to
                                    dset = obj.file[r]
                                    g.add((subj, hasRegionReferenceTo, path_to_uri(BASE, dset.name)))
                            except Exception:
                                continue
                except Exception:
                    pass
        def visit_children(name, obj):
            parent = path_to_uri(BASE, name)
            if isinstance(obj, (h5py.Group, h5py.File)):
                for child in obj.keys():
                    child_path = name.rstrip("/") + "/" + child if name != "/" else "/" + child
                    child_uri = path_to_uri(BASE, child_path)
                    g.add((parent, hasChild, child_uri))
                    # Capture link types (soft/external)
                    try:
                        link = obj.get(child, getlink=True)
                        import h5py as _h5
                        if isinstance(link, _h5.SoftLink):
                            g.add((parent, hasSoftLinkTo, path_to_uri(BASE, link.path)))
                        elif isinstance(link, _h5.ExternalLink):
                            g.add((parent, hasExternalLinkTo, Literal(f"{link.filename}::{link.path}")))
                    except Exception:
                        pass
        f.visititems(visit)
        # Add root -> first-level children edges
        visit_children("/", f)
        f.visititems(visit_children)
    return g


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an OWL TTL from a LinkML YAML schema derived from an NWB file.")
    parser.add_argument("input", nargs="?", default="", help="Path to NWB file (.nwb). If omitted, you will be prompted.")
    parser.add_argument("--schema", type=str, default="", help="Path to LinkML YAML schema. Defaults to <input>.linkml.yaml; will be auto-generated if missing.")
    parser.add_argument("--output", type=str, default="", help="Output TTL path. Defaults to <input>.ttl")
    parser.add_argument("--data", type=str, choices=["none","stats","sample","full"], default="stats", help="How much dataset data to embed as triples.")
    parser.add_argument("--ontology", type=str, choices=["full","used","none"], default="none", help="Ontology to include: full LinkML OWL, used-only terms, or none (default: none).")
    parser.add_argument("--sample-limit", type=int, default=50, help="Max number of elements per dataset when --data=sample.")
    parser.add_argument("--max-bytes", type=int, default=100_000_000_000, help="Hard cap on bytes per dataset values (<=0 means unlimited).")
    parser.add_argument("--stats-inline-limit", type=int, default=500, help="In stats mode, inline up to N elements for 1D arrays.")
    args = parser.parse_args()

    # Resolve NWB input (prompt if missing)
    nwb_str = args.input.strip() if isinstance(args.input, str) else ""
    if not nwb_str:
        nwb_str = input("Enter path to NWB file (.nwb): ").strip()
    nwb_path = Path(nwb_str).expanduser().resolve()
    if not nwb_path.exists():
        raise SystemExit(f"Input file not found: {nwb_path}")

    # If data-only, skip schema resolution entirely
    if args.ontology == "none":
        # Resolve output TTL path
        if args.output:
            out_path = Path(args.output).expanduser().resolve()
        else:
            out_path = nwb_path.with_suffix("").with_suffix(".ttl")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        base_uri = make_base_uri({}, nwb_path)
        data_graph = build_instance_graph(
            nwb_path=nwb_path,
            base_uri=base_uri,
            include_data=args.data,
            sample_limit=args.sample_limit,
            max_bytes=args.max_bytes,
            stats_inline_limit=args.stats_inline_limit,
        )
        data_graph.serialize(destination=str(out_path), format="turtle")
        print(f"Wrote TTL: {out_path}")
        return

    # Resolve schema path (support split-schema directory with core.yaml)
    if args.schema:
        schema_candidate = Path(args.schema).expanduser().resolve()
        if schema_candidate.is_dir():
            schema_path = schema_candidate / "core.yaml"
        else:
            schema_path = schema_candidate
    else:
        split_dir = nwb_path.with_suffix("").with_suffix(".linkml")
        if split_dir.exists() and split_dir.is_dir():
            schema_path = split_dir / "core.yaml"
        else:
            schema_path = nwb_path.with_suffix("").with_suffix(".linkml.yaml")

    # Auto-generate schema if missing using the local generator (if available)
    if not schema_path.exists():
        gen_script = Path("/Users/adityapatane/nlk2/nwb_to_linkml/n.py")
        gen_python = Path("/Users/adityapatane/nlk2/.venv312/bin/python")
        if gen_script.exists() and gen_python.exists():
            # Let generator produce split schema by default; then use core.yaml
            out_dir = nwb_path.with_suffix("").with_suffix(".linkml")
            out_dir.mkdir(parents=True, exist_ok=True)
            cmd = [str(gen_python), str(gen_script), str(nwb_path), "--cache-dir", str(Path("/Users/adityapatane/nlk2/.nwb_linkml_cache").expanduser().resolve())]
            print("Generating LinkML schema via:", " ".join(cmd))
            subprocess.run(cmd, check=True)
            schema_path = out_dir / "core.yaml"
        else:
            raise SystemExit(f"Schema not found and generator unavailable: expected {schema_path} or split dir {nwb_path.with_suffix('').with_suffix('.linkml')}")

    # Resolve output TTL path
    if args.output:
        out_path = Path(args.output).expanduser().resolve()
    else:
        out_path = nwb_path.with_suffix("").with_suffix(".ttl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Decide whether we are working with a split schema (core.yaml + parts)
    is_split_schema = schema_path.name == "core.yaml" or (schema_path.parent.is_dir() and len(list(schema_path.parent.glob("*.yaml"))) > 1)

    def sanitize_schema_dict(schema_dict: dict) -> dict:
        # Sanitize slot and attribute names to be URI-safe
        def sanitize_local(name: str) -> str:
            return sanitize(name)

        candidate_names = set()
        slots_node = schema_dict.get("slots")
        if isinstance(slots_node, dict):
            candidate_names.update(slots_node.keys())

        classes_node = schema_dict.get("classes")
        if isinstance(classes_node, dict):
            for _, cbody in classes_node.items():
                if not isinstance(cbody, dict):
                    continue
                attrs = cbody.get("attributes")
                if isinstance(attrs, dict):
                    candidate_names.update(attrs.keys())
                    for abody in attrs.values():
                        if isinstance(abody, dict) and isinstance(abody.get("name"), str):
                            candidate_names.add(abody["name"])
                        if isinstance(abody, dict) and isinstance(abody.get("slot"), str):
                            candidate_names.add(abody["slot"])
                s_list = cbody.get("slots")
                if isinstance(s_list, list):
                    for s in s_list:
                        if isinstance(s, str):
                            candidate_names.add(s)
                su = cbody.get("slot_usage")
                if isinstance(su, dict):
                    candidate_names.update(su.keys())
                    for sbody in su.values():
                        if isinstance(sbody, dict) and isinstance(sbody.get("slot"), str):
                            candidate_names.add(sbody["slot"])

        # Build rename map
        slot_renames = {}
        for old in candidate_names:
            new = sanitize_local(old)
            if new != old:
                slot_renames[old] = new

        def rename_keys(d: dict) -> dict:
            new_d = {}
            for k, v in d.items():
                nk = slot_renames.get(k, k)
                new_d[nk] = v
            return new_d

        # Apply renames in slots
        if isinstance(slots_node, dict) and slot_renames:
            new_slots = rename_keys(slots_node)
            for k, body in list(new_slots.items()):
                if isinstance(body, dict):
                    body["name"] = k
            schema_dict["slots"] = new_slots

        # Apply renames in classes
        if isinstance(classes_node, dict) and slot_renames:
            for _, cbody in classes_node.items():
                if not isinstance(cbody, dict):
                    continue
                attrs = cbody.get("attributes")
                if isinstance(attrs, dict):
                    new_attrs = rename_keys(attrs)
                    for aname, abody in list(new_attrs.items()):
                        if isinstance(abody, dict):
                            abody["name"] = aname
                            if isinstance(abody.get("slot"), str):
                                sname = abody["slot"]
                                abody["slot"] = slot_renames.get(sname, sanitize_local(sname))
                    cbody["attributes"] = new_attrs

                s_list = cbody.get("slots")
                if isinstance(s_list, list):
                    cbody["slots"] = [slot_renames.get(s, sanitize_local(s)) if isinstance(s, str) else s for s in s_list]

                su = cbody.get("slot_usage")
                if isinstance(su, dict):
                    new_su = rename_keys(su)
                    for sk, sbody in list(new_su.items()):
                        if isinstance(sbody, dict) and isinstance(sbody.get("slot"), str):
                            sname = sbody["slot"]
                            sbody["slot"] = slot_renames.get(sname, sanitize_local(sname))
                    cbody["slot_usage"] = new_su
        return schema_dict

    # Prepare sanitized schema input for OWL generator
    if is_split_schema:
        # Sanitize all YAML files into a persistent temporary directory to keep imports consistent
        import shutil as _shutil
        sanitized_dir = Path(tempfile.mkdtemp(prefix="linkml_split_"))
        for yml in schema_path.parent.glob("*.yaml"):
            with open(yml, "r", encoding="utf-8") as fh:
                d = yaml.safe_load(fh)
            if isinstance(d, dict):
                d = sanitize_schema_dict(d)
            with open(sanitized_dir / yml.name, "w", encoding="utf-8") as outfh:
                yaml.safe_dump(d, outfh, sort_keys=False, allow_unicode=True)
        tmp_schema_path = str(sanitized_dir / schema_path.name)
        # Load sanitized core schema to seed base_uri name
        try:
            with open(sanitized_dir / schema_path.name, "r", encoding="utf-8") as _fh:
                schema_dict = yaml.safe_load(_fh) or {}
        except Exception:
            schema_dict = {"name": nwb_path.stem}
        # Generate OWL TTL from the adjusted LinkML schema (split)
        from linkml.generators.owlgen import OwlSchemaGenerator
        gen = OwlSchemaGenerator(tmp_schema_path)
        gen.serialize(destination=str(out_path), format="turtle")
        if not out_path.exists():
            try:
                g = gen.as_graph()
                with tempfile.NamedTemporaryFile("wb", suffix=".ttl", delete=False) as tf:
                    tmp_out = Path(tf.name)
                    g.serialize(destination=str(tmp_out), format="turtle")
                tmp_out.replace(out_path)
            except Exception:
                pass
    else:
        sanitized_dir = None
    # Monolithic path
        with open(schema_path, "r", encoding="utf-8") as fh:
            schema_dict = yaml.safe_load(fh)
        if isinstance(schema_dict, dict):
            schema_dict = sanitize_schema_dict(schema_dict)
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
            yaml.safe_dump(schema_dict, tmp, sort_keys=False, allow_unicode=True)
            tmp_schema_path = tmp.name

    onto_graph = Graph()
    if args.ontology != "none":
        # Generate OWL TTL from the adjusted LinkML schema
        # Lazy import to avoid environment issues until needed
        from linkml.generators.owlgen import OwlSchemaGenerator
        gen = OwlSchemaGenerator(tmp_schema_path)
        # Try direct serialize
        gen.serialize(destination=str(out_path), format="turtle")
        # Ensure file exists; if not, force via rdflib Graph
        if not out_path.exists():
            try:
                g = gen.as_graph()
                with tempfile.NamedTemporaryFile("wb", suffix=".ttl", delete=False) as tf:
                    tmp_out = Path(tf.name)
                    g.serialize(destination=str(tmp_out), format="turtle")
                tmp_out.replace(out_path)
            except Exception:
                pass

    # Build instance graph only if requested
    if args.data != "none":
        base_uri = make_base_uri(schema_dict, nwb_path)
        data_graph = build_instance_graph(
            nwb_path=nwb_path,
            base_uri=base_uri,
            include_data=args.data,
            sample_limit=args.sample_limit,
            max_bytes=args.max_bytes,
            stats_inline_limit=args.stats_inline_limit,
        )
    else:
        data_graph = Graph()

    if args.ontology == "full":
        try:
            onto_graph = gen.as_graph()
        except Exception:
            onto_graph = Graph()
            onto_graph.parse(str(out_path), format="turtle")
    elif args.ontology == "used":
        # Load full ontology then prune to terms used in instance data
        try:
            full_onto = gen.as_graph()
        except Exception:
            full_onto = Graph()
            full_onto.parse(str(out_path), format="turtle")

        def expand_ancestors(g: Graph, seeds: set, predicate: URIRef) -> set:
            changed = True
            result = set(seeds)
            while changed:
                changed = False
                to_add = set()
                for n in list(result):
                    for _, _, o in g.triples((URIRef(n), predicate, None)):
                        if isinstance(o, URIRef) and str(o) not in result:
                            to_add.add(str(o))
                if to_add:
                    result.update(to_add)
                    changed = True
            return result

        # Terms used in data
        used_classes = {str(o) for _s, _p, o in data_graph.triples((None, RDF.type, None)) if isinstance(o, URIRef)}
        used_properties = {str(p) for _s, p, _o in data_graph if isinstance(p, URIRef)}

        # Expand with ancestors and property domain/range classes
        used_classes = expand_ancestors(full_onto, used_classes, RDFS.subClassOf)
        used_properties = expand_ancestors(full_onto, used_properties, RDFS.subPropertyOf)

        # Domains/ranges of properties
        for pid in list(used_properties):
            for _s, _p, o in full_onto.triples((URIRef(pid), RDFS.domain, None)):
                if isinstance(o, URIRef):
                    used_classes.add(str(o))
            for _s, _p, o in full_onto.triples((URIRef(pid), RDFS.range, None)):
                if isinstance(o, URIRef):
                    used_classes.add(str(o))
        used_classes = expand_ancestors(full_onto, used_classes, RDFS.subClassOf)

        # Build pruned ontology: include all triples whose subject is a used class or property,
        # plus any blank-node structures reachable within depth 2 from those subjects
        onto_graph = Graph()
        seeds = {URIRef(u) for u in used_classes.union(used_properties)}
        visited = set()
        from collections import deque
        dq = deque([(s, 0) for s in seeds])
        max_depth = 2
        while dq:
            node, depth = dq.popleft()
            if (node, depth) in visited or depth > max_depth:
                continue
            visited.add((node, depth))
            for s, p, o in full_onto.triples((node, None, None)):
                onto_graph.add((s, p, o))
                if depth < max_depth:
                    if hasattr(o, 'startswith'):
                        # not reliable for URIRef; fall through
                        pass
                    dq.append((o, depth + 1))
            # Also keep superclass/subproperty incoming statements that reference this node
            for s, p, o in full_onto.triples((None, RDFS.subClassOf, node)):
                onto_graph.add((s, p, o))
            for s, p, o in full_onto.triples((None, RDFS.subPropertyOf, node)):
                onto_graph.add((s, p, o))

    # Serialize: if ontology requested and data==none → ontology-only
    if args.data == "none":
        onto_graph.serialize(destination=str(out_path), format="turtle")
    else:
        merged = onto_graph + data_graph
        merged.serialize(destination=str(out_path), format="turtle")

    print(f"Wrote TTL: {out_path}")


if __name__ == "__main__":
    main()


