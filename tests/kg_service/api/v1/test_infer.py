"""API Tests for Inference Endpoint.

Tests for kg_service/api/v1/infer.py endpoint.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from agentic_neurodata_conversion.kg_service.api.v1.infer import InferRequest, InferResponse, infer_endpoint


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_with_suggestion():
    """Test inference endpoint with valid suggestion."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": True,
            "suggested_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "confidence": 0.8,
            "requires_confirmation": True,
            "reasoning": "Based on 2 prior observations with 100% agreement",
        }
    )

    request = InferRequest(
        field_path="subject.species", source_file="subject_001_session_C.nwb", subject_id="subject_001"
    )

    response = await infer_endpoint(request, mock_engine)

    assert isinstance(response, InferResponse)
    assert response.has_suggestion is True
    assert response.suggested_value == "Mus musculus"
    assert response.ontology_term_id == "NCBITaxon:10090"
    assert response.confidence == 0.8
    assert response.requires_confirmation is True
    assert "2 prior observations" in response.reasoning


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_no_suggestion_insufficient_evidence():
    """Test inference endpoint with insufficient evidence."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": False,
            "suggested_value": None,
            "ontology_term_id": None,
            "confidence": 0.0,
            "requires_confirmation": False,
            "reasoning": "Insufficient evidence (need ≥2 observations with 100% agreement)",
        }
    )

    request = InferRequest(field_path="subject.species", source_file="new_file.nwb", subject_id="subject_new")

    response = await infer_endpoint(request, mock_engine)

    assert response.has_suggestion is False
    assert response.suggested_value is None
    assert response.ontology_term_id is None
    assert response.confidence == 0.0
    assert response.requires_confirmation is False
    assert "Insufficient evidence" in response.reasoning


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_unsupported_field():
    """Test inference endpoint with unsupported field path."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": False,
            "suggested_value": None,
            "ontology_term_id": None,
            "confidence": 0.0,
            "requires_confirmation": False,
            "reasoning": "Inference not supported for subject.age",
        }
    )

    request = InferRequest(field_path="subject.age", source_file="test.nwb", subject_id="subject_001")

    response = await infer_endpoint(request, mock_engine)

    assert response.has_suggestion is False
    assert response.confidence == 0.0
    assert "not supported" in response.reasoning
    assert "subject.age" in response.reasoning


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_three_observations():
    """Test inference with more than minimum observations."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": True,
            "suggested_value": "Rattus norvegicus",
            "ontology_term_id": "NCBITaxon:10116",
            "confidence": 0.8,
            "requires_confirmation": True,
            "reasoning": "Based on 3 prior observations with 100% agreement",
        }
    )

    request = InferRequest(field_path="subject.species", source_file="session_new.nwb", subject_id="subject_002")

    response = await infer_endpoint(request, mock_engine)

    assert response.has_suggestion is True
    assert response.suggested_value == "Rattus norvegicus"
    assert response.confidence == 0.8
    assert "3 prior observations" in response.reasoning


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_empty_subject_id():
    """Test inference with empty subject_id."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": False,
            "suggested_value": None,
            "ontology_term_id": None,
            "confidence": 0.0,
            "requires_confirmation": False,
            "reasoning": "Insufficient evidence (need ≥2 observations with 100% agreement)",
        }
    )

    request = InferRequest(field_path="subject.species", source_file="test.nwb", subject_id="")

    response = await infer_endpoint(request, mock_engine)

    assert response.has_suggestion is False
    # Verify engine was still called with empty subject_id
    mock_engine.infer_field.assert_called_once_with(field_path="subject.species", subject_id="", target_file="test.nwb")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_error_handling():
    """Test inference endpoint error handling."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(side_effect=Exception("Database connection error"))

    request = InferRequest(field_path="subject.species", source_file="test.nwb", subject_id="subject_001")

    with pytest.raises(HTTPException) as exc_info:
        await infer_endpoint(request, mock_engine)

    assert exc_info.value.status_code == 500
    assert "Inference failed" in str(exc_info.value.detail)
    assert "Database connection error" in str(exc_info.value.detail)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_calls_engine_with_correct_params():
    """Test that endpoint calls inference engine with correct parameters."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": True,
            "suggested_value": "Homo sapiens",
            "ontology_term_id": "NCBITaxon:9606",
            "confidence": 0.8,
            "requires_confirmation": True,
            "reasoning": "Based on 2 prior observations with 100% agreement",
        }
    )

    request = InferRequest(
        field_path="subject.species", source_file="subject_001_session_C.nwb", subject_id="subject_001"
    )

    await infer_endpoint(request, mock_engine)

    # Verify engine was called with correct parameters
    mock_engine.infer_field.assert_called_once_with(
        field_path="subject.species", subject_id="subject_001", target_file="subject_001_session_C.nwb"
    )


