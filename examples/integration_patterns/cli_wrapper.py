#!/usr/bin/env python3
"""
Command-line interface wrapper for the Agentic Neurodata Conversion MCP Server.

This CLI provides a convenient command-line interface to all MCP server
functionality, with support for configuration files, batch processing,
and comprehensive error handling.

Usage:
    # Start MCP server first
    pixi run server
    
    # Use CLI commands
    python cli_wrapper.py status
    python cli_wrapper.py analyze /path/to/dataset
    python cli_wrapper.py convert /path/to/dataset --files-map '{"recording": "data.dat"}'
    python cli_wrapper.py evaluate /path/to/file.nwb
    python cli_wrapper.py pipeline /path/to/dataset --files-map '{"recording": "data.dat"}'
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

import requests


class MCPCLIWrapper:
    """Command-line interface wrapper for MCP server operations."""

    def __init__(self, api_url: str = "http://127.0.0.1:8000", verbose: bool = False):
        """
        Initialize CLI wrapper.
        
        Args:
            api_url: MCP server URL
            verbose: Enable verbose output
        """
        self.api_url = api_url.rstrip("/")
        self.verbose = verbose

    def _log(self, message: str, level: str = "INFO"):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{level}] {message}")

    def _call_tool(self, tool_name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call MCP server tool with error handling."""
        url = f"{self.api_url}/tool/{tool_name}"
        
        try:
            self._log(f"Calling tool: {tool_name}")
            response = requests.post(url, json=payload or {}, timeout=300)
            response.raise_for_status()
            result = response.json()
            self._log(f"Tool {tool_name} completed successfully")
            return result
        except requests.exceptions.RequestException as e:
            error_msg = f"Tool {tool_name} failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" -> {error_detail}"
                except:
                    error_msg += f" -> {e.response.text}"
            return {"status": "error", "message": error_msg}

    def status(self) -> int:
        """Get server status."""
        try:
            response = requests.get(f"{self.api_url}/status", timeout=10)
            response.raise_for_status()
            status = response.json()
            
            print("MCP Server Status:")
            print(f"  Status: {status.get('status', 'unknown')}")
            print(f"  Registered Tools: {status.get('registered_tools', 0)}")
            print(f"  Available Agents: {', '.join(status.get('agents', []))}")
            
            if "pipeline_state" in status and status["pipeline_state"]:
                print("  Pipeline State:")
                for key, value in status["pipeline_state"].items():
                    print(f"    {key}: {value}")
            
            return 0
        except Exception as e:
            print(f"Error: Cannot connect to MCP server: {e}")
            return 1

    def list_tools(self) -> int:
        """List available tools."""
        try:
            response = requests.get(f"{self.api_url}/tools", timeout=10)
            response.raise_for_status()
            tools = response.json()
            
            print("Available MCP Tools:")
            for tool_name, metadata in tools.get("tools", {}).items():
                print(f"  {tool_name}:")
                print(f"    Description: {metadata.get('description', 'No description')}")
                print(f"    Function: {metadata.get('function', 'Unknown')}")
            
            return 0
        except Exception as e:
            print(f"Error: Cannot get tools list: {e}")
            return 1

    def analyze(self, dataset_dir: str, use_llm: bool = False, output_file: Optional[str] = None) -> int:
        """Analyze dataset."""
        print(f"Analyzing dataset: {dataset_dir}")
        
        result = self._call_tool("dataset_analysis", {
            "dataset_dir": dataset_dir,
            "use_llm": use_llm
        })
        
        if result.get("status") == "success":
            print("✓ Dataset analysis completed successfully")
            
            analysis_result = result.get("result", {})
            if self.verbose:
                print("Analysis Results:")
                print(json.dumps(analysis_result, indent=2))
            else:
                print(f"Metadata keys extracted: {list(analysis_result.keys())}")
            
            # Save to file if requested
            if output_file:
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"Results saved to: {output_file}")
            
            return 0
        else:
            print(f"✗ Dataset analysis failed: {result.get('message')}")
            return 1

    def convert(
        self,
        dataset_dir: str,
        files_map: Dict[str, str],
        output_nwb: Optional[str] = None,
        metadata_file: Optional[str] = None
    ) -> int:
        """Convert dataset to NWB format."""
        print(f"Converting dataset: {dataset_dir}")
        
        # Get metadata (either from file or by analyzing)
        if metadata_file and Path(metadata_file).exists():
            print(f"Loading metadata from: {metadata_file}")
            with open(metadata_file) as f:
                metadata_result = json.load(f)
            normalized_metadata = metadata_result.get("result", {})
        else:
            print("Analyzing dataset for metadata...")
            analysis_result = self._call_tool("dataset_analysis", {
                "dataset_dir": dataset_dir,
                "use_llm": False
            })
            if analysis_result.get("status") != "success":
                print(f"✗ Failed to get metadata: {analysis_result.get('message')}")
                return 1
            normalized_metadata = analysis_result.get("result", {})
        
        # Perform conversion
        conversion_payload = {
            "normalized_metadata": normalized_metadata,
            "files_map": files_map
        }
        if output_nwb:
            conversion_payload["output_nwb_path"] = output_nwb
        
        result = self._call_tool("conversion_orchestration", conversion_payload)
        
        if result.get("status") == "success":
            nwb_path = result.get("output_nwb_path")
            print(f"✓ Conversion completed successfully")
            print(f"NWB file created: {nwb_path}")
            return 0
        else:
            print(f"✗ Conversion failed: {result.get('message')}")
            return 1

    def evaluate(self, nwb_path: str, output_file: Optional[str] = None) -> int:
        """Evaluate NWB file."""
        print(f"Evaluating NWB file: {nwb_path}")
        
        if not Path(nwb_path).exists():
            print(f"✗ NWB file not found: {nwb_path}")
            return 1
        
        result = self._call_tool("evaluate_nwb_file", {
            "nwb_path": nwb_path,
            "generate_report": True
        })
        
        if result.get("status") == "success":
            print("✓ NWB evaluation completed successfully")
            
            evaluation = result.get("result", {})
            
            # Show summary
            if "validation_errors" in evaluation:
                error_count = len(evaluation["validation_errors"])
                print(f"Validation errors: {error_count}")
                if error_count > 0 and self.verbose:
                    for error in evaluation["validation_errors"][:5]:  # Show first 5
                        print(f"  - {error}")
                    if error_count > 5:
                        print(f"  ... and {error_count - 5} more")
            
            if "quality_score" in evaluation:
                print(f"Quality score: {evaluation['quality_score']}")
            
            # Save to file if requested
            if output_file:
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"Evaluation report saved to: {output_file}")
            
            return 0
        else:
            print(f"✗ NWB evaluation failed: {result.get('message')}")
            return 1

    def pipeline(
        self,
        dataset_dir: str,
        files_map: Dict[str, str],
        output_dir: Optional[str] = None,
        use_llm: bool = False,
        skip_kg: bool = False
    ) -> int:
        """Run full conversion pipeline."""
        print(f"Running full pipeline for: {dataset_dir}")
        
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Step 1: Analysis
        print("\n1. Analyzing dataset...")
        analysis_result = self._call_tool("dataset_analysis", {
            "dataset_dir": dataset_dir,
            "use_llm": use_llm
        })
        
        if analysis_result.get("status") != "success":
            print(f"✗ Analysis failed: {analysis_result.get('message')}")
            return 1
        print("✓ Analysis completed")
        
        # Step 2: Conversion
        print("\n2. Converting to NWB...")
        conversion_payload = {
            "normalized_metadata": analysis_result.get("result", {}),
            "files_map": files_map
        }
        if output_dir:
            conversion_payload["output_nwb_path"] = str(Path(output_dir) / "converted.nwb")
        
        conversion_result = self._call_tool("conversion_orchestration", conversion_payload)
        
        if conversion_result.get("status") != "success":
            print(f"✗ Conversion failed: {conversion_result.get('message')}")
            return 1
        
        nwb_path = conversion_result.get("output_nwb_path")
        print(f"✓ Conversion completed: {nwb_path}")
        
        # Step 3: Evaluation
        print("\n3. Evaluating NWB file...")
        evaluation_result = self._call_tool("evaluate_nwb_file", {
            "nwb_path": nwb_path,
            "generate_report": True
        })
        
        if evaluation_result.get("status") == "success":
            print("✓ Evaluation completed")
        else:
            print(f"⚠ Evaluation failed: {evaluation_result.get('message')}")
        
        # Step 4: Knowledge Graph (optional)
        if not skip_kg:
            print("\n4. Generating knowledge graph...")
            kg_result = self._call_tool("generate_knowledge_graph", {
                "nwb_path": nwb_path,
                "output_format": "ttl"
            })
            
            if kg_result.get("status") == "success":
                print("✓ Knowledge graph generated")
            else:
                print(f"⚠ Knowledge graph generation failed: {kg_result.get('message')}")
        
        print(f"\n✓ Pipeline completed successfully")
        print(f"Output NWB file: {nwb_path}")
        
        return 0


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_file) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file {config_file}: {e}")
        sys.exit(1)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="CLI wrapper for Agentic Neurodata Conversion MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                                    # Check server status
  %(prog)s tools                                     # List available tools
  %(prog)s analyze /path/to/dataset                  # Analyze dataset
  %(prog)s convert /path/to/dataset --files-map '{"recording": "data.dat"}'
  %(prog)s evaluate /path/to/file.nwb               # Evaluate NWB file
  %(prog)s pipeline /path/to/dataset --files-map '{"recording": "data.dat"}'
        """
    )
    
    # Global options
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="MCP server URL")
    parser.add_argument("--config", help="Configuration file (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    subparsers.add_parser("status", help="Get server status")
    
    # Tools command
    subparsers.add_parser("tools", help="List available tools")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze dataset")
    analyze_parser.add_argument("dataset_dir", help="Dataset directory path")
    analyze_parser.add_argument("--use-llm", action="store_true", help="Use LLM for analysis")
    analyze_parser.add_argument("--output", help="Save results to file")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert dataset to NWB")
    convert_parser.add_argument("dataset_dir", help="Dataset directory path")
    convert_parser.add_argument("--files-map", required=True, help="Files mapping (JSON string)")
    convert_parser.add_argument("--output-nwb", help="Output NWB file path")
    convert_parser.add_argument("--metadata-file", help="Use metadata from file instead of analyzing")
    
    # Evaluate command
    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate NWB file")
    evaluate_parser.add_argument("nwb_path", help="NWB file path")
    evaluate_parser.add_argument("--output", help="Save evaluation report to file")
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Run full conversion pipeline")
    pipeline_parser.add_argument("dataset_dir", help="Dataset directory path")
    pipeline_parser.add_argument("--files-map", required=True, help="Files mapping (JSON string)")
    pipeline_parser.add_argument("--output-dir", help="Output directory")
    pipeline_parser.add_argument("--use-llm", action="store_true", help="Use LLM for analysis")
    pipeline_parser.add_argument("--skip-kg", action="store_true", help="Skip knowledge graph generation")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Load configuration if provided
    config = {}
    if args.config:
        config = load_config(args.config)
    
    # Override with command line arguments
    api_url = args.api_url or config.get("api_url", "http://127.0.0.1:8000")
    verbose = args.verbose or config.get("verbose", False)
    
    # Create CLI wrapper
    cli = MCPCLIWrapper(api_url=api_url, verbose=verbose)
    
    try:
        # Execute command
        if args.command == "status":
            return cli.status()
        
        elif args.command == "tools":
            return cli.list_tools()
        
        elif args.command == "analyze":
            return cli.analyze(
                dataset_dir=args.dataset_dir,
                use_llm=args.use_llm,
                output_file=args.output
            )
        
        elif args.command == "convert":
            try:
                files_map = json.loads(args.files_map)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in --files-map: {e}")
                return 1
            
            return cli.convert(
                dataset_dir=args.dataset_dir,
                files_map=files_map,
                output_nwb=args.output_nwb,
                metadata_file=args.metadata_file
            )
        
        elif args.command == "evaluate":
            return cli.evaluate(
                nwb_path=args.nwb_path,
                output_file=args.output
            )
        
        elif args.command == "pipeline":
            try:
                files_map = json.loads(args.files_map)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in --files-map: {e}")
                return 1
            
            return cli.pipeline(
                dataset_dir=args.dataset_dir,
                files_map=files_map,
                output_dir=args.output_dir,
                use_llm=args.use_llm,
                skip_kg=args.skip_kg
            )
        
        else:
            print(f"Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())