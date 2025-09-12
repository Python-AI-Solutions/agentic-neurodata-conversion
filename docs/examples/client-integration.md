# Client Integration Examples

This document provides examples of integrating with the MCP server from various client applications.

## Python Client Integration

### Basic Client Setup

```python
import requests
from typing import Dict, Any, Optional

class MCPClient:
    """Basic Python client for MCP server interaction."""

    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call an MCP tool with parameters."""
        response = self.session.post(
            f"{self.api_url}/tool/{tool_name}",
            json=kwargs
        )
        response.raise_for_status()
        return response.json()

    def get_available_tools(self) -> Dict[str, Any]:
        """Get list of available tools."""
        response = self.session.get(f"{self.api_url}/tools")
        response.raise_for_status()
        return response.json()
```

### Workflow Client Example

```python
class WorkflowClient(MCPClient):
    """Client for running complete conversion workflows."""

    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        super().__init__(api_url)
        self.pipeline_state = {}

    def analyze_dataset(self, dataset_dir: str, use_llm: bool = False) -> Dict[str, Any]:
        """Analyze dataset structure and metadata."""
        result = self.call_tool("dataset_analysis",
                               dataset_dir=dataset_dir,
                               use_llm=use_llm)

        if result.get("status") == "success":
            self.pipeline_state["metadata"] = result.get("result", {})

        return result

    def convert_dataset(self, files_map: Dict[str, str]) -> Dict[str, Any]:
        """Convert dataset to NWB format."""
        if "metadata" not in self.pipeline_state:
            raise ValueError("Must analyze dataset first")

        result = self.call_tool("conversion_orchestration",
                               normalized_metadata=self.pipeline_state["metadata"],
                               files_map=files_map)

        if result.get("status") == "success":
            self.pipeline_state["nwb_path"] = result.get("output_nwb_path")

        return result

    def evaluate_conversion(self) -> Dict[str, Any]:
        """Evaluate the converted NWB file."""
        if "nwb_path" not in self.pipeline_state:
            raise ValueError("Must convert dataset first")

        return self.call_tool("evaluate_nwb_file",
                             nwb_path=self.pipeline_state["nwb_path"],
                             generate_report=True)

# Usage example
client = WorkflowClient()

# Run complete pipeline
analysis = client.analyze_dataset("/path/to/dataset")
conversion = client.convert_dataset({"recording": "/path/to/data.dat"})
evaluation = client.evaluate_conversion()
```

## JavaScript/Node.js Integration

### Basic Node.js Client

```javascript
const axios = require('axios');

class MCPClient {
    constructor(apiUrl = 'http://127.0.0.1:8000') {
        this.apiUrl = apiUrl.replace(/\/$/, '');
        this.client = axios.create({
            baseURL: this.apiUrl,
            timeout: 30000
        });
    }

    async callTool(toolName, params = {}) {
        try {
            const response = await this.client.post(`/tool/${toolName}`, params);
            return response.data;
        } catch (error) {
            throw new Error(`Tool execution failed: ${error.message}`);
        }
    }

    async getAvailableTools() {
        const response = await this.client.get('/tools');
        return response.data;
    }

    async getServerStatus() {
        const response = await this.client.get('/status');
        return response.data;
    }
}

// Usage
const client = new MCPClient();

async function runAnalysis() {
    try {
        const result = await client.callTool('dataset_analysis', {
            dataset_dir: '/path/to/dataset',
            use_llm: false
        });
        console.log('Analysis result:', result);
    } catch (error) {
        console.error('Analysis failed:', error.message);
    }
}
```

