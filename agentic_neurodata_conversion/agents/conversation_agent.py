"""ConversationAgent implementation for Phase 4."""

import json
import logging
from pathlib import Path
import time
from typing import Any, Optional

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.config import settings
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import (
    DatasetInfo,
    MetadataExtractionResult,
    WorkflowStage,
)

logger = logging.getLogger(__name__)


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
        Detect dataset format from common electrophysiology recording systems.

        Supports detection of:
        - SpikeGLX/Neuropixels (.meta + .bin files)
        - Open Ephys (settings.xml, .continuous files)
        - Intan (.rhd, .rhs files)
        - Blackrock (.nev, .ns1-ns6 files)
        - Plexon (.plx, .pl2 files)
        - Axona (.set, .bin files)
        - NWB (.nwb files)
        - MEA formats (Multi-Electrode Arrays)

        Args:
            dataset_path: Path to dataset directory

        Returns:
            Format string identifying the recording system or "unknown"

        Raises:
            FileNotFoundError: If dataset_path does not exist
        """
        path = Path(dataset_path)

        # Check if path exists
        if not path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {dataset_path}")

        # 1. SpikeGLX/Neuropixels detection (Imec probes)
        # Look for .ap.meta/.lf.meta (action potential/local field) and corresponding .bin files
        meta_files = list(path.glob("*.ap.meta")) + list(path.glob("*.lf.meta")) + list(path.glob("*.imec*.meta"))
        bin_files = list(path.glob("*.ap.bin")) + list(path.glob("*.lf.bin")) + list(path.glob("*.imec*.bin"))
        if meta_files and bin_files:
            logger.info(f"Detected SpikeGLX format: {len(meta_files)} meta files, {len(bin_files)} bin files")
            return "spikeglx"

        # 2. Open Ephys detection
        # Check for settings.xml (primary indicator)
        if (path / "settings.xml").exists():
            logger.info("Detected Open Ephys format: settings.xml found")
            return "openephys"

        # Check for .continuous files (secondary indicator)
        continuous_files = list(path.glob("*.continuous"))
        if continuous_files:
            logger.info(f"Detected Open Ephys format: {len(continuous_files)} .continuous files")
            return "openephys"

        # Check for Open Ephys binary format (.oebin)
        if list(path.glob("*.oebin")) or (path / "structure.oebin").exists():
            logger.info("Detected Open Ephys Binary format: .oebin files found")
            return "openephys"

        # 3. Intan detection (.rhd = RHD2000 series, .rhs = RHS2000 series)
        rhd_files = list(path.glob("*.rhd"))
        rhs_files = list(path.glob("*.rhs"))
        if rhd_files or rhs_files:
            logger.info(f"Detected Intan format: {len(rhd_files)} .rhd files, {len(rhs_files)} .rhs files")
            return "intan"

        # 4. Blackrock detection (.nev = neural events, .nsX = continuous data at different sampling rates)
        nev_files = list(path.glob("*.nev"))
        ns_files = (list(path.glob("*.ns1")) + list(path.glob("*.ns2")) +
                   list(path.glob("*.ns3")) + list(path.glob("*.ns4")) +
                   list(path.glob("*.ns5")) + list(path.glob("*.ns6")))
        if nev_files or ns_files:
            logger.info(f"Detected Blackrock format: {len(nev_files)} .nev files, {len(ns_files)} .ns files")
            return "blackrock"

        # 5. Plexon detection (.plx = older format, .pl2 = newer format)
        plx_files = list(path.glob("*.plx"))
        pl2_files = list(path.glob("*.pl2"))
        if plx_files or pl2_files:
            logger.info(f"Detected Plexon format: {len(plx_files)} .plx files, {len(pl2_files)} .pl2 files")
            return "plexon"

        # 6. Axona detection (position tracking + neural data)
        set_files = list(path.glob("*.set"))
        axona_bin = list(path.glob("*.[0-9]"))  # Axona uses numbered extensions like .1, .2, etc.
        if set_files and axona_bin:
            logger.info(f"Detected Axona format: {len(set_files)} .set files")
            return "axona"

        # 7. NWB format detection (already in NWB format)
        nwb_files = list(path.glob("*.nwb"))
        if nwb_files:
            logger.info(f"Detected NWB format: {len(nwb_files)} .nwb files (already converted)")
            return "nwb"

        # 8. MEA (Multi-Electrode Array) formats
        # MCS (Multi Channel Systems)
        mcd_files = list(path.glob("*.mcd"))
        if mcd_files:
            logger.info(f"Detected MCS MEA format: {len(mcd_files)} .mcd files")
            return "mcs_mea"

        # HDF5-based MEA formats
        h5_files = list(path.glob("*.h5")) + list(path.glob("*.hdf5"))
        if h5_files:
            logger.info(f"Detected HDF5 format: {len(h5_files)} files (may be MEA or other format)")
            return "hdf5"

        # 9. NeuroNexus/Cambridge Neurotech probes (often in custom formats)
        # These sometimes use similar formats to Open Ephys or SpikeGLX

        # No recognized format indicators found
        logger.warning(f"Could not detect format for dataset at {dataset_path}")
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

    def _validate_spikeglx_structure(self, dataset_path: str) -> DatasetInfo:
        """
        Validate SpikeGLX/Neuropixels dataset structure.

        Checks for required SpikeGLX files and extracts dataset information:
        - .meta files must be present (.ap.meta or .lf.meta)
        - Corresponding .bin files must be present
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

        # Check for .meta files (required)
        meta_files = (list(path.glob("*.ap.meta")) +
                     list(path.glob("*.lf.meta")) +
                     list(path.glob("*.imec*.meta")))
        if not meta_files:
            raise ValueError(
                f"No .meta files found in SpikeGLX dataset: {dataset_path}"
            )

        # Check for corresponding .bin files (required)
        bin_files = (list(path.glob("*.ap.bin")) +
                    list(path.glob("*.lf.bin")) +
                    list(path.glob("*.imec*.bin")))
        if not bin_files:
            raise ValueError(
                f"No .bin files found in SpikeGLX dataset: {dataset_path}"
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
            format="spikeglx",
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
        logger.info(f"[conversation_agent] Calling LLM for metadata extraction (prompt length: {len(prompt)} chars)...")
        start_time = time.time()
        llm_response = await self.call_llm(prompt, system_message)
        logger.info(f"[conversation_agent] LLM call completed in {time.time() - start_time:.2f}s (response length: {len(llm_response)} chars)")

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

    def _process_metadata_for_conversion(
        self, metadata_result: MetadataExtractionResult
    ) -> tuple[MetadataExtractionResult, bool, Optional[str]]:
        """
        Process extracted metadata based on test_mode setting.

        In TEST MODE (settings.test_mode=True):
        - Automatically fill in missing required fields with defaults
        - Proceed with conversion immediately

        In PRODUCTION MODE (settings.test_mode=False):
        - Check for missing required fields
        - If any required fields are missing, request clarification from user
        - Return clarification prompt instead of auto-filling

        Args:
            metadata_result: Extracted metadata from files/LLM

        Returns:
            Tuple of (processed_metadata, requires_clarification, clarification_prompt)
        """
        # Define required fields for NWB conversion
        required_fields = {
            "subject_id": "unknown_subject",
            "species": "Homo sapiens",
            "sex": "U",  # U = Unknown
            "experimenter": "Unknown",
        }

        # Check which required fields are missing or None
        missing_fields = []
        metadata_dict = metadata_result.model_dump()

        for field, default_value in required_fields.items():
            if metadata_dict.get(field) is None or metadata_dict.get(field) == "":
                missing_fields.append(field)

        # If all required fields are present, return as-is
        if not missing_fields:
            logger.info("[conversation_agent] All required metadata fields are present")
            return metadata_result, False, None

        # TEST MODE: Auto-fill missing fields with defaults
        if settings.test_mode:
            logger.info(f"[conversation_agent] TEST MODE: Auto-filling {len(missing_fields)} missing fields with defaults")
            for field in missing_fields:
                setattr(metadata_result, field, required_fields[field])
            return metadata_result, False, None

        # PRODUCTION MODE: Request clarification from user
        logger.info(f"[conversation_agent] PRODUCTION MODE: Requesting user clarification for {len(missing_fields)} missing fields")

        clarification_prompt = f"""## Missing Required Metadata

The following required fields are missing or empty and need to be provided:

"""
        for field in missing_fields:
            if field == "subject_id":
                clarification_prompt += f"- **subject_id**: Identifier for the experimental subject (e.g., 'mouse_001', 'subject_A')\n"
            elif field == "species":
                clarification_prompt += f"- **species**: Scientific species name (e.g., 'Mus musculus' for mouse, 'Rattus norvegicus' for rat, 'Homo sapiens' for human)\n"
            elif field == "sex":
                clarification_prompt += f"- **sex**: Sex of the subject - must be one of: 'M' (Male), 'F' (Female), 'U' (Unknown), 'O' (Other)\n"
            elif field == "experimenter":
                clarification_prompt += f"- **experimenter**: Name(s) of the experimenter(s) who conducted the session\n"

        clarification_prompt += f"""
Please provide values for these fields to continue with the conversion. You can update them through the API at:
`POST /api/v1/sessions/{{session_id}}/clarify`

Or set TEST_MODE=true in your environment to automatically use default values for testing.
"""

        return metadata_result, True, clarification_prompt

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
        logger.info(f"[conversation_agent] Starting _initialize_session for session_id={session_id}, dataset_path={dataset_path}")
        try:
            # 1. Get session context
            logger.info(f"[conversation_agent] Fetching session context for {session_id}...")
            start_time = time.time()
            await self.get_session_context(session_id)
            logger.info(f"[conversation_agent] Session context fetched in {time.time() - start_time:.2f}s")

            # 2. Detect format
            logger.info("[conversation_agent] Detecting dataset format...")
            start_time = time.time()
            detected_format = self._detect_format(dataset_path)
            logger.info(f"[conversation_agent] Format detected as '{detected_format}' in {time.time() - start_time:.2f}s")

            # Check if format is supported
            if detected_format == "unknown":
                return {
                    "status": "error",
                    "message": f"Unsupported dataset format at {dataset_path}",
                    "session_id": session_id,
                }

            # 3. Validate structure based on detected format
            logger.info(f"[conversation_agent] Validating {detected_format} structure...")
            start_time = time.time()

            if detected_format == "openephys":
                dataset_info = self._validate_openephys_structure(dataset_path)
            elif detected_format == "spikeglx":
                dataset_info = self._validate_spikeglx_structure(dataset_path)
            else:
                # For other formats, create a generic DatasetInfo
                path = Path(dataset_path)
                total_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                file_count = sum(1 for f in path.rglob("*") if f.is_file())
                md_files = list(path.rglob("*.md"))
                metadata_files = [str(f.relative_to(path)) for f in md_files]

                dataset_info = DatasetInfo(
                    dataset_path=dataset_path,
                    format=detected_format,
                    total_size_bytes=total_size,
                    file_count=file_count,
                    has_metadata_files=len(metadata_files) > 0,
                    metadata_files=metadata_files,
                )

            logger.info(f"[conversation_agent] Structure validated in {time.time() - start_time:.2f}s")

            # 4. Extract metadata
            logger.info(f"[conversation_agent] Extracting metadata from {len(dataset_info.metadata_files)} .md files...")
            start_time = time.time()
            metadata_result = await self._extract_metadata_from_md_files(
                dataset_path, dataset_info.metadata_files
            )
            logger.info(f"[conversation_agent] Metadata extraction completed in {time.time() - start_time:.2f}s")

            # 4.5. Process metadata for conversion (test mode vs production)
            logger.info("[conversation_agent] Processing metadata (checking for missing required fields)...")
            processed_metadata, requires_clarification, clarification_prompt = self._process_metadata_for_conversion(
                metadata_result
            )

            # 5. Update session context
            logger.info("[conversation_agent] Updating session context...")
            start_time = time.time()
            updates = {
                "workflow_stage": WorkflowStage.COLLECTING_METADATA,
                "dataset_info": dataset_info.model_dump(),
                "metadata": processed_metadata.model_dump(),
                "current_agent": self.agent_name,
                "requires_user_clarification": requires_clarification,
            }

            # Add clarification prompt if needed
            if requires_clarification and clarification_prompt:
                updates["clarification_prompt"] = clarification_prompt
                logger.info(f"[conversation_agent] PRODUCTION MODE: Requesting user clarification for missing metadata fields")

            await self.update_session_context(session_id, updates)
            logger.info(f"[conversation_agent] Session context updated in {time.time() - start_time:.2f}s")

            # 6. Trigger conversion agent (only if no clarification needed)
            if requires_clarification:
                logger.info(f"[conversation_agent] Skipping conversion agent - waiting for user clarification")
                return {
                    "status": "clarification_required",
                    "message": "Please provide missing metadata fields",
                    "session_id": session_id,
                    "clarification_prompt": clarification_prompt,
                }

            # 6. Trigger conversion agent
            logger.info(f"[conversation_agent] Triggering conversion agent for session {session_id}")
            try:
                response = await self.http_client.post(
                    f"{self.mcp_server_url}/internal/route_message",
                    json={
                        "target_agent": "conversion_agent",
                        "message_type": "agent_execute",
                        "payload": {
                            "action": "convert_dataset",
                            "session_id": session_id,
                        },
                    },
                )
                response.raise_for_status()  # Raise exception for 4xx/5xx
                result = response.json()
                logger.info(f"[conversation_agent] Conversion agent triggered successfully: {result.get('status')}")
            except Exception as e:
                logger.error(f"[conversation_agent] Failed to trigger conversion agent: {type(e).__name__}: {e}")
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    logger.error(f"[conversation_agent] Response body: {e.response.text}")
                raise

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
            logger.info(f"[conversation_agent] Triggering conversion agent retry for session {session_id}")
            try:
                response = await self.http_client.post(
                    f"{self.mcp_server_url}/internal/route_message",
                    json={
                        "target_agent": "conversion_agent",
                        "message_type": "agent_execute",
                        "payload": {
                            "action": "convert_dataset",
                            "session_id": session_id,
                        },
                    },
                )
                response.raise_for_status()  # Raise exception for 4xx/5xx
                result = response.json()
                logger.info(f"[conversation_agent] Conversion agent retry triggered successfully: {result.get('status')}")
            except Exception as e:
                logger.error(f"[conversation_agent] Failed to trigger conversion agent retry: {type(e).__name__}: {e}")
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    logger.error(f"[conversation_agent] Response body: {e.response.text}")
                raise

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
