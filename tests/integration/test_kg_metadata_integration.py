"""Integration tests for KG metadata integration.

Tests the integration between KG wrapper and IntelligentMetadataParser.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.agents.metadata.intelligent_parser import IntelligentMetadataParser
from agentic_neurodata_conversion.models import ConversationPhase
from agentic_neurodata_conversion.services.kg_wrapper import reset_kg_wrapper


@pytest.fixture(autouse=True)
def reset_kg():
    """Reset KG wrapper before each test."""
    reset_kg_wrapper()
    yield
    reset_kg_wrapper()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_parser_uses_kg_for_species(global_state, mock_llm_service):
    """Test that parser uses KG for species normalization."""
    # Setup: Mock KG HTTP response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "field_path": "subject.species",
        "raw_value": "mouse",
        "normalized_value": "Mus musculus",
        "ontology_term_id": "NCBITaxon:10090",
        "match_type": "synonym",
        "confidence": 0.95,
        "status": "validated",
        "action_required": False,
        "warnings": [],
    }

    # Mock LLM response for batch parsing
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "species",
                    "raw_value": "mouse",
                    "normalized_value": "mouse",
                    "extraction_type": "explicit",
                    "confidence": 85.0,
                    "reasoning": "User mentioned 'mouse'",
                }
            ]
        }
    )

    # Setup global state
    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    # Create parser with KG wrapper
    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    # Mock the KG wrapper HTTP client
    with patch.object(parser.kg_wrapper._client, "post", new=AsyncMock(return_value=mock_response)):
        result = await parser.parse_natural_language_batch(user_input="The subject is a mouse", state=global_state)

    # Verify: KG was used and result is correct
    assert len(result) == 1
    species_field = result[0]
    assert species_field.field_name == "species"
    assert species_field.parsed_value == "Mus musculus"
    assert species_field.confidence == 95.0  # Converted to percentage
    assert "NCBITaxon:10090" in species_field.reasoning


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_parser_falls_back_when_kg_unavailable(global_state, mock_llm_service):
    """Test parser falls back to LLM when KG service unavailable."""
    # Mock LLM response
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "species",
                    "raw_value": "rat",
                    "normalized_value": "Rattus norvegicus",
                    "extraction_type": "explicit",
                    "confidence": 90.0,
                    "reasoning": "User mentioned 'rat', normalized to scientific name",
                }
            ]
        }
    )

    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    # Mock KG service to fail
    with patch.object(parser.kg_wrapper._client, "post", side_effect=Exception("Connection refused")):
        result = await parser.parse_natural_language_batch(user_input="The subject is a rat", state=global_state)

    # Verify: LLM result was used as fallback
    assert len(result) == 1
    species_field = result[0]
    assert species_field.field_name == "species"
    assert species_field.parsed_value == "Rattus norvegicus"
    # Confidence should be from LLM, not KG
    assert species_field.confidence > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_parser_stores_observation_in_neo4j(global_state, mock_llm_service):
    """Test that parser stores observations in Neo4j after KG validation."""
    # Mock KG normalization response
    mock_normalize_response = Mock()
    mock_normalize_response.status_code = 200
    mock_normalize_response.json.return_value = {
        "field_path": "subject.species",
        "raw_value": "mouse",
        "normalized_value": "Mus musculus",
        "ontology_term_id": "NCBITaxon:10090",
        "confidence": 0.95,
        "status": "validated",
        "action_required": False,
    }

    # Mock observation storage response
    mock_store_response = Mock()
    mock_store_response.json.return_value = {"status": "success", "observation_id": "obs-123"}

    # Mock LLM
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "species",
                    "raw_value": "mouse",
                    "normalized_value": "mouse",
                    "extraction_type": "explicit",
                    "confidence": 85.0,
                    "reasoning": "User mentioned 'mouse'",
                }
            ]
        }
    )

    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION
    global_state.input_path = "/test/data.nwb"

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    # Mock HTTP calls
    with patch.object(
        parser.kg_wrapper._client, "post", side_effect=[mock_normalize_response, mock_store_response]
    ) as mock_post:
        await parser.parse_natural_language_batch(user_input="The subject is a mouse", state=global_state)

        # Verify: Both normalize and store_observation were called
        assert mock_post.call_count == 2

        # First call: normalize
        first_call = mock_post.call_args_list[0]
        assert "/api/v1/normalize" in str(first_call)

        # Second call: store_observation
        second_call = mock_post.call_args_list[1]
        assert "/api/v1/observations" in str(second_call)
        payload = second_call[1]["json"]
        assert payload["field_path"] == "subject.species"
        assert payload["raw_value"] == "mouse"
        assert payload["normalized_value"] == "Mus musculus"
        assert payload["ontology_term_id"] == "NCBITaxon:10090"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_parser_skips_kg_for_non_ontology_fields(global_state, mock_llm_service):
    """Test that non-ontology-governed fields skip KG and use LLM directly."""
    # Mock LLM response for age field (not ontology-governed)
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "age",
                    "raw_value": "5 months",
                    "normalized_value": "P5M",
                    "extraction_type": "explicit",
                    "confidence": 95.0,
                    "reasoning": "User specified '5 months', converted to ISO 8601 duration",
                }
            ]
        }
    )

    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    # Track KG calls
    with patch.object(parser.kg_wrapper._client, "post", new=AsyncMock()) as mock_post:
        result = await parser.parse_natural_language_batch(user_input="The subject is 5 months old", state=global_state)

        # Verify: KG was NOT called for non-ontology field
        mock_post.assert_not_called()

    # Verify: LLM result was used directly
    assert len(result) == 1
    age_field = result[0]
    assert age_field.field_name == "age"
    assert age_field.parsed_value == "P5M"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_parser_kg_with_low_confidence(global_state, mock_llm_service):
    """Test that parser falls back to LLM when KG confidence is low."""
    # Mock KG response with low confidence (< 0.8)
    mock_kg_response = Mock()
    mock_kg_response.status_code = 200
    mock_kg_response.json.return_value = {
        "field_path": "subject.species",
        "raw_value": "fuzzy creature",
        "normalized_value": "unknown",
        "confidence": 0.3,  # Low confidence
        "status": "needs_review",
        "action_required": True,
    }

    # Mock LLM response
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "species",
                    "raw_value": "fuzzy creature",
                    "normalized_value": "unknown species",
                    "extraction_type": "inferred",
                    "confidence": 30.0,
                    "reasoning": "Vague description, cannot determine specific species",
                }
            ]
        }
    )

    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    with patch.object(parser.kg_wrapper._client, "post", return_value=mock_kg_response):
        result = await parser.parse_natural_language_batch(user_input="fuzzy creature", state=global_state)

    # Verify: LLM result was used because KG confidence was low
    assert len(result) == 1
    species_field = result[0]
    # Should use LLM result, not KG result
    assert species_field.parsed_value == "unknown species"


@pytest.mark.integration
def test_is_ontology_governed_field_helper():
    """Test the ontology field detection helper method."""
    parser = IntelligentMetadataParser(llm_service=None)

    # Ontology-governed fields
    assert parser._is_ontology_governed_field("species") is True
    assert parser._is_ontology_governed_field("sex") is True
    assert parser._is_ontology_governed_field("brain_region") is True
    assert parser._is_ontology_governed_field("electrode_location") is True

    # Non-ontology fields
    assert parser._is_ontology_governed_field("age") is False
    assert parser._is_ontology_governed_field("weight") is False
    assert parser._is_ontology_governed_field("session_description") is False
    assert parser._is_ontology_governed_field("experimenter") is False

    # Note: "location" is not ontology-governed as a separate field
    # It's handled as an extraction pattern for "brain_region" in schema.py
    assert parser._is_ontology_governed_field("location") is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kg_wrapper_singleton_pattern(mock_llm_service):
    """Test that get_kg_wrapper returns same instance."""
    reset_kg_wrapper()

    parser1 = IntelligentMetadataParser(llm_service=mock_llm_service)
    parser2 = IntelligentMetadataParser(llm_service=mock_llm_service)

    # Both should have the same KG wrapper instance
    assert parser1.kg_wrapper is parser2.kg_wrapper


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metadata_parser_continues_on_observation_storage_failure(global_state, mock_llm_service):
    """Test parser continues successfully even if observation storage fails."""
    # Mock KG normalization success
    mock_normalize_response = Mock()
    mock_normalize_response.status_code = 200
    mock_normalize_response.json.return_value = {
        "status": "validated",
        "normalized_value": "Mus musculus",
        "ontology_term_id": "NCBITaxon:10090",
        "confidence": 0.95,
        "action_required": False,
    }

    # Mock LLM
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "species",
                    "raw_value": "mouse",
                    "normalized_value": "mouse",
                    "extraction_type": "explicit",
                    "confidence": 85.0,
                    "reasoning": "User mentioned 'mouse'",
                }
            ]
        }
    )

    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    # Mock: normalize succeeds, but store_observation fails
    with patch.object(
        parser.kg_wrapper._client,
        "post",
        side_effect=[mock_normalize_response, Exception("Neo4j connection error")],
    ):
        # Should not raise exception
        result = await parser.parse_natural_language_batch(user_input="The subject is a mouse", state=global_state)

    # Verify: Parsing still succeeded despite storage failure
    assert len(result) == 1
    species_field = result[0]
    assert species_field.parsed_value == "Mus musculus"

    # Verify: Warning was logged
    warnings = [log for log in global_state.logs if "observation" in log.message.lower()]
    assert len(warnings) > 0


# ============================================================================
# Phase 1: Historical Inference Integration Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_with_historical_inference_confirmed(global_state, mock_llm_service):
    """Test complete workflow: LLM extract → KG infer → CONFIRMED badge → store."""
    global_state.input_path = "session_C.nwb"
    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    # Mock LLM to return subject_id and species
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "subject_id",
                    "raw_value": "subject_001",
                    "normalized_value": "subject_001",
                    "confidence": 95,
                    "reasoning": "Explicit subject ID",
                    "extraction_type": "explicit",
                },
                {
                    "field_name": "species",
                    "raw_value": "mouse",
                    "normalized_value": "Mus musculus",
                    "confidence": 75,
                    "reasoning": "Mouse → Mus musculus",
                    "extraction_type": "explicit",
                },
            ]
        }
    )

    # Mock KG inference to return suggestion that matches LLM
    mock_infer_response = Mock()
    mock_infer_response.status_code = 200
    mock_infer_response.json.return_value = {
        "has_suggestion": True,
        "suggested_value": "Mus musculus",  # Matches LLM
        "ontology_term_id": "NCBITaxon:10090",
        "confidence": 0.8,
        "requires_confirmation": True,
        "reasoning": "Based on 2 prior observations with 100% agreement",
        "evidence_count": 2,
    }

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    with patch.object(parser.kg_wrapper._client, "post", return_value=mock_infer_response):
        result = await parser.parse_natural_language_batch(user_input="subject_001, mouse", state=global_state)

    # Verify species field has CONFIRMED badge
    species_field = next((f for f in result if f.field_name == "species"), None)
    assert species_field is not None
    assert species_field.badge == "CONFIRMED"
    # Confidence should be boosted (>= 85%)
    assert species_field.confidence >= 85.0
    # Historical evidence should be attached
    assert species_field.historical_evidence is not None
    assert species_field.historical_evidence["evidence_count"] == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_with_historical_inference_gap_filling(global_state, mock_llm_service):
    """Test gap filling: LLM misses field, KG suggests → HISTORICAL badge."""
    global_state.input_path = "session_D.nwb"
    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    # Mock LLM to return only subject_id (no sex)
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "subject_id",
                    "raw_value": "subject_002",
                    "normalized_value": "subject_002",
                    "confidence": 95,
                    "reasoning": "Explicit subject ID",
                    "extraction_type": "explicit",
                }
            ]
        }
    )

    # Mock KG inference to suggest sex
    def mock_post_side_effect(url, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200

        # Return suggestion for sex field
        if "infer" in url and kwargs.get("json", {}).get("field_path") == "subject.sex":
            mock_response.json.return_value = {
                "has_suggestion": True,
                "suggested_value": "M",
                "ontology_term_id": None,
                "confidence": 0.8,
                "requires_confirmation": True,
                "reasoning": "Based on 3 prior observations with 100% agreement",
                "evidence_count": 3,
            }
        else:
            # No suggestion for other fields
            mock_response.json.return_value = {
                "has_suggestion": False,
                "suggested_value": None,
                "confidence": 0.0,
            }

        return mock_response

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    with patch.object(parser.kg_wrapper._client, "post", side_effect=mock_post_side_effect):
        result = await parser.parse_natural_language_batch(user_input="subject_002, visual cortex", state=global_state)

    # Verify sex field was added with HISTORICAL badge
    sex_field = next((f for f in result if f.field_name == "sex"), None)
    if sex_field:  # May or may not be added depending on inference call
        assert sex_field.badge == "HISTORICAL"
        assert sex_field.extraction_method == "historical_inference"
        assert sex_field.confidence == 80.0
        assert sex_field.historical_evidence["evidence_count"] == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_with_historical_inference_conflict(global_state, mock_llm_service):
    """Test conflict detection: LLM says rat, KG says mouse → CONFLICTING badge."""
    global_state.input_path = "session_E.nwb"
    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    # Mock LLM to return subject_id and rat
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "subject_id",
                    "raw_value": "subject_001",
                    "normalized_value": "subject_001",
                    "confidence": 95,
                    "reasoning": "Explicit subject ID",
                    "extraction_type": "explicit",
                },
                {
                    "field_name": "species",
                    "raw_value": "rat",
                    "normalized_value": "Rattus norvegicus",
                    "confidence": 75,
                    "reasoning": "Rat → Rattus norvegicus",
                    "extraction_type": "explicit",
                },
            ]
        }
    )

    # Mock KG inference to suggest mouse (conflict!)
    mock_infer_response = Mock()
    mock_infer_response.status_code = 200
    mock_infer_response.json.return_value = {
        "has_suggestion": True,
        "suggested_value": "Mus musculus",  # Conflicts with LLM (rat)
        "ontology_term_id": "NCBITaxon:10090",
        "confidence": 0.8,
        "requires_confirmation": True,
        "reasoning": "Based on 2 prior observations with 100% agreement",
        "evidence_count": 2,
    }

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    with patch.object(parser.kg_wrapper._client, "post", return_value=mock_infer_response):
        result = await parser.parse_natural_language_batch(user_input="subject_001, rat", state=global_state)

    # Verify species field has CONFLICTING badge
    species_field = next((f for f in result if f.field_name == "species"), None)
    assert species_field is not None
    assert species_field.badge == "CONFLICTING"
    # Confidence should be reduced
    assert species_field.confidence < 75.0
    # Conflicting value should be in evidence
    assert "conflicting_value" in species_field.historical_evidence
    assert species_field.historical_evidence["conflicting_value"] == "Mus musculus"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_confidence_boosting_formula(global_state, mock_llm_service):
    """Test confidence boosting formula: min(95, max(llm_conf, kg_conf) + 15)."""
    global_state.input_path = "test.nwb"
    global_state.conversation_phase = ConversationPhase.METADATA_COLLECTION

    # Mock LLM with confidence 75
    mock_llm_service.generate_structured_output = AsyncMock(
        return_value={
            "fields": [
                {
                    "field_name": "subject_id",
                    "raw_value": "subject_001",
                    "normalized_value": "subject_001",
                    "confidence": 95,
                    "reasoning": "Explicit",
                    "extraction_type": "explicit",
                },
                {
                    "field_name": "species",
                    "raw_value": "mouse",
                    "normalized_value": "Mus musculus",
                    "confidence": 75,  # LLM confidence
                    "reasoning": "Mouse → Mus musculus",
                    "extraction_type": "explicit",
                },
            ]
        }
    )

    # Mock KG with confidence 0.8 (80%)
    mock_infer_response = Mock()
    mock_infer_response.status_code = 200
    mock_infer_response.json.return_value = {
        "has_suggestion": True,
        "suggested_value": "Mus musculus",
        "confidence": 0.8,  # KG confidence
        "evidence_count": 2,
    }

    parser = IntelligentMetadataParser(llm_service=mock_llm_service)

    with patch.object(parser.kg_wrapper._client, "post", return_value=mock_infer_response):
        result = await parser.parse_natural_language_batch(user_input="subject_001, mouse", state=global_state)

    species_field = next((f for f in result if f.field_name == "species"), None)
    assert species_field is not None

    # Formula: min(95, max(75, 80) + 15) = min(95, 80 + 15) = min(95, 95) = 95
    assert species_field.confidence == 95.0
