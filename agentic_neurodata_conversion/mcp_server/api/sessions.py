"""
Session REST API endpoints for conversion pipeline workflow.

This module provides endpoints for:
- Session initialization
- Status monitoring
- User clarification
- Result retrieval

All endpoints follow REST conventions and provide proper error handling.
"""

import logging
from pathlib import Path
import time
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException, Request

from agentic_neurodata_conversion.models import (
    DatasetInfo,
    SessionClarifyRequest,
    SessionClarifyResponse,
    SessionContext,
    SessionInitializeRequest,
    SessionInitializeResponse,
    SessionResultResponse,
    SessionStatusResponse,
    WorkflowStage,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sessions"])


def _validate_dataset_path(dataset_path: str) -> Path:
    """
    Validate that dataset path exists and is a directory.

    Args:
        dataset_path: Path to validate

    Returns:
        Validated Path object

    Raises:
        HTTPException: If path doesn't exist or is not a directory
    """
    path = Path(dataset_path)

    if not path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Dataset path not found: {dataset_path}",
        )

    if not path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Dataset path must be a directory: {dataset_path}",
        )

    return path


def _collect_dataset_info(dataset_path: Path) -> DatasetInfo:
    """
    Collect basic dataset information from filesystem.

    Args:
        dataset_path: Path to dataset directory

    Returns:
        DatasetInfo with collected information
    """
    # Count total files
    all_files = list(dataset_path.rglob("*"))
    file_count = len([f for f in all_files if f.is_file()])

    # Calculate total size
    total_size = sum(f.stat().st_size for f in all_files if f.is_file())

    # Look for metadata files
    metadata_files = list(dataset_path.rglob("*.md"))
    has_metadata_files = len(metadata_files) > 0
    metadata_file_paths = [str(f) for f in metadata_files]

    # Detect format (basic detection - look for OpenEphys markers)
    format_name = "unknown"
    if (dataset_path / "structure.oebin").exists():
        format_name = "openephys"
    elif any(f.suffix == ".nwb" for f in all_files):
        format_name = "nwb"

    return DatasetInfo(
        dataset_path=str(dataset_path.absolute()),
        format=format_name,
        total_size_bytes=total_size,
        file_count=file_count,
        has_metadata_files=has_metadata_files,
        metadata_files=metadata_file_paths,
    )


