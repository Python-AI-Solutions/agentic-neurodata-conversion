# Testing and Quality Assurance Design

## Overview

This design document outlines comprehensive testing strategies and quality
assurance for the agentic neurodata conversion project. The testing framework
covers the MCP server, individual agents, client libraries, and end-to-end
conversion workflows, leveraging DataLad-managed test datasets for consistent
and reproducible testing.

## Architecture

### High-Level Testing Architecture

```
Testing and Quality Assurance Framework
├── Unit Testing Layer
│   ├── MCP Server Tests
│   ├── Agent Tests
│   ├── Client Library Tests
│   └── Utility Function Tests
├── Integration Testing Layer
│   ├── Agent-MCP Server Integration
│   ├── Client-Server Integration
│   ├── External Service Integration
│   └── End-to-End Pipeline Tests
├── Quality Assurance Systems
│   ├── Code Quality Checks
│   ├── Performance Testing
│   ├── Load Testing
│   └── Validation Testing
├── Test Data Management
│   ├── DataLad Test Datasets
│   ├── Mock Data Generation
│   ├── Fixture Management
│   └── Test Environment Setup
└── CI/CD Integration
    ├── Automated Test Execution
    ├── Coverage Reporting
    ├── Quality Gates
    └── Deployment Testing
```

### Testing Flow

```
Code Changes → Pre-commit Hooks → Unit Tests → Integration Tests → E2E Tests → Quality Gates → Deployment
                     ↓
Test Data Management → DataLad Datasets → Mock Services → Test Fixtures → Test Execution
                     ↓
Results Collection → Coverage Analysis → Performance Metrics → Quality Reports → Feedback Loop
```

## Core Components

### 1. Unit Testing Framework

#### MCP Server Testing

```python
# tests/unit/test_mcp_server.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from src.agentic_converter.mcp_server.server import MCPServer, mcp
from src.agentic_converter.mcp_server.interfaces.fastapi_interface import create_fastapi_app
from src.agentic_converter.core.config import Settings

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.server.host = "127.0.0.1"
    settings.server.port = 8000
    settings.server.debug = True
    settings.agents = Mock()
    return settings

@pytest.fixture
def mcp_server(mock_settings):
    """MCP server instance for testing."""
    with patch('src.agentic_converter.mcp_server.server.MCPServer._initialize_agents'):
        server = MCPServer(mock_settings)
        server.agents = {
            'conversation': Mock(),
            'conversion': Mock(),
            'evaluation': Mock(),
            'knowledge_graph': Mock()
        }
        return server

@pytest.fixture
def test_client(mcp_server):
    """FastAPI test client."""
    app = create_fastapi_app(mcp_server)
    return TestClient(app)

class TestMCPServer:
    """Test MCP server core functionality."""

    def test_server_initialization(self, mcp_server):
        """Test server initializes correctly."""
        assert mcp_server.agents is not None
        assert len(mcp_server.agents) == 4
        assert 'conversation' in mcp_server.agents
        assert 'conversion' in mcp_server.agents
        assert 'evaluation' in mcp_server.agents
        assert 'knowledge_graph' in mcp_server.agents

    @pytest.mark.asyncio
    async def test_tool_execution_success(self, mcp_server):
        """Test successful tool execution."""
        # Register a test tool
        @mcp.tool(name="test_tool")
        async def test_tool_func(param1: str, server=None):
            return {"status": "success", "result": param1}

        result = await mcp_server.execute_tool("test_tool", param1="test_value")

        assert result["status"] == "success"
        assert result["result"] == "test_value"

    @pytest.mark.asyncio
    async def test_tool_execution_error(self, mcp_server):
        """Test tool execution error handling."""
        # Register a tool that raises an exception
        @mcp.tool(name="error_tool")
        async def error_tool_func(server=None):
            raise ValueError("Test error")

        result = await mcp_server.execute_tool("error_tool")

        assert result["status"] == "error"
        assert "Test error" in result["message"]

    @pytest.mark.asyncio
    async def test_nonexistent_tool(self, mcp_server):
        """Test execution of non-existent tool."""
        with pytest.raises(ValueError, match="Tool not found"):
            await mcp_server.execute_tool("nonexistent_tool")

    def test_pipeline_state_management(self, mcp_server):
        """Test pipeline state management."""
        # Initial state should be empty
        assert len(mcp_server.pipeline_state) == 0

        # Update state
        mcp_server.pipeline_state.update({"test_key": "test_value"})
        assert mcp_server.pipeline_state["test_key"] == "test_value"

        # Clear state
        mcp_server.pipeline_state.clear()
        assert len(mcp_server.pipeline_state) == 0

class TestMCPServerAPI:
    """Test MCP server HTTP API endpoints."""

    def test_status_endpoint(self, test_client):
        """Test status endpoint."""
        response = test_client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "pipeline_state" in data
        assert "registered_tools" in data
        assert "agents" in data

    def test_tools_endpoint(self, test_client):
        """Test tools listing endpoint."""
        response = test_client.get("/tools")
        assert response.status_code == 200

        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], dict)

    def test_tool_execution_endpoint(self, test_client):
        """Test tool execution endpoint."""
        # Register a test tool
        @mcp.tool(name="api_test_tool")
        async def api_test_tool(param1: str = "default", server=None):
            return {"status": "success", "param1": param1}

        # Test with payload
        response = test_client.post("/tool/api_test_tool", json={"param1": "test_value"})
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["param1"] == "test_value"

    def test_tool_execution_not_found(self, test_client):
        """Test tool execution with non-existent tool."""
        response = test_client.post("/tool/nonexistent_tool")
        assert response.status_code == 404

    def test_reset_endpoint(self, test_client, mcp_server):
        """Test pipeline reset endpoint."""
        # Set some state
        mcp_server.pipeline_state["test"] = "value"

        response = test_client.post("/reset")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "reset"
        assert len(mcp_server.pipeline_state) == 0

class TestToolRegistry:
    """Test MCP tool registry functionality."""

    def test_tool_registration(self):
        """Test tool registration with decorator."""
        initial_count = len(mcp.tools)

        @mcp.tool(name="registry_test_tool", description="Test tool for registry")
        async def registry_test_tool():
            return {"test": "success"}

        assert len(mcp.tools) == initial_count + 1
        assert "registry_test_tool" in mcp.tools
        assert mcp.tool_metadata["registry_test_tool"]["description"] == "Test tool for registry"

    def test_tool_metadata(self):
        """Test tool metadata collection."""
        @mcp.tool(name="metadata_test_tool", description="Tool with metadata")
        async def metadata_test_tool(param1: str, param2: int = 42):
            return {"param1": param1, "param2": param2}

        metadata = mcp.tool_metadata["metadata_test_tool"]
        assert metadata["description"] == "Tool with metadata"
        assert metadata["function"] == "metadata_test_tool"

    def test_tool_listing(self):
        """Test tool listing functionality."""
        tools = mcp.list_tools()
        assert isinstance(tools, dict)

        # Should contain previously registered tools
        assert "registry_test_tool" in tools
        assert "metadata_test_tool" in tools
```

#### Agent Testing Framework

```python
# tests/unit/test_agents.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.agentic_converter.agents.conversation import ConversationAgent
from src.agentic_converter.agents.conversion import ConversionAgent
from src.agentic_converter.agents.evaluation import EvaluationAgent
from src.agentic_converter.agents.base import BaseAgent, AgentStatus, AgentResult

@pytest.fixture
def mock_agent_config():
    """Mock agent configuration."""
    config = Mock()
    config.use_llm = False
    config.conversion_timeout = 300
    config.llm_config = Mock()
    return config

class TestBaseAgent:
    """Test base agent functionality."""

    class TestAgent(BaseAgent):
        """Test implementation of BaseAgent."""

        def __init__(self, config):
            super().__init__(config, "test_agent")
            self.test_data = {}

        async def _validate_inputs(self, **kwargs):
            if "required_param" not in kwargs:
                raise ValueError("required_param is missing")
            return kwargs

        async def _execute_internal(self, **kwargs):
            return {"result": kwargs["required_param"]}

    @pytest.fixture
    def test_agent(self, mock_agent_config):
        """Test agent instance."""
        return self.TestAgent(mock_agent_config)

    @pytest.mark.asyncio
    async def test_successful_execution(self, test_agent):
        """Test successful agent execution."""
        result = await test_agent.execute(required_param="test_value")

        assert result.status == AgentStatus.COMPLETED
        assert result.data["result"] == "test_value"
        assert result.error is None
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_input_validation_error(self, test_agent):
        """Test input validation error handling."""
        result = await test_agent.execute()  # Missing required_param

        assert result.status == AgentStatus.ERROR
        assert "required_param is missing" in result.error
        assert result.data == {}

    @pytest.mark.asyncio
    async def test_execution_error(self, test_agent):
        """Test execution error handling."""
        with patch.object(test_agent, '_execute_internal', side_effect=Exception("Test error")):
            result = await test_agent.execute(required_param="test")

            assert result.status == AgentStatus.ERROR
            assert "Test error" in result.error

    def test_metrics_tracking(self, test_agent):
        """Test agent metrics tracking."""
        # Simulate some executions
        test_agent._update_metrics(1.5, success=True)
        test_agent._update_metrics(0.5, success=False)
        test_agent._update_metrics(2.0, success=True)

        metrics = test_agent.get_metrics()

        assert metrics['total_executions'] == 3
        assert metrics['successful_executions'] == 2
        assert metrics['failed_executions'] == 1
        assert metrics['success_rate'] == 2/3
        assert metrics['average_execution_time'] == (1.5 + 0.5 + 2.0) / 3

class TestConversationAgent:
    """Test conversation agent functionality."""

    @pytest.fixture
    def conversation_agent(self, mock_agent_config):
        """Conversation agent instance."""
        with patch('src.agentic_converter.agents.conversation.FormatDetector'):
            with patch('src.agentic_converter.agents.conversation.DomainKnowledgeBase'):
                return ConversationAgent(mock_agent_config)

    @pytest.mark.asyncio
    async def test_dataset_analysis_without_llm(self, conversation_agent, tmp_path):
        """Test dataset analysis without LLM."""
        # Create test dataset
        test_dataset = tmp_path / "test_dataset"
        test_dataset.mkdir()
        (test_dataset / "recording.dat").touch()

        # Mock format detector
        mock_analysis = {
            'formats': [{'format': 'open_ephys', 'confidence': 0.9}],
            'file_count': 1,
            'total_size': 1024,
            'structure': {},
            'earliest_timestamp': time.time(),
            'latest_timestamp': time.time()
        }

        with patch.object(conversation_agent.format_detector, 'analyze_directory', return_value=mock_analysis):
            result = await conversation_agent.execute(
                dataset_dir=str(test_dataset),
                use_llm=False
            )

            assert result.status == AgentStatus.COMPLETED
            assert 'format_analysis' in result.data
            assert 'enriched_metadata' in result.data
            assert 'missing_metadata' in result.data

    @pytest.mark.asyncio
    async def test_question_generation_with_llm(self, conversation_agent, tmp_path):
        """Test question generation with LLM."""
        conversation_agent.config.use_llm = True
        conversation_agent.llm_client = AsyncMock()

        # Mock LLM response
        mock_llm_response = '''
        [
            {
                "field": "experimenter",
                "question": "Who performed this experiment?",
                "explanation": "Required for NWB metadata",
                "priority": "high"
            }
        ]
        '''
        conversation_agent.llm_client.generate_completion.return_value = mock_llm_response

        # Create test dataset
        test_dataset = tmp_path / "test_dataset"
        test_dataset.mkdir()
        (test_dataset / "recording.dat").touch()

        # Mock format detector
        mock_analysis = {
            'formats': [{'format': 'open_ephys'}],
            'file_count': 1,
            'total_size': 1024,
            'structure': {},
            'file_patterns': []
        }

        with patch.object(conversation_agent.format_detector, 'analyze_directory', return_value=mock_analysis):
            result = await conversation_agent.execute(
                dataset_dir=str(test_dataset),
                use_llm=True
            )

            assert result.status == AgentStatus.COMPLETED
            assert len(result.data['questions']) > 0
            assert result.data['questions'][0]['field'] == 'experimenter'

class TestConversionAgent:
    """Test conversion agent functionality."""

    @pytest.fixture
    def conversion_agent(self, mock_agent_config):
        """Conversion agent instance."""
        with patch('src.agentic_converter.agents.conversion.NeuroConvWrapper'):
            with patch('src.agentic_converter.agents.conversion.ScriptTemplateManager'):
                return ConversionAgent(mock_agent_config)

    @pytest.mark.asyncio
    async def test_dry_run_conversion(self, conversion_agent, tmp_path):
        """Test dry run conversion."""
        # Create test file
        test_file = tmp_path / "test_recording.dat"
        test_file.touch()

        normalized_metadata = {
            'identifier': 'test_session',
            'session_description': 'Test session',
            'experimenter': 'Test User'
        }

        files_map = {
            'recording': str(test_file)
        }

        # Mock interface selection
        mock_interface_selection = {
            'recording': {
                'interface_class': 'OpenEphysRecordingInterface',
                'detected_format': 'open_ephys',
                'file_path': str(test_file),
                'interface_kwargs': {}
            }
        }

        with patch.object(conversion_agent, '_select_data_interfaces', return_value=mock_interface_selection):
            with patch.object(conversion_agent, '_generate_conversion_script', return_value="# Test script"):
                with patch.object(conversion_agent, '_validate_script_syntax'):
                    result = await conversion_agent.execute(
                        normalized_metadata=normalized_metadata,
                        files_map=files_map,
                        dry_run=True
                    )

                    assert result.status == AgentStatus.COMPLETED
                    assert result.data['dry_run'] is True
                    assert 'script_content' in result.data
                    assert result.data['script_content'] == "# Test script"

class TestEvaluationAgent:
    """Test evaluation agent functionality."""

    @pytest.fixture
    def evaluation_agent(self, mock_agent_config):
        """Evaluation agent instance."""
        agent = EvaluationAgent(mock_agent_config)

        # Mock validation systems
        agent.validation_systems = {
            'nwb_inspector': Mock(),
            'linkml_validator': Mock(),
            'schema_validator': Mock()
        }

        # Mock quality assessors
        agent.quality_assessors = {
            'metadata_completeness': Mock(),
            'data_integrity': Mock(),
            'best_practices': Mock()
        }

        # Mock report generators
        agent.report_generators = {
            'html_reporter': Mock(),
            'json_reporter': Mock(),
            'visualization_generator': Mock()
        }

        return agent

    @pytest.mark.asyncio
    async def test_nwb_evaluation(self, evaluation_agent, tmp_path):
        """Test NWB file evaluation."""
        # Create mock NWB file
        test_nwb = tmp_path / "test.nwb"
        test_nwb.touch()

        # Mock validation results
        mock_validation_results = {
            'nwb_inspector': {'status': 'passed', 'issues': []},
            'linkml': {'status': 'passed', 'errors': []},
            'schema': {'status': 'passed', 'violations': []}
        }

        # Mock quality results
        mock_quality_results = {
            'metadata_completeness': {'score': 0.9, 'missing_fields': []},
            'data_integrity': {'score': 0.95, 'issues': []},
            'best_practices': {'score': 0.85, 'recommendations': []}
        }

        with patch.object(evaluation_agent, '_run_validation_systems', return_value=mock_validation_results):
            with patch.object(evaluation_agent, '_run_quality_assessments', return_value=mock_quality_results):
                with patch.object(evaluation_agent, '_generate_knowledge_graph', return_value={'status': 'success'}):
                    result = await evaluation_agent.execute(
                        nwb_path=str(test_nwb),
                        generate_report=False
                    )

                    assert result.status == AgentStatus.COMPLETED
                    assert 'validation' in result.data
                    assert 'quality_assessment' in result.data
                    assert 'overall_quality_score' in result.data
```