@pytest.mark.unit
def test_infer_request_validation():
    """Test InferRequest model validation."""
    # Valid request
    request = InferRequest(field_path="subject.species", source_file="test.nwb", subject_id="subject_001")
    assert request.field_path == "subject.species"
    assert request.source_file == "test.nwb"
    assert request.subject_id == "subject_001"

    # Test with different field paths
    request2 = InferRequest(field_path="subject.age", source_file="file.nwb", subject_id="subject_002")
    assert request2.field_path == "subject.age"


@pytest.mark.unit
def test_infer_response_model_with_suggestion():
    """Test InferResponse model with suggestion."""
    response = InferResponse(
        has_suggestion=True,
        suggested_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        confidence=0.8,
        requires_confirmation=True,
        reasoning="Based on 2 prior observations with 100% agreement",
    )

    assert response.has_suggestion is True
    assert response.suggested_value == "Mus musculus"
    assert response.ontology_term_id == "NCBITaxon:10090"
    assert response.confidence == 0.8
    assert response.requires_confirmation is True


@pytest.mark.unit
def test_infer_response_model_no_suggestion():
    """Test InferResponse model without suggestion."""
    response = InferResponse(
        has_suggestion=False,
        suggested_value=None,
        ontology_term_id=None,
        confidence=0.0,
        requires_confirmation=False,
        reasoning="Insufficient evidence",
    )

    assert response.has_suggestion is False
    assert response.suggested_value is None
    assert response.ontology_term_id is None
    assert response.confidence == 0.0
    assert response.requires_confirmation is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_human_species():
    """Test inference with human species."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": True,
            "suggested_value": "Homo sapiens",
            "ontology_term_id": "NCBITaxon:9606",
            "confidence": 0.8,
            "requires_confirmation": True,
            "reasoning": "Based on 4 prior observations with 100% agreement",
        }
    )

    request = InferRequest(field_path="subject.species", source_file="clinical_data.nwb", subject_id="patient_123")

    response = await infer_endpoint(request, mock_engine)

    assert response.suggested_value == "Homo sapiens"
    assert response.ontology_term_id == "NCBITaxon:9606"
    assert response.has_suggestion is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_special_characters_in_file_name():
    """Test inference with special characters in file name."""
    mock_engine = Mock()
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": True,
            "suggested_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "confidence": 0.8,
            "requires_confirmation": True,
            "reasoning": "Based on 2 prior observations with 100% agreement",
        }
    )

    request = InferRequest(
        field_path="subject.species", source_file="subject_001_session-2023-12-01_run#3.nwb", subject_id="subject_001"
    )

    response = await infer_endpoint(request, mock_engine)

    assert response.has_suggestion is True
    # Verify file name was passed correctly
    mock_engine.infer_field.assert_called_once()
    call_args = mock_engine.infer_field.call_args
    assert call_args.kwargs["target_file"] == "subject_001_session-2023-12-01_run#3.nwb"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_endpoint_long_reasoning():
    """Test inference with long reasoning text."""
    mock_engine = Mock()
    long_reasoning = (
        "Based on 5 prior observations with 100% agreement. "
        "All observations from sessions A, B, C, D, and E consistently "
        "identified the species as Mus musculus (house mouse). "
        "High confidence in suggestion."
    )
    mock_engine.infer_field = AsyncMock(
        return_value={
            "has_suggestion": True,
            "suggested_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "confidence": 0.8,
            "requires_confirmation": True,
            "reasoning": long_reasoning,
        }
    )

    request = InferRequest(field_path="subject.species", source_file="session_F.nwb", subject_id="subject_001")

    response = await infer_endpoint(request, mock_engine)

    assert response.reasoning == long_reasoning
    assert len(response.reasoning) > 100
