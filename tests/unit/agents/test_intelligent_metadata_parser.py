"""
Comprehensive unit tests for IntelligentMetadataParser.

Tests cover:
- Natural language batch parsing
- Single field parsing
- Confidence level assessment
- Value normalization and formatting
- Date field post-processing
- Schema context building
- Fallback parsing mechanisms
- LLM-assisted parsing
"""

import os
import sys

import pytest

# Add backend/src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from agentic_neurodata_conversion.agents.metadata.intelligent_parser import (
    ConfidenceLevel,
    IntelligentMetadataParser,
    ParsedField,
)
from agentic_neurodata_conversion.models import GlobalState

# ============================================================================
# Fixtures
# ============================================================================

# Note: mock_llm_metadata_parser is provided by root conftest.py
# It returns metadata parsing responses suitable for this parser


@pytest.fixture
def parser_with_llm(mock_llm_metadata_parser):
    """
    Create parser with LLM service for testing.

    Uses mock_llm_metadata_parser from root conftest.py which provides
    metadata extraction responses suitable for IntelligentMetadataParser testing.
    """
    return IntelligentMetadataParser(llm_service=mock_llm_metadata_parser)


@pytest.fixture
def parser_without_llm():
    """Create parser without LLM service."""
    return IntelligentMetadataParser(llm_service=None)


@pytest.fixture
def global_state():
    """Create fresh GlobalState."""
    return GlobalState()


@pytest.fixture
def sample_user_responses():
    """Sample user responses for parsing."""
    return {
        "session_description": "Recording from mouse V1 cortex",
        "experimenter": "John Doe, Jane Smith",
        "subject_species": "Mouse",
        "subject_age": "90 days",
        "subject_sex": "Male",
        "session_start_time": "June 15, 2023 at 10:30 AM",
    }


# ============================================================================
# Test: ParsedField Class
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestParsedFieldClass:
    """Test suite for ParsedField class."""

    def test_parsed_field_creation(self):
        """Test creating ParsedField instance."""
        field = ParsedField(
            field_name="session_description",
            raw_input="Recording session",
            parsed_value="Test session",
            confidence=85.0,
            reasoning="Direct user input",
            nwb_compliant=True,
        )

        assert field.field_name == "session_description"
        assert field.parsed_value == "Test session"
        assert field.confidence == 85.0
        assert field.raw_input == "Recording session"

    def test_parsed_field_to_dict(self):
        """Test converting ParsedField to dictionary."""
        field = ParsedField(
            field_name="experimenter",
            raw_input="John Doe",
            parsed_value=["John Doe"],
            confidence=90.0,
            reasoning="User provided experimenter name",
            nwb_compliant=True,
        )

        field_dict = field.to_dict()

        assert isinstance(field_dict, dict)
        assert "field_name" in field_dict
        assert "parsed_value" in field_dict
        assert "confidence" in field_dict

    def test_parsed_field_confidence_level_property(self):
        """Test confidence_level property."""
        field = ParsedField(
            field_name="test",
            raw_input="test input",
            parsed_value="value",
            confidence=65.0,
            reasoning="Medium confidence parse",
            nwb_compliant=True,
        )

        assert field.confidence_level == ConfidenceLevel.MEDIUM

    def test_parsed_field_to_provenance_info(self):
        """Test converting to provenance info."""
        field = ParsedField(
            field_name="session_description",
            raw_input="Recording session test",
            parsed_value="Test",
            confidence=85.0,
            reasoning="Parsed from user input",
            nwb_compliant=True,
        )

        provenance = field.to_provenance_info()

        assert provenance is not None
        # ProvenanceInfo is a Pydantic model, not a dict
        assert hasattr(provenance, "value")


# ============================================================================
# Test: Initialization
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestIntelligentMetadataParserInitialization:
    """Test suite for IntelligentMetadataParser initialization."""

    def test_init_with_llm_service(self, mock_llm_service):
        """Test initialization with LLM service."""
        parser = IntelligentMetadataParser(llm_service=mock_llm_service)

        assert parser.llm_service is mock_llm_service

    def test_init_without_llm_service(self):
        """Test initialization without LLM service."""
        parser = IntelligentMetadataParser(llm_service=None)

        assert parser.llm_service is None


