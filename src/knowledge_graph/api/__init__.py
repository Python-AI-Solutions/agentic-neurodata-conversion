"""
FastAPI endpoints for knowledge graph operations.

Sequential implementation required due to shared FastAPI app.
"""

from .sparql import router as sparql_router
from .datasets import router as datasets_router

__all__ = [
    "sparql_router",
    "datasets_router"
]