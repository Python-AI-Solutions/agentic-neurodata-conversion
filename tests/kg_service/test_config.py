"""Configuration Tests.

Tests for kg_service configuration management using pydantic-settings.
Validates environment variable loading, defaults, and field validation.
"""

import pytest
from pydantic import ValidationError


def test_settings_load_from_env(monkeypatch):
    """Verify settings load from environment variables."""
    monkeypatch.setenv("NEO4J_URI", "bolt://test:7687")
    monkeypatch.setenv("NEO4J_USER", "testuser")
    monkeypatch.setenv("NEO4J_PASSWORD", "testpass")

    from kg_service.config import get_settings, reset_settings

    reset_settings()  # Clear cached settings

    settings = get_settings()
    assert settings.neo4j_uri == "bolt://test:7687"
    assert settings.neo4j_user == "testuser"
    assert settings.neo4j_password == "testpass"


def test_settings_defaults(monkeypatch):
    """Verify default values for optional settings."""
    # Set only required field
    monkeypatch.setenv("NEO4J_PASSWORD", "testpass")

    from kg_service.config import get_settings, reset_settings

    reset_settings()

    settings = get_settings()
    assert settings.neo4j_uri == "bolt://localhost:7687"
    assert settings.neo4j_user == "neo4j"
    assert settings.kg_service_url == "http://localhost:8001"
    assert settings.kg_service_enabled is True
    assert settings.kg_service_timeout == 5.0
    assert settings.kg_max_retries == 2


def test_settings_validation(monkeypatch):
    """Verify field validation works."""
    monkeypatch.setenv("NEO4J_PASSWORD", "pass")

    from kg_service.config import KGServiceSettings, reset_settings

    reset_settings()

    # Test timeout too high
    with pytest.raises(ValidationError):
        KGServiceSettings(
            neo4j_password="pass",
            kg_service_timeout=100.0,  # Max is 30.0
        )

    # Test timeout too low
    with pytest.raises(ValidationError):
        KGServiceSettings(
            neo4j_password="pass",
            kg_service_timeout=0.05,  # Min is 0.1
        )

    # Test max_retries too high
    with pytest.raises(ValidationError):
        KGServiceSettings(
            neo4j_password="pass",
            kg_max_retries=10,  # Max is 5
        )
