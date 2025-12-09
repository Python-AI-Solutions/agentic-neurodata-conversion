"""KG Service FastAPI Application.

Main entry point for Knowledge Graph service.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_neurodata_conversion.kg_service.api.v1 import infer, normalize, observations, semantic_validate, validate
from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    settings = get_settings()
    neo4j_conn = get_neo4j_connection(
        uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password
    )

    try:
        await neo4j_conn.connect()
        logger.info("KG Service started successfully")
        yield
    finally:
        # Shutdown
        await neo4j_conn.close()
        logger.info("KG Service shut down")


# Create FastAPI app
app = FastAPI(
    title="NWB Knowledge Graph Service",
    description="Ontology-based metadata validation for neuroscience data",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(normalize.router)
app.include_router(validate.router)
app.include_router(semantic_validate.router)
app.include_router(observations.router)
app.include_router(infer.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    neo4j_conn = get_neo4j_connection(
        uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password
    )

    neo4j_healthy = await neo4j_conn.health_check()

    return {"status": "healthy" if neo4j_healthy else "unhealthy", "neo4j": neo4j_healthy, "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "NWB Knowledge Graph",
        "version": "1.0.0",
        "endpoints": [
            "/api/v1/normalize",
            "/api/v1/validate",
            "/api/v1/semantic-validate",
            "/api/v1/observations",
            "/api/v1/infer",
            "/health",
        ],
    }
