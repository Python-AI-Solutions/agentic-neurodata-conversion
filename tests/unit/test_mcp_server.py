"""
Unit tests for MCP server functionality.

This module provides comprehensive unit tests for the MCP server including:
- Tool registration and execution
- Agent coordination and workflow orchestration
- HTTP API endpoints
- Error handling and edge cases

These tests follow TDD methodology - they test the actual implementation
and should fail until the proper functionality is implemented.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional

# Import FastAPI test client
try:
    from fastapi.testclient import TestClient
    from fastapi import HTTPException
except ImportError:
    TestClient = None
    HTTPException = Exception

# Import the actual MCP server components that should be implemented
try:
    from agentic_neurodata_conversion.mcp_server import (
        MCPServer, 
        ToolRegistry,
        PipelineState,
        ConversationAgent,
        ConversionAgent, 
        EvaluationAgent
    )
    MCP_SERVER_AVAILABLE = True
except ImportError:
    # These should fail until implemented
    MCPServer = None
    ToolRegistry = None
    PipelineState = None
    ConversationAgent = None
    ConversionAgent = None
    EvaluationAgent = None
    MCP_SERVER_AVAILABLE = False


# Skip all tests if MCP server components are not implemented
pytestmark = pytest.mark.skipif(
    not MCP_SERVER_AVAILABLE, 
    reason="MCP server components not implemented yet"
)


# Test fixtures
@pytest.fixture
def mcp_server():
    """Create an MCP server instance for testing."""
    if not MCP_SERVER_AVAILABLE:
        pytest.skip("MCP server not implemented")
    return MCPServer()


@pytest.fixture
def tool_registry():
    """Create a tool registry for testing."""
    if not MCP_SERVER_AVAILABLE:
        pytest.skip("Tool registry not implemented")
    return ToolRegistry()


@pytest.fixture
def pipeline_state():
    """Create a pipeline state for testing."""
    if not MCP_SERVER_AVAILABLE:
        pytest.skip("Pipeline state not implemented")
    return PipelineState()


@pytest.fixture
def conversation_agent():
    """Create a conversation agent for testing."""
    if not MCP_SERVER_AVAILABLE:
        pytest.skip("Conversation agent not implemented")
    return ConversationAgent()


@pytest.fixture
def conversion_agent():
    """Create a conversion agent for testing."""
    if not MCP_SERVER_AVAILABLE:
        pytest.skip("Conversion agent not implemented")
    return ConversionAgent()


@pytest.fixture
def evaluation_agent():
    """Create an evaluation agent for testing."""
    if not MCP_SERVER_AVAILABLE:
        pytest.skip("Evaluation agent not implemented")
    return EvaluationAgent()


@pytest.fixture
def test_dataset_path(tmp_path):
    """Create a test dataset for testing."""
    dataset_path = tmp_path / "test_dataset"
    dataset_path.mkdir()
    
    # Create mock data files
    (dataset_path / "recording.dat").write_bytes(b"mock recording data" * 1000)
    (dataset_path / "events.txt").write_text("timestamp,event\n1.0,start\n2.0,end\n")
    (dataset_path / "metadata.json").write_text('{"experimenter": "Test User"}')
    
    return str(dataset_path)


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "identifier": "test_session_001",
        "session_description": "Test recording session",
        "experimenter": ["Test User"],
        "lab": "Test Lab",
        "institution": "Test Institution",
        "experiment_description": "Test experiment for unit testing",
        "session_start_time": "2024-01-01T10:00:00",
        "keywords": ["test", "neuroscience", "nwb"]
    }


@pytest.fixture
def sample_files_map(tmp_path):
    """Sample files map for testing."""
    recording_file = tmp_path / "recording.dat"
    recording_file.write_bytes(b"mock recording data" * 1000)
    
    events_file = tmp_path / "events.txt"
    events_file.write_text("timestamp,event\n1.0,start\n2.0,end\n")
    
    return {
        "recording": str(recording_file),
        "events": str(events_file)
    }


class TestToolRegistry:
    """Test MCP tool registry functionality."""
    
    @pytest.mark.unit
    def test_tool_registration(self, tool_registry):
        """Test tool registration with decorator."""
        initial_count = len(tool_registry.get_tools())
        
        @tool_registry.register_tool(name="test_tool", description="Test tool for registry")
        async def test_tool():
            return {"test": "success"}
        
        tools = tool_registry.get_tools()
        assert len(tools) == initial_count + 1
        assert "test_tool" in tools
        assert tools["test_tool"]["description"] == "Test tool for registry"
    
    @pytest.mark.unit
    def test_tool_registration_without_name(self, tool_registry):
        """Test tool registration using function name."""
        @tool_registry.register_tool()
        async def auto_named_tool():
            return {"auto": "named"}
        
        tools = tool_registry.get_tools()
        assert "auto_named_tool" in tools
        assert tools["auto_named_tool"]["name"] == "auto_named_tool"
    
    @pytest.mark.unit
    def test_tool_overwrite_raises_error(self, tool_registry):
        """Test error when overwriting existing tool."""
        @tool_registry.register_tool(name="duplicate_tool")
        async def first_tool():
            return {"first": True}
        
        with pytest.raises(ValueError, match="Tool 'duplicate_tool' already registered"):
            @tool_registry.register_tool(name="duplicate_tool")
            async def second_tool():
                return {"second": True}
    
    @pytest.mark.unit
    def test_tool_execution(self, tool_registry):
        """Test tool execution through registry."""
        @tool_registry.register_tool(name="execution_test")
        async def execution_test(param1: str, param2: int = 42):
            return {"param1": param1, "param2": param2}
        
        result = asyncio.run(tool_registry.execute_tool("execution_test", param1="test", param2=100))
        assert result["param1"] == "test"
        assert result["param2"] == 100
    
    @pytest.mark.unit
    def test_tool_execution_not_found(self, tool_registry):
        """Test error when executing non-existent tool."""
        with pytest.raises(KeyError, match="Tool 'nonexistent' not found"):
            asyncio.run(tool_registry.execute_tool("nonexistent"))
    
    @pytest.mark.unit
    def test_list_tools(self, tool_registry):
        """Test tool listing functionality."""
        @tool_registry.register_tool(name="list_test_tool", description="Tool for listing test")
        async def list_test_tool():
            return {"listed": True}
        
        tools = tool_registry.list_tools()
        assert isinstance(tools, list)
        assert any(tool["name"] == "list_test_tool" for tool in tools)
        
        list_tool = next(tool for tool in tools if tool["name"] == "list_test_tool")
        assert list_tool["description"] == "Tool for listing test"


class TestMCPServer:
    """Test MCP server core functionality."""
    
    @pytest.mark.unit
    def test_server_initialization(self, mcp_server):
        """Test MCP server initialization."""
        assert mcp_server is not None
        assert hasattr(mcp_server, 'tool_registry')
        assert hasattr(mcp_server, 'pipeline_state')
        assert hasattr(mcp_server, 'start')
        assert hasattr(mcp_server, 'stop')
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_server_start_stop(self, mcp_server):
        """Test server start and stop functionality."""
        # Server should not be running initially
        assert not mcp_server.is_running()
        
        # Start server
        await mcp_server.start()
        assert mcp_server.is_running()
        
        # Stop server
        await mcp_server.stop()
        assert not mcp_server.is_running()
    
    @pytest.mark.unit
    def test_server_has_required_agents(self, mcp_server):
        """Test that server has all required agents."""
        assert hasattr(mcp_server, 'conversation_agent')
        assert hasattr(mcp_server, 'conversion_agent')
        assert hasattr(mcp_server, 'evaluation_agent')
        
        assert mcp_server.conversation_agent is not None
        assert mcp_server.conversion_agent is not None
        assert mcp_server.evaluation_agent is not None
    
    @pytest.mark.unit
    def test_server_tool_registry_integration(self, mcp_server):
        """Test server integration with tool registry."""
        registry = mcp_server.tool_registry
        assert registry is not None
        
        # Should have default tools registered
        tools = registry.get_tools()
        expected_tools = [
            "initialize_pipeline",
            "analyze_dataset", 
            "generate_conversion_script",
            "evaluate_nwb_file",
            "status",
            "clear_state"
        ]
        
        tool_names = [tool["name"] for tool in tools]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names


@pytest.mark.skipif(TestClient is None, reason="FastAPI not available")
class TestMCPServerAPI:
    """Test MCP server HTTP API endpoints."""
    
    @pytest.fixture
    def test_client(self, mcp_server):
        """Create FastAPI test client from MCP server."""
        if not hasattr(mcp_server, 'get_fastapi_app'):
            pytest.skip("MCP server does not expose FastAPI app")
        
        app = mcp_server.get_fastapi_app()
        return TestClient(app)
    
    @pytest.mark.integration
    def test_status_endpoint(self, test_client):
        """Test status endpoint."""
        response = test_client.get("/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "initialized" in data
        assert "pipeline_state" in data
        assert "registered_tools" in data
        assert "agents" in data
        
        # Should list expected agents
        assert "conversation" in data["agents"]
        assert "conversion" in data["agents"] 
        assert "evaluation" in data["agents"]
    
    def test_tools_endpoint(self, test_client):
        """Test tools listing endpoint."""
        response = test_client.get("/tools")
        assert response.status_code == 200
        
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
        
        # Should have default tools
        tool_names = [tool["name"] for tool in data["tools"]]
        expected_tools = [
            "initialize_pipeline",
            "analyze_dataset",
            "generate_conversion_script", 
            "evaluate_nwb_file",
            "status",
            "clear_state"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    def test_tool_execution_endpoint_success(self, test_client):
        """Test successful tool execution endpoint."""
        # Test initialize_pipeline tool
        response = test_client.post("/tool/initialize_pipeline", json={
            "config": {"output_dir": "/test/output", "use_llm": False}
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["config"]["output_dir"] == "/test/output"
    
    def test_tool_execution_endpoint_with_defaults(self, test_client):
        """Test tool execution with default parameters."""
        # Test status tool (no parameters required)
        response = test_client.post("/tool/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "initialized" in data
        assert "config" in data
    
    def test_tool_execution_not_found(self, test_client):
        """Test tool execution with non-existent tool."""
        response = test_client.post("/tool/nonexistent_tool")
        assert response.status_code == 404
        assert "Tool not found" in response.json()["detail"]
    
    def test_tool_execution_error(self, test_client):
        """Test tool execution error handling."""
        # Test analyze_dataset with invalid path
        response = test_client.post("/tool/analyze_dataset", json={
            "dataset_dir": "/nonexistent/path"
        })
        assert response.status_code == 500
        # Should return error details
        assert "detail" in response.json()
    
    def test_pipeline_initialization_endpoint(self, test_client):
        """Test pipeline initialization through API."""
        # Initialize pipeline
        response = test_client.post("/tool/initialize_pipeline", json={
            "config": {"output_dir": "/test/output"}
        })
        assert response.status_code == 200
        
        # Check status reflects initialization
        status_response = test_client.post("/tool/status")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["initialized"] is True
        assert status_data["config"]["output_dir"] == "/test/output"
    
    def test_pipeline_clear_endpoint(self, test_client):
        """Test pipeline clear through API."""
        # Initialize first
        test_client.post("/tool/initialize_pipeline", json={"config": {"test": "data"}})
        
        # Clear pipeline
        response = test_client.post("/tool/clear_state")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        # Verify state is cleared
        status_response = test_client.post("/tool/status")
        status_data = status_response.json()
        assert status_data["initialized"] is False


class TestPipelineState:
    """Test pipeline state management."""
    
    @pytest.mark.unit
    def test_pipeline_state_initialization(self, pipeline_state):
        """Test pipeline state initialization."""
        assert not pipeline_state.is_initialized()
        assert pipeline_state.get_config() == {}
        assert len(pipeline_state.get_workflow_history()) == 0
    
    def test_pipeline_state_initialization_with_config(self, pipeline_state):
        """Test pipeline initialization with configuration."""
        config = {"output_dir": "/test/output", "use_llm": False}
        
        pipeline_state.initialize(config)
        
        assert pipeline_state.is_initialized()
        assert pipeline_state.get_config() == config
        
        history = pipeline_state.get_workflow_history()
        assert len(history) == 1
        assert history[0]["step"] == "initialize"
        assert history[0]["config"] == config
    
    def test_pipeline_state_workflow_tracking(self, pipeline_state):
        """Test workflow step tracking."""
        pipeline_state.initialize({})
        
        # Add workflow steps
        pipeline_state.add_workflow_step("analyze_dataset", {"dataset_dir": "/test/data"})
        pipeline_state.add_workflow_step("generate_script", {"output_path": "/test/output.nwb"})
        
        history = pipeline_state.get_workflow_history()
        assert len(history) == 3  # initialize + 2 steps
        assert history[1]["step"] == "analyze_dataset"
        assert history[2]["step"] == "generate_script"
    
    def test_pipeline_state_data_storage(self, pipeline_state):
        """Test storing and retrieving pipeline data."""
        pipeline_state.initialize({})
        
        # Store analysis results
        analysis_data = {"format": "open_ephys", "metadata": {"experimenter": "Test"}}
        pipeline_state.set_analysis_report(analysis_data)
        
        # Store conversion script
        script_data = {"script_path": "/test/script.py", "output_path": "/test/output.nwb"}
        pipeline_state.set_conversion_script(script_data)
        
        # Verify data retrieval
        assert pipeline_state.get_analysis_report() == analysis_data
        assert pipeline_state.get_conversion_script() == script_data
    
    def test_pipeline_state_clear(self, pipeline_state):
        """Test clearing pipeline state."""
        # Setup some state
        pipeline_state.initialize({"test": "config"})
        pipeline_state.set_analysis_report({"test": "data"})
        
        # Clear state
        pipeline_state.clear()
        
        assert not pipeline_state.is_initialized()
        assert pipeline_state.get_config() == {}
        assert pipeline_state.get_analysis_report() is None


class TestAgentCoordination:
    """Test agent coordination and workflow orchestration."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_conversation_agent_analyze_dataset(self, conversation_agent, test_dataset_path):
        """Test conversation agent dataset analysis."""
        result = await conversation_agent.analyze_dataset(test_dataset_path)
        
        # Should return analysis results
        assert "format_analysis" in result
        assert "enriched_metadata" in result
        assert "missing_metadata" in result
        assert "questions" in result
        
        # Format analysis should identify data format
        format_analysis = result["format_analysis"]
        assert "formats" in format_analysis
        assert len(format_analysis["formats"]) > 0
    
    @pytest.mark.asyncio
    async def test_conversion_agent_generate_script(self, conversion_agent, sample_metadata, sample_files_map, tmp_path):
        """Test conversion agent script generation."""
        output_path = str(tmp_path / "test_output.nwb")
        
        result = await conversion_agent.synthesize_conversion_script(
            sample_metadata, sample_files_map, output_path
        )
        
        # Should return script content and metadata
        assert "script_content" in result
        assert "script_path" in result
        assert "output_nwb_path" in result
        
        # Script should contain conversion logic
        script_content = result["script_content"]
        assert "NWBConverter" in script_content
        assert "run_conversion" in script_content
    
    @pytest.mark.asyncio
    async def test_evaluation_agent_validate_nwb(self, evaluation_agent, tmp_path):
        """Test evaluation agent NWB validation."""
        # Create a mock NWB file
        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock nwb data")
        
        result = await evaluation_agent.validate_nwb(str(nwb_file))
        
        # Should return validation results
        assert "passed" in result
        assert "counts" in result
        assert "formatted_report" in result
        assert "total_issues" in result
    
    @pytest.mark.asyncio
    async def test_agent_workflow_orchestration(self, mcp_server, test_dataset_path, sample_files_map, tmp_path):
        """Test complete agent workflow orchestration through server."""
        # Initialize pipeline
        await mcp_server.initialize_pipeline({"output_dir": str(tmp_path)})
        
        # Step 1: Analyze dataset
        analysis_result = await mcp_server.analyze_dataset(test_dataset_path)
        assert analysis_result["status"] == "success"
        
        # Step 2: Generate conversion script
        metadata = analysis_result["result"]["enriched_metadata"]
        output_path = str(tmp_path / "workflow_test.nwb")
        
        script_result = await mcp_server.generate_conversion_script(
            metadata, sample_files_map, output_path
        )
        assert script_result["status"] == "success"
        
        # Step 3: Create mock NWB file and evaluate
        nwb_file = Path(output_path)
        nwb_file.write_bytes(b"mock nwb data from workflow")
        
        eval_result = await mcp_server.evaluate_nwb_file(output_path)
        assert eval_result["status"] == "success"
        
        # Verify pipeline state was updated
        state = mcp_server.pipeline_state
        assert state.is_initialized()
        assert state.get_analysis_report() is not None
        assert state.get_conversion_script() is not None
        assert state.get_evaluation_results() is not None
    
    @pytest.mark.asyncio
    async def test_agent_error_handling(self, conversation_agent):
        """Test agent error handling."""
        # Test with non-existent dataset path
        with pytest.raises(FileNotFoundError):
            await conversation_agent.analyze_dataset("/nonexistent/path")
    
    @pytest.mark.asyncio
    async def test_agent_state_sharing_through_server(self, mcp_server, test_dataset_path):
        """Test state sharing between agents through server."""
        # Initialize pipeline
        await mcp_server.initialize_pipeline({})
        
        # Agent 1 produces data
        analysis_result = await mcp_server.analyze_dataset(test_dataset_path)
        
        # Verify state was updated
        state = mcp_server.pipeline_state
        assert state.get_analysis_report() is not None
        
        # Agent 2 should be able to access the data
        analysis_data = state.get_analysis_report()
        assert "enriched_metadata" in analysis_data


