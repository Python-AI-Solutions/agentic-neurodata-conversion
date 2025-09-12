"""
File utility functions for the agentic neurodata conversion system.

This module provides common file operations, path handling, and file system
utilities used throughout the conversion pipeline.
"""

from collections.abc import Generator
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class FileUtils:
    """
    Utility class for file operations and path handling.

    Provides standardized methods for file operations, directory traversal,
    file validation, and path manipulation used across the system.
    """

    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """
        Ensure directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure exists

        Returns:
            Path object for the directory
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
        return path

    @staticmethod
    def safe_filename(filename: str, replacement: str = "_") -> str:
        """
        Create safe filename by replacing invalid characters.

        Args:
            filename: Original filename
            replacement: Character to replace invalid characters with

        Returns:
            Safe filename string
        """
        # Characters that are invalid in filenames
        invalid_chars = '<>:"/\\|?*'

        safe_name = filename
        for char in invalid_chars:
            safe_name = safe_name.replace(char, replacement)

        # Remove leading/trailing whitespace and dots
        safe_name = safe_name.strip(". ")

        # Ensure filename is not empty
        if not safe_name:
            safe_name = "unnamed_file"

        logger.debug(f"Created safe filename: '{filename}' -> '{safe_name}'")
        return safe_name

    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        size = file_path.stat().st_size
        logger.debug(f"File size: {file_path} = {size} bytes")
        return size

    @staticmethod
    def get_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
        """
        Calculate file hash for integrity checking.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm ('md5', 'sha1', 'sha256')

        Returns:
            Hexadecimal hash string
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        hash_obj = hashlib.new(algorithm)

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)

        file_hash = hash_obj.hexdigest()
        logger.debug(f"File hash ({algorithm}): {file_path} = {file_hash}")
        return file_hash

    @staticmethod
    def find_files(
        directory: Union[str, Path],
        pattern: str = "*",
        recursive: bool = True,
        include_dirs: bool = False,
    ) -> list[Path]:
        """
        Find files matching pattern in directory.

        Args:
            directory: Directory to search
            pattern: Glob pattern to match
            recursive: Whether to search recursively
            include_dirs: Whether to include directories in results

        Returns:
            List of matching file paths
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []

        glob_pattern = f"**/{pattern}" if recursive else pattern

        matches = []
        for path in directory.glob(glob_pattern):
            if include_dirs or path.is_file():
                matches.append(path)

        logger.debug(f"Found {len(matches)} files matching '{pattern}' in {directory}")
        return matches

    @staticmethod
    def copy_file(
        source: Union[str, Path], destination: Union[str, Path], overwrite: bool = False
    ) -> Path:
        """
        Copy file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing files

        Returns:
            Path to copied file
        """
        source = Path(source)
        destination = Path(destination)

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"Destination exists and overwrite=False: {destination}"
            )

        # Ensure destination directory exists
        FileUtils.ensure_directory(destination.parent)

        shutil.copy2(source, destination)
        logger.info(f"Copied file: {source} -> {destination}")
        return destination

    @staticmethod
    def move_file(
        source: Union[str, Path], destination: Union[str, Path], overwrite: bool = False
    ) -> Path:
        """
        Move file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing files

        Returns:
            Path to moved file
        """
        source = Path(source)
        destination = Path(destination)

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"Destination exists and overwrite=False: {destination}"
            )

        # Ensure destination directory exists
        FileUtils.ensure_directory(destination.parent)

        shutil.move(str(source), str(destination))
        logger.info(f"Moved file: {source} -> {destination}")
        return destination

    @staticmethod
    def delete_file(file_path: Union[str, Path], missing_ok: bool = True) -> bool:
        """
        Delete file if it exists.

        Args:
            file_path: Path to file to delete
            missing_ok: Whether to ignore missing files

        Returns:
            True if file was deleted, False if it didn't exist
        """
        file_path = Path(file_path)

        if not file_path.exists():
            if missing_ok:
                logger.debug(f"File not found (ignored): {file_path}")
                return False
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        file_path.unlink()
        logger.info(f"Deleted file: {file_path}")
        return True

    @staticmethod
    def get_directory_size(directory: Union[str, Path]) -> int:
        """
        Calculate total size of directory and its contents.

        Args:
            directory: Directory path

        Returns:
            Total size in bytes
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        total_size = 0
        for path in directory.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size

        logger.debug(f"Directory size: {directory} = {total_size} bytes")
        return total_size

    @staticmethod
    def cleanup_directory(
        directory: Union[str, Path],
        pattern: str = "*",
        older_than_days: Optional[int] = None,
    ) -> int:
        """
        Clean up files in directory matching criteria.

        Args:
            directory: Directory to clean
            pattern: Glob pattern for files to delete
            older_than_days: Only delete files older than this many days

        Returns:
            Number of files deleted
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return 0

        import time

        current_time = time.time()
        cutoff_time = (
            current_time - (older_than_days * 24 * 60 * 60) if older_than_days else 0
        )

        deleted_count = 0
        for file_path in directory.glob(pattern):
            if file_path.is_file() and (
                older_than_days is None or file_path.stat().st_mtime < cutoff_time
            ):
                file_path.unlink()
                deleted_count += 1
                logger.debug(f"Deleted: {file_path}")

        logger.info(f"Cleaned up {deleted_count} files from {directory}")
        return deleted_count

    @staticmethod
    def read_json_file(file_path: Union[str, Path]) -> dict[str, Any]:
        """
        Read and parse JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            logger.debug(f"Read JSON file: {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {file_path}: {e}")
            raise

    @staticmethod
    def write_json_file(
        data: dict[str, Any],
        file_path: Union[str, Path],
        indent: int = 2,
        overwrite: bool = True,
    ) -> Path:
        """
        Write data to JSON file.

        Args:
            data: Data to write
            file_path: Path to output file
            indent: JSON indentation
            overwrite: Whether to overwrite existing files

        Returns:
            Path to written file
        """
        file_path = Path(file_path)

        if file_path.exists() and not overwrite:
            raise FileExistsError(f"File exists and overwrite=False: {file_path}")

        # Ensure directory exists
        FileUtils.ensure_directory(file_path.parent)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            logger.debug(f"Wrote JSON file: {file_path}")
            return file_path
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to write JSON to {file_path}: {e}")
            raise

    @staticmethod
    def create_temp_directory(prefix: str = "agentic_neuro_", suffix: str = "") -> Path:
        """
        Create temporary directory.

        Args:
            prefix: Prefix for directory name
            suffix: Suffix for directory name

        Returns:
            Path to created temporary directory
        """
        import tempfile

        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, suffix=suffix))
        logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir

    @staticmethod
    def walk_directory(
        directory: Union[str, Path],
        include_files: bool = True,
        include_dirs: bool = False,
    ) -> Generator[Path, None, None]:
        """
        Walk directory tree yielding paths.

        Args:
            directory: Directory to walk
            include_files: Whether to yield file paths
            include_dirs: Whether to yield directory paths

        Yields:
            Path objects for files and/or directories
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return

        for root, dirs, files in os.walk(directory):
            root_path = Path(root)

            if include_dirs:
                for dir_name in dirs:
                    yield root_path / dir_name

            if include_files:
                for file_name in files:
                    yield root_path / file_name
