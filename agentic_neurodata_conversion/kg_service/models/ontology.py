"""Ontology Term Model.

Represents a term from an ontology (NCBI Taxonomy, UBERON, PATO).
Used for semantic validation of neuroscience metadata fields.

Ontology terms include:
- NCBITaxonomy: Species/organisms (e.g., Mus musculus, Rattus norvegicus)
- UBERON: Anatomical structures (e.g., hippocampus, cerebral cortex)
- PATO: Qualities/attributes (e.g., male, female biological sex)

Each term has a unique ID, label, definition, and synonyms for flexible matching.
"""

from pydantic import BaseModel, Field


class OntologyTerm(BaseModel):
    """Ontology term with synonyms and hierarchy.

    Represents a single term from a biomedical ontology. Terms are organized
    hierarchically with parent-child relationships and support synonym matching
    for flexible user input normalization.

    Attributes:
        term_id: Unique ontology term identifier (e.g., NCBITaxon:10090)
        label: Primary canonical label for the term
        definition: Human-readable definition explaining the term
        synonyms: Alternative labels used for matching user input
        ontology_name: Name of the source ontology
        parent_terms: List of parent term IDs for hierarchical relationships
    """

    term_id: str = Field(
        ...,
        description="Ontology term ID (e.g., NCBITaxon:10090)",
        examples=["NCBITaxon:10090", "UBERON:0002421", "PATO:0000384"],
    )
    label: str = Field(..., description="Primary label for the term", examples=["Mus musculus", "hippocampus", "male"])
    definition: str | None = Field(None, description="Definition of the term")
    synonyms: list[str] = Field(
        default_factory=list,
        description="Alternative labels for the term",
        examples=[["mouse", "house mouse", "lab mouse"]],
    )
    ontology_name: str = Field(..., description="Name of the ontology", examples=["NCBITaxonomy", "UBERON", "PATO"])
    parent_terms: list[str] = Field(
        default_factory=list, description="Parent term IDs (for hierarchy)", examples=[["NCBITaxon:10088"]]
    )

    class Config:
        """Pydantic model configuration with example."""

        json_schema_extra = {
            "example": {
                "term_id": "NCBITaxon:10090",
                "label": "Mus musculus",
                "definition": "House mouse - common laboratory model organism",
                "synonyms": ["mouse", "house mouse", "laboratory mouse", "lab mouse", "mice"],
                "ontology_name": "NCBITaxonomy",
                "parent_terms": ["NCBITaxon:10088"],
            }
        }
