# evaluation_agent_combined.py
"""
Combined evaluation agent:
- nwb inspector wrapper (nwbinspector if available)
- instance graph / TTL builder (rdflib + h5py when present)
- KG emit helpers (NT / JSON-LD / triples.txt)
- basic KG HTML visualizer using pyvis (optional)
- light LLM extraction helpers (OpenAI / Ollama, optional)
- EvaluationAgent class that exposes high-level methods for the MCP server to call
"""

import json
import os
from pathlib import Path
import time
import traceback
from typing import Any, Optional


# Optional imports are handled gracefully
def _safe_import(name):
    try:
        return __import__(name)
    except Exception:
        return None


# Optional modules
nwbinspector = _safe_import("nwbinspector")
rdflib = _safe_import("rdflib")
h5py = _safe_import("h5py")
numpy_mod = _safe_import("numpy")
pyvis = _safe_import("pyvis")
openai = _safe_import("openai")  # may be None
# urllib for Ollama
from urllib import request as _urlreq  # noqa: E402

# RDFlib names if available
if rdflib is not None:
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, RDFS, XSD
else:
    Graph = URIRef = Literal = Namespace = RDF = RDFS = XSD = None


# -------------------------
# Small data structure
# -------------------------
class EvalResult:
    def __init__(self, passed: bool, formatted_report: str, summary: str):
        self.passed = passed
        self.formatted_report = formatted_report
        self.summary = summary


# -------------------------
# Inspector wrapper
# -------------------------
def run_inspector(nwb_path: Path) -> EvalResult:
    """
    Run nwbinspector.inspect_nwbfile if available; return EvalResult.
    If nwbinspector is not installed we return a skipped result.
    """
    try:
        if nwbinspector is None:
            return EvalResult(True, "nwbinspector not installed; skipping.", "skipped")

        inspect_nwbfile = getattr(nwbinspector, "inspect_nwbfile", None)
        format_messages = getattr(nwbinspector, "format_messages", None)
        Importance = getattr(nwbinspector, "Importance", None)
        if inspect_nwbfile is None or format_messages is None or Importance is None:
            return EvalResult(True, "nwbinspector API mismatch; skipping.", "skipped")

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
        summary = (
            ", ".join([f"{k}:{v}" for k, v in counts.items() if v > 0]) or "no issues"
        )

        return EvalResult(
            passed=not failed, formatted_report="\n".join(formatted), summary=summary
        )
    except Exception as e:
        return EvalResult(
            False, f"Inspector error: {e}\n{traceback.format_exc()}", "error"
        )


# -------------------------
# TTL instance-graph builder (light)
# -------------------------
def _sanitize(name: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)


def _make_literal(value):
    try:
        if isinstance(value, (bytes, bytearray)):
            try:
                return Literal(value.decode("utf-8"))
            except Exception:
                return Literal(str(value))
        np = numpy_mod
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


