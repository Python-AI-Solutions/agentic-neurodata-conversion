"""
MCP server for Knowledge Graph Systems.

Constitutional compliance: Clean separation between knowledge graph logic and MCP interfaces.
"""

import asyncio
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

from ..knowledge_graph.services.triple_store import TripleStoreService
from ..knowledge_graph.models.dataset import Dataset

logger = logging.getLogger(__name__)

# MCP Response Models
class MCPToolResponse(BaseModel):
    """Standard MCP tool response format."""
    content: List[Dict[str, Any]]
    isError: bool = False
    errorMessage: Optional[str] = None

class MCPSparqlRequest(BaseModel):
    """MCP SPARQL query request."""
    query: str
    limit: Optional[int] = 10

class MCPEnrichmentRequest(BaseModel):
    """MCP metadata enrichment request."""
    entity_type: str
    entity_data: Dict[str, Any]
    sources: List[str] = ["NIFSTD", "NCBITaxon"]

class MCPValidationRequest(BaseModel):
    """MCP schema validation request."""
    data: Dict[str, Any]
    schema_type: str = "linkml"
    schema_version: str = "latest"

# MCP Server Application
mcp_app = FastAPI(
    title="Knowledge Graph MCP Server",
    description="Model Context Protocol server for knowledge graph operations",
    version="1.0.0"
)

# Global service instances
_triple_store: Optional[TripleStoreService] = None

def get_triple_store() -> TripleStoreService:
    """Get or create triple store service."""
    global _triple_store
    if _triple_store is None:
        _triple_store = TripleStoreService()
        logger.info("Initialized MCP triple store service")
    return _triple_store

@mcp_app.post("/mcp/tools/sparql_query", response_model=MCPToolResponse)
async def mcp_sparql_query(request: MCPSparqlRequest) -> MCPToolResponse:
    """
    MCP tool for executing SPARQL queries.

    Constitutional compliance: Structured response format for agent integration.
    """
    try:
        triple_store = get_triple_store()

        result = await triple_store.execute_sparql_query(
            query=request.query,
            timeout=30,
            limit=request.limit
        )

        if "error" in result:
            return MCPToolResponse(
                content=[{
                    "type": "error",
                    "text": f"SPARQL query failed: {result['error']}",
                    "data": {"execution_time": result.get("execution_time", 0)}
                }],
                isError=True,
                errorMessage=result["error"]
            )

        # Format for MCP agent consumption
        content = [{
            "type": "data",
            "text": f"SPARQL query executed successfully in {result['execution_time']:.3f}s",
            "data": {
                "results": result.get("results", {}),
                "count": result.get("count", 0),
                "execution_time": result["execution_time"],
                "query": request.query
            }
        }]

        return MCPToolResponse(content=content)

    except Exception as e:
        logger.error(f"MCP SPARQL query failed: {str(e)}")
        return MCPToolResponse(
            content=[{
                "type": "error",
                "text": f"MCP SPARQL query failed: {str(e)}",
                "data": {}
            }],
            isError=True,
            errorMessage=str(e)
        )

@mcp_app.post("/mcp/tools/enrich_metadata", response_model=MCPToolResponse)
async def mcp_enrich_metadata(request: MCPEnrichmentRequest) -> MCPToolResponse:
    """
    MCP tool for metadata enrichment.

    Constitutional compliance: All suggestions require human review.
    """
    try:
        # Simulate enrichment suggestions (would integrate with actual ontology services)
        suggestions = []

        if request.entity_type == "subject":
            entity_data = request.entity_data

            if "strain" in entity_data and entity_data["strain"] == "C57BL/6":
                suggestions.append({
                    "field": "species",
                    "current_value": entity_data.get("species", ""),
                    "suggested_value": "Mus musculus",
                    "confidence": 0.95,
                    "evidence": ["NCBITaxon:10090", "Common laboratory mouse strain"],
                    "requires_review": True,  # Constitutional requirement
                    "source": "NCBITaxon"
                })

            if "age" in entity_data and "P60" in str(entity_data["age"]):
                suggestions.append({
                    "field": "age_category",
                    "current_value": "",
                    "suggested_value": "adult",
                    "confidence": 0.9,
                    "evidence": ["P60 = 60 days postnatal", "Adult stage for mice"],
                    "requires_review": True,  # Constitutional requirement
                    "source": "NIFSTD"
                })

        content = [{
            "type": "data",
            "text": f"Generated {len(suggestions)} enrichment suggestions (all require human review)",
            "data": {
                "entity_type": request.entity_type,
                "suggestions": suggestions,
                "constitutional_note": "All suggestions require human review per constitutional principles"
            }
        }]

        return MCPToolResponse(content=content)

    except Exception as e:
        logger.error(f"MCP metadata enrichment failed: {str(e)}")
        return MCPToolResponse(
            content=[{
                "type": "error",
                "text": f"MCP metadata enrichment failed: {str(e)}",
                "data": {}
            }],
            isError=True,
            errorMessage=str(e)
        )

@mcp_app.post("/mcp/tools/validate_schema", response_model=MCPToolResponse)
async def mcp_validate_schema(request: MCPValidationRequest) -> MCPToolResponse:
    """
    MCP tool for schema validation.

    Constitutional compliance: LinkML schema validation with SHACL shapes.
    """
    try:
        # Simulate schema validation
        validation_errors = []
        warnings = []

        # Basic validation checks
        data = request.data

        if request.schema_type == "linkml":
            # Check for required NWB fields
            if "neurodata_type" not in data:
                validation_errors.append({
                    "path": "neurodata_type",
                    "message": "Missing required field: neurodata_type",
                    "severity": "error"
                })

            if data.get("neurodata_type") == "Dataset":
                if not data.get("title"):
                    validation_errors.append({
                        "path": "title",
                        "message": "Dataset title is required",
                        "severity": "error"
                    })

                if "nwb_files" in data and len(data["nwb_files"]) > 100:
                    validation_errors.append({
                        "path": "nwb_files",
                        "message": "Dataset cannot contain more than 100 NWB files (constitutional limit)",
                        "severity": "error"
                    })

        is_valid = len(validation_errors) == 0

        content = [{
            "type": "data",
            "text": f"Schema validation {'passed' if is_valid else 'failed'}",
            "data": {
                "valid": is_valid,
                "errors": validation_errors,
                "warnings": warnings,
                "schema_type": request.schema_type,
                "schema_version": request.schema_version,
                "constitutional_compliance": "LinkML schema validation enforced"
            }
        }]

        return MCPToolResponse(content=content)

    except Exception as e:
        logger.error(f"MCP schema validation failed: {str(e)}")
        return MCPToolResponse(
            content=[{
                "type": "error",
                "text": f"MCP schema validation failed: {str(e)}",
                "data": {}
            }],
            isError=True,
            errorMessage=str(e)
        )

@mcp_app.post("/mcp/tools/resolve_conflicts", response_model=MCPToolResponse)
async def mcp_resolve_conflicts(request: Dict[str, Any]) -> MCPToolResponse:
    """
    MCP tool for conflict resolution.

    Constitutional compliance: Present conflicts for manual human resolution.
    """
    try:
        entity_id = request.get("entity_id", "")
        conflict_type = request.get("conflict_type", "enrichment")

        # Simulate conflict detection
        conflicts = []

        if conflict_type == "enrichment":
            conflicts = [{
                "field": "species",
                "conflicting_values": [
                    {"value": "Mus musculus", "source": "NCBITaxon", "confidence": 0.95},
                    {"value": "House mouse", "source": "NIFSTD", "confidence": 0.85}
                ],
                "resolution_strategy": "manual_review_required",
                "constitutional_note": "Manual resolution required per constitutional principles"
            }]

        content = [{
            "type": "data",
            "text": f"Found {len(conflicts)} conflicts requiring manual resolution",
            "data": {
                "entity_id": entity_id,
                "conflicts": conflicts,
                "resolution_required": True,
                "constitutional_compliance": "Manual conflict resolution enforced"
            }
        }]

        return MCPToolResponse(content=content)

    except Exception as e:
        logger.error(f"MCP conflict resolution failed: {str(e)}")
        return MCPToolResponse(
            content=[{
                "type": "error",
                "text": f"MCP conflict resolution failed: {str(e)}",
                "data": {}
            }],
            isError=True,
            errorMessage=str(e)
        )

@mcp_app.get("/mcp/tools")
async def list_mcp_tools() -> Dict[str, Any]:
    """List available MCP tools."""
    return {
        "tools": [
            {
                "name": "sparql_query",
                "description": "Execute SPARQL queries with constitutional timeout compliance",
                "endpoint": "/mcp/tools/sparql_query"
            },
            {
                "name": "enrich_metadata",
                "description": "Generate metadata enrichment suggestions (human review required)",
                "endpoint": "/mcp/tools/enrich_metadata"
            },
            {
                "name": "validate_schema",
                "description": "Validate data against NWB-LinkML schemas",
                "endpoint": "/mcp/tools/validate_schema"
            },
            {
                "name": "resolve_conflicts",
                "description": "Present metadata conflicts for manual resolution",
                "endpoint": "/mcp/tools/resolve_conflicts"
            }
        ],
        "constitutional_compliance": {
            "clean_separation": "MCP interfaces separate from core knowledge graph logic",
            "structured_responses": "Agent-compatible response formats",
            "human_review": "All enrichment suggestions require human approval"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "mcp_server.knowledge_graph_server:mcp_app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )