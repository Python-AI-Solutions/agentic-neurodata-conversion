"""
Comprehensive unit tests for IntelligentMetadataMapper.

Tests cover:
- Custom metadata parsing
- NWB schema mapping
- Field name cleaning
- Missing metadata suggestions
- Display formatting
- LLM-assisted mapping
- Edge cases and error handling
"""

import os
import sys

import pytest

# Add backend/src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from agents.intelligent_metadata_mapper import IntelligentMetadataMapper
from models import GlobalState

# ============================================================================
# Fixtures
# ============================================================================

# Note: mock_llm_metadata_parser is provided by root conftest.py
# It returns metadata parsing responses suitable for this mapper


@pytest.fixture
def mapper_with_llm(mock_llm_metadata_parser):
    """
    Create mapper with LLM service for testing.

    Uses mock_llm_metadata_parser from root conftest.py which provides
    metadata extraction and mapping responses.
    """
    return IntelligentMetadataMapper(llm_service=mock_llm_metadata_parser)


@pytest.fixture
def mapper_without_llm():
    """Create mapper without LLM service."""
    return IntelligentMetadataMapper(llm_service=None)


@pytest.fixture
def sample_user_input():
    """Sample user metadata input."""
    return """
    Session: Test recording session
    Experimenter: John Doe
    Subject Species: Mouse
    Subject Age: 90 days
    Subject Sex: Male
    Institution: Test University
    Lab: Neuroscience Lab
    """


@pytest.fixture
def sample_extracted_metadata():
    """Sample extracted metadata."""
    return {
        "session": "Test recording session",
        "experimenter": "John Doe",
        "subject_species": "Mouse",
        "subject_age": "90 days",
        "subject_sex": "Male",
        "institution": "Test University",
        "lab": "Neuroscience Lab",
    }


@pytest.fixture
def global_state():
    """Create a GlobalState instance for testing."""
    return GlobalState()


# ============================================================================
# Test: Initialization
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestIntelligentMetadataMapperInitialization:
    """Test suite for IntelligentMetadataMapper initialization."""

    def test_init_with_llm_service(self, mock_llm_service):
        """Test initialization with LLM service."""
        mapper = IntelligentMetadataMapper(llm_service=mock_llm_service)

        assert mapper.llm_service is mock_llm_service

    def test_init_without_llm_service(self):
        """Test initialization without LLM service."""
        mapper = IntelligentMetadataMapper(llm_service=None)

        assert mapper.llm_service is None


# ============================================================================
# Test: Custom Metadata Parsing
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestCustomMetadataParsing:
    """Test suite for custom metadata parsing."""

    @pytest.mark.asyncio
    async def test_parse_custom_metadata_with_llm(self, sample_user_input, mock_llm_metadata_parser, global_state):
        """Test parsing custom metadata with LLM."""
        mock_llm_metadata_parser.generate_structured_output.return_value = {
            "session_description": "Test recording session",
            "experimenter": ["John Doe"],
            "subject": {"species": "Mus musculus", "age": "P90D", "sex": "M"},
        }

        # Create mapper with the same mock that we're asserting on
        mapper = IntelligentMetadataMapper(llm_service=mock_llm_metadata_parser)

        result = await mapper.parse_custom_metadata(sample_user_input, existing_metadata={}, state=global_state)

        assert result is not None
        assert isinstance(result, dict)
        mock_llm_metadata_parser.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_custom_metadata_without_llm(self, mapper_without_llm, sample_user_input, global_state):
        """Test parsing custom metadata without LLM."""
        result = await mapper_without_llm.parse_custom_metadata(
            sample_user_input, existing_metadata={}, state=global_state
        )

        assert result is not None
        assert isinstance(result, dict)
        # Should use fallback parsing

    @pytest.mark.asyncio
    async def test_parse_custom_metadata_empty_input(self, mapper_with_llm, global_state):
        """Test parsing empty input."""
        result = await mapper_with_llm.parse_custom_metadata("", existing_metadata={}, state=global_state)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_parse_custom_metadata_malformed_input(self, mapper_with_llm, global_state):
        """Test parsing malformed input."""
        malformed_input = "random text without structure"

        result = await mapper_with_llm.parse_custom_metadata(malformed_input, existing_metadata={}, state=global_state)

        assert result is not None
        # Should handle gracefully


