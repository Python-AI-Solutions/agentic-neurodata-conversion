import argparse
import contextlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Optional


def _safe_import(module_name: str):
    try:
        return __import__(module_name)
    except Exception:
        return None


# Optional deps that we will only use when present
rdflib = _safe_import("rdflib")
if rdflib is not None:
    from rdflib import Graph as RDFGraph
    from rdflib import Literal, Namespace, URIRef
    from rdflib.namespace import RDF, RDFS, XSD
else:
    RDFGraph = None
    URIRef = None
    Literal = None
    Namespace = None
    RDF = None
    RDFS = None
    XSD = None

h5py = _safe_import("h5py")
yaml = _safe_import("yaml")
numpy_mod = _safe_import("numpy")

# nwbinspector is optional; if missing, we skip inspection
nwbinspector = _safe_import("nwbinspector")

# linkml-related optional modules
linkml_runtime = _safe_import("linkml_runtime")
if linkml_runtime is not None:
    from linkml_runtime.dumpers import yaml_dumper
else:
    yaml_dumper = None

linkml_generators = None
try:
    from linkml.generators.owlgen import OwlSchemaGenerator  # type: ignore

    linkml_generators = True
except Exception:
    OwlSchemaGenerator = None

nwb_linkml = _safe_import("nwb_linkml")
if nwb_linkml is not None:
    try:
        from nwb_linkml.adapters.namespaces import BuildResult, NamespacesAdapter
        from nwb_linkml.io import load_namespace_schema
        from nwb_linkml.namespaces import HDMF_COMMON_REPO, NWB_CORE_REPO, NamespaceRepo
    except Exception:
        load_namespace_schema = None
        NamespacesAdapter = None
        BuildResult = None
        NWB_CORE_REPO = None
        HDMF_COMMON_REPO = None
        NamespaceRepo = None
else:
    load_namespace_schema = None
    NamespacesAdapter = None
    BuildResult = None
    NWB_CORE_REPO = None
    HDMF_COMMON_REPO = None
    NamespaceRepo = None

nwb_schema_language = _safe_import("nwb_schema_language")
if nwb_schema_language is not None:
    try:
        from nwb_schema_language import Namespaces as NWBNamespaces
    except Exception:
        NWBNamespaces = None
else:
    NWBNamespaces = None


# ---------------------- Utility helpers ----------------------


def sanitize(name: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)


def label_for(g, node) -> str:
    if rdflib is None:
        return str(node)
    if isinstance(node, URIRef):
        for o in g.objects(node, RDFS.label):
            return str(o)
        s = str(node)
        if "#" in s:
            return s.rsplit("#", 1)[-1]
        if "/" in s:
            return s.rstrip("/").rsplit("/", 1)[-1]
        return s
    return str(node)


def guess_format(path: Path) -> Optional[str]:
    suf = path.suffix.lower()
    if suf in {".ttl"}:
        return "turtle"
    if suf in {".nt"}:
        return "nt"
    if suf in {".rdf", ".xml"}:
        return "xml"
    if suf in {".json", ".jsonld"}:
        return "json-ld"
    return None


# ---------------------- Inspector ----------------------


class EvalResult:
    def __init__(self, passed: bool, formatted_report: str, summary: str) -> None:
        self.passed = passed
        self.formatted_report = formatted_report
        self.summary = summary


def run_inspector(nwb_path: Path) -> EvalResult:
    if nwbinspector is None:
        return EvalResult(
            passed=True,
            formatted_report="nwbinspector not installed; skipping.",
            summary="skipped",
        )

    try:
        inspect_nwbfile = nwbinspector.inspect_nwbfile
        Importance = nwbinspector.Importance
        format_messages = nwbinspector.format_messages
    except Exception:
        return EvalResult(
            passed=True,
            formatted_report="nwbinspector import error; skipping.",
            summary="skipped",
        )

    messages = list(inspect_nwbfile(nwbfile_path=str(nwb_path)))
    formatted = format_messages(messages=messages)
    counts = {imp.name: 0 for imp in Importance}
    for m in messages:
        counts[m.importance.name] = counts.get(m.importance.name, 0) + 1
    failing_levels = {
        "CRITICAL",
        "BEST_PRACTICE_VIOLATION",
        "PYNWB_VALIDATION",
        "ERROR",
    }
    failed = any(counts.get(level, 0) > 0 for level in failing_levels)
    summary = ", ".join([f"{k}:{v}" for k, v in counts.items() if v > 0]) or "no issues"
    return EvalResult(
        passed=not failed, formatted_report="\n".join(formatted), summary=summary
    )


# ---------------------- LinkML generation (from NWB) ----------------------


def _load_namespaces_from_yaml(path: Path):
    if yaml is None or NWBNamespaces is None:
        raise RuntimeError("YAML or nwb_schema_language not available")
    with open(path) as fh:
        ns_dict = yaml.safe_load(fh)
    return NWBNamespaces(**ns_dict)


