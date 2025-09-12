#!/usr/bin/env python3
"""
Simple MCP client template for basic server interaction.

This is a minimal example showing the essential patterns for interacting
with the Agentic Neurodata Conversion MCP Server. Use this as a starting
point for building custom integrations.

Usage:
    # Start MCP server first
    pixi run server

    # Run this example
    pixi run python simple_client.py
"""

import json
from typing import Any, Optional

import requests


class SimpleMCPClient:
    """
    Minimal MCP client demonstrating basic interaction patterns.

    This client shows the essential methods needed to interact with
    the MCP server. It's designed to be simple and easy to understand.
    """

    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        """
        Initialize the simple MCP client.

        Args:
            api_url: MCP server URL (default: http://127.0.0.1:8000)
        """
        self.api_url = api_url.rstrip("/")

    def _call_tool(
        self, tool_name: str, payload: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Call an MCP server tool.

        Args:
            tool_name: Name of the tool to call
            payload: Parameters to send to the tool

        Returns:
            Tool execution result
        """
        url = f"{self.api_url}/tool/{tool_name}"

        try:
            response = requests.post(url, json=payload or {})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error calling {tool_name}: {e}")
            return {"status": "error", "message": str(e)}

    def get_server_status(self) -> dict[str, Any]:
        """
        Get server status and basic information.

        Returns:
            Server status information
        """
        try:
            response = requests.get(f"{self.api_url}/status")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Server not reachable: {e}"}

    def list_tools(self) -> dict[str, Any]:
        """
        Get list of available MCP tools.

        Returns:
            Dictionary of available tools and their metadata
        """
        try:
            response = requests.get(f"{self.api_url}/tools")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"tools": {}, "error": str(e)}

    def analyze_dataset(
        self, dataset_dir: str, use_llm: bool = False
    ) -> dict[str, Any]:
        """
        Analyze a dataset directory.

        Args:
            dataset_dir: Path to the dataset directory
            use_llm: Whether to use LLM for enhanced analysis

        Returns:
            Analysis results with metadata
        """
        return self._call_tool(
            "dataset_analysis", {"dataset_dir": dataset_dir, "use_llm": use_llm}
        )

    def convert_dataset(
        self, metadata: dict[str, Any], files_map: dict[str, str]
    ) -> dict[str, Any]:
        """
        Convert dataset to NWB format.

        Args:
            metadata: Normalized metadata from dataset analysis
            files_map: Mapping of data types to file paths

        Returns:
            Conversion results with NWB file path
        """
        return self._call_tool(
            "conversion_orchestration",
            {"normalized_metadata": metadata, "files_map": files_map},
        )

    def evaluate_nwb(self, nwb_path: str) -> dict[str, Any]:
        """
        Evaluate an NWB file.

        Args:
            nwb_path: Path to the NWB file

        Returns:
            Evaluation results and quality metrics
        """
        return self._call_tool(
            "evaluate_nwb_file", {"nwb_path": nwb_path, "generate_report": True}
        )


def demo_basic_usage():
    """Demonstrate basic MCP client usage."""
    print("=== Simple MCP Client Demo ===\n")

    # Create client
    client = SimpleMCPClient()

    # 1. Check server status
    print("1. Checking server status...")
    status = client.get_server_status()
    print(f"   Status: {json.dumps(status, indent=2)}\n")

    if status.get("status") == "error":
        print("   Server is not running. Please start it with: pixi run server")
        return

    # 2. List available tools
    print("2. Listing available tools...")
    tools = client.list_tools()
    if "tools" in tools:
        tool_names = list(tools["tools"].keys())
        print(f"   Available tools: {tool_names}\n")
    else:
        print(f"   Error getting tools: {tools.get('error')}\n")

    # 3. Try dataset analysis (with example path)
    print("3. Analyzing example dataset...")
    dataset_dir = "examples/sample-datasets"  # This may not exist yet
    analysis_result = client.analyze_dataset(dataset_dir, use_llm=False)
    print(f"   Analysis result: {json.dumps(analysis_result, indent=2)}\n")

    # 4. Show how to handle results
    if analysis_result.get("status") == "success":
        print("   ✓ Dataset analysis succeeded!")
        metadata = analysis_result.get("result", {})
        print(f"   Metadata keys: {list(metadata.keys())}")

        # Example of next step (conversion)
        print("\n4. Example conversion (would need real files)...")
        files_map = {"recording": "example_file.dat"}
        conversion_result = client.convert_dataset(metadata, files_map)
        print(f"   Conversion result: {json.dumps(conversion_result, indent=2)}")

    else:
        print("   ✗ Dataset analysis failed or dataset not found")
        print("   This is expected if the example dataset doesn't exist yet")


def demo_error_handling():
    """Demonstrate error handling patterns."""
    print("\n=== Error Handling Demo ===\n")

    client = SimpleMCPClient()

    # Try calling a non-existent tool
    print("1. Calling non-existent tool...")
    result = client._call_tool("nonexistent_tool", {"param": "value"})
    print(f"   Result: {json.dumps(result, indent=2)}\n")

    # Try with invalid server URL
    print("2. Testing with invalid server URL...")
    bad_client = SimpleMCPClient("http://localhost:9999")
    status = bad_client.get_server_status()
    print(f"   Status: {json.dumps(status, indent=2)}\n")


def demo_custom_workflow():
    """Demonstrate building a custom workflow."""
    print("\n=== Custom Workflow Demo ===\n")

    client = SimpleMCPClient()

    # Check if server is available
    status = client.get_server_status()
    if status.get("status") == "error":
        print("Server not available for custom workflow demo")
        return

    print("Building a custom 2-step workflow:")
    print("Step 1: Dataset Analysis")
    print("Step 2: Results Processing")

    # Step 1: Analysis
    dataset_dir = "examples/sample-datasets"
    analysis = client.analyze_dataset(dataset_dir)

    # Step 2: Process results
    if analysis.get("status") == "success":
        print("✓ Analysis completed, processing results...")
        metadata = analysis.get("result", {})

        # Custom processing logic here
        processed_data = {
            "original_metadata": metadata,
            "processing_timestamp": "2024-01-01T00:00:00Z",
            "custom_field": "Added by custom workflow",
        }

        print("✓ Custom processing completed")
        print(f"   Processed data keys: {list(processed_data.keys())}")
    else:
        print("✗ Analysis failed, skipping processing")


def main():
    """Main function demonstrating various client patterns."""
    try:
        # Basic usage demo
        demo_basic_usage()

        # Error handling demo
        demo_error_handling()

        # Custom workflow demo
        demo_custom_workflow()

        print("\n=== Demo Complete ===")
        print("This example shows the basic patterns for MCP client development.")
        print("Use these patterns as a starting point for your own integrations.")

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error in demo: {e}")


if __name__ == "__main__":
    main()
