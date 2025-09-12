"""
Format detection utilities for the agentic neurodata conversion system.

This module provides functionality to detect and identify neuroscience data formats
based on file patterns, directory structures, and content analysis.
"""

import logging
from pathlib import Path
import re
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class FormatDetector:
    """
    Utility class for detecting neuroscience data formats.

    Provides methods to identify data formats based on file extensions,
    directory structures, and content patterns commonly used in neuroscience.
    """

    # Format definitions with detection patterns
    FORMAT_PATTERNS = {
        "open_ephys": {
            "name": "Open Ephys",
            "description": "Open Ephys recording format",
            "file_patterns": ["*.continuous", "*.spikes", "*.events"],
            "directory_patterns": ["Record Node *", "experiment*"],
            "required_files": ["settings.xml"],
            "optional_files": ["messages.events", "*.oebin"],
            "neuroconv_interface": "OpenEphysRecordingInterface",
        },
        "spikeglx": {
            "name": "SpikeGLX",
            "description": "SpikeGLX Neuropixels recording format",
            "file_patterns": ["*.bin", "*.meta"],
            "directory_patterns": [],
            "required_files": [],
            "file_pairs": [("*.ap.bin", "*.ap.meta"), ("*.lf.bin", "*.lf.meta")],
            "neuroconv_interface": "SpikeGLXRecordingInterface",
        },
        "neuralynx": {
            "name": "Neuralynx",
            "description": "Neuralynx recording format",
            "file_patterns": ["*.ncs", "*.nev", "*.ntt", "*.nse"],
            "directory_patterns": [],
            "required_files": [],
            "optional_files": ["*.nvt", "*.nrd"],
            "neuroconv_interface": "NeuraLynxRecordingInterface",
        },
        "blackrock": {
            "name": "Blackrock",
            "description": "Blackrock Microsystems recording format",
            "file_patterns": ["*.ns*", "*.nev", "*.ccf"],
            "directory_patterns": [],
            "required_files": [],
            "optional_files": ["*.sif"],
            "neuroconv_interface": "BlackrockRecordingInterface",
        },
        "intan": {
            "name": "Intan",
            "description": "Intan RHD/RHS recording format",
            "file_patterns": ["*.rhd", "*.rhs", "*.dat"],
            "directory_patterns": [],
            "required_files": [],
            "optional_files": ["*.xml"],
            "neuroconv_interface": "IntanRecordingInterface",
        },
        "mearec": {
            "name": "MEArec",
            "description": "MEArec simulated recordings",
            "file_patterns": ["*.h5", "*.hdf5"],
            "directory_patterns": [],
            "required_files": [],
            "content_patterns": ["mearec"],
            "neuroconv_interface": "MEArecRecordingInterface",
        },
        "nwb": {
            "name": "NWB",
            "description": "Neurodata Without Borders format",
            "file_patterns": ["*.nwb"],
            "directory_patterns": [],
            "required_files": [],
            "content_patterns": ["nwb-schema"],
            "neuroconv_interface": None,  # Already in NWB format
        },
    }

    def __init__(self):
        """Initialize format detector."""
        self._detection_cache = {}

    def detect_format(
        self, data_path: Union[str, Path], recursive: bool = True
    ) -> list[dict[str, Any]]:
        """
        Detect data formats in given path.

        Args:
            data_path: Path to analyze for data formats
            recursive: Whether to search recursively in subdirectories

        Returns:
            List of detected formats with confidence scores
        """
        data_path = Path(data_path)

        if not data_path.exists():
            logger.warning(f"Path not found: {data_path}")
            return []

        # Check cache first
        cache_key = (str(data_path), recursive)
        if cache_key in self._detection_cache:
            logger.debug(f"Using cached detection results for: {data_path}")
            return self._detection_cache[cache_key]

        logger.info(f"Detecting formats in: {data_path}")

        detected_formats = []

        if data_path.is_file():
            detected_formats = self._detect_file_format(data_path)
        else:
            detected_formats = self._detect_directory_format(data_path, recursive)

        # Cache results
        self._detection_cache[cache_key] = detected_formats

        logger.info(f"Detected {len(detected_formats)} formats in {data_path}")
        return detected_formats

    def _detect_file_format(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Detect format of a single file.

        Args:
            file_path: Path to file to analyze

        Returns:
            List of possible formats for the file
        """
        detected = []
        file_name = file_path.name.lower()

        for format_id, format_info in self.FORMAT_PATTERNS.items():
            confidence = 0

            # Check file patterns
            for pattern in format_info.get("file_patterns", []):
                if self._matches_pattern(file_name, pattern):
                    confidence += 0.8
                    break

            # Check content patterns for certain formats
            if (
                confidence > 0
                and format_info.get("content_patterns")
                and self._check_file_content(file_path, format_info["content_patterns"])
            ):
                confidence += 0.2

            if confidence > 0:
                detected.append(
                    {
                        "format_id": format_id,
                        "format_name": format_info["name"],
                        "description": format_info["description"],
                        "confidence": min(confidence, 1.0),
                        "file_path": str(file_path),
                        "neuroconv_interface": format_info.get("neuroconv_interface"),
                    }
                )

        # Sort by confidence
        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return detected

    def _detect_directory_format(
        self, directory: Path, recursive: bool
    ) -> list[dict[str, Any]]:
        """
        Detect formats in a directory.

        Args:
            directory: Directory to analyze
            recursive: Whether to search recursively

        Returns:
            List of detected formats in the directory
        """
        detected = []

        # Get all files in directory
        if recursive:
            all_files = list(directory.rglob("*"))
        else:
            all_files = list(directory.glob("*"))

        file_names = [f.name.lower() for f in all_files if f.is_file()]
        dir_names = [d.name for d in all_files if d.is_dir()]

        for format_id, format_info in self.FORMAT_PATTERNS.items():
            confidence = 0
            matched_files = []

            # Check required files
            required_files = format_info.get("required_files", [])
            if required_files:
                required_matches = 0
                for required_pattern in required_files:
                    if any(
                        self._matches_pattern(fname, required_pattern)
                        for fname in file_names
                    ):
                        required_matches += 1

                if required_matches == len(required_files):
                    confidence += 0.6
                elif required_matches > 0:
                    confidence += 0.3

            # Check file patterns
            file_pattern_matches = 0
            for pattern in format_info.get("file_patterns", []):
                pattern_matches = [
                    fname
                    for fname in file_names
                    if self._matches_pattern(fname, pattern)
                ]
                if pattern_matches:
                    file_pattern_matches += len(pattern_matches)
                    matched_files.extend(pattern_matches)

            if file_pattern_matches > 0:
                confidence += min(0.4, file_pattern_matches * 0.1)

            # Check directory patterns
            for dir_pattern in format_info.get("directory_patterns", []):
                if any(
                    self._matches_pattern(dname, dir_pattern) for dname in dir_names
                ):
                    confidence += 0.3
                    break

            # Check file pairs (e.g., .bin and .meta files)
            file_pairs = format_info.get("file_pairs", [])
            for pair in file_pairs:
                pattern1, pattern2 = pair
                files1 = [f for f in file_names if self._matches_pattern(f, pattern1)]
                files2 = [f for f in file_names if self._matches_pattern(f, pattern2)]

                # Check if we have matching pairs
                for f1 in files1:
                    base1 = self._get_base_name(f1, pattern1)
                    for f2 in files2:
                        base2 = self._get_base_name(f2, pattern2)
                        if base1 == base2:
                            confidence += 0.4
                            matched_files.extend([f1, f2])

            if confidence > 0:
                detected.append(
                    {
                        "format_id": format_id,
                        "format_name": format_info["name"],
                        "description": format_info["description"],
                        "confidence": min(confidence, 1.0),
                        "directory_path": str(directory),
                        "matched_files": list(set(matched_files)),
                        "neuroconv_interface": format_info.get("neuroconv_interface"),
                    }
                )

        # Sort by confidence
        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return detected

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """
        Check if filename matches glob-style pattern.

        Args:
            filename: Filename to check
            pattern: Glob pattern (e.g., "*.bin")

        Returns:
            True if filename matches pattern
        """
        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*").replace("?", ".")
        regex_pattern = f"^{regex_pattern}$"

        return bool(re.match(regex_pattern, filename, re.IGNORECASE))

    def _get_base_name(self, filename: str, pattern: str) -> str:
        """
        Extract base name from filename using pattern.

        Args:
            filename: Full filename
            pattern: Pattern with wildcards

        Returns:
            Base name without pattern-specific parts
        """
        # Simple implementation - remove pattern suffix/prefix
        if pattern.startswith("*."):
            # Remove extension
            return filename.rsplit(".", 1)[0]
        elif pattern.endswith("*"):
            # Remove prefix
            prefix = pattern[:-1]
            if filename.startswith(prefix):
                return filename[len(prefix) :]

        return filename

    def _check_file_content(self, file_path: Path, content_patterns: list[str]) -> bool:
        """
        Check if file contains specific content patterns.

        Args:
            file_path: Path to file to check
            content_patterns: List of patterns to search for

        Returns:
            True if any pattern is found in file
        """
        try:
            # Read first few KB of file to check for patterns
            with open(file_path, "rb") as f:
                content = f.read(8192).decode("utf-8", errors="ignore").lower()

            return any(pattern.lower() in content for pattern in content_patterns)

        except Exception as e:
            logger.debug(f"Could not check content of {file_path}: {e}")
            return False

    def get_format_info(self, format_id: str) -> Optional[dict[str, Any]]:
        """
        Get detailed information about a specific format.

        Args:
            format_id: Format identifier

        Returns:
            Format information dictionary or None if not found
        """
        return self.FORMAT_PATTERNS.get(format_id)

    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported format identifiers.

        Returns:
            List of format IDs
        """
        return list(self.FORMAT_PATTERNS.keys())

    def get_neuroconv_interfaces(self) -> dict[str, str]:
        """
        Get mapping of formats to NeuroConv interfaces.

        Returns:
            Dictionary mapping format IDs to NeuroConv interface names
        """
        interfaces = {}
        for format_id, format_info in self.FORMAT_PATTERNS.items():
            interface = format_info.get("neuroconv_interface")
            if interface:
                interfaces[format_id] = interface

        return interfaces

    def clear_cache(self) -> None:
        """Clear detection cache."""
        self._detection_cache.clear()
        logger.debug("Format detection cache cleared")

    def suggest_conversion_approach(
        self, detected_formats: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Suggest conversion approach based on detected formats.

        Args:
            detected_formats: List of detected formats from detect_format()

        Returns:
            Conversion approach suggestions
        """
        if not detected_formats:
            return {
                "status": "no_formats_detected",
                "message": "No supported formats detected",
                "suggestions": [],
            }

        # Get highest confidence format
        primary_format = detected_formats[0]

        suggestions = {
            "status": "success",
            "primary_format": primary_format,
            "conversion_approach": "neuroconv",
            "neuroconv_interface": primary_format.get("neuroconv_interface"),
            "confidence": primary_format.get("confidence", 0),
            "additional_formats": detected_formats[1:]
            if len(detected_formats) > 1
            else [],
            "recommendations": [],
        }

        # Add specific recommendations based on format
        format_id = primary_format.get("format_id")

        if format_id == "nwb":
            suggestions["recommendations"].append(
                "Data is already in NWB format - no conversion needed"
            )
        elif format_id in ["open_ephys", "spikeglx"]:
            suggestions["recommendations"].append(
                "High-quality format with good NeuroConv support"
            )
        elif primary_format.get("confidence", 0) < 0.5:
            suggestions["recommendations"].append(
                "Low confidence detection - manual verification recommended"
            )

        return suggestions
