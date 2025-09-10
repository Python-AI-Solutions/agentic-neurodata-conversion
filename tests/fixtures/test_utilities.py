"""
Test utilities and helper functions.

This module provides common utilities and helper functions
used across different test modules.
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator, Generator, Callable
from unittest.mock import patch, Mock, AsyncMock
import tempfile
import shutil


class TestTimer:
    """Utility for timing test operations."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
    
    def stop(self) -> float:
        """Stop timing and return elapsed time."""
        self.end_time = time.time()
        if self.start_time is None:
            raise ValueError("Timer not started")
        return self.end_time - self.start_time
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time."""
        if self.start_time is None:
            raise ValueError("Timer not started")
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time


@contextmanager
def temporary_directory() -> Generator[Path, None, None]:
    """Create a temporary directory that is cleaned up after use."""
    temp_dir = tempfile.mkdtemp()
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@contextmanager
def temporary_file(suffix: str = "", content: bytes = b"") -> Generator[Path, None, None]:
    """Create a temporary file that is cleaned up after use."""
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with open(fd, 'wb') as f:
            f.write(content)
        yield Path(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


@asynccontextmanager
async def async_temporary_directory() -> AsyncGenerator[Path, None]:
    """Async version of temporary_directory."""
    temp_dir = tempfile.mkdtemp()
    try:
        yield Path(temp_dir)
    finally:
        await asyncio.get_event_loop().run_in_executor(
            None, shutil.rmtree, temp_dir
        )


class MockPatcher:
    """Utility for managing multiple mock patches."""
    
    def __init__(self):
        self.patches: List[patch] = []
        self.mocks: Dict[str, Mock] = {}
    
    def add_patch(self, target: str, mock_obj: Optional[Mock] = None, **kwargs) -> Mock:
        """Add a patch and return the mock object."""
        if mock_obj is None:
            mock_obj = Mock(**kwargs)
        
        patcher = patch(target, mock_obj)
        self.patches.append(patcher)
        self.mocks[target] = mock_obj
        return mock_obj
    
    def add_async_patch(self, target: str, mock_obj: Optional[AsyncMock] = None, **kwargs) -> AsyncMock:
        """Add an async patch and return the mock object."""
        if mock_obj is None:
            mock_obj = AsyncMock(**kwargs)
        
        patcher = patch(target, mock_obj)
        self.patches.append(patcher)
        self.mocks[target] = mock_obj
        return mock_obj
    
    def start_all(self):
        """Start all patches."""
        for patcher in self.patches:
            patcher.start()
    
    def stop_all(self):
        """Stop all patches."""
        for patcher in self.patches:
            patcher.stop()
    
    def __enter__(self):
        self.start_all()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_all()


class AssertionHelper:
    """Helper class for common test assertions."""
    
    @staticmethod
    def assert_dict_contains(actual: Dict[str, Any], expected: Dict[str, Any]):
        """Assert that actual dict contains all key-value pairs from expected dict."""
        for key, value in expected.items():
            assert key in actual, f"Key '{key}' not found in actual dict"
            assert actual[key] == value, f"Value for key '{key}' does not match. Expected: {value}, Actual: {actual[key]}"
    
    @staticmethod
    def assert_list_contains_items(actual: List[Any], expected_items: List[Any]):
        """Assert that actual list contains all expected items."""
        for item in expected_items:
            assert item in actual, f"Item '{item}' not found in actual list"
    
    @staticmethod
    def assert_file_exists(file_path: Path):
        """Assert that file exists."""
        assert file_path.exists(), f"File does not exist: {file_path}"
    
    @staticmethod
    def assert_file_not_exists(file_path: Path):
        """Assert that file does not exist."""
        assert not file_path.exists(), f"File should not exist: {file_path}"
    
    @staticmethod
    def assert_json_file_contains(file_path: Path, expected_data: Dict[str, Any]):
        """Assert that JSON file contains expected data."""
        AssertionHelper.assert_file_exists(file_path)
        
        with open(file_path, 'r') as f:
            actual_data = json.load(f)
        
        AssertionHelper.assert_dict_contains(actual_data, expected_data)
    
    @staticmethod
    def assert_execution_time_under(func: Callable, max_time: float, *args, **kwargs):
        """Assert that function execution time is under max_time seconds."""
        timer = TestTimer()
        timer.start()
        
        try:
            result = func(*args, **kwargs)
            elapsed = timer.stop()
            
            assert elapsed < max_time, f"Execution took {elapsed:.3f}s, expected under {max_time}s"
            return result
        except Exception as e:
            timer.stop()
            raise e
    
    @staticmethod
    async def assert_async_execution_time_under(coro_func: Callable, max_time: float, *args, **kwargs):
        """Assert that async function execution time is under max_time seconds."""
        timer = TestTimer()
        timer.start()
        
        try:
            result = await coro_func(*args, **kwargs)
            elapsed = timer.stop()
            
            assert elapsed < max_time, f"Execution took {elapsed:.3f}s, expected under {max_time}s"
            return result
        except Exception as e:
            timer.stop()
            raise e


class DataValidator:
    """Utility for validating test data."""
    
    @staticmethod
    def validate_nwb_metadata(metadata: Dict[str, Any]) -> List[str]:
        """Validate NWB metadata and return list of issues."""
        issues = []
        
        required_fields = [
            "identifier",
            "session_description", 
            "experimenter",
            "lab",
            "institution"
        ]
        
        for field in required_fields:
            if field not in metadata:
                issues.append(f"Missing required field: {field}")
            elif not metadata[field]:
                issues.append(f"Empty required field: {field}")
        
        # Validate data types
        if "experimenter" in metadata and not isinstance(metadata["experimenter"], list):
            issues.append("experimenter should be a list")
        
        if "session_start_time" in metadata:
            try:
                from datetime import datetime
                if isinstance(metadata["session_start_time"], str):
                    datetime.fromisoformat(metadata["session_start_time"].replace('Z', '+00:00'))
            except ValueError:
                issues.append("Invalid session_start_time format")
        
        return issues
    
    @staticmethod
    def validate_conversion_result(result: Dict[str, Any]) -> List[str]:
        """Validate conversion result and return list of issues."""
        issues = []
        
        required_fields = ["status", "output_nwb_path"]
        
        for field in required_fields:
            if field not in result:
                issues.append(f"Missing required field: {field}")
        
        if result.get("status") not in ["success", "error", "warning"]:
            issues.append(f"Invalid status: {result.get('status')}")
        
        if result.get("status") == "success":
            nwb_path = result.get("output_nwb_path")
            if not nwb_path or not Path(nwb_path).exists():
                issues.append("NWB file not found at specified path")
        
        return issues


class PerformanceProfiler:
    """Utility for profiling test performance."""
    
    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}
    
    def measure(self, operation_name: str, func: Callable, *args, **kwargs):
        """Measure execution time of a function."""
        timer = TestTimer()
        timer.start()
        
        try:
            result = func(*args, **kwargs)
            elapsed = timer.stop()
            
            if operation_name not in self.measurements:
                self.measurements[operation_name] = []
            self.measurements[operation_name].append(elapsed)
            
            return result
        except Exception as e:
            timer.stop()
            raise e
    
    async def measure_async(self, operation_name: str, coro_func: Callable, *args, **kwargs):
        """Measure execution time of an async function."""
        timer = TestTimer()
        timer.start()
        
        try:
            result = await coro_func(*args, **kwargs)
            elapsed = timer.stop()
            
            if operation_name not in self.measurements:
                self.measurements[operation_name] = []
            self.measurements[operation_name].append(elapsed)
            
            return result
        except Exception as e:
            timer.stop()
            raise e
    
    def get_stats(self, operation_name: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        if operation_name not in self.measurements:
            return {}
        
        times = self.measurements[operation_name]
        return {
            "count": len(times),
            "min": min(times),
            "max": max(times),
            "mean": sum(times) / len(times),
            "total": sum(times)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations."""
        return {op: self.get_stats(op) for op in self.measurements.keys()}


