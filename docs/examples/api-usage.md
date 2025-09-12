# API Usage Examples

This document provides practical examples of using the MCP server API for various tasks.

## HTTP API Usage

### Basic API Interaction

```python
import requests
import json

# Server configuration
API_BASE = "http://127.0.0.1:8000"

def call_api(endpoint, method="GET", data=None):
    """Helper function for API calls."""
    url = f"{API_BASE}{endpoint}"

    if method == "GET":
        response = requests.get(url)
    elif method == "POST":
        response = requests.post(url, json=data)

    response.raise_for_status()
    return response.json()

# Check server status
status = call_api("/status")
print("Server Status:", json.dumps(status, indent=2))

# List available tools
tools = call_api("/tools")
print("Available Tools:", list(tools["tools"].keys()))

# Execute a tool
result = call_api("/tool/dataset_analysis", "POST", {
    "dataset_dir": "/path/to/dataset",
    "use_llm": False
})
print("Analysis Result:", result["status"])
```

### Error Handling

```python
import requests
from typing import Dict, Any, Optional

class MCPAPIClient:
    """Robust API client with comprehensive error handling."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "MCP-API-Client/1.0"
        })

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call MCP tool with comprehensive error handling."""
        try:
            response = self.session.post(
                f"{self.base_url}/tool/{tool_name}",
                json=kwargs,
                timeout=30
            )

            # Handle HTTP errors
            if response.status_code == 404:
                return {
                    "status": "error",
                    "message": f"Tool '{tool_name}' not found",
                    "available_tools": self.get_available_tools()
                }
            elif response.status_code == 422:
                return {
                    "status": "error",
                    "message": "Invalid parameters",
                    "details": response.json() if response.content else None
                }
            elif response.status_code >= 500:
                return {
                    "status": "error",
                    "message": f"Server error: {response.status_code}",
                    "server_response": response.text[:200]
                }

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "message": f"Cannot connect to MCP server at {self.base_url}",
                "suggestion": "Check if the server is running"
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "message": "Request timed out",
                "suggestion": "Try again or increase timeout"
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"Request failed: {str(e)}"
            }
        except json.JSONDecodeError:
            return {
                "status": "error",
                "message": "Invalid JSON response from server"
            }

    def get_available_tools(self) -> list:
        """Get list of available tool names."""
        try:
            response = self.session.get(f"{self.base_url}/tools", timeout=10)
            response.raise_for_status()
            tools_data = response.json()
            return list(tools_data.get("tools", {}).keys())
        except:
            return []

    def health_check(self) -> Dict[str, Any]:
        """Check server health and connectivity."""
        try:
            response = self.session.get(f"{self.base_url}/status", timeout=5)
            response.raise_for_status()

            status_data = response.json()
            return {
                "healthy": True,
                "status": status_data.get("status"),
                "tools_count": status_data.get("registered_tools", 0),
                "agents": status_data.get("agents", [])
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }

# Usage example
client = MCPAPIClient()

# Check health first
health = client.health_check()
if not health["healthy"]:
    print(f"Server not healthy: {health['error']}")
    exit(1)

# Call tool with error handling
result = client.call_tool("dataset_analysis",
                         dataset_dir="/nonexistent/path")

if result["status"] == "error":
    print(f"Error: {result['message']}")
    if "suggestion" in result:
        print(f"Suggestion: {result['suggestion']}")
else:
    print("Success!")
```

## Tool-Specific Usage Examples

### Dataset Analysis Tool

