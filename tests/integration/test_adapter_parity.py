"""Integration tests for adapter parity.

This module provides comprehensive integration tests to ensure that both MCP and HTTP
adapters provide identical functionality through different transport protocols.
"""

import asyncio
import json
from pathlib import Path
import tempfile
import uuid

import pytest

try:
    from agentic_neurodata_conversion.core.service import ConversionRequest
    from agentic_neurodata_conversion.core.tools import ToolStatus
    from agentic_neurodata_conversion.mcp_server.http_adapter import HTTPAdapter
    from agentic_neurodata_conversion.mcp_server.mcp_adapter import MCPAdapter

    COMPONENTS_AVAILABLE = True
except ImportError:
    ConversionRequest = None
    ToolStatus = None
    HTTPAdapter = None
    MCPAdapter = None
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE, reason="Adapter parity components not implemented yet"
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
async def mcp_adapter():
    """Create and initialize MCP adapter for testing."""
    if not COMPONENTS_AVAILABLE:
        pytest.skip("MCP adapter not available")

    adapter = MCPAdapter()
    await adapter.initialize()
    yield adapter
    await adapter.shutdown()


@pytest.fixture
async def http_adapter():
    """Create and initialize HTTP adapter for testing."""
    if not COMPONENTS_AVAILABLE:
        pytest.skip("HTTP adapter not available")

    adapter = HTTPAdapter()
    await adapter.initialize()
    yield adapter
    await adapter.shutdown()


@pytest.fixture
async def both_adapters():
    """Create and initialize both adapters for parity testing."""
    if not COMPONENTS_AVAILABLE:
        pytest.skip("Adapters not available")

    mcp_adapter = MCPAdapter()
    http_adapter = HTTPAdapter()

    await mcp_adapter.initialize()
    await http_adapter.initialize()

    yield mcp_adapter, http_adapter

    await mcp_adapter.shutdown()
    await http_adapter.shutdown()


