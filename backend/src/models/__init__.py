"""
Pydantic models for the agentic neurodata conversion system.
"""
from .api import (
    DownloadInfo,
    ErrorResponse,
    LogsResponse,
    RetryApprovalRequest,
    RetryApprovalResponse,
    StatusResponse,
    UploadResponse,
    UserDecision,
    UserInputRequest,
    UserInputResponse,
    ValidationResponse,
    WebSocketMessage,
)
from .mcp import MCPEvent, MCPMessage, MCPResponse
from .state import (
    ConversionStatus,
    GlobalState,
    LogEntry,
    LogLevel,
    ValidationStatus,
    ValidationOutcome,
    ConversationPhase,
    MetadataRequestPolicy,
)
from .validation import (
    CorrectionContext,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

__all__ = [
    # API models
    "DownloadInfo",
    "ErrorResponse",
    "LogsResponse",
    "RetryApprovalRequest",
    "RetryApprovalResponse",
    "StatusResponse",
    "UploadResponse",
    "UserDecision",
    "UserInputRequest",
    "UserInputResponse",
    "ValidationResponse",
    "WebSocketMessage",
    # MCP models
    "MCPEvent",
    "MCPMessage",
    "MCPResponse",
    # State models
    "ConversionStatus",
    "GlobalState",
    "LogEntry",
    "LogLevel",
    "ValidationStatus",
    "ValidationOutcome",
    "ConversationPhase",
    "MetadataRequestPolicy",
    # Validation models
    "CorrectionContext",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
]