def build_linkml_from_core(
    core_commit: Optional[str] = None, hdmf_commit: Optional[str] = None
):
    if (
        NWB_CORE_REPO is None
        or HDMF_COMMON_REPO is None
        or load_namespace_schema is None
    ):
        raise RuntimeError("nwb_linkml not installed")
    hdmf_ns_file = HDMF_COMMON_REPO.provide_from_git(commit=hdmf_commit)
    core_ns_file = NWB_CORE_REPO.provide_from_git(commit=core_commit)
    hdmf_ns = _load_namespaces_from_yaml(hdmf_ns_file)
    core_ns = _load_namespaces_from_yaml(core_ns_file)
    hdmf_adapter = load_namespace_schema(hdmf_ns, hdmf_ns_file)
    core_adapter = load_namespace_schema(core_ns, core_ns_file)
    core_adapter.imported.append(hdmf_adapter)
    return core_adapter.build()


def build_linkml_from_core_with_extensions(
    extension_namespace_files: list[Path],
    core_commit: Optional[str] = None,
    hdmf_commit: Optional[str] = None,
):
    if (
        NWB_CORE_REPO is None
        or HDMF_COMMON_REPO is None
        or load_namespace_schema is None
    ):
        raise RuntimeError("nwb_linkml not installed")
    hdmf_ns_file = HDMF_COMMON_REPO.provide_from_git(commit=hdmf_commit)
    core_ns_file = NWB_CORE_REPO.provide_from_git(commit=core_commit)
    hdmf_ns = _load_namespaces_from_yaml(hdmf_ns_file)
    core_ns = _load_namespaces_from_yaml(core_ns_file)
    hdmf_adapter = load_namespace_schema(hdmf_ns, hdmf_ns_file)
    core_adapter = load_namespace_schema(core_ns, core_ns_file)
    for ext_file in extension_namespace_files:
        ext_ns = _load_namespaces_from_yaml(ext_file)
        ext_adapter = load_namespace_schema(ext_ns, ext_file)
        core_adapter.imported.append(ext_adapter)
    core_adapter.imported.append(hdmf_adapter)
    return core_adapter.build()


def detect_namespaces_in_nwb(nwb_file: Path) -> set[str]:
    if h5py is None:
        return set()
    namespaces: set[str] = set()
    with h5py.File(nwb_file, "r") as f:

        def visit(_name, obj):
            if hasattr(obj, "attrs"):
                for key, val in obj.attrs.items():
                    if key == "namespace":
                        try:
                            if isinstance(val, bytes):
                                namespaces.add(val.decode("utf-8"))
                            elif isinstance(val, str):
                                namespaces.add(val)
                            elif isinstance(val, (list, tuple)):
                                for v in val:
                                    if isinstance(v, bytes):
                                        namespaces.add(v.decode("utf-8"))
                                    elif isinstance(v, str):
                                        namespaces.add(v)
                        except Exception:
                            pass

        f.visititems(visit)
    return namespaces


def find_namespace_yaml_in_dir(root: Path, namespace_name: str) -> Optional[Path]:
    if yaml is None:
        return None
    for dirpath, _dirs, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith((".yaml", ".yml")):
                continue
            fp = Path(dirpath) / fn
            try:
                with open(fp) as fh:
                    data = yaml.safe_load(fh)
                if isinstance(data, dict) and "namespaces" in data:
                    nss = data.get("namespaces") or []
                    for ns in nss:
                        if isinstance(ns, dict) and ns.get("name") == namespace_name:
                            return fp
            except Exception:
                continue
    return None


def clone_repo(repo_url: str, tmp_dir: Path, commit: Optional[str] = None) -> Path:
    dst = tmp_dir / (Path(repo_url).stem)
    subprocess.run(["git", "clone", "--depth", "1", repo_url, str(dst)], check=True)
    if commit:
        try:
            subprocess.run(
                ["git", "-C", str(dst), "fetch", "--all", "--tags"], check=False
            )
            subprocess.run(["git", "-C", str(dst), "checkout", commit], check=True)
        except subprocess.CalledProcessError:
            print(f"Warning: could not checkout commit/tag {commit} in {repo_url}")
    return dst


def resolve_extension_namespaces(
    detected_namespaces: set[str],
    cache_dir: Path,
    auto_fetch_ndx: bool,
    offline: bool,
    ndx_repo_overrides: dict[str, str],
    ndx_commit_overrides: dict[str, str] | None = None,
) -> list[Path]:
    if yaml is None:
        return []
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    for ns in sorted(detected_namespaces):
        if ns in {"core", "hdmf-common"}:
            continue
        cached = find_namespace_yaml_in_dir(cache_dir, ns)
        if cached:
            out_paths.append(cached)
            continue
        if offline:
            print(f"[offline] Namespace '{ns}' not found in cache; skipping.")
            continue
        if auto_fetch_ndx:
            repo_url = (
                ndx_repo_overrides.get(ns)
                or f"https://github.com/nwb-extensions/{ns}.git"
            )
            commit = (ndx_commit_overrides or {}).get(ns)
            try:
                with tempfile.TemporaryDirectory(prefix="ndx_fetch_") as d:
                    repo_root = clone_repo(repo_url, Path(d), commit=commit)
                    yaml_path = find_namespace_yaml_in_dir(repo_root, ns)
                    if yaml_path:
                        ns_dir = cache_dir / ns
                        ns_dir.mkdir(parents=True, exist_ok=True)
                        dest = ns_dir / yaml_path.name
                        shutil.copy2(yaml_path, dest)
                        out_paths.append(dest)
                        continue
                    else:
                        print(
                            f"Could not find namespace YAML for '{ns}' in cloned repo {repo_url}"
                        )
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone {repo_url}: {e}")
    return out_paths


