import argparse
from pathlib import Path
import subprocess
import sys

from rdflib import Graph, URIRef
from rdflib.namespace import RDFS


def run_cmd(cmd, input_text: str | None = None) -> None:
    try:
        if input_text is None:
            subprocess.run(cmd, check=True)
        else:
            subprocess.run(cmd, input=input_text.encode("utf-8"), check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(
            f"Command failed ({e.returncode}): {' '.join(map(str, cmd))}"
        ) from e


def label_for(g: Graph, node) -> str:
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


def emit_llm_files(ttl_path: Path) -> None:
    target_dir = ttl_path.parent
    stem = ttl_path.stem  # preserves multi-part stems like *.data and *.owl
    target_dir / stem
    g = Graph()
    g.parse(str(ttl_path), format="turtle")
    print(f"  Triples in {ttl_path.name}: {len(g)}")

    # 1) N-Triples
    g.serialize(destination=str(target_dir / f"{stem}.nt"), format="nt")

    # 2) JSON-LD
    g.serialize(
        destination=str(target_dir / f"{stem}.jsonld"), format="json-ld", indent=2
    )

    # 3) LLM-friendly triples.txt (labels where available)
    with open(target_dir / f"{stem}.triples.txt", "w", encoding="utf-8") as f:
        for s, p, o in g:
            f.write(f"{label_for(g, s)}\t{label_for(g, p)}\t{label_for(g, o)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Full pipeline: NWB -> LinkML -> TTL -> LLM KG files"
    )
    parser.add_argument(
        "nwb",
        nargs="?",
        default="",
        help="Path to NWB file (.nwb). If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(
            (Path(__file__).resolve().parent.parent / ".nwb_linkml_cache").resolve()
        ),
        help="Cache directory for NDX resolution",
    )
    parser.add_argument(
        "--data",
        choices=["none", "stats", "sample", "full"],
        default="stats",
        help="Data inclusion policy for TTL",
    )
    parser.add_argument(
        "--sample-limit", type=int, default=200, help="Sample size when --data=sample"
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=50_000_000,
        help="Max bytes per dataset when embedding values",
    )
    args = parser.parse_args()

    nwb_str = args.nwb.strip() or input("Enter path to NWB file (.nwb): ").strip()
    nwb_path = Path(nwb_str).expanduser().resolve()
    if not nwb_path.exists():
        raise SystemExit(f"NWB not found: {nwb_path}")

    # Paths
    repo_root = Path(__file__).resolve().parent.parent
    n_script = repo_root / "nwb_to_linkml" / "nwb_to_linkml.py"
    lt_script = repo_root / "linkmlnwb_to_ttl" / "linkmlnwb_to_ttl.py"

    anaconda_python = Path("/opt/anaconda3/bin/python")
    venv_python = repo_root / "nlk" / "bin" / "python"
    # Use Anaconda (pydantic v1) for nwb_to_linkml, and local venv (pydantic v2) for ttl/owl
    if anaconda_python.exists():
        py_n = anaconda_python
    else:
        py_n = venv_python if venv_python.exists() else Path(sys.executable)
    py_ttl = venv_python if venv_python.exists() else Path(sys.executable)

    # Final outputs directory
    final_dir = repo_root / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    base_stem = nwb_path.stem

    # 1) Generate LinkML (split schema directory by default)
    # n.py prompts for NWB path; provide via stdin to avoid hanging
    if n_script.exists():
        linkml_out_dir = final_dir / f"{base_stem}.linkml"
        cmd_n = [
            str(py_n),
            str(n_script),
            "--cache-dir",
            str(Path(args.cache_dir).expanduser()),
            "--output",
            str(linkml_out_dir),
        ]
        print("[1/3] Generating LinkML via:", " ".join(cmd_n))
        run_cmd(cmd_n, input_text=str(nwb_path) + "\n")
    else:
        print("Warning: n.py not found, skipping LinkML generation.")

    # 2) Generate data TTL (ontology none)
    ttl_out = final_dir / f"{base_stem}.data.ttl"
    if lt_script.exists():
        cmd_lt = [
            str(py_ttl),
            str(lt_script),
            str(nwb_path),
            "--ontology",
            "none",
            "--data",
            args.data,
            "--sample-limit",
            str(args.sample_limit),
            "--max-bytes",
            str(args.max_bytes),
            "--output",
            str(ttl_out),
        ]
        print("[2/3] Generating TTL via:", " ".join(cmd_lt))
        run_cmd(cmd_lt)
    else:
        print("Warning: lt.py not found, skipping TTL generation.")

    if not ttl_out.exists():
        raise SystemExit(f"TTL not created: {ttl_out}")

    # 3) Generate ontology TTL separately (used ontology, no instance data values)
    owl_out = final_dir / f"{base_stem}.owl.ttl"
    if lt_script.exists():
        cmd_owl = [
            str(py_ttl),
            str(lt_script),
            str(nwb_path),
            "--ontology",
            "full",
            "--data",
            "none",
            "--output",
            str(owl_out),
        ]
        print("[3/4] Generating OWL TTL via:", " ".join(cmd_owl))
        run_cmd(cmd_owl)
    else:
        print("Warning: lt.py not found, skipping ontology TTL generation.")

    # 4) Emit KG files for LLM ingestion from both TTLs
    print("[4/4] Writing NT / JSON-LD / triples.txt for data and ontology ...")
    emit_llm_files(ttl_out)
    emit_llm_files(owl_out)
    if ttl_out.exists():
        print("Done:")
        print(" -", ttl_out, "(data)")
        print(" -", ttl_out.with_suffix(".nt"))
        print(" -", ttl_out.with_suffix(".jsonld"))
        print(" -", ttl_out.with_suffix(".triples.txt"))
    if owl_out.exists():
        print(" -", owl_out, "(ontology)")
        print(" -", owl_out.with_suffix(".nt"))
        print(" -", owl_out.with_suffix(".jsonld"))
        print(" -", owl_out.with_suffix(".triples.txt"))


if __name__ == "__main__":
    main()