```python
def analyze_dataset_comprehensive(client, dataset_dir: str):
    """Comprehensive dataset analysis with multiple options."""

    # Basic analysis
    print("🔍 Running basic analysis...")
    basic_result = client.call_tool("dataset_analysis",
                                   dataset_dir=dataset_dir,
                                   use_llm=False)

    if basic_result["status"] != "success":
        print(f"Basic analysis failed: {basic_result['message']}")
        return None

    # Enhanced analysis with LLM
    print("🧠 Running enhanced analysis with LLM...")
    enhanced_result = client.call_tool("dataset_analysis",
                                      dataset_dir=dataset_dir,
                                      use_llm=True)

    # Compare results
    basic_metadata = basic_result.get("result", {}).get("normalized_metadata", {})
    enhanced_metadata = enhanced_result.get("result", {}).get("normalized_metadata", {})

    print("\n📊 Analysis Comparison:")
    print(f"Basic metadata fields: {len(basic_metadata)}")
    print(f"Enhanced metadata fields: {len(enhanced_metadata)}")

    # Show additional fields from LLM analysis
    enhanced_only = set(enhanced_metadata.keys()) - set(basic_metadata.keys())
    if enhanced_only:
        print(f"Additional fields from LLM: {list(enhanced_only)}")

    return enhanced_result

# Usage
client = MCPAPIClient()
result = analyze_dataset_comprehensive(client, "/path/to/dataset")
```

### Conversion Orchestration Tool

```python
def convert_with_options(client, metadata: dict, files_map: dict,
                        conversion_options: dict = None):
    """Convert dataset with custom options."""

    # Default conversion options
    default_options = {
        "compression": "gzip",
        "compression_opts": 9,
        "shuffle": True,
        "fletcher32": True,
        "chunk_shape": "auto"
    }

    # Merge with user options
    if conversion_options:
        default_options.update(conversion_options)

    print("⚙️  Starting conversion with options:")
    for key, value in default_options.items():
        print(f"   {key}: {value}")

    result = client.call_tool("conversion_orchestration",
                             normalized_metadata=metadata,
                             files_map=files_map,
                             conversion_options=default_options)

    if result["status"] == "success":
        nwb_path = result.get("output_nwb_path")
        print(f"✅ Conversion completed: {nwb_path}")

        # Get file size
        import os
        if os.path.exists(nwb_path):
            size_mb = os.path.getsize(nwb_path) / (1024 * 1024)
            print(f"📁 File size: {size_mb:.2f} MB")

        return result
    else:
        print(f"❌ Conversion failed: {result['message']}")
        return None

# Usage with custom options
custom_options = {
    "compression": "lzf",  # Faster compression
    "chunk_shape": (1000, 100)  # Custom chunking
}

result = convert_with_options(
    client,
    metadata={"experiment_description": "Test experiment"},
    files_map={"recording": "/path/to/data.dat"},
    conversion_options=custom_options
)
```

### NWB File Evaluation Tool

```python
def evaluate_with_detailed_report(client, nwb_path: str):
    """Evaluate NWB file with detailed reporting."""

    print(f"🔬 Evaluating NWB file: {nwb_path}")

    # Run evaluation with different validation levels
    validation_levels = ["basic", "standard", "strict"]
    results = {}

    for level in validation_levels:
        print(f"   Running {level} validation...")

        result = client.call_tool("nwb_file_validation",
                                 nwb_file_path=nwb_path,
                                 validation_level=level,
                                 generate_report=True)

        if result["status"] == "success":
            summary = result.get("result", {}).get("summary", {})
            results[level] = {
                "valid": summary.get("overall_valid", False),
                "quality_score": summary.get("quality_score", 0),
                "errors": summary.get("total_errors", 0),
                "warnings": summary.get("total_warnings", 0)
            }
        else:
            results[level] = {"error": result.get("message")}

    # Display comparison
    print("\n📊 Validation Level Comparison:")
    print(f"{'Level':<10} {'Valid':<8} {'Score':<8} {'Errors':<8} {'Warnings':<10}")
    print("-" * 50)

    for level, data in results.items():
        if "error" in data:
            print(f"{level:<10} {'ERROR':<8} {'-':<8} {'-':<8} {data['error'][:20]}")
        else:
            valid_str = "✅" if data["valid"] else "❌"
            print(f"{level:<10} {valid_str:<8} {data['quality_score']:<8} "
                  f"{data['errors']:<8} {data['warnings']:<10}")

    return results

# Usage
results = evaluate_with_detailed_report(client, "/path/to/file.nwb")
```

## Advanced API Patterns

### Async API Client