### React Integration

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const MCPDashboard = () => {
    const [tools, setTools] = useState([]);
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);

    const client = axios.create({
        baseURL: 'http://127.0.0.1:8000'
    });

    useEffect(() => {
        loadTools();
        loadStatus();
    }, []);

    const loadTools = async () => {
        try {
            const response = await client.get('/tools');
            setTools(Object.entries(response.data.tools));
        } catch (error) {
            console.error('Failed to load tools:', error);
        }
    };

    const loadStatus = async () => {
        try {
            const response = await client.get('/status');
            setStatus(response.data);
        } catch (error) {
            console.error('Failed to load status:', error);
        }
    };

    const executeTool = async (toolName, params) => {
        setLoading(true);
        try {
            const response = await client.post(`/tool/${toolName}`, params);
            console.log('Tool result:', response.data);
            return response.data;
        } catch (error) {
            console.error('Tool execution failed:', error);
            throw error;
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="mcp-dashboard">
            <h1>MCP Server Dashboard</h1>

            <div className="status-section">
                <h2>Server Status</h2>
                {status && (
                    <div>
                        <p>Status: {status.status}</p>
                        <p>Registered Tools: {status.registered_tools}</p>
                        <p>Active Agents: {status.agents.join(', ')}</p>
                    </div>
                )}
            </div>

            <div className="tools-section">
                <h2>Available Tools</h2>
                {tools.map(([name, metadata]) => (
                    <div key={name} className="tool-card">
                        <h3>{name}</h3>
                        <p>{metadata.description}</p>
                        <button
                            onClick={() => executeTool(name, {})}
                            disabled={loading}
                        >
                            Execute
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default MCPDashboard;
```

## CLI Integration

### Bash Script Integration

```bash
#!/bin/bash

# MCP Server CLI wrapper
MCP_URL="http://127.0.0.1:8000"

# Function to call MCP tools
call_mcp_tool() {
    local tool_name="$1"
    local params="$2"

    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$params" \
        "$MCP_URL/tool/$tool_name"
}

# Function to get server status
get_status() {
    curl -s "$MCP_URL/status" | jq '.'
}

# Function to list available tools
list_tools() {
    curl -s "$MCP_URL/tools" | jq '.tools'
}

# Example usage functions
analyze_dataset() {
    local dataset_dir="$1"
    local use_llm="${2:-false}"

    local params=$(jq -n \
        --arg dir "$dataset_dir" \
        --argjson llm "$use_llm" \
        '{dataset_dir: $dir, use_llm: $llm}')

    call_mcp_tool "dataset_analysis" "$params"
}

convert_dataset() {
    local metadata_file="$1"
    local files_map_file="$2"

    local metadata=$(cat "$metadata_file")
    local files_map=$(cat "$files_map_file")

    local params=$(jq -n \
        --argjson metadata "$metadata" \
        --argjson files_map "$files_map" \
        '{normalized_metadata: $metadata, files_map: $files_map}')

    call_mcp_tool "conversion_orchestration" "$params"
}

# Command line interface
case "$1" in
    "status")
        get_status
        ;;
    "tools")
        list_tools
        ;;
    "analyze")
        analyze_dataset "$2" "$3"
        ;;
    "convert")
        convert_dataset "$2" "$3"
        ;;
    *)
        echo "Usage: $0 {status|tools|analyze|convert}"
        echo "  status                    - Get server status"
        echo "  tools                     - List available tools"
        echo "  analyze <dir> [use_llm]   - Analyze dataset"
        echo "  convert <metadata> <files> - Convert dataset"
        exit 1
        ;;
esac
```

## Jupyter Notebook Integration

### Notebook Client Class

```python
# Cell 1: Setup
import requests
import json
from IPython.display import display, HTML, JSON
import pandas as pd

class NotebookMCPClient:
    """MCP client optimized for Jupyter notebook usage."""

    def __init__(self, api_url="http://127.0.0.1:8000"):
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.results = {}

    def call_tool(self, tool_name, display_result=True, **kwargs):
        """Call tool and optionally display results."""
        try:
            response = self.session.post(
                f"{self.api_url}/tool/{tool_name}",
                json=kwargs
            )
            response.raise_for_status()
            result = response.json()

            # Store result
            self.results[tool_name] = result

            if display_result:
                self._display_result(tool_name, result)

            return result

        except Exception as e:
            print(f"❌ Error calling {tool_name}: {e}")
            return {"status": "error", "message": str(e)}

    def _display_result(self, tool_name, result):
        """Display result in notebook-friendly format."""
        print(f"🔧 Tool: {tool_name}")

        if result.get("status") == "success":
            print("✅ Status: Success")
            if "result" in result:
                display(JSON(result["result"]))
        else:
            print("❌ Status: Error")
            print(f"Message: {result.get('message', 'Unknown error')}")

    def show_pipeline_summary(self):
        """Display summary of all executed tools."""
        summary_data = []
        for tool_name, result in self.results.items():
            summary_data.append({
                "Tool": tool_name,
                "Status": result.get("status", "unknown"),
                "Timestamp": result.get("timestamp", "N/A")
            })

        df = pd.DataFrame(summary_data)
        display(df)

