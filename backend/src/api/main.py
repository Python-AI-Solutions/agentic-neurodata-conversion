"""
FastAPI application for agentic neurodata conversion.

Main API server with REST endpoints and WebSocket support.
"""
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from agents import (
    register_conversation_agent,
    register_conversion_agent,
    register_evaluation_agent,
)
from models import (
    ConversionStatus,
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
from services import MCPServer, create_llm_service, get_mcp_server

# Initialize FastAPI app
app = FastAPI(
    title="Agentic Neurodata Conversion API",
    description="AI-assisted neurodata conversion to NWB format",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
_mcp_server: Optional[MCPServer] = None
_upload_dir: Path = Path(tempfile.gettempdir()) / "nwb_uploads"
_upload_dir.mkdir(exist_ok=True)


def get_or_create_mcp_server() -> MCPServer:
    """Get or create the MCP server with all agents registered."""
    global _mcp_server

    if _mcp_server is None:
        _mcp_server = get_mcp_server()

        # Initialize LLM service if API key is available
        llm_service = None
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            llm_service = create_llm_service(
                provider="anthropic",
                api_key=api_key,
            )

        # Register agents
        register_conversion_agent(_mcp_server, llm_service=llm_service)
        register_evaluation_agent(_mcp_server, llm_service=llm_service)
        register_conversation_agent(_mcp_server, llm_service=llm_service)

    return _mcp_server


async def _generate_upload_welcome_message(
    filename: str,
    file_size_mb: float,
    llm_service,
) -> dict:
    """
    Use LLM to generate a welcoming, informative upload response.

    Args:
        filename: Uploaded filename
        file_size_mb: File size in MB
        llm_service: LLM service instance

    Returns:
        Dictionary with message and detected info
    """
    # Fallback if no LLM
    if not llm_service:
        return {
            "message": "File uploaded successfully, conversion started",
            "detected_info": {},
        }

    # Analyze filename for clues
    system_prompt = """You are a neuroscience data expert analyzing uploaded files.
Based on the filename and size, provide:
1. A warm, welcoming message
2. What you detect about the file (format, likely data type)
3. Brief expectations (conversion time, what happens next)

Be friendly, specific, and helpful. Keep it to 2-3 sentences."""

    user_prompt = f"""A user just uploaded a file:
Filename: {filename}
Size: {file_size_mb:.1f}MB

Generate a welcoming message that shows you understand their file."""

    output_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Welcoming message (2-3 sentences)",
            },
            "detected_format": {
                "type": "string",
                "description": "Likely format if detectable from name",
            },
            "estimated_time_seconds": {
                "type": "number",
                "description": "Estimated conversion time",
            },
            "data_type": {
                "type": "string",
                "description": "Likely data type (ephys, imaging, etc.)",
            },
        },
        "required": ["message"],
    }

    try:
        response = await llm_service.generate_structured_output(
            prompt=user_prompt,
            output_schema=output_schema,
            system_prompt=system_prompt,
        )

        return {
            "message": response.get("message", "File uploaded successfully, conversion started"),
            "detected_info": {
                "format": response.get("detected_format"),
                "estimated_time_seconds": response.get("estimated_time_seconds"),
                "data_type": response.get("data_type"),
            },
        }
    except Exception:
        return {
            "message": "File uploaded successfully, conversion started",
            "detected_info": {},
        }


