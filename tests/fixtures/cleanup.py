"""
Test cleanup utilities.

This module provides utilities for cleaning up test artifacts,
temporary files, and test environments.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Set, Optional, Pattern
import re
import logging
from contextlib import contextmanager


logger = logging.getLogger(__name__)


class TestCleanupManager:
    """Manages cleanup of test artifacts and temporary resources."""
    
    def __init__(self):
        self.temp_files: Set[Path] = set()
        self.temp_dirs: Set[Path] = set()
        self.created_files: Set[Path] = set()
        self.created_dirs: Set[Path] = set()
        self.cleanup_patterns: List[Pattern] = []
        
        # Default cleanup patterns
        self.add_cleanup_pattern(r".*\.nwb$")
        self.add_cleanup_pattern(r".*\.ttl$")
        self.add_cleanup_pattern(r".*_test_.*")
        self.add_cleanup_pattern(r"test_.*\.py$")
        self.add_cleanup_pattern(r".*\.tmp$")
        self.add_cleanup_pattern(r".*\.log$")
    
    def add_cleanup_pattern(self, pattern: str):
        """Add a regex pattern for files to clean up."""
        self.cleanup_patterns.append(re.compile(pattern))
    
    def register_temp_file(self, file_path: Path) -> Path:
        """Register a temporary file for cleanup."""
        self.temp_files.add(file_path)
        return file_path
    
    def register_temp_dir(self, dir_path: Path) -> Path:
        """Register a temporary directory for cleanup."""
        self.temp_dirs.add(dir_path)
        return dir_path
    
    def register_created_file(self, file_path: Path) -> Path:
        """Register a created file for cleanup."""
        self.created_files.add(file_path)
        return file_path
    
    def register_created_dir(self, dir_path: Path) -> Path:
        """Register a created directory for cleanup."""
        self.created_dirs.add(dir_path)
        return dir_path
    
    def create_temp_file(self, suffix: str = "", content: bytes = b"") -> Path:
        """Create and register a temporary file."""
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        
        file_path = Path(temp_path)
        if content:
            file_path.write_bytes(content)
        
        return self.register_temp_file(file_path)
    
    def create_temp_dir(self) -> Path:
        """Create and register a temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        return self.register_temp_dir(temp_dir)
    
    def cleanup_temp_files(self):
        """Clean up registered temporary files."""
        for file_path in self.temp_files.copy():
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Cleaned up temp file: {file_path}")
                self.temp_files.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {file_path}: {e}")
    
    def cleanup_temp_dirs(self):
        """Clean up registered temporary directories."""
        for dir_path in self.temp_dirs.copy():
            try:
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    logger.debug(f"Cleaned up temp dir: {dir_path}")
                self.temp_dirs.remove(dir_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir {dir_path}: {e}")
    
    def cleanup_created_files(self):
        """Clean up registered created files."""
        for file_path in self.created_files.copy():
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Cleaned up created file: {file_path}")
                self.created_files.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up created file {file_path}: {e}")
    
    def cleanup_created_dirs(self):
        """Clean up registered created directories."""
        for dir_path in self.created_dirs.copy():
            try:
                if dir_path.exists() and dir_path.is_dir():
                    shutil.rmtree(dir_path)
                    logger.debug(f"Cleaned up created dir: {dir_path}")
                self.created_dirs.remove(dir_path)
            except Exception as e:
                logger.warning(f"Failed to clean up created dir {dir_path}: {e}")
    
    def cleanup_by_patterns(self, search_dir: Path = None):
        """Clean up files matching registered patterns."""
        if search_dir is None:
            search_dir = Path.cwd()
        
        for file_path in search_dir.rglob("*"):
            if file_path.is_file():
                for pattern in self.cleanup_patterns:
                    if pattern.match(str(file_path.name)):
                        try:
                            file_path.unlink()
                            logger.debug(f"Cleaned up pattern match: {file_path}")
                            break
                        except Exception as e:
                            logger.warning(f"Failed to clean up pattern match {file_path}: {e}")
    
    def cleanup_all(self, search_dir: Path = None):
        """Clean up all registered resources and pattern matches."""
        self.cleanup_temp_files()
        self.cleanup_temp_dirs()
        self.cleanup_created_files()
        self.cleanup_created_dirs()
        self.cleanup_by_patterns(search_dir)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()


class TestEnvironmentCleaner:
    """Cleans up test environment and restores original state."""
    
    def __init__(self):
        self.original_env: dict[str, Optional[str]] = {}
        self.original_cwd: Optional[Path] = None
        self.env_vars_to_restore: Set[str] = set()
    
    def set_env_var(self, key: str, value: str):
        """Set environment variable and remember original value."""
        if key not in self.original_env:
            self.original_env[key] = os.environ.get(key)
            self.env_vars_to_restore.add(key)
        
        os.environ[key] = value
    
    def unset_env_var(self, key: str):
        """Unset environment variable and remember original value."""
        if key not in self.original_env:
            self.original_env[key] = os.environ.get(key)
            self.env_vars_to_restore.add(key)
        
        if key in os.environ:
            del os.environ[key]
    
    def change_cwd(self, new_cwd: Path):
        """Change current working directory and remember original."""
        if self.original_cwd is None:
            self.original_cwd = Path.cwd()
        
        os.chdir(new_cwd)
    
    def restore_environment(self):
        """Restore original environment state."""
        # Restore environment variables
        for key in self.env_vars_to_restore:
            original_value = self.original_env.get(key)
            if original_value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = original_value
        
        # Restore working directory
        if self.original_cwd is not None:
            os.chdir(self.original_cwd)
        
        # Clear tracking
        self.original_env.clear()
        self.env_vars_to_restore.clear()
        self.original_cwd = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.restore_environment()


@contextmanager
def isolated_test_environment(temp_dir: Optional[Path] = None):
    """Context manager for isolated test environment."""
    cleanup_manager = TestCleanupManager()
    env_cleaner = TestEnvironmentCleaner()
    
    # Set up test environment
    env_cleaner.set_env_var("AGENTIC_CONVERTER_ENV", "test")
    env_cleaner.set_env_var("AGENTIC_CONVERTER_LOG_LEVEL", "DEBUG")
    env_cleaner.set_env_var("AGENTIC_CONVERTER_DISABLE_TELEMETRY", "true")
    
    if temp_dir is None:
        temp_dir = cleanup_manager.create_temp_dir()
    
    env_cleaner.change_cwd(temp_dir)
    
    try:
        yield {
            "cleanup_manager": cleanup_manager,
            "env_cleaner": env_cleaner,
            "temp_dir": temp_dir
        }
    finally:
        cleanup_manager.cleanup_all()
        env_cleaner.restore_environment()


def cleanup_test_artifacts(directories: List[Path] = None):
    """Clean up common test artifacts from specified directories."""
    if directories is None:
        directories = [Path.cwd()]
    
    artifact_patterns = [
        "*.nwb",
        "*.ttl", 
        "*.jsonld",
        "*_test_output*",
        "test_*.tmp",
        "*.log",
        "__pycache__",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        "coverage.xml",
        "test-results.xml"
    ]
    
    for directory in directories:
        if not directory.exists():
            continue
        
        for pattern in artifact_patterns:
            for path in directory.rglob(pattern):
                try:
                    if path.is_file():
                        path.unlink()
                        logger.debug(f"Cleaned up artifact: {path}")
                    elif path.is_dir():
                        shutil.rmtree(path)
                        logger.debug(f"Cleaned up artifact dir: {path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up artifact {path}: {e}")


def ensure_clean_test_state():
    """Ensure clean state before running tests."""
    # Clean up any leftover artifacts
    cleanup_test_artifacts()
    
    # Reset environment variables that might affect tests
    test_env_vars = [
        "AGENTIC_CONVERTER_ENV",
        "AGENTIC_CONVERTER_LOG_LEVEL", 
        "AGENTIC_CONVERTER_DATABASE_URL",
        "AGENTIC_CONVERTER_DISABLE_TELEMETRY",
        "AGENTIC_CONVERTER_CACHE_DISABLED"
    ]
    
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]
    
    # Set test environment
    os.environ["AGENTIC_CONVERTER_ENV"] = "test"
    os.environ["AGENTIC_CONVERTER_LOG_LEVEL"] = "DEBUG"