# Cell 2: Initialize client
client = NotebookMCPClient()

# Check server status
status = client.call_tool("get_status", display_result=False)
if status.get("status") == "success":
    print("🟢 MCP Server is running")
else:
    print("🔴 MCP Server connection failed")
```

```python
# Cell 3: Dataset Analysis
dataset_path = "/path/to/your/dataset"

analysis_result = client.call_tool(
    "dataset_analysis",
    dataset_dir=dataset_path,
    use_llm=True
)
```

```python
# Cell 4: Conversion
if "dataset_analysis" in client.results:
    files_map = {
        "recording": "/path/to/recording.dat",
        "behavior": "/path/to/behavior.csv"
    }

    conversion_result = client.call_tool(
        "conversion_orchestration",
        files_map=files_map
    )
```

```python
# Cell 5: Evaluation and Summary
if "conversion_orchestration" in client.results:
    evaluation_result = client.call_tool("evaluate_nwb_file")

    # Show pipeline summary
    client.show_pipeline_summary()
```

## Error Handling Patterns

### Robust Client Implementation

```python
import time
from typing import Optional
import logging

class RobustMCPClient:
    """MCP client with retry logic and comprehensive error handling."""

    def __init__(self, api_url: str, max_retries: int = 3, timeout: int = 30):
        self.api_url = api_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

    def call_tool_with_retry(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call tool with automatic retry on failure."""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    f"{self.api_url}/tool/{tool_name}",
                    json=kwargs,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout as e:
                last_error = f"Timeout after {self.timeout}s"
                self.logger.warning(f"Attempt {attempt + 1} timed out")

            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                self.logger.warning(f"Attempt {attempt + 1} connection failed")

            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500:
                    last_error = f"Server error: {e.response.status_code}"
                    self.logger.warning(f"Attempt {attempt + 1} server error")
                else:
                    # Client error, don't retry
                    return {
                        "status": "error",
                        "message": f"Client error: {e.response.status_code}"
                    }

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                self.logger.info(f"Waiting {wait_time}s before retry")
                time.sleep(wait_time)

        return {
            "status": "error",
            "message": f"Failed after {self.max_retries} attempts: {last_error}"
        }

    def health_check(self) -> bool:
        """Check if MCP server is healthy."""
        try:
            response = self.session.get(f"{self.api_url}/status", timeout=5)
            return response.status_code == 200
        except:
            return False
```

## Authentication Examples

### API Key Authentication

```python
class AuthenticatedMCPClient(MCPClient):
    """MCP client with API key authentication."""

    def __init__(self, api_url: str, api_key: str):
        super().__init__(api_url)
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "X-API-Key": api_key
        })
```

### OAuth Integration

```python
from requests_oauthlib import OAuth2Session

class OAuthMCPClient(MCPClient):
    """MCP client with OAuth2 authentication."""

    def __init__(self, api_url: str, client_id: str, client_secret: str, token_url: str):
        super().__init__(api_url)
        self.oauth = OAuth2Session(client_id)
        self.client_secret = client_secret
        self.token_url = token_url
        self._authenticate()

    def _authenticate(self):
        """Perform OAuth2 authentication."""
        token = self.oauth.fetch_token(
            self.token_url,
            client_secret=self.client_secret
        )
        self.session.headers.update({
            "Authorization": f"Bearer {token['access_token']}"
        })
```

These examples demonstrate various ways to integrate with the MCP server from different client environments, with proper error handling and authentication patterns.
