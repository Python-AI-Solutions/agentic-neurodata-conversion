"""
Integration test to verify brain_region field extraction after schema fix.

Tests that brain_region fields are properly extracted from user input when
included in the NWBDANDISchema. Uses mocked LLM and KG services to avoid API calls.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.agents.metadata.intelligent_parser import IntelligentMetadataParser
from agentic_neurodata_conversion.models import GlobalState
from agentic_neurodata_conversion.services import LLMService


@pytest.fixture
def mock_llm_ammon():
    """Create a mock LLM service for 'Ammon' brain region extraction."""
    service = Mock(spec=LLMService)

    response = {
        "fields": [
            {
                "field_name": "subject_id",
                "raw_value": "test_001",
                "normalized_value": "test_001",
                "confidence": 1.0,
                "reasoning": "Direct extraction from user input",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
            {
                "field_name": "species",
                "raw_value": "mouse",
                "normalized_value": "Mus musculus",
                "confidence": 0.95,
                "reasoning": "Common name 'mouse' maps to Mus musculus",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
            {
                "field_name": "sex",
                "raw_value": "male",
                "normalized_value": "M",
                "confidence": 1.0,
                "reasoning": "Direct extraction and NWB translation",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
            {
                "field_name": "brain_region",
                "raw_value": "Ammon",
                "normalized_value": "Ammon",
                "confidence": 0.9,
                "reasoning": "Extracted from user input, refers to Ammon's horn (hippocampus)",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": ["hippocampus", "Ammon's horn"],
            },
            {
                "field_name": "experimenter",
                "raw_value": "Dr. Test",
                "normalized_value": "Dr. Test",
                "confidence": 1.0,
                "reasoning": "Direct extraction",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
            {
                "field_name": "institution",
                "raw_value": "Test University",
                "normalized_value": "Test University",
                "confidence": 1.0,
                "reasoning": "Direct extraction",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
            {
                "field_name": "session_start_time",
                "raw_value": "2025-01-15 10:00 AM",
                "normalized_value": "2025-01-15T10:00:00",
                "confidence": 0.95,
                "reasoning": "Converted to ISO 8601 format",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
        ]
    }

    service.generate_structured_output = AsyncMock(return_value=response)
    service.is_available = Mock(return_value=True)
    service.get_model_name = Mock(return_value="mock-brain-region-extractor")

    return service


@pytest.fixture
def mock_llm_hippocampus():
    """Create a mock LLM service for 'hippocampus' brain region extraction."""
    service = Mock(spec=LLMService)

    response = {
        "fields": [
            {
                "field_name": "subject_id",
                "raw_value": "test_004a",
                "normalized_value": "test_004a",
                "confidence": 1.0,
                "reasoning": "Direct extraction from user input",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
            {
                "field_name": "species",
                "raw_value": "mouse",
                "normalized_value": "Mus musculus",
                "confidence": 0.95,
                "reasoning": "Common name 'mouse' maps to Mus musculus",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
            {
                "field_name": "brain_region",
                "raw_value": "hippocampus",
                "normalized_value": "hippocampus",
                "confidence": 0.95,
                "reasoning": "Direct extraction from user input",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
            {
                "field_name": "sex",
                "raw_value": "male",
                "normalized_value": "M",
                "confidence": 1.0,
                "reasoning": "Direct extraction and NWB translation",
                "extraction_type": "explicit",
                "needs_review": False,
                "alternatives": [],
            },
        ]
    }

    service.generate_structured_output = AsyncMock(return_value=response)
    service.is_available = Mock(return_value=True)
    service.get_model_name = Mock(return_value="mock-brain-region-extractor")

    return service


@pytest.fixture
def mock_kg_wrapper():
    """Create a mock KG wrapper that simulates ontology normalization."""
    kg_wrapper = Mock()

    # Mock normalize() to return KG validation responses
    async def mock_normalize(field_path, value, context=None):
        """Mock KG normalization for brain_region fields."""
        # Normalize "Ammon" and "hippocampus" to "Ammon's horn" (UBERON:0001954)
        if value.lower() in ["ammon", "hippocampus"]:
            return {
                "status": "validated",
                "normalized_value": "Ammon's horn",
                "ontology_term_id": "UBERON:0001954",
                "confidence": 0.85,
                "action_required": False,
                "reasoning": f"Ontology validation: UBERON:0001954. Synonym match: {value} -> Ammon's horn",
            }
        # For species field
        elif value.lower() == "mouse":
            return {
                "status": "validated",
                "normalized_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "confidence": 0.95,
                "action_required": False,
                "reasoning": "Ontology validation: NCBITaxon:10090. Synonym match: mouse -> Mus musculus",
            }
        # For sex field
        elif value.lower() in ["male", "m"]:
            return {
                "status": "validated",
                "normalized_value": "male",
                "ontology_term_id": "PATO:0000384",
                "confidence": 1.0,
                "action_required": False,
                "reasoning": "Ontology validation: PATO:0000384. Exact match: male",
            }
        else:
            return {
                "status": "not_found",
                "normalized_value": value,
                "ontology_term_id": None,
                "confidence": 0.0,
                "action_required": False,
                "reasoning": "No ontology match found",
            }

    # Mock semantic_validate() for cross-field validation
    async def mock_semantic_validate(species_term_id, anatomy_term_id):
        """Mock cross-field validation."""
        return {
            "is_compatible": True,
            "confidence": 0.95,
            "reasoning": "Compatible species-anatomy combination",
            "species_ancestors": [],
            "anatomy_ancestors": [],
            "warnings": [],
        }

    # Mock store_observation() to prevent errors
    async def mock_store_observation(**kwargs):
        """Mock observation storage."""
        return {"status": "success", "observation_id": "mock-id"}

    kg_wrapper.normalize = AsyncMock(side_effect=mock_normalize)
    kg_wrapper.semantic_validate = AsyncMock(side_effect=mock_semantic_validate)
    kg_wrapper.store_observation = AsyncMock(side_effect=mock_store_observation)

    return kg_wrapper


@pytest.mark.asyncio
@pytest.mark.integration
async def test_brain_region_extraction_ammon(mock_llm_ammon, mock_kg_wrapper):
    """Test that brain_region 'Ammon' is extracted from user input."""
    parser = IntelligentMetadataParser(llm_service=mock_llm_ammon)
    # Inject mock KG wrapper after parser creation
    parser.kg_wrapper = mock_kg_wrapper
    state = GlobalState()

    user_input = """
    subject_id: test_001
    species: mouse
    sex: male
    brain_region: Ammon
    experimenter: Dr. Test
    institution: Test University
    session_start_time: 2025-01-15 10:00 AM
    """

    parsed_fields = await parser.parse_natural_language_batch(user_input, state)

    # Verify brain_region was extracted
    brain_region_fields = [f for f in parsed_fields if f.field_name.lower() == "brain_region"]
    assert len(brain_region_fields) == 1, "brain_region field should be extracted"

    brain_region = brain_region_fields[0]
    assert brain_region.raw_input == "Ammon"
    # KG service normalizes "Ammon" to "Ammon's horn" (UBERON:0001954)
    assert brain_region.parsed_value == "Ammon's horn"
    assert brain_region.confidence >= 0.8

    # Verify other expected fields are also present
    field_names = {f.field_name.lower() for f in parsed_fields}
    assert "species" in field_names
    assert "sex" in field_names
    assert "experimenter" in field_names


@pytest.mark.asyncio
@pytest.mark.integration
async def test_brain_region_extraction_hippocampus(mock_llm_hippocampus, mock_kg_wrapper):
    """Test that brain_region 'hippocampus' is extracted from user input."""
    parser = IntelligentMetadataParser(llm_service=mock_llm_hippocampus)
    # Inject mock KG wrapper after parser creation
    parser.kg_wrapper = mock_kg_wrapper
    state = GlobalState()

    user_input = """
    subject_id: test_004a
    species: mouse
    brain_region: hippocampus
    sex: male
    """

    parsed_fields = await parser.parse_natural_language_batch(user_input, state)

    # Verify brain_region was extracted
    brain_region_fields = [f for f in parsed_fields if f.field_name.lower() == "brain_region"]
    assert len(brain_region_fields) == 1, "brain_region field should be extracted"

    brain_region = brain_region_fields[0]
    assert brain_region.raw_input == "hippocampus"
    # KG service normalizes "hippocampus" to "Ammon's horn" (UBERON:0001954) via synonym matching
    assert brain_region.parsed_value == "Ammon's horn"
    assert brain_region.confidence >= 0.8

    # Verify all fields from input are extracted
    field_names = {f.field_name.lower() for f in parsed_fields}
    assert "subject_id" in field_names
    assert "species" in field_names
    assert "brain_region" in field_names
    assert "sex" in field_names
