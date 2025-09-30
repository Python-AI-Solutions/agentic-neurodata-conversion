"""
Dataset model with NWB file limit validation.

Constitutional requirement: Max 100 NWB files per dataset.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import uuid4


class Dataset(BaseModel):
    """
    Dataset entity representing a collection of NWB files.

    Constitutional compliance: NWB file limit validation enforced.
    """

    dataset_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique dataset identifier")
    title: str = Field(..., min_length=1, description="Dataset title")
    description: Optional[str] = Field(None, description="Dataset description")
    nwb_files: List[str] = Field(..., description="List of NWB file paths")
    lab_id: Optional[str] = Field(None, description="Associated lab identifier")
    protocol_id: Optional[str] = Field(None, description="Associated protocol identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    status: str = Field(default="created", description="Dataset status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Semantic web properties
    rdf_type: str = Field(default="kg:Dataset", description="RDF type for semantic web")
    context: Dict[str, str] = Field(
        default_factory=lambda: {
            "@context": {
                "kg": "http://knowledge-graph.org/ontology/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
            }
        },
        description="JSON-LD context"
    )

    @validator('nwb_files')
    def validate_nwb_file_limit(cls, v):
        """
        Constitutional requirement: Max 100 NWB files per dataset.
        """
        if len(v) > 100:
            raise ValueError(
                f"Dataset cannot contain more than 100 NWB files. "
                f"Current count: {len(v)}. This is a constitutional limit."
            )
        if len(v) == 0:
            raise ValueError("Dataset must contain at least one NWB file.")
        return v

    @validator('nwb_files')
    def validate_nwb_file_extensions(cls, v):
        """Validate that all files have .nwb extension."""
        for file_path in v:
            if not file_path.endswith('.nwb'):
                raise ValueError(f"File {file_path} is not an NWB file (.nwb extension required)")
        return v

    def to_rdf_dict(self) -> Dict[str, Any]:
        """Convert to RDF-compatible dictionary format."""
        return {
            "@context": self.context["@context"],
            "@id": f"kg:dataset/{self.dataset_id}",
            "@type": self.rdf_type,
            "kg:title": self.title,
            "kg:description": self.description,
            "kg:hasNwbFiles": self.nwb_files,
            "kg:belongsToLab": f"kg:lab/{self.lab_id}" if self.lab_id else None,
            "kg:followsProtocol": f"kg:protocol/{self.protocol_id}" if self.protocol_id else None,
            "kg:createdAt": self.created_at.isoformat(),
            "kg:status": self.status
        }

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }