"""
Intelligent Metadata Inference from Files.

This module uses file analysis + LLM to automatically infer metadata
from file structure and content, reducing user burden and improving
data quality.

Features:
- Auto-extract metadata from file headers and structure
- Infer likely values using LLM reasoning
- Provide confidence scores for inferences
- Pre-fill metadata forms with intelligent defaults
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from models import GlobalState, LogLevel
from services import LLMService

logger = logging.getLogger(__name__)


class MetadataInferenceEngine:
    """
    Intelligent metadata inference from file analysis.

    Uses a combination of:
    1. Direct file metadata extraction (sampling rate, channels, duration)
    2. LLM-powered inference (recording type, species, brain region)
    3. Heuristic rules (common patterns in neuroscience data)
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the metadata inference engine.

        Args:
            llm_service: Optional LLM service for intelligent inference
        """
        self.llm_service = llm_service

    async def infer_metadata(
        self,
        input_path: str,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Infer metadata from input file using analysis + LLM.

        Args:
            input_path: Path to input data file
            state: Global conversion state

        Returns:
            Dictionary with:
            - inferred_metadata: Inferred field values
            - confidence_scores: Confidence for each inference (0-100)
            - reasoning: Explanation of how inference was made
            - suggestions: Suggestions for user to review
        """
        try:
            # Step 1: Extract technical file metadata
            file_meta = self._extract_file_metadata(input_path, state)

            # Step 2: Apply heuristic rules
            heuristic_inferences = self._apply_heuristic_rules(file_meta, state)

            # Step 3: Use LLM for intelligent inference (if available)
            if self.llm_service:
                llm_inferences = await self._llm_powered_inference(
                    file_meta,
                    heuristic_inferences,
                    state
                )
            else:
                llm_inferences = {
                    "inferred_metadata": {},
                    "confidence_scores": {},
                    "reasoning": {},
                }

            # Step 4: Combine results with confidence scoring
            combined_result = self._combine_inferences(
                file_meta,
                heuristic_inferences,
                llm_inferences,
            )

            state.add_log(
                LogLevel.INFO,
                "Metadata inference completed",
                {
                    "inferred_fields": list(combined_result["inferred_metadata"].keys()),
                    "avg_confidence": sum(combined_result["confidence_scores"].values()) / max(len(combined_result["confidence_scores"]), 1),
                }
            )

            return combined_result

        except Exception as e:
            logger.error(f"Metadata inference failed: {e}")
            state.add_log(
                LogLevel.WARNING,
                f"Metadata inference failed: {e}",
            )
            # Return empty result on failure
            return {
                "inferred_metadata": {},
                "confidence_scores": {},
                "reasoning": {},
                "suggestions": ["Unable to automatically infer metadata. Manual input recommended."],
            }

    def _extract_file_metadata(
        self,
        input_path: str,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Extract technical metadata directly from file.

        Args:
            input_path: Path to input file
            state: Global conversion state

        Returns:
            Dictionary with file metadata (format, size, structure, etc.)
        """
        file_path = Path(input_path)

        metadata = {
            "file_name": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2) if file_path.exists() else 0,
            "format": state.metadata.get("format", "unknown"),
        }

        # Extract format-specific metadata
        format_type = state.metadata.get("format", "").lower()

        if "spikeglx" in format_type:
            metadata.update(self._extract_spikeglx_metadata(input_path))
        elif "openephys" in format_type:
            metadata.update(self._extract_openephys_metadata(input_path))
        elif "intan" in format_type:
            metadata.update(self._extract_intan_metadata(input_path))

        return metadata

    def _extract_spikeglx_metadata(self, input_path: str) -> Dict[str, Any]:
        """Extract metadata from SpikeGLX files."""
        meta = {"recording_type": "electrophysiology", "system": "SpikeGLX"}

        # Parse filename for common patterns
        file_path = Path(input_path)
        filename = file_path.stem.lower()

        # Common SpikeGLX patterns: Noise4Sam_g0_t0.imec0.ap.bin
        if "imec" in filename:
            meta["probe_type"] = "Neuropixels"
            if "imec0" in filename:
                meta["probe_id"] = "0"

        if ".ap." in filename:
            meta["data_stream"] = "action potentials (AP)"
        elif ".lf." in filename:
            meta["data_stream"] = "local field potentials (LF)"

        # Try to read .meta file if it exists
        meta_file = file_path.with_suffix(".meta")
        if meta_file.exists():
            try:
                with open(meta_file, 'r') as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            if key == "imSampRate":
                                meta["sampling_rate_hz"] = float(value)
                            elif key == "nSavedChans":
                                meta["channel_count"] = int(value)
                            elif key == "fileTimeSecs":
                                meta["duration_seconds"] = float(value)
            except Exception:
                pass

        return meta

    def _extract_openephys_metadata(self, input_path: str) -> Dict[str, Any]:
        """Extract metadata from OpenEphys files."""
        return {
            "recording_type": "electrophysiology",
            "system": "Open Ephys",
        }

    def _extract_intan_metadata(self, input_path: str) -> Dict[str, Any]:
        """Extract metadata from Intan files."""
        return {
            "recording_type": "electrophysiology",
            "system": "Intan",
        }

    def _apply_heuristic_rules(
        self,
        file_meta: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Apply heuristic rules to infer metadata.

        Args:
            file_meta: Extracted file metadata
            state: Global conversion state

        Returns:
            Dictionary with heuristic inferences
        """
        inferences = {}

        # Rule 1: Recording type from format
        if file_meta.get("recording_type"):
            inferences["recording_modality"] = file_meta["recording_type"]

        # Rule 2: Device from system
        if file_meta.get("system"):
            inferences["device_name"] = file_meta["system"]

        # Rule 3: Species inference from filename patterns
        filename = file_meta.get("file_name", "").lower()
        if any(pattern in filename for pattern in ["mouse", "mus", "m0"]):
            inferences["species"] = "Mus musculus"
            inferences["species_common_name"] = "house mouse"
        elif any(pattern in filename for pattern in ["rat", "rattus"]):
            inferences["species"] = "Rattus norvegicus"
            inferences["species_common_name"] = "Norway rat"

        # Rule 4: Brain region inference from filename
        if "v1" in filename:
            inferences["brain_region"] = "V1"
            inferences["brain_region_full"] = "primary visual cortex"
        elif "hpc" in filename or "hippocampus" in filename:
            inferences["brain_region"] = "HPC"
            inferences["brain_region_full"] = "hippocampus"
        elif "pfc" in filename:
            inferences["brain_region"] = "PFC"
            inferences["brain_region_full"] = "prefrontal cortex"

        # Rule 5: Keywords from detected properties
        keywords = []
        if inferences.get("recording_modality"):
            keywords.append(inferences["recording_modality"])
        if inferences.get("species_common_name"):
            keywords.append(inferences["species_common_name"])
        if inferences.get("brain_region"):
            keywords.append(inferences["brain_region"])
        if file_meta.get("probe_type"):
            keywords.append(file_meta["probe_type"])

        if keywords:
            inferences["keywords"] = keywords

        return inferences

    async def _llm_powered_inference(
        self,
        file_meta: Dict[str, Any],
        heuristic_inferences: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to infer additional metadata with reasoning.

        Args:
            file_meta: Extracted file metadata
            heuristic_inferences: Heuristic rule inferences
            state: Global conversion state

        Returns:
            Dictionary with LLM inferences including confidence and reasoning
        """
        system_prompt = """You are an expert neuroscience data curator specializing in NWB metadata.

Your job is to analyze file metadata and make intelligent inferences about:
1. Recording type and modality (electrophysiology, calcium imaging, behavior, etc.)
2. Likely experimental subject (species, age range, etc.)
3. Likely brain regions recorded from
4. Suggested keywords for searchability
5. Experiment type and purpose

Provide confident inferences with reasoning, and indicate confidence level (0-100)."""

        user_prompt = f"""Analyze this neuroscience data file and infer NWB metadata:

**File Metadata:**
{json.dumps(file_meta, indent=2)}

**Heuristic Inferences (from rules):**
{json.dumps(heuristic_inferences, indent=2)}

**Task:**
Based on the file properties, infer:
1. What type of neuroscience recording is this? (electrophysiology, imaging, behavior, etc.)
2. What species is likely being recorded? (if not already inferred)
3. What brain region(s)? (expand abbreviations, e.g., "V1" → "primary visual cortex")
4. What experiment type? (acute recording, chronic recording, etc.)
5. Suggested keywords for data discovery
6. What should the experiment_description say?

For each inference:
- Provide the inferred value
- Explain your reasoning (why you think this)
- Give confidence score 0-100

Return JSON format."""

        output_schema = {
            "type": "object",
            "properties": {
                "inferred_metadata": {
                    "type": "object",
                    "properties": {
                        "recording_modality": {"type": "string"},
                        "species": {"type": "string"},
                        "brain_region": {"type": "string"},
                        "brain_region_full": {"type": "string"},
                        "experiment_type": {"type": "string"},
                        "experiment_description": {"type": "string"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "confidence_scores": {
                    "type": "object",
                    "description": "Confidence 0-100 for each inferred field",
                },
                "reasoning": {
                    "type": "object",
                    "description": "Explanation of how each inference was made",
                },
            },
            "required": ["inferred_metadata", "confidence_scores", "reasoning"],
        }

        try:
            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "LLM metadata inference completed",
                {
                    "inferred_fields": list(response.get("inferred_metadata", {}).keys()),
                }
            )

            return response

        except Exception as e:
            logger.error(f"LLM inference failed: {e}")
            state.add_log(
                LogLevel.WARNING,
                f"LLM-powered inference failed: {e}",
            )
            return {
                "inferred_metadata": {},
                "confidence_scores": {},
                "reasoning": {},
            }

    def _combine_inferences(
        self,
        file_meta: Dict[str, Any],
        heuristic_inferences: Dict[str, Any],
        llm_inferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Combine all inference sources with priority: LLM > Heuristic > File metadata.

        Args:
            file_meta: Direct file metadata
            heuristic_inferences: Rule-based inferences
            llm_inferences: LLM-powered inferences

        Returns:
            Combined inference result with confidence scores
        """
        combined_metadata = {}
        combined_confidence = {}
        combined_reasoning = {}
        suggestions = []

        # Priority 1: LLM inferences (most intelligent)
        llm_meta = llm_inferences.get("inferred_metadata", {})
        llm_confidence = llm_inferences.get("confidence_scores", {})
        llm_reasoning = llm_inferences.get("reasoning", {})

        for key, value in llm_meta.items():
            if value:  # Only include non-empty values
                combined_metadata[key] = value
                combined_confidence[key] = llm_confidence.get(key, 70)
                combined_reasoning[key] = llm_reasoning.get(key, "Inferred by LLM analysis")

        # Priority 2: Heuristic inferences (rule-based, reliable for specific patterns)
        for key, value in heuristic_inferences.items():
            if key not in combined_metadata and value:
                combined_metadata[key] = value
                combined_confidence[key] = 85  # Heuristics are pretty reliable
                combined_reasoning[key] = "Inferred from filename/format patterns"

        # Priority 3: Direct file metadata (highest confidence but limited scope)
        direct_fields = ["sampling_rate_hz", "channel_count", "duration_seconds", "probe_type"]
        for key in direct_fields:
            if key in file_meta and file_meta[key]:
                combined_metadata[key] = file_meta[key]
                combined_confidence[key] = 95  # Direct extraction is very reliable
                combined_reasoning[key] = "Extracted directly from file"

        # Generate suggestions for user
        suggestions.append("✅ Automatically inferred metadata from file analysis")

        low_confidence_fields = [
            key for key, conf in combined_confidence.items() if conf < 70
        ]
        if low_confidence_fields:
            suggestions.append(
                f"⚠️ Low confidence fields: {', '.join(low_confidence_fields)}. Please review."
            )

        if combined_metadata.get("species"):
            suggestions.append(
                f"🔍 Detected species: {combined_metadata['species']}. Verify if correct."
            )

        if combined_metadata.get("brain_region"):
            suggestions.append(
                f"🧠 Detected brain region: {combined_metadata['brain_region']}. Verify if correct."
            )

        return {
            "inferred_metadata": combined_metadata,
            "confidence_scores": combined_confidence,
            "reasoning": combined_reasoning,
            "suggestions": suggestions,
        }
