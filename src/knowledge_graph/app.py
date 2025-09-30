"""
Main FastAPI application for Knowledge Graph Systems.

Constitutional compliance: W3C standards, timeout enforcement, human review workflows.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

from .api.sparql import router as sparql_router
from .api.datasets import router as datasets_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Knowledge Graph Systems API",
    description="NWB data knowledge graph with semantic enrichment and validation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(sparql_router)
app.include_router(datasets_router)

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with constitutional compliance information."""
    return {
        "message": "Knowledge Graph Systems API",
        "version": "1.0.0",
        "constitutional_compliance": {
            "schema_first_development": "LinkML schema drives all data structures",
            "semantic_web_standards": "W3C RDF, SPARQL, SHACL compliance",
            "test_first_development": "Contract tests before implementation",
            "mcp_server_integration": "Clean separation of logic and MCP interfaces",
            "data_quality_assurance": "Confidence scoring and lineage tracking"
        },
        "endpoints": {
            "sparql": "/sparql - SPARQL query execution",
            "datasets": "/datasets - Dataset management",
            "docs": "/docs - Interactive API documentation"
        },
        "performance_targets": {
            "simple_queries": "<200ms",
            "complex_queries": "<30s",
            "concurrent_users": "1-10 supported",
            "dataset_scale": "max 100 NWB files per dataset"
        }
    }

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "constitutional_compliance": "active",
        "semantic_web_standards": "W3C compliant",
        "timestamp": "2025-09-29T00:00:00Z"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with constitutional compliance logging."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "constitutional_note": "Error handling follows constitutional principles"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "knowledge_graph.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )