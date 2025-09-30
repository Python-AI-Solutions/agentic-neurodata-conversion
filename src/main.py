"""Main CLI for NWB Knowledge Graph System.

This module orchestrates the complete workflow from NWB file to knowledge graph visualization.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
import json
from tqdm import tqdm

# Import modules
from src.nwb_loader import load_nwb_file, validate_nwb_integrity
from src.inspector_runner import run_inspection
from src.hierarchical_parser import parse_hdf5_structure
from src.linkml_schema_loader import load_official_schema
from src.linkml_converter import convert_nwb_to_linkml
from src.ttl_generator import generate_ttl, generate_jsonld
from src.graph_constructor import build_graph_from_ttl, compute_graph_analytics
from src.report_generator import generate_evaluation_report, export_report
from src.html_generator import generate_visualization
from src.visualization_engine import compute_force_directed_layout


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for CLI.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code: 0=success, 1=error, 2=invalid input
    """
    parser = argparse.ArgumentParser(
        description="NWB Knowledge Graph System - Convert NWB files to knowledge graphs"
    )
    parser.add_argument("nwb_file", type=Path, help="Path to NWB file")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--enable-reasoning", action="store_true", help="Enable OWL reasoning")
    parser.add_argument("--show-timing", action="store_true", help="Show timing information")
    parser.add_argument("--version", action="version", version="NWB-KG 1.0.0")

    parsed_args = parser.parse_args(args)

    nwb_file: Path = parsed_args.nwb_file
    output_dir: Path = parsed_args.output_dir
    verbose: bool = parsed_args.verbose
    enable_reasoning: bool = parsed_args.enable_reasoning

    # Check input file
    if not nwb_file.exists():
        print(f"Error: NWB file not found: {nwb_file}", file=sys.stderr)
        return 2

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine base name for outputs
    base_name = nwb_file.stem

    try:
        # Progress tracking
        phases = [
            "Loading NWB file",
            "Running validation",
            "Parsing HDF5 structure",
            "Loading LinkML schema",
            "Converting to LinkML",
            "Generating TTL",
            "Generating JSON-LD",
            "Building knowledge graph",
            "Computing graph analytics",
            "Generating evaluation report",
            "Generating visualization"
        ]

        with tqdm(total=len(phases), desc="Processing", disable=not verbose) as pbar:
            # Phase 1: Load NWB file
            if verbose:
                print(f"Loading NWB file: {nwb_file}")
            pbar.set_description(phases[0])
            nwbfile = load_nwb_file(nwb_file)
            pbar.update(1)

            # Phase 2: Run validation (nwbinspector)
            pbar.set_description(phases[1])
            inspection_results = run_inspection(nwb_file)
            pbar.update(1)

            # Phase 3: Parse HDF5 structure
            pbar.set_description(phases[2])
            hierarchy = parse_hdf5_structure(nwbfile)
            pbar.update(1)

            # Phase 4: Load LinkML schema
            pbar.set_description(phases[3])
            schema = load_official_schema("2.5.0")
            pbar.update(1)

            # Phase 5: Convert to LinkML (with complete hierarchy)
            pbar.set_description(phases[4])
            linkml_instances = convert_nwb_to_linkml(nwbfile, schema, hierarchy)
            pbar.update(1)

            # Phase 6: Generate TTL
            pbar.set_description(phases[5])
            ttl_content = generate_ttl(linkml_instances, schema)
            pbar.update(1)

            # Phase 7: Generate JSON-LD
            pbar.set_description(phases[6])
            jsonld_content = generate_jsonld(ttl_content)
            pbar.update(1)

            # Phase 8: Build knowledge graph
            pbar.set_description(phases[7])
            knowledge_graph = build_graph_from_ttl(ttl_content, enable_reasoning=enable_reasoning)
            pbar.update(1)

            # Phase 9: Compute graph analytics
            pbar.set_description(phases[8])
            graph_metrics = compute_graph_analytics(knowledge_graph)
            pbar.update(1)

            # Phase 10: Generate evaluation report
            pbar.set_description(phases[9])
            report = generate_evaluation_report(inspection_results, hierarchy, graph_metrics)
            pbar.update(1)

            # Phase 11: Generate visualization
            pbar.set_description(phases[10])
            metadata = {
                "node_count": graph_metrics.node_count,
                "edge_count": graph_metrics.edge_count,
                "density": graph_metrics.density,
                "file_name": nwb_file.name
            }
            visualization_html = generate_visualization(jsonld_content, metadata)
            pbar.update(1)

        # Write all outputs
        if verbose:
            print("Writing output files...")

        # 1-3: Evaluation reports (JSON, HTML, TXT)
        export_report(report, 'json', output_dir / f"{base_name}_evaluation_report.json")
        export_report(report, 'html', output_dir / f"{base_name}_evaluation_report.html")
        export_report(report, 'txt', output_dir / f"{base_name}_evaluation_report.txt")

        # 4: Hierarchy JSON
        def _clean_for_json(obj):
            """Convert objects to JSON-serializable format."""
            if isinstance(obj, dict):
                return {k: _clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [_clean_for_json(item) for item in obj]
            elif hasattr(obj, '__class__') and 'Reference' in obj.__class__.__name__:
                return f"<Reference: {str(obj)}>"
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                return str(obj)

        hierarchy_dict = {
            "root": hierarchy.root,
            "groups": [{"name": g.name, "path": g.path, "parent_path": g.parent_path} for g in hierarchy.groups],
            "datasets": [{"name": d.name, "path": d.path, "shape": list(d.shape) if d.shape else [], "dtype": d.dtype} for d in hierarchy.datasets],
            "links": [{"name": l.name, "path": l.path, "type": l.link_type} for l in hierarchy.links],
            "attributes": _clean_for_json(hierarchy.attributes)
        }
        with open(output_dir / f"{base_name}_hierarchy.json", 'w') as f:
            json.dump(hierarchy_dict, f, indent=2)

        # 5: LinkML data JSON-LD
        linkml_dict = {
            "@context": {"nwb": f"http://purl.org/nwb/{linkml_instances.metadata.schema_version}/"},
            "@graph": linkml_instances.instances
        }
        with open(output_dir / f"{base_name}_linkml_data.jsonld", 'w') as f:
            json.dump(linkml_dict, f, indent=2)

        # 6: Knowledge graph TTL
        with open(output_dir / f"{base_name}_knowledge_graph.ttl", 'w') as f:
            f.write(ttl_content)

        # 7: Knowledge graph JSON-LD
        with open(output_dir / f"{base_name}_knowledge_graph.jsonld", 'w') as f:
            f.write(jsonld_content)

        # 8: Graph metadata JSON
        metadata_dict = {
            "node_count": graph_metrics.node_count,
            "edge_count": graph_metrics.edge_count,
            "density": graph_metrics.density,
            "avg_degree": graph_metrics.avg_degree
        }
        with open(output_dir / f"{base_name}_graph_metadata.json", 'w') as f:
            json.dump(metadata_dict, f, indent=2)

        # 9: Visualization HTML
        with open(output_dir / f"{base_name}_visualization.html", 'w') as f:
            f.write(visualization_html)

        # 10: Force layout data
        nodes_for_layout = [{"id": n.id, "label": n.label} for n in knowledge_graph.nodes]
        edges_for_layout = [{"source": e.source, "target": e.target} for e in knowledge_graph.edges]
        layout_data = compute_force_directed_layout(nodes_for_layout, edges_for_layout)
        layout_dict = {
            "positions": layout_data.positions,
            "converged": layout_data.converged,
            "iterations": layout_data.iterations
        }
        with open(output_dir / f"{base_name}_force_layout.json", 'w') as f:
            json.dump(layout_dict, f, indent=2)

        if verbose:
            print(f"✓ Successfully processed {nwb_file.name}")
            print(f"✓ Generated 10 output files in {output_dir}")
            print(f"✓ Status: {report.summary.status}")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())