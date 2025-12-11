"""Application configuration management.

Uses pydantic-settings to load environment variables, with a nested structure
using the ``__`` delimiter (e.g., ``API__PORT=8000``).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str, *, component: str, missing: list[str] | None = None) -> None:
        super().__init__(message)
        self.component = component
        self.missing = missing or []


class CoreConfig(BaseModel):
    """Core application settings."""

    anthropic_api_key: str | None = None
    debug: bool = False
    allow_missing_anthropic_api_key: bool = False


class PathsConfig(BaseModel):
    """Filesystem paths and limits."""

    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"
    log_dir: str = "./logs"
    max_upload_size_gb: float = Field(
        default=10.0,
        ge=0.1,
        le=1000.0,
    )


class APIConfig(BaseModel):
    """Main API (agentic-neurodata-conversion) server settings."""

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return ["*"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raw = str(value).strip()
        if raw.startswith("["):
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, list):
                    return [str(item).strip() for item in decoded if str(item).strip()] or ["*"]
            except Exception:
                pass
        # Accept comma-separated string (including "*")
        origins = [part.strip() for part in raw.split(",")]
        return [origin for origin in origins if origin] or ["*"]


class KGClientConfig(BaseModel):
    """Client-side configuration for talking to the KG service over HTTP."""

    enabled: bool = True
    service_url: str = "http://localhost:8001"
    timeout_s: float = Field(
        default=5.0,
        ge=0.1,
        le=30.0,
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )


class GraphDBConfig(BaseModel):
    """Graph database connection settings (Neo4j today, swappable later)."""

    backend: str = "neo4j"
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str | None = None
    database: str = "neo4j"


class KGServiceConfig(BaseModel):
    """KG service server configuration (when running as its own process)."""

    host: str = "0.0.0.0"
    port: int = Field(
        default=8001,
        ge=1,
        le=65535,
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://localhost:3000"],
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        default_origins = ["http://localhost:8000", "http://localhost:3000"]
        if value is None:
            return default_origins
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return cleaned or default_origins
        raw = str(value).strip()
        if raw.startswith("["):
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, list):
                    cleaned = [str(item).strip() for item in decoded if str(item).strip()]
                    return cleaned or default_origins
            except Exception:
                pass
        origins = [part.strip() for part in raw.split(",")]
        cleaned = [origin for origin in origins if origin]
        return cleaned or default_origins


class ComposePortsConfig(BaseModel):
    """Ports published on the host by the docker compose stack."""

    neo4j_http_port: int = Field(default=7474, ge=1, le=65535)
    neo4j_bolt_port: int = Field(default=7687, ge=1, le=65535)
    kg_service_port: int = Field(default=8001, ge=1, le=65535)
    frontend_port: int = Field(default=3000, ge=1, le=65535)


class Settings(BaseSettings):
    """Nested application settings container."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
        enable_decoding=False,
    )

    core: CoreConfig = CoreConfig()
    paths: PathsConfig = PathsConfig()
    api: APIConfig = APIConfig()
    kg: KGClientConfig = KGClientConfig()
    graph_db: GraphDBConfig = GraphDBConfig()
    kg_service: KGServiceConfig = KGServiceConfig()
    compose: ComposePortsConfig = ComposePortsConfig()

    def require_api(self) -> None:
        """Validate configuration required to run the main API service."""
        if self.core.allow_missing_anthropic_api_key:
            return
        if not self.core.anthropic_api_key:
            raise ConfigError(
                "Missing CORE__ANTHROPIC_API_KEY (required to run the app).",
                component="api",
                missing=["CORE__ANTHROPIC_API_KEY"],
            )

    async def require_graph_db(self, *, probe: bool = True) -> None:
        """Validate configuration required to talk to the graph DB, optionally probing connectivity."""
        missing: list[str] = []
        if not self.graph_db.uri:
            missing.append("GRAPH_DB__URI")
        if not self.graph_db.user:
            missing.append("GRAPH_DB__USER")
        if not self.graph_db.password:
            missing.append("GRAPH_DB__PASSWORD")
        if missing:
            raise ConfigError(
                "Missing graph DB settings.",
                component="graph_db",
                missing=missing,
            )

        if probe:
            ok = await _probe_neo4j_bolt(self.graph_db.uri, self.graph_db.user, self.graph_db.password)
            if not ok:
                raise ConfigError(
                    f"Neo4j is not reachable at {self.graph_db.uri}.",
                    component="graph_db",
                )

    async def require_kg_service(self, *, probe_graph_db: bool = True) -> None:
        """Validate configuration required to run the KG service."""
        await self.require_graph_db(probe=probe_graph_db)

    def require_kg_client(self) -> None:
        """Validate configuration required for the API to call the KG service."""
        if not self.kg.enabled:
            return
        if not self.kg.service_url:
            raise ConfigError(
                "Missing KG__SERVICE_URL (required when KG__ENABLED=true).",
                component="kg_client",
                missing=["KG__SERVICE_URL"],
            )