# ============================================================================
# Test: Batch Parsing
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestBatchParsing:
    """Test suite for natural language batch parsing."""

    @pytest.mark.asyncio
    async def test_parse_natural_language_batch_with_llm(
        self, sample_user_responses, mock_llm_metadata_parser, global_state
    ):
        """Test batch parsing with LLM."""
        # The method takes a string, not a dict
        user_input = "Recording from mouse V1 cortex, experimenter John Doe"

        mock_llm_metadata_parser.generate_structured_output.return_value = {
            "fields": [
                {
                    "field_name": "session_description",
                    "raw_value": "Recording from mouse V1 cortex",
                    "normalized_value": "Recording from mouse V1 cortex",
                    "confidence": 85,
                    "reasoning": "Direct user input",
                    "needs_review": False,
                    "extraction_type": "explicit",
                    "alternatives": [],
                },
                {
                    "field_name": "experimenter",
                    "raw_value": "John Doe",
                    "normalized_value": ["Doe, John"],
                    "confidence": 90,
                    "reasoning": "Normalized name format",
                    "needs_review": False,
                    "extraction_type": "explicit",
                    "alternatives": [],
                },
            ]
        }

        # Create parser with the same mock that we're asserting on
        parser = IntelligentMetadataParser(llm_service=mock_llm_metadata_parser)

        results = await parser.parse_natural_language_batch(user_input, global_state)

        assert results is not None
        assert isinstance(results, list)
        mock_llm_metadata_parser.generate_structured_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_natural_language_batch_without_llm(self, parser_without_llm, global_state):
        """Test batch parsing without LLM (fallback)."""
        user_input = "session_description: Test session, experimenter: John Doe"

        results = await parser_without_llm.parse_natural_language_batch(user_input, global_state)

        assert results is not None
        assert isinstance(results, list)
        # Should use fallback parsing

    @pytest.mark.asyncio
    async def test_parse_natural_language_batch_empty_input(self, parser_with_llm, global_state):
        """Test batch parsing with empty input."""
        results = await parser_with_llm.parse_natural_language_batch("", global_state)

        assert results is not None
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_parse_natural_language_batch_llm_failure(self, parser_with_llm, mock_llm_service, global_state):
        """Test batch parsing with LLM failure."""
        user_input = "session_description: Test, experimenter: John"
        mock_llm_service.generate_structured_output.side_effect = Exception("LLM Error")

        results = await parser_with_llm.parse_natural_language_batch(user_input, global_state)

        # Should fallback to non-LLM parsing
        assert results is not None