```python
import asyncio
import aiohttp
from typing import Dict, Any

class AsyncMCPClient:
    """Asynchronous MCP API client for high-performance applications."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Content-Type": "application/json"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Async tool call."""
        try:
            async with self.session.post(
                f"{self.base_url}/tool/{tool_name}",
                json=kwargs
            ) as response:

                if response.status == 200:
                    return await response.json()
                else:
                    return {
                        "status": "error",
                        "message": f"HTTP {response.status}: {await response.text()}"
                    }

        except asyncio.TimeoutError:
            return {
                "status": "error",
                "message": "Request timed out"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    async def batch_analyze(self, datasets: list) -> list:
        """Analyze multiple datasets concurrently."""
        tasks = []

        for dataset in datasets:
            task = self.call_tool("dataset_analysis",
                                 dataset_dir=dataset["path"],
                                 use_llm=dataset.get("use_llm", False))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "dataset": datasets[i]["name"],
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append({
                    "dataset": datasets[i]["name"],
                    **result
                })

        return processed_results

# Usage
async def main():
    datasets = [
        {"name": "exp1", "path": "/data/exp1", "use_llm": True},
        {"name": "exp2", "path": "/data/exp2", "use_llm": False},
        {"name": "exp3", "path": "/data/exp3", "use_llm": True}
    ]

    async with AsyncMCPClient() as client:
        results = await client.batch_analyze(datasets)

        for result in results:
            print(f"Dataset {result['dataset']}: {result['status']}")

# Run async example
# asyncio.run(main())
```

### Pipeline State Management

```python
class StatefulMCPClient(MCPAPIClient):
    """MCP client with pipeline state management."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        super().__init__(base_url)
        self.local_state = {}

    def get_server_state(self) -> Dict[str, Any]:
        """Get current server pipeline state."""
        status = self.call_api("/status")
        return status.get("pipeline_state", {})

    def reset_pipeline(self) -> Dict[str, Any]:
        """Reset server pipeline state."""
        result = self.call_api("/reset", "POST")
        self.local_state.clear()
        return result

    def call_tool_stateful(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call tool and update local state."""
        result = self.call_tool(tool_name, **kwargs)

        if result.get("status") == "success":
            # Update local state with any state updates
            state_updates = result.get("state_updates", {})
            self.local_state.update(state_updates)

            # Store result for potential reuse
            self.local_state[f"last_{tool_name}_result"] = result

        return result

    def get_pipeline_progress(self) -> Dict[str, Any]:
        """Get current pipeline progress."""
        server_state = self.get_server_state()

        # Determine pipeline stage based on state
        stages = {
            "analysis": "last_analyzed_dataset" in server_state,
            "metadata": "normalized_metadata" in server_state,
            "conversion": "current_nwb_path" in server_state,
            "evaluation": "validation_passed" in server_state
        }

        completed_stages = [stage for stage, completed in stages.items() if completed]

        return {
            "completed_stages": completed_stages,
            "current_stage": completed_stages[-1] if completed_stages else "not_started",
            "progress_percent": len(completed_stages) / len(stages) * 100,
            "server_state": server_state,
            "local_state": self.local_state
        }

    def resume_pipeline(self, dataset_dir: str, files_map: dict) -> Dict[str, Any]:
        """Resume pipeline from current state."""
        progress = self.get_pipeline_progress()
        current_stage = progress["current_stage"]

        print(f"📊 Current pipeline stage: {current_stage}")
        print(f"📈 Progress: {progress['progress_percent']:.1f}%")

        if current_stage == "not_started":
            print("🔍 Starting from analysis...")
            return self.call_tool_stateful("dataset_analysis",
                                          dataset_dir=dataset_dir)

        elif current_stage == "analysis":
            print("⚙️  Resuming from conversion...")
            metadata = progress["server_state"].get("normalized_metadata", {})
            return self.call_tool_stateful("conversion_orchestration",
                                          normalized_metadata=metadata,
                                          files_map=files_map)

        elif current_stage == "conversion":
            print("🔬 Resuming from evaluation...")
            nwb_path = progress["server_state"].get("current_nwb_path")
            return self.call_tool_stateful("evaluate_nwb_file",
                                          nwb_path=nwb_path)

        else:
            print("✅ Pipeline already completed")
            return {"status": "completed", "message": "Pipeline already finished"}

# Usage
client = StatefulMCPClient()

# Check current progress
progress = client.get_pipeline_progress()
print(f"Current progress: {progress['progress_percent']:.1f}%")

# Resume or start pipeline
result = client.resume_pipeline(
    dataset_dir="/path/to/dataset",
    files_map={"recording": "/path/to/data.dat"}
)
```

