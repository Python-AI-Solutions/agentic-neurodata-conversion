"""Unit Tests for Observation Model.

Tests for kg_service/models/observation.py.
"""

from datetime import datetime

import pytest

from agentic_neurodata_conversion.kg_service.models.observation import (
    Observation,
    ObservationCreateRequest,
    ObservationResponse,
)


@pytest.mark.unit
def test_observation_model_creation():
    """Test Observation model creation."""
    obs = Observation(
        observation_id="obs-123",
        field_path="subject.species",
        raw_value="mouse",
        normalized_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        source_type="user",
        source_file="test.nwb",
        confidence=0.95,
        created_at=datetime.now(),
        is_active=True,
        provenance_json={"user_id": "test_user"},
    )

    assert obs.field_path == "subject.species"
    assert obs.confidence == 0.95
    assert obs.raw_value == "mouse"
    assert obs.normalized_value == "Mus musculus"
    assert obs.ontology_term_id == "NCBITaxon:10090"
    assert obs.source_type == "user"
    assert obs.is_active is True


@pytest.mark.unit
def test_observation_minimal_fields():
    """Test Observation with minimal required fields."""
    obs = Observation(field_path="subject.species", raw_value="mouse", source_type="user", confidence=0.95)

    assert obs.field_path == "subject.species"
    assert obs.raw_value == "mouse"
    assert obs.normalized_value is None
    assert obs.ontology_term_id is None
    assert obs.is_active is True
    assert obs.provenance_json == {}


@pytest.mark.unit
def test_observation_create_request():
    """Test ObservationCreateRequest model."""
    request = ObservationCreateRequest(
        field_path="subject.species",
        raw_value="mouse",
        normalized_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        source_type="user",
        source_file="test.nwb",
        confidence=0.95,
        provenance_json={"user_id": "test_user", "session_id": "sess_123"},
    )

    assert request.field_path == "subject.species"
    assert request.raw_value == "mouse"
    assert request.normalized_value == "Mus musculus"
    assert request.source_type == "user"
    assert request.confidence == 0.95
    assert "session_id" in request.provenance_json


@pytest.mark.unit
def test_observation_response():
    """Test ObservationResponse model."""
    response = ObservationResponse(observation_id="obs-123", status="stored")

    assert response.observation_id == "obs-123"
    assert response.status == "stored"


@pytest.mark.unit
def test_observation_provenance_json_default():
    """Test that provenance_json defaults to empty dict."""
    obs = Observation(field_path="subject.species", raw_value="test", source_type="user", confidence=1.0)

    assert obs.provenance_json == {}
    assert isinstance(obs.provenance_json, dict)


@pytest.mark.unit
def test_observation_is_active_default():
    """Test that is_active defaults to True."""
    obs = Observation(field_path="subject.species", raw_value="test", source_type="user", confidence=1.0)

    assert obs.is_active is True
