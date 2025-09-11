"""
Mock services and utilities for testing.

This module provides mock implementations of external services
and dependencies for isolated testing.
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, Mock


class MockLLMClient:
    """Mock LLM client for testing without external API calls."""

    def __init__(self, responses: Optional[dict[str, Any]] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.call_history: list[dict[str, Any]] = []

    async def generate_completion(self, prompt: str, **kwargs) -> str:
        """Generate mock completion."""
        self.call_count += 1
        self.call_history.append(
            {"method": "generate_completion", "prompt": prompt, "kwargs": kwargs}
        )

        # Return predefined response or default
        if "completion" in self.responses:
            return self.responses["completion"]

        return f"Mock completion for prompt: {prompt[:50]}..."

    async def generate_questions(self, context: str, **kwargs) -> list[dict[str, Any]]:
        """Generate mock questions."""
        self.call_count += 1
        self.call_history.append(
            {"method": "generate_questions", "context": context, "kwargs": kwargs}
        )

        if "questions" in self.responses:
            return self.responses["questions"]

        return [
            {
                "field": "experimenter",
                "question": "Who performed this experiment?",
                "explanation": "Required for NWB metadata",
                "priority": "high",
            },
            {
                "field": "session_description",
                "question": "What was the purpose of this recording session?",
                "explanation": "Provides context for the data",
                "priority": "medium",
            },
        ]

    async def analyze_format(
        self, file_info: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        """Analyze data format."""
        self.call_count += 1
        self.call_history.append(
            {"method": "analyze_format", "file_info": file_info, "kwargs": kwargs}
        )

        if "format_analysis" in self.responses:
            return self.responses["format_analysis"]

        return {
            "detected_format": "open_ephys",
            "confidence": 0.95,
            "reasoning": "Mock format detection based on file patterns",
        }


class MockNeuroConvInterface:
    """Mock NeuroConv interface for testing."""

    def __init__(self, responses: Optional[dict[str, Any]] = None):
        self.responses = responses or {}
        self.conversion_calls: list[dict[str, Any]] = []

    def get_metadata(self) -> dict[str, Any]:
        """Get mock metadata."""
        if "metadata" in self.responses:
            return self.responses["metadata"]

        return {
            "session_description": "Mock recording session",
            "experimenter": ["Mock Experimenter"],
            "lab": "Mock Lab",
            "institution": "Mock Institution",
        }

    def run_conversion(self, nwbfile_path: str, metadata: dict[str, Any], **kwargs):
        """Mock conversion execution."""
        self.conversion_calls.append(
            {"nwbfile_path": nwbfile_path, "metadata": metadata, "kwargs": kwargs}
        )

        # Create mock NWB file
        Path(nwbfile_path).touch()

    def validate(self) -> list[str]:
        """Mock validation."""
        if "validation_errors" in self.responses:
            return self.responses["validation_errors"]

        return []  # No errors


class MockNWBInspector:
    """Mock NWB Inspector for testing."""

    def __init__(self, responses: Optional[dict[str, Any]] = None):
        self.responses = responses or {}
        self.inspection_calls: list[str] = []

    def inspect_nwb_file(self, nwb_path: str) -> dict[str, Any]:
        """Mock NWB file inspection."""
        self.inspection_calls.append(nwb_path)

        if "inspection_results" in self.responses:
            return self.responses["inspection_results"]

        return {
            "status": "passed",
            "errors": [],
            "warnings": [],
            "info": ["Mock inspection completed successfully"],
        }


class MockDataLadDataset:
    """Mock DataLad dataset for testing."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.saved_files: list[str] = []
        self.installed_datasets: list[str] = []

    def save(self, path: Optional[str] = None, message: str = ""):
        """Mock save operation."""
        if path:
            self.saved_files.append(path)
        return {"status": "ok", "path": path or self.path}

    def install(self, source: str, path: Optional[str] = None):
        """Mock install operation."""
        install_path = path or source.split("/")[-1]
        self.installed_datasets.append(install_path)
        return {"status": "ok", "path": install_path}

    def get(self, path: str):
        """Mock get operation."""
        return {"status": "ok", "path": path}


