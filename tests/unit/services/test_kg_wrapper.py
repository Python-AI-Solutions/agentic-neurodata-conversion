"""Unit tests for KG Wrapper Service.

Tests HTTP client integration, retry logic, and fallback behavior.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from agentic_neurodata_conversion.services.kg_wrapper import KGWrapper, get_kg_wrapper, reset_kg_wrapper


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_success():
    """Test successful normalization call."""
    wrapper = KGWrapper(kg_base_url="http://test:8001", timeout=5.0, max_retries=2)

    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "field_path": "subject.species",
        "raw_value": "mouse",
        "normalized_value": "Mus musculus",
        "ontology_term_id": "NCBITaxon:10090",
        "match_type": "exact",
        "confidence": 0.95,
        "status": "validated",
        "action_required": False,
        "warnings": [],
    }

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.normalize(field_path="subject.species", value="mouse")

    assert result["normalized_value"] == "Mus musculus"
    assert result["ontology_term_id"] == "NCBITaxon:10090"
    assert result["confidence"] == 0.95
    assert result["status"] == "validated"

    # Verify correct API call
    wrapper._client.post.assert_called_once()
    call_args = wrapper._client.post.call_args
    assert call_args[0][0] == "http://test:8001/api/v1/normalize"
    assert call_args[1]["json"]["field_path"] == "subject.species"
    assert call_args[1]["json"]["value"] == "mouse"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_with_context():
    """Test normalization with context parameters."""
    wrapper = KGWrapper()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "validated", "confidence": 0.9}

    wrapper._client.post = AsyncMock(return_value=mock_response)

    context = {"source": "user_input", "session_id": "test-123"}
    await wrapper.normalize(field_path="subject.sex", value="male", context=context)

    # Verify context was passed
    call_args = wrapper._client.post.call_args
    assert call_args[1]["json"]["context"] == context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_retry_then_success():
    """Test retry logic: first attempt fails, second succeeds."""
    wrapper = KGWrapper(max_retries=2)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "validated", "confidence": 0.8}

    # First call raises exception, second succeeds
    wrapper._client.post = AsyncMock(side_effect=[httpx.ConnectError("Connection failed"), mock_response])

    result = await wrapper.normalize(field_path="subject.species", value="rat")

    # Should succeed on retry
    assert result["status"] == "validated"
    assert wrapper._client.post.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_timeout_then_fallback():
    """Test timeout leading to fallback mode."""
    wrapper = KGWrapper(max_retries=2)

    # All attempts timeout
    wrapper._client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

    result = await wrapper.normalize(field_path="subject.species", value="mouse")

    # Should return fallback response
    assert result["status"] == "fallback"
    assert result["confidence"] == 0.0
    assert result["normalized_value"] == "mouse"  # Pass-through
    assert result["ontology_term_id"] is None
    assert result["action_required"] is True
    assert "KG service not responding" in result["warnings"][0]

    # Verify all retries were attempted
    assert wrapper._client.post.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_non_200_status_fallback():
    """Test non-200 status code leading to fallback."""
    wrapper = KGWrapper(max_retries=2)

    # Return 500 error
    mock_response = Mock()
    mock_response.status_code = 500

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.normalize(field_path="subject.species", value="dog")

    # Should return fallback after all retries
    assert result["status"] == "fallback"
    assert result["raw_value"] == "dog"
    assert wrapper._client.post.call_count == 2


@pytest.mark.unit
def test_fallback_normalize_structure():
    """Test fallback response has correct structure."""
    wrapper = KGWrapper()

    result = wrapper._fallback_normalize(field_path="subject.species", value="cat")

    # Verify all required fields
    assert result["field_path"] == "subject.species"
    assert result["raw_value"] == "cat"
    assert result["normalized_value"] == "cat"
    assert result["ontology_term_id"] is None
    assert result["match_type"] is None
    assert result["confidence"] == 0.0
    assert result["status"] == "fallback"
    assert result["action_required"] is True
    assert len(result["warnings"]) == 3
    assert "Semantic validation unavailable" in result["warnings"][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_success():
    """Test successful validation call."""
    wrapper = KGWrapper()

    mock_response = Mock()
    mock_response.json.return_value = {"is_valid": True, "warnings": []}

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.validate(field_path="subject.species", value="Mus musculus")

    assert result["is_valid"] is True
    assert result["warnings"] == []

    # Verify correct endpoint
    call_args = wrapper._client.post.call_args
    assert call_args[0][0] == "http://localhost:8001/api/v1/validate"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_exception_handling():
    """Test validate returns error structure on exception."""
    wrapper = KGWrapper()

    wrapper._client.post = AsyncMock(side_effect=Exception("Network error"))

    result = await wrapper.validate(field_path="subject.species", value="invalid")

    assert result["is_valid"] is False
    assert "KG service unavailable" in result["warnings"][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_observation_success():
    """Test successful observation storage."""
    wrapper = KGWrapper()

    mock_response = Mock()
    mock_response.json.return_value = {"status": "success", "observation_id": "obs-123"}

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.store_observation(
        field_path="subject.species",
        raw_value="mouse",
        normalized_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        source_type="user",
        source_file="test.nwb",
        confidence=0.95,
        provenance={"user_id": "user-1", "session_id": "session-1"},
    )

    assert result["status"] == "success"
    assert result["observation_id"] == "obs-123"

    # Verify correct payload
    call_args = wrapper._client.post.call_args
    assert call_args[0][0] == "http://localhost:8001/api/v1/observations"
    payload = call_args[1]["json"]
    assert payload["field_path"] == "subject.species"
    assert payload["raw_value"] == "mouse"
    assert payload["normalized_value"] == "Mus musculus"
    assert payload["ontology_term_id"] == "NCBITaxon:10090"
    assert payload["confidence"] == 0.95


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_observation_exception_handling():
    """Test observation storage error handling."""
    wrapper = KGWrapper()

    wrapper._client.post = AsyncMock(side_effect=Exception("Database connection error"))

    result = await wrapper.store_observation(
        field_path="subject.species",
        raw_value="rat",
        normalized_value="Rattus norvegicus",
        ontology_term_id=None,
        source_type="user",
        source_file="test.nwb",
        confidence=0.5,
        provenance={},
    )

    assert result["status"] == "error"
    assert "Database connection error" in result["message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_client():
    """Test HTTP client cleanup."""
    wrapper = KGWrapper()
    wrapper._client.aclose = AsyncMock()

    await wrapper.close()

    wrapper._client.aclose.assert_called_once()


@pytest.mark.unit
def test_get_kg_wrapper_singleton():
    """Test singleton pattern returns same instance."""
    reset_kg_wrapper()  # Start fresh

    wrapper1 = get_kg_wrapper()
    wrapper2 = get_kg_wrapper()

    assert wrapper1 is wrapper2
    assert isinstance(wrapper1, KGWrapper)


@pytest.mark.unit
def test_reset_kg_wrapper():
    """Test resetting global instance."""
    reset_kg_wrapper()

    wrapper1 = get_kg_wrapper()
    reset_kg_wrapper()
    wrapper2 = get_kg_wrapper()

    # Should be different instances after reset
    assert wrapper1 is not wrapper2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_empty_value():
    """Test normalization with empty value."""
    wrapper = KGWrapper()

    wrapper._client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

    result = await wrapper.normalize(field_path="subject.species", value="")

    # Should fallback gracefully
    assert result["status"] == "fallback"
    assert result["raw_value"] == ""
    assert result["normalized_value"] == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_exponential_backoff():
    """Test exponential backoff between retries."""
    wrapper = KGWrapper(max_retries=3)

    wrapper._client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await wrapper.normalize(field_path="subject.species", value="mouse")

        # Verify sleep was called with increasing delays
        assert mock_sleep.call_count == 2  # max_retries - 1
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [0.5, 1.0]  # 0.5 * 1, 0.5 * 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_special_characters():
    """Test normalization with special characters in value."""
    wrapper = KGWrapper()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "validated",
        "confidence": 0.85,
        "normalized_value": "Test-Value_123",
    }

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.normalize(field_path="subject.species", value="Test-Value_123!@#")

    assert result["status"] == "validated"

    # Verify special characters passed through
    call_args = wrapper._client.post.call_args
    assert "Test-Value_123!@#" in str(call_args)


@pytest.mark.unit
def test_kg_wrapper_custom_config():
    """Test KGWrapper with custom configuration."""
    wrapper = KGWrapper(kg_base_url="http://custom:9000", timeout=10.0, max_retries=5)

    assert wrapper.kg_base_url == "http://custom:9000"
    assert wrapper.timeout == 10.0
    assert wrapper.max_retries == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_none_context():
    """Test normalization with None context (default parameter)."""
    wrapper = KGWrapper()

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "validated"}

    wrapper._client.post = AsyncMock(return_value=mock_response)

    await wrapper.normalize(field_path="subject.species", value="mouse", context=None)

    # Verify empty dict used as default
    call_args = wrapper._client.post.call_args
    assert call_args[1]["json"]["context"] == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_observation_with_none_ontology_id():
    """Test storing observation without ontology term ID."""
    wrapper = KGWrapper()

    mock_response = Mock()
    mock_response.json.return_value = {"status": "success"}

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.store_observation(
        field_path="subject.age",
        raw_value="5 months",
        normalized_value="P5M",
        ontology_term_id=None,  # No ontology term
        source_type="user",
        source_file="test.nwb",
        confidence=0.7,
        provenance={},
    )

    assert result["status"] == "success"

    # Verify None was passed correctly
    call_args = wrapper._client.post.call_args
    assert call_args[1]["json"]["ontology_term_id"] is None


# === Phase 1: Inference Integration Tests ===


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_value_success():
    """Test successful inference call returning historical suggestion."""
    wrapper = KGWrapper(kg_base_url="http://test:8001", timeout=5.0, max_retries=2)

    # Mock successful inference response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "has_suggestion": True,
        "suggested_value": "Mus musculus",
        "ontology_term_id": "NCBITaxon:10090",
        "confidence": 0.8,
        "requires_confirmation": True,
        "reasoning": "Based on 2 prior observations with 100% agreement",
        "evidence_count": 2,
    }

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.infer_value(
        field_path="subject.species", subject_id="subject_001", source_file="session_C.nwb"
    )

    # Verify correct response structure
    assert result["has_suggestion"] is True
    assert result["suggested_value"] == "Mus musculus"
    assert result["ontology_term_id"] == "NCBITaxon:10090"
    assert result["confidence"] == 0.8
    assert result["requires_confirmation"] is True
    assert result["evidence_count"] == 2
    assert "2 prior observations" in result["reasoning"]

    # Verify correct API call
    wrapper._client.post.assert_called_once()
    call_args = wrapper._client.post.call_args
    assert call_args[0][0] == "http://test:8001/api/v1/infer"
    assert call_args[1]["json"]["field_path"] == "subject.species"
    assert call_args[1]["json"]["subject_id"] == "subject_001"
    assert call_args[1]["json"]["source_file"] == "session_C.nwb"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_value_no_suggestion():
    """Test inference when no historical data is available."""
    wrapper = KGWrapper()

    # Mock response with no suggestion
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "has_suggestion": False,
        "suggested_value": None,
        "ontology_term_id": None,
        "confidence": 0.0,
        "requires_confirmation": False,
        "reasoning": "Insufficient evidence (need ≥2 observations with 100% agreement)",
    }

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.infer_value(
        field_path="subject.species", subject_id="new_subject_999", source_file="first_session.nwb"
    )

    # Verify no suggestion response
    assert result["has_suggestion"] is False
    assert result["suggested_value"] is None
    assert result["ontology_term_id"] is None
    assert result["confidence"] == 0.0
    assert "Insufficient evidence" in result["reasoning"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_value_service_unavailable():
    """Test graceful fallback when KG service is unavailable."""
    wrapper = KGWrapper(max_retries=2)

    # All attempts fail with connection error
    wrapper._client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    result = await wrapper.infer_value(field_path="subject.species", subject_id="subject_001", source_file="test.nwb")

    # Verify fallback response (no suggestion)
    assert result["has_suggestion"] is False
    assert result["suggested_value"] is None
    assert result["ontology_term_id"] is None
    assert result["confidence"] == 0.0
    assert result["requires_confirmation"] is False
    assert "KG service unavailable" in result["reasoning"]

    # Verify all retries were attempted
    assert wrapper._client.post.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_value_timeout_with_retry():
    """Test inference timeout with retry logic."""
    wrapper = KGWrapper(max_retries=3)

    # First two attempts timeout, third succeeds
    mock_success = Mock()
    mock_success.status_code = 200
    mock_success.json.return_value = {
        "has_suggestion": True,
        "suggested_value": "F",
        "ontology_term_id": None,
        "confidence": 0.8,
        "requires_confirmation": True,
        "reasoning": "Based on 3 prior observations",
    }

    wrapper._client.post = AsyncMock(
        side_effect=[httpx.TimeoutException("Timeout"), httpx.TimeoutException("Timeout"), mock_success]
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await wrapper.infer_value(field_path="subject.sex", subject_id="subject_002", source_file="test.nwb")

        # Should succeed on third attempt
        assert result["has_suggestion"] is True
        assert result["suggested_value"] == "F"
        assert wrapper._client.post.call_count == 3

        # Verify exponential backoff
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [0.5, 1.0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_value_http_error_status():
    """Test inference with HTTP error status code."""
    wrapper = KGWrapper(max_retries=2)

    # Return 500 error
    mock_response = Mock()
    mock_response.status_code = 500

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.infer_value(field_path="subject.species", subject_id="subject_001", source_file="test.nwb")

    # Should return no suggestion after retries
    assert result["has_suggestion"] is False
    assert "KG service returned error status" in result["reasoning"]
    assert wrapper._client.post.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_value_non_ontology_field():
    """Test inference for non-ontology fields (e.g., experimenter, strain)."""
    wrapper = KGWrapper()

    # Mock inference for experimenter field (no ontology)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "has_suggestion": True,
        "suggested_value": "Smith, Jane",
        "ontology_term_id": None,  # No ontology for experimenter
        "confidence": 0.8,
        "requires_confirmation": True,
        "reasoning": "Based on 5 prior observations with 100% agreement",
        "evidence_count": 5,
    }

    wrapper._client.post = AsyncMock(return_value=mock_response)

    result = await wrapper.infer_value(field_path="experimenter", subject_id="subject_001", source_file="test.nwb")

    # Verify non-ontology field inference works
    assert result["has_suggestion"] is True
    assert result["suggested_value"] == "Smith, Jane"
    assert result["ontology_term_id"] is None  # Non-ontology field
    assert result["evidence_count"] == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_value_unexpected_exception():
    """Test inference handling unexpected exception."""
    wrapper = KGWrapper(max_retries=1)

    # Raise unexpected exception
    wrapper._client.post = AsyncMock(side_effect=ValueError("Unexpected error"))

    result = await wrapper.infer_value(field_path="subject.species", subject_id="subject_001", source_file="test.nwb")

    # Should gracefully return no suggestion
    assert result["has_suggestion"] is False
    assert "Inference error" in result["reasoning"]
    assert "Unexpected error" in result["reasoning"]