def write_monolithic_yaml(schemas: list, output_path: Path) -> None:
    if yaml_dumper is None:
        raise RuntimeError("linkml_runtime not installed")
    from linkml_runtime.linkml_model import SchemaDefinition

    class_by_name = {}
    slot_by_name = {}
    type_by_name = {}
    import_set = set()

    def to_items(coll):
        if coll is None:
            return []
        if isinstance(coll, dict):
            return list(coll.items())
        items = []
        for x in coll:
            name = getattr(x, "name", None)
            if name is None:
                name = str(x)
            items.append((name, x))
        return items

    for sch in schemas:
        if getattr(sch, "imports", None):
            import_set.update(sch.imports)
        for cname, c in to_items(getattr(sch, "classes", None)):
            class_by_name[cname] = c
        for sname, s in to_items(getattr(sch, "slots", None)):
            slot_by_name[sname] = s
        for tname, t in to_items(getattr(sch, "types", None)):
            type_by_name[tname] = t

    combined = SchemaDefinition(
        name=output_path.stem,
        id=output_path.stem,
        imports=sorted(import_set),
        classes=list(class_by_name.values()),
        slots=list(slot_by_name.values()),
        types=list(type_by_name.values()),
    )
    yaml_dumper.dump(combined, str(output_path))


def write_split_yaml(schemas: list, out_dir: Path) -> None:
    if yaml_dumper is None:
        raise RuntimeError("linkml_runtime not installed")
    out_dir.mkdir(parents=True, exist_ok=True)
    for sch in schemas:
        file_path = out_dir / f"{getattr(sch, 'name', 'schema')}.yaml"
        yaml_dumper.dump(sch, str(file_path))


# ---------------------- TTL and instance graph ----------------------


def make_base_uri(schema_dict: dict, nwb_path: Path) -> str:
    name = schema_dict.get("name") if isinstance(schema_dict, dict) else None
    stem = sanitize(name) if isinstance(name, str) and name else sanitize(nwb_path.stem)
    return f"http://example.org/{stem}#"


def path_to_uri(base: Namespace, h5_path: str) -> URIRef:
    if not h5_path or h5_path == "/":
        return URIRef(str(base) + "root")
    frag = sanitize(h5_path.strip("/")) or "root"
    return URIRef(str(base) + frag)


def make_literal(value) -> Optional[Literal]:
    try:
        np = numpy_mod
        if isinstance(value, (bytes, bytearray)):
            try:
                return Literal(value.decode("utf-8"))
            except Exception:
                return Literal(str(value))
        if np is not None and isinstance(value, np.generic):
            return Literal(value.item())
        if isinstance(value, (str, int, float, bool)):
            return Literal(value)
        if (
            isinstance(value, (list, tuple))
            and len(value) > 0
            and isinstance(value[0], (str, int, float, bool))
        ):
            return Literal(str(list(value)))
        s = str(value)
        if len(s) > 0:
            return Literal(s)
    except Exception:
        return None
    return None


def estimate_nbytes(arr) -> int:
    try:
        return int(getattr(arr, "nbytes", 0) or 0)
    except Exception:
        return 0


def add_values(
    g,
    subj: URIRef,
    pred: URIRef,
    arr,
    sample_limit: Optional[int],
    max_bytes: Optional[int] = None,
):
    np = numpy_mod
    try:
        flat = np.ravel(arr) if np is not None else arr
    except Exception:
        flat = arr
    values = []
    if hasattr(flat, "__len__") and not isinstance(flat, (bytes, str)):
        values = flat[:sample_limit] if sample_limit is not None else flat
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