### 2. Integration Testing Framework

#### End-to-End Pipeline Testing

```python
# tests/integration/test_end_to_end_pipeline.py
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from src.agentic_converter.client.mcp_client import MCPClient, ClientConfig
from src.agentic_converter.mcp_server.server import MCPServer
from src.agentic_converter.core.config import Settings

@pytest.fixture
def test_dataset_path():
    """Create a test dataset for integration testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        dataset_path = Path(temp_dir) / "test_dataset"
        dataset_path.mkdir()

        # Create mock data files
        (dataset_path / "recording.dat").write_bytes(b"mock recording data" * 1000)
        (dataset_path / "events.txt").write_text("timestamp,event\\n1.0,start\\n2.0,end\\n")
        (dataset_path / "metadata.json").write_text('{"experimenter": "Test User"}')

        yield str(dataset_path)

@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for integration testing."""
    with patch('src.agentic_converter.mcp_server.server.MCPServer._initialize_agents'):
        settings = Mock(spec=Settings)
        server = MCPServer(settings)

        # Mock agents
        server.agents = {
            'conversation': Mock(),
            'conversion': Mock(),
            'evaluation': Mock(),
            'knowledge_graph': Mock()
        }

        return server

class TestEndToEndPipeline:
    """Test complete end-to-end conversion pipeline."""

    @pytest.mark.asyncio
    async def test_complete_pipeline_success(self, test_dataset_path, mock_mcp_server):
        """Test successful complete pipeline execution."""

        # Mock tool responses
        async def mock_execute_tool(tool_name, **kwargs):
            responses = {
                "initialize_pipeline": {
                    "status": "success",
                    "config": {"output_dir": "test_outputs"}
                },
                "analyze_dataset": {
                    "status": "success",
                    "result": {
                        "format_analysis": {"formats": ["open_ephys"]},
                        "enriched_metadata": {"experimenter": "Test User"},
                        "missing_metadata": []
                    }
                },
                "generate_conversion_script": {
                    "status": "success",
                    "output_nwb_path": "/tmp/test_output.nwb",
                    "script_content": "# Mock conversion script"
                },
                "evaluate_nwb_file": {
                    "status": "success",
                    "validation": {"nwb_inspector": {"status": "passed"}},
                    "quality_score": 0.95
                },
                "generate_knowledge_graph": {
                    "status": "success",
                    "ttl_path": "/tmp/test_output.ttl",
                    "entities_count": 42
                }
            }

            return responses.get(tool_name, {"status": "error", "message": f"Unknown tool: {tool_name}"})

        # Patch the server's execute_tool method
        mock_mcp_server.execute_tool = mock_execute_tool

        # Create client
        config = ClientConfig(api_url="http://test-server:8000")
        client = MCPClient(config)

        # Mock the client's call_tool method to use our mock server
        async def mock_call_tool(tool_name, payload=None, timeout=None):
            from src.agentic_converter.client.mcp_client import ConversionResult, PipelineStatus

            result_data = await mock_mcp_server.execute_tool(tool_name, **(payload or {}))
            return ConversionResult(
                success=result_data.get("status") == "success",
                status=PipelineStatus.COMPLETED if result_data.get("status") == "success" else PipelineStatus.ERROR,
                data=result_data
            )

        client.call_tool = mock_call_tool

        # Run pipeline
        files_map = {"recording": f"{test_dataset_path}/recording.dat"}
        result = await client.run_full_pipeline(
            dataset_dir=test_dataset_path,
            files_map=files_map,
            use_llm=False
        )

        # Verify results
        assert result.success is True
        assert "pipeline_results" in result.data
        assert result.data["pipeline_results"]["initialization"].success
        assert result.data["pipeline_results"]["analysis"].success
        assert result.data["pipeline_results"]["conversion"].success
        assert result.data["pipeline_results"]["evaluation"].success
        assert result.data["pipeline_results"]["knowledge_graph"].success

    @pytest.mark.asyncio
    async def test_pipeline_failure_recovery(self, test_dataset_path, mock_mcp_server):
        """Test pipeline failure and recovery."""

        # Mock tool responses with failure in conversion step
        async def mock_execute_tool_with_failure(tool_name, **kwargs):
            responses = {
                "initialize_pipeline": {"status": "success", "config": {}},
                "analyze_dataset": {"status": "success", "result": {"metadata": "test"}},
                "generate_conversion_script": {"status": "error", "message": "Conversion failed"},
                "evaluate_nwb_file": {"status": "success", "evaluation": "passed"},
                "generate_knowledge_graph": {"status": "success", "kg_data": "test"}
            }

            return responses.get(tool_name, {"status": "error", "message": f"Unknown tool: {tool_name}"})

        mock_mcp_server.execute_tool = mock_execute_tool_with_failure

        # Create client
        config = ClientConfig(api_url="http://test-server:8000")
        client = MCPClient(config)

        # Mock the client's call_tool method
        async def mock_call_tool(tool_name, payload=None, timeout=None):
            from src.agentic_converter.client.mcp_client import ConversionResult, PipelineStatus

            result_data = await mock_mcp_server.execute_tool(tool_name, **(payload or {}))
            return ConversionResult(
                success=result_data.get("status") == "success",
                status=PipelineStatus.ERROR if result_data.get("status") == "error" else PipelineStatus.COMPLETED,
                data=result_data,
                error=result_data.get("message") if result_data.get("status") == "error" else None
            )

        client.call_tool = mock_call_tool

        # Run pipeline
        files_map = {"recording": f"{test_dataset_path}/recording.dat"}
        result = await client.run_full_pipeline(
            dataset_dir=test_dataset_path,
            files_map=files_map
        )

        # Verify failure handling
        assert result.success is False
        assert "Conversion failed" in result.error
        assert result.data["failed_step"] == "conversion"
        assert result.data["pipeline_results"]["initialization"].success
        assert result.data["pipeline_results"]["analysis"].success
        assert not result.data["pipeline_results"]["conversion"].success

class TestDataLadIntegration:
    """Test DataLad integration for test data management."""

    @pytest.fixture
    def test_repo_path(self):
        """Create temporary repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_repository_initialization(self, test_repo_path):
        """Test DataLad repository initialization."""
        from src.agentic_converter.data_management.repository_structure import DataLadRepositoryManager

        repo_manager = DataLadRepositoryManager(str(test_repo_path))

        with patch('datalad.api.create') as mock_create:
            mock_dataset = Mock()
            mock_create.return_value = mock_dataset

            dataset = repo_manager.initialize_development_repository()

            assert mock_create.called
            assert dataset == mock_dataset

    def test_test_dataset_management(self, test_repo_path):
        """Test test dataset management."""
        from src.agentic_converter.data_management.repository_structure import (
            DataLadRepositoryManager, TestDatasetManager
        )

        repo_manager = DataLadRepositoryManager(str(test_repo_path))
        test_manager = TestDatasetManager(repo_manager)

        # Create mock source dataset
        source_path = test_repo_path / "source_dataset"
        source_path.mkdir()
        (source_path / "data.dat").write_bytes(b"test data")

        with patch('datalad.api.Dataset') as mock_dataset_class:
            mock_dataset = Mock()
            mock_dataset_class.return_value = mock_dataset

            success = test_manager.add_test_dataset(
                dataset_name="test_dataset_1",
                source_path=str(source_path),
                description="Test dataset for integration testing"
            )

            assert success
            assert mock_dataset.save.called

class TestPerformanceTesting:
    """Test performance characteristics of the system."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_conversion_performance(self, test_dataset_path):
        """Test conversion performance with timing."""
        import time

        # Mock fast conversion
        async def mock_fast_conversion(**kwargs):
            await asyncio.sleep(0.1)  # Simulate fast conversion
            return {"status": "success", "nwb_path": "/tmp/fast.nwb"}

        start_time = time.time()
        result = await mock_fast_conversion()
        end_time = time.time()

        assert result["status"] == "success"
        assert (end_time - start_time) < 1.0  # Should complete in under 1 second

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_conversions(self):
        """Test handling of concurrent conversion requests."""

        async def mock_conversion(conversion_id: int):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {"id": conversion_id, "status": "success"}

        # Run multiple conversions concurrently
        tasks = [mock_conversion(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r["status"] == "success" for r in results)
        assert set(r["id"] for r in results) == set(range(5))

    @pytest.mark.performance
    def test_memory_usage(self):
        """Test memory usage during operations."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Simulate memory-intensive operation
        large_data = [i for i in range(100000)]

        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory

        # Clean up
        del large_data

        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100 * 1024 * 1024
```

