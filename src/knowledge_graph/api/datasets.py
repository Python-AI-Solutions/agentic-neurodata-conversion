"""
Datasets API endpoints.

Constitutional compliance: NWB file limit validation, 30-second timeout.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
import logging
from pathlib import Path
from ..models.dataset import Dataset
from ..services.triple_store import TripleStoreService
from ..services.nwb_extractor import NWBExtractor
from .sparql import get_triple_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


class CreateDatasetRequest(BaseModel):
    """Dataset creation request model."""

    title: str
    description: Optional[str] = None
    nwb_files: List[str]
    lab_id: Optional[str] = None
    protocol_id: Optional[str] = None
    extract_nwb_metadata: bool = True  # Enable rich NWB metadata extraction


class DatasetResponse(BaseModel):
    """Dataset response model."""

    dataset_id: str
    title: str
    description: Optional[str]
    nwb_files: List[str]
    lab_id: Optional[str]
    protocol_id: Optional[str]
    status: str
    created_at: str


class DatasetListResponse(BaseModel):
    """Dataset list response model."""

    datasets: List[DatasetResponse]
    total: int
    limit: int
    offset: int


@router.post("/", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    request: CreateDatasetRequest,
    triple_store: TripleStoreService = Depends(get_triple_store)
) -> DatasetResponse:
    """
    Create a new dataset with constitutional compliance.

    Constitutional requirements:
    - Max 100 NWB files per dataset
    - Dataset creation within 30 seconds
    - LinkML schema validation
    """
    try:
        logger.info(f"Creating dataset: {request.title}")

        # Create dataset model with constitutional validation
        dataset = Dataset(
            title=request.title,
            description=request.description,
            nwb_files=request.nwb_files,
            lab_id=request.lab_id,
            protocol_id=request.protocol_id,
            status="created"
        )

        # Add basic dataset to knowledge graph
        rdf_dict = dataset.to_rdf_dict()
        success = await triple_store.add_dataset_triples(rdf_dict)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to add dataset to knowledge graph"
            )

        # Extract rich NWB metadata if requested
        if request.extract_nwb_metadata and request.nwb_files:
            logger.info("Extracting rich NWB metadata")
            extractor = NWBExtractor()

            for nwb_file in request.nwb_files:
                # Check if file exists
                if Path(nwb_file).exists():
                    try:
                        # Extract comprehensive metadata
                        metadata = extractor.extract_full_metadata(nwb_file)

                        # Create semantic triples
                        dataset_uri = f"kg:dataset/{dataset.dataset_id}"
                        triples = extractor.create_semantic_triples(metadata, dataset_uri)

                        # Add triples to knowledge graph
                        for subject, predicate, obj in triples:
                            await triple_store.store.add((subject, predicate, obj))

                        logger.info(f"Added {len(triples)} metadata triples for {nwb_file}")

                    except Exception as e:
                        logger.warning(f"Failed to extract metadata from {nwb_file}: {e}")
                else:
                    logger.warning(f"NWB file not found: {nwb_file}")


        # Return response
        return DatasetResponse(
            dataset_id=dataset.dataset_id,
            title=dataset.title,
            description=dataset.description,
            nwb_files=dataset.nwb_files,
            lab_id=dataset.lab_id,
            protocol_id=dataset.protocol_id,
            status=dataset.status,
            created_at=dataset.created_at.isoformat()
        )

    except ValueError as e:
        # Constitutional validation errors
        if "100 NWB files" in str(e):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": str(e),
                    "constitutional_violation": "NWB file limit exceeded",
                    "max_files_allowed": 100
                }
            )
        else:
            raise HTTPException(status_code=400, detail={"error": str(e)})

    except Exception as e:
        logger.error(f"Dataset creation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": f"Dataset creation failed: {str(e)}"}
        )


@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    limit: int = Query(10, ge=1, le=100, description="Number of datasets to return"),
    offset: int = Query(0, ge=0, description="Number of datasets to skip"),
    triple_store: TripleStoreService = Depends(get_triple_store)
) -> DatasetListResponse:
    """
    List datasets with pagination.

    Constitutional compliance: Query timeout limits enforced.
    """
    try:
        # Query datasets from knowledge graph
        query = f"""
        PREFIX kg: <http://knowledge-graph.org/ontology/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?dataset ?title ?description ?created WHERE {{
            ?dataset rdf:type kg:Dataset .
            ?dataset kg:title ?title .
            OPTIONAL {{ ?dataset kg:description ?description }}
            OPTIONAL {{ ?dataset kg:createdAt ?created }}
        }}
        ORDER BY DESC(?created)
        LIMIT {limit}
        OFFSET {offset}
        """

        result = await triple_store.execute_sparql_query(query, timeout=10)

        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail={"error": f"Failed to query datasets: {result['error']}"}
            )

        # Convert SPARQL results to dataset responses
        datasets = []
        bindings = result.get("results", {}).get("bindings", [])

        for binding in bindings:
            dataset_uri = binding.get("dataset", {}).get("value", "")
            dataset_id = dataset_uri.split("/")[-1] if "/" in dataset_uri else dataset_uri

            datasets.append(DatasetResponse(
                dataset_id=dataset_id,
                title=binding.get("title", {}).get("value", ""),
                description=binding.get("description", {}).get("value"),
                nwb_files=[],  # Would need separate query for files
                lab_id=None,
                protocol_id=None,
                status="active",
                created_at=binding.get("created", {}).get("value", "")
            ))

        # Get total count
        count_query = """
        PREFIX kg: <http://knowledge-graph.org/ontology/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT (COUNT(?dataset) as ?total) WHERE {
            ?dataset rdf:type kg:Dataset .
        }
        """

        count_result = await triple_store.execute_sparql_query(count_query, timeout=5)
        total = 0
        if not count_result.get("error"):
            count_bindings = count_result.get("results", {}).get("bindings", [])
            if count_bindings:
                total = int(count_bindings[0].get("total", {}).get("value", 0))

        return DatasetListResponse(
            datasets=datasets,
            total=total,
            limit=limit,
            offset=offset
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list datasets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to list datasets: {str(e)}"}
        )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    triple_store: TripleStoreService = Depends(get_triple_store)
) -> DatasetResponse:
    """
    Get specific dataset by ID.

    Constitutional compliance: Query timeout and validation.
    """
    try:
        # Query specific dataset
        query = f"""
        PREFIX kg: <http://knowledge-graph.org/ontology/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?title ?description ?created ?nwbFile ?lab ?protocol WHERE {{
            kg:dataset/{dataset_id} rdf:type kg:Dataset .
            kg:dataset/{dataset_id} kg:title ?title .
            OPTIONAL {{ kg:dataset/{dataset_id} kg:description ?description }}
            OPTIONAL {{ kg:dataset/{dataset_id} kg:createdAt ?created }}
            OPTIONAL {{ kg:dataset/{dataset_id} kg:hasNwbFile ?nwbFile }}
            OPTIONAL {{ kg:dataset/{dataset_id} kg:belongsToLab ?lab }}
            OPTIONAL {{ kg:dataset/{dataset_id} kg:followsProtocol ?protocol }}
        }}
        """

        result = await triple_store.execute_sparql_query(query, timeout=10)

        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail={"error": f"Failed to query dataset: {result['error']}"}
            )

        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            raise HTTPException(
                status_code=404,
                detail={"error": f"Dataset {dataset_id} not found"}
            )

        # Aggregate data from multiple bindings (due to NWB files)
        dataset_data = {
            "title": bindings[0].get("title", {}).get("value", ""),
            "description": bindings[0].get("description", {}).get("value"),
            "created_at": bindings[0].get("created", {}).get("value", ""),
            "nwb_files": [],
            "lab_id": None,
            "protocol_id": None
        }

        for binding in bindings:
            nwb_file = binding.get("nwbFile", {}).get("value")
            if nwb_file and nwb_file not in dataset_data["nwb_files"]:
                dataset_data["nwb_files"].append(nwb_file)

            if binding.get("lab", {}).get("value"):
                dataset_data["lab_id"] = binding["lab"]["value"].split("/")[-1]

            if binding.get("protocol", {}).get("value"):
                dataset_data["protocol_id"] = binding["protocol"]["value"].split("/")[-1]

        return DatasetResponse(
            dataset_id=dataset_id,
            title=dataset_data["title"],
            description=dataset_data["description"],
            nwb_files=dataset_data["nwb_files"],
            lab_id=dataset_data["lab_id"],
            protocol_id=dataset_data["protocol_id"],
            status="active",
            created_at=dataset_data["created_at"]
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get dataset {dataset_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to retrieve dataset: {str(e)}"}
        )