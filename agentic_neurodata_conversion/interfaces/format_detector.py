"""
Format detection interface for identifying neuroscience data formats.

This module provides the FormatDetector class for analyzing dataset directories
and identifying data formats, file structures, and basic metadata.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FormatDetector:
    """Detects neuroscience data formats from file patterns and structures."""

    def __init__(self):
        self.supported_formats = {
            "open_ephys": {
                "extensions": [".continuous", ".spikes", ".events"],
                "patterns": ["continuous", "spikes", "events"],
                "required_files": [],
            },
            "spikeglx": {
                "extensions": [".bin", ".meta"],
                "patterns": ["imec", "nidq"],
                "required_files": [],
            },
            "neuralynx": {
                "extensions": [".ncs", ".nev", ".ntt", ".nse"],
                "patterns": [],
                "required_files": [],
            },
            "blackrock": {
                "extensions": [".ns1", ".ns2", ".ns3", ".ns4", ".ns5", ".ns6", ".nev"],
                "patterns": [],
                "required_files": [],
            },
            "intan": {
                "extensions": [".rhd", ".rhs"],
                "patterns": [],
                "required_files": [],
            },
        }

    async def analyze_directory(self, dataset_dir: str) -> dict[str, Any]:
        """
        Analyze a dataset directory to detect formats and structure.

        Args:
            dataset_dir: Path to the dataset directory

        Returns:
            Dictionary containing analysis results
        """
        dataset_path = Path(dataset_dir)

        analysis = {
            "dataset_path": str(dataset_path.absolute()),
            "formats": [],
            "file_count": 0,
            "total_size": 0,
            "structure": {},
            "file_patterns": [],
            "earliest_timestamp": None,
            "latest_timestamp": None,
        }

        try:
            # Collect all files
            all_files = []
            for file_path in dataset_path.rglob("*"):
                if file_path.is_file():
                    all_files.append(file_path)

            analysis["file_count"] = len(all_files)

            # Analyze files
            extensions_found = set()
            patterns_found = set()
            timestamps = []

            for file_path in all_files:
                try:
                    # File size
                    file_size = file_path.stat().st_size
                    analysis["total_size"] += file_size

                    # Timestamps
                    mtime = file_path.stat().st_mtime
                    timestamps.append(mtime)

                    # Extensions and patterns
                    extensions_found.add(file_path.suffix.lower())
                    patterns_found.add(file_path.stem.lower())

                except (OSError, PermissionError):
                    logger.warning(f"Could not access file: {file_path}")
                    continue

            # Set timestamps
            if timestamps:
                analysis["earliest_timestamp"] = min(timestamps)
                analysis["latest_timestamp"] = max(timestamps)

            # Detect formats
            detected_formats = []
            for format_name, format_info in self.supported_formats.items():
                confidence = self._calculate_format_confidence(
                    format_info, extensions_found, patterns_found
                )
                if confidence > 0:
                    detected_formats.append(
                        {
                            "format": format_name,
                            "confidence": confidence,
                            "matching_extensions": [
                                ext
                                for ext in format_info["extensions"]
                                if ext in extensions_found
                            ],
                            "matching_patterns": [
                                pattern
                                for pattern in format_info["patterns"]
                                if any(pattern in p for p in patterns_found)
                            ],
                        }
                    )

            # Sort by confidence
            detected_formats.sort(key=lambda x: x["confidence"], reverse=True)
            analysis["formats"] = detected_formats

            # Store patterns for later use
            analysis["file_patterns"] = list(patterns_found)

            logger.info(
                f"Format detection completed: {len(detected_formats)} formats detected"
            )

        except Exception as e:
            logger.error(f"Format detection failed: {e}")
            analysis["error"] = str(e)

        return analysis

    def _calculate_format_confidence(
        self, format_info: dict[str, Any], extensions_found: set, patterns_found: set
    ) -> float:
        """Calculate confidence score for a format match."""
        confidence = 0.0

        # Check extensions
        matching_extensions = [
            ext for ext in format_info["extensions"] if ext in extensions_found
        ]
        if matching_extensions:
            confidence += 0.6 * (
                len(matching_extensions) / len(format_info["extensions"])
            )

        # Check patterns
        matching_patterns = [
            pattern
            for pattern in format_info["patterns"]
            if any(pattern in p for p in patterns_found)
        ]
        if matching_patterns:
            confidence += 0.4 * (
                len(matching_patterns) / max(len(format_info["patterns"]), 1)
            )

        return min(confidence, 1.0)

    async def extract_format_metadata(
        self, dataset_dir: str, format_name: str
    ) -> dict[str, Any]:
        """
        Extract format-specific metadata from dataset.

        Args:
            dataset_dir: Path to the dataset directory
            format_name: Name of the detected format

        Returns:
            Dictionary containing format-specific metadata
        """
        if format_name == "open_ephys":
            return await self._extract_open_ephys_metadata(dataset_dir)
        elif format_name == "spikeglx":
            return await self._extract_spikeglx_metadata(dataset_dir)
        elif format_name == "neuralynx":
            return await self._extract_neuralynx_metadata(dataset_dir)
        elif format_name == "blackrock":
            return await self._extract_blackrock_metadata(dataset_dir)
        elif format_name == "intan":
            return await self._extract_intan_metadata(dataset_dir)
        else:
            return await self._extract_generic_metadata(dataset_dir, format_name)

    async def _extract_open_ephys_metadata(self, dataset_dir: str) -> dict[str, Any]:
        """Extract Open Ephys specific metadata."""
        dataset_path = Path(dataset_dir)
        metadata = {"recording_system": "Open Ephys", "format": "open_ephys"}

        try:
            # Look for settings.xml file
            settings_file = None
            for settings_path in dataset_path.rglob("settings.xml"):
                settings_file = settings_path
                break

            if settings_file and settings_file.exists():
                metadata.update(await self._parse_open_ephys_settings(settings_file))

            # Look for continuous files to extract channel info
            continuous_files = list(dataset_path.rglob("*.continuous"))
            if continuous_files:
                metadata["continuous_files"] = len(continuous_files)
                # Try to extract sampling rate from filename patterns
                for file_path in continuous_files[:3]:  # Check first few files
                    filename = file_path.name
                    if "CH" in filename:
                        # Extract channel number
                        import re

                        match = re.search(r"CH(\d+)", filename)
                        if match:
                            if "channels" not in metadata:
                                metadata["channels"] = []
                            metadata["channels"].append(int(match.group(1)))

            # Look for events files
            events_files = list(dataset_path.rglob("*.events"))
            if events_files:
                metadata["events_files"] = len(events_files)

            # Look for spikes files
            spikes_files = list(dataset_path.rglob("*.spikes"))
            if spikes_files:
                metadata["spikes_files"] = len(spikes_files)

        except Exception as e:
            logger.warning(f"Error extracting Open Ephys metadata: {e}")
            metadata["extraction_error"] = str(e)

        return metadata

    async def _parse_open_ephys_settings(self, settings_file: Path) -> dict[str, Any]:
        """Parse Open Ephys settings.xml file."""
        metadata = {}

        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(settings_file)
            root = tree.getroot()

            # Extract sampling rate
            for processor in root.findall(".//PROCESSOR"):
                if processor.get("name") == "Sources/Rhythm FPGA":
                    sample_rate = processor.get("sampleRate")
                    if sample_rate:
                        metadata["sampling_rate"] = float(sample_rate)
                        break

            # Extract channel count
            channels = root.findall(".//CHANNEL")
            if channels:
                metadata["channel_count"] = len(channels)
                metadata["channel_info"] = []
                for channel in channels:
                    ch_info = {
                        "number": int(channel.get("number", 0)),
                        "name": channel.get("name", ""),
                        "enabled": channel.get("record", "false").lower() == "true",
                    }
                    metadata["channel_info"].append(ch_info)

        except Exception as e:
            logger.warning(f"Error parsing Open Ephys settings: {e}")
            metadata["settings_parse_error"] = str(e)

        return metadata

    async def _extract_spikeglx_metadata(self, dataset_dir: str) -> dict[str, Any]:
        """Extract SpikeGLX specific metadata."""
        dataset_path = Path(dataset_dir)
        metadata = {"recording_system": "SpikeGLX", "format": "spikeglx"}

        try:
            # Look for .meta files
            meta_files = list(dataset_path.rglob("*.meta"))
            if meta_files:
                metadata["meta_files"] = len(meta_files)
                # Parse the first meta file
                meta_file = meta_files[0]
                metadata.update(await self._parse_spikeglx_meta(meta_file))

            # Look for .bin files
            bin_files = list(dataset_path.rglob("*.bin"))
            if bin_files:
                metadata["bin_files"] = len(bin_files)
                metadata["data_files"] = [f.name for f in bin_files]

            # Identify probe types from filenames
            probe_types = set()
            for file_path in dataset_path.rglob("*"):
                if file_path.is_file():
                    filename = file_path.name.lower()
                    if "imec" in filename:
                        probe_types.add("imec")
                    elif "nidq" in filename:
                        probe_types.add("nidq")

            if probe_types:
                metadata["probe_types"] = list(probe_types)

        except Exception as e:
            logger.warning(f"Error extracting SpikeGLX metadata: {e}")
            metadata["extraction_error"] = str(e)

        return metadata

    async def _parse_spikeglx_meta(self, meta_file: Path) -> dict[str, Any]:
        """Parse SpikeGLX .meta file."""
        metadata = {}

        try:
            with open(meta_file) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Parse important metadata fields
                        if key == "imSampRate":
                            metadata["sampling_rate"] = float(value)
                        elif key == "nSavedChans":
                            metadata["channel_count"] = int(value)
                        elif key == "imProbeOpt":
                            metadata["probe_option"] = value
                        elif key == "typeThis":
                            metadata["file_type"] = value
                        elif key == "fileSizeBytes":
                            metadata["file_size_bytes"] = int(value)
                        elif key.startswith("~"):
                            # Channel map information
                            if "channel_map" not in metadata:
                                metadata["channel_map"] = {}
                            metadata["channel_map"][key] = value

        except Exception as e:
            logger.warning(f"Error parsing SpikeGLX meta file: {e}")
            metadata["meta_parse_error"] = str(e)

        return metadata

    async def _extract_neuralynx_metadata(self, dataset_dir: str) -> dict[str, Any]:
        """Extract Neuralynx specific metadata."""
        dataset_path = Path(dataset_dir)
        metadata = {"recording_system": "Neuralynx", "format": "neuralynx"}

        try:
            # Count different file types
            ncs_files = list(dataset_path.rglob("*.ncs"))  # Continuous data
            nev_files = list(dataset_path.rglob("*.nev"))  # Events
            ntt_files = list(dataset_path.rglob("*.ntt"))  # Tetrode data
            nse_files = list(dataset_path.rglob("*.nse"))  # Single electrode data

            if ncs_files:
                metadata["ncs_files"] = len(ncs_files)
                metadata["continuous_channels"] = [f.stem for f in ncs_files]

            if nev_files:
                metadata["nev_files"] = len(nev_files)

            if ntt_files:
                metadata["ntt_files"] = len(ntt_files)
                metadata["tetrode_files"] = [f.stem for f in ntt_files]

            if nse_files:
                metadata["nse_files"] = len(nse_files)

            # Try to extract header information from first .ncs file
            if ncs_files:
                header_info = await self._parse_neuralynx_header(ncs_files[0])
                metadata.update(header_info)

        except Exception as e:
            logger.warning(f"Error extracting Neuralynx metadata: {e}")
            metadata["extraction_error"] = str(e)

        return metadata

    async def _parse_neuralynx_header(self, ncs_file: Path) -> dict[str, Any]:
        """Parse Neuralynx file header."""
        metadata = {}

        try:
            with open(ncs_file, "rb") as f:
                # Read header (first 16KB)
                header_data = f.read(16384)
                header_str = header_data.decode("latin-1", errors="ignore")

                # Extract key information
                lines = header_str.split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith("-SamplingFrequency"):
                        parts = line.split()
                        if len(parts) > 1:
                            metadata["sampling_rate"] = float(parts[1])
                    elif line.startswith("-AcqEntName"):
                        parts = line.split(None, 1)
                        if len(parts) > 1:
                            metadata["channel_name"] = parts[1]
                    elif line.startswith("-InputRange"):
                        parts = line.split()
                        if len(parts) > 1:
                            metadata["input_range"] = float(parts[1])

        except Exception as e:
            logger.warning(f"Error parsing Neuralynx header: {e}")
            metadata["header_parse_error"] = str(e)

        return metadata

    async def _extract_blackrock_metadata(self, dataset_dir: str) -> dict[str, Any]:
        """Extract Blackrock specific metadata."""
        dataset_path = Path(dataset_dir)
        metadata = {"recording_system": "Blackrock", "format": "blackrock"}

        try:
            # Look for different Blackrock file types
            ns_files = {}
            for ext in [".ns1", ".ns2", ".ns3", ".ns4", ".ns5", ".ns6"]:
                files = list(dataset_path.rglob(f"*{ext}"))
                if files:
                    ns_files[ext] = len(files)

            if ns_files:
                metadata["ns_files"] = ns_files

            # Look for event files
            nev_files = list(dataset_path.rglob("*.nev"))
            if nev_files:
                metadata["nev_files"] = len(nev_files)

            # Look for CCF files (channel configuration)
            ccf_files = list(dataset_path.rglob("*.ccf"))
            if ccf_files:
                metadata["ccf_files"] = len(ccf_files)

        except Exception as e:
            logger.warning(f"Error extracting Blackrock metadata: {e}")
            metadata["extraction_error"] = str(e)

        return metadata

    async def _extract_intan_metadata(self, dataset_dir: str) -> dict[str, Any]:
        """Extract Intan specific metadata."""
        dataset_path = Path(dataset_dir)
        metadata = {"recording_system": "Intan", "format": "intan"}

        try:
            # Look for .rhd and .rhs files
            rhd_files = list(dataset_path.rglob("*.rhd"))
            rhs_files = list(dataset_path.rglob("*.rhs"))

            if rhd_files:
                metadata["rhd_files"] = len(rhd_files)
                metadata["file_type"] = "RHD2000"

            if rhs_files:
                metadata["rhs_files"] = len(rhs_files)
                metadata["file_type"] = "RHS2000"

            # Try to extract basic info from file headers
            data_files = rhd_files + rhs_files
            if data_files:
                header_info = await self._parse_intan_header(data_files[0])
                metadata.update(header_info)

        except Exception as e:
            logger.warning(f"Error extracting Intan metadata: {e}")
            metadata["extraction_error"] = str(e)

        return metadata

    async def _parse_intan_header(self, intan_file: Path) -> dict[str, Any]:
        """Parse Intan file header."""
        metadata = {}

        try:
            with open(intan_file, "rb") as f:
                # Read magic number and version
                magic_number = int.from_bytes(f.read(4), byteorder="little")

                if magic_number == 0xC6912702:  # RHD2000 format
                    version = f.read(2)
                    metadata["format_version"] = f"{version[1]}.{version[0]}"

                    # Read sampling rate (at offset 8)
                    f.seek(8)
                    sampling_rate = int.from_bytes(f.read(4), byteorder="little")
                    metadata["sampling_rate"] = float(sampling_rate)

        except Exception as e:
            logger.warning(f"Error parsing Intan header: {e}")
            metadata["header_parse_error"] = str(e)

        return metadata

    async def _extract_generic_metadata(
        self, dataset_dir: str, format_name: str
    ) -> dict[str, Any]:
        """Extract generic metadata for unknown formats."""
        dataset_path = Path(dataset_dir)
        metadata = {"recording_system": "Unknown", "format": format_name}

        try:
            # Basic file analysis
            all_files = list(dataset_path.rglob("*"))
            data_files = [f for f in all_files if f.is_file()]

            if data_files:
                # File size analysis
                total_size = sum(f.stat().st_size for f in data_files)
                metadata["total_size_bytes"] = total_size
                metadata["file_count"] = len(data_files)

                # Extension analysis
                extensions = {}
                for f in data_files:
                    ext = f.suffix.lower()
                    extensions[ext] = extensions.get(ext, 0) + 1

                metadata["file_extensions"] = extensions

        except Exception as e:
            logger.warning(f"Error extracting generic metadata: {e}")
            metadata["extraction_error"] = str(e)

        return metadata
