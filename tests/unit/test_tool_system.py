"""Contract tests for tool system.

This module provides comprehensive tests for the tool registry and execution system,
ensuring all tool functionality works correctly without transport dependencies.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import tempfile

import pytest

from agentic_neurodata_conversion.core.exceptions import ValidationError
from agentic_neurodata_conversion.core.service import ConversionService
from agentic_neurodata_conversion.core.tools import (
    ConversionToolSystem,
    ParameterType,
    ToolCategory,
    ToolDefinition,
    ToolExecution,
    ToolExecutor,
    ToolMetrics,
    ToolParameter,
    ToolRegistry,
    ToolStatus,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tool_registry():
    """Create a tool registry for testing."""
    return ToolRegistry()


@pytest.fixture
def tool_executor(tool_registry):
    """Create a tool executor for testing."""
    return ToolExecutor(tool_registry)


@pytest.fixture
async def conversion_tool_system():
    """Create a conversion tool system for testing."""
    service = ConversionService()
    await service.initialize()
    tool_system = ConversionToolSystem(service)
    yield tool_system
    await service.shutdown()


@pytest.fixture
def sample_tool_definition():
    """Create a sample tool definition for testing."""
    return ToolDefinition(
        name="test_tool",
        description="A test tool for unit testing",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="input_text",
                type=ParameterType.STRING,
                description="Input text to process",
                required=True,
            ),
            ToolParameter(
                name="count",
                type=ParameterType.INTEGER,
                description="Number of times to repeat",
                required=False,
                default=1,
                minimum=1,
                maximum=10,
            ),
            ToolParameter(
                name="uppercase",
                type=ParameterType.BOOLEAN,
                description="Whether to convert to uppercase",
                required=False,
                default=False,
            ),
        ],
        returns="Processed text result",
        examples=[{"input_text": "hello", "count": 2, "uppercase": True}],
        tags=["test", "utility"],
        timeout_seconds=30,
    )


@pytest.fixture
def temp_dataset():
    """Create a temporary dataset for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create dummy dataset files
        (temp_path / "data.bin").write_text("dummy ephys data")
        (temp_path / "metadata.json").write_text('{"experiment": "test"}')

        yield str(temp_path)


# ============================================================================
# Tool Registry Tests
# ============================================================================


class TestToolRegistry:
    """Test the ToolRegistry class."""

    @pytest.mark.unit
    def test_registry_initialization(self, tool_registry):
        """Test tool registry initialization."""
        assert len(tool_registry.tools) == 0
        assert len(tool_registry.tool_functions) == 0
        assert len(tool_registry.metrics) == 0

    @pytest.mark.unit
    def test_tool_registration_success(self, tool_registry, sample_tool_definition):
        """Test successful tool registration."""

        def test_function(**kwargs):
            return {"result": f"processed: {kwargs.get('input_text', '')}"}

        tool_registry.register_tool(sample_tool_definition, test_function)

        # Verify registration
        assert "test_tool" in tool_registry.tools
        assert "test_tool" in tool_registry.tool_functions
        assert "test_tool" in tool_registry.metrics

        # Verify tool definition
        registered_tool = tool_registry.get_tool("test_tool")
        assert registered_tool is not None
        assert registered_tool.name == "test_tool"
        assert registered_tool.category == ToolCategory.UTILITY
        assert len(registered_tool.parameters) == 3

        # Verify metrics initialization
        metrics = tool_registry.get_tool_metrics("test_tool")
        assert metrics is not None
        assert metrics.tool_name == "test_tool"
        assert metrics.total_executions == 0

    @pytest.mark.unit
    def test_tool_registration_invalid_signature(
        self, tool_registry, sample_tool_definition
    ):
        """Test tool registration with invalid function signature."""

        def invalid_function(_wrong_param):
            return {"result": "test"}

        # Should raise ValidationError for missing required parameters
        with pytest.raises(ValidationError) as exc_info:
            tool_registry.register_tool(sample_tool_definition, invalid_function)

        assert "missing required parameters" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_tool_registration_kwargs_function(
        self, tool_registry, sample_tool_definition
    ):
        """Test tool registration with **kwargs function (should work)."""

        def kwargs_function(**_kwargs):
            return {"result": "processed"}

        # Should work with **kwargs functions
        tool_registry.register_tool(sample_tool_definition, kwargs_function)
        assert "test_tool" in tool_registry.tools

    @pytest.mark.unit
    def test_list_tools_all(self, tool_registry, sample_tool_definition):
        """Test listing all tools."""

        def test_function(**_kwargs):
            return {"result": "test"}

        tool_registry.register_tool(sample_tool_definition, test_function)

        tools = tool_registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "test_tool"

    @pytest.mark.unit
    def test_list_tools_by_category(self, tool_registry):
        """Test listing tools by category."""
        # Register tools in different categories
        analysis_tool = ToolDefinition(
            name="analysis_tool",
            description="Analysis tool",
            category=ToolCategory.ANALYSIS,
            parameters=[],
            returns="Analysis result",
        )

        utility_tool = ToolDefinition(
            name="utility_tool",
            description="Utility tool",
            category=ToolCategory.UTILITY,
            parameters=[],
            returns="Utility result",
        )

        def dummy_function(**_kwargs):
            return {"result": "test"}

        tool_registry.register_tool(analysis_tool, dummy_function)
        tool_registry.register_tool(utility_tool, dummy_function)

        # Test category filtering
        analysis_tools = tool_registry.list_tools(category=ToolCategory.ANALYSIS)
        assert len(analysis_tools) == 1
        assert analysis_tools[0].name == "analysis_tool"

        utility_tools = tool_registry.list_tools(category=ToolCategory.UTILITY)
        assert len(utility_tools) == 1
        assert utility_tools[0].name == "utility_tool"

    @pytest.mark.unit
    def test_list_tools_by_tags(self, tool_registry):
        """Test listing tools by tags."""
        tool1 = ToolDefinition(
            name="tool1",
            description="Tool 1",
            category=ToolCategory.UTILITY,
            parameters=[],
            returns="Result",
            tags=["tag1", "tag2"],
        )

        tool2 = ToolDefinition(
            name="tool2",
            description="Tool 2",
            category=ToolCategory.UTILITY,
            parameters=[],
            returns="Result",
            tags=["tag2", "tag3"],
        )

        def dummy_function(**_kwargs):
            return {"result": "test"}

        tool_registry.register_tool(tool1, dummy_function)
        tool_registry.register_tool(tool2, dummy_function)

        # Test tag filtering
        tag1_tools = tool_registry.list_tools(tags=["tag1"])
        assert len(tag1_tools) == 1
        assert tag1_tools[0].name == "tool1"

        tag2_tools = tool_registry.list_tools(tags=["tag2"])
        assert len(tag2_tools) == 2

        # Test multiple tag filtering (AND operation)
        tag1_and_tag2_tools = tool_registry.list_tools(tags=["tag1", "tag2"])
        assert len(tag1_and_tag2_tools) == 1
        assert tag1_and_tag2_tools[0].name == "tool1"

    @pytest.mark.unit
    def test_search_tools(self, tool_registry, sample_tool_definition):
        """Test tool search functionality."""

        def test_function(**_kwargs):
            return {"result": "test"}

        tool_registry.register_tool(sample_tool_definition, test_function)

        # Search by name
        results = tool_registry.search_tools("test")
        assert len(results) == 1
        assert results[0].name == "test_tool"

        # Search by description
        results = tool_registry.search_tools("unit testing")
        assert len(results) == 1

        # Search by tag
        results = tool_registry.search_tools("utility")
        assert len(results) == 1

        # Search with no matches
        results = tool_registry.search_tools("nonexistent")
        assert len(results) == 0

    @pytest.mark.unit
    def test_metrics_update(self, tool_registry, sample_tool_definition):
        """Test tool metrics updating."""

        def test_function(**_kwargs):
            return {"result": "test"}

        tool_registry.register_tool(sample_tool_definition, test_function)

        # Create mock execution
        execution = ToolExecution(
            tool_name="test_tool",
            parameters={"input_text": "test"},
            status=ToolStatus.COMPLETED,
            execution_time=1.5,
        )
        execution.end_time = datetime.now(timezone.utc)

        # Update metrics
        tool_registry.update_metrics(execution)

        # Verify metrics
        metrics = tool_registry.get_tool_metrics("test_tool")
        assert metrics.total_executions == 1
        assert metrics.successful_executions == 1
        assert metrics.failed_executions == 0
        assert metrics.success_rate == 1.0
        assert metrics.average_execution_time == 1.5
        assert metrics.min_execution_time == 1.5
        assert metrics.max_execution_time == 1.5


# ============================================================================
# Tool Executor Tests
# ============================================================================


class TestToolExecutor:
    """Test the ToolExecutor class."""

    @pytest.mark.unit
    async def test_execute_tool_success(self, tool_executor, sample_tool_definition):
        """Test successful tool execution."""

        def test_function(**kwargs):
            input_text = kwargs.get("input_text", "")
            count = kwargs.get("count", 1)
            uppercase = kwargs.get("uppercase", False)

            result = input_text * count
            if uppercase:
                result = result.upper()

            return {"processed_text": result, "length": len(result)}

        tool_executor.registry.register_tool(sample_tool_definition, test_function)

        # Execute tool
        execution = await tool_executor.execute_tool(
            "test_tool", {"input_text": "hello", "count": 2, "uppercase": True}
        )

        # Verify execution
        assert execution.status == ToolStatus.COMPLETED
        assert execution.tool_name == "test_tool"
        assert execution.execution_time is not None
        assert execution.execution_time > 0
        assert execution.error is None

        # Verify result
        assert execution.result is not None
        assert execution.result["processed_text"] == "HELLOHELLO"
        assert execution.result["length"] == 10

    @pytest.mark.unit
    async def test_execute_tool_not_found(self, tool_executor):
        """Test execution of non-existent tool."""
        with pytest.raises(ValidationError) as exc_info:
            await tool_executor.execute_tool("nonexistent_tool", {})

        assert "tool not found" in str(exc_info.value).lower()

    @pytest.mark.unit
    async def test_execute_tool_missing_parameters(
        self, tool_executor, sample_tool_definition
    ):
        """Test tool execution with missing required parameters."""

        def test_function(**_kwargs):
            return {"result": "test"}

        tool_executor.registry.register_tool(sample_tool_definition, test_function)

        with pytest.raises(ValidationError) as exc_info:
            await tool_executor.execute_tool(
                "test_tool", {}
            )  # Missing required input_text

        assert "missing required parameters" in str(exc_info.value).lower()

    @pytest.mark.unit
    async def test_execute_tool_invalid_parameter_type(
        self, tool_executor, sample_tool_definition
    ):
        """Test tool execution with invalid parameter types."""

        def test_function(**_kwargs):
            return {"result": "test"}

        tool_executor.registry.register_tool(sample_tool_definition, test_function)

        with pytest.raises(ValidationError) as exc_info:
            await tool_executor.execute_tool(
                "test_tool",
                {
                    "input_text": "hello",
                    "count": "not_an_integer",  # Should be integer
                },
            )

        assert "must be an integer" in str(exc_info.value).lower()

    @pytest.mark.unit
    async def test_execute_tool_parameter_range_validation(
        self, tool_executor, sample_tool_definition
    ):
        """Test tool execution with out-of-range parameters."""

        def test_function(**_kwargs):
            return {"result": "test"}

        tool_executor.registry.register_tool(sample_tool_definition, test_function)

        with pytest.raises(ValidationError) as exc_info:
            await tool_executor.execute_tool(
                "test_tool",
                {
                    "input_text": "hello",
                    "count": 15,  # Maximum is 10
                },
            )

        assert "must be <=" in str(exc_info.value)

    @pytest.mark.unit
    async def test_execute_tool_with_defaults(
        self, tool_executor, sample_tool_definition
    ):
        """Test tool execution using default parameter values."""

        def test_function(**kwargs):
            return {
                "input_text": kwargs.get("input_text"),
                "count": kwargs.get("count", 1),
                "uppercase": kwargs.get("uppercase", False),
            }

        tool_executor.registry.register_tool(sample_tool_definition, test_function)

        execution = await tool_executor.execute_tool(
            "test_tool",
            {"input_text": "hello"},  # Only required parameter
        )

        assert execution.status == ToolStatus.COMPLETED
        assert execution.result["count"] == 1  # Default value
        assert execution.result["uppercase"] is False  # Default value

    @pytest.mark.unit
    async def test_execute_tool_timeout(self, tool_executor):
        """Test tool execution timeout."""
        # Create tool with very short timeout
        timeout_tool = ToolDefinition(
            name="timeout_tool",
            description="Tool that times out",
            category=ToolCategory.UTILITY,
            parameters=[],
            returns="Never returns",
            timeout_seconds=0.1,  # Very short timeout
        )

        async def slow_function(**_kwargs):
            await asyncio.sleep(1)  # Longer than timeout
            return {"result": "should not reach here"}

        tool_executor.registry.register_tool(timeout_tool, slow_function)

        execution = await tool_executor.execute_tool("timeout_tool", {})

        assert execution.status == ToolStatus.TIMEOUT
        assert execution.error is not None
        assert "timed out" in execution.error.lower()

    @pytest.mark.unit
    async def test_execute_tool_exception_handling(
        self, tool_executor, sample_tool_definition
    ):
        """Test tool execution with function that raises exception."""

        def failing_function(**_kwargs):
            raise ValueError("Test error message")

        tool_executor.registry.register_tool(sample_tool_definition, failing_function)

        execution = await tool_executor.execute_tool(
            "test_tool", {"input_text": "hello"}
        )

        assert execution.status == ToolStatus.FAILED
        assert execution.error is not None
        assert "Test error message" in execution.error

    @pytest.mark.unit
    async def test_active_executions_tracking(
        self, tool_executor, sample_tool_definition
    ):
        """Test tracking of active executions."""

        async def slow_function(**_kwargs):
            await asyncio.sleep(0.1)
            return {"result": "done"}

        tool_executor.registry.register_tool(sample_tool_definition, slow_function)

        # Start execution but don't wait
        task = asyncio.create_task(
            tool_executor.execute_tool("test_tool", {"input_text": "hello"})
        )

        # Give it a moment to start
        await asyncio.sleep(0.01)

        # Check active executions
        active = tool_executor.get_active_executions()
        assert len(active) == 1
        assert active[0].tool_name == "test_tool"
        assert active[0].status == ToolStatus.RUNNING

        # Wait for completion
        await task

        # Should be no active executions
        active = tool_executor.get_active_executions()
        assert len(active) == 0

    @pytest.mark.unit
    async def test_cancel_execution(self, tool_executor, sample_tool_definition):
        """Test execution cancellation."""

        async def slow_function(**_kwargs):
            await asyncio.sleep(1)
            return {"result": "done"}

        tool_executor.registry.register_tool(sample_tool_definition, slow_function)

        # Start execution
        task = asyncio.create_task(
            tool_executor.execute_tool("test_tool", {"input_text": "hello"})
        )

        # Give it a moment to start
        await asyncio.sleep(0.01)

        # Get execution ID
        active = tool_executor.get_active_executions()
        assert len(active) == 1
        execution_id = active[0].execution_id

        # Cancel execution
        success = tool_executor.cancel_execution(execution_id)
        assert success is True

        # Wait for task to complete
        execution = await task

        # Should be cancelled
        assert execution.status == ToolStatus.CANCELLED
        assert "cancelled" in execution.error.lower()


