"""Shared dependencies for API endpoints.

Includes MCP server initialization, file utilities, and helper functions.
"""

import logging
import os
import re
import threading
from pathlib import Path

from fastapi import HTTPException

from agentic_neurodata_conversion.agents import (
    register_conversation_agent,
    register_conversion_agent,
    register_evaluation_agent,
)
from agentic_neurodata_conversion.services import MCPServer, create_llm_service, get_mcp_server

logger = logging.getLogger(__name__)

# Global MCP server instance
_mcp_server = None
_mcp_server_lock = threading.Lock()


def get_or_create_mcp_server() -> MCPServer:
    """Get or create the MCP server with all agents registered."""
    global _mcp_server

    if _mcp_server is None:
        with _mcp_server_lock:
            # Double-check pattern to prevent race condition
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


async def generate_upload_welcome_message(
    filename: str,
    file_size_mb: float,
    llm_service,
) -> dict:
    """Use LLM to generate a welcoming, informative upload response.

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
    except Exception as e:
        # Log the error but don't fail the upload - LLM detection is optional
        logger.warning(f"LLM detection failed, using defaults: {e}", exc_info=True)
        return {
            "message": "File uploaded successfully, conversion started",
            "detected_info": {},
        }


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove path separators and parent directory references
    filename = os.path.basename(filename)
    filename = filename.replace("..", "")
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")

    # Remove potentially dangerous characters
    filename = re.sub(r"[^\w\s\-.]", "", filename)

    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name_part, ext = os.path.splitext(filename)
        filename = name_part[: max_length - len(ext)] + ext

    # Ensure it's not empty after sanitization
    if not filename or filename in (".", ".."):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: filename cannot be empty or contain only dots",
        )

    return filename


def validate_safe_path(file_path: Path, base_dir: Path) -> Path:
    """Validate that a file path is within the allowed base directory.

    Prevents directory traversal attacks.

    Args:
        file_path: Path to validate
        base_dir: Base directory that file must be within

    Returns:
        Validated path

    Raises:
        HTTPException: If path escapes base directory
    """
    # Resolve to absolute paths
    file_path = file_path.resolve()
    base_dir = base_dir.resolve()

    # Check if file_path is within base_dir
    try:
        file_path.relative_to(base_dir)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid path: path traversal detected. Path must be within allowed directory.",
        )

    return file_path