def get_settings(env_file: str | None = None) -> Settings:
    """Get settings, optionally loading from a specific env file."""
    resolved_env_file = _resolve_env_file(env_file)
    settings = Settings(_env_file=resolved_env_file)  # type: ignore[call-arg]

    # Minimal legacy env-var compatibility (env + dotenv file).
    dotenv = _read_simple_dotenv(resolved_env_file) if resolved_env_file else {}
    env = {**dotenv, **os.environ}

    if "CORE__ANTHROPIC_API_KEY" not in env and (api_key := env.get("ANTHROPIC_API_KEY")):
        settings.core.anthropic_api_key = api_key

    if "CORE__DEBUG" not in env and (debug := env.get("DEBUG")) is not None:
        settings.core.debug = debug.strip().lower() in ("1", "true", "yes", "y", "on")

    if "API__HOST" not in env and (host := env.get("HOST")):
        settings.api.host = host

    if "API__PORT" not in env and (port := env.get("PORT")):
        try:
            settings.api.port = int(port)
        except ValueError:
            pass

    if "API__CORS_ORIGINS" not in env and (cors := env.get("CORS_ORIGINS")):
        settings.api.cors_origins = APIConfig._parse_cors_origins(cors)  # type: ignore[attr-defined]

    if "PATHS__UPLOAD_DIR" not in env and (upload_dir := env.get("UPLOAD_DIR")):
        settings.paths.upload_dir = upload_dir
    if "PATHS__OUTPUT_DIR" not in env and (output_dir := env.get("OUTPUT_DIR")):
        settings.paths.output_dir = output_dir
    if "PATHS__LOG_DIR" not in env and (log_dir := env.get("LOG_DIR")):
        settings.paths.log_dir = log_dir
    if "PATHS__MAX_UPLOAD_SIZE_GB" not in env and (max_size := env.get("MAX_UPLOAD_SIZE_GB")):
        try:
            settings.paths.max_upload_size_gb = float(max_size)
        except ValueError:
            pass

    if "KG__SERVICE_URL" not in env and (kg_url := env.get("KG_SERVICE_URL")):
        settings.kg.service_url = kg_url
    if "KG__ENABLED" not in env and (enabled := env.get("KG_SERVICE_ENABLED")) is not None:
        settings.kg.enabled = enabled.strip().lower() in ("1", "true", "yes", "y", "on")
    if "KG__TIMEOUT_S" not in env and (timeout := env.get("KG_SERVICE_TIMEOUT")):
        try:
            settings.kg.timeout_s = float(timeout)
        except ValueError:
            pass
    if "KG__MAX_RETRIES" not in env and (retries := env.get("KG_MAX_RETRIES")):
        try:
            settings.kg.max_retries = int(retries)
        except ValueError:
            pass

    if "GRAPH_DB__URI" not in env and (neo4j_uri := env.get("NEO4J_URI")):
        settings.graph_db.uri = neo4j_uri
    if "GRAPH_DB__USER" not in env and (neo4j_user := env.get("NEO4J_USER")):
        settings.graph_db.user = neo4j_user
    if "GRAPH_DB__PASSWORD" not in env and (neo4j_password := env.get("NEO4J_PASSWORD")):
        settings.graph_db.password = neo4j_password
    if "GRAPH_DB__DATABASE" not in env and (neo4j_db := env.get("NEO4J_DATABASE")):
        settings.graph_db.database = neo4j_db

    if "KG_SERVICE__PORT" not in env and (kg_port := env.get("KG_SERVICE_PORT")):
        try:
            settings.kg_service.port = int(kg_port)
        except ValueError:
            pass
    if "KG_SERVICE__CORS_ORIGINS" not in env and (kg_cors := env.get("KG_SERVICE_CORS_ORIGINS")):
        settings.kg_service.cors_origins = KGServiceConfig._parse_cors_origins(kg_cors)  # type: ignore[attr-defined]

    if "COMPOSE__NEO4J_HTTP_PORT" not in env and (neo4j_http_port := env.get("NEO4J_HTTP_PORT")):
        try:
            settings.compose.neo4j_http_port = int(neo4j_http_port)
        except ValueError:
            pass
    if "COMPOSE__NEO4J_BOLT_PORT" not in env and (neo4j_bolt_port := env.get("NEO4J_BOLT_PORT")):
        try:
            settings.compose.neo4j_bolt_port = int(neo4j_bolt_port)
        except ValueError:
            pass
    if "COMPOSE__KG_SERVICE_PORT" not in env and (kg_service_port := env.get("KG_SERVICE_PORT")):
        try:
            settings.compose.kg_service_port = int(kg_service_port)
        except ValueError:
            pass
    if "COMPOSE__FRONTEND_PORT" not in env and (frontend_port := env.get("FRONTEND_PORT")):
        try:
            settings.compose.frontend_port = int(frontend_port)
        except ValueError:
            pass

    return settings


