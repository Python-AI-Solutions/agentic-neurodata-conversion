"""ConversationAgent implementation for Phase 4."""

import json
from pathlib import Path
from typing import Any, Optional

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import (
    DatasetInfo,
    MetadataExtractionResult,
    WorkflowStage,
)


class ConversationAgent(BaseAgent):
    """Conversation agent for dataset format detection, validation, and metadata extraction."""

    def get_capabilities(self) -> list[str]:
        """
        Return conversation agent capabilities.

        Returns:
            List of capability strings
        """
        return ["initialize_session", "handle_clarification"]

    def _detect_format(self, dataset_path: str) -> str:
        """
        Detect dataset format (OpenEphys or unknown).

        Checks for OpenEphys indicators in this order:
        1. settings.xml file presence
        2. .continuous files presence

        Args:
            dataset_path: Path to dataset directory

        Returns:
            Format string: "openephys" or "unknown"

        Raises:
            FileNotFoundError: If dataset_path does not exist
        """
        path = Path(dataset_path)

        # Check if path exists
        if not path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {dataset_path}")

        # Check for settings.xml (primary OpenEphys indicator)
        if (path / "settings.xml").exists():
            return "openephys"

        # Check for .continuous files (secondary OpenEphys indicator)
        continuous_files = list(path.glob("*.continuous"))
        if continuous_files:
            return "openephys"

        # No recognized format indicators found
        return "unknown"

    def _validate_openephys_structure(self, dataset_path: str) -> DatasetInfo:
        """
        Validate OpenEphys dataset structure.

        Checks for required OpenEphys files and extracts dataset information:
        - settings.xml must be present
        - At least one .continuous file must be present
        - Calculates total size and file count
        - Detects metadata files (.md)

        Args:
            dataset_path: Path to dataset directory

        Returns:
            DatasetInfo with all fields populated

        Raises:
            ValueError: If required files are missing
        """
        path = Path(dataset_path)

        # Check for settings.xml (required)
        settings_file = path / "settings.xml"
        if not settings_file.exists():
            raise ValueError(
                f"settings.xml not found in OpenEphys dataset: {dataset_path}"
            )

        # Check for .continuous files (required)
        continuous_files = list(path.glob("*.continuous"))
        if not continuous_files:
            raise ValueError(
                f"No .continuous files found in OpenEphys dataset: {dataset_path}"
            )

        # Calculate total size and file count
        total_size = 0
        file_count = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1

        # Find .md files
        md_files = list(path.rglob("*.md"))
        metadata_files = [str(f.relative_to(path)) for f in md_files]
        has_metadata_files = len(metadata_files) > 0

        # Create and return DatasetInfo
        return DatasetInfo(
            dataset_path=dataset_path,
            format="openephys",
            total_size_bytes=total_size,
            file_count=file_count,
            has_metadata_files=has_metadata_files,
            metadata_files=metadata_files,
        )

    async def _extract_metadata_from_md_files(
        self, dataset_path: str, md_files: list[str]
    ) -> MetadataExtractionResult:
        """
        Extract metadata from .md files using LLM.

        Reads all .md files, combines their content, and uses LLM to extract
        structured metadata in JSON format. Handles errors gracefully.

        Args:
            dataset_path: Path to dataset directory
            md_files: List of .md file paths (relative to dataset_path)

        Returns:
            MetadataExtractionResult with extracted metadata
        """
        # Return empty result if no .md files
        if not md_files:
            return MetadataExtractionResult()

        # Read all .md files and combine content
        path = Path(dataset_path)
        combined_content = []

        for md_file in md_files:
            md_path = path / md_file
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                combined_content.append(f"=== {md_file} ===\n{content}\n")

        full_content = "\n".join(combined_content)

        # Create LLM prompt requesting JSON output
        prompt = f"""Extract metadata from the following dataset documentation files.
Return ONLY a valid JSON object (no markdown, no code blocks, no additional text) with the following fields:
- subject_id: Identifier for the experimental subject
- species: Scientific name (e.g., "Mus musculus" for mouse, "Rattus norvegicus" for rat)
- age: Age of subject (e.g., "P56", "8 weeks")
- sex: Sex of subject ("Male", "Female", or "Unknown")
- session_start_time: ISO 8601 timestamp (e.g., "2024-01-15T12:00:00")
- experimenter: Name of experimenter
- device_name: Recording device name
- manufacturer: Device manufacturer
- recording_location: Brain region or recording location
- description: Brief session description
- extraction_confidence: Object with confidence level ("high", "medium", "low") for each extracted field

Use null for any fields you cannot determine. Standardize common names to scientific names (e.g., "mouse" -> "Mus musculus").

Dataset documentation:
{full_content}

Return ONLY the JSON object:"""

        system_message = "You are a metadata extraction assistant. Return ONLY valid JSON with no additional formatting or text."

        # Call LLM
        llm_response = await self.call_llm(prompt, system_message)

        # Try to parse JSON response
        try:
            # Remove markdown code blocks if present
            cleaned_response = llm_response.strip()
            if cleaned_response.startswith("```"):
                # Extract JSON from code block
                lines = cleaned_response.split("\n")
                json_lines = []
                in_code_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block or (not line.startswith("```")):
                        json_lines.append(line)
                cleaned_response = "\n".join(json_lines).strip()

            # Parse JSON
            metadata_dict = json.loads(cleaned_response)

            # Extract fields with defaults
            return MetadataExtractionResult(
                subject_id=metadata_dict.get("subject_id"),
                species=metadata_dict.get("species"),
                age=metadata_dict.get("age"),
                sex=metadata_dict.get("sex"),
                session_start_time=metadata_dict.get("session_start_time"),
                experimenter=metadata_dict.get("experimenter"),
                device_name=metadata_dict.get("device_name"),
                manufacturer=metadata_dict.get("manufacturer"),
                recording_location=metadata_dict.get("recording_location"),
                description=metadata_dict.get("description"),
                extraction_confidence=metadata_dict.get("extraction_confidence", {}),
                llm_extraction_log=llm_response,
            )

        except (json.JSONDecodeError, KeyError, TypeError):
            # Return empty metadata but preserve the LLM response for debugging
            return MetadataExtractionResult(
                llm_extraction_log=llm_response,
            )

    async def _initialize_session(
        self, session_id: str, dataset_path: str
    ) -> dict[str, Any]:
        """
        Initialize session with format detection, validation, and metadata extraction.

        Workflow:
        1. Get session context
        2. Detect dataset format
        3. Validate dataset structure
        4. Extract metadata from .md files
        5. Update session context
        6. Trigger conversion agent
        7. Return success

        Args:
            session_id: Session identifier
            dataset_path: Path to dataset directory

        Returns:
            Result dictionary with status and extracted information
        """
        try:
            # 1. Get session context
            await self.get_session_context(session_id)

            # 2. Detect format
            detected_format = self._detect_format(dataset_path)

            # Check if format is supported
            if detected_format == "unknown":
                return {
                    "status": "error",
                    "message": f"Unsupported dataset format at {dataset_path}",
                    "session_id": session_id,
                }

            # 3. Validate structure
            dataset_info = self._validate_openephys_structure(dataset_path)

            # 4. Extract metadata
            metadata_result = await self._extract_metadata_from_md_files(
                dataset_path, dataset_info.metadata_files
            )

            # 5. Update session context
            updates = {
                "workflow_stage": WorkflowStage.COLLECTING_METADATA,
                "dataset_info": dataset_info.model_dump(),
                "metadata": metadata_result.model_dump(),
                "current_agent": self.agent_name,
            }
            await self.update_session_context(session_id, updates)

            # 6. Trigger conversion agent
            await self.http_client.post(
                f"{self.mcp_server_url}/internal/route_message",
                json={
                    "session_id": session_id,
                    "target_agent": "conversion_agent",
                    "message_type": "agent_execute",
                    "payload": {
                        "action": "convert_dataset",
                    },
                },
            )

            # 7. Return success
            return {
                "status": "success",
                "message": "Session initialized successfully",
                "session_id": session_id,
                "dataset_info": dataset_info.model_dump(),
                "metadata": metadata_result.model_dump(),
            }

        except FileNotFoundError as e:
            return {
                "status": "error",
                "message": str(e),
                "session_id": session_id,
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e),
                "session_id": session_id,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error during initialization: {str(e)}",
                "session_id": session_id,
            }

    async def _handle_clarification(
        self,
        session_id: str,
        user_input: Optional[str],
        updated_metadata: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Handle user clarification for error resolution.

        Updates session metadata based on user input and triggers conversion
        agent to retry the conversion process.

        Args:
            session_id: Session identifier
            user_input: User's clarification text (optional)
            updated_metadata: Dictionary of metadata fields to update (optional)

        Returns:
            Result dictionary with status
        """
        try:
            # 1. Get session context
            session = await self.get_session_context(session_id)

            # 2. Update metadata from user input
            current_metadata = session.metadata or MetadataExtractionResult()
            updated_metadata_dict = current_metadata.model_dump()

            # Apply updates from updated_metadata if provided
            if updated_metadata:
                for key, value in updated_metadata.items():
                    if hasattr(current_metadata, key):
                        updated_metadata_dict[key] = value

            # 3. Clear clarification flags
            updates = {
                "metadata": updated_metadata_dict,
                "requires_user_clarification": False,
                "clarification_prompt": None,
            }
            await self.update_session_context(session_id, updates)

            # 4. Trigger conversion agent retry
            await self.http_client.post(
                f"{self.mcp_server_url}/internal/route_message",
                json={
                    "session_id": session_id,
                    "target_agent": "conversion_agent",
                    "message_type": "agent_execute",
                    "payload": {
                        "action": "convert_dataset",
                    },
                },
            )

            # 5. Return success
            return {
                "status": "success",
                "message": "Clarification processed successfully",
                "session_id": session_id,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing clarification: {str(e)}",
                "session_id": session_id,
            }

    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """
        Handle incoming MCP message.

        Routes message to appropriate handler based on action in payload.

        Args:
            message: MCP message to handle

        Returns:
            Result dictionary from handler
        """
        # Extract action from payload
        action = message.payload.get("action", "")
        session_id = message.session_id or message.payload.get("session_id", "")

        if action == "initialize_session":
            # Extract dataset_path directly from payload
            dataset_path = message.payload.get("dataset_path")
            if not dataset_path:
                return {
                    "status": "error",
                    "message": "Missing required parameter: dataset_path",
                    "session_id": session_id,
                }

            return await self._initialize_session(session_id, dataset_path)

        elif action == "handle_clarification":
            # Extract parameters directly from payload
            user_input = message.payload.get("user_input")
            updated_metadata = message.payload.get("updated_metadata")

            return await self._handle_clarification(
                session_id, user_input, updated_metadata
            )

        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}",
                "session_id": session_id,
            }
