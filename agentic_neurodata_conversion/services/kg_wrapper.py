"""KG Integration Wrapper.

Provides integration layer between MCP agents and KG service.
Implements retry logic and fallback mode when KG unavailable.
"""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class KGWrapper:
    """Wrapper for KG service with fallback support."""

    def __init__(self, kg_base_url: str = "http://localhost:8001", timeout: float = 5.0, max_retries: int = 2):
        self.kg_base_url = kg_base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def normalize(self, field_path: str, value: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Normalize a metadata field value.

        Falls back to basic validation if KG service unavailable.
        """
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(
                    f"{self.kg_base_url}/api/v1/normalize",
                    json={"field_path": field_path, "value": value, "context": context or {}},
                )

                if response.status_code == 200:
                    return response.json()  # type: ignore[no-any-return]

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"KG service connection failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error("KG service unavailable, using fallback")
                    return self._fallback_normalize(field_path, value)

        return self._fallback_normalize(field_path, value)

    def _fallback_normalize(self, field_path: str, value: Any) -> dict[str, Any]:
        """
        Fallback normalization when KG service unavailable.

        Returns basic validation with warning flag.
        """
        return {
            "field_path": field_path,
            "raw_value": value,
            "normalized_value": value,  # Pass through unchanged
            "ontology_term_id": None,
            "match_type": None,
            "confidence": 0.0,
            "status": "fallback",
            "action_required": True,
            "warnings": [
                "Semantic validation unavailable - KG service not responding",
                "Value passed through without ontology validation",
                "Manual review recommended",
            ],
        }

    async def validate(self, field_path: str, value: Any) -> dict[str, Any]:
        """Quick validation check."""
        try:
            response = await self._client.post(
                f"{self.kg_base_url}/api/v1/validate", json={"field_path": field_path, "value": value}
            )
            return response.json()  # type: ignore[no-any-return]
        except Exception:
            return {"is_valid": False, "warnings": ["KG service unavailable"]}

    async def store_observation(
        self,
        field_path: str,
        raw_value: Any,
        normalized_value: Any,
        ontology_term_id: str | None,
        source_type: str,
        source_file: str,
        confidence: float,
        provenance: dict[str, Any],
    ) -> dict[str, str]:
        """Store observation in Neo4j."""
        try:
            response = await self._client.post(
                f"{self.kg_base_url}/api/v1/observations",
                json={
                    "field_path": field_path,
                    "raw_value": raw_value,
                    "normalized_value": normalized_value,
                    "ontology_term_id": ontology_term_id,
                    "source_type": source_type,
                    "source_file": source_file,
                    "confidence": confidence,
                    "provenance_json": provenance,
                },
            )
            return response.json()  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Failed to store observation: {e}")
            return {"status": "error", "message": str(e)}

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()


# Global instance
_kg_wrapper: KGWrapper | None = None


def get_kg_wrapper() -> KGWrapper:
    """Get global KG wrapper instance."""
    global _kg_wrapper
    if _kg_wrapper is None:
        _kg_wrapper = KGWrapper()
    return _kg_wrapper


def reset_kg_wrapper() -> None:
    """Reset global instance for testing."""
    global _kg_wrapper
    _kg_wrapper = None
