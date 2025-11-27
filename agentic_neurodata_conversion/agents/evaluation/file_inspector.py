"""File inspection module for evaluation agent.

Handles:
- NWB file metadata extraction
- File size and creation date tracking
- Subject and experimental metadata extraction
- Provenance tracking for metadata sources
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileInspector:
    """Handles NWB file metadata extraction.

    Extracts comprehensive file information from NWB files using both
    h5py (fast, low-level) and PyNWB (comprehensive, high-level) approaches.

    Features:
    - File-level metadata (version, identifier, session info)
    - General metadata (experimenter, institution, lab)
    - Subject metadata (species, age, sex, etc.)
    - Provenance tracking for each field
    - Dual extraction strategy (h5py first, PyNWB fallback)
    """

    def __init__(self):
        """Initialize file inspector."""
        pass

    def extract_file_info(self, nwb_path: str) -> dict[str, Any]:
        """Extract comprehensive file information from NWB file for reports.

        Uses a two-tier approach:
        1. h5py for fast, direct HDF5 access
        2. PyNWB fallback for complete NWB object model access

        Args:
            nwb_path: Path to NWB file

        Returns:
            Dictionary with complete file metadata including:
            - File-level: nwb_version, identifier, session_description, etc.
            - General: experimenter, institution, lab, experiment_description
            - Subject: subject_id, species, sex, age, etc.
            - Provenance: _provenance dict tracking source of each field
            - Source files: _source_files dict mapping fields to file paths
        """
        # Initialize with all possible NWB metadata fields
        file_info: dict[str, Any] = {
            # File-level metadata
            "nwb_version": "Unknown",
            "file_size_bytes": 0,
            "creation_date": "Unknown",
            "identifier": "Unknown",
            "session_description": "N/A",
            "session_start_time": "N/A",
            "session_id": "N/A",
            # General metadata (experimenter, institution, lab)
            "experimenter": [],
            "institution": "N/A",
            "lab": "N/A",
            "experiment_description": "N/A",
            # Subject metadata
            "subject_id": "N/A",
            "species": "N/A",
            "sex": "N/A",
            "age": "N/A",
            "date_of_birth": "N/A",
            "description": "N/A",
            "genotype": "N/A",
            "strain": "N/A",
            # Provenance tracking - record source of each metadata field
            "_provenance": {},
            "_source_files": {},
        }

        def decode_value(value: Any) -> str:
            """Helper to decode bytes to string."""
            if isinstance(value, bytes):
                return value.decode("utf-8")
            elif isinstance(value, str):
                return value
            else:
                return str(value)

        try:
            nwb_file_path = Path(nwb_path)

            # Get file size and creation date
            if nwb_file_path.exists():
                file_info["file_size_bytes"] = nwb_file_path.stat().st_size
                file_info["creation_date"] = datetime.fromtimestamp(nwb_file_path.stat().st_ctime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            # Try to read NWB metadata using h5py (faster)
            try:
                import h5py

                with h5py.File(nwb_path, "r") as f:
                    # Debug logging
                    logger.debug(f"Reading NWB file with h5py: {nwb_path}")
                    logger.debug(f"Root level groups: {list(f.keys())}")
                    logger.debug(f"Root level attrs: {list(f.attrs.keys())}")

                    # Helper to set top-level attrs with provenance
                    def set_attr_with_provenance(attr_name: str, field_name: str | None = None) -> None:
                        """Extract and set a root-level attribute with provenance tracking."""
                        if field_name is None:
                            field_name = attr_name
                        if attr_name in f.attrs:
                            value = decode_value(f.attrs[attr_name])
                            file_info[field_name] = value
                            provenance_dict: dict[str, Any] = file_info["_provenance"]
                            provenance_dict[field_name] = "file-extracted"
                            source_dict: dict[str, Any] = file_info["_source_files"]
                            source_dict[field_name] = nwb_path

                    # Extract top-level attributes
                    set_attr_with_provenance("nwb_version")
                    set_attr_with_provenance("identifier")
                    set_attr_with_provenance("session_description")
                    set_attr_with_provenance("session_start_time")

                    # Extract general metadata
                    if "general" in f:
                        general = f["general"]
                        logger.debug("Found /general group")
                        logger.debug(f"/general attrs: {list(general.attrs.keys())}")
                        logger.debug(f"/general subgroups: {list(general.keys())}")

                        # CRITICAL FIX: Check both attributes AND datasets
                        # NeuroConv writes metadata as datasets, not attributes!
                        def get_value(group: Any, key: str) -> Any:
                            """Get value from either attribute or dataset."""
                            if key in group.attrs:
                                return group.attrs[key]
                            elif key in group:
                                # It's a dataset - read the value
                                return group[key][()]
                            return None

                        def set_with_provenance(
                            field_name: str,
                            value: Any,
                            provenance: str = "file-extracted",
                            source_file: str | None = None,
                        ) -> None:
                            """Set a field value and track its provenance."""
                            file_info[field_name] = value
                            provenance_dict: dict[str, Any] = file_info["_provenance"]
                            provenance_dict[field_name] = provenance
                            if source_file:
                                source_dict: dict[str, Any] = file_info["_source_files"]
                                source_dict[field_name] = source_file

                        # Experimenter (can be string or array)
                        exp_value = get_value(general, "experimenter")
                        if exp_value is not None:
                            if isinstance(exp_value, bytes):
                                set_with_provenance(
                                    "experimenter", [exp_value.decode("utf-8")], "file-extracted", nwb_path
                                )
                            elif isinstance(exp_value, str):
                                set_with_provenance("experimenter", [exp_value], "file-extracted", nwb_path)
                            elif isinstance(exp_value, (list, tuple)):
                                set_with_provenance(
                                    "experimenter",
                                    [e.decode("utf-8") if isinstance(e, bytes) else str(e) for e in exp_value],
                                    "file-extracted",
                                    nwb_path,
                                )
                            else:
                                # Handle numpy arrays or other iterable types
                                try:
                                    set_with_provenance(
                                        "experimenter", [decode_value(e) for e in exp_value], "file-extracted", nwb_path
                                    )
                                except TypeError:
                                    set_with_provenance(
                                        "experimenter", [decode_value(exp_value)], "file-extracted", nwb_path
                                    )

                        # Institution
                        inst_value = get_value(general, "institution")
                        if inst_value is not None:
                            set_with_provenance("institution", decode_value(inst_value), "file-extracted", nwb_path)

                        # Lab
                        lab_value = get_value(general, "lab")
                        if lab_value is not None:
                            set_with_provenance("lab", decode_value(lab_value), "file-extracted", nwb_path)

                        # Experiment description
                        exp_desc_value = get_value(general, "experiment_description")
                        if exp_desc_value is not None:
                            set_with_provenance(
                                "experiment_description", decode_value(exp_desc_value), "file-extracted", nwb_path
                            )

                        # Session ID
                        session_id_value = get_value(general, "session_id")
                        if session_id_value is not None:
                            set_with_provenance(
                                "session_id", decode_value(session_id_value), "file-extracted", nwb_path
                            )

                        # Extract subject metadata
                        if "subject" in general:
                            subject_group = general["subject"]

                            # Check both attrs and datasets for subject fields
                            subj_id_value = get_value(subject_group, "subject_id")
                            if subj_id_value is not None:
                                set_with_provenance(
                                    "subject_id", decode_value(subj_id_value), "file-extracted", nwb_path
                                )

                            species_value = get_value(subject_group, "species")
                            if species_value is not None:
                                set_with_provenance("species", decode_value(species_value), "file-extracted", nwb_path)

                            sex_value = get_value(subject_group, "sex")
                            if sex_value is not None:
                                set_with_provenance("sex", decode_value(sex_value), "file-extracted", nwb_path)

                            age_value = get_value(subject_group, "age")
                            if age_value is not None:
                                set_with_provenance("age", decode_value(age_value), "file-extracted", nwb_path)

                            dob_value = get_value(subject_group, "date_of_birth")
                            if dob_value is not None:
                                set_with_provenance(
                                    "date_of_birth", decode_value(dob_value), "file-extracted", nwb_path
                                )

                            desc_value = get_value(subject_group, "description")
                            if desc_value is not None:
                                set_with_provenance("description", decode_value(desc_value), "file-extracted", nwb_path)

                            geno_value = get_value(subject_group, "genotype")
                            if geno_value is not None:
                                set_with_provenance("genotype", decode_value(geno_value), "file-extracted", nwb_path)

                            strain_value = get_value(subject_group, "strain")
                            if strain_value is not None:
                                set_with_provenance("strain", decode_value(strain_value), "file-extracted", nwb_path)

            except Exception as e:
                # If h5py fails, try PyNWB
                logger.debug(f"h5py extraction failed: {e}, trying PyNWB...")
                try:
                    from pynwb import NWBHDF5IO

                    with NWBHDF5IO(nwb_path, "r") as io:
                        nwbfile = io.read()

                        # File-level attributes
                        file_info["nwb_version"] = str(getattr(nwbfile, "nwb_version", "Unknown"))
                        file_info["identifier"] = str(getattr(nwbfile, "identifier", "Unknown"))
                        file_info["session_description"] = str(getattr(nwbfile, "session_description", "N/A"))
                        file_info["session_start_time"] = str(getattr(nwbfile, "session_start_time", "N/A"))
                        file_info["session_id"] = str(getattr(nwbfile, "session_id", "N/A"))

                        # General metadata
                        experimenter = getattr(nwbfile, "experimenter", None)
                        if experimenter:
                            file_info["experimenter"] = (
                                list(experimenter)
                                if hasattr(experimenter, "__iter__") and not isinstance(experimenter, str)
                                else [str(experimenter)]
                            )

                        file_info["institution"] = str(getattr(nwbfile, "institution", "N/A"))
                        file_info["lab"] = str(getattr(nwbfile, "lab", "N/A"))
                        file_info["experiment_description"] = str(getattr(nwbfile, "experiment_description", "N/A"))

                        # Subject metadata
                        if nwbfile.subject:
                            file_info["subject_id"] = str(getattr(nwbfile.subject, "subject_id", "N/A"))
                            file_info["species"] = str(getattr(nwbfile.subject, "species", "N/A"))
                            file_info["sex"] = str(getattr(nwbfile.subject, "sex", "N/A"))
                            file_info["age"] = str(getattr(nwbfile.subject, "age", "N/A"))
                            file_info["date_of_birth"] = str(getattr(nwbfile.subject, "date_of_birth", "N/A"))
                            file_info["description"] = str(getattr(nwbfile.subject, "description", "N/A"))
                            file_info["genotype"] = str(getattr(nwbfile.subject, "genotype", "N/A"))
                            file_info["strain"] = str(getattr(nwbfile.subject, "strain", "N/A"))
                        else:
                            logger.warning("NWB file has no subject object!")

                        logger.debug(
                            f"PyNWB extraction succeeded: experimenter={file_info['experimenter']}, "
                            f"institution={file_info['institution']}, subject_id={file_info['subject_id']}"
                        )

                except Exception as pynwb_error:
                    logger.exception(f"Could not extract file info with PyNWB either: {pynwb_error}")

        except Exception as e:
            logger.exception(f"Error extracting file info: {e}")

        return file_info
