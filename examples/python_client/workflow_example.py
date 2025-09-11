#!/usr/bin/env python3
"""
Comprehensive workflow example for the Agentic Neurodata Conversion MCP Server.

This example demonstrates the complete pipeline from dataset analysis through
NWB conversion and evaluation, based on the original workflow.py pattern.

Usage:
    # Start MCP server first
    pixi run server
    
    # Run this example
    pixi run python workflow_example.py
    
    # Or with custom parameters
    pixi run python workflow_example.py --dataset-dir /path/to/data --use-llm
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import requests


class MCPWorkflowClient:
    """
    Comprehensive MCP client for running the full neurodata conversion pipeline.
    
    This client demonstrates all major MCP server capabilities including:
    - Dataset analysis and metadata extraction
    - Conversion script generation and execution
    - NWB file evaluation and quality assessment
    - Knowledge graph generation
    - Pipeline state management
    """

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:8000",
        output_dir: str = "outputs",
        use_llm: bool = False
    ):
        """
        Initialize the MCP workflow client.
        
        Args:
            api_url: MCP server URL
            output_dir: Directory for output files
            use_llm: Whether to use LLM for enhanced analysis
        """
        self.api_url = api_url.rstrip("/")
        self.output_dir = output_dir
        self.use_llm = use_llm
        self.pipeline_state = {}
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def _call_tool(self, tool_name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call MCP server tool with comprehensive error handling.
        
        Args:
            tool_name: Name of the MCP tool to call
            payload: Parameters to send to the tool
            
        Returns:
            Tool execution result or error information
        """
        url = f"{self.api_url}/tool/{tool_name}"
        
        try:
            print(f"[INFO] Calling tool: {tool_name}")
            if payload:
                print(f"[INFO] Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, json=payload or {}, timeout=300)
            response.raise_for_status()
            
            result = response.json()
            print(f"[SUCCESS] {tool_name} completed")
            return result
            
        except requests.exceptions.Timeout:
            error_msg = f"Tool {tool_name} timed out after 300 seconds"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Tool {tool_name} failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" -> {error_detail}"
                except:
                    error_msg += f" -> {e.response.text}"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error calling {tool_name}: {e}"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}

    def check_server_status(self) -> Dict[str, Any]:
        """Check if MCP server is running and get current status."""
        try:
            response = requests.get(f"{self.api_url}/status", timeout=10)
            response.raise_for_status()
            status = response.json()
            print(f"[INFO] Server status: {status.get('status', 'unknown')}")
            return status
        except Exception as e:
            print(f"[ERROR] Cannot connect to MCP server: {e}")
            return {"status": "error", "message": str(e)}

    def list_available_tools(self) -> Dict[str, Any]:
        """Get list of available MCP tools."""
        try:
            response = requests.get(f"{self.api_url}/tools", timeout=10)
            response.raise_for_status()
            tools = response.json()
            print(f"[INFO] Available tools: {list(tools.get('tools', {}).keys())}")
            return tools
        except Exception as e:
            print(f"[ERROR] Cannot get tools list: {e}")
            return {"tools": {}, "error": str(e)}

    def analyze_dataset(self, dataset_dir: str) -> Dict[str, Any]:
        """
        Analyze dataset structure and extract metadata.
        
        Args:
            dataset_dir: Path to the dataset directory
            
        Returns:
            Analysis result with normalized metadata
        """
        print(f"\n=== Step 1: Analyzing Dataset ===")
        print(f"Dataset directory: {dataset_dir}")
        print(f"Using LLM: {self.use_llm}")
        
        result = self._call_tool("dataset_analysis", {
            "dataset_dir": dataset_dir,
            "use_llm": self.use_llm
        })
        
        if result.get("status") == "success":
            self.pipeline_state["normalized_metadata"] = result.get("result", {})
            self.pipeline_state["dataset_dir"] = dataset_dir
            print(f"[SUCCESS] Dataset analysis completed")
            print(f"[INFO] Extracted metadata keys: {list(self.pipeline_state['normalized_metadata'].keys())}")
        else:
            print(f"[ERROR] Dataset analysis failed: {result.get('message')}")
        
        return result

    def generate_conversion_script(self, files_map: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate and execute NeuroConv conversion script.
        
        Args:
            files_map: Mapping of data types to file paths
            
        Returns:
            Conversion result with output NWB path
        """
        print(f"\n=== Step 2: Generating Conversion Script ===")
        
        if "normalized_metadata" not in self.pipeline_state:
            error_msg = "No metadata available. Run analyze_dataset first."
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
        
        print(f"Files map: {files_map}")
        
        result = self._call_tool("conversion_orchestration", {
            "normalized_metadata": self.pipeline_state["normalized_metadata"],
            "files_map": files_map,
            "output_nwb_path": str(Path(self.output_dir) / "converted_data.nwb")
        })
        
        if result.get("status") == "success":
            self.pipeline_state["nwb_path"] = result.get("output_nwb_path")
            print(f"[SUCCESS] Conversion completed")
            print(f"[INFO] NWB file created: {self.pipeline_state['nwb_path']}")
        else:
            print(f"[ERROR] Conversion failed: {result.get('message')}")
        
        return result

    def evaluate_nwb_file(self, nwb_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate generated NWB file quality and compliance.
        
        Args:
            nwb_path: Path to NWB file (uses pipeline state if not provided)
            
        Returns:
            Evaluation result with quality metrics
        """
        print(f"\n=== Step 3: Evaluating NWB File ===")
        
        nwb_path = nwb_path or self.pipeline_state.get("nwb_path")
        
        if not nwb_path:
            error_msg = "No NWB file available for evaluation"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
        
        if not Path(nwb_path).exists():
            error_msg = f"NWB file not found: {nwb_path}"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
        
        print(f"Evaluating NWB file: {nwb_path}")
        
        result = self._call_tool("evaluate_nwb_file", {
            "nwb_path": nwb_path,
            "generate_report": True
        })
        
        if result.get("status") == "success":
            print(f"[SUCCESS] NWB evaluation completed")
            evaluation = result.get("result", {})
            if "validation_errors" in evaluation:
                error_count = len(evaluation["validation_errors"])
                print(f"[INFO] Validation errors found: {error_count}")
            if "quality_score" in evaluation:
                print(f"[INFO] Quality score: {evaluation['quality_score']}")
        else:
            print(f"[ERROR] NWB evaluation failed: {result.get('message')}")
        
        return result

    def generate_knowledge_graph(self, nwb_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate knowledge graph from NWB data.
        
        Args:
            nwb_path: Path to NWB file (uses pipeline state if not provided)
            
        Returns:
            Knowledge graph generation result
        """
        print(f"\n=== Step 4: Generating Knowledge Graph ===")
        
        nwb_path = nwb_path or self.pipeline_state.get("nwb_path")
        
        if not nwb_path:
            error_msg = "No NWB file available for knowledge graph generation"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
        
        if not Path(nwb_path).exists():
            error_msg = f"NWB file not found: {nwb_path}"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
        
        print(f"Generating knowledge graph from: {nwb_path}")
        
        result = self._call_tool("generate_knowledge_graph", {
            "nwb_path": nwb_path,
            "output_format": "ttl",
            "include_provenance": True
        })
        
        if result.get("status") == "success":
            print(f"[SUCCESS] Knowledge graph generation completed")
            kg_info = result.get("result", {})
            if "graph_path" in kg_info:
                print(f"[INFO] Knowledge graph saved: {kg_info['graph_path']}")
            if "triple_count" in kg_info:
                print(f"[INFO] Triples generated: {kg_info['triple_count']}")
        else:
            print(f"[ERROR] Knowledge graph generation failed: {result.get('message')}")
        
        return result

    def reset_pipeline(self) -> Dict[str, Any]:
        """Reset pipeline state on server and client."""
        print(f"\n=== Resetting Pipeline State ===")
        
        try:
            response = requests.post(f"{self.api_url}/reset", timeout=10)
            response.raise_for_status()
            result = response.json()
            
            # Clear local state
            self.pipeline_state.clear()
            
            print(f"[SUCCESS] Pipeline state reset")
            return result
        except Exception as e:
            print(f"[ERROR] Failed to reset pipeline: {e}")
            return {"status": "error", "message": str(e)}

    def run_full_pipeline(
        self,
        dataset_dir: str,
        files_map: Dict[str, str],
        skip_kg: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete conversion pipeline.
        
        Args:
            dataset_dir: Path to dataset directory
            files_map: Mapping of data types to file paths
            skip_kg: Whether to skip knowledge graph generation
            
        Returns:
            Complete pipeline results
        """
        print(f"\n{'='*60}")
        print(f"STARTING FULL NEURODATA CONVERSION PIPELINE")
        print(f"{'='*60}")
        
        # Check server status first
        status = self.check_server_status()
        if status.get("status") == "error":
            return status
        
        # List available tools
        self.list_available_tools()
        
        results = {}
        
        # Step 1: Analyze dataset
        results["analysis"] = self.analyze_dataset(dataset_dir)
        if results["analysis"].get("status") != "success":
            print(f"\n[PIPELINE FAILED] Dataset analysis failed")
            return results
        
        # Step 2: Generate conversion
        results["conversion"] = self.generate_conversion_script(files_map)
        if results["conversion"].get("status") != "success":
            print(f"\n[PIPELINE FAILED] Conversion failed")
            return results
        
        # Step 3: Evaluate NWB file
        results["evaluation"] = self.evaluate_nwb_file()
        if results["evaluation"].get("status") != "success":
            print(f"\n[PIPELINE WARNING] Evaluation failed, but continuing...")
        
        # Step 4: Generate knowledge graph (optional)
        if not skip_kg:
            results["knowledge_graph"] = self.generate_knowledge_graph()
            if results["knowledge_graph"].get("status") != "success":
                print(f"\n[PIPELINE WARNING] Knowledge graph generation failed")
        
        # Final status
        final_status = self.check_server_status()
        results["final_status"] = final_status
        
        print(f"\n{'='*60}")
        print(f"PIPELINE COMPLETED")
        print(f"{'='*60}")
        
        # Summary
        print(f"\nPipeline Summary:")
        print(f"- Dataset Analysis: {'✓' if results['analysis'].get('status') == 'success' else '✗'}")
        print(f"- Conversion: {'✓' if results['conversion'].get('status') == 'success' else '✗'}")
        print(f"- Evaluation: {'✓' if results['evaluation'].get('status') == 'success' else '✗'}")
        if not skip_kg:
            print(f"- Knowledge Graph: {'✓' if results.get('knowledge_graph', {}).get('status') == 'success' else '✗'}")
        
        if self.pipeline_state.get("nwb_path"):
            print(f"\nOutput NWB file: {self.pipeline_state['nwb_path']}")
        
        return results


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Run Agentic Neurodata Conversion workflow example"
    )
    parser.add_argument(
        "--dataset-dir",
        default="examples/sample-datasets",
        help="Path to dataset directory"
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="MCP server URL"
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Output directory for results"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for enhanced analysis"
    )
    parser.add_argument(
        "--skip-kg",
        action="store_true",
        help="Skip knowledge graph generation"
    )
    parser.add_argument(
        "--files-map",
        help="JSON string with files mapping (e.g., '{\"recording\": \"/path/to/file.dat\"}')"
    )
    
    args = parser.parse_args()
    
    # Default files map if not provided
    files_map = {"recording": "sample_recording.dat"}
    if args.files_map:
        try:
            files_map = json.loads(args.files_map)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in --files-map: {e}")
            sys.exit(1)
    
    # Create client
    client = MCPWorkflowClient(
        api_url=args.api_url,
        output_dir=args.output_dir,
        use_llm=args.use_llm
    )
    
    # Run pipeline
    try:
        results = client.run_full_pipeline(
            dataset_dir=args.dataset_dir,
            files_map=files_map,
            skip_kg=args.skip_kg
        )
        
        # Save results
        results_file = Path(args.output_dir) / "pipeline_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {results_file}")
        
        # Exit with appropriate code
        success = all(
            result.get("status") == "success"
            for key, result in results.items()
            if key in ["analysis", "conversion"] and isinstance(result, dict)
        )
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n[INFO] Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()