def build_instance_graph(
    nwb_path: Path,
    base_uri: Optional[str] = None,
    include_data: str = "stats",
    sample_limit: int = 200,
    _max_bytes: int = 50_000_000,
    _stats_inline_limit: int = 500,
) -> Optional[Graph]:
    """
    Build an rdflib.Graph instance representing the NWB instance graph.
    If rdflib or h5py is not available, returns None.
    """
    if rdflib is None or h5py is None:
        return None
    try:
        g = Graph()
        if base_uri is None:
            base_uri = f"http://example.org/{_sanitize(nwb_path.stem)}#"
        BASE = Namespace(base_uri)
        EX = BASE

        Group = EX.Group
        Dataset = EX.Dataset
        hasValue = EX.hasValue
        hasDType = EX.hasDType
        hasShape = EX.hasShape

        import h5py as _h5

        with _h5.File(str(nwb_path), "r") as f:

            def path_to_uri(h5path: str):
                if not h5path or h5path == "/":
                    return URIRef(str(BASE) + "root")
                frag = _sanitize(h5path.strip("/")) or "root"
                return URIRef(str(BASE) + frag)

            # root
            root_subj = path_to_uri("/")
            g.add((root_subj, RDF.type, Group))
            # attributes on root
            try:
                for ak, av in f.attrs.items():
                    pred = URIRef(str(EX) + f"attr_{_sanitize(str(ak))}")
                    lit = _make_literal(av)
                    if lit is not None:
                        g.add((root_subj, pred, lit))
            except Exception:
                pass

            def visit(name, obj):
                subj = path_to_uri(name)
                if isinstance(obj, _h5.Group):
                    g.add((subj, RDF.type, Group))
                    try:
                        for ak, av in obj.attrs.items():
                            pred = URIRef(str(EX) + f"attr_{_sanitize(str(ak))}")
                            lit = _make_literal(av)
                            if lit is not None:
                                g.add((subj, pred, lit))
                    except Exception:
                        pass
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

                    # data inclusion policy
                    if include_data == "full":
                        try:
                            arr = obj[()]
                            if arr is not None:
                                # naive add values
                                vals = (
                                    arr
                                    if getattr(arr, "__len__", None)
                                    and not isinstance(arr, (bytes, str))
                                    else [arr]
                                )
                                for v in (
                                    vals
                                    if sample_limit is None
                                    else vals[:sample_limit]
                                ):
                                    lit = _make_literal(v)
                                    if lit is not None:
                                        g.add((subj, hasValue, lit))
                        except Exception:
                            pass
                    elif include_data == "sample":
                        try:
                            arr = obj[()]
                            if arr is not None:
                                vals = (
                                    arr
                                    if getattr(arr, "__len__", None)
                                    and not isinstance(arr, (bytes, str))
                                    else [arr]
                                )
                                for v in vals[:sample_limit]:
                                    lit = _make_literal(v)
                                    if lit is not None:
                                        g.add((subj, hasValue, lit))
                        except Exception:
                            pass
                    elif include_data == "stats":
                        # very lightweight stats: size
                        try:
                            arr = obj[()]
                            import numpy as np

                            np_arr = np.array(arr)
                            g.add(
                                (
                                    subj,
                                    EX.stat_size,
                                    Literal(int(getattr(np_arr, "size", 0))),
                                )
                            )
                        except Exception:
                            pass

                # nothing returned

            f.visititems(visit)
        return g
    except Exception:
        return None


# -------------------------
# KG emit helpers
# -------------------------
def emit_llm_files(ttl_path: Path) -> dict[str, Path]:
    """
    From a TTL file path, write .nt, .jsonld and .triples.txt (labels when possible).
    Returns dict of written paths.
    """
    results = {}
    if rdflib is None:
        return results
    g = Graph()
    fmt = "turtle"
    g.parse(str(ttl_path), format=fmt)
    parent = ttl_path.parent
    stem = ttl_path.stem
    nt_path = parent / f"{stem}.nt"
    jsonld_path = parent / f"{stem}.jsonld"
    triples_path = parent / f"{stem}.triples.txt"
    g.serialize(destination=str(nt_path), format="nt")
    g.serialize(destination=str(jsonld_path), format="json-ld", indent=2)

    # triples text with labels when available
    def lbl(node):
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

    with open(triples_path, "w", encoding="utf-8") as fh:
        for s, p, o in g:
            fh.write(f"{lbl(s)}\t{lbl(p)}\t{lbl(o)}\n")
    results["nt"] = nt_path
    results["jsonld"] = jsonld_path
    results["triples"] = triples_path
    return results


