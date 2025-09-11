"""Metadata enrichment and confidence scoring for knowledge graph."""

from dataclasses import dataclass
import logging
from typing import Any, Optional

from .rdf_store import RDFStoreManager


@dataclass
class EnrichmentResult:
    """Result of metadata enrichment."""

    field: str
    original_value: Any
    enriched_value: Any
    confidence: float
    source: str
    reasoning: str


class MetadataEnricher:
    """Enriches metadata using knowledge graph and external sources."""

    def __init__(self, rdf_store: RDFStoreManager):
        """
        Initialize metadata enricher.

        Args:
            rdf_store: RDF store manager instance
        """
        self.store = rdf_store
        self.logger = logging.getLogger(__name__)
        self.domain_knowledge = self._load_domain_knowledge()

    def enrich_metadata(self, metadata: dict[str, Any]) -> list[EnrichmentResult]:
        """
        Enrich metadata with knowledge graph information.

        Args:
            metadata: Original metadata dictionary

        Returns:
            List of enrichment results
        """
        enrichments = []

        # Species-strain consistency enrichment
        if "strain" in metadata and "species" not in metadata:
            species_enrichment = self._infer_species_from_strain(metadata["strain"])
            if species_enrichment:
                enrichments.append(species_enrichment)

        # Device capabilities enrichment
        if "device" in metadata:
            device_enrichments = self._enrich_device_information(metadata["device"])
            enrichments.extend(device_enrichments)

        # Protocol inference from experimental setup
        if "experimental_setup" in metadata:
            protocol_enrichments = self._infer_protocol(metadata["experimental_setup"])
            enrichments.extend(protocol_enrichments)

        # Lab information inference
        if "experimenter" in metadata and "lab" not in metadata:
            lab_enrichment = self._infer_lab_from_experimenter(metadata["experimenter"])
            if lab_enrichment:
                enrichments.append(lab_enrichment)

        # Age format standardization
        if "age" in metadata:
            age_enrichment = self._standardize_age_format(metadata["age"])
            if age_enrichment:
                enrichments.append(age_enrichment)

        # Sex standardization
        if "sex" in metadata:
            sex_enrichment = self._standardize_sex(metadata["sex"])
            if sex_enrichment:
                enrichments.append(sex_enrichment)

        self.logger.info(f"Generated {len(enrichments)} enrichment suggestions")
        return enrichments

    def _infer_species_from_strain(self, strain: str) -> Optional[EnrichmentResult]:
        """
        Infer species from strain information.

        Args:
            strain: Strain name

        Returns:
            Enrichment result or None
        """
        strain_species_mapping = self.domain_knowledge["strain_species"]
        species = strain_species_mapping.get(strain)

        if species:
            return EnrichmentResult(
                field="species",
                original_value=None,
                enriched_value=species,
                confidence=0.95,
                source="strain_species_mapping",
                reasoning=f"Species '{species}' inferred from strain '{strain}' using established strain-species mappings",
            )

        # Try partial matching for common strain patterns
        for known_strain, known_species in strain_species_mapping.items():
            if (
                known_strain.lower() in strain.lower()
                or strain.lower() in known_strain.lower()
            ):
                return EnrichmentResult(
                    field="species",
                    original_value=None,
                    enriched_value=known_species,
                    confidence=0.75,
                    source="strain_species_partial_match",
                    reasoning=f"Species '{known_species}' inferred from partial strain match between '{strain}' and '{known_strain}'",
                )

        return None

    def _enrich_device_information(self, device_name: str) -> list[EnrichmentResult]:
        """
        Enrich device information with capabilities and specifications.

        Args:
            device_name: Device name

        Returns:
            List of device enrichments
        """
        enrichments = []

        # Query knowledge graph for existing device information
        query = f"""
        PREFIX neuro: <http://neuroscience.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?property ?value WHERE {{
            ?device rdfs:label "{device_name}" .
            ?device ?property ?value .
        }}
        """

        results = self.store.query(query)

        for result in results:
            property_name = str(result["property"]).split("/")[-1]
            if property_name not in ["type", "label"]:
                enrichments.append(
                    EnrichmentResult(
                        field=f"device_{property_name}",
                        original_value=None,
                        enriched_value=str(result["value"]),
                        confidence=0.8,
                        source="knowledge_graph",
                        reasoning=f"Device property '{property_name}' retrieved from knowledge graph",
                    )
                )

        # Use domain knowledge for device capabilities
        device_capabilities = self.domain_knowledge["device_capabilities"]
        for known_device, capabilities in device_capabilities.items():
            if known_device.lower() in device_name.lower():
                for capability in capabilities:
                    enrichments.append(
                        EnrichmentResult(
                            field="device_capability",
                            original_value=None,
                            enriched_value=capability,
                            confidence=0.85,
                            source="device_capability_mapping",
                            reasoning=f"Capability '{capability}' inferred from device name '{device_name}' matching '{known_device}'",
                        )
                    )

        return enrichments

    def _infer_protocol(
        self, experimental_setup: dict[str, Any]
    ) -> list[EnrichmentResult]:
        """
        Infer experimental protocol from setup information.

        Args:
            experimental_setup: Experimental setup dictionary

        Returns:
            List of protocol enrichments
        """
        enrichments = []

        # Protocol inference based on recording type
        if "recording_type" in experimental_setup:
            recording_type = experimental_setup["recording_type"].lower()

            if "extracellular" in recording_type:
                enrichments.append(
                    EnrichmentResult(
                        field="protocol_type",
                        original_value=None,
                        enriched_value="extracellular_recording",
                        confidence=0.9,
                        source="protocol_inference",
                        reasoning="Extracellular recording protocol inferred from recording type",
                    )
                )

            elif "intracellular" in recording_type:
                enrichments.append(
                    EnrichmentResult(
                        field="protocol_type",
                        original_value=None,
                        enriched_value="intracellular_recording",
                        confidence=0.9,
                        source="protocol_inference",
                        reasoning="Intracellular recording protocol inferred from recording type",
                    )
                )

            elif "patch" in recording_type:
                enrichments.append(
                    EnrichmentResult(
                        field="protocol_type",
                        original_value=None,
                        enriched_value="patch_clamp",
                        confidence=0.95,
                        source="protocol_inference",
                        reasoning="Patch clamp protocol inferred from recording type",
                    )
                )

        # Stimulation protocol inference
        if "stimulation" in experimental_setup:
            stimulation_info = experimental_setup["stimulation"]
            if (
                isinstance(stimulation_info, dict)
                and "optogenetic" in str(stimulation_info).lower()
            ):
                enrichments.append(
                    EnrichmentResult(
                        field="stimulation_type",
                        original_value=None,
                        enriched_value="optogenetic_stimulation",
                        confidence=0.9,
                        source="protocol_inference",
                        reasoning="Optogenetic stimulation inferred from experimental setup",
                    )
                )

        return enrichments

    def _infer_lab_from_experimenter(
        self, experimenter: str
    ) -> Optional[EnrichmentResult]:
        """
        Infer lab from experimenter information.

        Args:
            experimenter: Experimenter name

        Returns:
            Lab enrichment result or None
        """
        # This would query external databases or internal mappings
        # For now, we don't have this data, so return None
        # In a real implementation, this would connect to institutional databases
        return None

    def _standardize_age_format(self, age: str) -> Optional[EnrichmentResult]:
        """
        Standardize age format to ISO 8601 duration format.

        Args:
            age: Age string in various formats

        Returns:
            Age standardization enrichment or None
        """
        import re

        # Common age patterns
        patterns = {
            r"(\d+)\s*days?": lambda m: f"P{m.group(1)}D",
            r"(\d+)\s*weeks?": lambda m: f"P{int(m.group(1)) * 7}D",
            r"(\d+)\s*months?": lambda m: f"P{m.group(1)}M",
            r"(\d+)\s*years?": lambda m: f"P{m.group(1)}Y",
            r"P(\d+)D": lambda _m: age,  # Already in ISO format
            r"P(\d+)M": lambda _m: age,  # Already in ISO format
            r"P(\d+)Y": lambda _m: age,  # Already in ISO format
        }

        age_lower = age.lower().strip()

        for pattern, converter in patterns.items():
            match = re.match(pattern, age_lower)
            if match:
                standardized_age = converter(match)
                if standardized_age != age:
                    return EnrichmentResult(
                        field="age_standardized",
                        original_value=age,
                        enriched_value=standardized_age,
                        confidence=0.95,
                        source="age_standardization",
                        reasoning=f"Standardized age format from '{age}' to ISO 8601 duration '{standardized_age}'",
                    )
                break

        return None

    def _standardize_sex(self, sex: str) -> Optional[EnrichmentResult]:
        """
        Standardize sex values to controlled vocabulary.

        Args:
            sex: Sex value in various formats

        Returns:
            Sex standardization enrichment or None
        """
        sex_mapping = {
            "m": "male",
            "f": "female",
            "male": "male",
            "female": "female",
            "unknown": "unknown",
            "u": "unknown",
            "?": "unknown",
        }

        sex_lower = sex.lower().strip()
        standardized_sex = sex_mapping.get(sex_lower)

        if standardized_sex and standardized_sex != sex:
            return EnrichmentResult(
                field="sex_standardized",
                original_value=sex,
                enriched_value=standardized_sex,
                confidence=0.98,
                source="sex_standardization",
                reasoning=f"Standardized sex value from '{sex}' to controlled vocabulary '{standardized_sex}'",
            )

        return None

    def _load_domain_knowledge(self) -> dict[str, Any]:
        """
        Load domain-specific knowledge for enrichment.

        Returns:
            Domain knowledge dictionary
        """
        return {
            "strain_species": {
                # Mouse strains
                "C57BL/6J": "Mus musculus",
                "C57BL/6": "Mus musculus",
                "BALB/c": "Mus musculus",
                "DBA/2J": "Mus musculus",
                "129S1/SvImJ": "Mus musculus",
                "FVB/NJ": "Mus musculus",
                "NOD/ShiLtJ": "Mus musculus",
                # Rat strains
                "Wistar": "Rattus norvegicus",
                "Sprague-Dawley": "Rattus norvegicus",
                "Long-Evans": "Rattus norvegicus",
                "Fischer 344": "Rattus norvegicus",
                "Brown Norway": "Rattus norvegicus",
                # Primate strains/species
                "Rhesus": "Macaca mulatta",
                "Macaque": "Macaca mulatta",
                # Other model organisms
                "Zebrafish": "Danio rerio",
                "Wildtype": "Unknown",  # Needs context
            },
            "device_capabilities": {
                "Neuropixels": [
                    "high_density_recording",
                    "silicon_probe",
                    "extracellular_recording",
                    "multi_channel_recording",
                ],
                "Open Ephys": [
                    "multichannel_recording",
                    "real_time_processing",
                    "extracellular_recording",
                ],
                "Intan": [
                    "multichannel_recording",
                    "extracellular_recording",
                    "low_noise_amplification",
                ],
                "Patch clamp": [
                    "intracellular_recording",
                    "single_cell_recording",
                    "voltage_clamp",
                    "current_clamp",
                ],
                "Multi Clamp": [
                    "patch_clamp",
                    "intracellular_recording",
                    "amplification",
                ],
                "Optogenetics": [
                    "optical_stimulation",
                    "light_delivery",
                    "temporal_control",
                ],
            },
        }


