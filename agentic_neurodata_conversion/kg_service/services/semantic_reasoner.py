"""Semantic Reasoner for Knowledge Graph.

Provides semantic reasoning capabilities using ontology hierarchies (IS_A, PART_OF relationships).
This service enables true semantic validation beyond string matching.

Features:
- Hierarchy traversal (find ancestors via IS_A relationships)
- Semantic validation (matches input against hierarchy)
- Cross-field compatibility checks (e.g., species ↔ anatomy validation)

Phase 1 Implementation (v1.0):
- Leverages existing IS_A relationships in Neo4j (currently 16 UBERON relationships)
- Works perfectly for UBERON anatomy terms (brain structures)
- Gracefully handles NCBITaxonomy (no hierarchies yet - returns empty ancestors)

Example:
    >>> reasoner = SemanticReasoner(neo4j_conn)
    >>> # Find ancestors of hippocampus
    >>> ancestors = await reasoner.find_ancestors("UBERON:0001954")
    >>> # Returns: [hippocampal formation, cerebral cortex, brain, CNS]
    >>>
    >>> # Validate with hierarchy support
    >>> result = await reasoner.validate_with_hierarchy(
    ...     field_path="ecephys.ElectrodeGroup.location",
    ...     value="Ammon's horn",
    ...     required_ancestor="brain"
    ... )
    >>> # Matches "Ammon's horn" and verifies it's part of "brain" hierarchy
"""

import logging
from typing import Any

from agentic_neurodata_conversion.kg_service.db.neo4j_connection import AsyncNeo4jConnection

logger = logging.getLogger(__name__)