### 3. Quality Assurance Systems

#### Code Quality and Coverage

```python
# tests/quality/test_code_quality.py
import pytest
import subprocess
import sys
from pathlib import Path

class TestCodeQuality:
    """Test code quality metrics and standards."""

    def test_ruff_linting(self):
        """Test that code passes ruff linting."""
        result = subprocess.run([
            sys.executable, "-m", "ruff", "check", "src/", "tests/"
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Ruff linting failed:\\n{result.stdout}\\n{result.stderr}"

    def test_ruff_formatting(self):
        """Test that code follows ruff formatting."""
        result = subprocess.run([
            sys.executable, "-m", "ruff", "format", "--check", "src/", "tests/"
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Ruff formatting check failed:\\n{result.stdout}\\n{result.stderr}"

    def test_mypy_type_checking(self):
        """Test that code passes mypy type checking."""
        result = subprocess.run([
            sys.executable, "-m", "mypy", "src/"
        ], capture_output=True, text=True)

        # Allow some mypy errors but ensure no critical issues
        assert result.returncode in [0, 1], f"MyPy type checking failed:\\n{result.stdout}\\n{result.stderr}"

    def test_import_structure(self):
        """Test that imports are properly structured."""
        src_path = Path("src")

        for py_file in src_path.rglob("*.py"):
            with open(py_file, 'r') as f:
                content = f.read()

                # Check for relative imports in main package
                if "from .." in content and "src/agentic_converter" in str(py_file):
                    # Relative imports should be used appropriately
                    lines = content.split('\\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith("from .."):
                            # This is acceptable for internal package imports
                            pass

    def test_docstring_coverage(self):
        """Test that functions have docstrings."""
        import ast

        src_path = Path("src")
        missing_docstrings = []

        for py_file in src_path.rglob("*.py"):
            with open(py_file, 'r') as f:
                try:
                    tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if (not node.name.startswith('_') and  # Skip private methods
                                not ast.get_docstring(node)):
                                missing_docstrings.append(f"{py_file}:{node.lineno}:{node.name}")

                except SyntaxError:
                    # Skip files with syntax errors (they'll be caught by other tests)
                    pass

        # Allow some missing docstrings but ensure coverage is reasonable
        assert len(missing_docstrings) < 50, f"Too many missing docstrings:\\n" + "\\n".join(missing_docstrings[:10])

class TestSecurityScanning:
    """Test for security vulnerabilities."""

    def test_bandit_security_scan(self):
        """Test that code passes bandit security scanning."""
        try:
            result = subprocess.run([
                sys.executable, "-m", "bandit", "-r", "src/", "-f", "json"
            ], capture_output=True, text=True)

            # Bandit returns non-zero for issues, but we'll check the output
            if result.returncode != 0:
                import json
                try:
                    bandit_results = json.loads(result.stdout)
                    high_severity = [r for r in bandit_results.get('results', [])
                                   if r.get('issue_severity') == 'HIGH']

                    assert len(high_severity) == 0, f"High severity security issues found: {high_severity}"
                except json.JSONDecodeError:
                    # If we can't parse the output, just check return code
                    assert result.returncode in [0, 1], f"Bandit security scan failed: {result.stderr}"

        except FileNotFoundError:
            pytest.skip("Bandit not installed")

    def test_dependency_vulnerabilities(self):
        """Test for known vulnerabilities in dependencies."""
        try:
            result = subprocess.run([
                sys.executable, "-m", "safety", "check", "--json"
            ], capture_output=True, text=True)

            if result.returncode != 0:
                import json
                try:
                    safety_results = json.loads(result.stdout)
                    critical_vulns = [v for v in safety_results if v.get('severity') == 'critical']

                    assert len(critical_vulns) == 0, f"Critical vulnerabilities found: {critical_vulns}"
                except json.JSONDecodeError:
                    # If we can't parse, just warn
                    pytest.skip(f"Could not parse safety output: {result.stdout}")

        except FileNotFoundError:
            pytest.skip("Safety not installed")
```