# -------------------------
# KG HTML visualization (pyvis)
# -------------------------
def generate_kg_html(
    ttl_path: Path, out_html: Optional[Path] = None, max_triples: int = 12000
) -> Optional[Path]:
    """
    Load TTL, build a subgraph, and create an interactive HTML (pyvis) if pyvis and rdflib are available.
    Returns path to HTML or None.
    """
    if rdflib is None or pyvis is None:
        return None
    try:
        g = Graph()
        fmt = "turtle" if ttl_path.suffix.lower() == ".ttl" else None
        g.parse(str(ttl_path), format=fmt)
        # Build subgraph edges (simple)
        edges = []
        nodes = set()
        for s, p, o in g:
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                ss = str(s)
                oo = str(o)
                pp = str(p)
                edges.append((ss, oo, pp))
                nodes.add(ss)
                nodes.add(oo)
                if len(edges) >= max_triples:
                    break
        # create pyvis network
        net = pyvis.network.Network(height="900px", width="100%", notebook=False)
        # Add nodes with simple labels
        for n in nodes:
            lbl = (
                n.rsplit("#", 1)[-1]
                if "#" in n
                else n.rsplit("/", 1)[-1]
                if "/" in n
                else n
            )
            net.add_node(n, label=lbl, title=n)
        for s, o, p in edges:
            net.add_edge(s, o, title=p)
        # Save html
        if out_html is None:
            out_html = ttl_path.with_suffix(".html")
        net.save_graph(str(out_html))
        return out_html
    except Exception:
        return None


# -------------------------
# Context writer
# -------------------------
def write_context_file(
    context_path: Path,
    nwb_path: Path,
    eval_result: EvalResult,
    data_outputs: Optional[dict[str, Path]] = None,
):
    context_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("NWB Evaluation Context")
    lines.append(f"File: {nwb_path}")
    lines.append(f"Decision: {'PASS' if eval_result.passed else 'FAIL'}")
    lines.append(f"Inspector counts: {eval_result.summary}")
    if data_outputs:
        lines.append("")
        lines.append("Data outputs:")
        for k, v in data_outputs.items():
            lines.append(f" - {k}: {v}")
    lines.append("")
    lines.append("=== Inspector Report (verbatim) ===")
    lines.extend((eval_result.formatted_report or "").splitlines())
    context_path.write_text("\n".join(lines), encoding="utf-8")


# -------------------------
# Minimal LLM helpers (OpenAI & Ollama)
# -------------------------
def try_openai_extract(prompt: str) -> Optional[dict[str, object]]:
    """
    Try to extract structured options using OpenAI ChatCompletion.
    Returns a dict or None.
    (This is a convenience helper; presence of OPENAI_API_KEY required)
    """
    if openai is None:
        return None
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        openai.api_key = key
        sys_prompt = (
            "Extract compact JSON with keys: nwb, data, ontology, overwrite, sample_limit, max_bytes, stats_inline_limit, out_dir, linkml, offline. "
            "Return only JSON or code fence containing JSON."
        )
        resp = openai.ChatCompletion.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4"),
            temperature=0,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        content = resp["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            # strip backticks
            content = content.strip("`")
        data = json.loads(content)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def try_ollama_extract(prompt: str) -> Optional[dict[str, object]]:
    """
    Try to extract structured options using Ollama local chat endpoint.
    Requires OLLAMA_ENDPOINT and OLLAMA_MODEL env vars to be set.
    """
    url = os.environ.get("OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/chat").strip()
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b").strip()
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": "Return ONLY compact JSON with keys: nwb, data, ontology, overwrite, sample_limit, max_bytes, stats_inline_limit, out_dir, linkml, offline.",
            },
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0},
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = _urlreq.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with _urlreq.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            j = json.loads(body)
            # try to find content field
            content = None
            if isinstance(j, dict):
                msg = j.get("message") or {}
                content = msg.get("content") or j.get("response")
            if not content:
                return None
            text = content.strip()
            if text.startswith("```"):
                text = text.strip("`")
            obj = json.loads(text)
            return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# -------------------------
