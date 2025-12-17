"""KG Normalization Service.

Phase 2: Integrated with Semantic Reasoner (v1.0)

Normalization pipeline:
- With semantic reasoning (default): 4-stage validation with hierarchy traversal
  1. Exact match (confidence 1.0)
  2. Synonym match (confidence 0.95)
  3. Semantic search with hierarchy (confidence 0.85)
  4. Needs review (confidence 0.0)

- Without semantic reasoning (legacy): 3-stage string matching
  1. Exact match (confidence 1.0)
  2. Synonym match (confidence 0.95)
  3. Needs review (confidence 0.0)
"""

import logging
import unicodedata
from typing import Any

from agentic_neurodata_conversion.kg_service.db.neo4j_connection import AsyncNeo4jConnection
from agentic_neurodata_conversion.kg_service.services.semantic_reasoner import SemanticReasoner

logger = logging.getLogger(__name__)


class AsyncKGService:
    """Async service for ontology-based metadata normalization.

    Phase 2: Now integrates with SemanticReasoner for hierarchy-aware validation.
    """

    def __init__(self, neo4j_conn: AsyncNeo4jConnection):
        """Initialize KG service with Neo4j connection.

        Args:
            neo4j_conn: AsyncNeo4jConnection instance
        """
        self.neo4j_conn = neo4j_conn
        self.semantic_reasoner = SemanticReasoner(neo4j_conn)

    def _preprocess(self, value: str) -> str:
        """Preprocess input value for matching.

        - Lowercase
        - Strip whitespace
        - Unicode normalize (NFC)

        Args:
            value: Raw input value

        Returns:
            Preprocessed value
        """
        if not isinstance(value, str):
            value = str(value)

        # Unicode normalization
        value = unicodedata.normalize("NFC", value)

        # Lowercase and strip
        value = value.lower().strip()

        return value

    async def _get_schema_field(self, field_path: str) -> dict[str, Any] | None:
        """Get schema field information from Neo4j.

        Args:
            field_path: NWB field path

        Returns:
            Schema field dict or None if not found
        """
        query = """
        MATCH (f:SchemaField {field_path: $field_path})
        RETURN f.field_path AS field_path,
               f.ontology_governed AS ontology_governed,
               f.ontology_name AS ontology_name
        LIMIT 1
        """

        params = {"field_path": field_path}
        results = await self.neo4j_conn.execute_read(query, params)

        if results:
            return results[0]

        return None

    async def _exact_match(self, field_path: str, value: str) -> dict[str, Any] | None:
        """Stage 1: Exact match on label (case-insensitive).

        Args:
            field_path: NWB field path
            value: Preprocessed value to match

        Returns:
            Matched term dict or None
        """
        query = """
        MATCH (field:SchemaField {field_path: $field_path})
        WHERE field.ontology_governed = true
        MATCH (term:OntologyTerm)
        WHERE term.ontology_name = field.ontology_name
          AND toLower(term.label) = toLower($value)
        RETURN term.term_id AS term_id,
               term.label AS label,
               term.ontology_name AS ontology_name
        LIMIT 1
        """

        params = {"field_path": field_path, "value": value}
        results = await self.neo4j_conn.execute_read(query, params)

        if results:
            logger.info(f"Exact match: {value} -> {results[0]['label']}")
            return results[0]

        return None

    async def _synonym_match(self, field_path: str, value: str) -> dict[str, Any] | None:
        """Stage 2: Synonym match (case-insensitive).

        Args:
            field_path: NWB field path
            value: Preprocessed value to match

        Returns:
            Matched term dict or None
        """
        query = """
        MATCH (field:SchemaField {field_path: $field_path})
        WHERE field.ontology_governed = true
        MATCH (term:OntologyTerm)
        WHERE term.ontology_name = field.ontology_name
          AND any(syn IN term.synonyms WHERE toLower(syn) = toLower($value))
        RETURN term.term_id AS term_id,
               term.label AS label,
               term.ontology_name AS ontology_name
        LIMIT 1
        """

        params = {"field_path": field_path, "value": value}
        results = await self.neo4j_conn.execute_read(query, params)

        if results:
            logger.info(f"Synonym match: {value} -> {results[0]['label']}")
            return results[0]

        return None

    async def normalize_field(
        self, field_path: str, value: Any, context: dict[str, Any] | None = None, use_semantic_reasoning: bool = True
    ) -> dict[str, Any]:
        """Normalize a metadata field value using semantic reasoning (Phase 2).

        Args:
            field_path: NWB field path (e.g., "subject.species")
            value: Raw input value
            context: Optional context (source_file, etc.)
            use_semantic_reasoning: Use 4-stage semantic validation (default: True)
                                   If False, uses legacy 3-stage string matching

        Returns:
            Normalization result with status, confidence, and matched term

        Phase 2 Enhancement:
            When use_semantic_reasoning=True (default), delegates to SemanticReasoner
            which provides 4-stage validation with hierarchy traversal and semantic search.
        """
        if use_semantic_reasoning:
            # Phase 2: Use semantic reasoner with hierarchy support
            logger.info(f"Normalizing {field_path}={value} with semantic reasoning")
            result = await self.semantic_reasoner.validate_with_hierarchy(
                field_path=field_path, value=str(value), required_ancestor=None
            )
            # SemanticReasoner returns a compatible response format
            return result

        # Legacy path: 3-stage string matching (kept for backward compatibility)
        logger.info(f"Normalizing {field_path}={value} with legacy string matching")

        # Check if field is ontology-governed
        schema_field = await self._get_schema_field(field_path)
        if not schema_field or not schema_field.get("ontology_governed"):
            logger.warning(f"Field {field_path} is not ontology-governed")
            return self._build_response(
                field_path=field_path,
                raw_value=value,
                normalized_value=None,
                ontology_term_id=None,
                match_type=None,
                confidence=0.0,
                status="not_applicable",
                action_required=False,
                warnings=[f"Field {field_path} is not ontology-governed"],
            )

        # Preprocess
        preprocessed_value = self._preprocess(str(value))

        # Stage 1: Exact match
        match = await self._exact_match(field_path, preprocessed_value)
        if match:
            return self._build_response(
                field_path=field_path,
                raw_value=value,
                normalized_value=match["label"],
                ontology_term_id=match["term_id"],
                match_type="exact",
                confidence=1.0,
                status="validated",
                action_required=False,
            )

        # Stage 2: Synonym match
        match = await self._synonym_match(field_path, preprocessed_value)
        if match:
            return self._build_response(
                field_path=field_path,
                raw_value=value,
                normalized_value=match["label"],
                ontology_term_id=match["term_id"],
                match_type="synonym",
                confidence=0.95,
                status="validated",
                action_required=False,
            )

        # Stage 3: Needs review
        logger.warning(f"No match found for {field_path}={value}")
        return self._build_response(
            field_path=field_path,
            raw_value=value,
            normalized_value=None,
            ontology_term_id=None,
            match_type=None,
            confidence=0.0,
            status="needs_review",
            action_required=True,
            warnings=[f"No ontology term found for value: {value}"],
        )

    def _build_response(
        self,
        field_path: str,
        raw_value: Any,
        normalized_value: str | None,
        ontology_term_id: str | None,
        match_type: str | None,
        confidence: float,
        status: str,
        action_required: bool,
        warnings: list | None = None,
    ) -> dict[str, Any]:
        """Build normalization response.

        Args:
            field_path: NWB field path
            raw_value: Original input value
            normalized_value: Normalized value
            ontology_term_id: Ontology term ID
            match_type: Type of match (exact/synonym/None)
            confidence: Confidence score (0.0-1.0)
            status: Status (validated/needs_review/not_applicable)
            action_required: Whether user action is needed
            warnings: Warning messages

        Returns:
            Response dictionary
        """
        return {
            "field_path": field_path,
            "raw_value": raw_value,
            "normalized_value": normalized_value,
            "ontology_term_id": ontology_term_id,
            "match_type": match_type,
            "confidence": confidence,
            "status": status,
            "action_required": action_required,
            "warnings": warnings or [],
        }

    async def validate_field(self, field_path: str, value: Any) -> dict[str, Any]:
        """Quick validation without full normalization.

        Args:
            field_path: NWB field path
            value: Value to validate

        Returns:
            Validation result with is_valid boolean
        """
        result = await self.normalize_field(field_path, value)
        return {
            "is_valid": result["status"] == "validated",
            "confidence": result["confidence"],
            "warnings": result["warnings"],
        }


# Global instance
_kg_service: AsyncKGService | None = None


def get_kg_service(neo4j_conn: AsyncNeo4jConnection) -> AsyncKGService:
    """Get global KG service instance.

    Args:
        neo4j_conn: AsyncNeo4jConnection instance

    Returns:
        AsyncKGService singleton instance
    """
    global _kg_service
    if _kg_service is None:
        _kg_service = AsyncKGService(neo4j_conn)
    return _kg_service


def reset_kg_service() -> None:
    """Reset global KG service instance.

    Used for testing to reset the singleton.
    """
    global _kg_service
    _kg_service = None