def add_stats(g, subj: URIRef, EX: Namespace, dset, stats_inline_limit: int) -> None:
    np = numpy_mod
    try:
        data = dset[()]  # may be array-like
        if data is None:
            return
        arr = np.array(data) if np is not None else data
        with contextlib.suppress(Exception):
            g.add((subj, EX.stat_size, Literal(int(getattr(arr, "size", 0)))))
        try:
            if (
                np is not None
                and hasattr(arr, "dtype")
                and np.issubdtype(arr.dtype, np.number)
            ):
                g.add((subj, EX.stat_min, Literal(float(np.nanmin(arr)))))
                g.add((subj, EX.stat_max, Literal(float(np.nanmax(arr)))))
                g.add((subj, EX.stat_mean, Literal(float(np.nanmean(arr)))))
                g.add((subj, EX.stat_std, Literal(float(np.nanstd(arr)))))
        except Exception:
            pass
        try:
            if getattr(arr, "ndim", 0) == 0:
                lit = make_literal(data)
                if lit is not None:
                    g.add((subj, EX.hasValue, lit))
            elif getattr(arr, "ndim", 0) == 1 and int(getattr(arr, "size", 0)) <= int(
                stats_inline_limit
            ):
                count = 0
                for v in getattr(arr, "tolist", lambda: [])():
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
):
    if rdflib is None or h5py is None:
        raise RuntimeError("rdflib and h5py are required for TTL instance graph")
    g = RDFGraph()
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
                        g.add(
                            (
                                subj,
                                hasCompressionOpts,
                                Literal(str(obj.compression_opts)),
                            )
                        )
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
                try:
                    if hasattr(obj, "dims"):
                        for axis_index, dim in enumerate(obj.dims):
                            try:
                                label = getattr(dim, "label", None)
                                if (
                                    isinstance(label, (str, bytes))
                                    and len(str(label)) > 0
                                ):
                                    g.add(
                                        (
                                            subj,
                                            hasDimLabel,
                                            Literal(f"{axis_index}:{str(label)}"),
                                        )
                                    )
                            except Exception:
                                pass
                            try:
                                for scale in dim:
                                    scale_name = getattr(scale, "name", None)
                                    if (
                                        isinstance(scale_name, str)
                                        and len(scale_name) > 0
                                    ):
                                        g.add(
                                            (
                                                subj,
                                                hasDimScale,
                                                path_to_uri(BASE, scale_name),
                                            )
                                        )
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    np = numpy_mod
                    ref_dtype = h5py.check_dtype(ref=obj.dtype)
                    reg_dtype = h5py.check_dtype(regionref=obj.dtype)
                    if ref_dtype is not None or reg_dtype is not None:
                        vals = obj[()]
                        flat = np.ravel(vals) if np is not None else vals
                        for r in flat:
                            try:
                                if (
                                    ref_dtype is not None
                                    and isinstance(r, h5py.Reference)
                                    and r
                                ):
                                    target = obj.file[r].name
                                    g.add(
                                        (
                                            subj,
                                            hasReferenceTo,
                                            path_to_uri(BASE, target),
                                        )
                                    )
                                elif (
                                    reg_dtype is not None
                                    and isinstance(r, h5py.RegionReference)
                                    and r
                                ):
                                    dset = obj.file[r]
                                    g.add(
                                        (
                                            subj,
                                            hasRegionReferenceTo,
                                            path_to_uri(BASE, dset.name),
                                        )
                                    )
                            except Exception:
                                continue
                except Exception:
                    pass
                try:
                    if include_data == "full":
                        arr = obj[()]
                        if arr is not None and (
                            max_bytes is None
                            or max_bytes <= 0
                            or estimate_nbytes(arr) <= max_bytes
                        ):
                            add_values(g, subj, hasValue, arr, sample_limit=None)
                    elif include_data == "sample":
                        arr = obj[()]
                        if arr is not None:
                            add_values(
                                g,
                                subj,
                                hasValue,
                                arr,
                                sample_limit=sample_limit,
                                max_bytes=max_bytes,
                            )
                    elif include_data == "stats":
                        add_stats(g, subj, EX, obj, stats_inline_limit)
                except Exception:
                    pass

        def visit_children(name, obj):
            parent = path_to_uri(BASE, name)
            if isinstance(obj, (h5py.Group, h5py.File)):
                for child in obj:
                    child_path = (
                        name.rstrip("/") + "/" + child if name != "/" else "/" + child
                    )
                    child_uri = path_to_uri(BASE, child_path)
                    g.add((parent, hasChild, child_uri))
                    try:
                        link = obj.get(child, getlink=True)
                        if isinstance(link, h5py.SoftLink):
                            g.add((parent, hasSoftLinkTo, path_to_uri(BASE, link.path)))
                        elif isinstance(link, h5py.ExternalLink):
                            g.add(
                                (
                                    parent,
                                    hasExternalLinkTo,
                                    Literal(f"{link.filename}::{link.path}"),
                                )
                            )
                    except Exception:
                        pass

        f.visititems(visit)
        visit_children("/", f)
        f.visititems(visit_children)

    return g


def emit_llm_files(ttl_path: Path) -> tuple[Path, Path, Path]:
    if rdflib is None:
        raise RuntimeError("rdflib is required for NT/JSON-LD/triples generation")
    target_dir = ttl_path.parent
    stem = ttl_path.stem
    g = RDFGraph()
    g.parse(str(ttl_path), format="turtle")
    nt_path = target_dir / f"{stem}.nt"
    jsonld_path = target_dir / f"{stem}.jsonld"
    triples_path = target_dir / f"{stem}.triples.txt"
    g.serialize(destination=str(nt_path), format="nt")
    g.serialize(destination=str(jsonld_path), format="json-ld", indent=2)
    with open(triples_path, "w", encoding="utf-8") as f:
        for s, p, o in g:
            f.write(f"{label_for(g, s)}\t{label_for(g, p)}\t{label_for(g, o)}\n")
    return nt_path, jsonld_path, triples_path


# ---------------------- KG HTML rendering ----------------------


def build_subgraph(
    g: RDFGraph,
    max_triples: int = 8000,
    include_literals: bool = False,
) -> tuple[set[str], list[tuple[str, str, str]], dict[str, dict[str, list[str]]]]:
    node_ids: set[str] = set()
    edge_triples: list[tuple[str, str, str]] = []
    props: dict[str, dict[str, list[str]]] = {}
    seen: set[tuple[str, str, str]] = set()

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
                add_prop(sid, label_for(g, p), str(o))
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


