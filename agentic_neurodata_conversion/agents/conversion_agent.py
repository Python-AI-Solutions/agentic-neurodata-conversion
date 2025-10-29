"""ConversionAgent for NWB file generation (Phase 5 implementation)."""

from datetime import datetime
from pathlib import Path
import time
from typing import Any

from neuroconv.datainterfaces import OpenEphysRecordingInterface, SpikeGLXRecordingInterface

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import (
    ConversionResults,
    WorkflowStage,
)


class ConversionAgent(BaseAgent):
    """Conversion agent for NWB file generation."""

    def get_capabilities(self) -> list[str]:
        """
        Return conversion agent capabilities.

        Returns:
            List of capability strings
        """
        return ["convert_to_nwb", "validate_conversion"]

    async def _convert_to_nwb(
        self, session_id: str, dataset_path: str, dataset_format: str, metadata: dict
    ) -> ConversionResults:
        """
        Convert electrophysiology dataset to NWB format using NeuroConv.

        Supports multiple formats:
        - OpenEphys: Uses OpenEphysRecordingInterface
        - SpikeGLX: Uses SpikeGLXRecordingInterface

        Args:
            session_id: Session identifier for output naming
            dataset_path: Path to dataset directory
            dataset_format: Format of the dataset (e.g., "openephys", "spikeglx")
            metadata: Metadata dictionary for NWB file

        Returns:
            ConversionResults with file path and conversion metrics

        Raises:
            ValueError: If dataset format is not supported
            Exception: If conversion fails (corrupt data, missing files, etc.)
        """
        start_time = time.time()

        try:
            # Create appropriate interface based on format
            if dataset_format == "openephys":
                interface = OpenEphysRecordingInterface(folder_path=dataset_path)
            elif dataset_format == "spikeglx":
                # SpikeGLX interface needs the path to the .bin or .meta file
                # Find the .ap.bin file (action potential band)
                path = Path(dataset_path)
                ap_bin_files = list(path.glob("*.ap.bin"))

                if not ap_bin_files:
                    raise ValueError(f"No .ap.bin file found in SpikeGLX dataset: {dataset_path}")

                # Use the first .ap.bin file found
                file_path = str(ap_bin_files[0])
                interface = SpikeGLXRecordingInterface(file_path=file_path)
            else:
                raise ValueError(
                    f"Unsupported dataset format: {dataset_format}. "
                    f"Supported formats: openephys, spikeglx"
                )

            # Get default metadata from interface (includes ElectrodeGroups, Device, etc.)
            interface_metadata = interface.get_metadata()

            # Prepare user metadata for NWB
            user_metadata = self._prepare_metadata(metadata)

            # Deep merge: user metadata overrides interface defaults
            nwb_metadata = self._deep_merge_metadata(interface_metadata, user_metadata)

            # Set output path
            output_dir = Path.cwd() / "output" / "nwb_files"
            output_dir.mkdir(parents=True, exist_ok=True)
            nwb_file_path = output_dir / f"{session_id}.nwb"

            # Run conversion
            interface.run_conversion(
                nwbfile_path=str(nwb_file_path),
                metadata=nwb_metadata,
                overwrite=True,
            )

            # Calculate duration
            end_time = time.time()
            duration = end_time - start_time

            # Return conversion results
            return ConversionResults(
                nwb_file_path=str(nwb_file_path.absolute()),
                conversion_duration_seconds=duration,
                conversion_warnings=[],
                conversion_errors=[],
                conversion_log=f"Conversion of {dataset_format} dataset completed successfully in {duration:.2f}s",
            )

        except Exception:
            # Re-raise with full stack trace preserved
            raise

    def _prepare_metadata(self, session_metadata: dict) -> dict:
        """
        Prepare metadata for NWB conversion.

        Maps session metadata to NWB schema including Subject, NWBFile, and Device.
        Applies reasonable defaults for missing fields.

        Args:
            session_metadata: Session metadata dictionary

        Returns:
            NWB-formatted metadata dictionary
        """
        nwb_metadata: dict[str, Any] = {}

        # Subject metadata (always create with required fields)
        # NWB requires: subject_id, sex, and species as non-None strings
        subject_metadata = {}

        # Provide default subject_id if missing or None
        subject_id = session_metadata.get("subject_id")
        if subject_id is None or subject_id == "":
            subject_metadata["subject_id"] = "unknown_subject"
        else:
            subject_metadata["subject_id"] = subject_id

        # Provide default species if missing or None (required by NWB)
        species = session_metadata.get("species")
        if species is None or species == "":
            subject_metadata["species"] = "Homo sapiens"  # Default to human
        else:
            subject_metadata["species"] = species

        # Provide default sex if missing or None (required by NWB)
        sex = session_metadata.get("sex")
        if sex is None or sex == "":
            subject_metadata["sex"] = "U"  # U = Unknown
        else:
            subject_metadata["sex"] = sex

        # Add optional subject fields if present
        if "age" in session_metadata and session_metadata["age"]:
            subject_metadata["age"] = session_metadata["age"]

        if "subject_description" in session_metadata and session_metadata["subject_description"]:
            subject_metadata["description"] = session_metadata["subject_description"]

        nwb_metadata["Subject"] = subject_metadata

        # NWBFile metadata
        nwbfile_metadata = {}

        # Session description (required)
        nwbfile_metadata["session_description"] = session_metadata.get(
            "session_description", "OpenEphys recording session"
        )

        # Identifier (use session_id or generate)
        nwbfile_metadata["identifier"] = session_metadata.get(
            "identifier", session_metadata.get("session_id", "UNSPECIFIED")
        )

        # Session start time (required by NWB, must not be None)
        session_start_time = session_metadata.get("session_start_time")
        if session_start_time is None or session_start_time == "":
            # Default to current time in ISO format
            nwbfile_metadata["session_start_time"] = datetime.utcnow().isoformat() + "Z"
        else:
            nwbfile_metadata["session_start_time"] = session_start_time

        # Experimenter (convert to list if string, provide default if None)
        experimenter = session_metadata.get("experimenter")
        if experimenter is None or experimenter == "":
            # NWB requires experimenter to be a list, never None
            nwbfile_metadata["experimenter"] = ["Unknown"]
        elif isinstance(experimenter, str):
            nwbfile_metadata["experimenter"] = [experimenter]
        else:
            nwbfile_metadata["experimenter"] = experimenter

        # Lab and institution
        if "lab" in session_metadata:
            nwbfile_metadata["lab"] = session_metadata["lab"]

        if "institution" in session_metadata:
            nwbfile_metadata["institution"] = session_metadata["institution"]

        nwb_metadata["NWBFile"] = nwbfile_metadata

        # Device metadata
        if any(
            key in session_metadata
            for key in ["device_name", "device_manufacturer", "device_description"]
        ):
            device_metadata = {}

            device_metadata["name"] = session_metadata.get(
                "device_name", "recording_device"
            )
            device_metadata["description"] = session_metadata.get(
                "device_description", "Recording device"
            )

            if "device_manufacturer" in session_metadata:
                device_metadata["manufacturer"] = session_metadata[
                    "device_manufacturer"
                ]

            # Devices should be a list in NWB
            nwb_metadata["Ecephys"] = {"Device": [device_metadata]}

        return nwb_metadata

    def _deep_merge_metadata(self, base: dict, override: dict) -> dict:
        """
        Deep merge two metadata dictionaries.

        User metadata (override) takes precedence over interface defaults (base).
        For nested dictionaries, merges recursively. For "Ecephys" specifically,
        preserves electrode groups and devices from both sources.

        Args:
            base: Base metadata (from interface.get_metadata())
            override: Override metadata (from user/LLM)

        Returns:
            Merged metadata dictionary
        """
        # Convert to regular dict if it's a DeepDict (from neuroconv)
        # DeepDict.copy() has a different signature that causes TypeError
        result = dict(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Special handling for Ecephys to preserve electrode groups
                if key == "Ecephys":
                    result[key] = self._merge_ecephys_metadata(result[key], value)
                else:
                    # Recursive merge for other nested dicts
                    result[key] = self._deep_merge_metadata(result[key], value)
            else:
                # Override for all other types
                result[key] = value

        return result

    def _merge_ecephys_metadata(self, base: dict, override: dict) -> dict:
        """
        Merge Ecephys metadata, preserving electrode groups and devices from interface.

        The interface provides complete Device and ElectrodeGroup lists. User metadata
        (if any) should complement, not replace these.

        Args:
            base: Base Ecephys metadata (from interface)
            override: Override Ecephys metadata (from user)

        Returns:
            Merged Ecephys metadata
        """
        # Convert to regular dict to avoid DeepDict copy() issues
        result = dict(base)

        for key, value in override.items():
            if key in ("Device", "ElectrodeGroup"):
                # Keep interface defaults for Device and ElectrodeGroup
                # These are auto-populated from the recording data
                continue
            else:
                # Override other fields (ElectricalSeries settings, etc.)
                result[key] = value

        return result

    async def _generate_error_message(
        self, error: Exception, dataset_path: str, metadata: dict
    ) -> str:
        """
        Generate user-friendly error message with remediation steps.

        Uses LLM to generate a plain language explanation of the error
        and actionable remediation steps.

        Args:
            error: The exception that occurred during conversion
            dataset_path: Path to the dataset that failed conversion
            metadata: Metadata that was being used for conversion

        Returns:
            User-friendly error message with remediation steps (under 200 words)
        """
        # Get error details
        error_type = type(error).__name__
        error_message = str(error)

        # Create LLM prompt
        prompt = f"""A conversion error occurred while converting an OpenEphys dataset to NWB format.

Error Details:
- Error Type: {error_type}
- Error Message: {error_message}
- Dataset Path: {dataset_path}

Dataset Context:
- Session Description: {metadata.get("session_description", "N/A")}
- Subject ID: {metadata.get("subject_id", "N/A")}
- Device: {metadata.get("device_name", "N/A")}

Please provide a user-friendly error explanation and specific remediation steps.
Keep the response under 200 words and focus on actionable steps the user can take.

Format:
**Error**: [Brief plain language explanation]
**Remediation**: [Numbered list of specific steps to fix]
"""

        system_message = (
            "You are a helpful assistant for neuroscience data conversion. "
            "Provide clear, actionable guidance for resolving conversion errors."
        )

        try:
            # Call LLM to generate error message
            response = await self.call_llm(prompt, system_message=system_message)
            return response

        except Exception:
            # Fallback if LLM call fails
            return (
                f"**Error**: {error_type} occurred during conversion.\n\n"
                f"**Details**: {error_message}\n\n"
                f"**Remediation**:\n"
                f"1. Verify that the dataset path is correct: {dataset_path}\n"
                f"2. Check that the dataset contains valid OpenEphys files\n"
                f"3. Ensure all required metadata fields are provided\n"
                f"4. Contact support if the issue persists"
            )

    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """
        Handle incoming MCP message.

        Routes conversion requests to the appropriate handler method.

        Args:
            message: MCP message to handle

        Returns:
            Result dictionary with status and relevant data
        """
        action = message.payload.get("action", "")

        if action == "convert_dataset":
            return await self._convert_dataset(message.session_id or "unknown")
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}",
                "session_id": message.session_id or "unknown",
            }

    async def _convert_dataset(self, session_id: str) -> dict[str, Any]:
        """
        Complete conversion workflow.

        Orchestrates the full conversion process including:
        1. Get session context
        2. Update workflow stage to CONVERTING
        3. Prepare metadata
        4. Convert to NWB
        5. Store conversion results
        6. Trigger evaluation agent
        7. Return success

        On error:
        - Generate user-friendly error message
        - Set requires_clarification flag
        - Set workflow_stage to FAILED

        Args:
            session_id: Session identifier

        Returns:
            Result dictionary with status and conversion details
        """
        session_context = None  # Initialize to None for exception handler
        try:
            # Step 1: Get session context
            session_context = await self.get_session_context(session_id)

            # Verify we have dataset info
            if not session_context.dataset_info:
                return {
                    "status": "error",
                    "message": "No dataset information found in session context",
                    "session_id": session_id,
                }

            # Verify we have metadata
            if not session_context.metadata:
                return {
                    "status": "error",
                    "message": "No metadata found in session context",
                    "session_id": session_id,
                }

            # Step 2: Update workflow stage to CONVERTING
            await self.update_session_context(
                session_id,
                {
                    "workflow_stage": WorkflowStage.CONVERTING,
                    "current_agent": self.agent_name,
                },
            )

            # Step 3: Prepare metadata (convert MetadataExtractionResult to dict)
            metadata_dict = session_context.metadata.model_dump()

            # Step 4: Convert to NWB
            conversion_results = await self._convert_to_nwb(
                session_id=session_id,
                dataset_path=session_context.dataset_info.dataset_path,
                dataset_format=session_context.dataset_info.format,
                metadata=metadata_dict,
            )

            # Step 5: Store conversion results
            await self.update_session_context(
                session_id,
                {
                    "conversion_results": conversion_results.model_dump(),
                    "workflow_stage": WorkflowStage.EVALUATING,
                },
            )

            # Step 6: Trigger evaluation agent
            await self.http_client.post(
                f"{self.mcp_server_url}/internal/route_message",
                json={
                    "session_id": session_id,
                    "target_agent": "evaluation_agent",
                    "message_type": "agent_execute",
                    "payload": {
                        "action": "validate_nwb",
                    },
                },
            )

            # Step 7: Return success
            return {
                "status": "success",
                "message": "Conversion completed successfully",
                "session_id": session_id,
                "nwb_file_path": conversion_results.nwb_file_path,
                "conversion_duration_seconds": conversion_results.conversion_duration_seconds,
            }

        except Exception as e:
            # On error: Generate user-friendly error message
            error_message = await self._generate_error_message(
                error=e,
                dataset_path=(
                    session_context.dataset_info.dataset_path
                    if session_context and session_context.dataset_info
                    else "unknown"
                ),
                metadata=(
                    session_context.metadata.model_dump()
                    if session_context and session_context.metadata
                    else {}
                ),
            )

            # Set requires_clarification flag and workflow_stage to FAILED
            await self.update_session_context(
                session_id,
                {
                    "workflow_stage": WorkflowStage.FAILED,
                    "requires_user_clarification": True,
                    "clarification_prompt": error_message,
                },
            )

            # Return error response
            return {
                "status": "error",
                "message": "Conversion failed",
                "session_id": session_id,
                "error_details": error_message,
                "error_type": type(e).__name__,
            }
