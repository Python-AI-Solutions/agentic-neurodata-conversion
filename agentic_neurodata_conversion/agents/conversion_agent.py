"""ConversionAgent for NWB file generation (Phase 5 implementation)."""

from datetime import datetime
from pathlib import Path
import time
from typing import Any

from neuroconv.datainterfaces import OpenEphysRecordingInterface

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
        self, session_id: str, dataset_path: str, metadata: dict
    ) -> ConversionResults:
        """
        Convert OpenEphys dataset to NWB format using NeuroConv.

        Uses OpenEphysRecordingInterface from neuroconv to convert the dataset,
        applies metadata, and runs conversion with gzip compression.

        Args:
            session_id: Session identifier for output naming
            dataset_path: Path to OpenEphys dataset directory
            metadata: Metadata dictionary for NWB file

        Returns:
            ConversionResults with file path and conversion metrics

        Raises:
            Exception: If conversion fails (corrupt data, missing files, etc.)
        """
        start_time = time.time()

        try:
            # Create OpenEphys interface
            interface = OpenEphysRecordingInterface(folder_path=dataset_path)

            # Prepare metadata for NWB
            nwb_metadata = self._prepare_metadata(metadata)

            # Set output path
            output_dir = Path.cwd() / "output" / "nwb_files"
            output_dir.mkdir(parents=True, exist_ok=True)
            nwb_file_path = output_dir / f"{session_id}.nwb"

            # Run conversion with gzip compression
            interface.run_conversion(
                nwbfile_path=str(nwb_file_path),
                metadata=nwb_metadata,
                overwrite=True,
                compression="gzip",
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
                conversion_log=f"Conversion completed successfully in {duration:.2f}s",
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

        # Subject metadata
        if any(
            key in session_metadata
            for key in ["subject_id", "species", "age", "sex", "subject_description"]
        ):
            subject_metadata = {}

            if "subject_id" in session_metadata:
                subject_metadata["subject_id"] = session_metadata["subject_id"]

            if "species" in session_metadata:
                subject_metadata["species"] = session_metadata["species"]

            if "age" in session_metadata:
                subject_metadata["age"] = session_metadata["age"]

            if "sex" in session_metadata:
                subject_metadata["sex"] = session_metadata["sex"]

            if "subject_description" in session_metadata:
                subject_metadata["description"] = session_metadata[
                    "subject_description"
                ]

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

        # Session start time (with default)
        if "session_start_time" in session_metadata:
            nwbfile_metadata["session_start_time"] = session_metadata[
                "session_start_time"
            ]
        else:
            # Default to current time in ISO format
            nwbfile_metadata["session_start_time"] = datetime.utcnow().isoformat() + "Z"

        # Experimenter (convert to list if string)
        if "experimenter" in session_metadata:
            experimenter = session_metadata["experimenter"]
            if isinstance(experimenter, str):
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
                    "action": "validate_nwb",
                    "payload": {"nwb_file_path": conversion_results.nwb_file_path},
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