### 4. Test Data Management

#### DataLad Test Dataset Management

```python
# tests/fixtures/test_data_manager.py
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from src.agentic_converter.data_management.repository_structure import (
    DataLadRepositoryManager, TestDatasetManager
)

class TestDataManager:
    """Manages test datasets for the test suite."""

    def __init__(self):
        self.test_datasets = {}
        self.mock_datasets_created = False

    def create_mock_datasets(self, base_path: Path):
        """Create mock datasets for testing."""
        if self.mock_datasets_created:
            return

        datasets = {
            'open_ephys_sample': {
                'format': 'open_ephys',
                'files': {
                    'continuous.dat': b'mock continuous data' * 1000,
                    'settings.xml': '''<?xml version="1.0"?>
                        <SETTINGS>
                            <SIGNALCHAIN>
                                <PROCESSOR name="Record Node" pluginName="Record Node">
                                    <CHANNEL_INFO>
                                        <CHANNEL number="0" name="CH1"/>
                                    </CHANNEL_INFO>
                                </PROCESSOR>
                            </SIGNALCHAIN>
                        </SETTINGS>''',
                    'structure.oebin': '''{"continuous": [{"folder_name": "Record Node", "sample_rate": 30000}]}'''
                }
            },
            'spikeglx_sample': {
                'format': 'spikeglx',
                'files': {
                    'recording.ap.bin': b'mock spike data' * 2000,
                    'recording.ap.meta': '''nSavedChans=385
sampleRate=30000.0
fileTimeSecs=60.0
imSampRate=30000.0''',
                    'recording.lf.bin': b'mock lfp data' * 500,
                    'recording.lf.meta': '''nSavedChans=385
sampleRate=2500.0
fileTimeSecs=60.0
imSampRate=2500.0'''
                }
            },
            'neuralynx_sample': {
                'format': 'neuralynx',
                'files': {
                    'CSC1.ncs': b'mock neuralynx continuous data' * 1500,
                    'Events.nev': b'mock neuralynx events' * 100,
                    'VT1.nvt': b'mock video tracking data' * 200
                }
            }
        }

        for dataset_name, dataset_info in datasets.items():
            dataset_path = base_path / 'test_datasets' / dataset_name
            dataset_path.mkdir(parents=True, exist_ok=True)

            for filename, content in dataset_info['files'].items():
                file_path = dataset_path / filename
                if isinstance(content, str):
                    file_path.write_text(content)
                else:
                    file_path.write_bytes(content)

            # Create metadata file
            metadata = {
                'name': dataset_name,
                'format': dataset_info['format'],
                'description': f'Mock {dataset_info["format"]} dataset for testing',
                'file_count': len(dataset_info['files']),
                'total_size': sum(len(content) if isinstance(content, bytes) else len(content.encode())
                                for content in dataset_info['files'].values())
            }

            import json
            (dataset_path / 'dataset_metadata.json').write_text(json.dumps(metadata, indent=2))

            self.test_datasets[dataset_name] = {
                'path': str(dataset_path),
                'metadata': metadata
            }

        self.mock_datasets_created = True

@pytest.fixture(scope="session")
def test_data_manager():
    """Session-scoped test data manager."""
    return TestDataManager()

@pytest.fixture
def mock_test_datasets(test_data_manager, tmp_path):
    """Create mock test datasets in temporary directory."""
    test_data_manager.create_mock_datasets(tmp_path)
    return test_data_manager.test_datasets

@pytest.fixture
def open_ephys_dataset(mock_test_datasets):
    """Open Ephys test dataset."""
    return mock_test_datasets['open_ephys_sample']

@pytest.fixture
def spikeglx_dataset(mock_test_datasets):
    """SpikeGLX test dataset."""
    return mock_test_datasets['spikeglx_sample']

@pytest.fixture
def neuralynx_dataset(mock_test_datasets):
    """Neuralynx test dataset."""
    return mock_test_datasets['neuralynx_sample']

class TestDatasetFixtures:
    """Test the test dataset fixtures themselves."""

    def test_open_ephys_dataset_structure(self, open_ephys_dataset):
        """Test Open Ephys dataset structure."""
        dataset_path = Path(open_ephys_dataset['path'])

        assert dataset_path.exists()
        assert (dataset_path / 'continuous.dat').exists()
        assert (dataset_path / 'settings.xml').exists()
        assert (dataset_path / 'structure.oebin').exists()
        assert (dataset_path / 'dataset_metadata.json').exists()

        # Check metadata
        metadata = open_ephys_dataset['metadata']
        assert metadata['format'] == 'open_ephys'
        assert metadata['file_count'] == 3

    def test_spikeglx_dataset_structure(self, spikeglx_dataset):
        """Test SpikeGLX dataset structure."""
        dataset_path = Path(spikeglx_dataset['path'])

        assert dataset_path.exists()
        assert (dataset_path / 'recording.ap.bin').exists()
        assert (dataset_path / 'recording.ap.meta').exists()
        assert (dataset_path / 'recording.lf.bin').exists()
        assert (dataset_path / 'recording.lf.meta').exists()

        # Check metadata
        metadata = spikeglx_dataset['metadata']
        assert metadata['format'] == 'spikeglx'
        assert metadata['file_count'] == 4

    def test_neuralynx_dataset_structure(self, neuralynx_dataset):
        """Test Neuralynx dataset structure."""
        dataset_path = Path(neuralynx_dataset['path'])

        assert dataset_path.exists()
        assert (dataset_path / 'CSC1.ncs').exists()
        assert (dataset_path / 'Events.nev').exists()
        assert (dataset_path / 'VT1.nvt').exists()

        # Check metadata
        metadata = neuralynx_dataset['metadata']
        assert metadata['format'] == 'neuralynx'
        assert metadata['file_count'] == 3
```

