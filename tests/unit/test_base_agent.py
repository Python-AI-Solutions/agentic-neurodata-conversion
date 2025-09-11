"""
Unit tests for the base agent framework.

Tests the BaseAgent abstract class, AgentResult dataclass, and AgentConfig.
"""

import pytest

# Import the actual components that should be implemented
try:
    from agentic_neurodata_conversion.agents.base import (
        AgentConfig,
        AgentResult,
        AgentStatus,
        BaseAgent,
    )

    COMPONENTS_AVAILABLE = True
except ImportError:
    # These should fail until implemented
    BaseAgent = None
    AgentResult = None
    AgentStatus = None
    AgentConfig = None
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE, reason="Base agent components not implemented yet"
)


class TestAgentConfig:
    """Test the AgentConfig class."""

    @pytest.mark.unit
    def test_agent_config_initialization(self):
        """Test AgentConfig initialization with default values."""
        config = AgentConfig()

        assert config.version == "1.0"
        assert config.llm_config == {}
        assert config.use_llm is False
        assert config.conversion_timeout == 300

    @pytest.mark.unit
    def test_agent_config_custom_values(self):
        """Test AgentConfig initialization with custom values."""
        llm_config = {"model": "gpt-4", "temperature": 0.7}
        config = AgentConfig(
            version="2.0",
            llm_config=llm_config,
            use_llm=True,
            conversion_timeout=600,
            custom_param="test_value",
        )

        assert config.version == "2.0"
        assert config.llm_config == llm_config
        assert config.use_llm is True
        assert config.conversion_timeout == 600
        assert config.custom_param == "test_value"


class TestAgentResult:
    """Test the AgentResult dataclass."""

    @pytest.mark.unit
    def test_agent_result_initialization(self):
        """Test AgentResult initialization."""
        result = AgentResult(
            status=AgentStatus.COMPLETED,
            data={"key": "value"},
            metadata={"agent_type": "test"},
            provenance={"source": "test"},
            execution_time=1.5,
            agent_id="test_agent_123",
        )

        assert result.status == AgentStatus.COMPLETED
        assert result.data == {"key": "value"}
        assert result.metadata == {"agent_type": "test"}
        assert result.provenance == {"source": "test"}
        assert result.execution_time == 1.5
        assert result.agent_id == "test_agent_123"
        assert result.error is None
        assert result.warnings == []

    @pytest.mark.unit
    def test_agent_result_with_error(self):
        """Test AgentResult with error information."""
        result = AgentResult(
            status=AgentStatus.ERROR,
            data={},
            metadata={},
            provenance={},
            execution_time=0.5,
            agent_id="test_agent_123",
            error="Test error message",
            warnings=["Warning 1", "Warning 2"],
        )

        assert result.status == AgentStatus.ERROR
        assert result.error == "Test error message"
        assert result.warnings == ["Warning 1", "Warning 2"]

    @pytest.mark.unit
    def test_agent_result_warnings_default(self):
        """Test that warnings defaults to empty list."""
        result = AgentResult(
            status=AgentStatus.COMPLETED,
            data={},
            metadata={},
            provenance={},
            execution_time=1.0,
            agent_id="test_agent_123",
        )

        assert result.warnings == []


class ConcreteTestAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    def __init__(self, config: AgentConfig):
        super().__init__(config, "test_agent")
        self.validate_inputs_called = False
        self.execute_internal_called = False
        self.process_results_called = False

    async def _validate_inputs(self, **kwargs):
        """Test implementation of input validation."""
        self.validate_inputs_called = True
        if "invalid" in kwargs:
            raise ValueError("Invalid input provided")
        return kwargs

    async def _execute_internal(self, **kwargs):
        """Test implementation of internal execution."""
        self.execute_internal_called = True
        if "fail" in kwargs:
            raise RuntimeError("Execution failed")
        return {"result": "success", "input_count": len(kwargs)}

    async def _process_results(self, result_data, **kwargs):
        """Test implementation of result processing."""
        self.process_results_called = True
        result_data["processed"] = True
        return result_data