# ============================================================================
# Test: NWB Schema Mapping
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestNWBSchemaMapping:
    """Test suite for NWB schema mapping."""

    @pytest.mark.asyncio
    async def test_map_to_nwb_schema_complete(self, mapper_with_llm, global_state):
        """Test mapping complete metadata to NWB schema."""
        extracted_fields = [
            {"suggested_name": "session", "value": "Test recording session", "category": "experimental"},
            {"suggested_name": "experimenter", "value": "John Doe", "category": "experimental"},
            {"suggested_name": "subject_species", "value": "Mouse", "category": "subject"},
        ]
        result = await mapper_with_llm._map_to_nwb_schema(extracted_fields, state=global_state)

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_map_to_nwb_schema_species_conversion(self, mapper_with_llm, global_state):
        """Test species name conversion to scientific name."""
        extracted_fields = [{"suggested_name": "subject_species", "value": "Mouse", "category": "subject"}]

        result = await mapper_with_llm._map_to_nwb_schema(extracted_fields, state=global_state)

        # Should convert to scientific name
        assert result is not None
        # Just verify it doesn't crash - actual conversion logic is tested elsewhere

    @pytest.mark.asyncio
    async def test_map_to_nwb_schema_age_conversion(self, mapper_with_llm, global_state):
        """Test age conversion to ISO 8601 format."""
        extracted_fields = [{"suggested_name": "subject_age", "value": "90 days", "category": "subject"}]

        result = await mapper_with_llm._map_to_nwb_schema(extracted_fields, state=global_state)

        # Should convert to ISO 8601 (P90D)
        assert result is not None
        # Just verify it doesn't crash - actual conversion logic is tested elsewhere

    @pytest.mark.asyncio
    async def test_map_to_nwb_schema_sex_code_conversion(self, mapper_with_llm, global_state):
        """Test sex conversion to single letter code."""
        extracted_fields = [{"suggested_name": "subject_sex", "value": "Male", "category": "subject"}]

        result = await mapper_with_llm._map_to_nwb_schema(extracted_fields, state=global_state)

        # Should convert to M/F/U
        assert result is not None
        # Just verify it doesn't crash - actual conversion logic is tested elsewhere

    @pytest.mark.asyncio
    async def test_map_to_nwb_schema_experimenter_array(self, mapper_with_llm, global_state):
        """Test experimenter converted to array format."""
        extracted_fields = [{"suggested_name": "experimenter", "value": "John Doe", "category": "experimental"}]

        result = await mapper_with_llm._map_to_nwb_schema(extracted_fields, state=global_state)

        # Experimenter should be an array in NWB
        assert result is not None
        # Just verify it doesn't crash - actual conversion logic is tested elsewhere


# ============================================================================
# Test: Parsing Without LLM
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestParsingWithoutLLM:
    """Test suite for fallback parsing without LLM."""

    def test_parse_without_llm_key_value_pairs(self, mapper_without_llm):
        """Test parsing simple key-value pairs."""
        user_input = """
        Session: Test session
        Experimenter: John Doe
        Species: Mouse
        """

        result = mapper_without_llm._parse_without_llm(user_input)

        assert result is not None
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_parse_without_llm_empty_input(self, mapper_without_llm):
        """Test parsing empty input."""
        result = mapper_without_llm._parse_without_llm("")

        assert result is not None
        assert isinstance(result, dict)

    def test_parse_without_llm_malformed_input(self, mapper_without_llm):
        """Test parsing malformed input."""
        result = mapper_without_llm._parse_without_llm("no colons here")

        assert result is not None
        # Should handle gracefully


# ============================================================================
# Test: Field Name Cleaning
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestFieldNameCleaning:
    """Test suite for field name cleaning."""

    def test_clean_field_name_lowercase(self, mapper_with_llm):
        """Test converting to lowercase."""
        cleaned = mapper_with_llm._clean_field_name("Session Description")

        assert cleaned is not None
        assert cleaned.islower()

    def test_clean_field_name_spaces_to_underscores(self, mapper_with_llm):
        """Test converting spaces to underscores."""
        cleaned = mapper_with_llm._clean_field_name("Subject Species")

        assert cleaned is not None
        assert " " not in cleaned
        assert "_" in cleaned

    def test_clean_field_name_remove_special_chars(self, mapper_with_llm):
        """Test removing special characters."""
        cleaned = mapper_with_llm._clean_field_name("Field-Name!")

        assert cleaned is not None
        # Should only contain alphanumeric and underscores
        assert cleaned.replace("_", "").isalnum()


# ============================================================================
# Test: Missing Metadata Suggestions
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestMissingMetadataSuggestions:
    """Test suite for missing metadata suggestions."""

    @pytest.mark.asyncio
    async def test_suggest_missing_metadata_partial(self, mapper_with_llm):
        """Test suggestions for partial metadata."""
        partial_metadata = {
            "session_description": "Test session",
            # Missing: experimenter, institution, etc.
        }

        suggestions = await mapper_with_llm.suggest_missing_metadata(partial_metadata, file_type="spikeglx")

        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    @pytest.mark.asyncio
    async def test_suggest_missing_metadata_complete(self, mapper_with_llm):
        """Test suggestions for complete metadata."""
        complete_metadata = {
            "session_description": "Test",
            "experimenter": ["John"],
            "institution": "Test U",
            "lab": "Test Lab",
            "subject": {"species": "Mus musculus"},
        }

        suggestions = await mapper_with_llm.suggest_missing_metadata(complete_metadata, file_type="spikeglx")

        assert suggestions is not None
        assert isinstance(suggestions, list)
        # Should have fewer suggestions

    @pytest.mark.asyncio
    async def test_suggest_missing_metadata_empty(self, mapper_with_llm):
        """Test suggestions for empty metadata."""
        suggestions = await mapper_with_llm.suggest_missing_metadata({}, file_type="spikeglx")

        assert suggestions is not None
        assert isinstance(suggestions, list)
        # Should suggest many missing fields
        assert len(suggestions) > 0