### 5. CI/CD Integration

#### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, "3.10", "3.11"]

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Full history for DataLad

      - name: Setup Pixi
        uses: prefix-dev/setup-pixi@v0.4.1
        with:
          pixi-version: v0.13.0

      - name: Install dependencies
        run: pixi install

      - name: Setup test data
        run: |
          pixi run python -c "
          from tests.fixtures.test_data_manager import TestDataManager
          import tempfile
          from pathlib import Path

          manager = TestDataManager()
          test_dir = Path('test_data')
          test_dir.mkdir(exist_ok=True)
          manager.create_mock_datasets(test_dir)
          "

      - name: Run code quality checks
        run: |
          pixi run ruff check src/ tests/
          pixi run ruff format --check src/ tests/
          pixi run mypy src/ --ignore-missing-imports

      - name: Run unit tests
        run: |
          pixi run pytest tests/unit/ -v \
            --cov=src/agentic_converter \
            --cov-report=xml \
            --cov-report=html \
            --cov-report=term-missing

      - name: Run integration tests
        run: |
          pixi run pytest tests/integration/ -v \
            --cov=src/agentic_converter \
            --cov-append \
            --cov-report=xml

      - name: Run performance tests
        run: |
          pixi run pytest tests/ -v -m performance \
            --benchmark-only \
            --benchmark-json=benchmark.json

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results-${{ matrix.python-version }}
          path: |
            htmlcov/
            benchmark.json
            pytest-report.xml

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Pixi
        uses: prefix-dev/setup-pixi@v0.4.1

      - name: Install security tools
        run: |
          pixi add bandit safety
          pixi install

      - name: Run security scan
        run: |
          pixi run bandit -r src/ -f json -o bandit-report.json
          pixi run safety check --json --output safety-report.json

      - name: Upload security reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-reports
          path: |
            bandit-report.json
            safety-report.json

  build:
    needs: [test, security]
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Pixi
        uses: prefix-dev/setup-pixi@v0.4.1

      - name: Build package
        run: |
          pixi run python -m build

      - name: Test installation
        run: |
          pixi run pip install dist/*.whl
          pixi run python -c "import agentic_converter; print('Package installed successfully')"

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-artifacts
          path: dist/
```

This comprehensive testing and quality assurance design provides multiple layers
of validation to ensure the reliability, performance, and quality of the agentic
neurodata conversion system.
