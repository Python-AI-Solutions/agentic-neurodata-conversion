"""Contract tests for core service layer.

This module provides comprehensive tests for the core service layer,
ensuring all business logic works correctly without transport dependencies.
"""

import asyncio
from datetime import datetime
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from agentic_neurodata_conversion.core.exceptions import AgentError
from agentic_neurodata_conversion.core.service import (
    AgentInfo,
    AgentManager,
    AgentStatus,
    ConversionRequest,
    ConversionResponse,
    ConversionService,
    ConversionStatus,
    SessionState,
    WorkflowOrchestrator,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
async def conversion_service():
    """Create and initialize a conversion service for testing."""
    service = ConversionService()
    await service.initialize()
    yield service
    await service.shutdown()


@pytest.fixture
async def agent_manager():
    """Create and initialize an agent manager for testing."""
    from agentic_neurodata_conversion.core.config import get_settings

    config = get_settings()
    manager = AgentManager(config)
    await manager.initialize_agents()
    yield manager
    await manager.shutdown_agents()


@pytest.fixture
async def workflow_orchestrator(agent_manager):
    """Create a workflow orchestrator for testing."""
    orchestrator = WorkflowOrchestrator(agent_manager)
    yield orchestrator


@pytest.fixture
def temp_dataset():
    """Create a temporary dataset for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create dummy dataset files
        (temp_path / "data.bin").write_text("dummy ephys data")
        (temp_path / "metadata.json").write_text(
            '{"experiment": "test", "subject": "mouse001"}'
        )
        (temp_path / "session_info.txt").write_text(
            "session_id: test_session\ndate: 2024-01-01"
        )

        yield str(temp_path)


@pytest.fixture
def sample_metadata():
    """Sample normalized metadata for testing."""
    return {
        "subject_id": "test_subject_001",
        "session_id": "test_session_001",
        "experiment_description": "Test experiment for unit testing",
        "experimenter": "Test User",
        "institution": "Test Institution",
        "session_start_time": "2024-01-01T10:00:00",
        "data_format": "open_ephys",
    }


@pytest.fixture
def sample_files_map():
    """Sample files map for testing."""
    return {
        "ephys": "/test/data/ephys_data.bin",
        "behavior": "/test/data/behavior_data.csv",
        "video": "/test/data/video_data.mp4",
    }


# ============================================================================
# Core Service Tests
# ============================================================================


class TestConversionService:
    """Test the main ConversionService class."""

    @pytest.mark.unit
    async def test_service_initialization(self):
        """Test service initialization and shutdown."""
        service = ConversionService()

        # Test initial state
        assert not service._initialized
        assert service.agent_manager is not None
        assert service.workflow_orchestrator is not None

        # Test initialization
        await service.initialize()
        assert service._initialized

        # Test shutdown
        await service.shutdown()
        assert not service._initialized

    @pytest.mark.unit
    async def test_service_double_initialization(self, conversion_service):
        """Test that double initialization is handled gracefully."""
        # Service is already initialized by fixture
        assert conversion_service._initialized

        # Second initialization should not cause issues
        await conversion_service.initialize()
        assert conversion_service._initialized

    @pytest.mark.unit
    async def test_dataset_analysis_success(self, conversion_service, temp_dataset):
        """Test successful dataset analysis."""
        response = await conversion_service.dataset_analysis(
            dataset_dir=temp_dataset, use_llm=False, session_id="test_analysis_001"
        )

        # Verify response structure
        assert isinstance(response, ConversionResponse)
        assert response.status == ConversionStatus.COMPLETED
        assert response.session_id == "test_analysis_001"
        assert response.execution_time is not None
        assert response.execution_time > 0
        assert response.error is None

        # Verify response data
        assert "analysis_type" in response.data
        assert "dataset_path" in response.data
        assert "metadata_extracted" in response.data
        assert "llm_used" in response.data
        assert response.data["llm_used"] is False

    @pytest.mark.unit
    async def test_dataset_analysis_with_llm(self, conversion_service, temp_dataset):
        """Test dataset analysis with LLM enabled."""
        response = await conversion_service.dataset_analysis(
            dataset_dir=temp_dataset, use_llm=True, session_id="test_analysis_llm_001"
        )

        assert response.status == ConversionStatus.COMPLETED
        assert response.data["llm_used"] is True

    @pytest.mark.unit
    async def test_dataset_analysis_invalid_directory(self, conversion_service):
        """Test dataset analysis with invalid directory."""
        response = await conversion_service.dataset_analysis(
            dataset_dir="/nonexistent/directory",
            use_llm=False,
            session_id="test_analysis_error_001",
        )

        assert response.status == ConversionStatus.FAILED
        assert response.error is not None
        assert "does not exist" in response.error

    @pytest.mark.unit
    async def test_conversion_orchestration_success(
        self, conversion_service, sample_metadata, sample_files_map
    ):
        """Test successful conversion orchestration."""
        response = await conversion_service.conversion_orchestration(
            normalized_metadata=sample_metadata,
            files_map=sample_files_map,
            output_nwb_path="/test/output.nwb",
            session_id="test_conversion_001",
        )

        assert isinstance(response, ConversionResponse)
        assert response.status == ConversionStatus.COMPLETED
        assert response.session_id == "test_conversion_001"
        assert response.execution_time is not None
        assert response.error is None

        # Verify conversion data
        assert "conversion_type" in response.data
        assert "script_generated" in response.data
        assert "output_path" in response.data

    @pytest.mark.unit
    async def test_conversion_orchestration_missing_metadata(
        self, conversion_service, sample_files_map
    ):
        """Test conversion orchestration with missing metadata."""
        response = await conversion_service.conversion_orchestration(
            normalized_metadata={},  # Empty metadata
            files_map=sample_files_map,
            session_id="test_conversion_error_001",
        )

        assert response.status == ConversionStatus.FAILED
        assert response.error is not None
        assert "metadata is required" in response.error.lower()

    @pytest.mark.unit
    async def test_conversion_orchestration_missing_files(
        self, conversion_service, sample_metadata
    ):
        """Test conversion orchestration with missing files map."""
        response = await conversion_service.conversion_orchestration(
            normalized_metadata=sample_metadata,
            files_map={},  # Empty files map
            session_id="test_conversion_error_002",
        )

        assert response.status == ConversionStatus.FAILED
        assert response.error is not None
        assert "files map is required" in response.error.lower()

    @pytest.mark.unit
    async def test_evaluate_nwb_file_success(self, conversion_service):
        """Test successful NWB file evaluation."""
        # Create a dummy NWB file for testing
        with tempfile.NamedTemporaryFile(suffix=".nwb", delete=False) as temp_file:
            temp_file.write(b"dummy nwb content")
            temp_nwb_path = temp_file.name

        try:
            response = await conversion_service.evaluate_nwb_file(
                nwb_path=temp_nwb_path,
                generate_report=True,
                include_visualizations=True,
                session_id="test_evaluation_001",
            )

            assert isinstance(response, ConversionResponse)
            assert response.status == ConversionStatus.COMPLETED
            assert response.session_id == "test_evaluation_001"
            assert response.execution_time is not None
            assert response.error is None

            # Verify evaluation data
            assert "evaluation_type" in response.data
            assert "nwb_file_path" in response.data
            assert "validation_passed" in response.data

        finally:
            Path(temp_nwb_path).unlink(missing_ok=True)

    @pytest.mark.unit
    async def test_evaluate_nwb_file_not_found(self, conversion_service):
        """Test NWB evaluation with non-existent file."""
        response = await conversion_service.evaluate_nwb_file(
            nwb_path="/nonexistent/file.nwb",
            generate_report=True,
            session_id="test_evaluation_error_001",
        )

        assert response.status == ConversionStatus.FAILED
        assert response.error is not None
        assert "does not exist" in response.error

    @pytest.mark.unit
    async def test_run_full_pipeline_success(self, conversion_service, temp_dataset):
        """Test successful full pipeline execution."""
        request = ConversionRequest(
            dataset_dir=temp_dataset, use_llm=False, session_id="test_pipeline_001"
        )

        response = await conversion_service.run_full_pipeline(request)

        assert isinstance(response, ConversionResponse)
        assert response.status == ConversionStatus.RUNNING  # Pipeline starts async
        assert response.session_id == "test_pipeline_001"
        assert response.execution_time is not None
        assert response.error is None

        # Verify pipeline data
        assert "task_id" in response.data
        assert "message" in response.data
        assert response.data["message"] == "Pipeline execution started"

    @pytest.mark.unit
    async def test_get_session_status_existing(self, conversion_service, temp_dataset):
        """Test getting status of existing session."""
        # Start a pipeline to create a session
        request = ConversionRequest(
            dataset_dir=temp_dataset,
            use_llm=False,
            session_id="test_session_status_001",
        )

        await conversion_service.run_full_pipeline(request)

        # Get session status
        status = await conversion_service.get_session_status("test_session_status_001")

        assert status is not None
        assert status["session_id"] == "test_session_status_001"
        assert "status" in status
        assert "current_step" in status
        assert "start_time" in status
        assert "progress" in status

    @pytest.mark.unit
    async def test_get_session_status_nonexistent(self, conversion_service):
        """Test getting status of non-existent session."""
        status = await conversion_service.get_session_status("nonexistent_session")
        assert status is None

    @pytest.mark.unit
    async def test_cancel_session_success(self, conversion_service, temp_dataset):
        """Test successful session cancellation."""
        # Start a pipeline to create a session
        request = ConversionRequest(
            dataset_dir=temp_dataset,
            use_llm=False,
            session_id="test_cancel_session_001",
        )

        await conversion_service.run_full_pipeline(request)

        # Cancel the session
        success = await conversion_service.cancel_session("test_cancel_session_001")
        assert success is True

        # Verify session is cancelled
        status = await conversion_service.get_session_status("test_cancel_session_001")
        if status:  # Session might be cleaned up
            assert status["status"] == "cancelled"

    @pytest.mark.unit
    async def test_cancel_session_nonexistent(self, conversion_service):
        """Test cancelling non-existent session."""
        success = await conversion_service.cancel_session("nonexistent_session")
        assert success is False

    @pytest.mark.unit
    async def test_get_agent_status(self, conversion_service):
        """Test getting agent status."""
        status = await conversion_service.get_agent_status()

        assert isinstance(status, dict)
        assert len(status) > 0

        # Check expected agents
        expected_agents = {"conversation", "conversion", "evaluation"}
        assert expected_agents.issubset(set(status.keys()))

        # Check agent status structure
        for _agent_name, agent_info in status.items():
            assert "name" in agent_info
            assert "status" in agent_info
            assert "total_executions" in agent_info
            assert "success_rate" in agent_info

    @pytest.mark.unit
    async def test_get_specific_agent_status(self, conversion_service):
        """Test getting status of specific agent."""
        status = await conversion_service.get_agent_status("conversation")

        assert isinstance(status, dict)
        assert status["name"] == "conversation"
        assert "status" in status
        assert "statistics" in status


# ============================================================================
# Agent Manager Tests
# ============================================================================


class TestAgentManager:
    """Test the AgentManager class."""

    @pytest.mark.unit
    async def test_agent_initialization(self):
        """Test agent manager initialization."""
        from agentic_neurodata_conversion.core.config import get_settings

        config = get_settings()
        manager = AgentManager(config)

        # Test initial state
        assert len(manager.agents) == 0

        # Test initialization
        await manager.initialize_agents()

        # Verify agents are initialized
        expected_agents = {"conversation", "conversion", "evaluation"}
        assert set(manager.agents.keys()) == expected_agents

        for agent_name, agent_info in manager.agents.items():
            assert isinstance(agent_info, AgentInfo)
            assert agent_info.name == agent_name
            assert agent_info.status in [AgentStatus.READY, AgentStatus.ERROR]

        await manager.shutdown_agents()

    @pytest.mark.unit
    async def test_agent_execution(self, agent_manager):
        """Test agent task execution."""
        result = await agent_manager.execute_agent_task(
            "conversation",
            dataset_dir="/test/path",
            use_llm=False,
            session_id="test_agent_exec_001",
        )

        assert result.status in [ConversionStatus.COMPLETED, ConversionStatus.FAILED]
        assert result.agent_id == "conversation"
        assert result.execution_time is not None
        assert isinstance(result.data, dict)

        # Check agent statistics were updated
        agent_info = agent_manager.agents["conversation"]
        assert agent_info.total_executions > 0

    @pytest.mark.unit
    async def test_agent_execution_nonexistent(self, agent_manager):
        """Test execution of non-existent agent."""
        with pytest.raises(AgentError) as exc_info:
            await agent_manager.execute_agent_task("nonexistent_agent")

        assert "not found" in str(exc_info.value)

    @pytest.mark.unit
    async def test_agent_status_retrieval(self, agent_manager):
        """Test agent status retrieval."""
        # Get all agents
        all_status = await agent_manager.get_agent_status()
        assert isinstance(all_status, dict)
        assert len(all_status) == 3

        # Get specific agent
        conv_status = await agent_manager.get_agent_status("conversation")
        assert conv_status["name"] == "conversation"
        assert "status" in conv_status
        assert "statistics" in conv_status


# ============================================================================
# Workflow Orchestrator Tests
# ============================================================================


class TestWorkflowOrchestrator:
    """Test the WorkflowOrchestrator class."""

    @pytest.mark.unit
    async def test_pipeline_execution_start(self, workflow_orchestrator, temp_dataset):
        """Test starting pipeline execution."""
        session_id = "test_workflow_001"

        task_id = await workflow_orchestrator.start_pipeline_execution(
            session_id=session_id, dataset_dir=temp_dataset, use_llm=False
        )

        assert task_id == f"pipeline_{session_id}"
        assert session_id in workflow_orchestrator.active_sessions

        # Check session state
        session = workflow_orchestrator.active_sessions[session_id]
        assert isinstance(session, SessionState)
        assert session.session_id == session_id
        assert session.dataset_dir == temp_dataset
        assert session.use_llm is False

    @pytest.mark.unit
    async def test_session_status_retrieval(self, workflow_orchestrator, temp_dataset):
        """Test session status retrieval."""
        session_id = "test_workflow_status_001"

        # Start pipeline
        await workflow_orchestrator.start_pipeline_execution(
            session_id=session_id, dataset_dir=temp_dataset, use_llm=False
        )

        # Get status
        status = await workflow_orchestrator.get_session_status(session_id)

        assert status is not None
        assert status["session_id"] == session_id
        assert "status" in status
        assert "current_step" in status
        assert "progress" in status
        assert isinstance(status["progress"], float)

    @pytest.mark.unit
    async def test_session_cancellation(self, workflow_orchestrator, temp_dataset):
        """Test session cancellation."""
        session_id = "test_workflow_cancel_001"

        # Start pipeline
        await workflow_orchestrator.start_pipeline_execution(
            session_id=session_id, dataset_dir=temp_dataset, use_llm=False
        )

        # Cancel session
        success = await workflow_orchestrator.cancel_session(session_id)
        assert success is True

        # Verify cancellation
        session = workflow_orchestrator.active_sessions.get(session_id)
        if session:  # Session might be cleaned up
            assert session.status == ConversionStatus.CANCELLED


# ============================================================================
# Data Model Tests
# ============================================================================


class TestDataModels:
    """Test core data models."""

    @pytest.mark.unit
    def test_conversion_request_validation(self, temp_dataset):
        """Test ConversionRequest validation."""
        # Valid request
        request = ConversionRequest(
            dataset_dir=temp_dataset, use_llm=False, session_id="test_request_001"
        )

        assert request.dataset_dir == temp_dataset
        assert request.use_llm is False
        assert request.session_id == "test_request_001"

    @pytest.mark.unit
    def test_conversion_request_invalid_directory(self):
        """Test ConversionRequest with invalid directory."""
        with pytest.raises(ValueError) as exc_info:
            ConversionRequest(dataset_dir="/nonexistent/directory", use_llm=False)

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.unit
    def test_conversion_response_creation(self):
        """Test ConversionResponse creation."""
        response = ConversionResponse(
            status=ConversionStatus.COMPLETED,
            data={"test": "data"},
            session_id="test_response_001",
            execution_time=1.5,
        )

        assert response.status == ConversionStatus.COMPLETED
        assert response.data == {"test": "data"}
        assert response.session_id == "test_response_001"
        assert response.execution_time == 1.5
        assert response.error is None
        assert isinstance(response.timestamp, datetime)

    @pytest.mark.unit
    def test_session_state_creation(self):
        """Test SessionState creation and properties."""
        session = SessionState(
            session_id="test_session_001", dataset_dir="/test/path", use_llm=True
        )

        assert session.session_id == "test_session_001"
        assert session.dataset_dir == "/test/path"
        assert session.use_llm is True
        assert session.status == ConversionStatus.PENDING
        assert isinstance(session.start_time, datetime)
        assert session.end_time is None

    @pytest.mark.unit
    def test_agent_info_creation(self):
        """Test AgentInfo creation and properties."""
        agent = AgentInfo(name="test_agent", agent_type="test_type")

        assert agent.name == "test_agent"
        assert agent.agent_type == "test_type"
        assert agent.status == AgentStatus.INITIALIZING
        assert isinstance(agent.created_at, datetime)
        assert agent.total_executions == 0
        assert agent.success_rate == 0.0

        # Test success rate calculation
        agent.total_executions = 10
        agent.successful_executions = 8
        assert agent.success_rate == 0.8


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in core service."""

    @pytest.mark.unit
    async def test_service_not_initialized_error(self):
        """Test operations on uninitialized service."""
        service = ConversionService()

        # Should work without initialization (auto-initializes)
        await service.dataset_analysis(
            dataset_dir="/tmp",  # Will fail for other reasons
            use_llm=False,
        )

        # Service should auto-initialize
        assert service._initialized

        await service.shutdown()

    @pytest.mark.unit
    async def test_validation_error_handling(self, conversion_service):
        """Test handling of validation errors."""
        # Test with invalid parameters that should trigger validation
        response = await conversion_service.conversion_orchestration(
            normalized_metadata={},  # Invalid empty metadata
            files_map={},  # Invalid empty files map
            session_id="test_validation_error",
        )

        assert response.status == ConversionStatus.FAILED
        assert response.error is not None

    @pytest.mark.unit
    async def test_concurrent_operations(self, conversion_service, temp_dataset):
        """Test concurrent operations on the service."""
        # Start multiple operations concurrently
        tasks = []
        for i in range(3):
            task = conversion_service.dataset_analysis(
                dataset_dir=temp_dataset,
                use_llm=False,
                session_id=f"concurrent_test_{i}",
            )
            tasks.append(task)

        # Wait for all to complete
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status == ConversionStatus.COMPLETED
            assert response.error is None

        # Session IDs should be unique
        session_ids = [r.session_id for r in responses]
        assert len(set(session_ids)) == 3


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance characteristics of core service."""

    @pytest.mark.unit
    async def test_operation_timing(self, conversion_service, temp_dataset):
        """Test that operations complete within reasonable time."""
        start_time = datetime.now()

        response = await conversion_service.dataset_analysis(
            dataset_dir=temp_dataset, use_llm=False, session_id="performance_test_001"
        )

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Should complete within 5 seconds
        assert total_time < 5.0
        assert response.execution_time is not None
        assert response.execution_time > 0
        assert response.execution_time < 5.0

    @pytest.mark.unit
    async def test_memory_usage_stability(self, conversion_service, temp_dataset):
        """Test that repeated operations don't cause memory leaks."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform multiple operations
        for i in range(5):
            response = await conversion_service.dataset_analysis(
                dataset_dir=temp_dataset, use_llm=False, session_id=f"memory_test_{i}"
            )
            assert response.status == ConversionStatus.COMPLETED

            # Force garbage collection
            gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024


# ============================================================================
# Integration Points Tests
# ============================================================================


class TestIntegrationPoints:
    """Test integration points with external systems."""

    @pytest.mark.unit
    async def test_configuration_integration(self, conversion_service):
        """Test integration with configuration system."""
        # Service should use configuration
        assert conversion_service.config is not None

        # Should have access to agent configuration
        agent_config = conversion_service.config.agents
        assert agent_config is not None
        assert hasattr(agent_config, "conversation_model")
        assert hasattr(agent_config, "conversion_timeout")

    @pytest.mark.unit
    async def test_logging_integration(self, conversion_service, temp_dataset):
        """Test integration with logging system."""

        # Capture log messages
        with patch(
            "agentic_neurodata_conversion.core.service.logging.getLogger"
        ) as mock_logger:
            mock_log_instance = MagicMock()
            mock_logger.return_value = mock_log_instance

            # Perform operation that should log
            await conversion_service.dataset_analysis(
                dataset_dir=temp_dataset, use_llm=False, session_id="logging_test_001"
            )

            # Verify logging was called
            assert mock_log_instance.info.called or mock_log_instance.debug.called

    @pytest.mark.unit
    async def test_exception_integration(self, conversion_service):
        """Test integration with custom exception system."""
        # Test that custom exceptions are properly raised and handled
        response = await conversion_service.dataset_analysis(
            dataset_dir="/definitely/nonexistent/path",
            use_llm=False,
            session_id="exception_test_001",
        )

        # Should handle the error gracefully
        assert response.status == ConversionStatus.FAILED
        assert response.error is not None
        assert isinstance(response.error, str)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