### Custom Tool Registration

```python
def register_custom_tool(client, tool_definition: dict):
    """Register a custom tool (conceptual - would need server support)."""

    # This is a conceptual example of how custom tools might be registered
    # In practice, tools are registered server-side using the @mcp.tool decorator

    tool_spec = {
        "name": tool_definition["name"],
        "description": tool_definition["description"],
        "parameters": tool_definition["parameters"],
        "implementation": tool_definition["implementation_url"]
    }

    # This would be a hypothetical endpoint for dynamic tool registration
    result = client.call_api("/register_tool", "POST", tool_spec)
    return result

# Example custom tool definition
custom_tool = {
    "name": "custom_quality_check",
    "description": "Custom quality assessment for specific data types",
    "parameters": {
        "data_path": {"type": "string", "required": True},
        "quality_threshold": {"type": "number", "default": 0.8}
    },
    "implementation_url": "https://example.com/custom_tool.py"
}

# Register custom tool (conceptual)
# result = register_custom_tool(client, custom_tool)
```

## Integration Patterns

### Webhook Integration

```python
from flask import Flask, request, jsonify
import threading
import time

class WebhookMCPIntegration:
    """Integration that responds to webhooks by triggering MCP workflows."""

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/webhook/dataset_uploaded', methods=['POST'])
        def handle_dataset_upload():
            data = request.json
            dataset_path = data.get('dataset_path')

            if not dataset_path:
                return jsonify({"error": "dataset_path required"}), 400

            # Trigger async processing
            threading.Thread(
                target=self.process_dataset_async,
                args=(dataset_path, data)
            ).start()

            return jsonify({"status": "processing_started"})

        @self.app.route('/webhook/conversion_complete', methods=['POST'])
        def handle_conversion_complete():
            data = request.json
            nwb_path = data.get('nwb_path')

            # Trigger evaluation
            result = self.mcp_client.call_tool("evaluate_nwb_file",
                                              nwb_path=nwb_path)

            return jsonify(result)

    def process_dataset_async(self, dataset_path: str, metadata: dict):
        """Process dataset asynchronously."""
        try:
            # Analysis
            analysis_result = self.mcp_client.call_tool("dataset_analysis",
                                                       dataset_dir=dataset_path)

            if analysis_result.get("status") == "success":
                # Extract files from metadata or analysis
                files_map = metadata.get("files_map", {})

                # Conversion
                conversion_result = self.mcp_client.call_tool(
                    "conversion_orchestration",
                    normalized_metadata=analysis_result["result"]["normalized_metadata"],
                    files_map=files_map
                )

                # Notify completion (could send webhook, email, etc.)
                self.notify_completion(dataset_path, conversion_result)

        except Exception as e:
            self.notify_error(dataset_path, str(e))

    def notify_completion(self, dataset_path: str, result: dict):
        """Notify about completion."""
        print(f"✅ Processing completed for {dataset_path}")
        # Could send webhook, email, Slack message, etc.

    def notify_error(self, dataset_path: str, error: str):
        """Notify about error."""
        print(f"❌ Processing failed for {dataset_path}: {error}")
        # Could send error notification

# Usage
client = MCPAPIClient()
webhook_integration = WebhookMCPIntegration(client)

# Run webhook server
# webhook_integration.app.run(host='0.0.0.0', port=5000)
```

These API usage examples demonstrate various patterns for interacting with the MCP server, from basic HTTP calls to advanced async processing and webhook integrations. Each example includes proper error handling and follows best practices for API consumption.