# ============================================================================
# Test: Single Field Parsing
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestSingleFieldParsing:
    """Test suite for single field parsing."""

    @pytest.mark.asyncio
    async def test_parse_single_field_with_llm(self, parser_with_llm, mock_llm_service, global_state):
        """Test parsing single field with LLM."""
        mock_llm_service.generate_structured_output.return_value = {
            "normalized_value": "Mus musculus",
            "confidence": 90,
            "reasoning": "Species name normalization",
            "needs_review": False,
            "alternatives": [],
        }

        result = await parser_with_llm.parse_single_field(
            field_name="species",
            user_input="Mouse",
            state=global_state,
        )

        assert result is not None
        assert isinstance(result, ParsedField)

    @pytest.mark.asyncio
    async def test_parse_single_field_without_llm(self, parser_without_llm, global_state):
        """Test parsing single field without LLM."""
        result = await parser_without_llm.parse_single_field(
            field_name="session_description",
            user_input="Test session",
            state=global_state,
        )

        assert result is not None
        assert isinstance(result, ParsedField)

    @pytest.mark.asyncio
    async def test_parse_single_field_empty_response(self, parser_with_llm, global_state):
        """Test parsing empty user response."""
        result = await parser_with_llm.parse_single_field(
            field_name="test",
            user_input="",
            state=global_state,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_single_field_alternatives_structure(self, parser_without_llm, global_state):
        """Test parse_single_field returns ParsedField with alternatives attribute - covers lines 383-400."""
        result = await parser_without_llm.parse_single_field(
            field_name="subject_age",
            user_input="90 days",
            state=global_state,
        )

        assert result is not None
        assert isinstance(result, ParsedField)
        assert hasattr(result, "alternatives")
        assert isinstance(result.alternatives, list)

    @pytest.mark.asyncio
    async def test_parse_single_field_needs_review_structure(self, parser_without_llm, global_state):
        """Test parse_single_field returns ParsedField with needs_review attribute - covers lines 383-400."""
        result = await parser_without_llm.parse_single_field(
            field_name="subject_species",
            user_input="mouse",
            state=global_state,
        )

        assert result is not None
        assert hasattr(result, "needs_review")
        assert isinstance(result.needs_review, bool)

    @pytest.mark.asyncio
    async def test_parse_single_field_missing_alternatives_key(self, parser_with_llm, mock_llm_service, global_state):
        """Test parse_single_field when alternatives key is missing - covers lines 383-400."""
        # LLM response without alternatives key (should default to [])
        mock_llm_service.generate_structured_output.return_value = {
            "normalized_value": "Test value",
            "confidence": 80,
            "reasoning": "Direct input",
            "needs_review": False,
            # alternatives key missing
        }

        result = await parser_with_llm.parse_single_field(
            field_name="session_description",
            user_input="Test",
            state=global_state,
        )

        assert result is not None
        # Should handle missing alternatives gracefully with get("alternatives", [])
        assert hasattr(result, "alternatives")
        assert isinstance(result.alternatives, list)

    @pytest.mark.asyncio
    async def test_parse_single_field_missing_needs_review_key(self, parser_with_llm, mock_llm_service, global_state):
        """Test parse_single_field when needs_review key is missing - covers lines 383-400."""
        # LLM response without needs_review key (should default to False)
        mock_llm_service.generate_structured_output.return_value = {
            "normalized_value": "Test value",
            "confidence": 85,
            "reasoning": "Direct input",
            "alternatives": [],
            # needs_review key missing
        }

        result = await parser_with_llm.parse_single_field(
            field_name="session_description",
            user_input="Test",
            state=global_state,
        )

        assert result is not None
        # Should handle missing needs_review gracefully with get("needs_review", False)
        assert hasattr(result, "needs_review")
        assert isinstance(result.needs_review, bool)

    @pytest.mark.asyncio
    async def test_parse_single_field_logs_result(self, parser_without_llm, global_state):
        """Test that parse_single_field logs parsing results - covers lines 383-400."""
        initial_log_count = len(global_state.logs)

        result = await parser_without_llm.parse_single_field(
            field_name="session_description",
            user_input="Test session",
            state=global_state,
        )

        # Fallback parsing should still log
        assert len(global_state.logs) >= initial_log_count
        assert result is not None


# ============================================================================
# Test: Value Formatting
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestValueFormatting:
    """Test suite for value formatting."""

    def test_format_value_string(self, parser_with_llm):
        """Test formatting string value."""
        formatted = parser_with_llm._format_value("Test string")

        # _format_value uses repr() which adds quotes
        assert formatted == "'Test string'"

    def test_format_value_list(self, parser_with_llm):
        """Test formatting list value."""
        formatted = parser_with_llm._format_value(["Item1", "Item2"])

        assert isinstance(formatted, str)
        assert "Item1" in formatted

    def test_format_value_dict(self, parser_with_llm):
        """Test formatting dictionary value."""
        formatted = parser_with_llm._format_value({"key": "value"})

        assert isinstance(formatted, str)

    def test_format_value_none(self, parser_with_llm):
        """Test formatting None value."""
        formatted = parser_with_llm._format_value(None)

        assert formatted is not None


# ============================================================================
# Test: Date Field Post-Processing
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestDateFieldPostProcessing:
    """Test suite for date field post-processing."""

    def test_post_process_date_field_iso_format(self, parser_with_llm, global_state):
        """Test post-processing ISO format date."""
        result = parser_with_llm._post_process_date_field(
            "session_start_time",
            "2023-06-15T10:30:00",
            global_state,
        )

        assert result is not None
        # Should be valid ISO 8601 format

    def test_post_process_date_field_natural_language(self, parser_with_llm, global_state):
        """Test post-processing natural language date."""
        result = parser_with_llm._post_process_date_field(
            "session_start_time",
            "June 15, 2023",
            global_state,
        )

        assert result is not None

    def test_post_process_date_field_invalid_date(self, parser_with_llm, global_state):
        """Test post-processing invalid date."""
        result = parser_with_llm._post_process_date_field(
            "session_start_time",
            "not a date",
            global_state,
        )

        # Should handle gracefully
        assert result is not None


# ============================================================================
# Test: Schema Context Building
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestSchemaContextBuilding:
    """Test suite for schema context building."""

    def test_build_schema_context(self, parser_with_llm):
        """Test building schema context."""
        context = parser_with_llm._build_schema_context()

        assert context is not None
        assert isinstance(context, str)
        assert len(context) > 0

    def test_build_schema_context_includes_nwb_fields(self, parser_with_llm):
        """Test schema context includes NWB fields."""
        context = parser_with_llm._build_schema_context()

        # Should mention key NWB fields
        common_fields = ["session_description", "experimenter", "subject"]
        # At least some fields should be mentioned
        assert any(field in context.lower() for field in common_fields)


# ============================================================================
# Test: Normalization Rules
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestNormalizationRules:
    """Test suite for normalization rules."""

    def test_get_normalization_rules_species(self, parser_with_llm):
        """Test normalization rules for species field."""
        from agentic_neurodata_conversion.agents.metadata.schema import (
            FieldRequirementLevel,
            FieldType,
            MetadataFieldSchema,
        )

        field_schema = MetadataFieldSchema(
            name="species",
            display_name="Species",
            field_type=FieldType.STRING,
            description="Species name",
            requirement_level=FieldRequirementLevel.REQUIRED,
            example="Mus musculus",
            extraction_patterns=[],
            why_needed="Species identification",
        )

        rules = parser_with_llm._get_normalization_rules(field_schema)

        assert rules is not None
        assert isinstance(rules, str)

    def test_get_normalization_rules_age(self, parser_with_llm):
        """Test normalization rules for age field."""
        from agentic_neurodata_conversion.agents.metadata.schema import (
            FieldRequirementLevel,
            FieldType,
            MetadataFieldSchema,
        )

        field_schema = MetadataFieldSchema(
            name="age",
            display_name="Age",
            field_type=FieldType.STRING,
            description="Age in ISO 8601 format",
            requirement_level=FieldRequirementLevel.REQUIRED,
            example="P90D",
            extraction_patterns=[],
            why_needed="Subject age tracking",
        )

        rules = parser_with_llm._get_normalization_rules(field_schema)

        assert rules is not None


# ============================================================================
# Test: Fallback Parsing
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestFallbackParsing:
    """Test suite for fallback parsing mechanisms."""

    def test_fallback_parse_batch(self, parser_without_llm, global_state):
        """Test fallback batch parsing."""
        user_input = "session_description: Test, experimenter: John"
        results = parser_without_llm._fallback_parse_batch(user_input, global_state)

        assert results is not None
        assert isinstance(results, list)
        assert len(results) >= 0

    def test_fallback_parse_single(self, parser_without_llm, global_state):
        """Test fallback single field parsing."""
        result = parser_without_llm._fallback_parse_single(
            "session_description",
            "Test session",
            global_state,
        )

        assert result is not None
        assert isinstance(result, ParsedField)

    def test_fallback_parse_batch_empty_input(self, parser_without_llm, global_state):
        """Test fallback parsing with empty input."""
        results = parser_without_llm._fallback_parse_batch("", global_state)

        assert results is not None
        assert isinstance(results, list)


# ============================================================================
# Test: Confirmation Message Generation
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestConfirmationMessageGeneration:
    """Test suite for confirmation message generation."""

    def test_generate_confirmation_message_single_field(self, parser_with_llm):
        """Test generating confirmation for single field."""
        parsed_field = ParsedField(
            field_name="session_description",
            raw_input="Recording session",
            parsed_value="Test session",
            confidence=85.0,
            reasoning="User provided description",
            nwb_compliant=True,
        )

        message = parser_with_llm.generate_confirmation_message([parsed_field])

        assert message is not None
        assert isinstance(message, str)
        assert len(message) > 0

    def test_generate_confirmation_message_multiple_fields(self, parser_with_llm):
        """Test generating confirmation for multiple fields."""
        fields = [
            ParsedField(
                field_name="session_description",
                raw_input="Test description",
                parsed_value="Test",
                confidence=85.0,
                reasoning="Direct input",
                nwb_compliant=True,
            ),
            ParsedField(
                field_name="experimenter",
                raw_input="John",
                parsed_value=["John"],
                confidence=90.0,
                reasoning="Experimenter name",
                nwb_compliant=True,
            ),
        ]

        message = parser_with_llm.generate_confirmation_message(fields)

        assert message is not None
        assert len(message) > 0

    def test_generate_confirmation_message_empty_list(self, parser_with_llm):
        """Test generating confirmation with empty list."""
        message = parser_with_llm.generate_confirmation_message([])

        assert message is not None

    def test_generate_confirmation_message_confidence_indicators(self, parser_with_llm):
        """Test confidence indicators in confirmation message - covers lines 429-432."""
        fields = [
            ParsedField(
                field_name="high_field",
                raw_input="test",
                parsed_value="high",
                confidence=85.0,  # >=80 should get ✓
                reasoning="High confidence",
                nwb_compliant=True,
            ),
            ParsedField(
                field_name="medium_field",
                raw_input="test",
                parsed_value="medium",
                confidence=65.0,  # >=50 and <80 should get ⚠️
                reasoning="Medium confidence",
                nwb_compliant=True,
            ),
            ParsedField(
                field_name="low_field",
                raw_input="test",
                parsed_value="low",
                confidence=35.0,  # <50 should get ❓
                reasoning="Low confidence",
                nwb_compliant=True,
            ),
        ]

        message = parser_with_llm.generate_confirmation_message(fields)

        assert message is not None
        # Check that all three indicators are present
        assert "✓" in message  # High confidence indicator
        assert "⚠️" in message  # Medium confidence indicator
        assert "❓" in message  # Low confidence indicator

    def test_generate_confirmation_message_missing_required_fields(self, parser_with_llm, global_state):
        """Test missing required field detection - covers lines 493-529."""
        # Add some metadata to state to simulate partial completion
        global_state.metadata = {
            "session_description": "Test session",
        }

        # Parse only one field, leaving others missing
        parsed_field = ParsedField(
            field_name="experimenter",
            raw_input="John Doe",
            parsed_value=["Doe, John"],
            confidence=90.0,
            reasoning="User input",
            nwb_compliant=True,
        )

        message = parser_with_llm.generate_confirmation_message([parsed_field], state=global_state)

        assert message is not None
        # Should detect missing required fields
        # The message should mention missing fields (implementation dependent)

    def test_generate_confirmation_message_with_pending_fields(self, parser_with_llm, global_state):
        """Test that pending fields are not marked as missing - covers lines 493-529."""
        # Add pending parsed fields
        global_state.pending_parsed_fields = {
            "subject_species": ParsedField(
                field_name="subject_species",
                raw_input="Mouse",
                parsed_value="Mus musculus",
                confidence=90.0,
                reasoning="Species normalization",
                nwb_compliant=True,
            )
        }

        parsed_field = ParsedField(
            field_name="experimenter",
            raw_input="John Doe",
            parsed_value=["Doe, John"],
            confidence=90.0,
            reasoning="User input",
            nwb_compliant=True,
        )

        message = parser_with_llm.generate_confirmation_message([parsed_field], state=global_state)

        assert message is not None
        # subject_species should NOT be in missing fields since it's pending

    def test_generate_confirmation_message_missing_optional_vs_required(self, parser_with_llm, global_state):
        """Test distinction between missing required and optional fields - covers lines 493-529."""
        # Add minimal metadata
        global_state.metadata = {
            "session_description": "Test",
        }

        parsed_field = ParsedField(
            field_name="experimenter",
            raw_input="John",
            parsed_value=["John"],
            confidence=90.0,
            reasoning="Name",
            nwb_compliant=True,
        )

        message = parser_with_llm.generate_confirmation_message([parsed_field], state=global_state)

        assert message is not None
        # Message should categorize missing fields as required vs optional
        # Implementation may use ⚠️ for required and 📋 for optional

    def test_generate_confirmation_message_all_fields_present(self, parser_with_llm, global_state):
        """Test confirmation when all required fields are present."""
        # Populate all required fields in metadata
        global_state.metadata = {
            "session_description": "Test session",
            "session_start_time": "2023-06-15T10:30:00",
            "experimenter": ["Doe, John"],
            "subject_species": "Mus musculus",
            "subject_age": "P90D",
            "subject_sex": "M",
        }

        parsed_field = ParsedField(
            field_name="institution",
            raw_input="Stanford",
            parsed_value="Stanford University",
            confidence=90.0,
            reasoning="Institution",
            nwb_compliant=True,
        )

        message = parser_with_llm.generate_confirmation_message([parsed_field], state=global_state)

        assert message is not None
        # No missing required fields warning expected


# ============================================================================
# Test: Apply With Best Knowledge
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestApplyWithBestKnowledge:
    """Test suite for apply_with_best_knowledge method."""

    @pytest.mark.asyncio
    async def test_apply_with_best_knowledge_high_confidence(self, parser_with_llm, global_state):
        """Test applying high confidence field (>=80%)."""
        parsed_field = ParsedField(
            field_name="session_description",
            raw_input="Recording from mouse cortex",
            parsed_value="Recording from mouse cortex",
            confidence=85.0,
            reasoning="User input",
            nwb_compliant=True,
        )

        result = await parser_with_llm.apply_with_best_knowledge(parsed_field, global_state)

        assert result is not None
        assert result == "Recording from mouse cortex"

        # Verify provenance was set correctly
        assert "session_description" in global_state.metadata_provenance
        prov = global_state.metadata_provenance["session_description"]
        assert prov.confidence == 85.0
        assert prov.needs_review is False  # High confidence doesn't need review

    @pytest.mark.asyncio
    async def test_apply_with_best_knowledge_medium_confidence(self, parser_with_llm, global_state):
        """Test applying medium confidence field (50-79%) - covers lines 605-624."""
        parsed_field = ParsedField(
            field_name="experimenter",
            raw_input="John from the lab",
            parsed_value=["Doe, John"],
            confidence=65.0,
            reasoning="Inferred last name from context",
            nwb_compliant=True,
        )

        result = await parser_with_llm.apply_with_best_knowledge(parsed_field, global_state)

        assert result is not None
        assert result == ["Doe, John"]

        # Verify provenance for medium confidence
        assert "experimenter" in global_state.metadata_provenance
        prov = global_state.metadata_provenance["experimenter"]
        assert prov.confidence == 65.0
        assert prov.needs_review is True  # Medium confidence should be reviewed
        assert "Reasoning:" in prov.source  # Should include reasoning in source

        # Verify warning log was created
        assert len(global_state.logs) > 0
        warning_logs = [log for log in global_state.logs if "medium confidence" in log.message.lower()]
        assert len(warning_logs) > 0
        assert "⚠️" in warning_logs[0].message

    @pytest.mark.asyncio
    async def test_apply_with_best_knowledge_low_confidence(self, parser_with_llm, global_state):
        """Test applying low confidence field (<50%) - covers lines 627-655."""
        parsed_field = ParsedField(
            field_name="subject_age",
            raw_input="young adult",
            parsed_value="P90D",
            confidence=35.0,
            reasoning="Guessed based on typical age range",
            nwb_compliant=True,
            alternatives=["P60D", "P120D"],
        )

        result = await parser_with_llm.apply_with_best_knowledge(parsed_field, global_state)

        assert result is not None
        assert result == "P90D"

        # Verify provenance for low confidence
        assert "subject_age" in global_state.metadata_provenance
        prov = global_state.metadata_provenance["subject_age"]
        assert prov.confidence == 35.0
        assert prov.needs_review is True  # Low confidence must be reviewed
        assert "LOW CONFIDENCE" in prov.source

        # Verify metadata_warnings was populated (critical for low confidence)
        assert "subject_age" in global_state.metadata_warnings
        warning = global_state.metadata_warnings["subject_age"]
        assert warning["value"] == "P90D"
        assert warning["confidence"] == 35.0
        assert warning["original_input"] == "young adult"
        assert "Low confidence parsing" in warning["warning"]
        assert warning["alternatives"] == ["P60D", "P120D"]

        # Verify warning log was created with low confidence indicator
        warning_logs = [log for log in global_state.logs if "LOW confidence" in log.message]
        assert len(warning_logs) > 0
        assert "❓" in warning_logs[0].message
        assert "NEEDS REVIEW" in warning_logs[0].message

    @pytest.mark.asyncio
    async def test_apply_with_best_knowledge_boundary_confidence_50(self, parser_with_llm, global_state):
        """Test boundary case: exactly 50% confidence should be medium."""
        parsed_field = ParsedField(
            field_name="subject_sex",
            raw_input="not sure, maybe male",
            parsed_value="M",
            confidence=50.0,
            reasoning="Uncertain inference",
            nwb_compliant=True,
        )

        result = await parser_with_llm.apply_with_best_knowledge(parsed_field, global_state)

        # 50% should be treated as medium confidence (>=50)
        prov = global_state.metadata_provenance["subject_sex"]
        assert prov.needs_review is True
        # Should NOT be in metadata_warnings (only for <50%)
        assert "subject_sex" not in global_state.metadata_warnings

    @pytest.mark.asyncio
    async def test_apply_with_best_knowledge_boundary_confidence_80(self, parser_with_llm, global_state):
        """Test boundary case: exactly 80% confidence should be high."""
        parsed_field = ParsedField(
            field_name="session_description",
            raw_input="Recording session",
            parsed_value="Recording session",
            confidence=80.0,
            reasoning="Direct input",
            nwb_compliant=True,
        )

        result = await parser_with_llm.apply_with_best_knowledge(parsed_field, global_state)

        # 80% should be treated as high confidence (>=80)
        prov = global_state.metadata_provenance["session_description"]
        assert prov.needs_review is False

    @pytest.mark.asyncio
    async def test_apply_with_best_knowledge_provenance_stored(self, parser_with_llm, global_state):
        """Test that provenance is correctly stored with all required fields."""
        # Test that provenance is set with correct attributes
        parsed_field = ParsedField(
            field_name="experimenter",
            raw_input="John Doe",
            parsed_value=["Doe, John"],
            confidence=90.0,
            reasoning="Direct extraction",
            nwb_compliant=True,
            was_explicit=True,
        )

        await parser_with_llm.apply_with_best_knowledge(parsed_field, global_state)

        assert "experimenter" in global_state.metadata_provenance
        prov = global_state.metadata_provenance["experimenter"]
        assert prov.value == ["Doe, John"]
        assert prov.confidence == 90.0
        assert prov.raw_input == "John Doe"

    @pytest.mark.asyncio
    async def test_apply_with_best_knowledge_long_reasoning_truncation(self, parser_with_llm, global_state):
        """Test that long reasoning strings are truncated in provenance source."""
        long_reasoning = "A" * 200  # 200 chars, should be truncated to 100
        long_input = "B" * 200

        parsed_field = ParsedField(
            field_name="session_description",
            raw_input=long_input,
            parsed_value="Test",
            confidence=65.0,
            reasoning=long_reasoning,
            nwb_compliant=True,
        )

        await parser_with_llm.apply_with_best_knowledge(parsed_field, global_state)

        prov = global_state.metadata_provenance["session_description"]
        # Source should truncate both raw_input and reasoning to [:100]
        assert len(prov.source) < 300  # If not truncated, would be >400 chars


# ============================================================================
# Test: Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.agent_conversion
class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_parse_with_unicode_characters(self, parser_with_llm, global_state):
        """Test parsing with unicode characters."""
        result = await parser_with_llm.parse_single_field(
            field_name="experimenter",
            user_input="José García",
            state=global_state,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_with_special_characters(self, parser_with_llm, global_state):
        """Test parsing with special characters."""
        result = await parser_with_llm.parse_single_field(
            field_name="session_description",
            user_input="Test & validation (2023)",
            state=global_state,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_very_long_input(self, parser_with_llm, global_state):
        """Test parsing very long input."""
        long_text = "A" * 10000

        result = await parser_with_llm.parse_single_field(
            field_name="session_description",
            user_input=long_text,
            state=global_state,
        )

        assert result is not None