@pytest.fixture
def integration_dataset():
    """Create a comprehensive dataset for integration testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a realistic neuroscience dataset structure
        (temp_path / "ephys_data.bin").write_bytes(
            b"\x00\x01\x02\x03" * 1000
        )  # Binary ephys data
        (temp_path / "behavior_data.csv").write_text(
            "timestamp,x_position,y_position,velocity,trial_id\n"
            "0.0,10.5,20.3,1.2,1\n"
            "0.033,10.6,20.4,1.3,1\n"
            "0.066,10.7,20.5,1.4,1\n"
        )
        (temp_path / "metadata.json").write_text(
            json.dumps(
                {
                    "subject_id": "mouse_001",
                    "session_id": "session_20240101_001",
                    "experiment_description": "Integration test experiment",
                    "experimenter": "Test User",
                    "institution": "Test Institution",
                    "session_start_time": "2024-01-01T10:00:00",
                    "data_format": "open_ephys",
                    "sampling_rate": 30000,
                    "num_channels": 64,
                },
                indent=2,
            )
        )
        (temp_path / "session_info.txt").write_text(
            "Session Information\n"
            "==================\n"
            "Date: 2024-01-01\n"
            "Duration: 3600 seconds\n"
            "Notes: Integration test session\n"
        )
        (temp_path / "config.yaml").write_text(
            "experiment:\n"
            "  name: integration_test\n"
            "  type: electrophysiology\n"
            "  duration: 3600\n"
            "recording:\n"
            "  sampling_rate: 30000\n"
            "  channels: 64\n"
        )

        yield str(temp_path)


@pytest.fixture
def sample_files_map(integration_dataset):
    """Create a realistic files map for testing."""
    dataset_path = Path(integration_dataset)
    return {
        "ephys": str(dataset_path / "ephys_data.bin"),
        "behavior": str(dataset_path / "behavior_data.csv"),
        "metadata": str(dataset_path / "metadata.json"),
    }


@pytest.fixture
def sample_metadata():
    """Create realistic normalized metadata for testing."""
    return {
        "subject_id": "mouse_001",
        "session_id": "session_20240101_001",
        "experiment_description": "Integration test experiment with comprehensive data",
        "experimenter": "Integration Test User",
        "institution": "Test Research Institution",
        "session_start_time": "2024-01-01T10:00:00",
        "data_format": "open_ephys",
        "sampling_rate": 30000,
        "num_channels": 64,
        "session_duration": 3600,
        "behavioral_paradigm": "open_field",
        "recording_location": "hippocampus",
    }


# ============================================================================
# Core Service Parity Tests
# ============================================================================


class TestCoreServiceParity:
    """Test that both adapters use the same core service functionality."""

    @pytest.mark.integration
    async def test_service_initialization_parity(self, both_adapters):
        """Test that both adapters initialize the same core service."""
        mcp_adapter, http_adapter = both_adapters

        # Both should have initialized conversion services
        assert mcp_adapter.conversion_service._initialized
        assert http_adapter.conversion_service._initialized

        # Both should have tool systems
        assert mcp_adapter.tool_system is not None
        assert http_adapter.tool_system is not None

        # Tool counts should match
        mcp_tools = len(mcp_adapter.tool_system.registry.list_tools())
        http_tools = len(http_adapter.tool_system.registry.list_tools())
        assert mcp_tools == http_tools == 4

    @pytest.mark.integration
    async def test_agent_status_parity(self, both_adapters):
        """Test that both adapters report identical agent status."""
        mcp_adapter, http_adapter = both_adapters

        mcp_agents = await mcp_adapter.conversion_service.get_agent_status()
        http_agents = await http_adapter.conversion_service.get_agent_status()

        # Same agent names
        assert set(mcp_agents.keys()) == set(http_agents.keys())

        # Same agent statuses
        for agent_name in mcp_agents:
            mcp_status = mcp_agents[agent_name].get("status")
            http_status = http_agents[agent_name].get("status")
            assert mcp_status == http_status, f"Agent {agent_name} status mismatch"

    @pytest.mark.integration
    async def test_dataset_analysis_parity(self, both_adapters, integration_dataset):
        """Test that dataset analysis produces identical results."""
        mcp_adapter, http_adapter = both_adapters

        session_id_base = f"parity_test_{uuid.uuid4().hex[:8]}"

        # Execute analysis through both adapters
        mcp_response = await mcp_adapter.conversion_service.dataset_analysis(
            dataset_dir=integration_dataset,
            use_llm=False,
            session_id=f"{session_id_base}_mcp",
        )

        http_response = await http_adapter.conversion_service.dataset_analysis(
            dataset_dir=integration_dataset,
            use_llm=False,
            session_id=f"{session_id_base}_http",
        )

        # Status should match
        assert mcp_response.status == http_response.status

        # Key analysis results should match
        mcp_data = mcp_response.data
        http_data = http_response.data

        # Compare core analysis fields (excluding session-specific data)
        core_fields = [
            "analysis_type",
            "metadata_extracted",
            "llm_used",
            "detected_formats",
            "file_count",
        ]
        for field in core_fields:
            assert mcp_data.get(field) == http_data.get(field), (
                f"Field {field} mismatch"
            )

        # Execution times should be similar (within 1 second)
        time_diff = abs(
            (mcp_response.execution_time or 0) - (http_response.execution_time or 0)
        )
        assert time_diff < 1.0, f"Execution time difference too large: {time_diff}s"

    @pytest.mark.integration
    async def test_conversion_orchestration_parity(
        self, both_adapters, sample_metadata, sample_files_map
    ):
        """Test that conversion orchestration produces identical results."""
        mcp_adapter, http_adapter = both_adapters

        session_id_base = f"conversion_parity_{uuid.uuid4().hex[:8]}"

        # Execute conversion through both adapters
        mcp_response = await mcp_adapter.conversion_service.conversion_orchestration(
            normalized_metadata=sample_metadata,
            files_map=sample_files_map,
            output_nwb_path=f"/tmp/mcp_output_{session_id_base}.nwb",
            session_id=f"{session_id_base}_mcp",
        )

        http_response = await http_adapter.conversion_service.conversion_orchestration(
            normalized_metadata=sample_metadata,
            files_map=sample_files_map,
            output_nwb_path=f"/tmp/http_output_{session_id_base}.nwb",
            session_id=f"{session_id_base}_http",
        )

        # Status should match
        assert mcp_response.status == http_response.status

        # Key conversion results should match
        mcp_data = mcp_response.data
        http_data = http_response.data

        core_fields = ["conversion_type", "script_generated", "conversion_successful"]
        for field in core_fields:
            assert mcp_data.get(field) == http_data.get(field), (
                f"Field {field} mismatch"
            )

    @pytest.mark.integration
    async def test_full_pipeline_parity(self, both_adapters, integration_dataset):
        """Test that full pipeline execution produces identical results."""
        mcp_adapter, http_adapter = both_adapters

        session_id_base = f"pipeline_parity_{uuid.uuid4().hex[:8]}"

        # Create conversion requests
        mcp_request = ConversionRequest(
            dataset_dir=integration_dataset,
            use_llm=False,
            session_id=f"{session_id_base}_mcp",
        )

        http_request = ConversionRequest(
            dataset_dir=integration_dataset,
            use_llm=False,
            session_id=f"{session_id_base}_http",
        )

        # Execute pipelines
        mcp_response = await mcp_adapter.conversion_service.run_full_pipeline(
            mcp_request
        )
        http_response = await http_adapter.conversion_service.run_full_pipeline(
            http_request
        )

        # Both should start successfully
        assert mcp_response.status == http_response.status
        assert mcp_response.status.value == "running"

        # Both should have task IDs
        assert "task_id" in mcp_response.data
        assert "task_id" in http_response.data

        # Messages should be identical
        assert mcp_response.data.get("message") == http_response.data.get("message")


# ============================================================================
# Tool System Parity Tests
# ============================================================================


class TestToolSystemParity:
    """Test that both adapters provide identical tool functionality."""

    @pytest.mark.integration
    async def test_tool_registration_parity(self, both_adapters):
        """Test that both adapters have identical tool registrations."""
        mcp_adapter, http_adapter = both_adapters

        mcp_tools = mcp_adapter.tool_system.registry.list_tools()
        http_tools = http_adapter.tool_system.registry.list_tools()

        # Same number of tools
        assert len(mcp_tools) == len(http_tools)

        # Same tool names
        mcp_names = {tool.name for tool in mcp_tools}
        http_names = {tool.name for tool in http_tools}
        assert mcp_names == http_names

        # Same tool categories
        mcp_categories = {tool.category for tool in mcp_tools}
        http_categories = {tool.category for tool in http_tools}
        assert mcp_categories == http_categories

        # Compare tool definitions in detail
        for mcp_tool in mcp_tools:
            http_tool = next(t for t in http_tools if t.name == mcp_tool.name)

            assert mcp_tool.description == http_tool.description
            assert mcp_tool.category == http_tool.category
            assert len(mcp_tool.parameters) == len(http_tool.parameters)
            assert mcp_tool.timeout_seconds == http_tool.timeout_seconds
            assert mcp_tool.tags == http_tool.tags

    @pytest.mark.integration
    async def test_tool_execution_parity(self, both_adapters, integration_dataset):
        """Test that tool execution produces identical results."""
        mcp_adapter, http_adapter = both_adapters

        session_id_base = f"tool_parity_{uuid.uuid4().hex[:8]}"

        # Test dataset analysis tool
        mcp_execution = await mcp_adapter.tool_system.executor.execute_tool(
            "dataset_analysis",
            {
                "dataset_dir": integration_dataset,
                "use_llm": False,
                "session_id": f"{session_id_base}_mcp",
            },
        )

        http_execution = await http_adapter.tool_system.executor.execute_tool(
            "dataset_analysis",
            {
                "dataset_dir": integration_dataset,
                "use_llm": False,
                "session_id": f"{session_id_base}_http",
            },
        )

        # Execution status should match
        assert mcp_execution.status == http_execution.status
        assert mcp_execution.status == ToolStatus.COMPLETED

        # Tool names should match
        assert mcp_execution.tool_name == http_execution.tool_name

        # Results should have same structure
        mcp_result = mcp_execution.result
        http_result = http_execution.result

        assert set(mcp_result.keys()) == set(http_result.keys())

        # Core result fields should match
        assert mcp_result["status"] == http_result["status"]

        # Data structures should match
        mcp_data = mcp_result["data"]
        http_data = http_result["data"]

        core_fields = ["analysis_type", "metadata_extracted", "llm_used"]
        for field in core_fields:
            assert mcp_data.get(field) == http_data.get(field)


# ============================================================================
# Session Management Parity Tests
# ============================================================================


class TestSessionManagementParity:
    """Test that session management works identically across adapters."""

    @pytest.mark.integration
    async def test_session_creation_parity(self, both_adapters, integration_dataset):
        """Test that session creation works identically."""
        mcp_adapter, http_adapter = both_adapters

        session_id_base = f"session_parity_{uuid.uuid4().hex[:8]}"

        # Start pipelines to create sessions
        mcp_request = ConversionRequest(
            dataset_dir=integration_dataset, session_id=f"{session_id_base}_mcp"
        )

        http_request = ConversionRequest(
            dataset_dir=integration_dataset, session_id=f"{session_id_base}_http"
        )

        await mcp_adapter.conversion_service.run_full_pipeline(mcp_request)
        await http_adapter.conversion_service.run_full_pipeline(http_request)

        # Both should have active sessions
        mcp_sessions = list(
            mcp_adapter.conversion_service.workflow_orchestrator.active_sessions.keys()
        )
        http_sessions = list(
            http_adapter.conversion_service.workflow_orchestrator.active_sessions.keys()
        )

        # Should have at least one session each
        assert len(mcp_sessions) > 0
        assert len(http_sessions) > 0

        # Our specific sessions should exist
        assert f"{session_id_base}_mcp" in mcp_sessions
        assert f"{session_id_base}_http" in http_sessions

    @pytest.mark.integration
    async def test_session_status_parity(self, both_adapters, integration_dataset):
        """Test that session status reporting is identical."""
        mcp_adapter, http_adapter = both_adapters

        session_id_base = f"status_parity_{uuid.uuid4().hex[:8]}"

        # Start pipelines
        mcp_request = ConversionRequest(
            dataset_dir=integration_dataset, session_id=f"{session_id_base}_mcp"
        )

        http_request = ConversionRequest(
            dataset_dir=integration_dataset, session_id=f"{session_id_base}_http"
        )

        await mcp_adapter.conversion_service.run_full_pipeline(mcp_request)
        await http_adapter.conversion_service.run_full_pipeline(http_request)

        # Get session statuses
        mcp_status = await mcp_adapter.conversion_service.get_session_status(
            f"{session_id_base}_mcp"
        )
        http_status = await http_adapter.conversion_service.get_session_status(
            f"{session_id_base}_http"
        )

        # Both should have status
        assert mcp_status is not None
        assert http_status is not None

        # Status structures should be identical
        assert set(mcp_status.keys()) == set(http_status.keys())

        # Key fields should have same types
        for key in ["session_id", "status", "current_step", "progress"]:
            assert key in mcp_status
            assert key in http_status
            assert type(mcp_status[key]) is type(http_status[key])


# ============================================================================
# Error Handling Parity Tests
# ============================================================================


class TestErrorHandlingParity:
    """Test that error handling is identical across adapters."""

    @pytest.mark.integration
    async def test_invalid_dataset_error_parity(self, both_adapters):
        """Test that invalid dataset errors are handled identically."""
        mcp_adapter, http_adapter = both_adapters

        invalid_path = "/definitely/nonexistent/path"
        session_id_base = f"error_parity_{uuid.uuid4().hex[:8]}"

        # Test analysis with invalid path
        mcp_response = await mcp_adapter.conversion_service.dataset_analysis(
            dataset_dir=invalid_path, use_llm=False, session_id=f"{session_id_base}_mcp"
        )

        http_response = await http_adapter.conversion_service.dataset_analysis(
            dataset_dir=invalid_path,
            use_llm=False,
            session_id=f"{session_id_base}_http",
        )

        # Both should fail
        assert mcp_response.status.value == "failed"
        assert http_response.status.value == "failed"

        # Both should have error messages
        assert mcp_response.error is not None
        assert http_response.error is not None

        # Error messages should be similar
        assert "does not exist" in mcp_response.error.lower()
        assert "does not exist" in http_response.error.lower()


# ============================================================================
# Performance Parity Tests
# ============================================================================


class TestPerformanceParity:
    """Test that performance characteristics are similar across adapters."""

    @pytest.mark.integration
    async def test_execution_time_parity(self, both_adapters, integration_dataset):
        """Test that execution times are similar across adapters."""
        mcp_adapter, http_adapter = both_adapters

        session_id_base = f"perf_parity_{uuid.uuid4().hex[:8]}"

        # Execute same operation through both adapters
        mcp_response = await mcp_adapter.conversion_service.dataset_analysis(
            dataset_dir=integration_dataset,
            use_llm=False,
            session_id=f"{session_id_base}_mcp",
        )

        http_response = await http_adapter.conversion_service.dataset_analysis(
            dataset_dir=integration_dataset,
            use_llm=False,
            session_id=f"{session_id_base}_http",
        )

        # Both should complete successfully
        assert mcp_response.status.value == "completed"
        assert http_response.status.value == "completed"

        # Execution times should be similar (within 50% of each other)
        mcp_time = mcp_response.execution_time or 0
        http_time = http_response.execution_time or 0

        if mcp_time > 0 and http_time > 0:
            time_ratio = max(mcp_time, http_time) / min(mcp_time, http_time)
            assert time_ratio < 2.0, (
                f"Execution time difference too large: MCP={mcp_time:.3f}s, HTTP={http_time:.3f}s"
            )


# ============================================================================
# End-to-End Parity Tests
# ============================================================================


class TestEndToEndParity:
    """Test complete end-to-end workflows for parity."""

    @pytest.mark.integration
    async def test_complete_workflow_parity(self, both_adapters, integration_dataset):
        """Test that complete workflows produce identical results."""
        mcp_adapter, http_adapter = both_adapters

        session_id_base = f"e2e_parity_{uuid.uuid4().hex[:8]}"

        # Execute complete workflow through both adapters
        mcp_request = ConversionRequest(
            dataset_dir=integration_dataset,
            use_llm=False,
            session_id=f"{session_id_base}_mcp",
        )

        http_request = ConversionRequest(
            dataset_dir=integration_dataset,
            use_llm=False,
            session_id=f"{session_id_base}_http",
        )

        # Start both pipelines
        mcp_start_response = await mcp_adapter.conversion_service.run_full_pipeline(
            mcp_request
        )
        http_start_response = await http_adapter.conversion_service.run_full_pipeline(
            http_request
        )

        # Both should start successfully
        assert mcp_start_response.status.value == "running"
        assert http_start_response.status.value == "running"

        # Both should have task IDs
        assert "task_id" in mcp_start_response.data
        assert "task_id" in http_start_response.data

        # Wait for completion (with timeout)
        max_wait_time = 30  # seconds
        wait_interval = 0.5  # seconds
        waited_time = 0

        mcp_final_status = None
        http_final_status = None

        while waited_time < max_wait_time:
            mcp_status = await mcp_adapter.conversion_service.get_session_status(
                f"{session_id_base}_mcp"
            )
            http_status = await http_adapter.conversion_service.get_session_status(
                f"{session_id_base}_http"
            )

            if mcp_status and mcp_status.get("status") in ["completed", "failed"]:
                mcp_final_status = mcp_status

            if http_status and http_status.get("status") in ["completed", "failed"]:
                http_final_status = http_status

            if mcp_final_status and http_final_status:
                break

            await asyncio.sleep(wait_interval)
            waited_time += wait_interval

        # Both should have completed
        assert mcp_final_status is not None, "MCP workflow did not complete in time"
        assert http_final_status is not None, "HTTP workflow did not complete in time"

        # Both should have same final status
        assert mcp_final_status["status"] == http_final_status["status"]

        # If successful, both should have similar progress
        if mcp_final_status["status"] == "completed":
            assert mcp_final_status.get("progress", 0) == http_final_status.get(
                "progress", 0
            )


if __name__ == "__main__":
    # Run the parity tests
    pytest.main([__file__, "-v", "--tb=short"])
