import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Optional

import h5py
from linkml_runtime.dumpers import yaml_dumper
from nwb_linkml.adapters.namespaces import BuildResult, NamespacesAdapter

# nwb-linkml imports
from nwb_linkml.io import load_namespace_schema
from nwb_linkml.namespaces import HDMF_COMMON_REPO, NWB_CORE_REPO

# nwb schema language (pydantic v1 models)
from nwb_schema_language import Namespaces as NWBNamespaces
import yaml


def _load_namespaces_from_yaml(path: Path) -> NWBNamespaces:
    with open(path) as fh:
        ns_dict = yaml.safe_load(fh)
    # Construct pydantic v1 model directly
    return NWBNamespaces(**ns_dict)


def build_linkml_from_core(
    core_commit: Optional[str] = None, hdmf_commit: Optional[str] = None
) -> BuildResult:
    """Load NWB core + HDMF-common and build LinkML elements without linkml-runtime loader."""
    # Get local paths to the namespace YAMLs (cloning if needed)
    hdmf_ns_file = HDMF_COMMON_REPO.provide_from_git(commit=hdmf_commit)
    core_ns_file = NWB_CORE_REPO.provide_from_git(commit=core_commit)

    # Load as pydantic v1 models
    hdmf_ns = _load_namespaces_from_yaml(hdmf_ns_file)
    core_ns = _load_namespaces_from_yaml(core_ns_file)

    # Build adapters
    hdmf_adapter: NamespacesAdapter = load_namespace_schema(hdmf_ns, hdmf_ns_file)
    core_adapter: NamespacesAdapter = load_namespace_schema(core_ns, core_ns_file)

    # Wire imports and build
    core_adapter.imported.append(hdmf_adapter)
    return core_adapter.build()


def build_linkml_from_namespace_file(namespace_file: Path) -> BuildResult:
    """Load a local NWB namespace YAML and build LinkML elements.

    This allows pointing at a custom namespace file if provided.
    """
    ns = _load_namespaces_from_yaml(namespace_file)
    adapter: NamespacesAdapter = load_namespace_schema(ns, namespace_file)
    return adapter.build()


def build_linkml_from_core_with_extensions(
    extension_namespace_files: list[Path],
    core_commit: Optional[str] = None,
    hdmf_commit: Optional[str] = None,
) -> BuildResult:
    """Build LinkML from core + provided extension namespace YAML files."""
    # Base core
    hdmf_ns_file = HDMF_COMMON_REPO.provide_from_git(commit=hdmf_commit)
    core_ns_file = NWB_CORE_REPO.provide_from_git(commit=core_commit)

    hdmf_ns = _load_namespaces_from_yaml(hdmf_ns_file)
    core_ns = _load_namespaces_from_yaml(core_ns_file)

    hdmf_adapter: NamespacesAdapter = load_namespace_schema(hdmf_ns, hdmf_ns_file)
    core_adapter: NamespacesAdapter = load_namespace_schema(core_ns, core_ns_file)

    # Extensions
    for ext_file in extension_namespace_files:
        ext_ns = _load_namespaces_from_yaml(ext_file)
        ext_adapter: NamespacesAdapter = load_namespace_schema(ext_ns, ext_file)
        core_adapter.imported.append(ext_adapter)

    core_adapter.imported.append(hdmf_adapter)
    return core_adapter.build()


def detect_namespaces_in_nwb(nwb_file: Path) -> set[str]:
    """Traverse the NWB/HDF5 file and collect unique 'namespace' attribute values everywhere."""
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
            # Sometimes only neurodata_type is present and implies core; we don't add anything in that case

        f.visititems(visit)
    return namespaces