def render_kg_html(
    ttl_path: Path, out_html: Optional[Path] = None, open_browser: bool = False
) -> Optional[Path]:
    if rdflib is None:
        return None
    try:
        from pyvis.network import Network
    except Exception:
        return None

    fmt = guess_format(ttl_path)
    g = RDFGraph()
    g.parse(str(ttl_path), format=fmt)
    nodes, edges, props = build_subgraph(g, max_triples=12000, include_literals=False)

    degree: dict[str, int] = {}
    for s, _p, o in edges:
        degree[s] = degree.get(s, 0) + 1
        degree[o] = degree.get(o, 0) + 1

    indegree: dict[str, int] = dict.fromkeys(nodes, 0)
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for s, _p, o in edges:
        adj.setdefault(s, set()).add(o)
        indegree[o] = indegree.get(o, 0) + 1
        indegree.setdefault(s, indegree.get(s, 0))
    roots = [n for n, d in indegree.items() if d == 0] or [
        n for n, d in indegree.items() if d == min(indegree.values())
    ]
    from collections import deque

    level: dict[str, int] = {}
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
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    net = Network(
        height="800px",
        width="100%",
        directed=True,
        notebook=False,
        cdn_resources="in_line",
    )
    net.set_options(
        json.dumps(
            {
                "physics": {
                    "enabled": True,
                    "solver": "forceAtlas2Based",
                    "forceAtlas2Based": {
                        "gravitationalConstant": -50,
                        "springLength": 250,
                        "springConstant": 0.08,
                        "avoidOverlap": 1.0,
                    },
                    "stabilization": {"enabled": True, "iterations": 150, "fit": True},
                },
                "interaction": {"hover": True, "navigationButtons": True},
                "edges": {"smooth": {"enabled": True, "type": "dynamic"}},
                "nodes": {"scaling": {"min": 6, "max": 28}},
            }
        )
    )

    for nid in nodes:
        label = (
            nid.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            if not str(nid).startswith("literal:")
            else "literal"
        )
        tip_lines: list[str] = []
        for k, vs in props.get(nid, {}).items():
            tip_lines.append(f"<b>{html.escape(k)}</b>: {html.escape(', '.join(vs))}")
        title = "<br/>".join(tip_lines) if tip_lines else html.escape(nid)
        lvl_color = palette[level.get(nid, 0) % len(palette)]
        net.add_node(
            nid,
            label=label,
            title=title,
            color=lvl_color,
            value=max(1, degree.get(nid, 1)),
        )

    for s, p, o in edges:
        net.add_edge(s, o, label=p.rsplit("#", 1)[-1].rsplit("/", 1)[-1], title=p)

    out_path = out_html or ttl_path.with_suffix(".html")
    with contextlib.suppress(Exception):
        net.write_html(str(out_path))
    if open_browser:
        try:
            import webbrowser

            webbrowser.open(out_path.as_uri())
        except Exception:
            pass
    return out_path


# ---------------------- Orchestration ----------------------


def generate_linkml_for_nwb(
    nwb_path: Path,
    cache_dir: Path,
    output: Path,
    auto_fetch_ndx: bool = True,
    offline: bool = False,
    ndx_repo_overrides: Optional[list[str]] = None,
    ndx_pin_overrides: Optional[list[str]] = None,
    pin_core: Optional[str] = None,
    pin_hdmf: Optional[str] = None,
) -> Optional[Path]:
    if nwb_linkml is None or linkml_runtime is None or nwb_schema_language is None:
        print(
            "[linkml] nwb_linkml or dependencies not installed; skipping LinkML generation."
        )
        return None

    provided_ns_files: list[Path] = []
    overrides: dict[str, str] = {}
    if ndx_repo_overrides:
        for item in ndx_repo_overrides:
            if "=" in item:
                key, val = item.split("=", 1)
                overrides[key.strip()] = val.strip()
    pin_overrides: dict[str, str] = {}
    if ndx_pin_overrides:
        for item in ndx_pin_overrides:
            if "=" in item:
                key, val = item.split("=", 1)
                pin_overrides[key.strip()] = val.strip()

    detected = detect_namespaces_in_nwb(nwb_path)
    resolved_exts = resolve_extension_namespaces(
        detected_namespaces=detected,
        cache_dir=cache_dir,
        auto_fetch_ndx=bool(auto_fetch_ndx),
        offline=bool(offline),
        ndx_repo_overrides=overrides,
        ndx_commit_overrides=pin_overrides,
    )
    all_ext_files = provided_ns_files + resolved_exts

    try:
        result = build_linkml_from_core_with_extensions(
            all_ext_files,
            core_commit=pin_core or None,
            hdmf_commit=pin_hdmf or None,
        )
    except Exception as e:
        print(f"[linkml] Proceeding despite build error: {e}")
        result = build_linkml_from_core(
            core_commit=pin_core or None, hdmf_commit=pin_hdmf or None
        )

    if output.suffix.lower() in (".yaml", ".yml"):
        write_monolithic_yaml(result.schemas, output)
        print(f"[linkml] Wrote monolithic schema: {output}")
        return output
    else:
        output.mkdir(parents=True, exist_ok=True)
        write_split_yaml(result.schemas, output)
        print(f"[linkml] Wrote split schemas to: {output}")
        return output