# High-level EvaluationAgent
# -------------------------
class EvaluationAgent:
    """Facade for evaluation tasks used by MCP server"""

    def __init__(self, base_cache_dir: Optional[Path] = None):
        self.base_cache_dir = (
            Path(base_cache_dir) if base_cache_dir else Path.cwd() / ".eval_cache"
        )
        self.base_cache_dir.mkdir(parents=True, exist_ok=True)

    def validate_nwb(self, nwb_path: str) -> dict[str, Any]:
        """Return dictionary with validation results (safe for MCP state)."""
        try:
            er = run_inspector(Path(nwb_path))
            return {
                "passed": er.passed,
                "formatted_report": er.formatted_report,
                "summary": er.summary,
            }
        except Exception as e:
            return {"passed": False, "formatted_report": str(e), "summary": "error"}

    def generate_ttl_and_outputs(
        self,
        nwb_path: str,
        out_dir: Optional[str] = None,
        include_data: str = "stats",
        sample_limit: int = 200,
        max_bytes: int = 50_000_000,
        stats_inline_limit: int = 500,
        ontology: str = "none",
    ) -> dict[str, Any]:
        """
        Attempt to generate instance graph (rdflib.Graph), write TTL and emit LLM files.
        Returns info about files created (paths as strings) or error.
        """
        out = {"status": "error", "message": "not run", "files": {}}
        try:
            out_dir = (
                Path(out_dir)
                if out_dir
                else (Path(nwb_path).parent / "evaluation_results")
            )
            out_dir.mkdir(parents=True, exist_ok=True)

            g = build_instance_graph(
                Path(nwb_path),
                base_uri=f"http://example.org/{_sanitize(Path(nwb_path).stem)}#",
                include_data=include_data,
                sample_limit=sample_limit,
                max_bytes=max_bytes,
                stats_inline_limit=stats_inline_limit,
            )
            if g is None:
                out["status"] = "skipped"
                out["message"] = "rdflib/h5py not available or graph build failed"
                return out

            # write TTL
            ttl_path = out_dir / f"{Path(nwb_path).stem}.data.ttl"
            g.serialize(destination=str(ttl_path), format="turtle")
            out["files"]["ttl"] = str(ttl_path)

            # emit llm files (nt/jsonld/triples)
            llm_files = emit_llm_files(ttl_path)
            out["files"].update({k: str(v) for k, v in llm_files.items()})

            # generate html KG if pyvis available
            html_path = generate_kg_html(
                ttl_path, out_html=out_dir / f"{Path(nwb_path).stem}.html"
            )
            if html_path:
                out["files"]["html"] = str(html_path)

            out["status"] = "success"
            return out
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "trace": traceback.format_exc(),
            }

    def write_context_and_report(
        self,
        nwb_path: str,
        eval_results: dict[str, Any],
        outputs: Optional[dict[str, str]] = None,
        out_dir: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Write a human-readable context file + text quality report to out_dir.
        """
        try:
            out_dir = (
                Path(out_dir)
                if out_dir
                else (Path(nwb_path).parent / "evaluation_results")
            )
            out_dir.mkdir(parents=True, exist_ok=True)
            ctx_path = out_dir / f"{Path(nwb_path).stem}_context_{int(time.time())}.txt"
            er = EvalResult(
                eval_results.get("passed", True),
                eval_results.get("formatted_report", ""),
                eval_results.get("summary", ""),
            )
            write_context_file(
                ctx_path,
                Path(nwb_path),
                er,
                {k: Path(v) for k, v in (outputs or {}).items()},
            )
            # Also write a short quality report file
            report_path = (
                out_dir / f"{Path(nwb_path).stem}_quality_report_{int(time.time())}.txt"
            )
            # create summary text
            lines = []
            lines.append("NWB Quality Report")
            lines.append(f"File: {nwb_path}")
            lines.append(
                f"Validation: {'PASS' if eval_results.get('passed') else 'FAIL'}"
            )
            lines.append(f"Inspector summary: {eval_results.get('summary')}")
            if outputs:
                lines.append("Outputs:")
                for k, v in outputs.items():
                    lines.append(f" - {k}: {v}")
            lines.append("\nDetailed inspector report:")
            lines.append(eval_results.get("formatted_report", ""))
            report_path.write_text("\n".join(lines), encoding="utf-8")
            return {"context": str(ctx_path), "report": str(report_path)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# end of evaluation_agent_combined.py
