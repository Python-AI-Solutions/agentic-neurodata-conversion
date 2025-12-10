"""API Tests for Validate Endpoint.

Tests for kg_service/api/v1/validate.py endpoint.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from agentic_neurodata_conversion.kg_service.api.v1.validate import validate_endpoint
from agentic_neurodata_conversion.kg_service.models.requests import ValidateRequest, ValidateResponse


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_endpoint_valid():
    """Test validate endpoint with valid value."""
    mock_service = Mock()
    mock_service.validate_field = AsyncMock(return_value={"is_valid": True, "confidence": 1.0, "warnings": []})

    request = ValidateRequest(field_path="subject.species", value="Mus musculus")

    response = await validate_endpoint(request, mock_service)

    assert isinstance(response, ValidateResponse)
    assert response.is_valid is True
    assert response.confidence == 1.0
    assert len(response.warnings) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_endpoint_invalid():
    """Test validate endpoint with invalid value."""
    mock_service = Mock()
    mock_service.validate_field = AsyncMock(
        return_value={"is_valid": False, "confidence": 0.0, "warnings": ["No ontology match found"]}
    )

    request = ValidateRequest(field_path="subject.species", value="unicorn")

    response = await validate_endpoint(request, mock_service)

    assert response.is_valid is False
    assert response.confidence == 0.0
    assert len(response.warnings) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_endpoint_synonym_match():
    """Test validate endpoint with synonym match (still valid)."""
    mock_service = Mock()
    mock_service.validate_field = AsyncMock(return_value={"is_valid": True, "confidence": 0.95, "warnings": []})

    request = ValidateRequest(field_path="subject.species", value="mouse")

    response = await validate_endpoint(request, mock_service)

    assert response.is_valid is True
    assert response.confidence == 0.95


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_endpoint_error_handling():
    """Test validate endpoint error handling."""
    mock_service = Mock()
    mock_service.validate_field = AsyncMock(side_effect=Exception("Database error"))

    request = ValidateRequest(field_path="subject.species", value="Mus musculus")

    with pytest.raises(HTTPException) as exc_info:
        await validate_endpoint(request, mock_service)

    assert exc_info.value.status_code == 500
    assert "Validation failed" in str(exc_info.value.detail)


@pytest.mark.unit
def test_validate_request_validation():
    """Test ValidateRequest model validation."""
    request = ValidateRequest(field_path="subject.species", value="Mus musculus")
    assert request.field_path == "subject.species"
    assert request.value == "Mus musculus"


@pytest.mark.unit
def test_validate_response_model():
    """Test ValidateResponse model."""
    response = ValidateResponse(is_valid=True, confidence=1.0, warnings=[])

    assert response.is_valid is True
    assert response.confidence == 1.0
    assert len(response.warnings) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_endpoint_brain_region():
    """Test validate endpoint with brain region."""
    mock_service = Mock()
    mock_service.validate_field = AsyncMock(return_value={"is_valid": True, "confidence": 1.0, "warnings": []})

    request = ValidateRequest(field_path="ecephys.ElectrodeGroup.location", value="hippocampus")

    response = await validate_endpoint(request, mock_service)

    assert response.is_valid is True
    assert response.confidence == 1.0
