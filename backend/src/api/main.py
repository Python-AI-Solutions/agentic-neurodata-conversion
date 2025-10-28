"""
FastAPI application for agentic neurodata conversion.

Main API server with REST endpoints and WebSocket support.
"""
import os
import tempfile
from pathlib import Path
from typing import List, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

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
    LogLevel,
    LogsResponse,
    MCPMessage,
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
from models.metadata import NWBMetadata
# WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Phase 2 Integration
from models.workflow_state_manager import WorkflowStateManager
from models.state import ValidationOutcome, ConversationPhase, MetadataRequestPolicy
from pydantic import ValidationError
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

# WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Phase 2 - Initialize WorkflowStateManager
_workflow_manager = WorkflowStateManager()


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
    additional_files: List[UploadFile] = File(default=[]),
    metadata: Optional[str] = Form(None),
):
    """
    Upload neurodata file(s) for conversion. Supports multiple files.

    Args:
        file: Main uploaded file (required)
        additional_files: Additional files (e.g., .meta files for SpikeGLX)
        metadata: Optional JSON metadata string

    Returns:
        Upload confirmation with session info
    """
    import hashlib
    import json

    mcp_server = get_or_create_mcp_server()

    # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Phase 2 - Use WorkflowStateManager
    if not _workflow_manager.can_accept_upload(mcp_server.global_state):
        status_str = mcp_server.global_state.status.value if mcp_server.global_state.status else "unknown"
        raise HTTPException(
            status_code=409,
            detail=f"Cannot upload while {status_str}. Please wait or reset.",
        )

    # EDGE CASE FIX #2: Validate file count and types (prevent multiple separate datasets)
    total_files = 1 + len(additional_files)

    # Check for too many files
    if total_files > 10:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files uploaded ({total_files}). Maximum 10 files allowed. "
                   "If you have multiple datasets, please upload them one at a time."
        )

    # Check for multiple primary data files (suggests multiple separate datasets)
    primary_extensions = {'.bin', '.dat', '.continuous', '.h5', '.nwb'}
    all_files_list = [file] + additional_files
    primary_files = [f for f in all_files_list
                     if any(f.filename.lower().endswith(ext) for ext in primary_extensions)]

    if len(primary_files) > 1:
        # Check if this is a legitimate multi-file format
        filenames = [f.filename for f in primary_files]
        is_spikeglx_set = any('.ap.bin' in fn or '.lf.bin' in fn for fn in filenames)
        is_openephys_set = all('.continuous' in fn for fn in filenames)

        if not (is_spikeglx_set or is_openephys_set):
            raise HTTPException(
                status_code=400,
                detail=f"Multiple data files detected ({len(primary_files)}). "
                       f"This system processes ONE recording session at a time. "
                       f"Please upload files for a single session only. "
                       f"Files: {', '.join(filenames)}"
            )

    # Validate file type
    ALLOWED_EXTENSIONS = {
        '.bin', '.dat', '.continuous', '.nwb', '.meta', '.json',
        '.rhd', '.rhs', '.ncs', '.nev', '.ntt', '.plx', '.tif', '.avi'
    }
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Validate file size (max 5GB for now)
    MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB in bytes
    content = await file.read()
    await file.close()  # Bug #13: Explicitly close file handle after reading

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content) / (1024**3):.2f}GB. Maximum: 5GB"
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )

    # Save main file
    file_path = _upload_dir / file.filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Save additional files (e.g., .meta files, other companion files)
    uploaded_files = [file.filename]
    for additional_file in additional_files:
        add_file_path = _upload_dir / additional_file.filename
        add_content = await additional_file.read()
        with open(add_file_path, "wb") as f:
            f.write(add_content)
        uploaded_files.append(additional_file.filename)

    # Validate that SpikeGLX files have their required companion .meta files
    if ".ap.bin" in file.filename or ".lf.bin" in file.filename or ".nidq.bin" in file.filename:
        meta_filename = file.filename.replace(".bin", ".meta")
        meta_file_path = _upload_dir / meta_filename

        # Check if .meta file was uploaded
        if not meta_file_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"SpikeGLX .bin files require a matching .meta file. "
                       f"Please upload both '{file.filename}' and '{meta_filename}' together. "
                       f"The .meta file contains essential recording parameters (sampling rate, "
                       f"channel count, probe configuration) needed for accurate conversion."
            )

    # Validate OpenEphys files have required companion files
    if file.filename == "structure.oebin":
        # New OpenEphys format - should have accompanying data files
        # We'll validate this more thoroughly during conversion, but warn user
        if len(additional_files) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"OpenEphys format requires multiple files. When uploading 'structure.oebin', "
                       f"please also upload the accompanying .dat files and other recording files from the same session folder. "
                       f"All files from the recording session are needed for complete data extraction."
            )
    elif file.filename == "settings.xml":
        # Old OpenEphys format - should have .continuous files
        continuous_files = [f for f in additional_files if ".continuous" in f.filename]
        if len(continuous_files) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Old OpenEphys format requires .continuous data files. When uploading 'settings.xml', "
                       f"please also upload all .continuous files from the same recording session. "
                       f"All files are needed for complete data extraction."
            )

    # Calculate checksum of main file
    checksum = hashlib.sha256(content).hexdigest()

    # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Phase 2 - Use WorkflowStateManager
    in_active_conversation = _workflow_manager.is_in_active_conversation(mcp_server.global_state)

    if not in_active_conversation:
        # Reset state for new upload session (Bug #8 fix)
        # This prevents retry counter and metadata flags from carrying over
        mcp_server.global_state.correction_attempt = 0
        mcp_server.global_state.user_declined_fields.clear()
        mcp_server.global_state.metadata_requests_count = 0
        mcp_server.global_state.user_wants_minimal = False
        mcp_server.global_state.user_wants_sequential = False
        mcp_server.global_state.validation_status = None  # Bug #17: Reset validation status
        mcp_server.global_state.overall_status = None  # Bug #9: Reset overall_status
        mcp_server.global_state.conversation_history = []  # Clear old conversations
        # Reset custom metadata flag to ensure proper workflow
        if '_custom_metadata_prompted' in mcp_server.global_state.metadata:
            del mcp_server.global_state.metadata['_custom_metadata_prompted']
    else:
        # Preserve conversation state but update file paths
        mcp_server.global_state.add_log(
            LogLevel.INFO,
            "Re-upload detected during active conversation - preserving conversation state",
            {"previous_request_count": mcp_server.global_state.metadata_requests_count}
        )

    # Parse and validate metadata if provided
    # NOTE: Metadata is OPTIONAL during upload - we collect it during conversation
    # But if metadata IS provided, we validate it strictly
    metadata_dict = {}
    if metadata:
        try:
            metadata_raw = json.loads(metadata)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in metadata field: {str(e)}",
            )

        # Only validate if user actually provided metadata fields
        # Empty dict {} means "no metadata yet" - this is OK for initial upload
        if metadata_raw:  # Non-empty metadata provided
            # ✅ STRICT VALIDATION with Pydantic
            # We validate strictly when metadata is provided, but allow partial metadata
            # Required fields will be enforced before conversion starts
            try:
                # Allow partial metadata by making fields optional during upload
                # Full validation happens before conversion in conversation_agent
                validated_metadata = NWBMetadata(**metadata_raw)
                # Convert validated model back to dict
                metadata_dict = validated_metadata.model_dump(exclude_none=True)
            except ValidationError as e:
                # Build user-friendly error messages
                errors = []
                for error in e.errors():
                    field = " → ".join(str(loc) for loc in error["loc"])
                    message = error["msg"]
                    errors.append(f"{field}: {message}")

                raise HTTPException(
                    status_code=422,  # Unprocessable Entity
                    detail={
                        "message": "Metadata validation failed",
                        "errors": errors,
                        "hint": "Please check the required fields and formats. See /docs for examples."
                    }
                )

    # CRITICAL FIX: DO NOT auto-start conversion on upload
    # According to requirements (orchestration/SKILL.md), the system should:
    # 1. Upload file
    # 2. Acknowledge upload
    # 3. Wait for user to explicitly start conversion
    # This prevents the auto-start bug described in the user's screenshot

    # INFINITE LOOP FIX: Skip re-acknowledging if already in active conversation
    if in_active_conversation:
        mcp_server.global_state.add_log(
            LogLevel.INFO,
            "Upload during active conversation - skipping duplicate acknowledgment",
            {"status": str(current_status), "conversation_type": mcp_server.global_state.conversation_type}
        )

        # Return the current conversation state
        current_message = mcp_server.global_state.llm_message or "Please continue the conversation to provide the requested information."

        return UploadResponse(
            session_id="session-1",
            message=current_message,
            input_path=str(file_path),
            checksum=checksum,
            status="conversation_active",
            uploaded_files=uploaded_files,
            conversation_active=True,
        )

    # Determine the correct input path for conversion (when user triggers it)
    # For SpikeGLX, use the directory (or specifically the .bin file)
    conversion_input_path = str(file_path)
    if ".meta" in file.filename:
        # If user uploaded .meta file first, find the corresponding .bin file
        bin_filename = file.filename.replace(".meta", ".bin")
        bin_path = _upload_dir / bin_filename
        if bin_path.exists():
            conversion_input_path = str(_upload_dir)  # Use directory for SpikeGLX
        else:
            # .bin file doesn't exist yet, use .meta for now
            conversion_input_path = str(file_path)
    elif ".ap.bin" in file.filename or ".lf.bin" in file.filename:
        # For .bin files, use the directory path for SpikeGLX detection
        conversion_input_path = str(_upload_dir)

    # Store the upload information in state WITHOUT starting conversion
    mcp_server.global_state.input_path = conversion_input_path  # Keep as string
    mcp_server.global_state.metadata.update(metadata_dict)
    mcp_server.global_state.pending_conversion_input_path = conversion_input_path  # Keep as string

    mcp_server.global_state.add_log(
        LogLevel.INFO,
        "File uploaded successfully - awaiting user command to start conversion",
        {
            "file": file.filename,
            "size_mb": len(content) / (1024 * 1024),
            "checksum": checksum,
            "conversion_input_path": conversion_input_path
        }
    )

    # Generate LLM-powered welcome message that DOES NOT auto-start conversion
    file_size_mb = len(content) / (1024 * 1024)

    # Get LLM service from MCP server
    llm_service = None
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        llm_service = create_llm_service(provider="anthropic", api_key=api_key)

    # Generate welcome message that acknowledges upload WITHOUT starting conversion
    if llm_service:
        try:
            system_prompt = """You are a helpful NWB conversion assistant.

A user just uploaded a file. Acknowledge the upload in a friendly way and explain what happens next.
Make it clear they need to actively start the conversion process - don't assume they want to start immediately.
Keep it concise (2-3 sentences max)."""

            user_prompt = f"""The user just uploaded: {file.filename} ({file_size_mb:.2f} MB)

Generate a welcome message that:
1. Acknowledges the upload
2. Briefly explains what this system does (convert to NWB format)
3. Tells them to start the conversion when ready (don't auto-start!)

Return JSON with a 'message' field."""

            output_schema = {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }

            response = await llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            welcome_message = response.get("message", "File uploaded successfully! Ready to start conversion when you are.")
        except Exception as e:
            mcp_server.global_state.add_log(
                LogLevel.WARNING,
                f"Failed to generate LLM welcome message: {e}",
            )
            welcome_message = f"File '{file.filename}' uploaded successfully! ({file_size_mb:.2f} MB)\n\nReady to convert to NWB format. Start the conversion when you're ready."
    else:
        welcome_message = f"File '{file.filename}' uploaded successfully! ({file_size_mb:.2f} MB)\n\nReady to convert to NWB format. Start the conversion when you're ready."

    return UploadResponse(
        session_id="session-1",  # MVP: single session
        message=welcome_message,
        input_path=str(file_path),
        checksum=checksum,
        status="upload_acknowledged",
        uploaded_files=[file.filename],
        conversation_active=False,
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
        overall_status=state.overall_status,  # Bug #12: Include overall_status
        progress=None,  # MVP: no progress tracking
        message=state.llm_message,  # Include LLM conversational message
        input_path=state.input_path,
        output_path=state.output_path,
        correction_attempt=state.correction_attempt,
        can_retry=mcp_server.global_state.can_retry,  # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use retry limit
        conversation_type=state.conversation_type,  # NEW: conversational type
    )


