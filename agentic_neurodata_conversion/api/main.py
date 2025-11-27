"""FastAPI application for agentic neurodata conversion.

Main API server with REST endpoints and WebSocket support.

All endpoints have been modularized into routers:
- conversion: File upload and conversion workflow
- status: Status, logs, and metadata provenance
- downloads: NWB file and report downloads
- chat: Conversational interaction with LLM
- validation: Validation results and corrections
- health: Health checks and session management
- websocket: Real-time WebSocket communication
"""

import logging
import os
import tempfile
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Import all routers
from agentic_neurodata_conversion.api.routers import (
    chat_router,
    conversion_router,
    downloads_router,
    health_router,
    status_router,
    validation_router,
    websocket_router,
)

# Import conversion router to set upload directory
from agentic_neurodata_conversion.api.routers.conversion import set_upload_dir


async def startup_event():
    """Validate environment configuration on startup.

    Raises:
        ValueError: If required environment variables are missing
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required. Please set it in your .env file or environment."
        )

    # Log successful validation
    logger.info("✓ API key validation passed")


# Initialize FastAPI app
app = FastAPI(
    title="Agentic Neurodata Conversion API",
    description="AI-assisted neurodata conversion to NWB format",
    version="0.1.0",
)

# Register startup event handler
app.add_event_handler("startup", startup_event)

# Configuration constants
CORS_CACHE_MAX_AGE_SECONDS = 3600  # 1 hour

# CORS middleware - configurable for different environments
# In production, set CORS_ORIGINS environment variable to restrict access
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Convert "*" string to list for CORSMiddleware
if CORS_ORIGINS == ["*"]:
    logger.warning("⚠️  CORS is configured to allow ALL origins (*)")
    logger.warning("⚠️  Disabling credentials to prevent CSRF attacks")
    logger.warning("⚠️  Set CORS_ORIGINS environment variable in production!")
    allow_origins = ["*"]
    allow_credentials = False  # SECURITY: Never allow credentials with wildcard origins
else:
    allow_origins = [origin.strip() for origin in CORS_ORIGINS]
    allow_credentials = True  # Safe to allow credentials with specific origins
    logger.info(f"✓ CORS configured for specific origins: {allow_origins}")
    logger.info(f"✓ Credentials allowed: {allow_credentials}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    max_age=CORS_CACHE_MAX_AGE_SECONDS,
)

# Global state - upload directory
_upload_dir: Path = Path(tempfile.gettempdir()) / "nwb_uploads"
_upload_dir.mkdir(exist_ok=True)

# Set upload directory for conversion router
set_upload_dir(_upload_dir)


# Global exception handlers for consistent error responses
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with user-friendly messages.

    Returns a structured error response with field-level details.
    """
    logger.warning(f"Validation error in {request.method} {request.url.path}: {exc}")

    # Build user-friendly error messages
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append({"field": field, "message": message})

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation failed",
            "errors": errors,
            "error_type": "ValidationError",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to ensure consistent error responses.

    Logs the error and returns a standardized JSON error response.
    """
    logger.error(f"Unhandled exception in {request.method} {request.url.path}: {exc}", exc_info=True)

    # Don't expose internal error details in production
    error_detail = str(exc) if os.getenv("DEBUG", "false").lower() == "true" else "An internal server error occurred"

    return JSONResponse(
        status_code=500,
        content={"detail": error_detail, "error_type": type(exc).__name__, "path": str(request.url.path)},
    )


# Include all routers
app.include_router(health_router)  # Root and health endpoints (no prefix)
app.include_router(conversion_router)  # /api/upload, /api/start-conversion
app.include_router(status_router)  # /api/status, /api/logs, /api/metadata-provenance
app.include_router(downloads_router)  # /api/download/*, /api/reports/view
app.include_router(chat_router)  # /api/chat, /api/chat/smart, /api/user-input
app.include_router(validation_router)  # /api/validation, /api/retry-approval, /api/improvement-decision
app.include_router(websocket_router)  # /ws


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # nosec B104 - required for Docker/network access in development
        port=8000,
        reload=True,
    )
