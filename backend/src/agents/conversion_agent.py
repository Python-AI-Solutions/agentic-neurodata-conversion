"""
Conversion Agent implementation.

Responsible for:
- Format detection
- NWB conversion using NeuroConv
- Pure technical conversion logic (no user interaction)
"""
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import neuroconv
from pynwb import NWBHDF5IO

from models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
)


class ConversionAgent:
    """
    Conversion agent for format detection and NWB conversion.

    This agent handles all technical conversion operations.
    """

    def __init__(self):
        """Initialize the conversion agent."""
        self._supported_formats = self._get_supported_formats()

    def _get_supported_formats(self) -> List[str]:
        """
        Get list of supported data formats from NeuroConv.

        Returns:
            List of supported format names
        """
        try:
            # Get available data interfaces from NeuroConv
            from neuroconv import get_format_summaries

            summaries = get_format_summaries()
            return [fmt["format"] for fmt in summaries]
        except Exception:
            # Fallback to known common formats
            return [
                "SpikeGLX",
                "Neuropixels",
                "OpenEphys",
                "Blackrock",
                "Axona",
                "Neuralynx",
                "Plexon",
            ]

    async def handle_detect_format(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Detect the data format of uploaded files.

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

        state.update_status(ConversionStatus.DETECTING_FORMAT)
        state.add_log(
            LogLevel.INFO,
            f"Starting format detection for: {input_path}",
            {"input_path": input_path},
        )

        try:
            detected_format = self._detect_format(input_path)

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

    def _detect_format(self, input_path: str) -> Optional[str]:
        """
        Detect data format based on file structure and content.

        Args:
            input_path: Path to input file or directory

        Returns:
            Detected format name or None if ambiguous
        """
        path = Path(input_path)

        # Check for SpikeGLX
        if self._is_spikeglx(path):
            return "SpikeGLX"

        # Check for OpenEphys
        if self._is_openephys(path):
            return "OpenEphys"

        # Check for Neuropixels
        if self._is_neuropixels(path):
            return "Neuropixels"

        # Add more format detection logic as needed

        return None

    def _is_spikeglx(self, path: Path) -> bool:
        """Check if data is SpikeGLX format."""
        if path.is_dir():
            # Look for .ap.bin and .ap.meta files
            ap_bins = list(path.glob("*.ap.bin"))
            ap_metas = list(path.glob("*.ap.meta"))
            return len(ap_bins) > 0 and len(ap_metas) > 0
        elif path.is_file():
            # Check if it's a .bin or .meta file
            return path.suffix in [".bin"] and (".ap." in path.name or ".lf." in path.name)
        return False

    def _is_openephys(self, path: Path) -> bool:
        """Check if data is OpenEphys format."""
        if path.is_dir():
            # Look for structure.oebin or settings.xml
            return (path / "structure.oebin").exists() or (path / "settings.xml").exists()
        return False

    def _is_neuropixels(self, path: Path) -> bool:
        """Check if data is Neuropixels format."""
        # Neuropixels data often has specific naming patterns
        if path.is_file() and ".nidq." in path.name:
            return True
        return False

    async def handle_run_conversion(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Run NWB conversion using NeuroConv.

        Args:
            message: MCP message with context containing conversion parameters
            state: Global state

        Returns:
            MCPResponse with conversion result or error
        """
        input_path = message.context.get("input_path")
        output_path = message.context.get("output_path")
        format_name = message.context.get("format")
        metadata = message.context.get("metadata", {})

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

        state.update_status(ConversionStatus.CONVERTING)
        state.add_log(
            LogLevel.INFO,
            f"Starting NWB conversion: {format_name}",
            {
                "input_path": input_path,
                "output_path": output_path,
                "format": format_name,
            },
        )

        try:
            # Run conversion
            self._run_neuroconv_conversion(
                input_path=input_path,
                output_path=output_path,
                format_name=format_name,
                metadata=metadata,
            )

            # Calculate checksum
            checksum = self._calculate_checksum(output_path)
            state.checksums[output_path] = checksum

            state.output_path = output_path
            state.add_log(
                LogLevel.INFO,
                "Conversion completed successfully",
                {
                    "output_path": output_path,
                    "checksum": checksum,
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
                error_context={"exception": str(e)},
            )

    def _run_neuroconv_conversion(
        self,
        input_path: str,
        output_path: str,
        format_name: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Run NeuroConv conversion.

        Args:
            input_path: Path to input data
            output_path: Path for output NWB file
            format_name: Format name (e.g., "SpikeGLX")
            metadata: Metadata dictionary

        Raises:
            Exception: If conversion fails
        """
        from neuroconv import NWBConverter
        from neuroconv.datainterfaces import SpikeGLXRecordingInterface

        # Map format names to interface classes
        # For MVP, we support SpikeGLX. Add more formats as needed.
        format_map = {
            "SpikeGLX": SpikeGLXRecordingInterface,
        }

        if format_name not in format_map:
            raise ValueError(f"Unsupported format: {format_name}. Supported: {list(format_map.keys())}")

        interface_class = format_map[format_name]

        # Create interface with source data
        from pathlib import Path
        input_file = Path(input_path)

        # For SpikeGLX, always use folder_path (even if a single file was uploaded)
        # because the interface needs to find the corresponding .meta file
        if format_name == "SpikeGLX":
            if input_file.is_file():
                # Use the parent directory
                folder_path = str(input_file.parent)
            else:
                folder_path = input_path

            # Try to detect available streams and use the first non-SYNC stream
            try:
                # First try without stream_id to see what's available
                from spikeinterface.extractors import SpikeGLXRecordingExtractor
                import neo

                # Get available streams
                reader = neo.rawio.SpikeGLXRawIO(dirname=folder_path)
                reader.parse_header()
                stream_ids = reader.header['signal_streams']['id']

                # Prefer non-SYNC streams (typically 'imec0.ap' or similar)
                non_sync_streams = [s for s in stream_ids if 'SYNC' not in s]
                stream_id = non_sync_streams[0] if non_sync_streams else stream_ids[0]

                data_interface = interface_class(folder_path=folder_path, stream_id=stream_id)
            except Exception:
                # Fallback: try without stream_id and let it fail with a better error
                data_interface = interface_class(folder_path=folder_path)
        else:
            # For other formats
            if input_file.is_file():
                data_interface = interface_class(file_path=input_path)
            else:
                data_interface = interface_class(folder_path=input_path)

        # For single-interface conversions, just use the interface directly
        # Get metadata from interface
        interface_metadata = data_interface.get_metadata()

        # Merge user-provided metadata
        for key, value in metadata.items():
            if key in interface_metadata:
                interface_metadata[key].update(value)
            else:
                interface_metadata[key] = value

        # Run conversion directly from interface
        data_interface.run_conversion(
            nwbfile_path=output_path,
            metadata=interface_metadata,
            overwrite=True,
        )

    def _calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hex digest
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def register_conversion_agent(mcp_server) -> ConversionAgent:
    """
    Register Conversion Agent handlers with MCP server.

    Args:
        mcp_server: MCP server instance

    Returns:
        ConversionAgent instance
    """
    agent = ConversionAgent()

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

    return agent
