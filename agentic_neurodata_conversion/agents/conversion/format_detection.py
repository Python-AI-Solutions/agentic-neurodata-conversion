"""Format detection module for conversion agent.

Handles:
- Supported format enumeration (84+ formats)
- LLM-powered intelligent format detection
- Hardcoded pattern matching (fallback)
- Format-specific validators (SpikeGLX, OpenEphys, Neuropixels)
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentic_neurodata_conversion.services.llm_service import LLMService

from agentic_neurodata_conversion.models import ConversionStatus, GlobalState, LogLevel, MCPMessage, MCPResponse

logger = logging.getLogger(__name__)


class FormatDetector:
    """Format detection for neuroscience data files."""

    def __init__(self, llm_service: "LLMService | None" = None):
        """Initialize format detector.

        Args:
            llm_service: Optional LLM service for intelligent detection
        """
        self._llm_service = llm_service
        self._supported_formats = self._get_supported_formats()

    def _get_supported_formats(self) -> list[str]:
        """Get list of supported data formats from NeuroConv.

        Returns:
            List of supported format names (84+ formats)
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

        MCP message handler for format detection requests.

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
            detected_format = await self.detect_format(input_path, state)

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

    async def detect_format(self, input_path: str, state: GlobalState) -> str | None:
        """Detect data format based on file structure and content.

        LLM-First Format Detection Strategy:
        1. Try LLM-based intelligent detection (more accurate)
        2. Fall back to hardcoded pattern matching if LLM unavailable/low confidence

        Args:
            input_path: Path to input file or directory
            state: Global state for logging

        Returns:
            Detected format name or None if ambiguous
        """
        path = Path(input_path)

        # Try LLM detection FIRST (more intelligent, handles edge cases)
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

                # Validate that LLM returned a valid NeuroConv format name
                # This prevents hallucinated format names
                if detected_format not in self._supported_formats:
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

        # Check for Axon/ABF files as fallback
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

        Args:
            path: Path to file or directory

        Returns:
            True if SpikeGLX format detected
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

        Args:
            path: Path to file or directory

        Returns:
            True if OpenEphys format detected
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

        Args:
            path: Path to file or directory

        Returns:
            True if Neuropixels format detected
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
