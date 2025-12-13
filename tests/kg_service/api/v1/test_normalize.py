"""API Tests for Normalize Endpoint.

Tests for kg_service/api/v1/normalize.py endpoint.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from agentic_neurodata_conversion.kg_service.api.v1.normalize import normalize_endpoint
from agentic_neurodata_conversion.kg_service.models.requests import NormalizeRequest, NormalizeResponse


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_endpoint_exact_match():
    """Test normalize endpoint with exact match."""
    mock_service = Mock()
    mock_service.normalize_field = AsyncMock(
        return_value={
            "field_path": "subject.species",
            "raw_value": "Mus musculus",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "match_type": "exact",
            "confidence": 1.0,
            "status": "validated",
            "action_required": False,
            "warnings": [],
        }
    )

    request = NormalizeRequest(field_path="subject.species", value="Mus musculus")

    response = await normalize_endpoint(request, mock_service)

    assert isinstance(response, NormalizeResponse)
    assert response.field_path == "subject.species"
    assert response.status == "validated"
    assert response.confidence == 1.0
    assert response.match_type == "exact"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_endpoint_synonym_match():
    """Test normalize endpoint with synonym match."""
    mock_service = Mock()
    mock_service.normalize_field = AsyncMock(
        return_value={
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
    )

    request = NormalizeRequest(field_path="subject.species", value="mouse")

    response = await normalize_endpoint(request, mock_service)

    assert response.status == "validated"
    assert response.confidence == 0.95
    assert response.match_type == "synonym"
    assert response.normalized_value == "Mus musculus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_endpoint_needs_review():
    """Test normalize endpoint when normalization needs review."""
    mock_service = Mock()
    mock_service.normalize_field = AsyncMock(
        return_value={
            "field_path": "subject.species",
            "raw_value": "unicorn",
            "normalized_value": None,
            "ontology_term_id": None,
            "match_type": None,
            "confidence": 0.0,
            "status": "needs_review",
            "action_required": True,
            "warnings": ["No ontology match found for 'unicorn'"],
        }
    )

    request = NormalizeRequest(field_path="subject.species", value="unicorn")

    response = await normalize_endpoint(request, mock_service)

    assert response.status == "needs_review"
    assert response.confidence == 0.0
    assert response.action_required is True
    assert len(response.warnings) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_endpoint_with_context():
    """Test normalize endpoint with context."""
    mock_service = Mock()
    mock_service.normalize_field = AsyncMock(
        return_value={
            "field_path": "subject.species",
            "raw_value": "Mus musculus",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "match_type": "exact",
            "confidence": 1.0,
            "status": "validated",
            "action_required": False,
            "warnings": [],
        }
    )

    request = NormalizeRequest(
        field_path="subject.species", value="Mus musculus", context={"source_file": "test.nwb", "user_id": "test_user"}
    )

    response = await normalize_endpoint(request, mock_service)

    assert response.status == "validated"
    # Verify context was passed to service (including use_semantic_reasoning from Phase 2)
    mock_service.normalize_field.assert_called_once_with(
        field_path="subject.species",
        value="Mus musculus",
        context={"source_file": "test.nwb", "user_id": "test_user"},
        use_semantic_reasoning=True,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_endpoint_error_handling():
    """Test normalize endpoint error handling."""
    mock_service = Mock()
    mock_service.normalize_field = AsyncMock(side_effect=Exception("Database error"))

    request = NormalizeRequest(field_path="subject.species", value="Mus musculus")

    with pytest.raises(HTTPException) as exc_info:
        await normalize_endpoint(request, mock_service)

    assert exc_info.value.status_code == 500
    assert "Normalization failed" in str(exc_info.value.detail)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_endpoint_not_applicable():
    """Test normalize endpoint for non-ontology-governed field."""
    mock_service = Mock()
    mock_service.normalize_field = AsyncMock(
        return_value={
            "field_path": "subject.subject_id",
            "raw_value": "ABC123",
            "normalized_value": None,
            "ontology_term_id": None,
            "match_type": None,
            "confidence": 1.0,
            "status": "not_applicable",
            "action_required": False,
            "warnings": ["Field is not ontology-governed"],
        }
    )

    request = NormalizeRequest(field_path="subject.subject_id", value="ABC123")

    response = await normalize_endpoint(request, mock_service)

    assert response.status == "not_applicable"
    assert response.confidence == 1.0
    assert response.action_required is False


@pytest.mark.unit
def test_normalize_request_validation():
    """Test NormalizeRequest model validation."""
    # Valid request
    request = NormalizeRequest(field_path="subject.species", value="Mus musculus")
    assert request.field_path == "subject.species"
    assert request.value == "Mus musculus"
    assert request.context is None

    # With context
    request_with_context = NormalizeRequest(
        field_path="subject.species", value="mouse", context={"source_file": "test.nwb"}
    )
    assert request_with_context.context == {"source_file": "test.nwb"}


@pytest.mark.unit
def test_normalize_response_model():
    """Test NormalizeResponse model."""
    response = NormalizeResponse(
        field_path="subject.species",
        raw_value="mouse",
        normalized_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        match_type="synonym",
        confidence=0.95,
        status="validated",
        action_required=False,
        warnings=[],
    )

    assert response.field_path == "subject.species"
    assert response.normalized_value == "Mus musculus"
    assert response.confidence == 0.95
    assert response.status == "validated"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_endpoint_brain_region():
    """Test normalize endpoint with brain region."""
    mock_service = Mock()
    mock_service.normalize_field = AsyncMock(
        return_value={
            "field_path": "ecephys.ElectrodeGroup.location",
            "raw_value": "hippocampus",
            "normalized_value": "hippocampus",
            "ontology_term_id": "UBERON:0002421",
            "match_type": "exact",
            "confidence": 1.0,
            "status": "validated",
            "action_required": False,
            "warnings": [],
        }
    )

    request = NormalizeRequest(field_path="ecephys.ElectrodeGroup.location", value="hippocampus")

    response = await normalize_endpoint(request, mock_service)

    assert response.status == "validated"
    assert "UBERON:" in response.ontology_term_id
    assert response.confidence == 1.0
