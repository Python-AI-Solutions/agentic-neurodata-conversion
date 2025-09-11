# Copyright (c) 2025 Agentic Neurodata Conversion Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tool registry and execution system for agentic neurodata conversion.

This module provides a transport-agnostic tool registry and execution system that can be
used by different transport adapters (MCP, HTTP, etc.) to expose conversion functionality
as callable tools with metadata, validation, and execution tracking.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
import inspect
import logging
import time
from typing import TYPE_CHECKING, Any, Callable
import uuid

from pydantic import BaseModel, Field, field_validator

from .exceptions import ValidationError

if TYPE_CHECKING:
    from .service import ConversionService

# ============================================================================
# Tool System Data Models
# ============================================================================


class ToolCategory(str, Enum):
    """Categories for organizing tools."""

    ANALYSIS = "analysis"
    CONVERSION = "conversion"
    EVALUATION = "evaluation"
    PIPELINE = "pipeline"
    UTILITY = "utility"


class ToolStatus(str, Enum):
    """Status enumeration for tool execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ParameterType(str, Enum):
    """Parameter types for tool definitions."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class ToolParameter(BaseModel):
    """Tool parameter definition."""

    name: str = Field(..., description="Parameter name")
    type: ParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Any | None = Field(None, description="Default value if not required")
    enum: list[Any] | None = Field(
        None, description="Allowed values for enum parameters"
    )
    minimum: int | float | None = Field(
        None, description="Minimum value for numeric parameters"
    )
    maximum: int | float | None = Field(
        None, description="Maximum value for numeric parameters"
    )
    pattern: str | None = Field(None, description="Regex pattern for string parameters")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate parameter name format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Parameter name must be alphanumeric with underscores or hyphens"
            )
        return v


class ToolDefinition(BaseModel):
    """Complete tool definition with metadata."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    category: ToolCategory = Field(..., description="Tool category")
    parameters: list[ToolParameter] = Field(
        default_factory=list, description="Tool parameters"
    )
    returns: str = Field(..., description="Description of what the tool returns")
    examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Usage examples"
    )
    tags: list[str] = Field(default_factory=list, description="Tool tags for discovery")
    version: str = Field(default="1.0.0", description="Tool version")
    timeout_seconds: int = Field(
        default=300, ge=1, description="Execution timeout in seconds"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Tool name must be alphanumeric with underscores or hyphens"
            )
        return v


class ToolExecution(BaseModel):
    """Tool execution tracking and results."""

    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = Field(..., description="Name of executed tool")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Execution parameters"
    )
    status: ToolStatus = Field(default=ToolStatus.PENDING)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = Field(None)
    execution_time: float | None = Field(None, description="Execution time in seconds")
    result: dict[str, Any] | None = Field(None, description="Execution result")
    error: str | None = Field(None, description="Error message if failed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Execution metadata"
    )

    @property
    def duration(self) -> float | None:
        """Calculate execution duration."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ToolMetrics(BaseModel):
    """Tool performance metrics and statistics."""

    tool_name: str = Field(..., description="Tool name")
    total_executions: int = Field(default=0)
    successful_executions: int = Field(default=0)
    failed_executions: int = Field(default=0)
    timeout_executions: int = Field(default=0)
    cancelled_executions: int = Field(default=0)
    average_execution_time: float = Field(default=0.0)
    min_execution_time: float | None = Field(None)
    max_execution_time: float | None = Field(None)
    last_execution: datetime | None = Field(None)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_executions == 0:
            return 0.0
        return self.failed_executions / self.total_executions

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Tool Registry and Execution System
# ============================================================================


class ToolRegistry:
    """Registry for managing tool definitions and metadata."""

    def __init__(self):
        """Initialize tool registry."""
        self.tools: dict[str, ToolDefinition] = {}
        self.tool_functions: dict[str, Callable] = {}
        self.metrics: dict[str, ToolMetrics] = {}
        self.logger = logging.getLogger(__name__)

    def register_tool(self, definition: ToolDefinition, function: Callable) -> None:
        """Register a tool with its definition and implementation.

        Args:
            definition: Tool definition with metadata
            function: Callable function that implements the tool

        Raises:
            ValidationError: If tool definition is invalid
        """
        # Validate function signature matches parameters (skip for **kwargs functions)
        sig = inspect.signature(function)
        function_params = set(sig.parameters.keys())

        # Remove 'self' parameter if present (for methods)
        if "self" in function_params:
            function_params.remove("self")

        # Skip validation if function uses **kwargs (flexible parameter handling)
        has_var_keyword = any(
            param.kind == param.VAR_KEYWORD for param in sig.parameters.values()
        )

        if not has_var_keyword:
            required_params = {p.name for p in definition.parameters if p.required}
            missing_params = required_params - function_params
            if missing_params:
                raise ValidationError(
                    f"Function missing required parameters: {missing_params}",
                    validation_type="function_signature",
                    field_name="parameters",
                )

        self.tools[definition.name] = definition
        self.tool_functions[definition.name] = function
        self.metrics[definition.name] = ToolMetrics(tool_name=definition.name)

        self.logger.info(
            f"Registered tool: {definition.name} ({definition.category.value})"
        )

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Get tool definition by name.

        Args:
            name: Tool name

        Returns:
            Tool definition or None if not found
        """
        return self.tools.get(name)

    def list_tools(
        self, category: ToolCategory | None = None, tags: list[str] | None = None
    ) -> list[ToolDefinition]:
        """List tools with optional filtering.

        Args:
            category: Filter by category
            tags: Filter by tags (tool must have all specified tags)

        Returns:
            List of matching tool definitions
        """
        tools = list(self.tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if tags:
            tools = [t for t in tools if all(tag in t.tags for tag in tags)]

        return tools

    def search_tools(self, query: str) -> list[ToolDefinition]:
        """Search tools by name, description, or tags.

        Args:
            query: Search query

        Returns:
            List of matching tool definitions
        """
        query_lower = query.lower()
        matches = []

        for tool in self.tools.values():
            if (
                query_lower in tool.name.lower()
                or query_lower in tool.description.lower()
                or any(query_lower in tag.lower() for tag in tool.tags)
            ):
                matches.append(tool)

        return matches

    def get_tool_metrics(self, name: str) -> ToolMetrics | None:
        """Get performance metrics for a tool.

        Args:
            name: Tool name

        Returns:
            Tool metrics or None if not found
        """
        return self.metrics.get(name)

    def get_all_metrics(self) -> dict[str, ToolMetrics]:
        """Get metrics for all tools.

        Returns:
            Dictionary mapping tool names to metrics
        """
        return self.metrics.copy()

    def update_metrics(self, execution: ToolExecution) -> None:
        """Update tool metrics based on execution result.

        Args:
            execution: Completed tool execution
        """
        metrics = self.metrics.get(execution.tool_name)
        if not metrics:
            return

        metrics.total_executions += 1
        metrics.last_execution = execution.end_time or datetime.now(timezone.utc)

        if execution.status == ToolStatus.COMPLETED:
            metrics.successful_executions += 1
        elif execution.status == ToolStatus.FAILED:
            metrics.failed_executions += 1
        elif execution.status == ToolStatus.TIMEOUT:
            metrics.timeout_executions += 1
        elif execution.status == ToolStatus.CANCELLED:
            metrics.cancelled_executions += 1

        # Update execution time statistics
        if execution.execution_time is not None:
            if (
                metrics.min_execution_time is None
                or execution.execution_time < metrics.min_execution_time
            ):
                metrics.min_execution_time = execution.execution_time

            if (
                metrics.max_execution_time is None
                or execution.execution_time > metrics.max_execution_time
            ):
                metrics.max_execution_time = execution.execution_time

            # Update average (simple moving average)
            total_time = metrics.average_execution_time * (metrics.total_executions - 1)
            metrics.average_execution_time = (
                total_time + execution.execution_time
            ) / metrics.total_executions


class ToolExecutor:
    """Executes tools with timeout, error handling, and result processing."""

    def __init__(self, registry: ToolRegistry):
        """Initialize tool executor.

        Args:
            registry: Tool registry instance
        """
        self.registry = registry
        self.active_executions: dict[str, ToolExecution] = {}
        self.logger = logging.getLogger(__name__)

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        execution_id: str | None = None,
    ) -> ToolExecution:
        """Execute a tool with the given parameters.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            execution_id: Optional execution ID (generated if not provided)

        Returns:
            Tool execution result

        Raises:
            ValidationError: If tool not found or parameters invalid
        """
        # Get tool definition and function
        tool_def = self.registry.get_tool(tool_name)
        if not tool_def:
            raise ValidationError(
                f"Tool not found: {tool_name}",
                validation_type="tool_lookup",
                field_name="tool_name",
            )

        tool_func = self.registry.tool_functions.get(tool_name)
        if not tool_func:
            raise ValidationError(
                f"Tool function not found: {tool_name}",
                validation_type="function_lookup",
                field_name="tool_name",
            )

        # Create execution tracking
        execution = ToolExecution(
            execution_id=execution_id or str(uuid.uuid4()),
            tool_name=tool_name,
            parameters=parameters,
            status=ToolStatus.PENDING,
        )

        self.active_executions[execution.execution_id] = execution

        try:
            # Validate parameters
            self._validate_parameters(tool_def, parameters)

            # Execute tool with timeout
            execution.status = ToolStatus.RUNNING
            start_time = time.time()

            result = await self._execute_with_timeout(
                tool_func, parameters, tool_def.timeout_seconds
            )

            end_time = time.time()
            execution.execution_time = end_time - start_time
            execution.end_time = datetime.now(timezone.utc)
            execution.result = result
            execution.status = ToolStatus.COMPLETED

            self.logger.info(
                f"Tool {tool_name} executed successfully in {execution.execution_time:.3f}s"
            )

        except asyncio.TimeoutError:
            execution.status = ToolStatus.TIMEOUT
            execution.end_time = datetime.now(timezone.utc)
            execution.error = (
                f"Tool execution timed out after {tool_def.timeout_seconds} seconds"
            )
            self.logger.warning(f"Tool {tool_name} timed out")

        except Exception as e:
            execution.status = ToolStatus.FAILED
            execution.end_time = datetime.now(timezone.utc)
            execution.error = str(e)
            self.logger.error(f"Tool {tool_name} failed: {e}")

        finally:
            # Update metrics and cleanup
            self.registry.update_metrics(execution)
            self.active_executions.pop(execution.execution_id, None)

        return execution

    def _validate_parameters(
        self, tool_def: ToolDefinition, parameters: dict[str, Any]
    ) -> None:
        """Validate tool parameters against definition.

        Args:
            tool_def: Tool definition
            parameters: Parameters to validate

        Raises:
            ValidationError: If parameters are invalid
        """
        # Check required parameters
        required_params = {p.name for p in tool_def.parameters if p.required}
        provided_params = set(parameters.keys())

        missing_params = required_params - provided_params
        if missing_params:
            raise ValidationError(
                f"Missing required parameters: {missing_params}",
                validation_type="parameter_validation",
                field_name="parameters",
            )

        # Validate parameter types and constraints
        for param_def in tool_def.parameters:
            if param_def.name not in parameters:
                continue

            value = parameters[param_def.name]
            self._validate_parameter_value(param_def, value)

    def _validate_parameter_value(self, param_def: ToolParameter, value: Any) -> None:
        """Validate a single parameter value.

        Args:
            param_def: Parameter definition
            value: Value to validate

        Raises:
            ValidationError: If value is invalid
        """
        # Type validation
        if param_def.type == ParameterType.STRING and not isinstance(value, str):
            raise ValidationError(
                f"Parameter {param_def.name} must be a string",
                validation_type="parameter_type",
                field_name=param_def.name,
            )
        elif param_def.type == ParameterType.INTEGER and not isinstance(value, int):
            raise ValidationError(
                f"Parameter {param_def.name} must be an integer",
                validation_type="parameter_type",
                field_name=param_def.name,
            )
        elif param_def.type == ParameterType.NUMBER and not isinstance(
            value, (int, float)
        ):
            raise ValidationError(
                f"Parameter {param_def.name} must be a number",
                validation_type="parameter_type",
                field_name=param_def.name,
            )
        elif param_def.type == ParameterType.BOOLEAN and not isinstance(value, bool):
            raise ValidationError(
                f"Parameter {param_def.name} must be a boolean",
                validation_type="parameter_type",
                field_name=param_def.name,
            )

        # Enum validation
        if param_def.enum and value not in param_def.enum:
            raise ValidationError(
                f"Parameter {param_def.name} must be one of: {param_def.enum}",
                validation_type="parameter_enum",
                field_name=param_def.name,
            )

        # Numeric range validation
        if param_def.type in [ParameterType.INTEGER, ParameterType.NUMBER]:
            if param_def.minimum is not None and value < param_def.minimum:
                raise ValidationError(
                    f"Parameter {param_def.name} must be >= {param_def.minimum}",
                    validation_type="parameter_range",
                    field_name=param_def.name,
                )
            if param_def.maximum is not None and value > param_def.maximum:
                raise ValidationError(
                    f"Parameter {param_def.name} must be <= {param_def.maximum}",
                    validation_type="parameter_range",
                    field_name=param_def.name,
                )

        # String pattern validation
        if param_def.type == ParameterType.STRING and param_def.pattern:
            import re

            if not re.match(param_def.pattern, value):
                raise ValidationError(
                    f"Parameter {param_def.name} must match pattern: {param_def.pattern}",
                    validation_type="parameter_pattern",
                    field_name=param_def.name,
                )

    async def _execute_with_timeout(
        self, func: Callable, parameters: dict[str, Any], timeout_seconds: int
    ) -> dict[str, Any]:
        """Execute function with timeout.

        Args:
            func: Function to execute
            parameters: Function parameters
            timeout_seconds: Timeout in seconds

        Returns:
            Function result

        Raises:
            asyncio.TimeoutError: If execution times out
        """
        if asyncio.iscoroutinefunction(func):
            return await asyncio.wait_for(func(**parameters), timeout=timeout_seconds)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: func(**parameters)),
                timeout=timeout_seconds,
            )

    def get_active_executions(self) -> list[ToolExecution]:
        """Get list of currently active executions.

        Returns:
            List of active tool executions
        """
        return list(self.active_executions.values())

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an active execution.

        Args:
            execution_id: Execution ID to cancel

        Returns:
            True if execution was cancelled, False if not found
        """
        execution = self.active_executions.get(execution_id)
        if not execution:
            return False

        execution.status = ToolStatus.CANCELLED
        execution.end_time = datetime.now(timezone.utc)
        execution.error = "Execution cancelled by user request"

        # Update metrics and cleanup
        self.registry.update_metrics(execution)
        self.active_executions.pop(execution_id, None)

        self.logger.info(f"Cancelled execution {execution_id}")
        return True


