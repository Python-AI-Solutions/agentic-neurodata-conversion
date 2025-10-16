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
from utils.file_versioning import create_versioned_file, compute_sha256


class ConversionAgent:
    """
    Conversion agent for format detection and NWB conversion.

    This agent handles all technical conversion operations.
    """

    def __init__(self, llm_service: Optional["LLMService"] = None):
        """
        Initialize the conversion agent.

        Args:
            llm_service: Optional LLM service for intelligent features
        """
        self._supported_formats = self._get_supported_formats()
        self._llm_service = llm_service

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

    async def _detect_format(self, input_path: str, state: GlobalState) -> Optional[str]:
        """
        Detect data format based on file structure and content.

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
                state.add_log(
                    LogLevel.INFO,
                    f"LLM detected format: {detected_format} (confidence: {confidence}%)",
                )
                return detected_format

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

        # Still ambiguous
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

    async def _detect_format_with_llm(
        self,
        input_path: str,
        state: GlobalState,
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to intelligently detect data format when hardcoded patterns fail.

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

        from pathlib import Path
        import json

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

Common formats:
- **SpikeGLX**: Files like "*.ap.bin", "*.ap.meta", "*.lf.bin", "*.lf.meta"
- **OpenEphys**: Directories with "structure.oebin", "settings.xml", or "continuous/" folders
- **Neuropixels**: Files with ".nidq." in the name, or specific probe naming
- **Intan**: ".rhd" or ".rhs" files
- **Neuralynx**: ".ncs", ".nev", ".ntt" files
- **Plexon**: ".plx" files
- **TDT**: Tank/Block directory structure
- **Imaging (ScanImage)**: ".tif" with specific metadata
- **Miniscope**: ".avi" with timestamp files
- **Calcium Imaging**: Various formats with ROI data

Analyze the file structure carefully and make an educated guess."""

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
            return response

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
            # 🎯 PRIORITY 5: Narrate conversion start
            from pathlib import Path
            file_size_mb = Path(input_path).stat().st_size / (1024 * 1024) if Path(input_path).exists() else 0

            narration_start = await self._narrate_progress(
                stage="starting",
                format_name=format_name,
                context={"file_size_mb": file_size_mb},
                state=state,
            )

            # Optimize conversion parameters with LLM
            optimization = await self._optimize_conversion_parameters(
                format_name=format_name,
                file_size_mb=file_size_mb,
                state=state,
            )

            # 🎯 PRIORITY 5: Narrate processing
            narration_processing = await self._narrate_progress(
                stage="processing",
                format_name=format_name,
                context={"file_size_mb": file_size_mb, "progress_percent": 50},
                state=state,
            )

            # Run conversion
            self._run_neuroconv_conversion(
                input_path=input_path,
                output_path=output_path,
                format_name=format_name,
                metadata=metadata,
            )

            # 🎯 PRIORITY 5: Narrate finalization
            narration_finalizing = await self._narrate_progress(
                stage="finalizing",
                format_name=format_name,
                context={"output_path": output_path},
                state=state,
            )

            # Calculate checksum
            checksum = self._calculate_checksum(output_path)
            state.checksums[output_path] = checksum

            # 🎯 PRIORITY 5: Narrate completion
            narration_complete = await self._narrate_progress(
                stage="complete",
                format_name=format_name,
                context={"output_path": output_path, "checksum": checksum},
                state=state,
            )

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

    async def _optimize_conversion_parameters(
        self,
        format_name: str,
        file_size_mb: float,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to determine optimal NWB conversion parameters.

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
        context: Dict[str, Any],
        state: GlobalState,
    ) -> str:
        """
        🎯 PRIORITY 5: Progress Narration
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
            return narration.strip()
        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Progress narration failed: {e}")
            # Fallback
            return f"Processing {format_name} data at stage: {stage}"

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
        return compute_sha256(Path(file_path))

    async def handle_apply_corrections(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Apply corrections and reconvert NWB file.

        Implements Task T038 and Story 8.5: Automatic Issue Correction
        Implements Story 8.7: Reconversion Orchestration

        Args:
            message: MCP message with correction context
            state: Global state

        Returns:
            MCPResponse with reconversion result
        """
        correction_context = message.context.get("correction_context")
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
                    compute_checksum=True
                )
                state.add_log(
                    LogLevel.INFO,
                    f"Versioned previous NWB file: {versioned_path}",
                    {"checksum": checksum},
                )

            # Re-run conversion with corrected metadata
            reconvert_message = MCPMessage(
                target_agent="conversion",
                action="run_conversion",
                context={
                    "input_path": state.input_path,
                    "output_path": state.output_path,  # Same output path
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
    """
    Register Conversion Agent handlers with MCP server.

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