async def _probe_neo4j_bolt(uri: str, user: str, password: str, *, timeout_s: float = 2.0) -> bool:
    """Return True if Neo4j is reachable over Bolt."""
    parsed = urlparse(uri)
    if parsed.scheme not in ("bolt", "neo4j"):
        return True

    try:
        from neo4j import AsyncGraphDatabase  # lazy import; dependency is optional in some contexts

        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        try:
            await asyncio.wait_for(driver.verify_connectivity(), timeout=timeout_s)
            return True
        finally:
            await driver.close()
    except Exception:
        return False


def _resolve_env_file(env_file: str | None) -> str | None:
    """Resolve the env file path used for configuration.

    Order:
    1) explicit `env_file` argument (if provided)
    2) `$ENV_FILE` env var (if set)
    3) (non-pytest) first `.env` found by walking up from CWD
    4) (non-pytest) `.env` next to the repo root (adjacent to this package)
    """
    if env_file:
        return str(Path(env_file).expanduser().resolve())

    env_override = os.getenv("ENV_FILE")
    if env_override:
        return str(Path(env_override).expanduser().resolve())

    # Keep unit tests deterministic: by default, pytest runs should not implicitly
    # pick up a developer's local `.env`. Test runners can set `ENV_FILE=.env`
    # explicitly when they *do* want dotenv-based configuration.
    if "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST"):
        return None

    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return str(candidate)

    package_root = Path(__file__).resolve().parents[1]
    candidate = package_root / ".env"
    if candidate.exists():
        return str(candidate)

    return None


def _read_simple_dotenv(path: str) -> dict[str, str]:
    """Parse a simple dotenv file (KEY=VALUE), ignoring quotes/escapes."""
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except OSError:
        return {}

    values: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def reset_settings() -> None:
    """Reset settings (kept for test compatibility)."""
    return None
