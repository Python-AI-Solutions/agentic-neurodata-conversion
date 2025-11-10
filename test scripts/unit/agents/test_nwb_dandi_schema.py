"""
Unit tests for NWBDANDISchema.

Tests schema definitions and metadata field management for NWB and DANDI compliance.
"""

import pytest

from agents.nwb_dandi_schema import (
    FieldRequirementLevel,
    FieldType,
    MetadataFieldSchema,
    NWBDANDISchema,
)


@pytest.mark.unit
class TestFieldRequirementLevel:
    """Tests for FieldRequirementLevel enum."""

    def test_required_value(self):
        """Test REQUIRED enum value."""
        assert FieldRequirementLevel.REQUIRED == "required"

    def test_recommended_value(self):
        """Test RECOMMENDED enum value."""
        assert FieldRequirementLevel.RECOMMENDED == "recommended"

    def test_optional_value(self):
        """Test OPTIONAL enum value."""
        assert FieldRequirementLevel.OPTIONAL == "optional"


@pytest.mark.unit
class TestFieldType:
    """Tests for FieldType enum."""

    def test_string_value(self):
        """Test STRING enum value."""
        assert FieldType.STRING == "string"

    def test_list_value(self):
        """Test LIST enum value."""
        assert FieldType.LIST == "list"

    def test_date_value(self):
        """Test DATE enum value."""
        assert FieldType.DATE == "date"

    def test_duration_value(self):
        """Test DURATION enum value."""
        assert FieldType.DURATION == "duration"

    def test_number_value(self):
        """Test NUMBER enum value."""
        assert FieldType.NUMBER == "number"

    def test_enum_value(self):
        """Test ENUM enum value."""
        assert FieldType.ENUM == "enum"

    def test_nested_value(self):
        """Test NESTED enum value."""
        assert FieldType.NESTED == "nested"


@pytest.mark.unit
class TestMetadataFieldSchema:
    """Tests for MetadataFieldSchema Pydantic model."""

    def test_create_minimal_field_schema(self):
        """Test creating field schema with minimal required fields."""
        field = MetadataFieldSchema(
            name="test_field",
            display_name="Test Field",
            description="A test field",
            field_type=FieldType.STRING,
            requirement_level=FieldRequirementLevel.REQUIRED,
            example="example value",
            extraction_patterns=["test", "field"],
            why_needed="For testing",
        )

        assert field.name == "test_field"
        assert field.display_name == "Test Field"
        assert field.field_type == FieldType.STRING
        assert field.requirement_level == FieldRequirementLevel.REQUIRED

    def test_create_full_field_schema(self):
        """Test creating field schema with all fields."""
        field = MetadataFieldSchema(
            name="experimenter",
            display_name="Experimenter",
            description="Person who performed experiment",
            field_type=FieldType.LIST,
            requirement_level=FieldRequirementLevel.REQUIRED,
            allowed_values=None,
            format="LastName, FirstName",
            example='["Smith, Jane"]',
            extraction_patterns=["experimenter", "researcher"],
            synonyms=["scientist", "investigator"],
            normalization_rules={"Dr. Smith": "Smith"},
            nwb_path="/general/experimenter",
            dandi_field="contributor",
            why_needed="For attribution",
        )

        assert field.name == "experimenter"
        assert field.synonyms == ["scientist", "investigator"]
        assert field.normalization_rules == {"Dr. Smith": "Smith"}
        assert field.nwb_path == "/general/experimenter"

    def test_default_values(self):
        """Test default values for optional fields."""
        field = MetadataFieldSchema(
            name="test",
            display_name="Test",
            description="Test",
            field_type=FieldType.STRING,
            requirement_level=FieldRequirementLevel.OPTIONAL,
            example="test",
            extraction_patterns=["test"],
            why_needed="test",
        )

        assert field.synonyms == []
        assert field.normalization_rules == {}
        assert field.allowed_values is None