# ============================================================================
# Conversion Tool System Tests
# ============================================================================


class TestConversionToolSystem:
    """Test the ConversionToolSystem class."""

    @pytest.mark.unit
    async def test_system_initialization(self, conversion_tool_system):
        """Test conversion tool system initialization."""
        assert conversion_tool_system.conversion_service is not None
        assert conversion_tool_system.registry is not None
        assert conversion_tool_system.executor is not None

        # Check that conversion tools are registered
        tools = conversion_tool_system.registry.list_tools()
        assert len(tools) == 4  # Expected number of conversion tools

        tool_names = {tool.name for tool in tools}
        expected_tools = {
            "dataset_analysis",
            "conversion_orchestration",
            "evaluate_nwb_file",
            "run_full_pipeline",
        }
        assert tool_names == expected_tools

    @pytest.mark.unit
    async def test_dataset_analysis_tool(self, conversion_tool_system, temp_dataset):
        """Test dataset analysis tool execution."""
        execution = await conversion_tool_system.executor.execute_tool(
            "dataset_analysis",
            {
                "dataset_dir": temp_dataset,
                "use_llm": False,
                "session_id": "test_dataset_analysis",
            },
        )

        assert execution.status == ToolStatus.COMPLETED
        assert execution.result is not None
        assert execution.result["status"] == "completed"
        assert "data" in execution.result

        # Check analysis data structure
        analysis_data = execution.result["data"]
        assert "analysis_type" in analysis_data
        assert "dataset_path" in analysis_data
        assert "metadata_extracted" in analysis_data

    @pytest.mark.unit
    async def test_conversion_orchestration_tool(self, conversion_tool_system):
        """Test conversion orchestration tool execution."""
        execution = await conversion_tool_system.executor.execute_tool(
            "conversion_orchestration",
            {
                "normalized_metadata": {"subject_id": "test_subject"},
                "files_map": {"ephys": "/test/data.bin"},
                "session_id": "test_conversion",
            },
        )

        assert execution.status == ToolStatus.COMPLETED
        assert execution.result is not None
        assert execution.result["status"] == "completed"
        assert "data" in execution.result

        # Check conversion data structure
        conversion_data = execution.result["data"]
        assert "conversion_type" in conversion_data
        assert "script_generated" in conversion_data

    @pytest.mark.unit
    async def test_evaluate_nwb_tool(self, conversion_tool_system):
        """Test NWB evaluation tool execution."""
        # Create temporary NWB file
        with tempfile.NamedTemporaryFile(suffix=".nwb", delete=False) as temp_file:
            temp_file.write(b"dummy nwb content")
            temp_nwb_path = temp_file.name

        try:
            execution = await conversion_tool_system.executor.execute_tool(
                "evaluate_nwb_file",
                {
                    "nwb_path": temp_nwb_path,
                    "generate_report": True,
                    "session_id": "test_evaluation",
                },
            )

            assert execution.status == ToolStatus.COMPLETED
            assert execution.result is not None
            assert execution.result["status"] == "completed"
            assert "data" in execution.result

            # Check evaluation data structure
            evaluation_data = execution.result["data"]
            assert "evaluation_type" in evaluation_data
            assert "nwb_file_path" in evaluation_data

        finally:
            Path(temp_nwb_path).unlink(missing_ok=True)

    @pytest.mark.unit
    async def test_full_pipeline_tool(self, conversion_tool_system, temp_dataset):
        """Test full pipeline tool execution."""
        execution = await conversion_tool_system.executor.execute_tool(
            "run_full_pipeline",
            {
                "dataset_dir": temp_dataset,
                "use_llm": False,
                "session_id": "test_pipeline",
            },
        )

        assert execution.status == ToolStatus.COMPLETED
        assert execution.result is not None
        assert execution.result["status"] == "running"  # Pipeline starts async
        assert "data" in execution.result

        # Check pipeline data structure
        pipeline_data = execution.result["data"]
        assert "task_id" in pipeline_data

    @pytest.mark.unit
    async def test_tool_categories(self, conversion_tool_system):
        """Test that tools are properly categorized."""
        tools = conversion_tool_system.registry.list_tools()

        # Check categories
        categories = {tool.category for tool in tools}
        expected_categories = {
            ToolCategory.ANALYSIS,
            ToolCategory.CONVERSION,
            ToolCategory.EVALUATION,
            ToolCategory.PIPELINE,
        }
        assert categories == expected_categories

        # Check specific tool categories
        analysis_tools = conversion_tool_system.registry.list_tools(
            category=ToolCategory.ANALYSIS
        )
        assert len(analysis_tools) == 1
        assert analysis_tools[0].name == "dataset_analysis"

        conversion_tools = conversion_tool_system.registry.list_tools(
            category=ToolCategory.CONVERSION
        )
        assert len(conversion_tools) == 1
        assert conversion_tools[0].name == "conversion_orchestration"

    @pytest.mark.unit
    async def test_tool_parameter_validation(self, conversion_tool_system):
        """Test parameter validation for conversion tools."""
        # Test missing required parameter
        with pytest.raises(ValidationError):
            await conversion_tool_system.executor.execute_tool(
                "dataset_analysis",
                {},  # Missing required dataset_dir
            )

        # Test invalid parameter type
        with pytest.raises(ValidationError):
            await conversion_tool_system.executor.execute_tool(
                "dataset_analysis",
                {
                    "dataset_dir": "/test/path",
                    "use_llm": "not_a_boolean",  # Should be boolean
                },
            )

    @pytest.mark.unit
    async def test_tool_metrics_tracking(self, conversion_tool_system, temp_dataset):
        """Test that tool metrics are properly tracked."""
        # Execute a tool
        await conversion_tool_system.executor.execute_tool(
            "dataset_analysis",
            {
                "dataset_dir": temp_dataset,
                "use_llm": False,
                "session_id": "metrics_test",
            },
        )

        # Check metrics
        metrics = conversion_tool_system.registry.get_tool_metrics("dataset_analysis")
        assert metrics is not None
        assert metrics.total_executions > 0
        assert metrics.successful_executions > 0
        assert metrics.success_rate > 0
        assert metrics.average_execution_time > 0