def create_sample_nwb_metadata() -> Dict[str, Any]:
    """Create sample NWB metadata for testing."""
    return {
        "identifier": "test_session_001",
        "session_description": "Test recording session for unit testing",
        "experimenter": ["Test User"],
        "lab": "Test Lab",
        "institution": "Test Institution",
        "experiment_description": "Test experiment for validating conversion pipeline",
        "session_start_time": "2024-01-01T10:00:00",
        "keywords": ["test", "neuroscience", "nwb"],
        "related_publications": [],
        "notes": "Generated for testing purposes"
    }


def create_sample_files_map(temp_dir: Path) -> Dict[str, str]:
    """Create sample files map for testing."""
    # Create sample data files
    recording_file = temp_dir / "recording.dat"
    recording_file.write_bytes(b"mock recording data" * 1000)
    
    events_file = temp_dir / "events.txt"
    events_file.write_text("timestamp,event\n1.0,start\n2.0,end\n")
    
    metadata_file = temp_dir / "metadata.json"
    metadata_file.write_text(json.dumps(create_sample_nwb_metadata(), indent=2))
    
    return {
        "recording": str(recording_file),
        "events": str(events_file),
        "metadata": str(metadata_file)
    }


async def wait_for_condition(condition: Callable[[], bool], timeout: float = 5.0, interval: float = 0.1) -> bool:
    """Wait for a condition to become true within timeout."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition():
            return True
        await asyncio.sleep(interval)
    
    return False


def retry_on_failure(max_attempts: int = 3, delay: float = 0.1):
    """Decorator to retry function on failure."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
                    continue
            
            raise last_exception
        
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                    continue
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator