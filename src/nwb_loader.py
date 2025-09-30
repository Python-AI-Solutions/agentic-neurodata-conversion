"""NWB file loader and validator.

This module provides functions to load and validate NWB files using pynwb and h5py.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from pynwb import NWBHDF5IO, NWBFile
import h5py


@dataclass
class ValidationResult:
    """Result of NWB file validation."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    file_path: Path


def load_nwb_file(path: Path) -> NWBFile:
    """Load an NWB file and return NWBFile object.

    Args:
        path: Path to the NWB file

    Returns:
        NWBFile object

    Raises:
        FileNotFoundError: If file does not exist
        Exception: If file is corrupted or invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"NWB file not found: {path}")

    try:
        # Open with pynwb
        io = NWBHDF5IO(str(path), mode='r', load_namespaces=True)
        nwbfile = io.read()

        # Keep IO object alive by storing reference
        # This prevents the file from being closed prematurely
        nwbfile._io = io

        return nwbfile

    except Exception as e:
        raise Exception(f"Failed to load NWB file {path}: {str(e)}") from e


def validate_nwb_integrity(path: Path) -> ValidationResult:
    """Validate NWB file integrity.

    Args:
        path: Path to the NWB file

    Returns:
        ValidationResult with validation status and messages

    Raises:
        FileNotFoundError: If file does not exist
    """
    if not path.exists():
        raise FileNotFoundError(f"NWB file not found: {path}")

    errors = []
    warnings = []

    try:
        # Check if file is valid HDF5
        with h5py.File(path, 'r') as f:
            # Check for required NWB groups
            if 'general' not in f:
                warnings.append("Missing 'general' group")
            if 'acquisition' not in f:
                warnings.append("Missing 'acquisition' group")

        # Try to load with pynwb
        try:
            io = NWBHDF5IO(str(path), mode='r', load_namespaces=True)
            nwbfile = io.read()

            # Basic validation checks
            if not hasattr(nwbfile, 'identifier'):
                errors.append("Missing required field: identifier")
            if not hasattr(nwbfile, 'session_description'):
                errors.append("Missing required field: session_description")
            if not hasattr(nwbfile, 'session_start_time'):
                errors.append("Missing required field: session_start_time")

            io.close()

        except Exception as e:
            errors.append(f"Failed to load with pynwb: {str(e)}")

    except Exception as e:
        errors.append(f"Not a valid HDF5 file: {str(e)}")

    is_valid = len(errors) == 0

    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        file_path=path
    )