@pytest.mark.unit
class TestGetAllFields:
    """Tests for get_all_fields method."""

    def test_get_all_fields_returns_list(self):
        """Test get_all_fields returns a list."""
        fields = NWBDANDISchema.get_all_fields()

        assert isinstance(fields, list)
        assert len(fields) > 0

    def test_get_all_fields_contains_required_fields(self):
        """Test all fields includes required fields."""
        fields = NWBDANDISchema.get_all_fields()
        field_names = [f.name for f in fields]

        # Check for essential NWB fields
        assert "experimenter" in field_names
        assert "institution" in field_names
        assert "experiment_description" in field_names
        assert "session_description" in field_names
        assert "session_start_time" in field_names
        assert "subject_id" in field_names
        assert "species" in field_names
        assert "sex" in field_names

    def test_get_all_fields_contains_recommended_fields(self):
        """Test all fields includes recommended fields."""
        fields = NWBDANDISchema.get_all_fields()
        field_names = [f.name for f in fields]

        assert "lab" in field_names
        assert "age" in field_names
        assert "keywords" in field_names

    def test_get_all_fields_contains_optional_fields(self):
        """Test all fields includes optional fields."""
        fields = NWBDANDISchema.get_all_fields()
        field_names = [f.name for f in fields]

        assert "weight" in field_names
        assert "related_publications" in field_names
        assert "description" in field_names

    def test_all_fields_have_required_attributes(self):
        """Test all fields have required attributes."""
        fields = NWBDANDISchema.get_all_fields()

        for field in fields:
            assert hasattr(field, "name")
            assert hasattr(field, "display_name")
            assert hasattr(field, "description")
            assert hasattr(field, "field_type")
            assert hasattr(field, "requirement_level")
            assert hasattr(field, "example")
            assert hasattr(field, "extraction_patterns")
            assert hasattr(field, "why_needed")

    def test_experimenter_field_complete(self):
        """Test experimenter field has complete information."""
        fields = NWBDANDISchema.get_all_fields()
        experimenter = next(f for f in fields if f.name == "experimenter")

        assert experimenter.display_name == "Experimenter(s)"
        assert experimenter.field_type == FieldType.LIST
        assert experimenter.requirement_level == FieldRequirementLevel.REQUIRED
        assert len(experimenter.extraction_patterns) > 0
        assert len(experimenter.synonyms) > 0
        assert len(experimenter.normalization_rules) > 0

    def test_species_field_normalization_rules(self):
        """Test species field has normalization rules."""
        fields = NWBDANDISchema.get_all_fields()
        species = next(f for f in fields if f.name == "species")

        assert "mouse" in species.normalization_rules
        assert species.normalization_rules["mouse"] == "Mus musculus"
        assert "rat" in species.normalization_rules
        assert species.normalization_rules["rat"] == "Rattus norvegicus"


@pytest.mark.unit
class TestGetRequiredFields:
    """Tests for get_required_fields method."""

    def test_get_required_fields_returns_only_required(self):
        """Test get_required_fields returns only REQUIRED level fields."""
        required = NWBDANDISchema.get_required_fields()

        for field in required:
            assert field.requirement_level == FieldRequirementLevel.REQUIRED

    def test_get_required_fields_includes_essentials(self):
        """Test required fields includes essential NWB fields."""
        required = NWBDANDISchema.get_required_fields()
        required_names = [f.name for f in required]

        assert "experimenter" in required_names
        assert "institution" in required_names
        assert "experiment_description" in required_names
        assert "session_description" in required_names
        assert "session_start_time" in required_names
        assert "subject_id" in required_names
        assert "species" in required_names
        assert "sex" in required_names

    def test_get_required_fields_excludes_optional(self):
        """Test required fields excludes optional fields."""
        required = NWBDANDISchema.get_required_fields()
        required_names = [f.name for f in required]

        assert "weight" not in required_names
        assert "description" not in required_names


@pytest.mark.unit
class TestGetRecommendedFields:
    """Tests for get_recommended_fields method."""

    def test_get_recommended_fields_includes_required_and_recommended(self):
        """Test recommended fields includes both REQUIRED and RECOMMENDED levels."""
        recommended = NWBDANDISchema.get_recommended_fields()
        levels = {f.requirement_level for f in recommended}

        assert FieldRequirementLevel.REQUIRED in levels
        assert FieldRequirementLevel.RECOMMENDED in levels

    def test_get_recommended_fields_excludes_optional(self):
        """Test recommended fields excludes OPTIONAL level."""
        recommended = NWBDANDISchema.get_recommended_fields()

        for field in recommended:
            assert field.requirement_level != FieldRequirementLevel.OPTIONAL

    def test_get_recommended_fields_includes_lab(self):
        """Test recommended fields includes lab field."""
        recommended = NWBDANDISchema.get_recommended_fields()
        field_names = [f.name for f in recommended]

        assert "lab" in field_names
        assert "age" in field_names


