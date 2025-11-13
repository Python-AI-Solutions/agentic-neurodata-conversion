"""File versioning utility with SHA256 checksums.

Implements Story 8.7 requirement for versioned NWB files during correction loop.
"""

import hashlib
from pathlib import Path


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 checksum of a file.

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal SHA256 checksum string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_versioned_filename(original_path: Path, attempt_number: int, checksum: str = None) -> Path:
    """Generate versioned filename for correction attempts.

    Format: original_v{N}_{checksum_prefix}.nwb
    Example: mouse_001_v2_a3f9d1c8.nwb

    Args:
        original_path: Path to original NWB file
        attempt_number: Correction attempt number (1, 2, 3, ...)
        checksum: Optional SHA256 checksum (first 8 chars used)

    Returns:
        Path with versioned filename
    """
    stem = original_path.stem  # filename without extension
    suffix = original_path.suffix  # .nwb
    parent = original_path.parent

    if attempt_number == 0:
        # Original file - no version suffix
        return original_path

    if checksum:
        # Include checksum prefix for integrity verification
        version_suffix = f"_v{attempt_number}_{checksum[:8]}"
    else:
        # Just version number
        version_suffix = f"_v{attempt_number}"

    versioned_name = f"{stem}{version_suffix}{suffix}"
    return parent / versioned_name


def create_versioned_file(original_path: Path, attempt_number: int, compute_checksum: bool = True) -> tuple[Path, str]:
    """Create a versioned copy of an NWB file.

    Args:
        original_path: Path to file to version
        attempt_number: Correction attempt number
        compute_checksum: Whether to compute SHA256 checksum

    Returns:
        Tuple of (versioned_path, checksum)

    Raises:
        FileNotFoundError: If original file doesn't exist
    """
    if not original_path.exists():
        raise FileNotFoundError(f"File not found: {original_path}")

    checksum = None
    if compute_checksum:
        checksum = compute_sha256(original_path)

    versioned_path = get_versioned_filename(original_path, attempt_number, checksum)

    # Copy file to versioned path
    import shutil

    shutil.copy2(original_path, versioned_path)

    return versioned_path, checksum


def verify_file_integrity(file_path: Path, expected_checksum: str) -> bool:
    """Verify file integrity using SHA256 checksum.

    Args:
        file_path: Path to file
        expected_checksum: Expected SHA256 checksum

    Returns:
        True if checksums match, False otherwise
    """
    if not file_path.exists():
        return False

    actual_checksum = compute_sha256(file_path)
    return actual_checksum == expected_checksum


def get_all_versions(base_path: Path) -> list[Path]:
    """Get all version files for a base NWB file.

    Args:
        base_path: Path to original NWB file

    Returns:
        List of all version file paths (sorted by version number)
    """
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    versions = []

    # Original file
    if base_path.exists():
        versions.append(base_path)

    # Find all versioned files
    pattern = f"{stem}_v*{suffix}"
    for versioned_file in parent.glob(pattern):
        versions.append(versioned_file)

    # Sort by version number
    def extract_version(path: Path) -> int:
        try:
            # Extract v{N} from filename
            name = path.stem
            if "_v" in name:
                version_part = name.split("_v")[1].split("_")[0]
                return int(version_part)
            return 0
        except (ValueError, IndexError):
            return 0

    versions.sort(key=extract_version)
    return versions