def find_namespace_yaml_in_dir(root: Path, namespace_name: str) -> Optional[Path]:
    """Search for a YAML file under root that defines the given namespace name."""
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.lower().endswith((".yaml", ".yml")):
                continue
            fp = Path(dirpath) / fn
            try:
                with open(fp) as fh:
                    data = yaml.safe_load(fh)
                # Expect a "namespaces" key containing list of dicts with name
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
        # Try to checkout the requested commit/tag
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
    """Resolve namespace YAML paths for detected non-core namespaces.

    Strategy:
    - Skip 'core' and 'hdmf-common'
    - Check cache_dir recursively for YAML defining the namespace
    - If not found and auto_fetch_ndx and not offline: try to clone GitHub repo for 'nwb-extensions/<ns>'
      or override mapping if provided, then search for YAML
    - Cache the found YAML by copying into cache_dir/<ns>/<filename>
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []

    for ns in sorted(detected_namespaces):
        if ns in {"core", "hdmf-common"}:
            continue

        # 1) cache lookup
        cached = find_namespace_yaml_in_dir(cache_dir, ns)
        if cached:
            out_paths.append(cached)
            continue

        if offline:
            print(f"[offline] Namespace '{ns}' not found in cache; skipping.")
            continue

        # 2) auto-fetch
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
                        # copy into cache
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
    """Write a single combined LinkML YAML schema that inlines all classes/slots/types."""
    from linkml_runtime.linkml_model import (
        SchemaDefinition,
    )

    class_by_name = {}
    slot_by_name = {}
    type_by_name = {}
    import_set = set()

    def to_items(coll):
        if coll is None:
            return []
        if isinstance(coll, dict):
            return list(coll.items())
        # assume iterable of objects with .name
        items = []
        for x in coll:
            name = getattr(x, "name", None)
            if name is None:
                # fallback to string key
                name = str(x)
            items.append((name, x))
        return items

    for sch in schemas:
        # Collect imports
        if sch.imports:
            import_set.update(sch.imports)

        # Collect classes/slots/types (dedupe by name; handle dict or list forms)
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
    """Write each SchemaDefinition to its own YAML inside the output directory."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for sch in schemas:
        file_path = out_dir / f"{sch.name}.yaml"
        yaml_dumper.dump(sch, str(file_path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate LinkML schema(s) from NWB core namespaces using nwb-linkml."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="",
        type=str,
        help="Path to NWB file (.nwb). If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--namespace",
        action="append",
        default=[],
        help="Path to an NWB namespace YAML to include (can be repeated).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output file or directory. If endswith .yaml -> monolith; else split files in directory (default: <input>.linkml/).",
    )
    parser.add_argument(
        "--auto-fetch-ndx",
        action="store_true",
        default=True,
        help="Auto-fetch detected NDX extensions from nwb-extensions on GitHub (default: on).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not attempt any network calls; use only cache and provided --namespace files.",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=".nwb_linkml_cache",
        help="Directory to cache extension namespace YAMLs.",
    )
    parser.add_argument(
        "--ndx-repo",
        action="append",
        default=[],
        help="Override mapping 'namespace=repo_url' for auto-fetch.",
    )
    parser.add_argument(
        "--ndx-pin",
        action="append",
        default=[],
        help="Pin extension commit 'namespace=commit_or_tag'.",
    )
    parser.add_argument(
        "--pin-core",
        type=str,
        default="",
        help="Commit or tag to pin NWB core namespace repo to.",
    )
    parser.add_argument(
        "--pin-hdmf",
        type=str,
        default="",
        help="Commit or tag to pin HDMF-common namespace repo to.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        default=True,
        help="Do not fail if some namespaces cannot be fetched (default: on).",
    )
    args = parser.parse_args()

    # Always prompt for NWB path; if blank, fall back to CLI arg (if provided)
    prompt_str = input("Enter path to NWB file (.nwb): ").strip()
    input_str = prompt_str or (
        args.input.strip() if isinstance(args.input, str) else ""
    )
    if not input_str:
        raise SystemExit("No NWB file path provided.")

    input_path = Path(input_str).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    # Determine output
    if args.output:
        out = Path(args.output).expanduser().resolve()
    else:
        # Default next to input: directory containing per-namespace YAML files
        # e.g., /path/file.nwb -> /path/file.linkml/
        out = input_path.with_suffix("").with_suffix(".linkml")

    # Resolve namespace file list
    provided_ns_files: list[Path] = []
    for nspath in args.namespace or []:
        p = Path(nspath).expanduser().resolve()
        if not p.exists():
            raise SystemExit(f"Namespace file not found: {p}")
        provided_ns_files.append(p)

    # Detect namespaces present in the NWB and resolve extension YAMLs
    detected = detect_namespaces_in_nwb(input_path)
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    # Parse overrides like 'ndx-myext=https://github.com/...'
    overrides: dict[str, str] = {}
    for item in args.ndx_repo or []:
        if "=" in item:
            key, val = item.split("=", 1)
            overrides[key.strip()] = val.strip()

    pin_overrides: dict[str, str] = {}
    for item in args.ndx_pin or []:
        if "=" in item:
            key, val = item.split("=", 1)
            pin_overrides[key.strip()] = val.strip()

    resolved_exts = resolve_extension_namespaces(
        detected_namespaces=detected,
        cache_dir=cache_dir,
        auto_fetch_ndx=bool(args.auto_fetch_ndx),
        offline=bool(args.offline),
        ndx_repo_overrides=overrides,
        ndx_commit_overrides=pin_overrides,
    )

    all_ext_files = provided_ns_files + resolved_exts

    # Build from core + extensions
    try:
        result = build_linkml_from_core_with_extensions(
            all_ext_files,
            core_commit=args.pin_core or None,
            hdmf_commit=args.pin_hdmf or None,
        )
    except Exception as e:
        if not args.allow_missing:
            raise
        print(f"Warning: Proceeding despite build error: {e}")
        # Try to fall back to core only
        result = build_linkml_from_core(
            core_commit=args.pin_core or None, hdmf_commit=args.pin_hdmf or None
        )

    # Write output
    if out.suffix.lower() in (".yaml", ".yml"):
        write_monolithic_yaml(result.schemas, out)
        print(f"Wrote monolithic LinkML schema: {out}")
    else:
        write_split_yaml(result.schemas, out)
        print(f"Wrote per-namespace LinkML schemas to: {out}")


if __name__ == "__main__":
    main()
