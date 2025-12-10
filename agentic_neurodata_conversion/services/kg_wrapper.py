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

    async def infer_value(
        self,
        field_path: str,
        subject_id: str,
        source_file: str,
    ) -> dict[str, Any]:
        """
        Infer field value from historical observations.

        Calls the KG service inference API to get suggestions based on
        historical observations for the given subject and field.

        Args:
            field_path: Field to infer (e.g., "subject.species", "experimenter")
            subject_id: Subject identifier
            source_file: Current file being processed (excluded from evidence)

        Returns:
            Dict containing:
            - has_suggestion (bool): Whether a suggestion is available
            - suggested_value (Any|None): Suggested value
            - ontology_term_id (str|None): Ontology term ID if applicable
            - confidence (float): Confidence score (0.8 if suggestion, 0.0 otherwise)
            - requires_confirmation (bool): Whether user confirmation needed
            - reasoning (str): Explanation of result
            - evidence_count (int): Number of supporting observations (if has_suggestion)
            - contributing_sessions (list[dict]|None): List of sessions that contributed evidence,
                each containing 'source_file' and 'created_at' (only if has_suggestion=True)

        Example:
            >>> result = await kg_wrapper.infer_value("subject.species", "mouse001", "session_C.nwb")
            >>> if result["has_suggestion"]:
            >>>     print(f"Suggested: {result['suggested_value']}")
            >>>     print(f"Based on: {result['contributing_sessions']}")
        """
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(
                    f"{self.kg_base_url}/api/v1/infer",
                    json={
                        "field_path": field_path,
                        "subject_id": subject_id,
                        "source_file": source_file,  # Fixed: API expects source_file, not target_file
                    },
                )

                if response.status_code == 200:
                    return response.json()  # type: ignore[no-any-return]
                else:
                    logger.warning(
                        f"KG inference returned status {response.status_code} for {field_path} (attempt {attempt + 1})"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))
                    else:
                        logger.error(f"KG inference failed after {self.max_retries} attempts")
                        return self._no_suggestion_response("KG service returned error status")

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"KG inference connection failed for {field_path} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error("KG inference service unavailable after retries")
                    return self._no_suggestion_response("KG service unavailable")

            except Exception as e:
                logger.error(f"Unexpected error during KG inference for {field_path}: {e}")
                return self._no_suggestion_response(f"Inference error: {str(e)}")

        return self._no_suggestion_response("Max retries exceeded")

    async def semantic_validate(
        self,
        species_term_id: str,
        anatomy_term_id: str,
    ) -> dict[str, Any]:
        """
        Validate cross-field compatibility between species and anatomy terms.

        Calls the KG service semantic validation API to check if the given
        species-anatomy combination is semantically compatible (e.g., does
        the species have the anatomical structure?).

        Args:
            species_term_id: Species ontology term ID (e.g., "NCBITaxon:10090")
            anatomy_term_id: Anatomy ontology term ID (e.g., "UBERON:0001954")

        Returns:
            Dict containing:
            - is_compatible (bool): Whether combination is valid
            - confidence (float): Confidence score (0.95 for known, 0.0 for unknown)
            - reasoning (str): Explanation of result
            - species_ancestors (list[str]): Species taxonomy hierarchy
            - anatomy_ancestors (list[str]): Anatomy hierarchy
            - warnings (list[str]): Any warnings about the combination

        Example:
            >>> result = await kg_wrapper.semantic_validate("NCBITaxon:10090", "UBERON:0001954")
            >>> if result["is_compatible"]:
            >>>     print(f"Valid: {result['reasoning']}")
            >>> else:
            >>>     print(f"Invalid: {result['reasoning']}")
        """
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(
                    f"{self.kg_base_url}/api/v1/semantic-validate",
                    json={
                        "species_term_id": species_term_id,
                        "anatomy_term_id": anatomy_term_id,
                    },
                )

                if response.status_code == 200:
                    return response.json()  # type: ignore[no-any-return]
                else:
                    logger.warning(
                        f"KG semantic validation returned status {response.status_code} (attempt {attempt + 1})"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))
                    else:
                        logger.error(f"KG semantic validation failed after {self.max_retries} attempts")
                        return self._no_validation_response("KG service returned error status")

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"KG semantic validation connection failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    logger.error("KG semantic validation service unavailable after retries")
                    return self._no_validation_response("KG service unavailable")

            except Exception as e:
                logger.error(f"Unexpected error during KG semantic validation: {e}")
                return self._no_validation_response(f"Validation error: {str(e)}")

        return self._no_validation_response("Max retries exceeded")

    def _no_validation_response(self, reason: str) -> dict[str, Any]:
        """Return standard 'validation unavailable' response (permissive default)."""
        return {
            "is_compatible": True,  # Permissive: allow when validation unavailable
            "confidence": 0.0,
            "reasoning": f"Cross-field validation unavailable: {reason}. Assuming compatible.",
            "species_ancestors": [],
            "anatomy_ancestors": [],
            "warnings": [f"Semantic validation unavailable: {reason}"],
        }

    def _no_suggestion_response(self, reason: str) -> dict[str, Any]:
        """Return standard 'no suggestion' response."""
        return {
            "has_suggestion": False,
            "suggested_value": None,
            "ontology_term_id": None,
            "confidence": 0.0,
            "requires_confirmation": False,
            "reasoning": reason,
        }

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
