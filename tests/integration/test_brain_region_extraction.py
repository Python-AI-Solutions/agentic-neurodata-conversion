"""
Integration test to verify brain_region field extraction after schema fix.

Tests that brain_region fields are properly extracted from user input when
included in the NWBDANDISchema. Uses mocked LLM service to avoid API calls.
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


@pytest.mark.asyncio
@pytest.mark.integration
async def test_brain_region_extraction_ammon(mock_llm_ammon):
    """Test that brain_region 'Ammon' is extracted from user input."""
    parser = IntelligentMetadataParser(llm_service=mock_llm_ammon)
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
async def test_brain_region_extraction_hippocampus(mock_llm_hippocampus):
    """Test that brain_region 'hippocampus' is extracted from user input."""
    parser = IntelligentMetadataParser(llm_service=mock_llm_hippocampus)
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