class MockMCPServer:
    """Mock MCP server for testing client interactions."""

    def __init__(self):
        self.tools: dict[str, Callable] = {}
        self.tool_calls: list[dict[str, Any]] = []
        self.pipeline_state: dict[str, Any] = {}

    def register_tool(self, name: str, func: Callable):
        """Register a mock tool."""
        self.tools[name] = func

    async def execute_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Execute mock tool."""
        self.tool_calls.append(
            {
                "tool": tool_name,
                "kwargs": kwargs,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        if tool_name in self.tools:
            return await self.tools[tool_name](**kwargs)

        # Default responses for common tools
        default_responses = {
            "initialize_pipeline": {
                "status": "success",
                "config": {"output_dir": "/tmp/test_output"},
            },
            "analyze_dataset": {
                "status": "success",
                "result": {
                    "format_analysis": {"formats": ["open_ephys"]},
                    "enriched_metadata": {"experimenter": "Test User"},
                    "missing_metadata": [],
                },
            },
            "generate_conversion_script": {
                "status": "success",
                "output_nwb_path": "/tmp/test_output.nwb",
                "script_content": "# Mock conversion script",
            },
            "evaluate_nwb_file": {
                "status": "success",
                "validation": {"nwb_inspector": {"status": "passed"}},
                "quality_score": 0.95,
            },
            "generate_knowledge_graph": {
                "status": "success",
                "ttl_path": "/tmp/test_output.ttl",
                "entities_count": 42,
            },
        }

        return default_responses.get(
            tool_name, {"status": "error", "message": f"Unknown tool: {tool_name}"}
        )

    def reset_pipeline(self):
        """Reset pipeline state."""
        self.pipeline_state.clear()
        return {"status": "reset"}


class MockHTTPClient:
    """Mock HTTP client for testing API interactions."""

    def __init__(self):
        self.requests: list[dict[str, Any]] = []
        self.responses: dict[str, Any] = {}

    def set_response(self, url_pattern: str, response: dict[str, Any]):
        """Set mock response for URL pattern."""
        self.responses[url_pattern] = response

    async def post(
        self, url: str, json_data: Optional[dict] = None, **kwargs
    ) -> dict[str, Any]:
        """Mock POST request."""
        self.requests.append(
            {"method": "POST", "url": url, "json": json_data, "kwargs": kwargs}
        )

        # Find matching response
        for pattern, response in self.responses.items():
            if pattern in url:
                return response

        # Default response
        return {"status": "success", "data": {}}

    async def get(self, url: str, **kwargs) -> dict[str, Any]:
        """Mock GET request."""
        self.requests.append({"method": "GET", "url": url, "kwargs": kwargs})

        # Find matching response
        for pattern, response in self.responses.items():
            if pattern in url:
                return response

        # Default response
        return {"status": "success", "data": {}}


def create_mock_agent(agent_type: str) -> Mock:
    """Create a mock agent with common interface."""
    agent = Mock()
    agent.agent_type = agent_type

    # Mock execute method
    async def mock_execute(**kwargs):
        # Mock result without importing actual classes
        result = Mock()
        result.status = "COMPLETED"
        result.data = {"mock": f"{agent_type}_result", "input": kwargs}
        result.error = None
        result.execution_time = 0.1
        return result

    agent.execute = AsyncMock(side_effect=mock_execute)
    agent.get_metrics = Mock(
        return_value={
            "total_executions": 1,
            "successful_executions": 1,
            "failed_executions": 0,
            "success_rate": 1.0,
            "average_execution_time": 0.1,
        }
    )

    return agent


def create_mock_settings() -> Mock:
    """Create mock application settings."""
    settings = Mock()

    # Environment settings
    settings.environment = "test"
    settings.debug = True
    settings.log_level = "DEBUG"

    # Server settings
    settings.server = Mock()
    settings.server.host = "127.0.0.1"
    settings.server.port = 8000
    settings.server.workers = 1

    # Agent settings
    settings.agents = Mock()
    settings.agents.conversation = Mock()
    settings.agents.conversion = Mock()
    settings.agents.evaluation = Mock()
    settings.agents.knowledge_graph = Mock()

    # Database settings
    settings.database = Mock()
    settings.database.url = "sqlite:///:memory:"

    return settings


class MockFileSystem:
    """Mock file system for testing file operations."""

    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.directories: set[str] = set()

    def create_file(self, path: str, content: bytes = b""):
        """Create a mock file."""
        self.files[path] = content

        # Create parent directories
        parent = str(Path(path).parent)
        if parent != ".":
            self.directories.add(parent)

    def create_directory(self, path: str):
        """Create a mock directory."""
        self.directories.add(path)

    def exists(self, path: str) -> bool:
        """Check if path exists."""
        return path in self.files or path in self.directories

    def read_file(self, path: str) -> bytes:
        """Read mock file content."""
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]

    def list_directory(self, path: str) -> list[str]:
        """List directory contents."""
        if path not in self.directories:
            raise FileNotFoundError(f"Directory not found: {path}")

        contents = []
        for file_path in self.files:
            if str(Path(file_path).parent) == path:
                contents.append(Path(file_path).name)

        for dir_path in self.directories:
            if str(Path(dir_path).parent) == path:
                contents.append(Path(dir_path).name)

        return contents
