"""Status router for conversion status, logs, and metadata provenance endpoints.

Handles:
- Current conversion status and progress
- Log retrieval with pagination
- Metadata provenance tracking for scientific transparency
"""

import logging

from fastapi import APIRouter

from agentic_neurodata_conversion.api.dependencies import get_or_create_mcp_server
from agentic_neurodata_conversion.models import (
    LogsResponse,
    StatusResponse,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current conversion status.

    Returns detailed information about the current conversion state including:
    - Conversion status (idle, converting, completed, failed, etc.)
    - Validation status and overall outcome
    - Progress percentage and stage
    - LLM conversational messages
    - File paths (input/output)
    - Retry information

    Returns:
        Current status and progress
    """
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    return StatusResponse(
        status=state.status,
        validation_status=state.validation_status,
        overall_status=state.overall_status,
        progress=state.progress_percent,
        progress_message=state.progress_message,
        current_stage=state.current_stage,
        message=state.llm_message,
        input_path=state.input_path,
        output_path=state.output_path,
        correction_attempt=state.correction_attempt,
        can_retry=mcp_server.global_state.can_retry,
        conversation_type=state.conversation_type,
    )


@router.get("/metadata-provenance")
async def get_metadata_provenance():
    """Get metadata provenance information for all fields.

    Provides complete audit trail showing source, confidence, and reliability
    of each metadata field for scientific transparency and DANDI compliance.

    Provenance types include:
    - USER_PROVIDED: Directly provided by user
    - AI_PARSED: Extracted by AI from user input
    - AUTO_EXTRACTED: Automatically extracted from file
    - FILENAME_INFERRED: Inferred from filename patterns
    - AUTO_CORRECTED: Automatically corrected from validation
    - SYSTEM_DEFAULT: System default value

    Returns:
        Dictionary with:
        - provenance: Field names mapped to provenance information
        - total_fields: Total number of tracked fields
        - needs_review_count: Number of fields requiring review
    """
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # Convert ProvenanceInfo objects to dict for JSON serialization
    provenance_data = {}
    for field_name, prov_info in state.metadata_provenance.items():
        provenance_data[field_name] = {
            "value": prov_info.value,
            "provenance": prov_info.provenance.value,
            "confidence": prov_info.confidence,
            "source": prov_info.source,
            "timestamp": prov_info.timestamp.isoformat(),
            "needs_review": prov_info.needs_review,
            "raw_input": prov_info.raw_input,
            "badge": prov_info.badge,
            "historical_evidence": prov_info.historical_evidence,
        }

    return {
        "provenance": provenance_data,
        "total_fields": len(provenance_data),
        "needs_review_count": sum(1 for p in state.metadata_provenance.values() if p.needs_review),
    }


@router.get("/logs", response_model=LogsResponse)
async def get_logs(limit: int = 100, offset: int = 0):
    """Get conversion logs with pagination.

    Retrieves structured log entries from the current conversion session.
    Logs include detailed information about each step of the conversion process,
    including debug info, warnings, errors, and progress updates.

    Args:
        limit: Maximum number of logs to return (default: 100)
        offset: Offset for pagination (default: 0)

    Returns:
        LogsResponse containing:
        - logs: List of log entries with level, message, timestamp, and context
        - total_count: Total number of available logs
    """
    mcp_server = get_or_create_mcp_server()
    logs = mcp_server.global_state.logs

    total = len(logs)
    paginated_logs = logs[offset : offset + limit]

    return LogsResponse(
        logs=[log.model_dump() for log in paginated_logs],
        total_count=total,
    )


@router.post("/track-conflict-resolution")
async def track_conflict_resolution(resolution_data: dict):
    """Track when user resolves a metadata conflict (Phase 2 Task 2.3).

    Updates inference metrics to track conflict resolution outcomes.
    Helps measure the effectiveness of historical inference and user preferences.

    Args:
        resolution_data: Dictionary containing:
            - field_name (str): Name of the conflicting field
            - selected_type (str): 'llm', 'kg', or 'custom'
            - selected_value (str): The value user chose
            - llm_value (str): LLM-suggested value
            - kg_value (str): Historical data suggested value

    Returns:
        Success message with updated metrics
    """
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    field_name = resolution_data.get("field_name")
    selected_type = resolution_data.get("selected_type")
    selected_value = resolution_data.get("selected_value")

    # Increment conflict resolution counter
    state.inference_metrics["user_resolved_conflict"] += 1

    # Log resolution for debugging
    logger.info(f"Conflict resolved for {field_name}: user selected {selected_type} = '{selected_value}'")

    return {
        "status": "success",
        "message": f"Conflict resolution tracked for {field_name}",
        "metrics": {
            "total_resolved": state.inference_metrics["user_resolved_conflict"],
            "total_conflicts": state.inference_metrics["conflicting_count"],
        },
    }
