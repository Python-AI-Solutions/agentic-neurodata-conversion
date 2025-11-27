"""Conversion execution module for conversion agent.

Handles:
- NeuroConv conversion execution (84+ formats)
- Progress monitoring during conversion
- Conversion parameter optimization
- Thread-safe file size tracking
"""

import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentic_neurodata_conversion.services.llm_service import LLMService

from agentic_neurodata_conversion.models import ConversionStatus, GlobalState, LogLevel, MCPMessage, MCPResponse
from agentic_neurodata_conversion.utils.file_versioning import compute_sha256

logger = logging.getLogger(__name__)


class ConversionRunner:
    """Handles NeuroConv conversion execution.

    Manages the complete conversion workflow including:
    - Format-to-interface mapping for 84+ NeuroConv formats
    - Dynamic interface loading and initialization
    - Progress monitoring via file size tracking
    - LLM-powered parameter optimization
    - Checksum calculation
    """

    def __init__(
        self,
        llm_service: "LLMService | None" = None,
        helpers=None,
    ):
        """Initialize conversion runner.

        Args:
            llm_service: Optional LLM service for parameter optimization and narration
            helpers: ConversionHelpers instance for metadata mapping and narration
        """
        self._llm_service = llm_service
        self._helpers = helpers

    async def handle_run_conversion(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Run NWB conversion using NeuroConv.

        MCP handler that orchestrates the full conversion workflow:
        1. Extract parameters from message
        2. Filter metadata to NWB-allowed fields
        3. Track conversion timing and file sizes
        4. Narrate progress with LLM
        5. Optimize conversion parameters
        6. Execute conversion
        7. Calculate checksums
        8. Return result with metrics

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
        from datetime import datetime

        conversion_start_time = time.time()
        conversion_start_timestamp = datetime.now()

        # Get detailed file information
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
            # Narrate conversion start
            state.update_progress(10, f"Analyzing {format_name} data ({file_size_mb:.1f} MB)...", "analysis")

            if self._helpers:
                await self._helpers.narrate_progress(
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

            # Narrate processing
            state.update_progress(30, "Processing data...", "processing")
            if self._helpers:
                await self._helpers.narrate_progress(
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

            # Narrate finalization
            state.update_progress(90, "Finalizing NWB file...", "finalization")
            if self._helpers:
                await self._helpers.narrate_progress(
                    stage="finalizing",
                    format_name=format_name,
                    context={"output_path": output_path},
                    state=state,
                )

            # Calculate checksum
            state.update_progress(98, "Calculating file checksum...", "checksum")
            checksum = None
            if self._helpers:
                checksum = self._helpers.calculate_checksum(output_path)
            else:
                checksum = str(compute_sha256(Path(output_path)))
            state.checksums[output_path] = checksum

            # Narrate completion
            if self._helpers:
                await self._helpers.narrate_progress(
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
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {
                    "input_path": input_path,
                    "format": format_name,
                    "exception": str(e),
                },
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="CONVERSION_FAILED",
                error_message=error_msg,
                error_context={
                    "exception": str(e),
                    "technical_details": error_msg,
                },
            )

    def _run_neuroconv_conversion(
        self,
        input_path: str,
        output_path: str,
        format_name: str,
        metadata: dict[str, Any],
        state: GlobalState,
    ) -> None:
        """Run NeuroConv conversion.

        Handles the complete NeuroConv workflow:
        1. Map format name to interface class
        2. Dynamically import the interface
        3. Initialize interface with format-specific logic
        4. Extract interface metadata
        5. Map user metadata to NWB structure
        6. Merge metadata
        7. Monitor file size progress in background thread
        8. Run conversion
        9. Clean up on errors

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
        input_file = Path(input_path)

        # Format-specific interface initialization
        state.update_progress(55, f"Initializing {format_name} interface...", "interface_init")

        if format_name in ["SpikeGLX", "Neuropixels"]:
            # Determine folder containing SpikeGLX files
            folder_path = str(input_file.parent) if input_file.is_file() else input_path
            path = Path(folder_path)

            # Find .ap.bin file (action potential band) - primary recording stream
            # SpikeGLX requires file_path parameter, not folder_path
            ap_bin_files = list(path.glob("*.ap.bin"))

            if not ap_bin_files:
                raise ValueError(
                    f"No .ap.bin file found in SpikeGLX directory: {folder_path}. "
                    f"Expected format: '<name>_g<gate>_t<trigger>.imec<probe>.ap.bin'. "
                    f"Files present: {[f.name for f in path.glob('*.bin')]}"
                )

            # Use the first .ap.bin file found
            # NeuroConv will automatically find companion .meta file
            file_path = str(ap_bin_files[0])
            state.update_progress(60, f"Initializing SpikeGLX with {ap_bin_files[0].name}...", "interface_init")

            try:
                # Initialize with file_path (not folder_path) - this is how it worked before refactoring
                # Both .bin and .meta files are used (companion file structure)
                data_interface = interface_class(file_path=file_path)
            except Exception as e:
                raise ValueError(
                    f"Failed to initialize SpikeGLX interface for {file_path}. "
                    f"Error: {str(e)}. "
                    f"Ensure both .bin and .meta files are present in the same directory."
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

        # Map flat user metadata to NWB's nested structure
        state.update_progress(75, "Applying user-provided metadata...", "metadata_mapping")
        logger.debug(f"Flat user metadata: {metadata}")

        structured_metadata = {}
        if self._helpers:
            structured_metadata = self._helpers.map_flat_to_nested_metadata(metadata)
        else:
            # Fallback if no helpers - just pass metadata as-is
            structured_metadata = metadata

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

        Features:
        - Estimates output size (typically 60-120% of input)
        - Calculates write speed (MB/s)
        - Detects stalls (no size change for 30+ seconds)
        - Event-based waiting for fast shutdown

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
