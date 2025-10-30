"""
Download REST API endpoints for serving generated files.

This module provides secure endpoints for:
- Downloading NWB files
- Downloading validation reports
- Serving files from configured output directory

All endpoints validate file paths to prevent directory traversal attacks.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from agentic_neurodata_conversion.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["downloads"], prefix="/api/v1/downloads")


def _validate_file_path(file_type: str, filename: str) -> Path:
    """
    Validate file path and prevent directory traversal attacks.

    Args:
        file_type: Type of file ("nwb" or "report")
        filename: Name of the file to serve

    Returns:
        Validated absolute Path object

    Raises:
        HTTPException: If path is invalid or file doesn't exist
    """
    # Validate file type
    if file_type not in ("nwb", "report"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file_type}. Must be 'nwb' or 'report'",
        )

    # Prevent directory traversal
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: directory traversal not allowed",
        )

    # Determine subdirectory based on file type
    subdir = "nwb_files" if file_type == "nwb" else "reports"

    # Build absolute path
    base_path = Path(settings.filesystem_output_base_path).resolve()
    file_path = (base_path / subdir / filename).resolve()

    # Verify the resolved path is still within the allowed directory
    if not str(file_path).startswith(str(base_path)):
        raise HTTPException(
            status_code=400,
            detail="Invalid file path: attempted directory traversal",
        )

    # Check file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}",
        )

    # Check it's actually a file
    if not file_path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a file: {filename}",
        )

    return file_path


@router.get("/nwb/{filename}")
async def download_nwb_file(filename: str):
    """
    Download an NWB file by filename.

    Args:
        filename: Name of the NWB file (e.g., "session_123.nwb")

    Returns:
        FileResponse with the NWB file

    Raises:
        HTTPException: 400 for invalid paths, 404 if file not found
    """
    try:
        file_path = _validate_file_path("nwb", filename)
        logger.info(f"Serving NWB file: {file_path}")

        return FileResponse(
            path=str(file_path),
            media_type="application/octet-stream",
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving NWB file {filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to serve file: {str(e)}",
        )


@router.get("/report/{filename}")
async def download_report(filename: str):
    """
    Download a validation report by filename.

    Args:
        filename: Name of the report file (e.g., "validation_report_123.json")

    Returns:
        FileResponse with the report file

    Raises:
        HTTPException: 400 for invalid paths, 404 if file not found
    """
    try:
        file_path = _validate_file_path("report", filename)
        logger.info(f"Serving report file: {file_path}")

        # Determine media type based on extension
        media_type = "application/json"
        if filename.endswith(".html"):
            media_type = "text/html"
        elif filename.endswith(".pdf"):
            media_type = "application/pdf"

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving report {filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to serve file: {str(e)}",
        )