class ConfidenceScorer:
    """Assigns confidence scores to enrichments and inferences."""

    def __init__(self):
        """Initialize confidence scorer."""
        self.scoring_rules = self._initialize_scoring_rules()

    def score_enrichment(self, enrichment: EnrichmentResult) -> float:
        """
        Score the confidence of an enrichment.

        Args:
            enrichment: Enrichment result to score

        Returns:
            Adjusted confidence score (0.0 to 1.0)
        """
        base_confidence = enrichment.confidence

        # Adjust based on source reliability
        source_multipliers = {
            "strain_species_mapping": 1.0,
            "strain_species_partial_match": 0.85,
            "knowledge_graph": 0.9,
            "device_capability_mapping": 0.9,
            "protocol_inference": 0.85,
            "age_standardization": 0.98,
            "sex_standardization": 0.98,
            "external_database": 0.85,
            "inference": 0.7,
            "ai_suggestion": 0.6,
        }

        multiplier = source_multipliers.get(enrichment.source, 0.5)
        adjusted_confidence = base_confidence * multiplier

        return min(1.0, adjusted_confidence)

    def _initialize_scoring_rules(self) -> dict[str, float]:
        """
        Initialize confidence scoring rules.

        Returns:
            Dictionary of scoring rules
        """
        return {
            "exact_match": 1.0,
            "fuzzy_match": 0.8,
            "inference": 0.7,
            "ai_suggestion": 0.6,
            "partial_match": 0.75,
            "standardization": 0.95,
            "default": 0.5,
        }
