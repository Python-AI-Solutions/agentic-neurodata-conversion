"""API routers for the Agentic Neurodata Conversion API.

Modular router organization following FastAPI best practices:
- conversion: File upload and conversion workflow
- status: Status, logs, and metadata provenance
- downloads: NWB file and report downloads
- chat: Conversational interaction with LLM
- validation: Validation results and corrections
- health: Health checks and session management
- websocket: Real-time WebSocket communication
"""

from .chat import router as chat_router
from .conversion import router as conversion_router
from .downloads import router as downloads_router
from .health import router as health_router
from .status import router as status_router
from .validation import router as validation_router
from .websocket import router as websocket_router

__all__ = [
    "conversion_router",
    "status_router",
    "downloads_router",
    "chat_router",
    "validation_router",
    "health_router",
    "websocket_router",
]
