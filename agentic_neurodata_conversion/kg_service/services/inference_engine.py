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
        # Uses separate subject_id property for efficient querying
        query = """
        MATCH (obs:Observation {field_path: 'subject.species'})
        WHERE obs.subject_id = $subject_id
          AND obs.source_file <> $target_file
          AND obs.is_active = true
        WITH obs.normalized_value AS species, count(*) AS evidence_count
        ORDER BY evidence_count DESC
        LIMIT 1
        WITH species, evidence_count
        WHERE evidence_count >= 2
        MATCH (obs2:Observation {field_path: 'subject.species'})
        WHERE obs2.subject_id = $subject_id
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
        """Infer value for ANY field from historical observations.

        Works for all stable fields: species, sex, strain, genotype,
        date_of_birth, experimenter, institution, lab, etc.

        Requirements:
        - ≥2 observations with same normalized_value
        - 100% agreement (no conflicts)
        - Excludes target_file
        - Only active observations

        Args:
            field_path: Field to infer (e.g., "subject.species", "subject.strain", "experimenter")
            subject_id: Subject identifier
            target_file: Current file being processed

        Returns:
            Dict containing:
            - has_suggestion (bool): Whether a suggestion is available
            - suggested_value (str|None): Suggested value
            - ontology_term_id (str|None): Ontology term ID (if field is ontology-governed)
            - confidence (float): Confidence score (0.8 if suggestion, 0.0 otherwise)
            - requires_confirmation (bool): Always True for suggestions
            - reasoning (str): Explanation of inference result
            - contributing_sessions (list[dict]|None): List of sessions that contributed evidence,
                each containing 'source_file' and 'created_at' (only present if has_suggestion=True)
            - evidence_count (int|None): Number of supporting observations (only if has_suggestion=True)

        Example:
            >>> result = await engine.infer_field("subject.species", "subject_001", "file.nwb")
            >>> result = await engine.infer_field("experimenter", "subject_001", "file.nwb")
            >>> # Example result with contributing_sessions:
            >>> # {
            >>> #     "has_suggestion": True,
            >>> #     "suggested_value": "Mus musculus",
            >>> #     "contributing_sessions": [
            >>> #         {"source_file": "session_A.nwb", "created_at": "2024-08-15T10:30:00"},
            >>> #         {"source_file": "session_B.nwb", "created_at": "2024-08-20T14:22:00"}
            >>> #     ],
            >>> #     "evidence_count": 2
            >>> # }
        """
        logger.info(f"Inferring {field_path} for subject_id={subject_id}, target_file={target_file}")

        # Query to find field value with sufficient evidence
        # Requirements:
        # 1. Get all observations for this subject and field (excluding target file)
        # 2. Group by normalized_value, count occurrences
        # 3. Check if top value has ≥2 observations
        # 4. Verify 100% agreement (only one unique value exists)
        # 5. Optionally link to ontology term (not all fields have ontology terms)
        query = """
        MATCH (obs:Observation {field_path: $field_path})
        WHERE obs.subject_id = $subject_id
          AND obs.source_file <> $target_file
          AND obs.is_active = true
        WITH obs.normalized_value AS value, count(*) AS evidence_count
        ORDER BY evidence_count DESC
        LIMIT 1
        WITH value, evidence_count
        WHERE evidence_count >= 2
        MATCH (obs2:Observation {field_path: $field_path})
        WHERE obs2.subject_id = $subject_id
          AND obs2.source_file <> $target_file
          AND obs2.is_active = true
        WITH value, evidence_count, collect(DISTINCT obs2.normalized_value) AS all_values
        WHERE size(all_values) = 1
        OPTIONAL MATCH (obs3:Observation {field_path: $field_path, normalized_value: value})
                       -[:NORMALIZED_TO]->(term:OntologyTerm)
        WHERE obs3.subject_id = $subject_id
        MATCH (contributing_obs:Observation {field_path: $field_path, normalized_value: value})
        WHERE contributing_obs.subject_id = $subject_id
          AND contributing_obs.source_file <> $target_file
          AND contributing_obs.is_active = true
        WITH value, evidence_count, term.term_id AS ontology_term_id,
             collect(DISTINCT {
                 source_file: contributing_obs.source_file,
                 created_at: toString(contributing_obs.created_at)
             }) AS contributing_sessions
        RETURN value AS suggested_value,
               ontology_term_id,
               evidence_count,
               contributing_sessions
        """

        params = {"field_path": field_path, "subject_id": subject_id, "target_file": target_file}

        try:
            results = await self.neo4j_conn.execute_read(query, params)

            if results and len(results) > 0:
                result = results[0]
                evidence_count = result["evidence_count"]
                ontology_term_id = result.get("ontology_term_id")  # May be None for non-ontology fields
                contributing_sessions = result.get("contributing_sessions", [])

                logger.info(
                    f"Inference successful for {field_path}: {result['suggested_value']} "
                    f"(evidence_count={evidence_count}, confidence=0.8)"
                )

                return {
                    "has_suggestion": True,
                    "suggested_value": result["suggested_value"],
                    "ontology_term_id": ontology_term_id,
                    "confidence": 0.8,
                    "requires_confirmation": True,
                    "reasoning": f"Based on {evidence_count} prior observations with 100% agreement",
                    "contributing_sessions": contributing_sessions,
                    "evidence_count": evidence_count,
                    "subject_id": subject_id,
                }

            logger.info(f"Inference failed for {field_path}: insufficient evidence or conflicting observations")

            return {
                "has_suggestion": False,
                "suggested_value": None,
                "ontology_term_id": None,
                "confidence": 0.0,
                "requires_confirmation": False,
                "reasoning": "Insufficient evidence (need ≥2 observations with 100% agreement)",
            }

        except Exception as e:
            logger.error(f"Inference error for {field_path}: {e}")
            raise
