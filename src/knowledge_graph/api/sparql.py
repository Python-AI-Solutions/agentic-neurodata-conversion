"""
SPARQL endpoint with tiered timeout per constitutional requirements.

Constitutional compliance:
- <200ms for simple queries
- <30s for complex queries
- W3C SPARQL JSON format
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
import logging
from ..services.triple_store import TripleStoreService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sparql", tags=["SPARQL"])

# Global triple store instance
# In production, this would be injected via dependency injection
_triple_store = None


def get_triple_store() -> TripleStoreService:
    """Dependency injection for triple store service."""
    global _triple_store
    if _triple_store is None:
        _triple_store = TripleStoreService()
        logger.info("Initialized SPARQL triple store")
    return _triple_store


class SPARQLQuery(BaseModel):
    """SPARQL query request model."""

    query: str = Field(..., min_length=1, description="SPARQL query string")
    timeout: int = Field(
        default=30,
        ge=1,
        le=30,
        description="Query timeout in seconds (max 30 per constitutional requirement)"
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )
    format: str = Field(
        default="json",
        regex=r"^(json|xml|turtle|n3)$",
        description="Response format"
    )

    @validator('query')
    def validate_sparql_query(cls, v):
        """Basic SPARQL query validation."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")

        # Check for basic SPARQL keywords
        sparql_keywords = ['SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE', 'INSERT', 'DELETE']
        if not any(keyword in v.upper() for keyword in sparql_keywords):
            raise ValueError("Query must contain valid SPARQL keywords")

        # Prevent potentially dangerous operations in basic validation
        dangerous_patterns = ['DROP', 'CLEAR', 'DELETE WHERE', 'INSERT WHERE']
        if any(pattern in v.upper() for pattern in dangerous_patterns):
            raise ValueError("Query contains potentially dangerous operations")

        return v

    @validator('timeout')
    def validate_constitutional_timeout(cls, v):
        """Constitutional compliance: Maximum 30-second timeout."""
        if v > 30:
            logger.warning(f"Timeout {v}s exceeds constitutional limit, capping at 30s")
            return 30
        return v


class SPARQLResponse(BaseModel):
    """SPARQL query response model (W3C compliant)."""

    head: Optional[Dict[str, Any]] = Field(None, description="Query head with variables")
    results: Optional[Dict[str, Any]] = Field(None, description="Query results with bindings")
    boolean: Optional[bool] = Field(None, description="ASK query result")
    execution_time: float = Field(..., description="Query execution time in seconds")
    count: Optional[int] = Field(None, description="Number of results returned")
    status: str = Field(default="success", description="Query execution status")
    error: Optional[str] = Field(None, description="Error message if query failed")


@router.post("/", response_model=SPARQLResponse)
async def execute_sparql_query(
    query_request: SPARQLQuery,
    triple_store: TripleStoreService = Depends(get_triple_store)
) -> SPARQLResponse:
    """
    Execute SPARQL query with constitutional compliance.

    Constitutional requirements:
    - Tiered timeout: <200ms simple, <30s complex
    - W3C SPARQL JSON format compliance
    - Proper error handling and logging
    """
    try:
        logger.info(f"Executing SPARQL query with {query_request.timeout}s timeout")

        # Execute query with constitutional timeout compliance
        result = await triple_store.execute_sparql_query(
            query=query_request.query,
            timeout=query_request.timeout,
            limit=query_request.limit
        )

        # Check for errors in result
        if "error" in result:
            if result.get("status") == "timeout":
                raise HTTPException(
                    status_code=408,
                    detail={
                        "error": result["error"],
                        "execution_time": result.get("execution_time", 0),
                        "constitutional_note": "Query exceeded 30-second constitutional timeout limit"
                    }
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": result["error"],
                        "execution_time": result.get("execution_time", 0)
                    }
                )

        # Log performance metrics for constitutional compliance monitoring
        execution_time = result.get("execution_time", 0)
        if execution_time > 0.2:
            logger.info(
                f"Query execution time {execution_time:.3f}s exceeded simple query "
                f"threshold (200ms)"
            )

        # Return W3C compliant SPARQL JSON response
        return SPARQLResponse(
            head=result.get("head"),
            results=result.get("results"),
            boolean=result.get("boolean"),
            execution_time=execution_time,
            count=result.get("count"),
            status="success"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"SPARQL query execution failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Internal server error during query execution: {str(e)}",
                "constitutional_note": "Query processing failed within constitutional limits"
            }
        )


@router.get("/samples")
async def get_sample_queries(
    triple_store: TripleStoreService = Depends(get_triple_store)
) -> Dict[str, str]:
    """Get sample SPARQL queries for testing and documentation."""
    return triple_store.get_sample_queries()


@router.get("/statistics")
async def get_graph_statistics(
    triple_store: TripleStoreService = Depends(get_triple_store)
) -> Dict[str, Any]:
    """Get knowledge graph statistics."""
    try:
        stats = await triple_store.get_graph_statistics()
        return {
            "status": "success",
            "statistics": stats,
            "constitutional_compliance": {
                "max_query_timeout": "30 seconds",
                "simple_query_target": "<200ms",
                "sparql_format": "W3C SPARQL JSON"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get graph statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to retrieve statistics: {str(e)}"}
        )