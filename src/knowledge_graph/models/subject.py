"""
Subject model with species mapping.

Constitutional compliance: Species mapping with NCBITaxon ontology integration.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from uuid import uuid4


class Subject(BaseModel):
    """
    Subject entity representing an experimental subject (animal or human).

    Constitutional compliance: Species mapping with confidence scoring.
    """

    subject_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique subject identifier")
    subject_label: str = Field(..., min_length=1, description="Subject label/name")
    description: Optional[str] = Field(None, description="Subject description")

    # Species information with ontology mapping
    species: str = Field(..., description="Species name (common or scientific)")
    species_uri: Optional[str] = Field(None, description="NCBITaxon URI for species")
    species_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score for species mapping"
    )

    # Subject characteristics
    strain: Optional[str] = Field(None, description="Strain/breed information")
    sex: Optional[str] = Field(None, regex=r"^(male|female|unknown)$", description="Subject sex")
    age: Optional[str] = Field(None, description="Age at time of experiment")
    age_unit: Optional[str] = Field(None, regex=r"^(days|weeks|months|years)$", description="Age unit")
    birth_date: Optional[date] = Field(None, description="Birth date")
    weight: Optional[float] = Field(None, gt=0, description="Weight in grams")

    # Experimental context
    genotype: Optional[str] = Field(None, description="Genotype information")
    treatment: Optional[List[str]] = Field(default_factory=list, description="Applied treatments")

    # Metadata and tracking
    lab_id: Optional[str] = Field(None, description="Associated lab identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Semantic web properties
    rdf_type: str = Field(default="kg:Subject", description="RDF type for semantic web")

    @validator('species')
    def validate_species_format(cls, v):
        """Validate species name format."""
        if len(v.strip()) < 2:
            raise ValueError("Species name must be at least 2 characters long")
        return v.strip()

    @validator('species_uri')
    def validate_species_uri(cls, v):
        """Validate NCBITaxon URI format."""
        if v is not None:
            if not v.startswith(('http://purl.obolibrary.org/obo/NCBITaxon_', 'NCBITaxon:')):
                raise ValueError(
                    "Species URI must be a valid NCBITaxon identifier "
                    "(e.g., 'http://purl.obolibrary.org/obo/NCBITaxon_10090' or 'NCBITaxon:10090')"
                )
        return v

    @validator('age')
    def validate_age_format(cls, v):
        """Validate age format (P60, 8 weeks, etc.)."""
        if v is not None:
            # Accept common age formats
            valid_patterns = ['P', 'postnatal day', 'weeks', 'months', 'years']
            if not any(pattern in v.lower() for pattern in valid_patterns):
                # Try to parse as number + unit
                parts = v.split()
                if len(parts) == 2:
                    try:
                        float(parts[0])  # Validate first part is numeric
                        if parts[1].lower() not in ['days', 'weeks', 'months', 'years']:
                            raise ValueError("Age unit must be days, weeks, months, or years")
                    except ValueError:
                        raise ValueError(
                            "Age format not recognized. Use formats like 'P60', '8 weeks', "
                            "'3 months', or '2 years'"
                        )
        return v

    @validator('birth_date')
    def validate_birth_date(cls, v):
        """Validate birth date is not in the future."""
        if v is not None and v > date.today():
            raise ValueError("Birth date cannot be in the future")
        return v

    def get_ncbi_taxon_id(self) -> Optional[str]:
        """Extract NCBITaxon ID from URI."""
        if self.species_uri:
            if self.species_uri.startswith('http://purl.obolibrary.org/obo/NCBITaxon_'):
                return self.species_uri.split('_')[-1]
            elif self.species_uri.startswith('NCBITaxon:'):
                return self.species_uri.split(':')[-1]
        return None

    def to_rdf_dict(self) -> Dict[str, Any]:
        """Convert to RDF-compatible dictionary format."""
        rdf_dict = {
            "@id": f"kg:subject/{self.subject_id}",
            "@type": self.rdf_type,
            "kg:label": self.subject_label,
            "kg:description": self.description,
            "kg:hasSpecies": self.species,
            "kg:strain": self.strain,
            "kg:sex": self.sex,
            "kg:age": self.age,
            "kg:weight": self.weight,
            "kg:genotype": self.genotype,
            "kg:belongsToLab": f"kg:lab/{self.lab_id}" if self.lab_id else None,
        }

        # Add ontology mapping if available
        if self.species_uri:
            rdf_dict["kg:hasSpeciesOntology"] = self.species_uri
            rdf_dict["kg:speciesConfidence"] = self.species_confidence

        # Add treatments if any
        if self.treatment:
            rdf_dict["kg:hasTreatments"] = self.treatment

        return rdf_dict

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }