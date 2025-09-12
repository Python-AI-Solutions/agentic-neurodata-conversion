"""Custom exception classes for the agentic neurodata conversion system.

This module defines a hierarchy of custom exceptions that provide specific error handling
for different components of the system including MCP server, agents, validation, and conversion.
"""

from typing import Any, Optional


class AgenticConverterError(Exception):
    """Base exception class for all agentic converter errors.

    Provides common functionality for error tracking, context, and structured error information.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """Initialize base exception with enhanced error information.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for programmatic handling
            context: Additional context information about the error
            cause: Original exception that caused this error (if any)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for structured logging and API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        """String representation with error code if available."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigurationError(AgenticConverterError):
    """Raised when there are configuration-related errors.

    This includes invalid settings, missing required configuration,
    or configuration validation failures.
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None,
        **kwargs,
    ):
        """Initialize configuration error with specific config context.

        Args:
            message: Error message
            config_key: The configuration key that caused the error
            expected_type: Expected type/format for the configuration
            actual_value: The actual value that caused the error
        """
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        if expected_type:
            context["expected_type"] = expected_type
        if actual_value is not None:
            context["actual_value"] = str(actual_value)

        super().__init__(
            message,
            error_code=kwargs.get("error_code", "CONFIG_ERROR"),
            context=context,
            cause=kwargs.get("cause"),
        )


class ValidationError(AgenticConverterError):
    """Raised when data validation fails.

    This includes schema validation, data format validation,
    and business rule validation failures.
    """

    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None,
        **kwargs,
    ):
        """Initialize validation error with validation context.

        Args:
            message: Error message
            validation_type: Type of validation that failed (schema, format, etc.)
            field_name: Name of the field that failed validation
            invalid_value: The value that failed validation
        """
        context = kwargs.get("context", {})
        if validation_type:
            context["validation_type"] = validation_type
        if field_name:
            context["field_name"] = field_name
        if invalid_value is not None:
            context["invalid_value"] = str(invalid_value)

        super().__init__(
            message,
            error_code=kwargs.get("error_code", "VALIDATION_ERROR"),
            context=context,
            cause=kwargs.get("cause"),
        )


class ConversionError(AgenticConverterError):
    """Raised when data conversion operations fail.

    This includes NeuroConv conversion failures, file format issues,
    and NWB file generation problems.
    """

    def __init__(
        self,
        message: str,
        conversion_stage: Optional[str] = None,
        source_format: Optional[str] = None,
        target_format: Optional[str] = None,
        file_path: Optional[str] = None,
        **kwargs,
    ):
        """Initialize conversion error with conversion context.

        Args:
            message: Error message
            conversion_stage: Stage of conversion where error occurred
            source_format: Source data format
            target_format: Target data format (usually NWB)
            file_path: Path to file being converted
        """
        context = kwargs.get("context", {})
        if conversion_stage:
            context["conversion_stage"] = conversion_stage
        if source_format:
            context["source_format"] = source_format
        if target_format:
            context["target_format"] = target_format
        if file_path:
            context["file_path"] = file_path

        super().__init__(
            message,
            error_code=kwargs.get("error_code", "CONVERSION_ERROR"),
            context=context,
            cause=kwargs.get("cause"),
        )


class AgentError(AgenticConverterError):
    """Raised when agent operations fail.

    This includes agent initialization, execution, and communication failures.
    """

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        agent_operation: Optional[str] = None,
        **kwargs,
    ):
        """Initialize agent error with agent context.

        Args:
            message: Error message
            agent_name: Name of the agent that failed
            agent_operation: Operation the agent was performing
        """
        context = kwargs.get("context", {})
        if agent_name:
            context["agent_name"] = agent_name
        if agent_operation:
            context["agent_operation"] = agent_operation

        super().__init__(
            message,
            error_code=kwargs.get("error_code", "AGENT_ERROR"),
            context=context,
            cause=kwargs.get("cause"),
        )


class MCPServerError(AgenticConverterError):
    """Raised when MCP server operations fail.

    This includes tool registration, execution, and server lifecycle errors.
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        server_operation: Optional[str] = None,
        **kwargs,
    ):
        """Initialize MCP server error with server context.

        Args:
            message: Error message
            tool_name: Name of the MCP tool that failed
            server_operation: Server operation that failed
        """
        context = kwargs.get("context", {})
        if tool_name:
            context["tool_name"] = tool_name
        if server_operation:
            context["server_operation"] = server_operation

        super().__init__(
            message,
            error_code=kwargs.get("error_code", "MCP_SERVER_ERROR"),
            context=context,
            cause=kwargs.get("cause"),
        )


class DataProcessingError(AgenticConverterError):
    """Raised when data processing operations fail.

    This includes file I/O errors, data parsing failures, and format detection issues.
    """

    def __init__(
        self,
        message: str,
        processing_stage: Optional[str] = None,
        file_path: Optional[str] = None,
        data_format: Optional[str] = None,
        **kwargs,
    ):
        """Initialize data processing error with processing context.

        Args:
            message: Error message
            processing_stage: Stage of processing where error occurred
            file_path: Path to file being processed
            data_format: Format of data being processed
        """
        context = kwargs.get("context", {})
        if processing_stage:
            context["processing_stage"] = processing_stage
        if file_path:
            context["file_path"] = file_path
        if data_format:
            context["data_format"] = data_format

        super().__init__(
            message,
            error_code=kwargs.get("error_code", "DATA_PROCESSING_ERROR"),
            context=context,
            cause=kwargs.get("cause"),
        )


class KnowledgeGraphError(AgenticConverterError):
    """Raised when knowledge graph operations fail.

    This includes RDF generation, SPARQL queries, and ontology validation errors.
    """

    def __init__(
        self,
        message: str,
        operation_type: Optional[str] = None,
        graph_format: Optional[str] = None,
        **kwargs,
    ):
        """Initialize knowledge graph error with graph context.

        Args:
            message: Error message
            operation_type: Type of graph operation that failed
            graph_format: RDF format being used
        """
        context = kwargs.get("context", {})
        if operation_type:
            context["operation_type"] = operation_type
        if graph_format:
            context["graph_format"] = graph_format

        super().__init__(
            message,
            error_code=kwargs.get("error_code", "KNOWLEDGE_GRAPH_ERROR"),
            context=context,
            cause=kwargs.get("cause"),
        )


# Exception hierarchy for easy catching
__all__ = [
    "AgenticConverterError",
    "ConfigurationError",
    "ValidationError",
    "ConversionError",
    "AgentError",
    "MCPServerError",
    "DataProcessingError",
    "KnowledgeGraphError",
]
