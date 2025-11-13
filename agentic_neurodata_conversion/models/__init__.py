"""
Pydantic models for the agentic neurodata conversion system.
"""

from .api import (
    ChatResponse,
    DownloadInfo,
    ErrorResponse,
    HealthResponse,
    ImprovementDecisionResponse,
    LogsResponse,
    ResetResponse,
    RetryApprovalRequest,
    RetryApprovalResponse,
    StartConversionResponse,
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
    ConversationPhase,
    ConversionStatus,
    GlobalState,
    LogEntry,
    LogLevel,
    MetadataProvenance,
    MetadataRequestPolicy,
    ProvenanceInfo,
    ValidationOutcome,
    ValidationStatus,
)
from .validation import CorrectionContext, ValidationIssue, ValidationResult, ValidationSeverity

__all__ = [
    # API models
    "ChatResponse",
    "DownloadInfo",
    "ErrorResponse",
    "HealthResponse",
    "ImprovementDecisionResponse",
    "LogsResponse",
    "ResetResponse",
    "RetryApprovalRequest",
    "RetryApprovalResponse",
    "StartConversionResponse",
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
    "MetadataProvenance",
    "ProvenanceInfo",
    # Validation models
    "CorrectionContext",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
]