@app.get("/api/metadata-provenance")
async def get_metadata_provenance():
    """
    Get metadata provenance information for all fields.

    Returns complete audit trail showing source, confidence, and reliability
    of each metadata field for scientific transparency and DANDI compliance.

    Returns:
        Dictionary of field names to provenance information
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
        }

    return {
        "provenance": provenance_data,
        "total_fields": len(provenance_data),
        "needs_review_count": sum(1 for p in state.metadata_provenance.values() if p.needs_review),
    }


@app.post("/api/start-conversion")
async def start_conversion():
    """
    Start the conversion workflow after file upload.

    This triggers the Conversation Agent to:
    1. Validate metadata
    2. Request missing fields if needed
    3. Start conversion once metadata is complete

    Returns:
        Response with status
    """
    mcp_server = get_or_create_mcp_server()

    # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Phase 2 - Use WorkflowStateManager
    if not _workflow_manager.can_start_conversion(mcp_server.global_state):
        if not mcp_server.global_state.input_path:
            raise HTTPException(
                status_code=400,
                detail="No file uploaded. Please upload a file first.",
            )
        else:
            status_str = mcp_server.global_state.status.value if mcp_server.global_state.status else "unknown"
            raise HTTPException(
                status_code=409,
                detail=f"Conversion already in progress: {status_str}",
            )

    # Send message to Conversation Agent to start conversion workflow
    start_msg = MCPMessage(
        target_agent="conversation",
        action="start_conversion",
        context={
            "input_path": str(mcp_server.global_state.input_path),
            "metadata": mcp_server.global_state.metadata,
        },
    )

    response = await mcp_server.send_message(start_msg)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.error.get("message", "Failed to start conversion"),
        )

    return {
        "message": "Conversion workflow started",
        "status": mcp_server.global_state.status.value if mcp_server.global_state.status else "unknown",
    }


@app.post("/api/improvement-decision")
async def improvement_decision(decision: str = Form(...)):
    """
    Submit improvement decision for PASSED_WITH_ISSUES validation.

    When validation passes but has warnings, user can choose:
    - "improve" - Enter correction loop to fix warnings
    - "accept" - Accept file as-is and finalize

    Args:
        decision: "improve" or "accept"

    Returns:
        Response with new status
    """
    mcp_server = get_or_create_mcp_server()

    if decision not in ["improve", "accept"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'improve' or 'accept'",
        )

    # Send message to Conversation Agent
    improvement_msg = MCPMessage(
        target_agent="conversation",
        action="improvement_decision",
        context={"decision": decision},
    )

    response = await mcp_server.send_message(improvement_msg)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.error.get("message", "Failed to process decision"),
        )

    return {
        "accepted": True,
        "message": response.result.get("message", "Decision accepted"),
        "status": mcp_server.global_state.status.value if mcp_server.global_state.status else "unknown",
    }


@app.post("/api/retry-approval", response_model=RetryApprovalResponse)
async def retry_approval(request: RetryApprovalRequest):
    """
    Submit retry approval decision.

    Args:
        request: Retry approval request

    Returns:
        Response with new status
    """
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
    # If unknown status, preserve current status rather than resetting to IDLE
    new_status = status_map.get(new_status_str, mcp_server.global_state.status or ConversionStatus.AWAITING_RETRY_APPROVAL)

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
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # EDGE CASE FIX #1: Check if LLM is already processing
    if state.llm_processing:
        return {
            "message": "I'm still processing your previous message. Please wait a moment...",
            "status": "busy",
            "needs_more_info": False,
            "extracted_metadata": {},
        }

    # Acquire LLM lock to prevent concurrent processing
    async with state._llm_lock:
        state.llm_processing = True
        try:
            # Send conversational message
            chat_msg = MCPMessage(
                target_agent="conversation",
                action="conversational_response",
                context={"message": message},
            )

            # Add timeout to prevent indefinite waiting
            import asyncio
            response = await asyncio.wait_for(
                mcp_server.send_message(chat_msg),
                timeout=180.0  # 3 minute timeout for LLM processing
            )

        except asyncio.TimeoutError:
            state.add_log(
                LogLevel.ERROR,
                "Chat LLM call timed out",
                {"message": message[:100]},
            )
            return {
                "message": "I'm sorry, that request is taking longer than expected. Please try a simpler message or try again in a moment.",
                "status": "error",
                "error": "timeout",
                "needs_more_info": True,
                "extracted_metadata": {},
            }
        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Chat endpoint error: {str(e)}",
                {"message": message[:100], "error_type": type(e).__name__},
            )
            return {
                "message": f"I encountered an error: {str(e)}. Please try rephrasing your message.",
                "status": "error",
                "error": str(e),
                "needs_more_info": True,
                "extracted_metadata": {},
            }
        finally:
            state.llm_processing = False

    # Validate response object
    if not response:
        state.add_log(LogLevel.ERROR, "Empty response from conversation agent")
        return {
            "message": "I'm having trouble processing that. Could you try rephrasing?",
            "status": "error",
            "error": "empty_response",
            "needs_more_info": True,
            "extracted_metadata": {},
        }

    if not response.success:
        error_msg = response.error.get("message", "Failed to process message") if hasattr(response, 'error') and response.error else "Unknown error"
        state.add_log(
            LogLevel.ERROR,
            "Conversation agent returned error",
            {"error": error_msg},
        )
        return {
            "message": f"I encountered an issue: {error_msg}. Please try again.",
            "status": "error",
            "error": error_msg,
            "needs_more_info": True,
            "extracted_metadata": {},
        }

    result = response.result if hasattr(response, 'result') else {}

    # Validate result has required fields
    if not isinstance(result, dict):
        state.add_log(LogLevel.ERROR, "Invalid result type from conversation agent", {"type": str(type(result))})
        result = {}

    # ✅ FIX: Determine status explicitly based on workflow state
    # This ensures frontend can reliably detect conversation continuation vs completion
    ready_to_proceed = result.get("ready_to_proceed", False)
    needs_more_info = result.get("needs_more_info", True)  # Default to True for safety

    # ✅ CRITICAL FIX: Auto-trigger conversion when user confirms ready
    # This prevents the Agent 1 → Agent 2 handoff failure
    if ready_to_proceed and state.input_path:
        state.add_log(
            LogLevel.INFO,
            "User confirmed ready to proceed - triggering conversion",
            {"ready_to_proceed": ready_to_proceed},
        )

        # Trigger conversion workflow in background
        # Import here to avoid circular dependency
        import asyncio
        from agents import register_conversation_agent

        # Create conversion task message
        conv_agent = register_conversation_agent(mcp_server)

        # Get format from state or detect it
        format_name = state.detected_format if state.detected_format else "unknown"

        # If format is unknown, we need to detect it first
        if format_name == "unknown":
            from agents import register_conversion_agent
            conv_agent_inst = register_conversion_agent(mcp_server)

            detect_msg = MCPMessage(
                target_agent="conversion",
                action="detect_format",
                context={"input_path": state.input_path},
            )
            detect_response = await mcp_server.send_message(detect_msg)

            if detect_response.success:
                format_name = detect_response.result.get("format", "unknown")
                state.detected_format = format_name
                state.add_log(LogLevel.INFO, f"Detected format: {format_name}")

        # Now trigger actual conversion
        start_msg = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={
                "input_path": state.input_path,
                "metadata": state.metadata,
            },
        )

        # Trigger conversion asynchronously (don't wait for it)
        # The frontend will poll /api/status to monitor progress
        asyncio.create_task(mcp_server.send_message(start_msg))

        response_status = "ready_to_convert"
    elif needs_more_info:
        # Continue multi-turn conversation - frontend keeps chat active
        response_status = "conversation_continues"
    else:
        # Conversation complete but user hasn't confirmed ready yet
        response_status = "conversation_complete"

    # Override with explicit status from result if provided (trust the agent)
    response_status = result.get("status", response_status)

    # Return response with explicit status for frontend compatibility
    return {
        "message": result.get("message", "I processed your message but have no specific response."),
        "status": response_status,
        "needs_more_info": needs_more_info,
        "extracted_metadata": result.get("extracted_metadata", {}),
        "ready_to_proceed": ready_to_proceed,
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
    mcp_server = get_or_create_mcp_server()
    state = mcp_server.global_state

    # EDGE CASE FIX #1: Check if LLM is already processing
    if state.llm_processing:
        return {
            "type": "busy",
            "answer": "I'm still processing your previous message. Please wait a moment...",
            "suggestions": [],
            "actions": [],
        }

    # Acquire LLM lock to prevent concurrent processing
    async with state._llm_lock:
        state.llm_processing = True
        try:
            # Route to general query handler
            query_msg = MCPMessage(
                target_agent="conversation",
                action="general_query",
                context={"query": message},
            )

            response = await mcp_server.send_message(query_msg)
        finally:
            state.llm_processing = False

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
        "can_retry": True,  # Bug #14 fix: Always allow retry
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


@app.get("/api/reports/view")
async def view_html_report():
    """
    View the HTML evaluation report in browser.

    Returns:
        HTML report content for display in browser
    """
    from fastapi.responses import HTMLResponse

    mcp_server = get_or_create_mcp_server()

    if not mcp_server.global_state.output_path:
        raise HTTPException(
            status_code=404,
            detail="No conversion output available",
        )

    output_path_str = str(mcp_server.global_state.output_path).strip()
    if not output_path_str:
        raise HTTPException(
            status_code=404,
            detail="Output path is empty",
        )

    # Find the HTML report file
    output_dir = Path(output_path_str).parent
    output_stem = Path(output_path_str).stem
    html_report = output_dir / f"{output_stem}_evaluation_report.html"

    if html_report.exists():
        # Check if we need to regenerate the report with workflow_trace
        if workflow_trace_path.exists():
            # Load workflow_trace
            with open(workflow_trace_path, 'r') as f:
                workflow_trace = json.load(f)

            # Check if the workflow_trace has metadata_provenance
            if 'metadata_provenance' in workflow_trace:
                # Regenerate the HTML report with the correct workflow_trace
                from services.report_service import ReportService
                from agents.evaluation_agent import EvaluationAgent

                # Extract file info from NWB file
                nwb_path = mcp_server.global_state.output_path
                eval_agent = EvaluationAgent()
                file_info = eval_agent._extract_file_info(nwb_path)

                # MERGE BACK the original provenance from workflow_trace
                # This preserves the detailed AI-parsed provenance instead of generic "file-extracted"
                if 'metadata_provenance' in workflow_trace:
                    file_info['_workflow_provenance'] = workflow_trace['metadata_provenance']

                # Create validation result with file info
                validation_result = {
                    'overall_status': mcp_server.global_state.overall_status.value if mcp_server.global_state.overall_status else 'UNKNOWN',
                    'nwb_file_path': str(nwb_path),
                    'file_info': file_info,
                    'issues': [],
                    'issue_counts': {},
                }

                # Regenerate HTML report with workflow_trace
                report_service = ReportService()
                report_service.generate_html_report(
                    html_report,
                    validation_result,
                    None,  # llm_analysis
                    workflow_trace
                )

                logger.info(f"Regenerated HTML report with workflow_trace from {workflow_trace_path}")

        # Read and return HTML content directly for browser display
        with open(html_report, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)

    raise HTTPException(
        status_code=404,
        detail="No HTML report available. Report may not have been generated yet.",
    )


@app.get("/api/download/report")
async def download_report():
    """
    Download the evaluation report (HTML, PDF, or JSON).

    Returns:
        Report file as download
    """
    mcp_server = get_or_create_mcp_server()

    if not mcp_server.global_state.output_path:
        raise HTTPException(
            status_code=404,
            detail="No conversion output available",
        )

    output_path_str = str(mcp_server.global_state.output_path).strip()
    if not output_path_str:
        raise HTTPException(
            status_code=404,
            detail="Output path is empty",
        )

    # Find the report file
    output_dir = Path(output_path_str).parent
    output_stem = Path(output_path_str).stem

    # Try HTML first (primary format)
    html_report = output_dir / f"{output_stem}_evaluation_report.html"
    if html_report.exists():
        return FileResponse(
            path=str(html_report),
            media_type="text/html",
            filename=html_report.name,
        )

    # Try PDF
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
