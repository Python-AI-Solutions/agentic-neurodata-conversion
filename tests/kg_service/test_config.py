"""Configuration Tests.

Validates the unified pydantic-settings configuration used by the KG service
and the main application.
"""

import pytest
from pydantic import ValidationError


def test_settings_load_from_nested_env(monkeypatch):
    """Verify nested env vars (using __ delimiter) are loaded."""
    monkeypatch.setenv("GRAPH_DB__URI", "bolt://test:7687")
    monkeypatch.setenv("GRAPH_DB__USER", "testuser")
    monkeypatch.setenv("GRAPH_DB__PASSWORD", "testpass")
    monkeypatch.setenv("KG__SERVICE_URL", "http://localhost:9999")

    from agentic_neurodata_conversion.config import get_settings, reset_settings

    reset_settings()

    settings = get_settings()
    assert settings.graph_db.uri == "bolt://test:7687"
    assert settings.graph_db.user == "testuser"
    assert settings.graph_db.password == "testpass"
    assert settings.kg.service_url == "http://localhost:9999"


def test_settings_defaults(monkeypatch):
    """Verify default values for optional settings."""
    monkeypatch.delenv("ENV_FILE", raising=False)
    monkeypatch.delenv("GRAPH_DB__URI", raising=False)
    monkeypatch.delenv("GRAPH_DB__USER", raising=False)
    monkeypatch.delenv("GRAPH_DB__PASSWORD", raising=False)
    monkeypatch.delenv("GRAPH_DB__DATABASE", raising=False)
    monkeypatch.delenv("KG__SERVICE_URL", raising=False)
    monkeypatch.delenv("KG__ENABLED", raising=False)
    monkeypatch.delenv("KG__TIMEOUT_S", raising=False)
    monkeypatch.delenv("KG__MAX_RETRIES", raising=False)

    from agentic_neurodata_conversion.config import get_settings, reset_settings

    reset_settings()
    settings = get_settings()

    assert settings.graph_db.uri == "bolt://localhost:7687"
    assert settings.graph_db.user == "neo4j"
    assert settings.graph_db.password is None
    assert settings.kg.service_url == "http://localhost:8001"
    assert settings.kg.enabled is True
    assert settings.kg.timeout_s == 5.0
    assert settings.kg.max_retries == 2


def test_kg_client_validation():
    """Verify KG client field validation works."""
    from agentic_neurodata_conversion.config import KGClientConfig

    with pytest.raises(ValidationError):
        KGClientConfig(timeout_s=100.0)
    with pytest.raises(ValidationError):
        KGClientConfig(timeout_s=0.05)
    with pytest.raises(ValidationError):
        KGClientConfig(max_retries=10)