# ============================================================================
# Tool System Integration
# ============================================================================


class ConversionToolSystem:
    """Integration layer that registers conversion tools with the tool system."""

    def __init__(self, conversion_service: ConversionService):
        """Initialize conversion tool system.

        Args:
            conversion_service: Core conversion service instance
        """
        self.conversion_service = conversion_service
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry)
        self.logger = logging.getLogger(__name__)

        # Register conversion tools
        self._register_conversion_tools()

    def _register_conversion_tools(self) -> None:
        """Register all conversion tools with the registry."""

        # Dataset Analysis Tool
        dataset_analysis_def = ToolDefinition(
            name="dataset_analysis",
            description="Analyze dataset structure and extract metadata for NWB conversion",
            category=ToolCategory.ANALYSIS,
            parameters=[
                ToolParameter(
                    name="dataset_dir",
                    type=ParameterType.STRING,
                    description="Path to dataset directory to analyze",
                    required=True,
                ),
                ToolParameter(
                    name="use_llm",
                    type=ParameterType.BOOLEAN,
                    description="Whether to use LLM for metadata extraction",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="session_id",
                    type=ParameterType.STRING,
                    description="Optional session ID for tracking",
                    required=False,
                ),
            ],
            returns="Analysis results including detected formats, metadata, and file information",
            examples=[{"dataset_dir": "/path/to/dataset", "use_llm": False}],
            tags=["analysis", "metadata", "dataset"],
            timeout_seconds=300,
        )

        self.registry.register_tool(
            dataset_analysis_def, self._dataset_analysis_wrapper
        )

        # Conversion Orchestration Tool
        conversion_def = ToolDefinition(
            name="conversion_orchestration",
            description="Generate and execute NeuroConv conversion script",
            category=ToolCategory.CONVERSION,
            parameters=[
                ToolParameter(
                    name="normalized_metadata",
                    type=ParameterType.OBJECT,
                    description="Normalized metadata from dataset analysis",
                    required=True,
                ),
                ToolParameter(
                    name="files_map",
                    type=ParameterType.OBJECT,
                    description="Mapping of file types to paths",
                    required=True,
                ),
                ToolParameter(
                    name="output_nwb_path",
                    type=ParameterType.STRING,
                    description="Output path for NWB file",
                    required=False,
                ),
                ToolParameter(
                    name="session_id",
                    type=ParameterType.STRING,
                    description="Optional session ID for tracking",
                    required=False,
                ),
            ],
            returns="Conversion results including output file path and processing information",
            examples=[
                {
                    "normalized_metadata": {"subject_id": "test"},
                    "files_map": {"ephys": "/path/to/data.bin"},
                }
            ],
            tags=["conversion", "neuroconv", "nwb"],
            timeout_seconds=600,
        )

        self.registry.register_tool(
            conversion_def, self._conversion_orchestration_wrapper
        )

        # NWB Evaluation Tool
        evaluation_def = ToolDefinition(
            name="evaluate_nwb_file",
            description="Evaluate NWB file quality and generate validation reports",
            category=ToolCategory.EVALUATION,
            parameters=[
                ToolParameter(
                    name="nwb_path",
                    type=ParameterType.STRING,
                    description="Path to NWB file to evaluate",
                    required=True,
                ),
                ToolParameter(
                    name="generate_report",
                    type=ParameterType.BOOLEAN,
                    description="Whether to generate detailed evaluation report",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="include_visualizations",
                    type=ParameterType.BOOLEAN,
                    description="Whether to include visualizations in report",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="session_id",
                    type=ParameterType.STRING,
                    description="Optional session ID for tracking",
                    required=False,
                ),
            ],
            returns="Evaluation results including validation status, quality metrics, and report paths",
            examples=[{"nwb_path": "/path/to/output.nwb", "generate_report": True}],
            tags=["evaluation", "validation", "nwb", "quality"],
            timeout_seconds=300,
        )

        self.registry.register_tool(evaluation_def, self._evaluate_nwb_wrapper)

        # Full Pipeline Tool
        pipeline_def = ToolDefinition(
            name="run_full_pipeline",
            description="Execute complete conversion pipeline from analysis to evaluation",
            category=ToolCategory.PIPELINE,
            parameters=[
                ToolParameter(
                    name="dataset_dir",
                    type=ParameterType.STRING,
                    description="Path to dataset directory",
                    required=True,
                ),
                ToolParameter(
                    name="files_map",
                    type=ParameterType.OBJECT,
                    description="Optional mapping of file types to paths",
                    required=False,
                ),
                ToolParameter(
                    name="use_llm",
                    type=ParameterType.BOOLEAN,
                    description="Whether to use LLM for metadata extraction",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="output_nwb_path",
                    type=ParameterType.STRING,
                    description="Optional output path for NWB file",
                    required=False,
                ),
                ToolParameter(
                    name="session_id",
                    type=ParameterType.STRING,
                    description="Optional session ID for tracking",
                    required=False,
                ),
            ],
            returns="Pipeline execution status and task ID for monitoring progress",
            examples=[{"dataset_dir": "/path/to/dataset", "use_llm": False}],
            tags=["pipeline", "workflow", "conversion", "end-to-end"],
            timeout_seconds=1800,  # 30 minutes for full pipeline
        )

        self.registry.register_tool(pipeline_def, self._run_full_pipeline_wrapper)

        self.logger.info("Registered 4 conversion tools with tool system")

    async def _dataset_analysis_wrapper(self, **kwargs) -> dict[str, Any]:
        """Wrapper for dataset analysis tool."""
        response = await self.conversion_service.dataset_analysis(**kwargs)
        return {
            "status": response.status.value,
            "data": response.data,
            "session_id": response.session_id,
            "execution_time": response.execution_time,
            "warnings": response.warnings,
            "error": response.error,
        }

    async def _conversion_orchestration_wrapper(self, **kwargs) -> dict[str, Any]:
        """Wrapper for conversion orchestration tool."""
        response = await self.conversion_service.conversion_orchestration(**kwargs)
        return {
            "status": response.status.value,
            "data": response.data,
            "session_id": response.session_id,
            "execution_time": response.execution_time,
            "warnings": response.warnings,
            "error": response.error,
        }

    async def _evaluate_nwb_wrapper(self, **kwargs) -> dict[str, Any]:
        """Wrapper for NWB evaluation tool."""
        response = await self.conversion_service.evaluate_nwb_file(**kwargs)
        return {
            "status": response.status.value,
            "data": response.data,
            "session_id": response.session_id,
            "execution_time": response.execution_time,
            "warnings": response.warnings,
            "error": response.error,
        }

    async def _run_full_pipeline_wrapper(self, **kwargs) -> dict[str, Any]:
        """Wrapper for full pipeline tool."""
        from .service import ConversionRequest

        # Create conversion request
        request = ConversionRequest(**kwargs)
        response = await self.conversion_service.run_full_pipeline(request)

        return {
            "status": response.status.value,
            "data": response.data,
            "session_id": response.session_id,
            "execution_time": response.execution_time,
            "warnings": response.warnings,
            "error": response.error,
        }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "ToolCategory",
    "ToolStatus",
    "ParameterType",
    # Data Models
    "ToolParameter",
    "ToolDefinition",
    "ToolExecution",
    "ToolMetrics",
    # Core Classes
    "ToolRegistry",
    "ToolExecutor",
    "ConversionToolSystem",
]