@router.post("/sessions/initialize", response_model=SessionInitializeResponse)
async def initialize_session(
    request_body: SessionInitializeRequest,
    req: Request,
) -> SessionInitializeResponse:
    """
    Initialize a new conversion session.

    This endpoint:
    1. Validates the dataset path
    2. Generates a unique session ID
    3. Collects basic dataset information
    4. Creates session context in storage
    5. Sends initialization message to conversation agent
    6. Returns session details

    Args:
        request_body: Session initialization request with dataset path
        req: FastAPI request object (contains app.state)

    Returns:
        SessionInitializeResponse with session_id and status

    Raises:
        HTTPException 400: If dataset path is invalid
        HTTPException 500: If agent communication or storage fails
    """
    # Get dependencies from app state
    context_manager = req.app.state.context_manager
    agent_registry = req.app.state.agent_registry
    message_router = req.app.state.message_router

    # 1. Validate dataset path
    logger.info(f"[initialize_session] Validating dataset path: {request_body.dataset_path}")
    start_time = time.time()
    dataset_path = _validate_dataset_path(request_body.dataset_path)
    logger.info(f"[initialize_session] Dataset path validated in {time.time() - start_time:.2f}s")

    # 2. Generate unique session ID
    session_id = str(uuid.uuid4())
    logger.info(f"[initialize_session] Generated session_id: {session_id}")

    # 3. Collect dataset information
    logger.info(f"[initialize_session] Collecting dataset information...")
    start_time = time.time()
    try:
        dataset_info = _collect_dataset_info(dataset_path)
        logger.info(f"[initialize_session] Dataset info collected in {time.time() - start_time:.2f}s")
    except Exception as e:
        logger.error(f"[initialize_session] Failed to collect dataset info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect dataset information: {str(e)}",
        ) from e

    # 4. Create session context
    logger.info(f"[initialize_session] Creating session context...")
    session_context = SessionContext(
        session_id=session_id,
        workflow_stage=WorkflowStage.INITIALIZED,
        dataset_info=dataset_info,
    )

    # 5. Save to context manager
    logger.info(f"[initialize_session] Saving session context to Redis...")
    start_time = time.time()
    try:
        await context_manager.create_session(session_context)
        logger.info(f"[initialize_session] Session context saved in {time.time() - start_time:.2f}s")
    except Exception as e:
        logger.error(f"[initialize_session] Failed to save session context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session context: {str(e)}",
        ) from e

    # 6. Verify conversation agent is registered
    logger.info(f"[initialize_session] Verifying conversation_agent is registered...")
    conversation_agent = agent_registry.get_agent("conversation_agent")
    if conversation_agent is None:
        logger.error(f"[initialize_session] conversation_agent not registered!")
        raise HTTPException(
            status_code=500,
            detail="conversation_agent is not registered in the system",
        )
    logger.info(f"[initialize_session] conversation_agent found: {conversation_agent}")

    # 7. Send message to conversation agent
    logger.info(f"[initialize_session] Sending initialize_session task to conversation_agent...")
    start_time = time.time()
    try:
        await message_router.execute_agent_task(
            target_agent="conversation_agent",
            task_name="initialize_session",
            session_id=session_id,
            parameters={"dataset_path": str(dataset_path.absolute())},
        )
        elapsed = time.time() - start_time
        logger.info(f"[initialize_session] conversation_agent task completed in {elapsed:.2f}s")
    except Exception as e:
        elapsed = time.time() - start_time
        # Better error logging - include exception type and repr if str is empty
        error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        logger.error(f"[initialize_session] Failed to send message after {elapsed:.2f}s: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message to conversation agent: {error_msg}",
        ) from e

    # 8. Return response
    logger.info(f"[initialize_session] Session {session_id} initialized successfully")
    return SessionInitializeResponse(
        session_id=session_id,
        workflow_stage=WorkflowStage.INITIALIZED,
        message=f"Session {session_id} initialized successfully. Starting metadata collection.",
    )


def _calculate_progress(workflow_stage: WorkflowStage) -> int:
    """
    Calculate progress percentage based on workflow stage.

    Args:
        workflow_stage: Current workflow stage

    Returns:
        Progress percentage (0-100)
    """
    progress_map = {
        WorkflowStage.INITIALIZED: 10,
        WorkflowStage.COLLECTING_METADATA: 25,
        WorkflowStage.CONVERTING: 50,
        WorkflowStage.EVALUATING: 75,
        WorkflowStage.COMPLETED: 100,
        WorkflowStage.FAILED: 0,  # Failed sessions show 0% progress
    }
    return progress_map.get(workflow_stage, 0)


def _generate_status_message(session: SessionContext) -> str:
    """
    Generate human-readable status message based on session state.

    Args:
        session: Session context

    Returns:
        User-friendly status message
    """
    stage = session.workflow_stage

    if stage == WorkflowStage.INITIALIZED:
        return "Session initialized. Preparing to collect metadata."
    elif stage == WorkflowStage.COLLECTING_METADATA:
        return "Collecting and extracting metadata from dataset."
    elif stage == WorkflowStage.CONVERTING:
        return "Converting dataset to NWB format."
    elif stage == WorkflowStage.EVALUATING:
        return "Validating NWB file and generating report."
    elif stage == WorkflowStage.COMPLETED:
        return "Conversion completed successfully."
    else:  # WorkflowStage.FAILED
        return "Conversion failed. Please check error details."


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    req: Request,
) -> SessionStatusResponse:
    """
    Get current session status and progress.

    This endpoint:
    1. Retrieves session from context manager
    2. Calculates progress percentage based on workflow stage
    3. Generates user-friendly status message
    4. Returns comprehensive status information

    Args:
        session_id: Session identifier
        req: FastAPI request object

    Returns:
        SessionStatusResponse with current status

    Raises:
        HTTPException 404: If session not found
    """
    # Get dependencies from app state
    context_manager = req.app.state.context_manager

    # 1. Get session from context manager
    session = await context_manager.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    # 2. Calculate progress percentage
    progress_percentage = _calculate_progress(session.workflow_stage)

    # 3. Generate status message
    status_message = _generate_status_message(session)

    # 4. Return response
    return SessionStatusResponse(
        session_id=session_id,
        workflow_stage=session.workflow_stage,
        progress_percentage=progress_percentage,
        status_message=status_message,
        current_agent=session.current_agent,
        requires_clarification=session.requires_user_clarification,
        clarification_prompt=session.clarification_prompt,
    )


@router.post("/sessions/{session_id}/clarify", response_model=SessionClarifyResponse)
async def clarify_session(
    session_id: str,
    request_body: SessionClarifyRequest,
    req: Request,
) -> SessionClarifyResponse:
    """
    Submit user clarification for error resolution.

    This endpoint:
    1. Retrieves session from context manager
    2. Sends clarification message to conversation agent
    3. Returns acknowledgment with current workflow stage

    Args:
        session_id: Session identifier
        request_body: Clarification request with user input and/or metadata
        req: FastAPI request object

    Returns:
        SessionClarifyResponse with acknowledgment

    Raises:
        HTTPException 404: If session not found
        HTTPException 500: If message routing fails
    """
    # Get dependencies from app state
    context_manager = req.app.state.context_manager
    message_router = req.app.state.message_router

    # 1. Get session from context manager
    session = await context_manager.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    # 2. Prepare parameters for agent
    parameters: dict[str, Any] = {}
    if request_body.user_input is not None:
        parameters["user_input"] = request_body.user_input
    if request_body.updated_metadata is not None:
        parameters["updated_metadata"] = request_body.updated_metadata

    # 3. Send message to conversation agent
    try:
        await message_router.execute_agent_task(
            target_agent="conversation_agent",
            task_name="handle_clarification",
            session_id=session_id,
            parameters=parameters,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send clarification to conversation agent: {str(e)}",
        ) from e

    # 4. Return response
    return SessionClarifyResponse(
        message="Clarification received. Processing your input.",
        workflow_stage=session.workflow_stage,
    )


@router.get("/sessions/{session_id}/result", response_model=SessionResultResponse)
async def get_session_result(
    session_id: str,
    req: Request,
) -> SessionResultResponse:
    """
    Get final conversion results and validation report.

    This endpoint:
    1. Retrieves session from context manager
    2. Verifies session is in COMPLETED state
    3. Extracts conversion and validation results
    4. Returns comprehensive result information

    Args:
        session_id: Session identifier
        req: FastAPI request object

    Returns:
        SessionResultResponse with results

    Raises:
        HTTPException 404: If session not found
        HTTPException 400: If session not completed
    """
    # Get dependencies from app state
    context_manager = req.app.state.context_manager

    # 1. Get session from context manager
    session = await context_manager.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found",
        )

    # 2. Verify session is completed
    if session.workflow_stage != WorkflowStage.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} is not completed. Current stage: {session.workflow_stage}",
        )

    # 3. Extract results from session context
    if session.conversion_results is None or session.validation_results is None:
        raise HTTPException(
            status_code=500,
            detail="Session marked as completed but missing results data",
        )

    # Extract NWB file path
    nwb_file_path = (
        session.conversion_results.nwb_file_path or session.output_nwb_path or ""
    )

    # Extract validation report path
    validation_report_path = (
        session.validation_results.validation_report_path
        or session.output_report_path
        or ""
    )

    # Extract overall status
    overall_status = session.validation_results.overall_status

    # Extract LLM summary
    llm_validation_summary = session.validation_results.llm_validation_summary or ""

    # Validation issues are already ValidationIssue objects
    validation_issues = session.validation_results.issues

    # 4. Return response
    return SessionResultResponse(
        session_id=session_id,
        nwb_file_path=nwb_file_path,
        validation_report_path=validation_report_path,
        overall_status=overall_status,
        llm_validation_summary=llm_validation_summary,
        validation_issues=validation_issues,
    )