def generate_ttl(
    nwb_path: Path,
    schema: Optional[Path],
    out_ttl: Path,
    ontology: str = "none",
    data_mode: str = "stats",
    sample_limit: int = 50,
    max_bytes: int = 100_000_000,
    stats_inline_limit: int = 500,
) -> Path:
    if rdflib is None:
        raise RuntimeError("rdflib is required")

    # Ontology generation (if requested)
    onto_graph = RDFGraph()
    schema_dict = {}
    tmp_schema_path = None
    is_split_schema = False
    owl_ttl_path: Optional[Path] = None
    if ontology != "none" and schema is not None:
        schema_path = schema / "core.yaml" if schema.is_dir() else schema
        is_split_schema = (schema_path.name == "core.yaml") or (
            schema_path.parent.is_dir()
            and len(list(schema_path.parent.glob("*.yaml"))) > 1
        )

        def _sanitize_schema_dict(sd: dict) -> dict:
            candidate_names = set()
            slots_node = sd.get("slots")
            if isinstance(slots_node, dict):
                candidate_names.update(slots_node.keys())
            classes_node = sd.get("classes")
            if isinstance(classes_node, dict):
                for _k, cbody in classes_node.items():
                    if not isinstance(cbody, dict):
                        continue
                    attrs = cbody.get("attributes")
                    if isinstance(attrs, dict):
                        candidate_names.update(attrs.keys())
                        for abody in attrs.values():
                            if isinstance(abody, dict) and isinstance(
                                abody.get("name"), str
                            ):
                                candidate_names.add(abody["name"])
                            if isinstance(abody, dict) and isinstance(
                                abody.get("slot"), str
                            ):
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
                            if isinstance(sbody, dict) and isinstance(
                                sbody.get("slot"), str
                            ):
                                candidate_names.add(sbody["slot"])
            slot_renames = {}
            for old in candidate_names:
                new = sanitize(old)
                if new != old:
                    slot_renames[old] = new

            def rename_keys(d: dict) -> dict:
                new_d = {}
                for k, v in d.items():
                    nk = slot_renames.get(k, k)
                    new_d[nk] = v
                return new_d

            if isinstance(slots_node, dict) and slot_renames:
                new_slots = rename_keys(slots_node)
                for k, body in list(new_slots.items()):
                    if isinstance(body, dict):
                        body["name"] = k
                sd["slots"] = new_slots
            if isinstance(classes_node, dict) and slot_renames:
                for _ck, cbody in classes_node.items():
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
                                    abody["slot"] = slot_renames.get(
                                        sname, sanitize(sname)
                                    )
                        cbody["attributes"] = new_attrs
                    s_list = cbody.get("slots")
                    if isinstance(s_list, list):
                        cbody["slots"] = [
                            slot_renames.get(s, sanitize(s))
                            if isinstance(s, str)
                            else s
                            for s in s_list
                        ]
                    su = cbody.get("slot_usage")
                    if isinstance(su, dict):
                        new_su = rename_keys(su)
                        for _sk, sbody in list(new_su.items()):
                            if isinstance(sbody, dict) and isinstance(
                                sbody.get("slot"), str
                            ):
                                sname = sbody["slot"]
                                sbody["slot"] = slot_renames.get(sname, sanitize(sname))
                        cbody["slot_usage"] = new_su
            return sd

        if yaml is not None:
            if is_split_schema:
                sanitized_dir = Path(tempfile.mkdtemp(prefix="linkml_split_"))
                for yml in schema_path.parent.glob("*.yaml"):
                    with open(yml, encoding="utf-8") as fh:
                        d = yaml.safe_load(fh)
                    if isinstance(d, dict):
                        d = _sanitize_schema_dict(d)
                    with open(sanitized_dir / yml.name, "w", encoding="utf-8") as outfh:
                        yaml.safe_dump(d, outfh, sort_keys=False, allow_unicode=True)
                tmp_schema_path = str(sanitized_dir / schema_path.name)
                try:
                    with open(
                        sanitized_dir / schema_path.name, encoding="utf-8"
                    ) as _fh:
                        schema_dict = yaml.safe_load(_fh) or {}
                except Exception:
                    schema_dict = {"name": nwb_path.stem}
            else:
                with open(schema_path, encoding="utf-8") as fh:
                    schema_dict = yaml.safe_load(fh)
                if isinstance(schema_dict, dict):
                    schema_dict = _sanitize_schema_dict(schema_dict)
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".yaml", delete=False
                ) as tmp:
                    yaml.safe_dump(
                        schema_dict, tmp, sort_keys=False, allow_unicode=True
                    )
                    tmp_schema_path = tmp.name

        owl_ttl_path = out_ttl.with_name(f"{nwb_path.stem}.owl.ttl")
        # Try local OWL generation if available; otherwise use external python
        if tmp_schema_path:
            generated = False
            if OwlSchemaGenerator is not None:
                try:
                    gen = OwlSchemaGenerator(tmp_schema_path)  # type: ignore
                    gen.serialize(destination=str(owl_ttl_path), format="turtle")
                    generated = owl_ttl_path.exists()
                except Exception:
                    generated = False
            if not generated:
                # External generation via project venv or Anaconda
                repo_root = Path(__file__).resolve().parent
                ext_py = (
                    repo_root.parent
                    / "evaluation_agent"
                    / "file_generation"
                    / "nlk"
                    / "bin"
                    / "python"
                ).resolve()
                code = (
                    "from linkml.generators.owlgen import OwlSchemaGenerator; "
                    f"OwlSchemaGenerator(r'{tmp_schema_path}').serialize(destination=r'{str(owl_ttl_path)}', format='turtle')"
                )
                used = False
                try:
                    if ext_py.exists():
                        subprocess.run([str(ext_py), "-c", code], check=True)
                        used = owl_ttl_path.exists()
                except Exception:
                    used = False
                if not used:
                    conda_py = Path("/opt/anaconda3/bin/python3.12")
                    try:
                        if conda_py.exists():
                            subprocess.run([str(conda_py), "-c", code], check=True)
                            used = owl_ttl_path.exists()
                    except Exception:
                        used = False
        # Load ontology graph if produced
        try:
            if owl_ttl_path and owl_ttl_path.exists():
                onto_graph.parse(str(owl_ttl_path), format="turtle")
        except Exception:
            pass

    # Data/instance graph
    if data_mode != "none":
        base_uri = make_base_uri(schema_dict, nwb_path)
        data_graph = build_instance_graph(
            nwb_path=nwb_path,
            base_uri=base_uri,
            include_data=data_mode,
            sample_limit=sample_limit,
            max_bytes=max_bytes,
            stats_inline_limit=stats_inline_limit,
        )
    else:
        data_graph = RDFGraph()

    # Merge ontology (if any) and data
    if ontology == "none":
        data_graph.serialize(destination=str(out_ttl), format="turtle")
    else:
        try:
            onto_graph = RDFGraph()
            if out_ttl.exists():
                onto_graph.parse(str(out_ttl), format="turtle")
        except Exception:
            onto_graph = RDFGraph()
        merged = onto_graph + data_graph
        merged.serialize(destination=str(out_ttl), format="turtle")

    return out_ttl