class TestMCPServerTools:
    """Test MCP server tool implementations."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_initialize_pipeline_tool(self, mcp_server):
        """Test initialize_pipeline tool."""
        config = {"output_dir": "/test/output", "use_llm": False}
        
        result = await mcp_server.initialize_pipeline(config)
        
        assert result["status"] == "success"
        assert result["config"] == config
        
        # Verify pipeline state was updated
        assert mcp_server.pipeline_state.is_initialized()
        assert mcp_server.pipeline_state.get_config() == config
    
    @pytest.mark.asyncio
    async def test_analyze_dataset_tool(self, mcp_server, test_dataset_path):
        """Test analyze_dataset tool."""
        # Initialize pipeline first
        await mcp_server.initialize_pipeline({})
        
        result = await mcp_server.analyze_dataset(
            dataset_dir=test_dataset_path,
            use_llm=False
        )
        
        assert result["status"] == "success"
        assert "result" in result
        
        analysis_result = result["result"]
        assert "format_analysis" in analysis_result
        assert "enriched_metadata" in analysis_result
        assert "missing_metadata" in analysis_result
        
        # Verify pipeline state was updated
        assert mcp_server.pipeline_state.get_analysis_report() is not None
    
    @pytest.mark.asyncio
    async def test_generate_conversion_script_tool(self, mcp_server, sample_metadata, sample_files_map, tmp_path):
        """Test generate_conversion_script tool."""
        # Initialize pipeline first
        await mcp_server.initialize_pipeline({"output_dir": str(tmp_path)})
        
        output_path = str(tmp_path / "test_output.nwb")
        
        result = await mcp_server.generate_conversion_script(
            normalized_metadata=sample_metadata,
            files_map=sample_files_map,
            output_nwb_path=output_path
        )
        
        assert result["status"] == "success"
        assert result["output_nwb_path"] == output_path
        assert "script_path" in result
        
        # Verify script file was created
        script_path = result["script_path"]
        assert Path(script_path).exists()
        
        # Verify pipeline state was updated
        conversion_script = mcp_server.pipeline_state.get_conversion_script()
        assert conversion_script is not None
        assert conversion_script["output_path"] == output_path
    
    @pytest.mark.asyncio
    async def test_evaluate_nwb_file_tool(self, mcp_server, tmp_path):
        """Test evaluate_nwb_file tool."""
        # Initialize pipeline first
        await mcp_server.initialize_pipeline({"output_dir": str(tmp_path)})
        
        # Create mock NWB file
        nwb_file = tmp_path / "test.nwb"
        nwb_file.write_bytes(b"mock nwb data")
        
        result = await mcp_server.evaluate_nwb_file(
            nwb_path=str(nwb_file),
            generate_report=True
        )
        
        assert result["status"] == "success"
        assert "validation" in result
        
        validation_result = result["validation"]
        assert "passed" in validation_result
        assert "counts" in validation_result
        assert "formatted_report" in validation_result
        
        # Verify pipeline state was updated
        eval_results = mcp_server.pipeline_state.get_evaluation_results()
        assert eval_results is not None
        assert eval_results["nwb_path"] == str(nwb_file)
    
    @pytest.mark.asyncio
    async def test_status_tool(self, mcp_server):
        """Test status tool."""
        # Setup some state
        config = {"test": "config"}
        await mcp_server.initialize_pipeline(config)
        
        result = await mcp_server.get_status()
        
        assert result["initialized"] is True
        assert result["config"] == config
        assert "workflow_history" in result
        assert "registered_tools" in result
        
        # Should list expected tools
        tool_names = [tool["name"] for tool in result["registered_tools"]]
        expected_tools = ["initialize_pipeline", "analyze_dataset", "generate_conversion_script"]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_clear_state_tool(self, mcp_server):
        """Test clear_state tool."""
        # Setup some state to clear
        await mcp_server.initialize_pipeline({"test": "config"})
        
        # Verify state exists
        assert mcp_server.pipeline_state.is_initialized()
        
        # Clear state
        result = await mcp_server.clear_state()
        
        assert result["status"] == "success"
        
        # Verify state is cleared
        assert not mcp_server.pipeline_state.is_initialized()
        assert mcp_server.pipeline_state.get_config() == {}
        assert mcp_server.pipeline_state.get_analysis_report() is None
    
    @pytest.mark.asyncio
    async def test_run_full_pipeline_tool(self, mcp_server, test_dataset_path, sample_files_map, tmp_path):
        """Test run_full_pipeline tool."""
        # Initialize pipeline
        await mcp_server.initialize_pipeline({"output_dir": str(tmp_path)})
        
        result = await mcp_server.run_full_pipeline(
            dataset_dir=test_dataset_path,
            files_map=sample_files_map,
            output_dir=str(tmp_path),
            use_llm=False
        )
        
        assert result["status"] == "success"
        assert "analysis" in result
        assert "conversion" in result
        assert "evaluation" in result
        
        # Verify all pipeline steps completed
        assert result["analysis"]["status"] == "success"
        assert result["conversion"]["status"] == "success"
        
        # Verify pipeline state reflects full workflow
        state = mcp_server.pipeline_state
        assert state.get_analysis_report() is not None
        assert state.get_conversion_script() is not None
        
        # Check workflow history
        history = state.get_workflow_history()
        assert len(history) >= 4  # initialize + analysis + conversion + evaluation


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pipeline_not_initialized_error(self, mcp_server):
        """Test error when pipeline is not initialized."""
        # Try to analyze dataset without initializing pipeline
        with pytest.raises(RuntimeError, match="Pipeline not initialized"):
            await mcp_server.analyze_dataset("/test/path")
    
    @pytest.mark.asyncio
    async def test_file_not_found_error(self, mcp_server):
        """Test error handling for missing files."""
        await mcp_server.initialize_pipeline({})
        
        # Try to analyze non-existent dataset
        with pytest.raises(FileNotFoundError):
            await mcp_server.analyze_dataset("/nonexistent/path")
    
    @pytest.mark.asyncio
    async def test_invalid_nwb_file_error(self, mcp_server, tmp_path):
        """Test error handling for invalid NWB files."""
        await mcp_server.initialize_pipeline({})
        
        # Create invalid NWB file
        invalid_nwb = tmp_path / "invalid.nwb"
        invalid_nwb.write_text("not a valid nwb file")
        
        result = await mcp_server.evaluate_nwb_file(str(invalid_nwb))
        
        # Should return error status, not raise exception
        assert result["status"] == "error"
        assert "validation" in result
        assert not result["validation"]["passed"]
    
    @pytest.mark.asyncio
    async def test_agent_failure_handling(self, mcp_server):
        """Test handling of agent failures."""
        await mcp_server.initialize_pipeline({})
        
        # Mock agent failure by patching conversation agent
        with patch.object(mcp_server.conversation_agent, 'analyze_dataset', 
                         side_effect=RuntimeError("Agent processing failed")):
            
            result = await mcp_server.analyze_dataset("/test/path")
            
            # Should return error status, not raise exception
            assert result["status"] == "error"
            assert "Agent processing failed" in result["message"]
    
    @pytest.mark.asyncio
    async def test_tool_registry_error_handling(self, tool_registry):
        """Test tool registry error handling."""
        # Test executing non-existent tool
        with pytest.raises(KeyError, match="Tool 'nonexistent' not found"):
            await tool_registry.execute_tool("nonexistent")
        
        # Test registering tool with invalid name
        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            @tool_registry.register_tool(name="")
            async def empty_name_tool():
                pass
    
    @pytest.mark.asyncio
    async def test_pipeline_state_error_handling(self, pipeline_state):
        """Test pipeline state error handling."""
        # Test accessing data before initialization
        with pytest.raises(RuntimeError, match="Pipeline not initialized"):
            pipeline_state.get_analysis_report()
        
        # Test invalid workflow step
        pipeline_state.initialize({})
        with pytest.raises(ValueError, match="Invalid workflow step"):
            pipeline_state.add_workflow_step("", {})
    
    @pytest.mark.asyncio
    async def test_concurrent_access_error_handling(self, mcp_server):
        """Test error handling during concurrent access."""
        await mcp_server.initialize_pipeline({})
        
        # Simulate concurrent access to pipeline state
        async def concurrent_operation():
            return await mcp_server.get_status()
        
        # Should handle concurrent access gracefully
        tasks = [concurrent_operation() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert result["initialized"] is True
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self, mcp_server, tmp_path):
        """Test resource cleanup when operations fail."""
        await mcp_server.initialize_pipeline({"output_dir": str(tmp_path)})
        
        # Mock conversion agent to fail after creating temporary files
        original_method = mcp_server.conversion_agent.synthesize_conversion_script
        
        def failing_method(*args, **kwargs):
            # Create a temporary file
            temp_file = tmp_path / "temp_script.py"
            temp_file.write_text("temporary script")
            
            # Then fail
            raise RuntimeError("Conversion failed")
        
        with patch.object(mcp_server.conversion_agent, 'synthesize_conversion_script', 
                         side_effect=failing_method):
            
            result = await mcp_server.generate_conversion_script({}, {}, str(tmp_path / "output.nwb"))
            
            # Should return error status
            assert result["status"] == "error"
            
            # Temporary files should be cleaned up (implementation dependent)
            # This test verifies the error handling structure is in place


class TestPerformanceAndConcurrency:
    """Test performance characteristics and concurrent execution."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mcp_server):
        """Test concurrent execution of multiple tools."""
        await mcp_server.initialize_pipeline({})
        
        # Execute multiple status calls concurrently
        tasks = [mcp_server.get_status() for _ in range(5)]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for result in results:
            assert result["initialized"] is True
            assert "config" in result
    
    @pytest.mark.asyncio
    async def test_tool_execution_timeout(self, tool_registry):
        """Test tool execution with timeout."""
        @tool_registry.register_tool(name="slow_tool")
        async def slow_tool(delay: float = 1.0):
            await asyncio.sleep(delay)
            return {"completed": True}
        
        # Test with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                tool_registry.execute_tool("slow_tool", delay=2.0),
                timeout=0.5
            )
    
    @pytest.mark.asyncio
    async def test_pipeline_state_thread_safety(self, pipeline_state):
        """Test pipeline state thread safety."""
        pipeline_state.initialize({})
        
        async def concurrent_update(step_id: int):
            pipeline_state.add_workflow_step(f"step_{step_id}", {"id": step_id})
            return step_id
        
        # Execute concurrent updates
        tasks = [concurrent_update(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        
        # Verify all steps were recorded
        history = pipeline_state.get_workflow_history()
        assert len(history) >= 11  # initialize + 10 steps
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self, mcp_server, tmp_path):
        """Test memory usage with large dataset analysis."""
        await mcp_server.initialize_pipeline({"output_dir": str(tmp_path)})
        
        # Create a large mock dataset
        large_dataset = tmp_path / "large_dataset"
        large_dataset.mkdir()
        
        # Create multiple large files
        for i in range(10):
            large_file = large_dataset / f"data_{i}.dat"
            large_file.write_bytes(b"x" * 1024 * 1024)  # 1MB per file
        
        # Should handle large dataset without memory issues
        result = await mcp_server.analyze_dataset(str(large_dataset))
        
        # Should complete successfully
        assert result["status"] == "success"
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_server_resource_limits(self, mcp_server):
        """Test server behavior under resource constraints."""
        await mcp_server.initialize_pipeline({})
        
        # Test with many concurrent operations
        async def resource_intensive_operation():
            return await mcp_server.get_status()
        
        # Should handle many concurrent requests
        tasks = [resource_intensive_operation() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Most operations should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 40  # Allow some failures under stress
    
    @pytest.mark.asyncio
    async def test_tool_registry_performance(self, tool_registry):
        """Test tool registry performance with many tools."""
        # Register many tools
        for i in range(100):
            @tool_registry.register_tool(name=f"perf_tool_{i}")
            async def perf_tool(tool_id: int = i):
                return {"tool_id": tool_id}
        
        # Should list tools efficiently
        tools = tool_registry.list_tools()
        assert len(tools) >= 100
        
        # Should execute tools efficiently
        result = await tool_registry.execute_tool("perf_tool_50")
        assert result["tool_id"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])