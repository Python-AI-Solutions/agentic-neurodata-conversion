"""Knowledge Graph Service configuration.

The KG service shares the project's unified configuration object
(`agentic_neurodata_conversion.config.Settings`).
"""

from agentic_neurodata_conversion.config import Settings
from agentic_neurodata_conversion.config import get_settings as _get_settings
from agentic_neurodata_conversion.config import reset_settings as _reset_settings


def get_settings(env_file: str | None = None) -> Settings:
    """Return unified Settings (optionally from a specific env file)."""
    return _get_settings(env_file=env_file)


def reset_settings() -> None:
    """Reset cached settings (primarily for tests)."""
    _reset_settings()