# ============================================================================
# Data Model Tests
# ============================================================================


class TestToolDataModels:
    """Test tool system data models."""

    @pytest.mark.unit
    def test_tool_parameter_validation(self):
        """Test ToolParameter validation."""
        # Valid parameter
        param = ToolParameter(
            name="test_param",
            type=ParameterType.STRING,
            description="Test parameter",
            required=True,
        )

        assert param.name == "test_param"
        assert param.type == ParameterType.STRING
        assert param.required is True

        # Invalid parameter name
        with pytest.raises(ValueError):
            ToolParameter(
                name="invalid-name!",  # Contains invalid characters
                type=ParameterType.STRING,
                description="Test",
            )

    @pytest.mark.unit
    def test_tool_definition_validation(self):
        """Test ToolDefinition validation."""
        # Valid definition
        definition = ToolDefinition(
            name="valid_tool",
            description="A valid tool",
            category=ToolCategory.UTILITY,
            parameters=[],
            returns="Test result",
        )

        assert definition.name == "valid_tool"
        assert definition.category == ToolCategory.UTILITY
        assert definition.timeout_seconds == 300  # Default value

        # Invalid tool name
        with pytest.raises(ValueError):
            ToolDefinition(
                name="invalid tool name!",  # Contains spaces and special chars
                description="Test",
                category=ToolCategory.UTILITY,
                parameters=[],
                returns="Test",
            )

    @pytest.mark.unit
    def test_tool_execution_properties(self):
        """Test ToolExecution properties and calculations."""
        start_time = datetime.now(timezone.utc)
        execution = ToolExecution(
            tool_name="test_tool", parameters={"test": "value"}, start_time=start_time
        )

        # Test initial state
        assert execution.status == ToolStatus.PENDING
        assert execution.duration is None  # No end time yet

        # Set end time and execution time
        end_time = datetime.now(timezone.utc)
        execution.end_time = end_time
        execution.execution_time = 1.5

        # Test duration calculation
        duration = execution.duration
        assert duration is not None
        assert duration > 0

    @pytest.mark.unit
    def test_tool_metrics_calculations(self):
        """Test ToolMetrics calculations."""
        metrics = ToolMetrics(tool_name="test_tool")

        # Initial state
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 0.0

        # Add some executions
        metrics.total_executions = 10
        metrics.successful_executions = 8
        metrics.failed_executions = 2

        # Test calculations
        assert metrics.success_rate == 0.8
        assert metrics.failure_rate == 0.2


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