@pytest.mark.unit
class TestGetFieldByName:
    """Tests for get_field_by_name method."""

    def test_get_field_by_name_found(self):
        """Test getting field by name when it exists."""
        field = NWBDANDISchema.get_field_by_name("experimenter")

        assert field is not None
        assert field.name == "experimenter"
        assert field.display_name == "Experimenter(s)"

    def test_get_field_by_name_not_found(self):
        """Test getting field by name when it doesn't exist."""
        field = NWBDANDISchema.get_field_by_name("nonexistent_field")

        assert field is None

    def test_get_field_by_name_case_sensitive(self):
        """Test get_field_by_name is case sensitive."""
        field = NWBDANDISchema.get_field_by_name("EXPERIMENTER")

        assert field is None

    def test_get_all_fields_by_name(self):
        """Test getting multiple fields by name."""
        all_fields = NWBDANDISchema.get_all_fields()

        for field_schema in all_fields:
            retrieved = NWBDANDISchema.get_field_by_name(field_schema.name)
            assert retrieved is not None
            assert retrieved.name == field_schema.name


@pytest.mark.unit
class TestGenerateLLMExtractionPrompt:
    """Tests for generate_llm_extraction_prompt method."""

    def test_generate_llm_extraction_prompt_returns_string(self):
        """Test prompt generation returns a string."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_includes_required_fields_section(self):
        """Test prompt includes required fields section."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert "REQUIRED FIELDS" in prompt
        assert "experimenter" in prompt.lower()
        assert "institution" in prompt.lower()

    def test_prompt_includes_recommended_fields_section(self):
        """Test prompt includes recommended fields section."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert "RECOMMENDED FIELDS" in prompt

    def test_prompt_includes_optional_fields_section(self):
        """Test prompt includes optional fields section."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert "OPTIONAL FIELDS" in prompt

    def test_prompt_includes_extraction_strategy(self):
        """Test prompt includes extraction strategy."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert "Extraction Strategy" in prompt
        assert "Be Comprehensive" in prompt

    def test_prompt_includes_response_format(self):
        """Test prompt includes response format."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert "Response Format" in prompt
        assert "extracted_metadata" in prompt
        assert "ready_to_proceed" in prompt

    def test_prompt_includes_field_examples(self):
        """Test prompt includes field examples."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        # Check that examples from schema are included
        assert "Example:" in prompt or "e.g.," in prompt

    def test_prompt_includes_normalization_rules(self):
        """Test prompt includes normalization rules."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert "Normalize" in prompt or "normalization" in prompt.lower()

    def test_prompt_includes_why_needed_explanations(self):
        """Test prompt includes why_needed explanations."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert "Why needed" in prompt or "why" in prompt.lower()

    def test_prompt_includes_ready_to_proceed_logic(self):
        """Test prompt includes ready_to_proceed logic."""
        prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        assert "ready_to_proceed" in prompt
        assert "Set `ready_to_proceed: true`" in prompt or "ready_to_proceed=TRUE" in prompt


@pytest.mark.unit
class TestValidateMetadata:
    """Tests for validate_metadata method."""

    def test_validate_complete_metadata(self):
        """Test validation with all required fields."""
        metadata = {
            "experimenter": ["Smith, Jane"],
            "institution": "MIT",
            "experiment_description": "Test experiment",
            "session_description": "Test session",
            "session_start_time": "2024-01-15T14:30:00",
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
        }

        is_valid, missing = NWBDANDISchema.validate_metadata(metadata)

        assert is_valid is True
        assert len(missing) == 0

    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields."""
        metadata = {
            "experimenter": ["Smith, Jane"],
            "institution": "MIT",
            # Missing other required fields
        }

        is_valid, missing = NWBDANDISchema.validate_metadata(metadata)

        assert is_valid is False
        assert len(missing) > 0
        assert "experiment_description" in missing
        assert "session_description" in missing

    def test_validate_empty_metadata(self):
        """Test validation with empty metadata."""
        metadata = {}

        is_valid, missing = NWBDANDISchema.validate_metadata(metadata)

        assert is_valid is False
        assert len(missing) > 0

    def test_validate_none_values_treated_as_missing(self):
        """Test validation treats None values as missing."""
        metadata = {
            "experimenter": None,
            "institution": "MIT",
            "experiment_description": "Test",
            "session_description": "Test",
            "session_start_time": "2024-01-15T14:30:00",
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
        }

        is_valid, missing = NWBDANDISchema.validate_metadata(metadata)

        assert is_valid is False
        assert "experimenter" in missing

    def test_validate_empty_string_treated_as_missing(self):
        """Test validation treats empty strings as missing."""
        metadata = {
            "experimenter": ["Smith, Jane"],
            "institution": "",  # Empty string
            "experiment_description": "Test",
            "session_description": "Test",
            "session_start_time": "2024-01-15T14:30:00",
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
        }

        is_valid, missing = NWBDANDISchema.validate_metadata(metadata)

        assert is_valid is False
        assert "institution" in missing

    def test_validate_with_extra_fields(self):
        """Test validation ignores extra non-required fields."""
        metadata = {
            "experimenter": ["Smith, Jane"],
            "institution": "MIT",
            "experiment_description": "Test",
            "session_description": "Test",
            "session_start_time": "2024-01-15T14:30:00",
            "subject_id": "mouse001",
            "species": "Mus musculus",
            "sex": "M",
            "extra_field": "extra_value",  # Extra field
        }

        is_valid, missing = NWBDANDISchema.validate_metadata(metadata)

        assert is_valid is True
        assert len(missing) == 0