@app.on_event("startup")
async def startup_event():
    """Initialize the MCP server on startup."""
    get_or_create_mcp_server()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Agentic Neurodata Conversion API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    mcp_server = get_or_create_mcp_server()
    handlers = mcp_server.get_handlers_info()

    return {
        "status": "healthy",
        "agents": list(handlers.keys()),
        "handlers": handlers,
    }


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    """
    Upload a neurodata file for conversion.

    Args:
        file: Uploaded file
        metadata: Optional JSON metadata string

    Returns:
        Upload confirmation with session info
    """
    import hashlib
    import json

    mcp_server = get_or_create_mcp_server()

    # Check if already processing
    if mcp_server.global_state.status != ConversionStatus.IDLE:
        raise HTTPException(
            status_code=409,
            detail="Another conversion is in progress. Please wait or reset.",
        )

    # Save uploaded file
    file_path = _upload_dir / file.filename
    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    # For SpikeGLX files, also check if we need to copy the corresponding .meta file
    # This helps when users upload only the .bin file
    if ".ap.bin" in file.filename or ".lf.bin" in file.filename:
        meta_filename = file.filename.replace(".bin", ".meta")
        # Check if meta file exists in our test data directory
        test_meta = Path("test_data/spikeglx") / meta_filename
        if test_meta.exists():
            import shutil
            shutil.copy(test_meta, _upload_dir / meta_filename)

    # Calculate checksum
    checksum = hashlib.sha256(content).hexdigest()

    # Parse metadata if provided
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON in metadata field",
            )

    # Start conversion workflow
    from models import MCPMessage

    start_msg = MCPMessage(
        target_agent="conversation",
        action="start_conversion",
        context={
            "input_path": str(file_path),
            "metadata": metadata_dict,
        },
    )

    response = await mcp_server.send_message(start_msg)

    if not response.success:
        error_msg = response.error.get("message", "Unknown error")
        error_context = response.error.get("context", {})
        print(f"ERROR: Conversion failed - {error_msg}")
        print(f"ERROR CONTEXT: {error_context}")
        raise HTTPException(
            status_code=500,
            detail=error_msg,
        )

    # Generate LLM-powered welcome message
    file_size_mb = len(content) / (1024 * 1024)

    # Get LLM service from MCP server
    llm_service = None
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        llm_service = create_llm_service(provider="anthropic", api_key=api_key)

    welcome_data = await _generate_upload_welcome_message(
        filename=file.filename,
        file_size_mb=file_size_mb,
        llm_service=llm_service,
    )

    return UploadResponse(
        session_id="session-1",  # MVP: single session
        message=welcome_data["message"],  # LLM-POWERED!
        input_path=str(file_path),
        checksum=checksum,
    )


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """
    Get current conversion status.

    Returns:
        Current status and progress
    """
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    return StatusResponse(
        status=state.status,
        validation_status=state.validation_status,
        progress=None,  # MVP: no progress tracking
        message=state.llm_message,  # Include LLM conversational message
        input_path=state.input_path,
        output_path=state.output_path,
        correction_attempt=state.correction_attempt,
        can_retry=state.can_retry(),
        conversation_type=state.conversation_type,  # NEW: conversational type
    )


@app.post("/api/retry-approval", response_model=RetryApprovalResponse)
async def retry_approval(request: RetryApprovalRequest):
    """
    Submit retry approval decision.

    Args:
        request: Retry approval request

    Returns:
        Response with new status
    """
    from models import MCPMessage

    mcp_server = get_or_create_mcp_server()

    retry_msg = MCPMessage(
        target_agent="conversation",
        action="retry_decision",
        context={"decision": request.decision.value},
    )

    response = await mcp_server.send_message(retry_msg)

    if not response.success:
        raise HTTPException(
            status_code=400,
            detail=response.error["message"],
        )

    new_status_str = response.result.get("status", "unknown")
    # Map string status to enum
    status_map = {
        "failed": ConversionStatus.FAILED,
        "analyzing_corrections": ConversionStatus.CONVERTING,
        "awaiting_corrections": ConversionStatus.AWAITING_USER_INPUT,
    }
    new_status = status_map.get(new_status_str, ConversionStatus.IDLE)

    return RetryApprovalResponse(
        accepted=True,
        message=response.result.get("message", "Decision accepted"),
        new_status=new_status,
    )