class ResourceMonitor:
    """Monitor resource usage during tests."""
    
    def __init__(self):
        self.start_memory: Optional[float] = None
        self.peak_memory: float = 0.0
        self.file_handles_start: Optional[int] = None
    
    def start_monitoring(self):
        """Start monitoring resources."""
        try:
            import psutil
            process = psutil.Process()
            
            self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
            self.file_handles_start = process.num_fds() if hasattr(process, 'num_fds') else None
            self.peak_memory = self.start_memory
            
        except ImportError:
            logger.warning("psutil not available, resource monitoring disabled")
    
    def update_peak_memory(self):
        """Update peak memory usage."""
        try:
            import psutil
            process = psutil.Process()
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = max(self.peak_memory, current_memory)
        except ImportError:
            pass
    
    def get_memory_usage(self) -> dict[str, float]:
        """Get memory usage statistics."""
        try:
            import psutil
            process = psutil.Process()
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            return {
                "start_mb": self.start_memory or 0.0,
                "current_mb": current_memory,
                "peak_mb": self.peak_memory,
                "increase_mb": current_memory - (self.start_memory or 0.0)
            }
        except ImportError:
            return {}
    
    def get_file_handle_usage(self) -> dict[str, int]:
        """Get file handle usage statistics."""
        try:
            import psutil
            process = psutil.Process()
            current_handles = process.num_fds() if hasattr(process, 'num_fds') else 0
            
            return {
                "start": self.file_handles_start or 0,
                "current": current_handles,
                "increase": current_handles - (self.file_handles_start or 0)
            }
        except ImportError:
            return {}
    
    def check_resource_leaks(self) -> List[str]:
        """Check for potential resource leaks."""
        issues = []
        
        memory_stats = self.get_memory_usage()
        if memory_stats.get("increase_mb", 0) > 100:  # More than 100MB increase
            issues.append(f"High memory increase: {memory_stats['increase_mb']:.1f} MB")
        
        handle_stats = self.get_file_handle_usage()
        if handle_stats.get("increase", 0) > 10:  # More than 10 file handles
            issues.append(f"File handle leak: {handle_stats['increase']} handles")
        
        return issues