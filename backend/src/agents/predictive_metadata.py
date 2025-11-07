"""
Predictive Metadata System with LLM Learning.

This module predicts and suggests metadata based on deep file analysis,
going beyond simple inference to provide smart defaults.
"""

import json
from pathlib import Path
from typing import Any, Optional

from models import GlobalState, LogLevel
from services import LLMService


class PredictiveMetadataSystem:
    """
    Advanced metadata prediction using LLM and pattern recognition.

    Features:
    - Deep file content analysis
    - Cross-file pattern learning
    - Smart defaults based on similar files
    - Confidence-weighted suggestions
    - Contextual metadata generation
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize predictive metadata system.

        Args:
            llm_service: LLM service for intelligent predictions
        """
        self.llm_service = llm_service
        self.prediction_history = []  # Store predictions for learning

    async def predict_metadata(
        self,
        file_path: str,
        file_format: str,
        basic_inference: dict[str, Any],
        state: GlobalState,
    ) -> dict[str, Any]:
        """
        Predict comprehensive metadata using deep analysis.

        Args:
            file_path: Path to the data file
            file_format: Detected file format
            basic_inference: Basic inference results
            state: Global conversion state

        Returns:
            Dict with:
            - predicted_metadata: Predicted field values
            - confidence_scores: Confidence for each prediction
            - reasoning: Explanation of predictions
            - smart_defaults: Suggested default values
            - fill_suggestions: How to fill remaining fields
        """
        if not self.llm_service:
            return self._basic_predictions(basic_inference)

        try:
            # Step 1: Deep file analysis
            file_analysis = await self._deep_file_analysis(file_path, file_format, state)

            # Step 2: Cross-reference with previous conversions
            similar_patterns = self._find_similar_patterns(file_analysis)

            # Step 3: LLM-powered prediction
            predictions = await self._llm_predict_metadata(
                file_path=file_path,
                file_format=file_format,
                file_analysis=file_analysis,
                basic_inference=basic_inference,
                similar_patterns=similar_patterns,
                state=state,
            )

            # Store prediction for future learning
            self._store_prediction(file_path, predictions)

            state.add_log(
                LogLevel.INFO,
                f"Predictive metadata generated with {len(predictions.get('predicted_metadata', {}))} fields",
                {
                    "predicted_fields": list(predictions.get("predicted_metadata", {}).keys()),
                    "avg_confidence": sum(predictions.get("confidence_scores", {}).values())
                    / max(len(predictions.get("confidence_scores", {})), 1),
                },
            )

            return predictions

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Predictive metadata failed, using basic: {e}",
            )
            return self._basic_predictions(basic_inference)

    async def _deep_file_analysis(
        self,
        file_path: str,
        file_format: str,
        state: GlobalState,
    ) -> dict[str, Any]:
        """
        Perform deep analysis of file beyond basic inference.
        """
        path = Path(file_path)
        analysis = {
            "path": file_path,
            "format": file_format,
            "filename_parts": self._parse_filename(path.name),
        }

        # Format-specific deep analysis
        if file_format == "SpikeGLX":
            analysis.update(await self._analyze_spikeglx_deep(path, state))
        elif file_format == "OpenEphys":
            analysis.update(await self._analyze_openephys_deep(path, state))

        return analysis

    def _parse_filename(self, filename: str) -> dict[str, Any]:
        """Extract structured information from filename."""
        parts = {
            "has_date": False,
            "has_subject_id": False,
            "has_session_id": False,
            "has_experimenter_hint": False,
            "lab_patterns": [],
        }

        filename_lower = filename.lower()

        # Detect date patterns (YYYYMMDD, YYYY-MM-DD, etc.)
        import re

        date_patterns = [
            r"\d{8}",  # 20240117
            r"\d{4}-\d{2}-\d{2}",  # 2024-01-17
            r"\d{4}_\d{2}_\d{2}",  # 2024_01_17
        ]
        for pattern in date_patterns:
            if re.search(pattern, filename):
                parts["has_date"] = True
                parts["date_string"] = re.search(pattern, filename).group()
                break

        # Detect subject ID patterns
        subject_patterns = [
            r"mouse[_-]?\d+",
            r"rat[_-]?\d+",
            r"subject[_-]?\d+",
            r"animal[_-]?\d+",
        ]
        for pattern in subject_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                parts["has_subject_id"] = True
                parts["subject_id_hint"] = match.group()
                break

        # Detect session ID patterns
        session_patterns = [
            r"session[_-]?\d+",
            r"sess[_-]?\d+",
            r"s\d{2,}",
        ]
        for pattern in session_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                parts["has_session_id"] = True
                parts["session_id_hint"] = match.group()
                break

        # Detect lab/experimenter name patterns
        # Common patterns: LastnameYYYY, Lastname_YYYYMMDD, etc.
        if "_" in filename or "-" in filename:
            first_part = filename.split("_")[0].split("-")[0]
            if first_part.isalpha() and len(first_part) > 2:
                parts["has_experimenter_hint"] = True
                parts["experimenter_hint"] = first_part

        return parts

    async def _analyze_spikeglx_deep(self, path: Path, state: GlobalState) -> dict[str, Any]:
        """Deep analysis of SpikeGLX files."""
        analysis = {"spikeglx_details": {}}

        # Try to read .meta file for rich metadata
        meta_file = path.with_suffix(".meta")
        if meta_file.exists():
            try:
                meta_content = {}
                with open(meta_file) as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            meta_content[key] = value

                analysis["spikeglx_details"] = {
                    "has_meta_file": True,
                    "sampling_rate": meta_content.get("imSampRate"),
                    "channel_count": meta_content.get("nSavedChans"),
                    "recording_time": meta_content.get("fileTimeSecs"),
                    "probe_type": meta_content.get("imProbeOpt"),
                }
            except Exception as e:
                state.add_log(LogLevel.DEBUG, f"Could not parse .meta file: {e}")

        return analysis

    async def _analyze_openephys_deep(self, path: Path, state: GlobalState) -> dict[str, Any]:
        """Deep analysis of OpenEphys files."""
        return {"openephys_details": {}}

    def _find_similar_patterns(self, file_analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Find similar file patterns from history."""
        similar = []

        for past_prediction in self.prediction_history[-10:]:  # Last 10 predictions
            # Simple similarity scoring
            similarity_score = 0

            if past_prediction.get("format") == file_analysis.get("format"):
                similarity_score += 40

            # Compare filename patterns
            past_filename_parts = past_prediction.get("filename_parts", {})
            current_filename_parts = file_analysis.get("filename_parts", {})

            if past_filename_parts.get("has_subject_id") == current_filename_parts.get("has_subject_id"):
                similarity_score += 10
            if past_filename_parts.get("has_date") == current_filename_parts.get("has_date"):
                similarity_score += 10

            if similarity_score > 40:
                similar.append(
                    {
                        "past_file": past_prediction.get("path"),
                        "similarity": similarity_score,
                        "metadata_used": past_prediction.get("metadata", {}),
                    }
                )

        return similar

    async def _llm_predict_metadata(
        self,
        file_path: str,
        file_format: str,
        file_analysis: dict[str, Any],
        basic_inference: dict[str, Any],
        similar_patterns: list[dict[str, Any]],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to predict metadata intelligently."""
        system_prompt = """You are an expert neuroscience data curator with predictive abilities.

Your job is to predict comprehensive NWB metadata based on:
1. Deep file analysis (format, structure, content)
2. Filename patterns (dates, subject IDs, experimenter hints)
3. Similar previous conversions
4. Domain knowledge of neuroscience labs and protocols

Provide smart defaults and educated guesses with confidence scores.
Be bold in predictions but honest about uncertainty."""

        user_prompt = f"""Predict comprehensive NWB metadata for this file.

**File Path**: {file_path}
**Detected Format**: {file_format}

**Deep File Analysis**:
```json
{json.dumps(file_analysis, indent=2)}
```

**Basic Inference (heuristic)**:
```json
{json.dumps(basic_inference.get("inferred_metadata", {}), indent=2)}
```

**Similar Previous Files** (if any):
{json.dumps(similar_patterns, indent=2) if similar_patterns else "No similar files found"}

**Your Task**:
Predict ALL possible metadata fields with confidence scores:

**DANDI-Required Fields** (prioritize):
- experimenter: Full name(s) of experimenter(s)
- institution: Full institution name
- experiment_description: Rich, detailed description
- session_description: What happened in this session

**Subject Metadata**:
- subject_id: Unique identifier
- species: Scientific name
- age: Age with units
- sex: M/F/U/O
- genotype: If genetic line is clear

**Session Metadata**:
- session_start_time: ISO timestamp if date in filename
- keywords: 5-10 relevant keywords

**Recording Metadata**:
- recording_system: Device/software used
- recording_location: Brain region

For EACH field:
1. Make your best prediction
2. Provide confidence score (0-100)
3. Explain reasoning
4. Note if it's a guess vs. extracted from file

Be aggressive with predictions - provide values even if uncertain!"""

        output_schema = {
            "type": "object",
            "properties": {
                "predicted_metadata": {"type": "object", "description": "Predicted metadata field values"},
                "confidence_scores": {"type": "object", "description": "Confidence 0-100 for each field"},
                "reasoning": {"type": "object", "description": "Explanation for each prediction"},
                "smart_defaults": {"type": "object", "description": "Suggested default values for empty fields"},
                "fill_suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Suggestions for how user can fill remaining fields",
                },
            },
            "required": ["predicted_metadata", "confidence_scores", "reasoning"],
        }

        response = await self.llm_service.generate_structured_output(
            prompt=user_prompt,
            output_schema=output_schema,
            system_prompt=system_prompt,
        )

        return response

    def _basic_predictions(self, basic_inference: dict[str, Any]) -> dict[str, Any]:
        """Fallback basic predictions without LLM."""
        return {
            "predicted_metadata": basic_inference.get("inferred_metadata", {}),
            "confidence_scores": basic_inference.get("confidence_scores", {}),
            "reasoning": basic_inference.get("reasoning", {}),
            "smart_defaults": {},
            "fill_suggestions": ["Provide metadata based on your experimental protocol"],
        }

    def _store_prediction(self, file_path: str, predictions: dict[str, Any]):
        """Store prediction for future pattern learning."""
        self.prediction_history.append(
            {
                "path": file_path,
                "metadata": predictions.get("predicted_metadata", {}),
                "confidence": predictions.get("confidence_scores", {}),
                "timestamp": "stored",
            }
        )

        # Keep only last 20 predictions
        if len(self.prediction_history) > 20:
            self.prediction_history = self.prediction_history[-20:]