@pytest.mark.unit
class TestGetFieldDisplayInfo:
    """Tests for get_field_display_info method."""

    def test_get_field_display_info_found(self):
        """Test getting display info for existing field."""
        info = NWBDANDISchema.get_field_display_info("experimenter")

        assert "name" in info
        assert info["name"] == "Experimenter(s)"
        assert "description" in info
        assert "example" in info
        assert "why_needed" in info

    def test_get_field_display_info_not_found(self):
        """Test getting display info for non-existent field."""
        info = NWBDANDISchema.get_field_display_info("nonexistent_field")

        assert "name" in info
        assert info["name"] == "nonexistent_field"
        assert "description" in info
        assert info["description"] == "Unknown field"

    def test_get_field_display_info_all_fields(self):
        """Test getting display info for all fields."""
        all_fields = NWBDANDISchema.get_all_fields()

        for field in all_fields:
            info = NWBDANDISchema.get_field_display_info(field.name)
            assert info["name"] == field.display_name
            assert info["description"] == field.description
            assert info["example"] == field.example
            assert info["why_needed"] == field.why_needed


@pytest.mark.unit
class TestNWBDANDISchemaIntegration:
    """Integration tests for NWBDANDISchema."""

    def test_schema_consistency(self):
        """Test schema is internally consistent."""
        all_fields = NWBDANDISchema.get_all_fields()
        required = NWBDANDISchema.get_required_fields()
        recommended = NWBDANDISchema.get_recommended_fields()

        # Required is subset of recommended
        required_names = {f.name for f in required}
        recommended_names = {f.name for f in recommended}
        assert required_names.issubset(recommended_names)

        # Recommended is subset of all
        all_names = {f.name for f in all_fields}
        assert recommended_names.issubset(all_names)

    def test_field_names_unique(self):
        """Test all field names are unique."""
        all_fields = NWBDANDISchema.get_all_fields()
        field_names = [f.name for f in all_fields]

        assert len(field_names) == len(set(field_names))

    def test_all_required_fields_have_extraction_patterns(self):
        """Test all required fields have extraction patterns."""
        required = NWBDANDISchema.get_required_fields()

        for field in required:
            assert len(field.extraction_patterns) > 0

    def test_complete_workflow(self):
        """Test complete validation workflow."""
        # Step 1: Get required fields
        required = NWBDANDISchema.get_required_fields()
        assert len(required) > 0

        # Step 2: Create metadata dict
        metadata = {field.name: f"test_{field.name}" for field in required}

        # Step 3: Validate
        is_valid, missing = NWBDANDISchema.validate_metadata(metadata)
        assert is_valid is True
        assert len(missing) == 0

        # Step 4: Get display info for each field
        for field_name in metadata.keys():
            info = NWBDANDISchema.get_field_display_info(field_name)
            assert info["name"] != "Unknown field"
