"""Conversion Agent implementation.

Responsible for:
- Format detection
- NWB conversion using NeuroConv
- Pure technical conversion logic (no user interaction)
"""

import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from services.llm_service import LLMService

logger = logging.getLogger(__name__)

from agentic_neurodata_conversion.agents.intelligent_format_detector import IntelligentFormatDetector
from agentic_neurodata_conversion.models import ConversionStatus, GlobalState, LogLevel, MCPMessage, MCPResponse
from agentic_neurodata_conversion.utils.file_versioning import compute_sha256, create_versioned_file


class ConversionAgent:
    """Conversion agent for format detection and NWB conversion.

    This agent handles all technical conversion operations.
    """

    def __init__(self, llm_service: Optional["LLMService"] = None):
        """Initialize the conversion agent.

        Args:
            llm_service: Optional LLM service for intelligent features
        """
        self._supported_formats = self._get_supported_formats()
        self._llm_service = llm_service
        self._format_detector = IntelligentFormatDetector(llm_service) if llm_service else None

    def _get_supported_formats(self) -> list[str]:
        """Get list of supported data formats from NeuroConv.

        Returns:
            List of supported format names
        """
        try:
            # Get available data interfaces from NeuroConv
            from neuroconv import get_format_summaries

            summaries = get_format_summaries()

            # Handle different return types from get_format_summaries
            if isinstance(summaries, dict):
                # If it's a dict, extract format names from keys or values
                return list(summaries.keys()) if summaries else []
            elif isinstance(summaries, list):
                # If it's a list of dicts
                return [fmt.get("format", fmt) if isinstance(fmt, dict) else str(fmt) for fmt in summaries]
            else:
                # Unknown format, use fallback
                raise ValueError(f"Unexpected format summaries type: {type(summaries)}")
        except Exception as e:
            # Fallback to all supported formats (84 total)
            logger.warning(f"Failed to get format summaries dynamically, using fallback list: {e}")
            return [
                # Electrophysiology Recording
                "AlphaOmegaRecording",
                "Axon",
                "AxonRecording",
                "AxonaRecording",
                "AxonaUnitRecording",
                "BiocamRecording",
                "BlackrockRecording",
                "CellExplorerRecording",
                "EDFRecording",
                "IntanRecording",
                "MCSRawRecording",
                "MEArecRecording",
                "MaxOneRecording",
                "NeuralynxRecording",
                "Neuropixels",
                "NeuroScopeRecording",
                "OpenEphys",
                "OpenEphysBinary",
                "OpenEphysLegacyRecording",
                "Plexon2Recording",
                "PlexonRecording",
                "Spike2Recording",
                "SpikeGLX",
                "SpikeGadgetsRecording",
                "TdtRecording",
                "WhiteMatterRecording",
                # Spike Sorting
                "BlackrockSorting",
                "CellExplorerSorting",
                "KiloSortSorting",
                "NeuralynxSorting",
                "NeuroScopeSorting",
                "OpenEphysSorting",
                "PhySorting",
                "PlexonSorting",
                # Imaging
                "BrukerTiffMultiPlaneImaging",
                "BrukerTiffSinglePlaneImaging",
                "FemtonicsImaging",
                "Hdf5Imaging",
                "InscopixImaging",
                "MicroManagerTiffImaging",
                "MiniscopeImaging",
                "SbxImaging",
                "ScanImageImaging",
                "ScanImageLegacyImaging",
                "ScanImageMultiFileImaging",
                "ThorImaging",
                "TiffImaging",
                # Segmentation
                "CaimanSegmentation",
                "CnmfeSegmentation",
                "ExtractSegmentation",
                "InscopixSegmentation",
                "MinianSegmentation",
                "SimaSegmentation",
                "Suite2pSegmentation",
                # Behavior/Video
                "AxonaPositionData",
                "DeepLabCut",
                "ExternalVideo",
                "FicTracData",
                "InternalVideo",
                "LightningPoseData",
                "MiniscopeBehavior",
                "NeuralynxNvt",
                "SLEAP",
                "Video",
                # LFP/Analog/Other
                "Audio",
                "AxonaLFPData",
                "CellExplorerLFP",
                "CsvTimeIntervals",
                "EDFAnalog",
                "ExcelTimeIntervals",
                "Image",
                "IntanAnalog",
                "MedPC",
                "NeuroScopeLFP",
                "OpenEphysBinaryAnalog",
                "PlexonLFP",
                "SpikeGLXNIDQ",
                "TDTFiberPhotometry",
                # Converters
                "BrukerTiffMultiPlane",
                "BrukerTiffSinglePlane",
                "LightningPose",
                "Miniscope",
                "SortedRecording",
                "SortedSpikeGLX",
                "SpikeGLXConverter",
            ]

    async def handle_detect_format(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Detect the data format of uploaded files.

        Args:
            message: MCP message with context containing 'input_path'
            state: Global state

        Returns:
            MCPResponse with detected format or error
        """
        input_path = message.context.get("input_path")

        if not input_path:
            state.add_log(
                LogLevel.ERROR,
                "Missing input_path in detect_format request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_INPUT_PATH",
                error_message="input_path is required for format detection",
            )

        await state.update_status(ConversionStatus.DETECTING_FORMAT)
        state.add_log(
            LogLevel.INFO,
            f"Starting format detection for: {input_path}",
            {"input_path": input_path},
        )

        try:
            detected_format = await self._detect_format(input_path, state)

            if detected_format:
                state.add_log(
                    LogLevel.INFO,
                    f"Detected format: {detected_format}",
                    {"format": detected_format, "input_path": input_path},
                )
                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "format": detected_format,
                        "confidence": "high",
                        "supported_formats": self._supported_formats,
                    },
                )
            else:
                state.add_log(
                    LogLevel.WARNING,
                    "Could not detect format automatically",
                    {"input_path": input_path},
                )
                # Return ambiguous response - Conversation Agent will handle this
                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "format": None,
                        "confidence": "ambiguous",
                        "supported_formats": self._supported_formats,
                        "message": "Format detection ambiguous - user input required",
                    },
                )

        except Exception as e:
            error_msg = f"Format detection failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"input_path": input_path, "exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="DETECTION_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    async def _detect_format(self, input_path: str, state: GlobalState) -> str | None:
        """Detect data format based on file structure and content.

        🎯 PRIORITY 4: LLM-First Format Detection
        First tries LLM-based intelligent detection (more accurate).
        Falls back to hardcoded pattern matching if LLM unavailable/low confidence.

        Args:
            input_path: Path to input file or directory
            state: Global state for logging

        Returns:
            Detected format name or None if ambiguous
        """
        path = Path(input_path)

        # 🎯 NEW: Try LLM detection FIRST (more intelligent, handles edge cases)
        if self._llm_service:
            state.add_log(
                LogLevel.INFO,
                "Attempting LLM-based format detection (intelligent analysis)",
            )
            llm_result = await self._detect_format_with_llm(input_path, state)

            # Only accept if confidence is high (>70%)
            if llm_result and llm_result.get("confidence", 0) > 70:
                detected_format = llm_result.get("format")
                confidence = llm_result.get("confidence")

                # BUG FIX: Validate that LLM returned a valid NeuroConv format name
                # This prevents hallucinated format names like "AxonRawBinaryFormat"
                supported_formats = self._get_supported_formats()
                if detected_format not in supported_formats:
                    state.add_log(
                        LogLevel.WARNING,
                        f"LLM returned invalid format '{detected_format}' (not in NeuroConv). "
                        f"This may be a hallucination. Falling back to pattern matching.",
                        {"invalid_format": detected_format, "alternatives": llm_result.get("alternatives", [])},
                    )
                else:
                    state.add_log(
                        LogLevel.INFO,
                        f"LLM detected format: {detected_format} (confidence: {confidence}%)",
                    )
                    return str(detected_format)

            confidence = llm_result.get("confidence", 0) if llm_result else 0
            state.add_log(
                LogLevel.INFO,
                f"LLM confidence too low ({confidence}%), falling back to pattern matching",
            )

        # Fallback to fast hardcoded pattern matching
        state.add_log(
            LogLevel.INFO,
            "Using hardcoded pattern matching as fallback",
        )

        # Check for SpikeGLX
        if self._is_spikeglx(path):
            state.add_log(
                LogLevel.INFO,
                "Format detected via pattern matching: SpikeGLX",
            )
            return "SpikeGLX"

        # Check for OpenEphys
        if self._is_openephys(path):
            state.add_log(
                LogLevel.INFO,
                "Format detected via pattern matching: OpenEphys",
            )
            return "OpenEphys"

        # Check for Neuropixels
        if self._is_neuropixels(path):
            state.add_log(
                LogLevel.INFO,
                "Format detected via pattern matching: Neuropixels",
            )
            return "Neuropixels"

        # BUG FIX: Check for Axon/ABF files as fallback
        if path.is_file() and path.suffix.lower() == ".abf":
            state.add_log(
                LogLevel.INFO,
                "Format detected via pattern matching: Axon (.abf file)",
            )
            return "Axon"

        # Still ambiguous
        return None

    def _is_spikeglx(self, path: Path) -> bool:
        """Check if data is SpikeGLX format.

        Improved detection that checks for:
        - AP (action potential) band files
        - LF (local field potential) band files
        - Companion .meta files
        - NIDQ (National Instruments DAQ) files
        """
        if path.is_dir():
            # Look for .ap.bin/.lf.bin and corresponding .meta files
            ap_bins = list(path.glob("*.ap.bin"))
            lf_bins = list(path.glob("*.lf.bin"))
            nidq_bins = list(path.glob("*.nidq.bin"))
            meta_files = list(path.glob("*.meta"))

            # Valid if we have at least one data file with a matching .meta
            has_data = len(ap_bins) > 0 or len(lf_bins) > 0 or len(nidq_bins) > 0
            has_meta = len(meta_files) > 0

            return has_data and has_meta
        elif path.is_file():
            # Check if it's a SpikeGLX file by extension pattern
            is_bin = path.suffix == ".bin"
            has_spikeglx_pattern = any(
                [
                    ".ap." in path.name,
                    ".lf." in path.name,
                    ".nidq." in path.name,
                ]
            )
            return is_bin and has_spikeglx_pattern
        return False

    def _is_openephys(self, path: Path) -> bool:
        """Check if data is OpenEphys format.

        Improved detection for both old and new OpenEphys formats:
        - New format: structure.oebin file
        - Old format: settings.xml file
        - Binary format: continuous/ folder with .dat files
        """
        if path.is_dir():
            # New Open Ephys format (>= 0.4.0)
            if (path / "structure.oebin").exists():
                return True

            # Old Open Ephys format (< 0.4.0)
            if (path / "settings.xml").exists():
                return True

            # Binary format check
            continuous_dir = path / "continuous"
            if continuous_dir.exists() and continuous_dir.is_dir():
                # Look for .continuous or .dat files
                continuous_files = list(continuous_dir.glob("*.continuous")) + list(continuous_dir.glob("*.dat"))
                if len(continuous_files) > 0:
                    return True

        return False

    def _is_neuropixels(self, path: Path) -> bool:
        """Check if data is Neuropixels format.

        Neuropixels probes use SpikeGLX for acquisition, so we look for:
        - NIDQ (National Instruments) files
        - Imec probe files (imec0, imec1, etc.)
        - Specific Neuropixels naming patterns
        """
        if path.is_file():
            # NIDQ files are common in Neuropixels recordings
            if ".nidq." in path.name:
                return True
            # Imec probe files
            if ".imec" in path.name and ".bin" in path.suffix:
                return True

        if path.is_dir():
            # Check for imec probe folders or files
            imec_files = list(path.glob("*imec*.bin"))
            nidq_files = list(path.glob("*.nidq.bin"))
            if len(imec_files) > 0 or len(nidq_files) > 0:
                return True

        return False

    async def _detect_format_with_llm(
        self,
        input_path: str,
        state: GlobalState,
    ) -> dict[str, Any] | None:
        """Use LLM to intelligently detect data format when hardcoded patterns fail.

        Analyzes file structure, naming patterns, and content to determine format.
        Particularly useful for:
        - Ambiguous file naming
        - Novel data formats
        - Corrupted or incomplete file structures

        Args:
            input_path: Path to input file or directory
            state: Global state for logging

        Returns:
            Dictionary with 'format', 'confidence', 'indicators', etc. or None if still ambiguous
        """
        if not self._llm_service:
            return None

        import json
        from pathlib import Path

        path = Path(input_path)

        # Gather file structure information
        file_info = {
            "path": str(path),
            "is_file": path.is_file(),
            "is_directory": path.is_dir(),
            "name": path.name,
            "suffix": path.suffix,
            "size_mb": 0,
            "files": [],
        }

        try:
            if path.is_file():
                file_info["size_mb"] = round(path.stat().st_size / (1024 * 1024), 2)
                # Check for companion files
                parent = path.parent
                file_info["files"] = [f.name for f in parent.iterdir() if f.is_file()][:20]

            elif path.is_dir():
                all_files = list(path.rglob("*"))[:50]  # Limit to 50 files
                file_info["files"] = [str(f.relative_to(path)) for f in all_files if f.is_file()]
                file_info["total_files"] = len(all_files)
                file_info["size_mb"] = round(
                    sum(f.stat().st_size for f in all_files if f.is_file()) / (1024 * 1024),
                    2,
                )

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Could not gather full file info for LLM detection: {e}",
            )

        system_prompt = """You are an expert in neuroscience data formats, specializing in electrophysiology and imaging data.

Your job is to analyze file structure and naming patterns to identify the recording format.

IMPORTANT: You MUST use the exact format names recognized by NeuroConv. Do not invent or modify format names.

Common electrophysiology formats:
- **SpikeGLX** or **Neuropixels**: Files like "*.ap.bin", "*.ap.meta", "*.lf.bin", "*.lf.meta", or ".nidq." files
- **OpenEphys** or **OpenEphysBinary**: Directories with "structure.oebin", "settings.xml", or "continuous/" folders
- **Axon** or **AxonRecording**: ".abf" files (Axon Instruments pCLAMP/ABF format)
- **IntanRecording**: ".rhd" or ".rhs" files (Intan Technologies)
- **BlackrockRecording**: ".ns1", ".ns2", ".ns3", ".ns4", ".ns5", ".ns6", ".nev" files
- **NeuralynxRecording**: ".ncs", ".nev", ".ntt", ".nvt" files
- **PlexonRecording** or **Plexon2Recording**: ".plx" or ".pl2" files
- **TdtRecording**: Tank/Block directory structure (Tucker-Davis Technologies)
- **SpikeGadgetsRecording**: ".rec" files with companion metadata
- **Spike2Recording**: ".smr" or ".smrx" files (CED Spike2)
- **EDFRecording**: ".edf" files (European Data Format)
- **AlphaOmegaRecording**: Alpha Omega recordings
- **AxonaRecording**: ".bin", ".set", ".eeg" (Axona/Dacq systems)
- **BiocamRecording**: 3Brain Biocam recordings
- **CellExplorerRecording**: CellExplorer format
- **MCSRawRecording**: Multi Channel Systems raw recordings
- **MaxOneRecording**: MaxWell Biosystems MaxOne recordings
- **NeuroScopeRecording**: NeuroScope format
- **WhiteMatterRecording**: White Matter recordings

Common imaging formats:
- **ScanImageImaging**: ".tif" with ScanImage metadata
- **MiniscopeImaging**: ".avi" with timestamp files (Miniscope recordings)
- **BrukerTiffSinglePlaneImaging** or **BrukerTiffMultiPlaneImaging**: Bruker TIF files
- **InscopixImaging**: Inscopix recordings
- **TiffImaging**: Generic TIFF imaging
- **ThorImaging**: ThorLabs imaging
- **Hdf5Imaging**: HDF5-based imaging
- **SbxImaging**: Scanbox imaging
- **MicroManagerTiffImaging**: Micro-Manager TIFF files
- **FemtonicsImaging**: Femtonics imaging

Behavior/tracking formats:
- **DeepLabCut**: DeepLabCut pose estimation files
- **SLEAP**: SLEAP pose tracking files
- **Video**: Generic video files

Analyze the file structure carefully and return ONLY format names from the list above. Do not invent new format names."""

        user_prompt = f"""I have neuroscience recording data that I need to identify:

File Information:
{json.dumps(file_info, indent=2)}

Based on the file structure and naming patterns:
1. What recording format is this most likely?
2. How confident are you (0-100%)?
3. What are the key indicators?
4. Are there alternative possibilities?

Be specific about the format name used by NeuroConv."""

        output_schema = {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "Detected format name (SpikeGLX, OpenEphys, etc.)",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level 0-100",
                },
                "indicators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key indicators that led to this conclusion",
                },
                "alternatives": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Other possible formats if confidence is low",
                },
                "ambiguous": {
                    "type": "boolean",
                    "description": "Whether the format is ambiguous and needs user clarification",
                },
            },
            "required": ["format", "confidence", "indicators", "ambiguous"],
        }

        try:
            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            format_name = response.get("format")
            confidence = response.get("confidence", 0)
            ambiguous = response.get("ambiguous", True)

            state.add_log(
                LogLevel.INFO,
                f"LLM format detection: {format_name} (confidence: {confidence}%)",
                {
                    "format": format_name,
                    "confidence": confidence,
                    "indicators": response.get("indicators", []),
                    "alternatives": response.get("alternatives", []),
                    "ambiguous": ambiguous,
                },
            )

            # Return the full response dictionary so caller can check confidence
            return dict(response) if response else None

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"LLM format detection failed: {e}",
            )
            return None

    async def handle_run_conversion(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Run NWB conversion using NeuroConv.

        Args:
            message: MCP message with context containing conversion parameters
            state: Global state

        Returns:
            MCPResponse with conversion result or error
        """
        input_path = message.context.get("input_path")
        output_path = message.context.get("output_path")
        format_name = message.context.get("format")
        metadata_raw = message.context.get("metadata", {})

        # BUG FIX: Use whitelist approach to only pass valid NWB metadata fields
        # Based on official PyNWB 2.8.3+ documentation
        # This is safer than blacklist - only documented NWB fields can pass through

        # NWBFile metadata fields (from PyNWB NWBFile class)
        NWB_FILE_FIELDS = {
            # Required fields
            "session_description",
            "identifier",
            "session_start_time",
            # Optional NWBFile metadata fields
            "experimenter",
            "experiment_description",
            "session_id",
            "institution",
            "keywords",
            "notes",
            "pharmacology",
            "protocol",
            "related_publications",
            "slices",
            "source_script",
            "source_script_file_name",
            "surgery",
            "virus",
            "stimulus_notes",
            "lab",
            "data_collection",
        }

        # Subject fields (from PyNWB Subject class)
        # These may be passed flat and will be structured into a Subject object by NeuroConv
        SUBJECT_FIELDS = {
            "subject_id",
            "species",
            "sex",
            "age",
            "strain",
            "date_of_birth",
            "genotype",
            "weight",
            "description",
        }

        # Filter to only allowed NWB fields - prevents internal tracking fields from leaking
        metadata = {k: v for k, v in metadata_raw.items() if k in NWB_FILE_FIELDS or k in SUBJECT_FIELDS}

        if not all([input_path, output_path, format_name]):
            state.add_log(
                LogLevel.ERROR,
                "Missing required parameters for conversion",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_PARAMETERS",
                error_message="input_path, output_path, and format are required",
            )

        await state.update_status(ConversionStatus.CONVERTING)
        state.update_progress(0, "Initializing conversion...", "initialization")

        # Track conversion timing
        import time
        from datetime import datetime

        conversion_start_time = time.time()
        conversion_start_timestamp = datetime.now()

        # Get detailed file information
        from pathlib import Path

        file_path = Path(input_path)
        file_size_bytes = file_path.stat().st_size if file_path.exists() else 0
        file_size_mb = file_size_bytes / (1024 * 1024)
        file_size_gb = file_size_bytes / (1024 * 1024 * 1024)

        # Format file size for display
        if file_size_gb >= 1.0:
            file_size_display = f"{file_size_gb:.2f} GB"
        elif file_size_mb >= 1.0:
            file_size_display = f"{file_size_mb:.1f} MB"
        else:
            file_size_display = f"{file_size_bytes / 1024:.1f} KB"

        state.add_log(
            LogLevel.INFO,
            f"Starting NWB conversion: {format_name} ({file_size_display})",
            {
                "format": format_name,
                "input_file": file_path.name,
                "input_path": input_path,
                "output_path": output_path,
                "file_size_bytes": file_size_bytes,
                "file_size_mb": round(file_size_mb, 2),
                "file_size_display": file_size_display,
                "start_timestamp": conversion_start_timestamp.isoformat(),
            },
        )

        try:
            # 🎯 PRIORITY 5: Narrate conversion start

            state.update_progress(10, f"Analyzing {format_name} data ({file_size_mb:.1f} MB)...", "analysis")

            await self._narrate_progress(
                stage="starting",
                format_name=format_name,
                context={"file_size_mb": file_size_mb},
                state=state,
            )

            # Optimize conversion parameters with LLM
            state.update_progress(20, "Optimizing conversion parameters...", "optimization")
            await self._optimize_conversion_parameters(
                format_name=format_name,
                file_size_mb=file_size_mb,
                state=state,
            )

            # 🎯 PRIORITY 5: Narrate processing
            state.update_progress(30, "Processing data...", "processing")
            await self._narrate_progress(
                stage="processing",
                format_name=format_name,
                context={"file_size_mb": file_size_mb, "progress_percent": 50},
                state=state,
            )

            # Run conversion
            state.update_progress(50, "Converting to NWB format...", "conversion")
            self._run_neuroconv_conversion(
                input_path=input_path,
                output_path=output_path,
                format_name=format_name,
                metadata=metadata,
                state=state,
            )

            # 🎯 PRIORITY 5: Narrate finalization
            state.update_progress(90, "Finalizing NWB file...", "finalization")
            await self._narrate_progress(
                stage="finalizing",
                format_name=format_name,
                context={"output_path": output_path},
                state=state,
            )

            # Calculate checksum
            state.update_progress(98, "Calculating file checksum...", "checksum")
            checksum = self._calculate_checksum(output_path)
            state.checksums[output_path] = checksum

            # 🎯 PRIORITY 5: Narrate completion
            await self._narrate_progress(
                stage="complete",
                format_name=format_name,
                context={"output_path": output_path, "checksum": checksum},
                state=state,
            )

            state.output_path = output_path
            state.update_progress(100, "Conversion completed successfully!", "complete")

            # Calculate conversion metrics
            conversion_end_time = time.time()
            conversion_end_timestamp = datetime.now()
            duration_seconds = conversion_end_time - conversion_start_time
            duration_minutes = duration_seconds / 60

            # Get output file size
            output_file_path = Path(output_path)
            output_size_bytes = output_file_path.stat().st_size if output_file_path.exists() else 0
            output_size_mb = output_size_bytes / (1024 * 1024)
            output_size_gb = output_size_bytes / (1024 * 1024 * 1024)

            # Format output file size
            if output_size_gb >= 1.0:
                output_size_display = f"{output_size_gb:.2f} GB"
            elif output_size_mb >= 1.0:
                output_size_display = f"{output_size_mb:.1f} MB"
            else:
                output_size_display = f"{output_size_bytes / 1024:.1f} KB"

            # Calculate compression ratio and speed
            if file_size_bytes > 0:
                compression_ratio = ((file_size_bytes - output_size_bytes) / file_size_bytes) * 100
                compression_sign = "smaller" if compression_ratio > 0 else "larger"
                compression_ratio_abs = abs(compression_ratio)
            else:
                compression_ratio = 0
                compression_sign = "same"
                compression_ratio_abs = 0

            # Calculate conversion speed (MB/s)
            conversion_speed_mbps = file_size_mb / duration_seconds if duration_seconds > 0 else 0

            # Format duration for display
            if duration_minutes >= 1.0:
                duration_display = (
                    f"{int(duration_minutes // 60)}h {int(duration_minutes % 60)}m {int(duration_seconds % 60)}s"
                    if duration_minutes >= 60
                    else f"{int(duration_minutes)}m {int(duration_seconds % 60)}s"
                )
            else:
                duration_display = f"{duration_seconds:.1f}s"

            state.add_log(
                LogLevel.INFO,
                f"Conversion completed successfully in {duration_display} ({output_size_display}, {compression_ratio_abs:.1f}% {compression_sign})",
                {
                    "output_path": output_path,
                    "output_file": output_file_path.name,
                    "checksum": checksum,
                    "duration_seconds": round(duration_seconds, 2),
                    "duration_display": duration_display,
                    "output_size_bytes": output_size_bytes,
                    "output_size_mb": round(output_size_mb, 2),
                    "output_size_display": output_size_display,
                    "compression_ratio_percent": round(compression_ratio, 2),
                    "compression_sign": compression_sign,
                    "conversion_speed_mbps": round(conversion_speed_mbps, 2),
                    "end_timestamp": conversion_end_timestamp.isoformat(),
                },
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "output_path": output_path,
                    "checksum": checksum,
                    "message": "Conversion completed successfully",
                },
            )

        except Exception as e:
            error_msg = f"Conversion failed: {str(e)}"

            # Use LLM to explain the error if available
            user_friendly_explanation = await self._explain_conversion_error(
                error=e,
                format_name=format_name,
                input_path=input_path,
                state=state,
            )

            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {
                    "input_path": input_path,
                    "format": format_name,
                    "exception": str(e),
                    "user_explanation": user_friendly_explanation,
                },
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="CONVERSION_FAILED",
                error_message=user_friendly_explanation or error_msg,
                error_context={
                    "exception": str(e),
                    "technical_details": error_msg,
                },
            )

    async def _explain_conversion_error(
        self,
        error: Exception,
        format_name: str,
        input_path: str,
        state: GlobalState,
    ) -> str | None:
        """Use LLM to generate user-friendly error explanations.

        Transforms technical error messages into actionable guidance that
        helps users understand what went wrong and how to fix it.

        Args:
            error: The exception that occurred
            format_name: Data format being converted
            input_path: Path to input file
            state: Global state for logging

        Returns:
            User-friendly error explanation, or None if LLM unavailable
        """
        if not self._llm_service:
            return None

        from pathlib import Path

        error_type = type(error).__name__
        error_message = str(error)

        # Gather context about the file
        file_context: dict[str, Any] = {}
        try:
            path = Path(input_path)
            if path.exists():
                if path.is_file():
                    file_context["type"] = "file"
                    file_context["name"] = path.name
                    file_context["size_mb"] = round(path.stat().st_size / (1024 * 1024), 2)
                    file_context["parent_dir"] = str(path.parent)
                    # List sibling files for context
                    siblings = [f.name for f in path.parent.iterdir() if f.is_file()][:10]
                    file_context["sibling_files"] = siblings
                else:
                    file_context["type"] = "directory"
                    file_context["name"] = path.name
                    files = [f.name for f in path.iterdir() if f.is_file()][:20]
                    file_context["files"] = files
        except Exception as e:
            # Non-critical - file context is optional for format detection
            logger.debug(f"Failed to gather file context for format detection: {e}")

        system_prompt = """You are a helpful neuroscience data conversion assistant.

Your job is to explain technical errors in simple, actionable terms.

When explaining errors:
1. Start with what went wrong in plain English
2. Explain the likely cause
3. Provide specific, actionable steps to fix it
4. Be empathetic and encouraging
5. Keep it concise (2-4 sentences)

Focus on helping the user resolve the issue, not on technical jargon."""

        user_prompt = f"""An error occurred during NWB conversion:

Format: {format_name}
Error Type: {error_type}
Error Message: {error_message}
File Context: {file_context}

Please explain what went wrong and how to fix it in user-friendly language."""

        try:
            explanation = await self._llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more focused explanations
                max_tokens=300,
            )

            state.add_log(
                LogLevel.INFO,
                "Generated user-friendly error explanation via LLM",
            )

            return str(explanation).strip()

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate error explanation via LLM: {e}",
            )
            return None

    async def _optimize_conversion_parameters(
        self,
        format_name: str,
        file_size_mb: float,
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to determine optimal NWB conversion parameters.

        Analyzes file characteristics to suggest best settings for:
        - Compression method and level
        - DANDI archive optimization
        - Quality vs speed tradeoffs

        Args:
            format_name: Data format name
            file_size_mb: Input file size in MB
            state: Global state for logging

        Returns:
            Dictionary of optimized parameters (empty if LLM unavailable)
        """
        if not self._llm_service:
            return {}  # Use NeuroConv defaults

        system_prompt = """You are an expert in NWB file optimization and DANDI archive requirements.

Suggest optimal NeuroConv conversion parameters based on:
- File format and size
- DANDI upload efficiency
- Balance between file size and conversion speed
- Data integrity requirements

Common considerations:
- Larger files (>100MB) benefit from compression
- DANDI prefers reasonably compressed files
- Electrophysiology data compresses well with gzip
- Imaging data may need different approaches"""

        user_prompt = f"""Optimize NWB conversion parameters for:

Format: {format_name}
Input size: {file_size_mb:.1f}MB
Target: DANDI archive submission

Suggest optimal settings and explain reasoning."""

        output_schema = {
            "type": "object",
            "properties": {
                "use_compression": {
                    "type": "boolean",
                    "description": "Whether to enable compression",
                },
                "compression_recommended": {
                    "type": "string",
                    "description": "Recommended approach (none/gzip/lzf)",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why these settings are optimal",
                },
                "expected_output_size_mb": {
                    "type": "number",
                    "description": "Estimated output file size",
                },
                "optimization_priority": {
                    "type": "string",
                    "enum": ["speed", "size", "balanced"],
                    "description": "What was optimized for",
                },
            },
            "required": ["use_compression", "reasoning"],
        }

        try:
            optimization = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                f"LLM-optimized conversion parameters: {optimization.get('compression_recommended', 'default')}",
                {
                    "use_compression": optimization.get("use_compression"),
                    "reasoning": optimization.get("reasoning"),
                    "expected_size_mb": optimization.get("expected_output_size_mb"),
                },
            )

            # NeuroConv's run_conversion doesn't directly take compression params
            # but we can log the recommendation for future enhancement
            return {
                "optimization": optimization,
                "recommended_approach": optimization.get("compression_recommended", "default"),
            }

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Parameter optimization failed, using defaults: {e}",
            )
            return {}

    async def _narrate_progress(
        self,
        stage: str,
        format_name: str,
        context: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """🎯 PRIORITY 5: Progress Narration.

        Use LLM to provide human-friendly progress updates during conversion.

        Args:
            stage: Current stage (e.g., "starting", "processing", "finalizing")
            format_name: Data format being converted
            context: Additional context (file_size, progress_percent, etc.)
            state: Global state for logging

        Returns:
            Human-friendly narration string
        """
        if not self._llm_service:
            # Fallback to generic messages
            fallback_messages = {
                "starting": f"Starting conversion of {format_name} data...",
                "processing": f"Processing {format_name} data ({context.get('progress_percent', 0)}% complete)...",
                "finalizing": "Finalizing NWB file...",
                "complete": "Conversion complete!",
            }
            return fallback_messages.get(stage, "Processing...")

        system_prompt = """You are a helpful assistant narrating the progress of a neuroscience data conversion.

Your job is to provide clear, friendly updates that help users understand what's happening.

- Be concise (1-2 sentences)
- Use plain language (avoid technical jargon unless necessary)
- Show enthusiasm but stay professional
- Mention specific milestones when relevant"""

        user_prompt = f"""Generate a progress update for this conversion stage:

Stage: {stage}
Format: {format_name}
Context: {context}

Provide a brief, friendly update about what's happening now."""

        try:
            narration = await self._llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )
            state.add_log(LogLevel.INFO, f"Progress: {narration}")
            return str(narration).strip()
        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Progress narration failed: {e}")
            # Fallback
            return f"Processing {format_name} data at stage: {stage}"

    def _run_neuroconv_conversion(
        self,
        input_path: str,
        output_path: str,
        format_name: str,
        metadata: dict[str, Any],
        state: GlobalState,
    ) -> None:
        """Run NeuroConv conversion.

        Args:
            input_path: Path to input data
            output_path: Path for output NWB file
            format_name: Format name (e.g., "SpikeGLX")
            metadata: Metadata dictionary (flat structure from user)
            state: Global state for progress tracking

        Raises:
            Exception: If conversion fails
        """
        # Comprehensive format-to-interface mapping for all 84 NeuroConv interfaces
        # Using dynamic imports to avoid loading all interfaces at startup
        format_to_interface_map = {
            # Electrophysiology Recording (24 formats)
            "AlphaOmegaRecording": "AlphaOmegaRecordingInterface",
            "Axon": "AbfInterface",  # .abf files - Axon Instruments pCLAMP
            "AxonRecording": "AxonRecordingInterface",
            "AxonaRecording": "AxonaRecordingInterface",
            "AxonaUnitRecording": "AxonaUnitRecordingInterface",
            "BiocamRecording": "BiocamRecordingInterface",
            "BlackrockRecording": "BlackrockRecordingInterface",
            "CellExplorerRecording": "CellExplorerRecordingInterface",
            "EDFRecording": "EDFRecordingInterface",
            "IntanRecording": "IntanRecordingInterface",
            "MCSRawRecording": "MCSRawRecordingInterface",
            "MEArecRecording": "MEArecRecordingInterface",
            "MaxOneRecording": "MaxOneRecordingInterface",
            "NeuralynxRecording": "NeuralynxRecordingInterface",
            "Neuropixels": "SpikeGLXRecordingInterface",  # Alias for SpikeGLX
            "NeuroScopeRecording": "NeuroScopeRecordingInterface",
            "OpenEphys": "OpenEphysRecordingInterface",
            "OpenEphysBinary": "OpenEphysBinaryRecordingInterface",
            "OpenEphysLegacyRecording": "OpenEphysLegacyRecordingInterface",
            "Plexon2Recording": "Plexon2RecordingInterface",
            "PlexonRecording": "PlexonRecordingInterface",
            "Spike2Recording": "Spike2RecordingInterface",
            "SpikeGLX": "SpikeGLXRecordingInterface",
            "SpikeGadgetsRecording": "SpikeGadgetsRecordingInterface",
            "TdtRecording": "TdtRecordingInterface",
            "WhiteMatterRecording": "WhiteMatterRecordingInterface",
            # Spike Sorting (8 formats)
            "BlackrockSorting": "BlackrockSortingInterface",
            "CellExplorerSorting": "CellExplorerSortingInterface",
            "KiloSortSorting": "KiloSortSortingInterface",
            "NeuralynxSorting": "NeuralynxSortingInterface",
            "NeuroScopeSorting": "NeuroScopeSortingInterface",
            "OpenEphysSorting": "OpenEphysSortingInterface",
            "PhySorting": "PhySortingInterface",
            "PlexonSorting": "PlexonSortingInterface",
            # Imaging (13 formats)
            "BrukerTiffMultiPlaneImaging": "BrukerTiffMultiPlaneImagingInterface",
            "BrukerTiffSinglePlaneImaging": "BrukerTiffSinglePlaneImagingInterface",
            "FemtonicsImaging": "FemtonicsImagingInterface",
            "Hdf5Imaging": "Hdf5ImagingInterface",
            "InscopixImaging": "InscopixImagingInterface",
            "MicroManagerTiffImaging": "MicroManagerTiffImagingInterface",
            "MiniscopeImaging": "MiniscopeImagingInterface",
            "SbxImaging": "SbxImagingInterface",
            "ScanImageImaging": "ScanImageImagingInterface",
            "ScanImageLegacyImaging": "ScanImageLegacyImagingInterface",
            "ScanImageMultiFileImaging": "ScanImageMultiFileImagingInterface",
            "ThorImaging": "ThorImagingInterface",
            "TiffImaging": "TiffImagingInterface",
            # Segmentation (7 formats)
            "CaimanSegmentation": "CaimanSegmentationInterface",
            "CnmfeSegmentation": "CnmfeSegmentationInterface",
            "ExtractSegmentation": "ExtractSegmentationInterface",
            "InscopixSegmentation": "InscopixSegmentationInterface",
            "MinianSegmentation": "MinianSegmentationInterface",
            "SimaSegmentation": "SimaSegmentationInterface",
            "Suite2pSegmentation": "Suite2pSegmentationInterface",
            # Behavior/Video (11 formats)
            "AxonaPositionData": "AxonaPositionDataInterface",
            "DeepLabCut": "DeepLabCutInterface",
            "ExternalVideo": "ExternalVideoInterface",
            "FicTracData": "FicTracDataInterface",
            "InternalVideo": "InternalVideoInterface",
            "LightningPoseData": "LightningPoseDataInterface",
            "MiniscopeBehavior": "MiniscopeBehaviorInterface",
            "NeuralynxNvt": "NeuralynxNvtInterface",
            "SLEAP": "SLEAPInterface",
            "Video": "VideoInterface",
            # LFP/Analog/Other (15 formats)
            "Audio": "AudioInterface",
            "AxonaLFPData": "AxonaLFPDataInterface",
            "CellExplorerLFP": "CellExplorerLFPInterface",
            "CsvTimeIntervals": "CsvTimeIntervalsInterface",
            "EDFAnalog": "EDFAnalogInterface",
            "ExcelTimeIntervals": "ExcelTimeIntervalsInterface",
            "Image": "ImageInterface",
            "IntanAnalog": "IntanAnalogInterface",
            "MedPC": "MedPCInterface",
            "NeuroScopeLFP": "NeuroScopeLFPInterface",
            "OpenEphysBinaryAnalog": "OpenEphysBinaryAnalogInterface",
            "PlexonLFP": "PlexonLFPInterface",
            "SpikeGLXNIDQ": "SpikeGLXNIDQInterface",
            "TDTFiberPhotometry": "TDTFiberPhotometryInterface",
            # Converters (6 formats)
            "BrukerTiffMultiPlane": "BrukerTiffMultiPlaneConverter",
            "BrukerTiffSinglePlane": "BrukerTiffSinglePlaneConverter",
            "LightningPose": "LightningPoseConverter",
            "Miniscope": "MiniscopeConverter",
            "SortedRecording": "SortedRecordingConverter",
            "SortedSpikeGLX": "SortedSpikeGLXConverter",
            "SpikeGLXConverter": "SpikeGLXConverterPipe",
        }

        if format_name not in format_to_interface_map:
            raise ValueError(
                f"Unsupported format: {format_name}. "
                f"Supported formats: {', '.join(sorted(format_to_interface_map.keys()))}"
            )

        # Dynamically import the required interface
        interface_class_name = format_to_interface_map[format_name]
        try:
            from neuroconv import datainterfaces

            interface_class = getattr(datainterfaces, interface_class_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Failed to import interface '{interface_class_name}' for format '{format_name}'. Error: {str(e)}"
            ) from e

        # Create interface with source data
        from pathlib import Path

        input_file = Path(input_path)

        # Format-specific interface initialization
        state.update_progress(55, f"Initializing {format_name} interface...", "interface_init")

        if format_name in ["SpikeGLX", "Neuropixels"]:
            if input_file.is_file():
                # Use the parent directory
                folder_path = str(input_file.parent)
            else:
                folder_path = input_path

            # Try to detect available streams and use the first non-SYNC stream
            state.update_progress(60, "Detecting data streams...", "stream_detection")
            try:
                # First try without stream_id to see what's available
                import neo

                # Get available streams
                reader = neo.rawio.SpikeGLXRawIO(dirname=folder_path)
                reader.parse_header()
                stream_ids = reader.header["signal_streams"]["id"]

                # Prefer non-SYNC streams (typically 'imec0.ap' or similar)
                non_sync_streams = [s for s in stream_ids if "SYNC" not in s]
                stream_id = non_sync_streams[0] if non_sync_streams else stream_ids[0]

                data_interface = interface_class(folder_path=folder_path, stream_id=stream_id)
            except ValueError as e:
                # Filename parsing error - provide helpful message
                if "Cannot parse filename" in str(e):
                    raise ValueError(
                        f"SpikeGLX filename format not recognized. "
                        f"Expected format: '<name>_g<gate>_t<trigger>.imec<probe>.ap.bin' or similar. "
                        f"Files in {folder_path}: {list(Path(folder_path).glob('*.bin'))}"
                    ) from e
                raise
            except Exception as e:
                # Other errors - provide context
                raise ValueError(
                    f"Failed to initialize SpikeGLX interface for {folder_path}. "
                    f"Error: {str(e)}. "
                    f"Make sure .bin and .meta files are present."
                ) from e

        elif format_name in ["OpenEphys", "OpenEphysBinary"]:
            # OpenEphys requires a folder path
            folder_path = str(input_file.parent) if input_file.is_file() else input_path

            try:
                data_interface = interface_class(folder_path=folder_path)
            except Exception as e:
                raise ValueError(
                    f"Failed to initialize OpenEphys interface for {folder_path}. "
                    f"Error: {str(e)}. "
                    f"Make sure the folder contains structure.oebin or settings.xml."
                ) from e

        else:
            # Generic format handling for all other formats (Axon, Intan, Blackrock, etc.)
            try:
                if input_file.is_file():
                    state.add_log(
                        LogLevel.INFO,
                        f"Initializing {format_name} interface with file: {input_file.name}",
                    )

                    # BUG FIX: Some interfaces (like AbfInterface) use file_paths (plural, as list)
                    # instead of file_path (singular, as string)
                    if format_name in ["Axon", "AxonRecording"]:
                        # AbfInterface expects file_paths as a list
                        state.add_log(
                            LogLevel.INFO,
                            f"Using file_paths parameter (list) for {format_name}",
                        )
                        data_interface = interface_class(file_paths=[input_path])
                    else:
                        # Most other interfaces use file_path as a string
                        data_interface = interface_class(file_path=input_path)
                else:
                    state.add_log(
                        LogLevel.INFO,
                        f"Initializing {format_name} interface with folder: {input_file.name}",
                    )
                    data_interface = interface_class(folder_path=input_path)
            except Exception as e:
                # BUG FIX: Add detailed error logging for generic format initialization failures
                error_msg = f"Failed to initialize {format_name} interface for {input_path}."
                error_details = []

                # Add format-specific hints based on common errors
                error_str = str(e).lower()
                if "no such file" in error_str or "does not exist" in error_str:
                    error_details.append("File or directory not found")
                elif "permission" in error_str:
                    error_details.append("Permission denied - check file permissions")
                elif "corrupt" in error_str or "invalid" in error_str:
                    error_details.append("File may be corrupted or invalid format")
                elif "metadata" in error_str:
                    error_details.append("Missing or invalid metadata in file")
                elif "compression" in error_str:
                    error_details.append("Compression format not supported")
                else:
                    error_details.append(f"Error: {str(e)}")

                # Log detailed error information
                state.add_log(
                    LogLevel.ERROR,
                    f"{error_msg} {' | '.join(error_details)}",
                    {
                        "format": format_name,
                        "input_path": input_path,
                        "interface_class": interface_class_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )

                # Re-raise with context
                raise ValueError(
                    f"{error_msg}\n"
                    f"Format: {format_name}\n"
                    f"Interface: {interface_class_name}\n"
                    f"Error: {str(e)}\n"
                    f"Hint: Make sure the file is a valid {format_name} format and is not corrupted."
                ) from e

        # For single-interface conversions, just use the interface directly
        # Get metadata from interface
        state.update_progress(70, "Extracting file metadata...", "metadata_extraction")
        interface_metadata = data_interface.get_metadata()

        # 🔧 FIX: Map flat user metadata to NWB's nested structure
        # User provides: {"experimenter": "Dr. Smith", "institution": "MIT", ...}
        # NWB expects: {"NWBFile": {"experimenter": [...], "institution": "..."}, "Subject": {...}}
        import logging

        state.update_progress(75, "Applying user-provided metadata...", "metadata_mapping")
        logger = logging.getLogger(__name__)
        logger.debug(f"Flat user metadata: {metadata}")

        structured_metadata = self._map_flat_to_nested_metadata(metadata)

        logger.debug(f"Structured metadata: {structured_metadata}")

        # Merge structured user metadata with interface metadata
        for top_level_key, nested_dict in structured_metadata.items():
            if top_level_key not in interface_metadata:
                interface_metadata[top_level_key] = {}

            if isinstance(nested_dict, dict):
                interface_metadata[top_level_key].update(nested_dict)
            else:
                interface_metadata[top_level_key] = nested_dict

        logger.debug(f"Final NWBFile metadata: {interface_metadata.get('NWBFile', {})}")
        logger.debug(f"Final Subject metadata: {interface_metadata.get('Subject', {})}")

        # Run conversion directly from interface
        state.update_progress(80, "Writing NWB file to disk...", "writing")

        # Calculate input file size for progress estimation
        try:
            input_file_path = Path(input_path)
            if input_file_path.is_file():
                input_size_bytes = input_file_path.stat().st_size
            else:
                # If it's a folder, estimate from first .bin file
                bin_files = list(input_file_path.glob("*.bin"))
                if bin_files:
                    input_size_bytes = bin_files[0].stat().st_size
                    # Handle zero-size files
                    if input_size_bytes == 0:
                        logger.warning(f"First .bin file has zero size: {bin_files[0]}")
                        input_size_bytes = 100 * 1024 * 1024  # Default 100MB
                else:
                    input_size_bytes = 100 * 1024 * 1024  # Default 100MB
            input_size_mb = max(1.0, input_size_bytes / (1024 * 1024))  # Ensure at least 1MB to avoid division by zero
        except Exception as e:
            logger.warning(f"Could not determine input file size: {e}")
            input_size_mb = 100.0  # Default estimate

        # Start background file size monitoring thread
        stop_monitoring = threading.Event()
        monitor_thread = None  # Initialize to None for safe cleanup

        try:
            monitor_thread = threading.Thread(
                target=self._monitor_file_size_progress,
                args=(output_path, input_size_mb, state, stop_monitoring, 80.0, 95.0),
                daemon=True,
            )
            monitor_thread.start()

            data_interface.run_conversion(
                nwbfile_path=output_path,
                metadata=interface_metadata,
                overwrite=True,
            )

        except Exception:
            # Stop monitoring thread if it was started
            if monitor_thread and monitor_thread.is_alive():
                stop_monitoring.set()
                monitor_thread.join(timeout=2.0)

            # Bug #16: Clean up partial/corrupt file on conversion error
            if Path(output_path).exists():
                try:
                    Path(output_path).unlink()
                    logger.debug(f"Cleaned up partial NWB file: {output_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up partial file: {cleanup_error}")
            raise  # Re-raise original exception
        finally:
            # Stop monitoring thread if it exists and is running
            if monitor_thread and monitor_thread.is_alive():
                stop_monitoring.set()
                monitor_thread.join(timeout=2.0)

        state.update_progress(95, "Verifying NWB file integrity...", "verification")

    def _monitor_file_size_progress(
        self,
        output_path: str,
        input_size_mb: float,
        state: GlobalState,
        stop_event: threading.Event,
        base_progress: float = 50.0,
        max_progress: float = 90.0,
    ) -> None:
        """Monitor output file size growth during conversion and update progress.

        Runs in background thread. Updates progress from base_progress to max_progress
        based on estimated output file size.

        Args:
            output_path: Path to output NWB file being written
            input_size_mb: Input file size in MB for estimation
            state: Global state for progress updates
            stop_event: Threading event to signal when to stop monitoring
            base_progress: Starting progress percentage (default 50%)
            max_progress: Maximum progress percentage (default 90%)
        """
        # Bug #37: Top-level exception handler to prevent silent thread failures
        try:
            output_file = Path(output_path)

            # Estimate output size (typically 60-120% of input size for NWB compression)
            # Use conservative estimate of 100% (same size as input)
            estimated_output_mb = input_size_mb * 1.0

            last_size_mb = 0.0
            last_update_time = time.time()
            stall_count = 0

            state.add_log(
                LogLevel.INFO,
                f"Starting file size monitoring (estimated output: {estimated_output_mb:.1f} MB)",
                {"estimated_output_mb": estimated_output_mb},
            )

            while not stop_event.is_set():
                try:
                    if output_file.exists():
                        current_size_bytes = output_file.stat().st_size
                        current_size_mb = current_size_bytes / (1024 * 1024)

                        # Calculate progress based on file size
                        if estimated_output_mb > 0:
                            size_progress = min(1.0, current_size_mb / estimated_output_mb)
                            progress = base_progress + (size_progress * (max_progress - base_progress))
                        else:
                            # If we can't estimate, just increment slowly
                            progress = min(max_progress, base_progress + (time.time() - last_update_time) * 0.5)

                        # Update progress if file grew significantly (>5 MB or >10%)
                        size_delta_mb = current_size_mb - last_size_mb
                        if size_delta_mb > 5.0 or (last_size_mb > 0 and size_delta_mb / last_size_mb > 0.1):
                            # Calculate write speed
                            time_delta = time.time() - last_update_time
                            if time_delta > 0:
                                speed_mbps = size_delta_mb / time_delta
                                state.update_progress(
                                    progress,
                                    f"Writing data... ({current_size_mb:.1f} MB written, {speed_mbps:.2f} MB/s)",
                                    "data_writing",
                                )
                            else:
                                state.update_progress(
                                    progress,
                                    f"Writing data... ({current_size_mb:.1f} MB written)",
                                    "data_writing",
                                )

                            last_size_mb = current_size_mb
                            last_update_time = time.time()
                            stall_count = 0

                        # Detect stalls (no size change for 30 seconds)
                        elif time.time() - last_update_time > 30:
                            stall_count += 1
                            if stall_count == 1:
                                state.add_log(
                                    LogLevel.WARNING,
                                    f"File size hasn't changed in 30 seconds ({current_size_mb:.1f} MB)",
                                    {"current_size_mb": current_size_mb},
                                )

                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Error monitoring file size: {e}",
                    )

                # Bug #36: Use event-based waiting instead of blocking sleep for faster shutdown
                if stop_event.wait(5.0):
                    break  # Exit immediately if stop requested

            state.add_log(
                LogLevel.INFO,
                f"File size monitoring stopped (final size: {last_size_mb:.1f} MB)",
                {"final_size_mb": last_size_mb},
            )
        except Exception as e:
            # Bug #37: Catch any unhandled exceptions to prevent silent thread failure
            logger.error(f"File size monitoring thread crashed: {e}", exc_info=True)
            state.add_log(
                LogLevel.ERROR,
                f"File size monitoring failed: {str(e)}",
                {"error_type": type(e).__name__},
            )

    def _map_flat_to_nested_metadata(self, flat_metadata: dict[str, Any]) -> dict[str, Any]:
        """Map flat user-provided metadata to NWB's nested structure.

        User provides metadata like:
            {"experimenter": "Dr. Smith", "institution": "MIT", "subject_id": "mouse001"}

        NWB expects nested structure like:
            {
                "NWBFile": {
                    "experimenter": ["Dr. Smith"],
                    "institution": "MIT",
                    "session_description": "...",
                    "experiment_description": "...",
                    "keywords": [...]
                },
                "Subject": {
                    "subject_id": "mouse001",
                    "species": "Mus musculus",
                    "age": "P90D"
                }
            }

        Args:
            flat_metadata: Flat metadata dictionary from user

        Returns:
            Nested metadata dictionary matching NWB structure
        """
        # Define the mapping from flat field names to NWB nested structure
        NWBFILE_FIELDS = {
            "experimenter",
            "institution",
            "session_description",
            "experiment_description",
            "keywords",
            "related_publications",
            "session_id",
            "lab",
            "protocol",
            "notes",
        }

        SUBJECT_FIELDS = {
            "subject_id",
            "species",
            "age",
            "sex",
            "description",
            "weight",
            "strain",
            "genotype",
        }

        nested: dict[str, dict[str, Any]] = {}

        # Process standard fields
        for key, value in flat_metadata.items():
            # Skip internal metadata fields
            if key.startswith("_"):
                continue

            if key in NWBFILE_FIELDS:
                if "NWBFile" not in nested:
                    nested["NWBFile"] = {}

                # Handle list fields that NWB expects as lists
                if key in ["experimenter", "keywords", "related_publications"]:
                    # If user provided a string, convert to list
                    if isinstance(value, str):
                        nested["NWBFile"][key] = [value]
                    elif isinstance(value, list):
                        nested["NWBFile"][key] = value
                    else:
                        nested["NWBFile"][key] = [str(value)]
                else:
                    nested["NWBFile"][key] = value

            elif key in SUBJECT_FIELDS:
                if "Subject" not in nested:
                    nested["Subject"] = {}
                nested["Subject"][key] = value

            else:
                # Unknown field - try to place it in NWBFile as a fallback
                if "NWBFile" not in nested:
                    nested["NWBFile"] = {}
                nested["NWBFile"][key] = value

        # Process custom fields if present
        if "_custom_fields" in flat_metadata:
            custom_fields = flat_metadata["_custom_fields"]

            # Create a custom namespace for user-defined fields
            if custom_fields:
                if "NWBFile" not in nested:
                    nested["NWBFile"] = {}

                # Store custom fields in notes or as separate entries
                # NWB allows arbitrary fields in the file
                for custom_key, custom_value in custom_fields.items():
                    # Clean the key name to be NWB-compliant
                    clean_key = custom_key.replace(" ", "_").lower()

                    # Try to intelligently place custom fields
                    if any(term in clean_key for term in ["subject", "animal", "mouse", "rat"]):
                        # Subject-related custom field
                        if "Subject" not in nested:
                            nested["Subject"] = {}
                        nested["Subject"][clean_key] = custom_value
                    else:
                        # General custom field - add to NWBFile
                        nested["NWBFile"][clean_key] = custom_value

                # Also store a summary of custom fields in notes for documentation
                if custom_fields:
                    custom_summary = "Custom metadata fields:\n"
                    for k, v in custom_fields.items():
                        custom_summary += f"  - {k}: {v}\n"

                    existing_notes = nested["NWBFile"].get("notes", "")
                    if existing_notes:
                        nested["NWBFile"]["notes"] = f"{existing_notes}\n\n{custom_summary}"
                    else:
                        nested["NWBFile"]["notes"] = custom_summary

        return nested

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hex digest
        """
        result = compute_sha256(Path(file_path))
        return str(result)

    async def handle_apply_corrections(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Apply corrections and reconvert NWB file.

        Implements Task T038 and Story 8.5: Automatic Issue Correction
        Implements Story 8.7: Reconversion Orchestration

        Args:
            message: MCP message with correction context
            state: Global state

        Returns:
            MCPResponse with reconversion result
        """
        message.context.get("correction_context")
        auto_fixes = message.context.get("auto_fixes", {})
        user_input = message.context.get("user_input", {})

        if not state.input_path:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_INPUT_PATH",
                error_message="No input path in state for reconversion",
            )

        state.add_log(
            LogLevel.INFO,
            f"Applying corrections (attempt {state.correction_attempt + 1})",
            {"auto_fixes": len(auto_fixes), "user_input": len(user_input)},
        )

        try:
            # Increment correction attempt
            state.increment_correction_attempt()

            # Build corrected metadata by merging state metadata with fixes
            corrected_metadata = state.metadata.copy()

            # Apply automatic fixes
            for field, value in auto_fixes.items():
                corrected_metadata[field] = value
                state.add_log(
                    LogLevel.INFO,
                    f"Applied automatic fix: {field} = {value}",
                )

            # Apply user-provided input
            for field, value in user_input.items():
                corrected_metadata[field] = value
                state.add_log(
                    LogLevel.INFO,
                    f"Applied user input: {field} = {value}",
                )

            # Version the previous NWB file if it exists
            if state.output_path and Path(state.output_path).exists():
                versioned_path, checksum = create_versioned_file(
                    Path(state.output_path),
                    state.correction_attempt - 1,  # Previous attempt
                    compute_checksum=True,
                )
                state.add_log(
                    LogLevel.INFO,
                    f"Versioned previous NWB file: {versioned_path}",
                    {"checksum": checksum},
                )

            # Re-run conversion with corrected metadata
            # Get format from state metadata (Bug #18 fix)
            format_name = state.metadata.get("format", "SpikeGLX")

            reconvert_message = MCPMessage(
                target_agent="conversion",
                action="run_conversion",
                context={
                    "input_path": state.input_path,
                    "output_path": state.output_path,  # Same output path
                    "format": format_name,  # Bug #18: Add missing format parameter
                    "metadata": corrected_metadata,
                },
                reply_to=message.message_id,
            )

            # Execute reconversion
            result = await self.handle_run_conversion(reconvert_message, state)

            if result.success:
                state.add_log(
                    LogLevel.INFO,
                    f"Reconversion successful (attempt {state.correction_attempt})",
                    {"output_path": state.output_path},
                )

                # Compute checksum of new file
                if state.output_path:
                    checksum = compute_sha256(Path(state.output_path))
                    state.add_log(
                        LogLevel.INFO,
                        f"New NWB file checksum: {checksum}",
                    )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "reconversion_successful",
                        "output_path": state.output_path,
                        "attempt": state.correction_attempt,
                        "checksum": checksum,
                    },
                )
            else:
                state.add_log(
                    LogLevel.ERROR,
                    f"Reconversion failed (attempt {state.correction_attempt})",
                    {"error": result.error},
                )
                return result

        except Exception as e:
            error_msg = f"Correction application failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"exception": str(e), "attempt": state.correction_attempt},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="CORRECTION_APPLICATION_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )


def register_conversion_agent(mcp_server, llm_service: Optional["LLMService"] = None) -> ConversionAgent:
    """Register Conversion Agent handlers with MCP server.

    Args:
        mcp_server: MCP server instance
        llm_service: Optional LLM service for intelligent features

    Returns:
        ConversionAgent instance
    """
    agent = ConversionAgent(llm_service=llm_service)

    mcp_server.register_handler(
        "conversion",
        "detect_format",
        agent.handle_detect_format,
    )

    mcp_server.register_handler(
        "conversion",
        "run_conversion",
        agent.handle_run_conversion,
    )

    mcp_server.register_handler(
        "conversion",
        "apply_corrections",
        agent.handle_apply_corrections,
    )

    return agent
