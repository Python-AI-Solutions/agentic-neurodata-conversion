"""
Observation Service.

Handles CRUD operations for observations in Neo4j.
"""

import json
import logging

from agentic_neurodata_conversion.kg_service.db.neo4j_connection import AsyncNeo4jConnection
from agentic_neurodata_conversion.kg_service.models.observation import Observation

logger = logging.getLogger(__name__)


class ObservationService:
    """Service for managing observations."""

    def __init__(self, neo4j_conn: AsyncNeo4jConnection):
        self.neo4j_conn = neo4j_conn

    async def store_observation(self, obs: Observation) -> str:
        """
        Store observation in Neo4j.

        Creates Observation node and NORMALIZED_TO relationship.

        Raises:
            ValueError: If ontology_term_id is provided but term doesn't exist in graph.
        """
        # Validate ontology term exists before creating observation
        if obs.ontology_term_id:
            term_check = await self.neo4j_conn.execute_read(
                "MATCH (t:OntologyTerm {term_id: $term_id}) RETURN t.term_id AS term_id",
                {"term_id": obs.ontology_term_id},
            )
            if not term_check:
                raise ValueError(f"Ontology term '{obs.ontology_term_id}' not found in knowledge graph")

        # Handle optional ontology_term_id - only create relationship if term exists
        if obs.ontology_term_id:
            query = """
            CREATE (obs:Observation {
                observation_id: randomUUID(),
                field_path: $field_path,
                raw_value: $raw_value,
                normalized_value: $normalized_value,
                source_type: $source_type,
                source_file: $source_file,
                confidence: $confidence,
                provenance_json: $provenance_json,
                created_at: datetime(),
                is_active: true
            })
            WITH obs
            MATCH (term:OntologyTerm {term_id: $ontology_term_id})
            CREATE (obs)-[:NORMALIZED_TO]->(term)
            RETURN obs.observation_id AS observation_id
            """
        else:
            # No ontology term - just create observation node
            query = """
            CREATE (obs:Observation {
                observation_id: randomUUID(),
                field_path: $field_path,
                raw_value: $raw_value,
                normalized_value: $normalized_value,
                source_type: $source_type,
                source_file: $source_file,
                confidence: $confidence,
                provenance_json: $provenance_json,
                created_at: datetime(),
                is_active: true
            })
            RETURN obs.observation_id AS observation_id
            """

        params = {
            "field_path": obs.field_path,
            "raw_value": obs.raw_value,
            "normalized_value": obs.normalized_value,
            "ontology_term_id": obs.ontology_term_id,
            "source_type": obs.source_type,
            "source_file": obs.source_file,
            "confidence": obs.confidence,
            "provenance_json": json.dumps(obs.provenance_json),
        }

        try:
            results = await self.neo4j_conn.execute_write(query, params)
            observation_id: str = results[0]["observation_id"]
            logger.info(f"Stored observation: {observation_id}")
            return observation_id
        except Exception as e:
            logger.error(f"Failed to store observation: {e}")
            raise

    async def supersede_observations(self, session_id: str, field_path: str) -> int:
        """
        Supersede old observations (set is_active = false).

        Returns count of superseded observations.
        """
        query = """
        MATCH (obs:Observation)
        WHERE obs.field_path = $field_path
          AND obs.is_active = true
          AND obs.provenance_json CONTAINS $session_id
        SET obs.is_active = false
        RETURN count(obs) AS count
        """

        params = {"session_id": session_id, "field_path": field_path}
        results = await self.neo4j_conn.execute_write(query, params)
        count = results[0]["count"] if results else 0
        logger.info(f"Superseded {count} observations")
        return count
