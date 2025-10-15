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
        register_conversion_agent(_mcp_server)
        register_evaluation_agent(_mcp_server, llm_service=llm_service)
        register_conversation_agent(_mcp_server, llm_service=llm_service)

    return _mcp_server


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

    return UploadResponse(
        session_id="session-1",  # MVP: single session
        message="File uploaded successfully, conversion started",
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
        message=None,
        input_path=state.input_path,
        output_path=state.output_path,
        correction_attempt=state.correction_attempt,
        can_retry=state.can_retry(),
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