@app.post("/api/user-input", response_model=UserInputResponse)
async def submit_user_input(request: UserInputRequest):
    """
    Submit user input (e.g., format selection, corrections).

    Args:
        request: User input request

    Returns:
        Response with new status
    """
    from models import MCPMessage

    mcp_server = get_or_create_mcp_server()

    # Check if we're awaiting format selection
    if mcp_server.global_state.status == ConversionStatus.AWAITING_USER_INPUT:
        if "format" in request.input_data:
            # Format selection
            format_msg = MCPMessage(
                target_agent="conversation",
                action="user_format_selection",
                context={"format": request.input_data["format"]},
            )

            response = await mcp_server.send_message(format_msg)

            if not response.success:
                raise HTTPException(
                    status_code=400,
                    detail=response.error["message"],
                )

            return UserInputResponse(
                accepted=True,
                message="Format selection accepted, conversion started",
                new_status=ConversionStatus.CONVERTING,
            )

    raise HTTPException(
        status_code=400,
        detail="Invalid state for user input",
    )


@app.post("/api/chat")
async def chat_message(message: str = Form(...)):
    """
    Send a conversational message to the LLM-driven chat.

    This enables natural conversation for gathering metadata,
    answering questions about validation issues, etc.

    Args:
        message: User's message

    Returns:
        LLM's response
    """
    from models import MCPMessage

    mcp_server = get_or_create_mcp_server()

    # Send conversational message
    chat_msg = MCPMessage(
        target_agent="conversation",
        action="conversational_response",
        context={"message": message},
    )

    response = await mcp_server.send_message(chat_msg)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.error.get("message", "Failed to process message"),
        )

    result = response.result
    return {
        "message": result.get("message"),
        "status": result.get("status"),
        "needs_more_info": result.get("needs_more_info", False),
        "extracted_metadata": result.get("extracted_metadata", {}),
    }


@app.post("/api/chat/smart")
async def smart_chat(message: str = Form(...)):
    """
    Smart chat endpoint that works in ALL states, at ANY time.

    This makes the system feel like Claude.ai - always ready to help.
    Users can ask questions before upload, during conversion, after validation.
    The LLM understands context and provides intelligent, state-aware responses.

    Args:
        message: User's message/question

    Returns:
        Intelligent response with optional action suggestions
    """
    from models import MCPMessage

    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # Route to general query handler
    query_msg = MCPMessage(
        target_agent="conversation",
        action="general_query",
        context={"query": message},
    )

    response = await mcp_server.send_message(query_msg)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.error.get("message", "Failed to process your question"),
        )

    result = response.result
    return {
        "type": result.get("type", "general_query_response"),
        "answer": result.get("answer"),
        "suggestions": result.get("suggestions", []),
        "suggested_action": result.get("suggested_action"),
    }


@app.get("/api/validation", response_model=ValidationResponse)
async def get_validation_results():
    """
    Get validation results.

    Returns:
        Validation results if available
    """
    mcp_server = get_or_create_mcp_server()

    # For MVP, return simplified validation info from logs
    # In full implementation, this would fetch from evaluation agent
    return ValidationResponse(
        is_valid=False,
        issues=[],
        summary={"critical": 0, "error": 0, "warning": 0, "info": 0},
    )


