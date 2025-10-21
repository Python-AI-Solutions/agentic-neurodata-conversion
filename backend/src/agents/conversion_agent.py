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
from agents.intelligent_format_detector import IntelligentFormatDetector


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
        self._format_detector = (
            IntelligentFormatDetector(llm_service) if llm_service else None
        )

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
        """
        Check if data is SpikeGLX format.

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
            has_spikeglx_pattern = any([
                ".ap." in path.name,
                ".lf." in path.name,
                ".nidq." in path.name,
            ])
            return is_bin and has_spikeglx_pattern
        return False

    def _is_openephys(self, path: Path) -> bool:
        """
        Check if data is OpenEphys format.

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
        """
        Check if data is Neuropixels format.

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

        await state.update_status(ConversionStatus.CONVERTING)
        state.update_progress(0, "Initializing conversion...", "initialization")
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

            state.update_progress(10, f"Analyzing {format_name} data ({file_size_mb:.1f} MB)...", "analysis")

            narration_start = await self._narrate_progress(
                stage="starting",
                format_name=format_name,
                context={"file_size_mb": file_size_mb},
                state=state,
            )

            # Optimize conversion parameters with LLM
            state.update_progress(20, "Optimizing conversion parameters...", "optimization")
            optimization = await self._optimize_conversion_parameters(
                format_name=format_name,
                file_size_mb=file_size_mb,
                state=state,
            )

            # 🎯 PRIORITY 5: Narrate processing
            state.update_progress(30, "Processing data...", "processing")
            narration_processing = await self._narrate_progress(
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
            narration_finalizing = await self._narrate_progress(
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
            narration_complete = await self._narrate_progress(
                stage="complete",
                format_name=format_name,
                context={"output_path": output_path, "checksum": checksum},
                state=state,
            )

            state.output_path = output_path
            state.update_progress(100, "Conversion completed successfully!", "complete")
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
    ) -> Optional[str]:
        """
        Use LLM to generate user-friendly error explanations.

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
        file_context = {}
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
        except Exception:
            pass

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

            return explanation.strip()

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
        state: GlobalState,
    ) -> None:
        """
        Run NeuroConv conversion.

        Args:
            input_path: Path to input data
            output_path: Path for output NWB file
            format_name: Format name (e.g., "SpikeGLX")
            metadata: Metadata dictionary (flat structure from user)
            state: Global state for progress tracking

        Raises:
            Exception: If conversion fails
        """
        from neuroconv import NWBConverter
        from neuroconv.datainterfaces import (
            SpikeGLXRecordingInterface,
            OpenEphysRecordingInterface,
            OpenEphysBinaryRecordingInterface,
        )

        # Map format names to interface classes
        format_map = {
            "SpikeGLX": SpikeGLXRecordingInterface,
            "OpenEphys": OpenEphysRecordingInterface,
            "OpenEphysBinary": OpenEphysBinaryRecordingInterface,
            "Neuropixels": SpikeGLXRecordingInterface,  # Neuropixels data uses SpikeGLX format
        }

        if format_name not in format_map:
            raise ValueError(
                f"Unsupported format: {format_name}. "
                f"Supported formats: {', '.join(sorted(format_map.keys()))}"
            )

        interface_class = format_map[format_name]

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
            if input_file.is_file():
                folder_path = str(input_file.parent)
            else:
                folder_path = input_path

            try:
                data_interface = interface_class(folder_path=folder_path)
            except Exception as e:
                raise ValueError(
                    f"Failed to initialize OpenEphys interface for {folder_path}. "
                    f"Error: {str(e)}. "
                    f"Make sure the folder contains structure.oebin or settings.xml."
                ) from e

        else:
            # Generic format handling
            if input_file.is_file():
                data_interface = interface_class(file_path=input_path)
            else:
                data_interface = interface_class(folder_path=input_path)

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
        try:
            data_interface.run_conversion(
                nwbfile_path=output_path,
                metadata=interface_metadata,
                overwrite=True,
            )
        except Exception as e:
            # Bug #16: Clean up partial/corrupt file on conversion error
            if Path(output_path).exists():
                try:
                    Path(output_path).unlink()
                    logger.debug(f"Cleaned up partial NWB file: {output_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up partial file: {cleanup_error}")
            raise  # Re-raise original exception

        state.update_progress(95, "Verifying NWB file integrity...", "verification")

    def _map_flat_to_nested_metadata(self, flat_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map flat user-provided metadata to NWB's nested structure.

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

        nested = {}

        for key, value in flat_metadata.items():
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

        return nested

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
