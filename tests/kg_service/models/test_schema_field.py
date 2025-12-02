"""Schema Field Model Tests.

Tests for SchemaField Pydantic model.
Validates model creation for NWB metadata field definitions.
"""

from agentic_neurodata_conversion.kg_service.models.schema_field import SchemaField


def test_schema_field_creation():
    """Verify SchemaField model creation with all fields."""
    field = SchemaField(
        field_path="subject.species",
        description="Species of subject",
        required=True,
        ontology_governed=True,
        ontology="NCBITaxonomy",
        value_type="string",
        examples=["Mus musculus"],
    )

    assert field.field_path == "subject.species"
    assert field.description == "Species of subject"
    assert field.required is True
    assert field.ontology_governed is True
    assert field.ontology == "NCBITaxonomy"
    assert field.value_type == "string"
    assert len(field.examples) == 1
    assert "Mus musculus" in field.examples


def test_schema_field_optional_ontology():
    """Verify SchemaField works without ontology for non-governed fields."""
    field = SchemaField(
        field_path="general.experimenter",
        description="Name of experimenter",
        required=False,
        ontology_governed=False,
        value_type="string",
        examples=["John Doe"],
    )

    assert field.field_path == "general.experimenter"
    assert field.ontology_governed is False
    assert field.ontology is None