class TestBaseAgent:
    """Test the BaseAgent abstract class."""

    @pytest.fixture
    def agent_config(self):
        """Create a test agent configuration."""
        return AgentConfig(version="test", use_llm=False)

    @pytest.fixture
    def test_agent(self, agent_config):
        """Create a test agent instance."""
        return ConcreteTestAgent(agent_config)

    @pytest.mark.unit
    def test_agent_initialization(self, test_agent):
        """Test agent initialization."""
        assert test_agent.agent_type == "test_agent"
        assert test_agent.agent_id.startswith("test_agent_")
        assert test_agent.status == AgentStatus.IDLE
        assert test_agent.metrics["total_executions"] == 0
        assert test_agent.metrics["successful_executions"] == 0
        assert test_agent.metrics["failed_executions"] == 0
        assert test_agent.metrics["average_execution_time"] == 0.0

    @pytest.mark.unit
    async def test_successful_execution(self, test_agent):
        """Test successful agent execution."""
        result = await test_agent.execute(test_param="value")

        assert isinstance(result, AgentResult)
        assert result.status == AgentStatus.COMPLETED
        assert result.data["result"] == "success"
        assert result.data["input_count"] == 1
        assert result.data["processed"] is True
        assert result.agent_id == test_agent.agent_id
        assert result.error is None
        assert result.execution_time >= 0  # Allow for very fast execution

        # Check that all methods were called
        assert test_agent.validate_inputs_called
        assert test_agent.execute_internal_called
        assert test_agent.process_results_called

        # Check metrics were updated
        assert test_agent.metrics["total_executions"] == 1
        assert test_agent.metrics["successful_executions"] == 1
        assert test_agent.metrics["failed_executions"] == 0
        assert (
            test_agent.metrics["average_execution_time"] >= 0
        )  # Allow for very fast execution

    @pytest.mark.unit
    async def test_execution_with_validation_error(self, test_agent):
        """Test agent execution with validation error."""
        result = await test_agent.execute(invalid="value")

        assert isinstance(result, AgentResult)
        assert result.status == AgentStatus.ERROR
        assert result.error == "Invalid input provided"
        assert result.data == {}

        # Check that validation was called but execution was not
        assert test_agent.validate_inputs_called
        assert not test_agent.execute_internal_called
        assert not test_agent.process_results_called

        # Check metrics were updated
        assert test_agent.metrics["total_executions"] == 1
        assert test_agent.metrics["successful_executions"] == 0
        assert test_agent.metrics["failed_executions"] == 1

    @pytest.mark.unit
    async def test_execution_with_internal_error(self, test_agent):
        """Test agent execution with internal execution error."""
        result = await test_agent.execute(fail="value")

        assert isinstance(result, AgentResult)
        assert result.status == AgentStatus.ERROR
        assert result.error == "Execution failed"
        assert result.data == {}

        # Check that validation and execution were called but processing was not
        assert test_agent.validate_inputs_called
        assert test_agent.execute_internal_called
        assert not test_agent.process_results_called

        # Check metrics were updated
        assert test_agent.metrics["total_executions"] == 1
        assert test_agent.metrics["successful_executions"] == 0
        assert test_agent.metrics["failed_executions"] == 1

    @pytest.mark.unit
    def test_get_metrics(self, test_agent):
        """Test getting agent metrics."""
        metrics = test_agent.get_metrics()

        assert "total_executions" in metrics
        assert "successful_executions" in metrics
        assert "failed_executions" in metrics
        assert "average_execution_time" in metrics
        assert "success_rate" in metrics
        assert "current_status" in metrics

        assert metrics["success_rate"] == 0.0  # No executions yet
        assert metrics["current_status"] == "idle"

    @pytest.mark.unit
    async def test_metrics_calculation(self, test_agent):
        """Test metrics calculation after multiple executions."""
        # Execute successful task
        await test_agent.execute(test_param="value1")

        # Execute failed task
        await test_agent.execute(invalid="value")

        # Execute another successful task
        await test_agent.execute(test_param="value2")

        metrics = test_agent.get_metrics()

        assert metrics["total_executions"] == 3
        assert metrics["successful_executions"] == 2
        assert metrics["failed_executions"] == 1
        assert metrics["success_rate"] == 2 / 3
        assert metrics["average_execution_time"] >= 0  # Allow for very fast execution

    @pytest.mark.unit
    def test_metadata_generation(self, test_agent):
        """Test metadata generation."""
        metadata = test_agent._generate_metadata(param1="value1", param2=123)

        assert metadata["agent_type"] == "test_agent"
        assert metadata["agent_id"] == test_agent.agent_id
        assert "timestamp" in metadata
        assert metadata["config_version"] == "test"
        assert metadata["inputs"] == {"param1": "str", "param2": "int"}

    @pytest.mark.unit
    def test_provenance_generation(self, test_agent):
        """Test provenance generation."""
        provenance = test_agent._generate_provenance(param1="value1")

        assert provenance["agent"] == "test_agent"
        assert provenance["agent_id"] == test_agent.agent_id
        assert "execution_timestamp" in provenance
        assert provenance["input_sources"] == {"param1": "user_provided"}
        assert provenance["processing_steps"] == ["test_agent_processing"]
        assert provenance["external_services"] == []


class TestAgentStatus:
    """Test the AgentStatus enum."""

    @pytest.mark.unit
    def test_agent_status_values(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.PROCESSING.value == "processing"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.ERROR.value == "error"
