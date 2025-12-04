"""Inference Engine for Knowledge Graph.

Simple inference engine implementing species consistency rule:
- Requires ≥2 evidence observations from same subject
- Requires 100% agreement across all observations
- Returns confidence 0.8 for suggested species
- All suggestions require user confirmation
"""

import logging
from typing import Any

from agentic_neurodata_conversion.kg_service.db.neo4j_connection import AsyncNeo4jConnection

logger = logging.getLogger(__name__)


class InferenceEngine:
    """Simple inference engine for species consistency.

    Implements a single rule: infer species for a subject based on
    their historical observations across multiple files.

    Requirements:
    - Minimum 2 observations required
    - 100% agreement required (no conflicts)
    - Returns confidence 0.8
    - Always requires user confirmation
    """

    def __init__(self, neo4j_conn: AsyncNeo4jConnection):
        """Initialize inference engine.

        Args:
            neo4j_conn: AsyncNeo4jConnection instance for database queries
        """
        self.neo4j_conn = neo4j_conn

    async def infer_species(self, subject_id: str, target_file: str) -> dict[str, Any]:
        """Infer species for subject based on historical observations.

        Analyzes all active observations for the given subject across
        different files (excluding the target file) and suggests a species
        if there is sufficient consistent evidence.

        Args:
            subject_id: Subject identifier (e.g., "subject_001")
            target_file: Current file being processed (excluded from evidence)

        Returns:
            Dict containing:
            - has_suggestion (bool): Whether a suggestion is available
            - suggested_value (str|None): Suggested species label
            - ontology_term_id (str|None): Ontology term ID
            - confidence (float): Confidence score (0.8 if suggestion, 0.0 otherwise)
            - requires_confirmation (bool): Always True for suggestions
            - reasoning (str): Explanation of inference result

        Example:
            >>> engine = InferenceEngine(neo4j_conn)
            >>> result = await engine.infer_species("subject_001", "file_C.nwb")
            >>> print(result)
            {
                "has_suggestion": True,
                "suggested_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "confidence": 0.8,
                "requires_confirmation": True,
                "reasoning": "Based on 2 prior observations with 100% agreement"
            }
        """
        logger.info(f"Inferring species for subject_id={subject_id}, target_file={target_file}")

        # Query to find species with sufficient evidence
        # Requirements:
        # 1. Get all observations for this subject (excluding target file)
        # 2. Group by normalized_value, count occurrences
        # 3. Check if top species has ≥2 observations
        # 4. Verify 100% agreement (only one unique species exists)
        query = """
        MATCH (obs:Observation {field_path: 'subject.species'})
        WHERE obs.source_file CONTAINS $subject_id
          AND obs.source_file <> $target_file
          AND obs.is_active = true
        WITH obs.normalized_value AS species, count(*) AS evidence_count
        ORDER BY evidence_count DESC
        LIMIT 1
        WITH species, evidence_count
        WHERE evidence_count >= 2
        MATCH (obs2:Observation {field_path: 'subject.species'})
        WHERE obs2.source_file CONTAINS $subject_id
          AND obs2.source_file <> $target_file
          AND obs2.is_active = true
        WITH species, evidence_count, collect(DISTINCT obs2.normalized_value) AS all_species
        WHERE size(all_species) = 1
        MATCH (term:OntologyTerm)
        WHERE term.label = species
        RETURN species AS suggested_value,
               term.term_id AS ontology_term_id,
               evidence_count
        """

        params = {"subject_id": subject_id, "target_file": target_file}

        try:
            results = await self.neo4j_conn.execute_read(query, params)

            if results and len(results) > 0:
                result = results[0]
                evidence_count = result["evidence_count"]

                logger.info(
                    f"Inference successful: {result['suggested_value']} "
                    f"(evidence_count={evidence_count}, confidence=0.8)"
                )

                return {
                    "has_suggestion": True,
                    "suggested_value": result["suggested_value"],
                    "ontology_term_id": result["ontology_term_id"],
                    "confidence": 0.8,
                    "requires_confirmation": True,
                    "reasoning": f"Based on {evidence_count} prior observations with 100% agreement",
                }

            logger.info("Inference failed: insufficient evidence or conflicting observations")

            return {
                "has_suggestion": False,
                "suggested_value": None,
                "ontology_term_id": None,
                "confidence": 0.0,
                "requires_confirmation": False,
                "reasoning": "Insufficient evidence (need ≥2 observations with 100% agreement)",
            }

        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise

    async def infer_field(self, field_path: str, subject_id: str, target_file: str) -> dict[str, Any]:
        """Infer value for any field (routing method).

        Currently only supports subject.species. Can be extended
        for other fields in the future.

        Args:
            field_path: Field to infer (e.g., "subject.species")
            subject_id: Subject identifier
            target_file: Current file being processed

        Returns:
            Dict with inference result or unsupported field message

        Example:
            >>> result = await engine.infer_field("subject.species", "subject_001", "file.nwb")
        """
        if field_path == "subject.species":
            return await self.infer_species(subject_id=subject_id, target_file=target_file)
        else:
            logger.warning(f"Inference not supported for field_path={field_path}")
            return {
                "has_suggestion": False,
                "suggested_value": None,
                "ontology_term_id": None,
                "confidence": 0.0,
                "requires_confirmation": False,
                "reasoning": f"Inference not supported for {field_path}",
            }
