"""Intelligent File Format Detection using LLM.

This module uses LLM + heuristics to intelligently detect neuroscience data formats,
going beyond simple file extension matching.
"""

import json
from pathlib import Path
from typing import Any

from models import GlobalState, LogLevel
from services import LLMService


class IntelligentFormatDetector:
    """LLM-powered format detection for neuroscience data files.

    Features:
    - Analyzes file structure beyond extensions
    - Detects companion files (e.g., .bin + .meta)
    - Recognizes naming patterns
    - Provides confidence scores
    - Suggests missing files
    """

    def __init__(self, llm_service: LLMService | None = None):
        """Initialize the intelligent format detector.

        Args:
            llm_service: Optional LLM service for intelligent analysis
        """
        self.llm_service = llm_service

        # Known format patterns
        self.format_patterns: dict[str, dict[str, Any]] = {
            "NWB": {
                "extensions": [".nwb", ".nwb.h5"],
                "patterns": ["nwb", "neurodata"],
                "description": "Neurodata Without Borders format",
            },
            "SpikeGLX": {
                "extensions": [".bin", ".meta"],
                "patterns": ["imec", "ap.bin", "lf.bin", "_g0_", "_t0"],
                "companion_required": True,
                "companion_ext": ".meta",
            },
            "OpenEphys": {
                "extensions": [".continuous", ".spikes", ".events"],
                "patterns": ["CH", "100_", "continuous"],
                "folder_structure": True,
            },
            "Intan": {
                "extensions": [".rhd", ".rhs"],
                "patterns": ["amplifier", "time"],
            },
            "Blackrock": {
                "extensions": [".ns1", ".ns2", ".ns3", ".ns4", ".ns5", ".ns6", ".nev"],
                "patterns": [],
            },
            "Plexon": {
                "extensions": [".plx", ".pl2"],
                "patterns": [],
            },
            "Neuralynx": {
                "extensions": [".ncs", ".nse", ".ntt", ".nvt", ".nev"],
                "patterns": ["CSC", "Events"],
            },
            "Axon": {
                "extensions": [".abf"],
                "patterns": ["abf", "pclamp", "axon"],
                "description": "Axon Instruments pCLAMP format",
            },
        }

    async def detect_format(
        self,
        file_path: str,
        state: GlobalState,
    ) -> dict[str, Any]:
        """Intelligently detect the format of a neuroscience data file.

        Args:
            file_path: Path to the file or directory
            state: Global conversion state

        Returns:
            Dict with:
            - detected_format: Most likely format
            - confidence: Confidence score 0-100
            - reasoning: Why this format was detected
            - missing_files: List of expected companion files that are missing
            - suggestions: Suggestions for user
        """
        path = Path(file_path)

        # Step 1: Gather file information
        file_info = self._analyze_file_structure(path)

        # Step 2: Apply heuristic rules
        heuristic_results = self._apply_heuristics(file_info)

        # Step 3: Use LLM for intelligent analysis (if available)
        if self.llm_service and len(heuristic_results) > 1:
            llm_result = await self._llm_format_analysis(file_info, heuristic_results, state)
            return llm_result
        elif heuristic_results:
            # Return best heuristic match
            best_match = max(heuristic_results, key=lambda x: x["confidence"])
            return {
                "detected_format": best_match["format"],
                "confidence": best_match["confidence"],
                "reasoning": best_match["reasoning"],
                "missing_files": best_match.get("missing_files", []),
                "suggestions": best_match.get("suggestions", []),
                "detection_method": "heuristic",
            }
        else:
            # Unknown format
            return {
                "detected_format": "unknown",
                "confidence": 0,
                "reasoning": "Could not match file patterns to any known format",
                "missing_files": [],
                "suggestions": ["Check if file is a recognized neuroscience data format"],
                "detection_method": "heuristic",
            }

    def _analyze_file_structure(self, path: Path) -> dict[str, Any]:
        """Analyze file/directory structure."""
        info = {
            "path": str(path),
            "name": path.name,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        }

        if path.is_file():
            info.update(
                {
                    "extension": path.suffix.lower(),
                    "stem": path.stem,
                    "size_mb": path.stat().st_size / (1024 * 1024),
                    "parent_files": [f.name for f in path.parent.iterdir() if f.is_file()][:20],  # Limit to 20
                }
            )
        elif path.is_dir():
            files = list(path.rglob("*"))[:50]  # Limit to 50 files
            info.update(
                {
                    "file_count": len(files),
                    "file_names": [f.name for f in files if f.is_file()][:20],
                    "extensions": list({f.suffix.lower() for f in files if f.is_file()}),
                    "subdirs": [d.name for d in path.iterdir() if d.is_dir()][:10],
                }
            )

        return info

    def _apply_heuristics(self, file_info: dict[str, Any]) -> list[dict[str, Any]]:
        """Apply heuristic rules to detect format."""
        results = []

        for format_name, patterns in self.format_patterns.items():
            match_score = 0
            reasoning_parts = []
            missing_files = []

            # Check extension match
            if file_info.get("extension") in patterns["extensions"]:
                match_score += 40
                reasoning_parts.append(f"File extension {file_info['extension']} matches {format_name}")

            # Check directory extensions (if directory)
            if file_info.get("extensions"):
                ext_matches = set(file_info["extensions"]) & set(patterns["extensions"])
                if ext_matches:
                    match_score += 30
                    reasoning_parts.append(f"Directory contains {format_name} files: {', '.join(ext_matches)}")

            # Check naming patterns
            file_name_lower = file_info.get("name", "").lower()
            parent_files = [f.lower() for f in file_info.get("parent_files", [])]

            for pattern in patterns.get("patterns", []):
                if pattern.lower() in file_name_lower:
                    match_score += 20
                    reasoning_parts.append(f"Filename contains '{pattern}' pattern")
                    break

            # Check companion files (e.g., .bin needs .meta for SpikeGLX)
            if patterns.get("companion_required") and file_info.get("is_file"):
                companion_ext = patterns.get("companion_ext")
                expected_companion = file_info["stem"] + companion_ext

                if expected_companion.lower() in parent_files:
                    match_score += 20
                    reasoning_parts.append(f"Found companion file: {expected_companion}")
                else:
                    match_score -= 10  # Penalty for missing required companion
                    missing_files.append(expected_companion)
                    reasoning_parts.append(f"Missing companion file: {expected_companion}")

            # Check folder structure requirements
            if patterns.get("folder_structure") and not file_info.get("is_dir"):
                match_score -= 20
                reasoning_parts.append(f"{format_name} typically requires folder structure")

            if match_score > 20:  # Only include if reasonable match
                result = {
                    "format": format_name,
                    "confidence": min(match_score, 90),  # Cap at 90 for heuristics
                    "reasoning": "; ".join(reasoning_parts),
                    "missing_files": missing_files,
                    "suggestions": self._generate_suggestions(format_name, missing_files),
                }
                results.append(result)

        return results

    def _generate_suggestions(self, format_name: str, missing_files: list[str]) -> list[str]:
        """Generate helpful suggestions based on detection."""
        suggestions = []

        if missing_files:
            suggestions.append(f"For {format_name} format, please upload: {', '.join(missing_files)}")

        if format_name == "SpikeGLX":
            suggestions.append("SpikeGLX recordings require both .bin (data) and .meta (metadata) files")
        elif format_name == "OpenEphys":
            suggestions.append("OpenEphys data should be uploaded as a folder containing all recording files")

        return suggestions

    async def _llm_format_analysis(
        self,
        file_info: dict[str, Any],
        heuristic_results: list[dict[str, Any]],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to intelligently choose between multiple possible formats."""
        try:
            system_prompt = """You are an expert in neuroscience data formats with deep knowledge of:
- NWB (Neurodata Without Borders) format
- SpikeGLX/Neuropixels file structures
- OpenEphys recording formats
- Intan, Blackrock, Plexon, Neuralynx systems
- File naming conventions in neuroscience labs
- Companion file requirements

Your job is to analyze file information and determine the most likely data format."""

            # Format heuristic results for LLM
            candidates = "\n".join(
                [f"**{r['format']}** (confidence: {r['confidence']}%)\n- {r['reasoning']}" for r in heuristic_results]
            )

            user_prompt = f"""Analyze this neuroscience data file and determine its format.

**File Information:**
```json
{json.dumps(file_info, indent=2)}
```

**Heuristic Analysis Results:**
{candidates}

**Your Task:**
1. Review all the evidence (filename, extension, companion files, patterns)
2. Choose the MOST LIKELY format
3. Provide confidence score (0-100)
4. Explain your reasoning
5. Note any missing files
6. Provide actionable suggestions

Be decisive but honest about uncertainty."""

            output_schema = {
                "type": "object",
                "properties": {
                    "detected_format": {"type": "string", "description": "The most likely data format"},
                    "confidence": {"type": "number", "description": "Confidence score 0-100"},
                    "reasoning": {"type": "string", "description": "Detailed explanation of format detection"},
                    "missing_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Expected companion files that are missing",
                    },
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Actionable suggestions for the user",
                    },
                    "alternative_formats": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Other possible formats to consider",
                    },
                },
                "required": ["detected_format", "confidence", "reasoning"],
            }

            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            response["detection_method"] = "llm"

            state.add_log(
                LogLevel.INFO,
                f"LLM format detection: {response['detected_format']} ({response['confidence']}%)",
                {
                    "format": response["detected_format"],
                    "confidence": response["confidence"],
                },
            )

            return dict(response)  # Cast Any to dict

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"LLM format detection failed, using best heuristic: {e}",
            )
            # Fallback to best heuristic
            best_match = max(heuristic_results, key=lambda x: x["confidence"])
            best_match["detection_method"] = "heuristic_fallback"
            return best_match