class SemanticReasoner:
    """Semantic reasoning service using ontology hierarchies.

    Provides advanced validation capabilities by traversing IS_A and PART_OF
    relationships in the knowledge graph. Enables semantic matching beyond
    exact string and synonym matching.

    Current State (Phase 1):
    - ✅ UBERON hierarchy traversal (16 IS_A relationships for brain anatomy)
    - ⏳ NCBITaxonomy hierarchy (no parent terms in database yet)

    Future Enhancements (Phase 2):
    - PART_OF relationships for anatomical structures
    - Species-specific anatomy validation
    - Semantic distance scoring

    Attributes:
        neo4j_conn: AsyncNeo4jConnection instance for database queries
    """

    def __init__(self, neo4j_conn: AsyncNeo4jConnection):
        """Initialize semantic reasoner.

        Args:
            neo4j_conn: AsyncNeo4jConnection instance for database access
        """
        self.neo4j_conn = neo4j_conn

    async def find_ancestors(
        self, term_id: str, max_depth: int = 5, relationship_type: str = "IS_A"
    ) -> list[dict[str, Any]]:
        """Find all ancestor terms via hierarchical relationships.

        Traverses IS_A (or other specified) relationships from a starting term
        up to a maximum depth, returning all ancestor terms with their distance.

        This is the foundation for semantic validation - it allows us to answer
        questions like:
        - Is "Ammon's horn" part of "hippocampus"? (Yes - distance 1)
        - Is "Ammon's horn" part of "brain"? (Yes - distance 3)
        - Is "hippocampus" valid for species "mouse"? (Need cross-field check)

        Args:
            term_id: Starting ontology term ID (e.g., "UBERON:0001954")
            max_depth: Maximum traversal depth (default 5, prevents infinite loops)
            relationship_type: Relationship to traverse (default "IS_A")

        Returns:
            List of ancestor term dictionaries, each containing:
            - term_id: Ancestor term ID
            - label: Ancestor term label
            - distance: Number of hops from starting term
            Sorted by distance (closest ancestors first)

        Example:
            >>> ancestors = await reasoner.find_ancestors("UBERON:0001954")
            >>> # Returns:
            >>> # [
            >>> #   {"term_id": "UBERON:0002421", "label": "hippocampal formation", "distance": 1},
            >>> #   {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 2},
            >>> #   {"term_id": "UBERON:0000955", "label": "brain", "distance": 3},
            >>> #   {"term_id": "UBERON:0001017", "label": "central nervous system", "distance": 4}
            >>> # ]

        Note:
            - Works perfectly for UBERON terms (brain anatomy)
            - Returns empty list for NCBITaxonomy terms (no hierarchies yet)
            - Empty result doesn't mean error - just no ancestors found
        """
        logger.info(f"Finding ancestors for {term_id} (max_depth={max_depth}, relationship={relationship_type})")

        # Cypher query with variable-length path traversal
        # Pattern: (start)-[:IS_A*1..5]->(ancestor)
        # *1..5 means "1 to 5 hops" - prevents infinite loops
        query = f"""
        MATCH path = (start:OntologyTerm {{term_id: $term_id}})-[:{relationship_type}*1..{max_depth}]->(ancestor)
        RETURN ancestor.term_id AS term_id,
               ancestor.label AS label,
               length(path) AS distance
        ORDER BY distance
        """

        params = {"term_id": term_id}

        try:
            results = await self.neo4j_conn.execute_read(query, params)

            if results:
                logger.info(f"Found {len(results)} ancestors for {term_id}")
            else:
                logger.info(f"No ancestors found for {term_id} (may be root term or no hierarchies loaded)")

            return results

        except Exception as e:
            logger.error(f"Error finding ancestors for {term_id}: {e}")
            raise

    async def validate_with_hierarchy(
        self, field_path: str, value: str, required_ancestor: str | None = None
    ) -> dict[str, Any]:
        """Validate value using hierarchy traversal - 4-stage validation pipeline.

        This is the core semantic validation method that goes beyond string matching.
        It implements a 4-stage pipeline with increasing flexibility:

        Stage 1: Exact match (confidence 1.0)
        Stage 2: Synonym match (confidence 0.95)
        Stage 3: Semantic match via hierarchy (confidence 0.85)
        Stage 4: No match (confidence 0.0)

        Stage 3 is NEW - it can match partial terms and verify hierarchy constraints.

        Args:
            field_path: NWB field path (e.g., "ecephys.ElectrodeGroup.location")
            value: User input value to validate (e.g., "hippocampus", "CA1", "Ammon's horn")
            required_ancestor: Optional constraint - matched term must be descendant of this
                              (e.g., "brain" ensures matched term is a brain structure)

        Returns:
            Validation result dictionary containing:
            - field_path: Input field path
            - raw_value: Original user input
            - normalized_value: Matched ontology term label (or None)
            - ontology_term_id: Matched term ID (or None)
            - match_type: "exact" | "synonym" | "semantic" | None
            - confidence: 1.0 | 0.95 | 0.85 | 0.0
            - status: "validated" | "needs_review"
            - action_required: bool
            - warnings: List of warning messages
            - semantic_info: Optional dict with hierarchy details (if semantic match)

        Example:
            >>> # Stage 1: Exact match
            >>> result = await reasoner.validate_with_hierarchy(
            ...     "ecephys.ElectrodeGroup.location", "hippocampus"
            ... )
            >>> # Returns: match_type="exact", confidence=1.0
            >>>
            >>> # Stage 3: Semantic match with partial input
            >>> result = await reasoner.validate_with_hierarchy(
            ...     "ecephys.ElectrodeGroup.location", "CA1 region"
            ... )
            >>> # Finds "Ammon's horn" (synonym for CA1), confidence=0.85
            >>>
            >>> # With hierarchy constraint
            >>> result = await reasoner.validate_with_hierarchy(
            ...     "ecephys.ElectrodeGroup.location",
            ...     "Ammon's horn",
            ...     required_ancestor="brain"
            ... )
            >>> # Verifies: Ammon's horn → hippocampus → ... → brain ✅

        Note:
            Stage 3 semantic matching works for both UBERON (brain anatomy)
            and NCBITaxonomy (species) via IS_A hierarchies.
        """
        logger.info(f"Validating {field_path}={value} with hierarchy support (required_ancestor={required_ancestor})")

        # Preprocess value (lowercase, strip whitespace)
        preprocessed_value = value.lower().strip()

        # Get schema field info
        schema_field = await self._get_schema_field(field_path)
        if not schema_field or not schema_field.get("ontology_governed"):
            logger.warning(f"Field {field_path} is not ontology-governed")
            return self._build_validation_response(
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

        ontology_name = schema_field["ontology_name"]

        # Stage 1: Exact match
        match = await self._exact_match(field_path, preprocessed_value, ontology_name)
        if match:
            # Verify hierarchy constraint if provided
            if required_ancestor:
                is_valid = await self._verify_hierarchy_constraint(match["term_id"], required_ancestor)
                if not is_valid:
                    logger.warning(
                        f"Exact match failed hierarchy constraint: {match['term_id']} not under {required_ancestor}"
                    )
                    # Continue to next stage instead of rejecting
                else:
                    return self._build_validation_response(
                        field_path=field_path,
                        raw_value=value,
                        normalized_value=match["label"],
                        ontology_term_id=match["term_id"],
                        match_type="exact",
                        confidence=1.0,
                        status="validated",
                        action_required=False,
                    )
            else:
                return self._build_validation_response(
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
        match = await self._synonym_match(field_path, preprocessed_value, ontology_name)
        if match:
            # Verify hierarchy constraint if provided
            if required_ancestor:
                is_valid = await self._verify_hierarchy_constraint(match["term_id"], required_ancestor)
                if not is_valid:
                    logger.warning(
                        f"Synonym match failed hierarchy constraint: {match['term_id']} not under {required_ancestor}"
                    )
                    # Continue to next stage
                else:
                    return self._build_validation_response(
                        field_path=field_path,
                        raw_value=value,
                        normalized_value=match["label"],
                        ontology_term_id=match["term_id"],
                        match_type="synonym",
                        confidence=0.95,
                        status="validated",
                        action_required=False,
                    )
            else:
                return self._build_validation_response(
                    field_path=field_path,
                    raw_value=value,
                    normalized_value=match["label"],
                    ontology_term_id=match["term_id"],
                    match_type="synonym",
                    confidence=0.95,
                    status="validated",
                    action_required=False,
                )

        # Stage 3: Semantic search (partial match + hierarchy validation)
        match = await self._semantic_search(field_path, preprocessed_value, ontology_name, required_ancestor)
        if match:
            return self._build_validation_response(
                field_path=field_path,
                raw_value=value,
                normalized_value=match["label"],
                ontology_term_id=match["term_id"],
                match_type="semantic",
                confidence=0.85,
                status="validated",
                action_required=False,
                semantic_info={
                    "search_type": match.get("search_type", "partial_match"),
                    "ancestors": match.get("ancestors", []),
                },
            )

        # Stage 4: No match
        logger.warning(f"No match found for {field_path}={value}")
        return self._build_validation_response(
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

    async def check_cross_field_compatibility(self, species_term_id: str, anatomy_term_id: str) -> dict[str, Any]:
        """Check if anatomy term is valid for given species.

        Validates cross-field constraints using ontology relationships.
        For example, "mouse hippocampus" is valid, but "mouse human brain" is not.

        This enables intelligent validation across multiple metadata fields,
        catching semantic errors that string matching would miss.

        Phase 1: Basic implementation using explicit constraints
        Phase 2: Learn constraints from historical observations

        Args:
            species_term_id: Species ontology term ID (e.g., "NCBITaxon:10090")
            anatomy_term_id: Anatomy ontology term ID (e.g., "UBERON:0001954")

        Returns:
            Compatibility check result containing:
            - is_compatible: bool - whether combination is valid
            - confidence: float - confidence in compatibility decision
            - reasoning: str - explanation of decision
            - warnings: list[str] - any warnings or caveats

        Example:
            >>> # Valid: Mouse has hippocampus
            >>> result = await reasoner.check_cross_field_compatibility(
            ...     "NCBITaxon:10090",  # Mus musculus
            ...     "UBERON:0001954"     # Ammon's horn
            ... )
            >>> # Returns: is_compatible=True, confidence=0.95
            >>>
            >>> # Invalid: Invertebrate with mammalian brain structure
            >>> result = await reasoner.check_cross_field_compatibility(
            ...     "NCBITaxon:6239",    # C. elegans (worm)
            ...     "UBERON:0002421"     # hippocampal formation
            ... )
            >>> # Returns: is_compatible=False, confidence=0.90

        Note:
            Phase 1.5 uses hierarchy-based taxonomic constraints (vertebrate/invertebrate).
            Phase 2 will learn from historical observations (more accurate).
        """
        logger.info(f"Checking compatibility: species={species_term_id}, anatomy={anatomy_term_id}")

        try:
            # Get species and anatomy terms
            species_query = """
            MATCH (t:OntologyTerm {term_id: $term_id})
            RETURN t.term_id AS term_id, t.label AS label, t.ontology_name AS ontology_name
            """
            anatomy_query = """
            MATCH (t:OntologyTerm {term_id: $term_id})
            RETURN t.term_id AS term_id, t.label AS label, t.ontology_name AS ontology_name
            """

            species_result = await self.neo4j_conn.execute_read(species_query, {"term_id": species_term_id})
            anatomy_result = await self.neo4j_conn.execute_read(anatomy_query, {"term_id": anatomy_term_id})

            if not species_result:
                return {
                    "is_compatible": False,
                    "confidence": 0.0,
                    "reasoning": f"Species term not found: {species_term_id}",
                    "warnings": ["Invalid species term ID"],
                }

            if not anatomy_result:
                return {
                    "is_compatible": False,
                    "confidence": 0.0,
                    "reasoning": f"Anatomy term not found: {anatomy_term_id}",
                    "warnings": ["Invalid anatomy term ID"],
                }

            species = species_result[0]
            anatomy = anatomy_result[0]

            # Verify ontologies match expected types
            if species["ontology_name"] != "NCBITaxonomy":
                return {
                    "is_compatible": False,
                    "confidence": 0.0,
                    "reasoning": f"Expected NCBITaxonomy, got {species['ontology_name']}",
                    "warnings": ["Species term is not from NCBITaxonomy"],
                }

            if anatomy["ontology_name"] != "UBERON":
                return {
                    "is_compatible": False,
                    "confidence": 0.0,
                    "reasoning": f"Expected UBERON, got {anatomy['ontology_name']}",
                    "warnings": ["Anatomy term is not from UBERON"],
                }

            # Phase 1.5: Hierarchy-based vertebrate/invertebrate classification
            # Uses taxonomic hierarchies to automatically detect invertebrates
            # Vertebrates: Have complex CNS (brain, spinal cord)
            # Invertebrates: Have simple nervous systems (ganglia, nerve cords)

            # Get species ancestors to detect vertebrate vs invertebrate
            species_ancestors = await self.find_ancestors(species_term_id, max_depth=10)
            species_ancestor_labels = {a["label"] for a in species_ancestors}

            # Vertebrate markers: Vertebrata, Mammalia, Aves, Amphibia, Teleostei
            vertebrate_markers = {"Vertebrata", "Mammalia", "Aves", "Amphibia", "Teleostei", "Chordata"}
            is_vertebrate = bool(species_ancestor_labels & vertebrate_markers)

            # Invertebrate markers: Protostomia, Arthropoda, Nematoda, Mollusca, Annelida
            invertebrate_markers = {"Protostomia", "Arthropoda", "Nematoda", "Mollusca", "Annelida", "Insecta"}
            is_invertebrate = bool(species_ancestor_labels & invertebrate_markers)

            # Check if anatomy is a vertebrate brain structure (has "brain" as ancestor)
            anatomy_ancestors = await self.find_ancestors(anatomy_term_id, max_depth=10)
            is_vertebrate_brain_structure = any(
                a["label"].lower() in ["brain", "central nervous system", "cerebral cortex"] for a in anatomy_ancestors
            ) or anatomy["label"].lower() in ["brain", "central nervous system", "cerebral cortex"]

            # If anatomy is a vertebrate brain structure and species is invertebrate, incompatible
            if is_vertebrate_brain_structure and is_invertebrate:
                logger.warning(
                    f"Incompatible: {species['label']} (invertebrate) "
                    f"cannot have {anatomy['label']} (vertebrate brain structure)"
                )
                return {
                    "is_compatible": False,
                    "confidence": 0.95,  # Higher confidence now with hierarchy-based detection
                    "reasoning": (
                        f"{species['label']} is an invertebrate (ancestors: {', '.join(sorted(species_ancestor_labels & invertebrate_markers))}) "
                        f"and does not have {anatomy['label']} (vertebrate CNS structure)"
                    ),
                    "warnings": [],
                }

            # If anatomy is vertebrate brain and species is vertebrate, valid!
            if is_vertebrate_brain_structure and is_vertebrate:
                logger.info(f"Compatible: {species['label']} (vertebrate) can have {anatomy['label']}")
                return {
                    "is_compatible": True,
                    "confidence": 0.95,  # High confidence for vertebrate + brain
                    "reasoning": (
                        f"{species['label']} is a vertebrate (ancestors: {', '.join(sorted(species_ancestor_labels & vertebrate_markers))}) "
                        f"and can have {anatomy['label']} (vertebrate CNS structure)"
                    ),
                    "warnings": [],
                }

            # Default: Compatible (permissive for unknown combinations)
            logger.info(f"Compatible (permissive): {species['label']} + {anatomy['label']}")
            return {
                "is_compatible": True,
                "confidence": 0.80,  # Slightly lower confidence for permissive default
                "reasoning": (
                    f"{species['label']} is compatible with {anatomy['label']}. "
                    "Phase 1.5 uses hierarchy-based vertebrate/invertebrate classification."
                ),
                "warnings": ["Permissive validation - combination not explicitly validated"],
            }

        except Exception as e:
            logger.error(f"Error checking compatibility: {e}")
            return {
                "is_compatible": True,  # Permissive default on error
                "confidence": 0.0,
                "reasoning": f"Error during validation: {str(e)}",
                "warnings": ["Validation error - defaulting to permissive"],
            }

    # ========== Helper Methods for validate_with_hierarchy() ==========

    async def _get_schema_field(self, field_path: str) -> dict[str, Any] | None:
        """Get schema field information from Neo4j."""
        query = """
        MATCH (f:SchemaField {field_path: $field_path})
        RETURN f.field_path AS field_path,
               f.ontology_governed AS ontology_governed,
               f.ontology_name AS ontology_name
        LIMIT 1
        """
        params = {"field_path": field_path}
        results = await self.neo4j_conn.execute_read(query, params)
        return results[0] if results else None

    async def _exact_match(self, field_path: str, value: str, ontology_name: str) -> dict[str, Any] | None:
        """Stage 1: Exact match on label (case-insensitive)."""
        query = """
        MATCH (term:OntologyTerm)
        WHERE term.ontology_name = $ontology_name
          AND toLower(term.label) = toLower($value)
        RETURN term.term_id AS term_id,
               term.label AS label,
               term.ontology_name AS ontology_name
        LIMIT 1
        """
        params = {"ontology_name": ontology_name, "value": value}
        results = await self.neo4j_conn.execute_read(query, params)
        if results:
            logger.info(f"Exact match: {value} -> {results[0]['label']}")
        return results[0] if results else None

    async def _synonym_match(self, field_path: str, value: str, ontology_name: str) -> dict[str, Any] | None:
        """Stage 2: Synonym match (case-insensitive)."""
        query = """
        MATCH (term:OntologyTerm)
        WHERE term.ontology_name = $ontology_name
          AND any(syn IN term.synonyms WHERE toLower(syn) = toLower($value))
        RETURN term.term_id AS term_id,
               term.label AS label,
               term.ontology_name AS ontology_name
        LIMIT 1
        """
        params = {"ontology_name": ontology_name, "value": value}
        results = await self.neo4j_conn.execute_read(query, params)
        if results:
            logger.info(f"Synonym match: {value} -> {results[0]['label']}")
        return results[0] if results else None

    async def _semantic_search(
        self, field_path: str, value: str, ontology_name: str, required_ancestor: str | None
    ) -> dict[str, Any] | None:
        """Stage 3: Semantic search using partial match + hierarchy validation."""
        query = """
        MATCH (term:OntologyTerm)
        WHERE term.ontology_name = $ontology_name
          AND (
            toLower(term.label) CONTAINS toLower($value)
            OR any(syn IN term.synonyms WHERE toLower(syn) CONTAINS toLower($value))
          )
        RETURN term.term_id AS term_id,
               term.label AS label,
               term.ontology_name AS ontology_name
        LIMIT 5
        """
        params = {"ontology_name": ontology_name, "value": value}
        results = await self.neo4j_conn.execute_read(query, params)

        if not results:
            return None

        # Filter by hierarchy constraint if provided
        if required_ancestor:
            for match in results:
                is_valid = await self._verify_hierarchy_constraint(match["term_id"], required_ancestor)
                if is_valid:
                    ancestors = await self.find_ancestors(match["term_id"], max_depth=5)
                    logger.info(f"Semantic match: {value} -> {match['label']} (with hierarchy validation)")
                    return {
                        **match,
                        "search_type": "partial_match_with_hierarchy",
                        "ancestors": [f"{a['label']} ({a['distance']} hops)" for a in ancestors[:3]],
                    }
            return None
        else:
            match = results[0]
            logger.info(f"Semantic match: {value} -> {match['label']} (partial match)")
            return {**match, "search_type": "partial_match", "ancestors": []}

    async def _verify_hierarchy_constraint(self, term_id: str, required_ancestor: str) -> bool:
        """Verify that term is a descendant of required ancestor."""
        ancestors = await self.find_ancestors(term_id, max_depth=10)
        for ancestor in ancestors:
            if ancestor["label"].lower() == required_ancestor.lower() or ancestor["term_id"] == required_ancestor:
                return True
        return False

    def _build_validation_response(
        self,
        field_path: str,
        raw_value: str,
        normalized_value: str | None,
        ontology_term_id: str | None,
        match_type: str | None,
        confidence: float,
        status: str,
        action_required: bool,
        warnings: list | None = None,
        semantic_info: dict | None = None,
    ) -> dict[str, Any]:
        """Build validation response dictionary."""
        response = {
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
        if semantic_info:
            response["semantic_info"] = semantic_info
        return response


# Global instance (singleton pattern, consistent with other services)
_semantic_reasoner: SemanticReasoner | None = None


def get_semantic_reasoner(neo4j_conn: AsyncNeo4jConnection) -> SemanticReasoner:
    """Get global SemanticReasoner instance.

    Implements singleton pattern to reuse reasoner across the application.

    Args:
        neo4j_conn: AsyncNeo4jConnection instance

    Returns:
        SemanticReasoner singleton instance

    Example:
        >>> from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection
        >>> from agentic_neurodata_conversion.kg_service.config import get_settings
        >>> settings = get_settings()
        >>> conn = get_neo4j_connection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        >>> await conn.connect()
        >>> reasoner = get_semantic_reasoner(conn)
    """
    global _semantic_reasoner
    if _semantic_reasoner is None:
        _semantic_reasoner = SemanticReasoner(neo4j_conn)
    return _semantic_reasoner


def reset_semantic_reasoner() -> None:
    """Reset global SemanticReasoner instance.

    Primarily used for testing to reset the singleton between test cases.

    Example:
        >>> reset_semantic_reasoner()  # Force new instance on next get
        >>> reasoner = get_semantic_reasoner(conn)
    """
    global _semantic_reasoner
    _semantic_reasoner = None