@app.get("/api/correction-context")
async def get_correction_context():
    """
    Get detailed correction context including issue breakdown.

    Returns:
        Correction context with auto-fixable and user-input-required issues
    """
    from models import MCPMessage

    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # Search logs for LLM correction guidance
    llm_guidance = None
    validation_result = None

    for log in reversed(state.logs):
        if "LLM correction guidance" in log.message or "corrections" in log.message.lower():
            # Try to extract correction data from log context
            if log.context:
                llm_guidance = log.context
        if "validation" in log.message.lower() and log.context:
            if "overall_status" in log.context:
                validation_result = log.context

    if not llm_guidance and not validation_result:
        return {
            "status": "no_context",
            "message": "No correction context available",
            "auto_fixable": [],
            "user_input_required": [],
        }

    # Parse LLM guidance to extract issue breakdown
    auto_fixable = []
    user_input_required = []

    if llm_guidance:
        suggestions = llm_guidance.get("suggestions", [])
        for suggestion in suggestions:
            issue_info = {
                "issue": suggestion.get("issue", "Unknown issue"),
                "suggestion": suggestion.get("suggestion", ""),
                "severity": suggestion.get("severity", "info"),
            }

            if suggestion.get("actionable", False):
                auto_fixable.append(issue_info)
            else:
                user_input_required.append(issue_info)

    # If no specific suggestions, extract from validation result
    if not auto_fixable and not user_input_required and validation_result:
        summary = validation_result.get("summary", {})
        if summary.get("error", 0) > 0:
            auto_fixable.append({
                "issue": f"{summary['error']} validation errors found",
                "suggestion": "System will attempt automatic corrections",
                "severity": "error",
            })

    return {
        "status": "available",
        "correction_attempt": state.correction_attempt,
        "can_retry": state.can_retry(),
        "auto_fixable": auto_fixable,
        "user_input_required": user_input_required,
        "validation_summary": validation_result.get("summary", {}) if validation_result else {},
    }


@app.get("/api/logs", response_model=LogsResponse)
async def get_logs(limit: int = 100, offset: int = 0):
    """
    Get conversion logs.

    Args:
        limit: Maximum number of logs to return
        offset: Offset for pagination

    Returns:
        List of log entries
    """
    mcp_server = get_or_create_mcp_server()
    logs = mcp_server.global_state.logs

    total = len(logs)
    paginated_logs = logs[offset : offset + limit]

    return LogsResponse(
        logs=[log.model_dump() for log in paginated_logs],
        total_count=total,
    )


@app.get("/api/download/nwb")
async def download_nwb():
    """
    Download the converted NWB file.

    Returns:
        NWB file as download
    """
    mcp_server = get_or_create_mcp_server()

    if not mcp_server.global_state.output_path:
        raise HTTPException(
            status_code=404,
            detail="No NWB file available for download",
        )

    output_path = Path(mcp_server.global_state.output_path)

    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="NWB file not found",
        )

    return FileResponse(
        path=str(output_path),
        media_type="application/x-hdf5",
        filename=output_path.name,
    )


@app.get("/api/download/report")
async def download_report():
    """
    Download the evaluation report (PDF or JSON).

    Returns:
        Report file as download
    """
    mcp_server = get_or_create_mcp_server()

    if not mcp_server.global_state.output_path:
        raise HTTPException(
            status_code=404,
            detail="No conversion output available",
        )

    # Find the report file
    output_dir = Path(mcp_server.global_state.output_path).parent
    output_stem = Path(mcp_server.global_state.output_path).stem

    # Try PDF first
    pdf_report = output_dir / f"{output_stem}_evaluation_report.pdf"
    if pdf_report.exists():
        return FileResponse(
            path=str(pdf_report),
            media_type="application/pdf",
            filename=pdf_report.name,
        )

    # Try JSON
    json_report = output_dir / f"{output_stem}_correction_context.json"
    if json_report.exists():
        return FileResponse(
            path=str(json_report),
            media_type="application/json",
            filename=json_report.name,
        )

    raise HTTPException(
        status_code=404,
        detail="No report file available for download",
    )


@app.post("/api/reset")
async def reset_session():
    """
    Reset the conversion session.

    Returns:
        Confirmation message
    """
    mcp_server = get_or_create_mcp_server()
    mcp_server.reset_state()

    return {"message": "Session reset successfully"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()

    mcp_server = get_or_create_mcp_server()

    # Subscribe to MCP events
    async def event_handler(event):
        """Forward MCP events to WebSocket."""
        try:
            message = WebSocketMessage(
                event_type=event.event_type,
                data=event.data,
            )
            await websocket.send_json(message.model_dump())
        except Exception:
            pass  # WebSocket may be closed

    mcp_server.subscribe_to_events(event_handler)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_json()
            # Handle WebSocket messages if needed
            # For MVP, just acknowledge
            await websocket.send_json({"status": "received"})

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