def write_context_file(
    context_path: Path,
    nwb_path: Path,
    eval_result: EvalResult,
    data_outputs: Optional[dict[str, Path]] = None,
) -> None:
    context_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("NWB Evaluation Context")
    lines.append(f"File: {nwb_path}")
    lines.append(f"Decision: {'PASS' if eval_result.passed else 'FAIL'}")
    lines.append(f"Inspector counts: {eval_result.summary}")
    if data_outputs:
        lines.append("")
        lines.append("Data outputs:")
        lines.append(f" - TTL: {data_outputs.get('ttl')}")
        lines.append(f" - JSON-LD: {data_outputs.get('jsonld')}")
        lines.append(f" - triples.txt: {data_outputs.get('triples')}")
    lines.append("")
    lines.append("=== Inspector Report (verbatim) ===")
    lines.extend((eval_result.formatted_report or "").splitlines())
    context_path.write_text("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="All-in-one NWB evaluation and KG generator (single file)"
    )
    ap.add_argument(
        "--out-dir",
        default=str((Path(__file__).resolve().parent / "results").resolve()),
        help="Directory to write outputs",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing report/context files where applicable",
    )
    ap.add_argument(
        "--data",
        choices=["none", "stats", "sample", "full"],
        default="stats",
        help="Dataset values to include in TTL",
    )
    ap.add_argument(
        "--sample-limit", type=int, default=200, help="Sample size for --data=sample"
    )
    ap.add_argument(
        "--max-bytes",
        type=int,
        default=50_000_000,
        help="Max bytes to inline for dataset values",
    )
    ap.add_argument(
        "--stats-inline-limit",
        type=int,
        default=500,
        help="Max 1D elements to inline in stats mode",
    )
    ap.add_argument(
        "--ontology",
        choices=["none", "full"],
        default="none",
        help="Ontology include policy for TTL output",
    )
    ap.add_argument(
        "--schema",
        type=str,
        default="",
        help="Path to LinkML schema file or directory (optional). If provided with --ontology, it will be used.",
    )
    ap.add_argument(
        "--make-kg",
        action="store_true",
        help="[Deprecated] KG HTML is always generated if dependencies are available",
    )
    ap.add_argument(
        "--linkml",
        action="store_true",
        help="Attempt to generate LinkML schema(s) using nwb_linkml (optional)",
    )
    ap.add_argument(
        "--offline",
        action="store_true",
        help="Offline mode for extension resolution (no network)",
    )
    ap.add_argument(
        "--cache-dir",
        default=str((Path(__file__).resolve().parent / ".nwb_linkml_cache").resolve()),
        help="Cache dir for extension YAMLs",
    )
    args = ap.parse_args()

    nwb_in = input("Enter path to .nwb file: ").strip()
    nwb_path = Path(nwb_in).expanduser().resolve()
    if not nwb_path.exists():
        sys.exit(f"Path not found: {nwb_path}")

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Inspect
    eval_result = run_inspector(nwb_path)

    # 2) Optionally generate LinkML (split directory next to results for visibility)
    schema_dir: Optional[Path] = None
    if args.linkml:
        try:
            schema_dir = out_dir / f"{nwb_path.stem}.linkml"
            cache_dir = Path(args.cache_dir).expanduser().resolve()
            # Always (re)generate schema via external generator first
            if schema_dir.exists():
                with contextlib.suppress(Exception):
                    shutil.rmtree(schema_dir)
            repo_root = Path(__file__).resolve().parent
            ext_gen = (
                repo_root.parent
                / "evaluation_agent"
                / "file_generation"
                / "nwb_to_linkml"
                / "nwb_to_linkml.py"
            ).resolve()
            # 1) Project NLK venv
            try:
                ext_py = (
                    repo_root.parent
                    / "evaluation_agent"
                    / "file_generation"
                    / "nlk"
                    / "bin"
                    / "python"
                ).resolve()
                if ext_py.exists() and ext_gen.exists():
                    schema_dir.mkdir(parents=True, exist_ok=True)
                    cmd = [
                        str(ext_py),
                        str(ext_gen),
                        "--cache-dir",
                        str(cache_dir),
                        "--output",
                        str(schema_dir),
                    ]
                    print("[linkml] Using external generator:", " ".join(cmd))
                    subprocess.run(
                        cmd, input=(str(nwb_path) + "\n"), text=True, check=True
                    )
            except Exception:
                pass
            # 2) Anaconda fallback
            try:
                empty = not (schema_dir.exists() and any(schema_dir.glob("*.yaml")))
            except Exception:
                empty = True
            if empty:
                try:
                    conda_py = Path("/opt/anaconda3/bin/python3.12")
                    if conda_py.exists() and ext_gen.exists():
                        schema_dir.mkdir(parents=True, exist_ok=True)
                        cmd = [
                            str(conda_py),
                            str(ext_gen),
                            "--cache-dir",
                            str(cache_dir),
                            "--output",
                            str(schema_dir),
                        ]
                        print("[linkml] Using anaconda generator:", " ".join(cmd))
                        subprocess.run(
                            cmd, input=(str(nwb_path) + "\n"), text=True, check=True
                        )
                except Exception:
                    pass
            # 3) If still no schema, continue without ontology
            try:
                if not (schema_dir.exists() and any(schema_dir.glob("*.yaml"))):
                    print(
                        "[linkml] generation unavailable; continuing without ontology"
                    )
                    schema_dir = None
            except Exception:
                schema_dir = None
        except Exception as e:
            print(f"[linkml] generation failed: {e}")
            schema_dir = None

    # If user provided --schema, prefer it
    if isinstance(getattr(args, "schema", ""), str) and args.schema.strip():
        cand = Path(args.schema.strip()).expanduser().resolve()
        if cand.exists():
            # If directory, try to find an entry file (core.yaml or *core*.yaml)
            if cand.is_dir():
                entry = cand / "core.yaml"
                if not entry.exists():
                    # pick a best-effort core-like file
                    picks = list(cand.glob("*core*.yaml")) + list(
                        cand.glob("*nwb*.yaml")
                    )
                    if picks:
                        entry = picks[0]
                schema_dir = entry.parent if entry.exists() else cand
            else:
                schema_dir = cand

    # 3) Generate data TTL (ontology per flag)
    data_ttl = out_dir / f"{nwb_path.stem}.data.ttl"
    if data_ttl.exists() and not args.overwrite:
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_ttl = data_ttl.with_name(f"{nwb_path.stem}.data_{ts}.ttl")
    try:
        out_ttl = generate_ttl(
            nwb_path=nwb_path,
            schema=schema_dir,
            out_ttl=data_ttl,
            ontology=args.ontology,
            data_mode=args.data,
            sample_limit=args.sample_limit,
            max_bytes=args.max_bytes,
            stats_inline_limit=args.stats_inline_limit,
        )
    except Exception as e:
        print(f"[ttl] generation failed: {e}")
        out_ttl = None

    # 4) Emit NT/JSON-LD/triples for data TTL
    data_outputs = {}
    if out_ttl and out_ttl.exists():
        try:
            nt_path, jsonld_path, triples_path = emit_llm_files(out_ttl)
            data_outputs = {
                "ttl": out_ttl,
                "jsonld": jsonld_path,
                "triples": triples_path,
            }
        except Exception as e:
            print(f"[llm-files] failed: {e}")

    # 5) KG HTML (always attempt)
    if out_ttl and out_ttl.exists():
        try:
            kg_path = render_kg_html(out_ttl, open_browser=False)
            if kg_path:
                print(f"Wrote interactive KG: {kg_path}")
        except Exception:
            pass

    # 6) Context file
    context_path = out_dir / f"{nwb_path.stem}_context.txt"
    if context_path.exists() and not args.overwrite:
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        context_path = context_path.with_name(f"{nwb_path.stem}_context_{ts}.txt")
    write_context_file(
        context_path, nwb_path, eval_result, data_outputs if data_outputs else None
    )
    print(f"Saved context: {context_path}")
    if out_ttl:
        print(f"Data TTL: {out_ttl}")


if __name__ == "__main__":
    main()
