"""
File utility functions for the agentic neurodata conversion system.

This module provides common file operations and utilities used throughout
the conversion pipeline.
"""

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class FileUtils:
    """
    Utility class for common file operations.
    
    Provides methods for file validation, copying, hashing, and other
    file system operations commonly needed in the conversion pipeline.
    """
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.
        
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
    def safe_copy_file(
        source: Union[str, Path],
        destination: Union[str, Path],
        overwrite: bool = False
    ) -> Path:
        """
        Safely copy a file with validation and error handling.
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing destination file
            
        Returns:
            Path to the copied file
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            FileExistsError: If destination exists and overwrite is False
        """
        source = Path(source)
        destination = Path(destination)
        
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Destination file exists: {destination}")
        
        # Ensure destination directory exists
        FileUtils.ensure_directory(destination.parent)
        
        # Copy file
        shutil.copy2(source, destination)
        logger.info(f"Copied file: {source} -> {destination}")
        
        return destination
    
    @staticmethod
    def calculate_file_hash(
        file_path: Union[str, Path],
        algorithm: str = "sha256"
    ) -> str:
        """
        Calculate hash of a file.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use (md5, sha1, sha256, etc.)
            
        Returns:
            Hexadecimal hash string
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        file_hash = hash_obj.hexdigest()
        logger.debug(f"Calculated {algorithm} hash for {file_path}: {file_hash}")
        
        return file_hash
    
    @staticmethod
    def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get comprehensive information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file information
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = file_path.stat()
        
        file_info = {
            "path": str(file_path),
            "name": file_path.name,
            "stem": file_path.stem,
            "suffix": file_path.suffix,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
            "is_file": file_path.is_file(),
            "is_directory": file_path.is_dir(),
            "is_symlink": file_path.is_symlink(),
            "permissions": oct(stat.st_mode)[-3:],
        }
        
        # Add hash for files (not directories)
        if file_path.is_file():
            try:
                file_info["sha256_hash"] = FileUtils.calculate_file_hash(file_path)
            except Exception as e:
                logger.warning(f"Could not calculate hash for {file_path}: {e}")
                file_info["sha256_hash"] = None
        
        return file_info
    
    @staticmethod
    def find_files_by_pattern(
        directory: Union[str, Path],
        pattern: str,
        recursive: bool = True
    ) -> List[Path]:
        """
        Find files matching a pattern in a directory.
        
        Args:
            directory: Directory to search in
            pattern: Glob pattern to match (e.g., "*.dat", "**/*.nwb")
            recursive: Whether to search recursively
            
        Returns:
            List of matching file paths
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if recursive and not pattern.startswith("**/"):
            pattern = f"**/{pattern}"
        
        matches = list(directory.glob(pattern))
        
        # Filter to only files (not directories)
        file_matches = [p for p in matches if p.is_file()]
        
        logger.info(f"Found {len(file_matches)} files matching pattern '{pattern}' in {directory}")
        
        return file_matches
    
    @staticmethod
    def get_directory_size(directory: Union[str, Path]) -> Dict[str, Any]:
        """
        Calculate the total size of a directory and its contents.
        
        Args:
            directory: Directory path
            
        Returns:
            Dictionary with size information
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for item in directory.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
            elif item.is_dir():
                dir_count += 1
        
        size_info = {
            "directory": str(directory),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
            "file_count": file_count,
            "directory_count": dir_count,
            "total_items": file_count + dir_count
        }
        
        logger.info(f"Directory size analysis for {directory}: {size_info['total_size_mb']} MB, {file_count} files")
        
        return size_info
    
    @staticmethod
    def validate_file_access(
        file_path: Union[str, Path],
        check_read: bool = True,
        check_write: bool = False
    ) -> Dict[str, bool]:
        """
        Validate file access permissions.
        
        Args:
            file_path: Path to the file
            check_read: Whether to check read permission
            check_write: Whether to check write permission
            
        Returns:
            Dictionary with access validation results
        """
        file_path = Path(file_path)
        
        access_info = {
            "exists": file_path.exists(),
            "is_file": file_path.is_file() if file_path.exists() else False,
            "readable": False,
            "writable": False,
            "executable": False
        }
        
        if file_path.exists():
            if check_read:
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1)
                    access_info["readable"] = True
                except (PermissionError, OSError):
                    access_info["readable"] = False
            
            if check_write:
                try:
                    # Try to open in append mode to test write access
                    with open(file_path, 'ab'):
                        pass
                    access_info["writable"] = True
                except (PermissionError, OSError):
                    access_info["writable"] = False
            
            # Check if file is executable
            access_info["executable"] = file_path.stat().st_mode & 0o111 != 0
        
        return access_info
    
    @staticmethod
    def cleanup_temp_files(
        temp_directory: Union[str, Path],
        max_age_hours: int = 24,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up temporary files older than specified age.
        
        Args:
            temp_directory: Directory containing temporary files
            max_age_hours: Maximum age in hours before files are deleted
            dry_run: If True, only report what would be deleted without actually deleting
            
        Returns:
            Dictionary with cleanup results
        """
        import time
        
        temp_directory = Path(temp_directory)
        
        if not temp_directory.exists():
            return {"error": f"Temp directory not found: {temp_directory}"}
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        files_to_delete = []
        total_size = 0
        
        for file_path in temp_directory.rglob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_size = file_path.stat().st_size
                    files_to_delete.append({
                        "path": str(file_path),
                        "size": file_size,
                        "age_hours": round(file_age / 3600, 1)
                    })
                    total_size += file_size
        
        cleanup_result = {
            "temp_directory": str(temp_directory),
            "files_found": len(files_to_delete),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "dry_run": dry_run,
            "deleted_files": []
        }
        
        if not dry_run:
            for file_info in files_to_delete:
                try:
                    Path(file_info["path"]).unlink()
                    cleanup_result["deleted_files"].append(file_info)
                    logger.info(f"Deleted temp file: {file_info['path']}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_info['path']}: {e}")
        
        logger.info(f"Cleanup completed: {len(cleanup_result['deleted_files'])} files deleted, {cleanup_result['total_size_mb']} MB freed")
        
        return cleanup_result