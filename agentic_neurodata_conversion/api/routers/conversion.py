"""Conversion router for file upload and conversion workflow endpoints.

Handles:
- File upload with validation and sanitization
- Conversion workflow initiation
- Multi-file upload support (e.g., SpikeGLX .bin + .meta files)
"""

import hashlib
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from agentic_neurodata_conversion.api.dependencies import (
    get_or_create_mcp_server,
    sanitize_filename,
    validate_safe_path,
)
from agentic_neurodata_conversion.models import (
    LogLevel,
    MCPMessage,
    UploadResponse,
)
from agentic_neurodata_conversion.models.metadata import NWBMetadata
from agentic_neurodata_conversion.models.workflow_state_manager import WorkflowStateManager
from agentic_neurodata_conversion.services import create_llm_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["conversion"])

# Configuration constants
MAX_UPLOAD_SIZE_GB = 5
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_GB * 1024 * 1024 * 1024

# Upload directory
_upload_dir: Path | None = None

# Workflow manager
_workflow_manager = WorkflowStateManager()


def set_upload_dir(upload_dir: Path):
    """Set the upload directory for file storage.

    Args:
        upload_dir: Path to directory for storing uploaded files
    """
    global _upload_dir
    _upload_dir = upload_dir
    _upload_dir.mkdir(exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    additional_files: list[UploadFile] = File(default=[]),
    metadata: str | None = Form(None),
):
    """Upload neurodata file(s) for conversion. Supports multiple files.

    Args:
        file: Main uploaded file (required)
        additional_files: Additional files (e.g., .meta files for SpikeGLX)
        metadata: Optional JSON metadata string

    Returns:
        Upload confirmation with session info
    """
    if _upload_dir is None:
        raise HTTPException(status_code=500, detail="Upload directory not configured")

    mcp_server = get_or_create_mcp_server()

    # Check if upload is allowed in current state
    if not _workflow_manager.can_accept_upload(mcp_server.global_state):
        status_str = mcp_server.global_state.status.value if mcp_server.global_state.status else "unknown"
        raise HTTPException(
            status_code=409,
            detail=f"Cannot upload while {status_str}. Please wait or reset.",
        )

    # Validate file count and types (prevent multiple separate datasets)
    total_files = 1 + len(additional_files)

    # Check for too many files
    if total_files > 10:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files uploaded ({total_files}). Maximum 10 files allowed. "
            "If you have multiple datasets, please upload them one at a time.",
        )

    # Check for multiple primary data files (suggests multiple separate datasets)
    primary_extensions = {".bin", ".dat", ".continuous", ".h5", ".nwb"}
    all_files_list = [file] + additional_files
    primary_files = [f for f in all_files_list if any(f.filename.lower().endswith(ext) for ext in primary_extensions)]

    if len(primary_files) > 1:
        # Check if this is a legitimate multi-file format
        filenames = [f.filename for f in primary_files]
        is_spikeglx_set = any(".ap.bin" in fn or ".lf.bin" in fn for fn in filenames)
        is_openephys_set = all(".continuous" in fn for fn in filenames)

        if not (is_spikeglx_set or is_openephys_set):
            raise HTTPException(
                status_code=400,
                detail=f"Multiple data files detected ({len(primary_files)}). "
                f"This system processes ONE recording session at a time. "
                f"Please upload files for a single session only. "
                f"Files: {', '.join(filenames)}",
            )

    # Validate file type
    ALLOWED_EXTENSIONS = {
        ".abf",
        ".avi",
        ".bin",
        ".continuous",
        ".dat",
        ".json",
        ".meta",
        ".ncs",
        ".nev",
        ".ntt",
        ".nwb",
        ".plx",
        ".rhd",
        ".rhs",
        ".tif",
    }
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Validate file size
    content = await file.read()
    await file.close()  # Explicitly close file handle after reading

    # Validate content was successfully read
    if content is None:
        raise HTTPException(status_code=400, detail="Failed to read file content")

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File too large: {len(content) / (1024**3):.2f}GB. Maximum: {MAX_UPLOAD_SIZE_GB}GB"
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Save main file - sanitize filename to prevent path traversal
    safe_filename = sanitize_filename(file.filename)
    file_path = _upload_dir / safe_filename
    # Validate path is within upload directory (defense in depth)
    file_path = validate_safe_path(file_path, _upload_dir)

    with open(file_path, "wb") as f:
        f.write(content)

    # Save additional files (e.g., .meta files, other companion files)
    uploaded_files = [safe_filename]
    for additional_file in additional_files:
        safe_add_filename = sanitize_filename(additional_file.filename)
        add_file_path = _upload_dir / safe_add_filename
        # Validate path is within upload directory
        add_file_path = validate_safe_path(add_file_path, _upload_dir)

        add_content = await additional_file.read()
        with open(add_file_path, "wb") as f:
            f.write(add_content)
        uploaded_files.append(safe_add_filename)

    # Validate that SpikeGLX files have their required companion .meta files
    if ".ap.bin" in safe_filename or ".lf.bin" in safe_filename or ".nidq.bin" in safe_filename:
        meta_filename = safe_filename.replace(".bin", ".meta")
        meta_file_path = _upload_dir / meta_filename

        # Check if .meta file was uploaded
        if not meta_file_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"SpikeGLX .bin files require a matching .meta file. "
                f"Please upload both '{safe_filename}' and '{meta_filename}' together. "
                f"The .meta file contains essential recording parameters (sampling rate, "
                f"channel count, probe configuration) needed for accurate conversion.",
            )

    # Validate OpenEphys files have required companion files
    if safe_filename == "structure.oebin":
        # New OpenEphys format - should have accompanying data files
        if len(additional_files) == 0:
            raise HTTPException(
                status_code=400,
                detail="OpenEphys format requires multiple files. When uploading 'structure.oebin', "
                "please also upload the accompanying .dat files and other recording files from the same session folder. "
                "All files from the recording session are needed for complete data extraction.",
            )
    elif safe_filename == "settings.xml":
        # Old OpenEphys format - should have .continuous files
        continuous_files = [f for f in additional_files if ".continuous" in f.filename]
        if len(continuous_files) == 0:
            raise HTTPException(
                status_code=400,
                detail="Old OpenEphys format requires .continuous data files. When uploading 'settings.xml', "
                "please also upload all .continuous files from the same recording session. "
                "All files are needed for complete data extraction.",
            )

    # Calculate checksum of main file
    checksum = hashlib.sha256(content).hexdigest()

    # Check if in active conversation
    in_active_conversation = _workflow_manager.is_in_active_conversation(mcp_server.global_state)

    if not in_active_conversation:
        # Reset state for new upload session
        # This prevents retry counter and metadata flags from carrying over
        mcp_server.global_state.correction_attempt = 0
        mcp_server.global_state.user_declined_fields.clear()
        mcp_server.global_state.metadata_requests_count = 0
        mcp_server.global_state.user_wants_minimal = False
        mcp_server.global_state.user_wants_sequential = False
        mcp_server.global_state.validation_status = None
        mcp_server.global_state.overall_status = None
        mcp_server.global_state.conversation_history = []  # Clear old conversations
        # Reset custom metadata flag to ensure proper workflow
        if "_custom_metadata_prompted" in mcp_server.global_state.metadata:
            del mcp_server.global_state.metadata["_custom_metadata_prompted"]
    else:
        # Preserve conversation state but update file paths
        mcp_server.global_state.add_log(
            LogLevel.INFO,
            "Re-upload detected during active conversation - preserving conversation state",
            {"previous_request_count": mcp_server.global_state.metadata_requests_count},
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
            # Strict validation with Pydantic
            # We validate strictly when metadata is provided, but allow partial metadata
            # Required fields will be enforced before conversion starts
            try:
                # Allow partial metadata by making fields optional during upload
                # Full validation happens before conversion in conversation_agent
                validated_metadata = NWBMetadata(**metadata_raw)
                # Convert validated model back to dict, preserving validation state
                # Keep all fields including None to track what was provided vs omitted
                metadata_dict = validated_metadata.model_dump(exclude_unset=True)
                # Also store which fields were explicitly set by user for validation tracking
                metadata_dict["_user_provided_fields"] = set(metadata_raw.keys())
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
                        "hint": "Please check the required fields and formats. See /docs for examples.",
                    },
                )

    # DO NOT auto-start conversion on upload
    # According to requirements, the system should:
    # 1. Upload file
    # 2. Acknowledge upload
    # 3. Wait for user to explicitly start conversion

    # Skip re-acknowledging if already in active conversation
    if in_active_conversation:
        mcp_server.global_state.add_log(
            LogLevel.INFO,
            "Upload during active conversation - skipping duplicate acknowledgment",
            {
                "status": str(mcp_server.global_state.status),
                "conversation_type": mcp_server.global_state.conversation_type,
            },
        )

        # Return the current conversation state
        current_message = (
            mcp_server.global_state.llm_message
            or "Please continue the conversation to provide the requested information."
        )

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
    if ".meta" in safe_filename:
        # If user uploaded .meta file first, find the corresponding .bin file
        bin_filename = safe_filename.replace(".meta", ".bin")
        bin_path = _upload_dir / bin_filename
        if bin_path.exists():
            conversion_input_path = str(_upload_dir)  # Use directory for SpikeGLX
        else:
            # .bin file doesn't exist yet, use .meta for now
            conversion_input_path = str(file_path)
    elif ".ap.bin" in safe_filename or ".lf.bin" in safe_filename:
        # For .bin files, use the directory path for SpikeGLX detection
        conversion_input_path = str(_upload_dir)

    # Store the upload information in state WITHOUT starting conversion
    mcp_server.global_state.input_path = conversion_input_path
    mcp_server.global_state.metadata.update(metadata_dict)
    mcp_server.global_state.pending_conversion_input_path = conversion_input_path

    mcp_server.global_state.add_log(
        LogLevel.INFO,
        "File uploaded successfully - awaiting user command to start conversion",
        {
            "file": file.filename,
            "size_mb": len(content) / (1024 * 1024),
            "checksum": checksum,
            "conversion_input_path": conversion_input_path,
        },
    )

    # Generate LLM-powered welcome message that DOES NOT auto-start conversion
    file_size_mb = len(content) / (1024 * 1024)

    # Get LLM service
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

            output_schema = {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}

            response = await llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            welcome_message = response.get(
                "message", "File uploaded successfully! Ready to start conversion when you are."
            )
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
        uploaded_files=[safe_filename],
        conversation_active=False,
    )


@router.post("/start-conversion")
async def start_conversion():
    """Start the conversion workflow after file upload.

    This triggers the Conversation Agent to:
    1. Validate metadata
    2. Request missing fields if needed
    3. Start conversion once metadata is complete

    Returns:
        Response with status
    """
    mcp_server = get_or_create_mcp_server()

    # Check if conversion can be started in current state
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
        # Include validation/error context in response
        error_detail = {
            "message": response.error.get("message", "Failed to start conversion"),
            "error_code": response.error.get("error_code", "UNKNOWN_ERROR"),
        }

        # Add validation context if available
        if "error_context" in response.error:
            error_detail["context"] = response.error["error_context"]

        raise HTTPException(
            status_code=500,
            detail=error_detail,
        )

    return {
        "message": "Conversion workflow started",
        "status": mcp_server.global_state.status.value if mcp_server.global_state.status else "unknown",
    }