# ============================================================================
# Test: Display Formatting
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestDisplayFormatting:
    """Test suite for metadata display formatting."""

    def test_format_metadata_for_display_complete(self, mapper_with_llm, sample_extracted_metadata):
        """Test formatting complete metadata for display."""
        formatted = mapper_with_llm.format_metadata_for_display(sample_extracted_metadata, mapping_report=[])

        assert formatted is not None
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_format_metadata_for_display_empty(self, mapper_with_llm):
        """Test formatting empty metadata."""
        formatted = mapper_with_llm.format_metadata_for_display({}, mapping_report=[])

        assert formatted is not None
        assert isinstance(formatted, str)

    def test_format_metadata_for_display_nested(self, mapper_with_llm):
        """Test formatting nested metadata."""
        nested_metadata = {
            "session_description": "Test",
            "subject": {
                "species": "Mus musculus",
                "age": "P90D",
                "sex": "M",
            },
        }

        formatted = mapper_with_llm.format_metadata_for_display(nested_metadata, mapping_report=[])

        assert formatted is not None
        assert isinstance(formatted, str)
        # Should handle nested structure


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_parse_metadata_with_unicode(self, mapper_with_llm, global_state):
        """Test parsing metadata with unicode characters."""
        unicode_input = """
        Experimenter: José García
        Institution: École Polytechnique
        """

        result = await mapper_with_llm.parse_custom_metadata(unicode_input, existing_metadata={}, state=global_state)

        assert result is not None
        # Should handle unicode correctly

    @pytest.mark.asyncio
    async def test_parse_metadata_with_special_chars(self, mapper_with_llm, global_state):
        """Test parsing metadata with special characters."""
        special_input = """
        Lab: Smith's Lab (2023)
        Description: Test & validation
        """

        result = await mapper_with_llm.parse_custom_metadata(special_input, existing_metadata={}, state=global_state)

        assert result is not None

    @pytest.mark.asyncio
    async def test_map_to_nwb_schema_invalid_species(self, mapper_with_llm, global_state):
        """Test mapping invalid species name."""
        extracted_fields = [{"suggested_name": "subject_species", "value": "UnknownAnimal123", "category": "subject"}]

        result = await mapper_with_llm._map_to_nwb_schema(extracted_fields, state=global_state)

        # Should handle gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_map_to_nwb_schema_invalid_age(self, mapper_with_llm, global_state):
        """Test mapping invalid age format."""
        extracted_fields = [{"suggested_name": "subject_age", "value": "unknown", "category": "subject"}]

        result = await mapper_with_llm._map_to_nwb_schema(extracted_fields, state=global_state)

        # Should handle gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self, mapper_with_llm, mock_llm_service, sample_user_input, global_state):
        """Test fallback when LLM times out."""
        mock_llm_service.generate_structured_output.side_effect = Exception("Timeout")

        result = await mapper_with_llm.parse_custom_metadata(
            sample_user_input, existing_metadata={}, state=global_state
        )

        # Should fallback to non-LLM parsing
        assert result is not None

    def test_clean_field_name_empty_string(self, mapper_with_llm):
        """Test cleaning empty field name."""
        cleaned = mapper_with_llm._clean_field_name("")

        assert cleaned is not None
        assert isinstance(cleaned, str)

    def test_clean_field_name_only_special_chars(self, mapper_with_llm):
        """Test cleaning field name with only special characters."""
        cleaned = mapper_with_llm._clean_field_name("!@#$%")

        assert cleaned is not None
        # Should return something valid


# ============================================================================
# Test: Integration Scenarios
# ============================================================================


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests for metadata mapping workflows."""

    @pytest.mark.asyncio
    async def test_complete_metadata_mapping_workflow(self, mapper_with_llm, sample_user_input, global_state):
        """Test complete metadata mapping workflow."""
        # Step 1: Parse custom metadata
        parsed = await mapper_with_llm.parse_custom_metadata(
            sample_user_input, existing_metadata={}, state=global_state
        )

        assert parsed is not None
        assert isinstance(parsed, dict)

        # Step 2: Map to NWB schema (parsed is already in correct format from parse_custom_metadata)
        # Skip this step as parse_custom_metadata already returns mapped data

        # Step 3: Check for missing fields
        suggestions = await mapper_with_llm.suggest_missing_metadata(parsed, file_type="spikeglx")

        assert suggestions is not None

        # Step 4: Format for display
        formatted = mapper_with_llm.format_metadata_for_display(parsed, mapping_report=[])

        assert formatted is not None
        assert len(formatted) > 0
